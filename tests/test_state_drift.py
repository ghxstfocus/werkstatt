"""Tests fuer tools/state_drift.py (OP-136b, OP-141-Vorarbeit)."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parent.parent))
sys.path.insert(0, str(_HERE.parent.parent / "tools"))

from state_drift import check_drift


def test_check_heute_gruen():
    """Realer Repo-Zustand ist drift-frei."""
    result = check_drift()
    assert result["ok"] is True
    assert result["unbekannte_felder"] == []
    assert result["fehlende_uebergaenge"] == []
    assert result["n_transitions"] == 5


def test_check_erkennt_unbekanntes_feld():
    """TRANSITIONS-Feld, das nicht in RunState deklariert ist -> Drift."""
    from werkstatt import state_contracts as sc
    patched = {**sc.TRANSITIONS,
               "fake->fake": [("voellig_erfundenes_feld", True)]}
    with patch("state_drift.TRANSITIONS", patched):
        result = check_drift()
    assert not result["ok"]
    assert "voellig_erfundenes_feld" in result["unbekannte_felder"]


def test_check_erkennt_fehlenden_uebergang():
    """Wenn ein erwarteter Uebergang fehlt -> Drift."""
    from werkstatt import state_contracts as sc
    patched = {k: v for k, v in sc.TRANSITIONS.items()
               if k != "planner->builder"}
    with patch("state_drift.TRANSITIONS", patched):
        result = check_drift()
    assert not result["ok"]
    assert "planner->builder" in result["fehlende_uebergaenge"]
