"""Tests fuer werkstatt/phase_state.py (Phase 13)."""
from __future__ import annotations

import json

import pytest

from werkstatt.phase_state import PhaseState


def test_init_new_und_load(tmp_path):
    ps = PhaseState("testprojekt", base_dir=tmp_path)
    assert not ps.exists()
    ps.init_new("Aufgabe X", [{"id": "t1", "name": "Task 1"}])
    assert ps.exists()
    assert ps.data["project"] == "testprojekt"
    assert len(ps.data["tasks"]) == 1
    # Load in neuer Instanz
    ps2 = PhaseState("testprojekt", base_dir=tmp_path)
    assert ps2.load() is True
    assert ps2.data["tasks"][0]["status"] == "pending"


def test_plan_candidate_roundtrip_binds_goal_run_and_preflight_evidence(
    tmp_path,
):
    phase = PhaseState("demo", base_dir=tmp_path)
    phase.run_id = "run-1"
    digest = phase.record_plan_candidate(
        goal="Implement AC1",
        run_id="run-1",
        tasks=[{"id": "t1", "criterion_refs": ["AC1"]}],
        tests=["pytest -q"],
        criteria=["AC1"],
        phases=[],
        architect_prose="Scoped plan",
        preflight_findings=[{"klasse": "test", "datei": "tests/test_old.py"}],
    )

    resumed = PhaseState("demo", base_dir=tmp_path)
    assert resumed.load()
    candidate = resumed.load_plan_candidate(goal="Implement AC1", run_id="run-1")
    assert candidate is not None
    assert candidate["preflight_findings"] == [{
        "klasse": "test", "datei": "tests/test_old.py",
    }]
    assert resumed.plan_candidate_is_approved(
        goal="Implement AC1", run_id="run-1",
    ) is False
    assert resumed.load_plan_candidate(goal="Different goal", run_id="run-1") is None
    assert resumed.load_plan_candidate(goal="Implement AC1", run_id="other-run") is None

    record = resumed.data["plan_candidate_checkpoint"]
    record["payload"]["preflight_findings"][0]["klasse"] = "changed"
    assert resumed.load_plan_candidate(goal="Implement AC1", run_id="run-1") is None
    assert record["candidate_sha256"] == digest


def test_preflight_checkpoint_roundtrip_rejects_tampering_and_resets_old_role(
    tmp_path,
):
    phase = PhaseState("demo", base_dir=tmp_path)
    phase.run_id = "old-run"
    phase.data["planner_role_stage"] = "architect"
    phase.data["planner_role_goal_sha256"] = "old-goal-hash"
    findings = [{"klasse": "test", "datei": "tests/test_api.py"}]
    phase.record_preflight_checkpoint(
        goal="Current goal", run_id="new-run", findings=findings,
    )
    assert "planner_role_stage" not in phase.data

    resumed = PhaseState("demo", base_dir=tmp_path)
    assert resumed.load()
    assert resumed.load_preflight_checkpoint(
        goal="Current goal", run_id="new-run",
    ) == findings
    record = resumed.data["preflight_checkpoint"]
    record["payload"]["findings"][0]["klasse"] = "changed"
    assert resumed.load_preflight_checkpoint(
        goal="Current goal", run_id="new-run",
    ) is None


def test_task_review_checkpoint_is_bound_to_current_verify_and_source(tmp_path):
    source = tmp_path / "src" / "feature.py"
    source.parent.mkdir()
    source.write_text("value = 1\n", encoding="utf-8")
    phase = PhaseState("demo", base_dir=tmp_path / ".werkstatt")
    phase.init_new(
        "Update feature",
        [{
            "id": "t1", "name": "Update feature", "action": "update",
            "task_files": ["src/feature.py"], "criterion_refs": ["AC1"],
        }],
        akzeptanzkriterien=["feature updated"],
    )
    phase.run_id = "review-run"
    phase.mark_running("t1")
    assert phase.record_task_verify_evidence(
        "t1",
        [{
            "stage_id": "pytest", "ok": True, "exit_code": 0,
            "scope_files": ["src/feature.py"],
        }],
        phase="post_build",
    )

    assert phase.record_task_review_checkpoint(
        "t1", verify_warnings=["bounded warning"],
    )
    assert phase.task_review_checkpoint_is_current("t1")
    assert phase.data["tasks"][0]["review_checkpoint"]["verify_warnings"] == [
        "bounded warning",
    ]

    source.write_text("value = 2\n", encoding="utf-8")
    assert not phase.task_review_checkpoint_is_current("t1")


