"""State-Contract-Validierung (OP-136, vereinfacht OP-141-Vorarbeit).

Feld-basierte Validierung fuer Rollenwechsel: prueft pro
Transition, ob die als Pflicht markierten RunState-Felder
befuellt sind. Wirft ContractViolation bei Verstoss.

Nach OP-141-Vorarbeit (2026-11-05): keine Property-Views mehr,
keine Contract-Dataclasses, keine CONTRACTS-Registry. TRANSITIONS
referenziert RunState-Felder direkt.

Kein Import aus werkstatt.* auf Modulebene (audit wird lazy
importiert), Modul bleibt leaf.
"""
from __future__ import annotations


class ContractViolation(Exception):
    """Pflichtfeld nicht befuellt — Loop muss abbrechen (OP-136)."""

    def __init__(self, transition: str, felder: list[str]):
        self.transition = transition
        self.felder = felder
        super().__init__(
            f"ContractViolation bei '{transition}': "
            f"Pflichtfelder leer: {', '.join(felder)}"
        )


# Welche RunState-Felder sind bei welchem Rollenwechsel Pflicht?
# True = immer Pflicht. "auto" = nicht pruefen (Feld kann legitim
# leer sein, z.B. Scout wird uebersprungen).
TRANSITIONS: dict[str, list[tuple[str, bool | str]]] = {
    "explorer->scout": [
        ("explorer_context", True),
    ],
    "scout->architect": [
        ("scout_api_auszug", "auto"),
        ("explorer_findings", "auto"),
    ],
    "architect->planner": [
        ("architect_prosa", True),
    ],
    "planner->builder": [
        ("tasks", True),
    ],
    "builder->reviewer": [
        ("tasks", True),
    ],
}


def _ist_leer(wert) -> bool:
    """Prueft, ob ein Feld-Wert leer ist (None, '', [], {}, 0, False)."""
    return not wert


def _do_audit_violation(state, key: str, leer: list[str]) -> None:
    """Schreibt das Audit-Event (lazy import gegen Zirkularitaet).

    Der Call heisst bewusst 'audit(...)' (nicht 'audit_fn(...)'),
    damit tools/audit_drift.py ihn im AST findet.
    """
    try:
        from werkstatt.audit import audit_safe
    except ImportError:
        return
    audit_safe(
        "state_contract_violation",
        {"transition": key, "felder": leer},
        getattr(state, "project_dir", None),
        str(state.project_name),
    )


def validate_transition(
    von: str,
    zu: str,
    state,
    audit_fn=None,
) -> None:
    """Prueft Pflichtfelder fuer einen Rollenwechsel (OP-136).

    Wirft ContractViolation bei Verstoss. audit_fn (fuer Tests) ersetzt
    den Standard-audit()-Call aus _do_audit_violation.
    """
    key = f"{von}->{zu}"
    if key not in TRANSITIONS:
        return

    leer: list[str] = []
    for feld_name, regel in TRANSITIONS[key]:
        if regel == "auto":
            continue
        if regel is True:
            wert = getattr(state, feld_name, None)
            if _ist_leer(wert):
                leer.append(feld_name)

    if not leer:
        return

    if audit_fn is not None:
        audit_fn(
            "state_contract_violation",
            {"transition": key, "felder": leer},
            str(getattr(state, "project_dir", "")),
            str(state.project_name),
        )
    else:
        _do_audit_violation(state, key, leer)

    raise ContractViolation(key, leer)
