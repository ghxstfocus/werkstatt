"""Tests fuer werkstatt/phase_state.py (Phase 13)."""
from __future__ import annotations

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
