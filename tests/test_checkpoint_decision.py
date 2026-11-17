from __future__ import annotations

import hashlib
from types import SimpleNamespace

import pytest

from tests.factories import coordinator_decision_for_task
from werkstatt import run_followups
from werkstatt.checkpoint_coordinator import (
    choose_task_checkpoint_action as _checkpoint_decision_payload,
)
from werkstatt.phase_state import PhaseState
from werkstatt.roles import task_dispatch as task_phase
from werkstatt.state import RunState

_SMALL_UPDATE_DIFF = (
    "diff --git a/src/feature.py b/src/feature.py\n"
    "--- a/src/feature.py\n+++ b/src/feature.py\n"
    "@@ -1 +1 @@\n-value = 1\n+value = 2\n"
)


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
    if phase.data.get("tasks"):
        phase.bind_approved_plan()
    phase.save()
    return phase


def _state_after_setup(goal: str = "Ziel") -> RunState:
    state = RunState(aufgabe=goal)
    state.coordinator_setup_context_ready = True
    return state


def _record_preflight(phase: PhaseState, state: RunState) -> None:
    """Seed a current evidence checkpoint when a test targets later routing."""
    assert state.run_id
    phase.record_preflight_checkpoint(
        goal=state.aufgabe, run_id=state.run_id, findings=[],
    )


def test_coordinator_selects_followup_reconciliation_at_checkpoint(
    tmp_path, monkeypatch,
) -> None:
    from werkstatt import loop

    phase = SimpleNamespace(
        run_id="run-followup",
        data={
            "tasks": [{"id": "task-1", "status": "pending"}],
            "setup_complete": True,
            "plan_complete": True,
            "aufgabe": "Original goal",
        },
    )
    run_record = {
        "checkpoint": {
            "chat_followup_requests": [{
                "proposal_id": "proposal-2",
                "seq": 19,
                "status": "received",
                "request": "Inspect one more edge case",
            }],
        },
    }
    monkeypatch.setattr(loop, "get_run_id", lambda: "run-followup")
    monkeypatch.setattr(
        loop, "EventStore",
        lambda: SimpleNamespace(
            get_run_record=lambda project, run_id: (
                run_record if (project, run_id) == ("demo", "run-followup")
                else None
            ),
        ),
    )
    state = RunState(
        aufgabe="Original goal",
        project_dir=tmp_path,
        project_name="demo",
        run_id="run-followup",
    )

    decision = loop._run_coordinator_action(phase, state)

    assert decision["coordinator_action"] == "reconcile_chat_followup"
    assert decision["decision_basis"]["proposal_id"] == "proposal-2"
    assert decision["decision_basis"]["message_seq"] == 19
    assert decision["decision_basis"]["current_task_graph_count"] == 1
    assert decision["decision_basis"]["main_goal_preserved"] is True


def test_narrow_direct_builder_can_skip_setup_and_checkpoint_its_source(
    tmp_path,
) -> None:
    from werkstatt.loop import (
        _deterministic_setup_context_checkpoint,
        _run_coordinator_action,
    )

    source = tmp_path / "src" / "feature.py"
    source.parent.mkdir(exist_ok=True)
    source.write_text("def feature():\n    return 1\n", encoding="utf-8")
    goal = "Korrigiere den Rueckgabewert von feature in src/feature.py"
    phase = PhaseState("demo", base_dir=tmp_path / ".werkstatt")
    phase.run_id = "direct-run-1"
    state = RunState(
        aufgabe=goal,
        project_dir=tmp_path,
        project_name="demo",
        run_id="direct-run-1",
    )

    decision = _run_coordinator_action(phase, state)

    assert decision["coordinator_action"] == "planner_direct"
    assert decision["decision_basis"]["preflight_checkpoint_current"] is False
    assert decision["decision_basis"]["preflight_policy"] == (
        "skip_low_risk_direct_builder"
    )
    assert state.preflight_checkpoint_skipped is True
    assert decision["decision_basis"]["setup_context_source"] == (
        "direct_current_source_tool"
    )
    assert state.explorer_context["dispatch"]["selected"] == "direct_builder"
    checkpoint = _deterministic_setup_context_checkpoint(state)
    assert checkpoint is not None
    phase.data["setup_context_checkpoint"] = checkpoint
    phase.save()

    resumed_phase = PhaseState("demo", base_dir=tmp_path / ".werkstatt")
    assert resumed_phase.load()
    resumed_state = RunState(
        aufgabe=goal,
        project_dir=tmp_path,
        project_name="demo",
        run_id="direct-run-1",
    )
    resumed = _run_coordinator_action(resumed_phase, resumed_state)

    assert resumed["coordinator_action"] == "planner_direct"
    assert resumed["decision_basis"]["preflight_policy"] == (
        "skip_low_risk_direct_builder"
    )
    assert resumed_state.preflight_checkpoint_skipped is True
    assert resumed_state.coordinator_setup_context_ready is True
    assert resumed_state.explorer_context == checkpoint["context"]


def test_current_approved_plan_resumes_without_legacy_setup_marker(
    tmp_path,
) -> None:
    from werkstatt.loop import _run_coordinator_action

    phase = _phase(
        tmp_path,
        [{
            "id": "task-1",
            "name": "Apply approved change",
            "description": "Use the approved task scope.",
            "action": "update",
            "task_files": ["src/feature.py"],
            "criterion_refs": ["AC1"],
        }],
        ["The approved behavior is implemented"],
    )
    phase.run_id = "resume-without-setup"
    phase.data["run_id"] = phase.run_id
    phase.data.pop("setup_complete")
    phase.bind_approved_plan()
    phase.save()
    state = RunState(
        aufgabe="Ziel", project_name="demo", project_dir=tmp_path,
        run_id=phase.run_id,
    )

    decision = _run_coordinator_action(phase, state)

    assert decision["coordinator_action"] == "execute_task_checkpoint"
    assert decision["decision_basis"]["setup_checkpoint_complete"] is False
    assert decision["decision_basis"]["plan_checkpoint_complete"] is True
    assert decision["decision_basis"]["plan_fingerprint_matches"] is True
    assert decision["decision_basis"]["setup_context_source"] == (
        "checkpointed_plan"
    )
    assert state.coordinator_setup_context_ready is False


