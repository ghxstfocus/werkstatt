"""OP-166: last_verify_errors + reviewer_bugs pro Task zurueck.

Loop-Test-4 (2026-11-05): t7-Reflection sah 5 Runden lang dieselben
2 Fehler aus t2 (gates.py), konnte sie nicht loesen (Zieldatei
tests/test_gates.py != gates.py). 0 Patches pro Runde.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "/opt/werkstatt")

from werkstatt.phases import _reset_task_state

_here = Path(__file__).parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))
from factories import mk_state  # noqa: E402


def test_reset_clears_last_verify_errors():
    st = mk_state()
    st.last_verify_errors = ["gates.py:419:high", "gates.py:632:medium"]
    _reset_task_state(st)
    assert st.last_verify_errors == []


def test_reset_clears_reviewer_bugs():
    st = mk_state()
    st.reviewer_bugs = [{"severity": "high", "description": "old"}]
    _reset_task_state(st)
    assert st.reviewer_bugs == []


def test_zwei_task_isolation():
    """task1 fail mit Fehlern -> task2 start sieht sauberen State."""
    st = mk_state()
    # task1 Reflection endet mit Fehlern
    st.last_verify_errors = ["task1:gates.py:419"]
    st.reviewer_bugs = [{"severity": "high", "description": "task1_bug"}]
    # task2 start
    _reset_task_state(st)
    assert st.last_verify_errors == []
    assert st.reviewer_bugs == []
    # task2 eigene Fehler
    st.last_verify_errors.append("task2:test_gates.py:bar")
    assert st.last_verify_errors == ["task2:test_gates.py:bar"]


def test_reset_crasht_nicht_bei_fehlenden_feldern():
    """Fail-soft: wenn state die Felder nicht hat, kein Fehler.

    OP-174 P3: mk_state() setzt last_verify_errors + reviewer_bugs
    (RunState-Defaults). Um fehlendes Feld zu simulieren, entfernen
    wir beide Attribute nach mk_state(). _reset_task_state muss
    robust sein (try/except).
    """
    st = mk_state()
    delattr(st, "last_verify_errors")
    delattr(st, "reviewer_bugs")
    _reset_task_state(st)
    assert st.last_verify_errors == []
    assert st.reviewer_bugs == []
