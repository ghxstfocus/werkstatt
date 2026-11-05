"""Tests fuer tools/state_drift.py (OP-136b)."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parent.parent))
sys.path.insert(0, str(_HERE.parent.parent / "tools"))

from state_drift import check_drift


def test_check_drift_heute_gruen():
    """Realer Repo-Zustand ist drift-frei."""
    result = check_drift()
    assert result["ok"] is True
    assert result["fehlende_properties"] == []
    assert result["unbekannte_transitions"] == []
    assert result["fehlende_transitions"] == []


def test_check_erkennt_fehlende_property():
    """CONTRACTS-Key ohne @property auf RunState -> Drift."""
    from werkstatt import state_contracts as sc
    fake = sc.Contract(typ="X", schreiber=[], leser=[])
    patched = {**sc.CONTRACTS, "fake_contract": fake}
    with patch("state_drift.CONTRACTS", patched):
        result = check_drift()
    assert not result["ok"]
    assert "fake_contract" in result["fehlende_properties"]


def test_check_erkennt_unbekannten_transition_contract():
    """TRANSITIONS-Feld ohne CONTRACTS-Key -> Drift."""
    from werkstatt import state_contracts as sc
    patched = {**sc.TRANSITIONS, "fake->fake": [("fake_contract", True)]}
    with patch("state_drift.TRANSITIONS", patched):
        result = check_drift()
    assert not result["ok"]
    assert "fake_contract" in result["unbekannte_transitions"]


def test_check_erkennt_fehlenden_transitions_eintrag():
    """CONTRACTS-Key weder in TRANSITIONS noch transition_frei -> Drift."""
    from werkstatt import state_contracts as sc
    fake = sc.Contract(typ="X", schreiber=[], leser=[])
    patched_contracts = {**sc.CONTRACTS, "fake_contract": fake}
    fake_props = set(sc.CONTRACTS.keys()) | {"fake_contract"}
    with patch("state_drift.CONTRACTS", patched_contracts), \
         patch("state_drift._properties_auf_runstate",
               return_value=fake_props):
        result = check_drift()
    assert not result["ok"]
    assert "fake_contract" in result["fehlende_transitions"]


def test_check_erlaubt_transition_frei():
    """CONTRACTS-Key mit transition_frei=True -> kein Drift."""
    from werkstatt import state_contracts as sc
    fake = sc.Contract(typ="X", schreiber=[], leser=[],
                       transition_frei=True)
    patched_contracts = {**sc.CONTRACTS, "fake_contract": fake}
    fake_props = set(sc.CONTRACTS.keys()) | {"fake_contract"}
    with patch("state_drift.CONTRACTS", patched_contracts), \
         patch("state_drift._properties_auf_runstate",
               return_value=fake_props):
        result = check_drift()
    assert "fake_contract" not in result["fehlende_transitions"]