@pytest.mark.parametrize(
    ("diff", "expected_decision", "expected_executor"),
    [
        (
            _SMALL_UPDATE_DIFF,
            "complete_task_checkpoint",
            "task_completion",
        ),
        (
            _SMALL_UPDATE_DIFF,
            "review_task_checkpoint",
            "reviewer",
        ),
    ],
)
def test_review_checkpoint_routes_from_current_diff_and_verify_warnings(
    tmp_path, monkeypatch, diff, expected_decision, expected_executor,
):
    from werkstatt import reviewer

    task = {
        "id": "task-1", "name": "Update feature value",
        "description": "Change the feature value.", "action": "update",
        "task_files": ["src/feature.py"], "criterion_refs": ["AC1"],
    }
    phase = PhaseState("demo", base_dir=tmp_path / ".werkstatt")
    phase.init_new(
        "Ziel", [task],
        akzeptanzkriterien=["The feature returns the new value"],
    )
    phase.run_id = "review-dispatch-run"
    phase.bind_approved_plan()
    source = tmp_path / "src" / "feature.py"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("value = 2\n", encoding="utf-8")
    phase.mark_running("task-1")
    assert phase.record_task_verify_evidence(
        "task-1",
        [{
            "stage_id": "pytest", "ok": True, "exit_code": 0,
            "scope_files": ["src/feature.py"],
        }],
        phase="post_build",
    )
    warnings = ["ruff advisory"] if expected_decision == "review_task_checkpoint" else []
    assert phase.record_task_review_checkpoint(
        "task-1", verify_warnings=warnings,
    )
    monkeypatch.setattr(reviewer, "_get_git_diff", lambda **_kwargs: diff)

    decision = _checkpoint_decision_payload(
        phase,
        phase.get_task("task-1"),
        state=RunState(aufgabe="Ziel", project_dir=tmp_path),
    )

    assert decision["decision"] == expected_decision
    assert decision["next_executor"] == expected_executor
    assert decision["review_dispatch"]["invoke_reviewer"] is (
        expected_decision == "review_task_checkpoint"
    )
    assert len(decision["review_dispatch"]["evidence"]["diff_sha256"]) == 64


def test_checkpoint_dispatches_builder_handoff_to_verify_executor(tmp_path):
    source = tmp_path / "src" / "feature.py"
    source.parent.mkdir(parents=True)
    source.write_text("value = 2\n", encoding="utf-8")
    phase = PhaseState("demo", base_dir=tmp_path / ".werkstatt")
    phase.init_new(
        "Ziel",
        [{
            "id": "task-1", "name": "Update feature", "action": "update",
            "task_files": ["src/feature.py"], "criterion_refs": ["AC1"],
        }],
        akzeptanzkriterien=["feature updated"],
    )
    phase.run_id = "build-verify-run"
    phase.mark_running("task-1")
    assert phase.record_task_build_checkpoint("task-1")

    decision = _checkpoint_decision_payload(
        phase,
        phase.get_next_task(),
        state=RunState(aufgabe="Ziel", project_dir=tmp_path),
    )

    assert decision["decision"] == "verify_task_checkpoint"
    assert decision["next_executor"] == "verify_only"
    assert decision["verification_only"] is True


def test_coordinator_selects_bounded_recovery_for_current_verify_failure(tmp_path):
    source = tmp_path / "src" / "feature.py"
    source.parent.mkdir()
    source.write_text("value = 2\n", encoding="utf-8")
    phase = PhaseState("demo", base_dir=tmp_path / ".werkstatt")
    phase.init_new(
        "Update feature",
        [{
            "id": "task-1", "name": "Update feature", "action": "update",
            "task_files": ["src/feature.py"], "criterion_refs": ["AC1"],
        }],
        akzeptanzkriterien=["feature updated"],
    )
    phase.run_id = "verify-recovery-run"
    phase.mark_running("task-1")
    assert phase.record_task_build_checkpoint("task-1")
    assert phase.record_task_verify_failure_checkpoint(
        "task-1", ["ruff: E501 line too long"],
    )

    decision = _checkpoint_decision_payload(
        phase,
        phase.get_next_task(),
        state=RunState(aufgabe="Update feature", project_dir=tmp_path),
    )

    assert decision["decision"] == "recover_verify_failure_checkpoint"
    assert decision["next_executor"] == "verify_recovery"
    assert decision["next_task_id"] == "task-1"

    source.write_text("value = 3\n", encoding="utf-8")
    stale_decision = _checkpoint_decision_payload(
        phase,
        phase.get_next_task(),
        state=RunState(aufgabe="Update feature", project_dir=tmp_path),
    )
    assert stale_decision["decision"] == "reject_stale_verify_failure_checkpoint"
    assert stale_decision["next_executor"] is None


def test_coordinator_routes_pending_plan_candidate_to_human_gate(tmp_path) -> None:
    from werkstatt.loop import _run_coordinator_action

    goal = "Implementiere die belegten Anforderungen"
    phase = PhaseState("demo", base_dir=tmp_path)
    phase.run_id = "candidate-run"
    digest = phase.record_plan_candidate(
        goal=goal,
        run_id="candidate-run",
        tasks=[{"id": "t1", "description": "Implementiere AC1"}],
        tests=["pytest -q tests/test_feature.py"],
        criteria=["AC1: Verhalten ist korrekt"],
        phases=[],
        architect_prose="Plan mit aktueller Quellenlage",
    )
    state = RunState(
        aufgabe=goal, project_name="demo", run_id="candidate-run",
        project_dir=tmp_path,
    )

    pending = _run_coordinator_action(phase, state)

    assert pending["coordinator_action"] == "plan_approval_gate"
    assert pending["decision_basis"]["candidate_sha256"] == digest
    assert pending["decision_basis"]["plan_candidate_approved"] is False

    assert phase.approve_plan_candidate(
        goal=goal, run_id="candidate-run", candidate_sha256=digest,
    )
    approved = _run_coordinator_action(phase, state)

    assert approved["coordinator_action"] == "plan_prebuild_verify"
    assert approved["decision_basis"]["plan_candidate_approved"] is True


def test_plan_candidate_actions_bind_human_approval_before_prebuild(
    tmp_path, monkeypatch,
) -> None:
    from werkstatt import loop

    goal = "Implementiere die belegten Anforderungen"
    phase = PhaseState("demo", base_dir=tmp_path)
    phase.run_id = "candidate-run"
    phase.record_plan_candidate(
        goal=goal,
        run_id="candidate-run",
        tasks=[{"id": "t1", "description": "Implementiere AC1"}],
        tests=["pytest -q tests/test_feature.py"],
        criteria=["AC1: Verhalten ist korrekt"],
        phases=[],
        architect_prose="Plan mit aktueller Quellenlage",
        preflight_findings=[{
            "datei": "tests/test_old.py", "klasse": "test",
        }],
    )
    state = RunState(
        aufgabe=goal, project_name="demo", run_id="candidate-run",
        project_dir=tmp_path,
    )
    monkeypatch.setattr(loop, "get_run_id", lambda: "candidate-run")
    monkeypatch.setattr(loop, "_human_gate_plan", lambda _state: 0)
    monkeypatch.setattr(loop, "_plan_gate", lambda _state: True)
    verified: list[str] = []
    monkeypatch.setattr(
        loop, "_verify_patches",
        lambda _state, *, phase: verified.append(phase) or True,
    )

    assert loop._run_plan_candidate_approval(state, phase, "demo") == 0
    assert phase.plan_candidate_is_approved(
        goal=goal, run_id="candidate-run",
    )
    assert verified == []

    assert loop._run_plan_candidate_prebuild_verify(
        state, phase, "demo",
    ) == 0
    assert verified == ["pre_build"]
    assert state.preflight_fehler == [{
        "datei": "tests/test_old.py", "klasse": "test",
    }]
    assert phase.data["plan_complete"] is True
    assert phase.approved_plan_is_current()
    assert phase.data["plan_prebuild_verify_checkpoint"]["status"] == "passed"
    assert phase.data["plan_prebuild_verify_checkpoint"][
        "preflight_findings_sha256"
    ]
    assert phase.load_plan_candidate(
        goal=goal, run_id="candidate-run",
    ) is None


