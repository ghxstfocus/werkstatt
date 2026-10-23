"""Reviewer-Agent (Phase 8, 2026-10-23).

Eigenstaendiger Reviewer. Bekommt Diff + Anforderung
+ Testergebnisse. Gibt strukturiertes Feedback zurueck.
Kein GO/NO_GO-Raten, sondern konkrete Bug-Funde.
"""
from __future__ import annotations

import json
import subprocess

from werkstatt.agent import ask_llm
from werkstatt.audit import audit
from werkstatt.state import RunState

REVIEWER_SYSTEM = """Du bist ein elite Code-Reviewer.
Du bekommst einen Git-Diff und die Anforderung.
Pruefe NUR auf Korrektheit (Bugs, Logikfehler, fehlende Edge-Cases).
Ignoriere Stil und Formatierung.

Antworte NUR mit validem JSON:
{
  "approved": true|false,
  "bugs": [{"file": "...", "line": 0, "description": "...", "severity": "high|medium|low"}],
  "summary": "..."
}
"""


def _get_git_diff() -> str:
    """Holt den aktuellen Git-Diff (nur unstaged/staged Aenderungen)."""
    try:
        res = subprocess.run(
            ["git", "diff", "HEAD"],
            cwd="/opt/werkstatt", capture_output=True, text=True, timeout=30, check=False
        )
        return res.stdout[:10000]
    except Exception:  # noqa: BLE001
        return ""


def run_reviewer(state: RunState) -> bool:
    """Prueft den Code. Gibt True zurueck, wenn approved."""
    pd = state.project_dir
    pn = state.project_name
    api_key = getattr(state, "api_key", "")

    if not api_key:
        audit("reviewer_kein_key", {}, pd, pn)
        return False

    diff = _get_git_diff()
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
        api_key, REVIEWER_SYSTEM, user_content,
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

    return approved
