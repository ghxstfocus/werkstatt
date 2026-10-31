"""Spec: Fix A v3.1 schuetzt Code+Doku-Kombination (Code-Task create)."""
from __future__ import annotations
import sys
sys.path.insert(0, "/opt/werkstatt")
import pytest
from werkstatt.planner import _doku_post_check


class TestCodeUndDoku:
    def test_create_code_plus_md_bleiben_beide(self) -> None:
        tasks = [
            {"id": "t1", "action": "create",
             "task_files": ["scripts/preflight_check.py"]},
            {"id": "t2", "action": "update",
             "task_files": ["docs/STATUS.md"]},
        ]
        aufgabe = ("Lege scripts/preflight_check.py an und aktualisiere "
                   "docs/STATUS.md. Nur diese zwei Dateien.")
        r = _doku_post_check(tasks, "prosa", None, "t", aufgabe)
        assert len(r) == 2

    def test_update_code_nicht_in_aufgabe_wird_gefiltert(self) -> None:
        tasks = [
            {"id": "t1", "action": "update",
             "task_files": ["some/other.py"]},
            {"id": "t2", "action": "update",
             "task_files": ["docs/STATUS.md"]},
        ]
        aufgabe = "Nur docs/STATUS.md aendern, keine Python-Datei."
        r = _doku_post_check(tasks, "prosa", None, "t", aufgabe)
        assert len(r) == 1
        assert r[0]["task_files"] == ["docs/STATUS.md"]