def test_role_is_selected_before_role_specific_preflight(tmp_path, monkeypatch) -> None:
    from werkstatt import loop

    goal = "Analysiere src/feature.py und ergaenze einen Regressionstest"
    phase = PhaseState("demo", base_dir=tmp_path / ".werkstatt")
    phase.init_new(goal, [], tests=[], akzeptanzkriterien=[])
    phase.run_id = "preflight-run"
    state = RunState(
        aufgabe=goal, project_name="demo", project_dir=tmp_path,
        run_id="preflight-run",
    )
    state.coordinator_setup_context_ready = True
    state.explorer_context = _deterministic_explorer_context(tmp_path)
    source = tmp_path / "src" / "feature.py"
    source.parent.mkdir(exist_ok=True)
    source.write_text("VALUE = 1\n", encoding="utf-8")
    monkeypatch.setattr(loop, "get_run_id", lambda: "preflight-run")
    monkeypatch.setattr(loop, "check_run_lease", lambda _state: None)
    findings = [{"klasse": "test", "datei": "tests/test_feature.py"}]
    monkeypatch.setattr(
        "werkstatt.planner._preflight_scan", lambda _state: findings,
    )

    initial = loop._run_coordinator_action(phase, state)
    assert initial["coordinator_action"] == "planner_scout"
    assert initial["decision_basis"]["preflight_checkpoint_current"] is False

    # A stage marker is telemetry only. It cannot substitute for a persisted
    # Scout result and must not advance the role selection.
    phase.data["planner_role_stage"] = "scout"
    phase.data["planner_role_goal_sha256"] = hashlib.sha256(
        goal.encode("utf-8"),
    ).hexdigest()
    stage_only = loop._run_coordinator_action(phase, state)
    assert stage_only["coordinator_action"] == "planner_scout"

    from werkstatt.planner_artifacts import make_role_artifact

    state.planner_role_artifacts = {
        "scout": make_role_artifact(
            "scout", {"auftrag_prosa": "Belegte Untersuchung"},
            run_id="preflight-run", goal=goal, input_sha256="a" * 64,
        ),
    }
    after_scout = loop._run_coordinator_action(phase, state)
    assert after_scout["coordinator_action"] == "plan_preflight"
    assert after_scout["decision_basis"]["selected_planner_role"] == "architect"
    assert loop._run_plan_preflight_checkpoint(state, phase, "demo") == 0
    assert phase.load_preflight_checkpoint(
        goal=goal, run_id="preflight-run",
    ) == findings
    assert state.preflight_checkpoint_ready is True

    state.explorer_context = _deterministic_explorer_context(tmp_path)
    state.coordinator_setup_context_ready = True
    phase.data["planner_role_stage"] = "architect"
    next_decision = loop._run_coordinator_action(phase, state)
    assert next_decision["coordinator_action"].startswith("planner_")
    assert next_decision["decision_basis"][
        "preflight_checkpoint_current"
    ] is True
    assert "preflight_findings" in next_decision["decision_basis"][
        "planner_role_available_evidence"
    ]


def test_explicit_source_scout_reason_survives_control_audit_allowlist() -> None:
    from werkstatt.loop import _safe_coordinator_decision_basis

    basis = _safe_coordinator_decision_basis({
        "planner_role_decision": "scout",
        "planner_role_decision_reason": (
            "explicit_current_sources_need_scoped_investigation"
        ),
        "planner_role_available_evidence": [
            "user_goal", "explicit_source_evidence",
        ],
        "planner_role_required_evidence": [
            "user_goal", "explicit_source_evidence",
        ],
        "planner_role_missing_evidence": ["scout_report"],
    })

    assert basis is not None
    assert basis["planner_role_decision_reason"] == (
        "explicit_current_sources_need_scoped_investigation"
    )
    assert basis["planner_role_available_evidence"] == [
        "user_goal", "explicit_source_evidence",
    ]




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


def test_phase_end_verify_failure_routes_one_recovery_to_coordinator(
    tmp_path, monkeypatch,
) -> None:
    from werkstatt import failure_record

    phase = _phase(
        tmp_path,
        [{"id": "t1", "name": "Implement", "criterion_refs": ["AC1"]}],
        ["AC1"],
    )
    phase.run_id = "phase-recovery-run"
    phase.bind_approved_plan()
    phase.mark_done("t1")
    fingerprint = {"value": "a" * 64}
    monkeypatch.setattr(
        failure_record, "_worktree_fingerprint",
        lambda _path: fingerprint["value"],
    )
    failure_record_data = {
        "failure_id": "failure-1",
        "artifact_ref": "audit-logs/run/failures/phase-end.json",
        "work_sha": "c" * 40,
        "worktree_fingerprint": "a" * 64,
        "failed_stages": [{
            "stage_id": "pytest_full", "exit_code": 1,
            "error_excerpt": "AssertionError",
        }],
    }
    assert phase.record_phase_end_verify_failure(
        failure_record_data, project_dir=tmp_path,
    )
    state = RunState(
        aufgabe="Ziel",
        project_dir=tmp_path,
        project_name="demo",
        run_id="phase-recovery-run",
    )

    decision = _checkpoint_decision_payload(phase, None, state=state)
    assert decision["decision"] == "recover_phase_end_verify_checkpoint"
    assert decision["next_executor"] == "verify_recovery"

    assert phase.claim_phase_end_verify_recovery(project_dir=tmp_path)
    stalled = _checkpoint_decision_payload(phase, None, state=state)
    assert stalled["decision"] == "reject_stalled_phase_end_verify_recovery"
    assert stalled["next_executor"] is None


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
                "planner_role_available_evidence": [
                    "user_goal", "project_inventory", "explorer_evidence",
                ],
                "planner_role_required_evidence": [
                    "user_goal", "project_inventory",
                ],
                "planner_role_missing_evidence": ["scout_report"],
                "planner_role_missing_inputs": ["current_source_evidence"],
                "untrusted_evidence": ["raw prompt"],
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
        "planner_role_available_evidence": [
            "user_goal", "project_inventory", "explorer_evidence",
        ],
        "planner_role_required_evidence": [
            "user_goal", "project_inventory",
        ],
        "planner_role_missing_evidence": ["scout_report"],
        "planner_role_missing_inputs": ["current_source_evidence"],
    }


def test_coordinator_audit_projects_review_choice_without_raw_diff() -> None:
    from werkstatt.loop import _coordinator_decision_audit_payload

    digest = "a" * 64
    payload = _coordinator_decision_audit_payload(
        "review-run",
        {
            "decision": "review_task_checkpoint",
            "coordinator_action": "review_task_checkpoint",
            "next_executor": "reviewer",
            "review_dispatch": {
                "invoke_reviewer": True,
                "reason": "verify_warning_present",
                "evidence": {
                    "diff_sha256": digest,
                    "diff_chars": 90,
                    "risk_reasons": ["verify_warning_present"],
                    "raw_diff": "secret source content",
                },
            },
        },
    )

    assert payload["review_dispatch"] == {
        "invoke_reviewer": True,
        "reason": "verify_warning_present",
        "evidence": {
            "diff_sha256": digest,
            "diff_chars": 90,
            "risk_reasons": ["verify_warning_present"],
        },
    }
    assert "raw_diff" not in payload["review_dispatch"]["evidence"]
    assert "private_prompt" not in payload


