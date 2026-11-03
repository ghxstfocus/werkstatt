"""Drift-Check: Registry vs. Code."""
from __future__ import annotations

import ast
import importlib
import re
from pathlib import Path

from werkstatt.control.registry import CONTROL_REGISTRY


def _resolve(source: str):
    """Loest 'werkstatt.X.Y' zu einer Funktion auf. None bei Fehler."""
    try:
        mod_path, _, attr = source.rpartition(".")
        mod = importlib.import_module(mod_path)
        return getattr(mod, attr, None)
    except (ImportError, AttributeError):
        return None


def _alle_kandidaten() -> dict[str, tuple[str, int]]:
    """AST-Scan: alle Kontrolle-Kandidaten im Code.

    Kandidat = Funktion deren Name mit _check_, _verify_, _gate_,
    _preflight_, _pruefe_, _human_gate, _plan_gate, _reflection_loop,
    _phase_end_reflection beginnt.
    """
    pattern = re.compile(
        r"^(_check|_verify|_gate|_preflight|_guard|_validate|_pruefe|"
        r"_human_gate|_plan_gate|_reflection_loop|_phase_end_reflection|"
        r"scan_patches)"
    )
    out: dict[str, tuple[str, int]] = {}
    for py in Path("werkstatt").rglob("*.py"):
        if "control/" in str(py):
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and pattern.match(node.name):
                out.setdefault(node.name, (str(py), node.lineno))
    return out


def check_drift() -> dict:
    """Prueft Registry vs. Code.

    Returns dict mit:
        ok: True wenn kein Drift.
        broken_sources: Registry-Eintraege deren fn nicht importierbar ist.
        unregistered: Code-Funktionen die Kontroll-Kandidaten sind,
            aber nicht in der Registry stehen.
        dead_registry: Registry-Eintraege deren source-Funktion
            nicht mehr existiert.
    """
    broken: list[dict] = []
    dead: list[dict] = []
    for name, ctrl in CONTROL_REGISTRY.items():
        fn = _resolve(ctrl.source)
        if fn is None:
            broken.append({"name": name, "source": ctrl.source})
            continue
        if fn is not ctrl.fn:
            # Import-Pfad zeigt auf andere Funktion (Refactor-Drift)
            dead.append({"name": name, "source": ctrl.source})

    registriert = {ctrl.source for ctrl in CONTROL_REGISTRY.values()}
    registriert_names = set(CONTROL_REGISTRY.keys())
    unregistered: list[str] = []
    for fname, (fpath, fline) in _alle_kandidaten().items():
        if fname in registriert_names:
            continue
        # Viele Helper sind legitim unregistriert (z.B. _task_ende,
        # _setze_runde_patches). Nur Warnung.
        unregistered.append(f"{fpath}:{fline} {fname}()")

    return {
        "ok": not broken and not dead,
        "broken_sources": broken,
        "dead_registry": dead,
        "unregistered_count": len(unregistered),
        "unregistered": sorted(unregistered),
    }
