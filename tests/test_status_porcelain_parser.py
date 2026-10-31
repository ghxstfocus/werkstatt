"""Spec: status --porcelain Parser mit fuehrendem Leerzeichen (Fix X)."""
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
    (tmp_path / "a.py").write_text("init\n")
    _git("add", "-A")
    _git("commit", "-q", "-m", "init")


class TestStatusPorcelainParser:
    def test_modified_tracked_wird_erkannt(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        (tmp_path / "a.py").write_text("geaendert\n")
        state = SimpleNamespace(patches=[])
        cmd = ["python3", "-m", "py_compile", "{changed_py_files}"]
        result = _expand_cmd_placeholders(cmd, state, tmp_path)
        assert result is not None, "modified tracked wurde nicht erkannt"
        assert "a.py" in result

    def test_untracked_wird_erkannt(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        (tmp_path / "b.py").write_text("x = 1\n")
        state = SimpleNamespace(patches=[])
        cmd = ["python3", "-m", "py_compile", "{changed_py_files}"]
        result = _expand_cmd_placeholders(cmd, state, tmp_path)
        assert result is not None
        assert "b.py" in result

    def test_staged_wird_erkannt(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        (tmp_path / "a.py").write_text("neu\n")
        subprocess.run(["git", "-C", str(tmp_path), "add", "-A"],
                       check=True, capture_output=True)
        state = SimpleNamespace(patches=[])
        cmd = ["python3", "-m", "py_compile", "{changed_py_files}"]
        result = _expand_cmd_placeholders(cmd, state, tmp_path)
        assert result is not None
        assert "a.py" in result

    def test_gemischt_modified_und_untracked(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        (tmp_path / "a.py").write_text("geaendert\n")
        (tmp_path / "b.py").write_text("neu\n")
        state = SimpleNamespace(patches=[])
        cmd = ["python3", "-m", "py_compile", "{changed_py_files}"]
        result = _expand_cmd_placeholders(cmd, state, tmp_path)
        assert result is not None
        assert "a.py" in result
        assert "b.py" in result