def test_task_build_checkpoint_schedules_separate_verify_action(tmp_path):
    source = tmp_path / "src" / "feature.py"
    source.parent.mkdir()
    source.write_text("value = 2\n", encoding="utf-8")
    phase = PhaseState("demo", base_dir=tmp_path / ".werkstatt")
    phase.init_new(
        "Update feature",
        [{
            "id": "t1", "name": "Update feature", "action": "update",
            "task_files": ["src/feature.py"], "criterion_refs": ["AC1"],
        }],
        akzeptanzkriterien=["feature updated"],
    )
    phase.run_id = "build-run"
    phase.mark_running("t1")

    assert phase.record_task_build_checkpoint("t1")
    assert phase.task_build_checkpoint_is_current("t1")
    next_task = phase.get_next_task()
    assert next_task is not None
    assert next_task["verification_only"] is True
    assert next_task["action"] == "verify"

    source.write_text("value = 3\n", encoding="utf-8")
    assert not phase.task_build_checkpoint_is_current("t1")

    phase.update_task("t1", "failed", failure="verify_failed")
    assert phase.get_task("t1").get("build_checkpoint") is None
    assert phase.get_task("t1").get("verification_pending") is None
    assert phase.get_next_task() is None


def test_verify_failure_checkpoint_is_hash_bound_and_selected_for_recovery(tmp_path):
    source = tmp_path / "src" / "feature.py"
    source.parent.mkdir()
    source.write_text("value = 2\n", encoding="utf-8")
    phase = PhaseState("demo", base_dir=tmp_path / ".werkstatt")
    phase.init_new(
        "Update feature",
        [{
            "id": "t1", "name": "Update feature", "action": "update",
            "task_files": ["src/feature.py"], "criterion_refs": ["AC1"],
        }],
        akzeptanzkriterien=["feature updated"],
    )
    phase.run_id = "verify-failure-run"
    phase.mark_running("t1")
    assert phase.record_task_build_checkpoint("t1")
    assert phase.record_task_verify_failure_checkpoint(
        "t1", ["ruff: E501 line too long"],
    )
    assert phase.task_verify_failure_checkpoint_is_current("t1")
    selected = phase.get_next_task()
    assert selected is not None
    assert selected["verify_recovery_only"] is True
    assert selected["verify_recovery_checkpoint_current"] is True

    source.write_text("value = 3\n", encoding="utf-8")
    assert not phase.task_verify_failure_checkpoint_is_current("t1")
    selected = phase.get_next_task()
    assert selected is not None
    assert selected["verify_recovery_only"] is True
    assert selected["verify_recovery_checkpoint_current"] is False

    phase.update_task("t1", "human_review", failure="stale")
    assert phase.get_task("t1").get("verify_failure_checkpoint") is None


def test_init_new_persistiert_criterion_refs_ueber_reload(tmp_path):
    ps = PhaseState("testprojekt", base_dir=tmp_path)
    ps.init_new(
        "Kriteriengebundener Plan",
        [{"id": "t1", "criterion_refs": ["AC1", "AC3"]}],
        akzeptanzkriterien=["Kriterium 1", "Kriterium 2", "Kriterium 3"],
    )

    assert ps.data["tasks"][0]["criterion_refs"] == ["AC1", "AC3"]

    resumed = PhaseState("testprojekt", base_dir=tmp_path)
    assert resumed.load() is True
    assert resumed.data["tasks"][0]["criterion_refs"] == ["AC1", "AC3"]


def test_approved_plan_fingerprint_binds_plan_but_allows_runtime_progress():
    phase = PhaseState("demo")
    phase.init_new(
        "Goal",
        [{
            "id": "t1",
            "name": "Edit source",
            "description": "Approved implementation",
            "action": "update",
            "task_files": ["src/main.py"],
            "criterion_refs": ["AC1"],
        }],
        tests=["pytest tests/test_main.py"],
        akzeptanzkriterien=["Expected behavior is implemented"],
    )
    original = phase.bind_approved_plan()
    assert phase.approved_plan_is_current()

    phase.mark_running("t1")
    assert phase.approved_plan_is_current()
    phase.data["tasks"][0]["description"] = "Changed after approval"
    assert not phase.approved_plan_is_current()
    assert phase.approved_plan_fingerprint() != original


