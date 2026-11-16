"""Persist structured, bounded evidence for a failed final verification."""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_SECRET_ASSIGNMENT = re.compile(
    r"(?i)\b(api[_-]?key|access[_-]?token|secret|password|authorization)"
    r"(\s*[:=]\s*)([^\s,;]+)"
)
_BEARER = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
_KEY_TOKEN = re.compile(r"\b(?:sk|gh[pousr]t?)-[A-Za-z0-9_-]{12,}\b")
_UNVERSIONED_MAX_ENTRIES = 10_000
_UNVERSIONED_MAX_BYTES = 64 * 1024 * 1024


def _audit_root() -> Path:
    from werkstatt.audit import _werkstatt_home

    return _werkstatt_home()


def _git_output(project_dir: Path, *args: str) -> bytes | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(project_dir), *args],
            capture_output=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode:
        return None
    return result.stdout or b""


def _worktree_fingerprint(project_dir: Path) -> str | None:
    """Hash tracked diffs and contents of non-ignored untracked files.

    Untracked contents are hashed, never persisted. Symlink targets are
    hashed as link text and are not followed outside the project tree. A
    project without a Git checkout has no worktree fingerprint.
    """
    root = project_dir.resolve()
    if not any((parent / ".git").exists() for parent in (root, *root.parents)):
        return _unversioned_tree_fingerprint(root)
    status = _git_output(
        project_dir, "status", "--porcelain=v1", "--untracked-files=all",
    )
    diff = _git_output(project_dir, "diff", "--binary", "HEAD")
    untracked = _git_output(
        project_dir, "ls-files", "--others", "--exclude-standard", "-z",
    )
    if status is None or diff is None or untracked is None:
        return None
    digest = hashlib.sha256(status + b"\0" + diff)
    root = project_dir.resolve()
    paths = sorted(part for part in untracked.split(b"\0") if part)
    for raw_path in paths:
        relative = Path(os.fsdecode(raw_path))
        digest.update(b"\0untracked\0")
        digest.update(raw_path)
        digest.update(b"\0")
        if relative.is_absolute():
            digest.update(b"<invalid-path>")
            continue
        candidate = root / relative
        try:
            candidate.parent.resolve().relative_to(root)
            mode = candidate.lstat().st_mode
            if os.path.islink(candidate):
                digest.update(b"symlink:")
                digest.update(os.fsencode(os.readlink(candidate)))
            elif stat.S_ISREG(mode):
                digest.update(b"file:")
                with candidate.open("rb") as handle:
                    while chunk := handle.read(1024 * 1024):
                        digest.update(chunk)
            else:
                digest.update(b"non-regular-file")
        except (OSError, ValueError):
            digest.update(b"<unavailable>")
        digest.update(b"\0")
    return digest.hexdigest()


def _unversioned_tree_fingerprint(root: Path) -> str | None:
    """Hash a small non-Git tree; return unavailable when the bound is hit."""
    digest = hashlib.sha256(b"werkstatt-unversioned-tree-v1\0")
    pending = [root]
    entries_seen = 0
    bytes_seen = 0
    try:
        while pending:
            directory = pending.pop()
            with os.scandir(directory) as iterator:
                entries = list(iterator)
            entries_seen += len(entries)
            if entries_seen > _UNVERSIONED_MAX_ENTRIES:
                return None
            entries.sort(key=lambda item: item.name)
            child_directories: list[Path] = []
            for entry in entries:
                path = Path(entry.path)
                if entry.name in {".git", ".werkstatt"} and entry.is_dir(
                    follow_symlinks=False,
                ):
                    continue
                relative = path.relative_to(root).as_posix()
                raw_relative = os.fsencode(relative)
                digest.update(raw_relative + b"\0")
                if entry.is_symlink():
                    digest.update(b"symlink\0")
                    digest.update(os.fsencode(os.readlink(path)))
                elif entry.is_dir(follow_symlinks=False):
                    digest.update(b"directory\0")
                    child_directories.append(path)
                elif entry.is_file(follow_symlinks=False):
                    size = entry.stat(follow_symlinks=False).st_size
                    bytes_seen += size
                    if bytes_seen > _UNVERSIONED_MAX_BYTES:
                        return None
                    digest.update(b"file\0")
                    with path.open("rb") as handle:
                        while chunk := handle.read(1024 * 1024):
                            digest.update(chunk)
                else:
                    digest.update(b"non-regular\0")
                digest.update(b"\0")
            pending.extend(reversed(child_directories))
        return digest.hexdigest()
    except OSError:
        return None


