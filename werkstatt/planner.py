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

from werkstatt.agent import ask_llm
from werkstatt.audit import audit
from werkstatt.state import RunState

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

    reply = ask_llm(
        api_key, PLANNER_SYSTEM, user_content,
        model="deepseek-chat", temperature=0.2, max_tokens=4000,
    )

    if not reply.ok:
        audit("planner_llm_fehler", {"fehler": reply.error}, pd, pn)
        return False

    # JSON aus dem Reply extrahieren
    raw = reply.content.strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start < 0 or end <= start:
        audit("planner_json_fehler", {"raw": raw[:200]}, pd, pn)
        return False

    try:
        plan = json.loads(raw[start:end])
    except json.JSONDecodeError:
        audit("planner_json_fehler", {"raw": raw[:200]}, pd, pn)
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