def test_phase_end_review_checkpoint_is_bound_to_run_plan_and_worktree(
    tmp_path,
):
    phase = PhaseState("demo", base_dir=tmp_path)
    phase.run_id = "run-1"
    phase.init_new(
        "Goal",
        [{"id": "t1", "name": "Edit", "action": "update"}],
    )
    phase.bind_approved_plan()
    fingerprint = "a" * 64

    phase.record_phase_end_review(worktree_fingerprint=fingerprint)

    assert phase.phase_end_review_is_current(
        worktree_fingerprint=fingerprint,
    )
    assert not phase.phase_end_review_is_current(
        worktree_fingerprint="b" * 64,
    )

    phase.data["tasks"][0]["description"] = "Changed plan"
    assert not phase.phase_end_review_is_current(
        worktree_fingerprint=fingerprint,
    )


def test_human_gate_checkpoint_binds_commit_consent_to_run_plan_and_tree(
    tmp_path,
):
    phase = PhaseState("demo", base_dir=tmp_path)
    phase.run_id = "run-1"
    phase.init_new("Goal", [{"id": "t1", "name": "Edit"}])
    phase.bind_approved_plan()
    fingerprint = "b" * 64

    phase.record_human_gate(
        worktree_fingerprint=fingerprint,
        commit_requested=True,
    )

    assert phase.human_gate_is_current(worktree_fingerprint=fingerprint)
    assert phase.data["human_gate_checkpoint"]["commit_requested"] is True
    assert not phase.human_gate_is_current(worktree_fingerprint="c" * 64)
    phase.run_id = "other-run"
    assert not phase.human_gate_is_current(worktree_fingerprint=fingerprint)


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        (lambda phase: phase.data["tasks"][0].update(action="read"), False),
        (
            lambda phase: phase.data["tasks"][0].update(
                task_files=["src/other.py"],
            ),
            False,
        ),
        (
            lambda phase: phase.data["tasks"][0].update(
                dependencies=["t0"],
            ),
            False,
        ),
        (
            lambda phase: phase.data["tasks"][0].update(
                criterion_refs=["AC2"],
            ),
            False,
        ),
        (lambda phase: phase.data.update(tests=["pytest other_test.py"]), False),
        (
            lambda phase: phase.data.update(
                akzeptanzkriterien=["A different result is required"],
            ),
            False,
        ),
        (lambda phase: phase.data.update(phasen=[{"id": "p2"}]), False),
    ],
)
def test_approved_plan_fingerprint_rejects_changed_execution_inputs(
    tmp_path, mutation, expected,
):
    phase = PhaseState("demo", base_dir=tmp_path)
    phase.init_new(
        "Goal",
        [{
            "id": "t1",
            "name": "Edit source",
            "description": "Approved implementation",
            "action": "update",
            "task_files": ["src/main.py"],
            "dependencies": [],
            "criterion_refs": ["AC1"],
        }],
        tests=["pytest tests/test_main.py"],
        akzeptanzkriterien=["Expected behavior is implemented"],
    )
    phase.bind_approved_plan()

    mutation(phase)

    assert phase.approved_plan_is_current() is expected


def test_task_verify_evidence_is_persisted_and_bound_to_criteria(tmp_path):
    project_dir = tmp_path / "project"
    (project_dir / "src").mkdir(parents=True)
    source = project_dir / "src" / "main.py"
    source.write_text("value = 1\n", encoding="utf-8")
    ps = PhaseState("testprojekt", base_dir=project_dir / ".werkstatt")
    ps.run_id = "test-run"
    ps.init_new(
        "Kriterium mit Task-Verify-Beleg",
        [{"id": "t1", "task_files": ["src/main.py"],
          "criterion_refs": ["AC1"]}],
        akzeptanzkriterien=["Verhalten wird geprueft"],
    )

    assert ps.record_task_verify_evidence(
        "t1",
        [
            {
                "stage_id": "pytest_changed", "exit_code": 0, "ok": True,
                "scope_files": ["src/main.py"],
            },
            {
                "stage_id": "ruff_changed", "exit_code": 1, "ok": False,
                "scope_files": ["src/main.py"],
            },
            {"stage_id": "pytest_bad", "exit_code": False, "ok": True},
        ],
        phase="post_build",
    )

    resumed = PhaseState("testprojekt", base_dir=project_dir / ".werkstatt")
    assert resumed.load()
    evidence = resumed.get_task("t1")["verify_evidence"]
    assert evidence["criterion_refs"] == ["AC1"]
    assert evidence["task_files"] == ["src/main.py"]
    assert evidence["task_file_sha256"] == ps._task_file_hashes(
        ["src/main.py"],
    )
    assert evidence["stages"] == [{
        "stage_id": "pytest_changed", "exit_code": 0, "ok": True,
        "scope_files": ["src/main.py"],
    }]
    assert resumed.task_verify_evidence_is_current("t1", evidence)
    source.write_text("value = 2\n", encoding="utf-8")
    assert not resumed.task_verify_evidence_is_current("t1", evidence)


