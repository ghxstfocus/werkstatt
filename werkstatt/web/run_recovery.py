"""Fail-closed validation for explicit recovery of a dead web-loop worker."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from werkstatt.event_store import EventStore
from werkstatt.phase_state import PhaseState


class RunRecoveryError(ValueError):
    """The persisted run cannot be resumed without guessing or losing state."""


def prepare_run_recovery(
    project: str,
    project_dir: Path,
    registry_record: dict[str, Any] | None,
    *,
    store: EventStore | None = None,
) -> dict[str, Any]:
    """Validate an idle run and return its pinned context without mutating it."""
    if registry_record is None or registry_record.get("state") != "idle":
        raise RunRecoveryError("Es gibt keinen beendeten Run zur Wiederaufnahme.")
    run_id = registry_record.get("run_id")
    if not isinstance(run_id, str) or not re.fullmatch(
        r"[A-Za-z0-9_.:-]{1,160}", run_id,
    ):
        raise RunRecoveryError("Die gespeicherte Run-ID ist ungueltig.")

    context = registry_record.get("context")
    if not isinstance(context, dict) or context.get("schema_version") != 1:
        raise RunRecoveryError("Der Run-Kontext fehlt oder hat ein unbekanntes Schema.")
    goal = context.get("goal")
    source = context.get("source")
    if not isinstance(goal, str) or not goal.strip() or not isinstance(source, dict):
        raise RunRecoveryError("Ziel oder Quelle des Runs fehlen.")
    run_store = store or EventStore()
    run_record = run_store.get_run_record(project, run_id)
    if run_record is None or run_record.get("target") != goal:
        raise RunRecoveryError("RunRecord fehlt oder Ziel stimmt nicht ueberein.")
    if run_record.get("status") not in {"running", "failed"}:
        raise RunRecoveryError("Der Run ist nicht wiederaufnehmbar.")
    pinned_sha = source.get("pinned_sha")
    if (
        source.get("kind") == "github"
        and run_record.get("base_commit") != pinned_sha
    ):
        raise RunRecoveryError("RunRecord und gepinnte Remote-Revision weichen ab.")

    root = Path(project_dir).resolve()
    source_kind = source.get("kind")
    if source_kind == "local":
        work_dir = root
    elif source_kind == "github":
        work_dir = _validate_github_worktree(root, run_id, source)
    else:
        raise RunRecoveryError("Unbekannter Projektquellentyp im Run-Kontext.")

    if not (work_dir / "docs" / "STATUS.md").is_file():
        raise RunRecoveryError("STATUS.md fehlt im gepinnten Run-Verzeichnis.")
    phase_state = _load_matching_checkpoint(project, work_dir, run_id, goal)
    return {
        "run_id": run_id,
        "goal": goal,
        "op_id": context.get("op_id"),
        "context": context,
        "project_dir": work_dir,
        "checkpoint_version": run_record["checkpoint_version"],
        "checkpoint": phase_state.data,
    }


def _validate_github_worktree(
    project_dir: Path,
    run_id: str,
    source: dict[str, Any],
) -> Path:
    from werkstatt.project_sources import (
        GitHubSyncError,
        _git,
        _managed_worktrees_root,
        _origin_repository,
    )

    worktree_value = source.get("worktree")
    repository = source.get("repository")
    run_branch = source.get("run_branch")
    pinned_sha = source.get("pinned_sha")
    if (
        not isinstance(worktree_value, str)
        or not isinstance(repository, str)
        or not isinstance(run_branch, str)
        or not isinstance(pinned_sha, str)
        or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", pinned_sha.lower())
        or run_branch != f"werkstatt/run/{run_id}"
    ):
        raise RunRecoveryError("Gepinnte GitHub-Quelldaten sind unvollstaendig.")

    try:
        worktree = Path(worktree_value).expanduser().resolve(strict=True)
        managed_root = _managed_worktrees_root(project_dir)
    except (OSError, RuntimeError, GitHubSyncError) as exc:
        raise RunRecoveryError(f"Run-Worktree ist nicht verfuegbar: {exc}") from exc
    if not worktree.is_dir() or worktree.parent != managed_root or worktree.name != run_id:
        raise RunRecoveryError("Run-Worktree liegt ausserhalb des verwalteten Bereichs.")
    try:
        project_repository = _origin_repository(project_dir)
    except GitHubSyncError as exc:
        raise RunRecoveryError(f"GitHub-Repository nicht pruefbar: {exc}") from exc
    if project_repository != repository:
        raise RunRecoveryError("GitHub-Repository stimmt nicht mit dem Run-Kontext ueberein.")

    listed = _git(project_dir, "worktree", "list", "--porcelain")
    top_level = _git(worktree, "rev-parse", "--show-toplevel")
    branch = _git(worktree, "branch", "--show-current")
    listed_paths = {
        Path(line.removeprefix("worktree ")).resolve()
        for line in listed.stdout.splitlines()
        if line.startswith("worktree ")
    }
    if (
        listed.returncode != 0
        or worktree not in listed_paths
        or top_level.returncode != 0
        or Path(top_level.stdout.strip()).resolve() != worktree
        or branch.returncode != 0
        or branch.stdout.strip() != run_branch
    ):
        raise RunRecoveryError("Git-Worktree-Zuordnung oder Run-Branch ist inkonsistent.")
    pinned_is_ancestor = _git(
        worktree, "merge-base", "--is-ancestor", pinned_sha, "HEAD",
    )
    if pinned_is_ancestor.returncode != 0:
        raise RunRecoveryError(
            "Run-Worktree stammt nicht mehr von der gepinnten Remote-Revision ab.",
        )
    return worktree


def _load_matching_checkpoint(
    project: str,
    work_dir: Path,
    run_id: str,
    goal: str,
) -> PhaseState:
    phase_state = PhaseState(project, base_dir=work_dir / ".werkstatt")
    active_path = phase_state.path
    backup_path = active_path.with_suffix(".yaml.fresh-bak")
    candidates = [active_path, backup_path]
    for candidate in candidates:
        if not candidate.is_file():
            continue
        phase_state.path = candidate
        try:
            valid = phase_state.load()
        except (OSError, ValueError, KeyError, RuntimeError):
            valid = False
        finally:
            phase_state.path = active_path
        if (
            valid
            and phase_state.run_id == run_id
            and phase_state.data.get("aufgabe") == goal
        ):
            phase_state.path = candidate
            return phase_state
    raise RunRecoveryError(
        "Kein strukturell gueltiger Phase-Checkpoint fuer diese Run-ID gefunden.",
    )
