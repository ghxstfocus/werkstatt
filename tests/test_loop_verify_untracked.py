"""Spec: verify-Stages erkennen untracked Dateien (Fix V)."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, "/opt/werkstatt")
import pytest
from werkstatt.loop import _expand_cmd_placeholders


def _init_repo(tmp_path: Path) -> None:
    def _git(*args):
        subprocess.run(["git", "-C", str(tmp_path), *args],
                       check=True, capture_output=True)
    _git("init", "-q")
    _git("config", "user.email", "t@t")
    _git("config", "user.name", "t")
    (tmp_path / "README.md").write_text("init\n")
    _git("add", "-A")
    _git("commit", "-q", "-m", "init")


class TestVerifyUntracked:
    def test_untracked_py_wird_erkannt(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        (tmp_path / "scripts").mkdir()
        (tmp_path / "scripts" / "new.py").write_text("x = 1\n")
        state = SimpleNamespace(patches=[])
        cmd = ["python3", "-m", "py_compile", "{changed_py_files}"]
        result = _expand_cmd_placeholders(cmd, state, tmp_path)
        assert result is not None
        assert "scripts/new.py" in result

    def test_leerer_repo_stage_skip(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        state = SimpleNamespace(patches=[])
        cmd = ["python3", "-m", "py_compile", "{changed_py_files}"]
        result = _expand_cmd_placeholders(cmd, state, tmp_path)
        assert result is None

    def test_geaenderte_md_wird_von_py_compile_ignoriert(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "STATUS.md").write_text("# x\n")
        state = SimpleNamespace(patches=[])
        cmd = ["python3", "-m", "py_compile", "{changed_py_files}"]
        result = _expand_cmd_placeholders(cmd, state, tmp_path)
        assert result is None