def test_task_verify_evidence_requires_a_successful_stage(tmp_path):
    project_dir = tmp_path / "project"
    (project_dir / "src").mkdir(parents=True)
    (project_dir / "src" / "main.py").write_text("x=1\n", encoding="utf-8")
    ps = PhaseState("testprojekt", base_dir=project_dir / ".werkstatt")
    ps.run_id = "test-run"
    ps.init_new(
        "Kriterium ohne erfolgreichen Stage",
        [{
            "id": "t1", "task_files": ["src/main.py"],
            "criterion_refs": ["AC1"],
        }],
        akzeptanzkriterien=["Verhalten wird geprueft"],
    )

    assert not ps.record_task_verify_evidence(
        "t1",
        [{
            "stage_id": "pytest_changed", "exit_code": 1, "ok": False,
            "scope_files": ["src/main.py"],
        }],
        phase="post_build",
    )
    assert "verify_evidence" not in ps.get_task("t1")


def test_task_verify_evidence_does_not_borrow_global_stage(tmp_path):
    project_dir = tmp_path / "project"
    (project_dir / "src").mkdir(parents=True)
    (project_dir / "src" / "main.py").write_text("x=1\n", encoding="utf-8")
    ps = PhaseState("testprojekt", base_dir=project_dir / ".werkstatt")
    ps.run_id = "test-run"
    ps.init_new(
        "Kriterium ohne taskbezogenen Stage",
        [{
            "id": "t1", "task_files": ["src/main.py"],
            "criterion_refs": ["AC1"],
        }],
        akzeptanzkriterien=["Verhalten wird geprueft"],
    )

    assert not ps.record_task_verify_evidence(
        "t1",
        [{"stage_id": "pytest_regression", "exit_code": 0, "ok": True}],
        phase="post_build",
    )
    assert "verify_evidence" not in ps.get_task("t1")


def test_stale_task_evidence_is_requeued_as_verify_only(tmp_path):
    project_dir = tmp_path / "project"
    (project_dir / "src").mkdir(parents=True)
    source = project_dir / "src" / "main.py"
    source.write_text("value = 1\n", encoding="utf-8")
    ps = PhaseState("testprojekt", base_dir=project_dir / ".werkstatt")
    ps.run_id = "test-run"
    ps.init_new(
        "Stale task evidence",
        [{
            "id": "t1", "action": "update", "task_files": ["src/main.py"],
            "criterion_refs": ["AC1"],
        }],
        akzeptanzkriterien=["Aktueller Inhalt ist verifiziert"],
    )
    assert ps.record_task_verify_evidence(
        "t1",
        [{
            "stage_id": "pytest_changed", "exit_code": 0, "ok": True,
            "scope_files": ["src/main.py"],
        }],
        phase="post_build",
    )
    ps.mark_done("t1")
    source.write_text("value = 2\n", encoding="utf-8")

    assert ps.queue_stale_task_reverification() == ["t1"]
    reverify = ps.get_next_task()
    assert reverify is not None
    assert reverify["id"] == "t1"
    assert reverify["action"] == "verify"
    assert reverify["verification_only"] is True

    ps.mark_running("t1")
    assert ps.record_task_verify_evidence(
        "t1",
        [{
            "stage_id": "pytest_changed", "exit_code": 0, "ok": True,
            "scope_files": ["src/main.py"],
        }],
        phase="post_build",
    )
    ps.mark_done("t1")
    assert ps.queue_stale_task_reverification() == []
    assert ps.task_verify_evidence_is_current(
        "t1", ps.get_task("t1")["verify_evidence"],
    )


def test_init_new_verwirft_ungueltige_criterion_refs(tmp_path):
    ps = PhaseState("testprojekt", base_dir=tmp_path)

    with pytest.raises(ValueError, match="criterion_refs"):
        ps.init_new("X", [{"id": "t1", "criterion_refs": ["AC1", 2]}])

    assert not ps.exists()


