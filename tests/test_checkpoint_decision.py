from __future__ import annotations

import hashlib
from types import SimpleNamespace

from werkstatt import run_followups
from werkstatt.phase_state import PhaseState
from werkstatt.phases import tasks as task_phase
from werkstatt.phases.tasks import _checkpoint_decision_payload
from werkstatt.state import RunState


def _phase(tmp_path, tasks, criteria):
    has_read_tasks = any(
        isinstance(task, dict) and task.get("action") == "read"
        for task in tasks
    )
    base_dir = tmp_path / ".werkstatt" if has_read_tasks else tmp_path
    phase = PhaseState("demo", base_dir=base_dir)
    phase.init_new("Ziel", tasks, akzeptanzkriterien=criteria)
    phase.data["setup_complete"] = True
    phase.data["plan_complete"] = True
    if has_read_tasks:
        phase.run_id = "fixture-read-run"
        for task in phase.data["tasks"]:
            if task.get("action") != "read":
                continue
            task_files = task.get("task_files")
            if not task_files:
                task_files = [f"read_scope/{task['id']}.txt"]
                task["task_files"] = task_files
            file_evidence = []
            for relative in task_files:
                target = tmp_path / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    target.write_text("fixture source\n", encoding="utf-8")
                content = target.read_bytes()
                file_evidence.append({
                    "file": relative,
                    "sha256": hashlib.sha256(content).hexdigest(),
                    "bytes": len(content),
                    "lines": content.count(b"\n"),
                })
            assert phase.record_task_read_evidence(task["id"], file_evidence)
        phase.save()
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
    assert decision["next_executor"] == "verify_only"
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


def test_outer_coordinator_routes_allowlisted_task_failure_at_checkpoint(
    tmp_path,
) -> None:
    from werkstatt.loop import _recoverable_task_error_decision

    phase = _phase(
        tmp_path,
        [
            {"id": "failed", "name": "First", "criterion_refs": ["AC1"]},
            {"id": "next", "name": "Independent", "criterion_refs": ["AC2"]},
        ],
        ["First", "Second"],
    )
    phase.mark_failed("failed", failure="builder_failed")

    decision = _recoverable_task_error_decision(
        phase, _state_after_setup(), progress_changed=True,
    )

    assert decision is not None
    assert decision["coordinator_action"] == "execute_task_checkpoint"
    assert decision["next_task_id"] == "next"


def test_outer_coordinator_keeps_unknown_or_stale_task_failures_terminal(
    tmp_path,
) -> None:
    from werkstatt.loop import _recoverable_task_error_decision

    phase = _phase(
        tmp_path,
        [{"id": "failed", "name": "First", "criterion_refs": ["AC1"]}],
        ["First"],
    )
    phase.mark_failed("failed", failure="reflection_erschoepft_rejected")

    assert _recoverable_task_error_decision(
        phase, _state_after_setup(), progress_changed=True,
    ) is None
    phase.data["tasks"][0]["failure"] = "builder_failed"
    assert _recoverable_task_error_decision(
        phase, _state_after_setup(), progress_changed=False,
    ) is None


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


def test_checkpoint_replans_safe_failed_and_unassigned_criteria_together(
    tmp_path,
) -> None:
    phase = _phase(
        tmp_path,
        [
            {"id": "done", "criterion_refs": ["AC1"]},
            {"id": "failed", "criterion_refs": ["AC2"]},
        ],
        ["First", "Second", "Third"],
    )
    phase.mark_done("done")
    phase.mark_failed("failed", failure="builder_failed")

    decision = _checkpoint_decision_payload(phase, None)

    assert decision["decision"] == "replan_failed_criteria"
    assert decision["next_executor"] == "planner_and_plan_gate"
    assert decision["criteria_task_coverage"]["error"] == "criteria_not_assigned"
    assert decision["criteria_task_coverage"]["uncovered"] == ["AC2", "AC3"]


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
    from werkstatt.phase_state import PhaseState

    project = tmp_path
    (project / ".werkstatt").mkdir()
    (project / "src").mkdir()
    (project / "src" / "feature.py").write_text("value = 1\n", encoding="utf-8")
    phase = PhaseState("demo", base_dir=project / ".werkstatt")
    phase.init_new(
        "Feature works",
        [{
            "id": "t1", "name": "Implement", "criterion_refs": ["AC1"],
            "task_files": ["src/feature.py"],
        }],
        akzeptanzkriterien=["Feature works"],
    )
    phase.run_id = "demo-run-1"
    phase.save()
    assert phase.record_task_verify_evidence(
        "t1",
        [{
            "stage_id": "pytest_changed", "ok": True, "exit_code": 0,
            "scope_files": ["src/feature.py"],
        }],
        phase="post_build",
    )
    phase.mark_done("t1")

    decision = _checkpoint_decision_payload(phase, None)

    assert decision["decision"] == "run_phase_end_verify"
    assert decision["goal_candidate_before_final_verify"] is True
    assert decision["criteria_task_verification"]["current_count"] == 1
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
    assert final["decision"] == "reject_criteria_verify_scope_missing"
    assert final["coordinator_action"] == "reject_checkpoint"
    assert final["goal_candidate_before_final_verify"] is False
    assert final["next_executor"] is None


