"""Session-bound isolated worktrees for project-chat Debug mode."""
from __future__ import annotations

import difflib
import hashlib
import re
import subprocess
import sys
import uuid
from pathlib import Path, PureWindowsPath
from typing import Any

from werkstatt.debugger_handoff import _safe_path

_COMMAND_TIMEOUT_S = 30
_MAX_FILE_BYTES = 1_000_000
_MAX_DIFF_BYTES = 100_000
_MAX_CHANGED_FILES = 50
_MAX_CHANGED_BYTES = 5_000_000


def _git(root: Path, *args: str, timeout: int = _COMMAND_TIMEOUT_S) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True,
        check=False, timeout=timeout,
    )
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or "Git-Aufruf fehlgeschlagen")[-2000:])
    return result.stdout.strip()


def ensure_debug_workspace(
    source_root: Path | str,
    project_snapshot: Path | str,
    project: str,
    session_id: str,
) -> tuple[Path, str]:
    """Return/create a persistent detached worktree pinned to the chat snapshot."""
    source = Path(source_root).expanduser().resolve(strict=True)
    snapshot = Path(project_snapshot).expanduser().resolve(strict=True)
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", project):
        raise ValueError("Projektname fuer Debug-Workspace ist ungueltig.")
    if not session_id or len(session_id) > 200:
        raise ValueError("Debug-Session fehlt oder ist ungueltig.")
    source_top = Path(_git(source, "rev-parse", "--show-toplevel")).resolve(strict=True)
    snapshot_top = Path(_git(snapshot, "rev-parse", "--show-toplevel")).resolve(strict=True)
    if source_top != source or snapshot_top != snapshot:
        raise ValueError("Debug-Modus benoetigt Repo-Wurzeln als Projektpfad.")
    source_head = _git(source, "rev-parse", "--verify", "HEAD")
    if source_head != _git(snapshot, "rev-parse", "--verify", "HEAD"):
        raise ValueError("Projekt-Checkout und Chat-Snapshot haben unterschiedliche HEADs.")
    project_key = hashlib.sha256(str(source).encode("utf-8")).hexdigest()[:16]
    session_key = hashlib.sha256(session_id.encode("utf-8")).hexdigest()[:32]
    workspace_parent = (
        source.parent / ".werkstatt-chat-workspaces" / project / project_key
    )
    managed_root = source.parent.resolve(strict=True) / ".werkstatt-chat-workspaces"
    resolved_parent = workspace_parent.resolve(strict=False)
    if not resolved_parent.is_relative_to(managed_root):
        raise ValueError("Debug-Workspace-Pfad liegt ausserhalb des verwalteten Bereichs.")
    workspace = workspace_parent / session_key
    if workspace.exists():
        resolved_workspace = workspace.resolve(strict=True)
        top = Path(_git(resolved_workspace, "rev-parse", "--show-toplevel")).resolve(strict=True)
        common = Path(_git(resolved_workspace, "rev-parse", "--git-common-dir"))
        if not common.is_absolute():
            common = (resolved_workspace / common).resolve(strict=True)
        else:
            common = common.resolve(strict=True)
        expected_common = Path(_git(source, "rev-parse", "--git-common-dir"))
        if not expected_common.is_absolute():
            expected_common = (source / expected_common).resolve(strict=True)
        else:
            expected_common = expected_common.resolve(strict=True)
        if top != resolved_workspace or common != expected_common:
            raise ValueError("Vorhandener Debug-Workspace ist kein Worktree dieses Projekts.")
        workspace_head = _git(resolved_workspace, "rev-parse", "--verify", "HEAD")
        return resolved_workspace, workspace_head

    source_status = _git(source, "status", "--porcelain", "--untracked-files=all")
    if source_status:
        raise ValueError("Projekt-Checkout ist nicht sauber; isolierter Debug-Worktree nicht erstellt.")

    workspace_parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["git", "worktree", "add", "--detach", str(workspace), source_head],
        cwd=source, capture_output=True, text=True, check=False,
        timeout=_COMMAND_TIMEOUT_S,
    )
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or "Worktree konnte nicht erstellt werden")[-2000:])
    resolved_workspace = workspace.resolve(strict=True)
    if Path(_git(resolved_workspace, "rev-parse", "--show-toplevel")).resolve(strict=True) != resolved_workspace:
        raise RuntimeError("Erstellter Debug-Workspace hat eine unerwartete Repo-Wurzel.")
    return resolved_workspace, source_head