def test_phase_end_verify_failure_has_one_recovery_per_worktree(
    tmp_path, monkeypatch,
):
    from werkstatt import failure_record

    phase = PhaseState("demo", base_dir=tmp_path)
    phase.run_id = "verify-run"
    phase.init_new(
        "Complete goal",
        [{"id": "t1", "name": "Implement", "status": "done"}],
        akzeptanzkriterien=["AC1"],
    )
    phase.bind_approved_plan()
    fingerprint = {"value": "a" * 64}
    monkeypatch.setattr(
        failure_record, "_worktree_fingerprint",
        lambda _path: fingerprint["value"],
    )
    failed = {
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
        failed, project_dir=tmp_path,
    )
    assert phase.phase_end_verify_failure_is_current(project_dir=tmp_path)
    claimed = phase.claim_phase_end_verify_recovery(project_dir=tmp_path)
    assert claimed is not None
    assert claimed["status"] == "attempted"
    assert not phase.phase_end_verify_failure_is_current(project_dir=tmp_path)
    assert not phase.record_phase_end_verify_failure(
        {**failed, "failure_id": "failure-2"}, project_dir=tmp_path,
    )

    fingerprint["value"] = "b" * 64
    assert phase.record_phase_end_verify_failure(
        {
            **failed,
            "failure_id": "failure-3",
            "worktree_fingerprint": "b" * 64,
        },
        project_dir=tmp_path,
    )
    assert phase.phase_end_verify_failure_is_current(project_dir=tmp_path)
    assert phase.data["phase_end_verify_failure_checkpoint"][
        "attempted_worktree_sha256"
    ] == ["a" * 64]


def test_append_followup_tasks_persistiert_und_ist_idempotent(tmp_path):
    ps = PhaseState("testprojekt", base_dir=tmp_path)
    ps.run_id = "run-followup"
    ps.init_new("Hauptziel", [{"id": "t1"}], akzeptanzkriterien=["Basis"])
    ps.bind_approved_plan()
    fingerprint = "a" * 64
    ps.record_phase_end_review(worktree_fingerprint=fingerprint)
    ps.record_human_gate(
        worktree_fingerprint=fingerprint,
        commit_requested=True,
    )
    ps.record_phase_end_verify(
        worktree_fingerprint=fingerprint,
        evidence_sha256="b" * 64,
        stage_ids=["pytest_full"],
    )
    added = [{
        "id": "fu_task1",
        "name": "Zwischenauftrag",
        "dependencies": ["t1"],
        "criterion_refs": ["AC2"],
        "phase_id": "phase_fu",
    }]

    assert ps.append_followup_tasks(
        added,
        criteria=["Basis", "Folgekriterium"],
        tests=["pytest -q"],
        phases=[{"id": "phase_fu", "titel": "Follow-up", "tasks": ["fu_task1"]}],
        followup_id="proposal-1",
    ) == ["fu_task1"]
    assert ps.approved_plan_is_current()
    assert "phase_end_review_checkpoint" not in ps.data
    assert "human_gate_checkpoint" not in ps.data
    assert "phase_end_verify_checkpoint" not in ps.data
    assert ps.append_followup_tasks(
        added,
        criteria=["Basis", "Folgekriterium"],
        tests=["pytest -q"],
        phases=[{"id": "phase_fu", "titel": "Follow-up", "tasks": ["fu_task1"]}],
        followup_id="proposal-1",
    ) == ["fu_task1"]

    resumed = PhaseState("testprojekt", base_dir=tmp_path)
    assert resumed.load()
    assert [task["id"] for task in resumed.data["tasks"]] == ["t1", "fu_task1"]
    assert resumed.data["tasks"][1]["source_followup_id"] == "proposal-1"
    assert resumed.data["akzeptanzkriterien"] == ["Basis", "Folgekriterium"]
    assert resumed.data["tests"] == ["pytest -q"]
    assert resumed.data["phasen"] == [
        {"id": "phase_fu", "titel": "Follow-up", "tasks": ["fu_task1"]},
    ]
    assert resumed.approved_plan_is_current()


