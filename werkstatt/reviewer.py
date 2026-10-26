"""Reviewer-Agent (Phase 8, 2026-10-23).

Eigenstaendiger Reviewer. Bekommt Diff + Anforderung
+ Testergebnisse. Gibt strukturiertes Feedback zurueck.
Kein GO/NO_GO-Raten, sondern konkrete Bug-Funde.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from werkstatt.agent import ask_llm
from werkstatt.audit import audit
from werkstatt.skills import load_all_skills, load_skill_by_name
from werkstatt.state import RunState

REVIEWER_SYSTEM = """Du bist ein elite Code-Reviewer.
Du bekommst einen Git-Diff und die Anforderung.
Pruefe NUR auf Korrektheit (Bugs, Logikfehler, fehlende Edge-Cases).
Ignoriere Stil und Formatierung.

M-380: PROGRESS.md ist NICHT Teil deines Reviews. Du siehst es nicht (wird vor dem Review gefiltert). Bewerte NUR den Builder-Patch. Wenn du PROGRESS.md siehst, ist das ein Bug im Filter — ignoriere es STRIKT.

Antworte NUR mit validem JSON:
{
  "approved": true|false,
  "bugs": [{"file": "...", "line": 0, "description": "...", "severity": "high|medium|low"}],
  "summary": "..."
}
"""


def _get_git_diff(
    project_dir: str | Path = "/opt/werkstatt",
    task_files: list[str] | None = None,
) -> str:
    """Holt den aktuellen Git-Diff im Zielprojekt.

    M-314: umfasst jetzt auch UNTRACKED-Dateien (git ls-files
    --others). Vorher war der Reviewer blind fuer neue Dateien,
    die der Builder mit `create` angelegt hat.

    K4: Wenn task_files uebergeben, nur diese Pfade diffen — sonst
    sieht der Reviewer kumulative Aenderungen frueherer Tasks.
    """
    try:
        pd = Path(project_dir)
        pathspec = list(task_files) if task_files else ["."]
        res = subprocess.run(
            ["git", "diff", "HEAD", "--", *pathspec, ":!PROGRESS.md"],
            cwd=str(pd), capture_output=True, text=True, timeout=30, check=False
        )
        parts = [res.stdout[:500000]] if res.stdout else []

        # M-314: untracked-Dateien als "Neue Datei"-Block anhaengen.
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=str(pd), capture_output=True, text=True, timeout=30, check=False
        )
        if untracked.stdout:
            for rel in untracked.stdout.splitlines():
                if not rel or rel.startswith("."):
                    continue
                # K4b: nur untracked-Dateien der aktuellen Task.
                if task_files and not any(
                    rel == tf or rel.startswith(tf.rstrip("/") + "/")
                    for tf in task_files
                ):
                    continue
                f = pd / rel
                if not f.is_file():
                    continue
                try:
                    content = f.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                block = ["--- /dev/null", f"+++ b/{rel}", "@@ NEUE DATEI @@"]
                for line in content.splitlines():
                    block.append(f"+{line}")
                parts.append("\n".join(block) + "\n")

        return "\n".join(parts)[:20000]
    except Exception:  # noqa: BLE001
        return ""


def _reviewer_system() -> str:
    """M-374: review-work IMMER laden."""
    skills = load_all_skills()
    parts = [REVIEWER_SYSTEM]
    rw = load_skill_by_name("review-work", skills)
    if rw and rw["body"]:
        parts.append("## Skill: Review-Work\n" + rw["body"])
    return "\n\n".join(parts)


def run_reviewer(state: RunState) -> bool:
    """Prueft den Code. Gibt True zurueck, wenn approved."""
    pd = state.project_dir
    pn = state.project_name
    api_key = getattr(state, "api_key", "")

    if not api_key:
        audit("reviewer_kein_key", {}, pd, pn)
        return False

    pd = getattr(state, "project_dir", None) or Path("/opt/werkstatt")
    # K4: task_files aus aktuelle_task — Reviewer sieht nur
    # den Diff der aktuellen Task, nicht kumulativ.
    _akt_task_early = getattr(state, "aktuelle_task", None)
    _tf_early = None
    if isinstance(_akt_task_early, dict) and _akt_task_early.get("task_files"):
        _tf_early = list(_akt_task_early["task_files"])
    diff = _get_git_diff(pd, task_files=_tf_early)
    if not diff:
        audit("reviewer_kein_diff", {}, pd, pn)
        return True  # Nichts zu reviewen -> OK

    aufgabe = getattr(state, "aufgabe", "")
    tests_ok = getattr(state, "baseline_gruen", True)

    # M-459: Reviewer prueft Task-Description, nicht Gesamtaufgabe.
    _akt_task = getattr(state, "aktuelle_task", None)
    _task_name = ""
    _task_desc = ""
    _arch_desc = ""
    if isinstance(_akt_task, dict):
        _task_name = _akt_task.get("name", "")
        _task_desc = _akt_task.get("description", "")
        if _akt_task.get("action") == "architect":
            _arch_desc = _task_desc
    user_content = (
        f"## AKTUELLE TASK: {_task_name}\n"
        f"## TASK-BESCHREIBUNG: {_task_desc}\n"
        f"## GESAMTAUFGABE: {aufgabe}\n\n"
        f"Baseline gruen: {tests_ok}\n\n"
        f"Diff:\n{diff}"
    )
    # Hinweis an den Reviewer: pruefe die Task, nicht die Gesamtaufgabe.
    user_content += (
        "\n\nPruefe: Hat DIESE Task das getan, was ihre "
        "TASK-BESCHREIBUNG verlangt? Die GESAMTAUFGABE ist nur "
        "Kontext — nicht der Pruefungsgegenstand."
    )
    if _arch_desc:
        user_content += f"\n\nArchitect-Vorgabe:\n{_arch_desc}"
        # M-414: Volle Zieldatei lesen
        _zieldatei = _akt_task.get("task_files", [])
        if _zieldatei:
            _fp = Path(pd) / _zieldatei[0]
            if _fp.is_file():
                try:
                    _content = _fp.read_text(encoding="utf-8")[:30000]
                    user_content += (
                        f"\n\n--- VOLLE ZIELDATEI: {_zieldatei[0]} ---\n"
                        f"{_content}\n"
                        f"--- ENDE ---"
                    )
                except (OSError, UnicodeDecodeError):
                    pass

    reply = ask_llm(
        api_key, _reviewer_system(), user_content,
        model="deepseek-chat", temperature=0.0, max_tokens=4000,
    )

    if not reply.ok:
        audit("reviewer_llm_fehler", {"fehler": reply.error}, pd, pn)
        return False

    raw = reply.content.strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start < 0 or end <= start:
        audit("reviewer_json_fehler", {"raw": raw[:200]}, pd, pn)
        return False

    try:
        result = json.loads(raw[start:end])
    except json.JSONDecodeError:
        audit("reviewer_json_fehler", {"raw": raw[:200]}, pd, pn)
        return False

    approved = result.get("approved", False)
    bugs = result.get("bugs", [])

    audit("reviewer_result", {
        "approved": approved,
        "bugs": len(bugs),
        "summary": result.get("summary", "")[:200],
    }, pd, pn)

    if not approved:
        for bug in bugs:
            audit("reviewer_bug", bug, pd, pn)
        # M-314: bugs in State persistieren (fuer Reflection).
        state.reviewer_bugs = list(bugs)  # type: ignore[attr-defined]
    else:
        state.reviewer_bugs = []  # type: ignore[attr-defined]

    return approved
