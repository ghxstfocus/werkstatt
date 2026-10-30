"""Spec: Builder isoliert negative Anweisungen aus der Prosa."""
from __future__ import annotations
import sys
sys.path.insert(0, "/opt/werkstatt")
import pytest
from werkstatt.builder import _extrahiere_verbote


class TestVerboteExtraktion:
    def test_nicht_umnummerieren(self) -> None:
        p = "Es wird also nur der Textblock entfernt, nicht umnummeriert."
        out = _extrahiere_verbote(p)
        assert "<verbote" in out
        assert "nicht umnummeriert" in out

    def test_nur_datei(self) -> None:
        p = "Nur docs/STATUS.md aendern, keine Python-Datei anfassen."
        out = _extrahiere_verbote(p)
        assert "<verbote" in out
        assert "Nur docs/STATUS.md" in out or "keine Python" in out

    def test_behalte_abschnitt(self) -> None:
        p = "Behalte den Abschnitt Offene Punkte vollstaendig."
        out = _extrahiere_verbote(p)
        assert "<verbote" in out
        assert "Behalte" in out

    def test_keine_verbote_leer(self) -> None:
        p = "Baue eine neue Funktion die Events verarbeitet."
        out = _extrahiere_verbote(p)
        assert out == ""

    def test_leere_prosa(self) -> None:
        assert _extrahiere_verbote("") == ""
