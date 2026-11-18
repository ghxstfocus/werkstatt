import json

import pytest

from werkstatt import criteria_replan
from werkstatt.phase_state import PhaseState
from werkstatt.state import RunState


@pytest.mark.parametrize(
    ("action", "failure", "detail", "expected"),
    [
        (
            "verify", "verify_failed",
            json.dumps({"source": "verify", "errors": ["tests: failed"]}),
            ["verify-task"],
        ),
        ("verify", "verify_failed", "", []),
        ("verify", "verify_failed", "[]", []),
        ("verify", "verify_failed", "null", []),
        (
            "verify", "verify_failed",
            json.dumps({"source": "builder", "errors": ["tests: failed"]}),
            [],
        ),
        (
            "update", "verify_failed",
            json.dumps({"source": "verify", "errors": ["tests: failed"]}),
            [],
        ),
        ("verify", "verify_evidence_missing", "", []),
    ],
)
def test_verify_task_replan_requires_current_hard_error_evidence(
    tmp_path, action, failure, detail, expected,
):
    phase = PhaseState("demo", base_dir=tmp_path)
    phase.init_new(
        "Goal",
        [{"id": "verify-task", "action": action, "criterion_refs": ["AC1"]}],
        akzeptanzkriterien=["Criterion"],
    )
    phase.mark_failed("verify-task", failure=failure, detail=detail or None)

    assert criteria_replan.eligible_failed_task_ids(
        phase, ["AC1"],
    ) == expected


def test_replans_only_missing_criteria_and_preserves_completed_tasks(
    tmp_path, monkeypatch,
):
    phase = PhaseState("demo", base_dir=tmp_path)
    phase.init_new(
        "Goal",
        [{
            "id": "existing",
            "name": "Existing criterion task",
            "action": "read",
            "criterion_refs": ["AC1"],
            "task_files": ["src/one.py"],
        }],
        tests=["pytest tests/test_one.py"],
        akzeptanzkriterien=["First criterion", "Second criterion"],
    )
    phase.data["setup_complete"] = True
    phase.data["plan_complete"] = True
    phase.bind_approved_plan()
    phase.mark_done("existing")
    state = RunState(
        project_dir=tmp_path,
        project_name="demo",
        run_id="run-criteria-gap",
        aufgabe="OP-398 " + "long original request detail " * 3000,
        api_key="test-key",
        tasks=list(phase.data["tasks"]),
        tests=list(phase.data["tests"]),
        akzeptanzkriterien=list(phase.data["akzeptanzkriterien"]),
        budget={"max_llm_calls": 20},
    )

    phase.run_id = state.run_id
    monkeypatch.setattr(criteria_replan, "audit", lambda *args, **kwargs: True, raising=False)

    assert criteria_replan.replan_unassigned_criteria(state, phase) is True

    existing = phase.get_task("existing")
    assert existing["status"] == "done"
    assert existing["criterion_refs"] == ["AC1"]
    assert len(phase.data["tasks"]) == 1
    record = criteria_replan.active_criteria_replan(phase)
    assert record is not None
    assert record["status"] == "roles_pending"
    assert "AC2: Second criterion" in record["planner_goal"]
    assert "OP-398" not in record["planner_goal"]
    assert len(record["planner_goal"]) < 5_000
    assert phase.data["akzeptanzkriterien"] == [
        "First criterion", "Second criterion",
    ]
    assert phase.criteria_progress()["uncovered"] == ["AC2"]


def test_checkpoint_replan_prepares_bounded_subgoal(
    tmp_path,
):
    phase = PhaseState("demo", base_dir=tmp_path)
    phase.init_new(
        "Goal",
        [{"id": "first", "action": "read", "criterion_refs": ["AC1"]}],
        akzeptanzkriterien=["First", "Second"],
    )
    phase.data["setup_complete"] = True
    phase.data["plan_complete"] = True
    phase.bind_approved_plan()
    phase.mark_done("first")
    state = RunState(
        project_dir=tmp_path,
        project_name="demo",
        run_id="run-checkpoint-criteria-replan",
        aufgabe="OP-398 " + "long request detail " * 1000,
        tasks=list(phase.data["tasks"]),
        akzeptanzkriterien=list(phase.data["akzeptanzkriterien"]),
    )
    phase.run_id = state.run_id

    assert criteria_replan.replan_unassigned_criteria(
        state, phase,
    ) is True

    record = criteria_replan.active_criteria_replan(phase)
    assert record is not None
    assert record["status"] == "roles_pending"
    assert record["parent_goal"].startswith("OP-398")
    assert "OP-398" not in record["planner_goal"]
    assert "AC2: Second" in record["planner_goal"]
    assert len(record["planner_goal"]) < 5_000
    assert state.criteria_replan_id == record["replan_id"]
    assert state.aufgabe == record["planner_goal"]
    assert phase.data["tasks"][0]["status"] == "done"
    assert "plan_candidate_checkpoint" not in phase.data


