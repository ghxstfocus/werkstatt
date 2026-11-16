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
    phase.data["setup_complete"] = True
    phase.data["plan_complete"] = True
    return phase


def _state_after_setup(goal: str = "Ziel") -> RunState:
    state = RunState(aufgabe=goal)
    state.coordinator_setup_context_ready = True
    return state


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


def test_checkpoint_replans_only_unassigned_criteria_after_graph_completion(
    tmp_path,
) -> None:
    phase = _phase(
        tmp_path,
        [{"id": "t1", "name": "First criterion", "criterion_refs": ["AC1"]}],
        ["First criterion", "Second criterion"],
    )
    phase.mark_done("t1")

    decision = _checkpoint_decision_payload(phase, None)

    assert decision["decision"] == "replan_unassigned_criteria"
    assert decision["next_executor"] == "planner_and_plan_gate"
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


def test_checkpoint_replans_eligible_failed_task_instead_of_claiming_completion(
    tmp_path,
) -> None:
    phase = _phase(
        tmp_path,
        [{"id": "t1", "name": "Implement", "criterion_refs": ["AC1"]}],
        ["Feature works"],
    )
    phase.mark_failed("t1", failure="builder_failed")

    decision = _checkpoint_decision_payload(phase, None)

    assert decision["decision"] == "replan_failed_criteria"
    assert decision["next_executor"] == "planner_and_plan_gate"


def test_checkpoint_replans_only_eligible_failed_criterion_tasks(tmp_path) -> None:
    phase = _phase(
        tmp_path,
        [
            {"id": "done", "name": "First", "criterion_refs": ["AC1"]},
            {"id": "failed", "name": "Second", "criterion_refs": ["AC2"]},
        ],
        ["First criterion", "Second criterion"],
    )
    phase.mark_done("done")
    phase.mark_failed("failed", failure="builder_failed")

    decision = _checkpoint_decision_payload(phase, None)

    assert decision["decision"] == "replan_failed_criteria"
    assert decision["next_executor"] == "planner_and_plan_gate"
    assert decision["criteria_task_coverage"]["uncovered"] == ["AC2"]


def test_checkpoint_does_not_replan_unapproved_failure_classes(tmp_path) -> None:
    phase = _phase(
        tmp_path,
        [{"id": "failed", "name": "Second", "criterion_refs": ["AC1"]}],
        ["Criterion"],
    )
    phase.mark_failed("failed", failure="reflection_erschoepft_rejected")

    decision = _checkpoint_decision_payload(phase, None)

    assert decision["decision"] == "verify_with_failed_tasks"
    assert decision["next_executor"] == "phase_end_verify"
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
    state = _state_after_setup()

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


def test_run_coordinator_rebuilds_setup_context_and_hydrates_plan_on_resume(
    tmp_path,
) -> None:
    from werkstatt.loop import _run_coordinator_action

    state = RunState(aufgabe="Goal")
    assert _run_coordinator_action(None, state)["coordinator_action"] == (
        "explore_setup"
    )

    phase = PhaseState("demo", base_dir=tmp_path)
    phase.init_new("Goal", [], tests=[], akzeptanzkriterien=[])
    phase.data["setup_complete"] = True
    phase.save()
    resumed_phase = PhaseState("demo", base_dir=tmp_path)
    assert resumed_phase.load()
    # A new process must rebuild its transient Explorer context even though
    # the old process had completed setup.
    assert _run_coordinator_action(resumed_phase, state)["coordinator_action"] == (
        "explore_setup"
    )
    state.coordinator_setup_context_ready = True
    assert _run_coordinator_action(resumed_phase, state)["coordinator_action"] == (
        "plan_preflight"
    )

    resumed_phase.data["plan_complete"] = True
    resumed_phase.save()
    final_phase = PhaseState("demo", base_dir=tmp_path)
    assert final_phase.load()
    decision = _run_coordinator_action(final_phase, state)
    assert decision["coordinator_action"] == "finalize_run"

    planned_phase = _phase(
        tmp_path / "planned",
        [{"id": "task-1", "action": "read", "criterion_refs": ["AC1"]}],
        ["Inspect implementation"],
    )
    planned_phase.data["plan_complete"] = True
    planned_phase.save()
    resumed_state = _state_after_setup()
    selected = _run_coordinator_action(planned_phase, resumed_state)
    assert selected["coordinator_action"] == "execute_task_checkpoint"
    assert selected["next_task_id"] == "task-1"
    assert resumed_state.tasks[0]["id"] == "task-1"


def test_run_coordinator_decision_is_cas_persisted_for_chat_status(tmp_path):
    from werkstatt.event_store import EventStore
    from werkstatt.loop import _persist_run_coordinator_decision

    store = EventStore(tmp_path / "events.db")
    store.create_run_record("demo", "demo-run-1", "Complete goal")
    decision = {
        "decision": "execute_planned_task",
        "coordinator_action": "execute_task_checkpoint",
        "reason": "Builder needed for the next dependency-free task.",
        "next_executor": "builder",
        "next_task_id": "task-1",
        "task_progress": {
            "total": 3, "pending": 1, "running": 0,
            "done": 1, "failed": 1, "blocked": 0,
        },
        "criteria_task_coverage": {
            "tracked": True, "valid": True,
            "covered": ["AC1"], "uncovered": [f"AC{n}" for n in range(2, 27)],
            "error": "invalid_criterion_refs:SECRET prompt text",
        },
    }

    _persist_run_coordinator_decision(
        store, "demo", "demo-run-1", decision,
    )

    record = store.get_run_record("demo", "demo-run-1")
    assert record is not None
    assert record["checkpoint"]["coordinator_decision"] == {
        "decision": "execute_planned_task",
        "action": "execute_task_checkpoint",
        "reason": "Builder needed for the next dependency-free task.",
        "executor": "builder",
        "task_id": "task-1",
        "checkpoint_version": 1,
        "evidence": {
            "task_progress": {
                "total": 3, "pending": 1, "running": 0,
                "done": 1, "failed": 1, "blocked": 0,
            },
            "criteria_task_coverage": {
                "tracked": True, "valid": True,
                "covered_count": 1, "covered": ["AC1"],
                "covered_omitted_count": 0,
                "uncovered_count": 25,
                "uncovered": [f"AC{n}" for n in range(2, 22)],
                "uncovered_omitted_count": 5,
                "error": "invalid_criterion_refs",
            },
        },
    }


