"""Explorer-Subagent. Read-only. Deterministische Messung VOR dem LLM.

M-338-Fix: Der Explorer MESS'T zuerst (ruff, pytest), extrahiert
die Dateien, und liefert sie als key_files. Das LLM formuliert
nur noch findings. Kein Raten.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from werkstatt.agent import ask_llm
from werkstatt.audit import audit
from werkstatt.skills import load_all_skills, load_skill_by_name
from werkstatt.state import RunState
from werkstatt.tools import run_readonly

EXPLORER_SYSTEM = """Du bist ein read-only Codebase-Explorer.

WICHTIG (M-338-Fix):
  - Wenn die Aufgabe eine Messung verlangt (ruff-Fehler,
    Test-Fehler, Bug), hast du die Messung BEREITS erhalten
    (siehe "Messungen" im Kontext). Nutze sie.
  - Rate NICHT. Die Dateien aus der Messung sind deine
    key_files.
  - Wenn keine Messung moeglich war und keine Datei explizit
    in der Aufgabe genannt ist: key_files = [].

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
            ["find", str(project_dir), "-name", "*.py", "-type", "f",
             "-not", "-path", "*/.venv/*", "-not", "-path", "*/__pycache__/*"],
            capture_output=True, text=True, timeout=30, check=False,
        )
        return [f for f in res.stdout.split("\n") if f.strip()][:max_files]
    except Exception:  # noqa: BLE001
        return []


def _extract_dateien(stdout: str) -> list[str]:
    """Extrahiert Dateipfade aus ruff-concise-Output.

    Format: 'pfad/datei.py:zeile:spalte: CODE message'
    """
    dateien: list[str] = []
    for line in stdout.splitlines():
        m = re.match(r"^([^:\s]+\.py):", line)
        if m:
            d = m.group(1)
            if d not in dateien:
                dateien.append(d)
    return dateien


def _messen(frage: str, project_dir: Path) -> dict[str, Any]:
    """M-373: Deterministische Messung VOR dem LLM.

    Fuehrt basierend auf der Aufgabe die passenden Befehle aus.
    """
    results: dict[str, Any] = {}
    frage_lower = frage.lower()

    if "ruff" in frage_lower:
        r = run_readonly("ruff check . --output-format=concise", project_dir)
        results["ruff"] = {
            "ok": r.get("ok", False),
            "stdout": r.get("stdout", "")[:5000],
            "stderr": r.get("stderr", "")[:1000],
            "dateien": _extract_dateien(r.get("stdout", "")),
        }

    if "pytest" in frage_lower or "test" in frage_lower:
        r = run_readonly("pytest -q", project_dir)
        results["pytest"] = {
            "ok": r.get("ok", False),
            "stdout": r.get("stdout", "")[:3000],
            "stderr": r.get("stderr", "")[:1000],
        }

    return results


def _format_findings(messungen: dict[str, Any]) -> str:
    """Formatiert die Messungen als Klartext fuer den Planner."""
    lines = []
    for name, m in messungen.items():
        n = len(m.get("dateien", []))
        lines.append(f"{name}: {n} Datei(en) betroffen")
        if m.get("dateien"):
            lines.append(f"  Dateien: {', '.join(m['dateien'])}")
        if m.get("stdout"):
            lines.append(f"  Ausgabe (Auszug): {m['stdout'][:500]}")
    return "\n".join(lines)


def _explorer_system(frage: str) -> str:
    """Haengt systematic-debugging + using-werkstatt an."""
    skills = load_all_skills()
    parts = [EXPLORER_SYSTEM]
    # Meta-Skill IMMER
    uw = load_skill_by_name("using-werkstatt", skills)
    if uw and uw["body"]:
        parts.append("## Skill: Using-Werkstatt\n" + uw["body"])
    # systematic-debugging bei Trigger
    trigger = ("ruff", "test", "bug", "fehler", "debug", "pytest")
    if any(w in frage.lower() for w in trigger):
        sd = load_skill_by_name("systematic-debugging", skills)
        if sd and sd["body"]:
            parts.append("## Skill: Systematic-Debugging\n" + sd["body"])
    return "\n\n".join(parts)


def run_explorer(state: RunState, frage: str) -> dict:
    pd = state.project_dir
    pn = state.project_name
    api_key = getattr(state, "api_key", "")

    # === M-373: Deterministische Messung ZUERST ===
    messungen = _messen(frage, Path(pd))
    if messungen:
        audit("explorer_messung", {
            "befehle": list(messungen.keys()),
            "dateien_gesamt": sum(len(m.get("dateien", [])) for m in messungen.values()),
        }, pd, pn)

    # Dateien aus Messung extrahieren -> deterministische key_files
    key_files: list[dict] = []
    for name, m in messungen.items():
        for datei in m.get("dateien", []):
            key_files.append({
                "file": datei,
                "why": f"{name}-Fehler",
                "symbols": "",
                "confidence": "high",
            })

    if key_files:
        audit("explorer_key_files_deterministisch", {
            "n": len(key_files),
            "files": [k["file"] for k in key_files][:20],
        }, pd, pn)
        findings = _format_findings(messungen)
        return {
            "findings": findings,
            "key_files": key_files,
            "next_reads": [k["file"] for k in key_files],
        }

    # === Fallback: LLM-Explorer (bestehender Pfad) ===
    if not api_key:
        audit("explorer_kein_key", {}, pd, pn)
        return {"findings": "", "key_files": [], "next_reads": []}

    py_files = _list_py_files(Path(pd))
    context = (
        f"Frage: {frage}\n\n"
        f"Messungen (bereits ausgefuehrt):\n"
        + (_format_findings(messungen) if messungen else "(keine)")
        + f"\n\nPython-Dateien ({len(py_files)}):\n"
        + "\n".join(py_files[:50])
    )

    reply = ask_llm(
        api_key, _explorer_system(frage), context,
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