def test_checkpoint_replan_candidate_is_gated_before_append(tmp_path, monkeypatch):
    phase = PhaseState("demo", base_dir=tmp_path)
    phase.init_new(
        "Goal",
        [{"id": "first", "action": "read", "criterion_refs": ["AC1"]}],
        tests=["pytest"],
        akzeptanzkriterien=["First", "Second"],
    )
    phase.data["setup_complete"] = True
    phase.data["plan_complete"] = True
    phase.bind_approved_plan()
    phase.mark_done("first")
    state = RunState(
        project_dir=tmp_path,
        project_name="demo",
        run_id="run-checkpoint-criteria-candidate",
        aufgabe="Goal",
        tasks=list(phase.data["tasks"]),
        tests=list(phase.data["tests"]),
        akzeptanzkriterien=list(phase.data["akzeptanzkriterien"]),
    )
    phase.run_id = state.run_id
    assert criteria_replan.replan_unassigned_criteria(
        state, phase,
    ) is True
    record = criteria_replan.active_criteria_replan(phase)
    assert record is not None

    state.tasks = [{
        "id": "second",
        "name": "Complete second criterion",
        "description": "Implement and verify the second criterion.",
        "action": "update",
        "task_files": ["src/two.py"],
        "dependencies": [],
        "criterion_refs": ["AC1"],
        "phase_id": None,
        "parent_id": None,
    }]
    state.tests = ["pytest tests/test_two.py"]
    state.akzeptanzkriterien = ["Second"]
    state.architect_prosa = "Bounded replan candidate."
    digest = criteria_replan.store_criteria_replan_candidate(
        state, phase, run_id=state.run_id,
    )
    criteria_replan.restore_criteria_replan_parent(state, phase)
    assert [task["id"] for task in phase.data["tasks"]] == ["first"]
    assert criteria_replan.active_criteria_replan(phase)["candidate_sha256"] == digest

    from werkstatt import gates

    gates_called = []
    monkeypatch.setattr(gates, "_plan_gate", lambda _state: True)
    monkeypatch.setattr(
        gates, "_human_gate_plan",
        lambda _state, kontext="": gates_called.append(kontext) or 0,
    )
    monkeypatch.setattr(
        "werkstatt.audit.audit", lambda *_args, **_kwargs: True,
    )

    assert criteria_replan.apply_criteria_replan_candidate(
        state, phase, record["replan_id"],
    ) is True
    assert gates_called == ["criteria_replan"]
    assert next(task["id"] for task in phase.data["tasks"]) == "first"
    assert phase.data["tasks"][1]["id"].endswith("_second")
    assert phase.data["tasks"][1]["criterion_refs"] == ["AC2"]
    assert phase.data["criteria_replans"][0]["status"] == "applied"


def test_checkpoint_candidate_rejects_planner_that_changes_criteria(
    tmp_path, monkeypatch,
):
    phase = PhaseState("demo", base_dir=tmp_path)
    phase.init_new(
        "Goal",
        [{"id": "existing", "criterion_refs": ["AC1"], "action": "read"}],
        akzeptanzkriterien=["First criterion", "Second criterion"],
    )
    phase.mark_done("existing")
    state = RunState(
        project_dir=tmp_path,
        project_name="demo",
        run_id="run-criteria-change",
        aufgabe="Goal",
        api_key="test-key",
        budget={"max_llm_calls": 20},
    )
    phase.run_id = state.run_id
    assert criteria_replan.replan_unassigned_criteria(state, phase) is True
    state.tasks = [{
        "id": "repair",
        "name": "Repair",
        "description": "Repair second criterion.",
        "action": "update",
        "task_files": ["src/two.py"],
        "dependencies": [],
        "criterion_refs": ["AC1"],
    }]
    state.akzeptanzkriterien = ["Rewritten second criterion"]
    with pytest.raises(ValueError, match="freigegebene Kriterien veraendert"):
        criteria_replan.store_criteria_replan_candidate(
            state, phase, run_id=state.run_id,
        )
    assert [task["id"] for task in phase.data["tasks"]] == ["existing"]
    assert phase.data["criteria_replans"][0]["status"] == "roles_pending"


