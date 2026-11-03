#!/usr/bin/env python3
"""Deterministischer Audit-Katalog-Check (OP-094).

Prueft, ob der Katalog in `werkstatt/audit.py::_AUDIT_KINDS_BEKANNT`
mit den tatsaechlichen `audit(...)`-Aufrufen im Code uebereinstimmt.

Klassifiziert jede Abweichung:
- Tippfehler: Katalog-Name und Code-Name sind sich sehr aehnlich
  (difflib-Ratio >= 0.8) → Vorschlag: welcher Name ist der richtige.
- Echter Drift: keine Aehnlichkeit → Mensch muss entscheiden.

CLI:
  --check         Nur pruefen, Exit 1 bei Drift (CI-tauglich)
  --fix           Tippfehler automatisch korrigieren (Ratio >= 0.9)
  --json          Maschinenlesbar
  --max-dist N    Difflib-Cutoff (default 0.8)

Beispiel-Aufruf (Preflight):
  python3 tools/audit_drift.py --check
"""
from __future__ import annotations

import argparse
import ast
import difflib
import json
import re
import sys
from pathlib import Path

WERKSTATT = Path("werkstatt")
AUDIT_FILE = WERKSTATT / "audit.py"


def finde_code_kinds() -> set[str]:
    """Findet alle audit("x", ...)-Aufrufe via AST (robuster als Regex)."""
    kinds: set[str] = set()
    for py in WERKSTATT.rglob("*.py"):
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (isinstance(func, ast.Name) and func.id == "audit"):
                if not (isinstance(func, ast.Attribute) and func.attr == "audit"):
                    continue
            if not node.args:
                continue
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                kinds.add(first.value)
    return kinds


def finde_katalog() -> set[str]:
    """Liest _AUDIT_KINDS_BEKANNT aus werkstatt/audit.py."""
    src = AUDIT_FILE.read_text(encoding="utf-8")
    m = re.search(
        r'_AUDIT_KINDS_BEKANNT[^=]*=\s*frozenset\(\{(.*?)\}\)',
        src,
        re.DOTALL,
    )
    if not m:
        return set()
    return set(re.findall(r"'([a-z_][a-z0-9_]*)'", m.group(1)))


def klassifiziere(
    katalog: set[str], code: set[str], max_dist: float = 0.8
) -> dict:
    tot = sorted(katalog - code)
    fehlend = sorted(code - katalog)
    tippfehler: list[dict] = []
    echt: list[dict] = []
    for t in tot:
        matches = difflib.get_close_matches(t, fehlend, n=1, cutoff=max_dist)
        if matches:
            ratio = difflib.SequenceMatcher(None, t, matches[0]).ratio()
            tippfehler.append({"katalog": t, "code": matches[0], "ratio": round(ratio, 3)})
        else:
            echt.append({"katalog": t, "code": None})
    for f in fehlend:
        if any(tf["code"] == f for tf in tippfehler):
            continue
        matches = difflib.get_close_matches(f, tot, n=1, cutoff=max_dist)
        if not matches:
            echt.append({"katalog": None, "code": f})
    return {
        "tot": tot,
        "fehlend": fehlend,
        "tippfehler": tippfehler,
        "echt": echt,
    }


def auto_fix(tippfehler: list[dict], min_ratio: float = 0.9) -> int:
    """Korrigiert Tippfehler im Katalog bei Ratio >= min_ratio."""
    src = AUDIT_FILE.read_text(encoding="utf-8")
    fixed = 0
    for tf in tippfehler:
        if tf["ratio"] < min_ratio:
            continue
        # Nur im Katalog ersetzen, nicht im ganzen File
        m = re.search(
            r"(_AUDIT_KINDS_BEKANNT[^=]*=\s*frozenset\(\{(.*?)\}\))",
            src,
            re.DOTALL,
        )
        if not m:
            continue
        block = m.group(0)
        neuer_block = block.replace(
            f"'{tf['katalog']}'", f"'{tf['code']}'", 1
        )
        if neuer_block != block:
            src = src.replace(block, neuer_block, 1)
            fixed += 1
    if fixed:
        AUDIT_FILE.write_text(src, encoding="utf-8")
    return fixed


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true")
    p.add_argument("--fix", action="store_true")
    p.add_argument("--json", action="store_true")
    p.add_argument("--max-dist", type=float, default=0.8)
    args = p.parse_args()

    katalog = finde_katalog()
    code = finde_code_kinds()
    result = klassifiziere(katalog, code, args.max_dist)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["tippfehler"]:
            print("Tippfehler (Katalog-Eintrag vs. Code):")
            for tf in result["tippfehler"]:
                print(f"  '{tf['katalog']}' → '{tf['code']}'  (ratio {tf['ratio']})")
        if result["echt"]:
            print("Echter Drift:")
            for e in result["echt"]:
                if e["katalog"]:
                    print(f"  Katalog hat '{e['katalog']}', Code ruft nie auf")
                else:
                    print(f"  Code ruft '{e['code']}', Katalog fehlt")

    if args.fix:
        fixed = auto_fix(result["tippfehler"])
        print(f"  ✓ {fixed} Tippfehler automatisch korrigiert")

    if args.check:
        return 0 if not (result["echt"] or result["tippfehler"]) else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