def test_coordinator_audit_payload_includes_task_verify_evidence() -> None:
    from werkstatt.loop import _coordinator_decision_audit_payload

    verification = {
        "required_task_count": 2,
        "current_count": 1,
        "reverify_possible_count": 0,
        "unverifiable_count": 1,
        "current": ["task-1"],
        "current_omitted_count": 0,
        "reverify_possible": [],
        "reverify_possible_omitted_count": 0,
        "unverifiable": ["task-2"],
        "unverifiable_omitted_count": 0,
    }

    payload = _coordinator_decision_audit_payload(
        "demo-run-1",
        {
            "decision": "reject_criteria_verify_scope_missing",
            "coordinator_action": "reject_checkpoint",
            "preserve_failed_tasks_on_setup": True,
            "criteria_task_verification": verification,
            "decision_basis": {
                "setup_context_ready": False,
                "plan_goal_matches": True,
                "task_count": 2,
                "private_prompt": "must not be copied",
            },
            "private_prompt": "must not be copied",
        },
    )

    assert payload["run_id"] == "demo-run-1"
    assert payload["criteria_task_verification"] == verification
    assert payload["preserve_failed_tasks_on_setup"] is True
    assert payload["decision_basis"] == {
        "setup_context_ready": False,
        "plan_goal_matches": True,
        "task_count": 2,
    }
    assert "private_prompt" not in payload


def test_run_coordinator_rebuilds_setup_context_and_hydrates_plan_on_resume(
    tmp_path,
) -> None:
    from werkstatt.loop import _run_coordinator_action

    state = RunState(aufgabe="Goal")
    missing_setup = _run_coordinator_action(None, state)
    assert missing_setup["coordinator_action"] == "explore_setup"
    assert missing_setup["decision_basis"] == {
        "setup_context_ready": False,
        "setup_checkpoint_complete": False,
        "plan_checkpoint_complete": False,
        "plan_goal_matches": False,
        "task_count": 0,
    }

    phase = PhaseState("demo", base_dir=tmp_path)
    phase.init_new("Goal", [], tests=[], akzeptanzkriterien=[])
    phase.data["setup_complete"] = True
    phase.run_id = "run-1"
    state.run_id = "run-1"
    phase.save()
    resumed_phase = PhaseState("demo", base_dir=tmp_path)
    assert resumed_phase.load()
    # A new process must rebuild its transient Explorer context even though
    # the old process had completed setup.
    resumed_setup = _run_coordinator_action(resumed_phase, state)
    assert resumed_setup["coordinator_action"] == "explore_setup"
    assert resumed_setup["decision_basis"]["setup_checkpoint_complete"] is True
    assert resumed_setup["decision_basis"]["plan_checkpoint_complete"] is False
    state.coordinator_setup_context_ready = True
    assert _run_coordinator_action(resumed_phase, state)["coordinator_action"] == (
        "planner_scout"
    )

    resumed_phase.data["planner_role_stage"] = "scout"
    resumed_phase.data["planner_role_goal_sha256"] = hashlib.sha256(
        b"Goal",
    ).hexdigest()
    assert _run_coordinator_action(resumed_phase, state)["coordinator_action"] == (
        "planner_architect"
    )
    resumed_phase.data["planner_role_stage"] = "architect"
    assert _run_coordinator_action(resumed_phase, state)["coordinator_action"] == (
        "planner_split"
    )
    # Role-stage progress is run and goal scoped; a stale stage cannot skip
    # the Scout on another run or a changed goal.
    state.run_id = "other-run"
    assert _run_coordinator_action(resumed_phase, state)["coordinator_action"] == (
        "planner_scout"
    )
    state.run_id = "run-1"
    state.aufgabe = "Other goal"
    assert _run_coordinator_action(resumed_phase, state)["coordinator_action"] == (
        "planner_scout"
    )

    state.aufgabe = "Goal"
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


