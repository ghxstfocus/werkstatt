"""Spec: Rollback opt-in + --resume + Task-Fortschritt (Fixes AA/AB/AC/AD)."""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, "/opt/werkstatt")
import pytest


class TestRollbackOptIn:
    def test_rollback_flag_existiert(self) -> None:
        import werkstatt.loop as _loop
        src = Path(_loop.__file__).read_text(encoding="utf-8")
        assert '"--rollback"' in src

    def test_resume_flag_existiert(self) -> None:
        import werkstatt.loop as _loop
        src = Path(_loop.__file__).read_text(encoding="utf-8")
        assert '"--resume"' in src

    def test_rollback_skipped_audit_kind(self) -> None:
        import werkstatt.audit as _a
        assert "loop_rollback_skipped" in _a._AUDIT_KINDS_BEKANNT

    def test_resume_from_bak_audit_kind(self) -> None:
        import werkstatt.audit as _a
        assert "loop_resume_from_bak" in _a._AUDIT_KINDS_BEKANNT


class TestTaskFortschrittBlock:
    def _write_phase_state(self, tmp_path: Path, tasks: list) -> None:
        import yaml
        (tmp_path / ".werkstatt").mkdir(parents=True, exist_ok=True)
        (tmp_path / ".werkstatt" / "test.phase.yaml").write_text(
            yaml.safe_dump({
                "project": "test",
                "tasks": tasks,
                "status": "in_progress",
            })
        )

    def test_zeigt_done_und_failed(self, tmp_path: Path) -> None:
        self._write_phase_state(tmp_path, [
            {"id": "t1", "name": "A", "status": "done"},
            {"id": "t2", "name": "B", "status": "done"},
            {"id": "t3", "name": "C", "status": "failed",
             "failure": "patch_write_failed"},
            {"id": "t4", "name": "D", "status": "pending"},
        ])
        from werkstatt.loop import _task_fortschritt_block
        out = _task_fortschritt_block(tmp_path, "test")
        assert "Tasks: 2/4 done" in out
        assert "1 failed" in out
        assert "1 offen" in out
        assert "[x] t1" in out
        assert "[!] t3" in out
        assert "patch_write_failed" in out
        assert "[ ] t4" in out

    def test_keine_phase_state_leer(self, tmp_path: Path) -> None:
        from werkstatt.loop import _task_fortschritt_block
        out = _task_fortschritt_block(tmp_path, "nicht_da")
        assert out == ""
