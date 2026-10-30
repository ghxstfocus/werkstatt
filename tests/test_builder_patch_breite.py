"""Spec: Patch-Breiten-Check fuer Doku-Loeschungen (Fix J 2026-10-31)."""
from __future__ import annotations
import sys
sys.path.insert(0, "/opt/werkstatt")
import pytest
from werkstatt.builder import _pruefe_doku_patch_breite


def _patch(old, new=""):
    return {"action": "update", "file": "docs/STATUS.md",
            "old_string": old, "new_string": new}


class TestPatchBreite:
    def test_zwei_punkte_geloescht_wird_verworfen(self) -> None:
        aufgabe = "Punkt 1 entfernen, aber Punkte 2-7 nicht umnummerieren."
        old = "1. Erster Punkt\n   Zeile\n\n2. Zweiter Punkt\n   Mehr"
        r = _pruefe_doku_patch_breite([_patch(old)], aufgabe,
                                       "docs/STATUS.md", None, "t")
        assert r == []

    def test_ein_punkt_geloescht_bleibt(self) -> None:
        aufgabe = "Punkt 1 entfernen, nicht umnummerieren."
        old = "1. Erster Punkt\n   Zeile A\n   Zeile B"
        r = _pruefe_doku_patch_breite([_patch(old)], aufgabe,
                                       "docs/STATUS.md", None, "t")
        assert len(r) == 1

    def test_update_patch_bleibt(self) -> None:
        aufgabe = "Punkt 1 entfernen, nicht umnummerieren."
        r = _pruefe_doku_patch_breite([_patch("1. Alt", "1. Neu")],
                                       aufgabe, "docs/STATUS.md", None, "t")
        assert len(r) == 1

    def test_ohne_negativ_marker_keine_filterung(self) -> None:
        aufgabe = "Entferne Punkte 1-3 komplett."
        old = "1. A\n\n2. B\n\n3. C"
        r = _pruefe_doku_patch_breite([_patch(old)], aufgabe,
                                       "docs/STATUS.md", None, "t")
        assert len(r) == 1

    def test_behalte_trigger(self) -> None:
        aufgabe = "Behalte die bestehende Nummerierung."
        r = _pruefe_doku_patch_breite([_patch("1. A\n\n2. B")], aufgabe,
                                       "docs/STATUS.md", None, "t")
        assert r == []