def test_planner_role_stage_persists_for_same_run_and_goal(tmp_path) -> None:
    import pytest

    from werkstatt.loop import (
        _persist_planner_role_stage,
        _run_coordinator_action,
    )

    phase = PhaseState("demo", base_dir=tmp_path)
    phase.data = {"project": "demo", "aufgabe": "Goal", "tasks": []}
    _persist_planner_role_stage(
        phase, "scout", run_id="run-1", goal="Goal",
    )

    resumed = PhaseState("demo", base_dir=tmp_path)
    assert resumed.load()
    state = RunState(aufgabe="Goal", run_id="run-1")
    state.coordinator_setup_context_ready = True
    decision = _run_coordinator_action(resumed, state)
    assert decision["coordinator_action"] == "planner_architect"
    assert decision["decision_basis"]["planner_role_stage"] == "scout"

    with pytest.raises(ValueError, match="Rollenstage"):
        _persist_planner_role_stage(
            resumed, "builder", run_id="run-1", goal="Goal",
        )


def test_coordinator_dispatches_only_roles_needed_by_current_planner_route(
    tmp_path,
) -> None:
    from werkstatt.loop import _run_coordinator_action

    broad_goal = "Analysiere src/feature.py und erklaere die Ursache des Fehlers"
    phase = PhaseState("demo", base_dir=tmp_path / "phase")
    phase.init_new(broad_goal, [], tests=[], akzeptanzkriterien=[])
    phase.data["setup_complete"] = True
    phase.run_id = "run-1"
    phase.save()
    state = RunState(
        aufgabe=broad_goal, project_name="demo", project_dir=tmp_path,
        run_id="run-1",
    )
    state.explorer_context = _deterministic_explorer_context(tmp_path)
    state.coordinator_setup_context_ready = True

    broad_decision = _run_coordinator_action(phase, state)
    assert broad_decision["coordinator_action"] == "planner_scout"
    assert broad_decision["decision_basis"]["scout_route_reason"].startswith(
        "auftrag_enthaelt_breiten_marker:"
    )

    focused_goal = "Ergaenze src/feature.py um eine neue Funktion"
    phase.data["aufgabe"] = focused_goal
    phase.save()
    state.aufgabe = focused_goal
    focused_decision = _run_coordinator_action(phase, state)
    assert focused_decision["coordinator_action"] == "planner_architect"
    assert focused_decision["decision_basis"]["scout_route_reason"] == (
        "explizite_einzeldatei_mit_explorer_beleg"
    )
    assert focused_decision["reason"] == (
        "scout_skipped:explizite_einzeldatei_mit_explorer_beleg"
    )


def _deterministic_explorer_context(tmp_path):
    source = tmp_path / "src" / "feature.py"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("def feature():\n    return 1\n", encoding="utf-8")
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    return {
        "findings": (
            "Explizites Einzeldatei-Ziel ist durch den deterministischen "
            "Planner-Router bestaetigt; kein Explorer-LLM-Aufruf."
        ),
        "key_files": [{
            "file": "src/feature.py",
            "why": "explizit in Aufgabe",
            "confidence": "high",
            "preview": "def feature():\n    return 1\n",
            "source_sha256": source_hash,
            "source_complete": True,
        }],
        "next_reads": [],
        "content_retrieval": {},
        "dispatch": {
            "role": "explorer",
            "selected": "skip",
            "reason": "explizite_einzeldatei_mit_explorer_beleg",
            "evidence_kind": "deterministic",
        },
        "related_files_scan": {"status": "complete"},
    }


