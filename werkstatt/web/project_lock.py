"""Shared in-process locks for project-scoped Loop lifecycle operations."""
from __future__ import annotations

import threading
from typing import Any

_LOCKS: dict[str, Any] = {}
_GUARD = threading.Lock()


def project_loop_lock(project: str) -> Any:
    """Return the same lifecycle lock to every web control path."""
    with _GUARD:
        return _LOCKS.setdefault(project, threading.RLock())
