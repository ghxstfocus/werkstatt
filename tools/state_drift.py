#!/usr/bin/env python3
"""State-Drift-Tool (OP-136b, vereinfacht OP-141-Vorarbeit).

Prueft Konsistenz zwischen TRANSITIONS und RunState:

Checks:
  1. Jeder in TRANSITIONS referenzierte Feld-Name ist in RunState
     deklariert (via state_inventory.deklarierte_felder).
  2. Alle 5 erwarteten Uebergaenge sind in TRANSITIONS.

CLI:
  --check    Exit 1 bei Drift
  --json     Maschinenlesbar
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.state_inventory import deklarierte_felder
from werkstatt.state_contracts import TRANSITIONS

ERWARTETE_UEBERGAENGE = frozenset({
    "explorer->scout",
    "scout->architect",
    "architect->planner",
    "planner->builder",
    "builder->reviewer",
})


def check_drift() -> dict:
    """Fuehrt die zwei Checks aus. Rueckgabe: dict mit Details."""
    deklariert = set(deklarierte_felder().keys())

    referenzierte: set[str] = set()
    for felder in TRANSITIONS.values():
        for feld_name, _regel in felder:
            referenzierte.add(feld_name)

    unbekannte_felder = sorted(referenzierte - deklariert)
    fehlende_uebergaenge = sorted(ERWARTETE_UEBERGAENGE - set(TRANSITIONS))

    ok = not (unbekannte_felder or fehlende_uebergaenge)
    return {
        "ok": ok,
        "unbekannte_felder": unbekannte_felder,
        "fehlende_uebergaenge": fehlende_uebergaenge,
        "n_transitions": len(TRANSITIONS),
        "n_referenzierte_felder": len(referenzierte),
    }


def main() -> int:
    p = argparse.ArgumentParser(
        description="State-Drift-Check (OP-136b, read-only)."
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
        print(f"\u2713 Kein State-Drift "
              f"({result['n_transitions']} Uebergaenge, "
              f"{result['n_referenzierte_felder']} Felder).")
        return 0

    print("\u2717 State-Drift gefunden:")
    if result["unbekannte_felder"]:
        print(f"  TRANSITIONS referenziert unbekannte Felder: "
              f"{result['unbekannte_felder']}")
    if result["fehlende_uebergaenge"]:
        print(f"  Fehlende Uebergaenge in TRANSITIONS: "
              f"{result['fehlende_uebergaenge']}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