def test_append_followup_tasks_rejects_unknown_dependency_without_mutation(tmp_path):
    ps = PhaseState("testprojekt", base_dir=tmp_path)
    ps.init_new("Hauptziel", [{"id": "t1"}])

    with pytest.raises(ValueError, match="Abhaengigkeiten"):
        ps.append_followup_tasks(
            [{"id": "fu_task1", "dependencies": ["missing"]}],
            criteria=[],
            tests=[],
            phases=[],
            followup_id="proposal-1",
        )

    assert [task["id"] for task in ps.data["tasks"]] == ["t1"]


def test_resume_findet_naechsten_task(tmp_path):
    ps = PhaseState("testprojekt", base_dir=tmp_path)
    ps.init_new("X", [{"id": "t1"}, {"id": "t2"}, {"id": "t3"}])
    # t1 done
    ps.mark_done("t1")
    next_task = ps.get_next_task()
    assert next_task["id"] == "t2"
    # t2 done -> t3
    ps.mark_done("t2")
    assert ps.get_next_task()["id"] == "t3"


def test_resume_alle_done(tmp_path):
    ps = PhaseState("testprojekt", base_dir=tmp_path)
    ps.init_new("X", [{"id": "t1"}])
    ps.mark_done("t1")
    assert ps.get_next_task() is None
    assert ps.is_complete() is True


def test_failure_log(tmp_path):
    ps = PhaseState("testprojekt", base_dir=tmp_path)
    ps.init_new("X", [{"id": "t1"}])
    ps.mark_failed("t1", failure="pytest failed: 3 errors")
    task = ps.get_task("t1")
    assert task["status"] == "failed"
    assert "pytest failed" in task["failure"]


def test_decision_log(tmp_path):
    ps = PhaseState("testprojekt", base_dir=tmp_path)
    ps.init_new("X", [{"id": "t1"}])
    ps.mark_done("t1", decision="Ansatz A gewaehlt, weil B zu langsam")
    task = ps.get_task("t1")
    assert task["decision"] == "Ansatz A gewaehlt, weil B zu langsam"


def test_progress(tmp_path):
    ps = PhaseState("testprojekt", base_dir=tmp_path)
    ps.init_new("X", [{"id": "t1"}, {"id": "t2"}, {"id": "t3"}])
    ps.mark_done("t1")
    ps.mark_failed("t2", failure="x")
    p = ps.progress()
    assert p["total"] == 3
    assert p["done"] == 1
    assert p["failed"] == 1
    assert p["pending"] == 1


def test_progress_does_not_count_blocked_tasks_as_pending(tmp_path):
    ps = PhaseState("testprojekt", base_dir=tmp_path)
    ps.init_new("X", [{"id": "t1"}, {"id": "t2"}])
    ps.mark_done("t1")
    ps.mark_blocked("t2", grund="deps:missing")

    progress = ps.progress()

    assert progress["done"] == 1
    assert progress["pending"] == 0
    assert progress["blocked"] == 1


def test_superseded_failed_task_stays_in_history_but_not_active_progress(
    tmp_path,
):
    phase = PhaseState("testprojekt", base_dir=tmp_path)
    phase.init_new(
        "Repair",
        [
            {"id": "failed", "criterion_refs": ["AC1"]},
            {"id": "replacement", "criterion_refs": ["AC1"]},
        ],
        akzeptanzkriterien=["Criterion"],
    )
    phase.mark_failed("failed", failure="builder_failed")
    phase.mark_done("replacement")

    phase.supersede_failed_tasks(
        ["failed"], replan_id="criteria-replan-test",
    )

    assert phase.get_task("failed")["status"] == "superseded"
    assert phase.get_task("failed")["failure"] == "builder_failed"
    assert phase.criteria_progress()["valid"] is True
    assert phase.criteria_progress()["covered"] == ["AC1"]
    assert phase.progress() == {
        "total": 1,
        "done": 1,
        "failed": 0,
        "blocked": 0,
        "pending": 0,
    }
    assert phase.is_complete() is True


def test_resume_failed_setzt_pending(tmp_path):
    """M-310c: resume_failed macht failed -> pending."""
    ps = PhaseState("testprojekt", base_dir=tmp_path)
    ps.init_new("X", [{"id": "t1"}, {"id": "t2"}])
    ps.mark_failed("t1", failure="builder_failed")
    ps.mark_done("t2")
    n = ps.resume_failed()
    assert n == 1
    assert ps.get_task("t1")["status"] == "pending"
    assert ps.get_task("t1")["failure"] is None
    assert ps.get_task("t2")["status"] == "done"


