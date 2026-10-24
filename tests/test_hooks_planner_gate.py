"""Tests fuer hooks/planner_gate.py (M-349 + M-350)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_HOOK = Path("/opt/werkstatt/hooks/planner_gate.py")


def _run(payload: dict) -> dict:
    res = subprocess.run(
        [sys.executable, str(_HOOK)],
        input=json.dumps(payload),
        capture_output=True, text=True, timeout=10, check=False,
    )
    assert res.returncode == 0, f"rc={res.returncode} stderr={res.stderr}"
    return json.loads(res.stdout)


def test_doku_task_verboten():
    """M-349: Doku-Task -> allow=false."""
    result = _run({
        "tasks": [{"id": "t1", "action": "update",
                   "task_files": ["docs/STATUS.md"]}],
    })
    assert result["allow"] is False
    assert result["info"]["regel"] == "DOKU_TASK"
    assert "docs/STATUS.md" in result["info"]["fakt"]


def test_action_ungueltig():
    """M-350a: action nicht in read/create/update -> allow=false."""
    result = _run({
        "tasks": [{"id": "t1", "action": "write",
                   "task_files": ["core/x.py"]}],
    })
    assert result["allow"] is False
    assert result["info"]["regel"] == "ACTION"
    assert "write" in result["info"]["details"]


def test_task_files_ordner_verboten():
    """M-350a: task_files ohne Suffix -> allow=false."""
    result = _run({
        "tasks": [{"id": "t1", "action": "update",
                   "task_files": ["core/checks/"]}],
    })
    assert result["allow"] is False
    assert result["info"]["regel"] in ("TASK_FILE", "DOKU_TASK")


def test_phasen_pflicht_bei_6_tasks():
    """M-350a: >5 Tasks ohne Phasen -> allow=false."""
    tasks = [
        {"id": f"t{i}", "action": "read", "task_files": ["core/x.py"]}
        for i in range(1, 7)
    ]
    result = _run({"tasks": tasks})
    assert result["allow"] is False
    assert result["info"]["regel"] == "PHASEN_PFLICHT"
    assert "Phasen" in result["info"]["details"]


def test_gueltiger_plan_erlaubt():
    """M-349/350: Valider Plan -> allow=true."""
    result = _run({
        "tasks": [
            {"id": "t1", "action": "update",
             "task_files": ["core/x.py"], "phase_id": "p1"},
        ],
        "phasen": [{"id": "p1", "titel": "P1", "tasks": ["t1"]}],
    })
    assert result["allow"] is True
