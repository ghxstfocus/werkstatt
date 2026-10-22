#!/usr/bin/env python3
"""
pipeline.py - Projektunabhaengiger Multi-Agenten-Ablauf.
Block fuer Block. Ein Approval-Gate am Ende.

Verwendung:
  DEEPSEEK_API_KEY=sk-... runuser -u security-ai -- \
    /opt/security-ai/.venv/bin/python3 \
    /opt/werkstatt/pipeline.py --project <name> "<Block-Beschreibung>"

Liest /opt/werkstatt/projects/<name>.yaml. Laedt Agenten aus agents_dir.
Redaction: redaction.redact_all() vor jedem LLM-Call.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import requests
import yaml

from werkstatt.apply import _shift_lines, apply_code_patches
from werkstatt.audit import (
    _AUDIT_KINDS_BEKANNT,
    _AUDIT_RAW_MAX_LEN,
    _AUDIT_RAW_REDACTION_LIMIT,
    _ap_audit_haeufigkeit,
    _plan_audit_pfad,
    audit,
    set_run_id,
)
from werkstatt.commit_input import (
    _PHASE_HEADER_COMMIT_REVIEW,  # noqa: F401 (Re-Export fuer Tests)
    _build_commit_input,
    _build_judge_input,
    _build_phase_judge_input,
    _contract_pfad,
    _format_basis_gate_test_results,  # noqa: F401 (Re-Export fuer Tests)
    _git_diff_phase,  # noqa: F401 (Re-Export fuer Tests)
    _lese_contract,
    _lese_plan,  # noqa: F401 (Re-Export fuer Tests)
    _plan_pfad,
    format_code_patches_fuer_commit,  # noqa: F401 (Re-Export fuer Tests)
)

# Re-Export der HARD_RULES-Konstanten. Tests und
# pipeline-interne Nutzung (build_system_prompt,
# _build_judge_prompt) greifen ueber pipeline.HARD_RULES_*
# zu. ruff sieht Re-Export nicht, daher noqa.
from werkstatt.hard_rules import (  # noqa: F401
    HARD_RULES_BASE,
    HARD_RULES_BUILDER,
    HARD_RULES_BY_ROLE,
    HARD_RULES_JUDGE,
    HARD_RULES_PLANNER,
    HARD_RULES_PLANNER_STUFE1,
    HARD_RULES_PLANNER_STUFE2,
    HARD_RULES_REVIEWER,
    HARD_RULES_SOLVER,
    HARD_RULES_TEST_GENERATOR,
)
from werkstatt.measurement import (
    _NEW_FILE_MARKER,  # noqa: F401 (Re-Export fuer Tests)
    _alle_patches_sind_new_file,  # noqa: F401 (Re-Export fuer Tests)
    _mess_index_block,  # noqa: F401 (Re-Export fuer Tests)
    _mess_inhalt_block,  # noqa: F401 (Re-Export fuer Tests)
    _mess_inhalt_nach_apply,  # noqa: F401 (Re-Export fuer Tests)
    _mess_inhalt_zieldateien,
    _messwerte_fuer_planner,
    _messwerte_fuer_prompt,
    collect_messwerte,
    format_messwerte_block,
)

# W36-2a: aus werkstatt.parser re-exportiert
from werkstatt.parser import (
    _parse_phase_kopf,
    _parse_phase_plan,
)
from werkstatt.prompts import (
    _bauer_recovery_prompt,
    _build_judge_prompt,
    _format_whitelist_block,
    aufgabe_block,
    format_doc_snippets,
    format_projekt_stand,
    formatiere_runden,
    recovery_hinweis_block,
)

# W36: aus werkstatt.state re-exportiert
from werkstatt.state import (
    BudgetExhausted,
    LLMReply,
    Measurement,
    NachlaufErgebnis,
    PhaseMainVorlaufErgebnis,
    PhaseVorlaufErgebnis,
    RecoveryVorschlag,
    RunState,
    SolverBefund,
    SolverDiagnose,
    VorlaufErgebnis,
)
from werkstatt.subprocess_env import subprocess_env
from werkstatt.verify import (  # noqa: F401 (Re-Export fuer Tests)
    verify_code,
    verify_code_kwargs,
    verify_values,
)

# Auflage 2132: Format fuer Commit-Paket (Erstbau + Neubau).
# Wird an zwei Stellen verwendet (build_commit_paket und
# COMMIT-NO-GO-Builder-Neubau), damit sie nicht divergieren.
COMMIT_PAKET_FORMAT = (
    "Format (verbindlich):\n"
    "COMMIT-MESSAGE:\n"
    "<Message mit den fuenf Pflichtabschnitten>\n"
    "ENDE COMMIT-MESSAGE\n\n"
    "BETROFFENE DATEIEN:\n"
    "  - <pfad relativ zum Projekt>\n"
    "ENDE BETROFFENE DATEIEN\n\n"
    "Pflichtabschnitte der Commit-Message (alle fuenf):\n"
    "  - Ausgangslage: warum diese Aenderung?\n"
    "  - Aenderung: was wurde geaendert?\n"
    "  - Tests: welche Tests, Testzahl konkret gemessen.\n"
    "  - Verifikation: ruff, mypy, pytest.\n"
    "  - Reviewed: Reviewer-Verdict mit Auflagen.\n\n"
    "Platzhalter (wie '<N>') sind verboten. Zahlen MUESSEN konkret sein.\n\n"
    "HINWEIS: Die Datei-Aenderungen sind bereits angewendet.\n"
    "Der Commit uebernimmt den echten Zustand (git diff)."
)


# =====================================================================
# Auflage 2183 A4/A5 (P1): Gegenstandsvergleich.
# =====================================================================
P1_SCHWELLWERT_DEFAULT = 0.5
P1_MIN_TOKENS_DEFAULT = 10

# Grund-Konstanten fuer den Audit-Eintrag solver_trigger (U6/U7).
P1_GRUND_GETRIGGERT    = "getriggert"
P1_GRUND_KEIN_LEER     = "kein_trigger_leer"
P1_GRUND_KEIN_ZU_KURZ  = "kein_trigger_zu_kurz"
P1_GRUND_KEIN_JACCARD  = "kein_trigger_jaccard"
P1_GRUND_KEIN_KEIN_PAAR = "kein_trigger_kein_paar"
P1_GRUND_KEIN_SCHON    = "kein_trigger_schon_getriggert"

# P1: Tokenisierung. Buchstaben >= 3 Zeichen ODER Zahlen.
# Zahlen bleiben (identifizieren Gegenstand, z.B. "Zeile 2404").
P1_TOKEN_RE = re.compile(r"[a-zA-ZaeoeueAEOEUE]{3,}|[0-9]+")

# P1: feste Stopwort-Liste (Deutsch + Englisch).
# Sprache ist nicht projektspezifisch, deshalb im Code.
P1_STOPWOERTER = frozenset({
    # 3-Zeichen-Funktionswoerter (V4):
    "und", "ist", "war", "ein", "als", "auf", "aus",
    "bei", "mit", "hat", "soll",
    "aber", "auch", "beim", "dann", "dass", "denn", "der",
    "die", "das", "dem", "den", "des", "dies",
    "doch", "eine", "einer", "eines", "etwa", "fuer", "hier",
    "immer", "kann", "kein", "keine", "koennen", "muss",
    "nach", "nicht", "noch", "nur", "oder", "ohne", "schon",
    "sein", "seine", "sich", "siehe", "sind", "ueber", "unter",
    "vom", "von", "vor", "wenn", "werden", "wie", "wird",
    "wurde", "wurden", "zum", "zur", "zwei",
    "about", "after", "again", "also", "been", "before",
    "being", "between", "could", "does", "each", "from",
    "have", "into", "more", "most", "must", "only", "other",
    "over", "same", "should", "some", "such", "than", "that",
    "their", "them", "then", "there", "these", "they", "this",
    "those", "through", "under", "very", "were", "what",
    "when", "where", "which", "while", "with", "would", "your",
})

# =====================================================================
# Auflage 2183 C: COMMAND: RUN solver.
# =====================================================================
SOLVER_ARG_MAX_LEN = 200  # Reviewer-Grund, kurzer Freitext.

# Auflage 2183 Block 5: Obergrenze fuer Solver-Aufrufe.
MAX_SOLVER_RUNDEN_DEFAULT = 3

ERLAUBTE_SOLVER_QUELLEN = frozenset({
    "p1_trigger", "reviewer_command",
    "anker_nicht_gemessen", "builder_rueckfrage",
    "wirkungsloser_patch",
})
# Redaction (lokal, projektunabhaengig)
sys.path.insert(0, str(Path(__file__).parent))
import redaction

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
COVERAGE_MIN_PCT = 80.0



# In Anlehnung an docs/WORKFLOW.md.
# Auflage 2182: HARD_RULES_BASE + rollenspezifisch.
#
# HARD_RULES_BASE gilt fuer ALLE Rollen.
# HARD_RULES_<ROLLE> ergaenzt die Basis mit
# rollenspezifischen Regeln. build_system_prompt
# waehlt anhand des Agent-Namens.
#
# Nummerierung:
#   HR1, HR7, HR8, HR9, HR10 bleiben in BASE.
#   HR2-HR6 sind entfallen; Inhalte stehen in B6-B9.
#   Rollenspezifisch: R*, B*, T*.


# Mapping Agent-Name -> Rollen-Regeln.
# coverage und chaos sind No-LLM-Rollen und rufen
# build_system_prompt nicht auf. Deshalb kein Eintrag.
# Auflage 2183 B + Kurskorrektur 2026-10-14 (Block 2).
# Aufgabe: Unterstuetzung fuer den Builder-Agenten.
# Diagnose, woran es scheitert + wie besser.
# Adressat: Builder-Agent.
# Auflage 2183 Block 3: Solver sieht dieselbe
# Projekt-Doku wie der Reviewer.


# =====================================================================
# Planner-Regeln, Stufe 1 (Auftrags-Uebersetzer).
# Siehe P2a-A11, P2a-S4-A1. Wortgleich zu vorher.
# =====================================================================
# Alias aus Kompatibilitaet: zeigt auf STUFE1
# (= Default). STUFE2 wird vom Aufrufer explizit
# gewaehlt (build_system_prompt stufe=2).
# Siehe P2a-A11, P2a-S4.
# =====================================================================
# Planner-Regeln, Stufe 2 (Phasen-Planer, --phase).
# Aufrufer waehlt die Stufe (build_system_prompt
# stufe=1|2, siehe P2a-S4-A5).
#
# Diff zu STUFE1:
#   P1' = P1, aber "Auftraege" -> "Auftraege
#          oder Phasenplaene" (Stufe 2).
#   P3' = P3, aber "Auftrag" -> "Phasenplan"
#          (Format PHASE/UNTERBLOCK).
#   P4' = P4, aber "Auftrag" -> "Unterblock".
#   P7  entfaellt (reines Stufe-1-Format,
#        gemessen: nur Block/Praefix-Regeln).
#   P9' = P9, aber "gegen P7 oder P8" ->
#          "gegen P10-P18" (Stufe-2-Format).
# Unveraendert: P2, P5, P6, P8.
# Neu: P10-P16 (P2a).
# Neu 2026-10-16 (Planner-Praezision):
#   P15 verschaerft (Datei-Regel + Unterpunkt-
#        Regel getrennt, atomare Ausnahme).
#   P17 neu (Builder-Freundlichkeit + Beispiel).
#   P18 neu (Reviewer-Befund im Detail + Schutz-
#        Hinweis).
#   P9' erweitert (P10-P18, planner.max_runden).
# =====================================================================
# Auflage 2041: Groessenlimits fuer das Messprotokoll.
MAX_PROTOKOLL_PER_COMMAND = 10_000
# W6a-4 (2026-10-16): read_file braucht mehr Platz,
# weil Anker tief in grossen Dateien stehen.
MAX_PROTOKOLL_PER_COMMAND_READ_FILE = 20_000
# W6a-4 (2026-10-16): Total auf 150_000 erhoeht,
# damit 5 read_files a 20_000 + andere passen.
MAX_PROTOKOLL_TOTAL = 150_000

# W51d (2026-10-18): Planner-spezifische Grenzen.
# Der Planner misst bis zu 20 Zieldateien pro
# Phase. 20 * 10_000 = 200_000. Der Builder behaelt
# 20_000/read_file (Test-Kontext braucht laengere
# Auszuege). quelle-Pruefung in execute_commands.
_PLANNER_PROTOKOLL_PER_READ = 10_000
_PLANNER_PROTOKOLL_TOTAL = 200_000

# Auflage 2042: erlaubte Quellen-Marker fuer COMMAND-Audits.
ERLAUBTE_QUELLEN = {
    "reviewer", "builder", "test_generator",
    "pipeline_auto", "reviewer_command",
    "planner",
}



WERKSTATT_HOME = Path("/opt/werkstatt")
PROJECTS_DIR = WERKSTATT_HOME / "projects"


def require_budget(state: RunState, max_llm: int) -> None:
    """Auflage 2051: prueft das Budget VOR jedem LLM-Call.

    Wirft BudgetExhausted, wenn state.llm_calls >= max_llm.
    """
    if max_llm > 0 and state.llm_calls >= max_llm:
        raise BudgetExhausted(
            f"LLM-Budget erschoepft: {state.llm_calls}/{max_llm}"
        )


def require_budget_time(state: RunState, max_minutes: int) -> None:
    """Auflage 2080: prueft das Zeitbudget vor LLM-Aufrufen.

    Wirft BudgetExhausted, wenn die verstrichene Zeit seit
    state.start_monotonic groesser ist als max_minutes * 60
    Sekunden. Bei genau == max*60 wird noch nicht ausgeloest
    (der erste Check nach Ueberschreitung greift).

    max_minutes <= 0 deaktiviert die Pruefung.
    start_monotonic <= 0 heisst "nicht gesetzt", ebenfalls
    keine Pruefung (Tests koennen den Wert so umgehen).
    """
    if max_minutes <= 0:
        return
    if state.start_monotonic <= 0:
        return
    verstrichen = time.monotonic() - state.start_monotonic
    grenze = max_minutes * 60
    if verstrichen > grenze:
        raise BudgetExhausted(
            f"Zeitbudget erschoepft: {verstrichen:.1f}s / {grenze}s"
        )


def load_project_config(project_name: str) -> dict[str, Any]:
    """Laedt die Projekt-Konfiguration aus /opt/werkstatt/projects/.

    Kein CWD-Bezug. Fail closed, wenn Projekt oder Datei fehlt.
    """
    if not project_name or "/" in project_name or ".." in project_name:
        print(f"[FAIL] Ungueltiger Projektname: {project_name!r}. Fail closed.")
        sys.exit(1)
    path = PROJECTS_DIR / f"{project_name}.yaml"
    if not path.exists():
        print(f"[FAIL] Projekt-Konfiguration fehlt: {path}. Fail closed.")
        sys.exit(1)
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        print(f"[FAIL] Projekt-Konfiguration ist kein dict: {path}. Fail closed.")
        sys.exit(1)
    return data


# =====================================================================
# Projekt-Schema-Validator (Phase 1, Warn-Modus).
# Schema: schemas/projekt.yaml.
# Modus: Umgebungsvariable WERKSTATT_SCHEMA_MODUS=warn|fail.
#        Default: warn. Spaeter: fail (nach Uebergangsphase).
# =====================================================================
SCHEMA_PFAD = Path("/opt/werkstatt/schemas/projekt.yaml")

_ALIAS_TOP = {
    "agents_dir": "project_agents_dir",
}
def _alias_docs_aus_schema(schema_docs: dict[str, Any]) -> dict[str, str]:
    """Liest die Alias-Map aus dem Schema.

    Ein Schluessel-Eintrag mit 'alias: <alt>' erzeugt
    den Eintrag {<alt>: <neu>} in der Map. Damit ist
    das Schema die einzige Quelle der Alias-Definition.
    """
    m: dict[str, str] = {}
    for neu, spec in schema_docs.get("schluessel", {}).items():
        alt = spec.get("alias")
        if isinstance(alt, str) and alt:
            m[alt] = neu
    return m


def _lade_schema() -> dict[str, Any]:
    if not SCHEMA_PFAD.exists():
        print(f"[FAIL] Schema fehlt: {SCHEMA_PFAD}. Fail closed.")
        sys.exit(1)
    with SCHEMA_PFAD.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict) or "felder" not in data:
        print(f"[FAIL] Schema ungueltig: {SCHEMA_PFAD}. Fail closed.")
        sys.exit(1)
    return data


def _typ_ok(wert: Any, typ: str) -> bool:
    if typ == "str | null":
        return wert is None or isinstance(wert, str)
    if typ == "str":
        return isinstance(wert, str)
    if typ == "bool":
        return isinstance(wert, bool)
    if typ == "int":
        return isinstance(wert, int) and not isinstance(wert, bool)
    if typ == "float":
        return isinstance(wert, (int, float)) and not isinstance(wert, bool)
    if typ == "dict":
        return isinstance(wert, dict)
    if typ == "list[str]":
        return isinstance(wert, list) and all(isinstance(x, str) for x in wert)
    return True


def _pruefe_docs(config: dict[str, Any], schema_docs: dict[str, Any],
                 meldungen: list[str]) -> None:
    docs = config.get("docs", {})
    if not isinstance(docs, dict):
        meldungen.append("docs: muss ein dict sein")
        return
    alias_map = _alias_docs_aus_schema(schema_docs)
    for alt, neu in alias_map.items():
        if alt in docs and neu not in docs:
            docs[neu] = docs.pop(alt)
            meldungen.append(f"docs.{alt}: Alias aufgeloest zu docs.{neu}")
    erlaubt = set(schema_docs.get("schluessel", {}).keys())
    for k in list(docs.keys()):
        if k not in erlaubt:
            meldungen.append(
                f"docs.{k}: unbekannt (erlaubt: {sorted(erlaubt)})")
    for k, spec in schema_docs.get("schluessel", {}).items():
        if spec.get("kategorie") == "K" and k not in docs:
            meldungen.append(f"docs.{k}: Pflichtfeld fehlt")


def pruefe_projekt_yaml(config: dict[str, Any], *,
                        modus: str | None = None) -> list[str]:
    """Prueft eine Projekt-Konfiguration gegen schemas/projekt.yaml.

    Liefert die Liste der Meldungen (leer = ok).
    modus: 'warn' | 'fail' | None (= aus Env, Default warn).
    Im Modus 'fail' wird bei Meldungen sys.exit(2) ausgeloest.
    """
    if modus is None:
        modus = os.getenv("WERKSTATT_SCHEMA_MODUS", "warn")
    schema = _lade_schema()
    felder = schema.get("felder", {})
    meldungen: list[str] = []

    if not isinstance(config, dict):
        meldungen.append("config: kein dict")
    else:
        for alt, neu in _ALIAS_TOP.items():
            if alt in config and neu not in config:
                config[neu] = config.pop(alt)
                meldungen.append(f"{alt}: Alias aufgeloest zu {neu}")
        for k in list(config.keys()):
            if k not in felder:
                meldungen.append(f"{k}: unbekanntes Feld")
        for k, spec in felder.items():
            if k == "docs":
                continue
            if spec.get("kategorie") == "K" and k not in config:
                meldungen.append(f"{k}: Pflichtfeld fehlt")
            if k in config:
                typ = spec.get("typ", "")
                if typ and not _typ_ok(config[k], typ):
                    meldungen.append(
                        f"{k}: falscher Typ (erwartet {typ}, "
                        f"ist {type(config[k]).__name__})")
        if "docs" in config:
            _pruefe_docs(config, felder.get("docs", {}), meldungen)

    for k, spec in felder.items():
        if k in config:
            continue
        if "default" in spec:
            config[k] = spec["default"]

    if meldungen:
        if modus == "fail":
            for m in meldungen:
                print(f"[FAIL] Schema: {m}")
            sys.exit(2)
        for m in meldungen:
            print(f"[WARN] Schema: {m}")
    return meldungen


def _lade_und_pruefe_projekt(project_name: str) -> dict[str, Any]:
    """load_project_config + pruefe_projekt_yaml."""
    config = load_project_config(project_name)
    pruefe_projekt_yaml(config)
    return config


# =====================================================================
# Anti-Pattern-Bibliothek (Phase 3a-1, 2026-10-15).
# Katalog: anti-patterns/katalog.yaml.
# Schema: anti-patterns/README.md.
# =====================================================================
ANTI_PATTERN_KATALOG = Path("/opt/werkstatt/anti-patterns/katalog.yaml")

# Planner-Konfiguration (Block P1, 2026-10-15).
# TT4: Praefix-Liste als Konstante, nicht hart im Regex.
PLANNER_BLOCK_PRAEFIXE = (
    "feat", "fix", "docs", "refactor", "test",
)

_AP_IDS_RE = re.compile(r"^ap-[a-z0-9-]+$")
_AP_ROLLEN_ERLAUBT = frozenset({
    "builder", "reviewer", "solver", "test_generator",
})
_AP_PFLICHTFELDER = (
    "id", "titel", "beschreibung", "loesung",
    "begruendung", "kategorie", "rollen",
)

# Bekannte Audit-Kinds (aus audit-logs/*.jsonl abgeleitet,
# 2026-10-15). Neue Kinds MUESSEN hier ergaenzt werden,
# sonst schlaegt die Katalog-Validierung fehl.
# W48-A16-b (2026-10-18): Anzahl der registrierten
# Audit-Kinds. Bei neuem Kind: DIESE Zeile UND
# _AUDIT_KINDS_BEKANNT anpassen. Der AST-Test
# (test_audit_kinds_alle_aufrufe_registriert) prueft
# die Nutzung, test_katalog_anzahl_matcht_soll die
# Registrierung.
_KATALOG_SOLL = 167  # W61: +builder_readfile_blockiert, verify_code_befund



def _validiere_ap_eintrag(e: dict[str, Any], *, index: int) -> None:
    for feld in _AP_PFLICHTFELDER:
        if feld not in e:
            print(f"[FAIL] Anti-Pattern[{index}]: Pflichtfeld "
                  f"{feld!r} fehlt. Fail closed.")
            sys.exit(1)
    eid = e["id"]
    if not isinstance(eid, str) or not _AP_IDS_RE.match(eid):
        print(f"[FAIL] Anti-Pattern[{index}]: id {eid!r} passt nicht "
              f"zu ^ap-[a-z0-9-]+$. Fail closed.")
        sys.exit(1)
    if not isinstance(e["rollen"], list) or not e["rollen"]:
        print(f"[FAIL] Anti-Pattern[{index}] ({eid}): rollen leer "
              f"oder kein list. Fail closed.")
        sys.exit(1)
    for r in e["rollen"]:
        if r not in _AP_ROLLEN_ERLAUBT:
            print(f"[FAIL] Anti-Pattern[{index}] ({eid}): Rolle "
                  f"{r!r} unbekannt. Erlaubt: "
                  f"{sorted(_AP_ROLLEN_ERLAUBT)}. Fail closed.")
            sys.exit(1)
    if e["kategorie"] not in (1, 2, 3):
        print(f"[FAIL] Anti-Pattern[{index}] ({eid}): kategorie "
              f"{e['kategorie']!r} nicht in {{1,2,3}}. Fail closed.")
        sys.exit(1)
    for ak in e.get("audit_kinds", []) or []:
        if ak not in _AUDIT_KINDS_BEKANNT:
            print(f"[FAIL] Anti-Pattern[{index}] ({eid}): "
                  f"audit_kind {ak!r} unbekannt. Fail closed.")
            sys.exit(1)
    for tg in e.get("trigger_gruende", []) or []:
        if tg not in ERLAUBTE_SOLVER_QUELLEN:
            print(f"[FAIL] Anti-Pattern[{index}] ({eid}): "
                  f"trigger_grund {tg!r} nicht in "
                  f"ERLAUBTE_SOLVER_QUELLEN. Fail closed.")
            sys.exit(1)


def lade_anti_patterns() -> list[dict[str, Any]]:
    """Laedt und validiert anti-patterns/katalog.yaml.

    Fail closed bei fehlender oder ungueltiger Datei.
    """
    if not ANTI_PATTERN_KATALOG.exists():
        print(f"[FAIL] Anti-Pattern-Katalog fehlt: "
              f"{ANTI_PATTERN_KATALOG}. Fail closed.")
        sys.exit(1)
    with ANTI_PATTERN_KATALOG.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        print("[FAIL] Anti-Pattern-Katalog ist kein dict. Fail closed.")
        sys.exit(1)
    if data.get("version") != 1:
        print("[FAIL] Anti-Pattern-Katalog version != 1. Fail closed.")
        sys.exit(1)
    eintraege = data.get("eintraege", [])
    if not isinstance(eintraege, list):
        print("[FAIL] Anti-Pattern-Katalog eintraege kein list. "
              "Fail closed.")
        sys.exit(1)
    seen: set[str] = set()
    for i, e in enumerate(eintraege):
        if not isinstance(e, dict):
            print(f"[FAIL] Anti-Pattern[{i}] kein dict. Fail closed.")
            sys.exit(1)
        _validiere_ap_eintrag(e, index=i)
        if e["id"] in seen:
            print(f"[FAIL] Anti-Pattern[{i}]: id {e['id']!r} "
                  f"doppelt. Fail closed.")
            sys.exit(1)
        seen.add(e["id"])
    return eintraege


def anti_patterns_fuer(
    rolle: str,
    trigger_grund: str | None = None,
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Filtert Anti-Patterns nach Rolle und optional Trigger-Grund.

    - Eintrag wird gezeigt, wenn rolle in e['rollen'].
    - Wenn trigger_grund gesetzt:
        - Eintrag ohne trigger_gruende: immer zeigen
          (VV2 Fallback).
        - Eintrag mit trigger_gruende: nur zeigen, wenn
          trigger_grund enthalten.
    - Sortierung: nach Summe der audit_kinds-Treffer
      im Audit-Log, absteigend. Eintraege ohne
      audit_kinds am Ende.
    - limit: max Anzahl zurueckgegebener Eintraege (VV1).
    """
    alle = lade_anti_patterns()
    treffer = _ap_audit_haeufigkeit()

    def audit_key(e: dict[str, Any]) -> int:
        s = 0
        for ak in e.get("audit_kinds", []) or []:
            s += treffer.get(ak, 0)
        return -s

    def stufe(e: dict[str, Any]) -> int:
        # XX1: Stufe 1 = Eintrag hat trigger_gruende-Feld
        # UND der aktuelle Grund steht darin.
        if trigger_grund is None:
            return 2
        tgs = e.get("trigger_gruende")
        if tgs and trigger_grund in tgs:
            return 1
        return 2

    ausgewaehlt: list[dict[str, Any]] = []
    for e in alle:
        if rolle not in e.get("rollen", []):
            continue
        if trigger_grund is not None:
            tgs = e.get("trigger_gruende")
            if tgs and trigger_grund not in tgs:
                continue
        ausgewaehlt.append(e)
    # XX2: zwei Stufen, innerhalb jeder Stufe nach
    # Audit-Haeufigkeit (XX3: abschneiden danach).
    ausgewaehlt.sort(key=lambda e: (stufe(e), audit_key(e)))
    return ausgewaehlt[:limit]


# WW3: Mapping Anker-Fehler-Grund -> Trigger-Grund aus
# ERLAUBTE_SOLVER_QUELLEN. "leer" und "shift_akzeptiert"
# haben keinen Trigger-Grund und fallen auf None.
_AP_GRUND_ZU_TRIGGER = {
    "wirkungslos": "wirkungsloser_patch",
    "nicht_gefunden": "anker_nicht_gemessen",
}

# Prioritaet bei mehreren Anker-Fehlern:
# wirkungslos > nicht_gefunden > leer / shift_akzeptiert.
_AP_GRUND_PRIO = ("wirkungslos", "nicht_gefunden", "leer",
                  "shift_akzeptiert")

_AP_BESCHREIBUNG_MAX = 500


def _ap_kuerzen(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len - 1].rstrip() + "…"


def _ap_trigger_grund_aus_state(state: RunState) -> str | None:
    """WW3: leitet den Trigger-Grund aus den Anker-Fehlern ab.

    Liefert None, wenn kein Fehler vorliegt oder der Grund
    keinen Trigger-Grund hat.
    """
    gruende = [g for (_, _, _, g) in state.letzte_anker_fehler]
    for g in _AP_GRUND_PRIO:
        if g in gruende:
            return _AP_GRUND_ZU_TRIGGER.get(g)
    return None


def _anti_pattern_block(
    state: RunState,
    rolle: str,
    trigger_grund: str | None = None,
    *,
    aufrufer: str | None = None,
) -> str:
    """WW4: formatiert die relevanten Anti-Patterns als
    Prompt-Block. Liefert "" wenn nichts zu zeigen ist.

    Schreibt Audit-Event anti_patterns_injiziert, wenn
    mindestens ein Eintrag gezeigt wird (YY6: kein
    Audit bei leerem Block).

    YY4: aufrufer (z.B. "command", "deadlock",
    "trigger_a_b_c") wird mit ins Audit geschrieben,
    damit der Pfad nachvollziehbar ist.
    """
    aps = anti_patterns_fuer(rolle, trigger_grund, limit=3)
    if not aps:
        return ""
    zeilen = ["## ANTI-PATTERNS"]
    for e in aps:
        beschreibung = _ap_kuerzen(
            e["beschreibung"].strip(), _AP_BESCHREIBUNG_MAX)
        loesung = _ap_kuerzen(
            e["loesung"].strip(), _AP_BESCHREIBUNG_MAX)
        zeilen.append("")
        zeilen.append(f"- [{e['id']}] {e['titel']}")
        zeilen.append(f"  Beschreibung: {beschreibung}")
        zeilen.append(f"  Loesung: {loesung}")
    # Audit (YY6: nur bei nicht-leerem Block).
    if state.project_dir is not None:
        payload: dict[str, Any] = {
            "rolle": rolle,
            "trigger_grund": trigger_grund,
            "ids": [e["id"] for e in aps],
        }
        if aufrufer is not None:
            payload["aufrufer"] = aufrufer
        audit("anti_patterns_injiziert", payload,
              state.project_dir, state.project_name)
    return "\n".join(zeilen)


# =====================================================================
# Planner (Block P1, 2026-10-15).
# Stufe 1 des Planner-Konzepts (docs/PLANNER-KONZEPT.md).
# =====================================================================

def parse_planner_reply(text: str) -> dict[str, Any]:
    """Parst die Planner-Antwort.

    Liefert:
      {
        "art": "auftrag" | "rueckfrage" | "ungueltig",
        "praefix": str | None,
        "titel": str,
        "text": str,
        "frage": str,
      }

    Regeln (TT5):
      - Antwort beginnt mit "Block: <praefix> - <Titel>":
        praefix muss in PLANNER_BLOCK_PRAEFIXE sein.
      - Antwort beginnt mit "RUECKFRAGE:":
        art=rueckfrage.
      - Sonst: art=ungueltig.
    """
    ergebnis: dict[str, Any] = {
        "art": "ungueltig",
        "text": text,
    }
    stripped = text.strip()
    if not stripped:
        return ergebnis

    # Rueckfrage?
    if stripped.startswith("RUECKFRAGE:"):
        ergebnis["art"] = "rueckfrage"
        ergebnis["frage"] = stripped[len("RUECKFRAGE:"):].strip()
        return ergebnis

    # Auftrag?
    erste_zeile = stripped.split("\n", 1)[0].strip()
    if erste_zeile.startswith("Block:"):
        rest_zeile = erste_zeile[len("Block:"):].strip()
        if " - " in rest_zeile:
            praefix_teil, titel = rest_zeile.split(" - ", 1)
            praefix = praefix_teil.strip().lower()
            if praefix in PLANNER_BLOCK_PRAEFIXE:
                ergebnis["art"] = "auftrag"
                ergebnis["praefix"] = praefix
                ergebnis["titel"] = titel.strip()
                return ergebnis
    return ergebnis


# =====================================================================
# Block P2a: Phasen-Modus (Stufe 2) — Parser.
# Siehe docs/PLANNER-KONZEPT.md, Abschnitt 8.
# =====================================================================

# Block 2b / B3: Praefix fuer UNBEANTWORTET-Marker.
# Gekoppelt an P18 Schritt 5. Bei P18-Aenderung
# hier anpassen.
_UNBEANTWORTET_PRAEFIX = "UNBEANTWORTET:"


# W35a-2c (2026-10-17): ID-Muster fuer _parse_phase_plan.



def _plan_unbeantwortet_punkte(
    unterbloecke: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Block 2b / B1: erkennt UNBEANTWORTET-Punkte.

    Eingabe: geparste Unterbloecke (aus _parse_phase_plan).
    Rueckgabe: Liste von dicts mit
      {"unterblock": "U<n>", "punkt": "<text>"}.

    Erkennung: ein Unterpunkt beginnt mit dem
    Praefix aus _UNBEANTWORTET_PRAEFIX (case-
    sensitive, P18 Schritt 5).
    """
    treffer: list[dict[str, str]] = []
    for u in unterbloecke:
        if not isinstance(u, dict):
            continue
        uid = u.get("id", "?")
        for punkt in u.get("unterpunkte", []):
            if not isinstance(punkt, str):
                continue
            if punkt.startswith(_UNBEANTWORTET_PRAEFIX):
                treffer.append({
                    "unterblock": uid,
                    "punkt": punkt,
                })
    return treffer


def _phase_plan_als_text(
    phase_id: str,
    phase_titel: str,
    unterbloecke: list[dict[str, Any]],
) -> str:
    """Serialisiert einen Plan ins Phasentext-Format.

    Auflage P2a-S5c-A3/A4/A5: das Ergebnis MUSS
    _parse_phase_plan ohne ValueError durchlaufen.
    Eigenschaft (Property):
      _parse_phase_plan(_phase_plan_als_text(
          id, titel, unterbloecke)) == unterbloecke
    fuer gueltige Eingaben (auch bei Titeln mit
    ' - ').

    Fehler: ValueError, wenn ein Unterblock
    'unterpunkte' oder 'geschaetzte_runden' fehlen
    hat (Aufrufer-Bug).

    Rueckgabe ohne trailing newline.
    """
    if not phase_id or not phase_titel:
        raise ValueError(
            "_phase_plan_als_text: phase_id oder "
            "phase_titel leer")
    zeilen: list[str] = [
        f"PHASE: {phase_id} - {phase_titel}",
    ]
    for u in unterbloecke:
        if "id" not in u or "titel" not in u:
            raise ValueError(
                "_phase_plan_als_text: Unterblock ohne "
                "id oder titel")
        if "unterpunkte" not in u or not u["unterpunkte"]:
            raise ValueError(
                f"_phase_plan_als_text: U{u.get('id')}: "
                "unterpunkte fehlen")
        if "geschaetzte_runden" not in u:
            raise ValueError(
                f"_phase_plan_als_text: U{u.get('id')}: "
                "geschaetzte_runden fehlt")
        n_rd = u["geschaetzte_runden"]
        if type(n_rd) is not int or n_rd < 1:
            raise ValueError(
                f"_phase_plan_als_text: U{u.get('id')}: "
                "geschaetzte_runden ungueltig")
        zeilen.append(
            f"UNTERBLOCK: {u['id']} - {u['titel']}")
        zeilen.append("Unterpunkte:")
        for p in u["unterpunkte"]:
            if not isinstance(p, str) or not p.strip():
                raise ValueError(
                    f"_phase_plan_als_text: "
                    f"U{u.get('id')}: unterpunkt leer")
            zeilen.append(f"  - {p.strip()}")
        zeilen.append(f"Geschaetzte Runden: {n_rd}")
        zeilen.append("")
    # Letzte Leerzeile entfernen, damit kein trailing \n.
    while zeilen and not zeilen[-1]:
        zeilen.pop()
    return "\n".join(zeilen)


def _phase_edit_modus(
    phase_id: str,
    phase_titel: str,
    unterbloecke: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """Fuehrt den [e]-Pfad aus (gefuellter Edit).

    Auflage P2a-S5c-A2': nur Titel und
    geschaetzte_runden pro Unterblock sind editierbar.
    Unterpunkte und id bleiben unveraendert.

    Rueckgabe: (neue_unterbloecke, anzahl_geaendert).
    Bei 'q' oder leerer Eingabe ueberall:
      (alter_plan, 0).
    Wirft KeyboardInterrupt/EOFError weiter.
    """
    neue: list[dict[str, Any]] = []
    anzahl_geaendert = 0
    print("\n=== EDIT-MODUS ===")
    print("(leer = unveraendert, q = Edit beenden)")
    for u in unterbloecke:
        if u["id"] == "__q__":
            # Sicherheitsnetz: kein realer id-Wert.
            pass
        titel_neu = u["titel"]
        runden_neu = u["geschaetzte_runden"]
        geaendert = False
        print(f"\n{u['id']}: {u['titel']}")
        t_ein = input("  Neuer Titel > ").strip()
        if t_ein.lower() == "q":
            print("[i] Edit abgebrochen.")
            return unterbloecke, 0
        if t_ein:
            titel_neu = t_ein
            geaendert = True
        # Runden.
        aktuell_runden = u["geschaetzte_runden"]
        while True:
            r_ein = input(
                f"  Geschaetzte Runden "
                f"(aktuell {aktuell_runden}, "
                f"leer = unveraendert) > "
            ).strip()
            if r_ein.lower() == "q":
                print("[i] Edit abgebrochen.")
                return unterbloecke, 0
            if not r_ein:
                break
            try:
                n = int(r_ein)
            except ValueError:
                print("[!] Ungueltig: int >= 1 erwartet. "
                      "Bitte erneut.")
                continue
            if str(n) != r_ein or type(n) is not int or n < 1:
                print("[!] Ungueltig: int >= 1 erwartet. "
                      "Bitte erneut.")
                continue
            runden_neu = n
            geaendert = True
            break
        neuer_u = dict(u)
        neuer_u["titel"] = titel_neu
        neuer_u["geschaetzte_runden"] = runden_neu
        neue.append(neuer_u)
        if geaendert:
            anzahl_geaendert += 1
    print("\n---")
    print("Edit beendet.")
    return neue, anzahl_geaendert


# ---------------------------------------------------------------------
# Block P2a: Persistenz phase.yaml.
# Siehe docs/PLANNER-KONZEPT.md, Abschnitt 9.1.
# ---------------------------------------------------------------------

_PHASE_YAML_DIR = Path("/opt/werkstatt/projects")


def _phase_yaml_pfad(project_name: str) -> Path:
    """Pfad zur Phase-Datei eines Projekts.

    Analog zu projects/<name>.memory.yaml.
    """
    return _PHASE_YAML_DIR / f"{project_name}.phase.yaml"


# Hinweis: ValueError statt TypeError ist hier bewusst —
# die Aufrufer (CLI, Audit) pruefen einheitlich auf ValueError.
# Siehe P2a-A7, P2a-S3-A6, P2a-S3-A7. TRY004 wird mit einer
# begruendeten Ausnahmedirektive auf den raise-Zeilen
# ausgehebelt.
def _phase_plan_laden(
    project_name: str,
) -> dict[str, Any] | None:
    """Liest den Phasenplan aus projects/<name>.phase.yaml.

    Rueckgabe:
      - None, wenn Datei fehlt.
      - None, wenn phase_aktiv != true.
      - dict mit allen Feldern sonst.

    Fehler (P2a-A7, P2a-S3-A5, P2a-S3-A6):
      - yaml.YAMLError: propagiert.
      - Datei leer -> ValueError("phase.yaml: leer").
      - Kein dict -> ValueError("phase.yaml: kein dict").
      - phase_aktiv ist nicht bool -> ValueError.
      - Pflichtfeld fehlt/falscher Typ -> ValueError
        mit Feldname.

    Auflage P2a-S1-A4: prueft NICHT phase_erstellt_am
    (Funktion kennt keine Zeit-Semantik).
    """
    pfad = _phase_yaml_pfad(project_name)
    if not pfad.exists():
        return None
    text = pfad.read_text(encoding="utf-8")
    daten = yaml.safe_load(text)
    if daten is None:
        raise ValueError("phase.yaml: leer")
    if not isinstance(daten, dict):
        raise ValueError(  # noqa: TRY004 (P2a-A7)
            "phase.yaml: kein dict")

    aktiv = daten.get("phase_aktiv")
    if aktiv is None and "phase_aktiv" not in daten:
        # Feld fehlt komplett: kein aktiver Plan.
        return None
    if type(aktiv) is not bool:
        raise ValueError(
            "phase.yaml: phase_aktiv kein bool")
    if aktiv is False:
        return None

    # Pflichtfelder (P2a-S1-A8, P2a-S3-A7).
    pid = daten.get("phase_id")
    if not isinstance(pid, str) or not pid:
        raise ValueError(
            "phase.yaml: Pflichtfeld fehlt oder falscher "
            "Typ: phase_id")
    ptitel = daten.get("phase_titel")
    if not isinstance(ptitel, str) or not ptitel:
        raise ValueError(
            "phase.yaml: Pflichtfeld fehlt oder falscher "
            "Typ: phase_titel")
    pstart = daten.get("phase_start_head")
    if "phase_start_head" not in daten:
        raise ValueError(
            "phase.yaml: Pflichtfeld fehlt oder falscher "
            "Typ: phase_start_head")
    if not isinstance(pstart, str):
        raise ValueError(  # noqa: TRY004 (P2a-A7)
            "phase.yaml: Pflichtfeld fehlt oder falscher "
            "Typ: phase_start_head")
    punter = daten.get("phase_unterbloecke")
    if not isinstance(punter, list):
        raise ValueError(  # noqa: TRY004 (P2a-A7)
            "phase.yaml: Pflichtfeld fehlt oder falscher "
            "Typ: phase_unterbloecke")
    for eintrag in punter:
        if not isinstance(eintrag, dict):
            raise ValueError(  # noqa: TRY004 (P2a-A7)
                "phase.yaml: Pflichtfeld fehlt oder falscher "
                "Typ: phase_unterbloecke")

    return daten


def _phase_plan_speichern(
    project_name: str,
    plan: dict[str, Any],
) -> None:
    """Schreibt den Phasenplan atomar nach phase.yaml.

    Auflage P2a-S1-A4: kennt KEINE Zeit-Semantik.
    Schreibt das dict wie uebergeben. phase_erstellt_am
    setzt der Aufrufer.

    Auflage P2a-A6, P2a-S3-A3, P2a-S3-A4: atomar
    (temp + os.replace), mode 0600, fsync vor close.
    Kein Verzeichnis-fsync (bewusst, P2a).

    Auflage P2a-S1-A3: yaml.safe_dump mit
      default_flow_style=False, allow_unicode=True,
      sort_keys=False, width=4096.

    Auflage P2a-S3-A9: tmp-Lebenszyklus.
      - O_EXCL legt tmp exklusiv an (Race-Schutz).
      - try/finally unlink fuer den Fall, dass
        os.replace scheitert (IOError) und tmp noch
        existiert.
      - Nach erfolgreichem os.replace existiert tmp
        nicht mehr; finally-unlink laeuft ins Leere
        (exists() == False).
    """
    ziel = _phase_yaml_pfad(project_name)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    tmp_name = (
        f".{ziel.name}.tmp.{os.getpid()}.{time.time_ns()}")
    tmp = ziel.parent / tmp_name
    try:
        fd = os.open(
            str(tmp),
            os.O_CREAT | os.O_WRONLY | os.O_EXCL,
            0o600,
        )
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            yaml.safe_dump(
                plan, fh,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
                width=4096,
            )
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(str(tmp), str(ziel))
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def _letzter_reviewer_befund(state: RunState) -> str:
    """W35a-1: liefert den letzten Reviewer-Befund
    aus state.review_runden[-1]["raw"].

    Leer, wenn keine Review-Runde vorliegt.
    Wird fuer phase.yaml-Feld letzter_befund genutzt.
    """
    if not state.review_runden:
        return ""
    letzte = state.review_runden[-1]
    if not isinstance(letzte, dict):
        return ""
    raw = letzte.get("raw", "")
    if not isinstance(raw, str):
        return ""
    return raw[:500]


def _phase_yaml_status_update(
    project_name: str,
    unterblock_id: str,
    status: str,
    commit_paket: dict[str, Any] | None = None,
    letzter_befund: str | None = None,
    letzter_test_fehler: str | None = None,
) -> None:
    """Setzt den Status eines Unterblocks in phase.yaml.

    Block P2b-1. Auflagen P2b-A5, P2b-1-A6:
      - Liest ausschliesslich ueber _phase_plan_laden
        (kein direkter YAML-Zugriff).
      - status muss in STATUS_WERTE liegen.
      - unterblock_id muss existieren.
      - phase_erstellt_am wird NICHT angetastet:
        das dict wird durchgereicht, nur der
        Status im Ziel-Eintrag wird gepatcht.

    Phasen-Persistenz-A1 (2026-10-16):
      Optionaler commit_paket-Parameter. Wenn
      gesetzt, wird das Paket in den Ziel-
      Unterblock geschrieben. Format:
        commit_paket: {dateien: [...], message: "..."}

    W35a-1 (2026-10-17): optionaler letzter_befund-
      Parameter. Bei NO-GO (status="no_go") wird
      der Reviewer-Befund (max 500 Zeichen) im
      Unterblock-Feld "letzter_befund" persistiert.
      Bei status="done" wird letzter_befund = ""
      gesetzt (Loeschen).

    Fail-closed: jede Verletzung -> ValueError.
    """
    STATUS_WERTE = frozenset({
        "pending", "running", "done", "no_go", "failed",
    })
    if status not in STATUS_WERTE:
        raise ValueError(
            f"phase.yaml: status '{status}' unbekannt "
            f"(erlaubt: {sorted(STATUS_WERTE)})")
    daten = _phase_plan_laden(project_name)
    if daten is None:
        raise ValueError(
            "phase.yaml: kein aktiver Plan")
    unterbloecke = daten.get("phase_unterbloecke", [])
    ziel = None
    for u in unterbloecke:
        if isinstance(u, dict) and u.get("id") == unterblock_id:
            ziel = u
            break
    if ziel is None:
        raise ValueError(
            f"phase.yaml: unterblock_id "
            f"'{unterblock_id}' nicht gefunden")
    ziel["status"] = status
    # W35a-1 (2026-10-17): letzter_befund
    # pflegen. Bei no_go: setzen. Bei done:
    # loeschen. Bei anderen: unveraendert.
    if status == "no_go" and letzter_befund:
        ziel["letzter_befund"] = (
            letzter_befund[:500])
    elif status == "done":
        ziel["letzter_befund"] = ""
    # W61: letzter_test_fehler persistieren (bei failed).
    if status == "failed" and letzter_test_fehler:
        ziel["letzter_test_fehler"] = (
            letzter_test_fehler[:2000])
    elif status in ("done", "pending"):
        ziel.pop("letzter_test_fehler", None)
    # Phasen-Persistenz-A1 (2026-10-16): commit_paket
    # mitschreiben, damit der naechste Resume es
    # laden kann (Sammel-Commit und Basis-Gate).
    if commit_paket is not None:
        ziel["commit_paket"] = {
            "dateien": list(
                commit_paket.get("dateien", [])),
            "message": str(
                commit_paket.get("message", ""))[:500],
        }
    _phase_plan_speichern(project_name, daten)


def _phase_rollback(
    project_name: str,
    state: RunState,
    grund: str,
) -> bool:
    """Block P2b-2: Rollback auf phase_start_head (RR-K1/K2/K3).

    Ablauf (Konzept 5.2):
      1. phase_start_head pruefen (state, von run_phase
         aus YAML synchronisiert).
      2. HEAD == phase_start_head?
      3. git status clean?
      4. git reset --hard <phase_start_head>.
      5. git clean -fd -- <file_whitelist-Pfade>.
      6. state.phase_commit_pakete leeren.
      7. audit phase_rollback.

    Best-Effort (F6): faengt Exceptions um die
    git-Subprozesse, gibt False zurueck, audit
    dokumentiert.
    Rueckgabe (F4): bool. True nur bei
    vollstaendigem Erfolg.
    """
    start = state.phase_start_head
    if not start:
        audit("phase_rollback",
              {"grund": grund, "ok": False,
               "warum": "kein_phase_start_head"},
              state.project_dir, project_name)
        return False

    head_jetzt = _git_rev_parse_head(state.project_dir)
    if head_jetzt != start:
        audit("phase_rollback",
              {"grund": grund, "ok": False,
               "warum": "HEAD_abweichend",
               "head_jetzt": head_jetzt,
               "head_ziel": start},
              state.project_dir, project_name)
        return False

    status_out = _git_status_porcelain(state.project_dir)
    if status_out.strip():
        audit("phase_rollback",
              {"grund": grund, "ok": False,
               "warum": "status_schmutzig"},
              state.project_dir, project_name)
        return False

    # Reset.
    try:
        res_reset = subprocess.run(
            ("git", "reset", "--hard", start),
            cwd=str(state.project_dir),
            capture_output=True, text=True,
            timeout=60, check=False,
            env=subprocess_env(),
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        audit("phase_rollback",
              {"grund": grund, "ok": False,
               "warum": "exception",
               "exception": str(exc)},
              state.project_dir, project_name)
        return False
    if res_reset.returncode != 0:
        audit("phase_rollback",
              {"grund": grund, "ok": False,
               "warum": "reset_rc",
               "rc": res_reset.returncode},
              state.project_dir, project_name)
        return False

    # git clean -fd nur in file_whitelist-Pfaden.
    # dry-run zuerst, um die Anzahl zu zaehlen.
    clean_pfade = tuple(state.file_whitelist)
    clean_zahl = 0
    if clean_pfade:
        try:
            res_dry = subprocess.run(
                ("git", "clean", "-nd", "--") + clean_pfade,
                cwd=str(state.project_dir),
                capture_output=True, text=True,
                timeout=60, check=False,
                env=subprocess_env(),
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            audit("phase_rollback",
                  {"grund": grund, "ok": False,
                   "warum": "exception_clean_dry",
                   "exception": str(exc)},
                  state.project_dir, project_name)
            return False
        if res_dry.returncode != 0:
            audit("phase_rollback",
                  {"grund": grund, "ok": False,
                   "warum": "clean_dry_rc",
                   "rc": res_dry.returncode},
                  state.project_dir, project_name)
            return False
        clean_zahl = len(
            [z for z in res_dry.stdout.splitlines() if z.strip()])
        try:
            res_clean = subprocess.run(
                ("git", "clean", "-fd", "--") + clean_pfade,
                cwd=str(state.project_dir),
                capture_output=True, text=True,
                timeout=60, check=False,
                env=subprocess_env(),
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            audit("phase_rollback",
                  {"grund": grund, "ok": False,
                   "warum": "exception_clean",
                   "exception": str(exc)},
                  state.project_dir, project_name)
            return False
        if res_clean.returncode != 0:
            audit("phase_rollback",
                  {"grund": grund, "ok": False,
                   "warum": "clean_rc",
                   "rc": res_clean.returncode},
                  state.project_dir, project_name)
            return False

    pakete_verworfen = len(state.phase_commit_pakete)
    state.phase_commit_pakete = []
    audit("phase_rollback",
          {"grund": grund, "ok": True,
           "head_ziel": start,
           "clean_zahl": clean_zahl,
           "pakete_verworfen": pakete_verworfen},
          state.project_dir, project_name)
    return True



def _loop_cap_audit(
    state: RunState,
    loop_name: str,
    aktuelle_runde: int,
    max_runden: int,
) -> None:
    """W30: einheitlicher Cap-Audit nach dem Loop.

    W30-fix (2026-10-18): Umbenannt von
    _loop_cap_erreicht (W30, 2026-10-17). Die
    alte Funktion prueft `aktuelle_runde <=
    max_runden -> return False` und wurde in
    for-Loops gerufen, wo `runde` immer
    <= max_runden ist. Der Check griff nie.

    Kein Check-im-Loop. W30-Ziel "zentraler
    Check" wurde nicht erreicht; die Loops
    funktionieren dezentral. W30-fix macht
    Cap-Ereignisse ueber alle Loops hinweg
    sichtbar (Aggregation loop_name/runde).

    Aufruf nach dem for-Loop mit
    aktuelle_runde = max_runden + 1.

    Kein Rueckgabewert. Der Aufrufer hat
    bereits einen festen Fail-Pfad
    (return None / return 18 / Solver-Trigger).
    """
    if aktuelle_runde <= max_runden:
        return
    audit("loop_cap_erreicht",
          {"loop_name": loop_name,
           "aktuelle_runde": aktuelle_runde,
           "max_runden": max_runden},
          state.project_dir, state.project_name)
    print(f"[FAIL] Loop-Cap erreicht: "
          f"{loop_name} {aktuelle_runde}/{max_runden}. "
          f"Fail closed.")


def _phase_gesamt_review(state: RunState) -> dict[str, Any]:
    """P2b-4 / M1 + M2: deterministische Aggregation.

    Kein LLM. Rueckgabe: dict mit
      unterbloecke_total, unterbloecke_done,
      pakete, dateien_gesamt, dateien_union,
      duplikate.
    """
    ups = state.phase_unterbloecke
    status_liste = [
        (u.get("status") if isinstance(u, dict) else None)
        for u in ups
    ]
    done = sum(1 for s in status_liste if s == "done")
    pakete = state.phase_commit_pakete
    dateien_alle: list[str] = [
        d
        for p in pakete
        for d in p.get("dateien", [])
    ]
    # W61: Duplikate pro Paket zaehlen, nicht global.
    # Sequenzielle Unterbloecke patchen oft dieselbe Datei
    # (z.B. applier.py in U2, U3, U4). Das ist kein Fehler.
    # Duplikat = dieselbe Datei 2x im SELBEN Paket.
    duplikate = sum(
        len(p.get("dateien", [])) - len(set(p.get("dateien", [])))
        for p in pakete
        if isinstance(p, dict)
    )
    dateien_union = sorted(set(dateien_alle))
    return {
        "unterbloecke_total": len(ups),
        "unterbloecke_done": done,
        "pakete": len(pakete),
        "dateien_gesamt": len(dateien_alle),
        "dateien_union": dateien_union,
        "duplikate": duplikate,
    }


def _phase_sammel_message(
    state: RunState,
) -> str:
    """P2b-4 / A3: Commit-Message-Format.

    PHASE <id>: <titel>

    <U1: message>
    <U2: message>
    ...

    Pakete werden in Reihenfolge der done-Unterbloecke
    zugeordnet. B2-Unterbloecke (done ohne Paket)
    bekommen eine Hinweiszeile.
    """
    zeilen = [
        f"PHASE {state.phase_id}: {state.phase_titel}",
        "",
    ]
    paket_iter = iter(state.phase_commit_pakete)
    for u in state.phase_unterbloecke:
        if not isinstance(u, dict):
            continue
        uid = u.get("id", "?")
        status = u.get("status", "?")
        if status != "done":
            zeilen.append(f"{uid}: [{status}]")
            zeilen.append("")
            continue
        try:
            p = next(paket_iter)
        except StopIteration:
            zeilen.append(
                f"{uid}: (Auftrag bereits erfuellt, "
                f"kein Commit)")
            zeilen.append("")
            continue
        msg = p.get("message", "") or "(leer)"
        zeilen.append(f"{uid}: {msg}")
        zeilen.append("")
    return "\n".join(zeilen).rstrip() + "\n"


def _phase_deterministisch_pruefen(
    state: RunState,
    aggregat: dict[str, Any],
) -> tuple[int, str] | None:
    """W29a: deterministische Vor-Pruefung der Phase.

    D1: alle Unterbloecke done.
    D2: keine Duplikate in Datei-Union.
    D3: jede Datei in file_whitelist.
    D4: keine Waisen-Datei (Union = Pakete).
    D5: jede Datei existiert (tote Dateien).

    Rueckgabe:
      None           -> gruen, weiter zur Judge-Pruefung.
      (rc, grund)    -> rot, sofort fail-closed.

    Reihenfolge D1..D5: billig zu teuer.
    """
    # D1: alle done?
    if aggregat["unterbloecke_done"] != \
            aggregat["unterbloecke_total"]:
        offen = [
            u.get("id", "?")
            for u in state.phase_unterbloecke
            if isinstance(u, dict)
            and u.get("status") != "done"
        ]
        return (17, f"D1_offene_unterbloecke:{','.join(offen)}")

    # D2: Duplikate in Datei-Union.
    if aggregat["duplikate"] > 0:
        return (17,
                f"D2_duplikate:{aggregat['duplikate']}")

    # D3: Whitelist.
    wl = [str(p) for p in (state.file_whitelist or [])]
    if wl:
        fremd = [
            d for d in aggregat["dateien_union"]
            if not any(
                d == w or d.startswith(w.rstrip("/") + "/")
                for w in wl
            )
        ]
        if fremd:
            return (17,
                    "D3_whitelist_verletzt:"
                    + ",".join(fremd[:5]))

    # D4: Waisen (Union == Pakete).
    aus_paketen: list[str] = [
        d
        for p in state.phase_commit_pakete
        for d in p.get("dateien", [])
    ]
    set_aus_paketen = set(aus_paketen)
    set_union = set(aggregat["dateien_union"])
    waisen = sorted(set_union - set_aus_paketen)
    if waisen:
        return (17, "D4_waisen:" + ",".join(waisen[:5]))

    # D5: tote Dateien (Pfad existiert nicht).
    tot: list[str] = []
    for d in aggregat["dateien_union"]:
        p = state.project_dir / d
        if not p.exists():
            tot.append(d)
    if tot:
        return (17, "D5_tote_dateien:" + ",".join(tot[:5]))

    return None


def _phase_judge_review(
    state: RunState,
    aggregat: dict[str, Any],
) -> str:
    """W29b: ruft den Judge fuer die Gesamtphase.

    Rueckgabe: "GO" | "NO_GO" | "FEHLER".
    """
    # W46c: Doku-Phase -> Judge ueberspringen.
    _w46c_alle_doku = bool(state.phase_commit_pakete) and all(
        isinstance(_p, dict)
        and all(str(_d).endswith(".md")
                for _d in _p.get("dateien", []))
        for _p in state.phase_commit_pakete)
    _w46c_kein_passed = not any(
        isinstance(_tr, dict)
        and _tr.get("passed_count", 0) > 0
        for _tr in state.basis_gate_test_results)
    if _w46c_alle_doku and _w46c_kein_passed:
        print("[i] Phase-Judge uebersprungen "
              "(Doku-Phase, keine Tests).")
        audit("phase_judge_uebersprungen_doku",
              {"phase_id": state.phase_id,
               "pakete": len(state.phase_commit_pakete)},
              state.project_dir, state.project_name)
        return "GO"
    system_prompt = _build_judge_prompt(state)
    system_prompt += (
        "\n\n=== PHASE-JUDGE ===\n"
        "Du pruefst eine GESAMTE PHASE.\n"
        "Antworte mit GENAU EINEM Wort in der "
        "ersten Zeile:\n"
        "PHASE-GO oder PHASE-NO-GO.\n"
        "Bei NO-GO: 1-5 Problem-Punkte danach.\n"
        "Kein Fliesstext.")
    user_content = _build_phase_judge_input(
        state, aggregat)
    reply = ask_llm(
        state.api_key, system_prompt, user_content,
        state.judge_model, 0.0, state.llm_timeout_s,
        state=state, max_tokens=state.max_tokens_judge,
    )
    if not reply.ok:
        return "FEHLER"
    text = reply.content.lstrip()
    erste = text.split("\n", 1)[0].strip().upper()
    if "PHASE-GO" in erste and "NO-GO" not in erste:
        return "GO"
    if "PHASE-NO-GO" in erste or "NO-GO" in erste:
        return "NO_GO"
    return "FEHLER"


def _phase_judge_repair_runde(
    state: RunState,
    aggregat: dict[str, Any],
) -> str:
    """W29b: EINE Repair-Runde (Cap 1, A-W29-4).

    Rueckgabe: "GO" | "NO_GO" | "FEHLER".
    """
    # W46c: Doku-Phase -> Judge ueberspringen.
    _w46c_alle_doku = bool(state.phase_commit_pakete) and all(
        isinstance(_p, dict)
        and all(str(_d).endswith(".md")
                for _d in _p.get("dateien", []))
        for _p in state.phase_commit_pakete)
    _w46c_kein_passed = not any(
        isinstance(_tr, dict)
        and _tr.get("passed_count", 0) > 0
        for _tr in state.basis_gate_test_results)
    if _w46c_alle_doku and _w46c_kein_passed:
        print("[i] Phase-Judge uebersprungen "
              "(Doku-Phase, keine Tests).")
        audit("phase_judge_uebersprungen_doku",
              {"phase_id": state.phase_id,
               "pakete": len(state.phase_commit_pakete)},
              state.project_dir, state.project_name)
        return "GO"
    system_prompt = _build_judge_prompt(state)
    system_prompt += (
        "\n\n=== PHASE-JUDGE (REPARATUR-RUNDE) ===\n"
        "Du hast in der Vorrunde PHASE-NO-GO gesagt.\n"
        "Der Mensch und der Builder haben den Befund "
        "nicht abschliessend bearbeitet (kein Loop "
        "in dieser Runde).\n"
        "Du pruefst erneut.\n"
        "Antworte mit PHASE-GO oder PHASE-NO-GO.")
    user_content = _build_phase_judge_input(
        state, aggregat)
    reply = ask_llm(
        state.api_key, system_prompt, user_content,
        state.judge_model, 0.0, state.llm_timeout_s,
        state=state, max_tokens=state.max_tokens_judge,
    )
    if not reply.ok:
        return "FEHLER"
    text = reply.content.lstrip()
    erste = text.split("\n", 1)[0].strip().upper()
    if "PHASE-GO" in erste and "NO-GO" not in erste:
        return "GO"
    if "PHASE-NO-GO" in erste or "NO-GO" in erste:
        return "NO_GO"
    return "FEHLER"


def _phase_sammel_paket(state: RunState) -> dict[str, Any]:
    """P2b-4 / A2 + M5: Sammel-Paket fuer apply_commit_and_doku.

    Liest phase_commit_pakete und baut ein
    einziges Paket mit Union-aller-dateien und
    kombinierter Message.

    Vertrag (apply_commit_and_doku liest):
      message, dateien, doku_patches.
    """
    alle_dateien: list[str] = [
        d
        for p in state.phase_commit_pakete
        for d in p.get("dateien", [])
    ]
    alle_doku: list[dict[str, Any]] = [
        dp
        for p in state.phase_commit_pakete
        for dp in p.get("doku_patches", [])
    ]
    return {
        "message": _phase_sammel_message(state),
        "dateien": sorted(set(alle_dateien)),
        "doku_patches": alle_doku,
    }


def _print_phase_approval_dokument(
    state: RunState,
    aggregat: dict[str, Any],
) -> None:
    """P2b-4 / M9: Aggregat-Anzeige fuer die Phasen-Approval."""
    print("\n" + "=" * 70)
    print("PHASEN-APPROVAL")
    print("=" * 70)
    print(f"Phase:        {state.phase_id} - "
          f"{state.phase_titel}")
    print(f"Unterbloecke: {aggregat['unterbloecke_total']}")
    print(f"Pakete:       {aggregat['pakete']}")
    print(f"Dateien (Union): {len(aggregat['dateien_union'])}")
    if aggregat["duplikate"]:
        print(f"  (Duplikate zwischen Paketen: "
              f"{aggregat['duplikate']})")
    print()
    for u in state.phase_unterbloecke:
        if not isinstance(u, dict):
            continue
        titel = u.get("titel", "")
        status = u.get("status", "?")
        print(f"  {u.get('id', '?')}: {titel} "
              f"[{status}]")
    print()
    if state.phase_commit_pakete:
        print("Commit-Message-Vorschau:")
        print("-" * 70)
        print(_phase_sammel_message(state).rstrip())
        print("-" * 70)
    else:
        print("[i] Keine Pakete. Kein Commit.")



def _phase_rr_k8(
    state: RunState,
    projekt_plan: str,
) -> str:
    """P2b-5 / N8: RR-K8-Menue. Mensch entscheidet.

    Rueckgabe: "neu" | "abbrechen" | "neu_starten".
    "neu" = Mensch hat einen neuen Plan eingegeben
    (in `state` als neue Unterbloecke abgelegt).
    """
    print("\n" + "=" * 70)
    print("RR-K8: KONFLIKT PLANNER VS. REVIEWER")
    print("=" * 70)
    print("[1] Plan manuell neu eingeben")
    print("[2] Phase abbrechen")
    print("[3] mit geaendertem Auftrag neu starten")
    for _v in range(5):
        try:
            wahl = input("Deine Wahl: ").strip()
        except (EOFError, KeyboardInterrupt):
            return "abbrechen"
        if wahl == "1":
            print("[i] Bitte den korrigierten Plan eingeben "
                  "(Format P10-P14). Ende mit einer "
                  "Leerzeile nach 'Geschaetzte Runden: N'.")
            print("[i] Alter Plan als Referenz:")
            print(projekt_plan)
            try:
                text_eingabe = input("Plan-Text: ")
            except (EOFError, KeyboardInterrupt):
                return "abbrechen"
            # Validierung.
            try:
                neue_ups = _parse_phase_plan(text_eingabe)
                neue_id, neue_titel = _parse_phase_kopf(
                    text_eingabe)
            except ValueError as exc:
                print(f"[!] Plan ungueltig: {exc}")
                print("[i] Nochmal oder [2]/[3].")
                continue
            plan = _phase_plan_laden(state.project_name)
            if plan is None:
                print("[!] phase.yaml nicht lesbar.")
                return "abbrechen"
            plan["phase_id"] = neue_id
            plan["phase_titel"] = neue_titel
            plan["phase_unterbloecke"] = [
                {
                    "id": u["id"],
                    "titel": u["titel"],
                    "status": "pending",
                    "commit_paket": {},
                    "unterpunkte": u["unterpunkte"],
                    "geschaetzte_runden":
                        u["geschaetzte_runden"],
                }
                for u in neue_ups
            ]
            _phase_plan_speichern(state.project_name, plan)
            return "neu"
        if wahl == "2":
            return "abbrechen"
        if wahl == "3":
            return "neu_starten"
        print("[!] Bitte 1, 2 oder 3.")
    return "abbrechen"


def _phase_plan_korrektur(
    project_name: str,
    state: RunState,
    api_key: str,
) -> bool:
    """P2b-5 / N4-N8: Plan-Korrektur bei Phase-NO-GO.

    Rueckgabe: True = neuer Plan liegt in phase.yaml,
    state.phase_unterbloecke neu. False = abbrechen
    (RR-K8 oder Fehler).
    """
    # Historie laden (Korrektur ist self-contained).
    historie = load_recent_commits(
        state.project_dir, n=10)
    # Kompakte Darstellungen.
    alter_plan_zeilen = [
        f"PHASE {state.phase_id}: {state.phase_titel}",
    ]
    for u in state.phase_unterbloecke:
        if not isinstance(u, dict):
            continue
        _zeile = (
            f"{u.get('id', '?')}: {u.get('titel', '')} "
            f"[{u.get('status', '?')}]")
        # Plan-Korrektur-Schutz-A2 (2026-10-16):
        # Unterpunkte mit ausgeben, damit der Planner
        # sie sehen und behalten kann.
        for _punkt in u.get("unterpunkte", []):
            _zeile += f"\n    - {_punkt}"
        alter_plan_zeilen.append(_zeile)
    alter_plan = "\n".join(alter_plan_zeilen)
    pakete_zeilen: list[str] = []
    for i, p in enumerate(state.phase_commit_pakete, 1):
        dateien = ", ".join(p.get("dateien", []))
        msg = p.get("message", "")[:120]
        pakete_zeilen.append(
            f"Paket {i}: {dateien}\n  {msg}")
    pakete_kompakt = "\n".join(pakete_zeilen) or "(keine)"

    # V2-A1: Reviewer-Befund als BEFUND, nicht NO-GO.
    reviewer_befund = ""
    if state.review_runden:
        reviewer_befund = state.review_runden[-1].get(
            "raw", "")
    kontext = {
        "begruendung": "Mensch hat Phase abgelehnt.",
        "alter_plan": alter_plan,
        "pakete_kompakt": pakete_kompakt,
        "reviewer_befund": reviewer_befund,
    }
    # Block 2a / B1: Phasenstand bauen.
    _naechster: str | None = None
    _ups_stand: list[dict[str, Any]] = []
    for _u in state.phase_unterbloecke:
        if not isinstance(_u, dict):
            continue
        _status = _u.get("status", "")
        _pkg = _u.get("commit_paket", {}) or {}
        _pkg_groesse = len(_pkg.get("dateien", []))
        _letzter = ""
        if _status in {"no_go", "failed"} and state.review_runden:
            _letzter = state.review_runden[-1].get("raw", "")
        _ups_stand.append({
            "id": _u.get("id", "?"),
            "status": _status,
            "paket_groesse": _pkg_groesse,
            "letzter_befund": _letzter,
        })
        if _naechster is None and _status in {
                "no_go", "failed", "pending"}:
            _naechster = _u.get("id")
    phase_stand = {
        "phase_id": state.phase_id,
        "unterbloecke": _ups_stand,
        "naechster": _naechster,
    }
    audit("phase_plan_korrektur_start",
          {"phase_id": state.phase_id,
           "pakete_verworfen":
               len(state.phase_commit_pakete),
           "grund": "unterblock_no_go",
           "unterblock_id": (
               state.phase_unterbloecke[
                   state.phase_aktueller_index]
                   .get("id", "")
               if (0 <= state.phase_aktueller_index
                   < len(state.phase_unterbloecke))
               else "")},
          state.project_dir, project_name)
    antwort = _planner_lauf(
        state, api_key, "Korrektur-Auftrag",
        state.project_dir, project_name, historie,
        stufe=2, korrektur_kontext=kontext,
        phase_stand=phase_stand)
    if antwort is None:
        audit("phase_plan_korrektur_failed",
              {"phase_id": state.phase_id,
               "grund": "planner_none"},
              state.project_dir, project_name)
        wahl = _phase_rr_k8(state, alter_plan)
        if wahl == "neu":
            return True
        if wahl == "neu_starten":
            print("[i] Bitte mit geaendertem Auftrag "
                  "neuen --phase-Aufruf starten.")
        return False
    try:
        neue_id, neue_titel = _parse_phase_kopf(antwort)
        neue_ups = _parse_phase_plan(antwort)
    except ValueError as exc:
        audit("phase_plan_korrektur_failed",
              {"phase_id": state.phase_id,
               "grund": "parse_failed",
               "exception": str(exc)},
              state.project_dir, project_name)
        wahl = _phase_rr_k8(state, alter_plan)
        if wahl == "neu":
            return True
        if wahl == "neu_starten":
            print("[i] Bitte mit geaendertem Auftrag "
                  "neuen --phase-Aufruf starten.")
        return False
    # Block 2b / B1: UNBEANTWORTET-Punkte pruefen.
    unbeantwortet = _plan_unbeantwortet_punkte(neue_ups)
    if unbeantwortet:
        audit("phase_plan_unbeantwortet",
              {"phase_id": state.phase_id,
               "punkte": unbeantwortet,
               "anzahl": len(unbeantwortet)},
              state.project_dir, project_name)
        print("[FAIL] Plan enthaelt UNBEANTWORTET-Punkte. "
              "Plan wird verworfen.")
        for _e in unbeantwortet:
            _txt = _e["punkt"]
            print(f"  [{_e['unterblock']}] "
                  + (_truncate_mit_marker(_txt, 200)
                     if len(_txt) > 200 else _txt))
        wahl = _phase_rr_k8(state, alter_plan)
        if wahl == "neu":
            return True
        if wahl == "neu_starten":
            print("[i] Bitte mit geaendertem Auftrag "
                  "neuen --phase-Aufruf starten.")
        return False
    # Anzeige + Bestaetigung.
    print("\n" + "=" * 70)
    print("PLAN-KORREKTUR")
    print("=" * 70)
    print(f"Phase: {neue_id} - {neue_titel}")
    for u in neue_ups:
        print(f"{u['id']}: {u['titel']}  "
              f"({len(u['unterpunkte'])} Unterpunkte)")
    wahl2 = ""
    for _v in range(5):
        try:
            wahl2 = input(
                "[j] uebernehmen / [n] abbrechen > "
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            return False
        if wahl2 in {"j", "ja", "y", "yes"}:
            break
        if wahl2 in {"n", "no", "nein"}:
            return False
        print("[!] Bitte [j] oder [n].")
    if wahl2 not in {"j", "ja", "y", "yes"}:
        return False
    # Alte Pakete verwerfen.
    state.phase_commit_pakete = []
    # Plan-Korrektur-Schutz-A1 (2026-10-16):
    # Struktur-Check + Merge mit dem bestehenden Plan.
    # done-Unterbloecke bleiben unveraendert.
    # no_go/failed/pending werden durch neue_ups ersetzt.
    plan = _phase_plan_laden(project_name)
    if plan is None:
        return False
    _alte_ups = plan.get("phase_unterbloecke", [])
    # 1. Struktur-Check: Anzahl, ids, Reihenfolge.
    if len(_alte_ups) != len(neue_ups):
        print("[FAIL] Plan-Korrektur: Anzahl der Unterbloecke "
              f"geaendert ({len(_alte_ups)} -> {len(neue_ups)}). "
              "Fail closed.")
        audit("phase_plan_korrektur_failed",
              {"phase_id": state.phase_id,
               "grund": "struktur_verletzt",
               "detail": "anzahl"}, state.project_dir, project_name)
        return False
    for _i, (_alt, _neu) in enumerate(
            zip(_alte_ups, neue_ups)):
        if not isinstance(_alt, dict):
            continue
        if _alt.get("id") != _neu.get("id"):
            print("[FAIL] Plan-Korrektur: id an Position "
                  f"{_i} geaendert "
                  f"({_alt.get('id')} -> {_neu.get('id')}). "
                  "Fail closed.")
            audit("phase_plan_korrektur_failed",
                  {"phase_id": state.phase_id,
                   "grund": "struktur_verletzt",
                   "detail": "id_geaendert",
                   "position": _i},
                  state.project_dir, project_name)
            return False
        if _alt.get("titel") != _neu.get("titel"):
            print("[FAIL] Plan-Korrektur: titel an Position "
                  f"{_i} geaendert. Fail closed.")
            audit("phase_plan_korrektur_failed",
                  {"phase_id": state.phase_id,
                   "grund": "struktur_verletzt",
                   "detail": "titel_geaendert",
                   "position": _i},
                  state.project_dir, project_name)
            return False
    # 2. Merge: done-Unterbloecke schuetzen.
    _gemergt: list[dict[str, Any]] = []
    for _alt, _neu in zip(_alte_ups, neue_ups):
        if not isinstance(_alt, dict):
            _gemergt.append({
                "id": _neu["id"],
                "titel": _neu["titel"],
                "status": "pending",
                "commit_paket": {},
                "unterpunkte": _neu["unterpunkte"],
                "geschaetzte_runden": _neu["geschaetzte_runden"],
            })
            continue
        if _alt.get("status") == "done":
            # done: der neue Plan darf hier nichts aendern.
            _gemergt.append({
                "id": _alt["id"],
                "titel": _alt["titel"],
                "status": "done",
                "commit_paket": dict(
                    _alt.get("commit_paket", {})),
                "unterpunkte": list(
                    _alt.get("unterpunkte", [])),
                "geschaetzte_runden": _alt.get(
                    "geschaetzte_runden", 1),
            })
            continue
        # no_go/failed/pending: neuer Plan uebernimmt.
        _gemergt.append({
            "id": _neu["id"],
            "titel": _neu["titel"],
            "status": "pending",
            "commit_paket": {},
            "unterpunkte": _neu["unterpunkte"],
            "geschaetzte_runden": _neu["geschaetzte_runden"],
        })
    plan["phase_id"] = neue_id
    plan["phase_titel"] = neue_titel
    plan["phase_unterbloecke"] = _gemergt
    _phase_plan_speichern(project_name, plan)
    # V4-A1: Pakete verwerfen.
    state.phase_commit_pakete = []
    # state aktualisieren.
    state.phase_id = neue_id
    state.phase_titel = neue_titel
    state.phase_unterbloecke = plan["phase_unterbloecke"]
    state.phase_aktueller_index = 0
    return True



def _phase_vorlauf(
        state: RunState,
        project_name: str,
) -> PhaseVorlaufErgebnis | int:
    """3a-2a: Vorlauf aus run_phase extrahiert (Z. 2084-2214, HEAD 5708bcf).

    Wortwoertliche Extraktion. Der if-state_ref-Guard bleibt in run_phase.
    Returns: PhaseVorlaufErgebnis bei Erfolg, int (1|18|0) bei Vorlauf-
    Fehler oder "alle done".
    """
    # P2b-5: api_key fuer Plan-Korrektur (Planner).
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        print("[FAIL] DEEPSEEK_API_KEY fehlt. Fail closed.")
        return 1
    daten = _phase_plan_laden(project_name)
    if daten is None:
        print("[FAIL] phase.yaml: kein aktiver Plan.")
        audit("run_phase_ende",
              {"phase_id": state.phase_id,
               "unterbloecke": 0,
               "rc": 18,
               "abgebrochen": True},
              state.project_dir, project_name)
        return 18
    unterbloecke = daten.get("phase_unterbloecke", [])
    if not unterbloecke:
        print("[FAIL] phase.yaml: keine Unterbloecke.")
        audit("run_phase_ende",
              {"phase_id": state.phase_id,
               "unterbloecke": 0,
               "rc": 18,
               "abgebrochen": True},
              state.project_dir, project_name)
        return 18

    # Idempotenz (P2b-1-A4).
    status_liste = [
        (u.get("status") if isinstance(u, dict) else None)
        for u in unterbloecke
    ]
    if all(s == "done" for s in status_liste):
        # W47 (2026-10-17): Unterscheide zwischen
        # 'Phase bereits offiziell beendet'
        # (phase_aktiv=False) und 'alle done, aber
        # Sammel-Commit fehlt' (phase_aktiv=True).
        # Im zweiten Fall weiter zum Gesamt-Review.
        if not state.phase_aktiv:
            print("[i] Phase bereits abgeschlossen. "
                  "Kein Loop.")
            audit("run_phase_ende",
                  {"phase_id": state.phase_id,
                   "unterbloecke": len(unterbloecke),
                   "rc": 0,
                   "abgebrochen": False,
                   "bereits_fertig": True},
                  state.project_dir, project_name)
            return 0
        print("[i] Alle Unterbloecke done. "
              "Gesamt-Review folgt.")
    # W61: failed = Builder-Problem (Plan gueltig).
    # failed -> pending, Builder versucht es nochmal.
    # no_go = Plan-Problem (Mensch/Planner), fail-closed.
    _failed = [
        u for u in unterbloecke
        if isinstance(u, dict) and u.get("status") == "failed"
    ]
    for _u in _failed:
        _u["status"] = "pending"
        # W61: persistierten Test-Fehler in state laden.
        if _u.get("letzter_test_fehler"):
            state.letzter_test_fehler = str(
                _u["letzter_test_fehler"])
        print(f"[i] Unterblock {_u.get('id', '?')} "
              f"failed -> pending (Builder nochmal).")
    if _failed:
        _phase_plan_speichern(project_name, daten)
        status_liste = [
            (u.get("status") if isinstance(u, dict) else None)
            for u in unterbloecke
        ]
    if any(s == "no_go" for s in status_liste):
        print("[FAIL] Phase enthaelt no_go. Fail closed.")
        audit("run_phase_ende",
              {"phase_id": state.phase_id,
               "unterbloecke": len(unterbloecke),
               "rc": 18,
               "abgebrochen": True,
               "grund": "no_go_oder_failed"},
              state.project_dir, project_name)
        return 18

    # F1/F2/P2b-2-A1: phase_start_head synchronisieren.
    # YAML gewinnt, wenn bereits gesetzt (Resume / Plan-
    # Aenderung RR-K3). Sonst neu setzen + speichern.
    yaml_head = str(daten.get("phase_start_head", "") or "")
    # P2b-2-A7 / K2: Inkonsistenz-Fall fail-closed.
    # yaml_head leer, aber state != "" -> Programmier-
    # fehler im Aufrufer oder externer Eingriff.
    if not yaml_head and state.phase_start_head:
        raise ValueError(
            "phase_start_head: state != '', YAML leer "
            "— inkonsistent")
    if yaml_head:
        state.phase_start_head = yaml_head
        audit("phase_start_head_gesetzt",
              {"phase_id": state.phase_id,
               "head": yaml_head,
               "quelle": "yaml"},
              state.project_dir, project_name)
    elif not state.phase_start_head:
        head_neu = _git_rev_parse_head(state.project_dir)
        if not head_neu:
            print("[FAIL] git rev-parse HEAD fehlgeschlagen. "
                  "Fail closed.")
            audit("run_phase_ende",
                  {"phase_id": state.phase_id,
                   "unterbloecke": len(unterbloecke),
                   "rc": 18,
                   "abgebrochen": True,
                   "grund": "rev_parse_fehlgeschlagen"},
                  state.project_dir, project_name)
            return 18
        state.phase_start_head = head_neu
        daten["phase_start_head"] = head_neu
        _phase_plan_speichern(project_name, daten)
        audit("phase_start_head_gesetzt",
              {"phase_id": state.phase_id,
               "head": head_neu,
               "quelle": "neu"},
              state.project_dir, project_name)

    audit("run_phase_start",
          {"phase_id": state.phase_id,
           "unterbloecke": len(unterbloecke),
           "start_head": state.phase_start_head},
          state.project_dir, project_name)

    # P2b-5 / N1 + N3: Phasen-Budget vor dem Loop.
    max_phase = int(state.budget.get(
        "max_llm_calls_phase", 0) or 0)

    return PhaseVorlaufErgebnis(
        state=state,
        unterbloecke=unterbloecke,
        api_key=api_key,
        max_phase=max_phase,
    )


def _phase_unterblock_loop(
        state: RunState,
        project_name: str,
        unterbloecke: list,
        max_phase: int,
) -> int:
    """3a-2b: Unterblock-Loop (extrahiert aus run_phase Z. 2242-2430, HEAD ab6f4cd).

    Wortwoertliche Extraktion. 4 Parameter (Signatur-Freeze 18c).
    Returns: 13 (Budget), 22 (rc-Klasse), 14 (UNKLAR),
    15 (NO-GO), rc_unterblock (Loop-Ende).
    """
    rc_unterblock = 0
    for i, u in enumerate(unterbloecke):
        # Budget-Check VOR jedem Unterblock.
        if max_phase > 0 and state.llm_calls >= max_phase:
            print(f"[!] Phasen-Budget erschoepft: "
                  f"{state.llm_calls}/{max_phase}.")
            audit("phase_budget_ende",
                  {"phase_id": state.phase_id,
                   "unterbloecke_done": i,
                   "unterbloecke_total": len(unterbloecke),
                   "llm_calls": state.llm_calls,
                   "max_phase": max_phase},
                  state.project_dir, project_name)
            return 13
        # Resume-A2: done-Unterbloecke ueberspringen.
        if (isinstance(u, dict)
                and u.get("status") == "done"):
            state.phase_aktueller_index = i + 1
            continue
        uid = u["id"] if isinstance(u, dict) else "?"
        state.phase_aktueller_index = i
        t0 = time.monotonic()
        audit("phase_unterblock_start",
              {"id": uid, "index": i,
               "phase_id": state.phase_id},
              state.project_dir, project_name)
        _phase_yaml_status_update(project_name, uid, "running")
        # W32 (2026-10-17): Contract vor Builder + Judge
        # schreiben. W27 hat _schreibe_contract gebaut,
        # aber nur im Erst-Anlage-Pfad (_phase_main_pfad)
        # verankert. Bei Resume (phase.yaml existiert
        # bereits) wurde der Contract nie geschrieben,
        # der Judge sah "(kein Contract vorhanden)"
        # und eskalierte.
        if isinstance(u, dict):
            _schreibe_contract(state, u)

        # P2b-3b / L1: lokaler state_ref pro Aufruf.
        sr_intern: list[RunState] = []
        paket_vorher = len(state.phase_commit_pakete)
        # Aufgaben-Text: Titel + Unterpunkte des
        # aktuellen Unterblocks.
        unterpunkte = u.get("unterpunkte", [])
        aufgabe_text = u.get("titel", "") + "\n" + "\n".join(
            f"- {p}" for p in unterpunkte)

        # P2b-3b / L5: Exception -> Rollback.
        try:
            rc_unterblock = run_pipeline(
                project_name, aufgabe_text,
                sr_intern, phasen_state=state)
        # P2b-3b / L5: bewusster Catch, um Rollback zu
        # triggern (HR-R9 Fail-closed).
        except Exception as exc:  # noqa: BLE001
            audit("phase_unterblock_ende",
                  {"id": uid, "index": i,
                   "status": "failed",
                   "exception": str(exc)},
                  state.project_dir, project_name)
            _phase_yaml_status_update(project_name, uid, "failed")
            ok = _phase_rollback(
                project_name, state, "exception")
            audit("run_phase_ende",
                  {"phase_id": state.phase_id,
                   "unterbloecke": len(unterbloecke),
                   "rc": 22, "abgebrochen": True,
                   "rollback_ok": ok},
                  state.project_dir, project_name)
            return 22

        # P2b-3b / L1: Vertragspruefung.
        if not sr_intern or sr_intern[0] is not state:
            raise RuntimeError(
                "run_pipeline hat state nicht in state_ref "
                "abgelegt")

        # P2b-3b / L4 + A4-NA1:
        # run_pipeline kann rc=0 liefern ueber:
        #   (a) B2-Pfad (Z. 5548): kein Paket.
        #   (b) Paket-Sammel-Pfad (P2b-3): Paket neu.
        #   (c) require_human_approval=False:
        #       greift im Phasen-Modus nicht (P2b-3 G4).
        # Im Phasen-Modus ist (b) an paket_neu
        # erkennbar, (c) ausgeschlossen, also ist
        # (a) das Komplement: rc=0 ohne Paket = B2.
        paket_neu = (
            len(state.phase_commit_pakete) > paket_vorher)

        dauer_s = round(time.monotonic() - t0, 3)

        if rc_unterblock == 0 and paket_neu:
            # Klasse 1: Erfolg mit Paket.
            # Phasen-Persistenz-A1 (2026-10-16): das
            # letzte Paket gehoert zu diesem Unterblock.
            _paket_fuer_yaml = (
                state.phase_commit_pakete[-1]
                if state.phase_commit_pakete else None)
            _phase_yaml_status_update(
                project_name, uid, "done",
                commit_paket=_paket_fuer_yaml)
            audit("phase_unterblock_ende",
                  {"id": uid, "index": i,
                   "status": "done",
                   "dauer_s": dauer_s},
                  state.project_dir, project_name)
            state.phase_aktueller_index = i + 1
            continue

        if rc_unterblock == 0 and not paket_neu:
            # Klasse 2: B2 (Auftrag bereits erfuellt).
            _phase_yaml_status_update(project_name, uid, "done")
            audit("phase_unterblock_ende",
                  {"id": uid, "index": i,
                   "status": "done",
                   "b2": True,
                   "dauer_s": dauer_s},
                  state.project_dir, project_name)
            state.phase_aktueller_index = i + 1
            continue

        if rc_unterblock == 14:
            # Bug-1 (2026-10-16): Eskalation durch
            # UNKLAR. Kein Rollback, kein failed.
            # Der Mensch entscheidet.
            _phase_yaml_status_update(
                project_name, uid, "no_go",
                letzter_befund=_letzter_reviewer_befund(
                    state))
            audit("phase_unterblock_ende",
                  {"id": uid, "index": i,
                   "status": "no_go",
                   "grund": "unklar_eskalation",
                   "dauer_s": dauer_s},
                  state.project_dir, project_name)
            audit("run_phase_ende",
                  {"phase_id": state.phase_id,
                   "unterbloecke": len(unterbloecke),
                   "rc": 14, "abgebrochen": True,
                   "grund": "unklar_eskalation"},
                  state.project_dir, project_name)
            return 14

        if rc_unterblock == 15:
            # Klasse 3: Unterblock-NO-GO.
            # KEIN Rollback.
            _phase_yaml_status_update(
                project_name, uid, "no_go",
                letzter_befund=_letzter_reviewer_befund(
                    state))
            audit("phase_unterblock_ende",
                  {"id": uid, "index": i,
                   "status": "no_go",
                   "dauer_s": dauer_s},
                  state.project_dir, project_name)
            audit("run_phase_ende",
                  {"phase_id": state.phase_id,
                   "unterbloecke": len(unterbloecke),
                   "rc": 15, "abgebrochen": True,
                   "grund": "unterblock_no_go"},
                  state.project_dir, project_name)
            return 15

        # Klasse 4: Fail-closed.
        # W61: Test-Fehler bei rc=17 persistieren.
        _ltf = (state.letzter_test_fehler
                if rc_unterblock == 17 else None)
        print(f"[DEBUG] rc={rc_unterblock} "
              f"letzter_test_fehler_len="
              f"{len(state.letzter_test_fehler or '')} "
              f"ltf={bool(_ltf)}")
        _phase_yaml_status_update(
            project_name, uid, "failed",
            letzter_test_fehler=_ltf)
        audit("phase_unterblock_ende",
              {"id": uid, "index": i,
               "status": "failed",
               "rc": rc_unterblock,
               "dauer_s": dauer_s},
              state.project_dir, project_name)
        ok = _phase_rollback(
            project_name, state,
            "unterblock_rc_" + str(rc_unterblock))
        audit("run_phase_ende",
              {"phase_id": state.phase_id,
               "unterbloecke": len(unterbloecke),
               "rc": rc_unterblock,
               "abgebrochen": True,
               "rollback_ok": ok},
              state.project_dir, project_name)
        return rc_unterblock
    return rc_unterblock


def _phase_nachlauf(
        state: RunState,
        project_name: str,
        state_ref: list[RunState],
) -> NachlaufErgebnis | int:
    """3a-2c: Nachlauf aus run_phase extrahiert (Z. 2463-2553, HEAD 3c757ec).

    Wortwoertliche Extraktion (body[10]..body[21]).
    3 Parameter (M-78 + M-89: state_ref fuer b2-Pfad). Return NachlaufErgebnis oder int.
    """
    aggregat = _phase_gesamt_review(state)
    print("[i] Gesamt-Review: "
          f"{aggregat['pakete']} Pakete, "
          f"{len(aggregat['dateien_union'])} Dateien.")

    if aggregat["pakete"] == 0:
        # B2-only-Phase: kein Commit.
        audit("phase_gesamt_review",
              {"phase_id": state.phase_id,
               "phase_titel": state.phase_titel,
               "unterbloecke_total":
                   aggregat["unterbloecke_total"],
               "unterbloecke_done":
                   aggregat["unterbloecke_done"],
               "pakete": 0,
               "dateien_gesamt": 0,
               "ergebnis": "keine_pakete",
               "begruendung": ""},
              state.project_dir, project_name)
        print("[i] Keine Pakete. Kein Commit.")
        state_ref.append(state)
        return 0

    # W29a: deterministische Vor-Pruefung (D1-D5).
    d = _phase_deterministisch_pruefen(state, aggregat)
    if d is not None:
        rc_d, grund = d
        print(f"[FAIL] Phase-Pruefung: {grund}")
        audit("phase_gesamt_review_no_go",
              {"phase_id": state.phase_id,
               "quelle": "deterministik",
               "grund": grund},
              state.project_dir, project_name)
        return rc_d

    # W29b: Judge-Pruefung (mit 1 Repair-Runde, A-W29-4).
    g = _phase_judge_review(state, aggregat)
    if g == "FEHLER":
        print("[FAIL] Phase-Judge nicht erreichbar. "
              "Fail closed.")
        audit("phase_gesamt_review_no_go",
              {"phase_id": state.phase_id,
               "quelle": "judge",
               "grund": "llm_fehler"},
              state.project_dir, project_name)
        return 18
    if g == "NO_GO":
        print("[i] Phase-Judge: NO-GO. "
              "Reparatur-Runde (Cap 1).")
        g2 = _phase_judge_repair_runde(state, aggregat)
        if g2 != "GO":
            print("[FAIL] Phase-Judge: NO-GO nach "
                  "Reparatur. Fail closed.")
            audit("phase_gesamt_review_no_go",
                  {"phase_id": state.phase_id,
                   "quelle": "judge",
                   "grund": "no_go_nach_reparatur",
                   "repair": g2},
                  state.project_dir, project_name)
            return 18
        print("[i] Phase-Judge: GO nach Reparatur.")

    _print_phase_approval_dokument(state, aggregat)

    # Approval [j]/[n], max 5 Versuche.
    wahl = ""
    for _versuch in range(5):
        try:
            wahl = input(
                "[j] committen / [n] abbrechen "
                "(Rollback) > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n[*] Abbruch.")
            audit("phase_abgebrochen",
                  {"phase_id": state.phase_id,
                   "grund": "abbruch"},
                  state.project_dir, project_name)
            return 1
        if wahl in {"j", "ja", "y", "yes"}:
            break
        if wahl in {"n", "no", "nein"}:
            break
        print("[!] Bitte [j] oder [n].")
    if wahl not in {"j", "ja", "y", "yes",
                    "n", "no", "nein"}:
        print("[!] Zu viele Fehleingaben. Fail closed.")
        audit("phase_abgebrochen",
              {"phase_id": state.phase_id,
               "grund": "fehleingaben"},
              state.project_dir, project_name)
        return 1
    return NachlaufErgebnis(
        rc=0, aggregat=aggregat, wahl=wahl,
    )


def _phase_wiederaufnahme(
        state: RunState,
        project_name: str,
        state_ref: list[RunState],
        aggregat: dict,
        wahl: str,
        api_key: str,
) -> int:
    """3a-2d: Wiederaufnahme + Sammel-Commit (Z. 2578-2644, HEAD 3f98364).

    Wortwoertliche Extraktion aus run_phase body[14]..body[19].
    6 Parameter (M-94/M-98/M-99): aggregat (2575), wahl (2576)
    aus _res_nachlauf; state_ref (2616/2618/2639); api_key
    (2606 an _phase_plan_korrektur).

    Rekursion: return run_phase(...) @ 2617.
    Max 1 Rekursionstiefe (phase_korrektur_zyklus >= 1 -> return 23).
    Doppelte Sicherung: _phase_main_pfad @ 10596/10602.
    """
    if wahl in {"n", "no", "nein"}:
        # Phase-NO-GO: Rollback, Bericht.
        audit("phase_gesamt_review",
              {"phase_id": state.phase_id,
               "phase_titel": state.phase_titel,
               "unterbloecke_total":
                   aggregat["unterbloecke_total"],
               "unterbloecke_done":
                   aggregat["unterbloecke_done"],
               "pakete": aggregat["pakete"],
               "dateien_gesamt":
                   aggregat["dateien_gesamt"],
               "ergebnis": "no_go",
               "begruendung": "Mensch hat abgelehnt"},
              state.project_dir, project_name)
        ok = _phase_rollback(
            project_name, state, "phase_no_go")
        # P2b-5 / N5 + N6: Plan-Korrektur, max 1 Zyklus.
        if state.phase_korrektur_zyklus >= 1:
            audit("phase_abgebrochen",
                  {"phase_id": state.phase_id,
                   "grund": "korrektur_max_erreicht",
                   "rollback_ok": ok},
                  state.project_dir, project_name)
            return 23
        print("[i] Phase abgelehnt. Plan-Korrektur wird "
              "versucht.")
        if not _phase_plan_korrektur(
                project_name, state, api_key):
            audit("phase_abgebrochen",
                  {"phase_id": state.phase_id,
                   "grund": "korrektur_failed",
                   "rollback_ok": ok},
                  state.project_dir, project_name)
            return 23
        # Plan korrigiert. state_ref leeren (Guard
        # verlangt das). Rekursion.
        state.phase_korrektur_zyklus += 1
        state_ref.clear()
        return run_phase(
            project_name, state, state_ref)

    # [j]: Sammel-Commit.
    audit("phase_gesamt_review",
          {"phase_id": state.phase_id,
           "phase_titel": state.phase_titel,
           "unterbloecke_total":
               aggregat["unterbloecke_total"],
           "unterbloecke_done":
               aggregat["unterbloecke_done"],
           "pakete": aggregat["pakete"],
           "dateien_gesamt": aggregat["dateien_gesamt"],
           "ergebnis": "go",
           "begruendung": ""},
          state.project_dir, project_name)
    sammel = _phase_sammel_paket(state)
    if apply_commit_and_doku(state, sammel):
        audit("commit_applied",
              {"phase": True,
               "pakete": aggregat["pakete"]},
              state.project_dir, project_name)
        state_ref.append(state)
        return 0
    print("[!] Sammel-Commit fehlgeschlagen.")
    # rc=20 ohne Rollback (apply_commit_and_doku ist
    # fail-safe).
    return 20


def run_phase(
    project_name: str,
    state: RunState,
    state_ref: list[RunState],
) -> int:
    """Block P2b-1: Geruest fuer den Phasen-Loop.

    Ablauf:
      1. phase.yaml via _phase_plan_laden pruefen.
      2. Idempotenz (P2b-1-A4):
         - alle done   -> rc=0, bereits_fertig=True.
         - no_go/failed-> rc=18, Fail-closed.
      3. audit run_phase_start.
      4. Loop ueber phase_unterbloecke:
         - phase_aktueller_index = i (P2b-1-A5).
         - audit phase_unterblock_start.
         - _phase_yaml_status_update("running").
         - STUB: kein run_pipeline-Aufruf (P2b-A9).
           TODO(P2b-3): hier run_pipeline.
         - _phase_yaml_status_update("done").
         - audit phase_unterblock_ende.
         - phase_aktueller_index = i + 1.
      5. audit run_phase_ende.
      6. rc=0.

    KEIN Rollback in P2b-1 (folgt in P2b-2).
    KEIN run_pipeline-Aufruf (folgt in P2b-3).

    Exception-Verhalten (Q4, P2b-1-A6): Exception wird
    NICHT abgefangen; der Aufrufer (P2b-2) faengt sie
    fuer den Rollback.
    """
    # P2b-3b / L1: state_ref muss leer sein.
    # Der State wird am Ende angehaengt (fuer main()).
    if state_ref:
        raise ValueError(
            "run_phase: state_ref muss leer sein")
    _vl = _phase_vorlauf(state, project_name)
    if isinstance(_vl, int):
        return _vl
    unterbloecke = _vl.unterbloecke
    api_key = _vl.api_key
    max_phase = _vl.max_phase

    _rc_loop = _phase_unterblock_loop(
        state, project_name, unterbloecke, max_phase,
    )
    if _rc_loop != 0:
        return _rc_loop

    audit("run_phase_ende",
          {"phase_id": state.phase_id,
           "unterbloecke": len(unterbloecke),
           "rc": 0,
           "abgebrochen": False},
          state.project_dir, project_name)

    # =========================================================
    # P2b-4: Phasen-Gesamt-Review + Approval + Commit.
    # =========================================================
    _res_nachlauf = _phase_nachlauf(
        state, project_name, state_ref,
    )
    if isinstance(_res_nachlauf, int):
        return _res_nachlauf
    aggregat = _res_nachlauf.aggregat
    wahl = _res_nachlauf.wahl

    _rc_wdh = _phase_wiederaufnahme(
        state, project_name, state_ref, aggregat, wahl, api_key,
    )
    return _rc_wdh



def _phase_stand_sektion(phase_stand: dict[str, Any]) -> str:
    """Block 2a / B1: AKTUELLER-PHASENSTAND-Sektion.

    Eingabe: dict mit Schluesseln
      phase_id: str
      unterbloecke: list[dict]
        (id, status, paket_groesse, letzter_befund)
      naechster: str | None

    Ausgabe: formatierter Text mit expliziter
    Anweisung "Plane NUR U<n>".
    """
    zeilen: list[str] = ["AKTUELLER PHASENSTAND:\n"]
    for u in phase_stand.get("unterbloecke", []):
        if not isinstance(u, dict):
            continue
        uid = u.get("id", "?")
        status = u.get("status", "?")
        paket = u.get("paket_groesse", 0)
        zeile = f"  {uid}: {status}"
        if status == "done" and paket:
            zeile += f" (Paket: {paket} Dateien)"
        letzter = u.get("letzter_befund", "")
        if letzter and status in {"no_go", "failed"}:
            gek = _truncate_mit_marker(letzter, 200)
            zeile += f"\n      letzter Befund: {gek}"
        zeilen.append(zeile + "\n")
    naechster = phase_stand.get("naechster")
    zeilen.append("\n")
    if naechster:
        zeilen.append(
            f"Der Resume beginnt bei {naechster}.\n"
            "\n"
            "WICHTIG: Behalte die Gesamtstruktur "
            "bei. Der Plan behaelt ALLE "
            "Unterbloecke in derselben "
            "Reihenfolge (U1, U2, ..., Un).\n"
            "\n"
            f"Aendere NUR den INHALT von "
            f"{naechster}.\n"
            "\n"
            "Alle anderen Unterbloecke bleiben "
            "unveraendert (dieselben ids, "
            "dieselben Titel, dieselben "
            "Unterpunkte).\n"
            "\n"
            "Formuliere den neuen Plan mit "
            "ALLEN Unterbloecken, nicht nur "
            f"mit {naechster}.\n"
        )
    else:
        zeilen.append(
            "Alle Unterbloecke sind abgeschlossen. "
            "Plane einen neuen Phasenplan oder brich "
            "ab.\n"
        )
    zeilen.append("\n")
    return "".join(zeilen)


def _w51a_extrahiere_datei_pfade(
        auftrag: str,
) -> list[str]:
    """W51a: extrahiert datei:-Pfade aus dem
    Auftragstext.

    Sucht 'datei:<pfad>' in jeder Zeile.
    Liefert die Pfade in Auftretensreihenfolge,
    ohne Duplikate.
    """
    import re as _re
    gesehen: set[str] = set()
    ergebnis: list[str] = []
    for m in _re.finditer(
            r"datei:([^\s,;]+)", auftrag):
        p = m.group(1).strip().strip("'\"")
        if not p or p in gesehen:
            continue
        gesehen.add(p)
        ergebnis.append(p)
    return ergebnis


def _planner_user_content(
    roher_auftrag: str,
    historie: str,
    stufe: int = 1,
    korrektur_kontext: dict[str, Any] | None = None,
    phase_stand: dict[str, Any] | None = None,
    state: RunState | None = None,
    letzter_plan_fehler: str = "",
) -> str:
    """Baut den User-Content fuer den Planner.

    Auflage P2a-S5a-A10: stufe=1 wortgleich zum
    bisherigen Verhalten (test_planner.py bleibt
    gruen). stufe=2 verweist auf P10-P14.

    P2b-5 / N10: korrektur_kontext (optional).
    Wenn gesetzt, wird ein Korrektur-Auftrag
    formuliert (NO-GO-Begruendung + Reviewer-
    Befund + alter Plan + Pakete kompakt).

    Block 2a / D1: reviewer_befund aus dem
    korrektur_kontext wird vollstaendig in den
    Prompt eingesetzt (P18 verlangt vollstaendige
    Verarbeitung). Redaction greift in ask_llm
    (Z. 3149), nicht hier.

    Block 2a / B1: phase_stand (optional). Wenn
    gesetzt, wird eine AKTUELLER-PHASENSTAND-
    Sektion in den Korrektur-Zweig eingefuegt.
    """
    if korrektur_kontext is not None:
        begr = korrektur_kontext.get("begruendung", "")
        reviewer_befund = korrektur_kontext.get(
            "reviewer_befund", "")
        alter_plan = korrektur_kontext.get("alter_plan", "")
        pakete_kompakt = korrektur_kontext.get(
            "pakete_kompakt", "")
        gemessener_inhalt = korrektur_kontext.get(
            "gemessener_inhalt", "")
        teile = [
            "KORREKTUR-AUFTRAG:\n",
            f"NO-GO-Begruendung: {begr}\n\n",
        ]
        # W42 (2026-10-17): gemessener Inhalt der
        # Zieldateien (vor dem Plan gemessen).
        # Verhindert, dass der Planner falsche
        # Anker aus dem alten Plan uebernimmt.
        if gemessener_inhalt:
            teile.append(
                "=== GEMESSENER INHALT (Zieldateien, "
                "verbindlich) ===\n"
                f"{gemessener_inhalt}\n"
                "=== /GEMESSENER INHALT ===\n\n"
            )
        if reviewer_befund:
            teile.append(
                "=== REVIEWER-BEFUND (vollstaendig) ===\n"
                f"{reviewer_befund}\n"
                "=== /REVIEWER-BEFUND ===\n\n"
            )
        if phase_stand is not None:
            teile.append(_phase_stand_sektion(phase_stand))
        teile.append(f"ALTER PLAN:\n{alter_plan}\n\n")
        # W3-A4: GEMESSENER INHALT fuer den Planner.
        if state is not None:
            _mw = _messwerte_fuer_planner(state)
            if _mw:
                teile.append(
                    f"GEMESSENER INHALT:\n{_mw}\n\n")
        teile.append(
            "GESAMMELTE PAKETE (kompakt):\n"
            f"{pakete_kompakt}\n\n"
        )
        teile.append(
            "Formuliere GENAU EINEN korrigierten "
            "Phasenplan im P10-P16-Format:\n"
            "  PHASE: <id> - <Titel>\n"
            "  \n"
            "  UNTERBLOCK: U<n> - <Titel>\n"
            "  Unterpunkte:\n"
            "    - <Punkt>\n"
            "  Geschaetzte Runden: <N>\n"
            "  \n"
            "  UNTERBLOCK: U<n+1> - <Titel>\n"
            "  ...\n"
            "\n"
            "ALLE Unterbloecke muessen im Plan "
            "erscheinen (auch die done). Nur der "
            "INHALT des offenen Unterblocks aendert "
            "sich. Die IDs muessen mit dem ALTER PLAN "
            "uebereinstimmen.\n"
            "Beachte P17 (Builder-Freundlichkeit) "
            "und P18 (Korrektur-Kompetenz).\n"
        )
        return "".join(teile)
    # W51a: Erstlauf-Pfad. MESS-PFLICHT-Block
    # fuer alle datei:-Referenzen aus dem Auftrag.
    _w51g_block = ""
    if letzter_plan_fehler:
        _w51g_block = (
            "=== DEIN LETZTER PLAN WURDE "
            "ABGELEHNT ===\n"
            f"Fehler: {letzter_plan_fehler}\n"
            "Korrigiere das Format (Reihenfolge,\n"
            "PHASE:-Kopf) oder pruefe, ob neue\n"
            "Messungen noetig sind. Liefere NUR\n"
            "den Plan im P10-P14-Format.\n"
            "=== /DEIN LETZTER PLAN WURDE "
            "ABGELEHNT ===\n\n"
        )
    _w51a_pfade = _w51a_extrahiere_datei_pfade(
        roher_auftrag)
    _w51a_block = ""
    if _w51a_pfade:
        _w51a_block = (
            "=== MESS-PFLICHT (W51) ===\n"
            "Messe JEDE der folgenden Zieldateien "
            "mit 'COMMAND: RUN read_file <pfad>', "
            "bevor du den Plan formulierst. "
            "Wenn die Datei existiert: aktion:patch "
            "mit anker aus dem gemessenen Inhalt. "
            "Wenn nicht: aktion:neu. "
            "Kein aktion:neu fuer existierende "
            "Dateien.\n"
            + "\n".join(f"  - {p}" for p in _w51a_pfade)
            + "\n=== /MESS-PFLICHT ===\n\n"
        )
    if stufe == 2:
        abschluss = (
            "Formuliere GENAU EINEN Phasenplan "
            "(PHASE/UNTERBLOCK) oder stelle eine "
            "Rueckfrage. Halte das Ausgabe-Format "
            "aus P10-P14 ein."
        )
    else:
        abschluss = (
            "Formuliere den naechsten praezisen Auftrag "
            "oder stelle eine Rueckfrage. "
            "Halte das Ausgabe-Format aus P7/P8 ein."
        )
    _w51d_mess_block = ""
    if state is not None and state.mess_protokoll:
        _w51d_mess_block = (
            "=== GEMESSENER INHALT ===\n"
            f"{state.mess_protokoll}\n"
            "=== /GEMESSENER INHALT ===\n\n"
        )
    # W25-planner-md (2026-10-18): Skills im
    # Planner-Prompt. _geladene_skills_block ist
    # nicht None-safe (liest state.geladene_skills),
    # daher state-Pruefung.
    _w25_skills_block = _available_skills_block()
    if state is not None:
        _w25_skills_block += _geladene_skills_block(state)
    return (
        _w51g_block
        + _w51a_block
        + _w51d_mess_block
        + _w25_skills_block
        + f"ROHER AUFTRAG DES MENSCHEN:\n{roher_auftrag}\n\n"
        f"LETZTE COMMITS IM ZIEL-REPO:\n{historie[:3000]}\n\n"
        f"{abschluss}"
    )


def _planner_lauf(
    state: RunState,
    api_key: str,
    roher_auftrag: str,
    project_dir: Path,
    project_name: str,
    historie: str,
    stufe: int = 1,
    korrektur_kontext: dict[str, Any] | None = None,
    phase_stand: dict[str, Any] | None = None,
    max_runden: int = 3,
) -> str | None:
    """Fuehrt den Planner aus und liefert die Antwort.

    W3 (2026-10-16): COMMAND-Loop. Der Planner
    darf COMMAND: RUN read_file senden. Die
    Werkstatt fuehrt aus, ruft den Planner
    erneut. Max max_runden Runden (Default 3).
    Bei Erschoepfung: fail-closed (None).

    Liefert None bei Fehler (Aufrufer behandelt Fail-closed).
    Liefert den Antwort-Text bei Erfolg.
    """
    if "planner" not in state.agents:
        print("[FAIL] Planner-Rolle nicht geladen. Fail closed.")
        audit("planner_rolle_fehlt", {}, project_dir, project_name)
        return None

    planner_prompt = build_system_prompt(
        state.agents["planner"], state.docs,
        state.agent_docs.get("planner", []),
        state=state,
        stufe=stufe)

    # W51g: lokales Set (Loop-Lebenszyklus).
    state._w51g_gemessen = set()
    for _runde in range(1, max_runden + 1):
        _w51g_fehler = (
            state.letzter_plan_fehler
            if _runde > 1 else "")
        user_content = _planner_user_content(
            roher_auftrag, historie, stufe,
            korrektur_kontext=korrektur_kontext,
            phase_stand=phase_stand,
            state=state,
            letzter_plan_fehler=_w51g_fehler)
        state.planner_runden = _runde
        reply = ask_llm(
            api_key, planner_prompt, user_content,
            state.planner_model, 0.0,
            state.llm_timeout_s, state=state,
            max_tokens=state.max_tokens_planner)
        if not reply.ok:
            print(f"[FAIL] Planner-Aufruf: {reply.error}")
            audit("planner_call_failed",
                  {"error": reply.error,
                   "runde": state.planner_runden},
                  project_dir, project_name)
            return None
        # W3-A1: COMMAND-Loop (lokale Schleife).
        if "COMMAND:" not in reply.content:
            return _w51c_bereinige_und_audit(
                reply.content, state, project_dir,
                project_name, _runde)
        # W51c-fix (2026-10-18): strikter
        # Planner-Parser (nur read_file,
        # load_skill). Blockiert coverage/
        # bandit/pip_audit im Planner-Pfad.
        _cmds = _parse_commands_planner(reply.content)
        if not _cmds:
            return _w51c_bereinige_und_audit(
                reply.content, state, project_dir,
                project_name, _runde)
        # W25: load_skill vor execute_commands.
        _run_cmds, _n_skills = _verarbeite_skill_commands(
            state, _cmds)
        if _n_skills:
            print(f"[i] Planner-COMMAND: "
                  f"{_n_skills} Skill(s) geladen.")
        # W25-planner-md (2026-10-18): load_skill-only
        # ist KEIN Abbruch. Der geladene Skill muss in
        # der naechsten Runde im Prompt wirken.
        if not _run_cmds and _n_skills > 0:
            # Naechste Runde, geladene Skills sichtbar.
            continue
        if not _run_cmds:
            return _w51c_bereinige_und_audit(
                reply.content, state, project_dir,
                project_name, _runde)
        _mess_vorher = len(state.mess_protokoll)
        _geaendert = execute_commands(
            state, _run_cmds, quelle="planner")
        _mess_nachher = len(state.mess_protokoll)
        print(f"[i] Planner-COMMAND Runde {_runde}/"
              f"{max_runden}: {len(_cmds)} Kommando(s).")
        if not _geaendert:
            return _w51c_bereinige_und_audit(
                reply.content, state, project_dir,
                project_name, _runde)
        # W51h: Plan + COMMANDs im selben Reply.
        # Parser-basierte Pruefung (kein String-Match
        # "PHASE:"), W51h VOR W51e (A-W51h-4).
        _w51h_bereinigt = _bereinige_planner_reply(
            reply.content)
        _w51h_plan_parsebar = False
        try:
            _parse_phase_kopf(_w51h_bereinigt)
            _parse_phase_plan(_w51h_bereinigt)
            _w51h_plan_parsebar = True
        except ValueError:
            pass
        if _w51h_plan_parsebar:
            return _w51h_bereinigt
        # W51e: Runde ohne neue Messung -> Loop
        # sinnlos, fail-closed mit None.
        if _mess_nachher == _mess_vorher:
            print("[!] Planner-Runde ohne neue "
                  "Messung. Loop abgebrochen.")
            audit("planner_command_ohne_neue_messung",
                  {"runde": _runde,
                   "anzahl_commands": len(_cmds),
                   "mess_vorher_len": _mess_vorher,
                   "mess_nachher_len": _mess_nachher,
                   "phase_id": state.phase_id},
                  project_dir, project_name)
            return None
    # W30-fix (2026-10-18): einheitlicher Cap-Audit.
    _loop_cap_audit(state, "planner_command",
                    max_runden + 1, max_runden)
    # Max-Runden erreicht.
    print(f"[FAIL] Planner-COMMAND max_runden "
          f"({max_runden}) erreicht. Fail closed.")
    audit("planner_command_max_runden",
          {"max_runden": max_runden},
          project_dir, project_name)
    return None


def load_agents(agents_dir: str) -> dict[str, dict[str, Any]]:
    base = Path(agents_dir).expanduser()
    if not base.exists():
        print(f"[FAIL] agents_dir fehlt: {base}. Fail closed.")
        sys.exit(1)
    agents: dict[str, dict[str, Any]] = {}
    for md in sorted(base.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        if not text.startswith("---"):
            continue
        parts = text.split("---", 2)
        if len(parts) < 3:
            continue
        fm = yaml.safe_load(parts[1])
        fm["body"] = parts[2].strip()
        fm["path"] = str(md)
        agents[fm["name"]] = fm
    missing = {"reviewer", "builder", "test_generator"} - set(agents.keys())
    if missing:
        print(f"[FAIL] Pflicht-Agenten fehlen: {missing}. Fail closed.")
        sys.exit(1)
    return agents


def load_docs(docs_config: dict[str, str], project_dir: Path) -> dict[str, str]:
    docs: dict[str, str] = {}
    for key, rel in docs_config.items():
        path = project_dir / rel
        if not path.exists():
            print(f"[FAIL] Pflichtdokument fehlt: {rel}. Fail closed.")
            sys.exit(1)
        docs[key] = path.read_text(encoding="utf-8")
    return docs




# Auflage 2200a: aktueller Run-Identifier.
# Wird in run_pipeline gesetzt, in audit() in jeden
# Eintrag geschrieben. Modul-global, weil audit()
# keinen state-Parameter hat und ein Umbau aller
# ~200 Aufrufer unverhaeltnismaessig waere.


def _review_round_audit_payload(
        runde: int,
        verdict: str,
        reviewer_antwort: str,
) -> dict[str, Any]:
    """Auflage Review-Persistenz-A7/A9 (2026-10-16).

    Baut den Audit-Payload fuer kind=review_round.
    Reviewer-Rohtext wird redacted und ggf. gekappt.
    Reine Funktion, testbar ohne LLM.
    """
    _raw_red, _ = redaction.redact_all(
        reviewer_antwort,
        max_len=_AUDIT_RAW_REDACTION_LIMIT)
    _raw_len_original = len(reviewer_antwort)
    _raw_len_redacted = len(_raw_red)
    _raw_redaction_gekuerzt = (
        _raw_len_redacted == _AUDIT_RAW_REDACTION_LIMIT)
    if _raw_len_redacted > _AUDIT_RAW_MAX_LEN:
        _raw_audit = _raw_red[:_AUDIT_RAW_MAX_LEN]
        _raw_gekuerzt = True
    else:
        _raw_audit = _raw_red
        _raw_gekuerzt = False
    payload: dict[str, object] = {
        "runde": runde,
        "verdict": verdict,
        "raw": _raw_audit,
        "raw_len": len(_raw_audit),
        "raw_len_redacted": _raw_len_redacted,
        "raw_len_original": _raw_len_original,
    }
    if _raw_gekuerzt:
        payload["raw_gekuerzt"] = True
    if _raw_redaction_gekuerzt:
        payload["raw_redaction_gekuerzt"] = True
    return payload


# Auflage Review-Persistenz-A7 (2026-10-16):
# Maximale Laenge des Reviewer-Rohtexts im Audit-Log.
# Kappung nach Redaction; bei Kappung zusaetzlich
# raw_gekuerzt=true im payload.

# Auflage Review-Persistenz-A7: Limit fuer redact_all
# deutlich ueber _AUDIT_RAW_MAX_LEN, damit die
# Redaction-Kappung nicht versehentlich greift.
# Bei == _AUDIT_RAW_REDACTION_LIMIT: Redaction hat
# selbst gekappt (raw_redaction_gekuerzt=true).




def _git_rev_parse_head(project_dir: Path) -> str:
    """Block P2b-2: git rev-parse HEAD im Ziel-Repo.

    Rueckgabe: der volle 40-Zeichen-SHA, oder ""
    bei Fehler. Kein raise (Aufrufer prueft auf "").
    """
    try:
        res = subprocess.run(
            ("git", "rev-parse", "HEAD"),
            cwd=str(project_dir),
            capture_output=True, text=True,
            timeout=30, check=False,
            env=subprocess_env(),
        )
    except (subprocess.TimeoutExpired, OSError):
        return ""
    if res.returncode != 0:
        return ""
    return res.stdout.strip()


def _git_status_porcelain(project_dir: Path) -> str:
    """Block P2b-2: git status --porcelain im Ziel-Repo.

    Rueckgabe: der Output. Leer = clean.
    Bei Fehler: Sentinel-String "!FEHLER!" (nicht leer),
    damit ein Aufrufer nicht versehentlich clean annimmt.
    """
    try:
        res = subprocess.run(
            ("git", "status", "--porcelain"),
            cwd=str(project_dir),
            capture_output=True, text=True,
            timeout=30, check=False,
            env=subprocess_env(),
        )
    except (subprocess.TimeoutExpired, OSError):
        return "!FEHLER!"
    if res.returncode != 0:
        return "!FEHLER!"
    return res.stdout


def build_catalog(config: dict[str, Any], project_dir: Path
                  ) -> tuple[dict[str, Measurement], dict[str, Measurement]]:
    venv = config.get("venv_python", str(project_dir / ".venv/bin/python3"))
    all_m: dict[str, Measurement] = {
        "py_compile": Measurement("py_compile",
            (venv, "-m", "compileall", "-q", "apps", "core", "harness", "tools", "scripts", "tests"),
            "Python-Syntax-Check.", 300),
        "ruff": Measurement("ruff", (venv, "-m", "ruff", "check", "."), "Lint."),
        "mypy": Measurement("mypy",
            (venv, "-m", "mypy", "apps", "core", "harness", "tools", "scripts"), "Typen.", 300),
        # Auflage 2159: mypy ueber tests/ liefert 1337 Fehler
        # (fehlende Annotations). Deshalb nicht in always_run,
        # sondern optional. Der Reviewer-Agent kann es anfordern.
        "mypy_tests": Measurement("mypy_tests",
            (venv, "-m", "mypy", "tests"), "Typen in tests/.", 300),
        "test_count": Measurement("test_count",
            (venv, "-m", "pytest", "--collect-only", "-q"), "Test-Anzahl."),
        # W61: pytest fuer eine einzelne Testdatei.
        # Arg: <pfad> (relativ, in file_whitelist).
        # Timeout 300s pro Datei, damit die volle Suite
        # (9+ Min) nicht das Budget sprengt.
        "pytest": Measurement("pytest",
            (venv, "-m", "pytest", "-q"), "Test ausfuehren.", 300),
        "git_status": Measurement("git_status", ("git", "status", "--porcelain"), "Tree."),
        "git_head": Measurement("git_head", ("git", "rev-parse", "--short", "HEAD"), "HEAD."),
        "coverage": Measurement("coverage",
            (venv, "-m", "pytest", "--cov=core", "--cov-report=json:coverage.json", "-q"),
            "Coverage.", 600),
        "chaos_probe": Measurement("chaos_probe",
            (venv, str(project_dir / "scripts" / "chaos_probe.py")), "Chaos.", 120),
        "bandit": Measurement("bandit",
            (venv, "-m", "bandit", "-r", "core", "harness", "-q"), "Security-Lint.", 300),
        "pip_audit": Measurement("pip_audit",
            (venv, "-m", "pip_audit", "-r", "requirements.txt", "--format", "json"),
            "CVE-Check.", 120),
        "read_file": Measurement("read_file", ("cat",), "Datei lesen."),
    }
    always = {k: v for k, v in all_m.items() if k in set(config.get("always_run", []))}
    optional = {k: v for k, v in all_m.items() if k in set(config.get("optional_catalog", []))}
    if not always:
        print("[FAIL] always_run leer. Fail closed.")
        sys.exit(1)
    return always, optional


def run_measurement_mit_argv(m: Measurement, whitelist: list[str],
                             project_dir: Path, extra_arg: str | None = None
                             ) -> tuple[str, bool, list[str]]:
    """Fuehrt eine Messung aus und gibt (out, ok, argv) zurueck.

    Auflage 2040: argv wird mitgegeben, damit der Aufrufer
    das tatsaechlich verwendete Kommando protokollieren kann.

    Auflage 2076: Dies ist die einzige Arbeitsfunktion.
    run_measurement() ist ein Wrapper, der argv wegwirft.
    """
    argv: list[str] = list(m.argv)
    # W61: pytest mit Arg (Testdatei).
    if m.mid == "pytest":
        if not extra_arg:
            return "pytest ohne Pfad.", False, []
        if not isinstance(extra_arg, str):
            return "pytest arg ist kein str.", False, []
        # Whitelist-Pruefung.
        if not any(extra_arg.startswith(w) for w in whitelist):
            return (f"pytest arg {extra_arg!r} nicht in "
                    f"Whitelist.", False, [])
        argv = list(argv) + [extra_arg]
        res = subprocess.run(
            argv, cwd=project_dir, capture_output=True,
            text=True, timeout=m.timeout_s)
        stdout_gekuerzt = res.stdout.strip().splitlines()
        letzte = stdout_gekuerzt[-1] if stdout_gekuerzt else ""
        out = (f"=== {m.mid} ===\nARGV: {' '.join(argv)}\n"
               f"RC: {res.returncode}\nSTDOUT (letzte Zeile):\n"
               f"{letzte}\nSTDERR:\n{res.stderr}\n")
        return out, res.returncode == 0, argv
    if m.mid == "read_file":
        if not extra_arg:
            return "read_file ohne Pfad.", False, []
        if not isinstance(extra_arg, str):
            return "read_file arg ist kein str.", False, []
        # W6b-1 (2026-10-16): Zeilenbereich
        # <pfad>:<start>-<ende>. Auswertung via
        # sed -n "<start>,<ende>p".
        _zeilenbereich: tuple[int, int] | None = None
        _pfad_arg = extra_arg
        if ":" in extra_arg:
            _kopf, _rest = extra_arg.rsplit(":", 1)
            if "-" in _rest:
                _a, _b = _rest.split("-", 1)
                try:
                    _start = int(_a)
                    _ende = int(_b)
                    if _start >= 1 and _ende >= _start:
                        _zeilenbereich = (_start, _ende)
                        _pfad_arg = _kopf
                except ValueError:
                    pass
        cand = (project_dir / _pfad_arg).resolve()
        try:
            rel = str(cand.relative_to(project_dir.resolve()))
        except ValueError:
            return f"Pfad ausserhalb Projekt: {_pfad_arg}", False, []
        if not any(rel.startswith(p) for p in whitelist):
            return f"Pfad nicht in Whitelist: {rel}", False, []
        if _zeilenbereich is not None:
            argv = ["sed", "-n",
                    f"{_zeilenbereich[0]},{_zeilenbereich[1]}p",
                    str(cand)]
        else:
            argv.append(str(cand))
    try:
        res = subprocess.run(argv, cwd=str(project_dir), capture_output=True,
                             text=True, timeout=m.timeout_s, check=False,
                             env=subprocess_env())
    except subprocess.TimeoutExpired:
        return f"TIMEOUT {m.timeout_s}s", False, argv
    except OSError as exc:
        return f"OSError: {exc}", False, argv
    # Auflage 2176: test_count-Ausgabe kuerzen.
    # Sonst enthaelt sie 1312 Zeilen Testnamen; die
    # Testzahl steht erst am Ende.
    if m.mid == "test_count":
        stdout_gekuerzt = res.stdout.strip().splitlines()
        letzte = stdout_gekuerzt[-1] if stdout_gekuerzt else ""
        out = (f"=== {m.mid} ===\nARGV: {' '.join(argv)}\n"
               f"RC: {res.returncode}\nSTDOUT (letzte Zeile):\n{letzte}\n"
               f"STDERR:\n{res.stderr}\n")
    else:
        out = (f"=== {m.mid} ===\nARGV: {' '.join(argv)}\nRC: {res.returncode}\n"
               f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}\n")
    return out, res.returncode == 0, argv


def run_measurement(m: Measurement, whitelist: list[str], project_dir: Path,
                    extra_arg: str | None = None) -> tuple[str, bool]:
    """Wrapper um run_measurement_mit_argv, wirft argv weg.

    Auflage 2076: Konsolidierung. Die Arbeitslogik liegt
    in run_measurement_mit_argv.
    """
    out, ok, _argv = run_measurement_mit_argv(
        m, whitelist, project_dir, extra_arg,
    )
    return out, ok



def ask_llm(api_key: str, system_prompt: str, user_content: str,
            model: str, temperature: float, timeout: int = 120,
            *, state: RunState | None = None,
            aufgabe: str = "unbekannt",
            max_tokens: int = 4096) -> LLMReply:
    """Fragt das LLM.

    Auflage 2125: Wenn `state` uebergeben wird, zaehlt
    der Aufruf in state.llm_calls — unabhaengig davon,
    ob der Call erfolgreich ist. Fehlschlaege zaehlen
    ebenfalls (konservativ, Budget-Schutz).
    """
    if state is not None:
        state.llm_calls += 1
    # Redaction: vor dem Senden anwenden
    # Auflage 2113: max_len=100_000, damit Block-Auftraege
    # groesser 2000 Zeichen nicht abgeschnitten werden.
    # Analog 2089 (System-Prompt).
    user_content, _ = redaction.redact_all(user_content, max_len=100000)
    system_prompt, _ = redaction.redact_all(system_prompt, max_len=100000)
    headers: dict[str, str] = {"Authorization": f"Bearer {api_key}",
                              "Content-Type": "application/json"}
    payload: dict[str, Any] = {"model": model,
        "max_tokens": max_tokens,
                               "messages": [{"role": "system", "content": system_prompt},
                                            {"role": "user", "content": user_content}],
                               "temperature": temperature}
    # Timeout-Fix 2026-10-16 (Option B, HR-R7):
    # B1 (Read-Timeout) bricht haengende Calls ab.
    # B2 (Deadline) verhindert Folge-Versuche nach
    # Ueberschreitung. B1 ist primaer, B2 sekundaer.
    _CONNECT_S = 15  # Timeout-A1: 15s statt 10s.
    _READ_S = 180
    _max_total_s = int(
        getattr(state, "max_total_llm_s", 240)
        if state is not None else 240)
    # Zeitout-Verhaeltnis (Timeout-A2): read=180 deckt
    # einen einzelnen Call ab. max_total=240 erlaubt
    # 180 s + 60 s Nachlauf fuer einen Retry.
    _t0 = time.monotonic()
    _deadline = _t0 + _max_total_s
    # Auflage 2087: Retry nur bei 429 (Rate Limit) und 5xx
    # (Server-Fehler). Kein Retry bei 4xx — ein Auth-Fehler
    # wuerde sich endlos wiederholen.
    # Max 2 Versuche. Backoff: 1s, dann 3s.
    backoffs = (1, 3)
    letzter_fehler: str = ""
    res = None
    _versuche_absolut = 0
    for versuch, warte in enumerate(backoffs, start=1):
        # Timeout-A4: adaptive Restzeit pruefen.
        _rest = _deadline - time.monotonic()
        if _rest <= 0:
            if state is not None:
                audit("llm_timeout_gesamt",
                      {"modell": model,
                       "aufgabe": aufgabe,
                       "dauer_s": round(
                           time.monotonic() - _t0, 2),
                       "versuche": _versuche_absolut,
                       "deadline_s": _max_total_s,
                       "letzter_fehler":
                           letzter_fehler[:200]},
                      state.project_dir,
                      state.project_name)
            return LLMReply(
                ok=False,
                error=f"Gesamt-Timeout {_max_total_s}s",
            )
        # Read-Timeout adaptiv: min(read, restzeit).
        _read_adapt = int(min(_READ_S, max(1, _rest)))
        _req_timeout = (_CONNECT_S, _read_adapt)
        # SIM113: Retry-Loop mit variabler Laenge
        # (max len(backoffs)), enumerate ist hier
        # nicht passend (Abbruch durch break).
        _versuche_absolut += 1  # noqa: SIM113
        try:
            res = requests.post(DEEPSEEK_API_URL, headers=headers,
                                json=payload, timeout=_req_timeout)
        except requests.Timeout as exc:
            letzter_fehler = f"HTTP Timeout: {exc}"
            res = None
            if state is not None:
                audit("llm_timeout_read",
                      {"modell": model,
                       "aufgabe": aufgabe,
                       "read_s": _read_adapt,
                       "versuch": _versuche_absolut},
                      state.project_dir,
                      state.project_name)
        except requests.RequestException as exc:
            letzter_fehler = f"HTTP: {exc}"
            res = None
        else:
            if res.status_code == 200:
                break
            # Nur 429 und 5xx werden wiederholt.
            if res.status_code != 429 and res.status_code < 500:
                return LLMReply(
                    ok=False,
                    error=f"HTTP {res.status_code}: {res.text[:200]}",
                )
            letzter_fehler = f"HTTP {res.status_code}: {res.text[:200]}"
        if versuch < len(backoffs):
            time.sleep(warte)

    if res is None:
        return LLMReply(ok=False, error=letzter_fehler)
    if res.status_code != 200:
        return LLMReply(ok=False, error=letzter_fehler)
    try:
        data = res.json()
        msg = data["choices"][0]["message"]
        content = msg.get("content", "") or ""
        # W58: deepseek-reasoner liefert reasoning_content
        # (Denk-Tokens) + content (sichtbare Antwort). Wenn
        # das max_tokens-Budget im Reasoning erschoepft ist,
        # ist content leer. Fallback auf reasoning_content.
        if not content:
            reasoning = msg.get("reasoning_content", "") or ""
            if reasoning:
                # Letzte Zeilen des Reasonings als Antwort.
                content = reasoning
        if not content:
            return LLMReply(
                ok=False,
                error=("leere Antwort (content und "
                       "reasoning_content leer)"))
        return LLMReply(ok=True, content=content)
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        return LLMReply(ok=False, error=f"Parsing: {exc}")


def _extrahiere_antwort(text: str) -> str:
    """P2b-Frage-B: zieht den ANTWORT-Block aus
    einer Reviewer-Antwort.

    Format:
      ANTWORT:
      <text>

    Liefert den Text oder "" wenn kein Block.
    """
    zeilen = text.splitlines()
    start = None
    for i, z in enumerate(zeilen):
        s = z.strip().upper()
        if s.startswith("ANTWORT:"):
            start = i
            break
    if start is None:
        return ""
    kopf = zeilen[start].strip()
    rest_kopf = kopf[len("ANTWORT:"):].strip()
    body = zeilen[start + 1:]
    if rest_kopf:
        return rest_kopf + "\n" + "\n".join(body)
    return "\n".join(body).strip()



def _review_unklar_widerspruch(raw: str) -> bool:
    """B0-A1/A5: prueft, ob ein UNKLAR-Verdikt
    einen Widerspruchs-Block enthaelt.

    Format (R15/S10):
      UNKLAR:
      Widerspruch: <Text>
      Beleg: <Text>

    Rueckgabe: True, wenn "Widerspruch:" als
    eigene Zeile im raw steht.
    """
    for zeile in raw.splitlines():
        if zeile.strip().startswith("Widerspruch:"):
            return True
    return False


def classify_verdict(text: str) -> str:
    """Erkennt GO / NO-GO / ESKALATION / COMMIT-* / COMMAND.

    Auflage 2077: Satzzeichen am Wortende werden gestrippt,
    damit "GO.", "NO-GO:" und "ESKALATION!" erkannt werden.
    Der Bindestrich bleibt Teil des Tokens (NO-GO), sonst
    wuerde "NO-GO." als "NO" gelesen.

    B0c (2026-10-16): Verdict kann am Anfang ODER am
    Ende der Antwort stehen. reviewer.md verlangt
    "am Ende GO, NO-GO oder ESKALATION". Darum:
    1. Suche am Anfang (max 15 Zeilen, bestehend).
    2. Fallback: Suche am Ende (max 5 nicht-leere
       Zeilen rueckwaerts).
    """
    satzzeichen = ".,;:!?)"
    gezaehlt = 0
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        gezaehlt += 1
        if gezaehlt > 15:
            break
        w = s.split(maxsplit=1)[0].upper().rstrip(satzzeichen)
        # W41: NO_GO (Unterstrich) tolerieren
        # (judge.md sagt "NO_GO", reviewer.md
        # sagt "NO-GO").
        if w == "NO_GO":
            w = "NO-GO"
        if w in {"GO", "NO-GO", "ESKALATION"}:
            return w
        if w == "COMMIT-NO_GO":
            w = "COMMIT-NO-GO"
        if w in {"COMMIT-GO", "COMMIT-NO-GO", "COMMIT-ESKALATION"}:
            return w
        # P2b-Frage-B: ANTWORT-Modus.
        if w == "ANTWORT":
            return "ANTWORT"
        if s.upper().startswith("COMMAND:"):
            return "COMMAND"
    # B0c: Fallback fuer Verdict am Ende.
    # B0c-2 (2026-10-16, Lauf 26): Markdown-Marker
    # strippen und die letzten 5 nicht-leeren Zeilen
    # pruefen (Verdict kann in -1, -2, ... stehen).
    # Nur kurze Zeilen (< 40 Zeichen) zaehlen, damit
    # 'R15: GO.' in Fliesstext nicht faelschlich
    # greift.
    _marker = "*`_# \t"
    _ende_zeilen: list[str] = []
    for line in reversed(text.splitlines()):
        _s = line.strip()
        if _s:
            _ende_zeilen.append(_s)
        if len(_ende_zeilen) >= 5:
            break
    for _ende_zeile in _ende_zeilen:
        _rein = _ende_zeile.strip(_marker).strip()
        if not _rein or len(_rein) > 40:
            continue
        w = _rein.split(maxsplit=1)[0].upper().rstrip(
            satzzeichen + "*`_")
        # W41: NO_GO (Unterstrich) tolerieren.
        if w == "NO_GO":
            w = "NO-GO"
        if w in {"GO", "NO-GO", "ESKALATION"}:
            return w
        if w == "COMMIT-NO_GO":
            w = "COMMIT-NO-GO"
        if w in {"COMMIT-GO", "COMMIT-NO-GO",
                 "COMMIT-ESKALATION"}:
            return w
        if w == "ANTWORT":
            return "ANTWORT"
        if _rein.upper().startswith("COMMAND:"):
            return "COMMAND"
    return "UNKLAR"


def _parse_commands_planner(
        text: str,
) -> list[dict[str, str]]:
    """W51c: COMMAND-Parser nur fuer den Planner.

    WHITELIST (A-W51c-8): nur 'COMMAND: RUN
    read_file <pfad>' und 'COMMAND: load_skill
    <name>'. Kein rm, kein solver, kein coverage,
    kein bandit, kein pip_audit.
    Akzeptiert Listungs-Praefixe ('- COMMAND:').

    W51c-fix (2026-10-18): _planner_lauf nutzt
    diesen Parser (vorher: globaler parse_commands).
    load_skill (W25) ist erlaubt. Der Planner-
    Prompt bietet load_skill noch nicht an
    (Merkposten W25-planner-md).

    WARUM TRENNUNG (W23-Lehre): parse_commands
    wird an 6 Stellen genutzt (Planner, Builder,
    Reviewer, Commit-Review). Globale Robustheits-
    Ausweitung wuerde Markdown-Beispiele in
    Builder/Reviewer-Prompts ausfuehren.
    """
    cmds: list[dict[str, str]] = []
    for line in text.splitlines():
        s = line.strip()
        for pre in ("- ", "* ", "• "):
            if s.startswith(pre):
                s = s[len(pre):].lstrip()
                break
        if not s.upper().startswith("COMMAND:"):
            continue
        body = s[len("COMMAND:"):].strip()
        # W51c-fix (2026-10-18): load_skill (W25)
        # ist im Planner-Pfad erlaubt.
        if body.lower().startswith("load_skill"):
            rest_ls = body[len("load_skill"):].strip()
            rest_ls = rest_ls.strip("\"'()")
            if rest_ls:
                cmds.append({"typ": "load_skill",
                             "arg": rest_ls})
            continue
        if not body.upper().startswith("RUN "):
            continue
        rest = body[4:].strip()
        parts = rest.split(maxsplit=1)
        if len(parts) < 2:
            continue
        if parts[0] != "read_file":
            continue
        cmds.append({"typ": "run", "id": "read_file",
                     "arg": parts[1]})
    return cmds


def _bereinige_planner_reply(
        text: str,
) -> str:
    """W51c: entfernt Mess-Artefakte aus Planner-Reply.

    Entfernt: MESSUNGEN-Block, GEMESSENER INHALT-
    Block, direkte COMMAND-Zeilen (Fallback).

    Fallback greift mit UND ohne MESSUNGEN-Klammer.
    Determinismus-Grenze (WEG-X-P19-R1): der
    Planner kann den Fix umgehen (nichts davon in
    den Reply) — dann greift
    _plan_ist_messungsbasiert (fail-closed).
    """
    import re as _re
    text = _re.sub(
        r"=== MESSUNGEN ===.*?=== /MESSUNGEN ===\n?",
        "", text, flags=_re.DOTALL)
    text = _re.sub(
        r"=== GEMESSENER INHALT ===.*?"
        r"=== /GEMESSENER INHALT ===\n?",
        "", text, flags=_re.DOTALL)
    zeilen = []
    for ln in text.splitlines(keepends=True):
        s = ln.strip()
        for pre in ("- ", "* ", "• "):
            if s.startswith(pre):
                s = s[len(pre):].lstrip()
                break
        if s.upper().startswith("COMMAND:"):
            continue
        zeilen.append(ln)
    return "".join(zeilen).strip() + "\n"


def _w51c_bereinige_und_audit(
        reply: str,
        state: RunState,
        project_dir: Path,
        project_name: str,
        runde: int,
) -> str:
    """W51c: bereinigt Planner-Reply, auditet Ergebnis.

    Prueft nach der Bereinigung, ob noch 'COMMAND:'
    im Reply steht. Wenn ja: command_block_in_plan
    (Fallback hat nicht gegriffen). Sonst:
    command_block_bereinigt, wenn ueberhaupt was
    entfernt wurde.
    """
    bereinigt = _bereinige_planner_reply(reply)
    if "COMMAND:" in bereinigt.upper():
        audit("command_block_in_plan",
              {"anzahl": bereinigt.upper().count(
                  "COMMAND:"),
               "runde": runde},
              project_dir, project_name)
    elif bereinigt.strip() != reply.strip():
        audit("command_block_bereinigt",
              {"runde": runde,
               "laenge_vorher": len(reply),
               "laenge_nachher": len(bereinigt)},
              project_dir, project_name)
    return bereinigt


def parse_commands(text: str) -> list[dict[str, str]]:
    """Parst COMMAND-Zeilen aus einer LLM-Antwort.

    Auflage 2039: arg muss str sein. Kein dict/list.
    Wenn der LLM einen JSON-Block liefert, wird das
    verworfen und der Eintrag nicht uebernommen.

    P2b-Frage-A: zwei Typen.
      COMMAND: RUN <id> <arg>
        -> {"typ": "run", "id": <id>, "arg": <arg>}
      COMMAND: frage_reviewer <text>
        -> {"typ": "frage_reviewer", "arg": <text>}
    Mehrere frage_reviewer-Zeilen werden mit \n
    zu einem einzigen Eintrag konkateniert.
    """
    cmds: list[dict[str, str]] = []
    frage_teile: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if not s.upper().startswith("COMMAND:"):
            continue
        body = s[len("COMMAND:"):].strip()
        # P2b-Frage-A: frage_reviewer.
        if body.lower().startswith("frage_reviewer"):
            rest_f = body[len("frage_reviewer"):].strip()
            if rest_f:
                frage_teile.append(rest_f)
            continue
        # W25 (2026-10-17): load_skill.
        if body.lower().startswith("load_skill"):
            rest_ls = body[len("load_skill"):].strip()
            rest_ls = rest_ls.strip("\"'()")
            if rest_ls:
                cmds.append({"typ": "load_skill",
                             "arg": rest_ls})
            continue
        if not body.upper().startswith("RUN "):
            continue
        rest = body[4:].strip()
        parts = rest.split(maxsplit=1)
        if not parts:
            continue
        cmd_id = parts[0]
        if not isinstance(cmd_id, str) or not cmd_id:
            continue
        arg_roh = parts[1].strip() if len(parts) > 1 else ""
        # Auflage 2039: arg MUSS str sein. Bei nicht-str: verwerfen.
        if not isinstance(arg_roh, str):
            continue
        cmds.append({"typ": "run", "id": cmd_id,
                     "arg": arg_roh})
    if frage_teile:
        cmds.append({"typ": "frage_reviewer",
                     "arg": "\n".join(frage_teile)})
    return cmds


def parse_auflagen(text: str) -> list[str]:
    auflagen: list[str] = []
    for line in text.splitlines():
        m = re.match(r"\s*Auflage\s+([A-Z]?\d+)\s*:?\s*(.*)", line, re.IGNORECASE)
        if m:
            auflagen.append(f"{m.group(1)}: {m.group(2).strip()}")
    return auflagen


def parse_empfehlung(text: str) -> dict[str, str]:
    emp = {"tests": "", "art": "", "prioritaet": ""}
    for line in text.splitlines():
        s = line.strip()
        if s.upper().startswith("EMPFEHLUNG TESTS:"):
            emp["tests"] = s.split(":", 1)[1].strip()
        elif s.upper().startswith("EMPFEHLUNG ART:"):
            emp["art"] = s.split(":", 1)[1].strip()
        elif s.upper().startswith("EMPFEHLUNG PRIORITAET:"):
            emp["prioritaet"] = s.split(":", 1)[1].strip()
    return emp



INHALTSWOERTER_TRIGGER_B = (
    "welche", "welcher", "welches",
    "aus welchem", "aus welcher",
    "wo ", "wohin", "woher",
    "was ", "wie ", "warum",
    "soll ich", "sollte ich",
)


def erhoehe_solver_aufruf(state: RunState,
                         max_runden: int) -> bool:
    """B5 (MM1): zentraler Zaehler fuer Solver-Aufrufe.

    Erhoeht state.solver_aufrufe um 1, wenn das Limit
    nicht erreicht ist. Rueckgabe True, wenn erhoeht.

    Kein append in solver_trigger_quellen (Kontext
    macht der Aufrufer).
    """
    if state.solver_aufrufe >= max_runden:
        return False
    state.solver_aufrufe += 1
    return True


def pruefe_trigger_b(reply: str) -> bool:
    """Stufe 0 Aenderung 3: Trigger B (Rueckfrage).

    II5: Fuss-Fenster 300 Zeichen.
    II6: "?" UND Inhaltswort. Stopwoerter wie
         "Fertig?" triggern nicht.
    HH9-Fall 2: Patch vorhanden, aber Rueckfrage im Fuss.
    """
    fenster = reply[-300:].lower()
    if "?" not in fenster:
        return False
    return any(w in fenster for w in INHALTSWOERTER_TRIGGER_B)


def klassifiziere_deadlock(state: RunState,
                          letzter_reply: str) -> str:
    """Stufe 0 Aenderung 4: differenziert den Deadlock.

    Rueckgabe:
      "anker_nicht_gemessen": Anker- oder Ersatz-Fehler
                              liegen vor.
      "rueckfrage":           Reply ohne Patch, ohne COMMAND,
                              mit Frage im Fuss.
      "leer":                 weder Patch noch COMMAND noch
                              Rueckfrage.
    """
    if state.letzte_anker_fehler or state.letzte_ersatz_fehler:
        return "anker_nicht_gemessen"
    hat_patch = "PATCH-BEGINN" in letzter_reply
    hat_command = "COMMAND:" in letzter_reply
    if not hat_patch and not hat_command and "?" in letzter_reply:
        return "rueckfrage"
    return "leer"


def baue_anker_rueckmeldung(state: RunState) -> str:
    """Stufe 0 Aenderung 2: baut den Rueckmeldungs-Block
    fuer den Builder-Prompt, wenn Anker oder Ersatz nicht
    im mess_protokoll stehen. HH4: max 5 Eintraege.

    Liefert "" wenn keine Fehler vorliegen.
    """
    if not state.letzte_anker_fehler and not state.letzte_ersatz_fehler:
        return ""
    zeilen = ["## ANKER-PRUEFUNG (deterministisch)"]
    zeilen.append(
        "Diese Anker / Import-Pfade stehen NICHT im "
        "GEMESSENER INHALT:")
    anker_eintraege = state.letzte_anker_fehler[:5]
    for i, pfad, anker, grund in anker_eintraege:
        kurz = anker[:80].replace("\n", "\\n")
        zeilen.append(f"- Patch {i} ({pfad}, {grund}): {kurz!r}")
    if len(state.letzte_anker_fehler) > 5:
        rest = len(state.letzte_anker_fehler) - 5
        zeilen.append(f"  ... und {rest} weitere Anker.")
    ersatz_eintraege = state.letzte_ersatz_fehler[:5]
    for i, pfad, modul in ersatz_eintraege:
        zeilen.append(
            f"- Patch {i} ({pfad}): Modul {modul!r} "
            f"nicht im GEMESSENER INHALT.")
    if len(state.letzte_ersatz_fehler) > 5:
        rest = len(state.letzte_ersatz_fehler) - 5
        zeilen.append(f"  ... und {rest} weitere Module.")
    zeilen.append("")
    zeilen.append("Du hast folgende Moeglichkeiten:")
    zeilen.append("(a) Neuer Patch mit korrektem Anker "
                  "(woertlich aus dem GEMESSENER INHALT).")
    zeilen.append("(b) COMMAND: RUN read_file <pfad>, "
                  "um mehr Kontext zu messen.")
    zeilen.append("")
    # Phase 3b: Anti-Pattern-Block, wenn relevant.
    _tg = _ap_trigger_grund_aus_state(state)
    ap_block = _anti_pattern_block(state, "builder", _tg)
    if ap_block:
        zeilen.append("")
        zeilen.append(ap_block)
    return "\n".join(zeilen) + "\n"


def _anker_in_messung(state: RunState, anker: str) -> bool:
    """W52b-C: prueft Anker gegen Datei-Inhalte aus state.messungen.

    Quelle ist ausschliesslich m.datei (Pfad zur
    .werkstatt/<run_id>/messungen/<sha1>.txt-Datei).
    Liest die Datei bei jedem Check neu (klein, gecacht
    auf OS-Ebene).

    W61: Whitespace-toleranter Vergleich. Der Parser
    strippt die YAML-Block-Einrueckung; der Anker kann
    daher gegenueber der Messdatei um die Block-
    Einrueckung kuerzer sein. Wir vergleichen zeilenweise
    mit lstrip auf beiden Seiten (Einrueckung egal).
    """
    if state is None or not anker:
        return False
    # Normalisierte Anker-Zeilen (ohne fuehrende Spaces).
    anker_zeilen = [z.lstrip() for z in anker.splitlines()
                    if z.strip()]
    if not anker_zeilen:
        return False
    anker_norm = "\n".join(anker_zeilen)
    for m in getattr(state, "messungen", []) or []:
        datei = getattr(m, "datei", None)
        if datei is None:
            continue
        try:
            inhalt = datei.read_text(encoding="utf-8",
                                     errors="replace")
        except OSError:
            continue
        # Exakter Match zuerst.
        if anker in inhalt:
            return True
        # Whitespace-toleranter Match: Inhalt zeilenweise
        # lstrippen und als Block suchen.
        inhalt_zeilen = [z.lstrip() for z in inhalt.splitlines()]
        inhalt_norm = "\n".join(inhalt_zeilen)
        if anker_norm in inhalt_norm:
            return True
    return False


def pruefe_anker_gegen_messung(
    patches: list[dict[str, str]],
    state: RunState,
) -> list[tuple[int, str, str, str]]:
    """Stufe 0, Aenderung 1: deterministische
    Anker-Pruefung gegen den GEMESSENER INHALT.

    Liefert Liste von (Patch-Index, Pfad, Anker, Grund).

    Grund-Werte:
      "wirkungslos":      Anker und Ersatz sind exakt
                          gleich. Der Patch aendert
                          nichts (JJ1: exakter Vergleich,
                          keine Whitespace-Toleranz).
      "leer":             Anker ist leer.
      "nicht_gefunden":   Anker steht nicht im
                          mess_protokoll (auch nicht
                          als +2-Shift-Variante).
      "shift_akzeptiert": Anker steht nicht wort-
                          woertlich, aber die +2-Shift-
                          Variante (HH2) steht genau
                          einmal am Zeilenanfang.

    JJ3: nur ein Grund pro Patch. Wenn zwei
    Probleme vorliegen, liefert jede Pruef-
    Funktion ihren eigenen Eintrag.

    HH2: Toleranz fuer +2-Shift, wie in
    apply_code_patches (Auflage 2165).
    HH3: Leerer Anker bekommt eigenen Grund.
    """
    fehlend: list[tuple[int, str, str, str]] = []
    for i, p in enumerate(patches):
        # P-Bugfix 2026-10-16: typ: new_file hat
        # keinen anker. Die Anker-Pruefung ist fuer
        # ihn nicht anwendbar.
        if p.get("typ") == "new_file":
            continue
        anker = p.get("anker", "")
        ersatz = p.get("ersatz", "")
        pfad = p.get("pfad", "")
        # JJ1/JJ2: wirkungslos (exakter Vergleich).
        if anker and anker == ersatz:
            fehlend.append((i, pfad, anker, "wirkungslos"))
            continue
        if not anker:
            fehlend.append((i, pfad, anker, "leer"))
            continue
        if _anker_in_messung(state, anker):
            continue
        # HH2: +2-Shift-Variante
        verschoben = _shift_lines(anker, "  ")
        if _anker_in_messung(state, verschoben):
            fehlend.append(
                (i, pfad, anker, "shift_akzeptiert"))
            continue
        fehlend.append((i, pfad, anker, "nicht_gefunden"))
    return fehlend


EXPLORE_SUBAGENT_PROMPT = """Du bist ein Suchexperte.
Deine Aufgabe: Finde ein Muster in einer Datei oder einem
Repo und gib die genaue Position zurueck.

Antworte NUR mit einer dieser Zeilen:
  FUND: <pfad>:<zeile>: <kontext (max 120 Zeichen)>
  NICHT_GEFUNDEN

Du hast maximal 3 Runden. Nutze grep und read_file.
Kein freier Text."""


BASH_SUBAGENT_PROMPT = """Du bist ein Shell-Experte.
Deine Aufgabe: Fuehre einen Shell-Befehl aus und gib
das Ergebnis zurueck. Kein Schreiben ausserhalb /tmp.

Antworte NUR mit:
  OK: <kurzausgabe (max 200 Zeichen)>
  FEHLER: <grund>

Du hast maximal 2 Runden. Kein freier Text."""


BROWSER_SUBAGENT_PROMPT = """Du bist ein Browser-Experte.
Deine Aufgabe: Rufe eine URL ab und gib den Inhalt
zurueck (gekuerzt).

Antworte NUR mit:
  OK: <inhalt (max 300 Zeichen)>
  FEHLER: <grund>

Du hast maximal 2 Runden. Kein freier Text."""


def build_subagent_state(parent: RunState) -> RunState:
    """Minimaler RunState fuer Subagenten (W61).

    Kopiert nur, was read_file/grep/execute_commands
    brauchen. Keine Parent-Historie, kein mess_protokoll,
    keine Skills, keine Code-Patches.
    """
    import copy as _copy
    s = _copy.copy(parent)
    s.messungen = []
    s.messungen_nach_apply = []
    s.mess_protokoll = ""
    s.mess_protokoll_nach_apply = ""
    s.gelesene_dateien = {}
    s.letzte_anker_fehler = []
    s.letzte_ersatz_fehler = []
    s.code_entwurf = ""
    s.code_patches = []
    s.review_runden = []
    s.auflagen_log = []
    s.empfehlung_log = []
    s.letzte_builder_frage = ""
    return s


def _subagent_lauf(
        state: RunState,
        api_key: str,
        system_prompt: str,
        frage: str,
        modell: str,
        max_runden: int,
        max_tokens: int,
        erlaubte_ids: set,
) -> str:
    """Generischer Subagenten-Lauf (W61).

    Frischer Kontext, eigene messungen, max N Runden.
    Gibt die fertige Antwort zurueck.
    """
    sub_state = build_subagent_state(state)
    user = frage
    for _ in range(max_runden):
        reply = ask_llm(
            api_key, system_prompt, user,
            modell, 0.0, state.llm_timeout_s,
            state=sub_state,
            max_tokens=max_tokens,
        )
        if not reply.ok:
            return "FEHLER: llm"
        inhalt = reply.content.strip()
        if (inhalt.startswith("FUND:")
                or inhalt.startswith("OK:")
                or inhalt.startswith("FEHLER:")
                or inhalt == "NICHT_GEFUNDEN"):
            return inhalt
        cmds = parse_commands(inhalt)
        if not cmds:
            return "NICHT_GEFUNDEN"
        cmds = [c for c in cmds if c.get("id") in erlaubte_ids]
        if not cmds:
            return "NICHT_GEFUNDEN"
        execute_commands(sub_state, cmds, quelle="subagent")
        user = ("Weiter. Antworte mit dem vorgegebenen "
                "Format (FUND/OK/FEHLER/NICHT_GEFUNDEN).")
    return "NICHT_GEFUNDEN"


def rufe_explore_subagent(
        state: RunState, api_key: str, frage: str,
) -> str:
    """W61: Explore-Subagent (aktiv)."""
    return _subagent_lauf(
        state, api_key,
        EXPLORE_SUBAGENT_PROMPT,
        f"Suche: {frage}\n\nAntworte mit FUND: <pfad>:<zeile>: "
        "<kontext> oder NICHT_GEFUNDEN.",
        state.builder_model, 3, 1024,
        {"read_file", "grep"},
    )


def rufe_bash_subagent(
        state: RunState, api_key: str, frage: str,
) -> str:
    """W61: Bash-Subagent (inaktiv, fuer spaeter)."""
    return _subagent_lauf(
        state, api_key,
        BASH_SUBAGENT_PROMPT,
        f"Befehl: {frage}",
        state.builder_model, 2, 1024,
        {"read_file", "grep", "pytest", "ruff", "mypy"},
    )


def rufe_browser_subagent(
        state: RunState, api_key: str, frage: str,
) -> str:
    """W61: Browser-Subagent (inaktiv, fuer spaeter)."""
    return _subagent_lauf(
        state, api_key,
        BROWSER_SUBAGENT_PROMPT,
        f"URL: {frage}",
        state.builder_model, 2, 1024,
        {"read_file"},
    )


def builder_reply_mit_command_loop(
    state: RunState,
    api_key: str,
    builder_prompt: str,
    user_prompt_fn: Callable[[RunState], str],
    project_dir: Path,
    project_name: str,
    max_builder_runden: int = 3,
    max_llm: int = 0,
    max_minutes: int = 0,
) -> tuple[LLMReply | None, int | None]:
    """Auflage 2187: Builder-COMMAND-Loop.

    Fuehrt ask_llm in einer Schleife aus, bis ein Reply ohne
    COMMAND-Zeilen kommt (also ein Patch) oder max_builder_runden
    erreicht ist. Builder-COMMANDs werden ueber execute_commands
    (quelle="builder") ausgefuehrt, das Ergebnis landet in
    state.mess_protokoll und geht in die naechste Runde.

    Rueckgabe:
      (reply, None):  Reply mit Patch oder Fehler.
      (None, 19):     Builder-Command-Deadlock.
    """
    gescheiterte: set[tuple[str, str]] = set()
    # W30-fix-b (2026-10-18): max_builder_runden < 1
    # ist ein Konfigurationsfehler. Fail-closed,
    # bevor der Loop startet (sonst UnboundLocalError
    # auf reply.content).
    if max_builder_runden < 1:
        print(f"[FAIL] max_builder_runden < 1 "
              f"({max_builder_runden}). Fail closed.")
        audit("builder_runden_ungueltig",
              {"max_builder_runden": max_builder_runden},
              project_dir, project_name)
        return None, 19
    for builder_runde in range(1, max_builder_runden + 1):
        aktueller_prompt = user_prompt_fn(state)
        _audit_builder_prompt(
            aktueller_prompt, state, project_dir, project_name)
        reply = ask_llm(
            api_key, builder_prompt, aktueller_prompt,
            state.builder_model, state.builder_temp,
            state.llm_timeout_s, state=state,
            max_tokens=state.max_tokens_builder,
        )
        if not reply.ok:
            return reply, None
        _audit_builder_reply(
            reply.content, state, project_dir, project_name)
        cmds = parse_commands(reply.content)
        if not cmds:
            # Stufe 0 Aenderung 2: Anker+Ersatz pruefen.
            patches = parse_code_patches(reply.content)
            if patches:
                anker_fehler = pruefe_anker_gegen_messung(
                    patches, state)
                # W13b (2026-10-16): pruefe_ersatz_
                # gegen_messung deaktiviert. Der
                # ERSATZ enthaelt neuen Code, der
                # per Definition nicht im GEMESSENER
                # INHALT stehen kann. Der Anker-Check
                # + apply_code_patches reichen.
                ersatz_fehler: list[tuple[int, str, str]] = []
                if anker_fehler:
                    state.letzte_anker_fehler = anker_fehler
                    state.letzte_ersatz_fehler = ersatz_fehler
                    state.anker_fehler_in_folge += 1
                    # B3: wirkungslos-Signal.
                    _wirkt = any(
                        g == "wirkungslos"
                        for (_, _, _, g) in anker_fehler)
                    state.letzter_patch_wirkungslos = _wirkt
                    if _wirkt:
                        audit("builder_wirkungsloser_patch",
                              {"runde": builder_runde,
                               "anzahl": sum(
                                   1 for (_, _, _, g)
                                   in anker_fehler
                                   if g == "wirkungslos")},
                              project_dir, project_name)
                    audit("builder_anker_fehler",
                          {"runde": builder_runde,
                           "anker": len(anker_fehler),
                           "ersatz": len(ersatz_fehler),
                           "in_folge":
                               state.anker_fehler_in_folge},
                          project_dir, project_name)
                    print(f"[!] Builder-Runde {builder_runde}: "
                          f"{len(anker_fehler)} Anker, "
                          f"{len(ersatz_fehler)} Ersatz "
                          f"nicht im GEMESSENER INHALT. "
                          f"Rueckmeldung in naechster Runde.")
                    continue
                # Alle Anker ok: zuruecksetzen und return.
                state.letzte_anker_fehler = []
                state.letzte_ersatz_fehler = []
                state.anker_fehler_in_folge = 0
            return reply, None
        # P2b-Frage-A: frage_reviewer aus den cmds
        # herausziehen. Wenn vorhanden:
        # state.letzte_builder_frage setzen, Audit.
        fragen = [c for c in cmds
                  if c.get("typ") == "frage_reviewer"]
        if fragen:
            frage_text = "\n".join(
                f.get("arg", "") for f in fragen)
            state.letzte_builder_frage = frage_text
            audit("builder_frage_reviewer",
                  {"runde": builder_runde,
                   "frage": frage_text[:500]},
                  project_dir, project_name)
            print(f"[i] Builder-Runde {builder_runde}: "
                  f"Rueckfrage an Reviewer: "
                  f"{frage_text[:120]}")
        # Nur RUN-Zeilen weiterverarbeiten.
        # W25: load_skill vor cmds_run-Filter.
        _run_cmds_b, _n_skills_b = _verarbeite_skill_commands(
            state, cmds)
        if _n_skills_b:
            print(f"[i] Builder-COMMAND: "
                  f"{_n_skills_b} Skill(s) geladen.")
        cmds_run = [c for c in _run_cmds_b
                    if c.get("typ", "run") == "run"]
        if not cmds_run:
            # Nur frage_reviewer -> kein Deadlock,
            # Rueckgabe an Aufrufer.
            return reply, None
        # W61: Subagenten (aktiv: explore).
        # bash/browser sind angelegt, aber nicht im
        # Builder-Loop aktiv (spaetere Zeitpunkte).
        _explore_cmds = [c for c in cmds_run
                         if c.get("id") == "explore"]
        if _explore_cmds:
            for ec in _explore_cmds:
                ergebnis = rufe_explore_subagent(
                    state, api_key, ec.get("arg", ""))
                print(f"[i] Explore: {ergebnis[:160]}")
                audit("explore_subagent",
                      {"frage": ec.get("arg", "")[:200],
                       "ergebnis": ergebnis[:300]},
                      project_dir, project_name)
                # W61: Ergebnis in state speichern, damit der
                # naechste Builder-Prompt es sieht.
                state.letzte_explore_ergebnisse.append({
                    "frage": ec.get("arg", ""),
                    "ergebnis": ergebnis,
                })
            # Naechste Builder-Runde mit dem Ergebnis.
            continue
        for cmd in cmds_run:
            key = (cmd.get("id", ""), cmd.get("arg", ""))
            if key in gescheiterte:
                print(
                    f"[!] COMMAND wiederholt fehlgeschlagen: "
                    f"{key}. Deadlock.")
                art = klassifiziere_deadlock(
                    state, reply.content)
                audit(f"builder_deadlock_{art}",
                      {"grund": "wiederholter_fehler",
                       "key": list(key)},
                      project_dir, project_name)
                audit("builder_command_deadlock",
                      {"grund": "wiederholter_fehler",
                       "key": list(key)},
                      project_dir, project_name)
                return None, 19
                # B5: Solver + B2 im Deadlock-Pfad.
                _rc_dl = handle_deadlock_mit_solver(
                    state, api_key, project_dir, project_name,
                    max_llm, max_minutes)
                if _rc_dl is not None:
                    return None, _rc_dl
        print(f"[i] Builder-Runde {builder_runde}: "
              f"{len(cmds_run)} COMMAND(s) angefordert.")
        ergebnisse = execute_commands(
            state, cmds_run, quelle="builder")
        for key, ok in ergebnisse.items():
            if ok:
                gescheiterte.discard(key)
            else:
                gescheiterte.add(key)
        audit("builder_command_executed",
              {"runde": builder_runde,
               "anzahl": len(cmds_run),
               "ids": [c.get("id", "?") for c in cmds_run]},
              project_dir, project_name)
    # W30-fix (2026-10-18): einheitlicher Cap-Audit.
    _loop_cap_audit(state, "builder_command",
                    max_builder_runden + 1, max_builder_runden)
    art = klassifiziere_deadlock(state, reply.content)
    audit(f"builder_deadlock_{art}",
          {"max_builder_runden": max_builder_runden},
          project_dir, project_name)
    audit("builder_command_deadlock",
          {"max_builder_runden": max_builder_runden,
           "klassifikation": art},
          project_dir, project_name)
    # B5: Solver + B2 im Deadlock-Pfad.
    _rc_dl = handle_deadlock_mit_solver(
        state, api_key, project_dir, project_name,
        max_llm, max_minutes)
    if _rc_dl is not None:
        return None, _rc_dl
    # Truncation-Fix-A1/A2 (2026-10-16):
    # Kontext-Grenze in Konstante + Marker.
    # GEMESSENER INHALT (nach Apply) separat, damit
    # der Reviewer den Datei-Inhalt vollstaendig sieht.
    _prompt_gek = _truncate_mit_marker(
        aktueller_prompt, _REVIEWER_KONTEXT_MAX)
    _mess_nach = state.mess_protokoll_nach_apply or ""
    _mess_nach_gek = _truncate_mit_marker(
        _mess_nach, 8000) if _mess_nach else "(keine)"
    kontext = (
        f"Der Builder hat in {max_builder_runden} "
        f"aufeinanderfolgenden Runden nur "
        f"COMMAND-Zeilen geliefert, keinen Patch.\n\n"
        f"Letzter Prompt (gekuerzt):\n{_prompt_gek}\n\n"
        f"GEMESSENER INHALT (nach Apply):\n"
        f"{_mess_nach_gek}\n"
    )
    v = ask_reviewer_for_recovery(state, "builder_command_deadlock", kontext)
    print_recovery(v)
    audit("recovery_builder_command_deadlock",
          {"kontext": kontext}, project_dir, project_name)
    return None, 19


def zaehle_no_go_in_folge(
        review_runden: list[dict[str, Any]]) -> int:
    """Auflage 2183 A3, angepasst in P1 (U8).

    Zaehlt aufeinanderfolgende NO-GO am Ende.
    Recovery-Runden zaehlen NICHT (sie sind die
    Antwort auf einen Solver-Befund, kein neuer
    Fehler). Sie brechen die Kette aber auch
    nicht ab.
    """
    n = 0
    for r in reversed(review_runden):
        if r.get("verdict") != "NO-GO":
            break
        if r.get("recovery"):
            continue
        n += 1
    return n


def _tokenisiere(text: str) -> set[str]:
    """P1 (U2): Tokenisierung fuer Jaccard.

    - lower() (case-insensitiv).
    - Buchstaben >= 3 Zeichen ODER Zahlen.
    - Stopwoerter weg.
    - Kein Bindestrich-Split (IPv6-Feld bleibt).
    """
    if not text:
        return set()
    roh = P1_TOKEN_RE.findall(text.lower())
    return {t for t in roh if t not in P1_STOPWOERTER}


def jaccard_aehnlichkeit(text_a: str, text_b: str) -> float:
    """P1 (U2): Jaccard-Aehnlichkeit zweier Texte.

    |A ∩ B| / |A ∪ B| ueber Tokenmengen.
    Leere Menge -> 0.0.
    """
    a = _tokenisiere(text_a)
    b = _tokenisiere(text_b)
    if not a or not b:
        return 0.0
    schnitt = a & b
    vereinigung = a | b
    if not vereinigung:
        return 0.0
    return len(schnitt) / len(vereinigung)


def _p1_schon_getriggert(
        review_runden: list[dict[str, Any]]) -> bool:
    """P1 (U8): Hat eine Runde bereits recovery=True?

    Verhindert erneuten Trigger nach Recovery.
    """
    return any(r.get("recovery") for r in review_runden)


def gegenstand_gleich(
        review_runden: list[dict[str, Any]],
        schwellwert: float,
        min_tokens: int) -> tuple[float | None, str]:
    """P1: pruefen, ob die zwei letzten NO-GO-Runden
    denselben Gegenstand betreffen.

    U1 (Reviewer): P1 ist eine Annaeherung an den
    Gegenstandsbegriff. Der Vergleich funktioniert
    nur, wenn der Reviewer denselben Gegenstand
    sprachlich aehnlich benennt. Bei abweichender
    Formulierung triggert P1 nicht — das ist ein
    bekannter Grenzfall, kein Bug. Schwellwert und
    min_tokens sind im Projekt-YAML justierbar;
    Kalibrierung mit echten NO-GO-Paaren steht
    aus (U4).

    Liefert (jaccard_wert, grund).
    jaccard_wert ist None, wenn nicht gerechnet wurde.

    Fail-closed (U5/U6):
      - < 2 NO-GO-Runden -> kein_trigger_kein_paar.
      - Schon getriggert -> kein_trigger_schon_getriggert.
      - Text leer -> kein_trigger_leer.
      - Text zu kurz -> kein_trigger_zu_kurz.
      - Jaccard < Schwellwert -> kein_trigger_jaccard.
      - Sonst -> getriggert.
    """
    # U8: zuerst pruefen, ob schon getriggert.
    # Sonst greift die Pruefung nicht, wenn die
    # letzte Runde recovery=True trug.
    if _p1_schon_getriggert(review_runden):
        return None, P1_GRUND_KEIN_SCHON
    no_go = [r for r in review_runden
             if r.get("verdict") == "NO-GO"
             and not r.get("recovery")]
    if len(no_go) < 2:
        return None, P1_GRUND_KEIN_KEIN_PAAR
    a = no_go[-2].get("raw", "")
    b = no_go[-1].get("raw", "")
    if not a.strip() or not b.strip():
        return None, P1_GRUND_KEIN_LEER
    ta = _tokenisiere(a)
    tb = _tokenisiere(b)
    if len(ta) < min_tokens or len(tb) < min_tokens:
        return None, P1_GRUND_KEIN_ZU_KURZ
    wert = jaccard_aehnlichkeit(a, b)
    if wert < schwellwert:
        return wert, P1_GRUND_KEIN_JACCARD
    return wert, P1_GRUND_GETRIGGERT


def build_system_prompt(agent: dict[str, Any], docs: dict[str, str],
                        doc_keys: list[str],
                        *,
                        state: RunState | None = None,
                        mit_anti_patterns: bool = True,
                        stufe: int = 1) -> str:
    """Baut System-Prompt aus Rollen-Body + HARD_RULES_BASE + Rolle + Projekt-Doku.

    Auflage 2182: HARD_RULES_BASE + rollenspezifische
    HARD_RULES_<ROLLE> (anhand agent["name"]).
    Reihenfolge: Rollen-Body, BASE, Rolle, Projekt-Doku.

    Phase 3c-2 (2026-10-15): Wenn state gesetzt,
    mit_anti_patterns True und Rolle reviewer, wird
    der Anti-Pattern-Block angehaengt (Trigger-Grund
    None, Fallback VV2). Builder bekommt den Block
    via baue_anker_rueckmeldung (Phase 3b), Solver
    via rufe_solver (Phase 3c-3). Recovery-Reviewer
    ruft mit mit_anti_patterns=False (YY3).
    """
    parts = [agent["body"], HARD_RULES_BASE]
    agent_name = agent.get("name", "")
    # stufe wirkt nur fuer rolle=planner (P2a-S5a-A2).
    # stufe=2 waehlt HARD_RULES_PLANNER_STUFE2.
    # Jeder andere Wert verhaelt sich wie 1 (BY_ROLE).
    if agent_name == "planner" and stufe == 2:
        rollen_rules = HARD_RULES_PLANNER_STUFE2
    else:
        rollen_rules = HARD_RULES_BY_ROLE.get(agent_name, "")
    if rollen_rules:
        parts.append(rollen_rules)
    if doc_keys:
        parts.append("\n\n--- PROJEKT-DOKU ---")
        for key in doc_keys:
            if key in docs:
                parts.append(f"\n--- {key} ---\n{docs[key]}")
    # Phase 3c-2: Reviewer-Anti-Pattern-Block.
    if (state is not None and mit_anti_patterns
            and agent_name == "reviewer"):
        ap_block = _anti_pattern_block(state, "reviewer", None)
        if ap_block:
            parts.append("\n\n" + ap_block)
    return "\n".join(parts)


def load_recent_commits(project_dir: Path, n: int = 10) -> str:
    try:
        res = subprocess.run(
            ("git", "log", f"-{n}", "--format=%h %an%n%s%n%b%n---"),
            cwd=str(project_dir), capture_output=True, text=True,
            timeout=30, check=False, env=subprocess_env(),
        )
    except (subprocess.TimeoutExpired, OSError):
        return "(git log nicht verfuegbar)"
    if res.returncode != 0:
        return f"(git log: {res.stderr[:200]})"
    return res.stdout


def auto_repair_ruff(project_dir: Path, venv_python: str) -> tuple[bool, str]:
    """Nur deterministische Fixes. Kein LLM."""
    protokoll = ""
    try:
        r1 = subprocess.run((venv_python, "-m", "ruff", "check", ".", "--fix"),
                            cwd=str(project_dir), capture_output=True, text=True,
                            timeout=300, check=False, env=subprocess_env())
        protokoll += f"=== ruff check --fix ===\nRC: {r1.returncode}\n{r1.stdout}\n{r1.stderr}\n"
        r2 = subprocess.run((venv_python, "-m", "ruff", "format", "."),
                            cwd=str(project_dir), capture_output=True, text=True,
                            timeout=300, check=False, env=subprocess_env())
        protokoll += f"=== ruff format ===\nRC: {r2.returncode}\n{r2.stdout}\n{r2.stderr}\n"
        r3 = subprocess.run((venv_python, "-m", "ruff", "check", "."),
                            cwd=str(project_dir), capture_output=True, text=True,
                            timeout=300, check=False, env=subprocess_env())
        return r3.returncode == 0, protokoll
    except (subprocess.TimeoutExpired, OSError) as exc:
        return False, protokoll + f"\nFEHLER: {exc}"


def snapshot_tests_dir(project_dir: Path) -> dict[str, int]:
    tests = project_dir / "tests"
    snap: dict[str, int] = {}
    if not tests.exists():
        return snap
    for f in tests.rglob("*.py"):
        try:
            snap[str(f.relative_to(project_dir))] = f.stat().st_size
        except OSError:
            pass
    return snap


def check_tests_dir_unveraendert(project_dir: Path, vorher: dict[str, int]
                                 ) -> tuple[bool, list[str]]:
    """Prueft, dass keine Test-Datei geloescht oder kleiner wurde."""
    nachher = snapshot_tests_dir(project_dir)
    probleme: list[str] = []
    for pfad, groesse in vorher.items():
        if pfad not in nachher:
            probleme.append(f"GELOESCHT: {pfad}")
        elif nachher[pfad] < groesse:
            probleme.append(f"KLEINER: {pfad} ({groesse} -> {nachher[pfad]})")
    return (len(probleme) == 0), probleme



# Auflage 2183 A2: Solver-Diagnose und SolverBefund.
# Getrennt von RecoveryVorschlag (Freitext-Kanal).
def format_solver_befund(befund: SolverBefund) -> str:
    """Auflage 2183 A2: formatiert SolverBefund fuer Prompt.

    Wirft ValueError, wenn der Befund fuer seine Diagnose
    nicht vollstaendig ist (Fail-closed, HR-R9).
    """
    if not befund.ist_vollstaendig():
        raise ValueError(
            f"SolverBefund unvollstaendig fuer {befund.art}")
    zeilen = [f"## SOLVER-BEFUND ({befund.run_id})"]
    zeilen.append(f"Diagnose: {befund.art.name}")
    if befund.kandidaten:
        zeilen.append("Kandidaten:")
        for k in befund.kandidaten:
            zeilen.append(f"  - {k}")
    if befund.praezisierter_auftrag:
        zeilen.append(
            f"Praezisierter Auftrag: {befund.praezisierter_auftrag}")
    if befund.rueckspiel_hinweis:
        zeilen.append(f"Rueckspiel: {befund.rueckspiel_hinweis}")
    if befund.eskalation:
        zeilen.append(f"Eskalation: {befund.eskalation}")
    return "\n".join(zeilen) + "\n"


def _solver_befund_block(state: RunState) -> str:
    """Auflage 2183 Block 2a+4: Befund-Block fuer den
    Builder-Prompt.

    Liefert "" wenn kein Befund vorliegt.
    Liefert "" und audit("solver_befund_verworfen"),
    wenn der letzte Befund unvollstaendig ist.

    KEIN Fallback auf aeltere Befunde. Der letzte
    Befund ist der relevante. Ein unvollstaendiger
    letzter Befund ist ein Fail-Fall, der an den
    Werkstatt-Chat geht.
    """
    if not state.solver_befunde:
        return ""
    letzter = state.solver_befunde[-1]
    try:
        text = format_solver_befund(letzter)
    except ValueError:
        audit("solver_befund_verworfen",
              {"grund": "unvollstaendig",
               "art": letzter.art.name,
               "run_id": letzter.run_id},
              state.project_dir, state.project_name)
        return ""
    return (
        "## SOLVER-BEFUND (Unterstuetzung)\n"
        f"{text}\n"
        "Der Solver-Agent hat diesen Befund fuer\n"
        "dich erstellt. Er ist eine PRAEZISIERUNG\n"
        "des Auftrags, kein neuer Auftrag. Folge\n"
        "ihm, wenn er mit dem Auftrag konsistent\n"
        "ist. Pruefe die Empfehlungen gegen den\n"
        "Auftrag und den GEMESSENER INHALT.\n"
        "Bei Widerspruch zum Auftrag: melde\n"
        "COMMAND: frage_reviewer widerspruch \n"
        "solver-befund\n"
        "Die Umsetzung ist deine Aufgabe.\n\n"
    )


def parse_solver_diagnose(text: str) -> SolverDiagnose:
    """Auflage 2183 B: parst die Solver-Antwort.

    Sucht "DIAGNOSE: <WERT>" in der ersten Zeile
    (case-insensitiv). Fallback: UNKLAR.
    """
    if not text:
        return SolverDiagnose.UNKLAR
    for line in text.splitlines()[:10]:
        m = re.match(
            r"\s*DIAGNOSE\s*:\s*([A-Z_]+)",
            line, re.IGNORECASE)
        if m:
            wert = m.group(1).upper().strip()
            for d in SolverDiagnose:
                if d.name == wert:
                    return d
    return SolverDiagnose.UNKLAR


def _parse_solver_feld(text: str, feldname: str) -> str:
    """Auflage 2183 B: liest ein Feld aus der
    Solver-Antwort. Format:
        FELDNAME: wert
    oder mehrzeilig bis zur naechsten Grossbuchstaben-
    Zeile.
    """
    zeilen = text.splitlines()
    start = None
    for k, line in enumerate(zeilen):
        if re.match(
                rf"\s*{re.escape(feldname)}\s*:",
                line, re.IGNORECASE):
            start = k
            break
    if start is None:
        return ""
    inhalt = [zeilen[start].split(":", 1)[1].strip()]
    for line in zeilen[start + 1:]:
        if re.match(r"\s*[A-Z_]+\s*:", line):
            break
        if line.strip():
            inhalt.append(line.strip())
    return "\n".join(inhalt).strip()


def _parse_solver_kandidaten(text: str) -> list[str]:
    """Auflage 2183 B: liest KANDIDATEN-Liste."""
    roh = _parse_solver_feld(text, "KANDIDATEN")
    if not roh:
        return []
    kandidaten = []
    for line in roh.splitlines():
        line = line.strip().lstrip("-*").strip()
        if line:
            kandidaten.append(line)
    return kandidaten


def baue_solver_befund(
        text: str, run_id: str) -> SolverBefund:
    """Auflage 2183 B: baut SolverBefund aus der
    Solver-Antwort.
    """
    art = parse_solver_diagnose(text)
    if art == SolverDiagnose.GLEICHER_FEHLER:
        return SolverBefund(
            art=art,
            kandidaten=_parse_solver_kandidaten(text),
            run_id=run_id)
    if art == SolverDiagnose.ANDERER_FEHLER:
        return SolverBefund(
            art=art,
            praezisierter_auftrag=_parse_solver_feld(
                text, "PRAEZISIERTER_AUFTRAG"),
            run_id=run_id)
    if art == SolverDiagnose.WIDERSPRUCH:
        return SolverBefund(
            art=art,
            rueckspiel_hinweis=_parse_solver_feld(
                text, "RUECKSPIEL"),
            run_id=run_id)
    return SolverBefund(
        art=SolverDiagnose.UNKLAR,
        eskalation=_parse_solver_feld(
            text, "ESKALATION") or text[:500],
        run_id=run_id)


def _letzte_zwei_entwuerfe(
        state: RunState) -> list[dict[str, Any]]:
    """Auflage 2183 B (X8): die letzten zwei
    normalen Entwuerfe aus der Historie.

    A1b-fix (2026-10-18): Recovery-Entwuerfe
    (phase="recovery") werden bewusst ausgeblendet.
    Wenn in einem Lauf NUR Recovery-Entwuerfe
    existieren (Builder scheitert in normal-Runde,
    Recovery greift), sieht der Solver
    "(keine Historie)". Das ist korrekt: der Solver
    soll die normalen Runden vergleichen, nicht
    die Korrekturversuche.
    """
    normal = [e for e in state.code_entwurf_historie
              if e.get("phase") == "normal"]
    return normal[-2:] if len(normal) >= 2 else normal


def _solver_prompt_bauen(state: RunState,
                         grund: str = "") -> str:
    """Auflage 2183 B + C: baut den User-Content
    fuer den Solver-Call.

    C: optionaler "Grund des Reviewers" (Freitext,
    kein Dateipfad).
    """
    no_go = [r for r in state.review_runden
             if r.get("verdict") == "NO-GO"
             and not r.get("recovery")]
    letzte = no_go[-2:] if len(no_go) >= 2 else no_go
    _skills_vor = (
        _available_skills_block()
        + _geladene_skills_block(state))
    zeilen = [
        _skills_vor + aufgabe_block(state).rstrip()]
    _wl = _format_whitelist_block(
        list(getattr(state, "file_whitelist", []) or []))
    zeilen.append(_wl.rstrip())
    zeilen.append("")
    _ps_block = format_projekt_stand(state)
    if _ps_block:
        zeilen.append(_ps_block)
    zeilen.append("## NO-GO-RUNDEN")
    for r in letzte:
        zeilen.append(
            f"--- Runde {r.get('runde', '?')} ---")
        zeilen.append(r.get("raw", "")[:2000])
    zeilen.append("")
    zeilen.append("## CODE-ENTWUERFE")
    entwuerfe = _letzte_zwei_entwuerfe(state)
    if not entwuerfe:
        zeilen.append("(keine Historie)")
    for e in entwuerfe:
        zeilen.append(
            f"--- Runde {e.get('runde', '?')} ---")
        zeilen.append(e.get("entwurf", "")[:2000])
    if state.code_entwurf:
        zeilen.append("")
        zeilen.append("## AKTUELLER ENTWURF")
        zeilen.append(state.code_entwurf[:2000])
    if state.solver_befunde:
        zeilen.append("")
        zeilen.append("## FRUEHERE SOLVER-BEFUNDE")
        for b in state.solver_befunde:
            zeilen.append(
                f"--- Runde {b.run_id} ---")
            zeilen.append(
                f"DIAGNOSE: {b.art.name}")
    zeilen.append("")
    zeilen.append("## GEMESSENER INHALT (verbindlich)")
    zeilen.append(_messwerte_fuer_prompt(state))
    if grund:
        zeilen.append("")
        zeilen.append(
            "## GRUND DES REVIEWERS "
            "(Freitext, kein Dateipfad)")
        zeilen.append(grund)
    zeilen.append("")
    zeilen.append(
        "Antworte mit DIAGNOSE: <WERT> in der ersten "
        "Zeile, dann der passende Inhalt.")
    return "\n".join(zeilen)


def rufe_solver(
        state: RunState, api_key: str,
        solver_prompt: str,
        grund_text: str = "",
        trigger_grund: str | None = None,
        aufrufer: str = "unbekannt",
) -> tuple[SolverBefund | None, str]:
    """Auflage 2183 B + C: ruft den Solver.

    Liefert (befund, grund).
    befund ist None bei Fehler; grund ist dann
    "llm_fehler" oder "befund_unvollstaendig".
    Bei Erfolg: (befund, "").

    C: grund_text ist optionaler Reviewer-Grund
    (Freitext).

    Phase 3c-3 (2026-10-15): trigger_grund ist der
    Trigger-Grund fuer den Anti-Pattern-Filter
    (p1_trigger, wirkungsloser_patch,
    anker_nicht_gemessen, builder_rueckfrage,
    reviewer_command). aufrufer ist "command",
    "deadlock", "trigger_a_b_c" oder "unbekannt"
    (YY4).
    """
    user_content = _solver_prompt_bauen(state, grund_text)
    # Phase 3c-3: Anti-Pattern-Block anhaengen.
    ap_block = _anti_pattern_block(
        state, "solver", trigger_grund, aufrufer=aufrufer)
    if ap_block:
        user_content = user_content + "\n\n" + ap_block
    # Solver-Sichtbarkeit 2026-10-16: Trigger + Aufrufer
    # in der Konsole. Uebergangsloesung bis Dashboard.
    print(f"[i] Solver-Trigger: "
          f"{trigger_grund or '(kein Grund)'} "
          f"(Aufrufer: {aufrufer})")
    reply = ask_llm(api_key, solver_prompt, user_content,
                    state.solver_model, 0.0,
                    state.llm_timeout_s, state=state,
                    max_tokens=state.max_tokens_solver)
    if not reply.ok:
        return None, "llm_fehler"
    befund = baue_solver_befund(reply.content,
                                state.run_id)
    if not befund.ist_vollstaendig():
        print(f"[!] Solver-Befund unvollstaendig "
              f"(art={befund.art.name}, "
              f"aufrufer={aufrufer}).")
        return None, "befund_unvollstaendig"
    # Solver-Sichtbarkeit 2026-10-16: Befund auf Konsole,
    # gekuerzt auf 300 Zeichen (Uebergangsloesung).
    print(f"[i] Solver-Befund: "
          f"{format_solver_befund(befund)[:300].strip()}")
    return befund, ""


def _solver_schon_gelaufen(state: RunState) -> bool:
    """Auflage 2183 C: hat der Solver in diesem Lauf
    schon einen Befund geliefert?
    """
    return bool(state.solver_befunde)


def _handle_solver_command(
        state: RunState, cmd: dict[str, str],
        api_key: str, runde: int,
        max_llm: int, project_dir: Path,
        project_name: str,
        max_minutes: int = 0) -> None:
    """Auflage 2183 C: behandelt COMMAND: RUN solver.

    Im Reviewer-COMMAND-Zweig (Phase 1).
    """
    arg = cmd.get("arg", "")
    if not isinstance(arg, str):
        arg = ""
    # F6: Arg kuerzen, nicht reject.
    if len(arg) > SOLVER_ARG_MAX_LEN:
        arg = arg[:SOLVER_ARG_MAX_LEN - 3] + "..."
    audit("reviewer_run_solver",
          {"runde": runde, "arg": arg},
          project_dir, project_name)
    # Y4: Duplikat-Pruefung.
    if _solver_schon_gelaufen(state):
        audit("solver_run_duplicate",
              {"runde": runde, "arg": arg},
              project_dir, project_name)
        print("[i] RUN solver ignoriert: "
              "Solver lief in diesem Lauf schon.")
        return
    # X5: eigenes Budget-Gate.
    rc = budget_or_recover(
        state, max_llm,
        f"Vor Solver-Call (Reviewer-Command, Runde {runde}).",
        project_dir, project_name,
        max_minutes=max_minutes)
    if rc is not None:
        audit("solver_budget_exhausted",
              {"runde": runde, "quelle": "reviewer_command"},
              project_dir, project_name)
        return
    solver_prompt = build_system_prompt(
        state.agents["solver"], state.docs,
        state.agent_docs.get("solver", []))
    befund, fehler = rufe_solver(
        state, api_key, solver_prompt, grund_text=arg,
        trigger_grund="reviewer_command",
        aufrufer="command")
    if befund is None:
        audit("solver_failed",
              {"runde": runde, "grund": fehler,
               "quelle": "reviewer_command"},
              project_dir, project_name)
        return
    state.solver_befunde.append(befund)
    state.solver_trigger_quellen.append("reviewer_command")
    state.review_runden[-1]["recovery"] = True
    audit("solver_befund",
          {"runde": runde, "art": befund.art.name,
           "run_id": befund.run_id,
           "quelle": "reviewer_command"},
          project_dir, project_name)


# New_file-Marker (2026-10-16): Konstante + Helper.
# Wenn alle Patches typ=new_file sind, ist der
# GEMESSENER-INHALT-Block erwartbar leer.
SKILLS_DIR = Path("/opt/werkstatt/skills")


def _load_skill(name: str) -> str:
    """W25: liest eine SKILL.md und liefert ihren Inhalt.

    Liefert "" wenn nicht vorhanden.
    """
    pfad = SKILLS_DIR / name / "SKILL.md"
    if not pfad.exists():
        return ""
    try:
        return pfad.read_text(encoding="utf-8")
    except OSError:
        return ""


def _list_skills() -> list[dict[str, str]]:
    """W25: liefert alle verfuegbaren Skills (name + description).

    Liest die SKILL.md-Header (name, description) aus dem
    YAML-Frontmatter. Kein voller Inhalt.
    """
    import re as _re
    skills: list[dict[str, str]] = []
    if not SKILLS_DIR.exists():
        return skills
    for pfad in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        try:
            text = pfad.read_text(encoding="utf-8")
        except OSError:
            continue
        m_name = _re.search(
            r"^name:\s*(.+)$", text, _re.MULTILINE)
        # description ist mehrzeilig (|).
        m_desc = _re.search(
            r"^description:\s*\|\s*\n"
            r"((?:\s{2,}.+\n)+)",
            text, _re.MULTILINE)
        name = (m_name.group(1).strip()
                if m_name else pfad.parent.name)
        if m_desc:
            desc_roh = m_desc.group(1)
            # Einrueckung entfernen.
            desc = "\n".join(
                z.strip() for z in desc_roh.splitlines()
                if z.strip())
        else:
            desc = ""
        skills.append({"name": name, "description": desc})
    return skills


def _lade_skill_in_state(state: RunState, name: str) -> None:
    """W25: laedt eine Skill in state.geladene_skills."""
    if not name:
        return
    if name not in state.geladene_skills:
        state.geladene_skills.append(name)
        audit("skill_geladen", {"name": name},
              state.project_dir, state.project_name)


def _available_skills_block() -> str:
    """W25: baut AVAILABLE-SKILLS-Block fuer Prompt.

    Listet alle Skills mit name + description (erste Zeile).
    Der Agent kann per COMMAND: load_skill <name> laden.
    """
    skills = _list_skills()
    if not skills:
        return ""
    teile = ["=== AVAILABLE SKILLS ==="]
    for s in skills:
        desc_kurz = (
            s["description"].split("\n")[0][:100]
            if s["description"] else "")
        teile.append(f"  - {s['name']}: {desc_kurz}")
    teile.append(
        "=== /AVAILABLE SKILLS ===\n"
        "Bei Bedarf: COMMAND: load_skill <name>\n\n")
    return "\n".join(teile)


def _geladene_skills_block(state: RunState) -> str:
    """W25: baut GELADENE-SKILLS-Block fuer Prompt."""
    if not state.geladene_skills:
        return ""
    teile = ["=== GELADENE SKILLS ==="]
    for name in state.geladene_skills:
        inhalt_skill = _load_skill(name)
        if inhalt_skill:
            teile.append(f"\n--- {name} ---\n{inhalt_skill}")
    teile.append("=== /GELADENE SKILLS ===\n\n")
    return "\n".join(teile)


def _verarbeite_skill_commands(
        state: RunState,
        cmds: list[dict[str, str]],
) -> tuple[list[dict[str, str]], int]:
    """W25: verarbeitet load_skill-Commands.

    Rueckgabe: (rest_cmds, anzahl_geladen).
    rest_cmds enthaelt nur noch run/frage_reviewer.
    """
    skills = [c for c in cmds
              if c.get("typ") == "load_skill"]
    rest = [c for c in cmds
            if c.get("typ", "run") != "load_skill"]
    for c in skills:
        _lade_skill_in_state(state, c.get("arg", ""))
    return rest, len(skills)


def _schreibe_plan(state: RunState, plan_text: str) -> bool:
    """W26: schreibt PLAN.md an zwei Stellen.

    - .werkstatt/plan.md im Ziel-Projekt (editierbar).
    - audit-logs/<run_id>/01-plan.md (Audit).

    Liefert True bei Erfolg, False bei Fehler.
    """
    if not plan_text:
        return False
    # .werkstatt/plan.md im Projekt.
    plan_pfad = _plan_pfad(state)
    try:
        plan_pfad.parent.mkdir(parents=True, exist_ok=True)
        plan_pfad.write_text(plan_text, encoding="utf-8")
    except OSError as exc:
        print(f"[WARN] _schreibe_plan (Projekt): {exc}")
    # audit-logs/<run_id>/01-plan.md.
    audit_pfad = _plan_audit_pfad(state)
    try:
        audit_pfad.parent.mkdir(parents=True, exist_ok=True)
        audit_pfad.write_text(plan_text, encoding="utf-8")
    except OSError as exc:
        print(f"[WARN] _schreibe_plan (Audit): {exc}")
    return True


def _contract_aus_unterblock(unterblock: dict) -> str:
    """W27: baut Markdown-Contract aus einem Unterblock.

    Enthaelt: id, titel, Kontext, Fail-closed,
    Grenzen, Akzeptanz, Abhaengigkeiten, Unterpunkte.
    """
    uid = unterblock.get("id", "?")
    titel = unterblock.get("titel", "")
    unterpunkte = unterblock.get("unterpunkte", [])
    teile = [f"# {uid}: {titel}\n"]
    # Unterpunkte als Markdown-Liste.
    teile.append("## Unterpunkte\n")
    for up in unterpunkte:
        if isinstance(up, str):
            teile.append(f"- {up}")
        elif isinstance(up, dict):
            teile.append(f"- {up.get('text', '')}")
    return "\n".join(teile) + "\n"


def _schreibe_contract(
        state: RunState, unterblock: dict) -> bool:
    """W27: schreibt einen Contract fuer einen Unterblock.

    Liefert True bei Erfolg.
    """
    uid = unterblock.get("id", "")
    if not uid:
        return False
    text = _contract_aus_unterblock(unterblock)
    pfad = _contract_pfad(state, uid)
    try:
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_text(text, encoding="utf-8")
        return True
    except OSError as exc:
        print(f"[WARN] _schreibe_contract ({uid}): {exc}")
        return False


# Phasen-Header (2026-10-16): Konstante Texte,
# damit der Reviewer seine Phase erkennt.
_PHASE_HEADER_CODE_REVIEW = (
    "## PHASE: CODE-REVIEW (Phase 1)\n")
def ask_reviewer_for_recovery(state: RunState, art: str, kontext: str) -> RecoveryVorschlag:
    # Auflage 2153: Auftrag vor dem Kontext.
    # Whitelist-Prompt-A2 (2026-10-16).
    _wl = _format_whitelist_block(
        list(getattr(state, "file_whitelist", []) or []))
    kopf = aufgabe_block(state) + _wl
    if art == "basis_gate":
        aufgabe = ("Das Basis-Gate ist rot und der deterministische "
                   "Auto-Repair-Versuch ist gescheitert.\n\n"
                   f"{kopf}{kontext}\n\n"
                   "Liefere:\nDIAGNOSE: <Ursache>\nREPARATURPLAN:\n  1. ...\n"
                   "  2. ...\nBLOCKGROESSE: <ein Block | mehrere Bloecke | eigener Punkt>\n"
                   "EMPFEHLUNG: <was der Mensch tun soll>\n")
    elif art == "no_go":
        aufgabe = (f"Der Builder hat kein akzeptables Ergebnis geliefert.\n\n{kopf}{kontext}\n\n"
                   "Liefere:\nDIAGNOSE: <warum>\nLOESUNGSVORSCHLAG:\n  1. ...\n  2. ...\n"
                   "BLOCKGROESSE: <...>\nEMPFEHLUNG: <approve | reject | aufteilen | eskalieren>\n")
    elif art == "eskalation":
        aufgabe = (f"Du hast ESKALATION ausgesprochen.\n\n{kopf}{kontext}\n\n"
                   "Liefere:\nDIAGNOSE: <Kern>\nFRAGE AN DEN MENSCHEN: <was>\n"
                   "OPTIONEN:\n  A) ...\n  B) ...\nBLOCKGROESSE: <...>\n"
                   "EMPFEHLUNG: <welche Option>\n")
    elif art == "budget":
        aufgabe = (f"Das Budget ist erschoepft.\n\n{kopf}{kontext}\n\n"
                   "Liefere:\nDIAGNOSE: <warum>\nLOESUNGSVORSCHLAG:\n  1. ...\n  2. ...\n"
                   "BLOCKGROESSE: <...>\nEMPFEHLUNG: <naechster Schritt>\n")
    elif art == "builder_command_deadlock":
        aufgabe = (
            f"Der Builder hat in aufeinanderfolgenden Runden nur "
            f"COMMAND-Zeilen geliefert (Builder-COMMAND-Loop, "
            f"Auflage 2187), keinen Code-Patch.\n\n{kopf}{kontext}\n\n"
            "Liefere:\nDIAGNOSE: <warum liefert der Builder keinen Patch>\n"
            "LOESUNGSVORSCHLAG:\n  1. ...\n  2. ...\n"
            "BLOCKGROESSE: <...>\n"
            "EMPFEHLUNG: <approve | reject | aufteilen | eskalieren>\n"
        )
    else:
        return RecoveryVorschlag(art=art, rohantwort="(unbekannt)")

    reply = ask_llm(
        state.api_key,
        build_system_prompt(
            state.agents["reviewer"], state.docs,
            state.agent_docs.get("reviewer", []),
            mit_anti_patterns=False),
        aufgabe,
        state.reviewer_recovery_model,
        0.0,
        state.llm_timeout_s,
        state=state,
        max_tokens=state.max_tokens_reviewer,
    )
    if not reply.ok:
        return RecoveryVorschlag(art=art,
                                 diagnose="(Reviewer nicht erreichbar)",
                                 empfehlung=f"API-Fehler: {reply.error}",
                                 rohantwort=reply.error)
    v = RecoveryVorschlag(art=art, rohantwort=reply.content)
    abschnitt = None
    for line in reply.content.splitlines():
        s = line.strip()
        if s.upper().startswith("DIAGNOSE:"):
            v.diagnose = s.split(":", 1)[1].strip()
            abschnitt = None
        elif s.upper().startswith("FRAGE AN DEN MENSCHEN:"):
            v.frage_an_menschen = s.split(":", 1)[1].strip()
            abschnitt = None
        elif s.upper().startswith(("REPARATURPLAN:", "LOESUNGSVORSCHLAG:", "OPTIONEN:")):
            abschnitt = "plan"
        elif s.upper().startswith("BLOCKGROESSE:"):
            v.blockgroesse = s.split(":", 1)[1].strip()
            abschnitt = None
        elif s.upper().startswith("EMPFEHLUNG:"):
            v.empfehlung = s.split(":", 1)[1].strip()
            abschnitt = None
        elif abschnitt == "plan" and s:
            m = re.match(r"^\s*(?:\d+\.|[-*]|[A-Z]\))\s*(.+)$", s)
            if m:
                v.reparaturplan.append(m.group(1).strip())
    return v


def print_recovery(v: RecoveryVorschlag) -> None:
    print("\n" + "=" * 70)
    print(f"LOESUNGSVORSCHLAG DES REVIEWERS (Stop: {v.art})")
    print("=" * 70)
    if v.diagnose:
        print(f"\nDIAGNOSE:\n  {v.diagnose}")
    if v.reparaturplan:
        print("\nPLAN:")
        for i, s in enumerate(v.reparaturplan, 1):
            print(f"  {i}. {s}")
    if v.blockgroesse:
        print(f"\nBLOCKGROESSE: {v.blockgroesse}")
    if v.frage_an_menschen:
        print(f"\nFRAGE AN DEN MENSCHEN:\n  {v.frage_an_menschen}")
    if v.empfehlung:
        print(f"\nEMPFEHLUNG: {v.empfehlung}")
    print("\n--- ROHE ANTWORT ---")
    print(v.rohantwort)
    print("=" * 70)



def budget_or_recover(state: RunState, max_llm: int, kontext: str,
                      project_dir: Path, project_name: str,
                      max_minutes: int = 0) -> int | None:
    """Auflage 2081 + 2080: einheitlicher Budget-Check mit Recovery.

    Prueft LLM-Budget (max_llm) und Zeitbudget (max_minutes).
    Bei BudgetExhausted (aus beiden Dimensionen):
    - ruft ask_reviewer_for_recovery("budget", kontext) auf,
    - gibt den Vorschlag aus,
    - schreibt recovery_budget ins Audit,
    - liefert Exit-Code 13.
    Sonst None (Aufrufer faehrt normal fort).

    Der Recovery-Kontext enthaelt beide Dimensionen,
    damit der Reviewer weiss, welche erschoepft ist (P3).
    """
    try:
        require_budget(state, max_llm)
        require_budget_time(state, max_minutes)
    except BudgetExhausted as exc:
        print(f"[!] {exc}")
        # P3: Kontext um beide Dimensionen ergaenzen.
        verstrichen_s = 0.0
        if state.start_monotonic > 0:
            verstrichen_s = time.monotonic() - state.start_monotonic
        kontext_voll = (
            f"{kontext}\n"
            f"LLM: {state.llm_calls}/{max_llm}, "
            f"Zeit: {verstrichen_s:.0f}s/{max_minutes * 60}s"
        )
        v = ask_reviewer_for_recovery(state, "budget", kontext_voll)
        print_recovery(v)
        audit("recovery_budget", {"kontext": kontext_voll},
              project_dir, project_name)
        return 13
    return None


def trim_output(out: str, grenze: int = MAX_PROTOKOLL_PER_COMMAND) -> str:
    """Kuerzt ein Messprotokoll-Stueck auf `grenze` Zeichen (Auflage 2041)."""
    if len(out) <= grenze:
        return out
    rest = len(out) - grenze
    return out[:grenze] + f"\n[... gekuerzt, {rest} Zeichen weggelassen ...]\n"


# Truncation-Fix (2026-10-16): gemeinsame Kontext-Grenze
# fuer Reviewer-Recovery-Kontexte.
_REVIEWER_KONTEXT_MAX = 2000


def _truncate_mit_marker(text: str, max_len: int) -> str:
    """Truncation-Fix (2026-10-16): kuerzt mit
    sichtbarem Marker.

    Bei len(text) > max_len: schneidet auf max_len
    und haengt einen Marker an. Der Marker ist klar
    erkennbar und verhindert, dass ein LLM aus dem
    abgeschnittenen Text falsche Schluesse zieht.
    """
    if len(text) <= max_len:
        return text
    rest = len(text) - max_len
    return (text[:max_len]
            + f"\n[... Kontext gekuerzt, {rest} "
            + "Zeichen weggelassen ...]\n")


def _schreibe_messung(
        state: RunState,
        pfad: str,
        inhalt: str,
        quelle: str,
        mtime: float,
) -> None:
    """W52b (2026-10-18): schreibt eine Messung als Datei.

    Ergaenzt state.messungen, state.gelesene_dateien
    (W59) und state.mess_protokoll (deprecated, fuer
    Bestandsleser).

    Pfad: .werkstatt/<run_id>/messungen/<sha1>.txt.
    """
    import hashlib
    from pathlib import Path as _P
    sha1 = hashlib.sha1(
        inhalt.encode("utf-8", errors="replace")).hexdigest()
    # Verzeichnis.
    run_id = state.run_id or "unbekannt"
    mess_dir = _P("/opt/werkstatt/.werkstatt") / run_id \
        / "messungen"
    try:
        mess_dir.mkdir(parents=True, exist_ok=True)
        datei = mess_dir / f"{sha1}.txt"
        datei.write_text(inhalt, encoding="utf-8")
    except OSError as exc:
        print(f"[WARN] Messung-Datei: {exc}")
        datei = None
    # state.messungen.
    from werkstatt.state import Messung
    state.messungen.append(Messung(
        pfad=pfad,
        sha1=sha1,
        mtime=mtime,
        groesse=len(inhalt.encode("utf-8",
                                  errors="replace")),
        quelle=quelle,
        datei=datei,
    ))
    # W59: gelesene Datei + mtime.
    state.gelesene_dateien[pfad] = mtime
    # Deprecated: String-Kanal.
    state.mess_protokoll += inhalt


def execute_commands(state: RunState, commands: list[dict[str, str]],
                     quelle: str
                     ) -> dict[tuple[str, str], bool]:
    """Fuehrt COMMAND-Zeilen aus. NUR wenn id in state.always oder state.optional.

    Auflagen 2039, 2040, 2041, 2042:
      - arg muss str sein.
      - argv geht ins Audit.
      - mess_protokoll wird begrenzt.
      - quelle ist ein Marker, kein Prompt-Text.
    """
    # Auflage 2042: quelle auf erlaubte Marker beschraenken.
    if quelle not in ERLAUBTE_QUELLEN:
        audit("quelle_invalid", {"quelle": str(quelle)[:80]}, state.project_dir, state.project_name)
        print(f"[WARN] Ungueltiger quelle-Marker: {str(quelle)[:80]}")
        quelle = "unknown"

    erlaubt = set(state.always.keys()) | set(state.optional.keys())
    katalog: dict[str, Measurement] = {}
    katalog.update(state.always)
    katalog.update(state.optional)

    ergebnisse: dict[tuple[str, str], bool] = {}
    for cmd in commands:
        cid = cmd.get("id", "")
        arg = cmd.get("arg", "")

        # Auflage 2039: id und arg muessen str sein.
        if not isinstance(cid, str) or not cid:
            audit("command_rejected",
                  {"id": str(cid)[:80], "arg": str(arg)[:80],
                   "quelle": quelle, "grund": "id_kein_str"},
                  state.project_dir, state.project_name)
            continue
        if not isinstance(arg, str):
            audit("command_rejected",
                  {"id": cid, "arg": str(arg)[:80],
                   "quelle": quelle, "grund": "arg_kein_str"},
                  state.project_dir, state.project_name)
            continue

        if cid not in erlaubt:
            print(f"[!] COMMAND abgelehnt (nicht in Whitelist): {cid}")
            audit("command_rejected",
                  {"id": cid, "arg": arg[:200], "quelle": quelle,
                   "grund": "nicht_in_whitelist"},
                  state.project_dir, state.project_name)
            continue

        m = katalog[cid]
        out, ok, argv = run_measurement_mit_argv(
            m, state.file_whitelist, state.project_dir,
            arg if cid == "read_file" else None,
        )
        # W6a-4 (2026-10-16): read_file darf groesser
        # sein (Anker-Zeilen sind oft tief in
        # grossen Dateien).
        # W51d: quelle-abhaengige Grenzen.
        if quelle == "planner":
            _grenze = (
                _PLANNER_PROTOKOLL_PER_READ
                if cid == "read_file"
                else MAX_PROTOKOLL_PER_COMMAND)
            _total = _PLANNER_PROTOKOLL_TOTAL
        else:
            _grenze = (
                MAX_PROTOKOLL_PER_COMMAND_READ_FILE
                if cid == "read_file"
                else MAX_PROTOKOLL_PER_COMMAND)
            _total = MAX_PROTOKOLL_TOTAL
        out = trim_output(out, grenze=_grenze)

        # Auflage 2041: Gesamtlaenge begrenzen.
        rest_platz = _total - len(state.mess_protokoll)
        if rest_platz <= 0:
            print("[!] mess_protokoll Gesamtlimit "
                  "erreicht. Weitere Messungen "
                  "werden nur auditiert.")
            audit("mess_protokoll_limit_erreicht",
                  {"len": len(state.mess_protokoll),
                   "total": _total,
                   "quelle": quelle},
                  state.project_dir, state.project_name)
            audit("command_executed",
                  {"id": cid, "arg": arg[:200], "argv": argv,
                   "quelle": quelle, "ok": ok, "ausgabe_verworfen": True},
                  state.project_dir, state.project_name)
            continue
        if len(out) > rest_platz:
            out = out[:rest_platz] + "\n[... Gesamtlimit erreicht ...]\n"

        # W51g: Dedup nur fuer Planner + read_file.
        _dedup_skip = False
        if (quelle == "planner" and cid == "read_file"
                and ok):
            _gem = getattr(
                state, "_w51g_gemessen", None)
            if _gem is not None and arg in _gem:
                _dedup_skip = True
        if _dedup_skip:
            ergebnisse[(cid, arg)] = ok
            audit("command_executed",
                  {"id": cid, "arg": arg[:200],
                   "argv": argv, "quelle": quelle,
                   "ok": ok, "dedup_verworfen": True},
                  state.project_dir, state.project_name)
            continue
        # W52b (2026-10-18): Messung als Datei
        # + state.messungen + state.gelesene_dateien.
        # mtime nur bei read_file (Datei-Messung).
        _mtime = 0.0
        if cid == "read_file" and ok:
            try:
                _mtime = (state.project_dir / arg).stat().st_mtime
            except OSError:
                _mtime = 0.0
        if ok:
            _schreibe_messung(
                state, arg, out, quelle, _mtime)
            if (quelle == "planner"
                    and cid == "read_file"):
                _gem = getattr(
                    state, "_w51g_gemessen", None)
                if _gem is not None:
                    _gem.add(arg)
        else:
            _schreibe_messung(
                state, arg,
                "\n\n!!! COMMAND FEHLGESCHLAGEN: "
                f"{cid} {arg} !!!\n"
                "Der COMMAND hat ok=false geliefert. "
                "Ursache im Output unten.\n"
                "Wenn der Pfad falsch war: pruefe den "
                "Pfad woertlich aus dem Auftrag, aus "
                "dem ZIELDATEIEN-Header oder aus dem "
                "KUERZUNGS-MARKER. Rekonstruiere ihn "
                "nicht.\n\n"
                + out,
                quelle, _mtime)
        ergebnisse[(cid, arg)] = ok

        # Auflage 2040: argv ins Audit.
        audit("command_executed",
              {"id": cid, "arg": arg[:200], "argv": argv,
               "quelle": quelle, "ok": ok},
              state.project_dir, state.project_name)

    return ergebnisse



def parse_commit_paket(text: str) -> dict[str, Any]:
    """Parst die Builder-Antwort fuer das Commit-Paket.

    Erwartet:
      COMMIT-MESSAGE:
      <...>
      ENDE COMMIT-MESSAGE
      BETROFFENE DATEIEN:
        - <pfad>
      ENDE BETROFFENE DATEIEN
      DOKU-PATCHES:
        - pfad: <pfad>
          anker: <text>
          ersatz: <text>
      ENDE DOKU-PATCHES
    """
    paket: dict[str, Any] = {"message": "", "dateien": [], "doku_patches": []}

    m = re.search(r"COMMIT-MESSAGE:\s*\n(.*?)\nENDE COMMIT-MESSAGE",
                  text, re.DOTALL)
    if m:
        paket["message"] = m.group(1).strip()

    m = re.search(r"BETROFFENE DATEIEN:\s*\n(.*?)\nENDE BETROFFENE DATEIEN",
                  text, re.DOTALL)
    if m:
        for line in m.group(1).splitlines():
            s = line.strip().lstrip("-*").strip()
            if s:
                paket["dateien"].append(s)

    m = re.search(r"DOKU-PATCHES:\s*\n(.*?)\nENDE DOKU-PATCHES",
                  text, re.DOTALL)
    if m:
        paket["doku_patches"] = _parse_patches(m.group(1))

    return paket


def record_code_entwurf(state: RunState, entwurf: str,
                        phase: str = "normal") -> None:
    """Auflage 2183 A1b: speichert Builder-Entwurf in der Historie.

    Setzt state.code_entwurf UND haengt einen Eintrag
    an state.code_entwurf_historie an.

    Eintrag: {runde, entwurf, phase}.
    runde = len(review_runden) + 1 (naechste Runde).
    phase = "normal" oder "recovery".
    Kuerzung: max 10 Eintraege, aeltester faellt weg.

    A1b-fix (2026-10-18): Wird produktiv aus dem
    Builder-Pfad gerufen (Z. 7960 recovery, Z. 9373
    normal, Z. 9796 normal, Z. 9843 normal).
    Vorher wurde state.code_entwurf direkt gesetzt
    und die Historie blieb leer — Folge: der Solver
    sah "(keine Historie)".

    Leerer entwurf wird protokolliert. Das ist ein
    Builder-Bug, nicht ein Bug in dieser Funktion.
    """
    state.code_entwurf = entwurf
    runde = len(state.review_runden) + 1
    state.code_entwurf_historie.append(
        {"runde": runde, "entwurf": entwurf, "phase": phase})
    if len(state.code_entwurf_historie) > 10:
        state.code_entwurf_historie.pop(0)


def parse_code_patches(text: str) -> list[dict[str, str]]:
    """UMB-1a: parst die Builder-Antwort fuer Code-Patches.

    Format: direkt PATCH-BEGINN/PATCH-ENDE-Bloecke, ohne
    Container-Marker.

      PATCH-BEGINN
      pfad: tools/disk_usage.py
      anker: |
        <alter Text>
      ersatz: |
        <neuer Text>
      PATCH-ENDE

      PATCH-BEGINN
      ...
      PATCH-ENDE

    Liefert eine Liste von Patches. Leere Liste, wenn
    keine Patches gefunden wurden.
    """
    return _parse_patches(text)


def _parse_patches(block_text: str) -> list[dict[str, str]]:
    """Parst PATCH-BEGINN/PATCH-ENDE-Bloecke (Auflagen 2088 + 2098).

    Wird sowohl fuer DOKU-PATCHES (parse_commit_paket) als
    auch fuer CODE-PATCHES (parse_code_patches) verwendet.
    

    Format:
      PATCH-BEGINN
      pfad: docs/PHASES.md
      anker: |
        <mehrzeilig>
      ersatz: |
        <mehrzeilig, darf leer sein>
      PATCH-ENDE

    Regeln:
    - Reihenfolge von pfad/anker/ersatz ist frei (P2).
    - Einrueckung ist 2 Spaces, Tabs werden abgelehnt (P1).
    - anker fehlt oder leer -> Patch verworfen.
    - pfad fehlt oder leer -> Patch verworfen.
    - ersatz darf leer sein (Loeschung).
    """
    ergebnis: list[dict[str, str]] = []
    # Bloecke an PATCH-BEGINN/PATCH-ENDE trennen.
    for match in re.finditer(
        r"PATCH-BEGINN\s*\n(.*?)\n\s*PATCH-ENDE",
        block_text, re.DOTALL,
    ):
        block = match.group(1)
        gepatcht = _parse_einzelpatch(block)
        if gepatcht is not None:
            ergebnis.append(gepatcht)
    return ergebnis


def _parse_einzelpatch(block: str) -> dict[str, str] | None:
    """Parst einen einzelnen PATCH-BEGINN-Block.

    Liefert dict oder None, wenn der Block ungueltig ist.
    """
    pfad = ""
    typ = "patch"
    inhalt: str | None = None
    anker: str | None = None
    ersatz: str | None = None
    aktives_feld: str | None = None
    aktuelle_zeilen: list[str] = []

    def _flush() -> None:
        nonlocal aktives_feld, aktuelle_zeilen
        if aktives_feld is None:
            return
        # W61: YAML-Block-Scalar-Heuristik.
        # Die minimale Einrueckung der nicht-leeren
        # Zeilen bestimmt den Modus:
        #   == 2  -> YAML-Standard, strippe 2.
        #   >  2  -> Builder-Code, Einrueckung erhalten.
        #   <  2  -> kein Block, roh.
        _nicht_leer = [z for z in aktuelle_zeilen if z.strip()]
        if _nicht_leer:
            _min = min(len(z) - len(z.lstrip())
                       for z in _nicht_leer)
            # W61-Pro: min 2 (YAML-Standard) oder 4
            # (Builder-Code im Block) strippen. min > 4:
            # erhalten (echter Code).
            if _min in (2, 4):
                aktuelle_zeilen = [
                    (z[_min:] if z.startswith(" " * _min) else z)
                    for z in aktuelle_zeilen
                ]
        wert = "\n".join(aktuelle_zeilen)
        if aktives_feld == "anker":
            nonlocal anker
            anker = wert
        elif aktives_feld == "ersatz":
            nonlocal ersatz
            ersatz = wert
        elif aktives_feld == "inhalt":
            nonlocal inhalt
            inhalt = wert
        elif aktives_feld == "pfad":
            nonlocal pfad
            pfad = wert.strip()
        elif aktives_feld == "typ":
            nonlocal typ
            typ = wert.strip()
        aktives_feld = None
        aktuelle_zeilen = []

    # W61: Einrueckung der aktuellen Feldzeile.
    feld_einrueckung = 0
    for raw_line in block.splitlines():
        # Tabs ablehnen (P1).
        if "\t" in raw_line:
            return None
        # Feld-Anfang?
        # P2b-Luecke-A: typ und inhalt ergaenzt.
        # W61: Anchored at start (Einrueckung wird
        # explizit gemessen).
        _feld_match = re.match(
            r"^\s*(typ|pfad|anker|ersatz|inhalt):\s*(.*)$",
            raw_line)
        m_feld = _feld_match
        if m_feld:
            # Einrueckung der Feldzeile merken.
            feld_einrueckung = (
                len(raw_line) - len(raw_line.lstrip()))
        if m_feld:
            _flush()
            name, rest = m_feld.group(1), m_feld.group(2)
            if name == "pfad" or name == "typ":
                if rest.startswith("|"):
                    aktives_feld = name
                    aktuelle_zeilen = []
                else:
                    if name == "pfad":
                        pfad = rest.strip()
                    else:
                        typ = rest.strip()
            else:
                # anker / ersatz / inhalt muessen "|" haben.
                if not rest.startswith("|"):
                    return None
                aktives_feld = name
                aktuelle_zeilen = []
            continue
        # Fortsetzungszeile (eingrueckt).
        # W61: Roh uebernehmen. Der Builder liefert die
        # Code-Einrueckung bereits im YAML-Block. Der
        # Parser strippt nichts (die YAML-Block-Scalar-
        # Semantik wuerde sonst die Code-Einrueckung
        # entfernen). _anker_in_messung ist whitespace-
        # tolerant, apply_code_patches nutzt den
        # +2-Shift-Fallback.
        if aktives_feld is not None:
            if raw_line.strip() == "":
                aktuelle_zeilen.append("")
            elif not re.match(
                    r"^\s*(typ|pfad|anker|ersatz|inhalt):",
                    raw_line):
                # W61: Jede Zeile, die kein neues Feld
                # beginnt, gehoert zum Block — auch ohne
                # Einrueckung (Code auf Spalte 0).
                aktuelle_zeilen.append(raw_line)
            else:
                # Neues Feld: Block beenden.
                _flush()
        # Sonst: ignorieren (z.B. Leerzeile ausserhalb).

    _flush()

    # Validierung.
    if not pfad:
        return None
    # P2b-Luecke-A: typ-Weiche.
    if typ == "new_file":
        # anker/ersatz sind verboten.
        if anker is not None or ersatz is not None:
            return None
        if inhalt is None:
            inhalt = ""
        return {"typ": "new_file", "pfad": pfad,
                "inhalt": inhalt}
    if typ != "patch":
        return None
    # Alter Pfad: typ=patch.
    if anker is None or anker == "":
        return None
    if ersatz is None:
        ersatz = ""
    return {"typ": "patch", "pfad": pfad,
            "anker": anker, "ersatz": ersatz}


def _rollback_zieldateien(state: RunState,
                         project_dir: Path,
                         project_name: str,
                         grund: str) -> None:
    """Auflage 2197 + 2026-10-16: Fail-closed-Rollback.

    Setzt alle Pfade aus state.code_patches zurueck.
    - typ="patch": git checkout -- <pfad> (modifiziert).
    - typ="new_file": rm -rf <pfad> (untracked, wird
      angelegt).
    Best effort: Fehler brechen nicht ab.
    """
    if not state.code_patches:
        return
    pfade_patch: list[str] = []
    pfade_new: list[str] = []
    for p in state.code_patches:
        if not isinstance(p, dict):
            continue
        pfad = p.get("pfad", "")
        if not pfad:
            continue
        typ = p.get("typ", "patch")
        if typ == "new_file":
            if pfad not in pfade_new:
                pfade_new.append(pfad)
        else:
            if pfad not in pfade_patch:
                pfade_patch.append(pfad)
    if not pfade_patch and not pfade_new:
        return
    try:
        res = subprocess.run(
            ("git", "status", "--porcelain", "-uall"),
            cwd=str(project_dir), capture_output=True, text=True,
            timeout=30, check=False, env=subprocess_env(),
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        audit("rollback_fail_closed",
              {"grund": grund, "fehler": f"git status: {exc}"},
              project_dir, project_name)
        return
    geaendert = {
        line[3:].strip()
        for line in res.stdout.splitlines()
        if line.startswith(" M")
    }
    untracked = {
        line[3:].strip()
        for line in res.stdout.splitlines()
        if line.startswith("??")
    }
    zurueckgesetzt = []
    entfernt = []
    for pfad in pfade_patch:
        if pfad in geaendert:
            try:
                subprocess.run(
                    ("git", "checkout", "--", pfad),
                    cwd=str(project_dir), capture_output=True,
                    text=True, timeout=30, check=False,
                    env=subprocess_env(),
                )
                zurueckgesetzt.append(pfad)
            except (subprocess.TimeoutExpired, OSError):
                pass
    # F2-A1 (2026-10-16): vor unlink git reset HEAD,
    # damit intent-to-add-Eintraege (git add -N)
    # sauber aus dem Index entfernt werden. Sonst
    # bleibt der Working Tree dirty.
    _pfade_zum_reset = [
        pfad for pfad in pfade_new
        if pfad in untracked or pfad in geaendert
    ]
    if _pfade_zum_reset:
        try:
            subprocess.run(
                ("git", "reset", "HEAD", "--",
                 *_pfade_zum_reset),
                cwd=str(project_dir),
                capture_output=True, text=True,
                timeout=30, check=False,
                env=subprocess_env(),
            )
        except (subprocess.TimeoutExpired, OSError):
            pass  # best-effort cleanup
    for pfad in pfade_new:
        if pfad in untracked or pfad in geaendert:
            try:
                ziel = project_dir / pfad
                if ziel.exists():
                    if ziel.is_dir():
                        import shutil as _sh
                        _sh.rmtree(ziel)
                    else:
                        ziel.unlink()
                    entfernt.append(pfad)
            except OSError:
                pass
    if zurueckgesetzt:
        print(f"[i] Fail-closed-Rollback (patch): {zurueckgesetzt}")
    if entfernt:
        print(f"[i] Fail-closed-Rollback (new_file): {entfernt}")
    audit("rollback_fail_closed",
          {"grund": grund, "zieldateien": zurueckgesetzt,
           "entfernt": entfernt,
           "gepruefte_patch": pfade_patch,
           "gepruefte_new": pfade_new},
          project_dir, project_name)


def _pipeline_ende(state: RunState, project_dir: Path,
                   project_name: str, rc: int,
                   grund: str = "") -> None:
    """Auflage 2183-P4-Log: schreibt pipeline_ende-Audit.

    Enthaelt llm_calls am Loop-Ende. Wird an allen
    Rueckgabepfaden von run_pipeline und in _fail_closed
    gerufen.
    """
    audit("pipeline_ende",
          {"rc": rc,
           "llm_calls": state.llm_calls,
           "runden": len(state.review_runden),
           "grund": grund[:200]},
          project_dir, project_name)


def _fail_closed(state: RunState, project_dir: Path,
                 project_name: str, code: int,
                 grund: str) -> int:
    """Auflage 2197: Rollback + Exit-Code.

    Zentrale Stelle fuer alle Fail-closed-Abbrueche im
    Commit-Pfad. Setzt den Arbeitsbaum zurueck und liefert
    den Exit-Code.
    """
    _rollback_zieldateien(state, project_dir, project_name, grund)
    return code


def handle_deadlock_mit_solver(
    state: RunState,
    api_key: str,
    project_dir: Path,
    project_name: str,
    max_llm: int,
    max_minutes: int,
) -> int | None:
    """B5 (MM6): Solver + B2 im Deadlock-Pfad.

    Liefert rc (0 bei B2-Erfolg) oder None wenn
    Fail-closed-Pfad weiter genutzt werden soll.
    """
    _trigger_grund = ""
    if state.letzter_patch_wirkungslos:
        _trigger_grund = "wirkungsloser_patch"
        audit("solver_trigger_c",
              {"pfad": "deadlock"},
              project_dir, project_name)
    elif state.anker_fehler_in_folge >= 2:
        _trigger_grund = "anker_nicht_gemessen"
        audit("solver_trigger_a",
              {"pfad": "deadlock",
               "in_folge": state.anker_fehler_in_folge},
              project_dir, project_name)
    if not _trigger_grund:
        return None

    rc_solver = budget_or_recover(
        state, max_llm,
        "Vor Solver-Call (Deadlock).",
        project_dir, project_name,
        max_minutes=max_minutes)
    if rc_solver is not None:
        audit("solver_budget_exhausted",
              {"pfad": "deadlock"},
              project_dir, project_name)
        return None

    _msr = int(state.solver_config.get(
        "max_runden", MAX_SOLVER_RUNDEN_DEFAULT))
    # W48-A16-b-2-a (2026-10-18): Merge zu
    # solver_max_runden_erreicht. Payload
    # symmetrisch (aufrufe, max_runden in beiden
    # Pfaden). pfad-Feld trennt no_go/deadlock.
    if not erhoehe_solver_aufruf(state, _msr):
        audit("solver_max_runden_erreicht",
              {"pfad": "deadlock",
               "aufrufe": state.solver_aufrufe,
               "max_runden": _msr,
               "grund": _trigger_grund},
              project_dir, project_name)
        return None

    solver_prompt = build_system_prompt(
        state.agents["solver"], state.docs,
        state.agent_docs.get("solver", []))
    befund, fehler = rufe_solver(
        state, api_key, solver_prompt,
        grund_text=_trigger_grund,
        trigger_grund=_trigger_grund,
        aufrufer="deadlock")
    if befund is None:
        audit("solver_failed",
              {"pfad": "deadlock", "grund": fehler},
              project_dir, project_name)
        return None
    state.solver_befunde.append(befund)
    state.solver_trigger_quellen.append(_trigger_grund)
    audit("solver_befund",
          {"pfad": "deadlock",
           "art": befund.art.name,
           "run_id": befund.run_id,
           "quelle": _trigger_grund},
          project_dir, project_name)

    if pruefe_auftrag_bereits_erfuellt(state):
        print("[+] Auftrag bereits erfuellt (Deadlock).")
        audit("auftrag_bereits_erfuellt",
              {"runden": len(state.review_runden),
               "art": befund.art.name,
               "trigger_grund": _trigger_grund,
               "pfad": "deadlock"},
              project_dir, project_name)
        audit("pipeline_erfolg_ohne_commit",
              {"grund": "auftrag_bereits_erfuellt"},
              project_dir, project_name)
        return 0
    return None


def pruefe_auftrag_bereits_erfuellt(state: RunState) -> bool:
    """Block Auftrag-erfuellt, B2: Auftrag bereits erfuellt?

    Bedingungen (JJ4, JJ5a):
      - state.letzter_patch_wirkungslos ist True.
      - Solver-Befund mit Quelle "wirkungsloser_patch".
      - Letzter Befund ist nicht WIDERSPRUCH (JJ4).
    """
    if not state.letzter_patch_wirkungslos:
        return False
    if "wirkungsloser_patch" not in state.solver_trigger_quellen:
        return False
    if not state.solver_befunde:
        return False
    letzter = state.solver_befunde[-1]
    # MM2: Bestaetigung = nicht WIDERSPRUCH, nicht
    # UNKLAR, und vollstaendig.
    if letzter.art in (SolverDiagnose.WIDERSPRUCH,
                       SolverDiagnose.UNKLAR):
        return False
    return letzter.ist_vollstaendig()


def _post_apply_messung(state: RunState,
                        file_whitelist: list[str]) -> bool:
    """Post-Apply-Neumessung (2026-10-16).

    Liest new_file- und patch-Pfade aus
    state.code_patches nach dem Apply (W33a,
    A-W33-5). Ergebnis nach
    state.mess_protokoll_nach_apply. Der bestehende
    mess_protokoll-Kanal bleibt unveraendert
    (Stand VOR Apply).

    Rueckgabe: True bei Erfolg (alle read_file ok
    oder kein new_file-Pfad), False bei Fehler
    (Fail-closed, Aufrufer bricht ab).
    """
    if not state.code_patches:
        return True
    # W33a (A-W33-5): sowohl new_file- als auch
    # patch-Pfade lesen. Vorher nur new_file -> bei
    # reinen patch-Aktionen blieb mess_nach leer,
    # der Judge eskalierte.
    pfade: list[str] = []
    for p in state.code_patches:
        if not isinstance(p, dict):
            continue
        typ = p.get("typ", "")
        if typ not in ("new_file", "patch"):
            continue
        pfad = p.get("pfad", "")
        if pfad and pfad not in pfade:
            pfade.append(pfad)
    if not pfade:
        return True
    m = state.always.get("read_file")
    if m is None:
        m = state.optional.get("read_file")
    if m is None:
        print("[i] Post-Apply-Messung: read_file "
              "nicht im Katalog. Kein Kanal.")
        return True
    neue_bloecke: list[str] = []
    # W61-Pro: strukturierte Messungen sammeln.
    _neue_messungen: list = []
    import hashlib as _hl
    from pathlib import Path as _P

    from werkstatt.state import Messung as _M
    _run_id = state.run_id or "unbekannt"
    _mess_dir = _P("/opt/werkstatt/.werkstatt") / _run_id / "messungen"
    try:
        _mess_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"[FAIL] Post-Apply-Messungen: {exc}")
        audit("mess_dir_fehler",
              {"run_id": _run_id, "exc": str(exc)[:200]},
              state.project_dir, state.project_name)
        return False
    for pfad in pfade:
        out, ok, argv = run_measurement_mit_argv(
            m, file_whitelist, state.project_dir, pfad)
        out = trim_output(out)
        neue_bloecke.append(out)
        if _mess_dir is not None and ok:
            _sha = _hl.sha1(
                out.encode("utf-8", errors="replace")).hexdigest()
            try:
                _datei = _mess_dir / f"{_sha}.txt"
                _datei.write_text(out, encoding="utf-8")
                _neue_messungen.append(_M(
                    pfad=pfad, sha1=_sha, mtime=0.0,
                    groesse=len(out.encode("utf-8", errors="replace")),
                    quelle="post_apply", datei=_datei))
            except OSError:
                pass
        audit("command_executed",
              {"id": "read_file", "arg": pfad[:200],
               "argv": argv, "quelle": "pipeline_auto",
               "ok": ok, "post_apply": True},
              state.project_dir, state.project_name)
        if not ok:
            print(f"[FAIL] Post-Apply-Messung: "
                  f"read_file fehlgeschlagen: {pfad}")
            return False
    if neue_bloecke:
        state.mess_protokoll_nach_apply = "\n".join(neue_bloecke)
        state.messungen_nach_apply = _neue_messungen
        print(f"[i] Post-Apply-Messung: "
              f"{len(pfade)} read_file-Aufrufe "
              f"({len(_neue_messungen)} strukturiert).")
    return True


def _ziel_test_pfade(state: RunState) -> list[str]:
    """W25-A28: Test-Pfade aus code_patches (startswith tests/)."""
    pfade: list[str] = []
    for p in state.code_patches:
        if not isinstance(p, dict):
            continue
        pfad = p.get("pfad", "")
        if isinstance(pfad, str) and pfad.startswith("tests/"):
            pfade.append(pfad)
    return pfade


def _klassifiziere_pytest(
        exit_code: int | None,
        stdout: str,
        stderr: str,
        dauer_s: float,
        is_timeout: bool = False,
) -> dict[str, Any]:
    """W25-A25/A38: klassifiziert pytest-Ergebnis."""
    import re
    if is_timeout:
        return {
            "exit_code": None,
            "klassifizierung": "timeout",
            "failed_count": -1,
            "passed_count": -1,
            "failed_test_ids": [],
            "failed_test_ids_mehr": 0,
            "raw_tail": "(timeout)",
            "dauer_s": dauer_s,
        }
    klass = {
        0: "gruen",
        1: "test_failures",
        2: "collection_error",
        3: "internal_error",
        4: "usage_error",
        5: "no_tests",
    }.get(exit_code if exit_code is not None else -1,
          "unknown")
    raw = (stdout or "") + "\n" + (stderr or "")
    m_failed = re.search(r"(\d+) failed", stdout)
    m_passed = re.search(r"(\d+) passed", stdout)
    failed_count = int(m_failed.group(1)) if m_failed else -1
    passed_count = int(m_passed.group(1)) if m_passed else -1
    failed_ids: list[str] = []
    for m in re.finditer(r"^FAILED (\S+)", stdout, re.MULTILINE):
        failed_ids.append(m.group(1))
    mehr = max(0, len(failed_ids) - 20)
    return {
        "exit_code": exit_code,
        "klassifizierung": klass,
        "failed_count": failed_count,
        "passed_count": passed_count,
        "failed_test_ids": failed_ids[:20],
        "failed_test_ids_mehr": mehr,
        "raw_tail": raw[-2000:] if len(raw) > 2000 else raw,
        "dauer_s": dauer_s,
    }


def _basis_gate_pytest_ziel(
        project_dir: Path,
        test_pfade: list[str],
        timeout_s: int = 60,
) -> dict[str, Any]:
    """W25: pytest -q --maxfail=1 auf Zieldateien.

    Timeout -> klassifizierung="timeout".
    Leere test_pfade -> wird vom Aufrufer geprueft.
    """
    import subprocess
    import time
    venv = str(project_dir / ".venv/bin/python3")
    # venv-Pfad via state, aber Aufrufer uebergibt
    # project_dir; deshalb hier Fallback. Der Aufrufer
    # (apply_and_recheck) nutzt project_dir/.venv/bin/python3.
    argv = [venv, "-m", "pytest", "-q", "--maxfail=1", *test_pfade]
    start = time.monotonic()
    try:
        res = subprocess.run(
            argv, cwd=str(project_dir),
            capture_output=True, text=True,
            timeout=timeout_s, check=False,
            env=subprocess_env(),
        )
    except subprocess.TimeoutExpired:
        return _klassifiziere_pytest(
            None, "", "", time.monotonic() - start,
            is_timeout=True)
    return _klassifiziere_pytest(
        res.returncode, res.stdout or "",
        res.stderr or "", time.monotonic() - start)


def _basis_gate_pytest_suite(
        project_dir: Path,
        timeout_s: int = 900,
) -> dict[str, Any]:
    """W25: pytest -q --maxfail=10 auf ganzer Suite."""
    import subprocess
    import time
    venv = str(project_dir / ".venv/bin/python3")
    argv = [venv, "-m", "pytest", "-q", "--maxfail=10"]
    start = time.monotonic()
    try:
        res = subprocess.run(
            argv, cwd=str(project_dir),
            capture_output=True, text=True,
            timeout=timeout_s, check=False,
            env=subprocess_env(),
        )
    except subprocess.TimeoutExpired:
        return _klassifiziere_pytest(
            None, "", "", time.monotonic() - start,
            is_timeout=True)
    return _klassifiziere_pytest(
        res.returncode, res.stdout or "",
        res.stderr or "", time.monotonic() - start)


_FRUEHER_VERURSACHT_MARKER: tuple[str, ...] = (
    "frueherer unterblock",
    "frueheren unterblock",
    "frueherem unterblock",
    "vorheriger unterblock",
    "vorherigen unterblock",
    "vorherigem unterblock",
    "bereits done",
    "bereits fertige",
    "vorheriger lauf",
    "vorherigen lauf",
)


def _fehler_nach_apply(
        v: object | None,
        pos: int,
) -> bool:
    """W25-2-A33/A36/A37: deterministisch pruefen,
    ob der Reviewer eine Reparatur im aktuellen
    Unterblock vorschlaegt.

    Regeln:
      - diagnose oder reparaturplan muss gefuellt sein.
      - Wenn diagnose einen Marker aus
        _FRUEHER_VERURSACHT_MARKER enthaelt
        (case-insensitive): NICHT reparierbar
        (Fehler stammt aus frueherem Unterblock).
      - Sonst: reparierbar.

    pos ist der aktuelle Unterblock-Index
    (nur fuer Audit-Kontext, nicht fuer die
    Entscheidung).
    """
    if v is None:
        return False
    diagnose = getattr(v, "diagnose", "") or ""
    plan = getattr(v, "reparaturplan", []) or []
    diagnose_str = str(diagnose) if diagnose else ""
    if not diagnose_str.strip() and not plan:
        return False
    _diag_low = diagnose_str.lower()
    for marker in _FRUEHER_VERURSACHT_MARKER:
        if marker in _diag_low:
            return False
    return True


def _sammel_commit_suite_kontext(
        state: RunState,
        tr: dict[str, Any],
) -> str:
    """W25-2-A33: Recovery-Kontext fuer (e)-Rot.

    Enthaelt:
      - failed_count, passed_count.
      - failed_test_ids (Liste, max 20 + Anzahl weiterer).
      - raw_tail (letzte 2000 Zeichen).
      - Phase-Zustand (Unterbloecke done/pending/no_go/failed).
      - Zieldateien des aktuellen Unterblocks
        (aus code_patches).
    """
    teile: list[str] = []
    teile.append(
        f"Rote Tests vor Sammel-Commit: "
        f"{tr.get('failed_count', -1)} failed, "
        f"{tr.get('passed_count', -1)} passed.")
    teile.append(
        f"Klassifizierung: "
        f"{tr.get('klassifizierung', 'unknown')}.")
    ids = tr.get("failed_test_ids", []) or []
    mehr = tr.get("failed_test_ids_mehr", 0) or 0
    if ids:
        teile.append("Fehlgeschlagene Tests:")
        for tid in ids:
            teile.append(f"  - {tid}")
        if mehr:
            teile.append(
                f"  ... und {mehr} weitere.")
    teile.append("")
    teile.append("Phase-Zustand:")
    for u in state.phase_unterbloecke:
        if not isinstance(u, dict):
            continue
        uid = u.get("id", "?")
        ust = u.get("status", "?")
        titel = u.get("titel", "")
        teile.append(f"  {uid} [{ust}] {titel}")
    teile.append("")
    teile.append(
        f"Aktueller Unterblock-Index: "
        f"{state.phase_aktueller_index}.")
    _pfade = _ziel_test_pfade(state)
    if _pfade:
        teile.append("Zieldatei-Tests des aktuellen "
                     "Unterblocks:")
        for p in _pfade:
            teile.append(f"  - {p}")
    teile.append("")
    teile.append("Protokoll (letzte 2000 Zeichen):")
    teile.append(str(tr.get("raw_tail", "")))
    return "\n".join(teile)


def _phase_apply_vor_review(
        state: RunState,
        file_whitelist: list[str],
) -> int | None:
    """W33b (2026-10-17): Apply + Post-Apply-Messung
    VOR dem Review-Loop im Phasen-Modus.

    Grund: der Judge (W28b) braucht mess_nach.txt
    und basis_gate_test_results. Beide entstehen
    heute erst in apply_and_recheck (nach dem
    Review-Loop) -> Judge sieht leere Eingaben
    und eskaliert.

    Ablauf:
      1. apply_code_patches (W24a-Idempotenz).
      2. git add -N fuer new_file-Pfade.
      3. mess_protokoll_veraltet = True (W23-A2).
      4. _post_apply_messung (W33a, patch+new_file).
      5. Guard: mess_nach nahe Judge-Budget
         (A-W33-7) -> Warnung, KEIN fail-closed.
      6. _basis_gate_pytest_ziel auf Zieldateien
         (A-W33-8, A-W33-9 (i)).
         Bei Rot: rc=17 sofort, kein Recovery.

    Rueckgabe:
      None  -- alles gruen.
      17    -- apply, Messung oder (b)-Rot.
    """
    if not state.code_patches:
        print("[!] Phasen-Apply: keine Code-Patches. "
              "Fail closed.")
        audit("code_patches_leer", {},
              state.project_dir, state.project_name)
        return 16
    print(f"\n[*] Phasen-Apply vor Review "
          f"({len(state.code_patches)} Patches).")
    # W61-Pro: AST-Grounding vor dem Apply. Erfundene
    # APIs (z.B. log(status=...)) werden gefangen, bevor
    # der Patch angewendet wird.
    _verify_befunde = verify_code(
        state.code_patches, state.project_dir, state)
    if _verify_befunde:
        print(f"[!] verify_code: {len(_verify_befunde)} "
              f"Befund(e). Patch abgelehnt.")
        for b in _verify_befunde[:10]:
            print(f"    {b}")
        audit("verify_code_befund",
              {"befunde": _verify_befunde[:10],
               "anzahl": len(_verify_befunde)},
              state.project_dir, state.project_name)
        state.letzter_test_fehler = (
            "=== VERIFY-CODE-BEFUNDE ===\n"
            + "\n".join(_verify_befunde[:10])
            + "\n=== /VERIFY-CODE-BEFUNDE ===\n")
        return 17
    ok_apply = apply_code_patches(state, state.code_patches)
    audit("code_patches_apply", {"ok": ok_apply,
                                 "anzahl": len(state.code_patches),
                                 "phase": True},
          state.project_dir, state.project_name)
    if not ok_apply:
        print("[!] Phasen-Apply fehlgeschlagen. "
              "Fail closed.")
        return 17
    # git add -N fuer new_file-Pfade (F2, 2169).
    _neue_pfade = [
        p.get("pfad", "")
        for p in state.code_patches
        if isinstance(p, dict)
        and p.get("typ") == "new_file"
        and p.get("pfad")
    ]
    if _neue_pfade:
        try:
            _res_add = subprocess.run(
                ("git", "add", "-N", *_neue_pfade),
                cwd=str(state.project_dir),
                capture_output=True, text=True,
                timeout=30, check=False,
                env=subprocess_env(),
            )
            if _res_add.returncode == 0:
                audit("git_add_intent",
                      {"pfade": _neue_pfade,
                       "phase": True},
                      state.project_dir, state.project_name)
            else:
                audit("git_add_intent_failed",
                      {"fehler": _res_add.stderr[:200],
                       "pfade": _neue_pfade},
                      state.project_dir, state.project_name)
                return 17
        except (subprocess.TimeoutExpired, OSError) as exc:
            audit("git_add_intent_failed",
                  {"fehler": str(exc),
                   "pfade": _neue_pfade},
                  state.project_dir, state.project_name)
            return 17
    # W23-A2: veraltet-Flag setzen, damit der
    # spaetere Commit-Review den NACH-Stand als
    # verbindlich nimmt.
    state.mess_protokoll_veraltet = True
    state.basis_protokoll_nach_apply = ""
    # Post-Apply-Messung (W33a: patch + new_file).
    if not _post_apply_messung(state, file_whitelist):
        return 17
    # A-W33-7: Guard gegen Token-Explosion.
    _len_nach = len(state.mess_protokoll_nach_apply)
    # Guard ist konservativ-warnend.
    # 4 Zeichen/Token ist Englisch-Faustregel.
    # Deutsch/Code liegt bei 3-3.5, Guard feuert
    # also etwas spaeter als 50%. Kein fail-closed,
    # nur Sichtbarkeit.
    _budget_bytes = state.max_tokens_judge * 4
    # Guard prueft mess_nach gegen Gesamt-Judge-
    # Budget. mess_nach ist nur ein Teil des
    # Judge-Prompts (contract.md, plan.md, Aufgabe
    # kommen dazu). 50% ist ein Konservativ-Signal,
    # keine Garantie, dass der Prompt passt.
    if _len_nach > _budget_bytes * 0.5:
        audit("mess_nach_nahe_budget",
              {"len_bytes": _len_nach,
               "budget_bytes": _budget_bytes},
              state.project_dir, state.project_name)
        print(f"[WARN] mess_nach nahe Judge-Budget: "
              f"{_len_nach}/{_budget_bytes} bytes")
    # A-W33-8 + A-W33-9 (i): (b)-Gate auf Zieldatei-
    # Tests. Bei Rot: rc=17 sofort, KEIN Recovery
    # (W25-2-Recovery ist (e)-Rot, nicht (b)-Rot).
    _w33_pfade = _ziel_test_pfade(state)
    if _w33_pfade:
        _w33_tr = _basis_gate_pytest_ziel(
            state.project_dir, _w33_pfade, 60)
        state.basis_protokoll_nach_apply += (
            "=== test_run (Phase-Apply, vor Review) ===\n"
            f"ARGV: pytest -q --maxfail=1 "
            f"{' '.join(_w33_pfade)}\n"
            f"RC: {_w33_tr['exit_code']}\n"
            f"STDOUT:\n{_w33_tr['raw_tail']}\n"
            f"STDERR:\n\n"
        )
        state.basis_gate_test_results.append({
            "scope": "ziel_pfade",
            "exit_code": _w33_tr["exit_code"],
            "klassifizierung":
                _w33_tr["klassifizierung"],
            "failed_count": _w33_tr["failed_count"],
            "passed_count": _w33_tr["passed_count"],
            "failed_test_ids":
                _w33_tr["failed_test_ids"],
            "raw_tail": _w33_tr["raw_tail"],
        })
        audit("basis_gate_test_result",
              {"scope": "ziel_pfade",
               "ist_gate": True,
               "phase_apply": True,
               "exit_code": _w33_tr["exit_code"],
               "klassifizierung":
                   _w33_tr["klassifizierung"]},
              state.project_dir, state.project_name)
        if _w33_tr["exit_code"] != 0:
            # W61: Test-Fehler fuer naechsten Builder-Lauf
            # speichern (Feedback-Loop).
            # W61: Kompakter Test-Fehler. Der raw_tail ist
            # oft zu lang und schneidet den entscheidenden
            # Hinweis ab. Stattdessen: fehlgeschlagene
            # Test-IDs + die letzten 300 Zeichen (Fehler-
            # Zeile).
            _raw = _w33_tr.get('raw_tail', '') or ''
            # W61: Die relevante Fehlerzeile extrahieren
            # (E ...), nicht die pytest-Zusammenfassung.
            _fehler_zeilen = [
                z.strip() for z in _raw.splitlines()
                if z.lstrip().startswith("E ")
                or "Error:" in z or "assert" in z.lower()
            ]
            if _fehler_zeilen:
                _letzte = "\n".join(_fehler_zeilen[-5:])
            else:
                _letzte = _raw[-300:].strip() if _raw else ''
            state.letzter_test_fehler = (
                f"=== TEST-FEHLER (b)-Gate ===\n"
                f"klassifizierung: "
                f"{_w33_tr['klassifizierung']}\n"
                f"failed_test_ids: "
                f"{_w33_tr.get('failed_test_ids', [])}\n"
                f"letzte_zeilen:\n{_letzte}\n"
                f"=== /TEST-FEHLER ===\n")
            print(f"[!] (b)-Gate rot: "
                  f"{_w33_tr['klassifizierung']}. "
                  f"Fail closed (rc=17, kein "
                  f"Recovery fuer (b)-Rot).")
            return 17
        print(f"[+] (b)-Gate gruen: "
              f"{_w33_tr['passed_count']} passed.")
    return None


def apply_and_recheck(state: RunState,
                      always: dict[str, Measurement],
                      file_whitelist: list[str]) -> int | None:
    """UMB-1d: wendet Code-Patches an und prueft das Basis-Gate erneut.

    Liefert None bei Erfolg, sonst einen Exit-Code:
      16: keine Code-Patches (Code-GO ohne Patches).
      17: apply_code_patches fehlgeschlagen.
      18: Basis-Gate nach Anwendung rot (Recovery wurde gerufen).
    """
    if not state.code_patches:
        print("[!] Code-GO, aber keine Code-Patches. Fail closed.")
        audit("code_patches_leer", {}, state.project_dir, state.project_name)
        return 16
    print(f"\n[*] Code-Patches anwenden ({len(state.code_patches)}).")
    ok_apply = apply_code_patches(state, state.code_patches)
    # Auflage 2158: Roh-Patches aus Audit entfernt.
    audit("code_patches_apply", {"ok": ok_apply,
                                  "anzahl": len(state.code_patches)},
          state.project_dir, state.project_name)
    if not ok_apply:
        print("[!] apply_code_patches fehlgeschlagen. Fail closed.")
        return 17

    # F2 (2169-Fix, 2026-10-16): git add -N fuer
    # neue Dateien. Damit erscheinen sie in
    # git diff --name-only HEAD (Phase-2-Pruefung).
    _neue_pfade = [
        p.get("pfad", "")
        for p in state.code_patches
        if isinstance(p, dict)
        and p.get("typ") == "new_file"
        and p.get("pfad")
    ]
    if _neue_pfade:
        try:
            _res_add = subprocess.run(
                ("git", "add", "-N", *_neue_pfade),
                cwd=str(state.project_dir),
                capture_output=True, text=True,
                timeout=30, check=False,
                env=subprocess_env(),
            )
            if _res_add.returncode == 0:
                audit("git_add_intent",
                      {"pfade": _neue_pfade},
                      state.project_dir, state.project_name)
            else:
                audit("git_add_intent_failed",
                      {"fehler": _res_add.stderr[:200],
                       "pfade": _neue_pfade},
                      state.project_dir, state.project_name)
                return 17
        except (subprocess.TimeoutExpired, OSError) as exc:
            audit("git_add_intent_failed",
                  {"fehler": str(exc),
                   "pfade": _neue_pfade},
                  state.project_dir, state.project_name)
            return 17

    print("[*] Basis-Gate nach Anwendung (ohne git_status).")
    # Bug-Fix 2026-10-14: Apply ist passiert.
    # mess_protokoll ist ab jetzt der Stand VOR Apply.
    state.mess_protokoll_veraltet = True
    state.basis_protokoll_nach_apply = ""
    # Post-Apply-Neumessung 2026-10-16: read_file
    # fuer new_file-Pfade, jetzt existieren sie.
    # Fail-closed bei unerwartetem read_file-Fehler.
    if not _post_apply_messung(state, file_whitelist):
        return 17
    nach_fehler: list[str] = []
    for mid, m in always.items():
        if mid in ("git_status", "git_head"):
            continue
        out, ok_m = run_measurement(m, file_whitelist, state.project_dir)
        state.basis_protokoll_nach_apply += out
        if not ok_m:
            nach_fehler.append(mid)
            print(f"[!] Basis-Gate-nach-apply rot: {mid}")
        else:
            print(f"[+] Basis-Gate-nach-apply gruen: {mid}")
    if nach_fehler:
        print(f"[!] Basis-Gate-nach-apply rot: {nach_fehler}")
        # Truncation-Fix-A2 (2026-10-16): Marker + Mess separat.
        _proto_gek = _truncate_mit_marker(
            state.basis_protokoll_nach_apply, 3000)
        _mess_nach = state.mess_protokoll_nach_apply or ""
        _mess_nach_gek = _truncate_mit_marker(
            _mess_nach, 8000) if _mess_nach else "(keine)"
        v = ask_reviewer_for_recovery(
            state, "basis_gate",
            f"Nach Anwendung der Code-Patches: {nach_fehler}\n\n"
            f"Protokoll:\n{_proto_gek}\n\n"
            f"GEMESSENER INHALT (nach Apply):\n{_mess_nach_gek}")
        print_recovery(v)
        audit("recovery_basis_gate_nach_apply",
              {"fehler": nach_fehler, "empfehlung": v.empfehlung},
              state.project_dir, state.project_name)
        # P-Bugfix 2026-10-16: rc=19 ist internes Signal
        # an run_pipeline, eine Builder-Korrektur-Runde
        # zu starten. run_pipeline faengt rc=19 ab.
        # Der Phasen-Loop sieht rc=19 NIE (run_pipeline
        # wandelt ihn in rc=0 oder rc=18).
        state.letzter_recovery_vorschlag = v
        return 19

    # W25-1: Zieldatei-Tests (b) pruefen.
    _w25_pfade = _ziel_test_pfade(state)
    if _w25_pfade:
        _w25_tr = _basis_gate_pytest_ziel(
            state.project_dir, _w25_pfade, 60)
        # WEG-X-P22a: Ergebnis in basis_protokoll_nach_apply
        # einbauen, damit der Recovery-Prompt die Test-Ausgabe
        # sieht (nicht nur den "rot: ruff"-Hinweis).
        state.basis_protokoll_nach_apply += (
            "=== test_run (nach Apply) ===\n"
            f"ARGV: pytest -q --maxfail=1 "
            f"{' '.join(_w25_pfade)}\n"
            f"RC: {_w25_tr['exit_code']}\n"
            f"STDOUT:\n{_w25_tr['raw_tail']}\n"
            f"STDERR:\n\n"
        )
        state.basis_gate_test_results.append({
            "scope": "ziel_pfade",
            "exit_code": _w25_tr["exit_code"],
            "klassifizierung":
                _w25_tr["klassifizierung"],
            "failed_count": _w25_tr["failed_count"],
            "passed_count": _w25_tr["passed_count"],
            "failed_test_ids":
                _w25_tr["failed_test_ids"],
            "raw_tail": _w25_tr["raw_tail"],
        })
        audit("basis_gate_test_result",
              {"scope": "ziel_pfade",
               "ist_gate": True,
               "exit_code": _w25_tr["exit_code"],
               "klassifizierung":
                   _w25_tr["klassifizierung"],
               "failed_count":
                   _w25_tr["failed_count"],
               "passed_count":
                   _w25_tr["passed_count"],
               "failed_test_ids":
                   _w25_tr["failed_test_ids"],
               "failed_test_ids_mehr":
                   _w25_tr["failed_test_ids_mehr"],
               "dauer_s": _w25_tr["dauer_s"],
               "raw_tail":
                   _w25_tr["raw_tail"]},
              state.project_dir, state.project_name)
        if _w25_tr["klassifizierung"] == "timeout":
            print("[!] W25 Zieldatei-Test-Timeout. "
                  "Fail-closed.")
            return 19
        if _w25_tr["exit_code"] != 0:
            print(f"[!] W25 Zieldatei-Test rot: "
                  f"{_w25_tr['failed_count']} failed, "
                  f"{_w25_tr['passed_count']} passed.")
            # Gleicher Recovery-Pfad wie always-Rot.
            _proto_gek = _truncate_mit_marker(
                state.basis_protokoll_nach_apply, 3000)
            v = ask_reviewer_for_recovery(
                state, "basis_gate",
                f"Zieldatei-Tests rot: "
                f"{_w25_tr['failed_test_ids']}\n\n"
                f"Protokoll:\n{_proto_gek}")
            print_recovery(v)
            audit("recovery_basis_gate_nach_apply",
                  {"fehler": ["test_ziel"],
                   "empfehlung": v.empfehlung},
                  state.project_dir, state.project_name)
            state.letzter_recovery_vorschlag = v
            return 19
    return None


def _post_apply_korrektur_loop(
        state: RunState,
        always: dict[str, Any],
        file_whitelist: list[str],
        builder_prompt: str,
        project_dir: Path,
        project_name: str,
        api_key: str,
        max_llm: int,
        max_minutes: int,
        max_korrektur_runden: int = 2,
) -> int:
    """Post-Apply-Fix 2026-10-16: Builder-Korrektur-
    Loop nach Post-Apply-Basis-Gate-Fehler.

    Rueckgabe:
      0   -- Basis-Gate nach Apply gruen.
      18  -- max_korrektur_runden erschoepft.
    """
    for runde in range(1, max_korrektur_runden + 1):
        print(f"[i] Post-Apply-Korrektur-Runde {runde}/"
              f"{max_korrektur_runden}.")
        audit("builder_recovery_nach_apply",
              {"runde": runde,
               "recovery_grund": "basis_gate_nach_apply",
               "diagnose_kurz":
                   (getattr(state.letzter_recovery_vorschlag,
                            "diagnose", "")[:200]
                    if state.letzter_recovery_vorschlag
                    else "")},
              project_dir, project_name)
        rc_loop = budget_or_recover(
            state, max_llm,
            f"Vor Builder-Korrektur-Runde {runde}.",
            project_dir, project_name,
            max_minutes=max_minutes)
        if rc_loop is not None:
            return rc_loop
        reply_roh, rc_b = builder_reply_mit_command_loop(
            state, api_key, builder_prompt,
            _bauer_recovery_prompt,
            project_dir, project_name,
            max_builder_runden=3,
            max_llm=max_llm, max_minutes=max_minutes,
        )
        if rc_b is not None:
            print(f"[!] Builder-Korrektur-Runde {runde} "
                  f"fehlgeschlagen: rc={rc_b}.")
            continue
        if reply_roh is None or not reply_roh.ok:
            print(f"[!] Builder-Korrektur-Runde {runde} "
                  f"keine Antwort.")
            continue
        # A1b-fix: Recovery-Kontext.
        record_code_entwurf(state, reply_roh.content,
                            phase="recovery")
        state.code_patches = parse_code_patches(reply_roh.content)
        print(f"[i] {len(state.code_patches)} Code-Patches "
              f"nach Korrektur-Runde {runde} geparst.")
        rc_apply = apply_and_recheck(
            state, always, file_whitelist)
        if rc_apply is None:
            print(f"[+] Post-Apply-Korrektur-Runde {runde} "
                  f"gruen.")
            return 0
        if rc_apply == 19:
            # Naechste Runde.
            continue
        # Andere rc: Fail-closed.
        return rc_apply
    # W30-fix (2026-10-18): einheitlicher Cap-Audit.
    _loop_cap_audit(state, "post_apply_korrektur",
                    max_korrektur_runden + 1,
                    max_korrektur_runden)
    print(f"[!] Post-Apply-Korrektur max_runden "
          f"({max_korrektur_runden}) erreicht. Fail closed.")
    return 18


def extract_paths_from_aufgabe(aufgabe: str,
                                file_whitelist: list[str],
                                project_dir: Path) -> list[str]:
    """Auflage 2146 + W1 (2026-10-16): extrahiert
    Datei-Pfade aus dem Auftrag.

    Drei Quellen (W1-A1):
      1. Suffix-Pfade: <pfad>.<endung>.
      2. from-Importe: from a.b.c import X
         -> a/b/c.py (nur, wenn a/b/c in
         file_whitelist UND a/b/ existiert).
      3. (kein 'import X' — im U5-Auftrag
         nicht verwendet; W1-A1).

    W1-A3: exists()-Filter fuer die Datei
    entfaellt (neue Dateien existieren noch
    nicht). Stattdessen: Elternverzeichnis
    muss existieren. Damit werden Pfade in
    neuen Dateien erkannt, stdlib-Pfade
    (os.path -> os/ existiert nicht) aber
    verworfen.

    Endungen (W1-A1): .py .md .yaml .yml
    .sql .json .toml .cfg .ini .txt.
    Dedupliziert.
    """
    if not aufgabe:
        return []
    _endungen = (
        "py|md|yaml|yml|sql|json|toml|cfg|ini|txt")
    _suffix_re = re.compile(
        r"[a-zA-Z0-9_./-]+\.(?:" + _endungen + r")")
    _from_re = re.compile(
        r"from\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s+import")

    kandidaten: list[str] = []
    # 1. Suffix-Pfade.
    for m in _suffix_re.finditer(aufgabe):
        kandidaten.append(m.group(0))
    # 2. from-Importe.
    for m in _from_re.finditer(aufgabe):
        modul = m.group(1)
        pfad = modul.replace(".", "/") + ".py"
        kandidaten.append(pfad)

    ergebnis: list[str] = []
    gesehen: set[str] = set()
    for p in kandidaten:
        p = p.lstrip("/")
        if p in gesehen:
            continue
        if not any(p.startswith(w) for w in file_whitelist):
            continue
        # W1-A3: Elternverzeichnis-Check.
        eltern = (project_dir / p).parent
        if not eltern.exists():
            continue
        gesehen.add(p)
        ergebnis.append(p)
    return ergebnis


# W10 (2026-10-16): Section-Name fuer den
# Aenderung-Block in der Commit-Message.
# Synchron mit dem W8b-Prompt-Format
# ("Aenderung:\n  - <pfad>").
_MESSAGE_SECTION_CHANGE = "Aenderung:"

# W10: Pfad-Endungen fuer den Section-Parser.
_MSG_PFAD_ENDUNGEN = (
    "py|sql|md|yaml|yml|json|toml|html|"
    "css|js|cfg|ini|txt"
)


def _normalisiere_pfad(p: str) -> str:
    """W10-A4: Pfad-Normalisierung fuer den Vergleich.

    - fuehrendes "./" entfernen
    - fuehrendes "/" entfernen
    - trailing "/" entfernen
    - Backslash -> Slash
    """
    p = p.replace("\\", "/").strip()
    p = p.removeprefix("./")
    p = p.removeprefix("/")
    p = p.removesuffix("/")
    return p


def _extrahiere_aenderung_pfade(message: str) -> (
        tuple[set[str], str]
):
    """W10-A2/A3: extrahiert Zieldatei-Pfade aus dem
    Aenderung-Block der Commit-Message.

    Rueckgabe: (pfade, fehler).
      fehler == "" -> OK, pfade gefuellt.
      fehler == "b" -> Section fehlt.
      fehler == "a" -> Section leer (keine Bullets).
      fehler == "c" -> Pfad-Parse-Fehler.

    Regex akzeptiert "Aenderung:" am Zeilenanfang
    (auch mit fuehrenden Whitespaces). Bullets mit
    "-" oder "*".
    """
    import re as _re
    # W10-A2: Section-Header suchen.
    header_re = _re.compile(
        r"^[ \t]*" + _re.escape(_MESSAGE_SECTION_CHANGE)
        + r"[ \t]*$",
        _re.MULTILINE)
    m = header_re.search(message)
    if m is None:
        return (set(), "b")
    # Bullets nach dem Header sammeln, bis naechste
    # Section (Zeile ohne fuehrendes "-"/"*" UND
    # nicht-leer UND nicht Fortsetzung).
    rest = message[m.end():]
    bullet_re = _re.compile(
        r"^[ \t]*[-*][ \t]+(.+)$", _re.MULTILINE)
    # W10c (2026-10-16): nur Pfade mit Verzeichnis-
    # Praefix (mindestens ein '/') zaehlen.
    # Dateinamen ohne Pfad (z.B. 'app.py') sind
    # Referenzen, keine Zieldateien.
    pfad_re = _re.compile(
        r"[a-zA-Z0-9_.-]+/[a-zA-Z0-9_./-]+\."
        + f"(?:{_MSG_PFAD_ENDUNGEN})")
    pfade: set[str] = set()
    gefunden = 0
    for zeile in rest.splitlines():
        s = zeile.strip()
        if not s:
            continue
        bm = bullet_re.match(zeile)
        if bm is None:
            # Naechste Section (nicht-Bullet-Zeile).
            # Stoppen.
            if gefunden > 0:
                break
            # Sonst: wir sind noch im Header-Bereich,
            # ignorieren.
            continue
        gefunden += 1
        text = bm.group(1)
        for pm in pfad_re.finditer(text):
            pfade.add(_normalisiere_pfad(pm.group(0)))
    if gefunden == 0:
        # W10b (2026-10-16): Fallback. Wenn der
        # Builder Fliesstext statt Bullets liefert:
        # alle Pfade bis zum naechsten Abschnitt
        # (naechste Zeile, die mit Grossbuchstabe
        # beginnt und mit ':' endet).
        abschnitt_re = _re.compile(
            r"^[A-Za-z][A-Za-z0-9 _-]*:",
            _re.MULTILINE)
        # Nach dem Header bis zum naechsten
        # Abschnitt.
        _rest = rest
        _m_abs = abschnitt_re.search(_rest)
        if _m_abs is not None:
            _rest = _rest[:_m_abs.start()]
        for _pm in pfad_re.finditer(_rest):
            pfade.add(_normalisiere_pfad(_pm.group(0)))
        if not pfade:
            return (set(), "a")
        return (pfade, "")
    if not pfade:
        return (set(), "c")
    return (pfade, "")


def _check_commit_scope(
    state: RunState,
    diff_name_only: str,
    project_dir: Path,
    project_name: str,
) -> tuple[bool, str]:
    """A1-final-4 (2026-10-16): Prueft, ob
    BETROFFENE DATEIEN eine Teilmenge von
    GIT DIFF --NAME-ONLY HEAD sind.

    Fail-closed VOR dem Reviewer-Aufruf.
    R16-Aequivalent als deterministischer
    Check.

    Rueckgabe: (ok, grund).
      ok=True -> grund="".
      ok=False -> grund="scope_violation".
    """
    dateien = set(
        state.commit_paket.get("dateien", []) or [])
    diff_pfade = {
        z.strip() for z in diff_name_only.splitlines()
        if z.strip() and z.strip() != "(keine)"}
    # W11b (2026-10-16): untracked Dateien
    # zusaetzlich aus git status -uall lesen.
    # git diff --name-only HEAD sieht sie nicht.
    try:
        _status_res = subprocess.run(
            ("git", "status", "--porcelain", "-uall"),
            cwd=str(project_dir), capture_output=True,
            text=True, timeout=30, check=False,
            env=subprocess_env())
        for _zeile in _status_res.stdout.splitlines():
            if len(_zeile) < 4:
                continue
            _pfad = _zeile[3:].strip()
            if _pfad:
                diff_pfade.add(_pfad)
    except (subprocess.TimeoutExpired, OSError):
        pass
    fremd = dateien - diff_pfade
    if not fremd:
        return (True, "")
    audit("commit_scope_violation",
          {"dateien": sorted(dateien),
           "git_diff": sorted(diff_pfade),
           "fremd": sorted(fremd)},
          project_dir, project_name)
    print("[FAIL] Commit-Scope verletzt: "
          "BETROFFENE DATEIEN nicht Teilmenge "
          "von GIT DIFF.")
    print(f"  BETROFFENE DATEIEN: {sorted(dateien)}")
    print(f"  GIT DIFF: {sorted(diff_pfade)}")
    print(f"  fremd: {sorted(fremd)}")
    return (False, "scope_violation")


def _audit_builder_prompt(prompt: str, state: RunState,
                          project_dir: Path, project_name: str) -> None:
    """Auflage 2194: protokolliert die Struktur des Builder-Prompts.

    Nur fuer Diagnose. Speichert Laenge, Sektionsnamen und die
    Laenge des GEMESSENER INHALT-Blocks (redigiert).
    """
    sektionen: list[str] = []
    for m in re.finditer(r"^([A-ZÄÖÜ][A-ZÄÖÜa-zäöü_ ()/,-]{2,60}):",
                          prompt, re.MULTILINE):
        s = m.group(1).strip()
        if s not in sektionen:
            sektionen.append(s)
    # GEMESSENER INHALT-Block-Laenge
    gem_len = 0
    marker = "GEMESSENER INHALT (verbindlich"
    if marker in prompt:
        i = prompt.find(marker)
        # bis zur naechsten Sektion oder Ende
        rest = prompt[i:]
        # Naechste Sektion suchen: Zeile, die mit Grossbuchstabe
        # beginnt und mit ":" endet
        m2 = re.search(
            r"\n(?!ARGV:|RC:|STDOUT:|STDERR:)"
            r"[A-ZÄÖÜ][A-ZÄÖÜäöü_ ()/,-]{2,60}:",
            rest[len(marker):])
        if m2:
            gem_len = len(rest[:len(marker) + m2.start()])
        else:
            gem_len = len(rest)
    anzahl_read_file = prompt.count("=== read_file ===")
    redigiert, _ = redaction.redact_all(prompt, max_len=200000)
    # P2b-Luecke-B / S9: Feld solver_befund_eingesetzt.
    solver_drin = "SOLVER-BEFUND" in prompt
    audit("builder_prompt_gebaut",
          {"prompt_len": len(redigiert),
           "sektionen": sektionen,
           "gemessener_inhalt_len": gem_len,
           "anzahl_read_file": anzahl_read_file,
           "solver_befund_eingesetzt": solver_drin},
          project_dir, project_name)


def _audit_builder_reply(reply_content: str, state: RunState,
                         project_dir: Path, project_name: str) -> None:
    """Auflage 2194-M: protokolliert den Builder-Reply (Kopf/Fuss).

    Felder gekuerzt (2194-M): kopf 300 statt 1500 Zeichen,
    fuss 200 statt 500 Zeichen. Reduziert Audit-Wachstum.
    """
    redigiert, _ = redaction.redact_all(reply_content, max_len=200000)
    kopf = redigiert[:300]
    fuss = redigiert[-200:] if len(redigiert) > 300 else ""
    audit("builder_reply_erhalten",
          {"reply_len": len(redigiert),
           "reply_kopf": kopf,
           "reply_fuss": fuss},
          project_dir, project_name)


def _anker_zeilenbereich(
    aufgabe: str,
    project_dir: Path,
) -> tuple[int, int] | None:
    """W6b-2 (2026-10-16): findet den Anker im Auftrag
    und liefert einen Zeilenbereich (start, ende).

    Format im Auftrag (aus dem Planner):
      ANKER (...): '<anker-text>' ERSATZ: '...'

    Liefert None, wenn kein Anker erkannt wird oder
    die Anker-Zeile nicht in der Datei gefunden wird.

    Praezisierung W6-A5: Fail-closed bei Anker nicht
    gefunden erfolgt im Aufrufer.
    """
    import re as _re
    # 1. Anker-Text extrahieren.
    # W6b-2 + WEG-X-P19c: ANKER-Format (alt) UND anker:-Feld (P17).
    # Alt: "ANKER (...): '<text>'"
    # P17: "anker:'<text>'"
    m = _re.search(
        r"(?:ANKER[^:]*|anker)\s*:\s*'([^']+)'",
        aufgabe, _re.IGNORECASE | _re.DOTALL)
    if m is None:
        return None
    anker_text = m.group(1).strip()
    if not anker_text:
        return None
    # W13a (2026-10-16): YAML-Quoting kann
    # \\n als Literal enthalten. In echte
    # Zeilenumbrueche wandeln.
    if "\\n" in anker_text and "\n" not in anker_text:
        anker_text = anker_text.replace("\\n", "\n")
    # 2. Datei-Pfad aus dem Auftrag finden.
    # Wir suchen "patch: <pfad>" im Auftrag.
    m2 = _re.search(
        r"patch:\s*([a-zA-Z0-9_./-]+\.(?:py|md|yaml|yml|sql))",
        aufgabe)
    if m2 is None:
        return None
    pfad = m2.group(1).strip()
    ziel = project_dir / pfad
    if not ziel.exists():
        return None
    # 3. Erste Anker-Zeile in der Datei finden.
    erste_zeile = anker_text.splitlines()[0].strip()
    if not erste_zeile:
        return None
    try:
        inhalt = ziel.read_text(encoding="utf-8")
    except OSError:
        return None
    treffer = None
    for i, zeile in enumerate(inhalt.splitlines(), 1):
        if zeile.strip() == erste_zeile:
            treffer = i
            break
    if treffer is None:
        return None
    # 4. Zeilenbereich: +-5 um die Anker-Zeile.
    _start = max(1, treffer - 5)
    _ende = treffer + 10
    return (_start, _ende)


def ensure_ziel_gemessen(
    state: RunState,
    ziel_pfade: list[str],
    project_dir: Path,
    file_whitelist: list[str],
    project_name: str,
    aufgabe: str = "",
) -> None:
    """Auflage 2192: Werkstatt messt automatisch fehlende Zieldateien.

    Fuer jeden Pfad in ziel_pfade: pruefen, ob er im
    mess_protokoll vollstaendig vorliegt. Wenn nicht:
    read_file mit quelle="pipeline_auto".
    """
    if not ziel_pfade:
        return
    # W6b-2b (2026-10-16): Anker-Zeilenbereich
    # berechnen. Nur fuer Patch-Pfade.
    _anker_info = _anker_zeilenbereich(aufgabe, project_dir)
    _anker_pfad = ""
    if _anker_info is not None:
        import re as _re
        _m = _re.search(
            r"patch:\s*([a-zA-Z0-9_./-]+\.(?:py|md|yaml|yml|sql))",
            aufgabe)
        if _m is not None:
            _anker_pfad = _m.group(1).strip()
    bereits = _gemessene_pfade(state)
    fehlend: list[dict[str, str]] = []
    for p in ziel_pfade:
        ziel = (project_dir / p).resolve()
        if str(ziel) in bereits:
            continue
        # W6b-2b: Bei Anker-Pfad Zeilenbereich nutzen.
        _arg = p
        if (_anker_info is not None
                and p == _anker_pfad):
            _arg = (f"{p}:{_anker_info[0]}-{_anker_info[1]}")
        fehlend.append({"id": "read_file", "arg": _arg})
    if not fehlend:
        return
    print(f"[i] Auto-Messung: {len(fehlend)} Zieldatei(en).")
    execute_commands(state, fehlend, quelle="pipeline_auto")


def _gemessene_pfade(state: RunState) -> set[str]:
    """W52b-C: Pfade aus state.messungen (Datei-Referenzen).

    Liest NICHT mehr den mess_protokoll-String. Quelle ist
    ausschliesslich state.messungen (W52b A/B)."""
    pfade: set[str] = set()
    if state is None:
        return pfade
    for m in getattr(state, "messungen", []) or []:
        if getattr(m, "pfad", None):
            pfade.add(m.pfad)
    return pfade


def read_target_snippets(paths: list[str],
                        project_dir: Path,
                        file_whitelist: list[str],
                        max_len: int = 3000,
                        bereits_gemessen: set[str] | None = None
                        ) -> str:
    """Auflage 2146: Ausschnitte aus den Zieldateien.

    Fail closed bei Pfad ausserhalb file_whitelist.
    Redaction auf die Ausschnitte.
    """
    if not paths:
        return "(keine Zieldateien im Auftrag erkannt)"
    teile = ["ZIELDATEIEN (Ausschnitte aus den zu patchenden Dateien):"]
    for p in paths:
        if not any(p.startswith(w) for w in file_whitelist):
            print(f"[WARN] read_target_snippets: "
                  f"Pfad ausserhalb Whitelist: {p}")
            continue
        ziel = project_dir / p
        if not ziel.exists():
            print(f"[WARN] read_target_snippets: "
                  f"Datei fehlt: {p}")
            continue
        try:
            inhalt = ziel.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"[WARN] read_target_snippets: "
                  f"Lesefehler {p}: {exc}")
            continue
        total = len(inhalt)
        gekuerzt = total > max_len
        vollpfad = str(ziel.resolve())
        if bereits_gemessen and vollpfad in bereits_gemessen:
            teile.append(
                f"--- {p} (vollstaendig im GEMESSENEN "
                f"INHALT unten) ---")
            teile.append(
                "[... Siehe Sektion GEMESSENER INHALT. "
                "Kein Auszug hier. ...]")
            continue
        ausschnitt = inhalt[:max_len]
        ausschnitt, _ = redaction.redact_all(
            ausschnitt, max_len=100000)
        if gekuerzt:
            kopf = (
                f"--- {p} (Zeichen 1-{max_len} von {total}, "
                f"GEKUERZT) ---"
            )
        else:
            kopf = (
                f"--- {p} (Zeichen 1-{total} von {total}, "
                f"vollstaendig) ---"
            )
        teile.append(kopf)
        teile.append(ausschnitt)
        if gekuerzt:
            rest = total - max_len
            teile.append(
                f"\n[... AUSSCHNITT GEKUERZT. {rest} weitere "
                f"Zeichen. Fuer die vollstaendige Datei: "
                f"COMMAND: RUN read_file {p}]"
            )
    return "\n".join(teile)


def build_commit_paket(state: RunState) -> dict[str, Any]:
    """Bittet den Builder um einen Commit-Paket-Vorschlag.

    Der Builder sieht: letzten Commit, Code-Entwurf, Reviewer-Verdict,
    sowie die betroffenen Dateien.
    """
    letzter = subprocess.run(
        ("git", "log", "-1", "--format=%B"),
        cwd=str(state.project_dir), capture_output=True, text=True,
        timeout=30, check=False, env=subprocess_env(),
    ).stdout
    # UMB-1c: git diff als Basis (die Aenderungen sind angewendet).
    git_diff = subprocess.run(
        ("git", "diff", "--stat"),
        cwd=str(state.project_dir), capture_output=True, text=True,
        timeout=30, check=False, env=subprocess_env(),
    ).stdout
    git_diff_voll = subprocess.run(
        ("git", "diff"),
        cwd=str(state.project_dir), capture_output=True, text=True,
        timeout=30, check=False, env=subprocess_env(),
    ).stdout
    git_status = subprocess.run(
        ("git", "status", "--porcelain"),
        cwd=str(state.project_dir), capture_output=True, text=True,
        timeout=30, check=False, env=subprocess_env(),
    ).stdout

    # D1 (2026-10-16): ZIELDATEIEN explizit vorgeben.
    # D3 ist Durchsetzung; D1 ist Beratung.
    _ziel_pfade = [
        p.get("pfad", "")
        for p in state.code_patches
        if isinstance(p, dict) and p.get("pfad")
    ]
    if _ziel_pfade:
        _ziel_block = (
            "ZIELDATEIEN DIESES AUFTRAGS "
            "(verbindlich, uebernimm sie woertlich "
            "in BETROFFENE DATEIEN):\n"
            + "\n".join(
                f"  - {pfad}" for pfad in _ziel_pfade)
            + "\nAndere untracked Dateien aus "
            "frueheren Auftraegen gehoeren NICHT "
            "in die Liste.\n\n"
        )
    else:
        _ziel_block = (
            "ZIELDATEIEN DIESES AUFTRAGS: "
            "(keine Patches - Auftrag bereits "
            "erfuellt).\n\n"
        )
    # W8-1 (2026-10-16): GIT STATUS auf die
    # Zieldateien filtern. Verhindert, dass der
    # Builder die volle untracked-Liste in die
    # Commit-Message kopiert.
    if _ziel_pfade:
        _gs_zeilen: list[str] = []
        for _gs in git_status.splitlines():
            if len(_gs) <= 3:
                continue
            _gs_pfad = _gs[3:].strip()
            if not _gs_pfad:
                continue
            if any(
                    _zp == _gs_pfad
                    or _gs_pfad.startswith(_zp)
                    or _zp.startswith(_gs_pfad)
                    for _zp in _ziel_pfade):
                _gs_zeilen.append(_gs)
        git_status = ("\n".join(_gs_zeilen) + "\n"
                      if _gs_zeilen
                      else "(keine Zieldateien)\n")
    aufgabe = (
        "Der Code-Review ist abgeschlossen. Der Reviewer hat "
        "in der letzten Runde GO gegeben. Die Code-Patches "
        "sind bereits angewendet.\n\n"
        "Baue das Commit-Paket:\n"
        "1. Commit-Message im Format des letzten Commits.\n"
        "2. Liste der betroffenen Dateien.\n\n"
        # W8b-1 (2026-10-16): strenges Verbot
        # fremder Pfade in der Message.
        "WICHTIG: Die Commit-Message nennt NUR "
        "die in ZIELDATEIEN DIESES AUFTRAGS "
        "aufgefuehrten Pfade.\n"
        "VERBOTEN in der Message:\n"
        "  - Ausblick auf spaetere Unterbloecke "
        "('folgt in U9', 'geplant: X').\n"
        "  - Zusaetzliche Pfade, die nicht in "
        "ZIELDATEIEN stehen.\n"
        "  - Erlaeuterungen zu Dateien, die nicht "
        "geaendert werden.\n"
        "Die BETROFFENE DATEIEN-Sektion und die "
        "Commit-Message nennen dieselbe Liste.\n\n"
        "Positiv-Format der Commit-Message:\n"
        "  Aenderung:\n"
        "    - <pfad aus ZIELDATEIEN>\n"
        "    - <pfad aus ZIELDATEIEN>\n"
        "Ein Pfad pro Zeile, alle aus ZIELDATEIEN.\n\n"
        + _ziel_block
        + "Achte auf die Auflagen des Reviewers (unten).\n\n"
        f"LETZTER COMMIT (Format-Referenz):\n{letzter}\n\n"
        f"GIT STATUS (nicht alles gehoert zu diesem Auftrag):\n"
        f"{git_status}\n\n"
        f"GIT DIFF --STAT:\n{git_diff}\n\n"
        f"GIT DIFF (gekuerzt):\n{git_diff_voll[:4000]}\n\n"
        f"REVIEWER-VERDICT:\n"
        f"{state.review_runden[-1]['raw'] if state.review_runden else '(keins)'}\n\n"
        + format_messwerte_block(collect_messwerte(state)) + "\n\n"
        "Antworte in genau diesem Format:\n\n"
        + COMMIT_PAKET_FORMAT
    )

    # Auflage 2124: einmaliger Retry bei reply.ok=False.
    # Kein Retry bei reply.ok=True und leerem Paket
    # (das ist ein Prompt-Problem, kein Transport-Problem).
    antworten: list = []
    for versuch in (1, 2):
        reply = ask_llm(
            state.api_key,
            build_system_prompt(
                state.agents.get("builder_commit",
                                 state.agents["builder"]), state.docs,
                                state.agent_docs.get("builder", [])),
            aufgabe,
            state.builder_model,
            state.builder_temp,
            state.llm_timeout_s,
            state=state,
            max_tokens=state.max_tokens_builder,
        )
        antworten.append(reply)
        if reply.ok:
            break
        if versuch == 1:
            # Nur einmal wiederholen.
            print(f"[i] build_commit_paket: Versuch 1 "
                  f"fehlgeschlagen ({reply.error}). "
                  f"Einmaliger Retry.")
            audit("builder_commit_paket_failed",
                  {"error": reply.error, "versuch": 1},
                  state.project_dir, state.project_name)
            # Auflage 2184: Default 30 (Konsistenz mit YAML).
            max_llm = state.budget.get("max_llm_calls", 30)
            rc = budget_or_recover(
                state, max_llm, "Vor Commit-Paket-Retry.",
                state.project_dir, state.project_name)
            if rc is not None:
                # Recovery wurde bereits aufgerufen.
                return {"message": "", "dateien": [],
                        "doku_patches": [],
                        "error": f"budget_or_recover rc={rc}"}
            continue
        # Versuch 2: endgueltig fehlgeschlagen.
        print(f"[!] build_commit_paket: Versuch 2 "
              f"fehlgeschlagen ({reply.error}). Kein weiterer Retry.")
        audit("builder_commit_paket_failed_retry",
              {"error": reply.error, "versuch": 2},
              state.project_dir, state.project_name)
        return {"message": "", "dateien": [], "doku_patches": [],
                "error": reply.error}

    if not reply.ok:
        # Fallback (nicht erreichbar nach dem Loop).
        return {"message": "", "dateien": [], "doku_patches": [],
                "error": reply.error}

    paket = parse_commit_paket(reply.content)
    paket["roh"] = reply.content
    # W8-3 (2026-10-16): Reply-Kopf/Fuss ins Audit,
    # damit die Commit-Message nachvollziehbar ist.
    _w8_redig, _ = redaction.redact_all(
        reply.content, max_len=200000)
    audit("commit_paket_gebaut",
          {"reply_len": len(_w8_redig),
           "reply_kopf": _w8_redig[:500],
           "reply_fuss": (_w8_redig[-500:]
                          if len(_w8_redig) > 500 else ""),
           "message_len": len(paket.get("message", "")),
           "anzahl_dateien": len(paket.get("dateien", []))},
          state.project_dir, state.project_name)
    # Auflage 2123: Audit, wenn das Paket leer geparst wurde.
    # Auflage 2134: Roh-Text entfernt (Debug-Ziel erreicht).
    if not paket.get("message") and not paket.get("dateien") \
            and not paket.get("doku_patches"):
        audit("commit_paket_leer",
              {"roh_len": len(reply.content)},
              state.project_dir, state.project_name)
    return paket


def apply_commit_and_doku(state: RunState, paket: dict[str, Any]) -> bool:
    """Wendet Doku-Patches an und committet.

    NUR nach Human-Gate. Explizite Datei-Liste, kein git add -A.

    Auflage 2082: Validieren vor Schreiben. In-Memory-Rollback
    fuer Doku-Dateien, falls git add oder git commit fehlschlaegt.
    """
    # ---- Phase 1: Validieren (nichts schreiben) ----
    dateien = paket.get("dateien", [])
    if not dateien:
        print("[!] Keine betroffenen Dateien angegeben. Abbruch.")
        return False
    for pfad in dateien:
        if not any(pfad.startswith(w) for w in state.file_whitelist):
            print(f"[!] Datei nicht in Whitelist: {pfad}")
            return False
        # Auflage 2048: Datei muss existieren.
        if not (state.project_dir / pfad).exists():
            print(f"[!] Datei existiert nicht: {pfad}")
            return False

    doku_patches = paket.get("doku_patches", [])
    doku_ziele: dict[Path, str] = {}
    for patch in doku_patches:
        ziel = state.project_dir / patch["pfad"]
        if not ziel.exists():
            print(f"[!] Doku-Datei fehlt: {patch['pfad']}")
            return False
        if ziel in doku_ziele:
            print(f"[!] Doku-Datei mehrfach im Paket: {patch['pfad']}")
            return False
        text = ziel.read_text(encoding="utf-8")
        count = text.count(patch["anker"])
        if count != 1:
            print(f"[!] Anker in {patch['pfad']} kommt {count}x vor. "
                  f"Erwartet: 1x. Abbruch.")
            return False
        doku_ziele[ziel] = text

    # ---- Phase 2: Doku-Patches schreiben + Original merken ----
    original: dict[Path, str] = {}
    for patch in doku_patches:
        ziel = state.project_dir / patch["pfad"]
        original[ziel] = doku_ziele[ziel]
        # W24a (2026-10-17): Idempotenz-Check.
        _aktuell_d = doku_ziele[ziel]
        _pat_anker = patch["anker"]
        _pat_ersatz = patch["ersatz"]
        _hat_ersatz_d = _pat_ersatz in _aktuell_d
        _hat_anker_d = _pat_anker in _aktuell_d
        if _hat_ersatz_d and not _hat_anker_d:
            # Patch bereits angewendet.
            audit("patch_bereits_angewendet",
                  {"pfad": str(ziel),
                   "anker_len": len(_pat_anker)},
                  state.project_dir, state.project_name)
            print(f"[i] Doku-Patch bereits angewendet: "
                  f"{ziel}.")
            continue
        # W35a-2d-6: Ambig nur, wenn WEDER Ersatz in
        # Anker NOCH Anker in Ersatz (Praefix-Faelle).
        if (_hat_ersatz_d and _hat_anker_d
                and _pat_anker not in _pat_ersatz
                and _pat_ersatz not in _pat_anker):
            print(f"[FAIL] Doku-Patch ambig: anker und "
                  f"ersatz beide in {ziel}.")
            audit("patch_ambig",
                  {"pfad": str(ziel),
                   "anker_len": len(_pat_anker),
                   "ersatz_len": len(_pat_ersatz)},
                  state.project_dir, state.project_name)
            return False
        if not _hat_anker_d:
            print(f"[FAIL] Doku-Anker fehlt in {ziel}.")
            audit("patch_anker_fehlt",
                  {"pfad": str(ziel),
                   "anker_len": len(_pat_anker)},
                  state.project_dir, state.project_name)
            return False
        neu = doku_ziele[ziel].replace(
            _pat_anker, _pat_ersatz, 1)
        ziel.write_text(neu, encoding="utf-8")
        print(f"[+] Doku gepatcht: {patch['pfad']}")

    def _rollback_doku() -> None:
        """Schreibt Doku-Dateien auf Original-Inhalt zurueck."""
        for ziel, inhalt in original.items():
            try:
                ziel.write_text(inhalt, encoding="utf-8")
            except OSError as exc:
                print(f"[!] Rollback fehlgeschlagen fuer {ziel}: {exc}")

    # ---- Phase 3: git add ----
    argv_add = ("git", "add", "--") + tuple(dateien)
    res_add = subprocess.run(
        argv_add, cwd=str(state.project_dir),
        capture_output=True, text=True, timeout=60, check=False,
        env=subprocess_env(),
    )
    if res_add.returncode != 0:
        print(f"[!] git add fehlgeschlagen: {res_add.stderr}")
        _rollback_doku()
        return False

    # ---- Phase 4: git commit ----
    # Auflage 2170: msg_datei in .git/ statt in der
    # Projekt-Wurzel. Die Wurzel gehoert root:security-ai 755,
    # builder darf dort nicht schreiben. .git gehoert
    # builder (durch chown) und ist die konventionelle
    # Stelle fuer Commit-Messages.
    msg_datei = state.project_dir / ".git" / ".commit-msg.tmp"
    msg_datei.write_text(paket["message"], encoding="utf-8")
    commit_argv: list[str] = ["git"]
    if state.git_author_name:
        commit_argv += ["-c", f"user.name={state.git_author_name}"]
    if state.git_author_email:
        commit_argv += ["-c", f"user.email={state.git_author_email}"]
    # W61: --allow-empty, wenn alle Zieldateien bereits
    # committed sind (z.B. manuell committed in einer
    # vorherigen Sitzung). Sonst scheitert git commit mit
    # "nichts zu committen".
    commit_argv += ["commit", "--allow-empty", "-F", str(msg_datei)]

    try:
        res_commit = subprocess.run(
            tuple(commit_argv),
            cwd=str(state.project_dir), capture_output=True, text=True,
            timeout=60, check=False, env=subprocess_env(),
        )
    finally:
        msg_datei.unlink(missing_ok=True)

    if res_commit.returncode != 0:
        print(f"[!] git commit fehlgeschlagen: {res_commit.stderr}")
        # git add rueckgaengig, dann Doku zurueck.
        subprocess.run(
            ("git", "reset", "HEAD", "--") + tuple(dateien),
            cwd=str(state.project_dir),
            capture_output=True, text=True, timeout=60, check=False,
            env=subprocess_env(),
        )
        _rollback_doku()
        return False

    # ---- Phase 5: Bestaetigung ----
    log = subprocess.run(
        ("git", "log", "-1", "--oneline"),
        cwd=str(state.project_dir), capture_output=True, text=True,
        timeout=30, check=False, env=subprocess_env(),
    ).stdout
    print(f"[+] Commit erstellt: {log.strip()}")
    return True



def print_approval_dokument(state: RunState) -> None:
    """Zeigt das Approval-Dokument mit vollstaendiger Reviewer-Argumentation."""
    print("\n" + "=" * 70)
    print("APPROVAL-DOKUMENT")
    print("=" * 70)
    print(f"Block:     {state.block_id}")
    print(f"Aufgabe:   {state.aufgabe}")
    print(f"Start:     {state.start_ts}")
    print(f"Runden:    {len(state.review_runden)}")
    print(f"LLM-Calls: {state.llm_calls}")
    if state.start_monotonic > 0:
        verstr = time.monotonic() - state.start_monotonic
        print(f"Verstrichen: {verstr:.0f}s")

    print("\n--- BASIS-GATE (immer, vor Reviewer) ---")
    print(state.basis_protokoll)

    if state.mess_protokoll:
        print("\n--- OPTIONALE MESSUNGEN ---")
        print(state.mess_protokoll)

    print("\n--- REVIEWER-ARGUMENTATION ---")
    for r in state.review_runden:
        print(f"\n[ROUND {r['runde']} - VERDICT: {r['verdict']}]")
        print(r["raw"])

    if state.commit_review:
        print("\n--- COMMIT-REVIEW ---")
        print(f"Verdikt: {state.commit_review.get('verdict', '?')}")
        print(state.commit_review.get("raw", ""))

    print("\n--- AUFLAGEN ---")
    for i, auflagen in enumerate(state.auflagen_log, 1):
        if auflagen:
            print(f"Runde {i}: " + "; ".join(auflagen))

    print("\n--- EMPFEHLUNGEN ---")
    for i, emp in enumerate(state.empfehlung_log, 1):
        print(f"Runde {i}: Tests={emp['tests']}, Art={emp['art']}, Prio={emp['prioritaet']}")

    print("\n--- CODE-ENTWURF ---")
    print(state.code_entwurf)

    if state.test_vorschlaege:
        print("\n--- TEST-VORSCHLAEGE ---")
        print(state.test_vorschlaege)

    if state.commit_paket:
        print("\n--- COMMIT-PAKET ---")
        print(f"Commit-Message:\n{state.commit_paket.get('message', '')}")
        print(f"Betroffene Dateien: {state.commit_paket.get('dateien', [])}")
        print(f"Doku-Patches: {len(state.commit_paket.get('doku_patches', []))}")


def _commit_review_w25_suite_nachlauf(
        state: RunState, project_dir: Path,
        project_name: str, uid: str,
) -> int | None:
    """Zweiter W25-Suite-Lauf nach Recovery.

    Rueckgabe:
      None = gruen (weiter zu C7).
      int  = rc 18 bei Suite2 rot.

    Layer: W0a-3 (3a-1c-2a, extrahiert aus C7).
    """
    # Erneut (e) pruefen.
    _w25_suite2 = _basis_gate_pytest_suite(
        project_dir, 900)
    audit("basis_gate_test_result",
          {"scope": "volle_suite",
           "ist_gate": True,
           "nachtlauf": True,
           "exit_code": _w25_suite2["exit_code"],
           "klassifizierung": _w25_suite2["klassifizierung"],
           "failed_count": _w25_suite2["failed_count"],
           "passed_count": _w25_suite2["passed_count"],
           "failed_test_ids": _w25_suite2["failed_test_ids"],
           "failed_test_ids_mehr":
               _w25_suite2["failed_test_ids_mehr"],
           "dauer_s": _w25_suite2["dauer_s"],
           "raw_tail": _w25_suite2["raw_tail"]},
          project_dir, project_name)
    if _w25_suite2["exit_code"] != 0:
        print("[!] (e)-Rot nach Korrektur "
              "weiterhin rot. Fail-closed.")
        return 18
    # A35: Status zurueck auf done.
    if uid:
        try:
            _phase_yaml_status_update(
                project_name, uid, "done")
        except ValueError:
            pass
    print("[+] (e)-Rot nach Recovery "
          "gruen. Sammel-Commit weiter.")
    return None

def _commit_review_w25_suite(
        state: RunState, project_dir: Path,
        project_name: str,
) -> dict | int:
    """Erster W25-Suite-Lauf vor Sammel-Commit.

    Rueckgabe:
      dict = Suite-Ergebnis (exit_code, klassifizierung,
             failed_count, passed_count, failed_test_ids,
             failed_test_ids_mehr, dauer_s, raw_tail).
      int  = rc 18 bei timeout.

    Layer: W0a-1 (3a-1c-2a, extrahiert aus C7).
    """
    _w25_suite = _basis_gate_pytest_suite(
        project_dir, 900)
    audit("basis_gate_test_result",
          {"scope": "volle_suite",
           "ist_gate": True,
           "exit_code": _w25_suite["exit_code"],
           "klassifizierung": _w25_suite["klassifizierung"],
           "failed_count": _w25_suite["failed_count"],
           "passed_count": _w25_suite["passed_count"],
           "failed_test_ids": _w25_suite["failed_test_ids"],
           "failed_test_ids_mehr":
               _w25_suite["failed_test_ids_mehr"],
           "dauer_s": _w25_suite["dauer_s"],
           "raw_tail": _w25_suite["raw_tail"]},
          project_dir, project_name)
    if _w25_suite["klassifizierung"] == "timeout":
        print("[!] W25 Suite-Test-Timeout. Fail-closed.")
        return 18
    return _w25_suite

def _commit_review_w25_recovery(
        state: RunState, w25_suite: dict, pos: int,
        always, file_whitelist,
        builder_prompt: str, project_dir: Path,
        project_name: str, api_key: str,
        max_llm: int, max_minutes: int,
) -> int | None:
    """W25-Recovery bei rotem Suite-Test.

    Rueckgabe:
      None = reparierbar (weiter zu W0a-3).
      int  = rc 18 (nicht-reparierbar oder Korrektur rot).

    Layer: W0a-2 (3a-1c-2a, extrahiert aus C7).
    """
    print(f"[FAIL] W25 Suite-Test rot vor "
          f"Sammel-Commit: "
          f"{w25_suite['failed_count']} "
          f"failed, "
          f"{w25_suite['passed_count']} "
          f"passed.")
    print(f"  Tests: {w25_suite['failed_test_ids']}")
    _ctx = _sammel_commit_suite_kontext(state, w25_suite)
    _v2 = ask_reviewer_for_recovery(
        state, "basis_gate_suite", _ctx)
    print_recovery(_v2)
    audit("phase_suite_rot_recovery",
          {"diagnose":
               (getattr(_v2, "diagnose", "") or "")[:2000],
           "failed_test_ids":
               w25_suite["failed_test_ids"],
           "klassifizierung":
               w25_suite["klassifizierung"]},
          project_dir, project_name)
    _reparierbar = _fehler_nach_apply(_v2, pos)
    if not _reparierbar:
        _uid = ""
        if 0 <= pos < len(state.phase_unterbloecke):
            _uid = state.phase_unterbloecke[pos].get("id", "")
        if _uid:
            try:
                _phase_yaml_status_update(
                    project_name, _uid, "no_go")
            except ValueError:
                pass
        print("[!] (e)-Rot nicht im aktuellen Unterblock "
              "reparierbar. Phase no_go.")
        return 18
    # Reparierbar -> no_go + 1 Korrektur-Runde.
    _uid = ""
    if 0 <= pos < len(state.phase_unterbloecke):
        _uid = state.phase_unterbloecke[pos].get("id", "")
    if _uid:
        try:
            _phase_yaml_status_update(
                project_name, _uid, "no_go")
        except ValueError:
            pass
    _rc_k = _post_apply_korrektur_loop(
        state, always, file_whitelist,
        builder_prompt=builder_prompt,
        project_dir=project_dir,
        project_name=project_name,
        api_key=api_key,
        max_llm=max_llm,
        max_minutes=max_minutes,
        # W30 (A-W30-2): 1 Runde im Recovery-Pfad
        # ((e)-Rot nach Phasen-Suite). Bewusst kuerzer
        # als der normale Pfad (2, Z. 9461).
        max_korrektur_runden=1)
    if _rc_k != 0:
        print("[!] Korrektur-Runde fuer (e)-Rot fehlgeschlagen.")
        return 18
    return None


def _vorlauf_und_state(
    project_name: str,
    aufgabe: str,
    state_ref: list[RunState],
    phasen_state: RunState | None = None,
) -> VorlaufErgebnis | int:
    """C0+C1: Vorlauf + State-Aufbau.

    Extrahiert aus run_pipeline, Z. 8041-8147 (Stand da67198).
    Return: int bei api_key-leer (1) oder memory-korrupt (3).
            VorlaufErgebnis bei Erfolg.
    Raise: ValueError bei phasen_state + nicht-leerem state_ref.
    """
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        print("[FAIL] DEEPSEEK_API_KEY fehlt. Fail closed.")
        return 1

    config = _lade_und_pruefe_projekt(project_name)
    project_dir = Path(config.get("project_dir", str(Path.cwd()))).expanduser()
    # Agent-Memory A2: Projekt-Stand aus memory.yaml.
    # UU6: fehlt = ok, korrupt = Fail-closed.
    projekt_stand: dict = {}
    _mem_pfad = Path("/opt/werkstatt/projects") / f"{project_name}.memory.yaml"
    if _mem_pfad.exists():
        try:
            _mem = yaml.safe_load(
                _mem_pfad.read_text(encoding="utf-8"))
            if isinstance(_mem, dict):
                projekt_stand = _mem.get("projekt_stand", {}) or {}
        except yaml.YAMLError as exc:
            print(f"[FAIL] memory.yaml korrupt: {exc}")
            audit("memory_yaml_korrupt",
                  {"pfad": str(_mem_pfad), "fehler": str(exc)},
                  project_dir, project_name)
            return 3
    agents_dir = config.get("project_agents_dir")
    if not agents_dir:
        agents_dir = "/opt/werkstatt/agents"
    agents = load_agents(agents_dir)
    docs = load_docs(config.get("docs", {}), project_dir)
    always, optional = build_catalog(config, project_dir)
    file_whitelist = config.get("file_whitelist", [])
    # Auflage 2184: Default 30, damit Projekte ohne YAML
    # nicht still auf 20 fallen.
    budget = config.get(
        "budget",
        # W30 (A-W30-1): Default 2 (Chef-Anweisung,
        # konsistent mit Code-Fallback Z. 9012).
        {"max_review_rounds": 2, "max_llm_calls": 30})

    solver_config: dict[str, float] = {}
    _solver_yaml = config.get("solver", {}) or {}
    if isinstance(_solver_yaml, dict):
        if "p1_schwellwert" in _solver_yaml:
            solver_config["p1_schwellwert"] = float(
                _solver_yaml["p1_schwellwert"])
        if "p1_min_tokens" in _solver_yaml:
            solver_config["p1_min_tokens"] = float(
                _solver_yaml["p1_min_tokens"])
        if "max_runden" in _solver_yaml:
            solver_config["max_runden"] = float(
                _solver_yaml["max_runden"])
    max_llm = budget.get("max_llm_calls", 30)
    max_minutes = budget.get("max_minutes", 0)  # Auflage 2080: 0 = aus

    git_author = config.get("git_author", {}) or {}
    # P2b-3 / G6: phasen_state-Guard.
    if phasen_state is not None:
        if state_ref:
            raise ValueError(
                "phasen_state uebergeben, aber "
                "state_ref nicht leer")
        state = phasen_state
        # P-Bugfix 2026-10-16: im Phasen-Modus ist
        # der Unterblock-Auftrag der aktuelle Auftrag.
        # Der Phasen-Gesamtauftrag bleibt in phase.yaml.
        state.aufgabe = aufgabe
    else:
        state = RunState(
            block_id=config.get("project", "unknown"),
            aufgabe=aufgabe,
            start_ts=datetime.now(UTC).isoformat(timespec="seconds"),
            docs=docs, agents=agents, always=always, optional=optional,
            file_whitelist=file_whitelist, api_key=api_key, budget=budget,
            agent_docs=config.get("agent_docs", {}),
            project_dir=project_dir,
            projekt_stand=projekt_stand,
            git_author_name=str(git_author.get("name", "")),
            git_author_email=str(git_author.get("email", "")),
            project_name=project_name,
        )
    # Auflage 2080: Startzeitpunkt fuer das Zeitbudget.
    state.start_monotonic = time.monotonic()

    # Auflage 2183-P4-Log2: state an main zurueckgeben.
    state_ref.append(state)

    # Auflage 2200a: Run-Identifier setzen.
    _neue_run_id = (
        datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        + f"-{os.getpid()}")
    # Auflage 2183 A2: run_id auch in state.
    set_run_id(_neue_run_id)
    state.run_id = _neue_run_id

    # P-Bugfix 2026-10-16: Phasen-Kontext im Audit.
    _start_daten: dict = {
        "aufgabe_hash": __import__("hashlib").sha256(
            aufgabe.encode()).hexdigest(),
        "aufgabe_kurz": aufgabe[:200],
        "llm_calls_start": 0,
    }
    if phasen_state is not None:
        _start_daten["phase_id"] = state.phase_id
        _start_daten["phase_titel"] = state.phase_titel
        _start_daten["unterblock_index"] = \
            state.phase_aktueller_index
    audit("pipeline_start", _start_daten,
          project_dir, project_name)
    return VorlaufErgebnis(
        state=state, config=config, budget=budget,
        max_llm=max_llm, max_minutes=max_minutes,
        project_dir=project_dir, file_whitelist=file_whitelist,
        api_key=api_key, always=always, optional=optional)


def _basis_gate(
    state: RunState,
    always: dict,
    config: dict,
    file_whitelist: list,
    project_dir: Path,
    project_name: str,
) -> int | None:
    """C2: Basis-Gate (Schritt 0). Fail-Fast bei rotem Gate.

    Extrahiert aus run_pipeline, Z. 8070-8131 (Stand d512264).
    Return: 11 bei rot, None bei gruen.
    """
    # ==================================================================
    # SCHRITT 0: BASIS-GATE (HARD FAIL)
    # ==================================================================
    print("[*] Schritt 0: Basis-Gate (immer).")
    print(f"[i] Messungen: {list(always.keys())}")
    basis_fehler: list[str] = []
    for mid, m in always.items():
        out, ok = run_measurement(m, file_whitelist, project_dir)
        state.basis_protokoll += out
        if not ok:
            basis_fehler.append(mid)
            print(f"[!] Basis-Gate rot: {mid}")
        else:
            print(f"[+] Basis-Gate gruen: {mid}")

    if basis_fehler:
        print("\n" + "=" * 70)
        print(f"[!] Basis-Gate rot. Fehler: {basis_fehler}")
        print("[*] Auto-Repair (nur deterministisch).")
        print("=" * 70)
        audit("basis_gate_rot", {"fehler": basis_fehler}, project_dir, project_name)

        # Nur deterministischer Fix: ruff --fix
        nur_ruff = basis_fehler == ["ruff"]
        if nur_ruff:
            tests_snap = snapshot_tests_dir(project_dir)
            ok, _ = auto_repair_ruff(
                project_dir,
                config.get("venv_python", str(project_dir / ".venv/bin/python3")),
            )
            audit("auto_repair_ruff", {"ok": ok}, project_dir, project_name)
            tests_ok, probleme = check_tests_dir_unveraendert(project_dir, tests_snap)
            if not tests_ok:
                print(f"[!] Auto-Repair hat tests/ veraendert: {probleme}")
                ok = False
            if ok:
                # Nachmessen
                state.basis_protokoll = ""
                neue_fehler: list[str] = []
                for mid, m in always.items():
                    out, ok_m = run_measurement(m, file_whitelist, project_dir)
                    state.basis_protokoll += out
                    if not ok_m:
                        neue_fehler.append(mid)
                if not neue_fehler:
                    print("[+] Basis-Gate gruen nach Auto-Repair.")
                    basis_fehler = []
                else:
                    basis_fehler = neue_fehler

        if basis_fehler:
            kontext = (
                f"Basis-Gate-Fehler: {basis_fehler}\n\n"
                f"Basis-Protokoll:\n{state.basis_protokoll[:3000]}"
            )
            v = ask_reviewer_for_recovery(state, "basis_gate", kontext)
            print_recovery(v)
            audit("recovery_basis_gate",
                  {"diagnose": v.diagnose, "plan": v.reparaturplan,
                   "empfehlung": v.empfehlung},
                  project_dir, project_name)
            return 11
    return None


def _commit_review_w25_loop(
    state: RunState,
    api_key: str,
    project_dir: Path,
    project_name: str,
    max_llm: int,
    max_minutes: int,
    reviewer_prompt: str,
    builder_prompt: str,
    _hat_anker_patches,
    _diff_name_only,
) -> int | None:
    """W2: Commit-NO-GO-Loop (max 2 Versuche).

    Extrahiert aus run_pipeline, Z. 8585-8755 (Stand 1091b3e).
    Signatur-Freeze 18c: 9 Parameter, siehe OFFENE-BLOECKE.md 3a-1c-2b.
    """
    if not _hat_anker_patches and not state.mess_protokoll:
        _anzahl_new_file = sum(
            1 for p in (state.code_patches or [])
            if isinstance(p, dict)
            and p.get("typ") == "new_file")
        if _anzahl_new_file > 0:
            print("[i] Commit-Review: reine new_file-"
                  "Patches. Keine Anker-Pruefung noetig "
                  "(R7 skip).")
        else:
            print("[i] Commit-Review: keine Patches. Skip.")
        _runde_audit = (
            state.review_runden[-1].get("runde", 0)
            if state.review_runden else 0)
        audit("commit_review_new_file_skip",
              {"runde": _runde_audit,
               "anzahl_new_file": _anzahl_new_file,
               "phase_id": getattr(state, "phase_id", "")},
              project_dir, project_name)

    # Auflage 2118: Commit-NO-GO-Loop, max 2 Versuche.
    max_commit_versuche = 2
    commit_versuche = 0
    while True:
        # Auflage 2120: leere Auflagen explizit 'keine'.
        auflagen_letzte = (state.auflagen_log[-1]
                           if state.auflagen_log
                              and state.auflagen_log[-1]
                           else [])
        auflagen_text = ("; ".join(auflagen_letzte)
                         if auflagen_letzte else "keine")

        # W11b (2026-10-16): Unterblock-Kontext
        # fuer den Commit-Review (nur Phasen-Modus).
        _w11_unterblock_kontext = ""
        if state.phase_aktiv:
            _w11_idx = state.phase_aktueller_index
            _w11_ups = state.phase_unterbloecke
            if 0 <= _w11_idx < len(_w11_ups):
                _w11_u = _w11_ups[_w11_idx]
                _w11_uid = (
                    _w11_u.get("id", "?")
                    if isinstance(_w11_u, dict) else "?")
                _w11_titel = (
                    _w11_u.get("titel", "")
                    if isinstance(_w11_u, dict) else "")
                _w11_total = len(_w11_ups)
                _w11_done = sum(
                    1 for _u in _w11_ups
                    if isinstance(_u, dict)
                    and _u.get("status") == "done")
                _w11_unterblock_kontext = (
                    f"UNTERBLOCK: {_w11_uid} "
                    f"({_w11_idx + 1} von {_w11_total}) "
                    f"— {_w11_titel}\n"
                    f"({_w11_done} von {_w11_total} "
                    f"bereits done)\n"
                )

        # W23 (2026-10-17): Commit-Review-Prompt ausgelagert
        # in _build_commit_input (testbar, wartbar).
        commit_input = _build_commit_input(
            state, _diff_name_only,
            _w11_unterblock_kontext, auflagen_text)
        rc = budget_or_recover(state, max_llm,
                              "Vor Commit-Review.",
                              project_dir, project_name,
                              max_minutes=max_minutes)
        if rc is not None:
            return rc
        if len(commit_input) > 50000:
            print(f"[WARN] commit_input {len(commit_input)} "
                  f"Zeichen (> 50000). Kontext-Risiko.")
        reply = ask_llm(api_key, reviewer_prompt, commit_input,
                        state.reviewer_verdict_model, 0.0,
                        state.llm_timeout_s,
                        state=state,
                        max_tokens=state.max_tokens_reviewer)
        if not reply.ok:
            print(f"[FAIL] Reviewer Commit-Review: {reply.error}")
            return _fail_closed(
                state, project_dir, project_name, 6,
                "commit_review_call_failed")

        commit_verdict = classify_verdict(reply.content)
        state.commit_review = {"verdict": commit_verdict,
                               "raw": reply.content}
        # Auflage 2140: Roh-Text aus Audit entfernt.
        audit("commit_review",
              {"verdict": commit_verdict,
               "runde": commit_versuche},
              project_dir, project_name)

        # Auflage 2183 C (Y2): COMMAND in Phase 2
        # wird nicht ausgefuehrt (2199-R7-P2).
        # Wenn der Reviewer RUN solver versucht:
        # Audit, sonst blinder Fleck.
        if commit_verdict == "COMMAND":
            cmds_p2 = parse_commands(reply.content)
            for c in cmds_p2:
                if c.get("id") == "solver":
                    audit(
                        "reviewer_run_solver_phase2_ignoriert",
                        {"runde": commit_versuche,
                         "arg": c.get("arg", "")[:200]},
                        project_dir, project_name)
        if commit_verdict == "COMMIT-GO":
            print("[+] Commit-GO erhalten.")
            return None

        if commit_verdict != "COMMIT-NO-GO":
            # ESKALATION / UNKLAR: Stop, Mensch entscheidet am Gate.
            print(f"[i] Commit-Review-Verdict: {commit_verdict}. "
                  "Kein Loop.")
            return None

        # COMMIT-NO-GO
        print(f"[-] Commit-NO-GO (Versuch {commit_versuche + 1}/"
              f"{max_commit_versuche}):\n{reply.content[:400]}")
        commit_versuche += 1
        if commit_versuche >= max_commit_versuche:
            print("[!] Commit-Review: maximale Versuche erreicht.")
            return _fail_closed(
                state, project_dir, project_name, 7,
                "commit_no_go_max_versuche")

        rc = budget_or_recover(state, max_llm,
                              "Vor Builder-Neubau (Commit-NO-GO).",
                              project_dir, project_name,
                              max_minutes=max_minutes)
        if rc is not None:
            return rc
        bauer_reply = ask_llm(
            api_key, builder_prompt,
            f"Der Reviewer hat das vorherige Commit-Paket "
            f"mit COMMIT-NO-GO abgelehnt.\n"
            f"Begruendung (Kontext, NICHT die "
            f"Reviewed-Zeile):\n{reply.content}\n\n"
            + format_messwerte_block(collect_messwerte(state)) + "\n\n"
            + format_doc_snippets(state.docs) + "\n\n"
            "Liefere ein ueberarbeitetes Commit-Paket.\n\n"
            "WICHTIG: Der Reviewed-Block der neuen Message "
            "spiegelt den Code-Review-Verdict DIESER Runde "
            "(CODE-GO), nicht den vorherigen COMMIT-NO-GO. "
            "Der vorherige NO-GO ist Kontext, keine "
            "Verdict-Quelle.\n\n"
            + COMMIT_PAKET_FORMAT,
            state.builder_model, state.builder_temp,
            state.llm_timeout_s,
            state=state,
            max_tokens=state.max_tokens_builder,
        )
        if not bauer_reply.ok:
            print(f"[FAIL] Builder Commit-Paket-Neubau: "
                  f"{bauer_reply.error}")
            # Auflage 2128: Audit fuer den Fehlerpfad.
            audit("builder_commit_paket_failed_retry",
                  {"error": bauer_reply.error,
                   "versuch": commit_versuche},
                  project_dir, project_name)
            return 8
        state.commit_paket = parse_commit_paket(bauer_reply.content)
        # Auflage 2128: Audit, wenn der Neubau leer ist.
        if not state.commit_paket.get("message") \
                and not state.commit_paket.get("dateien") \
                and not state.commit_paket.get("doku_patches"):
            # Auflage 2134: Roh-Text entfernt.
            audit("commit_paket_leer",
                  {"runde": commit_versuche,
                   "roh_len": len(bauer_reply.content)},
                  project_dir, project_name)
def _approval_und_human_gate(
        state: RunState,
        project_dir: Path,
        project_name: str,
        config: dict,
) -> int:
    """C8+C9 (3a-1c-4, Variante A): Approval-Dokument + Human-Gate.

    Extrahiert aus run_pipeline Z. 8819-8898 (HEAD 75f844b).

    Returns:
        0   approved / rejected / eskaliert / abgebrochen
        20  Commit fehlgeschlagen (apply_commit_and_doku False)
        21  Phasen-Modus: commit_paket ohne Dateien (fail-closed)
    """
    # SCHRITT 6: Approval-Dokument + Human-Gate
    # P2b-3 / G2 + G3 + G4: Phasen-Modus.
    # Kein Pro-Unterblock-Approval. Paket sammeln.
    # Leeres Paket -> Fail-closed, rc=21.
    if state.phase_aktiv:
        if not state.commit_paket.get("dateien"):
            print("[FAIL] Phasen-Modus: Commit-Paket ohne "
                  "Dateien. Fail closed.")
            audit("phase_commit_paket_leer",
                  {"phase_id": state.phase_id,
                   "unterblock_index":
                       state.phase_aktueller_index},
                  project_dir, project_name)
            return 21
        uid = ""
        if 0 <= state.phase_aktueller_index < len(
                state.phase_unterbloecke):
            uid = state.phase_unterbloecke[
                state.phase_aktueller_index].get("id", "")
        state.phase_commit_pakete.append(state.commit_paket)
        audit("phase_commit_paket_gesammelt",
              {"phase_id": state.phase_id,
               "unterblock_id": uid,
               "unterblock_index":
                   state.phase_aktueller_index,
               "dateien": state.commit_paket.get("dateien", []),
               "message_kurz":
                   state.commit_paket.get("message", "")[:200],
               "paket_nummer":
                   len(state.phase_commit_pakete) - 1},
              project_dir, project_name)
        print("[+] Phasen-Modus: Commit-Paket gesammelt "
              "(kein Commit).")
        return 0
    print_approval_dokument(state)

    print("\n" + "=" * 70)
    print("ENTSCHEIDUNG: [j] approve / [n] reject / [e] eskalation")
    print("=" * 70)
    try:
        wahl = input("Deine Wahl: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n[*] Abbruch.")
        audit("pipeline_abgebrochen", {}, project_dir, project_name)
        return 0

    if wahl in {"j", "ja", "y", "yes"}:
        print("[+] Approved.")
        audit("pipeline_approved", {"runden": len(state.review_runden)},
              project_dir, project_name)

        if not config.get("require_human_approval", True):
            print("[!] require_human_approval=False. Ueberspringe Commit.")
            return 0

        if apply_commit_and_doku(state, state.commit_paket):
            audit("commit_applied", {}, project_dir, project_name)
            return 0
        else:
            print("[!] Commit fehlgeschlagen. Manuell nachholen.")
            return 20

    if wahl in {"n", "no", "nein"}:
        print("[-] Rejected.")
        grund = ""
        try:
            grund = input("Begruendung (leer = keine): ").strip()
        except (EOFError, KeyboardInterrupt):
            pass
        audit("pipeline_rejected",
              {"runden": len(state.review_runden), "grund_kurz": grund[:200]},
              project_dir, project_name)
        return 0

    print("[!] Eskalation.")
    audit("pipeline_escalated", {"runden": len(state.review_runden)},
          project_dir, project_name)
    return 0


def run_pipeline(project_name: str, aufgabe: str,
                 state_ref: list[RunState],
                 *,
                 phasen_state: RunState | None = None) -> int:
    """Ein Pipeline-Lauf (ein Block oder ein Phasen-Unterblock).

    phasen_state (P2b-3): optionaler RunState aus einem
    Phasen-Loop. Wenn None: alter Pfad 1:1 (neuer RunState
    wird gebaut). Wenn gesetzt: der Aufrufer uebergibt den
    State (state_ref MUSS leer sein, sonst ValueError),
    und der Approval-Block wird durch den Phasen-Modus
    ersetzt (Paket sammeln statt committen).
    """
    _v = _vorlauf_und_state(
        project_name, aufgabe, state_ref, phasen_state)
    if isinstance(_v, int):
        return _v
    state = _v.state
    config = _v.config
    budget = _v.budget
    max_llm = _v.max_llm
    max_minutes = _v.max_minutes
    project_dir = _v.project_dir
    file_whitelist = _v.file_whitelist
    api_key = _v.api_key
    always = _v.always
    optional = _v.optional

    _rc_c2 = _basis_gate(
        state, always, config, file_whitelist,
        project_dir, project_name,
    )
    if _rc_c2 is not None:
        return _rc_c2

    print("[+] Basis-Gate gruen. Block startet.")

    # ==================================================================
    # SCHRITT 1: Reviewer waehlt optionale Messungen
    # ==================================================================
    print("\n[*] Schritt 1: Reviewer waehlt optionale Messungen.")

    doc_keys_reviewer = state.agent_docs.get("reviewer", [])
    reviewer_prompt = build_system_prompt(
        state.agents["reviewer"], state.docs,
        doc_keys_reviewer, state=state)
    # W28b (2026-10-17): Judge-Prompt (Code-Review).
    judge_prompt = _build_judge_prompt(state)

    historie = load_recent_commits(project_dir, n=10)

    overview = (
        "Basis-Gate (immer gelaufen, gruen):\n"
        + state.basis_protokoll[:1500]
        + "\n\nVerfuegbare optionale Messungen:\n"
        + "\n".join(f"  - {m.mid}: {m.beschreibung}" for m in optional.values())
    )
    reviewer_input = (
        aufgabe_block(state)
        + _format_whitelist_block(
            list(getattr(state, "file_whitelist", []) or []))
        + f"LETZTE COMMITS:\n{historie[:3000]}\n\n"
        f"{overview}\n\n"
        "Waehle optionale Messungen. Antworte mit COMMAND-Zeilen:\n"
        "COMMAND: RUN <id>\n"
        "COMMAND: RUN read_file <pfad>"
    )
    rc = budget_or_recover(state, max_llm,
                          "Vor Reviewer-Auswahl optionale Messungen.",
                          project_dir, project_name,
                          max_minutes=max_minutes)
    if rc is not None:
        return rc
    reply = ask_llm(api_key, reviewer_prompt, reviewer_input,
                    state.reviewer_verdict_model, 0.0, state.llm_timeout_s,
                    state=state,
                    max_tokens=state.max_tokens_reviewer)
    if not reply.ok:
        print(f"[FAIL] Reviewer: {reply.error}")
        audit("reviewer_call_failed", {"error": reply.error}, project_dir, project_name)
        return 2

    commands = parse_commands(reply.content)
    # W25: load_skill vor execute_commands.
    _run_cmds_r, _n_skills_r = _verarbeite_skill_commands(
        state, commands)
    if _n_skills_r:
        print(f"[i] Reviewer-COMMAND: "
              f"{_n_skills_r} Skill(s) geladen.")
    if _run_cmds_r:
        print(f"[i] Reviewer fordert {len(_run_cmds_r)} optionale Messungen.")
        execute_commands(state, _run_cmds_r, quelle="reviewer")
    else:
        print("[i] Reviewer fordert keine optionalen Messungen.")

    # ==================================================================
    # SCHRITT 2: Builder baut Code-Entwurf
    # ==================================================================
    print("\n[*] Schritt 2: Builder baut Code-Patches (UMB-1b).")
    builder_prompt = build_system_prompt(
        state.agents.get("builder_patch",
                         state.agents["builder"]), state.docs,
                                         state.agent_docs.get("builder", []))
    rc = budget_or_recover(state, max_llm,
                          "Vor Builder-Aufruf (Code-Patches).",
                          project_dir, project_name,
                          max_minutes=max_minutes)
    if rc is not None:
        return rc
    ziel_pfade = extract_paths_from_aufgabe(
        aufgabe, file_whitelist, project_dir)
    ensure_ziel_gemessen(
        state, ziel_pfade, project_dir, file_whitelist,
        project_name, aufgabe=aufgabe)
    def _builder_user_prompt(s: RunState) -> str:
        """Auflage 2191b: baut den Builder-Prompt pro Runde
        frisch, damit GEMESSENER INHALT und ZIELDATEIEN den
        aktuellen state.mess_protokoll sehen.
        """
        zp = extract_paths_from_aufgabe(
            aufgabe, file_whitelist, project_dir)
        zs = read_target_snippets(
            zp, project_dir, file_whitelist,
            bereits_gemessen=_gemessene_pfade(s))
        anker_block = baue_anker_rueckmeldung(s)
        _ps_block = format_projekt_stand(s)
        # W61: Explore-Ergebnisse der letzten Runde.
        _explore_block = ""
        if getattr(s, "letzte_explore_ergebnisse", None):
            _zeilen = ["ERGEBNISSE DER SUCHE (verbindlich):"]
            for _e in s.letzte_explore_ergebnisse:
                _zeilen.append(f"  Frage: {_e.get('frage', '')}")
                _zeilen.append(
                    f"  Ergebnis: {_e.get('ergebnis', '')}")
            _explore_block = "\n".join(_zeilen) + "\n\n"
        # W61: Test-Fehler aus dem letzten (b)-Rot.
        print(f"[DEBUG-PROMPT] phase_aktiv={s.phase_aktiv} "
              f"test_fehler_len={len(s.letzter_test_fehler or '')} "
              f"uid={s.phase_unterbloecke[s.phase_aktueller_index].get('id') if s.phase_unterbloecke else '?'}")
        _test_fehler_block = ""
        if getattr(s, "letzter_test_fehler", ""):
            _test_fehler_block = s.letzter_test_fehler + "\n\n"
            print(f"[DEBUG-TF] len={len(_test_fehler_block)}")
        # W61: Contract fuer den aktuellen Unterblock.
        # Der Builder MUSS wissen, was der Unterblock
        # verlangt (Anker, Test, Pruefung). Sonst raet er.
        _contract_block = ""
        if s.phase_aktiv and s.phase_unterbloecke:
            _uid = s.phase_unterbloecke[
                s.phase_aktueller_index].get("id", "?")
            _contract = _lese_contract(s, _uid)
            if _contract:
                _contract_block = (
                    f"=== CONTRACT ({_uid}) ===\n"
                    f"{_contract}\n"
                    f"=== /CONTRACT ===\n\n")
        return (
            _test_fehler_block
            + _contract_block
            + aufgabe_block(s)
            + _format_whitelist_block(
                list(getattr(s, "file_whitelist", []) or []))
            # W25: Skills-Bloecke.
            + _available_skills_block()
            + _geladene_skills_block(s)
            + (_ps_block if _ps_block else "")
            + _explore_block
            + (anker_block if anker_block else "")
            +
            f"BASIS-GATE:\n{s.basis_protokoll[:1500]}\n\n"
            + format_doc_snippets(s.docs) + "\n\n"
            + zs + "\n\n"
            + f"GEMESSENER INHALT (Index):\n"
            f"{_messwerte_fuer_prompt(s)}\n\n"
            + (_mess_inhalt_zieldateien(s, zp) + "\n\n"
               if _mess_inhalt_zieldateien(s, zp) else "")
            + "Liefere strukturierte Code-Patches im Format "
            "PATCH-BEGINN/PATCH-ENDE.\n"
            "Format und Einrueckungs-Regeln stehen im "
            "System-Prompt (Abschnitt 'EINRUECKUNG UND "
            "YAML-BLOCK').\n\n"
            "Mehrere Patches hintereinander "
            "(jeweils PATCH-BEGINN/PATCH-ENDE).\n"
            "Fuer neue Dateien: typ: new_file "
            "(siehe builder.md, Abschnitt NEUE DATEIEN).\n"
            "Kein freier Text. Kein Markdown. Nur Patches.\n"
            "Wenn du einen Anker nicht im Ausschnitt findest: "
            "keinen Patch fuer diese Datei. Kein Erfinden.\n\n"
            "W61: Wenn du einen Anker suchen musst, rufe den "
            "Explore-Subagenten auf:\n"
            "  COMMAND: RUN explore <muster> <pfad>\n"
            "Er durchsucht die Datei und gibt FUND: <pfad>:<zeile>: "
            "<kontext> zurueck. Nutze ihn, BEVOR du einen Patch "
            "mit einem unbestaetigten Anker sendest.\n\n"
            "WICHTIG: Nutze NICHT read_file fuer die Anker-Suche. "
            "read_file liefert nur den Index (Pfad, SHA, Preview). "
            "explore liefert die Zeile. Wenn du den Anker nicht "
            "im Index siehst, ist explore der einzige Weg."
        )
    max_builder_runden = budget.get("max_builder_runden", 3)
    reply_roh, rc = builder_reply_mit_command_loop(
        state, api_key, builder_prompt, _builder_user_prompt,
        project_dir, project_name,
        max_builder_runden=max_builder_runden,
        max_llm=max_llm, max_minutes=max_minutes,
    )
    if rc is not None:
        return rc
    assert reply_roh is not None
    if not reply_roh.ok:
        fehler = reply_roh.error
        print(f"[FAIL] Builder: {fehler}")
        audit("builder_call_failed", {"error": fehler},
              project_dir, project_name)
        return 4
    reply = reply_roh

    assert reply is not None

    # A1b-fix: normaler Builder-Lauf.
    record_code_entwurf(state, reply.content, phase="normal")
    state.code_patches = parse_code_patches(reply.content)
    print(f"[i] {len(state.code_patches)} Code-Patches geparst.")

    # W33b (2026-10-17): Apply + Post-Apply-Messung
    # VOR dem Review-Loop im Phasen-Modus. Der
    # Judge (W28b) braucht mess_nach + basis_gate,
    # beide entstehen sonst erst in
    # apply_and_recheck NACH dem Review.
    # Nur Phasen-Modus. Alte Architektur
    # (Nicht-Phasen) unveraendert, damit
    # bestehende Nicht-Phasen-Tests gruen bleiben.
    if state.phase_aktiv:
        _rc_w33 = _phase_apply_vor_review(
            state, file_whitelist)
        if _rc_w33 is not None:
            return _rc_w33

    # ==================================================================
    # SCHRITT 3: Review-Schleife (Phase 1)
    # ==================================================================
    max_rounds = budget.get("max_review_rounds", 2)
    verdict = "UNKLAR"
    for runde in range(1, max_rounds + 1):
        # Auflage 2078: der inline-Budget-Check ist entfernt.
        # Der Check erfolgt direkt vor dem Judge-Call via
        # budget_or_recover (siehe unten).

        print(f"\n[--- Judge-Runde {runde} ---]")

        # Auflage 2045: bisherige Runden mitgeben.
        # Der Reviewer soll sehen, was er in Runde 1..N-1 gesagt hat,
        # damit er pruefen kann, ob die Auflagen umgesetzt wurden.
        # Auflage 2183 A1a: ausgelagert nach
        # formatiere_runden().
        runden_block = formatiere_runden(state.review_runden)

        # Auflage 2177: Zieldatei-Ausschnitte an den
        # Reviewer. Der Reviewer sieht damit, was der
        # Builder sieht.
        ziel_pfade_rev = extract_paths_from_aufgabe(
            state.aufgabe, file_whitelist, project_dir)
        ziel_snippets_rev = read_target_snippets(
            ziel_pfade_rev, project_dir, file_whitelist,
            bereits_gemessen=_gemessene_pfade(state))
        szenario = (
            # Phasen-Header (2026-10-16).
            _PHASE_HEADER_CODE_REVIEW
            # Auflage 2152: Auftrag MUSS im Szenario stehen.
            + aufgabe_block(state)
            + _format_whitelist_block(
                list(getattr(state, "file_whitelist", []) or []))
            # W25: Skills-Bloecke.
            + _available_skills_block()
            + _geladene_skills_block(state)
            # Agent-Memory A2: Projekt-Stand.
            + format_projekt_stand(state)
            # Auflage 2178: MESSWERTE-Block direkt sichtbar.
            + format_messwerte_block(collect_messwerte(state))
            + "\n\n"
            + f"{runden_block}"
            f"BASIS-GATE:\n{state.basis_protokoll[:800]}\n\n"
            # Auflage 2191-R: GEMESSENER INHALT vor CODE-ENTWURF.
            # Bug-Fix 2026-10-14: Header, wenn Apply passierte.
            + (("!!! ACHTUNG: Code-Patches wurden angewendet.\n"
                "!!! Der folgende GEMESSENER INHALT ist der\n"
                "!!! Stand VOR dem Apply. Der aktuelle Stand\n"
                "!!! steht im MESSWERTE-Block und im\n"
                "!!! GEMESSENER INHALT NACH APPLY.\n\n")
               if state.mess_protokoll_veraltet else "")
            + f"GEMESSENER INHALT (verbindlich, gewinnt gegen "
            f"ZIELDATEIEN):\n{_messwerte_fuer_prompt(state)}\n\n"
            # Bug-Fix 2026-10-14: Nach-Apply-Block (Z4:
            # nur wenn vorhanden).
            + (f"GEMESSENER INHALT NACH APPLY:\n"
               f"{state.basis_protokoll_nach_apply}\n\n"
               if state.basis_protokoll_nach_apply else "")
            # Auflage 2177: Zieldatei-Ausschnitte.
            + ziel_snippets_rev + "\n\n"
            f"CODE-ENTWURF:\n{state.code_entwurf}\n\n"
            f"TEST-VORSCHLAEGE:\n{state.test_vorschlaege or '(keine)'}\n\n"
            # P2b-Frage-B: Builder-Frage-Abschnitt.
            + ("=== BUILDER-FRAGE ===\n"
               + state.letzte_builder_frage
               + "\n=== /BUILDER-FRAGE ===\n\n"
               "Antworte mit genau einem Block:\n"
               "ANTWORT:\n"
               "<deine Antwort>\n"
               "Kein Verdict in dieser Runde. Kein COMMAND.\n"
               if state.letzte_builder_frage else "")
            + ("Bewerte. Erste Zeile: GO, NO-GO oder "
               "ESKALATION."
               if not state.letzte_builder_frage
               else "")
        )
        # Auflage 2183 A1a + Block 2a: Recovery-Hinweis
        # ausgelagert. Der Reviewer-Agent sieht nur einen
        # neutralen Hinweis, keinen Befund-Text.
        # bool(state.solver_befunde) ist korrekt, weil
        # RunState pro Lauf neu konstruiert wird. Bei
        # persistentem State muesste auf run_id gefiltert
        # werden.
        szenario = (recovery_hinweis_block(
            state.review_runden,
            hat_befund=bool(state.solver_befunde))
            + szenario)
        rc = budget_or_recover(state, max_llm,
                              f"Vor Judge-Verdict Runde {runde}.",
                              project_dir, project_name,
                              max_minutes=max_minutes)
        if rc is not None:
            return rc
        # W28b (2026-10-17): Judge statt Reviewer.
        # Judge sieht NUR contract + mess_nach + test_results.
        # W46b: 'kein Eintrag mit passed_count > 0'
        # umfasst (i) keinen Test-Lauf (Doku-Patch,
        # _ziel_test_pfade leer) UND (ii) einen
        # Test-Lauf, in dem alle Tests skipped/0
        # passed sind. Fall (ii) ist semantisch
        # 'keine echte Testaussage' — Skip auf
        # GO ist vertretbar. Wenn spaeter der
        # Unterschied relevant wird: eigener Block
        # (Kriterium 'Eintrag mit exit_code != 0
        # ODER failed_count > 0 ODER passed_count
        # > 0').
        _w46b_alle_doku = bool(state.code_patches) and all(
            isinstance(p, dict)
            and str(p.get("pfad", "")).endswith(".md")
            for p in state.code_patches)
        _w46b_kein_passed = not any(
            isinstance(_tr, dict)
            and _tr.get("passed_count", 0) > 0
            for _tr in state.basis_gate_test_results)
        if _w46b_alle_doku and _w46b_kein_passed:
            print("[i] Judge uebersprungen (Doku-Patch, "
                  "keine Tests).")
            audit("judge_uebersprungen_doku",
                  {"runde": runde,
                   "anzahl_patches": len(state.code_patches),
                   "phase_id": state.phase_id},
                  project_dir, project_name)
            state.review_runden.append(
                {"runde": runde, "verdict": "GO",
                 "raw": "(uebersprungen: doku)",
                 "recovery": False})
            continue
        judge_input = _build_judge_input(state)
        reply = ask_llm(api_key, judge_prompt, judge_input,
                        state.judge_model, 0.0, state.llm_timeout_s,
                        state=state,
                        max_tokens=state.max_tokens_judge)
        if not reply.ok:
            print(f"[FAIL] Judge: {reply.error}")
            audit("judge_call_failed", {"error": reply.error, "runde": runde},
                  project_dir, project_name)
            return 5

        verdict = classify_verdict(reply.content)
        # Auflage 2183 A1a: recovery-Marker an der Runde.
        # Heute immer False; der Setzer kommt in A3.
        state.review_runden.append(
            {"runde": runde, "verdict": verdict,
             "raw": reply.content, "recovery": False})
        # P2b-Frage-B: ANTWORT-Modus.
        # Reviewer antwortet auf eine Builder-Frage.
        if verdict == "ANTWORT":
            antwort = _extrahiere_antwort(reply.content)
            state.letzte_reviewer_antwort = antwort
            # P2b-Frage-B: Frage ist beantwortet.
            state.letzte_builder_frage = ""
            audit("judge_frage_antwort",
                  {"runde": runde,
                   "antwort": antwort[:500],
                   "antwort_laenge": len(antwort)},
                  project_dir, project_name)
            print(f"[i] Judge-Antwort: "
                  f"{antwort[:200]}")
            # Naechste Builder-Runde mit der Antwort.
            continue
        state.auflagen_log.append(parse_auflagen(reply.content))
        _v2_rc = _review_verdict_behandlung(
            state=state, reply=reply, verdict=verdict,
            runde=runde, max_rounds=max_rounds,
            api_key=api_key, project_dir=project_dir,
            project_name=project_name,
            max_llm=max_llm, max_minutes=max_minutes,
            budget=budget, builder_prompt=builder_prompt,
        )
        if isinstance(_v2_rc, int):
            return _v2_rc
        if _v2_rc == 'break':
            break
        continue

    if verdict != "GO":
        kontext = (
            f"Nach {max_rounds} Runden kein GO. Letzte Antwort:\n"
            f"{state.review_runden[-1]['raw'] if state.review_runden else '(keine)'}"
        )
        v = ask_reviewer_for_recovery(state, "no_go", kontext)
        print_recovery(v)
        audit("recovery_no_go", {"empfehlung": v.empfehlung}, project_dir, project_name)
        return 15

    # ==================================================================
    # UMB-1d: Code-Patches anwenden + Basis-Gate erneut
    # ==================================================================
    rc_apply = apply_and_recheck(state, always, file_whitelist)
    # P-Bugfix 2026-10-16: rc=19 = Post-Apply-Basis-Gate
    # rot. Eigener Korrektur-Loop (Builder -> apply).
    if rc_apply == 19:
        return _post_apply_korrektur_loop(
            state, always, file_whitelist,
            builder_prompt=builder_prompt,
            project_dir=project_dir, project_name=project_name,
            api_key=api_key, max_llm=max_llm,
            max_minutes=max_minutes,
            # W30 (A-W30-2): 2 Runden im normalen
            # Post-Apply-Pfad. Recovery-Pfad
            # (Z. 9626) nutzt 1 Runde.
            max_korrektur_runden=2)
    if rc_apply is not None:
        return rc_apply

    # Block Auftrag-erfuellt B2: Auftrag ist bereits
    # erfuellt. Kein Commit, kein Tag, rc=0.
    if pruefe_auftrag_bereits_erfuellt(state):
        print("[+] Auftrag bereits erfuellt. "
              "Kein Commit noetig.")
        audit("auftrag_bereits_erfuellt",
              {"runden": len(state.review_runden),
               "art": state.solver_befunde[-1].art.name
                   if state.solver_befunde else ""},
              project_dir, project_name)
        audit("pipeline_erfolg_ohne_commit",
              {"grund": "auftrag_bereits_erfuellt"},
              project_dir, project_name)
        return 0

    # ==================================================================
    # SCHRITT 4: Coverage + ggf. Test-Generator + Chaos
    # ==================================================================
    print("\n[*] Schritt 4: Coverage und optionale Test-Generierung.")

    # Coverage laeuft nur, wenn im Katalog vorhanden
    if "coverage" in state.optional:
        print("[*] Coverage-Lauf.")
        execute_commands(state, [{"id": "coverage", "arg": ""}], quelle="reviewer")
        cov_file = project_dir / "coverage.json"
        if cov_file.exists():
            try:
                cov = json.loads(cov_file.read_text(encoding="utf-8"))
                state.coverage_pct = int(
                    cov.get("totals", {}).get("percent_covered", -1))
                print(f"[i] Coverage: {state.coverage_pct}%")
            except (OSError, ValueError):
                print("[WARN] coverage.json nicht lesbar.")
                state.coverage_pct = -1
        else:
            print("[WARN] coverage.json fehlt nach Coverage-Lauf.")
            state.coverage_pct = -1

        # Fail closed: unbekannte Coverage wird wie "< 80%" behandelt.
        if state.coverage_pct < 0 or state.coverage_pct < int(COVERAGE_MIN_PCT):
            print(f"[i] Coverage < {COVERAGE_MIN_PCT}%. Test-Generator wird gerufen.")
            tg_prompt = build_system_prompt(
                state.agents["test_generator"], state.docs,
                state.agent_docs.get("test_generator", []))
            reply = ask_llm(
                api_key, tg_prompt,
                f"Ungetestete Bereiche (Coverage {state.coverage_pct}%):\n"
                f"CODE-BASIS:\n{state.code_entwurf[:3000]}\n\n"
                "Liefere Test-Vorschlaege als Text. Kein Schreiben.",
                state.test_gen_model, 0.3, state.llm_timeout_s,
                state=state,
                max_tokens=state.max_tokens_builder,
            )
            if reply.ok:
                state.test_vorschlaege = reply.content

    if "chaos_probe" in state.optional:
        print("[*] Chaos-Probe.")
        execute_commands(state, [{"id": "chaos_probe", "arg": ""}], quelle="reviewer")

    # ==================================================================
    # SCHRITT 5: Reviewer-Phase 2 (Commit-Review)
    # ==================================================================
    if config.get("review_commit_package", True):
        print("\n[*] Schritt 5: Commit-Paket bauen und reviewen.")

        state.commit_paket = build_commit_paket(state)
        # W25-1 (e): volle Suite vor Sammel-Commit.
        if state.phase_aktiv:
            _w25_ergebnis = _commit_review_w25_suite(
                state, project_dir, project_name)
            if isinstance(_w25_ergebnis, int):
                return _w25_ergebnis
            _w25_suite = _w25_ergebnis
            if _w25_suite["exit_code"] != 0:
                _pos = state.phase_aktueller_index
                _rc_r = _commit_review_w25_recovery(
                    state, _w25_suite, _pos,
                    always, file_whitelist,
                    builder_prompt, project_dir,
                    project_name, api_key,
                    max_llm, max_minutes)
                if _rc_r is not None:
                    return _rc_r
                _uid = ""
                if 0 <= _pos < len(state.phase_unterbloecke):
                    _uid = state.phase_unterbloecke[_pos].get(
                        "id", "")
                _rc_n = _commit_review_w25_suite_nachlauf(
                    state, project_dir, project_name, _uid)
                if _rc_n is not None:
                    return _rc_n

        # D3 (2026-10-16): Deterministische Liste
        # im Phasen-Modus. Ueberschreibt die
        # Builder-Halluzination (10 statt 3 Pfade).
        # D-A4: MUSS vor phase_commit_pakete.append
        # (Z. 7900) laufen.
        # D-A1: auch bei B2 (leere Liste).
        if state.phase_aktiv:
            _d3_pfade = [
                p.get("pfad", "")
                for p in state.code_patches
                if isinstance(p, dict) and p.get("pfad")
            ]
            state.commit_paket["dateien"] = sorted(
                set(_d3_pfade))
            audit("phase_commit_dateien_deterministisch",
                  {"pfade": state.commit_paket["dateien"],
                   "anzahl": len(_d3_pfade),
                   "phase_id": state.phase_id},
                  project_dir, project_name)
        # W10 (2026-10-16): Message-Check praeziser.
        # Nur der Aenderung-Block wird geprueft,
        # nicht jede Pfad-Erwaehnung (Referenzen
        # auf Muster/Template sind zulaessig).
        _w10_msg = state.commit_paket.get("message", "")
        _w10_pfade, _w10_fehler = _extrahiere_aenderung_pfade(
            _w10_msg)
        _w10_wahrheit = {
            _normalisiere_pfad(d)
            for d in state.commit_paket.get("dateien", [])}
        if _w10_fehler:
            audit("commit_message_diskrepanz",
                  {"fall": _w10_fehler,
                   "message_pfade": sorted(_w10_pfade),
                   "dateien": sorted(_w10_wahrheit)},
                  project_dir, project_name)
            print("[FAIL] Commit-Message-Section "
                  "'Aenderung' nicht lesbar "
                  f"(fall={_w10_fehler}).")
            return 9
        if _w10_pfade != _w10_wahrheit:
            _w10_fremd = _w10_pfade - _w10_wahrheit
            _w10_fehlend = _w10_wahrheit - _w10_pfade
            audit("commit_message_diskrepanz",
                  {"fall": "diff",
                   "message_pfade": sorted(_w10_pfade),
                   "dateien": sorted(_w10_wahrheit),
                   "fremd": sorted(_w10_fremd),
                   "fehlend": sorted(_w10_fehlend)},
                  project_dir, project_name)
            print("[FAIL] Commit-Message-Aenderung-Block "
                  "passt nicht zu BETROFFENE DATEIEN.")
            print(f"  Aenderung: {sorted(_w10_pfade)}")
            print(f"  BETROFFENE DATEIEN: "
                  f"{sorted(_w10_wahrheit)}")
            return 9
        if not state.commit_paket.get("message"):
            print("[!] Commit-Paket leer. Kein Commit moeglich.")
            state.commit_paket["message"] = "(leer, Builder hat nichts geliefert)"

        # E (2026-10-16): git diff --name-only HEAD
        # fuer 2169-Nachweis im Commit-Review-Prompt.
        # E-A2: Fail-closed bei Fehler (kein "(Fehler)").
        try:
            _res_dn = subprocess.run(
                ("git", "diff", "--name-only", "HEAD"),
                cwd=str(project_dir),
                capture_output=True, text=True,
                timeout=30, check=False,
                env=subprocess_env(),
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            audit("commit_review_diff_fehler",
                  {"fehler": str(exc)},
                  project_dir, project_name)
            print("[FAIL] git diff --name-only HEAD "
                  "fehlgeschlagen.")
            return 9
        if _res_dn.returncode != 0:
            audit("commit_review_diff_fehler",
                  {"fehler": _res_dn.stderr[:200]},
                  project_dir, project_name)
            print("[FAIL] git diff --name-only HEAD "
                  "rc!=0.")
            return 9
        _diff_name_only = _res_dn.stdout.strip()
        if not _diff_name_only:
            _diff_name_only = "(keine)"
        audit("commit_review_diff_name_only",
              {"pfade": _diff_name_only.splitlines(),
               "phase_aktiv": state.phase_aktiv},
              project_dir, project_name)
        # A1-2 (2026-10-16): P3 — deterministischer
        # Commit-Scope-Check VOR dem Reviewer-Aufruf
        # (R16-Aequivalent).
        _scope_ok, _scope_grund = _check_commit_scope(
            state, _diff_name_only,
            project_dir, project_name)
        if not _scope_ok:
            return 9

        # Auflage 2191-R2b + 2026-10-16: Fail-closed nur,
        # wenn mind. ein Patch mit Anker existiert
        # (typ != new_file). Reine new_file-Patches
        # haben keinen Anker; R7 greift nicht.
        _hat_anker_patches = any(
            p.get("typ", "patch") != "new_file"
            for p in (state.code_patches or [])
            if isinstance(p, dict))
        if _hat_anker_patches and not state.mess_protokoll:
            print("[!] mess_protokoll leer. Commit-Review kann "
                  "Anker nicht pruefen (R7). Fail closed.")
            audit("commit_review_ohne_messung",
                  {"grund": "mess_protokoll_leer"},
                  project_dir, project_name)
            return _fail_closed(
                state, project_dir, project_name, 9,
                "commit_review_ohne_messung")
        # Skip-Pfad: reine new_file-Patches oder keine
        # Patches. Kein Anker, kein R7, kein Fail.
        _rc_w2 = _commit_review_w25_loop(
            state, api_key, project_dir, project_name,
            max_llm, max_minutes, reviewer_prompt, builder_prompt,
            _hat_anker_patches, _diff_name_only,
        )
        if _rc_w2 is not None:
            return _rc_w2

    # C8+C9 (3a-1c-4, Variante A): Approval-Dokument + Human-Gate
    return _approval_und_human_gate(
        state, project_dir, project_name, config,
    )


def _review_verdict_behandlung(
        state: RunState, reply: LLMReply, verdict: str,
        runde: int, max_rounds: int,
        api_key: str, project_dir: Path,
        project_name: str,
        max_llm: int, max_minutes: int,
        budget: dict, builder_prompt: str,
) -> int | None | Literal['break']:
    """Review-Verdict-Dispatch (extrahiert aus run_pipeline).

    Rueckgabe: None -> continue, 'break' -> break, int -> return rc.
    """

    state.empfehlung_log.append(parse_empfehlung(reply.content))
    audit("judge_round",
          _review_round_audit_payload(
              runde, verdict, reply.content),
          project_dir, project_name)

    if verdict == "COMMAND":
        cmds = parse_commands(reply.content)
        # Auflage 2183 C (Y1): Loop in gelieferter
        # Reihenfolge. solver-Commands werden an
        # _handle_solver_command delegiert, alle
        # anderen an execute_commands (einzeln,
        # damit die Reihenfolge erhalten bleibt).
        for cmd in cmds:
            if cmd.get("id") == "solver":
                _handle_solver_command(
                    state, cmd, api_key, runde,
                    max_llm, project_dir, project_name,
                    max_minutes=max_minutes)
            else:
                execute_commands(state, [cmd],
                                 quelle="judge")
        # Auflage 2145: Audit fuer COMMAND in der Review-
        # Schleife. Sonst ist nicht sichtbar, wann der
        # Reviewer COMMAND nutzt.
        audit("judge_command",
              {"runde": runde, "anzahl": len(cmds)},
              project_dir, project_name)
        return None

    if verdict == "ESKALATION":
        print(f"[!] ESKALATION:\n{reply.content[:500]}")
        v = ask_reviewer_for_recovery(state, "eskalation", reply.content)
        print_recovery(v)
        audit("recovery_eskalation",
              {"frage_an_menschen": v.frage_an_menschen[:500],
               "empfehlung": v.empfehlung[:500]},
              project_dir, project_name)
        return 14

    if verdict == "UNKLAR":
        # B0b: UNKLAR ist kein NO-GO.
        _hat_widerspruch = _review_unklar_widerspruch(
            reply.content)
        if _hat_widerspruch:
            print("[i] UNKLAR mit Widerspruchs-Block "
                  "(R15/S10-konform).")
            audit("review_unklar_widerspruch",
                  {"runde": runde},
                  project_dir, project_name)
        else:
            print("[i] UNKLAR ohne Widerspruchs-Block "
                  "(R15-Verstoss oder Sachunklarheit).")
            audit("review_r15_verstoss",
                  {"runde": runde,
                   "grund": "unklar_ohne_widerspruch"},
                  project_dir, project_name)
        _n_unklar = sum(
            1 for r in state.review_runden[-2:]
            if r.get("verdict") == "UNKLAR")
        print(f"[!] Reviewer-Verdikt UNKLAR "
              f"(Runde {runde}, "
              f"{_n_unklar}x in Folge).")
        if _n_unklar >= 2:
            print("[!] 2x UNKLAR in Folge. "
                  "Eskalation an den Menschen.")
            print("[i] Moegliche Aktionen:")
            print("    - Auftrag in phase.yaml "
                  "praezisieren")
            print("    - Phase mit --resume-force "
                  "neu starten")
            print("    - Phase abbrechen")
            audit("review_unklar_eskalation",
                  {"runde": runde,
                   "n_unklar": _n_unklar,
                   "raw": reply.content[:2000]},
                  project_dir, project_name)
            v = ask_reviewer_for_recovery(
                state, "unklar", reply.content)
            print_recovery(v)
            return 14
        return None

    if verdict == "NO-GO":
        print(f"[-] NO-GO:\n{reply.content[:300]}")
        # Auflage 2183 A3 + A4/A5 (P1): Trigger.
        # P1 verfeinert A3 um den Gegenstands-
        # vergleich. Der Audit-Eintrag wird IMMER
        # geschrieben (U6/U7), auch wenn nicht
        # getriggert.
        n_no_go = zaehle_no_go_in_folge(
            state.review_runden)
        schw = state.solver_config.get(
            "p1_schwellwert", P1_SCHWELLWERT_DEFAULT)
        mto = int(state.solver_config.get(
            "p1_min_tokens", P1_MIN_TOKENS_DEFAULT))
        jw, grund = gegenstand_gleich(
            state.review_runden, schw, mto)
        if n_no_go >= 2 and grund == P1_GRUND_GETRIGGERT:
            state.review_runden[-1]["recovery"] = True
        audit("solver_trigger",
              {"runde": runde,
               "n_no_go": n_no_go,
               "jaccard": jw,
               "schwellwert": schw,
               "min_tokens": mto,
               "gegenstand_gleich":
                   grund == P1_GRUND_GETRIGGERT,
               "grund": grund},
              project_dir, project_name)
        # Stufe 0 Aenderung 3: Trigger A und B.
        # II7: nur EIN Solver-Ruf pro Runde. P1
        # hat Vorrang. A/B nur wenn P1 nicht greift.
        _trigger_grund = ""
        if grund == P1_GRUND_GETRIGGERT:
            _trigger_grund = "p1_trigger"
        elif state.letzter_patch_wirkungslos:
            # B4: Builder hat wirkungslosen Patch
            # geliefert. Solver prueft, ob Auftrag
            # bereits erfuellt ist.
            _trigger_grund = "wirkungsloser_patch"
            audit("solver_trigger_c",
                  {"runde": runde},
                  project_dir, project_name)
        elif state.anker_fehler_in_folge >= 2:
            _trigger_grund = "anker_nicht_gemessen"
            audit("solver_trigger_a",
                  {"runde": runde,
                   "in_folge":
                       state.anker_fehler_in_folge},
                  project_dir, project_name)
        elif pruefe_trigger_b(reply.content):
            _trigger_grund = "builder_rueckfrage"
            audit("solver_trigger_b",
                  {"runde": runde},
                  project_dir, project_name)
        # Auflage 2183 B (X6): Solver-Call NUR
        # bei GETRIGGERT (P1) oder A/B.
        if _trigger_grund:
            # Auflage 2183 Block 5 (GG1):
            # Obergrenze fuer Solver-Aufrufe.
            _msr = int(state.solver_config.get(
                "max_runden",
                MAX_SOLVER_RUNDEN_DEFAULT))
            if not erhoehe_solver_aufruf(state, _msr):
                state.review_runden[-1]["recovery"] = False
                audit("solver_max_runden_erreicht",
                      {"runde": runde,
                       "aufrufe": state.solver_aufrufe,
                       "max_runden": _msr,
                       "pfad": "no_go"},
                      project_dir, project_name)
                rc = budget_or_recover(
                    state, max_llm,
                    "Nach Solver-Limit.",
                    project_dir, project_name,
                    max_minutes=max_minutes)
                if rc is not None:
                    return rc
                return None
            # X5: eigenes Budget-Gate.
            rc_solver = budget_or_recover(
                state, max_llm,
                f"Vor Solver-Call (Runde {runde}).",
                project_dir, project_name,
                max_minutes=max_minutes)
            if rc_solver is not None:
                state.review_runden[-1]["recovery"] = False
                audit("solver_budget_exhausted",
                      {"runde": runde},
                      project_dir, project_name)
            else:
                solver_prompt = build_system_prompt(
                    state.agents["solver"], state.docs,
                    state.agent_docs.get("solver", []))
                befund, fehler = rufe_solver(
                    state, api_key, solver_prompt,
                    grund_text=_trigger_grund,
                    trigger_grund=_trigger_grund,
                    aufrufer="trigger_a_b_c")
                if befund is None:
                    # X3: Marker zurueck,
                    # fail-closed (kein Dauer-Block).
                    state.review_runden[-1]["recovery"] = False
                    audit("solver_failed",
                          {"runde": runde,
                           "grund": fehler},
                          project_dir, project_name)
                else:
                    state.solver_befunde.append(befund)
                    state.solver_trigger_quellen.append(
                        _trigger_grund)
                    audit("solver_befund",
                          {"runde": runde,
                           "art": befund.art.name,
                           "run_id": befund.run_id,
                           "quelle": _trigger_grund},
                          project_dir, project_name)
        rc = budget_or_recover(state, max_llm,
                              f"Vor Builder-Neubau (NO-GO Runde {runde}).",
                              project_dir, project_name,
                              max_minutes=max_minutes)
        if rc is not None:
            return rc
        def _bauer_no_go_prompt(
                s: RunState,
                _reply: LLMReply = reply) -> str:
            # P2b-Frage-B: Antwort-Modus.
            # Wenn der Reviewer auf eine Frage
            # geantwortet hat, heisst der Kopf
            # "Reviewer-Antwort", nicht NO-GO.
            kopf = ("Reviewer-Antwort auf deine Frage"
                    if s.letzte_reviewer_antwort
                    else "Reviewer NO-GO")
            antwort_block = ""
            if s.letzte_reviewer_antwort:
                antwort_block = (
                    "=== REVIEWER-ANTWORT auf deine "
                    "Frage ===\n"
                    + s.letzte_reviewer_antwort
                    + "\n\n")
                # Verbrauchen.
                s.letzte_reviewer_antwort = ""
            return (
                f"{kopf}:\n{_reply.content}\n\n"
                + antwort_block
                + _solver_befund_block(s)
                + "GEMESSENER INHALT (verbindlich):\n"
                + f"{_messwerte_fuer_prompt(s)}\n\n"
                + "Ueberarbeite den Code-Entwurf. "
                + "Liefere strukturierte Code-Patches."
            )
        bauer_reply_roh, bauer_rc = builder_reply_mit_command_loop(
            state, api_key, builder_prompt, _bauer_no_go_prompt,
            project_dir, project_name,
            max_builder_runden=budget.get("max_builder_runden", 3),
            max_llm=max_llm, max_minutes=max_minutes,
        )
        if bauer_rc is not None:
            return bauer_rc
        assert bauer_reply_roh is not None
        if bauer_reply_roh.ok:
            # A1b-fix: NO-GO-Builder, normal.
            record_code_entwurf(
                state, bauer_reply_roh.content,
                phase="normal")
            state.code_patches = parse_code_patches(
                bauer_reply_roh.content)
        return None

    if verdict == "GO":
        # Auflage 2117: GO mit Auflagen -> eine weitere Runde.
        auflagen = (state.auflagen_log[-1]
                    if state.auflagen_log else [])
        if auflagen and runde < max_rounds:
            print(f"[i] Code-GO mit {len(auflagen)} Auflagen. "
                  "Weitere Runde zur Umsetzung.")
            rc = budget_or_recover(
                state, max_llm,
                f"Vor Builder-Aufruf (Auflagen-Umsetzung Runde {runde}).",
                project_dir, project_name,
                max_minutes=max_minutes)
            if rc is not None:
                return rc
            auflagen_text = "\n".join(f"- {a}" for a in auflagen)
            def _bauer_auflagen_prompt(
                    s: RunState,
                    _at: str = auflagen_text) -> str:
                return (
                    "Der Reviewer hat GO gegeben, aber folgende "
                    f"Auflagen formuliert:\n{_at}\n\n"
                    + "GEMESSENER INHALT (verbindlich):\n"
                    + f"{_messwerte_fuer_prompt(s)}\n\n"
                    + "Ueberarbeite die Code-Patches, um die "
                    + "Auflagen umzusetzen. Antworte mit den "
                    + "ueberarbeiteten PATCH-BEGINN/PATCH-ENDE-"
                    + "Bloecken. Kein freier Text."
                )
            bauer_reply_roh, bauer_rc = (
                builder_reply_mit_command_loop(
                    state, api_key, builder_prompt,
                    _bauer_auflagen_prompt,
                    project_dir, project_name,
                    max_builder_runden=budget.get(
                        "max_builder_runden", 3),
                    max_llm=max_llm, max_minutes=max_minutes,
                )
            )
            if bauer_rc is not None:
                return bauer_rc
            assert bauer_reply_roh is not None
            if bauer_reply_roh.ok:
                # A1b-fix: Auflagen-Builder, normal.
                record_code_entwurf(
                    state, bauer_reply_roh.content,
                    phase="normal")
                state.code_patches = parse_code_patches(
                    bauer_reply_roh.content)
                print(f"[i] {len(state.code_patches)} Code-Patches "
                      f"nach Auflagen-Umsetzung geparst.")
            return None
        print("[+] Code-GO erhalten.")
        return 'break'
    return None




def _phase_finish_aktiv(
    project_name: str,
    state: RunState,
    rc: int,
) -> None:
    """Resume-R6: setzt phase_aktiv=False nach Erfolg.

    Bedingungen:
      - rc == 0
      - state.phase_aktiv ist True
    Sonst no-op.
    """
    if rc != 0:
        return
    if not state.phase_aktiv:
        return
    plan = _phase_plan_laden(project_name)
    if plan is None:
        audit("phase_finish_warnung",
              {"grund": "plan_nicht_gefunden",
               "phase_id": state.phase_id},
              state.project_dir, project_name)
        return
    plan["phase_aktiv"] = False
    _phase_plan_speichern(project_name, plan)
    state.phase_aktiv = False
    audit("phase_finish",
          {"phase_id": state.phase_id},
          state.project_dir, project_name)



def _resume_force_reset(
        plan: dict[str, Any],
) -> dict[str, Any]:
    """Auflage Resume-Force-A2/A7 (2026-10-16).

    Setzt no_go/failed-Unterbloecke im Plan auf
    pending. Reine Funktion: kein print, kein audit,
    kein _phase_plan_speichern. Der Aufrufer
    uebernimmt die Nebenwirkungen.

    Rueckgabe:
      {"reset": bool,  # wurden Kandidaten gefunden?
       "kandidaten": [{"id": ..., "alter_status": ...}],
       "phase_start_head": "<hash>"}
    """
    ups = plan.get("phase_unterbloecke", [])
    kandidaten: list[dict[str, str]] = []
    for u in ups:
        if not isinstance(u, dict):
            continue
        status = u.get("status")
        if status in ("no_go", "failed"):
            kandidaten.append(
                {"id": u.get("id", ""),
                 "alter_status": status})
            u["status"] = "pending"
    return {
        "reset": bool(kandidaten),
        "kandidaten": kandidaten,
        "phase_start_head": str(
            plan.get("phase_start_head", "") or ""),
    }


def _phasen_basis_gate_ok(
        project_name: str,
        project_dir: Path,
) -> tuple[bool, str, dict[str, Any]]:
    """Phasen-Persistenz (2026-10-16): Basis-Gate
    im Phasen-Modus erweitert.

    Erlaubt untracked Dateien, die zu done-Unter-
    bloecken der phase.yaml gehoeren. Alles andere
    ist Fail-closed.

    Rueckgabe: (ok, grund, details).
      ok=True  + grund="clean": git status leer.
      ok=True  + grund="phasen_untracked": alle
                untracked Pfade gehoeren zu done-
                Unterbloecken.
      ok=False + grund="modifiziert": M/D/R-Eintraege.
      ok=False + grund="fremd_untracked": untracked
                Pfade ohne done-Zuordnung.
      ok=False + grund="git_fehler": git status
                nicht ausfuehrbar.
    """
    try:
        res = subprocess.run(
            ("git", "status", "--porcelain", "-uall"),
            cwd=str(project_dir), capture_output=True,
            text=True, timeout=30, check=False,
            env=subprocess_env(),
        )
    except (subprocess.TimeoutExpired, OSError):
        return (False, "git_fehler", {})
    if res.returncode != 0:
        return (False, "git_fehler", {})
    if not res.stdout.strip():
        return (True, "clean", {})
    # W7 (2026-10-16): A  (intent-to-add) und M
    # (modified) aus done-Pfaden werden akzeptiert
    # (Sammel-Commit folgt am Phasen-Ende).
    # D und R bleiben Fail-closed.
    modified: list[str] = []
    intent: list[str] = []
    untracked: list[str] = []
    for zeile in res.stdout.splitlines():
        if len(zeile) < 3:
            continue
        code = zeile[:2]
        pfad = zeile[3:].strip()
        if code == "??":
            untracked.append(pfad)
        elif code in ("A ", "AM"):
            intent.append(pfad)
        elif code in (" M", "M ", "MM"):
            modified.append(pfad)
        else:
            # D, R, UD, etc. → fail-closed.
            modified.append(pfad)
    if not (modified or intent or untracked):
        return (True, "clean", {})
    try:
        plan = _phase_plan_laden(project_name)
    except ValueError:
        plan = None
    if plan is None:
        # W7b (2026-10-16): Fallback praeziser.
        # Wenn modified/intent vorliegt, ist der
        # Grund 'modifiziert'; nur bei untracked
        # 'fremd_untracked'.
        if modified:
            return (False, "modifiziert",
                    {"modified": modified})
        if intent:
            return (False, "fremd_untracked",
                    {"intent": intent})
        return (False, "fremd_untracked",
                {"untracked": untracked})
    done_pfade: set[str] = set()
    done_ids: list[str] = []
    for u in plan.get("phase_unterbloecke", []):
        if not isinstance(u, dict):
            continue
        if u.get("status") != "done":
            continue
        pk = u.get("commit_paket")
        if not isinstance(pk, dict):
            continue
        for d in pk.get("dateien", []):
            if isinstance(d, str) and d:
                done_pfade.add(d)
        if pk.get("dateien"):
            done_ids.append(u.get("id", ""))

    def _norm(p: str) -> str:
        return p.lstrip("./")

    done_norm = {_norm(p) for p in done_pfade}
    # W7: Alle drei Listen gegen done_norm.
    fremd_mod = [
        p for p in modified
        if _norm(p) not in done_norm
    ]
    if fremd_mod:
        return (False, "modifiziert",
                {"modified": fremd_mod,
                 "done_pfade": sorted(done_pfade)})
    # W34 (2026-10-17): .werkstatt/ ist Laufzeit-
    # Verzeichnis (W26/W27: plan.md, contracts/).
    # Pro Lauf neu erzeugt, nicht versioniert
    # (.gitignore A.1). Defense-in-Depth: Ausnahme
    # wirkt auch, wenn .gitignore fehlt oder
    # umgangen wird. Andere Laufzeit-Verzeichnisse
    # NICHT in dieser Ausnahme (Merkposten W34b).
    # _norm entfernt fuehrende Punkte/Slashes, daher
    # den Praefix NACH _norm pruefen.
    _W34_PRAEFIX = "werkstatt/"
    fremd = [
        p for p in (untracked + intent)
        if _norm(p) not in done_norm
        and not _norm(p).startswith(_W34_PRAEFIX)
    ]
    if fremd:
        return (False, "fremd_untracked",
                {"untracked": untracked,
                 "intent": intent,
                 "fremd": fremd,
                 "done_pfade": sorted(done_pfade)})
    return (True, "phasen_clean",
            {"untracked": untracked,
             "intent": intent,
             "modified": modified,
             "done_ids": done_ids})


# WEG-X-P19b: Zaehler fuer Praefix-Format-Verwendung.
# Wird von _plan_ist_messungsbasiert gesetzt, vom
# Aufrufer im --phase-Pfad gelesen (Audit).
_plan_ist_messungsbasiert_praefix_zaehler: int = 0


def _plan_ist_messungsbasiert(
        plan: dict[str, Any],
) -> tuple[bool, list[str]]:
    """WEG-X-P19b: akzeptiert zwei Formate.

    Form (1) Praefix (degraded, WEG-X-P19b-A1):
      "neu: datei" oder "anker: 'text'".
      Wird per Audit-Event
      planner_plan_praefix_format_verwendet
      gezaehlt (Messung fuer Deprecation).

    Form (2) P17 (Ziel-Form):
      "datei:... aktion: neu|patch ... "
      mit "signatur:" (bei neu) oder
      "anker:" (bei patch).

    Syntax-Check: prueft nur, ob unterpunkte
    Form (1) oder (2) erfuellen. Dekorative
    Marker passieren den Check. Wahrheits-
    Pruefung ist LLM-Sache (P19).

    Echte Verletzungen bleiben fail-closed:
      - "test:..." ohne "datei:..."
      - "datei:..." ohne "aktion:"
      - "aktion: neu" ohne "signatur:"
      - "aktion: patch" ohne "anker:"
    """
    import re as _re
    fehlend: list[str] = []
    praefix_verwendet = 0
    for u in plan.get("phase_unterbloecke", []):
        if not isinstance(u, dict):
            continue
        uid = u.get("id", "?")
        unterpunkte = u.get("unterpunkte", []) or []
        for punkt in unterpunkte:
            if not isinstance(punkt, str):
                continue
            p = punkt
            # Form (1): Praefix "neu:" oder "anker:".
            hat_praefix_neu = bool(
                _re.search(r"(?i)\bneu\s*:", p))
            hat_praefix_anker = bool(
                _re.search(r"(?i)\banker\s*:", p))
            if hat_praefix_neu or hat_praefix_anker:
                praefix_verwendet += 1
                continue
            # Form (2): P17-Felder.
            hat_datei = bool(
                _re.search(r"(?i)\bdatei\s*:", p))
            hat_aktion_neu = bool(
                _re.search(
                    r"(?i)\baktion\s*:\s*neu\b", p))
            hat_aktion_patch = bool(
                _re.search(
                    r"(?i)\baktion\s*:\s*patch\b", p))
            hat_signatur = bool(
                _re.search(r"(?i)\bsignatur\s*:", p))
            hat_anker_feld = bool(
                _re.search(r"(?i)\banker\s*:", p))
            if (hat_datei and hat_aktion_neu
                    and hat_signatur):
                continue
            if (hat_datei and hat_aktion_patch
                    and hat_anker_feld):
                continue
            # Verletzungs-Grund bestimmen (A4).
            if not hat_datei and p.lstrip().lower().startswith(
                    "test:"):
                grund = ("test: ohne datei: — P17 verlangt "
                         "datei:aktion:signatur/anker + test")
            elif hat_datei and not (hat_aktion_neu
                                     or hat_aktion_patch):
                grund = "datei: ohne aktion: neu|patch"
            elif hat_aktion_neu and not hat_signatur:
                grund = "aktion: neu ohne signatur:"
            elif hat_aktion_patch and not hat_anker_feld:
                grund = "aktion: patch ohne anker:"
            else:
                grund = "kein anker/signatur oder datei/aktion"
            fehlend.append(f"{uid}: {grund} | {p[:60]}")
    global _plan_ist_messungsbasiert_praefix_zaehler
    _plan_ist_messungsbasiert_praefix_zaehler = (
        praefix_verwendet)
    return (len(fehlend) == 0, fehlend)


def _plan_ist_portionierbar(
        plan: dict[str, Any],
) -> tuple[bool, list[str]]:
    """WEG-X-P19: Portionierungs-Check, max 7 Unterpunkte
    pro Unterblock.

    Unterpunkt = ein Array-Eintrag in unterpunkte.
    Kann 'neu: datei', 'patch: datei', 'test: datei',
    oder 'hinweis: ...' sein.

    1-2 Zieldateien + 1 Test ist reine Prompt-Regel
    (P15), wird hier nicht geprueft (HR-R8,
    Variante (a)).
    """
    zu_gross: list[str] = []
    for u in plan.get("phase_unterbloecke", []):
        if not isinstance(u, dict):
            continue
        uid = u.get("id", "?")
        n = len(u.get("unterpunkte", []) or [])
        if n > 7:
            zu_gross.append(f"{uid}: {n} Unterpunkte")
    # W51f: Phasen-Groesse pruefen.
    # Grenze 5 Unterbloecke / 6 Zieldateien
    # (W51f-a). Nur Erstlauf-Pfad aufgerufen
    # (Z. 11792); Resume-Pfad (Z. 10753)
    # ruft diese Funktion nicht.
    _ups = plan.get("phase_unterbloecke", []) or []
    _n_ups = len(_ups)
    if _n_ups > 5:
        zu_gross.append(
            f"Phase: {_n_ups} Unterbloecke, "
            f"max 5. Teile in mehrere Phasen.")
    import re as _re
    _datei_pfade: set[str] = set()
    for _u in _ups:
        if not isinstance(_u, dict):
            continue
        for _p in _u.get("unterpunkte", []) or []:
            if not isinstance(_p, str):
                continue
            _m = _re.search(r"datei:([^\s,;]+)", _p)
            if _m:
                _datei_pfade.add(
                    _m.group(1).strip().strip("'\""))
    if len(_datei_pfade) > 6:
        zu_gross.append(
            f"Phase: {len(_datei_pfade)} Zieldateien, "
            f"max 6. Teile in mehrere Phasen.")
    return (len(zu_gross) == 0, zu_gross)


# W51b (2026-10-18): Werkstatt-Prefixe, die im
# Zielprojekt NICHT vorkommen duerfen. A-W51-10:
# 'harness/' ist NICHT enthalten, weil es in
# security-ai existiert und legitimer Zielpfad ist.
_W51_WERKSTATT_PREFIXE = (
    "agents/",
    "skills/",
    "werkstatt/",
)


def _plan_ist_new_file_valide(
        plan: dict[str, Any],
        project_dir: Path,
) -> tuple[bool, list[str], str]:
    """W51b: prueft aktion:neu gegen project_dir.

    W51: prueft nur Datei-Existenz gegen project_dir.
    Die 'Messe JEDE'-Regel im planner.md-Prompt ist
    NICHT deterministisch durchsetzbar (WEG-X-P19-R1).
    Der Prompt ist Leitfaden, der Check ist harte
    Sperre. Beide zusammen garantieren nicht, dass
    der Planner gemessen hat — nur dass er keinen
    'aktion:neu auf existierende Datei' baut.

    Rueckgabe: (ok, fehler, grund).
      ok=True, fehler=[], grund="": alles in Ordnung.
      ok=False, fehler=[...], grund="pfad" oder
        "existiert": Fail-closed.
    """
    import re as _re
    fehler: list[str] = []
    grund = ""
    projekt = project_dir.resolve()
    for u in plan.get("phase_unterbloecke", []):
        if not isinstance(u, dict):
            continue
        for punkt in u.get("unterpunkte", []) or []:
            if not isinstance(punkt, str):
                continue
            m = _re.search(
                r"datei:([^\s,;]+)", punkt)
            if not m:
                continue
            pfad = m.group(1).strip().strip("'\"")
            if not pfad:
                continue
            # Aktion bestimmen.
            m_akt = _re.search(
                r"aktion:\s*(neu|patch)", punkt)
            if not m_akt or m_akt.group(1) != "neu":
                continue
            # Pfad-Sicherheit (A-W51-3).
            p = Path(pfad)
            if p.is_absolute():
                try:
                    p.resolve().relative_to(projekt)
                except ValueError:
                    fehler.append(
                        f"{u.get('id','?')}: "
                        f"absoluter Pfad ausserhalb "
                        f"project_dir: {pfad}")
                    grund = grund or "pfad"
                    continue
            if ".." in p.parts:
                fehler.append(
                    f"{u.get('id','?')}: '..' im "
                    f"Pfad: {pfad}")
                grund = grund or "pfad"
                continue
            if any(pfad.startswith(pre)
                   for pre in _W51_WERKSTATT_PREFIXE):
                fehler.append(
                    f"{u.get('id','?')}: "
                    f"Werkstatt-Pfad: {pfad}")
                grund = grund or "pfad"
                continue
            # Datei-Existenz gegen project_dir.
            ziel = projekt / pfad
            if ziel.exists():
                fehler.append(
                    f"{u.get('id','?')}: "
                    f"aktion:neu auf existierende "
                    f"Datei: {pfad}")
                grund = grund or "existiert"
    return (len(fehler) == 0, fehler, grund)




def _phase_planner_resume(
        project_name: str,
        state: RunState,
        api_key: str,
        phasen_text: str,
        historie: str,
) -> int:
    """W35a-2 (2026-10-17): Planner-Resume im Resume-Pfad.

    Zustands-Automat (A-W35a-12/13/15):
      Z4:  trigger leer, befund gefuellt
           -> rc=18 (Monotonie-Verletzung).
      Z1:  trigger leer, befund leer
           -> Planner-Resume normal.
      Z2a: trigger gefuellt, solver_aufrufe==0
           -> rc=18 (Widerspruch).
      Z2b: trigger gefuellt, aufrufe>0, befund leer
           -> rc=18 (Solver ohne Befund).
      Z3:  trigger gefuellt, befund gefuellt
           -> Planner-Resume MIT solver_befund.

    Cap (A-W35a-5): 1x pro uid pro Prozess.
    Merge (A-W35a-16): via _phase_plan_korrektur-
      Mechanik (Struktur-Check + done-Schutz).

    Rueckgabe: rc (0 = Erfolg, sonst fail-closed).
    """
    ups = state.phase_unterbloecke
    _offene = [
        u for u in ups
        if isinstance(u, dict)
        and u.get("status") in ("no_go", "failed")
    ]
    if not _offene:
        return 0
    # Z4: Monotonie-Verletzung.
    if state.solver_befunde and not \
            state.solver_trigger_quellen:
        print("[FAIL] Planner-Resume: Z4 (Befund ohne "
              "Trigger). Fail closed.")
        audit("planner_resume_befund_ohne_trigger",
              {"phase_id": state.phase_id},
              state.project_dir, project_name)
        return 18
    # Z2a / Z2b / Z3.
    _solver_kontext = ""
    if state.solver_trigger_quellen:
        if state.solver_aufrufe == 0:
            print("[FAIL] Planner-Resume: Z2a (Trigger "
                  "ohne Solver-Aufruf). Fail closed.")
            audit("planner_resume_solver_nicht_gerufen",
                  {"phase_id": state.phase_id,
                   "trigger_anzahl":
                       len(state.solver_trigger_quellen)},
                  state.project_dir, project_name)
            return 18
        if not state.solver_befunde:
            print("[FAIL] Planner-Resume: Z2b (Solver "
                  "ohne Befund). Fail closed.")
            audit("planner_resume_solver_ohne_befund",
                  {"phase_id": state.phase_id,
                   "aufrufe": state.solver_aufrufe},
                  state.project_dir, project_name)
            return 18
        # Z3: solver_befund mitgeben.
        try:
            _solver_kontext = format_solver_befund(
                state.solver_befunde[-1])
        except ValueError as exc:
            print("[FAIL] Planner-Resume: Solver-Befund "
                  "kaputt. Fail closed.")
            audit("planner_resume_solver_befund_kaputt",
                  {"phase_id": state.phase_id,
                   "fehler": str(exc)[:200]},
                  state.project_dir, project_name)
            return 18
    # Cap pro uid.
    for _u in _offene:
        _uid = _u.get("id", "")
        if not _uid:
            continue
        _n = state.planner_resume_anzahl.get(_uid, 0)
        if _n >= 1:
            print(f"[FAIL] Planner-Resume-Cap erreicht "
                  f"({_uid}, {_n}x). Fail closed.")
            audit("planner_resume_cap_erreicht",
                  {"phase_id": state.phase_id,
                   "uid": _uid, "anzahl": _n},
                  state.project_dir, project_name)
            return 18
    # Planner-Resume starten.
    for _u in _offene:
        _uid = _u.get("id", "")
        if _uid:
            state.planner_resume_anzahl[_uid] = (
                state.planner_resume_anzahl.get(_uid, 0) + 1)
    audit("planner_resume_start",
          {"phase_id": state.phase_id,
           "offene": [_u.get("id") for _u in _offene],
           "solver_kontext_vorhanden": bool(_solver_kontext)},
          state.project_dir, project_name)
    print(f"[*] Planner-Resume: "
          f"{len(_offene)} offene Unterbloecke.")
    # phase_stand bauen.
    _ups_stand: list[dict[str, Any]] = []
    _naechster: str | None = None
    for _u in ups:
        if not isinstance(_u, dict):
            continue
        _status = _u.get("status", "?")
        _pkg_groesse = len(
            _u.get("commit_paket", {}).get("dateien", [])
            if isinstance(_u.get("commit_paket"), dict)
            else [])
        _letzter = _u.get("letzter_befund", "")
        _ups_stand.append({
            "id": _u.get("id", "?"),
            "status": _status,
            "paket_groesse": _pkg_groesse,
            "letzter_befund": _letzter,
        })
        if (_naechster is None
                and _status in {"no_go", "failed", "pending"}):
            _naechster = _u.get("id")
    _phase_stand = {
        "phase_id": state.phase_id,
        "unterbloecke": _ups_stand,
        "naechster": _naechster,
    }
    # korrektur_kontext (W35a-2b: vollstaendig wie
    # _phase_plan_korrektur).
    # W38 (2026-10-17): alter_plan im P10-P14-Format,
    # damit der Planner das Format erkennt und
    # repliziert.
    _alter_plan_zeilen: list[str] = [
        f"PHASE: {state.phase_id} - {state.phase_titel}",
        "",
    ]
    for _u in ups:
        if not isinstance(_u, dict):
            continue
        _uid = _u.get("id", "?")
        _utitel = _u.get("titel", "")
        _ustatus = _u.get("status", "?")
        _alter_plan_zeilen.append(
            f"UNTERBLOCK: {_uid} - {_utitel}")
        # W39: Status NICHT als Kommentar im
        # P10-P16-Format. Der Planner sieht den
        # Stand im phase_stand-Block.
        _alter_plan_zeilen.append("Unterpunkte:")
        for _punkt in _u.get("unterpunkte", []):
            # Unterpunkte sind einzeilig; Zeilenumbrueche
            # in Einzelzeilen aufloesen, damit das
            # -Format sauber bleibt.
            _punkt_sauber = " ".join(
                str(_punkt).splitlines())
            _alter_plan_zeilen.append(
                f"  - {_punkt_sauber}")
        _alter_plan_zeilen.append(
            f"Geschaetzte Runden: "
            f"{_u.get('geschaetzte_runden', 1)}")
        _alter_plan_zeilen.append("")
    _alter_plan = "\n".join(_alter_plan_zeilen)
    _pakete_zeilen: list[str] = []
    for _i, _p in enumerate(state.phase_commit_pakete, 1):
        _dateien = ", ".join(_p.get("dateien", []))
        _msg = _p.get("message", "")[:120]
        _pakete_zeilen.append(
            f"Paket {_i}: {_dateien}\n  {_msg}")
    _pakete_kompakt = "\n".join(_pakete_zeilen) or "(keine)"
    _korrektur_kontext: dict[str, Any] = {
        "begruendung": "Planner-Resume nach no_go/failed.",
        "alter_plan": _alter_plan,
        "pakete_kompakt": _pakete_kompakt,
        "reviewer_befund": (
            state.review_runden[-1].get("raw", "")
            if state.review_runden else ""),
    }
    if _solver_kontext:
        _korrektur_kontext["solver_befund"] = _solver_kontext
    # W42 (2026-10-17): Zieldateien der offenen
    # Unterbloecke messen, BEVOR der Planner
    # den Plan formuliert. Sonst uebernimmt er
    # falsche Anker aus dem alten Plan.
    _w42_pfade: list[str] = []
    for _off in _offene:
        for _punkt in _off.get("unterpunkte", []):
            for _m in re.finditer(
                    r"datei:\s*([^\s,]+)", str(_punkt)):
                _pfad = _m.group(1).strip()
                if (_pfad and _pfad not in _w42_pfade
                        and (_off.get("id")
                             in state.planner_resume_anzahl
                             or True)):
                    _w42_pfade.append(_pfad)
    # Nur beim ersten Resume fuer den Block.
    _w42_kontext: list[str] = []
    _read_meas = state.always.get("read_file")
    if _read_meas is None:
        _read_meas = state.optional.get("read_file")
    if _read_meas is not None:
        for _pfad in _w42_pfade[:4]:
            try:
                _out, _ok, _argv = run_measurement_mit_argv(
                    _read_meas,
                    list(getattr(state, "file_whitelist", [])),
                    state.project_dir, _pfad)
            except Exception:  # noqa: BLE001,S112
                continue
            if _ok:
                _w42_kontext.append(
                    f"=== read_file {_pfad} ===\n"
                    f"{_out[:2000]}")
                audit("planner_resume_messung",
                      {"pfad": _pfad,
                       "len": len(_out),
                       "ok": True},
                      state.project_dir, project_name)
            else:
                # W45 (2026-10-17): Datei fehlt.
                # Der Planner MUSS sehen, dass die
                # Zieldatei nicht existiert und
                # aktion:neu verwenden.
                _w42_kontext.append(
                    f"=== ZIELDATEI FEHLT: {_pfad} ===\n"
                    f"Dieser Pfad existiert NICHT im "
                    f"Projekt. Wenn der Auftrag diese "
                    f"Datei anlegen soll: verwende "
                    f"aktion:neu, nicht aktion:patch.\n"
                    f"Fehler: {_out[:200]}")
                audit("planner_resume_messung",
                      {"pfad": _pfad,
                       "ok": False,
                       "grund": "fehlt"},
                      state.project_dir, project_name)
    if _w42_kontext:
        _korrektur_kontext["gemessener_inhalt"] = (
            "\n\n".join(_w42_kontext))
    # Planner rufen.
    antwort = _planner_lauf(
        state, api_key, phasen_text,
        state.project_dir, project_name, historie,
        stufe=2, korrektur_kontext=_korrektur_kontext,
        phase_stand=_phase_stand)
    if antwort is None:
        print("[FAIL] Planner-Resume: Planner lieferte "
              "None. Fail closed.")
        audit("planner_resume_failed",
              {"phase_id": state.phase_id,
               "grund": "planner_none"},
              state.project_dir, project_name)
        return 18
    try:
        _neue_id, _neue_titel = _parse_phase_kopf(antwort)
        _neue_ups = _parse_phase_plan(antwort)
    except ValueError as exc:
        print(f"[FAIL] Planner-Resume: Parse-Fehler: {exc}")
        audit("planner_resume_failed",
              {"phase_id": state.phase_id,
               "grund": "parse_failed",
               "exception": str(exc)[:200]},
              state.project_dir, project_name)
        return 18
    # Merge via Struktur-Check (wie _phase_plan_korrektur).
    plan = _phase_plan_laden(project_name)
    if plan is None:
        audit("planner_resume_failed",
              {"phase_id": state.phase_id,
               "grund": "phase_yaml_nicht_lesbar"},
              state.project_dir, project_name)
        return 18
    _alte_ups = plan.get("phase_unterbloecke", [])
    # W35a-2d-1 (2026-10-17): Suffix-Erkennung +
    # Pruefungen. Bei Aufteilung eines no_go/failed-
    # Unterblocks in mehrere Suffix-Kinder.
    _w35a2d_alt_by_id: dict[str, dict] = {
        u.get("id", ""): u
        for u in _alte_ups if isinstance(u, dict)}
    _w35a2d_alt_ids_in_order: list[str] = [
        u.get("id", "") for u in _alte_ups
        if isinstance(u, dict)]

    def _w35a2d_find_parent(neu_id: str) -> str | None:
        kandidaten = [
            a for a in _w35a2d_alt_ids_in_order
            if a and neu_id.startswith(a)
            and len(neu_id) > len(a)
            and neu_id[len(a):].isalnum()
        ]
        if not kandidaten:
            return None
        return max(kandidaten, key=len)

    _w35a2d_neue_zu_parent: dict[str, str] = {}
    for _u in _neue_ups:
        _w35a2d_nid_lokal = _u.get("id", "")
        _w35a2d_p_lokal = _w35a2d_find_parent(
            _w35a2d_nid_lokal)
        if _w35a2d_p_lokal:
            _w35a2d_neue_zu_parent[
                _w35a2d_nid_lokal] = _w35a2d_p_lokal

    _w35a2d_neu_ids = {
        u.get("id", "") for u in _neue_ups}
    _w35a2d_suffix_kinder: dict[str, list[str]] = {}
    for _nid, _pid in _w35a2d_neue_zu_parent.items():
        _w35a2d_suffix_kinder.setdefault(
            _pid, []).append(_nid)

    # Tiefe 2 verboten.
    for _nid, _pid in _w35a2d_neue_zu_parent.items():
        if _pid in _w35a2d_neue_zu_parent:
            audit("planner_resume_split_depth",
                  {"phase_id": state.phase_id,
                   "kind": _nid, "parent": _pid},
                  state.project_dir, project_name)
            print(f"[FAIL] Split-Tiefe 2: {_nid} <- {_pid}.")
            return 18

    # Cap / done / Rename / Misch pro Elternteil.
    _w35a2d_split_anzahl = 0
    for _pid, _kinder in _w35a2d_suffix_kinder.items():
        _alt_u = _w35a2d_alt_by_id.get(_pid, {})
        if _alt_u.get("status") == "done":
            audit("planner_resume_split_done_verboten",
                  {"phase_id": state.phase_id,
                   "parent": _pid},
                  state.project_dir, project_name)
            print(f"[FAIL] Split auf done {_pid} "
                  f"verboten.")
            return 18
        if len(_kinder) > 4:
            audit("planner_resume_split_cap_erreicht",
                  {"phase_id": state.phase_id,
                   "parent": _pid,
                   "anzahl": len(_kinder)},
                  state.project_dir, project_name)
            print(f"[FAIL] Split-Cap: {_pid} -> "
                  f"{len(_kinder)} Kinder.")
            return 18
        if (len(_kinder) == 1
                and _pid not in _w35a2d_neu_ids):
            audit("planner_resume_rename_verboten",
                  {"phase_id": state.phase_id,
                   "parent": _pid,
                   "kind": _kinder[0]},
                  state.project_dir, project_name)
            print(f"[FAIL] Rename: {_pid} -> "
                  f"{_kinder[0]}.")
            return 18
        if _pid in _w35a2d_neu_ids:
            audit("planner_resume_misch_zustand",
                  {"phase_id": state.phase_id,
                   "parent": _pid,
                   "kinder": _kinder},
                  state.project_dir, project_name)
            print(f"[FAIL] Misch-Zustand: {_pid} "
                  f"und {_kinder}.")
            return 18
        _w35a2d_split_anzahl += 1
    if _w35a2d_split_anzahl > 1:
        audit("planner_resume_mehrfach_split_verboten",
              {"phase_id": state.phase_id,
               "anzahl": _w35a2d_split_anzahl},
              state.project_dir, project_name)
        print(f"[FAIL] Mehrfach-Split: "
              f"{_w35a2d_split_anzahl}.")
        return 18

    # Coverage C1/C2/C3 (A-W35a-2d-6).
    # C1: jeder neue Eintrag 1:1 ODER Suffix.
    for _u in _neue_ups:
        _w35a2d_nid_c1 = _u.get("id", "")
        if (_w35a2d_nid_c1
                not in _w35a2d_neue_zu_parent
                and _w35a2d_nid_c1
                not in _w35a2d_alt_by_id):
            audit("planner_resume_coverage",
                  {"phase_id": state.phase_id,
                   "grund": "c1_unbekannt",
                   "id": _w35a2d_nid_c1},
                  state.project_dir, project_name)
            print(f"[FAIL] Coverage C1: unbekannte id "
                  f"{_w35a2d_nid_c1}.")
            return 18
    # C2: jeder alte done-Eintrag unveraendert.
    for _u in _alte_ups:
        if not isinstance(_u, dict):
            continue
        if _u.get("status") != "done":
            continue
        _w35a2d_aid_c2 = _u.get("id", "")
        if not any(
                n.get("id") == _w35a2d_aid_c2
                for n in _neue_ups):
            audit("planner_resume_coverage",
                  {"phase_id": state.phase_id,
                   "grund": "c2_done_fehlt",
                   "id": _w35a2d_aid_c2},
                  state.project_dir, project_name)
            print(f"[FAIL] Coverage C2: done "
                  f"{_w35a2d_aid_c2} fehlt.")
            return 18
    # C3: jeder alte no_go/failed/pending 1:1
    #     ODER hat min. 1 Suffix-Kind.
    for _u in _alte_ups:
        if not isinstance(_u, dict):
            continue
        if _u.get("status") not in (
                "no_go", "failed", "pending"):
            continue
        _w35a2d_aid_c3 = _u.get("id", "")
        _hat_1zu1 = _w35a2d_aid_c3 in _w35a2d_neu_ids
        _hat_kinder = (
            _w35a2d_aid_c3 in _w35a2d_suffix_kinder)
        if not (_hat_1zu1 or _hat_kinder):
            audit("planner_resume_coverage",
                  {"phase_id": state.phase_id,
                   "grund": "c3_verloren",
                   "id": _w35a2d_aid_c3},
                  state.project_dir, project_name)
            print(f"[FAIL] Coverage C3: "
                  f"{_w35a2d_aid_c3} verloren.")
            return 18

    # Order-Preservation (A-W35a-2d-7).
    if _w35a2d_split_anzahl == 1:
        _w35a2d_pid_order = next(
            iter(_w35a2d_suffix_kinder))
        _w35a2d_kinder_order = (
            _w35a2d_suffix_kinder[_w35a2d_pid_order])
        _w35a2d_pos_alt = (
            _w35a2d_alt_ids_in_order.index(
                _w35a2d_pid_order))
        _w35a2d_pos_neu = [
            i for i, u in enumerate(_neue_ups)
            if u.get("id") in _w35a2d_kinder_order]
        if _w35a2d_pos_neu:
            _w35a2d_pos_min = min(_w35a2d_pos_neu)
            _w35a2d_pos_max = max(_w35a2d_pos_neu)
            if (_w35a2d_pos_max - _w35a2d_pos_min + 1
                    != len(_w35a2d_pos_neu)):
                audit("planner_resume_order_verletzt",
                      {"phase_id": state.phase_id,
                       "parent": _w35a2d_pid_order,
                       "grund": "nicht_aufeinander"},
                      state.project_dir, project_name)
                print(f"[FAIL] Order: "
                      f"{_w35a2d_pid_order}-Kinder "
                      f"nicht aufeinander.")
                return 18
            if _w35a2d_pos_min != _w35a2d_pos_alt:
                audit("planner_resume_order_verletzt",
                      {"phase_id": state.phase_id,
                       "parent": _w35a2d_pid_order,
                       "grund": "position",
                       "erwartet":
                           _w35a2d_pos_alt,
                       "gefunden":
                           _w35a2d_pos_min},
                      state.project_dir, project_name)
                print(f"[FAIL] Order: "
                      f"{_w35a2d_pid_order} an "
                      f"Position {_w35a2d_pos_min} "
                      f"statt {_w35a2d_pos_alt}.")
                return 18

    # Bestehender Anzahl-Check bleibt als Fallback,
    # aber bei validiertem Split (W35a-2d) ueberspringen.
    if (_w35a2d_split_anzahl == 0
            and len(_alte_ups) != len(_neue_ups)):
        print("[FAIL] Planner-Resume: Anzahl geaendert. "
              "Fail closed.")
        audit("planner_resume_failed",
              {"phase_id": state.phase_id,
               "grund": "struktur_anzahl",
               "alt": len(_alte_ups),
               "neu": len(_neue_ups)},
              state.project_dir, project_name)
        return 18
    # Bestehender ID-Check bleibt als Fallback,
    # aber bei validiertem Split ueberspringen.
    if _w35a2d_split_anzahl == 0:
        for _i, (_alt, _neu) in enumerate(
                zip(_alte_ups, _neue_ups)):
            if not isinstance(_alt, dict):
                continue
            if _alt.get("id") != _neu.get("id"):
                print(f"[FAIL] Planner-Resume: id an "
                      f"Position {_i} geaendert. "
                      f"Fail closed.")
                audit("planner_resume_failed",
                      {"phase_id": state.phase_id,
                       "grund": "struktur_id",
                       "position": _i},
                      state.project_dir, project_name)
                return 18
    # Merge (W35a-2d-3, 2026-10-17): neue Logik
    # mit Suffix-Erkennung + letzter_befund-Kopie.
    _gemergt: list[dict[str, Any]] = []
    for _neu in _neue_ups:
        _w35a2d_nid_m = _neu.get("id", "")
        _w35a2d_pid_m = _w35a2d_neue_zu_parent.get(
            _w35a2d_nid_m)
        if _w35a2d_pid_m is not None:
            # Suffix-Kind: letzter_befund vom
            # Elternteil kopieren.
            _w35a2d_pu = _w35a2d_alt_by_id.get(
                _w35a2d_pid_m, {})
            _w35a2d_pb = ""
            if _w35a2d_pu.get("status") in (
                    "no_go", "failed"):
                _w35a2d_pb = _w35a2d_pu.get(
                    "letzter_befund", "")
            _gemergt.append({
                "id": _w35a2d_nid_m,
                "titel": _neu.get("titel", ""),
                "status": "pending",
                "commit_paket": {},
                "unterpunkte": list(
                    _neu.get("unterpunkte", [])),
                "geschaetzte_runden": _neu.get(
                    "geschaetzte_runden", 1),
                "letzter_befund": _w35a2d_pb,
            })
            continue
        _w35a2d_alt_m = _w35a2d_alt_by_id.get(
            _w35a2d_nid_m)
        if (_w35a2d_alt_m is not None
                and _w35a2d_alt_m.get(
                    "status") == "done"):
            _gemergt.append({
                "id": _w35a2d_alt_m["id"],
                "titel": _w35a2d_alt_m.get(
                    "titel", ""),
                "status": "done",
                "commit_paket": dict(
                    _w35a2d_alt_m.get(
                        "commit_paket", {})),
                "unterpunkte": list(
                    _w35a2d_alt_m.get(
                        "unterpunkte", [])),
                "geschaetzte_runden": _w35a2d_alt_m.get(
                    "geschaetzte_runden", 1),
                "letzter_befund": _w35a2d_alt_m.get(
                    "letzter_befund", ""),
            })
            continue
        _gemergt.append({
            "id": _w35a2d_nid_m,
            "titel": _neu.get("titel", ""),
            "status": "pending",
            "commit_paket": {},
            "unterpunkte": list(
                _neu.get("unterpunkte", [])),
            "geschaetzte_runden": _neu.get(
                "geschaetzte_runden", 1),
            "letzter_befund": "",
        })
    plan["phase_id"] = _neue_id
    plan["phase_titel"] = _neue_titel
    plan["phase_unterbloecke"] = _gemergt
    _phase_plan_speichern(project_name, plan)
    state.phase_commit_pakete = []
    state.phase_id = _neue_id
    state.phase_titel = _neue_titel
    state.phase_unterbloecke = _gemergt
    state.phase_aktueller_index = 0
    # Split-Audit (A-W35a-2d-11).
    if _w35a2d_split_anzahl == 1:
        _w35a2d_split_pid = next(
            iter(_w35a2d_suffix_kinder))
        audit("planner_resume_split_ok",
              {"phase_id": state.phase_id,
               "parent": _w35a2d_split_pid,
               "kinder":
                   _w35a2d_suffix_kinder[
                       _w35a2d_split_pid]},
              state.project_dir, project_name)
    audit("planner_resume_merge",
          {"phase_id": state.phase_id,
           "unterbloecke": len(_gemergt),
           "done": sum(
               1 for _u in _gemergt
               if _u.get("status") == "done")},
          state.project_dir, project_name)
    print(f"[+] Planner-Resume: Plan gemergt "
          f"({len(_gemergt)} Unterbloecke).")
    return 0


def _phase_main_vorlauf(
    project_name: str,
) -> PhaseMainVorlaufErgebnis | int:
    """Block A aus _phase_main_pfad (3a-3a).

    M-117a: A liest nur project_name.
    7 fruehe Returns, sonst PhaseMainVorlaufErgebnis.
    """
    """Block P2a: fuehrt den Planner Stufe 2 aus und
    bestaetigt den Phasenplan.

    Ablauf:
      1. Minimales Basis-Gate (Projekt + git clean).
      2. Planner Stufe 2 (max planner_max_runden Runden).
      3. _parse_phase_kopf + _parse_phase_plan.
      4. Anzeige + Bestaetigung [j]/[n]/[e].
      5. Bei [j]: _phase_plan_speichern() SOFORT
         (RR-K13). state.phase_aktiv = True.
         KEIN run_pipeline (P2a: kein Phasen-Loop,
         der ist P2b).

    Rueckgabe: rc.
    """
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        print("[FAIL] DEEPSEEK_API_KEY fehlt. Fail closed.")
        return 1

    # Minimales Basis-Gate.
    try:
        config = _lade_und_pruefe_projekt(project_name)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 1
    project_dir = Path(
        config.get("project_dir", str(Path.cwd()))
    ).expanduser()
    if not project_dir.exists():
        print(f"[FAIL] project_dir fehlt: {project_dir}. "
              "Fail closed.")
        return 18

    # Phasen-Persistenz-A3 (2026-10-16): Basis-Gate
    # im Phasen-Modus erweitert. Erlaubt untracked
    # Dateien aus done-Unterbloecken.
    _bg_ok, _bg_grund, _bg_details = (
        _phasen_basis_gate_ok(project_name, project_dir))
    if not _bg_ok:
        print("[FAIL] Ziel-Repo nicht sauber (git status). "
              "Fail closed.")
        print(f"  Grund: {_bg_grund}")
        if _bg_details:
            print(f"  Details: {_bg_details}")
        audit("phase_basis_gate_failed",
              {"grund": _bg_grund, "details": _bg_details},
              project_dir, project_name)
        return 18
    if _bg_grund == "phasen_untracked":
        print("[i] Basis-Gate: untracked Dateien aus "
              "done-Unterbloecken erlaubt "
              f"({len(_bg_details.get('untracked', []))} "
              f"Pfade, done-IDs: {_bg_details.get('done_ids', [])}).")
        audit("phasen_basis_gate_untracked",
              {"anzahl_untracked":
                   len(_bg_details.get("untracked", [])),
               "pfade": _bg_details.get("untracked", []),
               "done_unterbloecke":
                   _bg_details.get("done_ids", [])},
              project_dir, project_name)

    # Rollen + Docs laden.
    agents_dir = config.get("project_agents_dir")
    if not agents_dir:
        agents_dir = "/opt/werkstatt/agents"
    agents = load_agents(agents_dir)
    docs = load_docs(config.get("docs", {}), project_dir)
    file_whitelist = config.get("file_whitelist", [])
    # Bug-Fix: Katalog laden (fuer Builder-COMMANDs).
    always_kat, optional_kat = build_catalog(
        config, project_dir)

    if "planner" not in agents:
        print("[FAIL] Planner-Rolle nicht gefunden. Fail closed.")
        audit("planner_rolle_fehlt", {}, project_dir,
              project_name)
        return 18

    # Planner-Konfiguration (A9, A10: identisch zu
    # _planner_main_pfad).
    _pcfg = config.get("planner", {}) or {}
    if not isinstance(_pcfg, dict):
        _pcfg = {}
    planner_modus = str(_pcfg.get("modus", "manual"))
    planner_max_runden = int(_pcfg.get("max_runden", 3))
    if planner_modus == "off":
        print("[i] Planner-Modus ist 'off'. Kein Planner-Lauf.")
        return 0
    # P2b-Resume: aktiver Plan vorhanden?
    # Wenn ja: Planner ueberspringen, direkt
    # run_phase.
    try:
        plan_vorhanden = _phase_plan_laden(project_name)
    except ValueError as exc:
        print(f"[FAIL] phase.yaml korrupt: {exc}")
        return 1
    return PhaseMainVorlaufErgebnis(
        api_key=api_key,
        config=config,
        project_dir=project_dir,
        agents=agents,
        docs=docs,
        file_whitelist=file_whitelist,
        always_kat=always_kat,
        optional_kat=optional_kat,
        planner_modus=planner_modus,
        planner_max_runden=planner_max_runden,
        plan_vorhanden=plan_vorhanden,
    )

def _phase_main_plan_verarbeiten(
    project_name: str,
    phasen_text: str,
    state_ref: list[RunState],
    resume_force: bool,
    vor: PhaseMainVorlaufErgebnis,
) -> tuple[RunState, int] | int:
    """Block B aus _phase_main_pfad (3a-3b).

    Liest vor.* (10 Felder) + 4 Parameter.
    force_new_phase und planner_max_runden NICHT in B (M-131).
    Rueckgabe RunState (regulaer) | int (3 Returns: _rc_pr, 18, rc).
    M-126: RunState direkt, kein 1-Feld-Dataclass.
    """
    # Block B lokal entpacken (vor-Felder)
    api_key = vor.api_key
    config = vor.config
    project_dir = vor.project_dir
    agents = vor.agents
    docs = vor.docs
    file_whitelist = vor.file_whitelist
    always_kat = vor.always_kat
    optional_kat = vor.optional_kat
    planner_modus = vor.planner_modus
    plan_vorhanden = vor.plan_vorhanden
    assert plan_vorhanden is not None  # Guard: nur bei Aufruf mit plan

    if not resume_force:
        _ups_check = plan_vorhanden.get(
            "phase_unterbloecke", [])
        # W61: Planner-Resume nur bei no_go (Plan-Problem).
        # Bei failed (Test-Gate rot, Builder-Code falsch)
        # ist der Plan gueltig — der Builder soll es
        # nochmal versuchen, kein Planner-Call.
        _hat_offene = any(
            isinstance(_u, dict)
            and _u.get("status") == "no_go"
            for _u in _ups_check)
        if _hat_offene:
            # state fuer Planner-Resume bauen.
            _pr_state = RunState(
                block_id=config.get("project", "?"),
                aufgabe=phasen_text,
                start_ts=datetime.now(UTC).isoformat(
                    timespec="seconds"),
                docs=docs, agents=agents,
                always=always_kat, optional=optional_kat,
                file_whitelist=file_whitelist,
                api_key=api_key,
                budget=config.get("budget", {}),
                agent_docs=config.get("agent_docs", {}),
                project_dir=project_dir,
                project_name=project_name,
                planner_modus=planner_modus,
            )
            _pr_state.phase_aktiv = True
            _pr_state.phase_id = str(
                plan_vorhanden.get("phase_id", ""))
            _pr_state.phase_titel = str(
                plan_vorhanden.get("phase_titel", ""))
            _pr_state.phase_unterbloecke = list(
                plan_vorhanden.get(
                    "phase_unterbloecke", []))
            _pr_historie = load_recent_commits(
                project_dir, n=10)
            _rc_pr = _phase_planner_resume(
                project_name, _pr_state, api_key,
                phasen_text, _pr_historie)
            if _rc_pr != 0:
                return _rc_pr
            # state wurde gemergt. Neue
            # phase.yaml neu laden.
            plan_vorhanden = _phase_plan_laden(
                project_name)
            if plan_vorhanden is None:
                print("[FAIL] Planner-Resume: "
                      "phase.yaml nach Merge nicht "
                      "lesbar. Fail closed.")
                return 18
    print("[i] Aktiver Phasenplan gefunden. "
          "Ueberspringe Planner.")
    ups_plan = plan_vorhanden.get(
        "phase_unterbloecke", [])
    # Resume-Force (Auflage A2-A7, 2026-10-16):
    # Mensch erzwingt Neustart trotz no_go/failed.
    if resume_force:
        _rf = _resume_force_reset(plan_vorhanden)
        if _rf["reset"]:
            print("[i] --resume-force: folgende "
                  "Unterbloecke werden auf pending "
                  "zurueckgesetzt:")
            for _k in _rf["kandidaten"]:
                print(f"    {_k['id']} ({_k['alter_status']})")
            print("[i] phase_start_head bleibt: "
                  f"{_rf['phase_start_head']}")
            _phase_plan_speichern(project_name, plan_vorhanden)
            audit("phase_resume_force",
                  {"phase_id": plan_vorhanden.get("phase_id"),
                   "reset_unterbloecke": _rf["kandidaten"],
                   "phase_korrektur_zyklus_vorher": 0,
                   "phase_start_head": _rf["phase_start_head"]},
                  project_dir, project_name)
        else:
            print("[i] --resume-force: keine "
                  "no_go/failed-Unterbloecke. Wirkungslos.")
    status_verteilung = {
        "done": 0, "pending": 0, "running": 0,
        "no_go": 0, "failed": 0,
    }
    for u in ups_plan:
        if isinstance(u, dict):
            s = u.get("status", "pending")
            if s in status_verteilung:
                status_verteilung[s] += 1
    bereits_fertig = (
        len(ups_plan) > 0
        and status_verteilung["done"] == len(ups_plan))
    audit("phase_resume_erkannt",
          {"phase_id": plan_vorhanden.get("phase_id"),
           "unterbloecke": len(ups_plan),
           "status_verteilung": status_verteilung,
           "bereits_fertig": bereits_fertig},
          project_dir, project_name)
    state = RunState(
        block_id=config.get("project", "unknown"),
        aufgabe=(f"Phase "
                 f"{plan_vorhanden.get('phase_id')}: "
                 f"{plan_vorhanden.get('phase_titel')}"),
        start_ts=datetime.now(UTC).isoformat(
            timespec="seconds"),
        docs=docs, agents=agents,
        always=always_kat, optional=optional_kat,
        file_whitelist=file_whitelist,
        api_key=api_key,
        budget=config.get("budget", {}),
        agent_docs=config.get("agent_docs", {}),
        project_dir=project_dir,
        project_name=project_name,
        planner_modus=planner_modus,
    )
    state.phase_id = plan_vorhanden.get("phase_id")
    state.phase_titel = plan_vorhanden.get(
        "phase_titel", "")
    state.phase_unterbloecke = ups_plan
    state.phase_aktiv = True
    # Phasen-Persistenz-A1 (2026-10-16): Pakete der
    # bereits done-Unterbloecke aus phase.yaml laden,
    # damit der Sammel-Commit sie einschliesst.
    state.phase_commit_pakete = [
        dict(u["commit_paket"])
        for u in ups_plan
        if isinstance(u, dict)
        and u.get("status") == "done"
        and isinstance(u.get("commit_paket"), dict)
        and u["commit_paket"].get("dateien")
    ]
    if state.phase_commit_pakete:
        print("[i] Phasen-Persistenz: "
              f"{len(state.phase_commit_pakete)} "
              "done-Paket(e) aus phase.yaml geladen.")
    state.start_monotonic = time.monotonic()
    # Resume-Fix: state_ref NICHT hier anhaengen.
    # run_phase macht das am Ende (Guard verlangt
    # leeren state_ref beim Aufruf).
    _neue_run_id = (
        datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        + f"-{os.getpid()}")
    set_run_id(_neue_run_id)
    state.run_id = _neue_run_id
    audit("pipeline_start",
          {"aufgabe_hash": __import__("hashlib").sha256(
              state.aufgabe.encode()).hexdigest(),
           "aufgabe_kurz": state.aufgabe[:200],
           "modus": "phase_resume"},
          project_dir, project_name)
    rc = run_phase(project_name, state, state_ref)
    # Plan-Korrektur / V1: Unterblock-NO-GO
    # (rc=15) -> Planner nachziehen.
    if (rc == 15
            and state.phase_korrektur_zyklus < 1):
        print("[i] Unterblock-NO-GO. Plan-Korrektur "
              "wird versucht.")
        korrigiert = _phase_plan_korrektur(
            project_name, state, api_key)
        if korrigiert:
            state.phase_korrektur_zyklus += 1
            state_ref.clear()
            rc = run_phase(project_name, state,
                           state_ref)
    return (state, rc)

def _phase_main_w50_gate(
    project_name: str,
    phasen_text: str,
    force_new_phase: bool,
    vor: PhaseMainVorlaufErgebnis,
) -> int | None:
    """C1 aus _phase_main_pfad (3a-3c-1).

    W50-Gate (phase.yaml abgeschlossen) + force_new_phase-Audit.
    Liest vor.project_dir (Z.10737/10743). body[14]
    (historie) bleibt in _phase_main_pfad (M-144).
    Rueckgabe: int (18, 18, 65) bei Fehler, None bei ok.
    """
    project_dir = vor.project_dir

    _w50_pfad = _phase_yaml_pfad(project_name)
    _w50_vorher_id = "(keine)"
    if _w50_pfad.exists():
        try:
            _w50_daten = yaml.safe_load(
                _w50_pfad.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            print(f"[FAIL] phase.yaml nicht lesbar: {exc}. "
                  "Fail closed.")
            return 18
        if not isinstance(_w50_daten, dict):
            print("[FAIL] phase.yaml ist kein dict. "
                  "Fail closed.")
            return 18
        _w50_vorher_id = _w50_daten.get("phase_id", "?")
        _w50_aktiv = _w50_daten.get("phase_aktiv")
        if _w50_aktiv is False and not force_new_phase:
            _k_offene = sum(
                1 for _u in _w50_daten.get(
                    "phase_unterbloecke", []) or []
                if isinstance(_u, dict)
                and _u.get("status") in ("no_go", "failed"))
            print(f"[FAIL] Phase {_w50_vorher_id} ist "
                  f"abgeschlossen in phase.yaml "
                  f"({_k_offene} offene Reste). "
                  "Neuanlage verlangt --new-phase.")
            audit("phase_abgeschlossen_keine_neuanlage",
                  {"phase_id": _w50_vorher_id,
                   "offene_reste": _k_offene,
                   "aufgabe_kurz": phasen_text[:200]},
                  project_dir, project_name)
            return 65
    if force_new_phase:
        audit("phase_neuanlage_mit_flag",
              {"phase_id_vorher": _w50_vorher_id,
               "aufgabe_kurz": phasen_text[:200]},
              project_dir, project_name)
    return None

def _phase_main_pfad(
    project_name: str,
    phasen_text: str,
    state_ref: list[RunState],
    resume_force: bool = False,
    force_new_phase: bool = False,
) -> int:
    _vor = _phase_main_vorlauf(project_name)
    if isinstance(_vor, int):
        return _vor
    api_key = _vor.api_key
    config = _vor.config
    project_dir = _vor.project_dir
    agents = _vor.agents
    docs = _vor.docs
    file_whitelist = _vor.file_whitelist
    always_kat = _vor.always_kat
    optional_kat = _vor.optional_kat
    planner_modus = _vor.planner_modus
    planner_max_runden = _vor.planner_max_runden
    plan_vorhanden = _vor.plan_vorhanden
    if plan_vorhanden is not None:
        _st = _phase_main_plan_verarbeiten(
            project_name, phasen_text, state_ref,
            resume_force, _vor)
        if isinstance(_st, int):
            return _st
        state, rc = _st
        _phase_finish_aktiv(project_name, state, rc)
        return rc

    # Historien.
    historie = load_recent_commits(project_dir, n=10)

    # RunState bauen (analog _planner_main_pfad).
    # W50 (2026-10-18): Planner-Durchfall bei
    # abgeschlossener Phase verhindern.
    _w50_rc = _phase_main_w50_gate(
        project_name, phasen_text,
        force_new_phase, _vor)
    if _w50_rc is not None:
        return _w50_rc

    state = RunState(
        block_id=config.get("project", "unknown"),
        aufgabe=phasen_text,
        start_ts=datetime.now(UTC).isoformat(timespec="seconds"),
        docs=docs, agents=agents,
        always=always_kat, optional=optional_kat,
        file_whitelist=file_whitelist,
        api_key=api_key,
        budget=config.get("budget", {}),
        agent_docs=config.get("agent_docs", {}),
        project_dir=project_dir,
        project_name=project_name,
        planner_modus=planner_modus,
    )
    state.start_monotonic = time.monotonic()

    _neue_run_id = (
        datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        + f"-{os.getpid()}")
    set_run_id(_neue_run_id)
    state.run_id = _neue_run_id

    audit("pipeline_start",
          {"aufgabe_hash": __import__("hashlib").sha256(
              phasen_text.encode()).hexdigest(),
           "aufgabe_kurz": phasen_text[:200],
           "modus": "phase"},
          project_dir, project_name)

    # Planner Stufe 2, max planner_max_runden Runden.
    phase_plan_ok = False
    phase_id = ""
    phase_titel = ""
    unterbloecke: list[dict[str, Any]] = []
    # F-P2a-S5c-1 (alpha): editierter Plan aus
    # vorheriger Runde. Wenn gesetzt, wird in der
    # naechsten Runde kein Planner-Aufruf gemacht.
    letzter_vorschlag: (
        tuple[str, str, list[dict[str, Any]]] | None
    ) = None
    for runde in range(1, planner_max_runden + 1):
        state.planner_runden = runde
        print(f"\n[--- Planner-Runde {runde} (Stufe 2) ---]")
        audit("planner_start",
              {"runde": runde, "modus": "phase",
               "stufe": 2},
              project_dir, project_name)

        if letzter_vorschlag is not None:
            # F-P2a-S5c-1 (alpha): kein Planner-Aufruf.
            phase_id, phase_titel, unterbloecke = \
                letzter_vorschlag
            letzter_vorschlag = None
            aus_edit = True
        else:
            antwort = _planner_lauf(
                state, api_key, phasen_text,
                project_dir, project_name, historie,
                stufe=2)
            if antwort is None:
                print("[FAIL] Planner-Aufruf fehlgeschlagen. "
                      "Fail closed.")
                return 1

            # Kopf + Unterbloecke parsen (F1: Audit bei
            # Parse-Fehler, Runde zaehlt - F2).
            try:
                phase_id, phase_titel = \
                    _parse_phase_kopf(antwort)
                unterbloecke = _parse_phase_plan(antwort)
            except ValueError as exc:
                print(f"[i] Planner-Antwort nicht im "
                      f"Format: {exc}")
                state.letzter_plan_fehler = str(exc)
                audit("phase_plan_parse_failed",
                      {"runde": runde, "error": str(exc)},
                      project_dir, project_name)
                continue

            phase_plan_ok = True
            state.letzter_plan_fehler = ""
            audit("planner_vorschlag",
                  {"runde": runde,
                   "titel": phase_titel[:200],
                   "laenge": len(antwort),
                   "stufe": 2},
                  project_dir, project_name)
            print(f"[+] Phasenplan erhalten (Runde {runde}).")
            aus_edit = False

        # WEG-X-P19: Fail-closed bei oberflaechlichem
        # oder zu grossem Plan.
        # Plan-Dict fuer die Checks bauen (unterbloecke
        # ist eine Liste, die Checks erwarten dict-Form
        # mit phase_unterbloecke).
        _plan_fuer_check: dict[str, Any] = {
            "phase_unterbloecke": unterbloecke,
        }
        _mess_ok, _mess_fehler = _plan_ist_messungsbasiert(
            _plan_fuer_check)
        _praefix_zaehler = (
            _plan_ist_messungsbasiert_praefix_zaehler)
        if _praefix_zaehler > 0:
            audit("planner_plan_praefix_format_verwendet",
                  {"anzahl": _praefix_zaehler},
                  project_dir, project_name)
        if not _mess_ok:
            print("[FAIL] Plan nicht messungsbasiert. "
                  "Unterpunkte ohne anker:/neu:-Marker.")
            for _f in _mess_fehler[:10]:
                print(f"  - {_f}")
            print("[i] Auftrag praezisieren oder "
                  "'neu:'-Modus verwenden.")
            audit("planner_plan_unvollstaendig",
                  {"grund": "nicht_messungsbasiert",
                   "fehlend": _mess_fehler[:10]},
                  project_dir, project_name)
            return 18
        # W51b: aktion:neu gegen project_dir pruefen.
        _nfv_ok, _nfv_fehler, _nfv_grund = (
            _plan_ist_new_file_valide(
                _plan_fuer_check, project_dir))
        if not _nfv_ok:
            print("[FAIL] Plan nennt aktion:neu fuer "
                  "existierende Datei oder Pfad "
                  "ausserhalb project_dir.")
            for _f in _nfv_fehler[:10]:
                print(f"  - {_f}")
            _audit_kind = (
                "planner_new_file_auf_existierend"
                if _nfv_grund == "existiert"
                else "planner_pfad_ausserhalb_projekt")
            audit(_audit_kind,
                  {"grund": _nfv_grund,
                   "fehlend": _nfv_fehler[:10]},
                  project_dir, project_name)
            return 18
        _port_ok, _port_fehler = _plan_ist_portionierbar(
            _plan_fuer_check)
        if not _port_ok:
            print("[FAIL] Plan zu gross portioniert "
                  "(HART max 7 Unterpunkte pro Unterblock).")
            for _f in _port_fehler[:10]:
                print(f"  - {_f}")
            print("[i] Auftrag praezisieren oder "
                  "kleiner planen.")
            _hat_phase = any(
                _f.startswith("Phase: ")
                for _f in _port_fehler)
            _kind = ("planner_phase_zu_gross"
                     if _hat_phase
                     else "planner_plan_unvollstaendig")
            _grund = ("zu_gross_phase"
                      if _hat_phase else "zu_gross")
            audit(_kind,
                  {"grund": _grund,
                   "uebergross": _port_fehler[:10]},
                  project_dir, project_name)
            return 18

        # Anzeige (A4, A6, A8).
        if (antwort is not None
                and "PHASE-TEILUNG:" in antwort):
            print("[i] Planner hat die Phase "
                  "geteilt. Nach Abschluss Teil 2 "
                  "mit --new-phase starten.")
        print("\n" + "=" * 70)
        if aus_edit:
            print("=== PHASENPLAN (aus Edit) ===")
            print("[i] Plan aus vorherigem Edit, kein neuer "
                  "Planner-Aufruf.")
        else:
            print("=== PHASENPLAN ===")
        print(f"Phase: {phase_id} - {phase_titel}")
        for u in unterbloecke:
            n_up = len(u["unterpunkte"])
            n_rd = u["geschaetzte_runden"]
            # A6: Runden-Schaetzung markieren.
            print(f"{u['id']}: {u['titel']}  "
                  f"({n_up} Unterpunkte, "
                  f"~{n_rd} Runden — Schaetzung)")
            # A6: Anker/Marker pro Unterpunkt zeigen.
            for _p in (u.get("unterpunkte") or [])[:12]:
                if not isinstance(_p, str):
                    continue
                _kurz = _p if len(_p) <= 100 else _p[:97] + "..."
                print(f"  - {_kurz}")
            if n_up > 12:
                print(f"  ... und {n_up - 12} weitere.")
        print(f"(Runde {runde}/{planner_max_runden})")
        print("=" * 70)

        # Bestaetigung (A5, A6, A7: max 5 Versuche).
        for _versuch in range(5):
            try:
                wahl = input(
                    "[j] uebernehmen / [n] verwerfen / "
                    "[e] editieren (folgt in Kuerze) > "
                ).strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\n[*] Abbruch.")
                return 0
            if wahl in {"j", "ja", "y", "yes"}:
                # Speichern VOR RunState (S5-A4).
                plan_dict: dict[str, Any] = {
                    "phase_aktiv": True,
                    "phase_id": phase_id,
                    "phase_titel": phase_titel,
                    "phase_start_head": "",
                    "phase_erstellt_am": datetime.now(
                        UTC).isoformat(timespec="seconds"),
                    "phase_unterbloecke": [
                        {
                            "id": u["id"],
                            "titel": u["titel"],
                            "status": "pending",
                            "commit_paket": {},
                            "unterpunkte": u["unterpunkte"],
                            "geschaetzte_runden":
                                u["geschaetzte_runden"],
                        }
                        for u in unterbloecke
                    ],
                }
                try:
                    _phase_plan_speichern(
                        project_name, plan_dict)
                except Exception as exc:  # noqa: BLE001
                    print(f"[FAIL] phase.yaml speichern: {exc}")
                    return 1
                # W26: PLAN.md schreiben.
                _plan_md = _phase_plan_als_text(
                    phase_id, phase_titel, unterbloecke)
                _schreibe_plan(state, _plan_md)
                print(f"[i] Plan geschrieben: "
                      f"{_plan_pfad(state)}")
                # W27: Contracts schreiben.
                for _u in plan_dict.get(
                        "phase_unterbloecke", []):
                    if _schreibe_contract(state, _u):
                        print(f"[i] Contract: "
                              f"{_contract_pfad(state, _u.get('id', '?'))}")
                state.phase_id = phase_id
                state.phase_titel = phase_titel
                state.phase_unterbloecke = plan_dict[
                    "phase_unterbloecke"]
                state.phase_aktiv = True
                audit("phase_plan_erstellt",
                      {"phase_id": phase_id,
                       "unterbloecke": len(unterbloecke)},
                      project_dir, project_name)
                print(f"[+] Phase angelegt: "
                      f"{_phase_yaml_pfad(project_name)}")
                rc = run_phase(
                    project_name, state, state_ref)
                # P2b-4 / M8 + Resume-R6: Helper.
                _phase_finish_aktiv(
                    project_name, state, rc)
                return rc
            if wahl in {"e", "edit", "editieren"}:
                # F5: Runde sofort verbraucht.
                try:
                    bearbeitet, anzahl_geaendert = \
                        _phase_edit_modus(
                            phase_id, phase_titel,
                            unterbloecke)
                except (EOFError, KeyboardInterrupt):
                    print("\n[*] Abbruch.")
                    return 0
                # Roundtrip-Validierung (F2, A4).
                try:
                    als_text = _phase_plan_als_text(
                        phase_id, phase_titel, bearbeitet)
                    neuer_plan = _parse_phase_plan(als_text)
                except ValueError as exc:
                    print(f"[!] Edit ungueltig: {exc}")
                    state.letzter_plan_fehler = str(exc)
                    audit("phase_plan_parse_failed",
                          {"runde": runde, "error": str(exc),
                           "nach": "edit"},
                          project_dir, project_name)
                    # Edit verworfen, neue Runde.
                    break
                # Eigenschafts-Check A4.
                if neuer_plan != bearbeitet:
                    print("[FAIL] Roundtrip-Fehler. "
                          "Fail closed.")
                    return 1
                if anzahl_geaendert > 0:
                    audit("phase_plan_editiert",
                          {"runde": runde,
                           "unterbloecke": len(bearbeitet),
                           "geaenderte": anzahl_geaendert},
                          project_dir, project_name)
                # A9: state-Feld aktualisieren, nicht
                # state_ref manipulieren.
                state.phase_unterbloecke = bearbeitet
                # F-P2a-S5c-1 (alpha): fuer die naechste
                # Runde merken, dann inneren Loop verlassen.
                letzter_vorschlag = (
                    phase_id, phase_titel, bearbeitet)
                # Inneren Loop verlassen; aeusserer Loop
                # laeuft weiter (Runde verbraucht).
                break
            if wahl in {"n", "no", "nein"}:
                print("[i] Verworfen.")
                break
            print("[i] Unbekannte Eingabe. Nochmal.")
        if wahl in {"n", "no", "nein"}:
            break
        if wahl in {"e", "edit", "editieren"}:
            continue
        # 5 Versuche erschoepft.
        print("[i] Zu viele Fehleingaben. Naechste Runde.")
        continue

    # Max-Runden oder [n] ohne [j]: verworfen (F2).
    if not phase_plan_ok:
        print("[i] Kein gueltiger Phasenplan. Verworfen.")
    audit("phase_plan_verworfen",
          {"runden": state.planner_runden},
          project_dir, project_name)
    return 0


def _planner_main_pfad(
    project_name: str,
    roher_auftrag: str,
    state_ref: list[RunState],
) -> int:
    """Block P1: fuehrt den Planner aus und bestaetigt den Auftrag.

    Ablauf:
      1. Minimales Basis-Gate: Projekt-YAML + Schema + git clean.
      2. Planner-Aufruf (max 3 Runden).
      3. Parser: Auftrag, Rueckfrage oder ungueltig.
      4. Bestaetigung: [j] uebernehmen, [n] verwerfen, [e] editieren.
      5. Bei [j]: Auftrag geht an run_pipeline.

    Rueckgabe: rc der Kette oder rc des Planner-Pfads.
    """
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        print("[FAIL] DEEPSEEK_API_KEY fehlt. Fail closed.")
        return 1

    # Minimales Basis-Gate (SS-KERN).
    try:
        config = _lade_und_pruefe_projekt(project_name)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 1
    project_dir = Path(config.get("project_dir", str(Path.cwd()))).expanduser()
    if not project_dir.exists():
        print(f"[FAIL] project_dir fehlt: {project_dir}. Fail closed.")
        return 18

    # git status clean?
    try:
        _st = subprocess.run(
            ("git", "status", "--porcelain"),
            cwd=str(project_dir), capture_output=True, text=True,
            timeout=30, check=False, env=subprocess_env(),
        )
        if _st.returncode != 0 or _st.stdout.strip():
            print("[FAIL] Ziel-Repo nicht sauber (git status). Fail closed.")
            print(_st.stdout[:500] if _st.stdout else "")
            audit("planner_basis_gate_failed",
                  {"grund": "git_status_schmutzig"},
                  project_dir, project_name)
            return 18
    except (subprocess.TimeoutExpired, OSError) as exc:
        print(f"[FAIL] git status: {exc}. Fail closed.")
        return 18

    # Rollen + Docs laden.
    agents_dir = config.get("project_agents_dir")
    if not agents_dir:
        agents_dir = "/opt/werkstatt/agents"
    agents = load_agents(agents_dir)
    docs = load_docs(config.get("docs", {}), project_dir)
    file_whitelist = config.get("file_whitelist", [])

    if "planner" not in agents:
        print("[FAIL] Planner-Rolle nicht gefunden. Fail closed.")
        audit("planner_rolle_fehlt", {}, project_dir, project_name)
        return 18

    # Planner-Konfiguration lesen.
    _pcfg = config.get("planner", {}) or {}
    if not isinstance(_pcfg, dict):
        _pcfg = {}
    planner_modus = str(_pcfg.get("modus", "manual"))
    planner_max_runden = int(_pcfg.get("max_runden", 3))
    if planner_modus == "off":
        print("[i] Planner-Modus ist 'off'. Kein Planner-Lauf.")
        return 0


    # W48 (2026-10-18): Planner-Start bei existierender
    # phase.yaml sperren. _phase_plan_laden liefert None
    # bei phase_aktiv=False (Z. 1744-1752) und macht den
    # inaktiven Fall unsichtbar; deshalb direkter Leser.
    # A-W48-9b + A-W48-11: Neuanlage ausschliesslich
    # ueber --phase.
    _w48_pfad = _phase_yaml_pfad(project_name)
    if _w48_pfad.exists():
        try:
            _w48_roh = _w48_pfad.read_text(encoding="utf-8")
            _w48_daten = yaml.safe_load(_w48_roh) or {}
        except (OSError, yaml.YAMLError) as exc:
            print(f"[FAIL] phase.yaml nicht lesbar: {exc}. Fail closed.")
            audit("planner_phase_yaml_kaputt",
                  {"fehler": str(exc)[:200]},
                  project_dir, project_name)
            return 18
        if not isinstance(_w48_daten, dict):
            print("[FAIL] phase.yaml ist kein dict. Fail closed.")
            audit("planner_phase_yaml_kaputt",
                  {"fehler": "kein dict"},
                  project_dir, project_name)
            return 18
        _w48_aktiv = _w48_daten.get("phase_aktiv")
        _w48_pid = _w48_daten.get("phase_id", "?")
        _k_offene_w48 = sum(
            1 for _u in _w48_daten.get(
                "phase_unterbloecke", []) or []
            if isinstance(_u, dict)
            and _u.get("status") in ("no_go", "failed"))
        if _w48_aktiv is True:
            print(f"[FAIL] Aktive Phase {_w48_pid} in phase.yaml "
                  f"({_k_offene_w48} offene Reste). "
                  "--planner gesperrt, bitte "
                  "--phase nutzen.")
            audit("planner_blockiert_aktive_phase",
                  {"phase_id": _w48_pid},
                  project_dir, project_name)
            return 65
        if _w48_aktiv is False:
            print(f"[FAIL] Phase {_w48_pid} ist abgeschlossen "
                  f"in phase.yaml ({_k_offene_w48} offene "
                  "Reste). --planner gesperrt, bitte "
                  "--phase (Neuanlage) nutzen.")
            audit("planner_blockiert_phase_abgeschlossen",
                  {"phase_id": _w48_pid},
                  project_dir, project_name)
            return 65
        # _w48_aktiv ist None (Feld fehlt): Alt-Datei, durchlassen.



    # Historien.
    historie = load_recent_commits(project_dir, n=10)

    # RunState bauen (minimal, analog run_pipeline).
    always_kat, optional_kat = build_catalog(
        config, project_dir)
    state = RunState(
        block_id=config.get("project", "unknown"),
        aufgabe=roher_auftrag,
        start_ts=datetime.now(UTC).isoformat(timespec="seconds"),
        docs=docs, agents=agents,
        always=always_kat, optional=optional_kat,
        file_whitelist=file_whitelist,
        api_key=api_key,
        budget=config.get("budget", {}),
        agent_docs=config.get("agent_docs", {}),
        project_dir=project_dir,
        project_name=project_name,
        planner_modus=planner_modus,
    )
    state.start_monotonic = time.monotonic()
    state_ref.append(state)

    # Run-ID setzen (fuer Audit).
    _neue_run_id = (
        datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        + f"-{os.getpid()}")
    set_run_id(_neue_run_id)
    state.run_id = _neue_run_id

    audit("pipeline_start",
          {"aufgabe_hash": __import__("hashlib").sha256(
              roher_auftrag.encode()).hexdigest(),
           "aufgabe_kurz": roher_auftrag[:200],
           "modus": "planner"},
          project_dir, project_name)

    # Planner-Lauf mit max 3 Runden (SS5).
    vorschlag_text: str | None = None
    for runde in range(1, planner_max_runden + 1):
        state.planner_runden = runde
        print(f"\n[--- Planner-Runde {runde} ---]")
        audit("planner_start",
              {"runde": runde, "modus": planner_modus},
              project_dir, project_name)

        antwort = _planner_lauf(
            state, api_key, roher_auftrag,
            project_dir, project_name, historie)
        if antwort is None:
            print("[FAIL] Planner-Aufruf fehlgeschlagen. Fail closed.")
            return 1

        parsed = parse_planner_reply(antwort)
        if parsed["art"] == "auftrag":
            vorschlag_text = antwort.strip()
            audit("planner_vorschlag",
                  {"runde": runde,
                   "praefix": parsed.get("praefix", ""),
                   "titel": parsed.get("titel", "")[:200],
                   "laenge": len(vorschlag_text)},
                  project_dir, project_name)
            print(f"[+] Planner-Vorschlag erhalten (Runde {runde}).")
            break
        if parsed["art"] == "rueckfrage":
            # Rueckfrage-Loop (TT6): dem Menschen zeigen, Antwort
            # holen, als Kontext weitergeben.
            print("\n=== RUECKFRAGE DES PLANNERS ===")
            print(parsed.get("frage", ""))
            print("=" * 70)
            try:
                antwort_mensch = input(
                    "Deine Antwort (leer = abbrechen): ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n[*] Abbruch.")
                return 0
            if not antwort_mensch:
                print("[i] Leere Antwort. Planner-Runde abgebrochen.")
                continue
            roher_auftrag = (
                roher_auftrag
                + "\n\n[Antwort des Menschen auf Rueckfrage]\n"
                + antwort_mensch)
            continue
        # art == ungueltig
        print("[i] Planner-Antwort nicht im Format. "
              "Neue Runde.")
        audit("planner_ungueltig",
              {"runde": runde,
               "laenge": len(antwort),
               "kopf": antwort.strip()[:200]},
              project_dir, project_name)

    if vorschlag_text is None:
        # Max-Runden erreicht (TT6/SS5).
        print("\n" + "=" * 70)
        print("Planner kann nicht formulieren.")
        print("[j] selbst formulieren (geht direkt an die Pipeline)")
        print("[n] abbrechen")
        print("=" * 70)
        try:
            wahl = input("Deine Wahl: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n[*] Abbruch.")
            return 0
        if wahl in {"j", "ja", "y", "yes"}:
            try:
                eigener = input("Auftrag: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n[*] Abbruch.")
                return 0
            if not eigener:
                print("[FAIL] Leerer Auftrag. Fail closed.")
                return 1
            audit("planner_uebersprungen",
                  {"grund": "max_runden",
                   "quelle": "mensch_eigener_auftrag"},
                  project_dir, project_name)
            return run_pipeline(project_name, eigener, state_ref)
        print("[i] Abgebrochen durch Mensch.")
        audit("planner_abgebrochen",
              {"runden": state.planner_runden},
              project_dir, project_name)
        return 1

    # Bestaetigung.
    print("\n" + "=" * 70)
    print("=== PLANNER-VORSCHLAG ===")
    print(vorschlag_text)
    print("=" * 70)
    print("[j] uebernehmen / [n] verwerfen / [e] editieren")
    try:
        wahl = input("Deine Wahl: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n[*] Abbruch.")
        return 0

    if wahl in {"j", "ja", "y", "yes"}:
        audit("planner_bestaetigt",
              {"wahl": "j", "runden": state.planner_runden},
              project_dir, project_name)
        return run_pipeline(project_name, vorschlag_text, state_ref)

    if wahl in {"e", "edit", "editieren"}:
        try:
            bearbeitet = input(
                "Editierten Auftrag eingeben: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[*] Abbruch.")
            return 0
        if not bearbeitet:
            print("[FAIL] Leerer Auftrag. Fail closed.")
            return 1
        audit("planner_bestaetigt",
              {"wahl": "e", "runden": state.planner_runden},
              project_dir, project_name)
        return run_pipeline(project_name, bearbeitet, state_ref)

    # [n] verwerfen
    print("[i] Verworfen.")
    audit("planner_verworfen",
          {"runden": state.planner_runden},
          project_dir, project_name)
    return 0


def _validate_new_phase_args(args: list[str]) -> int | None:
    """W50: prueft --new-phase ohne --phase.

    Rueckgabe: 65 bei Fehler, None sonst.
    Reine Argument-Pruefung, ohne Sicherheits-
    Seiteneffekte. Der root-Check in main() bleibt
    davor, weil er unabhaengig von den Args greift.
    """
    if "--new-phase" in args and "--phase" not in args:
        print("[FAIL] --new-phase verlangt --phase.")
        return 65
    return None


def main() -> int:

    """CLI-Einstieg.

    Nutzung:
      pipeline.py --project <name> "<Block-Beschreibung>"

    Erwartet DEEPSEEK_API_KEY in der Umgebung.
    Liest die Projekt-Konfiguration aus /opt/werkstatt/projects/<name>.yaml.
    Darf NICHT als root laufen (Audit-Rechte, Git-Rechte).
    """
    # Guard: nicht als root. Sonst Exit 66.
    # Die Pipeline laeuft als Projekt-User (z.B. security-ai, xyapp).
    # Als root wuerden Audit-Logs root:root gehoeren und der
    # Service-User koennte sie nicht mehr lesen (SECURITY_REVIEW_LOG Punkt 12).
    #
    # Auflage 2085: primär os.getuid() == 0 pruefen (deterministisch,
    # nicht von Env abhaengig). getpass.getuser() nur ergaenzend und
    # in try/except, weil es bei fehlenden Env-Variablen fehlschlagen
    # kann (KeyError/OSError). Bei Fehler: nicht abstuerzen, sondern
    # nur informieren.
    if os.getuid() == 0:
        print("[FAIL] Pipeline darf NICHT als root laufen "
              "(os.getuid() == 0).")
        print("[FAIL] Aufruf: runuser -u <projekt-user> -- ...")
        print("[FAIL] Beispiel: runuser -u security-ai -- ...")
        return 66
    import getpass
    try:
        aktueller_user = getpass.getuser()
    except (KeyError, OSError) as exc:
        print(f"[WARN] getpass.getuser() fehlgeschlagen: {exc}")
        aktueller_user = ""
    if aktueller_user == "root":
        print("[FAIL] Pipeline darf NICHT als root laufen "
              "(getpass.getuser() == 'root').")
        print("[FAIL] Aufruf: runuser -u <projekt-user> -- ...")
        return 66

    args = sys.argv[1:]
    project_name: str | None = None

    # Block P2a: Konflikt-Check (F1, P2a-S5c-A1).
    # --phase und --planner sind exklusiv. Kein Audit
    # (kein pipeline_start, kein RunState, keine
    # Projekt-Bindung).
    if "--phase" in args and "--planner" in args:
        print("[FAIL] --phase und --planner "
              "nicht kombinierbar.")
        return 65
    # --resume-force verlangt --phase (Auflage A1).
    if "--resume-force" in args and "--phase" not in args:
        print("[FAIL] --resume-force verlangt --phase.")
        return 65

    # W50: --new-phase verlangt --phase.
    _rc_np = _validate_new_phase_args(args)
    if _rc_np is not None:
        return _rc_np

    # Block P2a: --phase-Pfad. Reihenfolge: VOR --planner
    # (P2a-S5b-A1). Beide Bedingungen sind mit args[2]
    # exklusiv.
    if (len(args) >= 4 and args[0] == "--project"
            and args[2] == "--phase"):
        project_name = args[1].strip()
        phasen_text = args[3].strip()
        # --resume-force nur mit --phase (Auflage A1).
        _resume_force = "--resume-force" in args
        if not project_name:
            print("[FAIL] Leerer Projektname.")
            return 65
        if not phasen_text:
            print("[FAIL] Leerer Phasentext.")
            return 65
        phase_state_ref: list[RunState] = []
        rc = 1
        try:
            rc = _phase_main_pfad(
                project_name, phasen_text, phase_state_ref,
                resume_force=_resume_force,
                force_new_phase=("--new-phase" in args))
        except KeyboardInterrupt:
            print("\n[*] Abbruch durch Strg+C.")
            rc = 130
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] Unerwarteter Fehler: {exc}")
            import traceback
            traceback.print_exc()
            rc = 99
        finally:
            if phase_state_ref:
                try:
                    _pipeline_ende(
                        phase_state_ref[0],
                        phase_state_ref[0].project_dir,
                        phase_state_ref[0].project_name,
                        rc, "phase_exit")
                except Exception:  # noqa: BLE001
                    print("[WARN] pipeline_ende fehlgeschlagen.")
        return rc

    # Block P1: --planner-Pfad.
    # Format: pipeline.py --project <name> --planner "<roher Auftrag>"
    if (len(args) >= 4 and args[0] == "--project"
            and args[2] == "--planner"):
        project_name = args[1].strip()
        roher_auftrag = args[3].strip()
        if not project_name:
            print("[FAIL] Leerer Projektname.")
            return 65
        if not roher_auftrag:
            print("[FAIL] Leerer Auftrag.")
            return 65
        state_ref: list[RunState] = []
        rc = 1
        try:
            rc = _planner_main_pfad(
                project_name, roher_auftrag, state_ref)
        except KeyboardInterrupt:
            print("\n[*] Abbruch durch Strg+C.")
            rc = 130
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] Unerwarteter Fehler: {exc}")
            import traceback
            traceback.print_exc()
            rc = 99
        finally:
            if state_ref:
                try:
                    _pipeline_ende(
                        state_ref[0],
                        state_ref[0].project_dir,
                        state_ref[0].project_name,
                        rc, "planner_exit")
                except Exception:  # noqa: BLE001
                    print("[WARN] pipeline_ende fehlgeschlagen.")
        return rc

    if args and args[0] == "--project":
        if len(args) < 3:
            print("[FAIL] --project braucht einen Namen und eine Aufgabe.")
            print('Nutzung: pipeline.py --project <name> "<Block-Beschreibung>"')
            return 64
        project_name = args[1].strip()
        aufgabe = args[2].strip()
    else:
        print("[FAIL] --project <name> fehlt.")
        print('Nutzung: pipeline.py --project <name> "<Block-Beschreibung>"')
        print('        pipeline.py --project <name> --planner "<roher Auftrag>"')
        return 64

    if not project_name:
        print("[FAIL] Leerer Projektname.")
        return 65
    if not aufgabe:
        print("[FAIL] Leere Block-Beschreibung.")
        return 65

    state_ref = []
    rc = 1
    try:
        rc = run_pipeline(project_name, aufgabe, state_ref)
    except KeyboardInterrupt:
        print("\n[*] Abbruch durch Strg+C.")
        rc = 130
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] Unerwarteter Fehler: {exc}")
        import traceback
        traceback.print_exc()
        rc = 99
    finally:
        if state_ref:
            # Auflage 2183-P4-Log2: zentraler Endlog.
            try:
                _grund = (
                    "user_interrupt" if rc == 130
                    else "unhandled_exception" if rc == 99
                    else "run_pipeline_exit")
                _pipeline_ende(
                    state_ref[0],
                    state_ref[0].project_dir,
                    state_ref[0].project_name,
                    rc, _grund)
            except Exception:  # noqa: BLE001
                # Fehler im Endlog darf den Exit-Code
                # nicht ueberschreiben (P6).
                print("[WARN] pipeline_ende fehlgeschlagen.")
            # Agent-Memory A3: Projekt-Memory aktualisieren.
            # TT2: nach pipeline_ende, try/except, kein Fail-closed.
            try:
                _projekt = (state_ref[0].project_name
                            if state_ref else "")
                if _projekt:
                    import subprocess as _sp
                    _sp.run(
                        (sys.executable,
                         "/opt/werkstatt/werkstatt_aggregate.py",
                         _projekt, "--fenster-tage", "1"),
                        capture_output=True, text=True,
                        timeout=30, check=False)
            except Exception as exc:  # noqa: BLE001
                print(f"[WARN] Aggregator: {exc}")
                try:
                    audit("aggregator_failed",
                          {"fehler": str(exc)},
                          state_ref[0].project_dir,
                          state_ref[0].project_name)
                except Exception:  # noqa: BLE001
                    print("[WARN] Audit aggregator_failed "
                          "fehlgeschlagen.")
    return rc


if __name__ == "__main__":
    sys.exit(main())
