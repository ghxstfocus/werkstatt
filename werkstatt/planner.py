"""Planner-Agent (Phase 5, 2026-10-23).

Eigenstaendiger Planner. Liest Aufgabe + Kontext,
ruft ask_llm (JSON-Modus) auf, schreibt Plan in
state.tasks / state.tests / state.akzeptanzkriterien.

Kein Schreiben von Code. Kein Executor.
Reiner Denker (Codex Plan Mode).
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from werkstatt.agent import ask_llm
from werkstatt.loop_renderer import _with_spinner


# M-442: Architect-Modell konfigurierbar (Default: deepseek-chat).
# Fuer Messungen: WERKSTATT_ARCHITECT_MODEL=deepseek-reasoner
def _is_reasoning_model(model: str) -> bool:
    """M-445: Reasoning-Modelle unterstuetzen temperature/top_p nicht."""
    return "reasoner" in model.lower() or "r1" in model.lower()


_ARCHITECT_MODEL = os.environ.get("WERKSTATT_ARCHITECT_MODEL", "deepseek-chat")

from werkstatt.audit import audit
from werkstatt.state import RunState

# DEPRECATED (2026-10-29): PLANNER_SYSTEM wird im Gold-Pfad nicht
# mehr an das LLM gesendet. Der Architect-System-Prompt ist
# ARCHITECT_SYSTEM. Tests pruefen noch den Inhalt von
# PLANNER_SYSTEM (test_builder_agent.py::test_planner_prompt_m339,
# test_loop.py::test_planner_prompt_phasen_pflicht) — bleiben als
# Regressionsschutz, bis der Planner-Split umgestellt ist.
# Siehe Bau-Handoff, P0 (erledigt aa7881f) + docs/OFFENE-BLOECKE.md.
PLANNER_SYSTEM = """Du bist ein elite Software-Architekt und Planner.
Zerlege die Aufgabe in ausfuehrbare Tasks.

Jeder Task:
  - id, name, description
  - action: "read" | "create" | "update"
  - task_files: konkrete Datei-Pfade MIT Suffix (keine Ordner)
  - phase_id: optional, muss in phasen existieren

Phasen (Pflicht bei >5 Tasks oder Refactoring-Aufgaben):
  phasen: [{"id": "p1", "titel": "Analyse", "tasks": ["t1"]}]
  Jeder Task braucht dann eine phase_id.

Doku-Tasks sind VERBOTEN (docs/, CHANGELOG.md, README.md,
STATUS.md, PROGRESS.md). Doku schreibt der Loop.
Verstoesse werden vom Hook deterministisch geblockt.

Antworte NUR mit validem JSON:
{
  "phasen": [{"id": "p1", "titel": "...", "parent_id": null,
              "tasks": ["t1"]}],
  "tasks": [{"id": "t1", "name": "...", "description": "...",
             "action": "read"|"create"|"update",
             "task_files": ["pfad/zur/datei.py"],
             "phase_id": "p1",
             "akzeptanzkriterien": ["..."]}],
  "tests": ["..."],
  "akzeptanzkriterien": ["..."],
  "blocker": [{"klasse": "...", "text": "..."}],
  "follow_up": [{"klasse": "...", "text": "..."}],
  "ignore": [{"klasse": "...", "text": "..."}]
}

WICHTIG (wird vom Hook erzwungen):
  - action muss read/create/update sein.
  - task_files: Datei mit Suffix, KEINE Ordner, KEINE Wildcards.
  - Doku-Tasks verboten.
  - phase_id muss in phasen existieren.
"""


def _klassifiziere_fehler(stage_id: str, fehlertext: str) -> str:
    """M-299a: Klassifiziert einen Verify-Fehler nach Klasse.

    Klassen:
      env     — Umgebungsproblem (ModuleNotFoundError, ImportError)
      lint    — mechanisch (ruff --fix)
      type    — Typfehler (mypy)
      test    — Testfehler (pytest)
      syntax  — Syntaxfehler (py_compile)
      unknown — Sonstiges
    """
    # K9: Prefix-Match statt Gleichheit — verify.json liefert
    # py_compile_changed/py_compile_core, ruff_changed, pytest_changed.
    if stage_id.startswith("py_compile") or "SyntaxError" in fehlertext:
        return "syntax"
    if "ModuleNotFoundError" in fehlertext or "ImportError" in fehlertext:
        return "env"
    if stage_id.startswith("ruff"):
        return "lint"
    if stage_id.startswith("mypy"):
        return "type"
    if stage_id.startswith("pytest"):
        return "test"
    return "unknown"


def _preflight_scan(state: RunState) -> list[dict]:
    """M-299a: Liest verify.json, fuehrt Stages aus, klassifiziert Fehler.

    Liefert strukturierte Fehlerliste:
      [{klasse, stage_id, datei, text}, ...]

    Wird in state.preflight_fehler persistiert (vom Aufrufer).
    """
    import json
    import subprocess
    from pathlib import Path as _P

    pd = getattr(state, "project_dir", None)
    if pd is None:
        return []
    project_dir = _P(pd)

    contract = project_dir / ".werkstatt" / "verify.json"
    if not contract.exists():
        return []

    try:
        stages = json.loads(contract.read_text(encoding="utf-8")).get("stages", [])
    except (json.JSONDecodeError, OSError):
        return []

    fehler: list[dict] = []
    for stage in stages:
        cmd = stage.get("command")
        if not cmd:
            continue
        stage_id = stage.get("id", "?")
        try:
            res = subprocess.run(
                cmd, cwd=str(project_dir),
                capture_output=True, text=True, timeout=300, check=False,
            )
            if res.returncode == 0:
                continue
            stderr = (res.stderr or "") + (res.stdout or "")
            klasse = _klassifiziere_fehler(stage_id, stderr)
            # M-299i: Datei-Pfad aus Fehlertext extrahieren (deterministisch).
            # mypy/ruff: "path/to/file.py:ZEILE: ..." oder
            #            "path/to/file.py:ZEILE:SPALTE: CODE ..."
            _file_pattern = re.compile(r'([a-zA-Z0-9_./-]+\.(?:py|md|yaml|yml|json|txt|toml))')
            _dateien = _file_pattern.findall(stderr)
            _datei = _dateien[0] if _dateien else None
            fehler.append({
                "klasse": klasse,
                "stage_id": stage_id,
                "datei": _datei,
                "text": stderr[:500],
            })
        except Exception as exc:  # noqa: BLE001
            fehler.append({
                "klasse": "unknown",
                "stage_id": stage_id,
                "datei": None,
                "text": f"Exception: {exc}",
            })
    return fehler



_TOOL_CALL_TAGS = (
    "shell_command", "read_file", "write_file", "tool_call", "tool_result",
    "tool", "function", "function_calls", "invoke", "parameter",
    "antml:invoke", "antml:parameter",
)

_DSML_TOKEN = "\uff5c\uff5cDSML\uff5c\uff5c"


def _strip_xml_tags(text: str) -> str:
    """K7/K51/K52: Entfernt XML- und DSML-Tool-Call-Marker aus Prosa.

    K52: generischer Ansatz. Statt eine feste Tag-Liste zu pflegen
    (jedes LLM nutzt neue Marker: <tool_call>, <invoke>, <function_calls>,
    <read_file>, DSML-Special-Tokens), entfernen wir:
    - Bekannte Tag-Namen (Block + Einzel).
    - DSML-Special-Tokens (Unicode-Fullwidth-Pipes).
    - Verbleibende Bloecke <X>...</X> mit identischem Namen (rekursiv).
    """
    import re as _re
    # 1) K52: bekannte Tag-Namen als Block.
    _names = "|".join(_TOOL_CALL_TAGS)
    text = _re.sub(
        rf"<({_names})(?:[^>]*>|\s[^>]*>).*?</\1>",
        "",
        text,
        flags=_re.DOTALL,
    )
    # 2) K52: bekannte Tag-Namen als Einzel-Tag.
    text = _re.sub(
        rf"<({_names})[^>]*/?>",
        "",
        text,
        flags=_re.DOTALL,
    )
    # 3) K51: DSML-Special-Tokens.
    text = _re.sub(
        "<" + _DSML_TOKEN + r"[^>]*>.*?</" + _DSML_TOKEN + r"[^>]*>",
        "",
        text,
        flags=_re.DOTALL,
    )
    text = _re.sub(
        "<" + _DSML_TOKEN + r"[^>]*/?>",
        "",
        text,
        flags=_re.DOTALL,
    )
    # 4) K52: verbleibende <X>...</X>-Bloecke mit gleichem Namen
    #    (generisch, unabhaengig vom Tag-Namen).
    text = _re.sub(
        r"<([a-zA-Z_:][\w:.-]*)(?:\s[^>]*)?>.*?</\1>",
        "",
        text,
        flags=_re.DOTALL,
    )
    # 5) K52: verbleibende Einzel-Tags mit Attributen (kein
    #    Vergleichstext, z.B. <br>, <img>).
    text = _re.sub(
        r"<[a-zA-Z_:][\w:.-]*(?:\s[^>]*)?/?>",
        "",
        text,
    )
    return text.strip()


def _erledigte_punkte(pd) -> str:
    """K6: Sammelt erledigte Punkte aus git log + ROADMAP.md.

    Verhindert, dass der Architect bereits abgeschlossene
    Punkte erneut plant.
    """
    import re as _re
    import subprocess as _sp
    from pathlib import Path as _Path

    _teile: list[str] = []
    _pd = _Path(pd) if pd else _Path(".")
    try:
        res = _sp.run(
            ["git", "-C", str(_pd), "log", "--grep=✅", "--oneline", "-20"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        if res.stdout.strip():
            _teile.append("Commits mit ✅:\n" + res.stdout.strip())
    except Exception:  # noqa: BLE001
        pass

    # K6.1: ROADMAP.md UND STATUS.md als Signal.
    for _name, _rel in (
        ("ROADMAP", ("docs/ROADMAP.md", "ROADMAP.md")),
        ("STATUS", ("docs/STATUS.md", "STATUS.md")),
    ):
        _file = None
        for _cand in _rel:
            _cand_p = _pd / _cand
            if _cand_p.is_file():
                _file = _cand_p
                break
        if _file is None:
            continue
        try:
            _txt = _file.read_text(encoding="utf-8")
        except OSError:
            continue
        _matches = _re.findall(r"^.*✅.*$", _txt, flags=_re.MULTILINE)
        if _matches:
            _teile.append(
                f"{_name} ✅-Zeilen:\n" + "\n".join(_matches[:30])
            )

    return "\n\n".join(_teile)


ARCHITECT_SYSTEM = """Du bist ein elite Software-Architekt.
Beschreibe die Loesung in Prosa. KEIN JSON, KEIN Patch-Format.

