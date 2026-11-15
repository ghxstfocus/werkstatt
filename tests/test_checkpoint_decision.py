from __future__ import annotations

from types import SimpleNamespace

from werkstatt import run_followups
from werkstatt.phase_state import PhaseState
from werkstatt.phases import tasks as task_phase
from werkstatt.phases.tasks import _checkpoint_decision_payload
from werkstatt.state import RunState


def _phase(tmp_path, tasks, criteria):
    phase = PhaseState("demo", base_dir=tmp_path)
    phase.init_new("Ziel", tasks, akzeptanzkriterien=criteria)
    return phase


def test_checkpoint_routes_next_planned_task_and_keeps_open_criteria_visible(
    tmp_path,
) -> None:
    phase = _phase(
        tmp_path,
        [
            {"id": "t1", "name": "First", "criterion_refs": ["AC1"]},
            {
                "id": "t2", "name": "Second", "action": "verify",
                "criterion_refs": ["AC2"], "dependencies": ["t1"],
            },
        ],
        ["First criterion", "Second criterion"],
    )
    phase.mark_done("t1")
    next_task = phase.get_next_task()

    decision = _checkpoint_decision_payload(phase, next_task)

    assert decision["decision"] == "execute_planned_task"
    assert decision["next_task_id"] == "t2"
    assert decision["next_executor"] == "verify_and_review"
    assert decision["criteria_task_coverage"]["covered"] == ["AC1"]
    assert decision["criteria_task_coverage"]["uncovered"] == ["AC2"]
    assert decision["goal_candidate_before_final_verify"] is False
    assert decision["final_verify_required"] is True


def test_checkpoint_does_not_claim_goal_for_untracked_criteria(tmp_path) -> None:
    phase = _phase(
        tmp_path,
        [{"id": "t1", "name": "Read-only inventory", "action": "read"}],
        ["Inventory is complete"],
    )
    phase.mark_done("t1")

    decision = _checkpoint_decision_payload(phase, None)

    assert decision["decision"] == "verify_untracked_criteria"
    assert decision["next_executor"] == "phase_end_verify"
    assert decision["goal_candidate_before_final_verify"] is False


def test_checkpoint_calls_out_failed_task_instead_of_claiming_completion(
    tmp_path,
) -> None:
    phase = _phase(
        tmp_path,
        [{"id": "t1", "name": "Implement", "criterion_refs": ["AC1"]}],
        ["Feature works"],
    )
    phase.mark_failed("t1", failure="builder_failed")

    decision = _checkpoint_decision_payload(phase, None)

    assert decision["decision"] == "verify_with_failed_tasks"
    assert decision["goal_candidate_before_final_verify"] is False


def test_checkpoint_marks_complete_graph_as_only_candidate_before_verify(
    tmp_path,
) -> None:
    phase = _phase(
        tmp_path,
        [{"id": "t1", "name": "Implement", "criterion_refs": ["AC1"]}],
        ["Feature works"],
    )
    phase.mark_done("t1")

    decision = _checkpoint_decision_payload(phase, None)

    assert decision["decision"] == "run_phase_end_verify"
    assert decision["goal_candidate_before_final_verify"] is True
    assert decision["final_verify_required"] is True


def test_checkpoint_carries_compact_verify_evidence_without_raw_output(
    tmp_path,
) -> None:
    phase = _phase(
        tmp_path,
        [{"id": "t1", "name": "Implement", "criterion_refs": ["AC1"]}],
        ["Feature works"],
    )
    phase.mark_done("t1")
    state = RunState()
    state.last_verify_results = [{
        "stage_id": "pytest_changed",
        "ok": True,
        "exit_code": 0,
        "artifact_sha256": "a" * 64,
        "error_excerpt": "raw tool output must stay out",
    }]

    decision = _checkpoint_decision_payload(phase, None, state=state)

    assert decision["last_verify_evidence"] == [{
        "stage_id": "pytest_changed",
        "ok": True,
        "exit_code": 0,
        "artifact_sha256": "a" * 64,
    }]


def test_task_loop_persists_auditable_checkpoint_decision(tmp_path, monkeypatch) -> None:
    task = {
        "id": "t1", "name": "Implement", "action": "update",
        "criterion_refs": ["AC1"],
    }
    phase = _phase(tmp_path, [task], ["Feature works"])
    phase.mark_done("t1")
    state = RunState(
        project_dir=tmp_path,
        project_name="demo",
        aufgabe="Feature works",
        tasks=[task],
        budget={},
    )
    audit_events = []
    fake_store = SimpleNamespace(
        get_run_record=lambda _project, _run: {"checkpoint_version": 7},
    )
    monkeypatch.setattr("werkstatt.audit.get_run_id", lambda: "demo-run-1")
    monkeypatch.setattr("werkstatt.agent._enforce_run_budget", lambda _state: False)
    monkeypatch.setattr(task_phase, "EventStore", lambda: fake_store)
    monkeypatch.setattr(task_phase, "_persist_run_checkpoint", lambda *_a, **_kw: None)
    monkeypatch.setattr(task_phase, "audit", lambda *args: audit_events.append(args) or True)
    monkeypatch.setattr(
        run_followups, "reconcile_chat_followups", lambda *_args: False,
    )

    result = task_phase._phase_tasks_loop(state, phase)

    assert result[0] == 0
    event = next(args for args in audit_events if args[0] == "loop_checkpoint_decision")
    assert event[1]["checkpoint_id"] == "demo-run-1:7"
    assert event[1]["decision"] == "run_phase_end_verify"
    assert event[1]["goal_candidate_before_final_verify"] is True