def test_resume_failed_keine_failed_tasks(tmp_path):
    """M-310c: resume_failed ohne failed-Tasks -> 0."""
    ps = PhaseState("testprojekt", base_dir=tmp_path)
    ps.init_new("X", [{"id": "t1"}])
    ps.mark_done("t1")
    n = ps.resume_failed()
    assert n == 0


def test_resume_failed_can_preserve_terminal_failures_for_checkpoint_replan(
    tmp_path,
):
    ps = PhaseState("test", base_dir=tmp_path)
    ps.init_new("test", [{"id": "failed"}, {"id": "running"}])
    ps.mark_failed("failed", failure="builder_failed")
    ps.mark_running("running")

    assert ps.resume_failed(preserve_failed=True) == 1
    assert ps.get_task("failed")["status"] == "failed"
    assert ps.get_task("running")["status"] == "pending"


def test_resume_blocked_wird_nach_erfolgreicher_dependency_ausfuehrbar(tmp_path):
    """Blocked-Tasks werden beim Resume reaktiviert und koennen deps nachholen."""
    ps = PhaseState("testprojekt", base_dir=tmp_path)
    ps.data = {
        "tasks": [
            {"id": "t1", "status": "failed", "dependencies": []},
            {"id": "t2", "status": "blocked", "dependencies": ["t1"],
             "failure": "blocked: deps:t1"},
        ],
    }

    assert ps.resume_failed() == 2
    assert ps.get_task("t1")["status"] == "pending"
    assert ps.get_task("t2")["status"] == "pending"

    ps.mark_done("t1")
    assert ps.get_next_task()["id"] == "t2"


@pytest.mark.parametrize(
    "yaml_text",
    [
        "- not-a-mapping\n",
        "project: another-project\n",
        "tasks: invalid\n",
        "tasks:\n  - not-a-mapping\n",
        "tasks:\n  - id: [not, hashable]\n",
        "tasks:\n  - id: t1\n    dependencies: invalid\n",
        "tasks:\n  - id: t1\n    criterion_refs: invalid\n",
        "tasks:\n  - id: t1\n    criterion_refs: [AC1, 2]\n",
        "tasks:\n  - id: t1\n  - id: t1\n",
        "tasks:\n  - id: ''\n",
    ],
)
def test_load_verwirft_strukturell_ungueltigen_phase_state(
    tmp_path, yaml_text,
) -> None:
    ps = PhaseState("testprojekt", base_dir=tmp_path)
    ps.path.write_text(yaml_text, encoding="utf-8")

    assert ps.load() is False
    assert ps.data == {}


def test_load_normalisiert_fehlende_tasks_fuer_legacy_checkpoint(
    tmp_path,
) -> None:
    ps = PhaseState("testprojekt", base_dir=tmp_path)
    ps.path.write_text("project: testprojekt\n", encoding="utf-8")

    assert ps.load() is True
    assert ps.data.get("tasks", []) == []


def test_run_id_wird_im_phase_state_persistiert(tmp_path) -> None:
    ps = PhaseState("testprojekt", base_dir=tmp_path)
    ps.run_id = "testprojekt-run-1"
    ps.init_new("Run gebundener Checkpoint", [{"id": "t1"}])
    ps.save()

    loaded = PhaseState("testprojekt", base_dir=tmp_path)
    assert loaded.load() is True
    assert loaded.run_id == "testprojekt-run-1"


@pytest.mark.parametrize("run_id", ["", 123, ["run-a"]])
def test_load_verwirft_ungueltige_checkpoint_run_id(tmp_path, run_id) -> None:
    ps = PhaseState("testprojekt", base_dir=tmp_path)
    ps.path.write_text(
        f"project: testprojekt\nrun_id: {json.dumps(run_id)}\ntasks: []\n",
        encoding="utf-8",
    )

    assert ps.load() is False
    assert ps.data == {}



def test_criteria_progress_requires_done_task_for_each_criterion(tmp_path):
    ps = PhaseState("testprojekt", base_dir=tmp_path)
    ps.init_new(
        "Kriterienfortschritt",
        [
            {"id": "t1", "criterion_refs": ["AC1"]},
            {"id": "t2", "criterion_refs": ["AC2"]},
        ],
        akzeptanzkriterien=["Erstes Ziel", "Zweites Ziel"],
    )
    ps.mark_done("t1")

    progress = ps.criteria_progress()
    assert progress == {
        "tracked": True,
        "valid": True,
        "covered": ["AC1"],
        "uncovered": ["AC2"],
        "error": None,
    }

    ps.mark_done("t2")
    assert ps.criteria_progress()["uncovered"] == []
    assert ps.criteria_progress()["covered"] == ["AC1", "AC2"]


