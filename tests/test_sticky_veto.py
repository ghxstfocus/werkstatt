"""OP-064a: Sticky-Veto — einmal vetoed, nur Mensch setzt zurueck.

Live-Beleg Testrunde 3 (18:54 OP-004): spec_widerspruch_erkannt wurde
gesetzt, aber _phase_tasks_loop's Erfolgs-Pfad (_refl_ok=True) hat es
ignoriert. Reviewer Runde 2 approved, task_ok, obwohl Diff # type: ignore
enthielt.

Sticky-Veto: deterministische Signale setzen vetoed, LLM-Approval kann
es nicht aufheben. Nur mark_human_review/mark_done durch Mensch.
"""
from __future__ import annotations

import sys
from pathlib import Path

from werkstatt.phase_state import PhaseState
from werkstatt.task_runner import _task_ende

_here = Path(__file__).parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))
from factories import mk_state  # noqa: E402


def _mk_ps(tmp_path: Path) -> PhaseState:
    (tmp_path / ".werkstatt").mkdir(exist_ok=True)
    ps = PhaseState("p", base_dir=tmp_path / ".werkstatt")
    ps.data["tasks"] = [
        {"id": "t1", "name": "T1", "status": "running"},
    ]
    ps.save()
    return ps


def test_mark_vetoed_setzt_verdict(tmp_path: Path) -> None:
    ps = _mk_ps(tmp_path)
    ps.mark_vetoed("t1", grund="spec_widerspruch_vermutet")
    t = ps.get_task("t1")
    assert t.get("verdict") == "vetoed"
    assert t.get("failure") == "spec_widerspruch_vermutet"


def test_ist_vetoed(tmp_path: Path) -> None:
    ps = _mk_ps(tmp_path)
    assert ps.ist_vetoed("t1") is False
    ps.mark_vetoed("t1", grund="x")
    assert ps.ist_vetoed("t1") is True


def test_task_ende_respektiert_veto(tmp_path: Path) -> None:
    """ok=True, aber vetoed -> mark_human_review statt mark_done."""
    (tmp_path / ".werkstatt").mkdir(exist_ok=True)
    (tmp_path / "PROGRESS.md").write_text("# Fortschritt\n", encoding="utf-8")

    s = mk_state(
        project_dir=tmp_path,
        project_name="p",
        aufgabe="ohne OP",
        tasks_ok_counter=0,
    )

    ps = _mk_ps(tmp_path)
    ps.mark_vetoed("t1", grund="spec_widerspruch_vermutet")

    _audits: list[str] = []
    import werkstatt.task_runner as tr
    _orig_audit = tr.audit
    tr.audit = lambda k, p, *a, **kw: _audits.append(k)
    try:
        _task_ende(s, ps, "t1", ok=True, name="T1")
    finally:
        tr.audit = _orig_audit

    t = ps.get_task("t1")
    assert t.get("status") == "human_review", (
        f"Veto ignoriert, status={t.get('status')}"
    )
    assert "loop_task_veto_respected" in _audits
