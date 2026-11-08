"""Kleine Mathematik-Hilfsfunktionen.

Eigenstaendiges Utility-Modul ohne Abhaengigkeiten zu anderen
Werkstatt-Modulen.
"""

from __future__ import annotations

__all__ = ["add"]


def add(a: int, b: int) -> int:
    """Gibt die Summe zweier Ganzzahlen zurueck."""
    return a + b
