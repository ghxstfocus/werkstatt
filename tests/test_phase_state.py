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
