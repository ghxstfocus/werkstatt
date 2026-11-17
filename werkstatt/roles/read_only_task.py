"""Read approved project files and return bounded provenance evidence."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any


def read_task_scope_evidence(
    project_dir: str | Path,
    raw_paths: Any,
) -> tuple[list[dict[str, str | int]], str]:
    """Read a task's exact scope without following paths outside its project.

    The result contains metadata and hashes only. It deliberately does not
    return source text; downstream workers must request their own bounded,
    current source context.
    """
    if not isinstance(raw_paths, list) or not raw_paths:
        return [], "read_task_scope_missing"
    if len(raw_paths) > 50:
        return [], "read_task_scope_too_large"

    try:
        root = Path(project_dir).resolve(strict=True)
        total_bytes = 0
        seen_paths: set[str] = set()
        evidence: list[dict[str, str | int]] = []
        for raw_path in raw_paths:
            if not isinstance(raw_path, str) or not raw_path.strip():
                raise ValueError("read_task_path_invalid")
            relative = Path(raw_path)
            if (
                relative.is_absolute()
                or ".." in relative.parts
                or raw_path.replace("\\", "/").startswith("/")
            ):
                raise ValueError("read_task_path_outside_project")
            target = (root / relative).resolve(strict=True)
            target.relative_to(root)
            if not target.is_file():
                raise ValueError("read_task_source_not_file")
            normalized = target.relative_to(root).as_posix()
            if normalized in seen_paths:
                raise ValueError("read_task_duplicate_path")
            seen_paths.add(normalized)
            source_bytes = target.read_bytes()
            total_bytes += len(source_bytes)
            if len(source_bytes) > 1_000_000 or total_bytes > 4_000_000:
                raise ValueError("read_task_source_over_budget")
            evidence.append({
                "file": normalized,
                "sha256": sha256(source_bytes).hexdigest(),
                "bytes": len(source_bytes),
                "lines": (
                    source_bytes.count(b"\n")
                    + int(bool(source_bytes) and not source_bytes.endswith(b"\n"))
                ),
            })
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return [], str(exc)[:120]
    return evidence, ""
