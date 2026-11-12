"""Tests fuer die sichere Zuordnung des Loop-eigenen Git-Stashs."""
from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from werkstatt import git_ops


def test_git_stash_owned_finds_its_marker_among_foreign_stashes() -> None:
    own_commit = "a" * 40
    foreign_commit = "b" * 40
    commands: list[list[str]] = []
    marker = ""

    def _run(command, **_kwargs):
        nonlocal marker
        commands.append(command)
        if "push" in command:
            marker = command[-1]
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        return SimpleNamespace(
            returncode=0,
            stdout=(
                f"{foreign_commit}\tOn main: foreign stash\n"
                f"{own_commit}\tOn main: {marker}\n"
            ),
            stderr="",
        )

    with patch("werkstatt.git_ops.subprocess.run", side_effect=_run):
        stash_ref = git_ops._git_stash_owned(Path("/project"))

    assert stash_ref == own_commit
    assert commands[1][-1] == "--format=%H%x09%gs"


def test_git_stash_owned_recovers_marker_after_push_timeout() -> None:
    own_commit = "c" * 40
    marker = ""

    def _run(command, **_kwargs):
        nonlocal marker
        if "push" in command:
            marker = command[-1]
            raise subprocess.TimeoutExpired(command, 30)
        return SimpleNamespace(
            returncode=0,
            stdout=f"{own_commit}\tOn main: {marker}\n",
            stderr="",
        )

    with patch("werkstatt.git_ops.subprocess.run", side_effect=_run):
        stash_ref = git_ops._git_stash_owned(Path("/project"))

    assert stash_ref == own_commit


def test_git_stash_owned_does_not_claim_unmarked_foreign_stash() -> None:
    foreign_commit = "d" * 40

    def _run(command, **_kwargs):
        return SimpleNamespace(
            returncode=0,
            stdout=f"{foreign_commit}\tOn main: another actor's stash\n",
            stderr="",
        )

    with patch("werkstatt.git_ops.subprocess.run", side_effect=_run):
        stash_ref = git_ops._git_stash_owned(Path("/project"))

    assert stash_ref is None


def test_git_stash_owned_rejects_ambiguous_marker() -> None:
    commit_a = "e" * 40
    commit_b = "f" * 40
    marker = ""

    def _run(command, **_kwargs):
        nonlocal marker
        if "push" in command:
            marker = command[-1]
        return SimpleNamespace(
            returncode=0,
            stdout=(
                f"{commit_a}\tOn main: {marker}\n"
                f"{commit_b}\tOn main: {marker}\n"
            ),
            stderr="",
        )

    with patch("werkstatt.git_ops.subprocess.run", side_effect=_run):
        stash_ref = git_ops._git_stash_owned(Path("/project"))

    assert stash_ref is None
