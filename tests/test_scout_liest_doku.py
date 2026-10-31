"""Phase 5c — Scout liest priorisierte Projekt-Doku (PROJEKT-DOKU-Sektion)."""
from __future__ import annotations
from pathlib import Path

SCOUT = Path("/opt/werkstatt/werkstatt/scout.py")


def test_scout_hat_projekt_doku_sektion():
    src = SCOUT.read_text(encoding="utf-8")
    assert "## PROJEKT-DOKU" in src
    assert "_DOCS_PRIO" in src
    assert "max 4000" in src.lower() or "[:4000]" in src


def test_scout_prioritaet_reihenfolge():
    src = SCOUT.read_text(encoding="utf-8")
    prio_start = src.find("_DOCS_PRIO =")
    assert prio_start > 0
    prio_str = src[prio_start:prio_start + 200]
    assert '"entry"' in prio_str
    assert '"status"' in prio_str
    assert '"roadmap"' in prio_str
    # entry muss vor status stehen
    assert prio_str.find('"entry"') < prio_str.find('"status"')
    assert prio_str.find('"status"') < prio_str.find('"roadmap"')


def test_scout_status_vor_conventions():
    src = SCOUT.read_text(encoding="utf-8")
    prio_start = src.find("_DOCS_PRIO =")
    prio_str = src[prio_start:prio_start + 200]
    assert prio_str.find('"status"') < prio_str.find('"conventions"')
