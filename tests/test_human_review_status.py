"""OP-060b: human_review-Status."""
from __future__ import annotations
from pathlib import Path

from werkstatt.phase_state import PhaseState
from werkstatt.task_runner import _task_ende


def test_mark_human_review_setzt_status(tmp_path: Path) -> None:
    ps = PhaseState("p", base_dir=tmp_path)
    ps.data["tasks"] = [{"id": "t1", "name": "T1", "status": "pending"}]
    ps.mark_human_review("t1", grund="spec_widerspruch")
    t = ps.get_task("t1")
    assert t["status"] == "human_review"
    assert t.get("failure") == "spec_widerspruch"


def test_task_ende_human_review(tmp_path: Path) -> None:
    """_task_ende(human_review=True) setzt Status, kein PROGRESS-Eintrag."""
    from types import SimpleNamespace
    (tmp_path / ".werkstatt").mkdir()
    progress = tmp_path / "PROGRESS.md"
    progress.write_text("# Fortschritt\n", encoding="utf-8")

    s = SimpleNamespace()
    s.project_dir = tmp_path
    s.project_name = "p"
    s.aufgabe = "ohne OP"
    s.tasks_ok_counter = 0

    ps = PhaseState("p", base_dir=tmp_path)
    ps.data["tasks"] = [{"id": "t1", "name": "T1", "status": "pending"}]

    _task_ende(s, ps, "t1", ok=False, name="T1",
               human_review=True, failure="spec_widerspruch")

    t = ps.get_task("t1")
    assert t["status"] == "human_review"
    assert t.get("failure") == "spec_widerspruch"


def test_phase_state_propagate_ignoriert_human_review(tmp_path: Path) -> None:
    """_propagate_failed_to_parents: human_review-Kinder sind kein fail."""
    ps = PhaseState("p", base_dir=tmp_path)
    ps.data["tasks"] = [
        {"id": "t1", "status": "split", "parent_id": None},
        {"id": "t1_a", "status": "human_review", "parent_id": "t1"},
        {"id": "t1_b", "status": "failed", "parent_id": "t1"},
    ]
    ps._propagate_failed_to_parents("t1_b")
    parent = ps.get_task("t1")
    # Parent darf NICHT failed sein, weil t1_a human_review ist
    assert parent["status"] != "failed", (
        "Parent wurde faelschlich failed markiert trotz human_review-Kind"
    )
