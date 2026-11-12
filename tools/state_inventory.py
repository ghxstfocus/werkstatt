#!/usr/bin/env python3
"""State-Inventur (OP-134).

Read-only Messung: wer schreibt, wer liest, was fehlt im RunState.

Kategorien pro Feld:
- aktiv:        direkt gelesen + direkt geschrieben
- read_only:    direkt gelesen, nie direkt geschrieben
- write_only:   direkt geschrieben, nie gelesen
- getattr_only: nur via getattr(state, 'X') gelesen (lebt indirekt)
- tot:          weder direkt noch via getattr gelesen
- ghost:        auf state.X zugegriffen, aber nicht in state.py deklariert

CLI:
  (ohne Flag)  Tabelle ausgeben
  --json       Maschinenlesbar
  --check      Baseline-Check (exit 1 bei Drift)

Beispiel:
  python3 tools/state_inventory.py --check
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import defaultdict
from pathlib import Path

WERKSTATT = Path("werkstatt")
STATE_PY = WERKSTATT / "state.py"

# Dateien, in denen "_state" nicht RunState, sondern ein anderes
# Objekt ist (PhaseState). Wird beim Scannen ausgeschlossen.
NON_RUNSTATE_STATE_VARS: dict[str, set[str]] = {
    "werkstatt/pipeline_phases.py": {"_state"},
}

STATE_NAMEN = {"state", "run_state", "_state"}

# Baseline Stand 2026-11-04 (Session-Ende). --check failt bei Abweichung.
# Anpassen NUR mit dokumentiertem Grund (OP-135/136).
BASELINE_GEISTER: frozenset[str] = frozenset()
BASELINE_TOTE = frozenset({
    "agent_docs",
    "block_id",
    "start_ts",
})
BASELINE_GETATTR_ONLY = frozenset({
    "_w51g_gemessen",
    "baseline_gruen",
    "explorer_pytest_laufzeit_s",
    "max_total_llm_s",
    "messungen_nach_apply",
})


def _ist_state_var(node: ast.expr, modul: str) -> bool:
    if not isinstance(node, ast.Name):
        return False
    if node.id not in STATE_NAMEN:
        return False
    ausgeschlossen = NON_RUNSTATE_STATE_VARS.get(modul, set())
    return node.id not in ausgeschlossen


def deklarierte_felder() -> dict[str, str]:
    tree = ast.parse(STATE_PY.read_text(encoding="utf-8"))
    felder: dict[str, str] = {}
    for node in ast.walk(tree):
        if not (isinstance(node, ast.ClassDef) and node.name == "RunState"):
            continue
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                typ = ast.unparse(item.annotation) if item.annotation else "?"
                felder[item.target.id] = typ
            elif isinstance(item, ast.FunctionDef) and item.name == "__init__":
                for sub in ast.walk(item):
                    if isinstance(sub, ast.Assign):
                        for tgt in sub.targets:
                            if (isinstance(tgt, ast.Attribute)
                                    and isinstance(tgt.value, ast.Name)
                                    and tgt.value.id == "self"):
                                felder.setdefault(tgt.attr, "init")
    return felder


def scanne_zugriffe(
    files: list[Path] | None = None,
) -> tuple[
    dict[str, set[str]], dict[str, set[str]], dict[str, set[str]]
]:
    """Liefert (leser, schreiber, getattr) -> {feld: {module}}.

    OP-165: `files` optional — wenn gesetzt, werden nur diese
    Dateien gescannt (statt aller werkstatt/*.py).
    """
    leser: dict[str, set[str]] = defaultdict(set)
    schreiber: dict[str, set[str]] = defaultdict(set)
    gat: dict[str, set[str]] = defaultdict(set)

    quellen = files if files is not None else list(WERKSTATT.rglob("*.py"))
    for py in quellen:
        modul = str(py)
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue

        ziel_knoten: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
                ziele = node.targets if isinstance(node, ast.Assign) else [node.target]
                for tgt in ziele:
                    if isinstance(tgt, ast.Attribute) and _ist_state_var(tgt.value, modul):
                        schreiber[tgt.attr].add(modul)
                        ziel_knoten.add(id(tgt))
                    elif isinstance(tgt, ast.Attribute):
                        inner = tgt.value
                        if isinstance(inner, ast.Attribute) and _ist_state_var(inner.value, modul):
                            schreiber[inner.attr].add(modul)
                            ziel_knoten.add(id(inner))

        for node in ast.walk(tree):
            if (isinstance(node, ast.Attribute)
                    and _ist_state_var(node.value, modul)
                    and id(node) not in ziel_knoten):
                leser[node.attr].add(modul)

        for node in ast.walk(tree):
            if (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "getattr"
                    and len(node.args) >= 2
                    and _ist_state_var(node.args[0], modul)):
                arg = node.args[1]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    gat[arg.value].add(modul)

    return leser, schreiber, gat


def kategorisiere() -> dict[str, dict]:
    felder = deklarierte_felder()
    leser, schreiber, gat = scanne_zugriffe()
    ergebnis: dict[str, dict] = {}

    for name, typ in felder.items():
        dg = name in leser
        ds = name in schreiber
        ga = name in gat
        if dg and ds:
            kat = "aktiv"
        elif dg:
            kat = "read_only"
        elif ds:
            kat = "write_only"
        elif ga:
            kat = "getattr_only"
        else:
            kat = "tot"
        ergebnis[name] = {
            "typ": typ,
            "kategorie": kat,
            "leser": sorted(leser.get(name, set())),
            "schreiber": sorted(schreiber.get(name, set())),
            "getattr": sorted(gat.get(name, set())),
        }

    alle = set(leser) | set(schreiber) | set(gat)
    for name in alle - set(felder):
        ergebnis[name] = {
            "typ": "?",
            "kategorie": "ghost",
            "leser": sorted(leser.get(name, set())),
            "schreiber": sorted(schreiber.get(name, set())),
            "getattr": sorted(gat.get(name, set())),
        }

    return ergebnis


def tabelle(ergebnis: dict) -> None:
    for kat in ["ghost", "aktiv", "read_only", "write_only", "getattr_only", "tot"]:
        felder = [(n, d) for n, d in sorted(ergebnis.items())
                  if d["kategorie"] == kat]
        if not felder:
            continue
        print(f"\n## {kat} ({len(felder)})")
        for name, daten in felder:
            module = daten["leser"] + daten["schreiber"] + daten["getattr"]
            kurz = [Path(m).name for m in dict.fromkeys(module)][:3]
            print(f"  {name:42s} ::{daten['typ']:22s} in {kurz}")


def check_baseline(ergebnis: dict) -> int:
    ist_geister = {n for n, d in ergebnis.items() if d["kategorie"] == "ghost"}
    ist_tot = {n for n, d in ergebnis.items() if d["kategorie"] == "tot"}
    ist_gat = {n for n, d in ergebnis.items() if d["kategorie"] == "getattr_only"}

    ok = True
    for label, ist, soll in [
        ("Geister", ist_geister, BASELINE_GEISTER),
        ("Tote", ist_tot, BASELINE_TOTE),
        ("Getattr-only", ist_gat, BASELINE_GETATTR_ONLY),
    ]:
        neu = ist - soll
        weg = soll - ist
        if neu:
            ok = False
            print(f"✗ Neue {label}: {sorted(neu)}")
        if weg:
            ok = False
            print(f"✗ {label} weggefallen (Baseline anpassen): {sorted(weg)}")
        if not neu and not weg:
            print(f"✓ {label}: {len(ist)} (Baseline unverändert)")

    return 0 if ok else 1


def ghosts_in_files(files: list[str]) -> list[str]:
    """OP-165: Ghost-Felder in den gegebenen Dateien.

    Rueckgabe leer: keine Verletzung.
    Rueckgabe nicht leer: Fail (--changed -> Exit 1).
    """
    pfade: list[Path] = []
    for f in files:
        if not isinstance(f, str) or not f:
            continue
        fp = Path(f)
        if not fp.is_file():
            alt = Path("werkstatt") / f
            if alt.is_file():
                fp = alt
            else:
                continue
        pfade.append(fp)
    if not pfade:
        return []
    leser, schreiber, gat = scanne_zugriffe(files=pfade)
    treffer = [
        feld for feld in BASELINE_GEISTER
        if feld in leser or feld in schreiber or feld in gat
    ]
    return sorted(treffer)


def main() -> int:
    p = argparse.ArgumentParser(
        description="RunState-Inventur (read-only, OP-134)."
    )
    p.add_argument("--json", action="store_true", help="JSON-Ausgabe")
    p.add_argument("--check", action="store_true",
                   help="Baseline-Check, exit 1 bei Drift")
    p.add_argument("--changed", nargs="*", default=None,
                   metavar="FILE",
                   help="Exit 1, wenn eine der Dateien einen Ghost-"
                        "Feld-Zugriff hat (BASELINE_GEISTER).")
    args = p.parse_args()

    if args.changed is not None:
        treffer = ghosts_in_files(args.changed)
        if treffer:
            print(f"contract_check: Ghost-Felder in {args.changed}: "
                  f"{treffer}")
            return 1
        # OP-176: setattr-Check fuer unbekannte RunState-Felder.
        # OP-176: sibling-Import (tools/ ist kein Package, Script-
        # Aufruf `python3 tools/state_inventory.py` hat tools/ nicht
        # im sys.path). Zusaetzlich das Elternverzeichnis (das ist
        # der Projekt-Root), damit contract_check.py seinerseits
        # `from werkstatt.state import RunState` aufloesen kann.
        _root_dir = str(Path(__file__).resolve().parent.parent)
        if _root_dir not in sys.path:
            sys.path.insert(0, _root_dir)
        _tools_dir = str(Path(__file__).resolve().parent)
        if _tools_dir not in sys.path:
            sys.path.insert(0, _tools_dir)
        from contract_check import _pruefe_setattr_aufrufe, _state_felder

        _sf = _state_felder()
        _setattr_fehler: list[str] = []
        for _f in args.changed:
            if not isinstance(_f, str) or not _f:
                continue
            _fp = Path(_f)
            if not _fp.is_file():
                _alt = Path("werkstatt") / _f
                if _alt.is_file():
                    _fp = _alt
                else:
                    continue
            _setattr_fehler.extend(_pruefe_setattr_aufrufe(_fp, _sf))
        if _setattr_fehler:
            for _e in _setattr_fehler:
                print(f"contract_check: {_e}")
            return 1
        return 0

    ergebnis = kategorisiere()

    if args.check:
        return check_baseline(ergebnis)

    if args.json:
        print(json.dumps(ergebnis, indent=2, sort_keys=True))
        return 0

    print(f"RunState-Inventur — {len(ergebnis)} Felder gesamt")
    tabelle(ergebnis)
    return 0


if __name__ == "__main__":
    sys.exit(main())
