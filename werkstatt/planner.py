"""Planner-Agent (Phase 5, 2026-10-23).

Eigenstaendiger Planner. Liest Aufgabe + Kontext,
ruft ask_llm (JSON-Modus) auf, schreibt Plan in
state.tasks / state.tests / state.akzeptanzkriterien.

Kein Schreiben von Code. Kein Executor.
Reiner Denker (Codex Plan Mode).
"""
from __future__ import annotations

import json

from werkstatt.agent import ask_llm
from werkstatt.audit import audit
from werkstatt.state import RunState

PLANNER_SYSTEM = """Du bist ein elite Software-Architekt und Planner.
Zerlege die Aufgabe in ausfuehrbare Tasks.
Jeder Task hat: id, name, description, akzeptanzkriterien.
Antworte NUR mit validem JSON:
{
  "tasks": [{"id": "t1", "name": "...", "description": "...", "akzeptanzkriterien": ["..."]}],
  "tests": ["..."],
  "akzeptanzkriterien": ["..."]
}
Keine Erklaerung, nur JSON."""


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
            fehler.append({
                "klasse": klasse,
                "stage_id": stage_id,
                "datei": None,  # TODO: aus stderr extrahieren
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

    # Plan in State schreiben
    state.tasks = plan.get("tasks", [])  # type: ignore[attr-defined]
    state.tests = plan.get("tests", [])  # type: ignore[attr-defined]
    state.akzeptanzkriterien = plan.get("akzeptanzkriterien", [])  # type: ignore[attr-defined]

    audit("planner_plan_erstellt", {
        "tasks": len(state.tasks),  # type: ignore[attr-defined]
        "tests": len(state.tests),  # type: ignore[attr-defined]
        "kriterien": len(state.akzeptanzkriterien),  # type: ignore[attr-defined]
    }, pd, pn)

    return bool(state.tasks and state.tests and state.akzeptanzkriterien)  # type: ignore[attr-defined]
