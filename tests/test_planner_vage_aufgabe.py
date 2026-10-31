"""Phase 5e — Vage Aufgaben: STATUS.md als primaere Quelle."""
from __future__ import annotations
from pathlib import Path

PLANNER = Path("/opt/werkstatt/werkstatt/planner.py")


def test_vage_keywords_in_planner():
    src = PLANNER.read_text(encoding="utf-8")
    for kw in ("aufraeumen", "naechster", "was ist zu tun"):
        assert kw in src, f"Vage-Keyword fehlt: {kw}"


def test_status_als_primaere_quelle_marker():
    src = PLANNER.read_text(encoding="utf-8")
    assert "PRIMAERE AUFGABENQUELLE" in src
    assert "_ist_vage_task" in src
