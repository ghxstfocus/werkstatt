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


def _get_git_diff(project_dir: str | Path = "/opt/werkstatt") -> str:
    """Holt den aktuellen Git-Diff im Zielprojekt.

    M-314: umfasst jetzt auch UNTRACKED-Dateien (git ls-files
    --others). Vorher war der Reviewer blind fuer neue Dateien,
    die der Builder mit `create` angelegt hat.
    """
    try:
        pd = Path(project_dir)
        res = subprocess.run(
            ["git", "diff", "HEAD", "--", ".", ":!PROGRESS.md"],
            cwd=str(pd), capture_output=True, text=True, timeout=30, check=False
        )
        parts = [res.stdout[:10000]] if res.stdout else []

        # M-314: untracked-Dateien als "Neue Datei"-Block anhaengen.
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=str(pd), capture_output=True, text=True, timeout=30, check=False
        )
        if untracked.stdout:
            for rel in untracked.stdout.splitlines():
                if not rel or rel.startswith("."):
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
    diff = _get_git_diff(pd)
    if not diff:
        audit("reviewer_kein_diff", {}, pd, pn)
        return True  # Nichts zu reviewen -> OK

    aufgabe = getattr(state, "aufgabe", "")
    tests_ok = getattr(state, "baseline_gruen", True)

    user_content = (
        f"Aufgabe: {aufgabe}\n\n"
        f"Baseline gruen: {tests_ok}\n\n"
        f"Diff:\n{diff}"
    )

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
