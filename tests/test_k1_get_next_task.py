"""K1: get_next_task filtert pending/running; split_task idempotent."""
from pathlib import Path

from werkstatt.phase_state import PhaseState


def _ps(tmp_path, tasks):
    ps = PhaseState("k1", base_dir=tmp_path / ".werkstatt")
    ps.init_new("aufgabe", tasks)
    return ps


def test_get_next_task_ueberspringt_failed(tmp_path: Path) -> None:
    ps = _ps(tmp_path, [{"id": "t1"}, {"id": "t2"}, {"id": "t3"}])
    ps.mark_failed("t1", failure="x")
    assert ps.get_next_task()["id"] == "t2"


def test_get_next_task_liefert_pending(tmp_path: Path) -> None:
    ps = _ps(tmp_path, [{"id": "t1"}])
    assert ps.get_next_task()["id"] == "t1"


def test_get_next_task_liefert_running(tmp_path: Path) -> None:
    ps = _ps(tmp_path, [{"id": "t1"}])
    ps.mark_running("t1")
    assert ps.get_next_task()["id"] == "t1"


def test_get_next_task_alle_done(tmp_path: Path) -> None:
    ps = _ps(tmp_path, [{"id": "t1"}])
    ps.mark_done("t1")
    assert ps.get_next_task() is None


def test_get_next_task_alle_failed(tmp_path: Path) -> None:
    ps = _ps(tmp_path, [{"id": "t1"}])
    ps.mark_failed("t1", failure="x")
    assert ps.get_next_task() is None


