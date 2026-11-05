"""OP-168: Human-Gate vor Phase-Review-Loop-Abbruch.

Loop-Test-4 (2026-11-05): nach 3 Runden Phase-Review-Reject ohne
Gate -> LOOP FEHLGESCHLAGEN mit 8 Files dirty. User hatte keine
Wahl zwischen "behalten" und "verwerfen".
"""
from __future__ import annotations

import sys
from types import SimpleNamespace

sys.path.insert(0, "/opt/werkstatt")

from werkstatt.phases import _phase_review_gate


def _mk_state():
    s = SimpleNamespace()
    s.project_dir = "/tmp"
    s.project_name = "test"
    return s


def _mock_interactive(monkeypatch, antworten):
    """stdin als TTY markieren + input aus Antwortliste."""
    class _TTY:
        def isatty(self):
            return True
    monkeypatch.setattr(sys, "stdin", _TTY())
    it = iter(antworten)
    monkeypatch.setattr("builtins.input", lambda *a, **kw: next(it))


def _mock_non_interactive(monkeypatch):
    """stdin als non-TTY markieren (pytest-Standard)."""
    class _NoTTY:
        def isatty(self):
            return False
    monkeypatch.setattr(sys, "stdin", _NoTTY())


def test_j_gibt_0(monkeypatch):
    _mock_interactive(monkeypatch, ["j"])
    assert _phase_review_gate(_mk_state()) == 0


def test_n_gibt_1(monkeypatch):
    _mock_interactive(monkeypatch, ["n"])
    assert _phase_review_gate(_mk_state()) == 1


def test_grossbuchstabe_j(monkeypatch):
    _mock_interactive(monkeypatch, ["J"])
    assert _phase_review_gate(_mk_state()) == 0


def test_eof_gibt_1(monkeypatch):
    """TTY da, aber input wirft EOFError -> fail-closed."""
    class _TTY:
        def isatty(self):
            return True
    monkeypatch.setattr(sys, "stdin", _TTY())

    def _raise_eof(*a, **kw):
        raise EOFError
    monkeypatch.setattr("builtins.input", _raise_eof)
    assert _phase_review_gate(_mk_state()) == 1


def test_ungueltig_dann_j(monkeypatch):
    """Ungueltige Eingabe -> retry, dann j -> 0."""
    _mock_interactive(monkeypatch, ["x", "j"])
    assert _phase_review_gate(_mk_state()) == 0


def test_e_dann_n(monkeypatch):
    """'e' -> manuell, dann 'n' -> 1."""
    _mock_interactive(monkeypatch, ["e", "", "n"])
    assert _phase_review_gate(_mk_state()) == 1


def test_non_interactive_gibt_1(monkeypatch):
    """stdin nicht tty (pytest) -> fail-closed, kein input() (OSError-Schutz)."""
    _mock_non_interactive(monkeypatch)
    assert _phase_review_gate(_mk_state()) == 1