def test_criteria_progress_waits_for_all_tasks_sharing_split_criterion(tmp_path):
    ps = PhaseState("testprojekt", base_dir=tmp_path)
    ps.init_new(
        "Geteiltes Akzeptanzkriterium",
        [
            {"id": "t1_a", "criterion_refs": ["AC1"]},
            {"id": "t1_b", "criterion_refs": ["AC1"]},
        ],
        akzeptanzkriterien=["Gesamtziel des gesplitteten Tasks"],
    )
    ps.mark_done("t1_a")

    progress = ps.criteria_progress()
    assert progress["covered"] == []
    assert progress["uncovered"] == ["AC1"]

    ps.mark_done("t1_b")
    progress = ps.criteria_progress()
    assert progress["covered"] == ["AC1"]
    assert progress["uncovered"] == []


def test_plan_without_criteria_ignores_empty_ref_lists(tmp_path):
    ps = PhaseState("testprojekt", base_dir=tmp_path)
    ps.init_new(
        "Task ohne Zielkriterien",
        [{"id": "t1", "criterion_refs": []}],
    )

    assert ps.criteria_progress()["tracked"] is False


def test_legacy_checkpoint_with_empty_refs_is_untracked(tmp_path):
    ps = PhaseState("testprojekt", base_dir=tmp_path)
    ps.init_new(
        "Legacy checkpoint",
        [{"id": "t1"}],
        akzeptanzkriterien=["Altes Ziel"],
    )
    ps.data.pop("criteria_tracking")
    ps.save()

    resumed = PhaseState("testprojekt", base_dir=tmp_path)
    assert resumed.load() is True
    assert resumed.criteria_progress()["tracked"] is False


def test_invalid_criteria_tracking_marker_rejects_checkpoint(tmp_path):
    ps = PhaseState("testprojekt", base_dir=tmp_path)
    ps.path.write_text(
        "project: testprojekt\ncriteria_tracking: 'yes'\ntasks: []\n",
        encoding="utf-8",
    )

    assert ps.load() is False
    assert ps.data == {}


def test_null_criteria_tracking_marker_rejects_checkpoint(tmp_path):
    ps = PhaseState("testprojekt", base_dir=tmp_path)
    ps.path.write_text(
        "project: testprojekt\ncriteria_tracking: null\ntasks: []\n",
        encoding="utf-8",
    )

    assert ps.load() is False
    assert ps.data == {}


def test_checkpoint_cannot_disable_tracking_with_references(tmp_path):
    ps = PhaseState("testprojekt", base_dir=tmp_path)
    ps.path.write_text(
        "project: testprojekt\n"
        "criteria_tracking: false\n"
        "tasks:\n"
        "  - id: t1\n"
        "    criterion_refs: [AC1]\n",
        encoding="utf-8",
    )

    assert ps.load() is False
    assert ps.data == {}


def test_criteria_progress_rejects_unknown_reference(tmp_path):
    ps = PhaseState("testprojekt", base_dir=tmp_path)
    ps.init_new(
        "Ungueltige Kriterienreferenz",
        [{"id": "t1", "criterion_refs": ["AC2"]}],
        akzeptanzkriterien=["Ein Ziel"],
    )

    progress = ps.criteria_progress()
    assert progress["tracked"] is True
    assert progress["valid"] is False
    assert progress["error"] == "invalid_criterion_refs:t1"


def test_save_keeps_checkpoint_details_out_of_stderr(tmp_path, capsys) -> None:
    """Checkpoint-Saves duerfen keine Debug-Daten in Prozesslogs ausgeben."""
    state = PhaseState("testprojekt", base_dir=tmp_path)

    state.init_new("Aufgabe X", [{"id": "t1", "name": "Task 1"}])

    assert capsys.readouterr().err == ""



def test_init_new_rejects_duplicate_task_ids(tmp_path) -> None:
    ps = PhaseState("testprojekt", base_dir=tmp_path)

    with pytest.raises(ValueError, match="eindeutige"):
        ps.init_new("X", [{"id": "same"}, {"id": "same"}])

    assert not ps.exists()
