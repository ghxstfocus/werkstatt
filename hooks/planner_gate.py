"""Planner-Gate-Hook (M-349 + M-350 + M-349e).

Deterministische Pruefung des Plans nach dem Planner.
Der Hook ist die Wahrheit — nicht der Prompt.

Checks:
  1. DOKU_TASK: task_files matcht Doku-Regex.
  2. ACTION: action muss read/create/update sein.
  3. TASK_FILE: task_files muss Datei mit Suffix sein.
  4. PHASEN_PFLICHT: >5 Tasks -> phasen Pflicht.
  5. PHASE_ID: phase_id muss in phasen existieren.

Output: {"allow": bool, "reason": str, "info": {...}}
"""
from __future__ import annotations

import json
import re
import sys

_DOKU_PATTERNS = [
    re.compile(r"^docs/.*\.md$"),
    re.compile(r"^CHANGELOG\.md$"),
    re.compile(r"^PROGRESS\.md$"),
    re.compile(r"^README\.md$"),
    re.compile(r"^docs/STATUS\.md$"),
]
_VALID_ACTIONS = {"read", "create", "update"}
_VALID_SUFFIXES = (
    # Code
    ".py", ".sql", ".sh", ".bash",
    # Config
    ".yaml", ".yml", ".toml", ".cfg", ".ini", ".json",
    # Frontend
    ".html", ".css", ".js", ".ts",
)


def _deny(regel: str, task_id: str, datei: str,
          erklaerung: str, details: str) -> dict:
    """M-349e: info als Fakt (kein 'plane neu')."""
    if task_id and datei:
        fakt = f"Task {task_id} aendert {datei}"
    elif task_id:
        fakt = f"Task {task_id} verletzt Regel {regel}"
    elif datei:
        fakt = f"Datei {datei} verletzt Regel {regel}"
    else:
        fakt = f"Regel {regel} verletzt"
    return {
        "allow": False,
        "reason": f"{regel}: {fakt}",
        "info": {
            "regel": regel,
            "fakt": fakt,
            "erklaerung": erklaerung,
            "details": details,
            "verbotene_datei": datei,
        },
    }


def check_plan(payload: dict) -> dict:
    tasks = payload.get("tasks", [])
    phasen = payload.get("phasen", [])

    # 1) DOKU_TASK (Regex, nicht startswith)
    for t in tasks:
        if not isinstance(t, dict):
            continue
        for f in t.get("task_files", []) or []:
            if not isinstance(f, str):
                continue
            for pat in _DOKU_PATTERNS:
                if pat.match(f):
                    return _deny(
                        "DOKU_TASK",
                        t.get("id", "?"),
                        f,
                        "Doku-Tasks sind nicht erlaubt.",
                        "Der Loop schreibt Doku automatisch "
                        "(PROGRESS.md pro Task, CHANGELOG.md pro "
                        "Phase). Der Plan wird nicht gebaut.",
                    )

    # 2) ACTION
    for t in tasks:
        if not isinstance(t, dict):
            continue
        a = t.get("action")
        if a is not None and a not in _VALID_ACTIONS:
            return _deny(
                "ACTION",
                t.get("id", "?"),
                "",
                f"action='{a}' ist nicht erlaubt.",
                f"action='{a}' ist ungueltig. Erlaubte Werte: "
                f"{sorted(_VALID_ACTIONS)}.",
            )

    # 3) TASK_FILE
    for t in tasks:
        if not isinstance(t, dict):
            continue
        for f in t.get("task_files", []) or []:
            if not isinstance(f, str):
                return _deny(
                    "TASK_FILE",
                    t.get("id", "?"),
                    repr(f),
                    "task_files enthaelt Nicht-String.",
                    "task_files: list[str] mit konkreten "
                    "Datei-Pfaden.",
                )
            if f.endswith("/"):
                return _deny(
                    "TASK_FILE",
                    t.get("id", "?"),
                    f,
                    f"'{f}' ist ein Ordner.",
                    f"Erlaubt: Datei mit Suffix "
                    f"{sorted(_VALID_SUFFIXES)}.",
                )
            if not f.endswith(_VALID_SUFFIXES):
                return _deny(
                    "TASK_FILE",
                    t.get("id", "?"),
                    f,
                    f"'{f}' hat kein gueltiges Suffix.",
                    f"Erlaubt: {sorted(_VALID_SUFFIXES)}.",
                )

    # 4) PHASEN_PFLICHT
    if len(tasks) > 5 and not phasen:
        return _deny(
            "PHASEN_PFLICHT",
            "",
            "",
            f"{len(tasks)} Tasks, aber keine Phasen.",
            "Der Plan wird nicht gebaut. Phasen sind Pflicht "
            "bei >5 Tasks (M-323c).",
        )

    # 5) PHASE_ID
    if phasen:
        _ids = {p.get("id") for p in phasen if isinstance(p, dict)}
        for t in tasks:
            if not isinstance(t, dict):
                continue
            pid = t.get("phase_id")
            if pid is not None and pid not in _ids:
                return _deny(
                    "PHASE_ID",
                    t.get("id", "?"),
                    "",
                    f"phase_id='{pid}' ist nicht erlaubt.",
                    f"Gueltig: {sorted(_ids)}.",
                )

    return {"allow": True, "reason": "", "info": {}}


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        print(json.dumps({
            "allow": False,
            "reason": "PAYLOAD: ungueltiges JSON",
            "info": {"regel": "PAYLOAD", "fakt": "JSON ungueltig",
                     "erklaerung": "Payload ist kein JSON.",
                     "details": "Der Plan wird nicht gebaut.",
                     "verbotene_datei": ""},
        }))
        return 0
    print(json.dumps(check_plan(payload), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
