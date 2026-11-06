"""A-B1-2 (2026-10-18): Tests fuer tools/audit.py.

Drei synthetische Faelle:
  T-audit-1: Callback in Argument-Position -> lebendig.
  T-audit-2: Feld via s. gelesen -> lebendig.
  T-audit-3: echte tote Funktion -> tot.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

TOOLS = Path("/opt/werkstatt/tools")
sys.path.insert(0, str(TOOLS))
from unittest.mock import MagicMock, patch

import audit as audit_mod
from werkstatt.gates import _human_gate_plan
from werkstatt.phases import (
    _gate_failed_payload,
    _reviewer_rejected_payload,
)


def test_audit_erkennt_callback_als_argument() -> None:
    """T-audit-1: ast.Name in Argument-Position."""
    quelle = """
def aufrufer():
    builder_reply_mit_command_loop(api_key, prompt, callback_fn)

def callback_fn(state):
    return "x"
"""
    tree = ast.parse(quelle)
    fns = audit_mod._funktionen(tree)
    aufrufe = audit_mod._aufrufe_in(fns["aufrufer"])
    assert "callback_fn" in aufrufe, (
        f"callback_fn nicht in {aufrufe}")


def test_audit_erkennt_s_praefix() -> None:
    """T-audit-2: s.FELD wird als state-Feld erkannt."""
    quelle = """
def leser(s):
    x = s.letzte_reviewer_antwort
    return x
"""
    tree = ast.parse(quelle)
    _schreibt, liest = audit_mod._state_zugriffe(tree)
    assert "letzte_reviewer_antwort" in liest, (
        f"Feld nicht in liest: {liest}")


def test_audit_erkennt_tote_funktion() -> None:
    """T-audit-3: nirgends referenzierte Funktion ist tot."""
    quelle = """
def lebendig():
    tot_helfer()

def tot_helfer():
    return 1
"""
    tree = ast.parse(quelle)
    tot = audit_mod._tote_funktionen(tree)
    assert "tot_helfer" not in tot, (
        f"tot_helfer faelschlich in {tot}")
    # Gegenprobe: eine Funktion, die nichts ruft.
    quelle2 = """
def nie_gerufen():
    return 1
"""
    tree2 = ast.parse(quelle2)
    tot2 = audit_mod._tote_funktionen(tree2)
    assert "nie_gerufen" in tot2


def test_loop_reviewer_rejected_hat_bugs_und_task_id() -> None:
    """Reviewer-Reject-Payload enthaelt task_id und normalisierte bugs."""
    reviewer_result = {
        "bugs": [
            {"severity": "high", "description": "fehlt"},
            {"severity": "low", "beschreibung": "alt"},
        ]
    }
    payload = _reviewer_rejected_payload("t1", reviewer_result)
    assert payload["task_id"] == "t1"
    assert len(payload["bugs"]) == 2
    for bug in payload["bugs"]:
        assert set(bug.keys()) == {"severity", "description"}
    assert payload["bugs"][1]["description"] == "alt"

    assert set(payload.keys()) == {"task_id", "bugs"}


def test_loop_plan_gate_rejected_hat_grund() -> None:
    """Plan-Gate-Reject ruft audit mit grund nach Grund-Erfassung."""
    import os
    state = MagicMock()
    state.project_dir = Path("/tmp/fake-project")
    state.project_name = "testprojekt"
    state.geplante_tasks = [{"id": "t1", "beschreibung": "x"}]
    # WERKSTATT_IN_TEST=1 triggert sonst Early-Return 0 in _human_gate_plan.
    with patch.dict(os.environ, {"WERKSTATT_IN_TEST": "0"}), \
            patch("werkstatt.gates.audit") as mock_audit, \
            patch("builtins.input") as mock_input:
        mock_input.side_effect = ["n", "zu vage"]
        rc = _human_gate_plan(state, auto_approve=False)
    assert rc != 0
    args, _kw = mock_audit.call_args_list[-1]
    assert args[0] == "loop_plan_gate_rejected"
    assert args[1] == {"grund": "zu vage"}


def test_loop_gate_failed_hat_gate_und_fehler() -> None:
    """Gate-Failed-Payload enthaelt gate, fehler und phase."""
    payload = _gate_failed_payload(
        "verify", ["py_compile failed", "ruff E501"], phase="p1")
    assert payload["gate"] == "verify"
    assert payload["fehler"] == ["py_compile failed", "ruff E501"]
    assert payload["phase"] == "p1"

    assert set(payload.keys()) == {"gate", "fehler", "phase"}
