"""OP-163: Planner-Dependencies werden durchgesetzt.

Tasks mit unerfuellten `dependencies` werden uebersprungen und
am Loop-Ende als `blocked` markiert.
"""
from __future__ import annotations

from werkstatt.phase_state import PhaseState


def test_task_mit_unerfuellten_deps_wird_skipped(tmp_path):
    """(a) t1 (pending, dep=t2) + t2 (failed) -> t1 wird
    uebersprungen und als blocked markiert.
    """
    ps = PhaseState("test", base_dir=tmp_path)
    ps.data = {
        "tasks": [
            {"id": "t1", "status": "pending", "dependencies": ["t2"]},
            {"id": "t2", "status": "failed", "dependencies": []},
        ],
    }
    assert ps.get_next_task() is None

    _t1 = [t for t in ps.data["tasks"] if t["id"] == "t1"][0]
    assert ps._unmet_dependencies(_t1) == ["t2"]

    ps.mark_blocked("t1", grund="deps:t2")
    _t1 = [t for t in ps.data["tasks"] if t["id"] == "t1"][0]
    assert _t1["status"] == "blocked"
    assert _t1["failure"].startswith("blocked:")


def test_task_nach_erfuellter_dep_laeuft(tmp_path):
    """(b) t1 (pending, dep=t2) + t2 (done) -> t1 wird ausgefuehrt."""
    ps = PhaseState("test", base_dir=tmp_path)
    ps.data = {
        "tasks": [
            {"id": "t1", "status": "pending", "dependencies": ["t2"]},
            {"id": "t2", "status": "done", "dependencies": []},
        ],
    }
    nt = ps.get_next_task()
    assert nt is not None
    assert nt["id"] == "t1"
