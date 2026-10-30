"""Tests fuer hooks/planner_gate.py (M-349 + M-350 + K5.1)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_HOOK = Path("/opt/werkstatt/hooks/planner_gate.py")


def _run(payload: dict) -> dict:
    proc = subprocess.run(
        [sys.executable, str(_HOOK)],
        input=json.dumps(payload),
        capture_output=True, text=True, timeout=10, check=False,
    )
    return json.loads(proc.stdout)


def test_doku_only_plan_verboten():
    """Plan mit NUR Doku-Task -> abgelehnt."""
    result = _run({
        "tasks": [{"id": "t1", "task_files": ["docs/STATUS.md"], "action": "update"}],
        "phasen": [],
    })
    assert result["allow"] is False
    assert result["info"]["regel"] == "DOKU_TASK"


def test_code_plus_doku_erlaubt():
    """K5.1: Code-Task + Doku-Task -> erlaubt (Doku ist Nachtrag)."""
    result = _run({
        "tasks": [
            {"id": "t1", "task_files": ["app/foo.py"], "action": "update"},
            {"id": "t2", "task_files": ["docs/STATUS.md"], "action": "update"},
        ],
        "phasen": [],
    })
    assert result["allow"] is True, result


def test_nur_code_erlaubt():
    result = _run({
        "tasks": [{"id": "t1", "task_files": ["app/foo.py"], "action": "update"}],
        "phasen": [],
    })
    assert result["allow"] is True


def test_ungueltige_action():
    result = _run({
        "tasks": [{"id": "t1", "task_files": ["a.py"], "action": "write"}],
        "phasen": [],
    })
    assert result["allow"] is False
    assert result["info"]["regel"] == "ACTION"


def test_ordner_abgelehnt():
    result = _run({
        "tasks": [{"id": "t1", "task_files": ["app/"], "action": "update"}],
        "phasen": [],
    })
    assert result["allow"] is False
    assert result["info"]["regel"] in ("TASK_FILE", "DOKU_TASK")


def test_phasen_optional_bei_vielen_tasks():
    """K5.2: Phasen sind optional. 7 Code-Tasks ohne Phasen -> erlaubt."""
    tasks = [
        {"id": f"t{i}", "task_files": ["app/foo.py"], "action": "update"}
        for i in range(1, 8)
    ]
    result = _run({"tasks": tasks, "phasen": []})
    assert result["allow"] is True, result


def test_phasen_mit_gueltiger_id_erlaubt():
    """Phasen sind erlaubt, wenn sie gueltig sind."""
    tasks = [
        {"id": "t1", "task_files": ["app/foo.py"], "action": "update",
         "phase_id": "p1"},
    ]
    result = _run({"tasks": tasks, "phasen": [{"id": "p1"}]})
    assert result["allow"] is True, result


def test_phasen_mit_ungueltiger_id_abgelehnt():
    """PHASE_ID-Check bleibt: ungueltige phase_id -> deny."""
    tasks = [
        {"id": "t1", "task_files": ["app/foo.py"], "action": "update",
         "phase_id": "p_falsch"},
    ]
    result = _run({"tasks": tasks, "phasen": [{"id": "p1"}]})
    assert result["allow"] is False
    assert result["info"]["regel"] == "PHASE_ID"


# =====================================================================
# GOLD 2026-10-30: Doku-Aufgaben erlauben
# =====================================================================

def test_doku_only_plan_bei_doku_aufgabe_erlaubt():
    """Wenn die Prosa nur Doku nennt, ist ein Doku-Only-Plan ok.

    Regression: Live 2026-10-30 22:17: Aufgabe 'entferne Punkt 1
    aus docs/STATUS.md', Planner-Split baute 1 Doku-Task, Hook
    lehnte ab -> 3x Plan-Reflection -> Loop-Abbruch.
    """
    import sys
    sys.path.insert(0, "/opt/werkstatt/hooks")
    import planner_gate as pg

    payload = {
        "tasks": [
            {"id": "t1", "name": "STATUS Punkt 1 entfernen",
             "action": "update",
             "task_files": ["docs/STATUS.md"]},
        ],
        "phasen": [],
        "architect_prosa": (
            "## docs/STATUS.md\n"
            "In docs/STATUS.md den Punkt 1 entfernen. Keine "
            "Python-Datei.\n"
        ),
        "project_dir": "",
    }
    result = pg.check_plan(payload)
    assert result["allow"] is True, result


def test_doku_only_plan_ohne_doku_aufgabe_abgelehnt():
    """Wenn die Prosa Code nennt, ist ein Doku-Only-Plan ungueltig."""
    import sys
    sys.path.insert(0, "/opt/werkstatt/hooks")
    import planner_gate as pg

    payload = {
        "tasks": [
            {"id": "t1", "action": "update",
             "task_files": ["docs/STATUS.md"]},
        ],
        "phasen": [],
        "architect_prosa": (
            "## core/foo.py\n"
            "In core/foo.py die Funktion bar() anpassen.\n"
        ),
        "project_dir": "",
    }
    result = pg.check_plan(payload)
    assert result["allow"] is False
    assert result["info"]["regel"] == "DOKU_TASK"
