"""Integrity and path isolation tests for run-bound project snapshots."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from werkstatt import run_snapshot


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True,
    ).stdout.strip()


def _repo(root: Path) -> Path:
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "tests@example.invalid")
    _git(root, "config", "user.name", "Werkstatt Tests")
    (root / "README.md").write_text("base\n", encoding="utf-8")
    _git(root, "add", "README.md")
    _git(root, "commit", "-qm", "base")
    return root


def test_snapshot_contains_exact_tracked_and_untracked_worktree_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _repo(tmp_path / "project")
    monkeypatch.setattr(run_snapshot, "werkstatt_home", lambda: tmp_path / "state")
    (source / "README.md").write_text("working tree edit\n", encoding="utf-8")
    (source / "new.py").write_text("answer = 42\n", encoding="utf-8")
    (source / "obsolete.txt").write_text("remove me\n", encoding="utf-8")
    _git(source, "add", "obsolete.txt")
    _git(source, "commit", "-qm", "tracked file")
    (source / "obsolete.txt").unlink()

    snapshot = run_snapshot.create_project_snapshot(
        source, "demo", "run-1", "job-1",
    )

    assert snapshot.path != source
    assert (snapshot.path / "README.md").read_text() == "working tree edit\n"
    assert (snapshot.path / "new.py").read_text() == "answer = 42\n"
    assert not (snapshot.path / "obsolete.txt").exists()
    assert _git(snapshot.path, "rev-parse", "HEAD") == snapshot.head
    assert _git(snapshot.path, "status", "--short")


def test_snapshot_rejects_source_mutation_during_copy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _repo(tmp_path / "project")
    monkeypatch.setattr(run_snapshot, "werkstatt_home", lambda: tmp_path / "state")
    original = run_snapshot._digest
    calls = 0

    def changing_digest(root: Path, paths: list[str]) -> str:
        nonlocal calls
        value = original(root, paths)
        calls += 1
        if calls == 1:
            (source / "README.md").write_text("changed mid-copy\n", encoding="utf-8")
        return value

    monkeypatch.setattr(run_snapshot, "_digest", changing_digest)
    with pytest.raises(run_snapshot.SnapshotError, match="gewaendert"):
        run_snapshot.create_project_snapshot(source, "demo", "run-2", "job-2")

    assert not list((tmp_path / "state").rglob("job-2"))


def test_snapshot_rejects_symlink_escape_and_cleanup_outside_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _repo(tmp_path / "project")
    monkeypatch.setattr(run_snapshot, "werkstatt_home", lambda: tmp_path / "state")
    outside = tmp_path / "secret.txt"
    outside.write_text("secret", encoding="utf-8")
    (source / "secret-link").symlink_to(outside)

    with pytest.raises(run_snapshot.SnapshotError, match="Symlink"):
        run_snapshot.create_project_snapshot(source, "demo", "run-3", "job-3")

    with pytest.raises(run_snapshot.SnapshotError, match="Cleanup"):
        run_snapshot.remove_project_snapshot(
            outside, source, "demo", "run-3", "job-3",
        )
