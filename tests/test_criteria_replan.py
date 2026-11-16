import pytest

from werkstatt import criteria_replan
from werkstatt.phase_state import PhaseState
from werkstatt.state import RunState


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
    phase.mark_done("existing")
    state = RunState(
        project_dir=tmp_path,
        project_name="demo",
        run_id="run-criteria-gap",
        aufgabe="Goal",
        api_key="test-key",
        tasks=list(phase.data["tasks"]),
        tests=list(phase.data["tests"]),
        akzeptanzkriterien=list(phase.data["akzeptanzkriterien"]),
        budget={"max_llm_calls": 20},
    )

    def fake_planner(addition):
        assert "AC2: Second criterion" in addition.aufgabe
        addition.tasks = [{
            "id": "repair-second",
            "name": "Complete second criterion",
            "description": "Implement and verify the second criterion.",
            "action": "update",
            "task_files": ["src/two.py"],
            "dependencies": [],
            "criterion_refs": ["AC1"],
            "phase_id": None,
            "parent_id": None,
        }]
        addition.tests = ["pytest tests/test_two.py"]
        addition.akzeptanzkriterien = ["Second criterion"]
        addition.phasen = []
        addition.architect_prosa = "Only the second criterion is planned."
        addition.llm_calls += 2
        return True

    monkeypatch.setattr("werkstatt.planner.run_planner", fake_planner)
    monkeypatch.setattr("werkstatt.gates._plan_gate", lambda _state: True)
    monkeypatch.setattr(
        "werkstatt.gates._human_gate_plan",
        lambda _state, kontext="": 0,
    )
    monkeypatch.setattr(criteria_replan, "audit", lambda *args, **kwargs: True, raising=False)

    assert criteria_replan.replan_unassigned_criteria(state, phase) is True

    existing = phase.get_task("existing")
    assert existing["status"] == "done"
    assert existing["criterion_refs"] == ["AC1"]
    additions = [
        task for task in phase.data["tasks"]
        if task.get("source_followup_id", "").startswith("criteria-replan-")
    ]
    assert len(additions) == 1
    assert additions[0]["status"] == "pending"
    assert additions[0]["criterion_refs"] == ["AC2"]
    assert phase.data["akzeptanzkriterien"] == [
        "First criterion", "Second criterion",
    ]
    assert phase.criteria_progress()["valid"] is True
    assert phase.criteria_progress()["uncovered"] == ["AC2"]
    assert phase.data["criteria_replans"][0]["status"] == "applied"
    assert state.llm_calls == 2


def test_replan_rejects_planner_that_changes_original_criteria(
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
    gate_calls = []

    def fake_planner(addition):
        addition.akzeptanzkriterien = ["Rewritten second criterion"]
        addition.tasks = [{
            "id": "repair",
            "name": "Repair",
            "description": "Repair changed requirement.",
            "action": "update",
            "task_files": ["src/two.py"],
            "dependencies": [],
            "criterion_refs": ["AC1"],
        }]
        return True

    monkeypatch.setattr("werkstatt.planner.run_planner", fake_planner)
    monkeypatch.setattr("werkstatt.gates._plan_gate", lambda _state: True)
    monkeypatch.setattr(
        "werkstatt.gates._human_gate_plan",
        lambda *_args, **_kwargs: gate_calls.append(True) or 0,
    )

    assert criteria_replan.replan_unassigned_criteria(state, phase) is False
    assert [task["id"] for task in phase.data["tasks"]] == ["existing"]
    assert phase.data["criteria_replans"][0]["status"] == "failed"
    assert gate_calls == []


def test_replans_failed_criterion_after_recovery_and_supersedes_history(
    tmp_path, monkeypatch,
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

    def fake_planner(addition):
        assert "AC2: Second criterion" in addition.aufgabe
        assert "pytest tests/test_two.py failed" in addition.aufgabe
        assert "Failed second criterion" in addition.aufgabe
        assert "AC1" not in addition.aufgabe.split("Fehlgeschlagene Task-Belege", 1)[1]
        addition.tasks = [{
            "id": "replacement",
            "name": "Repair second criterion",
            "description": "Implement and verify the second criterion.",
            "action": "update",
            "task_files": ["src/two.py"],
            "dependencies": [],
            "criterion_refs": ["AC1"],
            "phase_id": None,
            "parent_id": None,
        }]
        addition.tests = ["pytest tests/test_two.py"]
        addition.akzeptanzkriterien = ["Second criterion"]
        addition.phasen = []
        addition.architect_prosa = "Targeted recovery plan."
        return True

    monkeypatch.setattr("werkstatt.planner.run_planner", fake_planner)
    monkeypatch.setattr("werkstatt.gates._plan_gate", lambda _state: True)
    monkeypatch.setattr(
        "werkstatt.gates._human_gate_plan",
        lambda _state, kontext="": 0,
    )

    assert criteria_replan.replan_unassigned_criteria(state, phase) is True

    failed = phase.get_task("failed")
    assert failed["status"] == "superseded"
    assert failed["failure"] == "builder_failed"
    assert failed["superseded_failure"] == "builder_failed"
    assert failed["superseded_by_replan_id"].startswith("criteria-replan-")
    replacement = next(
        task for task in phase.data["tasks"]
        if task.get("source_followup_id")
    )
    assert replacement["criterion_refs"] == ["AC2"]
    assert phase.criteria_progress()["valid"] is True
    assert phase.criteria_progress()["uncovered"] == ["AC2"]
    assert phase.progress() == {
        "total": 2,
        "done": 1,
        "failed": 0,
        "blocked": 0,
        "pending": 1,
    }


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
    monkeypatch.setattr("werkstatt.planner.run_planner", lambda _state: pytest.fail())

    assert criteria_replan.replan_unassigned_criteria(state, phase) is True
    assert phase.get_task("failed")["status"] == "superseded"
    assert phase.data["criteria_replans"][0]["status"] == "applied_after_resume"
    assert [task["id"] for task in state.tasks] == ["failed", "replacement"]