def test_run_coordinator_selects_scout_without_setup_and_hydrates_plan_on_resume(
    tmp_path, monkeypatch,
) -> None:
    from werkstatt.loop import _run_coordinator_action

    state = RunState(aufgabe="Goal")
    missing_setup = _run_coordinator_action(None, state)
    assert missing_setup["coordinator_action"] == "planner_scout"
    assert missing_setup["next_executor"] == "planner_scout"

    phase = PhaseState("demo", base_dir=tmp_path)
    phase.init_new("Goal", [], tests=[], akzeptanzkriterien=[])
    phase.data["setup_complete"] = True
    phase.run_id = "run-1"
    state.run_id = "run-1"
    phase.save()
    resumed_phase = PhaseState("demo", base_dir=tmp_path)
    assert resumed_phase.load()
    # Setup completion is not a mandatory predecessor. With no current plan,
    # a new process chooses Scout directly to gather its own evidence.
    resumed_setup = _run_coordinator_action(resumed_phase, state)
    assert resumed_setup["coordinator_action"] == "planner_scout"
    assert resumed_setup["decision_basis"]["setup_checkpoint_complete"] is True
    assert resumed_setup["decision_basis"]["plan_checkpoint_complete"] is False
    state.coordinator_setup_context_ready = True
    state.explorer_context = _deterministic_explorer_context(tmp_path)
    _record_preflight(resumed_phase, state)
    assert _run_coordinator_action(resumed_phase, state)["coordinator_action"] == (
        "planner_scout"
    )

    resumed_phase.data["planner_role_stage"] = "scout"
    resumed_phase.data["planner_role_goal_sha256"] = hashlib.sha256(
        b"Goal",
    ).hexdigest()
    assert _run_coordinator_action(resumed_phase, state)["coordinator_action"] == (
        "planner_scout"
    )
    from werkstatt.planner_artifacts import make_role_artifact

    state.planner_role_artifacts = {
        "scout": make_role_artifact(
            "scout", {"auftrag_prosa": "Current Scout evidence"},
            run_id="run-1", goal="Goal", input_sha256="b" * 64,
        ),
    }
    assert _run_coordinator_action(resumed_phase, state)["coordinator_action"] == (
        "planner_architect"
    )
    resumed_phase.data["planner_role_stage"] = "architect"
    state.planner_role_artifacts["architect"] = make_role_artifact(
        "architect", "A validated architect output containing sufficient current planning evidence.",
        run_id="run-1", goal="Goal", input_sha256="c" * 64,
    )
    selected_split = _run_coordinator_action(resumed_phase, state)
    assert selected_split["coordinator_action"] == "planner_split"
    assert selected_split["next_executor"] == "planner_split"
    # Neither a stale stage nor artifacts from another run/goal may skip
    # Scout; production resume loads only matching artifacts.
    state.run_id = "other-run"
    state.planner_role_artifacts = {}
    _record_preflight(resumed_phase, state)
    assert _run_coordinator_action(resumed_phase, state)["coordinator_action"] == (
        "planner_scout"
    )
    state.run_id = "run-1"
    state.aufgabe = "Other goal"
    state.planner_role_artifacts = {}
    _record_preflight(resumed_phase, state)
    assert _run_coordinator_action(resumed_phase, state)["coordinator_action"] == (
        "planner_scout"
    )

    state.aufgabe = "Goal"
    # Simulate a real approved checkpoint: the production coordinator only
    # marks a plan complete after the human gate has accepted a non-empty
    # graph and its immutable content has been bound to the checkpoint.
    resumed_phase.data["tasks"] = [{
        "id": "approved-task",
        "name": "Approved task",
        "description": "Inspect the approved scope",
        "action": "read",
        "dependencies": [],
        "criterion_refs": [],
    }]
    resumed_phase.data["plan_complete"] = True
    resumed_phase.bind_approved_plan()
    resumed_phase.save()
    final_phase = PhaseState("demo", base_dir=tmp_path)
    assert final_phase.load()
    decision = _run_coordinator_action(final_phase, state)
    assert decision["coordinator_action"] == "phase_end_review"

    worktree_fingerprint = "a" * 64
    monkeypatch.setattr(
        "werkstatt.failure_record._worktree_fingerprint",
        lambda _project_dir: worktree_fingerprint,
    )
    final_phase.record_phase_end_review(
        worktree_fingerprint=worktree_fingerprint,
    )
    decision = _run_coordinator_action(final_phase, state)
    assert decision["coordinator_action"] == "human_gate"

    final_phase.record_human_gate(
        worktree_fingerprint=worktree_fingerprint,
        commit_requested=True,
    )
    decision = _run_coordinator_action(final_phase, state)
    assert decision["coordinator_action"] == "phase_end_verify"

    from werkstatt.phase_state import phase_end_verify_evidence

    state.last_verify_results = [{
        "stage_id": "pytest_full",
        "exit_code": 0,
        "ok": True,
    }]
    evidence_sha256, stage_ids = phase_end_verify_evidence(
        state.last_verify_results,
    )
    assert evidence_sha256 is not None
    final_phase.record_phase_end_verify(
        worktree_fingerprint=worktree_fingerprint,
        evidence_sha256=evidence_sha256,
        stage_ids=stage_ids,
    )
    decision = _run_coordinator_action(final_phase, state)
    assert decision["coordinator_action"] == "commit_run"

    commit_sha = "c" * 40
    final_phase.record_commit_pending_post_verify(
        commit_sha=commit_sha,
        verify_evidence_sha256=evidence_sha256,
    )
    monkeypatch.setattr("werkstatt.loop._git_head", lambda _path: commit_sha)
    monkeypatch.setattr("werkstatt.loop._git_dirty", lambda _path: False)
    decision = _run_coordinator_action(final_phase, state)
    assert decision["coordinator_action"] == "post_commit_verify"

    monkeypatch.setattr(
        "werkstatt.failure_record._worktree_fingerprint",
        lambda _project_dir: "b" * 64,
    )
    monkeypatch.setattr("werkstatt.loop._git_dirty", lambda _path: True)
    decision = _run_coordinator_action(final_phase, state)
    assert decision["coordinator_action"] == "phase_end_review"

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


def test_planner_role_stage_is_telemetry_not_role_evidence(tmp_path) -> None:
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
    _record_preflight(resumed, state)
    decision = _run_coordinator_action(resumed, state)
    assert decision["coordinator_action"] == "planner_scout"
    assert decision["decision_basis"]["planner_role_stage"] == "scout"

    with pytest.raises(ValueError, match="Rollenstage"):
        _persist_planner_role_stage(
            resumed, "builder", run_id="run-1", goal="Goal",
        )


def test_phase_end_review_action_persists_current_worktree_evidence(
    tmp_path, monkeypatch,
) -> None:
    from werkstatt.loop import _run_phase_end_review_checkpoint

    phase = _phase(
        tmp_path,
        [{"id": "t1", "name": "Inspect", "action": "read"}],
        [],
    )
    phase.run_id = "run-1"
    phase.bind_approved_plan()
    phase.save()
    state = RunState(
        aufgabe="Ziel",
        project_dir=tmp_path,
        project_name="demo",
        run_id="run-1",
    )
    fingerprint = "c" * 64
    monkeypatch.setattr(
        "werkstatt.loop._phase_end_review_action",
        lambda *_args: 0,
    )
    monkeypatch.setattr(
        "werkstatt.failure_record._worktree_fingerprint",
        lambda _project_dir: fingerprint,
    )
    monkeypatch.setattr("werkstatt.loop.check_run_lease", lambda _state: None)

    assert _run_phase_end_review_checkpoint(state, phase, "demo") == 0
    assert phase.phase_end_review_is_current(
        worktree_fingerprint=fingerprint,
    )