def test_new_direct_loop_rotates_terminal_process_global_run_id(tmp_path):
    from werkstatt.audit import get_run_id, set_run_id
    from werkstatt.event_store import EventStore
    from werkstatt.loop import _select_loop_run_id

    store = EventStore(tmp_path / "events.db")
    store.create_run_record(
        "demo", "demo-terminal", "Old goal", status="completed",
    )
    state = RunState(project_name="demo")
    set_run_id("demo-terminal")
    try:
        selected = _select_loop_run_id("demo", state, None, store)
        assert selected != "demo-terminal"
        assert selected.startswith("demo-")
        assert get_run_id() == selected
    finally:
        set_run_id("")


def test_run_coordinator_rejects_unknown_task_action(tmp_path) -> None:
    from werkstatt.loop import _run_coordinator_action

    phase = _phase(
        tmp_path,
        [{"id": "t1", "action": "shell", "criterion_refs": ["AC1"]}],
        ["Feature works"],
    )

    decision = _run_coordinator_action(
        phase, _state_after_setup(str(phase.data["aufgabe"])),
    )

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
    phase.data["setup_complete"] = True
    phase.data["plan_complete"] = True
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

    decision = _run_coordinator_action(
        phase, _state_after_setup(str(phase.data["aufgabe"])),
    )

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
    phase.data["setup_complete"] = True
    phase.data["plan_complete"] = True
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

    decision = _run_coordinator_action(
        phase, _state_after_setup(str(phase.data["aufgabe"])),
    )

    assert decision["coordinator_action"] == "resolve_task_graph"
    assert decision["stale_tasks_queued"] == []
    assert phase.get_task("t1").get("verification_pending") is not True


def test_run_coordinator_dispatches_unassigned_criteria_replan(tmp_path) -> None:
    from werkstatt.loop import _run_coordinator_action

    phase = _phase(
        tmp_path,
        [{"id": "t1", "action": "read", "criterion_refs": ["AC1"]}],
        ["First criterion", "Second criterion"],
    )
    phase.mark_done("t1")

    decision = _run_coordinator_action(
        phase, _state_after_setup(str(phase.data["aufgabe"])),
    )

    assert decision["decision"] == "replan_unassigned_criteria"
    assert decision["coordinator_action"] == "replan_unassigned_criteria"
    assert decision["next_executor"] == "planner_and_plan_gate"


def test_run_coordinator_dispatches_failed_criteria_replan(tmp_path) -> None:
    from werkstatt.loop import _run_coordinator_action

    phase = _phase(
        tmp_path,
        [{"id": "failed", "action": "update", "criterion_refs": ["AC1"]}],
        ["Existing criterion"],
    )
    phase.mark_failed("failed", failure="builder_failed")

    decision = _run_coordinator_action(
        phase, _state_after_setup(str(phase.data["aufgabe"])),
    )

    assert decision["decision"] == "replan_failed_criteria"
    assert decision["coordinator_action"] == "replan_failed_criteria"
    assert decision["next_executor"] == "planner_and_plan_gate"


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

    decision = _run_coordinator_action(
        phase, _state_after_setup(str(phase.data["aufgabe"])),
    )

    assert decision["task_progress"]["pending"] == 0
    assert decision["task_progress"]["blocked"] == 1
    assert decision["decision"] == "reject_blocked_graph"
    assert decision["coordinator_action"] == "reject_checkpoint"
    assert decision["goal_candidate_before_final_verify"] is False


def test_task_loop_dispatches_criteria_replan_at_checkpoint(
    tmp_path, monkeypatch,
) -> None:
    phase = _phase(
        tmp_path,
        [{"id": "t1", "action": "read", "criterion_refs": ["AC1"]}],
        ["First criterion", "Second criterion"],
    )
    phase.mark_done("t1")
    state = RunState(
        project_dir=tmp_path,
        project_name="demo",
        aufgabe="Goal",
        tasks=list(phase.data["tasks"]),
        akzeptanzkriterien=list(phase.data["akzeptanzkriterien"]),
    )
    calls = []
    monkeypatch.setattr("werkstatt.audit.get_run_id", lambda: "")
    monkeypatch.setattr(task_phase, "audit", lambda *_a, **_kw: True)
    monkeypatch.setattr(
        "werkstatt.criteria_replan.replan_unassigned_criteria",
        lambda _state, _phase: calls.append("replan") or False,
    )

    result = task_phase._phase_tasks_loop(state, phase, max_task_steps=1)

    assert result[0] == 1
    assert calls == ["replan"]


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
