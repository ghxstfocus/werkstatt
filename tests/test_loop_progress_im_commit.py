"""Spec: PROGRESS.md landet im selben Commit wie der Task-Diff (Fix K)."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, "/opt/werkstatt")
import pytest


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


def _state(tmp_path: Path, tasks: list):
    return SimpleNamespace(
        project_dir=tmp_path,
        project_name="test",
        aufgabe="x",
        tasks=tasks,
        tasks_ok_counter=len([t for t in tasks if t.get("status") == "done"]),
        git_author_name="tester",
        git_author_email="tester@example.com",
    )


class TestProgressImCommit:
    def test_progress_md_ist_im_selben_commit(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "STATUS.md").write_text("# Status\n")
        from werkstatt import loop as _loop
        state = _state(tmp_path, [{
            "id": "t1", "status": "done",
            "task_files": ["docs/STATUS.md"],
        }])
        ok, sha = _loop._committe_zielprojekt(state)
        assert ok is True
        assert sha != ""
        head_files = subprocess.run(
            ["git", "-C", str(tmp_path), "diff-tree", "--no-commit-id",
             "--name-only", "-r", "HEAD"],
            capture_output=True, text=True,
        ).stdout.splitlines()
        assert "docs/STATUS.md" in head_files
        assert "PROGRESS.md" in head_files, (
            f"PROGRESS.md fehlt im Commit. Enthalten: {head_files}"
        )

    def test_working_tree_clean_nach_commit(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        # audit-logs/ wird von audit() ins project_dir geschrieben.
        # Als untracked ignorieren — gehoert nicht zum Commit.
        (tmp_path / ".gitignore").write_text("audit-logs/\n")
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "STATUS.md").write_text("# Status\n")
        from werkstatt import loop as _loop
        state = _state(tmp_path, [{
            "id": "t1", "status": "done",
            "task_files": ["docs/STATUS.md"],
        }])
        ok, _ = _loop._committe_zielprojekt(state)
        assert ok is True
        status = subprocess.run(
            ["git", "-C", str(tmp_path), "status", "--porcelain", "-uall"],
            capture_output=True, text=True,
        ).stdout.strip()
        # audit-logs/ darf als untracked uebrig bleiben
        relevant = [
            ln for ln in status.splitlines()
            if "audit-logs/" not in ln
        ]
        assert relevant == [], f"Working Tree nicht clean: {relevant}"
