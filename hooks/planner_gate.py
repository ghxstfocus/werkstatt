"""Planner-Gate-Hook (M-349 + M-350).

Deterministische Pruefung des Plans nach dem Planner.
Der Hook ist die Wahrheit — nicht der Prompt.

Checks:
  1. Keine Doku-Tasks (M-349): docs/*.md, CHANGELOG.md, ...
  2. action muss read/create/update sein (M-350a).
  3. task_files muss eine Datei mit Suffix sein (M-350a).
  4. Phasen-Pflicht bei >5 Tasks (M-323c, M-350a).
  5. phase_id muss in phasen existieren (M-323c, M-350a).

Output: {"allow": bool, "reason": str, "info": {...}}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_DOKU_MUSTER = (
    "docs/", "CHANGELOG.md", "PROGRESS.md",
    "README.md", "STATUS.md",
)
_VALID_ACTIONS = {"read", "create", "update"}
_VALID_SUFFIXES = (".py", ".yaml", ".yml", ".toml", ".cfg", ".ini", ".json")


def _deny(reason: str, info: dict) -> dict:
    return {"allow": False, "reason": reason, "info": info}


def check_plan(payload: dict) -> dict:
    tasks = payload.get("tasks", [])
    phasen = payload.get("phasen", [])
    project_dir_str = payload.get("project_dir", "")
    project_dir = Path(project_dir_str) if project_dir_str else None

    # 1) Keine Doku-Tasks
    for t in tasks:
        if not isinstance(t, dict):
            continue
        for f in t.get("task_files", []) or []:
            if not isinstance(f, str):
                continue
            for m in _DOKU_MUSTER:
                if f == m or f.startswith(m):
                    return _deny(
                        f"Doku-Task {t.get('id')} verboten: {f}",
                        {
                            "task_id": t.get("id"),
                            "verbotene_datei": f,
                            "hinweis": "Doku wird vom Loop geschrieben. "
                                       "Plane nur Code-Tasks.",
                        },
                    )

    # 2) + 3) action + task_files
    for t in tasks:
        if not isinstance(t, dict):
            continue
        _tid = t.get("id", "?")
        _action = t.get("action")
        if _action is not None and _action not in _VALID_ACTIONS:
            return _deny(
                f"Task {_tid}: action='{_action}' ungueltig "
                f"(erlaubt: read/create/update)",
                {"task_id": _tid, "action": _action},
            )
        _files = t.get("task_files", []) or []
        for f in _files:
            if not isinstance(f, str):
                return _deny(
                    f"Task {_tid}: task_files enthaelt Nicht-String {f!r}",
                    {"task_id": _tid, "datei": repr(f)},
                )
            if not f.endswith(_VALID_SUFFIXES):
                return _deny(
                    f"Task {_tid}: task_files '{f}' hat kein "
                    f"gueltiges Suffix (erlaubt: {_VALID_SUFFIXES})",
                    {"task_id": _tid, "datei": f,
                     "hinweis": "Keine Ordner. Konkrete Datei mit Suffix."},
                )
            if f.endswith("/"):
                return _deny(
                    f"Task {_tid}: task_files '{f}' ist ein Ordner",
                    {"task_id": _tid, "datei": f,
                     "hinweis": "Keine Ordner. Konkrete Datei."},
                )
            # Existenz-Check fuer create (M-350a)
            if project_dir is not None and _action == "create":
                _target = project_dir / f
                if _target.exists():
                    return _deny(
                        f"Task {_tid}: action=create, aber '{f}' existiert",
                        {"task_id": _tid, "datei": f,
                         "hinweis": "Fuer existierende Datei: action=update."},
                    )

    # 4) Phasen-Pflicht bei >5 Tasks
    if len(tasks) > 5 and not phasen:
        return _deny(
            f"{len(tasks)} Tasks, aber keine Phasen",
            {"anzahl_tasks": len(tasks),
             "hinweis": "Bei >5 Tasks sind Phasen Pflicht (M-323c)."},
        )

    # 5) phase_id in phasen
    if phasen:
        _phasen_ids = {
            p.get("id") for p in phasen if isinstance(p, dict)
        }
        for t in tasks:
            if not isinstance(t, dict):
                continue
            _pid = t.get("phase_id")
            if _pid is not None and _pid not in _phasen_ids:
                return _deny(
                    f"Task {t.get('id')}: phase_id='{_pid}' "
                    f"nicht in phasen ({sorted(_phasen_ids)})",
                    {"task_id": t.get("id"), "phase_id": _pid,
                     "phasen_ids": sorted(_phasen_ids)},
                )

    return {"allow": True, "reason": "", "info": {}}


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        print(json.dumps({"allow": False, "reason": "Ungueltiges Payload"}))
        return 0
    print(json.dumps(check_plan(payload), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
