"""OP-059d: verify-Fehler-Wiederholung als Spec-Widerspruch-Signal."""
from __future__ import annotations

from werkstatt.reflection import (
    _bug_text_deutet_spec_widerspruch,
    _verify_fehler_wiederholt_sich,
)


def test_bug_text_marker_erkannt() -> None:
    bugs = [{"severity": "high",
             "description": "Task-Beschreibung fordert X. Der Diff macht Y."}]
    assert _bug_text_deutet_spec_widerspruch(bugs) is True


def test_bug_text_generisch_kein_marker() -> None:
    bugs = [{"severity": "high", "description": "fake bug"}]
    assert _bug_text_deutet_spec_widerspruch(bugs) is False


def test_verify_fehler_wiederholt_sich() -> None:
    e = "mypy_changed: x.py:80: error: Unsupported operand types"
    assert _verify_fehler_wiederholt_sich([e, e]) is True


def test_verify_fehler_verschieden() -> None:
    e1 = "mypy_changed: x.py:80: error: Unsupported"
    e2 = "mypy_changed: x.py:80: error: Other problem"
    assert _verify_fehler_wiederholt_sich([e1, e2]) is False


def test_verify_fehler_leer() -> None:
    assert _verify_fehler_wiederholt_sich([]) is False
