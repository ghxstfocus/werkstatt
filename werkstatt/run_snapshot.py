"""Immutable, run-scoped source snapshots for background chat jobs (OP-401)."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from werkstatt.paths import werkstatt_home

__all__ = ["ProjectSnapshot", "SnapshotError", "create_project_snapshot", "remove_project_snapshot"]


class SnapshotError(RuntimeError):
    """Raised when a stable, isolated project snapshot cannot be proven."""


@dataclass(frozen=True)
class ProjectSnapshot:
    path: Path
    head: str
    fingerprint: str


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode:
        raise SnapshotError(
            f"git {' '.join(args[:2])} failed ({result.returncode}): "
            f"{result.stderr.strip()[:500]}",
        )
    return result.stdout


def _valid_id(value: str, label: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", value) or value in {".", ".."}:
        raise SnapshotError(f"Ungueltige {label}-ID.")
    return value


def _file_lists(root: Path) -> tuple[list[str], list[str]]:
    tracked = _git(root, "ls-files", "--cached", "-z").split("\0")
    untracked = _git(
        root, "ls-files", "--others", "--exclude-standard", "-z",
    ).split("\0")
    return sorted(item for item in tracked if item), sorted(
        item for item in untracked if item
    )


def _digest(root: Path, paths: list[str]) -> str:
    digest = hashlib.sha256()
    for name in paths:
        relative = PurePosixPath(name)
        if relative.is_absolute() or ".." in relative.parts:
            raise SnapshotError("Git lieferte einen unsicheren Snapshot-Pfad.")
        path = root.joinpath(*relative.parts)
        digest.update(name.encode("utf-8", errors="surrogateescape"))
        digest.update(b"\0")
        try:
            info = path.lstat()
        except FileNotFoundError:
            digest.update(b"missing\0")
            continue
        if path.is_symlink():
            target = os.readlink(path)
            resolved = (path.parent / target).resolve()
            if not resolved.is_relative_to(root.resolve()):
                raise SnapshotError(f"Symlink verlaesst das Projekt: {name}")
            digest.update(b"link\0")
            digest.update(target.encode("utf-8", errors="surrogateescape"))
        elif path.is_file():
            digest.update(b"file\0")
            digest.update(str(info.st_mode & 0o777).encode("ascii"))
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
        else:
            raise SnapshotError(f"Kein regulaerer Projektpfad: {name}")
        digest.update(b"\0")
    return digest.hexdigest()


def _remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


def _copy_file(source: Path, destination: Path, project_root: Path) -> None:
    if source.is_symlink():
        target = os.readlink(source)
        if not (source.parent / target).resolve().is_relative_to(project_root.resolve()):
            raise SnapshotError(f"Symlink verlaesst das Projekt: {source}")
        destination.symlink_to(target)
    elif source.is_file():
        shutil.copy2(source, destination, follow_symlinks=False)
    else:
        raise SnapshotError(f"Projektdatei fehlt oder ist ungueltig: {source}")


def _managed_root(source: Path, project: str, run_id: str) -> Path:
    project_key = hashlib.sha256(str(source.resolve()).encode("utf-8")).hexdigest()[:20]
    return (
        werkstatt_home() / ".werkstatt" / "chat-snapshots"
        / project_key / _valid_id(run_id, "Run")
    )


def create_project_snapshot(
    project_dir: Path,
    project: str,
    run_id: str,
    job_id: str,
) -> ProjectSnapshot:
    """Copy a Git worktree's exact tracked/untracked state into a private clone.

    The source file inventory, contents, and HEAD are hashed before and after
    copying. A concurrent mutation makes the operation fail instead of exposing
    a partial tree to the chat worker.
    """
    source = Path(project_dir).resolve()
    project = _valid_id(project, "Projekt")
    run_id = _valid_id(run_id, "Run")
    job_id = _valid_id(job_id, "Job")
    if not source.is_dir():
        raise SnapshotError("Projekt-Worktree ist nicht verfuegbar.")
    top = Path(_git(source, "rev-parse", "--show-toplevel").strip()).resolve()
    if top != source:
        raise SnapshotError("Snapshot-Quelle ist nicht die Git-Worktree-Wurzel.")

    final_root = _managed_root(source, project, run_id)
    final_path = final_root / job_id
    final_root.mkdir(parents=True, exist_ok=True)
    if final_path.exists() or final_path.is_symlink():
        try:
            manifest = json.loads((final_path / ".werkstatt-snapshot.json").read_text())
        except (OSError, ValueError):
            raise SnapshotError("Ein unvollstaendiger Snapshot belegt bereits die Job-ID.")
        if (
            manifest.get("project") == project
            and manifest.get("run_id") == run_id
            and manifest.get("job_id") == job_id
        ):
            return ProjectSnapshot(
                final_path, str(manifest["head"]), str(manifest["fingerprint"]),
            )
        raise SnapshotError("Snapshot-ID gehoert zu einem anderen Auftrag.")

    tracked, untracked = _file_lists(source)
    head = _git(source, "rev-parse", "HEAD").strip()
    source_fingerprint = _digest(source, sorted(set(tracked + untracked)))
    temporary = final_root / f".{job_id}.{uuid.uuid4().hex}.tmp"
    try:
        _git_clone = subprocess.run(
            ["git", "clone", "--quiet", "--no-hardlinks", "--no-checkout",
             str(source), str(temporary)],
            check=False,
            capture_output=True,
            text=True,
            timeout=180,
        )
        if _git_clone.returncode:
            raise SnapshotError(
                f"Git-Snapshot konnte nicht geklont werden: "
                f"{_git_clone.stderr.strip()[:500]}",
            )
        _git(temporary, "checkout", "--quiet", "--detach", head)
        tracked_in_source, untracked_in_source = _file_lists(source)
        tracked_set = set(tracked_in_source)
        for name in tracked_in_source:
            relative = PurePosixPath(name)
            source_file = source.joinpath(*relative.parts)
            target_file = temporary.joinpath(*relative.parts)
            if not source_file.exists() and not source_file.is_symlink():
                _remove_path(target_file)
                continue
            target_file.parent.mkdir(parents=True, exist_ok=True)
            _remove_path(target_file)
            _copy_file(source_file, target_file, source)
        for name in untracked_in_source:
            if name in tracked_set:
                continue
            relative = PurePosixPath(name)
            source_file = source.joinpath(*relative.parts)
            target_file = temporary.joinpath(*relative.parts)
            target_file.parent.mkdir(parents=True, exist_ok=True)
            _remove_path(target_file)
            _copy_file(source_file, target_file, source)

        final_tracked, final_untracked = _file_lists(source)
        final_head = _git(source, "rev-parse", "HEAD").strip()
        final_fingerprint = _digest(source, sorted(set(final_tracked + final_untracked)))
        if (
            final_head != head
            or final_tracked != tracked
            or final_untracked != untracked
            or final_fingerprint != source_fingerprint
        ):
            raise SnapshotError("Projektstand hat sich waehrend des Snapshots geaendert.")

        manifest = {
            "project": project,
            "run_id": run_id,
            "job_id": job_id,
            "head": head,
            "fingerprint": source_fingerprint,
        }
        (temporary / ".werkstatt-snapshot.json").write_text(
            json.dumps(manifest, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )
        os.replace(temporary, final_path)
        return ProjectSnapshot(final_path, head, source_fingerprint)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SnapshotError(f"Snapshot fehlgeschlagen: {exc}") from exc
    finally:
        if temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)


def remove_project_snapshot(
    snapshot_path: Path,
    project_dir: Path,
    project: str,
    run_id: str,
    job_id: str,
) -> bool:
    """Remove only the exact managed snapshot addressed by its job identity."""
    source = Path(project_dir).resolve()
    expected = (_managed_root(source, project, run_id) / _valid_id(job_id, "Job"))
    actual = Path(snapshot_path)
    if actual.is_symlink() or actual.resolve() != expected.resolve():
        raise SnapshotError("Snapshot-Cleanup ausserhalb des verwalteten Job-Pfads.")
    if not actual.exists():
        return False
    manifest = json.loads((actual / ".werkstatt-snapshot.json").read_text())
    if (
        manifest.get("project") != project
        or manifest.get("run_id") != run_id
        or manifest.get("job_id") != job_id
    ):
        raise SnapshotError("Snapshot-Cleanup Identitaet stimmt nicht ueberein.")
    shutil.rmtree(actual)
    return True