def _redact_excerpt(value: Any) -> str:
    excerpt = str(value or "")[:1200]
    excerpt = _SECRET_ASSIGNMENT.sub(r"\1\2[REDACTED]", excerpt)
    excerpt = _BEARER.sub("Bearer [REDACTED]", excerpt)
    return _KEY_TOKEN.sub("[REDACTED_TOKEN]", excerpt)


def create_failure_record(state: Any, *, stage: str) -> dict[str, Any]:
    """Write replayable final-verify evidence outside the project tree.

    The artifact stores bounded stage evidence, the checkout HEAD and a
    fingerprint of the staged, unstaged and untracked worktree state.
    Full command output is never copied into this artifact.
    """
    run_id = str(getattr(state, "run_id", "") or "")
    project_name = str(getattr(state, "project_name", "") or "")
    project_dir = Path(getattr(state, "project_dir", ".")).resolve()
    raw_run_id = run_id or "run-unknown"
    safe_run_id = (
        raw_run_id if re.fullmatch(r"[A-Za-z0-9._-]{1,128}", raw_run_id)
        else hashlib.sha256(raw_run_id.encode("utf-8", errors="replace")).hexdigest()
    )
    safe_stage = re.sub(r"[^A-Za-z0-9._-]", "_", str(stage))[:80] or "verify"

    head = _git_output(project_dir, "rev-parse", "--verify", "HEAD")
    fingerprint = _worktree_fingerprint(project_dir)
    work_sha = (
        head.decode("ascii", errors="ignore").strip()
        if head is not None else ""
    ) or None
    failed_stages = []
    for item in getattr(state, "last_verify_results", []) or []:
        if not isinstance(item, dict) or item.get("ok") is True:
            continue
        failed_stages.append({
            "stage_id": str(item.get("stage_id") or "?")[:120],
            "exit_code": item.get("exit_code"),
            "error_excerpt": _redact_excerpt(item.get("error_excerpt")),
        })

    record_id = uuid.uuid4().hex
    root = Path(_audit_root()).resolve()
    directory = root / "audit-logs" / safe_run_id / "failures"
    target = directory / f"{safe_stage}-{record_id}.json"
    record = {
        "schema_version": 1,
        "failure_id": record_id,
        "run_id": raw_run_id,
        "project": project_name,
        "stage": str(stage)[:120],
        "created_at": datetime.now(UTC).isoformat(),
        "work_sha": work_sha,
        "worktree_fingerprint": fingerprint,
        "failed_stages": failed_stages,
    }
    temp_name: str | None = None
    try:
        directory.mkdir(parents=True, exist_ok=True)
        if os.path.commonpath((str(root), str(target.resolve()))) != str(root):
            raise ValueError("Failure-Record-Pfad verlaesst Audit-Verzeichnis")
        serialized = json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=directory,
            prefix=".failure-",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_name = handle.name
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, target)
    except (OSError, ValueError) as exc:
        if temp_name is not None:
            try:
                Path(temp_name).unlink(missing_ok=True)
            except OSError:
                pass
        return {
            "failure_id": record_id,
            "artifact_ref": None,
            "persistence_error": type(exc).__name__,
            "work_sha": record["work_sha"],
            "worktree_fingerprint": fingerprint,
            "failed_stages": failed_stages,
        }

    record["artifact_ref"] = target.relative_to(root).as_posix()
    return record
