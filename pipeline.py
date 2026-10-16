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
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

import requests
import yaml

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
SUBPROCESS_TIMEOUT = 60
COVERAGE_MIN_PCT = 80.0
AUDIT_DIR_NAME = "audit-logs"
AUDIT_FILE_NAME = "agent-pipeline.jsonl"



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

HARD_RULES_BASE = """
## HARD RULES (universell, verbindlich)

HR1. Faktenlage vor Meinung.
     Keine API aus dem Gedaechtnis. Keine Datei-Inhalte annehmen.
     Keine Zahlen schaetzen. Immer messen, nicht erinnern.

HR7. Kategorie 3: Code VOR Ausfuehrung an den Reviewer.
     Kein Improvisieren nach NO-GO.

HR8. Doku-Pflege ist Pflicht.
     Ein Commit ohne Doku-Nachzug ist ein unvollstaendiger Commit.

HR9. Patch-Skripte > ~3 KB in /tmp schreiben, dort
     verifizieren, dann ausfuehren. Kein Heredoc in die
     interaktive Shell.

HR10. Nach jedem abgeschlossenen Block: Update an den Menschen.
"""


HARD_RULES_REVIEWER = """
## HARD RULES (Rolle: Reviewer)

R1. Verlange gemessene Zahlen. Der MESSWERTE-Block
    ist die Quelle.

R2. Vergleiche Commit-Message-Zahlen mit dem
    MESSWERTE-Block. Abweichung: COMMIT-NO-GO.

R3. Kein Selbst-Messen. Der Builder hat die
    Zieldatei-Ausschnitte. Wenn du Zweifel hast:
    COMMAND: RUN read_file <pfad>.
    Sonst: vertraue der Werkstatt-Mechanik
    (Anker-Pruefung bei apply_code_patches).

R4. Pruefe Pflichtabschnitte der Commit-Message
    (Ausgangslage, Aenderung, Tests, Verifikation,
    Reviewed).

R5. Pruefe Patch-Struktur (PATCH-BEGINN/ENDE,
    anker/ersatz, ersatz != anker).

R6. Du lieferst entweder COMMAND: RUN ODER ein
    Verdict (GO/NO-GO/ESKALATION), niemals beides.
    (Lehre aus Probebetrieb 12.)

R7. Pruefe jeden Patch-Anker gegen den
    GEMESSENER INHALT-Block. Drei Stufen:
    1. Anker woertlich enthalten: OK.
    2. Anker nicht woertlich, aber einer
       dieser Faelle trifft zu:
         a) der GEMESSENER INHALT-Block
            enthaelt den KUERZUNGS-MARKER
            "[... Gesamtlimit erreicht ...]"
            oder
            "[... gekuerzt, N Zeichen
            weggelassen ...]",
         b) die +2-Spaces-verschobene
            Variante des Ankers ist
            woertlich enthalten
            (Einrueckungs-Toleranz,
            Auflage 2165).
       Dann: COMMAND: RUN read_file <pfad>
       anfordern. Kein NO-GO.
    3. Anker in keiner Variante auffindbar:
       NO-GO mit Verweis auf den Patch.
       AUSNAHME: Wenn Stufe 2a oder 2b
       einschlaegig war, bleibt es bei
       COMMAND: RUN read_file.
"""


HARD_RULES_BUILDER = """
## HARD RULES (Rolle: Builder)

B1. Der MESSWERTE-Block ist die EINZIGE Quelle fuer
    Zahlen in der Commit-Message. Verwende keine
    anderen Zahlen.

B2. Wenn eine Zahl nicht im MESSWERTE-Block steht:
    schreibe "nicht gemessen".

B3. Erfinden von Zahlen ist ein HR1-Verstoss.

B4. Du bist kein Messender. Die Werkstatt ist der
    Messende. Uebernimm die Werte aus dem
    MESSWERTE-Block.

B5. Du darfst COMMAND: RUN liefern, um Messungen
    anzufordern (Builder COMMAND-Loop).

B6. Ein Ausfuehrungsblock pro logischer Einheit.
    Kein Vorab-Stapeln mehrerer unabhaengiger
    Bloecke.

B7. Vor cat > auf eine angeblich neue Datei:
    git ls-files <pfad> UND git status --porcelain
    pruefen.

B8. Nach jedem Patch einer bestehenden Datei:
    assert text.count(anker) == 1.
    Bei count != 1: STOP.

B9. Nach jedem Patch, der Tests betrifft:
    pytest --collect-only -q <datei> VOR
    pytest -q <datei>.

B10. Wenn ein Anker nicht im Zieldatei-Ausschnitt
     steht: "kein Patch fuer diese Datei".
     Kein Erfinden.
"""


HARD_RULES_TEST_GENERATOR = """
## HARD RULES (Rolle: Test-Generator)

T1. Beschreibe Test-Vorschlaege. Fuehre sie NICHT aus.

T2. Keine Zahlen erfinden. Zahlen nur, wenn sie im
    MESSWERTE-Block stehen.

T3. Keine Datei schreiben. Nur Text.

T4. Keine eigene Meinung zum Code.
"""


# Mapping Agent-Name -> Rollen-Regeln.
# coverage und chaos sind No-LLM-Rollen und rufen
# build_system_prompt nicht auf. Deshalb kein Eintrag.
# Auflage 2183 B + Kurskorrektur 2026-10-14 (Block 2).
# Aufgabe: Unterstuetzung fuer den Builder-Agenten.
# Diagnose, woran es scheitert + wie besser.
# Adressat: Builder-Agent.
HARD_RULES_SOLVER = """
S1. Du bist der Solver. Du unterstuetzt den
    Builder-Agenten, nicht den Reviewer, nicht
    den Menschen, nicht den Werkstatt-Chat.
S2. Du bekommst zwei NO-GO-Runden und die
    zugehoerigen CODE-ENTWUERFE aus der
    code_entwurf_historie.
S3. Du antwortest mit GENAU EINER Diagnose
    (siehe S4).
S4. Format pro Diagnose:
    DIAGNOSE: GLEICHER_FEHLER -> KANDIDATEN: (Liste)
    DIAGNOSE: ANDERER_FEHLER  -> PRAEZISIERTER_AUFTRAG: <Text>
    DIAGNOSE: WIDERSPRUCH     -> RUECKSPIEL: <Text>
    DIAGNOSE: UNKLAR          -> ESKALATION: <Text>
S5. Du darfst Code-Empfehlungen als Skizze
    geben (Anker, Struktur, Aufruf). Du
    lieferst KEINE fertigen Skripte, KEINE
    vollstaendigen Dateien. Der Builder-Agent
    baut die Umsetzung.
S6. Du bist kein Messender. Du forderst keine
    Messungen an. Du verlangst keine
    Dateizugriffe. Was du wissen musst, steht
    im Prompt.
S7. Wenn du nicht entscheiden kannst: UNKLAR.
    Das ist kein Fehler, sondern eine gueltige
    Diagnose. UNKLAR fuehrt zur Eskalation an
    den Werkstatt-Chat. Du richtest dich nicht
    direkt an den Menschen.
S8. Adressat ist der Builder-Agent. Du
    bewertest nicht. Du beschreibst, woran es
    scheitert, und empfiehlst, wie besser.
    Kein GO/NO-GO. Keine Aussage ueber die
    Qualitaet des Ergebnisses.
S9. Du siehst dieselbe Projekt-Doku wie der
    Reviewer-Agent. Nutze sie, um zu loesen.
"""
# Auflage 2183 Block 3: Solver sieht dieselbe
# Projekt-Doku wie der Reviewer.


# =====================================================================
# Planner-Regeln, Stufe 1 (Auftrags-Uebersetzer).
# Siehe P2a-A11, P2a-S4-A1. Wortgleich zu vorher.
# =====================================================================
HARD_RULES_PLANNER_STUFE1 = """
P1. Du bist der Planner. Du formulierst Auftraege,
    du baust nichts.
P2. Deine Eingabe sind der rohe Auftrag des
    Menschen, die konfigurierte Projekt-Doku und
    die letzten 10 Commits im Ziel-Repo.
P3. Du antwortest mit GENAU EINEM Auftrag ODER
    GENAU EINER Rueckfrage. Kein anderer Text.
P4. Der Auftrag muss praezise sein:
    Datei(en), Aenderung, Erfolgskriterium.
P5. Du baust nicht, committest nicht, reviewst
    nicht. Du sprichst keine Verdicts aus.
P6. Bei Unklarheit: Formuliere eine RUECKFRAGE
    statt eines Auftrags.
P7. Auftrag-Format ist bindend:
      Block: <praefix> - <Kurztitel>
      Ziel:
        <Was soll gebaut werden?>
      Vorgehen:
        1. <Schritt>
      Erfolgskriterium:
        - <Kriterium>
    Praefix-Werte: feat, fix, docs, refactor, test.
P8. Rueckfrage-Format ist bindend:
      RUECKFRAGE:
        <Frage>
P9. Das Format ist kein Vorschlag. Bei Verstoss
    gegen P7 oder P8 wird der Auftrag verworfen
    und du wirst erneut gerufen (max 3 Runden).
"""

# Alias aus Kompatibilitaet: zeigt auf STUFE1
# (= Default). STUFE2 wird vom Aufrufer explizit
# gewaehlt (build_system_prompt stufe=2).
# Siehe P2a-A11, P2a-S4.
HARD_RULES_PLANNER = HARD_RULES_PLANNER_STUFE1

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
#          "gegen P10-P14" (Stufe-2-Format).
# Unveraendert: P2, P5, P6, P8.
# Neu: P10-P14.
# =====================================================================
HARD_RULES_PLANNER_STUFE2 = """
P1'. Du bist der Planner. Du formulierst Auftraege
     oder Phasenplaene, du baust nichts.
P2. Deine Eingabe sind der rohe Auftrag des
    Menschen, die konfigurierte Projekt-Doku und
    die letzten 10 Commits im Ziel-Repo.
P3'. Du antwortest mit GENAU EINEM Phasenplan
     (Format PHASE/UNTERBLOCK, siehe P10-P14)
     ODER GENAU EINER Rueckfrage. Kein anderer
     Text.
P4'. Jeder Unterblock muss praezise sein:
     betroffene Datei(en), Aenderung,
     Erfolgskriterium.
P5. Du baust nicht, committest nicht, reviewst
    nicht. Du sprichst keine Verdicts aus.
P6. Bei Unklarheit: Formuliere eine RUECKFRAGE
    statt eines Phasenplans.
P8. Rueckfrage-Format ist bindend:
      RUECKFRAGE:
        <Frage>
P9'. Das Format ist kein Vorschlag. Bei Verstoss
     gegen P10-P14 wird der Phasenplan verworfen
     und du wirst erneut gerufen (max 3 Runden).
P10. Phase-Kopf-Format ist bindend:
       PHASE: <id> - <Titel>
     Der Trenner " - " (Leerzeichen, Minus,
     Leerzeichen) ist Pflicht.
P11. Unterblock-Format ist bindend:
       UNTERBLOCK: U<n> - <Titel>
       Unterpunkte:
         - <Punkt>
         - <Punkt>
       Geschaetzte Runden: <n>
     n ist monoton aufsteigend ab 1 (U1, U2, ...).
     Geschaetzte Runden ist int >= 1.
P12. Keine erfundenen Unterpunkte. Nur, was aus
     dem Phasentext oder dem Projektstand
     ableitbar ist.
P13. geschaetzte_runden konservativ (lieber hoeher
     als zu niedrig).
P14. Keine Prosa ausserhalb des Formats. Keine
     Meta-Kommentare. Kein "Hier ist der Plan".
"""