def test_resume_reuses_only_fresh_deterministic_explorer_checkpoint(
    tmp_path,
) -> None:
    from werkstatt.loop import (
        _deterministic_setup_context_checkpoint,
        _run_coordinator_action,
    )

    phase = PhaseState("demo", base_dir=tmp_path / ".werkstatt")
    phase.data = {"setup_complete": True}
    phase.run_id = "demo-run-1"
    original_state = RunState(
        aufgabe="Update src/feature.py",
        project_dir=tmp_path,
        project_name="demo",
        run_id="demo-run-1",
        explorer_context=_deterministic_explorer_context(tmp_path),
    )
    checkpoint = _deterministic_setup_context_checkpoint(original_state)
    assert checkpoint is not None
    phase.data["setup_context_checkpoint"] = checkpoint
    phase.save()

    resumed_phase = PhaseState("demo", base_dir=tmp_path / ".werkstatt")
    assert resumed_phase.load()
    resumed_state = RunState(
        aufgabe="Update src/feature.py",
        project_dir=tmp_path,
        project_name="demo",
        run_id="demo-run-1",
    )
    decision = _run_coordinator_action(resumed_phase, resumed_state)

    assert decision["coordinator_action"] == "planner_architect"
    assert resumed_state.coordinator_setup_context_ready is True
    assert resumed_state.explorer_context == checkpoint["context"]
    assert decision["decision_basis"]["scout_route_reason"] == (
        "explizite_einzeldatei_mit_explorer_beleg"
    )


def test_resume_rejects_stale_deterministic_explorer_source(tmp_path) -> None:
    from werkstatt.loop import (
        _deterministic_setup_context_checkpoint,
        _run_coordinator_action,
    )

    phase = PhaseState("demo", base_dir=tmp_path / ".werkstatt")
    phase.data = {"setup_complete": True}
    phase.run_id = "demo-run-1"
    original_state = RunState(
        aufgabe="Update src/feature.py",
        project_dir=tmp_path,
        project_name="demo",
        run_id="demo-run-1",
        explorer_context=_deterministic_explorer_context(tmp_path),
    )
    checkpoint = _deterministic_setup_context_checkpoint(original_state)
    assert checkpoint is not None
    phase.data["setup_context_checkpoint"] = checkpoint
    phase.save()
    (tmp_path / "src" / "feature.py").write_text(
        "def feature():\n    return 2\n", encoding="utf-8",
    )

    resumed_phase = PhaseState("demo", base_dir=tmp_path / ".werkstatt")
    assert resumed_phase.load()
    resumed_state = RunState(
        aufgabe="Update src/feature.py",
        project_dir=tmp_path,
        project_name="demo",
        run_id="demo-run-1",
    )
    decision = _run_coordinator_action(resumed_phase, resumed_state)

    assert decision["coordinator_action"] == "explore_setup"
    assert resumed_state.coordinator_setup_context_ready is False


def test_resume_rejects_deterministic_context_from_another_run_or_goal(
    tmp_path,
) -> None:
    from werkstatt.loop import (
        _deterministic_setup_context_checkpoint,
        _run_coordinator_action,
    )

    phase = PhaseState("demo", base_dir=tmp_path / ".werkstatt")
    phase.data = {"setup_complete": True}
    phase.run_id = "demo-run-1"
    original_state = RunState(
        aufgabe="Update src/feature.py",
        project_dir=tmp_path,
        project_name="demo",
        run_id="demo-run-1",
        explorer_context=_deterministic_explorer_context(tmp_path),
    )
    checkpoint = _deterministic_setup_context_checkpoint(original_state)
    assert checkpoint is not None
    phase.data["setup_context_checkpoint"] = checkpoint
    phase.save()

    for run_id, goal in (
        ("demo-run-2", "Update src/feature.py"),
        ("demo-run-1", "Update another target"),
    ):
        resumed_phase = PhaseState("demo", base_dir=tmp_path / ".werkstatt")
        assert resumed_phase.load()
        resumed_state = RunState(
            aufgabe=goal,
            project_dir=tmp_path,
            project_name="demo",
            run_id=run_id,
        )
        decision = _run_coordinator_action(resumed_phase, resumed_state)

        assert decision["coordinator_action"] == "explore_setup"
        assert resumed_state.coordinator_setup_context_ready is False


