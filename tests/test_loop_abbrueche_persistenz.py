"""Spec: Task-Failures landen in .werkstatt/abbrueche.jsonl (Fix AE)."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, "/opt/werkstatt")
import pytest


class _FakePS:
    def mark_failed(self, task_id, *, failure):
        pass
    def mark_done(self, task_id, *, decision=None):
        pass


class TestAbbruechePersistenz:
    def test_failed_task_schreibt_jsonl(self, tmp_path: Path) -> None:
        from werkstatt.loop import _task_ende
        state = SimpleNamespace(
            project_dir=tmp_path, project_name="t",
            aufgabe="x", tasks=[], tasks_ok_counter=0,
        )
        _task_ende(state, _FakePS(), "t5", ok=False,
                   name="chat_cli.py", failure="patch_write_failed",
                   dateien=["scripts/chat_cli.py"])
        _abr = tmp_path / ".werkstatt" / "abbrueche.jsonl"
        assert _abr.exists()
        _lines = _abr.read_text(encoding="utf-8").strip().splitlines()
        assert len(_lines) == 1
        _rec = json.loads(_lines[0])
        assert _rec["task_id"] == "t5"
        assert _rec["failure"] == "patch_write_failed"
        assert "scripts/chat_cli.py" in _rec["dateien"]

    def test_done_task_schreibt_keine_jsonl(self, tmp_path: Path) -> None:
        from werkstatt.loop import _task_ende
        state = SimpleNamespace(
            project_dir=tmp_path, project_name="t",
            aufgabe="x", tasks=[], tasks_ok_counter=0,
        )
        _task_ende(state, _FakePS(), "t1", ok=True, name="ok-task")
        _abr = tmp_path / ".werkstatt" / "abbrueche.jsonl"
        assert not _abr.exists()

    def test_mehrere_failures_append(self, tmp_path: Path) -> None:
        from werkstatt.loop import _task_ende
        state = SimpleNamespace(
            project_dir=tmp_path, project_name="t",
            aufgabe="x", tasks=[], tasks_ok_counter=0,
        )
        _task_ende(state, _FakePS(), "t5", ok=False, failure="a")
        _task_ende(state, _FakePS(), "t6", ok=False, failure="b")
        _abr = tmp_path / ".werkstatt" / "abbrueche.jsonl"
        _lines = _abr.read_text(encoding="utf-8").strip().splitlines()
        assert len(_lines) == 2
