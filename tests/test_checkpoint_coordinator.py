"""Tests for bounded shared-Chat decisions at planner checkpoints."""
from __future__ import annotations

import hashlib
import json

from werkstatt.state import LLMReply, RunState


def test_task_action_policy_lives_in_checkpoint_coordinator() -> None:
    from werkstatt.checkpoint_coordinator import choose_task_checkpoint_action
    from werkstatt.phases.tasks import _checkpoint_decision_payload

    assert choose_task_checkpoint_action.__module__ == (
        "werkstatt.checkpoint_coordinator"
    )
    # Existing test/import callers keep a compatibility alias while runtime
    # policy has a single owner outside the phase executor.
    assert _checkpoint_decision_payload is choose_task_checkpoint_action


def test_checkpoint_role_recommendation_uses_shared_chat_route_and_hashes(
    tmp_path, monkeypatch,
) -> None:
    from werkstatt.checkpoint_coordinator import recommend_checkpoint_role

    state = RunState(
        aufgabe="Ergaenze src/feature.py sinnvoll",
        project_name="demo",
        project_dir=tmp_path,
        run_id="demo-run-1",
        api_key="test-key",
    )
    source = tmp_path / "src" / "feature.py"
    source.parent.mkdir()
    source.write_text("def feature(): return 1\n", encoding="utf-8")
    source_record = {
        "path": "src/feature.py",
        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "complete": True,
    }
    captured = {}

    def fake_ask_llm(*args, **kwargs):
        captured["args"] = args
        captured.update(kwargs)
        return LLMReply(
            ok=True,
            content=json.dumps({
                "role": "scout",
                "reason_code": "more_repository_evidence_needed",
            }),
            request_sha256="a" * 64,
        )

    monkeypatch.setattr("werkstatt.agent.ask_llm", fake_ask_llm)
    recommendation = recommend_checkpoint_role(
        state,
        allowed_roles=("architect", "scout"),
        deterministic_role="architect",
        evidence=("user_goal", "explorer_source_evidence"),
        source_evidence=(source_record,),
    )

    assert recommendation["role"] == "scout"
    assert recommendation["source"] == "project_chat_model"
    assert captured["rolle"] == "project-coordinator"
    assert captured["reasoning_override"] is True
    assert captured["context_manifest"]["budget_event"] == (
        "project_coordinator_context_budget"
    )
    assert captured["context_manifest"]["required_context_complete"] is True
    assert len(captured["context_manifest"]["user_sha256"]) == 64
    assert len(captured["context_manifest"]["system_sha256"]) == 64
    sent_context = json.loads(captured["args"][2])
    assert sent_context["current_source_evidence"] == [source_record]


def test_checkpoint_role_rejects_unavailable_role_and_keeps_default(
    tmp_path, monkeypatch,
) -> None:
    from werkstatt.checkpoint_coordinator import recommend_checkpoint_role

    state = RunState(
        aufgabe="Goal", project_name="demo", project_dir=tmp_path,
        run_id="demo-run-2", api_key="test-key",
    )
    source = tmp_path / "src" / "feature.py"
    source.parent.mkdir()
    source.write_text("def feature(): return 1\n", encoding="utf-8")
    source_record = {
        "path": "src/feature.py",
        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "complete": True,
    }
    monkeypatch.setattr(
        "werkstatt.agent.ask_llm",
        lambda *args, **kwargs: LLMReply(
            ok=True,
            content='{"role":"builder_direct",'
            '"reason_code":"source_evidence_sufficient"}',
        ),
    )

    recommendation = recommend_checkpoint_role(
        state,
        allowed_roles=("architect", "scout"),
        deterministic_role="architect",
        evidence=("user_goal", "explorer_source_evidence"),
        source_evidence=(source_record,),
    )

    assert recommendation["role"] == "architect"
    assert recommendation["source"] == "deterministic_fallback"
    assert recommendation["reason_code"] == "coordinator_action_rejected"


def test_checkpoint_role_does_not_call_model_for_single_candidate(
    tmp_path, monkeypatch,
) -> None:
    from werkstatt.checkpoint_coordinator import recommend_checkpoint_role

    state = RunState(
        aufgabe="Goal", project_name="demo", project_dir=tmp_path,
        run_id="demo-run-3", api_key="test-key",
    )

    def unexpected_call(*args, **kwargs):
        raise AssertionError("single candidate must not call the model")

    monkeypatch.setattr("werkstatt.agent.ask_llm", unexpected_call)
    recommendation = recommend_checkpoint_role(
        state,
        allowed_roles=("scout",),
        deterministic_role="scout",
        evidence=("user_goal",),
    )

    assert recommendation["role"] == "scout"
    assert recommendation["source"] == "deterministic_fallback"


def test_checkpoint_role_choice_controls_scout_only_with_current_evidence(
    tmp_path,
) -> None:
    from werkstatt.checkpoint_coordinator import apply_checkpoint_role_choice

    source = tmp_path / "src" / "feature.py"
    source.parent.mkdir()
    source.write_text("value = 1\n", encoding="utf-8")
    evidence = ({
        "path": "src/feature.py",
        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "complete": True,
    },)

    scout = apply_checkpoint_role_choice(
        tmp_path,
        role="scout",
        deterministic_skip_path="src/feature.py",
        source_evidence=evidence,
        deterministic_reason="deterministic_skip",
    )
    assert scout["skip_path"] is None
    assert scout["reason"] == "project_coordinator_selected_scout"

    architect = apply_checkpoint_role_choice(
        tmp_path,
        role="architect",
        deterministic_skip_path="src/feature.py",
        source_evidence=evidence,
        deterministic_reason="deterministic_skip",
    )
    assert architect["skip_path"] == "src/feature.py"
    assert architect["source_files"] == ["src/feature.py"]

    source.write_text("value = 2\n", encoding="utf-8")
    stale = apply_checkpoint_role_choice(
        tmp_path,
        role="architect",
        deterministic_skip_path="src/feature.py",
        source_evidence=evidence,
        deterministic_reason="deterministic_skip",
    )
    assert stale["skip_path"] is None
    assert stale["reason"] == "coordinator_source_evidence_stale"
