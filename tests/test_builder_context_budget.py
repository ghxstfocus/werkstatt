from __future__ import annotations

from unittest.mock import patch

from werkstatt.roles.builder.run import (
    _budget_builder_context,
    _build_patches_fuer_datei,
)
from werkstatt.state import RunState


def test_builder_context_keeps_required_and_omits_optional_as_whole() -> None:
    prompt, meta = _budget_builder_context(
        [("TASK", "TASK-EVIDENCE"), ("FILE", "COMPLETE-FILE")],
        [("URGENT", "URGENT-EVIDENCE"), ("OPTIONAL", "X" * 500)],
        max_chars=1_400,
    )

    assert prompt is not None
    assert "TASK-EVIDENCE" in prompt
    assert "COMPLETE-FILE" in prompt
    assert "URGENT-EVIDENCE" in prompt
    assert "X" * 500 not in prompt
    assert "NICHT GELADENE KONTEXTABSCHNITTE" in prompt
    assert meta["omitted_optional"] == ["OPTIONAL"]
    assert meta["blocked"] is False


def test_builder_context_blocks_without_truncating_required_evidence() -> None:
    prompt, meta = _budget_builder_context(
        [("TASK", "T" * 20), ("FILE", "F" * 20)],
        [("SKILL", "S")],
        max_chars=30,
    )

    assert prompt is None
    assert meta["blocked"] is True
    assert meta["required_chars"] == 42
    assert meta["required_sections"] == ["TASK", "FILE"]


def test_builder_does_not_call_model_when_required_context_exceeds_budget(
    tmp_path,
) -> None:
    target = tmp_path / "large.py"
    target.write_text("#" + "x" * 61_000, encoding="utf-8")
    state = RunState(
        api_key="test-key",
        project_dir=tmp_path,
        project_name="demo",
        aktuelle_task={
            "name": "Update large.py",
            "description": "Preserve all evidence",
            "action": "update",
            "task_files": ["large.py"],
        },
    )
    with patch("werkstatt.roles.builder._common.ask_llm") as ask_llm, patch(
        "werkstatt.roles.builder._common.audit"
    ) as audit:
        patches = _build_patches_fuer_datei(
            state, "large.py", "Update the file safely.", "test-key",
        )

    assert patches == []
    ask_llm.assert_not_called()
    budget_event = next(
        args for args, _ in audit.call_args_list
        if args[0] == "builder_context_budget"
    )
    assert budget_event[1]["blocked"] is True
    assert budget_event[1]["required_chars"] > 60_000