HARD_RULES_BY_ROLE = {
    "reviewer": HARD_RULES_REVIEWER,
    "builder": HARD_RULES_BUILDER,
    "test_generator": HARD_RULES_TEST_GENERATOR,
}
HARD_RULES_BY_ROLE["solver"] = HARD_RULES_SOLVER
HARD_RULES_BY_ROLE["planner"] = HARD_RULES_PLANNER

# Auflage 2041: Groessenlimits fuer das Messprotokoll.
MAX_PROTOKOLL_PER_COMMAND = 10_000
MAX_PROTOKOLL_TOTAL = 100_000

# Auflage 2042: erlaubte Quellen-Marker fuer COMMAND-Audits.
ERLAUBTE_QUELLEN = {
    "reviewer", "builder", "test_generator",
    "pipeline_auto", "reviewer_command",
}



WERKSTATT_HOME = Path("/opt/werkstatt")
PROJECTS_DIR = WERKSTATT_HOME / "projects"


class BudgetExhausted(Exception):
    """Wird geworfen, wenn das LLM-Budget erschoepft ist."""


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
_AUDIT_KINDS_BEKANNT = frozenset({
    "anker_einrueckung_korrigiert",
    "auftrag_bereits_erfuellt",
    "basis_gate_rot",
    "builder_anker_fehler",
    "builder_command_deadlock",
    "builder_command_executed",
    "builder_deadlock_anker_nicht_gemessen",
    "builder_prompt_gebaut",
    "builder_reply_erhalten",
    "builder_wirkungsloser_patch",
    "code_patches_apply",
    "code_patches_leer",
    "command_executed",
    "command_rejected",
    "commit_applied",
    "commit_paket_leer",
    "commit_review",
    "phase_abgebrochen",
    "phase_budget_ende",
    "phase_commit_paket_gesammelt",
    "phase_commit_paket_leer",
    "phase_gesamt_review",
    "phase_plan_editiert",
    "phase_plan_erstellt",
    "phase_plan_korrektur_failed",
    "phase_plan_korrektur_start",
    "phase_plan_parse_failed",
    "phase_finish",
    "phase_finish_warnung",
    "phase_plan_verworfen",
    "phase_resume_erkannt",
    "phase_rollback",
    "phase_start_head_gesetzt",
    "phase_unterblock_ende",
    "phase_unterblock_start",
    "pipeline_approved",
    "pipeline_ende",
    "pipeline_erfolg_ohne_commit",
    "pipeline_rejected",
    "pipeline_start",
    "recovery_basis_gate",
    "recovery_basis_gate_nach_apply",
    "recovery_builder_command_deadlock",
    "recovery_eskalation",
    "recovery_no_go",
    "review_round",
    "reviewer_run_solver",
    "rollback_fail_closed",
    "run_phase_ende",
    "run_phase_start",
    "solver_befund",
    "solver_befund_verworfen",
    "solver_failed",
    "solver_run_duplicate",
    "solver_trigger",
    "solver_trigger_c",
})


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


def _ap_audit_haeufigkeit() -> dict[str, int]:
    """Zaehlt bekannte audit_kinds in den Werkstatt-Audit-Logs.

    Wird nur fuer Sortierung genutzt (VV1: die drei mit den
    meisten Treffern). Fehlende Logs = alle Zaehler 0.
    """
    haeufig: dict[str, int] = {k: 0 for k in _AUDIT_KINDS_BEKANNT}
    logdir = Path("/opt/werkstatt/audit-logs")
    if not logdir.exists():
        return haeufig
    for jf in sorted(logdir.glob("agent-pipeline-*.jsonl")):
        try:
            for line in jf.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                k = d.get("kind")
                if k in haeufig:
                    haeufig[k] += 1
        except OSError:
            continue
    return haeufig


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

def _parse_phase_kopf(text: str) -> tuple[str, str]:
    """Parst den PHASE-Kopf (Stufe 2).

    Rueckgabe: (phase_id, phase_titel).

    Fehler immer als ValueError mit klarer Regel.

    Auflage P2a-S5a-A5: z.strip() beim Erkennen
    toleriert fuehrende Whitespaces vor "PHASE:"
    (LLM-Replies mit Einrueckung).
    Auflage P2a-S5a-A6: split(" - ", 1) — maxsplit=1,
    damit ein Titel, der " - " enthaelt, nicht
    zerfaellt.
    """
    zeilen = text.splitlines()
    kopf_idx: int | None = None
    for i, z in enumerate(zeilen):
        if z.strip().startswith("PHASE:"):
            kopf_idx = i
            break
    if kopf_idx is None:
        raise ValueError("kein PHASE:-Kopf gefunden")
    kopf = zeilen[kopf_idx].strip()[len("PHASE:"):].strip()
    if " - " not in kopf:
        raise ValueError("Phase: Trenner '-' fehlt")
    phase_id, phase_titel = kopf.split(" - ", 1)
    if not phase_id.strip():
        raise ValueError("Phase: id leer nach strip()")
    if not phase_titel.strip():
        raise ValueError("Phase: titel leer nach strip()")
    return phase_id.strip(), phase_titel.strip()


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

def _parse_phase_plan(text: str) -> list[dict[str, Any]]:
    """Parst einen Phasentext in Unterbloecke.

    Eingabeformat (verbindlich):
      PHASE: <id> - <Titel>
      UNTERBLOCK: U1 - <Titel>
      Unterpunkte:
        - <Punkt>
        - <Punkt>
      Geschaetzte Runden: 2

    Rueckgabe: Liste von dicts, je Eintrag:
      {"id": "U1", "titel": "...",
       "unterpunkte": ["...", "..."],
       "geschaetzte_runden": 2}

    Der PHASE-Kopf wird validiert, aber NICHT zurueckgegeben
    (Auflage P2a-S2-A1). Den PHASE-Kopf liest der Aufrufer
    separat.

    Fehler immer als ValueError mit Regel + id/Position.
    """
    # PHASE-Kopf validieren ueber _parse_phase_kopf
    # (Auflage P2a-S5a-A9: ohne Zuweisung, damit
    # keine unbenutzten Variablen entstehen).
    _parse_phase_kopf(text)
    zeilen = text.splitlines()
    # Zweiter splitlines() bewusst: _parse_phase_kopf
    # gibt die Position nicht zurueck (P2a-S5a-A1).
    # Text ist kurz (<100 Zeilen).
    kopf_idx = next(
        i for i, z in enumerate(zeilen)
        if z.strip().startswith("PHASE:")
    )

    # 2. Unterbloecke ab kopf_idx+1 sammeln.
    unterbloecke: list[dict[str, Any]] = []
    i = kopf_idx + 1
    pos = 0
    while i < len(zeilen):
        roh = zeilen[i]
        stripped = roh.strip()
        if not stripped:
            i += 1
            continue
        if not stripped.startswith("UNTERBLOCK"):
            i += 1
            continue
        pos += 1
        # Kopf ungueltig, wenn nicht exakt "UNTERBLOCK: U<n> - <Titel>"
        if not stripped.startswith("UNTERBLOCK:"):
            raise ValueError(
                f"Unterblock {pos} (Zeile {i+1}): Kopf ungueltig: "
                f"{roh!r}")
        rest = stripped[len("UNTERBLOCK:"):].strip()
        if " - " not in rest:
            raise ValueError(
                f"Unterblock {pos} (Zeile {i+1}): Kopf ungueltig: "
                f"{roh!r}")
        id_teil, titel_teil = rest.split(" - ", 1)
        id_roh = id_teil.strip()
        titel_roh = titel_teil.strip()
        erwartete_id = f"U{pos}"
        if id_roh != erwartete_id:
            raise ValueError(
                f"U{pos}: id nicht mit 'U{pos}' ueberein "
                f"(gefunden: {id_roh!r})")
        if not titel_roh:
            raise ValueError(f"U{pos}: titel leer nach strip()")

        # Sektion Unterpunkte.
        i += 1
        while i < len(zeilen) and not zeilen[i].strip():
            i += 1
        if i >= len(zeilen) or \
                zeilen[i].strip() != "Unterpunkte:":
            raise ValueError(
                f"U{pos}: Reihenfolge Unterpunkte/Runden verletzt")
        i += 1
        unterpunkte: list[str] = []
        while i < len(zeilen):
            zp = zeilen[i]
            sp = zp.strip()
            if not sp:
                i += 1
                continue
            if sp.startswith("- "):
                punkt = sp[len("- "):].strip()
                if not punkt:
                    raise ValueError(
                        f"U{pos}: unterpunkt leer nach strip()")
                unterpunkte.append(punkt)
                i += 1
                continue
            if sp.startswith("Geschaetzte Runden:"):
                break
            # Fremdzeile zwischen Sektionen.
            raise ValueError(
                f"U{pos}: Reihenfolge Unterpunkte/Runden verletzt")
        if not unterpunkte:
            raise ValueError(f"U{pos}: unterpunkte fehlen")

        # Sektion Geschaetzte Runden.
        while i < len(zeilen) and not zeilen[i].strip():
            i += 1
        if i >= len(zeilen) or \
                not zeilen[i].strip().startswith("Geschaetzte Runden:"):
            raise ValueError(f"U{pos}: geschaetzte_runden fehlt")
        runden_roh = zeilen[i].strip()[len("Geschaetzte Runden:"):].strip()
        try:
            n = int(runden_roh)
        except ValueError as exc:
            raise ValueError(
                f"U{pos}: geschaetzte_runden ungueltig: "
                f"{runden_roh!r}") from exc
        if str(n) != runden_roh:
            raise ValueError(
                f"U{pos}: geschaetzte_runden ungueltig: "
                f"{runden_roh!r}")
        if type(n) is not int or n < 1:
            raise ValueError(
                f"U{pos}: geschaetzte_runden ungueltig: "
                f"{runden_roh!r}")
        i += 1

        unterbloecke.append({
            "id": id_roh,
            "titel": titel_roh,
            "unterpunkte": unterpunkte,
            "geschaetzte_runden": n,
        })

    if not unterbloecke:
        raise ValueError("Phase: kein Unterblock gefunden")
    if len(unterbloecke) > 20:
        raise ValueError(
            f"{len(unterbloecke)} Unterbloecke: "
            "Obergrenze 20 ueberschritten")
    return unterbloecke


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


