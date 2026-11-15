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


def test_run_coordinator_dispatches_one_task_at_a_time(tmp_path) -> None:
    from werkstatt.loop import _run_coordinator_action

    phase = _phase(
        tmp_path,
        [
            {"id": "t1", "action": "read", "criterion_refs": ["AC1"]},
            {
                "id": "t2", "action": "update", "criterion_refs": ["AC1"],
                "dependencies": ["t1"],
            },
        ],
        ["Feature works"],
    )
    state = RunState()

    first = _run_coordinator_action(phase, state)
    assert first["coordinator_action"] == "execute_task_checkpoint"
    assert first["next_task_id"] == "t1"
    assert first["next_executor"] == "read_only_task"

    phase.mark_done("t1")
    second = _run_coordinator_action(phase, state)
    assert second["coordinator_action"] == "execute_task_checkpoint"
    assert second["next_task_id"] == "t2"
    assert second["next_executor"] == "builder"

    phase.mark_done("t2")
    final = _run_coordinator_action(phase, state)
    assert final["coordinator_action"] == "finalize_run"
    assert final["next_executor"] == "phase_end_verify"


def test_run_coordinator_rejects_unknown_task_action(tmp_path) -> None:
    from werkstatt.loop import _run_coordinator_action

    phase = _phase(
        tmp_path,
        [{"id": "t1", "action": "shell", "criterion_refs": ["AC1"]}],
        ["Feature works"],
    )

    decision = _run_coordinator_action(phase, RunState())

    assert decision["coordinator_action"] == "reject_checkpoint"
    assert decision["decision"] == "reject_invalid_task_action"


def test_run_coordinator_requeues_stale_criterion_evidence(tmp_path) -> None:
    from werkstatt.loop import _run_coordinator_action

    project_dir = tmp_path / "project"
    (project_dir / "src").mkdir(parents=True)
    source = project_dir / "src" / "main.py"
    source.write_text("value = 1\n", encoding="utf-8")
    phase = PhaseState("demo", base_dir=project_dir / ".werkstatt")
    phase.run_id = "demo-run"
    phase.init_new(
        "Revalidate content after a later change",
        [{
            "id": "t1", "action": "update", "criterion_refs": ["AC1"],
            "task_files": ["src/main.py"],
        }],
        akzeptanzkriterien=["Current source content is verified"],
    )
    assert phase.record_task_verify_evidence(
        "t1",
        [{
            "stage_id": "pytest_changed", "exit_code": 0, "ok": True,
            "scope_files": ["src/main.py"],
        }],
        phase="post_build",
    )
    phase.mark_done("t1")
    source.write_text("value = 2\n", encoding="utf-8")

    decision = _run_coordinator_action(phase, RunState())

    assert decision["coordinator_action"] == "execute_task_checkpoint"
    assert decision["next_executor"] == "verify_and_review"
    assert decision["next_task_id"] == "t1"
    assert decision["verification_only"] is True
    assert decision["stale_tasks_queued"] == ["t1"]


def test_run_coordinator_resolves_blocked_graph_before_stale_verify(tmp_path) -> None:
    from werkstatt.loop import _run_coordinator_action

    project_dir = tmp_path / "project"
    (project_dir / "src").mkdir(parents=True)
    source = project_dir / "src" / "main.py"
    source.write_text("value = 1\n", encoding="utf-8")
    phase = PhaseState("demo", base_dir=project_dir / ".werkstatt")
    phase.run_id = "demo-run"
    phase.init_new(
        "Resolve graph before re-verifying",
        [
            {
                "id": "t1", "action": "update", "criterion_refs": ["AC1"],
                "task_files": ["src/main.py"],
            },
            {
                "id": "t2", "action": "update", "dependencies": ["missing"],
                "criterion_refs": ["AC1"], "task_files": ["src/main.py"],
            },
        ],
        akzeptanzkriterien=["Current source content is verified"],
    )
    assert phase.record_task_verify_evidence(
        "t1",
        [{
            "stage_id": "pytest_changed", "exit_code": 0, "ok": True,
            "scope_files": ["src/main.py"],
        }],
        phase="post_build",
    )
    phase.mark_done("t1")
    source.write_text("value = 2\n", encoding="utf-8")

    decision = _run_coordinator_action(phase, RunState())

    assert decision["coordinator_action"] == "resolve_task_graph"
    assert decision["stale_tasks_queued"] == []
    assert phase.get_task("t1").get("verification_pending") is not True


def test_run_coordinator_stops_after_graph_is_already_blocked(tmp_path) -> None:
    from werkstatt.loop import _run_coordinator_action

    phase = _phase(
        tmp_path,
        [{
            "id": "t1", "action": "update", "criterion_refs": ["AC1"],
            "dependencies": ["missing"],
        }],
        ["Feature works"],
    )
    phase.mark_blocked("t1", grund="deps:missing")

    decision = _run_coordinator_action(phase, RunState())

    assert decision["task_progress"]["pending"] == 0
    assert decision["task_progress"]["blocked"] == 1
    assert decision["decision"] == "reject_blocked_graph"
    assert decision["coordinator_action"] == "reject_checkpoint"
    assert decision["goal_candidate_before_final_verify"] is False


def test_task_dispatch_returns_at_next_persisted_boundary(
    tmp_path, monkeypatch,
) -> None:
    phase = _phase(
        tmp_path,
        [
            {"id": "t1", "action": "read", "criterion_refs": ["AC1"]},
            {"id": "t2", "action": "read", "criterion_refs": ["AC1"]},
        ],
        ["Inventory is complete"],
    )
    state = RunState(
        project_dir=tmp_path,
        project_name="demo",
        aufgabe="Inventory is complete",
        tasks=phase.data["tasks"],
    )
    monkeypatch.setattr("werkstatt.audit.get_run_id", lambda: "")
    monkeypatch.setattr(task_phase, "audit", lambda *_a, **_kw: True)

    result = task_phase._phase_tasks_loop(state, phase, max_task_steps=1)

    assert result[0] == 0
    assert phase.get_task("t1")["status"] == "done"
    assert phase.get_task("t2")["status"] == "pending"


def test_task_dispatch_rejects_empty_step_limit(tmp_path) -> None:
    phase = _phase(
        tmp_path,
        [{"id": "t1", "action": "read", "criterion_refs": ["AC1"]}],
        ["Inventory is complete"],
    )
    state = RunState(project_dir=tmp_path, project_name="demo")

    import pytest

    with pytest.raises(ValueError, match="max_task_steps"):
        task_phase._phase_tasks_loop(state, phase, max_task_steps=0)


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
