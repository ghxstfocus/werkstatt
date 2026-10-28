"""K38: Kind failed -> Parent failed (rekursiv)."""
from pathlib import Path

from werkstatt.phase_state import PhaseState


def _mk(tmp_path: Path, tasks: list) -> PhaseState:
    ps = PhaseState("p", base_dir=tmp_path)
    ps.init_new(
        "aufgabe", tasks,
        tests=[], akzeptanzkriterien=[], phasen=[],
    )
    return ps


def test_alle_kinder_failed_parent_failed(tmp_path):
    ps = _mk(tmp_path, [
        {"id": "t2", "name": "parent", "task_files": []},
    ])
    # Manuell: Kinder hinzufuegen
    ps.data["tasks"].extend([
        {"id": "t2_a", "name": "kind1", "parent_id": "t2", "status": "failed"},
        {"id": "t2_b", "name": "kind2", "parent_id": "t2", "status": "failed"},
    ])
    ps.save()
    ps.mark_failed("t2_a", failure="test")
    ps.mark_failed("t2_b", failure="test")
    # Nach zweitem: alle Kinder failed -> Parent failed.
    parent = next(t for t in ps.data["tasks"] if t["id"] == "t2")
    assert parent["status"] == "failed"
    assert parent["failure"] == "kinder_failed"


def test_nicht_alle_failed_parent_split(tmp_path):
    ps = _mk(tmp_path, [
        {"id": "t2", "name": "parent", "task_files": []},
    ])
    ps.data["tasks"].extend([
        {"id": "t2_a", "name": "kind1", "parent_id": "t2", "status": "pending"},
        {"id": "t2_b", "name": "kind2", "parent_id": "t2", "status": "pending"},
    ])
    ps.save()
    ps.mark_failed("t2_a", failure="test")
    parent = next(t for t in ps.data["tasks"] if t["id"] == "t2")
    # t2_b noch pending -> Parent bleibt unveraendert.
    assert parent["status"] != "failed"


def test_rekursiv_bis_root(tmp_path):
    ps = _mk(tmp_path, [
        {"id": "t1", "name": "root", "task_files": []},
    ])
    ps.data["tasks"].extend([
        {"id": "t1_a", "name": "p1", "parent_id": "t1", "status": "pending"},
        {"id": "t1_a_a", "name": "kind", "parent_id": "t1_a", "status": "pending"},
    ])
    ps.save()
    ps.mark_failed("t1_a_a", failure="test")
    t1_a = next(t for t in ps.data["tasks"] if t["id"] == "t1_a")
    t1 = next(t for t in ps.data["tasks"] if t["id"] == "t1")
    assert t1_a["status"] == "failed"
    assert t1["status"] == "failed"
