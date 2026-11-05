"""werkstatt.control — zentrale Registry aller Loop-Kontrollen.

Ziel: eine Datei zeigt, welche Kontrollen es gibt, in welcher Phase sie
laufen und wo sie implementiert sind. Bestehender Code bleibt vorerst
unveraendert — die Registry ist Single Source of Truth fuer Inventar
und Drift-Check.

Public API:
    from werkstatt.control import (
        Control, Phase,
        CONTROL_REGISTRY, run_control, run_phase,
        check_drift, list_controls,
    )
"""
from werkstatt.control.control import Control
from werkstatt.control.drift import check_drift
from werkstatt.control.phases import Phase
from werkstatt.control.registry import CONTROL_REGISTRY, list_controls
from werkstatt.control.runner import run_control, run_phase

__all__ = [
    "Control", "Phase",
    "CONTROL_REGISTRY", "list_controls",
    "run_control", "run_phase",
    "check_drift",
]
