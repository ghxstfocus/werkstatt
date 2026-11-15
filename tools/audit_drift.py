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
        nodes = list(ast.walk(tree))
        for node in nodes:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.name != "project_pending_events":
                continue
            # The projector prefixes persisted ChatJobStore lifecycle kinds.
            for child in ast.walk(node):
                if not isinstance(child, ast.Assign):
                    continue
                if not any(isinstance(target, ast.Name) and target.id == "statuses" for target in child.targets):
                    continue
                if isinstance(child.value, ast.Dict):
                    kinds.update(
                        f"chat_job_{key.value}"
                        for key in child.value.keys
                        if isinstance(key, ast.Constant) and isinstance(key.value, str)
                    )
        # Typed wrappers keep event names at their call sites while passing
        # the kind parameter to audit()/append_event(). Resolve those literal
        # call sites so the registry check covers persisted events as well.
        wrapper_kind_args: dict[str, tuple[int, str]] = {}
        for node in nodes:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            params = [arg.arg for arg in node.args.args]
            for child in ast.walk(node):
                if not isinstance(child, ast.Call):
                    continue
                func = child.func
                is_audit = (
                    isinstance(func, ast.Name)
                    and func.id in {"audit", "audit_safe"}
                ) or (
                    isinstance(func, ast.Attribute)
                    and func.attr in {"audit", "audit_safe"}
                )
                is_append_event = (
                    isinstance(func, ast.Attribute)
                    and func.attr == "append_event"
                )
                if is_audit and child.args and isinstance(child.args[0], ast.Name):
                    kind_name = child.args[0].id
                elif is_append_event and len(child.args) > 1 and isinstance(child.args[1], ast.Name):
                    kind_name = child.args[1].id
                else:
                    continue
                if kind_name in params:
                    prefix = "chat_job_" if is_append_event else ""
                    wrapper_kind_args[node.name] = (params.index(kind_name), prefix)

        # Resolve wrappers around wrappers (for example the web pause helper
        # delegates to _audit_web_loop_event) until the simple chain settles.
        changed = True
        while changed:
            changed = False
            for node in nodes:
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if node.name in wrapper_kind_args:
                    continue
                params = [arg.arg for arg in node.args.args]
                for child in ast.walk(node):
                    if not isinstance(child, ast.Call) or not isinstance(child.func, ast.Name):
                        continue
                    delegated = wrapper_kind_args.get(child.func.id)
                    if delegated is None:
                        continue
                    index, prefix = delegated
                    if len(child.args) <= index:
                        continue
                    kind_arg = child.args[index]
                    if not isinstance(kind_arg, ast.Name):
                        continue
                    kind_name = kind_arg.id
                    if kind_name in params:
                        wrapper_kind_args[node.name] = (params.index(kind_name), prefix)
                        changed = True
                        break

        for node in nodes:
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            _audit_namen = frozenset({"audit", "audit_safe"})
            _ist_name = isinstance(func, ast.Name) and func.id in _audit_namen
            _ist_attr = isinstance(func, ast.Attribute) and func.attr in _audit_namen
            # Klassischer audit("kind", ...)-Aufruf
            if _ist_name or _ist_attr:
                if not node.args:
                    continue
                first = node.args[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    kinds.add(first.value)
                continue
            # OP-321: EventStore().append(kind="...")-Aufruf
            # (gate_open, gate_answered, gate_expired, loop_gate_timeout,
            #  token_usage, gate_waiting, loop_started, ...)
            if isinstance(func, ast.Attribute) and func.attr == "append":
                for kw in node.keywords:
                    if (kw.arg == "kind"
                            and isinstance(kw.value, ast.Constant)
                            and isinstance(kw.value.value, str)):
                        kinds.add(kw.value.value)
            # ChatJobStore.append_event(job_id, kind, payload).
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "append_event"
                and len(node.args) > 1
                and isinstance(node.args[1], ast.Constant)
                and isinstance(node.args[1].value, str)
            ):
                suffix = node.args[1].value
                event_kind = (
                    "chat_job_run_snapshot_cleanup_failed"
                    if suffix == "run_snapshot_cleanup_failed"
                    else f"chat_job_{suffix}"
                )
                kinds.add(event_kind)
            # Literal event names passed through typed audit/event wrappers.
            if isinstance(func, ast.Name) and func.id in wrapper_kind_args:
                index, prefix = wrapper_kind_args[func.id]
                if len(node.args) > index:
                    kind = node.args[index]
                    if isinstance(kind, ast.Constant) and isinstance(kind.value, str):
                        kinds.add(prefix + kind.value)
    return kinds


def finde_katalog() -> set[str]:
    """Liest _AUDIT_KINDS_BEKANNT aus werkstatt/audit.py."""
    src = AUDIT_FILE.read_text(encoding="utf-8")
    tree = ast.parse(src)
    kinds: set[str] = set()
    for node in ast.walk(tree):
        targets: list[ast.expr]
        if isinstance(node, ast.AnnAssign):
            targets = [node.target]
            value = node.value
        elif isinstance(node, ast.Assign):
            targets = node.targets
            value = node.value
        else:
            continue
        if not any(
            isinstance(target, ast.Name)
            and target.id == "_AUDIT_KINDS_BEKANNT"
            for target in targets
        ) or value is None:
            continue
        # Every literal in the static set/union expression is a catalog kind.
        # Names in the right hand side (the previous set) contribute no
        # literals; their earlier assignment is collected separately.
        kinds.update(
            child.value for child in ast.walk(value)
            if isinstance(child, ast.Constant)
            and isinstance(child.value, str)
        )
    return kinds


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
