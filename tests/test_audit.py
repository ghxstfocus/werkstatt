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
import audit as audit_mod


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
    schreibt, liest = audit_mod._state_zugriffe(tree)
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
