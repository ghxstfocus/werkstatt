"""Serverseitige GitHub-Run-Worktrees."""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from werkstatt import project_sources as sources


@pytest.fixture(autouse=True)
def _managed_worktree_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "WERKSTATT_RUN_WORKTREE_DIR",
        str(tmp_path / "werkstatt-state" / "run-worktrees"),
    )


def _git(path: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _repo_with_origin(root: Path) -> tuple[Path, Path]:
    origin = root / "origin.git"
    project = root / "project"
    origin.mkdir()
    project.mkdir()
    subprocess.run(
        ["git", "init", "--bare", "--initial-branch=main", str(origin)],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(project), "init", "--initial-branch=main"],
        check=True,
    )
    _git(project, "config", "user.name", "Werkstatt Test")
    _git(project, "config", "user.email", "test@example.invalid")
    (project / "README.md").write_text("base\n", encoding="utf-8")
    _git(project, "add", "README.md")
    _git(project, "commit", "-m", "base")
    _git(project, "remote", "add", "origin", str(origin))
    _git(project, "push", "-u", "origin", "main")
    return project, origin


def _push_remote_commit(origin: Path, root: Path) -> str:
    remote_clone = root / "remote-clone"
    subprocess.run(
        ["git", "clone", str(origin), str(remote_clone)],
        check=True,
        capture_output=True,
    )
    _git(remote_clone, "config", "user.name", "Remote Test")
    _git(remote_clone, "config", "user.email", "remote@example.invalid")
    (remote_clone / "REMOTE.md").write_text("new remote revision\n", encoding="utf-8")
    _git(remote_clone, "add", "REMOTE.md")
    _git(remote_clone, "commit", "-m", "remote update")
    _git(remote_clone, "push", "origin", "main")
    return _git(remote_clone, "rev-parse", "HEAD")


@pytest.mark.parametrize(
    ("remote", "expected"),
    [
        ("https://github.com/example/project.git", "example/project"),
        ("git@github.com:example/project.git", "example/project"),
        ("ssh://git@github.com/example/project.git", "example/project"),
    ],
)
def test_github_slug_accepts_supported_remotes(remote: str, expected: str) -> None:
    assert sources._github_slug(remote) == expected


@pytest.mark.parametrize(
    "remote",
    [
        "https://token:secret@github.com/example/project.git",
        "http://github.com/example/project.git",
        "https://github.com/example/project.git?token=secret",
        "https://github.com/example/project/extra.git",
    ],
)
def test_github_slug_rejects_unsafe_remotes(remote: str) -> None:
    with pytest.raises(sources.GitHubSyncError):
        sources._github_slug(remote)


def test_prepare_worktree_pins_latest_remote_without_mutating_base(
    tmp_path: Path,
) -> None:
    project, origin = _repo_with_origin(tmp_path)
    base_sha = _git(project, "rev-parse", "HEAD")
    remote_sha = _push_remote_commit(origin, tmp_path)
    with patch.object(sources, "_github_slug", return_value="example/project"):
        prepared = sources.prepare_github_run_worktree(project, "demo-run")

    assert prepared is not None
    assert prepared.repository == "example/project"
    assert prepared.branch == "main"
    assert prepared.base_sha == base_sha
    assert prepared.remote_sha == remote_sha
    assert prepared.run_branch == "werkstatt/run/demo-run"
    assert _git(prepared.worktree_path, "rev-parse", "HEAD") == remote_sha
    remote_content = (prepared.worktree_path / "REMOTE.md").read_text(encoding="utf-8")
    assert remote_content == "new remote revision\n"
    assert _git(project, "rev-parse", "HEAD") == base_sha
    assert _git(project, "status", "--porcelain") == ""
    assert not (project / ".werkstatt").exists()
    assert not prepared.worktree_path.is_relative_to(project)
    run_branch = _git(prepared.worktree_path, "branch", "--show-current")
    assert run_branch == prepared.run_branch


def test_prepare_worktree_can_repeat_without_repo_ignore_rule(tmp_path: Path) -> None:
    project, origin = _repo_with_origin(tmp_path)
    remote_sha = _push_remote_commit(origin, tmp_path)
    with patch.object(sources, "_github_slug", return_value="example/project"):
        first = sources.prepare_github_run_worktree(project, "first-run")
        second = sources.prepare_github_run_worktree(project, "second-run")

    assert first is not None
    assert second is not None
    assert first.remote_sha == second.remote_sha == remote_sha
    assert first.worktree_path != second.worktree_path
    assert all(
        not prepared.worktree_path.is_relative_to(project)
        for prepared in (first, second)
    )
    assert not (project / ".werkstatt").exists()
    assert _git(project, "status", "--porcelain") == ""


def test_prepare_worktree_rejects_storage_inside_checkout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project, _origin = _repo_with_origin(tmp_path)
    monkeypatch.setenv("WERKSTATT_RUN_WORKTREE_DIR", str(project / ".state"))
    with (
        patch.object(sources, "_github_slug", return_value="example/project"),
        pytest.raises(sources.GitHubSyncError, match="ausserhalb des Projekt-Checkouts"),
    ):
        sources.prepare_github_run_worktree(project, "unsafe-storage")


def test_prepare_worktree_rejects_dirty_server_checkout(tmp_path: Path) -> None:
    project, _origin = _repo_with_origin(tmp_path)
    (project / "README.md").write_text("local change\n", encoding="utf-8")
    with (
        patch.object(sources, "_github_slug", return_value="example/project"),
        pytest.raises(sources.GitHubSyncError, match="lokale Aenderungen"),
    ):
        sources.prepare_github_run_worktree(project, "dirty-run")


def test_prepare_worktree_rejects_local_and_remote_divergence(tmp_path: Path) -> None:
    project, origin = _repo_with_origin(tmp_path)
    _git(project, "checkout", "-b", "server-only")
    (project / "SERVER.md").write_text("server commit\n", encoding="utf-8")
    _git(project, "add", "SERVER.md")
    _git(project, "commit", "-m", "server-only")
    _git(project, "branch", "--set-upstream-to=origin/main", "server-only")
    _push_remote_commit(origin, tmp_path)
    with (
        patch.object(sources, "_github_slug", return_value="example/project"),
        pytest.raises(sources.GitHubSyncError, match="voraus oder divergiert"),
    ):
        sources.prepare_github_run_worktree(project, "diverged-run")


def test_prepare_worktree_returns_none_for_non_github_project(tmp_path: Path) -> None:
    project, _origin = _repo_with_origin(tmp_path)
    with patch.object(sources, "_origin_repository", return_value=None):
        assert sources.prepare_github_run_worktree(project, "local-run") is None


def test_remove_prepared_worktree_removes_only_run_owned_branch(tmp_path: Path) -> None:
    project, origin = _repo_with_origin(tmp_path)
    _push_remote_commit(origin, tmp_path)
    with patch.object(sources, "_github_slug", return_value="example/project"):
        prepared = sources.prepare_github_run_worktree(project, "cleanup-run")
    assert prepared is not None
    sources.remove_prepared_worktree(project, prepared)
    assert not prepared.worktree_path.exists()
    assert _git(project, "branch", "--list", prepared.run_branch) == ""
    assert _git(project, "rev-parse", "HEAD") != ""


def test_origin_errors_fail_closed_for_a_git_checkout(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    error = subprocess.CompletedProcess(
        args=["git"], returncode=128, stdout="", stderr="git config damaged",
    )
    with (
        patch.object(sources, "_git", return_value=error),
        pytest.raises(sources.GitHubSyncError, match="nicht sicher geprueft"),
    ):
        sources._origin_repository(tmp_path)

