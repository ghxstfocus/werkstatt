"""Spec: Dependency-Failure fuehrt zu continue, nicht return 1 (Fix AP)."""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, "/opt/werkstatt")
import pytest


class _FakePS:
    def __init__(self, tasks):
        self.data = {"tasks": tasks}


class TestDependencyFail:
    def test_gleiche_datei_failed(self) -> None:
        from werkstatt.loop import _pruefe_prior_failed_dependency
        ps = _FakePS([
            {"id": "t1", "status": "failed",
             "task_files": ["harness/llm/deepseek_client.py"]},
            {"id": "t2", "status": "pending",
             "task_files": ["harness/llm/deepseek_client.py"]},
        ])
        ok, files = _pruefe_prior_failed_dependency(ps, "t2")
        assert ok is True
        assert "harness/llm/deepseek_client.py" in files

    def test_verschiedene_datei_kein_dep(self) -> None:
        from werkstatt.loop import _pruefe_prior_failed_dependency
        ps = _FakePS([
            {"id": "t1", "status": "failed",
             "task_files": ["harness/llm/deepseek_client.py"]},
            {"id": "t2", "status": "pending",
             "task_files": ["core/config.py"]},
        ])
        ok, _ = _pruefe_prior_failed_dependency(ps, "t2")
        assert ok is False

    def test_prior_done_kein_dep(self) -> None:
        from werkstatt.loop import _pruefe_prior_failed_dependency
        ps = _FakePS([
            {"id": "t1", "status": "done",
             "task_files": ["harness/llm/deepseek_client.py"]},
            {"id": "t2", "status": "pending",
             "task_files": ["harness/llm/deepseek_client.py"]},
        ])
        ok, _ = _pruefe_prior_failed_dependency(ps, "t2")
        assert ok is False

    def test_erste_task_kein_dep(self) -> None:
        from werkstatt.loop import _pruefe_prior_failed_dependency
        ps = _FakePS([
            {"id": "t1", "status": "pending",
             "task_files": ["harness/llm/deepseek_client.py"]},
        ])
        ok, _ = _pruefe_prior_failed_dependency(ps, "t1")
        assert ok is False

    def test_keine_task_files(self) -> None:
        from werkstatt.loop import _pruefe_prior_failed_dependency
        ps = _FakePS([
            {"id": "t1", "status": "failed", "task_files": []},
            {"id": "t2", "status": "pending", "task_files": []},
        ])
        ok, _ = _pruefe_prior_failed_dependency(ps, "t2")
        assert ok is False