def test_non_deterministic_explorer_output_is_not_checkpointed(tmp_path) -> None:
    from werkstatt.loop import _deterministic_setup_context_checkpoint

    state = RunState(
        aufgabe="Diagnose src/feature.py",
        project_dir=tmp_path,
        project_name="demo",
        run_id="demo-run-1",
        explorer_context={
            **_deterministic_explorer_context(tmp_path),
            "dispatch": {
                "role": "explorer",
                "selected": "invoke",
                "reason": "diagnose",
                "evidence_kind": "model_or_tool",
            },
        },
    )

    assert _deterministic_setup_context_checkpoint(
        state,
    ) is None


def test_run_coordinator_resumes_approved_task_without_repeating_explorer(
    tmp_path,
) -> None:
    from werkstatt.loop import _run_coordinator_action

    phase = _phase(
        tmp_path,
        [{
            "id": "task-1",
            "name": "Update implementation",
            "description": "Apply the approved file scoped implementation plan.",
            "action": "update",
            "task_files": ["src/feature.py"],
            "criterion_refs": ["AC1"],
        }],
        ["Feature works"],
    )
    state = RunState(aufgabe="Ziel")

    decision = _run_coordinator_action(phase, state)

    assert decision["coordinator_action"] == "execute_task_checkpoint"
    assert decision["next_task_id"] == "task-1"
    assert state.coordinator_setup_context_ready is False
    assert state.tasks[0]["description"] == (
        "Apply the approved file scoped implementation plan."
    )
    assert decision["decision_basis"]["setup_context_source"] == (
        "checkpointed_plan"
    )


def test_run_coordinator_rebuilds_context_when_checkpoint_requires_replanning(
    tmp_path,
) -> None:
    from werkstatt.loop import _run_coordinator_action

    phase = _phase(
        tmp_path,
        [{
            "id": "task-1",
            "name": "First criterion",
            "description": "Inspect and update the first requirement.",
            "action": "read",
            "criterion_refs": ["AC1"],
        }],
        ["First criterion", "Second criterion"],
    )
    phase.mark_done("task-1")
    state = RunState(aufgabe="Ziel")

    decision = _run_coordinator_action(phase, state)

    assert decision["coordinator_action"] == "explore_setup"
    assert decision["decision_basis"]["setup_context_ready"] is False


def test_recovery_replan_resume_preserves_failed_task_through_explorer_setup(
    tmp_path,
) -> None:
    from werkstatt.loop import _run_coordinator_action

    phase = _phase(
        tmp_path,
        [{
            "id": "failed-task",
            "name": "Implement criterion",
            "criterion_refs": ["AC1"],
            "task_files": ["src/feature.py"],
        }],
        ["Feature works"],
    )
    phase.mark_failed("failed-task", failure="builder_failed")
    state = RunState(aufgabe="Ziel")

    decision = _run_coordinator_action(phase, state)

    assert decision["decision"] == "prepare_project_context"
    assert decision["coordinator_action"] == "explore_setup"
    assert decision["preserve_failed_tasks_on_setup"] is True

    assert phase.resume_failed(
        preserve_failed=decision["preserve_failed_tasks_on_setup"],
    ) == 0
    assert phase.get_task("failed-task")["status"] == "failed"


def test_run_coordinator_decision_is_cas_persisted_for_chat_status(tmp_path):
    from werkstatt.event_store import EventStore
    from werkstatt.loop import _persist_run_coordinator_decision

    store = EventStore(tmp_path / "events.db")
    store.create_run_record("demo", "demo-run-1", "Complete goal")
    decision = {
        "decision": "execute_planned_task",
        "coordinator_action": "execute_task_checkpoint",
        "preserve_failed_tasks_on_setup": True,
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
        "criteria_task_verification": {
            "required_task_count": 23,
            "current_count": 1, "reverify_possible_count": 1,
            "unverifiable_count": 1,
            "current": ["task-1"], "reverify_possible": ["task-2"],
            "unverifiable": ["task-3"],
            "current_omitted_count": 0,
            "reverify_possible_omitted_count": 0,
            "unverifiable_omitted_count": 0,
        },
        "decision_basis": {
            "setup_context_ready": True,
            "setup_checkpoint_complete": True,
            "plan_checkpoint_complete": True,
            "plan_goal_matches": True,
            "setup_context_source": "checkpointed_plan",
            "task_count": 3,
            "private_prompt": "do not persist",
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
        "preserve_failed_tasks_on_setup": True,
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
            "criteria_task_verification": {
                "required_task_count": 23,
                "current_count": 1,
                "reverify_possible_count": 1,
                "unverifiable_count": 1,
                "current": ["task-1"], "current_omitted_count": 0,
                "reverify_possible": ["task-2"],
                "reverify_possible_omitted_count": 0,
                "unverifiable": ["task-3"],
                "unverifiable_omitted_count": 0,
            },
            "decision_basis": {
                "setup_context_ready": True,
                "setup_checkpoint_complete": True,
                "plan_checkpoint_complete": True,
                "plan_goal_matches": True,
                "setup_context_source": "checkpointed_plan",
                "task_count": 3,
            },
        },
    }


