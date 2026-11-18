"""werkstatt.control — Inventar und Drift-Pruefung der Kontrollen.

Die Registry ist kein Ablauf- oder Phasen-Runner. Checkpoint-Entscheidungen
werden vom zielorientierten Run-Koordinator getroffen.

Public API:
    from werkstatt.control import (
        Control,
        CONTROL_REGISTRY, run_control,
        check_drift, list_controls,
    )
"""
from werkstatt.control.control import Control
from werkstatt.control.drift import check_drift
from werkstatt.control.registry import CONTROL_REGISTRY, list_controls
from werkstatt.control.runner import run_control

__all__ = [
    "CONTROL_REGISTRY",
    "Control",
    "check_drift",
    "list_controls",
    "run_control",
]
