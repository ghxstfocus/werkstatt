"""Spec: Planner + Builder lesen Failures aus PhaseState (Fix AF)."""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, "/opt/werkstatt")
import pytest


def _write_phase_state(tmp_path: Path, tasks: list) -> None:
    import yaml
    (tmp_path / ".werkstatt").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".werkstatt" / "test.phase.yaml").write_text(
        yaml.safe_dump({
            "project": "test",
            "tasks": tasks,
            "status": "in_progress",
        })
    )


class TestPlannerFailuresFeedback:
    def test_failures_aus_phasestate(self, tmp_path: Path) -> None:
        _write_phase_state(tmp_path, [
            {"id": "t5", "name": "Chat-CLI",
             "status": "failed", "failure": "patch_write_failed",
             "task_files": ["scripts/chat_cli.py"]},
            {"id": "t1", "name": "DeepSeekClient",
             "status": "done", "failure": None,
             "task_files": ["harness/llm/deepseek_client.py"]},
        ])
        from werkstatt.phase_state import PhaseState
        _ps = PhaseState("test", base_dir=tmp_path / ".werkstatt")
        _ps.load()
        _fails = [
            t for t in _ps.data.get("tasks", [])
            if isinstance(t, dict) and t.get("status") == "failed"
        ]
        assert len(_fails) == 1
        assert _fails[0]["id"] == "t5"
        assert _fails[0]["failure"] == "patch_write_failed"

    def test_keine_failures_leer(self, tmp_path: Path) -> None:
        _write_phase_state(tmp_path, [
            {"id": "t1", "name": "A", "status": "done", "failure": None},
        ])
        from werkstatt.phase_state import PhaseState
        _ps = PhaseState("test", base_dir=tmp_path / ".werkstatt")
        _ps.load()
        _fails = [
            t for t in _ps.data.get("tasks", [])
            if isinstance(t, dict) and t.get("status") == "failed"
        ]
        assert _fails == []
