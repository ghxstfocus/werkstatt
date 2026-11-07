"""OP-178: Rollen-Registry-Migration — Aufrufer nutzen ROLLEN[name].

Spec: Jede Rolle mit nicht-leeren `skills` oder gesetztem
`skill_filter_rolle` MUSS im Code einen ROLLEN["<name>"]-Zugriff
haben. Sonst ist die Registry Doku, nicht Enforcement.

Ausnahmen (fail-closed ohne Registry-Lookup):
- architect: skills=() — Pilot aus ADR-0014, laedt trotzdem
  ROLLEN["architect"] fuer fail-loud-Check (0 Skills erwartet)
- scout: skills=() — laedt nur Metadata, nie Bodies

Wenn eine neue Rolle mit skills/filter_rolle dazukommt, wird der
Test rot, bis der Aufrufer migriert ist.
"""
from __future__ import annotations

import ast
import pathlib
import sys

sys.path.insert(0, "/opt/werkstatt")


def _finde_rollen_zugriffe() -> set[str]:
    """AST-Scan: welche ROLLEN["<name>"]-Subscripts gibt es in werkstatt/?"""
    gesehen: set[str] = set()
    root = pathlib.Path("/opt/werkstatt/werkstatt")
    for py in root.rglob("*.py"):
        if "__pycache__" in str(py):
            continue
        try:
            tree = ast.parse(py.read_text())
        except Exception:  # noqa: S112
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Subscript):
                continue
            if not isinstance(node.value, ast.Name):
                continue
            if node.value.id != "ROLLEN":
                continue
            sl = node.slice
            if isinstance(sl, ast.Constant) and isinstance(sl.value, str):
                gesehen.add(sl.value)
    return gesehen


def test_alle_aktiven_rollen_haben_registry_zugriff():
    """Jede Rolle mit skills oder filter_rolle nutzt ROLLEN[name]."""
    from werkstatt.rollen import ROLLEN

    zugriffe = _finde_rollen_zugriffe()
    fehlend = []
    for name, rolle in ROLLEN.items():
        braucht = bool(rolle.skills) or bool(rolle.skill_filter_rolle)
        if not braucht:
            continue
        if name not in zugriffe:
            fehlend.append(name)

    assert not fehlend, (
        f"Rollen ohne ROLLEN[...]-Zugriff im Code: {fehlend}. "
        f"Gefundene Zugriffe: {sorted(zugriffe)}"
    )


def test_architect_hat_registry_zugriff_fuer_fail_loud():
    """Architect-Pilot: ROLLEN["architect"] fuer 0-Skill-Check (ADR-0014)."""
    zugriffe = _finde_rollen_zugriffe()
    assert "architect" in zugriffe, (
        "architect.py muss ROLLEN['architect'] nutzen (fail-loud, M-446)"
    )


def test_scout_ist_ausnahme_ohne_registry_zugriff():
    """Scout hat keine Skills, laedt nur Metadata — keine Registry noetig.

    Wenn hier spaeter ein ROLLEN["scout"] auftaucht, ist das kein
    Fehler — aber dann sollte scout.skills auch nicht-leer sein.
    """
    from werkstatt.rollen import ROLLEN

    rolle = ROLLEN["scout"]
    assert rolle.skills == (), "scout.skills sollte leer bleiben"
    assert rolle.skill_filter_rolle is None