def test_planner_role_checkpoint_is_cas_persisted_without_prompt_text(
    monkeypatch, tmp_path,
):
    import json

    from werkstatt.event_store import EventStore
    from werkstatt.loop import _persist_run_planner_role_checkpoint

    store = EventStore(tmp_path / "events.db")
    store.create_run_record("demo", "demo-run-role", "Complete goal")
    monkeypatch.setattr("werkstatt.loop.EventStore", lambda: store)
    monkeypatch.setattr("werkstatt.loop.audit", lambda *_args, **_kwargs: None)
    state = RunState(project_name="demo", project_dir=tmp_path)
    _persist_run_planner_role_checkpoint(
        "demo", "demo-run-role", {
            "role": "architect", "status": "completed",
            "reason": "architect_prose_received",
            "input_sha256": "a" * 64,
            "output_sha256": "b" * 64,
            "prompt": "SECRET prompt must not persist",
        },
        run_state=state,
    )

    record = store.get_run_record("demo", "demo-run-role")
    assert record is not None
    checkpoint = record["checkpoint"]
    role_checkpoint = checkpoint["planner_role_checkpoint"]
    assert role_checkpoint["role"] == "architect"
    assert role_checkpoint["status"] == "completed"
    assert role_checkpoint["input_sha256"] == "a" * 64
    assert role_checkpoint["output_sha256"] == "b" * 64
    assert checkpoint["planner_role_history"] == [role_checkpoint]
    assert "SECRET prompt" not in json.dumps(checkpoint)


def test_planner_role_checkpoint_rejects_unknown_role():
    import pytest

    from werkstatt.loop import _persist_run_planner_role_checkpoint

    with pytest.raises(ValueError, match="Unbekannte Planner-Rolle"):
        _persist_run_planner_role_checkpoint(
            "demo", "demo-run", {"role": "shell", "status": "running"},
            run_state=RunState(),
        )


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
    assert decision["next_executor"] == "verify_only"
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


def test_read_task_is_redispatched_when_source_hash_changes(tmp_path) -> None:
    phase = _phase(
        tmp_path,
        [{"id": "read", "action": "read"}],
        [],
    )
    phase.mark_done("read")
    source = tmp_path / "read_scope" / "read.txt"
    source.write_text("changed source\n", encoding="utf-8")

    assert phase.queue_stale_task_reverification() == ["read"]
    queued = phase.get_next_task()
    assert queued is not None
    assert queued["id"] == "read"
    assert queued["action"] == "read"
    assert queued["read_reverification"] is True


def test_changed_read_dependency_precedes_pending_builder(tmp_path) -> None:
    from werkstatt.loop import _run_coordinator_action

    phase = _phase(
        tmp_path,
        [
            {"id": "read", "action": "read"},
            {
                "id": "build", "action": "update", "dependencies": ["read"],
                "task_files": ["src/feature.py"],
            },
        ],
        [],
    )
    phase.mark_done("read")
    (tmp_path / "read_scope" / "read.txt").write_text(
        "changed source\n", encoding="utf-8",
    )

    decision = _run_coordinator_action(
        phase, _state_after_setup(str(phase.data["aufgabe"])),
    )

    assert decision["next_task_id"] == "read"
    assert decision["next_executor"] == "read_only_task"
    assert decision["stale_tasks_queued"] == ["read"]


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
    assert event[1]["decision"] == "reject_criteria_verify_scope_missing"
    assert event[1]["criteria_task_verification"]["unverifiable_count"] == 1
    assert event[1]["goal_candidate_before_final_verify"] is False
