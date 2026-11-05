#!/usr/bin/env python3
"""State-Drift-Tool (OP-136b).

Prueft drei Konsistenz-Checks zwischen CONTRACTS, TRANSITIONS und
den @property-Views auf RunState.

Checks:
  1. Jeder CONTRACTS-Key hat eine gleichnamige @property auf RunState.
  2. Jeder in TRANSITIONS referenzierte Feld-Name ist bekannter
     CONTRACTS-Key.
  3. Jeder CONTRACTS-Key ist in TRANSITIONS referenziert oder hat
     Contract.transition_frei=True.

CLI:
  --check    Exit 1 bei Drift
  --json     Maschinenlesbar
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from werkstatt.state_contracts import (
    CONTRACTS,
    TRANSITIONS,
)

STATE_PY = Path("werkstatt/state.py")


def _properties_auf_runstate() -> set[str]:
    """Sammelt @property-Namen der RunState-Klasse via AST."""
    tree = ast.parse(STATE_PY.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "RunState":
            props: set[str] = set()
            for item in node.body:
                if not isinstance(item, ast.FunctionDef):
                    continue
                for deco in item.decorator_list:
                    if isinstance(deco, ast.Name) and deco.id == "property":
                        props.add(item.name)
                        break
            return props
    return set()


def check_drift() -> dict:
    """Fuehrt die drei Checks aus. Rueckgabe: dict mit Details."""
    props = _properties_auf_runstate()
    contracts = set(CONTRACTS.keys())

    fehlende_properties = sorted(contracts - props)

    referenzierte: set[str] = set()
    for felder in TRANSITIONS.values():
        for feld_name, _regel in felder:
            referenzierte.add(feld_name)
    unbekannte_transitions = sorted(referenzierte - contracts)

    fehlende_transitions = sorted(
        name for name in contracts
        if name not in referenzierte
        and not CONTRACTS[name].transition_frei
    )

    ok = not (
        fehlende_properties
        or unbekannte_transitions
        or fehlende_transitions
    )
    return {
        "ok": ok,
        "fehlende_properties": fehlende_properties,
        "unbekannte_transitions": unbekannte_transitions,
        "fehlende_transitions": fehlende_transitions,
        "n_contracts": len(contracts),
        "n_properties": len(props),
        "n_transitions": len(TRANSITIONS),
    }


def main() -> int:
    p = argparse.ArgumentParser(
        description="State-Registry-Drift-Check (OP-136b, read-only)."
    )
    p.add_argument("--check", action="store_true",
                   help="Exit 1 bei Drift")
    p.add_argument("--json", action="store_true",
                   help="Maschinenlesbar")
    args = p.parse_args()

    result = check_drift()

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["ok"] else 1

    if result["ok"]:
        print(f"\u2713 Kein State-Drift ({result['n_contracts']} Contracts, "
              f"{result['n_properties']} Properties, "
              f"{result['n_transitions']} Uebergaenge).")
        return 0

    print("\u2717 State-Drift gefunden:")
    if result["fehlende_properties"]:
        print(f"  CONTRACTS ohne @property: {result['fehlende_properties']}")
    if result["unbekannte_transitions"]:
        print(f"  TRANSITIONS referenziert unbekannte Contracts: "
              f"{result['unbekannte_transitions']}")
    if result["fehlende_transitions"]:
        print(f"  CONTRACTS ohne TRANSITIONS-Eintrag und ohne "
              f"transition_frei=True: {result['fehlende_transitions']}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
