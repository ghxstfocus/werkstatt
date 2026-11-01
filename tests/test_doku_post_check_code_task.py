"""OP-006: _doku_post_check darf Code-Tasks nicht wegwerfen."""
from __future__ import annotations
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, "/opt/werkstatt")

from werkstatt.planner import _doku_post_check


def test_code_task_nicht_weggeworfen():
    """Live-Beleg 2026-11-01: Aufgabe 'nur Delegation' + split .py
    -> Tasks muessen erhalten bleiben."""
    aufgabe = (
        "Arbeite OP-002b1 aus docs/STATUS.md ab. "
        "Der Task ist atomar: NUR Delegation an update_last_ip_if_changed."
    )
    tasks = [{
        "id": "t1",
        "name": "upsert_seen delegiert last_ip an Helfer",
        "action": "update",
        "task_files": ["core/inventory/repository.py"],
        "description": "...",
    }]
    result = _doku_post_check(
        tasks, "prosa", MagicMock(), "test", aufgabe=aufgabe,
    )
    assert len(result) == 1
    assert result[0]["id"] == "t1"
    assert result[0]["task_files"] == ["core/inventory/repository.py"]


def test_reine_doku_aufgabe_reduziert():
    """Wenn NUR .md-Tasks im Split sind, greift die Reduktion."""
    aufgabe = "Aktualisiere nur docs/STATUS.md"
    tasks = [
        {"id": "t1", "action": "update",
         "task_files": ["docs/STATUS.md"], "description": "..."},
        {"id": "t2", "action": "update",
         "task_files": ["docs/ROADMAP.md"], "description": "..."},
    ]
    result = _doku_post_check(
        tasks, "prosa", MagicMock(), "test", aufgabe=aufgabe,
    )
    assert len(result) == 1
    assert result[0]["id"] == "t1"


def test_leere_aufgabe_kein_trigger():
    """Ohne Trigger-Worte: Tasks bleiben unveraendert."""
    tasks = [{"id": "t1", "action": "update",
              "task_files": ["docs/STATUS.md"]}]
    result = _doku_post_check(
        tasks, "prosa", MagicMock(), "test", aufgabe="",
    )
    assert len(result) == 1
