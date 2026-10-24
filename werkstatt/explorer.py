"""Explorer-Subagent (Phase 14). Strikt read-only, JSON-Output."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from werkstatt.agent import ask_llm
from werkstatt.audit import audit
from werkstatt.state import RunState

EXPLORER_SYSTEM = """Du bist ein read-only Codebase-Explorer.
Finde die Dateien, die in der Aufgabe EXPLIZIT genannt sind.

WICHTIG (M-338):
  - Markiere NUR Dateien, die in der Aufgabe direkt vorkommen
    (z.B. "core/checks/" -> core/checks/__init__.py).
  - Markiere KEINE aehnlichen Dateien. Wenn die Aufgabe
    "core/checks/" nennt, markiere NICHT "tools/port_check.py".
  - Wenn keine Datei explizit genannt ist: key_files = [].

Du darfst NUR lesen und suchen.
Antworte NUR mit validem JSON:
{
  "findings": "Kurze Zusammenfassung",
  "key_files": [{"file": "pfad/datei.py", "why": "warum", "symbols": "symbole", "confidence": "high|medium|low"}],
  "next_reads": ["pfad/datei.py"]
}
Keine Erklaerung, nur JSON."""


def _list_py_files(project_dir: Path, max_files: int = 200) -> list[str]:
    try:
        res = subprocess.run(
            ["find", str(project_dir), "-name", "*.py", "-type", "f"],
            capture_output=True, text=True, timeout=30, check=False,
        )
        return [f for f in res.stdout.split("\n") if f.strip()][:max_files]
    except Exception:  # noqa: BLE001
        return []


def _grep_files(project_dir: Path, pattern: str, max_hits: int = 20) -> list[str]:
    try:
        res = subprocess.run(
            ["grep", "-r", "-n", "--include=*.py", pattern, str(project_dir)],
            capture_output=True, text=True, timeout=30, check=False,
        )
        return [h for h in res.stdout.split("\n") if h.strip()][:max_hits]
    except Exception:  # noqa: BLE001
        return []


def run_explorer(state: RunState, frage: str) -> dict:
    pd = state.project_dir
    pn = state.project_name
    api_key = getattr(state, "api_key", "")
    if not api_key:
        audit("explorer_kein_key", {}, pd, pn)
        return {"findings": "", "key_files": [], "next_reads": []}

    py_files = _list_py_files(Path(pd))
    grep_hits = _grep_files(Path(pd), frage[:100]) if frage else []
    context = (
        f"Frage: {frage}\n\n"
        f"Python-Dateien ({len(py_files)}):\n"
        + "\n".join(py_files[:50])
        + f"\n\nGrep-Treffer fuer '{frage[:50]}':\n"
        + "\n".join(grep_hits[:20])
    )

    reply = ask_llm(
        api_key, EXPLORER_SYSTEM, context,
        model="deepseek-chat", temperature=0.0, max_tokens=3000,
    )
    if not reply.ok:
        audit("explorer_llm_fehler", {"fehler": reply.error}, pd, pn)
        return {"findings": "", "key_files": [], "next_reads": []}

    raw = reply.content.strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start < 0 or end <= start:
        audit("explorer_json_fehler", {"raw": raw[:200]}, pd, pn)
        return {"findings": "", "key_files": [], "next_reads": []}

    try:
        result = json.loads(raw[start:end])
    except json.JSONDecodeError:
        audit("explorer_json_fehler", {"raw": raw[:200]}, pd, pn)
        return {"findings": "", "key_files": [], "next_reads": []}

    audit("explorer_result", {
        "findings_len": len(result.get("findings", "")),
        "key_files": len(result.get("key_files", [])),
    }, pd, pn)
    return result
