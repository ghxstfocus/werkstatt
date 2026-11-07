"""OP-168: Human-Gate vor Phase-Review-Loop-Abbruch.

Loop-Test-4 (2026-11-05): nach 3 Runden Phase-Review-Reject ohne
Gate -> LOOP FEHLGESCHLAGEN mit 8 Files dirty. User hatte keine
Wahl zwischen "behalten" und "verwerfen".
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, "/opt/werkstatt")

from werkstatt.loop import _phase_end_reflection
from werkstatt.phases import _phase_review_gate
from werkstatt.state import RunState

_here = Path(__file__).parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))
from factories import mk_state  # noqa: E402


def _mk_state() -> RunState:
    """Spec-State fuer Phase-Review-Gate (OP-174 P3).

    Vollstaendiger RunState ueber mk_state(). Alle Felder in
    RunState deklariert. Keine Sub-States.
    """
    return mk_state(project_dir="/tmp", project_name="test")


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


# =====================================================================
# OP-168b: _phase_end_reflection Integration (2 Smoke-Tests)
# =====================================================================

def _mk_state_phase_end(tmp_path):
    """State fuer _phase_end_reflection-Tests.

    Vollstaendiger RunState via mk_state, mit reviewer_bugs und
    patches vorbelegt, damit _phase_end_reflection eine Reject-
    Runde durchlaeuft und das Gate danach feuert.
    """
    return mk_state(
        project_dir=tmp_path,
        project_name="test",
        reviewer_bugs=[{"file": "a.py", "description": "x",
                        "severity": "high"}],
        patches=[{"file": "a.py"}],
    )


def test_reflection_reject_ruft_gate(tmp_path):
    """OP-168b AK (a): Reject-Runde -> _phase_review_gate wird gerufen.

    Spec: nach einer Reject-Runde MUSS der Mensch gefragt werden.
    Vor OP-168b liefen alle Runden stumm durch, erst am Ende kam
    ein Gate. Loop-Test-4 (2026-11-05) zeigte 3 Runden ohne
    Eingriff.
    """
    gate_calls: list[int] = []

    def _gate_spy(state):
        gate_calls.append(1)
        return 0  # j-Antwort

    s = _mk_state_phase_end(tmp_path)
    with patch("werkstatt.loop.run_builder", return_value=True), \
         patch("werkstatt.loop._apply_patches_with_hooks", return_value=1), \
         patch("werkstatt.loop._verify_patches", return_value=True), \
         patch("werkstatt.reviewer.run_phase_end_review", return_value=False), \
         patch("werkstatt.phases.review._phase_review_gate",
               side_effect=_gate_spy):
        assert _phase_end_reflection(s) is False
    assert len(gate_calls) >= 1, (
        f"Gate wurde {len(gate_calls)}x gerufen, erwartet >= 1"
    )


def test_gate_n_bricht_reflection_ab(tmp_path):
    """OP-168b AK (b): Gate liefert 1 (n) -> _phase_end_reflection
    returns False, KEINE weitere Builder-Runde.

    Spec: 'n' am Gate muss den Loop sofort beenden, nicht erst
    nach max Runden. Sonst kann der User nicht eingreifen.
    """
    gate_calls: list[int] = []
    builder_calls: list[int] = []

    def _gate_spy(state):
        gate_calls.append(1)
        return 1  # n-Antwort

    def _builder_spy(state):
        builder_calls.append(1)
        return True

    s = _mk_state_phase_end(tmp_path)
    with patch("werkstatt.loop.run_builder", side_effect=_builder_spy), \
         patch("werkstatt.loop._apply_patches_with_hooks", return_value=1), \
         patch("werkstatt.loop._verify_patches", return_value=True), \
         patch("werkstatt.reviewer.run_phase_end_review", return_value=False), \
         patch("werkstatt.phases.review._phase_review_gate",
               side_effect=_gate_spy):
        assert _phase_end_reflection(s) is False
    assert len(gate_calls) == 1, (
        f"Gate wurde {len(gate_calls)}x gerufen, erwartet 1"
    )
    assert len(builder_calls) == 1, (
        f"Builder wurde {len(builder_calls)}x gerufen, erwartet 1 "
        f"(keine 2. Runde nach 'n')"
    )