def _target(workspace: Path, raw_path: Any) -> tuple[str, Path]:
    if (
        not isinstance(raw_path, str)
        or raw_path != raw_path.strip()
        or len(raw_path) > 500
        or any(ord(char) < 32 for char in raw_path)
        or PureWindowsPath(raw_path).drive
    ):
        raise ValueError("Debug-Dateipfad ist ungueltig.")
    relative = _safe_path(raw_path)
    if relative != raw_path:
        raise ValueError("Debug-Dateipfad muss kanonisch angegeben sein.")
    target = workspace / relative
    cursor = workspace
    for part in Path(relative).parts[:-1]:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError("Debug-Dateipfad darf keine Symlink-Verzeichnisse enthalten.")
    resolved_parent = target.parent.resolve(strict=False)
    resolved_parent.relative_to(workspace)
    if target.is_symlink():
        raise ValueError("Debug-Datei darf kein Symlink sein.")
    resolved_target = target.resolve(strict=False)
    resolved_target.relative_to(workspace)
    return relative, resolved_target


def read_debug_file(workspace: Path, raw_path: Any) -> dict[str, Any]:
    relative, path = _target(workspace, raw_path)
    if not path.is_file():
        raise FileNotFoundError(relative)
    content = path.read_bytes()
    if len(content) > _MAX_FILE_BYTES:
        raise ValueError("Datei ueberschreitet das 1-MB-Limit.")
    return {
        "path": relative,
        "content": content.decode("utf-8"),
        "bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def write_debug_file(workspace: Path, raw_path: Any, content: Any) -> dict[str, Any]:
    relative, path = _target(workspace, raw_path)
    if not isinstance(content, str):
        raise TypeError("Dateiinhalt muss Text sein.")
    encoded = content.encode("utf-8")
    if b"\x00" in encoded:
        raise ValueError("Binaerer Inhalt ist im Debug-Texteditor nicht zulaessig.")
    if len(encoded) > _MAX_FILE_BYTES:
        raise ValueError("Dateiinhalt ueberschreitet das 1-MB-Limit.")
    tracked = _git(workspace, "diff", "--name-only", "-z", "HEAD")
    untracked = _git(workspace, "ls-files", "--others", "--exclude-standard", "-z")
    changed_paths = {
        path for path in (tracked + "\x00" + untracked).split("\x00") if path
    }
    if relative not in changed_paths:
        changed_paths.add(relative)
    if len(changed_paths) > _MAX_CHANGED_FILES:
        raise ValueError("Debug-Workspace ueberschreitet 50 geaenderte Dateien.")
    total_bytes = len(encoded)
    for changed in changed_paths:
        if changed == relative:
            continue
        _safe_path(changed)
        changed_path = (workspace / changed).resolve(strict=False)
        changed_path.relative_to(workspace)
        if changed_path.is_symlink():
            raise ValueError("Debug-Workspace enthaelt eine geaenderte Symlink-Datei.")
        if changed_path.is_file():
            total_bytes += changed_path.stat().st_size
    if total_bytes > _MAX_CHANGED_BYTES:
        raise ValueError("Debug-Workspace ueberschreitet 5 MB geaenderte Inhalte.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.parent.resolve(strict=True).relative_to(workspace)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    created = False
    try:
        with temporary.open("xb") as stream:
            created = True
            stream.write(encoded)
        temporary.replace(path)
    finally:
        if created:
            temporary.unlink(missing_ok=True)
    return {
        "path": relative,
        "bytes": len(encoded),
        "sha256": hashlib.sha256(encoded).hexdigest(),
    }


def debug_diff(workspace: Path) -> dict[str, Any]:
    result = subprocess.run(
        ["git", "diff", "--binary", "HEAD"], cwd=workspace,
        capture_output=True, check=False, timeout=_COMMAND_TIMEOUT_S,
    )
    if result.returncode:
        raise RuntimeError("Debug-Diff konnte nicht gelesen werden.")
    raw = result.stdout or b""
    diff_parts = [raw.decode("utf-8", errors="replace")]
    untracked = _git(workspace, "ls-files", "--others", "--exclude-standard", "-z")
    candidates = [path for path in untracked.split("\x00") if path]
    generated = [
        path for path in candidates
        if "__pycache__" in Path(path).parts
        or ".pytest_cache" in Path(path).parts
        or Path(path).name == ".coverage"
        or Path(path).suffix in {".pyc", ".pyo"}
    ]
    untracked_paths = [path for path in candidates if path not in generated]
    for raw_path in untracked_paths:
        relative = _safe_path(raw_path)
        raw_target = workspace / relative
        if raw_target.is_symlink():
            raise ValueError(f"Unversionierte Debug-Quelle ist ein Symlink: {relative}")
        path = raw_target.resolve(strict=True)
        path.relative_to(workspace)
        if not path.is_file():
            raise ValueError(f"Unversionierte Debug-Quelle ist keine Datei: {relative}")
        content = path.read_bytes()
        if b"\x00" in content or len(content) > _MAX_FILE_BYTES:
            raise ValueError(f"Unversionierte Datei ist binaer oder zu gross: {relative}")
        text = content.decode("utf-8")
        lines = text.splitlines(keepends=True)
        if lines and not lines[-1].endswith(("\n", "\r")):
            lines[-1] += "\n"
        diff_parts.append(
            f"diff --git a/{relative} b/{relative}\n"
            f"new file mode 100644\n"
            f"index 0000000..{_git(workspace, 'hash-object', relative)}\n"
            + "".join(difflib.unified_diff(
                [], lines, fromfile="/dev/null", tofile=f"b/{relative}",
            ))
        )
    complete_diff = "".join(diff_parts).encode("utf-8")
    return {
        "base_head": _git(workspace, "rev-parse", "--verify", "HEAD"),
        "changed_files": _git(workspace, "diff", "--name-only", "HEAD").splitlines(),
        "diff_bytes": len(complete_diff),
        "diff_sha256": hashlib.sha256(complete_diff).hexdigest(),
        "diff": complete_diff[:_MAX_DIFF_BYTES].decode("utf-8", errors="replace"),
        "truncated": len(complete_diff) > _MAX_DIFF_BYTES,
        "untracked_files": untracked_paths,
        "excluded_generated_files": generated,
    }


def run_debug_tests(workspace: Path, raw_path: Any, selector: Any = "") -> dict[str, Any]:
    relative, path = _target(workspace, raw_path)
    if not relative.startswith("tests/"):
        raise ValueError("Debug-Tests muessen unter tests/ liegen.")
    if not path.exists():
        raise FileNotFoundError(relative)
    if not isinstance(selector, str) or len(selector) > 200:
        raise ValueError("Testauswahl muss Text mit maximal 200 Zeichen sein.")
    command = [sys.executable, "-m", "pytest", "-q", str(path)]
    if selector.strip():
        command.extend(["-k", selector.strip()])
    result = subprocess.run(
        command, cwd=workspace, capture_output=True, text=True,
        check=False, timeout=120,
    )
    output = (result.stdout or "") + (result.stderr or "")
    return {
        "exit_code": result.returncode,
        "path": relative,
        "command": command[1:],
        "output": output[-12_000:],
        "truncated": len(output) > 12_000,
    }
