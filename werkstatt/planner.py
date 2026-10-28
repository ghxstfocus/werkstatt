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
from werkstatt.skills import load_all_skills, load_skill_by_name
from werkstatt.state import RunState
from werkstatt.tools import run_readonly

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



def _strip_xml_tags(text: str) -> str:
    """K7: Entfernt DSML/XML-Tool-Call-Tags aus Architect-Prosa.

    Der Architect liefert gelegentlich <shell_command>, <read_file>,
    <tool>, <function>-Tags. Diese gehoeren nicht in die Prosa,
    die an den Planner-Split und Builder geht.
    """
    import re as _re
    # Tags + Inhalt entfernen (nicht nur Tags).
    text = _re.sub(
        r"<(shell_command|read_file|tool|function|function_calls|invoke)"
        r"[^>]*>.*?</\1>",
        "",
        text,
        flags=_re.DOTALL,
    )
    # Selbstschliessende Tags.
    text = _re.sub(
        r"<(shell_command|read_file|tool|function|function_calls|invoke)"
        r"[^>]*/>",
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

WENN MEHRERE DATEIEN BETROFFEN SIND:
  Beschreibe JEDE Datei einzeln, mit ihrem Pfad als Ueberschrift.
  Beispiel:
    ## harness/versioning/applier.py
    <Beschreibung>

    ## core/changeapplier/applier.py
    <Beschreibung>

WENN NUR EINE DATEI BETROFFEN IST:
  Beschreibe sie direkt, ohne Ueberschrift.

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


def _planner_system(aufgabe: str, explorer_ctx: dict | None = None) -> str:
    """M-376: Explorer-Dateien ZUERST (Lost-in-the-Middle).

    Goldstandard: Relevante Information an den Anfang des
    Kontexts. Die gemessenen Dateien sind die wichtigste
    Information — sie stehen VOR PLANNER_SYSTEM.
    """
    skills = load_all_skills()
    parts: list[str] = []

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

    # === M-408: Architect-Modus (Prosa statt JSON) ===
    if "architect" in aufgabe.lower() or "prosa" in aufgabe.lower():
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
    else:
        parts.append(PLANNER_SYSTEM)

    # === M-397: Doku-Verbot (harte Regel, vor den Skills) ===
    parts.append(
        "<doku_verbot>\n"
        "Doku-Tasks (docs/*.md, README.md, ROADMAP.md, CHANGELOG.md) "
        "sind STRENG VERBOTEN.\n"
        "Der Loop schreibt PROGRESS.md automatisch.\n"
        "Wenn die findings offene Punkte in docs/ enthalten:\n"
        "  - Extrahiere das CODE-Stichwort "
        "(z.B. 'Migrations-Tracking' -> 'migration', "
        "'Sanity-Check' -> 'sanity', 'Logout-Button' -> 'logout')\n"
        "  - Plane einen Code-Task auf der zugehoerigen .py-Datei "
        "mit action=update.\n"
        "  - NIEMALS docs/*.md als task_files.\n"
        "</doku_verbot>"
    )

    # === M-399a: Datei-Pruefung (kein Erfinden) ===
    parts.append(
        "<datei_pruefung>\n"
        "Bevor du eine Datei in task_files setzt:\n"
        "  - Pruefe mit grep oder read_file, ob die Datei existiert.\n"
        "  - Wenn die Datei NICHT existiert und action=update: "
        "Erfinde sie NICHT.\n"
        "    Nutze action=create (dann legt der Builder sie an) "
        "oder eine existierende Datei.\n"
        "  - Wenn du unsicher bist: Nutze grep, um die Datei zu finden.\n"
        "</datei_pruefung>"
    )

    # === M-401: Task-Groesse (2-5 Minuten) ===
    parts.append(
        "<task_groesse>\n"
        "Jeder Task MUSS in 2-5 Minuten erledigt sein.\n"
        "  - Ein Task = EIN kleiner Fix (z.B. 'I001 in app.py beheben').\n"
        "  - KEINE 'ChangeApplier.apply implementieren' — das ist "
        "Stunden-Arbeit.\n"
        "  - Grosse Features aufteilen in mehrere kleine Tasks.\n"
        "  - Maximal 5 Tasks pro Phase.\n"
        "  - Wenn ein offener Punkt zu gross ist: Zerlege ihn in "
        "Teil-Tasks (z.B. 'apply-Signatur', 'apply-Happy-Path', "
        "'apply-Fehlerbehandlung').\n"
        "</task_groesse>"
    )

    # === Skills ===
    uw = load_skill_by_name("using-werkstatt", skills)
    if uw and uw["body"]:
        parts.append("## Skill: Using-Werkstatt\n" + uw["body"])
    pc = load_skill_by_name("plan-crafting", skills)
    if pc and pc["body"]:
        parts.append("## Skill: Plan-Crafting\n" + pc["body"])
    trigger = ("ruff", "test", "bug", "fehler", "debug", "pytest")
    if any(w in aufgabe.lower() for w in trigger):
        sd = load_skill_by_name("systematic-debugging", skills)
        if sd and sd["body"]:
            parts.append("## Skill: Systematic-Debugging\n" + sd["body"])

    # === M-376: Pflicht-Wiederholung am ENDE (recency bias) ===
    if isinstance(explorer_ctx, dict):
        _key2 = explorer_ctx.get("key_files") or []
        _files2 = [
            k.get("file") for k in _key2
            if isinstance(k, dict) and k.get("file")
        ]
        if _files2:
            parts.append(
                f"<erinnerung>Nur diese {len(_files2)} Dateien: "
                f"{', '.join(str(f) for f in _files2)}</erinnerung>"
            )

    # === M-398: Tool-Definition ===
    parts.append(
        "<tools>\n"
        "Du hast Zugriff auf zwei Tools, um den Code zu erkunden:\n"
        "\n"
        "  read_file: Lies eine Datei.\n"
        '    Antwort: {"tool": "read_file", "args": {"file": "pfad/datei.py"}}\n'
        "\n"
        "  grep: Suche in Dateien.\n"
        '    Antwort: {"tool": "grep", "args": {"pattern": "migration", '
        '"path": "core/"}}\n'
        "\n"
        "Wenn du mehr Kontext brauchst, antworte NUR mit einem Tool-Call-JSON.\n"
        "Wenn du genug weisst, antworte NUR mit dem Plan-JSON "
        '({"tasks": [...], "tests": [...], "akzeptanzkriterien": [...]}).\n'
        "</tools>"
    )

    return "\n\n".join(parts)


def _normalisiere(text: str) -> str:
    """M-463: Entfernt Backticks, mehrfache Leerzeichen.

    Damit Marker wie "1. In `applier.py`" und "1. In applier.py"
    matchen.
    """
    import re as _re
    text = text.replace("`", "")
    text = _re.sub(r"\s+", " ", text)
    return text.strip()


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


def _merge_mini_tasks(tasks: list[dict], max_merged_len: int = 2500) -> list[dict]:
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

        if same_file and same_act and combined_len <= max_merged_len:
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
            merged.append(dict(t))

    # IDs neu vergeben (t1..tN).
    for i, t in enumerate(merged, 1):
        t["id"] = f"t{i}"

    return merged


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

    # K20: Action anhand Datei-Existenz korrigieren (vor Merge).
    for _t_korr in _final:
        if isinstance(_t_korr, dict):
            _korrigiere_aktion(_t_korr, pd, pn)

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
            "Antworte mit gueltigem JSON."
        )

    # M-398: Tool-Use-Loop (max 3 Runden).
    _max_tool_runden = 3
    _tool_kontext = ""
    reply = None
    plan = None
    for _runde in range(_max_tool_runden + 1):
        _sys = _planner_system(aufgabe, _explorer_ctx)
        if _tool_kontext:
            _sys += "\n\n<tool_ergebnisse>\n" + _tool_kontext + "\n</tool_ergebnisse>"
        _user = user_content + (_tool_kontext if _tool_kontext else "")
        # M-445: temperature bleibt positional (ask_llm-Signatur).
        # Reasoning-Modelle ignorieren temperature serverseitig.
        reply = _with_spinner(
            "Architect",
            lambda: ask_llm(
                api_key, _sys, _user,
                model=_ARCHITECT_MODEL, temperature=0.2, max_tokens=16000,
            ),
        )
        if not reply.ok:
            audit("planner_llm_fehler", {"fehler": reply.error}, pd, pn)
            return False

        # M-453b: JSON erkennen. Wenn die Antwort JSON ist:
        # in den bestehenden JSON-Pfad fallen (kein Architect+Split).
        # Wenn Prosa: Architect+Split.
        _raw = reply.content.strip()
        _is_json = _raw.startswith("{") or '"tasks"' in _raw[:200]

        if not _is_json:
            # Prosa -> Architect+Split.
            # K7: XML/DSML-Tool-Call-Tags entfernen.
            _prosa = _strip_xml_tags(_raw)
            _key_files: list[str] = []
            if isinstance(_explorer_ctx, dict):
                for k in (_explorer_ctx.get("key_files") or []):
                    if isinstance(k, dict) and k.get("file"):
                        _f = k["file"]
                        if _f not in _key_files:
                            _key_files.append(_f)
                if not _key_files:
                    for _f in (_explorer_ctx.get("next_reads") or []):
                        if isinstance(_f, str) and _f not in _key_files:
                            _key_files.append(_f)
            audit("planner_architect_scope",
                  {"prosa_len": len(_prosa),
                   "anzahl_dateien": len(_key_files),
                   "dateien": _key_files[:10]}, pd, pn)

            # K17c: Migrations-Kollision wandert in planner_gate.py (Hook).
            state.architect_prosa = _prosa  # type: ignore[attr-defined]
            _sub_tasks = _zerlege_in_sub_tasks(
                _prosa, _key_files, api_key, pd, pn,
            )
            if _sub_tasks:
                state.tasks = _sub_tasks  # type: ignore[attr-defined]
            else:
                state.tasks = [{  # type: ignore[attr-defined]
                    "id": "t1", "name": "Architect-Loesung umsetzen",
                    "action": "update", "description": _prosa,
                    "task_files": _key_files,
                }]
            state.phasen = []  # type: ignore[attr-defined]
            state.tests = []  # type: ignore[attr-defined]
            state.akzeptanzkriterien = []  # type: ignore[attr-defined]
            audit("planner_architect_erstellt",
                  {"prosa_len": len(_prosa),
                   "anzahl_tasks": len(state.tasks)}, pd, pn)
            return True


        raw = reply.content.strip()
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start < 0 or end <= start:
            audit("planner_json_fehler", {"raw": raw[:200]}, pd, pn)
            return False

        try:
            _parsed = json.loads(raw[start:end])
        except json.JSONDecodeError:
            audit("planner_json_fehler", {"raw": raw[:200]}, pd, pn)
            return False

        # Tool-Call?
        if isinstance(_parsed, dict) and "tool" in _parsed and "tasks" not in _parsed:
            _tool = _parsed.get("tool")
            _args = _parsed.get("args", {})
            _cmd = None
            if _tool == "read_file":
                _fp = _args.get("file", "")
                if _fp and not _fp.startswith("/"):
                    _cmd = f"cat {_fp}"
            elif _tool == "grep":
                _pat = _args.get("pattern", "")
                _path = _args.get("path", ".")
                if _pat:
                    _safe_pat = _pat.replace('"', '')
                    _cmd = f'grep -rn "{_safe_pat}" --include=*.py --exclude-dir=.venv --exclude-dir=__pycache__ {_path}'
            if _cmd:
                _res = run_readonly(_cmd, Path(pd))
                _out = _res.get("stdout", "")[:3000]
                _tool_kontext += f"\n--- {_tool} {_args} ---\n{_out}\n"
                audit("planner_tool_call",
                      {"runde": _runde + 1, "tool": _tool, "args": _args,
                       "stdout_len": len(_out)}, pd, pn)
                continue
            else:
                audit("planner_tool_ungueltig",
                      {"runde": _runde + 1, "parsed": str(_parsed)[:200]}, pd, pn)
                return False

        # Plan-JSON
        plan = _parsed
        break

    if plan is None:
        audit("planner_kein_plan_nach_tools", {}, pd, pn)
        return False

    # M-306d Fix 3: action-Default. Wenn Planner "action" nicht
    # setzt, Default auf "write" (fail-safe) + Audit-Spur.
    _tasks_raw = plan.get("tasks", [])
    _action_missing = 0
    # M-317: Default "update" (nicht "write"). Fail-safe:
    # update = normaler Patch-Pfad, kein Idempotenz-Risiko.
    # "write" wird nicht mehr verwendet (M-306a -> M-317).
    for _t in _tasks_raw:
        if isinstance(_t, dict):
            _a = _t.get("action")
            if _a is None:
                _t["action"] = "update"
                _action_missing += 1
            elif _a == "write":
                # M-317: Legacy-Wert "write" -> "update"
                _t["action"] = "update"
    if _action_missing > 0:
        audit("planner_action_missing", {"anzahl": _action_missing}, pd, pn)

    # Plan in State schreiben
    state.tasks = _tasks_raw  # type: ignore[attr-defined]
    # M-310: phasen optional.
    state.phasen = plan.get("phasen", [])  # type: ignore[attr-defined]
    state.tests = plan.get("tests", [])  # type: ignore[attr-defined]
    state.akzeptanzkriterien = plan.get("akzeptanzkriterien", [])  # type: ignore[attr-defined]

    # M-299e: Planner-Entscheidung pro Fehler speichern.
    state.blocker_fehler = plan.get("blocker", [])  # type: ignore[attr-defined]
    state.follow_up_fehler = plan.get("follow_up", [])  # type: ignore[attr-defined]
    state.ignore_fehler = plan.get("ignore", [])  # type: ignore[attr-defined]

    audit("planner_plan_erstellt", {
        "tasks": len(state.tasks),  # type: ignore[attr-defined]
        "tests": len(state.tests),  # type: ignore[attr-defined]
        "kriterien": len(state.akzeptanzkriterien),  # type: ignore[attr-defined]
    }, pd, pn)

    return bool(state.tasks and state.tests and state.akzeptanzkriterien)  # type: ignore[attr-defined]