def test_rejected_phase_end_review_stops_without_inline_role_chain(
    tmp_path, monkeypatch,
) -> None:
    from werkstatt.phases.finalize import _phase_end_review_action

    state = RunState(
        aufgabe="Ziel",
        project_dir=tmp_path,
        project_name="demo",
        tasks=[{"id": "t1", "name": "Implement"}],
    )
    phase = _phase(
        tmp_path,
        [{"id": "t1", "name": "Implement", "action": "update"}],
        [],
    )
    monkeypatch.setattr(
        "werkstatt.reviewer.run_phase_end_review",
        lambda _state: False,
    )

    assert _phase_end_review_action(state, 0, phase) == 1
    assert state.phase_review_approved is not True


def test_human_gate_checkpoint_action_persists_commit_consent(
    tmp_path, monkeypatch,
) -> None:
    from werkstatt.loop import _run_human_gate_checkpoint

    phase = _phase(tmp_path, [{"id": "t1", "name": "Implement"}], [])
    phase.run_id = "run-human-gate"
    fingerprint = "d" * 64
    phase.record_phase_end_review(worktree_fingerprint=fingerprint)
    state = RunState(
        aufgabe="Ziel",
        project_dir=tmp_path,
        project_name="demo",
        run_id="run-human-gate",
    )
    monkeypatch.setattr(
        "werkstatt.failure_record._worktree_fingerprint",
        lambda _path: fingerprint,
    )
    monkeypatch.setattr(
        "werkstatt.loop._phase_human_gate_action",
        lambda _state: (2, True),
    )
    monkeypatch.setattr("werkstatt.loop.check_run_lease", lambda _state: None)

    assert _run_human_gate_checkpoint(state, phase, "demo") == 0
    assert phase.human_gate_is_current(worktree_fingerprint=fingerprint)
    assert phase.data["human_gate_checkpoint"]["commit_requested"] is True


def test_human_gate_checkpoint_rejects_worktree_change_during_gate(
    tmp_path, monkeypatch,
) -> None:
    from werkstatt.loop import _run_human_gate_checkpoint

    phase = _phase(tmp_path, [{"id": "t1", "name": "Implement"}], [])
    phase.run_id = "run-human-gate"
    before, after = "e" * 64, "f" * 64
    phase.record_phase_end_review(worktree_fingerprint=before)
    fingerprints = iter((before, after))
    state = RunState(
        aufgabe="Ziel",
        project_dir=tmp_path,
        project_name="demo",
        run_id="run-human-gate",
    )
    monkeypatch.setattr(
        "werkstatt.failure_record._worktree_fingerprint",
        lambda _path: next(fingerprints),
    )
    monkeypatch.setattr(
        "werkstatt.loop._phase_human_gate_action",
        lambda _state: (2, True),
    )
    monkeypatch.setattr("werkstatt.loop.check_run_lease", lambda _state: None)

    assert _run_human_gate_checkpoint(state, phase, "demo") == 3
    assert "human_gate_checkpoint" not in phase.data


def test_phase_end_verify_action_persists_current_evidence_checkpoint(
    tmp_path, monkeypatch,
) -> None:
    from werkstatt.loop import _run_phase_end_verify_checkpoint

    phase = _phase(tmp_path, [{"id": "t1", "name": "Inspect"}], [])
    phase.run_id = "run-phase-verify"
    phase.bind_approved_plan()
    fingerprint = "e" * 64
    phase.record_phase_end_review(worktree_fingerprint=fingerprint)
    phase.record_human_gate(
        worktree_fingerprint=fingerprint,
        commit_requested=True,
    )
    state = RunState(
        aufgabe="Ziel",
        project_dir=tmp_path,
        project_name="demo",
        run_id="run-phase-verify",
    )
    state.tasks = [{"id": "t1", "name": "Inspect"}]

    def verify(_state, *_args, **_kwargs):
        _state.last_verify_results = [{
            "stage_id": "pytest_full",
            "exit_code": 0,
            "ok": True,
            "phase_end_tree_sha256": fingerprint,
            "phase_end_tree_stable": True,
        }]
        return 0

    monkeypatch.setattr(
        "werkstatt.loop._phase_end_verify_action", verify,
    )
    monkeypatch.setattr(
        "werkstatt.failure_record._worktree_fingerprint",
        lambda _path: fingerprint,
    )
    monkeypatch.setattr("werkstatt.loop.check_run_lease", lambda _state: None)

    assert _run_phase_end_verify_checkpoint(state, phase, "demo") == 0
    from werkstatt.phase_state import phase_end_verify_evidence

    evidence_sha256, stage_ids = phase_end_verify_evidence(
        state.last_verify_results,
    )
    assert phase.phase_end_verify_is_current(
        worktree_fingerprint=fingerprint,
        evidence_sha256=evidence_sha256,
    )
    assert phase.data["phase_end_verify_checkpoint"]["stage_ids"] == stage_ids


def test_failed_phase_end_verify_yields_to_recovery_checkpoint(
    tmp_path, monkeypatch,
) -> None:
    from werkstatt.phases import finalize

    phase = _phase(tmp_path, [{"id": "t1", "name": "Inspect"}], [])
    phase.run_id = "run-phase-verify-failed"
    phase.bind_approved_plan()
    fingerprint = "f" * 64
    phase.record_phase_end_review(worktree_fingerprint=fingerprint)
    phase.record_human_gate(
        worktree_fingerprint=fingerprint,
        commit_requested=False,
    )
    state = RunState(
        aufgabe="Ziel",
        project_dir=tmp_path,
        project_name="demo",
        run_id="run-phase-verify-failed",
    )
    state.progress_written_at_commit = True
    state.last_verify_results = [{
        "stage_id": "pytest_full", "exit_code": 1, "ok": False,
        "error_excerpt": "AssertionError",
    }]
    monkeypatch.setattr(
        finalize, "_verify_patches", lambda *_args, **_kwargs: False,
    )
    monkeypatch.setattr(
        finalize, "create_failure_record",
        lambda *_args, **_kwargs: {
            "failure_id": "failure-final-1",
            "artifact_ref": "audit-logs/run/failure.json",
            "work_sha": "c" * 40,
            "worktree_fingerprint": fingerprint,
            "failed_stages": [{
                "stage_id": "pytest_full", "exit_code": 1,
                "error_excerpt": "AssertionError",
            }],
        },
    )
    monkeypatch.setattr(
        "werkstatt.failure_record._worktree_fingerprint",
        lambda _path: fingerprint,
    )
    monkeypatch.setattr(finalize, "audit", lambda *_args, **_kwargs: True)

    result = finalize._phase_end_verify_action(
        state, 1, phase.data["tasks"], "demo", phase, checkpointed=True,
    )

    assert result == 3
    assert phase.data["phase_end_verify_failure_checkpoint"]["status"] == "pending"