def _phase_yaml_status_update(
    project_name: str,
    unterblock_id: str,
    status: str,
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
    dateien_union = sorted(set(dateien_alle))
    duplikate = len(dateien_alle) - len(dateien_union)
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
        alter_plan_zeilen.append(
            f"{u.get('id', '?')}: {u.get('titel', '')} "
            f"[{u.get('status', '?')}]")
    alter_plan = "\n".join(alter_plan_zeilen)
    pakete_zeilen: list[str] = []
    for i, p in enumerate(state.phase_commit_pakete, 1):
        dateien = ", ".join(p.get("dateien", []))
        msg = p.get("message", "")[:120]
        pakete_zeilen.append(
            f"Paket {i}: {dateien}\n  {msg}")
    pakete_kompakt = "\n".join(pakete_zeilen) or "(keine)"

    kontext = {
        "begruendung": "Mensch hat Phase abgelehnt.",
        "alter_plan": alter_plan,
        "pakete_kompakt": pakete_kompakt,
    }
    audit("phase_plan_korrektur_start",
          {"phase_id": state.phase_id,
           "pakete_verworfen":
               len(state.phase_commit_pakete)},
          state.project_dir, project_name)
    antwort = _planner_lauf(
        state, api_key, "Korrektur-Auftrag",
        state.project_dir, project_name, historie,
        stufe=2, korrektur_kontext=kontext)
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
    # Neuen Plan schreiben (Status pending).
    plan = _phase_plan_laden(project_name)
    if plan is None:
        return False
    plan["phase_id"] = neue_id
    plan["phase_titel"] = neue_titel
    plan["phase_unterbloecke"] = [
        {
            "id": u["id"],
            "titel": u["titel"],
            "status": "pending",
            "commit_paket": {},
            "unterpunkte": u["unterpunkte"],
            "geschaetzte_runden": u["geschaetzte_runden"],
        }
        for u in neue_ups
    ]
    _phase_plan_speichern(project_name, plan)
    # state aktualisieren.
    state.phase_id = neue_id
    state.phase_titel = neue_titel
    state.phase_unterbloecke = plan["phase_unterbloecke"]
    state.phase_aktueller_index = 0
    return True



def run_phase(
    project_name: str,
    state: RunState,
    state_ref: list[RunState],
    *,
    korrektur_zyklus: int = 0,
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
        print("[i] Phase bereits abgeschlossen. Kein Loop.")
        audit("run_phase_ende",
              {"phase_id": state.phase_id,
               "unterbloecke": len(unterbloecke),
               "rc": 0,
               "abgebrochen": False,
               "bereits_fertig": True},
              state.project_dir, project_name)
        return 0
    if any(s in ("no_go", "failed") for s in status_liste):
        print("[FAIL] Phase enthaelt no_go/failed. Fail closed.")
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
            _phase_yaml_status_update(project_name, uid, "done")
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

        if rc_unterblock == 15:
            # Klasse 3: Unterblock-NO-GO.
            # KEIN Rollback.
            _phase_yaml_status_update(project_name, uid, "no_go")
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
        _phase_yaml_status_update(project_name, uid, "failed")
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

    audit("run_phase_ende",
          {"phase_id": state.phase_id,
           "unterbloecke": len(unterbloecke),
           "rc": 0,
           "abgebrochen": False},
          state.project_dir, project_name)

    # =========================================================
    # P2b-4: Phasen-Gesamt-Review + Approval + Commit.
    # =========================================================
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
        if korrektur_zyklus >= 1:
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
        state_ref.clear()
        return run_phase(
            project_name, state, state_ref,
            korrektur_zyklus=korrektur_zyklus + 1)

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



def _planner_user_content(
    roher_auftrag: str,
    historie: str,
    stufe: int = 1,
    korrektur_kontext: dict[str, Any] | None = None,
) -> str:
    """Baut den User-Content fuer den Planner.

    Auflage P2a-S5a-A10: stufe=1 wortgleich zum
    bisherigen Verhalten (test_planner.py bleibt
    gruen). stufe=2 verweist auf P10-P14.

    P2b-5 / N10: korrektur_kontext (optional).
    Wenn gesetzt, wird ein Korrektur-Auftrag
    formuliert (NO-GO-Begruendung + alter Plan
    + Pakete kompakt).
    """
    if korrektur_kontext is not None:
        begr = korrektur_kontext.get("begruendung", "")
        alter_plan = korrektur_kontext.get("alter_plan", "")
        pakete_kompakt = korrektur_kontext.get(
            "pakete_kompakt", "")
        return (
            "KORREKTUR-AUFTRAG:\n"
            f"NO-GO-Begruendung: {begr}\n\n"
            f"ALTER PLAN:\n{alter_plan}\n\n"
            f"GESAMMELTE PAKETE (kompakt):\n"
            f"{pakete_kompakt}\n\n"
            "Formuliere GENAU EINEN korrigierten "
            "Phasenplan (PHASE/UNTERBLOCK) im "
            "Format aus P10-P14.\n"
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
    return (
        f"ROHER AUFTRAG DES MENSCHEN:\n{roher_auftrag}\n\n"
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
) -> str | None:
    """Fuehrt den Planner aus und liefert die Antwort.

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

    user_content = _planner_user_content(
        roher_auftrag, historie, stufe,
        korrektur_kontext=korrektur_kontext)

    reply = ask_llm(
        api_key, planner_prompt, user_content,
        state.planner_model, 0.0,
        state.llm_timeout_s, state=state)
    if not reply.ok:
        print(f"[FAIL] Planner-Aufruf: {reply.error}")
        audit("planner_call_failed",
              {"error": reply.error, "runde": state.planner_runden},
              project_dir, project_name)
        return None

    return reply.content


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


def _werkstatt_home() -> Path:
    """Liefert das Werkstatt-Heimverzeichnis.

    Auflage 2110: Das ist der Pfad, in dem pipeline.py liegt.
    Nicht der CWD, nicht das Projekt. Damit landet Audit
    immer in /opt/werkstatt/audit-logs/, egal von wo der
    Aufruf kommt. Tests koennen diese Funktion mocken,
    um in ein tmp_path zu schreiben.
    """
    return Path(__file__).resolve().parent


# Auflage 2200a: aktueller Run-Identifier.
# Wird in run_pipeline gesetzt, in audit() in jeden
# Eintrag geschrieben. Modul-global, weil audit()
# keinen state-Parameter hat und ein Umbau aller
# ~200 Aufrufer unverhaeltnismaessig waere.
_AKTUELLE_RUN_ID: str = ""


def audit(kind: str, payload: dict[str, Any], project_dir: Path,
          project_name: str) -> None:
    """Schreibt einen Audit-Eintrag.

    Auflage 2043: project_name wird explizit uebergeben. Keine
    Modul-Variable mehr, keine unsichtbare Kopplung.
    """
    # Auflage 2110: Audit schreibt in die Werkstatt, nicht
    # ins Ziel-Projekt. Grund: Trennung Bau-User (Werkstatt)
    # von Service-User (Projekt). Werkstatt-Audit ist
    # projektuebergreifend, mit project-Feld im Eintrag.
    # project_dir wird nicht mehr fuer die Lokation genutzt,
    # bleibt aber Parameter (Aufrufer unveraendert).
    audit_dir = _werkstatt_home() / AUDIT_DIR_NAME
    audit_dir.mkdir(parents=True, exist_ok=True)
    tag = datetime.now(UTC).strftime("%Y-%m-%d")
    datei = audit_dir / f"agent-pipeline-{tag}.jsonl"
    entry = {
        "audit_id": f"PIPE-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{int(time.time()*1000)%100000}",
        "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds"),
        "agent": "agent_pipeline",
        "project": project_name,
        "kind": kind,
        **payload,
    }
    if _AKTUELLE_RUN_ID:
        entry["run_id"] = _AKTUELLE_RUN_ID
    try:
        with datei.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=True) + "\n")
    except OSError as exc:
        print(f"[WARN] Audit-Schreibfehler: {exc}")



def subprocess_env() -> dict[str, str]:
    """Erlaubt nur die Umgebungsvariablen, die Subprozesse brauchen.

    Auflage 2086: DEEPSEEK_API_KEY und andere Secrets werden
    NICHT durchgereicht. Allowlist statt Blacklist, damit neue
    Secrets nicht automatisch im Subprozess-Env landen.

    Erweiterung: Wenn ein Subprozess eine weitere Variable
    braucht, wird sie hier EXPLIZIT ergaenzt.
    """
    erlaubt = (
        "PATH", "HOME", "LANG", "LC_ALL", "LC_CTYPE",
        "TMPDIR", "USER", "SHELL",
    )
    return {k: os.environ[k] for k in erlaubt if k in os.environ}


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


@dataclass(frozen=True)
class Measurement:
    mid: str
    argv: tuple[str, ...]
    beschreibung: str
    timeout_s: int = SUBPROCESS_TIMEOUT


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
        "git_status": Measurement("git_status", ("git", "status", "--porcelain"), "Tree."),
        "git_head": Measurement("git_head", ("git", "rev-parse", "--short", "HEAD"), "HEAD."),
        "test_run": Measurement("test_run", (venv, "-m", "pytest", "-q"), "Vollsuite.", 600),
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
    if m.mid == "read_file":
        if not extra_arg:
            return "read_file ohne Pfad.", False, []
        if not isinstance(extra_arg, str):
            return "read_file arg ist kein str.", False, []
        cand = (project_dir / extra_arg).resolve()
        try:
            rel = str(cand.relative_to(project_dir.resolve()))
        except ValueError:
            return f"Pfad ausserhalb Projekt: {extra_arg}", False, []
        if not any(rel.startswith(p) for p in whitelist):
            return f"Pfad nicht in Whitelist: {rel}", False, []
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



@dataclass
class LLMReply:
    ok: bool
    content: str = ""
    error: str = ""


def ask_llm(api_key: str, system_prompt: str, user_content: str,
            model: str, temperature: float, timeout: int = 120,
            *, state: RunState | None = None) -> LLMReply:
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
                               "messages": [{"role": "system", "content": system_prompt},
                                            {"role": "user", "content": user_content}],
                               "temperature": temperature}
    # Auflage 2087: Retry nur bei 429 (Rate Limit) und 5xx
    # (Server-Fehler). Kein Retry bei 4xx — ein Auth-Fehler
    # wuerde sich endlos wiederholen.
    # Max 2 Versuche. Backoff: 1s, dann 3s.
    backoffs = (1, 3)
    letzter_fehler: str = ""
    res = None
    for versuch, warte in enumerate(backoffs, start=1):
        try:
            res = requests.post(DEEPSEEK_API_URL, headers=headers,
                                json=payload, timeout=timeout)
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
        return LLMReply(ok=True, content=data["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        return LLMReply(ok=False, error=f"Parsing: {exc}")


def classify_verdict(text: str) -> str:
    """Erkennt GO / NO-GO / ESKALATION / COMMIT-* / COMMAND.

    Auflage 2077: Satzzeichen am Wortende werden gestrippt,
    damit "GO.", "NO-GO:" und "ESKALATION!" erkannt werden.
    Der Bindestrich bleibt Teil des Tokens (NO-GO), sonst
    wuerde "NO-GO." als "NO" gelesen.
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
        if w in {"GO", "NO-GO", "ESKALATION"}:
            return w
        if w in {"COMMIT-GO", "COMMIT-NO-GO", "COMMIT-ESKALATION"}:
            return w
        if s.upper().startswith("COMMAND:"):
            return "COMMAND"
    return "UNKLAR"


def parse_commands(text: str) -> list[dict[str, str]]:
    """Parst COMMAND-Zeilen aus einer LLM-Antwort.

    Auflage 2039: arg muss str sein. Kein dict/list.
    Wenn der LLM einen JSON-Block liefert, wird das
    verworfen und der Eintrag nicht uebernommen.
    """
    cmds: list[dict[str, str]] = []
    for line in text.splitlines():
        s = line.strip()
        if not s.upper().startswith("COMMAND:"):
            continue
        body = s[len("COMMAND:"):].strip()
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
        cmds.append({"id": cmd_id, "arg": arg_roh})
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


def pruefe_anker_gegen_messung(
    patches: list[dict[str, str]],
    mess_protokoll: str,
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
        if anker in mess_protokoll:
            continue
        # HH2: +2-Shift-Variante
        verschoben = _shift_lines(anker, "  ")
        if verschoben in mess_protokoll:
            fehlend.append(
                (i, pfad, anker, "shift_akzeptiert"))
            continue
        fehlend.append((i, pfad, anker, "nicht_gefunden"))
    return fehlend


def pruefe_ersatz_gegen_messung(
    patches: list[dict[str, str]],
    mess_protokoll: str,
) -> list[tuple[int, str, str]]:
    """Stufe 0, Aenderung 1b: deterministische
    Ersatz-Pruefung gegen den GEMESSENER INHALT.

    Liefert Liste von (Patch-Index, Pfad, Modul).

    II1: Regex am Zeilenanfang. Erkennt mehrzeilige
    Klammer-Imports, weil nur der from-Import-Anfang
    gematcht wird. Erkennt NICHT: Inline-Imports
    (x = 1; from foo import bar), relative Imports
    (from .foo import bar), bedingte Imports
    (if True:\n    from foo...). Diese kommen in
    security-ai nicht vor.

    II2b: Treffer ist Substring-Match
    (modul in mess_protokoll). Kollisionen bei
    Modulnamen, die Praefix eines laengeren
    Modulnamens sind, werden nicht erkannt.
    Bei erster realer Kollision: Wortgrenzen
    oder exakter Match.
    """
    import re as _re
    fehlend: list[tuple[int, str, str]] = []
    # II1: Regex muss mit Buchstabe oder _ beginnen,
    # damit relative Imports (from .foo import) NICHT
    # erkannt werden.
    pfad_re = _re.compile(
        r"^\s*(?:from\s+([a-zA-Z_][\w.]*)\s+import"
        r"|import\s+([a-zA-Z_][\w.]*))",
        _re.MULTILINE,
    )
    for i, p in enumerate(patches):
        ersatz = p.get("ersatz", "")
        pfad = p.get("pfad", "")
        if not ersatz:
            continue
        for m in pfad_re.finditer(ersatz):
            modul = m.group(1) or m.group(2)
            if modul and modul not in mess_protokoll:
                fehlend.append((i, pfad, modul))
    return fehlend


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
    for builder_runde in range(1, max_builder_runden + 1):
        aktueller_prompt = user_prompt_fn(state)
        _audit_builder_prompt(
            aktueller_prompt, state, project_dir, project_name)
        reply = ask_llm(
            api_key, builder_prompt, aktueller_prompt,
            state.builder_model, state.builder_temp,
            state.llm_timeout_s, state=state,
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
                    patches, state.mess_protokoll)
                ersatz_fehler = pruefe_ersatz_gegen_messung(
                    patches, state.mess_protokoll)
                if anker_fehler or ersatz_fehler:
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
        for cmd in cmds:
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
              f"{len(cmds)} COMMAND(s) angefordert.")
        ergebnisse = execute_commands(
            state, cmds, quelle="builder")
        for key, ok in ergebnisse.items():
            if ok:
                gescheiterte.discard(key)
            else:
                gescheiterte.add(key)
        audit("builder_command_executed",
              {"runde": builder_runde,
               "anzahl": len(cmds),
               "ids": [c["id"] for c in cmds]},
              project_dir, project_name)
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
    kontext = (
        f"Der Builder hat in {max_builder_runden} aufeinanderfolgenden "
        f"Runden nur COMMAND-Zeilen geliefert, keinen Patch. "
        f"Letzter Prompt:\n{aktueller_prompt[:2000]}\n"
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


def formatiere_runden(review_runden: list[dict[str, Any]]) -> str:
    """Auflage 2183 A1a: formatiert review_runden.

    Liefert einen Block fuer den Reviewer-Prompt.
    Leerer String, wenn keine Runden vorhanden sind.
    Recovery-Runden erhalten den Marker RECOVERY.
    """
    if not review_runden:
        return ""
    zeilen = ["BISHERIGE RUNDEN:"]
    for r in review_runden:
        raw = r.get("raw", "")
        if len(raw) > 1500:
            raw = raw[:1500] + " [... gekuerzt ...]"
        mark = "RECOVERY - " if r.get("recovery") else ""
        zeilen.append(
            f"[ROUND {r['runde']} - {mark}{r['verdict']}]")
        zeilen.append(raw)
    return "\n".join(zeilen) + "\n\n"


def recovery_hinweis_block(
        review_runden: list[dict[str, Any]],
        hat_befund: bool = False) -> str:
    """Auflage 2183 A1a + Block 2a (W6/W7).

    Liefert den Block, wenn die letzte Runde recovery=True
    trug. Sonst leerer String.

    Kein Befund-Text mehr. Nur ein neutraler Hinweis,
    dass ein Solver-Befund existierte. Der Befund-Text
    geht an den Builder-Agenten (siehe _solver_befund_block).
    """
    if not review_runden:
        return ""
    if not review_runden[-1].get("recovery"):
        return ""
    if hat_befund:
        return (
            "## RECOVERY-RUNDE\n"
            "Diese Runde folgte auf einen Solver-Befund.\n"
            "Der Befund ist dem Builder-Agenten bekannt,\n"
            "nicht dir. Du bewertest das Ergebnis, nicht\n"
            "den Befund. Bewerte den Patch inhaltlich\n"
            "(R1-R7).\n"
            "Wenn der Patch den Solver-Befund nicht\n"
            "umsetzt, aber inhaltlich korrekt ist:\n"
            "Bewerte ihn trotzdem als korrekt.\n\n"
        )
    return (
        "## RECOVERY-RUNDE\n"
        "Dies ist eine Recovery-Runde ohne Solver-\n"
        "Befund. Pruefe den Code wie sonst (R1-R7).\n\n"
    )


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


@dataclass
class RunState:
    block_id: str
    aufgabe: str
    start_ts: str
    docs: dict[str, str]
    agents: dict[str, dict[str, Any]]
    always: dict[str, Measurement]
    optional: dict[str, Measurement]
    file_whitelist: list[str]
    api_key: str
    budget: dict[str, int]
    agent_docs: dict[str, list[str]]
    project_dir: Path
    # Agent-Memory A2: Projekt-Stand (aus memory.yaml).
    projekt_stand: dict = field(default_factory=dict)
    start_monotonic: float = 0.0  # Auflage 2080: Zeitmessung
    # Auflage 2183 P1 (U3): Schwellwert + min_tokens
    # justierbar, nicht im Code hart.
    solver_config: dict[str, float] = field(
        default_factory=dict)
    # Planner-Konfiguration (Block P1, 2026-10-15).
    # SS7-(C): Modell als hartcodierter Default, analog
    # zu builder_model. Frontmatter wird heute nicht gelesen.
    planner_model: str = "deepseek-chat"
    planner_vorschlag: str = ""
    planner_modus: str = "manual"
    planner_runden: int = 0
    reviewer_verdict_model: str = "deepseek-chat"
    reviewer_recovery_model: str = "deepseek-reasoner"
    builder_model: str = "deepseek-chat"
    builder_temp: float = 0.3
    test_gen_model: str = "deepseek-chat"
    llm_timeout_s: int = 180
    git_author_name: str = ""
    git_author_email: str = ""
    project_name: str = ""
    coverage_pct: int = -1  # -1 = nicht gemessen
    basis_protokoll: str = ""
    basis_protokoll_nach_apply: str = ""  # UMB-1b
    mess_protokoll: str = ""
    # Bug-Fix 2026-10-14: True, sobald mindestens
    # ein Apply passiert ist. Der GEMESSENER
    # INHALT-Block ist dann der Stand VOR dem
    # Apply. Kein Reset (mess_protokoll ist
    # akkumulativ).
    mess_protokoll_veraltet: bool = False
    code_entwurf: str = ""
    # Auflage 2183 A1b: Historisierung fuer Solver-Vergleich.
    code_entwurf_historie: list[dict[str, Any]] = \
        field(default_factory=list)
    # Auflage 2183 A2: run_id fuer Korrelation.
    run_id: str = ""
    # Auflage 2183 A2: Solver-Befunde.
    solver_befunde: list[SolverBefund] = \
        field(default_factory=list)
    # Auflage 2183 C: Quellen der Solver-Laeufe.
    solver_trigger_quellen: list[str] = \
        field(default_factory=list)
    # Auflage 2183 Block 5: Zaehlt Solver-Versuche
    # (auch fehlgeschlagene, GG2).
    solver_aufrufe: int = 0
    # Stufe 0 Aenderung 2: Anker- und Ersatz-Fehler
    # im Builder-Loop. Wird in _builder_user_prompt
    # als Rueckmeldung angezeigt.
    letzte_anker_fehler: list[tuple[int, str, str, str]] = \
        field(default_factory=list)
    letzte_ersatz_fehler: list[tuple[int, str, str]] = \
        field(default_factory=list)
    anker_fehler_in_folge: int = 0
    # Block Auftrag-erfuellt B3: letzter Patch war
    # wirkungslos (anker == ersatz). Signal fuer B2.
    letzter_patch_wirkungslos: bool = False
    code_patches: list[dict[str, str]] = field(default_factory=list)  # UMB-1b
    test_vorschlaege: str = ""
    commit_paket: dict[str, Any] = field(default_factory=dict)
    commit_review: dict[str, Any] = field(default_factory=dict)
    review_runden: list[dict[str, Any]] = field(default_factory=list)
    commands_log: list[dict[str, str]] = field(default_factory=list)
    auflagen_log: list[list[str]] = field(default_factory=list)
    empfehlung_log: list[dict[str, str]] = field(default_factory=list)
    llm_calls: int = 0
    # Block P2a: Phasen-Modus (Stufe 2).
    phase_id: str | None = None
    phase_titel: str = ""
    phase_unterbloecke: list[dict[str, Any]] = \
        field(default_factory=list)
    phase_aktueller_index: int = 0
    phase_commit_pakete: list[dict[str, Any]] = \
        field(default_factory=list)
    phase_start_head: str = ""
    phase_aktiv: bool = False



@dataclass
class RepairAttempt:
    nummer: int
    fehler_vor: list[str]
    massnahme: str
    erfolg: bool
    protokoll: str


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
class SolverDiagnose(Enum):
    """Auflage 2183 A2: vier Solver-Diagnostypen."""
    GLEICHER_FEHLER = "gleicher_fehler"
    ANDERER_FEHLER = "anderer_fehler"
    WIDERSPRUCH = "widerspruch"
    UNKLAR = "unklar"


@dataclass
class SolverBefund:
    """Auflage 2183 A2: strukturierter Solver-Befund.

    Wird vom Solver (B) erzeugt und in state.solver_befunde
    gespeichert. Getrennt von RecoveryVorschlag.
    """
    art: SolverDiagnose
    kandidaten: list[str] = field(default_factory=list)
    praezisierter_auftrag: str = ""
    rueckspiel_hinweis: str = ""
    eskalation: str = ""
    run_id: str = ""

    def ist_vollstaendig(self) -> bool:
        """Auflage 2183 A2: Felder fuer die Diagnose gefuellt?"""
        if self.art == SolverDiagnose.GLEICHER_FEHLER:
            return bool(self.kandidaten)
        if self.art == SolverDiagnose.ANDERER_FEHLER:
            return bool(self.praezisierter_auftrag)
        if self.art == SolverDiagnose.WIDERSPRUCH:
            return bool(self.rueckspiel_hinweis)
        if self.art == SolverDiagnose.UNKLAR:
            return bool(self.eskalation)
        return False


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


@dataclass
class RecoveryVorschlag:
    art: str
    diagnose: str = ""
    reparaturplan: list[str] = field(default_factory=list)
    empfehlung: str = ""
    blockgroesse: str = ""
    frage_an_menschen: str = ""
    rohantwort: str = ""


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
        "dich erstellt. Pruefe die Empfehlungen\n"
        "gegen den Auftrag und den GEMESSENER\n"
        "INHALT. Die Umsetzung ist deine Aufgabe.\n\n"
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
    zeilen = [aufgabe_block(state).rstrip()]
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
    zeilen.append(state.mess_protokoll or "(keine)")
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
    reply = ask_llm(api_key, solver_prompt, user_content,
                    state.reviewer_verdict_model, 0.0,
                    state.llm_timeout_s, state=state)
    if not reply.ok:
        return None, "llm_fehler"
    befund = baue_solver_befund(reply.content,
                                state.run_id)
    if not befund.ist_vollstaendig():
        return None, "befund_unvollstaendig"
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


def format_projekt_stand(state: RunState) -> str:
    """A2: formatiert den Projekt-Stand als Prompt-Block.

    Liefert "" wenn kein projekt_stand vorliegt (UU6).
    Max 5 Commits (UU8).
    """
    ps = state.projekt_stand or {}
    commits = ps.get("letzte_commits", [])
    if not commits:
        return ""
    zeilen = ["## PROJEKT-STAND (letzte Commits)"]
    for c in commits[:5]:
        h = c.get("hash", "")
        # datum kann datetime sein (yaml.safe_load).
        d = str(c.get("datum", ""))[:10]
        q = c.get("quelle", "")
        m = c.get("message", "")
        zeilen.append(f"- {h} ({d}, {q}) {m}")
        dateien = c.get("dateien", [])
        if dateien:
            zeilen.append(
                "  Dateien: " + ", ".join(dateien))
    zeilen.append("")
    return "\n".join(zeilen)


def aufgabe_block(state: RunState) -> str:
    """Auflage 2154: zentrale Formatierung des Auftrags.

    Liefert "AUFGABE: <auftrag>\n\n". Wird in allen
    Reviewer- und Builder-Prompts verwendet, damit
    der Auftrag konsistent ist.
    """
    return f"AUFGABE: {state.aufgabe}\n\n"


def ask_reviewer_for_recovery(state: RunState, art: str, kontext: str) -> RecoveryVorschlag:
    # Auflage 2153: Auftrag vor dem Kontext.
    kopf = aufgabe_block(state)
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
        out = trim_output(out)

        # Auflage 2041: Gesamtlaenge begrenzen.
        rest_platz = MAX_PROTOKOLL_TOTAL - len(state.mess_protokoll)
        if rest_platz <= 0:
            print("[!] mess_protokoll Gesamtlimit erreicht. Weitere Messungen werden nur auditiert.")
            audit("command_executed",
                  {"id": cid, "arg": arg[:200], "argv": argv,
                   "quelle": quelle, "ok": ok, "ausgabe_verworfen": True},
                  state.project_dir, state.project_name)
            continue
        if len(out) > rest_platz:
            out = out[:rest_platz] + "\n[... Gesamtlimit erreicht ...]\n"

        if ok:
            state.mess_protokoll += out
        else:
            state.mess_protokoll += (
                "\n\n!!! COMMAND FEHLGESCHLAGEN: "
                f"{cid} {arg} !!!\n"
                "Der COMMAND hat ok=false geliefert. "
                "Ursache im Output unten.\n"
                "Wenn der Pfad falsch war: pruefe den "
                "Pfad woertlich aus dem Auftrag, aus "
                "dem ZIELDATEIEN-Header oder aus dem "
                "KUERZUNGS-MARKER. Rekonstruiere ihn "
                "nicht.\n\n"
                + out
            )
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


def _shift_lines(text: str, prefix: str = "  ") -> str:
    """Auflage 2165: ergaenzt jede nicht-leere Zeile um prefix.

    Wird fuer die Einrueckungs-Normalisierung verwendet:
    Der Builder liefert Anker/Ersatz oft um 2 Spaces
    zu kurz. Wenn der Anker nur in der +2-Variante
    genau 1x matcht, korrigieren wir.
    """
    zeilen = text.split("\n")
    return "\n".join(
        (prefix + z) if z else z for z in zeilen
    )


def apply_code_patches(state: RunState,
                       patches: list[dict[str, str]],
                       dry_run: bool = False) -> bool:
    """UMB-1a: wendet Code-Patches an (In-Memory-Rollback).

    Pruefungen pro Patch:
      - pfad in state.file_whitelist
      - Datei existiert
      - pfad nicht doppelt in patches
      - Anker count == 1

    Bei dry_run: nur pruefen, nichts schreiben.

    Bei Fehler: nichts wurde geschrieben, return False.
    Wenn spaeter etwas fehlschlaegt (theoretisch nicht
    nach Vollvalidierung): In-Memory-Rollback.
    """
    # ---- Phase 1: Validierung ----
    if not patches:
        print("[!] apply_code_patches: keine Patches.")
        return False
    # Auflage 2173: Doppel-Pruefung auf (Pfad, Anker),
    # nicht nur Pfad. Mehrere Patches pro Datei sind
    # legitim, solange Anker unterschiedlich.
    gesehen: set[tuple[Path, str]] = set()
    original: dict[Path, str] = {}
    plan: list[tuple[Path, str, str]] = []
    for p in patches:
        pfad = p.get("pfad", "")
        anker = p.get("anker", "")
        ersatz = p.get("ersatz", "")
        if not pfad:
            print("[!] apply_code_patches: Patch ohne pfad.")
            return False
        if not any(pfad.startswith(w) for w in state.file_whitelist):
            print(f"[!] apply_code_patches: Pfad nicht in "
                  f"Whitelist: {pfad}")
            return False
        ziel = state.project_dir / pfad
        if not ziel.exists():
            print(f"[!] apply_code_patches: Datei fehlt: {pfad}")
            return False
        if (ziel, anker) in gesehen:
            print(f"[!] apply_code_patches: Patch "
                  f"(pfad, anker) doppelt: {pfad}")
            return False
        gesehen.add((ziel, anker))
        inhalt = ziel.read_text(encoding="utf-8")
        count = inhalt.count(anker)
        # Auflage 2161: Pruefe Zeilen-Anfang.
        am_anfang = (
            inhalt.startswith(anker)
            or ("\n" + anker) in inhalt
        )
        # Auflage 2165: Einrueckungs-Normalisierung.
        # Der Builder liefert Anker/Ersatz oft um 2 Spaces
        # zu kurz. Korrektur, wenn:
        #   - count != 1 (kein exakter Match), ODER
        #   - nicht am Zeilen-Anfang (Substring-Match).
        # UND die +2-Variante genau 1x am Zeilen-Anfang
        # matcht.
        if count != 1 or not am_anfang:
            anker_plus = _shift_lines(anker, "  ")
            plus_count = inhalt.count(anker_plus)
            plus_am_anfang = (
                inhalt.startswith(anker_plus)
                or ("\n" + anker_plus) in inhalt
            )
            if plus_count == 1 and plus_am_anfang:
                print(f"[i] apply_code_patches: Anker in {pfad} "
                      f"um 2 Spaces verschoben. Korrigiere.")
                audit("anker_einrueckung_korrigiert",
                      {"pfad": pfad}, state.project_dir,
                      state.project_name)
                anker = anker_plus
                ersatz = _shift_lines(ersatz, "  ")
                p["anker"] = anker
                p["ersatz"] = ersatz
                count = 1
                am_anfang = True
        if count != 1:
            print(f"[!] apply_code_patches: Anker in {pfad} "
                  f"kommt {count}x vor. Erwartet 1x.")
            return False
        if not am_anfang:
            print(f"[!] apply_code_patches: Anker in {pfad} "
                  f"steht nicht am Zeilen-Anfang. Fail closed.")
            return False
        original[ziel] = inhalt
        plan.append((ziel, anker, ersatz))

    if dry_run:
        print(f"[i] apply_code_patches (dry_run): "
              f"{len(plan)} Patches validiert.")
        return True

    # ---- Phase 2: Anwendung ----
    # Auflage 2173: bei mehreren Patches pro Datei
    # muss jede Iteration den AKTUELLEN Stand lesen,
    # nicht den Urzustand. Sonst ueberschreibt der
    # zweite Patch den ersten.
    geschrieben: list[Path] = []
    try:
        for ziel, anker, ersatz in plan:
            aktuell = ziel.read_text(encoding="utf-8")
            neu = aktuell.replace(anker, ersatz, 1)
            ziel.write_text(neu, encoding="utf-8")
            geschrieben.append(ziel)
            print(f"[+] Code gepatcht: "
                  f"{ziel.relative_to(state.project_dir)}")
    except OSError as exc:
        print(f"[!] apply_code_patches: Schreibfehler: {exc}")
        # Rollback
        for ziel in geschrieben:
            try:
                ziel.write_text(original[ziel], encoding="utf-8")
            except OSError as exc2:
                print(f"[!] Rollback fehlgeschlagen fuer {ziel}: {exc2}")
        return False

    return True


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
    anker: str | None = None
    ersatz: str | None = None
    aktives_feld: str | None = None
    aktuelle_zeilen: list[str] = []

    def _flush() -> None:
        nonlocal aktives_feld, aktuelle_zeilen
        if aktives_feld is None:
            return
        wert = "\n".join(aktuelle_zeilen)
        if aktives_feld == "anker":
            nonlocal anker
            anker = wert
        elif aktives_feld == "ersatz":
            nonlocal ersatz
            ersatz = wert
        elif aktives_feld == "pfad":
            nonlocal pfad
            pfad = wert.strip()
        aktives_feld = None
        aktuelle_zeilen = []

    for raw_line in block.splitlines():
        # Tabs ablehnen (P1).
        if "\t" in raw_line:
            return None
        # Feld-Anfang?
        m_feld = re.match(r"^(pfad|anker|ersatz):\s*(.*)$", raw_line)
        if m_feld:
            _flush()
            name, rest = m_feld.group(1), m_feld.group(2)
            if name == "pfad":
                if rest.startswith("|"):
                    # pfad als Block-Scalar ist erlaubt,
                    # wird aber praktisch selten genutzt.
                    aktives_feld = "pfad"
                    aktuelle_zeilen = []
                else:
                    pfad = rest.strip()
            else:
                # anker / ersatz muessen "|" haben (YAML-Block).
                if not rest.startswith("|"):
                    return None
                aktives_feld = name
                aktuelle_zeilen = []
            continue
        # Fortsetzungszeile (eingrueckt, 2 Spaces).
        if aktives_feld is not None:
            if raw_line.startswith("  "):
                aktuelle_zeilen.append(raw_line[2:])
            elif raw_line.strip() == "":
                # Leerzeile im Block erlaubt.
                aktuelle_zeilen.append("")
            else:
                # Ende des Block-Scalars.
                _flush()
        # Sonst: ignorieren (z.B. Leerzeile ausserhalb).

    _flush()

    # Validierung.
    if not pfad:
        return None
    if anker is None or anker == "":
        return None
    if ersatz is None:
        ersatz = ""
    return {"pfad": pfad, "anker": anker, "ersatz": ersatz}


def _rollback_zieldateien(state: RunState,
                         project_dir: Path,
                         project_name: str,
                         grund: str) -> None:
    """Auflage 2197: Fail-closed-Rollback.

    Setzt alle Pfade aus state.code_patches zurueck, die im
    Arbeitsbaum als " M" (modifiziert) auftauchen.
    Best effort: Fehler brechen nicht ab.
    """
    if not state.code_patches:
        return
    pfade = []
    for p in state.code_patches:
        pfad = p.get("pfad", "")
        if pfad and pfad not in pfade:
            pfade.append(pfad)
    if not pfade:
        return
    try:
        res = subprocess.run(
            ("git", "status", "--porcelain"),
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
    zurueckgesetzt = []
    for pfad in pfade:
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
    if zurueckgesetzt:
        print(f"[i] Fail-closed-Rollback: {zurueckgesetzt}")
    audit("rollback_fail_closed",
          {"grund": grund, "zieldateien": zurueckgesetzt,
           "gepruefte": pfade},
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


def rollback_vor_recovery(state: RunState, project_dir: Path,
                          project_name: str) -> None:
    """Auflage 2183 A1c: Rollback vor einer Recovery-Runde.

    Setzt Zieldateien auf HEAD zurueck, damit der Builder
    auf sauberem Baum startet. Kein Fail, kein Exit-Code.
    Der Lauf geht weiter (Recovery-Runde).

    Wird von A3 (Trigger) gerufen, sobald Recovery-Laeufe
    existieren. Heute ungenutzt.
    """
    _rollback_zieldateien(state, project_dir, project_name,
                         "recovery_start")


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
    if not erhoehe_solver_aufruf(state, _msr):
        audit("solver_max_solver_runden_erreicht",
              {"pfad": "deadlock",
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

    print("[*] Basis-Gate nach Anwendung (ohne git_status).")
    # Bug-Fix 2026-10-14: Apply ist passiert.
    # mess_protokoll ist ab jetzt der Stand VOR Apply.
    state.mess_protokoll_veraltet = True
    state.basis_protokoll_nach_apply = ""
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
        v = ask_reviewer_for_recovery(
            state, "basis_gate",
            f"Nach Anwendung der Code-Patches: {nach_fehler}\n\n"
            f"Protokoll:\n{state.basis_protokoll_nach_apply[:3000]}")
        print_recovery(v)
        audit("recovery_basis_gate_nach_apply",
              {"fehler": nach_fehler, "empfehlung": v.empfehlung},
              state.project_dir, state.project_name)
        return 18
    return None


def collect_messwerte(state: RunState) -> dict[str, Any]:
    """Auflage 2135: extrahiert Messwerte aus dem Basis-Protokoll.

    Liefert ein dict mit den Werten, die der Builder fuer die
    Commit-Message braucht:
      - test_anzahl (int | None)
      - ruff (gruen|rot)
      - mypy (gruen|rot)
      - py_compile (gruen|rot)
      - git_status (clean|geaendert)
      - git_head (str)
      - verstrichene_zeit_s (float)

    Basis: state.basis_protokoll (geschrieben vom Basis-Gate).
    Fallback bei Parse-Fehler: test_anzahl = None, sonst "rot".
    """
    import re as _re
    # Auflage 2196: nach apply_and_recheck hat
    # basis_protokoll_nach_apply die aktuellen Werte.
    basis = (
        state.basis_protokoll_nach_apply
        or state.basis_protokoll
        or ""
    )

    # Pro Messung: (mid, rc, stdout)
    # Auflage 2198: test_count nutzt seit 2176 das Format
    # STDOUT (letzte Zeile). Der Zusatz ist optional.
    treffer = _re.findall(
        r"=== (\w+) ===\nARGV: [^\n]*\nRC: (\d+)\n"
        r"STDOUT(?: \(letzte Zeile\))?:\n(.*?)STDERR:",
        basis, _re.DOTALL,
    )
    werte: dict[str, Any] = {
        "test_anzahl": None,
        "ruff": "rot",
        "mypy": "rot",
        "py_compile": "rot",
        "git_status": "geaendert",
        "git_head": "",
        "verstrichene_zeit_s": 0.0,
    }
    for mid, rc_str, stdout in treffer:
        rc = int(rc_str)
        if mid == "test_count":
            m = re.search(r"(\d+) tests? collected", stdout)
            if m:
                werte["test_anzahl"] = int(m.group(1))
        elif mid == "ruff":
            werte["ruff"] = "gruen" if rc == 0 else "rot"
        elif mid == "mypy":
            werte["mypy"] = "gruen" if rc == 0 else "rot"
        elif mid == "py_compile":
            werte["py_compile"] = "gruen" if rc == 0 else "rot"
        elif mid == "git_status":
            werte["git_status"] = ("clean"
                                   if stdout.strip() == ""
                                   else "geaendert")
        elif mid == "git_head":
            werte["git_head"] = stdout.strip()

    # Verstrichene Zeit aus start_monotonic
    if state.start_monotonic > 0:
        werte["verstrichene_zeit_s"] = (
            time.monotonic() - state.start_monotonic)

    return werte


def extract_paths_from_aufgabe(aufgabe: str,
                                file_whitelist: list[str],
                                project_dir: Path) -> list[str]:
    """Auflage 2146: extrahiert Datei-Pfade aus dem Auftrag.

    Regex findet Pfade mit Endung .py/.md/.yaml/.yml.
    Filter: Pfad muss in file_whitelist liegen und
    Datei muss existieren. Dedupliziert.
    """
    if not aufgabe:
        return []
    kandidaten = re.findall(
        r"[a-zA-Z0-9_./-]+\.(?:py|md|yaml|yml)",
        aufgabe,
    )
    ergebnis: list[str] = []
    gesehen: set[str] = set()
    for p in kandidaten:
        # Fuehrende Slashes entfernen (z.B. aus "/opt/...").
        p = p.lstrip("/")
        if p in gesehen:
            continue
        if not any(p.startswith(w) for w in file_whitelist):
            continue
        if not (project_dir / p).exists():
            continue
        gesehen.add(p)
        ergebnis.append(p)
    return ergebnis


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
        m2 = re.search(r"\n[A-ZÄÖÜ][A-ZÄÖÜa-zäöü_ ()/,-]{2,60}:",
                        rest[len(marker):])
        if m2:
            gem_len = len(rest[:len(marker) + m2.start()])
        else:
            gem_len = len(rest)
    redigiert, _ = redaction.redact_all(prompt, max_len=200000)
    audit("builder_prompt_gebaut",
          {"prompt_len": len(redigiert),
           "sektionen": sektionen,
           "gemessener_inhalt_len": gem_len},
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


def ensure_ziel_gemessen(
    state: RunState,
    ziel_pfade: list[str],
    project_dir: Path,
    file_whitelist: list[str],
    project_name: str,
) -> None:
    """Auflage 2192: Werkstatt messt automatisch fehlende Zieldateien.

    Fuer jeden Pfad in ziel_pfade: pruefen, ob er im
    mess_protokoll vollstaendig vorliegt. Wenn nicht:
    read_file mit quelle="pipeline_auto".
    """
    if not ziel_pfade:
        return
    bereits = _gemessene_pfade(state.mess_protokoll)
    fehlend: list[dict[str, str]] = []
    for p in ziel_pfade:
        ziel = (project_dir / p).resolve()
        if str(ziel) in bereits:
            continue
        fehlend.append({"id": "read_file", "arg": p})
    if not fehlend:
        return
    print(f"[i] Auto-Messung: {len(fehlend)} Zieldatei(en).")
    execute_commands(state, fehlend, quelle="pipeline_auto")


def _gemessene_pfade(mess_protokoll: str) -> set[str]:
    """Auflage 2190c: ermittelt Pfade, die im mess_protokoll
    vollstaendig gelesen wurden (read_file, ok, kein GEKUERZT).

    Liest den mess_protokoll-Text nach read_file-Aufrufen.
    Ein read_file-Aufruf ist vollstaendig, wenn RC 0 war und
    kein "AUSSCHNITT GEKUERZT"-Marker folgt.
    """
    pfade: set[str] = set()
    if not mess_protokoll:
        return pfade
    bloecke = mess_protokoll.split("=== read_file ===")
    for block in bloecke[1:]:
        zeilen = block.splitlines()
        pfad: str | None = None
        rc0 = False
        gekuerzt = False
        for z in zeilen:
            if z.startswith("ARGV: cat "):
                pfad = z[len("ARGV: cat "):].strip()
            elif z.startswith("RC: "):
                rc0 = z.strip() == "RC: 0"
            elif "AUSSCHNITT GEKUERZT" in z:
                gekuerzt = True
        if pfad and rc0 and not gekuerzt:
            pfade.add(pfad)
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


def format_doc_snippets(docs: dict[str, str],
                        max_len: int = 3000) -> str:
    """Auflage 2142: Ausschnitte aus den Doku-Dateien fuer den Builder.

    Der Builder braucht konkrete Anker-Texte aus den
    Zieldateien, um gueltige Doku-Patches zu bauen.
    Ohne diese Ausschnitte liefert er eine Rueckfrage
    (Befund S aus Probebetrieb 10).

    Pro Datei: max_len Zeichen Anfang. Redaction zuerst
    (Secrets-Schutz), max_len=100000 damit die Grenze
    nicht durch Redaction weiter gekuerzt wird.
    """
    if not docs:
        return "(keine Doku geladen)"
    teile = ["DOKU-AUSSCHNITTE (Auszug aus den Zieldateien):"]
    for key, inhalt in docs.items():
        total = len(inhalt)
        gekuerzt = total > max_len
        ausschnitt = inhalt[:max_len]
        ausschnitt, _ = redaction.redact_all(
            ausschnitt, max_len=100000)
        if gekuerzt:
            kopf = (
                f"--- {key} (Zeichen 1-{max_len} von {total}, "
                f"GEKUERZT) ---"
            )
        else:
            kopf = (
                f"--- {key} (Zeichen 1-{total} von {total}, "
                f"vollstaendig) ---"
            )
        teile.append(kopf)
        teile.append(ausschnitt)
        if gekuerzt:
            rest = total - max_len
            teile.append(
                f"\n[... AUSSCHNITT GEKUERZT. {rest} weitere "
                f"Zeichen. Fuer die vollstaendige Doku: "
                f"COMMAND: RUN read_file {key}]"
            )
    return "\n".join(teile)


def format_messwerte_block(werte: dict[str, Any]) -> str:
    """Formatiert die Messwerte fuer den Builder-Prompt.

    Auflage 2135: Der Builder verwendet diese Werte woertlich.
    """
    test_anzahl = werte.get("test_anzahl")
    test_str = str(test_anzahl) if test_anzahl is not None else "nicht gemessen"
    return (
        "MESSWERTE (von der Werkstatt gemessen, nicht schaetzen):\n"
        f"  test_anzahl: {test_str}\n"
        f"  ruff: {werte.get('ruff', 'rot')}\n"
        f"  mypy: {werte.get('mypy', 'rot')}\n"
        f"  py_compile: {werte.get('py_compile', 'rot')}\n"
        f"  git_status: {werte.get('git_status', 'geaendert')}\n"
        f"  git_head: {werte.get('git_head', '')}\n"
        f"  verstrichene_zeit_s: {werte.get('verstrichene_zeit_s', 0.0):.0f}"
    )


def format_code_patches_fuer_commit(
        patches: list[dict[str, str]]) -> str:
    """Auflage 2191-R2: formatiert CODE-PATCHES fuer commit_input.

    Nur pfad und anker. Kein ersatz (Reviewer-Begruendung P1:
    ersatz ist nicht Pruefgegenstand in Phase 2, steht in
    Commit-Message und git diff).

    Format:
      PATCH <n> (pfad):
      anker:
      <anker>
      ---
    """
    if not patches:
        return "(keine)"
    bloecke: list[str] = []
    for i, p in enumerate(patches, start=1):
        pfad = p.get("pfad", "")
        anker = p.get("anker", "")
        bloecke.append(
            f"PATCH {i} ({pfad}):\n"
            f"anker:\n{anker}\n"
            "---"
        )
    return "\n".join(bloecke)


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

    aufgabe = (
        "Der Code-Review ist abgeschlossen. Der Reviewer hat "
        "in der letzten Runde GO gegeben. Die Code-Patches "
        "sind bereits angewendet.\n\n"
        "Baue das Commit-Paket:\n"
        "1. Commit-Message im Format des letzten Commits.\n"
        "2. Liste der betroffenen Dateien (basierend auf "
        "git status/git diff).\n\n"
        "Achte auf die Auflagen des Reviewers (unten).\n\n"
        f"LETZTER COMMIT (Format-Referenz):\n{letzter}\n\n"
        f"GIT STATUS (die zu committenden Dateien):\n{git_status}\n\n"
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
            build_system_prompt(state.agents["builder"], state.docs,
                                state.agent_docs.get("builder", [])),
            aufgabe,
            state.builder_model,
            state.builder_temp,
            state.llm_timeout_s,
            state=state,
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
        neu = doku_ziele[ziel].replace(patch["anker"], patch["ersatz"], 1)
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
    commit_argv += ["commit", "-F", str(msg_datei)]

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
        {"max_review_rounds": 5, "max_llm_calls": 30})

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
    global _AKTUELLE_RUN_ID
    _AKTUELLE_RUN_ID = (
        datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        + f"-{os.getpid()}")
    # Auflage 2183 A2: run_id auch in state.
    state.run_id = _AKTUELLE_RUN_ID

    audit("pipeline_start",
          {"aufgabe_hash": __import__("hashlib").sha256(aufgabe.encode()).hexdigest(),
           "aufgabe_kurz": aufgabe[:200],
           "llm_calls_start": 0},
          project_dir, project_name)

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

    print("[+] Basis-Gate gruen. Block startet.")

    # ==================================================================
    # SCHRITT 1: Reviewer waehlt optionale Messungen
    # ==================================================================
    print("\n[*] Schritt 1: Reviewer waehlt optionale Messungen.")

    doc_keys_reviewer = state.agent_docs.get("reviewer", [])
    reviewer_prompt = build_system_prompt(
        state.agents["reviewer"], state.docs,
        doc_keys_reviewer, state=state)

    historie = load_recent_commits(project_dir, n=10)

    overview = (
        "Basis-Gate (immer gelaufen, gruen):\n"
        + state.basis_protokoll[:1500]
        + "\n\nVerfuegbare optionale Messungen:\n"
        + "\n".join(f"  - {m.mid}: {m.beschreibung}" for m in optional.values())
    )
    reviewer_input = (
        aufgabe_block(state)
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
                    state=state)
    if not reply.ok:
        print(f"[FAIL] Reviewer: {reply.error}")
        audit("reviewer_call_failed", {"error": reply.error}, project_dir, project_name)
        return 2

    commands = parse_commands(reply.content)
    if commands:
        print(f"[i] Reviewer fordert {len(commands)} optionale Messungen.")
        execute_commands(state, commands, quelle="reviewer")
    else:
        print("[i] Reviewer fordert keine optionalen Messungen.")

    # ==================================================================
    # SCHRITT 2: Builder baut Code-Entwurf
    # ==================================================================
    print("\n[*] Schritt 2: Builder baut Code-Patches (UMB-1b).")
    builder_prompt = build_system_prompt(state.agents["builder"], state.docs,
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
        project_name)
    def _builder_user_prompt(s: RunState) -> str:
        """Auflage 2191b: baut den Builder-Prompt pro Runde
        frisch, damit GEMESSENER INHALT und ZIELDATEIEN den
        aktuellen state.mess_protokoll sehen.
        """
        zp = extract_paths_from_aufgabe(
            aufgabe, file_whitelist, project_dir)
        zs = read_target_snippets(
            zp, project_dir, file_whitelist,
            bereits_gemessen=_gemessene_pfade(s.mess_protokoll))
        anker_block = baue_anker_rueckmeldung(s)
        _ps_block = format_projekt_stand(s)
        return (
            aufgabe_block(s)
            + (_ps_block if _ps_block else "")
            + (anker_block if anker_block else "")
            +
            f"BASIS-GATE:\n{s.basis_protokoll[:1500]}\n\n"
            + format_doc_snippets(s.docs) + "\n\n"
            + zs + "\n\n"
            + f"GEMESSENER INHALT (verbindlich, gewinnt gegen "
            f"ZIELDATEIEN):\n{s.mess_protokoll or '(keine)'}\n\n"
            + "Liefere strukturierte Code-Patches im Format "
            "PATCH-BEGINN/PATCH-ENDE.\n"
            "Format und Einrueckungs-Regeln stehen im "
            "System-Prompt (Abschnitt 'EINRUECKUNG UND "
            "YAML-BLOCK').\n\n"
            "Mehrere Patches hintereinander "
            "(jeweils PATCH-BEGINN/PATCH-ENDE).\n"
            "Kein freier Text. Kein Markdown. Nur Patches.\n"
            "Wenn du einen Anker nicht im Ausschnitt findest: "
            "keinen Patch fuer diese Datei. Kein Erfinden."
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

    state.code_entwurf = reply.content
    state.code_patches = parse_code_patches(reply.content)
    print(f"[i] {len(state.code_patches)} Code-Patches geparst.")

    # ==================================================================
    # SCHRITT 3: Review-Schleife (Phase 1)
    # ==================================================================
    max_rounds = budget.get("max_review_rounds", 5)
    verdict = "UNKLAR"
    for runde in range(1, max_rounds + 1):
        # Auflage 2078: der inline-Budget-Check ist entfernt.
        # Der Check erfolgt direkt vor dem Reviewer-Call via
        # budget_or_recover (siehe unten).

        print(f"\n[--- Review-Runde {runde} ---]")

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
            bereits_gemessen=_gemessene_pfade(
                state.mess_protokoll))
        szenario = (
            # Auflage 2152: Auftrag MUSS im Szenario stehen.
            aufgabe_block(state)
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
            f"ZIELDATEIEN):\n{state.mess_protokoll or '(keine)'}\n\n"
            # Bug-Fix 2026-10-14: Nach-Apply-Block (Z4:
            # nur wenn vorhanden).
            + (f"GEMESSENER INHALT NACH APPLY:\n"
               f"{state.basis_protokoll_nach_apply}\n\n"
               if state.basis_protokoll_nach_apply else "")
            # Auflage 2177: Zieldatei-Ausschnitte.
            + ziel_snippets_rev + "\n\n"
            f"CODE-ENTWURF:\n{state.code_entwurf}\n\n"
            f"TEST-VORSCHLAEGE:\n{state.test_vorschlaege or '(keine)'}\n\n"
            "Bewerte. Erste Zeile: GO, NO-GO oder ESKALATION."
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
                              f"Vor Reviewer-Verdict Runde {runde}.",
                              project_dir, project_name,
                              max_minutes=max_minutes)
        if rc is not None:
            return rc
        reply = ask_llm(api_key, reviewer_prompt, szenario,
                        state.reviewer_verdict_model, 0.0, state.llm_timeout_s,
                        state=state)
        if not reply.ok:
            print(f"[FAIL] Reviewer: {reply.error}")
            audit("reviewer_call_failed", {"error": reply.error, "runde": runde},
                  project_dir, project_name)
            return 5

        verdict = classify_verdict(reply.content)
        # Auflage 2183 A1a: recovery-Marker an der Runde.
        # Heute immer False; der Setzer kommt in A3.
        state.review_runden.append(
            {"runde": runde, "verdict": verdict,
             "raw": reply.content, "recovery": False})
        state.auflagen_log.append(parse_auflagen(reply.content))
        state.empfehlung_log.append(parse_empfehlung(reply.content))
        audit("review_round", {"runde": runde, "verdict": verdict}, project_dir, project_name)

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
                                     quelle="reviewer")
            # Auflage 2145: Audit fuer COMMAND in der Review-
            # Schleife. Sonst ist nicht sichtbar, wann der
            # Reviewer COMMAND nutzt.
            audit("review_command",
                  {"runde": runde, "anzahl": len(cmds)},
                  project_dir, project_name)
            continue

        if verdict == "ESKALATION":
            print(f"[!] ESKALATION:\n{reply.content[:500]}")
            v = ask_reviewer_for_recovery(state, "eskalation", reply.content)
            print_recovery(v)
            audit("recovery_eskalation",
                  {"frage_an_menschen": v.frage_an_menschen[:500],
                   "empfehlung": v.empfehlung[:500]},
                  project_dir, project_name)
            return 14

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
                    continue
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
                return (
                    f"Reviewer NO-GO:\n{_reply.content}\n\n"
                    + _solver_befund_block(s)
                    + "GEMESSENER INHALT (verbindlich):\n"
                    + f"{s.mess_protokoll or '(keine)'}\n\n"
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
                state.code_entwurf = bauer_reply_roh.content
                state.code_patches = parse_code_patches(
                    bauer_reply_roh.content)
            continue

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
                        + f"{s.mess_protokoll or '(keine)'}\n\n"
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
                    state.code_entwurf = bauer_reply_roh.content
                    state.code_patches = parse_code_patches(
                        bauer_reply_roh.content)
                    print(f"[i] {len(state.code_patches)} Code-Patches "
                          f"nach Auflagen-Umsetzung geparst.")
                continue
            print("[+] Code-GO erhalten.")
            break

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
        if not state.commit_paket.get("message"):
            print("[!] Commit-Paket leer. Kein Commit moeglich.")
            state.commit_paket["message"] = "(leer, Builder hat nichts geliefert)"

        # Auflage 2191-R2b: Fail-closed, wenn mess_protokoll leer ist.
        # Phase 2 kann ohne Messung R7 nicht anwenden.
        if not state.mess_protokoll:
            print("[!] mess_protokoll leer. Commit-Review kann "
                  "Anker nicht pruefen (R7). Fail closed.")
            audit("commit_review_ohne_messung",
                  {"grund": "mess_protokoll_leer"},
                  project_dir, project_name)
            return _fail_closed(
                state, project_dir, project_name, 9,
                "commit_review_ohne_messung")

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

            # Auflage 2180 + BO: MESSWERTE-Block statt
            # veralteter DOKU-PATCHES-Zeilen.
            commit_input = (
                f"CODE-GO ist erteilt. Pruefe das Commit-Paket.\n\n"
                f"COMMIT-MESSAGE:\n{state.commit_paket.get('message', '')}\n\n"
                f"BETROFFENE DATEIEN:\n" +
                "\n".join(
                    f"  - {d}"
                    for d in state.commit_paket.get("dateien", [])) +
                "\n\n"
                + format_messwerte_block(collect_messwerte(state))
                + "\n\nGEMESSENER INHALT (verbindlich, "
                + "gewinnt gegen ZIELDATEIEN):\n"
                + f"{state.mess_protokoll or '(keine)'}\n\n"
                + (f"GEMESSENER INHALT NACH APPLY:\n"
                   f"{state.basis_protokoll_nach_apply}\n\n"
                   if state.basis_protokoll_nach_apply else "")
                + "CODE-PATCHES (angewendet):\n"
                + format_code_patches_fuer_commit(state.code_patches)
                + "\n\n"
                f"AUFLAGEN AUS DIESER RUNDE:\n{auflagen_text}\n\n"
                "Antworte mit COMMIT-GO, COMMIT-NO-GO oder "
                "COMMIT-ESKALATION."
            )
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
                            state=state)
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
                break

            if commit_verdict != "COMMIT-NO-GO":
                # ESKALATION / UNKLAR: Stop, Mensch entscheidet am Gate.
                print(f"[i] Commit-Review-Verdict: {commit_verdict}. "
                      "Kein Loop.")
                break

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

    # ==================================================================
    # SCHRITT 6: Approval-Dokument + Human-Gate
    # ==================================================================
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



def _phase_main_pfad(
    project_name: str,
    phasen_text: str,
    state_ref: list[RunState],
) -> int:
    global _AKTUELLE_RUN_ID
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

    # git status clean?
    try:
        _st = subprocess.run(
            ("git", "status", "--porcelain"),
            cwd=str(project_dir), capture_output=True,
            text=True, timeout=30, check=False,
            env=subprocess_env(),
        )
        if _st.returncode != 0 or _st.stdout.strip():
            print("[FAIL] Ziel-Repo nicht sauber (git status). "
                  "Fail closed.")
            print(_st.stdout[:500] if _st.stdout else "")
            audit("phase_basis_gate_failed",
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
    if plan_vorhanden is not None:
        print("[i] Aktiver Phasenplan gefunden. "
              "Ueberspringe Planner.")
        ups_plan = plan_vorhanden.get(
            "phase_unterbloecke", [])
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
            docs=docs, agents=agents, always={},
            optional={},
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
        state.start_monotonic = time.monotonic()
        # Resume-Fix: state_ref NICHT hier anhaengen.
        # run_phase macht das am Ende (Guard verlangt
        # leeren state_ref beim Aufruf).
        _AKTUELLE_RUN_ID = (
            datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
            + f"-{os.getpid()}")
        state.run_id = _AKTUELLE_RUN_ID
        audit("pipeline_start",
              {"aufgabe_hash": __import__("hashlib").sha256(
                  state.aufgabe.encode()).hexdigest(),
               "aufgabe_kurz": state.aufgabe[:200],
               "modus": "phase_resume"},
              project_dir, project_name)
        rc = run_phase(project_name, state, state_ref)
        _phase_finish_aktiv(project_name, state, rc)
        return rc

    # Historien.
    historie = load_recent_commits(project_dir, n=10)

    # RunState bauen (analog _planner_main_pfad).
    state = RunState(
        block_id=config.get("project", "unknown"),
        aufgabe=phasen_text,
        start_ts=datetime.now(UTC).isoformat(timespec="seconds"),
        docs=docs, agents=agents,
        always={}, optional={},
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

    _AKTUELLE_RUN_ID = (
        datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        + f"-{os.getpid()}")
    state.run_id = _AKTUELLE_RUN_ID

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
                audit("phase_plan_parse_failed",
                      {"runde": runde, "error": str(exc)},
                      project_dir, project_name)
                continue

            phase_plan_ok = True
            audit("planner_vorschlag",
                  {"runde": runde,
                   "titel": phase_titel[:200],
                   "laenge": len(antwort),
                   "stufe": 2},
                  project_dir, project_name)
            print(f"[+] Phasenplan erhalten (Runde {runde}).")
            aus_edit = False

        # Anzeige (A4, A6, A8).
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
            print(f"{u['id']}: {u['titel']}  "
                  f"({n_up} Unterpunkte, ~{n_rd} Runden)")
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


    # Historien.
    historie = load_recent_commits(project_dir, n=10)

    # RunState bauen (minimal, analog run_pipeline).
    state = RunState(
        block_id=config.get("project", "unknown"),
        aufgabe=roher_auftrag,
        start_ts=datetime.now(UTC).isoformat(timespec="seconds"),
        docs=docs, agents=agents,
        always={}, optional={},
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
    _AKTUELLE_RUN_ID = (
        datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        + f"-{os.getpid()}")
    state.run_id = _AKTUELLE_RUN_ID

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
            state.planner_vorschlag = vorschlag_text
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

    # Block P2a: --phase-Pfad. Reihenfolge: VOR --planner
    # (P2a-S5b-A1). Beide Bedingungen sind mit args[2]
    # exklusiv.
    if (len(args) >= 4 and args[0] == "--project"
            and args[2] == "--phase"):
        project_name = args[1].strip()
        phasen_text = args[3].strip()
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
                project_name, phasen_text, phase_state_ref)
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
