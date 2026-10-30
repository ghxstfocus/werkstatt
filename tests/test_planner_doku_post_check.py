"""Spec: Doku-Post-Check reduziert Task-Liste auf 1 .md-Task.

Regression 2026-10-30 23:03: 19 task_files fuer 1 Datei-Aufgabe.
Fix A v2: Trigger ueber User-Auftrag (nur/ausschliesslich/keine python).
"""
from __future__ import annotations
import sys
from types import SimpleNamespace
sys.path.insert(0, "/opt/werkstatt")
import pytest
from werkstatt.planner import _doku_post_check


def _task(i, files):
    return {"id": f"t{i}", "name": f"T{i}", "action": "update",
            "task_files": files, "description": "x"}


class TestDokuPostCheck:
    def test_19_tasks_werden_zu_1(self) -> None:
        tasks = [_task(i, ["docs/STATUS.md"] if i == 1
                        else [f"file_{i}.py"]) for i in range(1, 20)]
        aufgabe = "Punkt 1 entfernen. Nur docs/STATUS.md, keine Python-Datei."
        r = _doku_post_check(tasks, "prosa", None, "t", aufgabe)
        assert len(r) == 1
        assert r[0]["task_files"] == ["docs/STATUS.md"]

    def test_kein_doku_trigger_keine_reduktion(self) -> None:
        tasks = [_task(1, ["core/a.py"]), _task(2, ["core/b.py"])]
        aufgabe = "Refactor core/a.py und core/b.py."
        r = _doku_post_check(tasks, "prosa", None, "t", aufgabe)
        assert len(r) == 2

    def test_trigger_aber_keine_md_task_leer(self) -> None:
        tasks = [_task(1, ["core/a.py"])]
        aufgabe = "Nur docs/STATUS.md aendern. Keine Python-Datei."
        r = _doku_post_check(tasks, "prosa", None, "t", aufgabe)
        assert r == []

    def test_mehrere_md_tasks_erste_behalten(self) -> None:
        tasks = [_task(1, ["docs/STATUS.md"]),
                 _task(2, ["docs/ROADMAP.md"])]
        aufgabe = "Nur docs/STATUS.md aendern."
        r = _doku_post_check(tasks, "prosa", None, "t", aufgabe)
        assert len(r) == 1
        assert r[0]["task_files"] == ["docs/STATUS.md"]

    def test_leere_tasks_bleiben_leer(self) -> None:
        assert _doku_post_check([], "x", None, "t", "x") == []


class TestCodeTaskSchutz:
    """Fix A v3: Code-Tasks werden nicht weggeworfen."""

    def test_code_task_bleibt_erhalten(self) -> None:
        tasks = [
            {"id": "t1", "name": "Preflight-Skript",
             "action": "create", "task_files": ["scripts/preflight.py"]},
            {"id": "t2", "name": "STATUS updaten",
             "action": "update", "task_files": ["docs/STATUS.md"]},
        ]
        aufgabe = "Nur docs/STATUS.md, keine Python-Datei."  # Trigger
        r = _doku_post_check(tasks, "prosa", None, "t", aufgabe)
        assert len(r) == 2, f"Code-Task weggeworfen: {r}"

    def test_nur_md_tasks_reduziert(self) -> None:
        tasks = [
            {"id": "t1", "task_files": ["docs/STATUS.md"]},
            {"id": "t2", "task_files": ["docs/ROADMAP.md"]},
        ]
        r = _doku_post_check(tasks, "prosa", None, "t",
                             "Nur docs/STATUS.md aendern.")
        assert len(r) == 1
        assert r[0]["task_files"] == ["docs/STATUS.md"]