def test_post_commit_verify_failure_returns_to_coordinator_checkpoint(
    tmp_path, monkeypatch,
) -> None:
    from werkstatt import failure_record
    from werkstatt.loop import _run_post_commit_verify_checkpoint

    phase = _phase(
        tmp_path,
        [{"id": "t1", "name": "Implement", "criterion_refs": ["AC1"]}],
        ["AC1"],
    )
    phase.run_id = "post-commit-failure-run"
    phase.bind_approved_plan()
    phase.mark_done("t1")
    fingerprint = "a" * 64
    commit_sha = "c" * 40
    phase.record_phase_end_review(worktree_fingerprint=fingerprint)
    phase.record_human_gate(
        worktree_fingerprint=fingerprint,
        commit_requested=True,
    )
    phase.record_phase_end_verify(
        worktree_fingerprint=fingerprint,
        evidence_sha256="b" * 64,
        stage_ids=["pytest_full"],
    )
    phase.record_commit_pending_post_verify(
        commit_sha=commit_sha,
        verify_evidence_sha256="b" * 64,
    )
    state = RunState(
        aufgabe="Ziel",
        project_dir=tmp_path,
        project_name="demo",
        run_id="post-commit-failure-run",
    )
    monkeypatch.setattr("werkstatt.loop.check_run_lease", lambda _state: None)
    monkeypatch.setattr("werkstatt.loop._git_head", lambda _path: commit_sha)
    monkeypatch.setattr("werkstatt.loop._git_dirty", lambda _path: False)
    monkeypatch.setattr(
        failure_record, "_worktree_fingerprint", lambda _path: fingerprint,
    )
    monkeypatch.setattr(
        "werkstatt.loop._verify_patches",
        lambda _state, **_kwargs: (
            setattr(_state, "last_verify_results", [{
                "stage_id": "pytest_full", "exit_code": 1, "ok": False,
                "error_excerpt": "AssertionError",
            }]) or False
        ),
    )
    monkeypatch.setattr(
        failure_record, "create_failure_record",
        lambda *_args, **_kwargs: {
            "failure_id": "post-failure-1",
            "artifact_ref": "audit-logs/run/failure.json",
            "work_sha": commit_sha,
            "worktree_fingerprint": fingerprint,
            "failed_stages": [{
                "stage_id": "pytest_full", "exit_code": 1,
                "error_excerpt": "AssertionError",
            }],
        },
    )
    monkeypatch.setattr(
        "werkstatt.phases.finalize._post_commit_snapshot_check",
        lambda *_args: (True, {"worktree_clean": True}),
    )
    monkeypatch.setattr("werkstatt.loop.audit", lambda *_args, **_kwargs: True)

    assert _run_post_commit_verify_checkpoint(state, phase, "demo") == 3
    checkpoint = phase.data["phase_end_verify_failure_checkpoint"]
    assert checkpoint["status"] == "pending"
    assert checkpoint["failure_id"] == "post-failure-1"


def test_phase_end_verify_action_retries_if_worktree_changes_during_verify(
    tmp_path, monkeypatch,
) -> None:
    from werkstatt.loop import _run_phase_end_verify_checkpoint

    phase = _phase(tmp_path, [{"id": "t1", "name": "Inspect"}], [])
    phase.run_id = "run-phase-verify-race"
    phase.bind_approved_plan()
    before = "1" * 64
    after = "2" * 64
    phase.record_phase_end_review(worktree_fingerprint=before)
    phase.record_human_gate(
        worktree_fingerprint=before,
        commit_requested=True,
    )
    state = RunState(
        aufgabe="Ziel",
        project_dir=tmp_path,
        project_name="demo",
        run_id="run-phase-verify-race",
    )
    state.tasks = [{"id": "t1", "name": "Inspect"}]
    fingerprint = [before]

    def verify(_state, *_args, **_kwargs):
        _state.last_verify_results = [{
            "stage_id": "pytest_full",
            "exit_code": 0,
            "ok": True,
            "phase_end_tree_sha256": before,
            "phase_end_tree_stable": True,
        }]
        fingerprint[0] = after
        return 0

    monkeypatch.setattr(
        "werkstatt.loop._phase_end_verify_action", verify,
    )
    monkeypatch.setattr(
        "werkstatt.failure_record._worktree_fingerprint",
        lambda _path: fingerprint[0],
    )
    monkeypatch.setattr("werkstatt.loop.check_run_lease", lambda _state: None)

    assert _run_phase_end_verify_checkpoint(state, phase, "demo") == 3
    assert "phase_end_verify_checkpoint" not in phase.data


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
    _record_preflight(phase, state)

    broad_decision = _run_coordinator_action(phase, state)
    assert broad_decision["coordinator_action"] == "planner_scout"
    assert broad_decision["decision_basis"]["scout_route_reason"].startswith(
        "auftrag_enthaelt_breiten_marker:"
    )
    assert broad_decision["decision_basis"]["planner_role_decision"] == "scout"
    assert broad_decision["decision_basis"]["planner_role_missing_evidence"] == [
        "scout_report",
    ]

    focused_goal = "Ergaenze src/feature.py um eine neue Funktion"
    phase.data["aufgabe"] = focused_goal
    phase.save()
    state.aufgabe = focused_goal
    _record_preflight(phase, state)
    focused_decision = _run_coordinator_action(phase, state)
    assert focused_decision["coordinator_action"] == "planner_direct"
    assert focused_decision["decision_basis"]["scout_route_reason"] == (
        "explizite_einzeldatei_mit_explorer_beleg"
    )
    assert focused_decision["reason"] == (
        "unique_source_bound_edit_ready"
    )
    assert focused_decision["decision_basis"]["direct_builder_ready"] is True

    source = tmp_path / "src" / "feature.py"
    source.write_text("TIMEOUT = 10\n", encoding="utf-8")
    state.explorer_context["key_files"][0]["source_sha256"] = (
        hashlib.sha256(source.read_bytes()).hexdigest()
    )
    direct_goal = "Setze TIMEOUT in src/feature.py auf 30"
    phase.data["aufgabe"] = direct_goal
    phase.save()
    state.aufgabe = direct_goal
    _record_preflight(phase, state)
    direct_decision = _run_coordinator_action(phase, state)
    assert direct_decision["coordinator_action"] == "planner_direct"
    assert direct_decision["decision_basis"]["planner_role_decision"] == (
        "builder_direct"
    )
    assert direct_decision["decision_basis"]["direct_builder_ready"] is True
    assert direct_decision["decision_basis"][
        "planner_role_required_evidence"
    ] == ["explicit_user_edit", "unique_current_source"]
    assert direct_decision["decision_basis"][
        "planner_role_available_evidence"
    ] == [
        "explicit_user_edit", "explorer_evidence",
        "explorer_source_evidence", "preflight_findings", "project_inventory",
        "unique_current_source", "user_goal",
    ]


