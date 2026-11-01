"""OP-064f: verdict-Semantik konsistent (pending|verified|vetoed).

Ziel: phase.yaml wird zur strukturierten Feature-List.
- init_new: jeder Task startet mit verdict="pending"
- mark_done (normal): verdict="verified"
- mark_vetoed: verdict="vetoed" (existiert)
- mark_done (Veto-Override durch Mensch): verdict="verified"

Vorher: verdict=None bei normal-done, "verified" nur bei Override.
Semantisch invertiert zur Intuition.
"""
from __future__ import annotations

from pathlib import Path

from werkstatt.phase_state import PhaseState


def _mk(tmp_path: Path) -> PhaseState:
    (tmp_path / ".werkstatt").mkdir(exist_ok=True)
    ps = PhaseState("p", base_dir=tmp_path / ".werkstatt")
    ps.init_new(
        aufgabe="a",
        tasks=[
            {"id": "t1", "name": "T1"},
            {"id": "t2", "name": "T2"},
        ],
        tests=["test_x"],
        akzeptanzkriterien=["akz"],
    )
    return ps


def test_init_new_setzt_verdict_pending(tmp_path: Path) -> None:
    """Neue Tasks starten mit verdict='pending' (nicht None)."""
    ps = _mk(tmp_path)
    for t in ps.data["tasks"]:
        assert t.get("verdict") == "pending", (
            f"Task {t.get('id')}: verdict={t.get('verdict')!r}, "
            f"erwartet 'pending'"
        )


def test_mark_done_setzt_verdict_verified(tmp_path: Path) -> None:
    """Normales mark_done: verdict wechselt von pending zu verified."""
    ps = _mk(tmp_path)
    ps.mark_done("t1")
    t = ps.get_task("t1")
    assert t.get("status") == "done"
    assert t.get("verdict") == "verified", (
        f"verdict={t.get('verdict')!r}, erwartet 'verified'"
    )


def test_mark_done_hebt_veto_auf_verified(tmp_path: Path) -> None:
    """Mensch-Override: vetoed -> verified (Verhalten aus OP-064a bleibt)."""
    ps = _mk(tmp_path)
    ps.mark_vetoed("t1", grund="spec_widerspruch_vermutet")
    assert ps.get_task("t1").get("verdict") == "vetoed"
    ps.mark_done("t1")
    assert ps.get_task("t1").get("verdict") == "verified"


def test_mark_vetoed_setzt_vetoed(tmp_path: Path) -> None:
    """mark_vetoed setzt verdict='vetoed' (Regression, Verhalten bleibt)."""
    ps = _mk(tmp_path)
    ps.mark_vetoed("t2", grund="antipattern:type_ignore")
    assert ps.get_task("t2").get("verdict") == "vetoed"


def test_mark_failed_laesst_verdict_unberuehrt(tmp_path: Path) -> None:
    """mark_failed veraendert verdict NICHT (bleibt pending).

    Rationale: failed ist Status, verdict ist Feature-Listen-Aussage.
    Ein fehlgeschlagener Task ist nicht 'verified' und nicht 'vetoed'
    durch einen deterministischen Guard — er ist einfach nicht fertig.
    """
    ps = _mk(tmp_path)
    ps.mark_failed("t1", failure="builder_failed")
    t = ps.get_task("t1")
    assert t.get("status") == "failed"
    assert t.get("verdict") == "pending", (
        f"verdict={t.get('verdict')!r}, erwartet 'pending' (unveraendert)"
    )