def test_failed_criterion_replan_preserves_history_until_candidate_approval(
    tmp_path,
):
    phase = PhaseState("demo", base_dir=tmp_path)
    phase.init_new(
        "Goal",
        [
            {
                "id": "done",
                "name": "Completed first criterion",
                "action": "read",
                "criterion_refs": ["AC1"],
            },
            {
                "id": "failed",
                "name": "Failed second criterion",
                "action": "update",
                "criterion_refs": ["AC2"],
            },
        ],
        tests=["pytest tests/test_first.py"],
        akzeptanzkriterien=["First criterion", "Second criterion"],
    )
    phase.data["setup_complete"] = True
    phase.data["plan_complete"] = True
    phase.bind_approved_plan()
    phase.mark_done("done")
    phase.mark_failed(
        "failed", failure="builder_failed",
        detail="pytest tests/test_two.py failed: assertion expected 2, got 1",
    )
    state = RunState(
        project_dir=tmp_path,
        project_name="demo",
        run_id="run-failed-criteria",
        aufgabe="Goal",
        api_key="test-key",
        tasks=list(phase.data["tasks"]),
        tests=list(phase.data["tests"]),
        akzeptanzkriterien=list(phase.data["akzeptanzkriterien"]),
        budget={"max_llm_calls": 20},
    )
    phase.run_id = state.run_id
    assert criteria_replan.replan_unassigned_criteria(state, phase) is True
    record = criteria_replan.active_criteria_replan(phase)
    assert record is not None
    assert record["status"] == "roles_pending"
    assert record["mode"] == "failed_criteria_recovery"
    assert record["replaced_task_ids"] == ["failed"]
    assert "AC2: Second criterion" in record["planner_goal"]
    assert "pytest tests/test_two.py failed" in record["planner_goal"]
    assert "untrusted Daten" in record["planner_goal"]
    assert "OP-398" not in record["planner_goal"]
    failed = phase.get_task("failed")
    assert failed["status"] == "failed"
    assert failed["failure"] == "builder_failed"
    assert len(phase.data["tasks"]) == 2


def test_checkpoint_replan_combines_failed_and_unassigned_criteria(
    tmp_path, monkeypatch,
):
    phase = PhaseState("demo", base_dir=tmp_path)
    phase.init_new(
        "Goal",
        [
            {"id": "done", "action": "read", "criterion_refs": ["AC1"]},
            {"id": "failed", "action": "update", "criterion_refs": ["AC2"]},
        ],
        akzeptanzkriterien=["First", "Second", "Third"],
    )
    phase.mark_done("done")
    phase.mark_failed(
        "failed", failure="builder_failed", detail="First recovery exhausted",
    )
    state = RunState(
        project_dir=tmp_path,
        project_name="demo",
        run_id="run-mixed-criteria-gap",
        aufgabe="Goal",
        api_key="test-key",
        tasks=list(phase.data["tasks"]),
        akzeptanzkriterien=list(phase.data["akzeptanzkriterien"]),
        budget={"max_llm_calls": 20},
    )

    phase.run_id = state.run_id

    assert criteria_replan.replan_unassigned_criteria(state, phase) is True
    record = criteria_replan.active_criteria_replan(phase)
    assert record is not None
    assert record["mode"] == "failed_and_unassigned_criteria"
    assert record["criteria_refs"] == ["AC2", "AC3"]
    assert record["criteria_texts"] == ["Second", "Third"]
    assert record["replaced_task_ids"] == ["failed"]
    assert phase.get_task("failed")["status"] == "failed"
    assert [task["id"] for task in phase.data["tasks"]] == ["done", "failed"]


def test_replan_recovers_append_before_ledger_update_for_failed_task(
    tmp_path, monkeypatch,
):
    phase = PhaseState("demo", base_dir=tmp_path)
    phase.init_new(
        "Goal",
        [{"id": "failed", "criterion_refs": ["AC1"], "action": "update"}],
        akzeptanzkriterien=["Criterion"],
    )
    phase.mark_failed("failed", failure="builder_failed")
    phase.data["criteria_replans"] = [{
        "replan_id": "criteria-replan-recovery",
        "status": "planning",
        "mode": "failed_criteria_recovery",
        "replaced_task_ids": ["failed"],
    }]
    phase.data["tasks"].append({
        "id": "replacement",
        "status": "pending",
        "criterion_refs": ["AC1"],
        "source_followup_id": "criteria-replan-recovery",
    })
    phase.save()
    state = RunState(
        project_dir=tmp_path,
        project_name="demo",
        run_id="run-failed-replan-resume",
        aufgabe="Goal",
    )
    assert criteria_replan.replan_unassigned_criteria(state, phase) is True
    assert phase.get_task("failed")["status"] == "superseded"
    assert phase.data["criteria_replans"][0]["status"] == "applied_after_resume"
    assert [task["id"] for task in state.tasks] == ["failed", "replacement"]
