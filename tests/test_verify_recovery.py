from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from werkstatt.phase_state import PhaseState
from werkstatt.roles.verify_recovery import run_verify_recovery


def _current_failure(tmp_path: Path) -> tuple[PhaseState, Path]:
    source = tmp_path / "src" / "feature.py"
    source.parent.mkdir()
    source.write_text("value = 1\n", encoding="utf-8")
    phase = PhaseState("sample_app", base_dir=tmp_path / ".werkstatt")
    phase.init_new(
        "Update feature",
        [{
            "id": "task-1", "action": "update", "task_files": ["src/feature.py"],
            "criterion_refs": ["AC1"],
        }],
        akzeptanzkriterien=["Feature updates"],
    )
    phase.run_id = "verify-recovery-test"
    phase.mark_running("task-1")
    assert phase.record_task_build_checkpoint("task-1")
    assert phase.record_task_verify_failure_checkpoint(
        "task-1", ["ruff: E501 line too long"],
    )
    return phase, source


def test_verify_recovery_calls_only_failed_configured_stages_once(tmp_path, monkeypatch):
    phase, _source = _current_failure(tmp_path)
    state = SimpleNamespace(
        project_dir=tmp_path,
        budget={"max_llm_calls": 1},
        last_verify_errors=[],
    )
    monkeypatch.setattr("werkstatt.verify._stage_ids", lambda _root: ["ruff", "pytest"])
    calls = []

    def recover(_state, **kwargs):
        calls.append(kwargs)
        return True

    monkeypatch.setattr("werkstatt.reflection._reflection_loop_core", recover)

    result = run_verify_recovery(state, phase, "task-1")

    assert result["status"] == "repair_handoff"
    assert calls == [{
        "max_runden": 1,
        "error_context": '{"errors": ["ruff: E501 line too long"], "source": "verify"}',
        "phase": "post_build",
        "verify_stage_ids": {"ruff"},
    }]
    assert phase.get_task("task-1").get("verify_failure_checkpoint") is None
    assert phase.task_build_checkpoint_is_current("task-1")


def test_verify_recovery_refuses_unmapped_error_without_builder_call(tmp_path, monkeypatch):
    phase, _source = _current_failure(tmp_path)
    state = SimpleNamespace(project_dir=tmp_path, budget={"max_llm_calls": 1})
    monkeypatch.setattr("werkstatt.verify._stage_ids", lambda _root: ["pytest"])

    def forbidden(*_args, **_kwargs):
        raise AssertionError("unmapped failure must not call Builder")

    monkeypatch.setattr("werkstatt.reflection._reflection_loop_core", forbidden)
    result = run_verify_recovery(state, phase, "task-1")
    assert result["status"] == "human_review"
    assert result["reason"] == "stage_unmapped"


def test_verify_recovery_refuses_missing_budget(tmp_path, monkeypatch):
    phase, _source = _current_failure(tmp_path)
    state = SimpleNamespace(project_dir=tmp_path, budget={})
    monkeypatch.setattr("werkstatt.verify._stage_ids", lambda _root: ["ruff"])
    result = run_verify_recovery(state, phase, "task-1")
    assert result["status"] == "human_review"
    assert result["reason"] == "run_budget_exhausted"
