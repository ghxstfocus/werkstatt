"""Planner-Agent (Phase 5, 2026-10-23).

Eigenstaendiger Planner. Liest Aufgabe + Kontext,
ruft ask_llm (JSON-Modus) auf, schreibt Plan in
state.tasks / state.tests / state.akzeptanzkriterien.

Kein Schreiben von Code. Kein Executor.
Reiner Denker (Codex Plan Mode).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from werkstatt.agent import ask_llm
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
    if stage_id == "py_compile" or "SyntaxError" in fehlertext:
        return "syntax"
    if "ModuleNotFoundError" in fehlertext or "ImportError" in fehlertext:
        return "env"
    if stage_id == "ruff":
        return "lint"
    if stage_id == "mypy":
        return "type"
    if stage_id == "pytest":
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



ARCHITECT_SYSTEM = """Du bist ein elite Software-Architekt.
Beschreibe die Loesung in Prosa. KEIN JSON, KEIN Patch-Format.

Format:
  1. Was ist das Problem?
  2. Welche Datei(en) muessen geaendert werden?
  3. Wie sieht die Loesung aus? (Signaturen, Schluessel-Logik)
  4. Welche Tests brauchen wir?

REGELN:
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

Antworte NUR mit diesem Prosa-Text. Kein Code, nur Beschreibung.
"""


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
        parts.append(ARCHITECT_SYSTEM)
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
        reply = ask_llm(
            api_key, _sys, _user,
            model="deepseek-chat", temperature=0.2, max_tokens=4000,
        )
        if not reply.ok:
            audit("planner_llm_fehler", {"fehler": reply.error}, pd, pn)
            return False

        # M-408b: Architect-Modus -> Prosa als eine Task
        if "architect" in aufgabe.lower() or "prosa" in aufgabe.lower():
            _prosa = reply.content.strip()
            _key_files = []
            if isinstance(_explorer_ctx, dict):
                _key_files = [
                    k.get("file") for k in (_explorer_ctx.get("key_files") or [])
                    if isinstance(k, dict) and k.get("file")
                ]
            state.tasks = [{
                "id": "t1",
                "name": "Architect-Loesung umsetzen",
                "action": "architect",
                "description": _prosa,
                "task_files": _key_files,
            }]
            state.phasen = []  # type: ignore[attr-defined]
            state.tests = []  # type: ignore[attr-defined]
            state.akzeptanzkriterien = []  # type: ignore[attr-defined]
            audit("planner_architect_erstellt",
                  {"prosa_len": len(_prosa),
                   "task_files": _key_files}, pd, pn)
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
