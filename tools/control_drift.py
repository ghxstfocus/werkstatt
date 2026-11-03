#!/usr/bin/env python3
"""CLI-Wrapper fuer werkstatt.control.drift.

Usage:
  python3 tools/control_drift.py --check    # Exit 1 bei Drift
  python3 tools/control_drift.py --list     # Alle Kontrollen anzeigen
  python3 tools/control_drift.py --dead     # Ungenutzte Kandidaten zeigen
  python3 tools/control_drift.py --json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from werkstatt.control import CONTROL_REGISTRY, check_drift, list_controls  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true")
    p.add_argument("--list", action="store_true")
    p.add_argument("--dead", action="store_true")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    result = check_drift()

    if args.list or (not args.check and not args.dead):
        print(f"\n{len(CONTROL_REGISTRY)} Kontrollen registriert:\n")
        for ctrl in list_controls():
            flag = "HART" if ctrl.hart else "weich"
            print(f"  [{ctrl.phase.value:14s}] {ctrl.name:32s} ({flag:5s}, prio {ctrl.prioritaet:3d})")
            print(f"    {ctrl.description}")
            print(f"    source: {ctrl.source}")
            print()

    if args.dead:
        if result["unregistered"]:
            print(f"\n{result['unregistered_count']} unregistrierte Kandidaten:")
            for u in result["unregistered"]:
                print(f"  {u}")
        else:
            print("\nKeine unregistrierten Kandidaten.")

    if args.check:
        if result["ok"]:
            print("✓ Kein Registry-Drift.")
            return 0
        print("✗ Registry-Drift gefunden:")
        for b in result["broken_sources"]:
            print(f"  BROKEN {b['name']}: {b['source']} nicht importierbar")
        for d in result["dead_registry"]:
            print(f"  DEAD {d['name']}: source zeigt auf andere fn")
        return 1

    if args.json:
        print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
