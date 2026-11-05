"""Smoke-Tests für tools/state_inventory.py (OP-134).

Prüfen die Parser-Korrektheit gegen bekannte Messbefunde der
Session 2026-11-04. Wenn diese Tests brechen, hat sich die
RunState-Struktur geändert — Baseline in tools/state_inventory.py
muss dann mit dokumentiertem Grund nachgezogen werden.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
import state_inventory


def test_findet_bekannte_felder_und_kategorien():
    erg = state_inventory.kategorisiere()
    # OP-135b: explorer_context ist jetzt deklariert, wird aber nur via
    # getattr gelesen → write_only. Nach OP-137 (Architect liest direkt)
    # wird daraus "aktiv". Dann hier auf "aktiv" umstellen.
    assert erg["explorer_context"]["kategorie"] == "aktiv"  # OP-161
    # api_index_cache: wird geschrieben, aber nur via getattr gelesen
    # → write_only. Widerlegt Handoff-Satz "toter Cache" (er lebt!),
    # aber auch frühere Behauptung "aktiv" (kein direkter Leser).
    assert erg["api_index_cache"]["kategorie"] == "write_only"
    # api_key ist getattr_only (nicht tot — Korrektur an früherer Messung)
    assert erg["api_key"]["kategorie"] == "getattr_only"
    # tasks ist aktiv (wird geschrieben und gelesen)
    assert erg["tasks"]["kategorie"] == "aktiv"


def test_solver_altlast_ist_tot():
    erg = state_inventory.kategorisiere()
    # Solver-Felder sind Altlasten (User-Entscheidung 2026-11-04)
    assert erg["solver_model"]["kategorie"] == "tot"
    assert erg["solver_befunde"]["kategorie"] == "tot"
    assert erg["solver_aufrufe"]["kategorie"] == "tot"


def test_baseline_ist_konsistent():
    erg = state_inventory.kategorisiere()
    assert state_inventory.check_baseline(erg) == 0