Format (STRIKT einhalten):
  1. Was ist das Problem?
  2. Welche Datei(en) muessen geaendert werden?
  3. Wie sieht die Loesung aus?
     PRO DATEI EIN BLOCK. Innerhalb eines Blocks: EINE
     Funktion/Methode komplett (Signatur, Logik, Fehler,
     Rueckgabe) als zusammenhaengender Absatz. NICHT als
     nummerierte Schritte.
     Der Planner-Split schneidet die Prosa an Datei- und
     Funktionsgrenzen. Eine Task = ein reviewbares Interface.
     Beispiel GUT:
       "In app/foo.py: neue Funktion bar(x, y). Validiert
        x > 0, ruft helper(y), gibt Result zurueck. Bei
        Fehler: BarError."
     Beispiel SCHLECHT:
       "1. In bar(): validiere x. 2. In bar(): rufe
        helper(y). 3. In bar(): gib Result zurueck."
     Jede Funktion/Klasse ist EIN Block. Wenn eine Datei
     mehrere Funktionen hat: EIN Block pro Funktion.
  4. Welche Tests brauchen wir?

REGELN:
  - KEINE XML-Tags, KEINE DSML-Tool-Calls.
    Verboten: <shell_command>, <read_file>, <tool>, <function>,
    <function_calls>, <invoke>.
    Du bist Architekt, nicht Tool-Caller. Beschreibe die
    Loesung als Prosa.
  - Code muss ruff-konform sein (E, F, I, SIM, RUF, BLE).
  - __all__ sortiert.
  - Kein `except Exception` ohne `# noqa: BLE001`.
  - Max line-length 100.
  - Keine unbenutzten Variablen (F841).

API-STABILITAET (WICHTIG):
  - Bestehende API NIE umbenennen (z.B. ApplierError bleibt ApplierError).
  - Bestehende Signaturen NIE aendern ohne Not.
  - Bestehende Rueckgabetypen NIE aendern.
  - Neue Features: ADDITIV (neue Methoden, neue Klassen), nicht ersetzend.

FROZEN DATACLASSES:
  - Wenn ein Parameter `frozen=True` ist: NICHT setattr() aufrufen.
  - Nutze dict/separate Struktur fuer Zusatz-Daten.

DATEI-UEBERSCHRIFTEN (PFLICHT fuer jede Datei):

Fuer JEDE Datei, die du aenderst, schreibe eine eigene
Ueberschrift im Format "## <voller-pfad>". Diese Ueberschrift
wird vom Builder genutzt, um den richtigen Abschnitt zu finden.

Beispiel:
  ## 3. Wie sieht die Loesung aus?

  ## apps/dashboard/routes_state.py
  Neue Funktion _section_timeline()...

  ## apps/dashboard/static/js/dashboard.js
  Neue Funktion renderTimeline()...

Regeln:
  - Ueberschrift EXAKT der Dateipfad, KEIN Backtick, KEIN "Datei:".
  - Format: "## <pfad>" (zwei Rauten, dann Pfad).
  - Fuer jede Datei ein eigener Block.
  - Der Builder sucht "## <pfad>", um den Abschnitt zu finden.
  - Wenn du eine Datei ohne "## <pfad>"-Ueberschrift beschreibst,
    findet der Builder sie NICHT.

WENN NUR EINE DATEI BETROFFEN IST:
  Beschreibe sie direkt, mit "## <pfad>"-Ueberschrift.

GROESSEN-ZIEL:
  Eine Funktion/Methode = 50-150 Zeilen Code. Zu klein
  (< 30 Zeilen) -> kein reviewbares Interface. Zu gross
  (> 200 Zeilen) -> Semantik-Verlust im Builder.