def test_initial_checkpoint_can_dispatch_scout_from_explicit_current_sources(
    tmp_path,
) -> None:
    from werkstatt.loop import _run_coordinator_action

    goal = "Pruefe src/alpha.py zusammen mit src/beta.py auf die Ursache"
    for relative, contents in (
        ("src/alpha.py", "def alpha(): return beta()\n"),
        ("src/beta.py", "def beta(): return missing()\n"),
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(contents, encoding="utf-8")
    phase = PhaseState("demo", base_dir=tmp_path / "phase")
    phase.init_new(goal, [], tests=[], akzeptanzkriterien=[])
    state = RunState(
        aufgabe=goal, project_name="demo", project_dir=tmp_path,
        run_id="explicit-source-run",
    )
    _record_preflight(phase, state)

    decision = _run_coordinator_action(phase, state)

    assert decision["coordinator_action"] == "planner_scout"
    basis = decision["decision_basis"]
    assert basis["setup_context_source"] == "explicit_current_sources"
    assert basis["planner_role_decision"] == "scout"
    assert basis["planner_role_decision_reason"] == (
        "explicit_current_sources_need_scoped_investigation"
    )
    assert basis["planner_role_available_evidence"] == [
        "explicit_source_evidence", "preflight_findings", "user_goal",
    ]
    assert basis["planner_role_required_evidence"] == [
        "user_goal", "explicit_source_evidence",
    ]
    assert "project_inventory" not in basis["planner_role_available_evidence"]
    assert "explorer_evidence" not in basis["planner_role_available_evidence"]
    assert state.explorer_context["related_files_scan"]["status"] == (
        "not_requested"
    )
    assert all(
        item["source_complete"] is True
        and len(item["source_sha256"]) == 64
        for item in state.explorer_context["key_files"]
    )


def test_project_coordinator_can_choose_scout_at_validated_role_checkpoint(
    tmp_path, monkeypatch,
) -> None:
    from werkstatt.loop import _run_coordinator_action
    from werkstatt.roles import planner_dispatch

    goal = "Ergaenze src/feature.py um eine neue Funktion"
    phase = PhaseState("demo", base_dir=tmp_path / "phase")
    phase.init_new(goal, [], tests=[], akzeptanzkriterien=[])
    phase.data["setup_complete"] = True
    phase.run_id = "run-project-coordinator"
    phase.save()
    state = RunState(
        aufgabe=goal,
        project_name="demo",
        project_dir=tmp_path,
        run_id="run-project-coordinator",
    )
    state.explorer_context = _deterministic_explorer_context(tmp_path)
    state.coordinator_setup_context_ready = True
    _record_preflight(phase, state)

    monkeypatch.setattr(
        planner_dispatch,
        "scout_route_decision",
        lambda *_args: (
            "src/feature.py", "explicit_source_is_current",
        ),
    )
    monkeypatch.setattr(
        planner_dispatch,
        "direct_builder_route_decision",
        lambda *_args, **_kwargs: (False, "architect_needed"),
    )
    monkeypatch.setattr(
        "werkstatt.checkpoint_coordinator.recommend_checkpoint_role",
        lambda *_args, **_kwargs: {
            "role": "scout",
            "source": "project_chat_model",
            "reason_code": "more_repository_evidence_needed",
            "allowed_roles": ["architect", "scout"],
        },
    )

    decision = _run_coordinator_action(phase, state)

    assert decision["coordinator_action"] == "planner_scout"
    assert decision["reason"] == "project_coordinator_selected_scout"
    assert decision["coordinator_model_choice"]["source"] == (
        "project_chat_model"
    )
    assert decision["decision_basis"]["planner_role_selected"] == "scout"


def test_coordinator_dispatches_scout_before_separate_context_setup(
    tmp_path,
) -> None:
    from werkstatt.loop import _run_coordinator_action

    phase = PhaseState("demo", base_dir=tmp_path / "phase")
    phase.init_new("Goal", [], tests=[], akzeptanzkriterien=[])
    phase.data["setup_complete"] = True
    phase.run_id = "run-1"
    phase.save()
    state = RunState(
        aufgabe="Goal", project_name="demo", project_dir=tmp_path,
        run_id="run-1",
    )
    state.coordinator_setup_context_ready = False
    state.explorer_context = {}
    _record_preflight(phase, state)

    decision = _run_coordinator_action(phase, state)
    assert decision["coordinator_action"] == "planner_scout"
    assert decision["next_executor"] == "planner_scout"
    assert decision["decision_basis"]["planner_role_required_evidence"] == [
        "user_goal",
    ]
    assert decision["decision_basis"]["planner_role_missing_inputs"] == []
    assert decision["decision_basis"]["setup_context_source"] == (
        "scout_owned_graphify_retrieval"
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
    _record_preflight(phase, original_state)
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

    assert decision["coordinator_action"] == "planner_direct"
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
    _record_preflight(phase, original_state)
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

    assert decision["coordinator_action"] == "planner_direct"
    assert resumed_state.coordinator_setup_context_ready is True
    assert resumed_state.explorer_context["key_files"][0]["source_sha256"] == (
        hashlib.sha256(
            (tmp_path / "src" / "feature.py").read_bytes(),
        ).hexdigest()
    )


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

    for run_id, goal, expected_action in (
        ("demo-run-2", "Update src/feature.py", "planner_direct"),
        ("demo-run-1", "Update another target", "planner_scout"),
    ):
        resumed_phase = PhaseState("demo", base_dir=tmp_path / ".werkstatt")
        assert resumed_phase.load()
        resumed_state = RunState(
            aufgabe=goal,
            project_dir=tmp_path,
            project_name="demo",
            run_id=run_id,
        )
        if run_id == "demo-run-2":
            _record_preflight(resumed_phase, resumed_state)
        decision = _run_coordinator_action(resumed_phase, resumed_state)

        assert decision["coordinator_action"] == expected_action
        assert resumed_state.coordinator_setup_context_ready is (
            expected_action == "planner_direct"
        )


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

    assert decision["coordinator_action"] == "replan_unassigned_criteria"
    assert state.coordinator_setup_context_ready is False


def test_recovery_replan_resume_preserves_failed_task_without_explorer_setup(
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

    assert decision["decision"] == "replan_failed_criteria"
    assert decision["coordinator_action"] == "replan_failed_criteria"
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
        "coordinator_model_choice": {
            "role": "architect",
            "source": "project_chat_model",
            "reason_code": "source_evidence_sufficient",
            "allowed_roles": ["scout", "architect"],
            "source_evidence": [{"path": "private.py", "sha256": "f" * 64}],
            "private_prompt": "must not persist",
        },
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
            "planner_role_decision": "builder_direct",
            "planner_role_decision_reason": "unique_source_bound_edit_ready",
            "planner_role_required_evidence": [
                "explicit_user_edit", "unique_current_source",
            ],
            "planner_role_missing_evidence": [],
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
        "coordinator_model_choice": {
            "role": "architect",
            "source": "project_chat_model",
            "reason_code": "source_evidence_sufficient",
            "allowed_roles": ["scout", "architect"],
        },
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
                "planner_role_decision": "builder_direct",
                "planner_role_decision_reason": "unique_source_bound_edit_ready",
                "planner_role_required_evidence": [
                    "explicit_user_edit", "unique_current_source",
                ],
                "planner_role_missing_evidence": [],
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


def test_coordinator_does_not_hydrate_plan_from_another_run(tmp_path) -> None:
    from werkstatt.loop import _run_coordinator_action

    phase = _phase(
        tmp_path,
        [{"id": "t1", "action": "read", "criterion_refs": ["AC1"]}],
        ["Inspect the current source"],
    )
    phase.run_id = "prior-run"
    phase.data["run_id"] = "prior-run"
    phase.save()
    state = RunState(
        aufgabe="Ziel",
        project_name="demo",
        project_dir=tmp_path,
        run_id="new-run",
    )

    decision = _run_coordinator_action(phase, state)

    assert decision["coordinator_action"] == "planner_scout"
    assert state.tasks == []
    assert state.tests == []
    assert state.akzeptanzkriterien == []


def test_coordinator_rejects_plan_changed_after_human_approval(tmp_path) -> None:
    from werkstatt.loop import _run_coordinator_action

    phase = _phase(
        tmp_path,
        [{
            "id": "t1", "action": "update", "criterion_refs": ["AC1"],
            "task_files": ["src/current.py"], "description": "Approved edit",
        }],
        ["Apply only the approved edit"],
    )
    phase.run_id = "approved-run"
    phase.data["run_id"] = "approved-run"
    phase.save()
    phase.data["tasks"][0]["description"] = "Tampered edit outside approval"
    state = RunState(
        aufgabe="Ziel",
        project_name="demo",
        project_dir=tmp_path,
        run_id="approved-run",
    )
    state.coordinator_setup_context_ready = True
    state.explorer_context = _deterministic_explorer_context(tmp_path)
    _record_preflight(phase, state)

    decision = _run_coordinator_action(phase, state)

    assert decision["coordinator_action"] == "planner_scout"
    assert decision["decision_basis"]["plan_fingerprint_matches"] is False
    assert state.tasks == []


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

    result = task_phase.run_task_checkpoint(
        state, phase,
        coordinator_decision=coordinator_decision_for_task(phase, state),
    )

    assert result[0] == 1
    assert calls == ["replan"]


def test_successful_criteria_replan_yields_before_new_task_dispatch(
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

    def replan(_state, current_phase):
        calls.append("replan")
        new_task = {
            "id": "t2", "action": "read", "status": "pending",
            "criterion_refs": ["AC2"],
        }
        current_phase.data["tasks"].append(new_task)
        state.tasks = list(current_phase.data["tasks"])
        current_phase.save()
        return True

    monkeypatch.setattr("werkstatt.audit.get_run_id", lambda: "")
    monkeypatch.setattr(task_phase, "audit", lambda *_a, **_kw: True)
    monkeypatch.setattr(
        "werkstatt.criteria_replan.replan_unassigned_criteria", replan,
    )
    monkeypatch.setattr(
        task_phase, "_run_with_progress",
        lambda *_a, **_kw: (_ for _ in ()).throw(
            AssertionError("new task ran before coordinator reassessment"),
        ),
    )

    result = task_phase.run_task_checkpoint(
        state, phase,
        coordinator_decision=coordinator_decision_for_task(phase, state),
    )

    assert result[0] == 0
    assert calls == ["replan"]
    assert phase.get_task("t2")["status"] == "pending"


def test_coordinator_routes_checkpoint_replan_goal_to_role_chooser(
    tmp_path, monkeypatch,
) -> None:
    from werkstatt import checkpoint_coordinator, criteria_replan, loop

    phase = _phase(
        tmp_path,
        [{"id": "t1", "action": "read", "criterion_refs": ["AC1"]}],
        ["First criterion", "Second criterion"],
    )
    phase.mark_done("t1")
    state = RunState(
        project_dir=tmp_path,
        project_name="demo",
        run_id=phase.run_id,
        aufgabe="OP-398 " + "long request detail " * 1000,
        tasks=list(phase.data["tasks"]),
        akzeptanzkriterien=list(phase.data["akzeptanzkriterien"]),
    )
    assert criteria_replan.replan_unassigned_criteria(
        state, phase,
    ) is True
    observed = {}

    def choose(current_state, **kwargs):
        observed["goal"] = current_state.aufgabe
        observed["task_count"] = len(kwargs["phase_data"].get("tasks", []))
        return {
            "decision": "prepare_approved_work_graph",
            "coordinator_action": "planner_split",
            "reason": "test_role_selection",
            "next_executor": "planner_split",
        }

    monkeypatch.setattr(
        checkpoint_coordinator, "choose_planner_checkpoint_action", choose,
    )
    decision = loop._run_coordinator_action(phase, state)

    assert decision["coordinator_action"] == "planner_split"
    assert observed["goal"] == criteria_replan.active_criteria_replan(phase)[
        "planner_goal"
    ]
    assert observed["task_count"] == 0
    assert [task["id"] for task in phase.data["tasks"]] == ["t1"]


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

    result = task_phase.run_task_checkpoint(
        state, phase,
        coordinator_decision=coordinator_decision_for_task(phase, state),
    )

    assert result[0] == 0
    assert phase.get_task("t1")["status"] == "done"
    assert phase.get_task("t2")["status"] == "pending"


def test_task_worker_rechecks_coordinator_choice_before_dispatch(
    tmp_path, monkeypatch,
) -> None:
    phase = _phase(
        tmp_path,
        [{"id": "t1", "action": "read", "criterion_refs": ["AC1"]}],
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

    result = task_phase.run_task_checkpoint(
        state,
        phase,
        coordinator_decision={
            "coordinator_action": "execute_task_checkpoint",
            "decision": "execute_planned_task",
            "next_task_id": "stale-task",
            "next_executor": "read_only_task",
        },
    )

    assert result[0] == 0
    assert state.coordinator_dispatch_stale is True
    assert phase.get_task("t1")["status"] == "pending"


def test_task_executor_fails_closed_without_coordinator_choice(
    tmp_path, monkeypatch,
) -> None:
    phase = _phase(
        tmp_path,
        [{"id": "t1", "action": "read", "criterion_refs": ["AC1"]}],
        ["Inventory is complete"],
    )
    state = RunState(
        project_dir=tmp_path,
        project_name="demo",
        aufgabe="Inventory is complete",
        tasks=phase.data["tasks"],
    )
    audit_events = []
    monkeypatch.setattr(
        task_phase, "audit",
        lambda event, payload, *_args, **_kwargs: audit_events.append(
            (event, payload),
        ) or True,
    )

    result = task_phase.run_task_checkpoint(state, phase)

    assert result[0] == 1
    assert phase.get_task("t1")["status"] == "pending"
    assert any(
        event == "loop_failed"
        and payload.get("reason") == "task_checkpoint_requires_coordinator_decision"
        for event, payload in audit_events
    )


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
    monkeypatch.setattr(task_phase, "audit", lambda *args: audit_events.append(args) or True)
    monkeypatch.setattr(
        run_followups,
        "reconcile_chat_followups",
        lambda *_args: pytest.fail(
            "Task executor must leave follow-up reconciliation to coordinator",
        ),
    )

    result = task_phase.run_task_checkpoint(
        state, phase,
        coordinator_decision=coordinator_decision_for_task(phase, state),
    )

    assert result[0] == 0
    event = next(args for args in audit_events if args[0] == "loop_checkpoint_decision")
    assert event[1]["checkpoint_id"] == "demo-run-1:7"
    assert event[1]["decision"] == "reject_criteria_verify_scope_missing"
    assert event[1]["criteria_task_verification"]["unverifiable_count"] == 1
    assert event[1]["goal_candidate_before_final_verify"] is False
