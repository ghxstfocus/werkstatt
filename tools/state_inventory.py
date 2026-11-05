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
BASELINE_GEISTER = frozenset({
    "_reflection_bug_sigs_vorher", "_reflection_diff_hash", "aktuelle_task", "applied_count",
    "auftrag_bereits_erfuellt", "auto_approve", "baseline_gruen", "explorer_pytest_laufzeit_s",
    "explorer_ruff_befunde", "last_planner_info", "last_verify_errors", "last_verify_hart_stages",
    "messungen_nach_apply", "phase_review_uebersprungen", "progress_written_at_commit", "reflection_erschoepft",
    "reflection_phase", "reviewer_deterministic_fail", "reviewer_stagnation_false_positive", "scout_bereits_erfuellt",
    "spec_widerspruch_erkannt", "split_failure_grund", "tasks_ok_counter",
})
BASELINE_TOTE = frozenset({
    "agent_docs", "anker_fehler_in_folge", "auflagen_log", "block_id",
    "blocker_fehler", "budget", "builder_model", "builder_temp",
    "code_entwurf", "code_entwurf_historie", "commands_log", "commit_review",
    "coverage_pct", "empfehlung_log", "ignore_fehler", "judge_model",
    "letzte_anker_fehler", "letzte_builder_frage", "letzte_ersatz_fehler",
    "letzte_explore_ergebnisse", "letzte_reviewer_antwort",
    "letzter_patch_wirkungslos", "letzter_plan_fehler", "letzter_test_fehler",
    "llm_timeout_s", "max_tokens_builder", "max_tokens_judge",
    "max_tokens_planner", "max_tokens_reviewer", "max_tokens_solver",
    "phase_commit_pakete", "phase_korrektur_zyklus", "planner_model",
    "planner_modus", "planner_resume_anzahl", "planner_runden",
    "review_runden", "reviewer_recovery_model", "reviewer_verdict_model",
    "solver_aufrufe", "solver_befunde", "solver_config", "solver_model",
    "solver_trigger_quellen", "start_ts", "test_gen_model",
    "test_vorschlaege",
})
BASELINE_GETATTR_ONLY = frozenset({
    "_w51g_gemessen", "api_key", "follow_up_fehler", "geladene_skills",
    "git_author_email", "git_author_name", "max_total_llm_s",
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


def scanne_zugriffe() -> tuple[
    dict[str, set[str]], dict[str, set[str]], dict[str, set[str]]
]:
    """Liefert (leser, schreiber, getattr) -> {feld: {module}}."""
    leser: dict[str, set[str]] = defaultdict(set)
    schreiber: dict[str, set[str]] = defaultdict(set)
    gat: dict[str, set[str]] = defaultdict(set)

    for py in WERKSTATT.rglob("*.py"):
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


def main() -> int:
    p = argparse.ArgumentParser(
        description="RunState-Inventur (read-only, OP-134)."
    )
    p.add_argument("--json", action="store_true", help="JSON-Ausgabe")
    p.add_argument("--check", action="store_true",
                   help="Baseline-Check, exit 1 bei Drift")
    args = p.parse_args()

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