TESTS SIND OUT-OF-SCOPE:
  Beschreibe KEINE Test-Dateien (tests/*, test_*.py, *_test.py).
  Beschreibe KEINE Aenderungen an Test-Dateien. Tests werden
  vom Menschen geschrieben, nicht vom Loop. Wenn deine Loesung
  Tests braucht: beschreibe nur, welche Faelle getestet werden
  sollten, nicht den Test-Code selbst.

MIGRATIONS-NUMMERN:
  - Wenn eine Migration noetig ist: pruefe data/migrations/.
  - Nimm die hoechste vorhandene Nummer +1.
  - Nummern-Kollision ist ein Review-Fail.
  - Nutze NIEMALS eine Nummer, die bereits als Datei existiert.

Antworte NUR mit diesem Prosa-Text. Kein Code, nur Beschreibung.

## GOLD: SCOUT-KONTEXT
Du bekommst im User-Content:
- "SCOUT-AUFTRAG" (vorformuliert).
- "VERFUEGBARE APIS (aus Code-Index)".

Nutze die APIs aus "VERFUEGBARE APIS" -- NICHT die aus der Aufgabe.
Wenn die Aufgabe eine API nennt, die nicht im API-Auszug steht:
  Nenne sie NICHT. Nutze die aehnlichste echte API.
Beispiel: Aufgabe sagt "read_events". API-Auszug hat
"list_recent_assessments". Nutze list_recent_assessments.
"""


PLANNER_SPLIT_SYSTEM = """Du bist ein Task-Zerleger.
Du bekommst eine Architect-Prosa und eine Liste von Dateien.
Zerlege die Prosa in so viele Sub-Tasks wie noetig (typisch 3-10).
Nicht mehr, nicht weniger als die Aufgabe braucht.

Jeder Sub-Task:
- id: "t1", "t2", ... (aufsteigend)
- name: kurzer Titel (< 50 Zeichen)
- action: "update" (Datei existiert) oder "create" (neue Datei)
- task_files: Liste der Dateien, die dieser Sub-Task aendert
  (max 1 Datei pro Task, wenn moeglich)
- architect_start: ERSTE Zeile des Architect-Abschnitts,
  der zu diesem Task gehoert (woertliches Zitat, z.B. "5. Backup").
  FUER __init__.py-Tasks: verwende den exakten Schritt, z.B.
  "15. In __init__.py: __all__ alphabetisch sortieren".
- architect_ende: LETZTE Zeile des Architect-Abschnitts
  (woertliches Zitat, z.B. "6. Anwenden").
  WICHTIG: architect_start und architect_ende muessen BENACHBARTE
  nummerierte Schritte sein (max 3 Schritte dazwischen).
  Wenn ein Task nur 1 Schritt umfasst, setze start = ende.
- dependencies: Liste von Task-IDs, die vorher fertig sein muessen.

Regeln:
  - INTERFACE-GRENZE: Jede Task liefert EIN vollstaendiges,
    reviewbares Interface — nicht einen Schritt einer Funktion.
    Beispiel GUT: eine Funktion/Methode komplett (Eingabepruefung,
    Kernlogik, Fehlerbehandlung, Rueckgabe) als EINE Task.
    Beispiel SCHLECHT: Eingabepruefung / Kernlogik / Fehler-
    behandlung als getrennte Tasks fuer dieselbe Funktion.
  - Groesse: 50-150 Zeilen Code pro Task. Zu klein (< 30 Zeilen):
    Reviewer sieht kein Feature. Zu gross (> 200 Zeilen):
    Semantik geht verloren.
  - Eine Datei mit N unabhaengigen Funktionen/Klassen:
    EINE Task pro Einheit, nicht pro Schritt.
  - Eine Datei mit EINER Funktion/Klasse: EINE Task fuer die
    ganze Einheit — nicht in Schritte aufteilen.
  - Keine Test-Dateien (tests/*).
  - architect_start und architect_ende MUESSEN woertlich in
    der Architect-Prosa vorkommen. Der Loop extrahiert dann
    den Text dazwischen.

Antworte NUR mit JSON:
{
  "tasks": [
    {"id": "t1", "name": "...", "action": "update",
     "task_files": ["..."], "architect_start": "...",
     "architect_ende": "...", "dependencies": []},
    ...
  ]
}
Keine Erklaerung, nur JSON."""

PLANNER_SPLIT_SINGLE_SYSTEM = """Du bist ein Task-Zerleger.
Du bekommst EINEN zu grossen Sub-Task (Description > 2000 Zeichen
oder vom Builder als zu gross gemeldet).
Zerlege ihn in 2-3 kleinere Sub-Tasks.

Jeder Sub-Task:
- id: "tN_a", "tN_b", ... (abgeleitet von der Original-ID)
- name: kurzer Titel (< 50 Zeichen)
- action: "update" oder "create"
- task_files: Liste der Dateien (max 1)
- architect_start: ERSTE Zeile des Architect-Abschnitts (woertlich)
- architect_ende: LETZTE Zeile (woertlich, benachbart zu start)
- dependencies: Liste von Task-IDs

Regeln:
  - Jede Sub-Task liefert ein vollstaendiges, reviewbares
    Interface (nicht einen Schritt). Max 3 Sub-Tasks.
  - Groesse: 50-150 Zeilen Code pro Sub-Task.
  - architect_start und architect_ende MUESSEN woertlich
    in der Architect-Prosa vorkommen.

Antworte NUR mit JSON:
{
  "tasks": [
    {"id": "...", "name": "...", "action": "update",
     "task_files": ["..."], "architect_start": "...",
     "architect_ende": "...", "dependencies": []},
    ...
  ]
}
Keine Erklaerung, nur JSON."""




def _migrations_stand(pd) -> str:
    """K17: Deterministischer Migrationsstand fuer Architect-Kontext.

    Liest data/migrations/ und liefert eine kurze, sortierte Liste
    der vorhandenen Nummern + die hoechste Nummer explizit. Wird
    NUR eingefuegt, wenn Dateien vorhanden sind. Kein Fehlerfall
    propagiert (fail-soft, Kontext ist Zusatzinfo).
    """
    try:
        from pathlib import Path as _P
        mdir = _P(str(pd)) / "data" / "migrations"
        if not mdir.is_dir():
            return ""
        files = sorted(f.name for f in mdir.glob("*.sql") if f.is_file())
        if not files:
            return ""
        nums = []
        for name in files:
            head = name.split("_", 1)[0]
            if head.isdigit():
                nums.append(head)
        if not nums:
            return ""
        hoechste = max(nums)
        naechste = f"{int(hoechste) + 1:04d}"
        # K17b: Kompakter pflicht-Block (Lost-in-the-Middle-Schutz).
        # Nur Fakten: hoechste Nr., naechste freie Nr., Sperrliste.
        gesperrt = ", ".join(f"{n}_*" for n in sorted(set(nums))[-5:])
        lines = [
            "<migrationsstand pflicht=\"true\">",
            f"Hoechste vorhandene Nummer: {hoechste}",
            f"Naechste freie Nummer: {naechste}",
            f"VERBOTEN (bereits belegt): {gesperrt}",
            "Waehle fuer neue Migrationen NUR die naechste freie Nummer.",
            "Eine andere Nummer fuehrt zu einem Review-Fail und Loop-Abbruch.",
            "</migrationsstand>",
        ]
        return "\n".join(lines)
    except Exception:  # noqa: BLE001
        return ""


def _pruefe_migrations_kollision(
    prosa: str, pd,
) -> list[dict]:
    """K17b: Deterministische Migrations-Kollision pruefen.

    Sucht in der Architect-Prosa nach 'data/migrations/NNNN_*.sql'
    und prueft, ob NNNN als Datei bereits existiert. Gibt Liste
    von Kollisionen zurueck (leer = OK).

    Fail-soft: bei IO-Fehler (Ordner fehlt) -> leere Liste.
    """
    try:
        import re
        from pathlib import Path as _P
        mdir = _P(str(pd)) / "data" / "migrations"
        if not mdir.is_dir():
            return []
        existierend = set()
        for f in mdir.glob("*.sql"):
            head = f.name.split("_", 1)[0]
            if head.isdigit():
                existierend.add(head)
        geplant = re.findall(r"data/migrations/(\d+)_", prosa)
        kollisionen: list[dict] = []
        for n in sorted(set(geplant)):
            if n in existierend:
                kollisionen.append({"nummer": n, "existiert": True})
        return kollisionen
    except Exception:  # noqa: BLE001
        return []


# =====================================================
# GOLD: Agent-Schnittstellen (kompakt, deterministisch)
# =====================================================

_BUILDER_SCHNITTSTELLE = """## DER BUILDER (Schnittstelle)
- Modell: deepseek-chat, max 8000 Tokens.
- Input: eine Zieldatei + dein Abschnitt fuer diese Datei.
- Output: JSON-Patch mit old_string (aus Datei) + new_string (deine Beschreibung).
- Grenzen: keine Tools, keine API-Raterei, keine Imports ohne explizite Nennung.
- Du musst liefern: "## <pfad>", Interface (Signatur), Logik, Integration, Imports.
"""

_ARCHITECT_SCHNITTSTELLE = """## DER ARCHITECT (Schnittstelle)
- Liefert: Prosa mit "## <pfad>", Interface, Logik, Integration.
- Plant modular: welche Datei, welche Klasse, welcher Datenfluss.
- Modell: deepseek-reasoner.
"""

_REVIEWER_SCHNITTSTELLE = """## DER REVIEWER (Schnittstelle)
- Prueft: bricht der Code? Task erfuellt? Bestehende Aufrufe erhalten?
- HIGH-Bug wenn: bestehender Aufruf entfernt, Funktion ueberschrieben, API erfunden.
"""

_SCOUT_NACHFOLGER_BLOCK = """## DEIN NACHFOLGER
Der Architect bekommt deinen `auftrag_prosa` + `api_auszug`.
Der Planner zerlegt seine Prosa in Tasks.
Der Builder baut pro Datei einen Patch.

WICHTIG: Du lieferst JSON (mit "auftrag_prosa" als Prosa-Text).
Der Architect liefert Prosa mit "## <pfad>"-Ueberschriften.
Du musst NICHT "## <pfad>" liefern -- nur den Auftrag formulieren.
"""


SCOUT_SYSTEM = """Du bist ein Scout.
Du formulierst einen Auftrag fuer den Architect.

## DEIN INPUT
- Die Aufgabe des Users (vage Idee).
- Der Code-Index (deterministisch aus AST): alle Module, Klassen,
  Funktionen, Signaturen, Imports.
- Die vom Explorer gemessenen Dateien.

## DEIN OUTPUT (JSON + Prosa)
{
  "ziel": "Was soll gebaut werden? (1-2 Saetze)",
  "relevante_dateien": [
    {"pfad": "...", "zeilen": [..], "warum": "..."}
  ],
  "api_auszug": {
    "pfad/der/datei.py": ["Klasse.method(args) -> return", "..."]
  },
  "vorgeschlagene_aenderungen": [
    "Neue Funktion _section_timeline in routes_state.py",
    "In dashboard_state additiv einbinden"
  ],
  "risiken": [
    "API X hat RBAC alert.view, nicht audit.read"
  ],
  "auftrag_prosa": "Ausformulierter Auftrag fuer den Architect (3-10 Saetze)"
}

## WICHTIG: WIDERSPRUCH-CHECK (STRIKT)

Der Auftrag nennt oft APIs, die es NICHT gibt (z.B. read_events()).
Pruefe JEDE im Auftrag genannte API gegen den Code-Index:

1. Ist die API im Code-Index? (Klasse, Methode, Signatur)
2. Wenn NICHT: als Risiko nennen.
3. Echte API suchen (aehnlicher Name, andere Klasse).
4. Im auftrag_prosa NUR echte APIs aus dem Code-Index nennen.

## BEISPIEL
- Auftrag sagt: "Nutze read_events(limit=15) aus core.audit_reader."
- Code-Index zeigt: "AuditReaderService.list_recent_assessments(actor, limit=100)"
- Risiko: "read_events existiert nicht in core.audit_reader. Echte API: AuditReaderService.list_recent_assessments"
- auftrag_prosa: "Nutze AuditReaderService.list_recent_assessments(principal, limit=15)"

## REGEL
- Nenne NUR APIs, die im Code-Index stehen.
- Erfinde KEINE APIs.
- Uebernimm KEINE APIs aus dem Auftrag, wenn sie nicht im Code-Index sind.
- Nenne konkrete Zeilen und Datei-Pfade.

## DEIN NACHFOLGER

Der Architect bekommt deinen Auftrag + die Datei-Inhalte und liefert Prosa.
Der Planner zerlegt in Tasks.
Der Builder baut pro Datei einen Patch.
"""


def _baue_api_index(project_dir) -> dict:
    """GOLD: Deterministischer API-Index (AST).

    Liefert fuer jede .py-Datei:
    - __all__ (falls vorhanden)
    - Klassen (mit Methoden + Signaturen)
    - Top-Level-Funktionen (mit Signaturen + Rueckgabetypen)
    - Imports (from X import Y)
    """
    import ast as _ast
    from pathlib import Path as _Path

    _pd = _Path(project_dir)
    _ignore = {
        ".venv", "venv", "__pycache__", "site-packages",
        "node_modules", ".git", ".tox", ".mypy_cache",
        ".pytest_cache", ".ruff_cache", ".eggs", "build", "dist",
    }
    index: dict = {}
    for _f in _pd.rglob("*.py"):
        if any(p in _ignore for p in _f.parts):
            continue
        try:
            _src = _f.read_text(encoding="utf-8", errors="replace")
            _tree = _ast.parse(_src)
        except (OSError, SyntaxError):
            continue
        _rel = str(_f.relative_to(_pd))
        _entry = {
            "all": [],
            "classes": [],
            "functions": [],
            "imports": [],
        }
        for _node in _tree.body:
            if isinstance(_node, _ast.Assign):
                for _t in _node.targets:
                    if isinstance(_t, _ast.Name) and _t.id == "__all__":
                        try:
                            _val = _ast.literal_eval(_node.value)
                            _entry["all"] = list(_val) if isinstance(_val, (list, tuple)) else []
                        except (ValueError, SyntaxError):
                            pass
            elif isinstance(_node, _ast.ClassDef):
                _methods = []
                for _m in _node.body:
                    if isinstance(_m, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                        _args = [a.arg for a in _m.args.args]
                        _ret = ""
                        if _m.returns:
                            try:
                                _ret = _ast.unparse(_m.returns)
                            except (AttributeError, ValueError):
                                pass
                        _methods.append({
                            "name": _m.name,
                            "args": _args,
                            "return": _ret,
                        })
                _entry["classes"].append({
                    "name": _node.name,
                    "methods": _methods,
                })
            elif isinstance(_node, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                _args = [a.arg for a in _node.args.args]
                _ret = ""
                if _node.returns:
                    try:
                        _ret = _ast.unparse(_node.returns)
                    except (AttributeError, ValueError):
                        pass
                _entry["functions"].append({
                    "name": _node.name,
                    "args": _args,
                    "return": _ret,
                })
            elif isinstance(_node, _ast.ImportFrom):
                _mod = _node.module or ""
                _names = [a.name for a in _node.names]
                _entry["imports"].append({
                    "from": _mod,
                    "names": _names,
                })
            elif isinstance(_node, _ast.Import):
                for _a in _node.names:
                    _entry["imports"].append({"import": _a.name})
        index[_rel] = _entry
    return index


def _format_api_index_for_prompt(index: dict, max_files: int = 40) -> str:
    """Deterministisch: API-Index -> Prompt-Text."""
    lines = []
    for i, (f, info) in enumerate(index.items()):
        if i >= max_files:
            lines.append(f"... und {len(index) - max_files} weitere Dateien")
            break
        _parts = []
        if info.get("all"):
            _parts.append(f"__all__: {', '.join(info['all'][:8])}")
        for _c in info.get("classes", [])[:5]:
            _methods = ", ".join(m["name"] for m in _c["methods"][:8])
            _parts.append(f"class {_c['name']}({_methods})")
        for _fn in info.get("functions", [])[:5]:
            _args = ", ".join(_fn["args"])
            _ret = f" -> {_fn['return']}" if _fn["return"] else ""
            _parts.append(f"def {_fn['name']}({_args}){_ret}")
        _sig = " | ".join(_parts) if _parts else "(kein oeffentliches API)"
        lines.append(f"- {f}: {_sig}")
    return "\n".join(lines)


def _finde_api(index: dict, name: str) -> list:
    """Deterministisch: sucht eine API (Funktion/Klasse/Methode) im Index."""
    _matches = []
    for _pfad, _info in index.items():
        for _fn in _info.get("functions", []):
            if _fn["name"] == name:
                _matches.append({
                    "pfad": _pfad,
                    "kind": "function",
                    "name": _fn["name"],
                    "args": _fn["args"],
                    "return": _fn["return"],
                })
        for _c in _info.get("classes", []):
            if _c["name"] == name:
                _matches.append({
                    "pfad": _pfad,
                    "kind": "class",
                    "name": _c["name"],
                    "methods": [m["name"] for m in _c["methods"]],
                })
            for _m in _c["methods"]:
                if _m["name"] == name:
                    _matches.append({
                        "pfad": _pfad,
                        "kind": "method",
                        "class": _c["name"],
                        "name": _m["name"],
                        "args": _m["args"],
                        "return": _m["return"],
                    })
    return _matches



def _architect_system_with_builder() -> str:
    """GOLD: ARCHITECT_SYSTEM + _BUILDER_SCHNITTSTELLE."""
    return ARCHITECT_SYSTEM + "\n\n" + _BUILDER_SCHNITTSTELLE


def _scout_system_with_nachfolger() -> str:
    """GOLD: SCOUT_SYSTEM + _SCOUT_NACHFOLGER_BLOCK."""
    return SCOUT_SYSTEM + "\n\n" + _SCOUT_NACHFOLGER_BLOCK


def _planner_system(aufgabe: str, explorer_ctx: dict | None = None) -> str:
    """M-376: Explorer-Dateien ZUERST (Lost-in-the-Middle).

    Goldstandard: Relevante Information an den Anfang des
    Kontexts. Die gemessenen Dateien sind die wichtigste
    Information — sie stehen VOR PLANNER_SYSTEM.
    """
    parts: list[str] = []

    # === K32: MIGRATIONSSTAND ZUERST (hoechste Prioritaet) ===
    # Der Architect darf Migrationsnummern NICHT raten.
    _mig_ctx = None
    if isinstance(explorer_ctx, dict):
        _mig_ctx = explorer_ctx.get("migrations")
    if isinstance(_mig_ctx, dict) and _mig_ctx.get("hoechste"):
        parts.append(
            "<migrationsstand pflicht=\"true\">\n"
            f"Hoechste belegte Migrationsnummer: {_mig_ctx['hoechste']}\n"
            f"Naechste freie Nummer: {_mig_ctx['naechste']}\n"
            f"VERBOTEN (belegt): {', '.join(n + '_*' for n in _mig_ctx.get('alle', [])[-5:])}\n"
            "Verwende fuer neue Migrationen NUR die naechste freie Nummer.\n"
            "Kollisionen fuehren zu Review-Fail und Loop-Abbruch.\n"
            "</migrationsstand>"
        )

    # === M-376: GEMESSENE DATEIEN ZUERST (hoechste Prioritaet) ===
    if isinstance(explorer_ctx, dict):
        _key = explorer_ctx.get("key_files") or []
        _files = [
            k.get("file") for k in _key
            if isinstance(k, dict) and k.get("file")
        ]
        if _files:
            _files_str = "\n".join(f"  - {f}" for f in _files)
            parts.append(
                "<measured_files>\n"
                f"Der Explorer hat {len(_files)} Datei(en) mit Fehlern "
                f"gemessen (deterministisch, nicht geraten):\n"
                f"{_files_str}\n"
                "</measured_files>"
            )
            parts.append(
                "<pflicht>\n"
                f"DEINE TASKS MUESSEN GENAU DIESE {len(_files)} DATEIEN "
                f"VERWENDEN.\n"
                "Erfinde KEINE anderen Dateien. KEINE generischen Tasks "
                "wie 'Datei 1', 'Datei 2'.\n"
                "Jeder Task nennt eine dieser Dateien mit action=update.\n"
                f"Die {len(_files)} Dateien sind: {', '.join(str(f) for f in _files)}\n"
                "</pflicht>"
            )

        else:
            # M-405: Keine key_files -> KEIN <pflicht>
            parts.append(
                "<hinweis>\n"
                "Keine Dateien gemessen. Nutze <tools> (grep, read_file).\n"
                "Die findings enthalten Hinweise.\n"
                "</hinweis>"
            )

    # === GOLD: Architect-Modus IMMER (nicht nur bei "architect") ===
    # Der Architect liefert Prosa, _zerlege_in_sub_tasks macht
    # daraus Tasks. Zwei Agents, zwei Calls.
    if True:
        # M-446: Architect-Modus -> NUR ARCHITECT_SYSTEM + measured_files.
        # Keine Skills (Tool-Definitionen triggern deepseek-reasoner
        # zu DSML-Tool-Calls statt Prosa), kein <doku_verbot>,
        # kein <task_groesse>.
        _arch_parts: list[str] = []
        if isinstance(explorer_ctx, dict):
            _arch_key = explorer_ctx.get("key_files") or []
            _arch_files = [
                k.get("file") for k in _arch_key
                if isinstance(k, dict) and k.get("file")
            ]
            if _arch_files:
                _arch_str = "\n".join(f"  - {f}" for f in _arch_files)
                _arch_parts.append(
                    "<measured_files>\n"
                    f"Der Explorer hat {len(_arch_files)} Datei(en) "
                    f"gemessen:\n{_arch_str}\n"
                    "</measured_files>"
                )
        _arch_parts.append(ARCHITECT_SYSTEM)
        return "\n\n".join(_arch_parts)
def _normalisiere(text: str) -> str:
    """M-463: Entfernt Backticks, mehrfache Leerzeichen.

    Damit Marker wie "1. In `applier.py`" und "1. In applier.py"
    matchen.
    """
    import re as _re
    text = text.replace("`", "")
    text = _re.sub(r"\s+", " ", text)
    return text.strip()


def _segmentiere_nach_pfad(prosa: str) -> list[dict]:
    """Deterministisch: zerlegt Prosa an "## <pfad>"-Ueberschriften.

    Liefert Liste von {"datei": str, "prosa": str}.
    Reine Textverarbeitung, kein LLM.
    """
    import re as _re
    segs: list[dict] = []
    pat = _re.compile(r"^##\s+(\S+\.py)\s*$", _re.MULTILINE)
    ms = list(pat.finditer(prosa))
    for i, m in enumerate(ms):
        start = m.start()
        ende = ms[i + 1].start() if i + 1 < len(ms) else len(prosa)
        segs.append({
            "datei": m.group(1),
            "prosa": prosa[start:ende].strip(),
        })
    return segs


def _extrahiere_prosa_abschnitt(
    prosa: str, start: str, ende: str,
) -> str:
    """M-461/M-463: Extrahiert woertlichen Prosa-Abschnitt zwischen Markern.

    Sucht erst woertlich, dann normalisiert (ohne Backticks).
    Fallback: leerer String (NICHT ganze Prosa).
    """
    if not start:
        return ""
    # 1. Woertliche Suche.
    i_start = prosa.find(start)
    if i_start < 0:
        # 2. Normalisierte Suche.
        _p_norm = _normalisiere(prosa)
        _s_norm = _normalisiere(start)
        i_start_norm = _p_norm.find(_s_norm)
        if i_start_norm < 0:
            return ""
        # Position im Original: erstes Wort des Markers.
        _erstes_wort = start.split()[0] if start.split() else start
        i_start = prosa.find(_erstes_wort)
        if i_start < 0:
            return ""
    if not ende or ende == start:
        return prosa[i_start:]
    i_ende = prosa.find(ende, i_start + len(start))
    if i_ende < 0:
        _ende_wort = ende.split()[0] if ende.split() else ende
        i_ende = prosa.find(_ende_wort, i_start + len(start))
        if i_ende < 0:
            return prosa[i_start:]
    _result = prosa[i_start:i_ende + len(ende)]
    # K15c: Laengen-Begrenzung an Block-Format angepasst.
    # M-466 hatte 800 Zeichen (Mini-Task-Zeitalter). K15/K15b
    # produzieren ganze Funktions-Bloecke; 800 schnitt den
    # Konstruktor ab. 2500 = ~150-200 Zeilen Code.
    if len(_result) > 2500:
        _cut = _result.rfind(".", 0, 2500)
        if _cut > 0:
            _result = _result[:_cut + 1]
        else:
            _result = _result[:2500]
    return _result


def _llm_split_einzel_task(
    prosa: str, task: dict, api_key: str, pd, pn,
) -> list[dict]:
    """M-469: Zerlegt EINEN zu grossen Task in 2-3 Sub-Tasks (LLM)."""
    import json as _json
    _user = (
        f"## ZU GROSSER TASK:\n"
        f"id: {task.get('id')}\n"
        f"name: {task.get('name')}\n"
        f"description (Laenge {len(task.get('description', ''))}):\n"
        f"{task.get('description', '')[:3000]}\n\n"
        f"## ARCHITECT-PROSA (Kontext):\n{prosa[:4000]}"
    )
    reply = _with_spinner(
        f"Split-{task.get('id', '?')}",
        lambda: ask_llm(
            api_key, PLANNER_SPLIT_SINGLE_SYSTEM, _user,
            model="deepseek-chat", temperature=0.2, max_tokens=4000,
        ),
    )
    if not reply.ok:
        return []
    raw = reply.content.strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start < 0 or end <= start:
        return []
    try:
        parsed = _json.loads(raw[start:end])
    except _json.JSONDecodeError:
        return []
    tasks_raw = parsed.get("tasks", [])
    if not isinstance(tasks_raw, list):
        return []
    out: list[dict] = []
    for i, t in enumerate(tasks_raw, 1):
        if not isinstance(t, dict):
            continue
        _start = t.get("architect_start") or ""
        _ende = t.get("architect_ende") or ""
        _abschnitt = _extrahiere_prosa_abschnitt(prosa, _start, _ende)
        if not _abschnitt and not _start:
            _tf = t.get("task_files") or task.get("task_files") or []
            _ziel = _tf[0] if _tf else ""
            if _ziel:
                for _seg in _segmentiere_nach_pfad(prosa):
                    if _seg["datei"] == _ziel or _seg["datei"].endswith("/" + _ziel) or _ziel.endswith(_seg["datei"]):
                        _abschnitt = _seg["prosa"]
                        break
        if not _abschnitt:
            _name = t.get("name") or ""
            _desc = t.get("description") or ""
            _abschnitt = f"## TASK: {_name}\n{_desc}" if _desc else _name
        # K19b: 2500 statt 800 -- konsistent mit K15c-Extraktor.
        if len(_abschnitt) > 2500:
            _cut = _abschnitt.rfind(".", 0, 2500)
            _abschnitt = _abschnitt[:_cut + 1] if _cut > 0 else _abschnitt[:2500]
        out.append({
            "id": t.get("id") or f"{task.get('id', 't')}_{i}",
            "name": t.get("name") or f"Sub {i}",
            "action": t.get("action", "update"),
            "task_files": t.get("task_files") or task.get("task_files") or [],
            "dependencies": t.get("dependencies") or [],
            "description": _abschnitt,
        })
    return out


def _korrigiere_aktion(task: dict, pd, pn: str) -> None:
    """K20: Korrigiert action anhand Datei-Existenz (deterministisch).

    - action='update' + Datei fehlt -> action='create'
    - action='create' + Datei existiert -> action='update'

    Mehrere task_files: pruefe JEDE. Bei gemischtem Zustand
    (manche existieren, manche nicht) -> keine Aenderung
    (unsicher, Architect oder Gate soll entscheiden).
    Audit-Eintrag pro Korrektur.
    """
    try:
        act = task.get("action", "update")
        if act not in ("update", "create"):
            return
        files = task.get("task_files") or []
        if not files or not isinstance(files, list):
            return
        from pathlib import Path as _P
        pd_path = _P(str(pd))
        zustaende = []
        for f in files:
            if not isinstance(f, str) or not f:
                return  # ungueltig, nicht anfassen
            zustaende.append((pd_path / f).is_file())
        if len(set(zustaende)) != 1:
            # Gemischt -- unsicher, nicht anfassen.
            return
        exists = zustaende[0]
        if act == "update" and not exists:
            task["action"] = "create"
            audit("planner_action_korrigiert", {
                "dateien": files, "von": "update", "nach": "create",
                "grund": "datei_fehlt",
            }, pd_path, pn)
        elif act == "create" and exists:
            task["action"] = "update"
            audit("planner_action_korrigiert", {
                "dateien": files, "von": "create", "nach": "update",
                "grund": "datei_existiert",
            }, pd_path, pn)
    except Exception:  # noqa: BLE001
        return


def _korrigiere_aktion_sequenziell(tasks: list[dict], pd, pn: str) -> None:
    """K20b: Beruecksichtigt Task-Reihenfolge.

    Problem: Architect plant t1=create + t2=create auf selber Datei.
    Sequentiell korrekt, aber K20 isoliert sieht beide als create
    (Datei fehlt beim Plan-Zeitpunkt).

    Fix: nach _korrigiere_aktion, iteriere in Reihenfolge.
    Merke 'wird angelegt bis Position'. Wenn Task an Position i
    auf Datei X create und X bereits (durch frueheren Task)
    angelegt wird -> update.
    """
    try:
        # Set: Datei wird bis jetzt angelegt.
        angelegt_bis: set[str] = set()
        for t in tasks:
            if not isinstance(t, dict):
                continue
            act = t.get("action", "update")
            files = t.get("task_files") or []
            if not isinstance(files, list):
                continue
            _alle_existieren = all(
                isinstance(f, str) and f in angelegt_bis
                for f in files
            )
            if act == "create" and _alle_existieren and files:
                t["action"] = "update"
                audit("planner_action_korrigiert", {
                    "dateien": files, "von": "create", "nach": "update",
                    "grund": "frueherer_task_legt_an",
                }, pd, pn)
            elif act == "create":
                for f in files:
                    if isinstance(f, str):
                        angelegt_bis.add(f)
    except Exception:  # noqa: BLE001
        return


def _merge_mini_tasks(tasks: list[dict], max_merged_len: int = 1800) -> list[dict]:
    """K15a: Merged benachbarte Tasks mit gleicher Zieldatei.

    Der LLM-Split zerlegt eine Funktion oft in 3-4 Mini-Tasks
    (Validierung / Kernlogik / Fehler / Rueckgabe). Keine ist
    allein reviewbar. Diese deterministische Nachbearbeitung merged
    aufeinanderfolgende Tasks mit gleicher task_files[0], solange
    die kombinierte desc_len <= max_merged_len bleibt.

    Andere Dateien und action-Wechsel (create <-> update) blocken
    den Merge.
    """
    if not tasks:
        return tasks

    # K41: zaehlt Merges pro Datei -- max 2 kombinierte Mini-Tasks
    # pro Zieldatei. Sonst entsteht ein Mega-Task (>200 Zeilen Code),
    # den der Builder nicht sauber baut.
    _merge_count: dict[str, int] = {}
    merged: list[dict] = []
    for t in tasks:
        if not merged:
            merged.append(dict(t))
            continue

        prev = merged[-1]
        prev_file = (prev.get("task_files") or [None])[0]
        cur_file = (t.get("task_files") or [None])[0]
        prev_act = prev.get("action", "update")
        cur_act = t.get("action", "update")

        same_file = prev_file is not None and prev_file == cur_file
        same_act = prev_act == cur_act
        combined_len = (
            len(prev.get("description", "")) + len(t.get("description", ""))
        )

        # K41: pro Datei max 2 Merges (d.h. max 2 Mini-Tasks zusammengefasst).
        _file_key = prev_file if isinstance(prev_file, str) else "_none_"
        _at_limit = _merge_count.get(_file_key, 0) >= 2

        if same_file and same_act and combined_len <= max_merged_len and not _at_limit:
            _merge_count[_file_key] = _merge_count.get(_file_key, 0) + 1
            # K36: Merge-Audit -- sichtbar machen, welche Tasks gemergt werden.
            _merge_audit = {
                "prev_id": prev.get("id"),
                "prev_file": prev_file,
                "prev_action": prev_act,
                "cur_id": t.get("id"),
                "cur_file": cur_file,
                "cur_action": cur_act,
                "combined_len": combined_len,
                "max_len": max_merged_len,
            }
            import sys
            print(f"[K36-MERGE] {_merge_audit}", file=sys.stderr)
            # Merge: Description anhaengen, architect_start behalten,
            # architect_ende auf den spaeteren Task setzen.
            prev["description"] = (
                prev.get("description", "").rstrip()
                + "\n\n"
                + t.get("description", "").lstrip()
            )
            if t.get("architect_ende"):
                prev["architect_ende"] = t["architect_ende"]
            _deps = set(prev.get("dependencies") or [])
            _deps.update(t.get("dependencies") or [])
            _deps.discard(prev.get("id"))
            prev["dependencies"] = sorted(_deps)
        else:
            # K36: Nicht-gemergt -- auch loggen.
            import sys
            print(
                f"[K36-KEEP] prev={prev.get('id')}({prev_file}) "
                f"cur={t.get('id')}({cur_file}) "
                f"same_file={same_file} same_act={same_act} "
                f"combined={combined_len}/{max_merged_len}",
                file=sys.stderr,
            )
            merged.append(dict(t))

    # IDs neu vergeben (t1..tN).
    for i, t in enumerate(merged, 1):
        t["id"] = f"t{i}"

    return merged


def _normalisiere_task_files(tasks, explorer_ctx, pd, pn) -> list:
    """K61a: Korrigiert task_files ohne Pfad-Praefix anhand key_files.

    Problem (Live 2026-10-29 14:16): Architect plante t5 mit
    task_files=["routes_state.py"], Builder fand die Datei nicht
    (sie liegt unter apps/dashboard/routes_state.py).

    Fail-closed bei Mehrdeutigkeit: mehrere Dateien mit gleichem
    Basisnamen -> unveraendert + audit, damit Builder meldet.
    """
    if not tasks:
        return tasks or []
    _basen: dict = {}
    for kf in (explorer_ctx or {}).get("key_files") or []:
        if isinstance(kf, dict):
            f = kf.get("file")
        elif isinstance(kf, str):
            f = kf
        else:
            continue
        if not f or "/" not in f:
            continue
        _basen.setdefault(f.rsplit("/", 1)[-1], []).append(f)
    for t in tasks:
        if not isinstance(t, dict):
            continue
        files = t.get("task_files") or []
        neu = []
        for f in files:
            if not isinstance(f, str) or not f:
                neu.append(f)
                continue
            if "/" in f:
                neu.append(f)
                continue
            treffer = _basen.get(f, [])
            if len(treffer) == 1:
                neu.append(treffer[0])
                audit("planner_task_files_korrigiert",
                      {"alt": f, "neu": treffer[0]}, pd, pn)
            elif len(treffer) > 1:
                neu.append(f)
                audit("planner_task_files_mehrdeutig",
                      {"name": f, "kandidaten": treffer}, pd, pn)
            else:
                neu.append(f)
        t["task_files"] = neu
    return tasks


def _zerlege_in_sub_tasks(
    prosa: str, key_files: list[str], api_key: str, pd, pn,
) -> list[dict]:
    """M-453: Zerlegt Architect-Prosa in 3-5 Sub-Tasks."""
    import json as _json
    _user = (
        f"## ARCHITECT-PROSA:\n{prosa}\n\n"
        f"## DATEIEN:\n" + "\n".join(f"- {f}" for f in key_files)
    )
    reply = _with_spinner(
        "Planner-Split",
        lambda: ask_llm(
            api_key, PLANNER_SPLIT_SYSTEM, _user,
            model="deepseek-chat", temperature=0.2, max_tokens=8000,
        ),
    )
    if not reply.ok:
        audit("planner_split_llm_fehler", {"fehler": reply.error}, pd, pn)
        return []
    raw = reply.content.strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start < 0 or end <= start:
        audit("planner_split_json_fehler", {"raw": raw[:200]}, pd, pn)
        return []
    try:
        parsed = _json.loads(raw[start:end])
    except _json.JSONDecodeError:
        audit("planner_split_json_fehler", {"raw": raw[:200]}, pd, pn)
        return []
    tasks_raw = parsed.get("tasks", [])
    if not isinstance(tasks_raw, list):
        return []
    tasks: list[dict] = []
    for i, t in enumerate(tasks_raw, 1):
        if not isinstance(t, dict):
            continue
        _start = t.get("architect_start") or ""
        _ende = t.get("architect_ende") or ""
        # M-461: Woertlichen Prosa-Abschnitt extrahieren.
        _abschnitt = _extrahiere_prosa_abschnitt(prosa, _start, _ende)
        # GOLD: Wenn architect_start fehlt (Gold-Architect liefert
        # "## <pfad>"-Ueberschriften), deterministisch segmentieren.
        if not _abschnitt and not _start:
            _tf = t.get("task_files") or []
            _ziel = _tf[0] if _tf else ""
            if _ziel:
                for _seg in _segmentiere_nach_pfad(prosa):
                    if _seg["datei"] == _ziel or _seg["datei"].endswith("/" + _ziel) or _ziel.endswith(_seg["datei"]):
                        _abschnitt = _seg["prosa"]
                        break
        if not _abschnitt:
            # M-463: Fallback: Task-Name + Description, NICHT ganze Prosa.
            _name = t.get("name") or ""
            _desc = t.get("description") or ""
            _abschnitt = f"## TASK: {_name}\n{_desc}" if _desc else _name
        # K19b: Fallback 2500 statt 800 -- K15c-Konsistenz.
        if len(_abschnitt) > 2500:
            _cut = _abschnitt.rfind(".", 0, 2500)
            if _cut > 0:
                _abschnitt = _abschnitt[:_cut + 1]
            else:
                _abschnitt = _abschnitt[:2500]
        tasks.append({
            "id": t.get("id") or f"t{i}",
            "name": t.get("name") or f"Sub-Task {i}",
            "action": t.get("action", "update"),
            "task_files": t.get("task_files") or [],
            "dependencies": t.get("dependencies") or [],
            "description": _abschnitt,
        })
    # M-469: Rekursive Zerlegung (ADaPT). Tasks > 2500 Zeichen (K19b).
    # werden neu zerlegt (max 2 Ebenen tief).
    _final: list[dict] = []
    import re as _re_470
    for t in tasks:
        _desc = t.get("description", "")
        # K11: Tiefe und Komplexitaetsmetriken fuer den Haupt-Task.
        # Vorher waren die Tiefe, Schritte und Bullets
        # '_komplexitaet' undefiniert -> NameError >2000 Zeichen.
        _tiefe = int(t.get("split_tiefe", 0) or 0)
        _schritte = len(_re_470.findall(
            r"^\s*\d+\.", _desc, _re_470.MULTILINE
        ))
        _bullets = len(_re_470.findall(
            r"^\s+-\s", _desc, _re_470.MULTILINE
        ))
        _komplexitaet = _schritte + _bullets
        # M-472: On-Demand-Zerlegung (ADaPT). Keine praeventive
        # Komplexitaetspruefung mehr. Nur Sicherheitsnetz: > 2000 Zeichen.
        _zu_gross = len(_desc) > 2500
        if not _zu_gross or _tiefe >= 2:
            _final.append(t)
        else:
            audit("planner_task_zu_gross",
                  {"id": t.get("id"),
                   "desc_len": len(_desc),
                   "schritte": _schritte,
                   "bullets": _bullets,
                   "komplexitaet": _komplexitaet,
                   "tiefe": _tiefe}, pd, pn)
            _sub = _llm_split_einzel_task(prosa, t, api_key, pd, pn)
            if _sub:
                for _st in _sub:
                    _st_desc = _st.get("description", "")
                    _st_schritte = len(_re_470.findall(
                        r"^\s*\d+\.", _st_desc, _re_470.MULTILINE
                    ))
                    _st_bullets = len(_re_470.findall(
                        r"^\s+-\s", _st_desc, _re_470.MULTILINE
                    ))
                    _st_komplex = _st_schritte + _st_bullets
                    # K19b: 2500 statt 800 -- konsistent mit K15c.
                    _st_gross = len(_st_desc) > 2500 or _st_komplex > 4
                    if not _st_gross or _tiefe + 1 >= 2:
                        _final.append(_st)
                    else:
                        _sub2 = _llm_split_einzel_task(prosa, _st, api_key, pd, pn)
                        _final.extend(_sub2 or [_st])
            else:
                _final.append(t)

    # K61a: task_files normalisieren (Dateiname -> voller Pfad).
    # Vor K20, damit _korrigiere_aktion auf korrekten Pfaden arbeitet.
    _final = _normalisiere_task_files(
        _final, {"key_files": key_files}, pd, pn,
    )
    # K20: Action anhand Datei-Existenz korrigieren (vor Merge).
    for _t_korr in _final:
        if isinstance(_t_korr, dict):
            _korrigiere_aktion(_t_korr, pd, pn)
    # K20b: Sequentiell -- create auf Datei, die ein frueherer
    # Task bereits anlegt -> update.
    _korrigiere_aktion_sequenziell(_final, pd, pn)

    # K36: Vor-Merge-State loggen.
    audit("planner_split_vor_merge", {
        "anzahl": len(_final),
        "tasks": [
            {"id": t.get("id"), "name": t.get("name"),
             "files": t.get("task_files"), "action": t.get("action"),
             "desc_len": len(t.get("description", ""))}
            for t in _final if isinstance(t, dict)
        ],
    }, pd, pn)

    # K15a: deterministischer Merge benachbarter Mini-Tasks.
    _vor_merge = len(_final)
    _final = _merge_mini_tasks(_final)
    if len(_final) != _vor_merge:
        audit("planner_split_merged",
              {"vorher": _vor_merge, "nachher": len(_final)},
              pd, pn)

    audit("planner_split", {"anzahl": len(_final), "tasks": [
        {"id": t["id"], "files": t["task_files"],
         "desc_len": len(t.get("description", ""))} for t in _final
    ]}, pd, pn)
    return _final


def _run_scout(
    state, aufgabe: str, code_index: dict,
    key_files: list, api_key: str,
) -> dict | None:
    """GOLD: Scout-Call (deepseek-chat). Liefert strukturierten Auftrag.

    Deterministisch: Code-Index aus AST.
    LLM: formuliert Auftrag (Ziel, relevante Dateien, API, Risiken).
    """
    import json as _json
    pd = state.project_dir
    pn = state.project_name

    _index_str = _format_api_index_for_prompt(code_index, max_files=40)
    _files_str = "\n".join(f"- {f}" for f in (key_files or [])[:20])
    user_content = (
        f"## AUFGABE\n{aufgabe}\n\n"
        f"## CODE-INDEX (Module/Klassen/Funktionen)\n{_index_str}\n\n"
        f"## EXPLORER-DATEIEN\n{_files_str}\n"
    )
    reply = _with_spinner(
        "Scout",
        lambda: ask_llm(
            api_key, _scout_system_with_nachfolger(), user_content,
            model="deepseek-chat", temperature=0.2, max_tokens=4000,
        ),
    )
    if not reply.ok:
        audit("planner_scout_llm_fehler", {"fehler": reply.error}, pd, pn)
        return None
    raw = reply.content.strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start < 0 or end <= start:
        audit("planner_scout_json_fehler", {"raw": raw[:200]}, pd, pn)
        return None
    try:
        parsed = _json.loads(raw[start:end])
    except _json.JSONDecodeError:
        audit("planner_scout_json_fehler", {"raw": raw[:200]}, pd, pn)
        return None
    if not isinstance(parsed, dict):
        return None
    audit("planner_scout_ok",
          {"dateien": len(parsed.get("relevante_dateien") or []),
           "risiken": len(parsed.get("risiken") or [])}, pd, pn)
    return parsed


def run_planner(state: RunState) -> bool:
    """Erstellt den Plan. Schreibt in state.tasks/tests/akzeptanzkriterien."""
    pd = state.project_dir
    pn = state.project_name
    api_key = getattr(state, "api_key", "")
    
    if not api_key:
        audit("planner_kein_key", {}, pd, pn)
        return False

    aufgabe = getattr(state, "aufgabe", "")
    docs_ctx = ""
    if getattr(state, "docs", None):
        docs_ctx = "\n".join(f"--- {k} ---\n{v}" for k, v in list(state.docs.items())[:3])

    user_content = f"Aufgabe: {aufgabe}\n\nKontext:\n{docs_ctx}"

    # K6: Abgeschlossene Punkte als Signal — verhindert Neu-Planen.
    _erledigt = _erledigte_punkte(getattr(state, "project_dir", None))
    if _erledigt:
        user_content += (
            "\n\n## BEREITS ERLEDIGT (NICHT neu planen):\n"
            + _erledigt[:3000]
        )

    # M-375/M-376: Explorer-Kontext lesen (key_files + findings).
    _explorer_ctx = getattr(state, "explorer_context", None)
    if isinstance(_explorer_ctx, dict):
        _key = _explorer_ctx.get("key_files") or []
        _findings = _explorer_ctx.get("findings") or ""
        if _key or _findings:
            _key_names = [
                k.get("file") for k in _key
                if isinstance(k, dict) and k.get("file")
            ]
            user_content += "\n\nExplorer-Kontext:"
            if _findings:
                user_content += f"\nBefund: {_findings[:2000]}"
            if _key_names:
                user_content += f"\nRelevante Dateien: {_key_names}"
                user_content += (
                    "\nNutze diese Dateien als task_files. "
                    "Erfinde KEINE anderen Dateien."
                )

    # M-395: key_files-Inhalt lesen (max 3 Dateien, je max 2000 Zeichen).
    _key_files_content = ""
    if isinstance(_explorer_ctx, dict):
        _key = _explorer_ctx.get("key_files") or []
        _file_paths = [
            k.get("file") for k in _key[:3]
            if isinstance(k, dict) and k.get("file")
        ]
        for _fp in _file_paths:
            if not isinstance(_fp, str):
                continue
            _target = Path(pd) / _fp
            if not _target.is_file():
                continue
            try:
                _content = _target.read_text(encoding="utf-8")[:2000]
                _key_files_content += (
                    f"\n--- {_fp} ---\n{_content}\n"
                )
            except (OSError, UnicodeDecodeError):
                continue
        if _key_files_content:
            user_content += (
                "\n\nDatei-Inhalt (relevant, gekuerzt):"
                + _key_files_content
            )

    # M-307b: letzte 10 PROGRESS.md-Eintraege als Kontext.
    try:
        from werkstatt import progress as _progress
        progress_text = _progress.read_recent(pd, n=10)
        if progress_text:
            user_content += f"\n\nProjekt-Fortschritt (letzte 10):\n{progress_text}"
    except Exception:  # noqa: BLE001, S110
        pass  # PROGRESS.md nicht kritisch

    # M-310b: strukturierter Phase-State (wo bin ich jetzt).
    try:
        from werkstatt.phase_state import PhaseState
        _ps = PhaseState(pn, base_dir=pd / ".werkstatt")
        if _ps.exists() and _ps.load():
            _tasks_status = [
                {"id": t.get("id"), "name": t.get("name", ""),
                 "status": t.get("status"), "failure": t.get("failure")}
                for t in _ps.data.get("tasks", [])
            ]
            if _tasks_status:
                user_content += (
                    "\n\nPhase-State (aktueller Stand):\n"
                    + json.dumps(_tasks_status, ensure_ascii=False)
                )
    except Exception:  # noqa: BLE001, S110
        pass  # PhaseState nicht kritisch fuer Prompt

    # M-299e: Preflight-Fehler + Follow_up aus vorheriger Phase.
    preflight = getattr(state, "preflight_fehler", []) or []
    follow_up_prev = getattr(state, "follow_up_fehler", []) or []
    if preflight:
        user_content += (
            "\n\nPreflight-Fehler (aktuell):\n"
            + json.dumps(preflight[:10], ensure_ascii=False)
        )
    if follow_up_prev:
        user_content += (
            "\n\nFollow_up (vorherige Phase, neu bewerten):\n"
            + json.dumps(follow_up_prev[:10], ensure_ascii=False)
        )

    # M-349d: Planner-Info aus vorherigem _plan_gate-Fail.
    # Der Hook hat den Plan abgelehnt. Der Planner MUSS die Info
    # sehen, sonst plant er blind neu.
    # K17: Migrationsstand deterministisch in den Kontext.
    _mig_stand = _migrations_stand(pd)
    if _mig_stand:
        user_content += "\n\n" + _mig_stand

    _planner_info = getattr(state, "last_planner_info", None)
    if _planner_info:
        user_content += (
            "\n\n=== ABGELEHNT ===\n"
            f"Regel: {_planner_info.get('regel', '?')}\n"
            f"Fakt: {_planner_info.get('fakt', '?')}\n"
            f"Erklaerung: {_planner_info.get('erklaerung', '?')}\n"
            f"Details: {_planner_info.get('details', '?')}\n"
            "\n"
            "Der vorherige Plan wurde nicht gebaut.\n"
            "Antworte mit gueltigem JSON. "
        "GOLD: KEINE TOOL-CALLS. KEIN {\"tool\": ...}. "
        "Beginne deine Antwort mit '{' und ende mit '}'. "
        "Erst Dateien lesen, DANN planen -- in einer Antwort."
        )

    # M-398: Tool-Use-Loop (max 3 Runden).
    # GOLD: Tool-Use nur 1 Runde. Architect soll PLANEN, nicht
    # staendig Dateien lesen. Bei 3 Runden liefert er oft nur
    # Tool-Calls (DSML) statt Plan-JSON (Live 14:52).
    # === GOLD: Architect (Prosa) + Planner (JSON) ===
    # Der Architect liefert strukturierte Prosa. Der Planner
    # (_zerlege_in_sub_tasks) macht daraus Tasks. Zwei Calls,
    # zwei Agents -- kein Tool-Use, kein JSON/Prosa-Raetsel.

    # === GOLD: CALL 0 -- Scout (Code-Index + Auftrag) ===
    _code_index = _baue_api_index(pd)
    _key_files_scan: list[str] = []
    if isinstance(_explorer_ctx, dict):
        for _k in (_explorer_ctx.get("key_files") or []):
            if isinstance(_k, dict) and _k.get("file"):
                _kf = _k["file"]
                if _kf not in _key_files_scan:
                    _key_files_scan.append(_kf)
    _scout_report = _run_scout(
        state, aufgabe, _code_index, _key_files_scan, api_key,
    )
    if _scout_report:
        _scout_auftrag = _scout_report.get("auftrag_prosa") or ""
        _scout_apis = _scout_report.get("api_auszug") or {}
        _scout_risiken = _scout_report.get("risiken") or []
        if _scout_auftrag:
            user_content += (
                "\n\n## SCOUT-AUFTRAG (vorformuliert):\n"
                + _scout_auftrag[:3000]
            )
        if _scout_apis:
            _api_lines = []
            for _af, _asyms in list(_scout_apis.items())[:10]:
                _api_lines.append(f"-- {_af}")
                for _asym in (_asyms or [])[:20]:
                    _api_lines.append(f"   {_asym}")
            user_content += (
                "\n\n## VERFUEGBARE APIS (aus Code-Index):\n"
                + "\n".join(_api_lines)[:4000]
            )
        if _scout_risiken:
            user_content += (
                "\n\n## SCOUT-RISIKEN:\n"
                + "\n".join(f"- {r}" for r in _scout_risiken[:10])
            )

    # CALL 1: Architect
    # GOLD: _planner_system baut ARCHITECT_SYSTEM + measured_files.
    # Dann _architect_system_with_builder() haengt _BUILDER_SCHNITTSTELLE an.
    _arch_sys_base = _planner_system(aufgabe, _explorer_ctx)
    _arch_sys = _arch_sys_base + "\n\n" + _BUILDER_SCHNITTSTELLE
    _arch_reply = _with_spinner(
        "Architect",
        lambda: ask_llm(
            api_key, _arch_sys, user_content,
            model=_ARCHITECT_MODEL, temperature=0.2, max_tokens=16000,
        ),
    )
    if not _arch_reply.ok:
        audit("planner_architect_llm_fehler",
              {"fehler": _arch_reply.error}, pd, pn)
        return False

    _arch_prosa = _strip_xml_tags(_arch_reply.content.strip())
    if len(_arch_prosa.strip()) < 50:
        audit("planner_architect_prosa_zu_kurz",
              {"len": len(_arch_prosa),
               "raw_prefix": _arch_reply.content[:200]}, pd, pn)
        return False

    audit("planner_architect_ok",
          {"prosa_len": len(_arch_prosa)}, pd, pn)
    state.architect_prosa = _arch_prosa  # type: ignore[attr-defined]

    # CALL 2: Planner (JSON aus Prosa)
    _key_files: list[str] = []
    if isinstance(_explorer_ctx, dict):
        for k in (_explorer_ctx.get("key_files") or []):
            if isinstance(k, dict) and k.get("file"):
                _f = k["file"]
                if _f not in _key_files:
                    _key_files.append(_f)

    _sub_tasks = _zerlege_in_sub_tasks(
        _arch_prosa, _key_files, api_key, pd, pn,
    )

    if _sub_tasks:
        _sub_tasks = _normalisiere_task_files(
            _sub_tasks, _explorer_ctx, pd, pn,
        )
        state.tasks = _sub_tasks  # type: ignore[attr-defined]
    else:
        state.tasks = [{  # type: ignore[attr-defined]
            "id": "t1", "name": "Architect-Loesung umsetzen",
            "action": "update", "description": _arch_prosa,
            "task_files": _key_files,
        }]

    state.phasen = []  # type: ignore[attr-defined]
    state.tests = []  # type: ignore[attr-defined]
    state.akzeptanzkriterien = []  # type: ignore[attr-defined]

    audit("planner_plan_erstellt",
          {"tasks": len(state.tasks),
           "prosa_len": len(_arch_prosa)}, pd, pn)

    return bool(state.tasks)  # type: ignore[attr-defined]
