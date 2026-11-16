"""Run-scoped exact-request replay for pure planning model responses."""
from __future__ import annotations

import hashlib

PLANNING_RESPONSE_ROLES = frozenset({"scout", "architect", "planner-split"})
MAX_RESPONSE_CHARS = 60_000
MAX_CACHE_CHARS = 180_000
MAX_CACHE_ENTRIES = 12


def goal_sha256(goal: str) -> str:
    return hashlib.sha256(goal.encode("utf-8")).hexdigest()


def valid_response_entry(
    entry: object,
    *,
    request_sha256: str,
    role: str,
    run_id: str,
    goal: str,
) -> dict[str, str] | None:
    """Validate exact prompt, role, goal, run, size, and output hash binding."""
    if not isinstance(entry, dict):
        return None
    content = entry.get("content")
    content_sha256 = entry.get("content_sha256")
    if (
        entry.get("request_sha256") != request_sha256
        or entry.get("role") != role
        or role not in PLANNING_RESPONSE_ROLES
        or entry.get("run_id") != run_id
        or entry.get("goal_sha256") != goal_sha256(goal)
        or not isinstance(content, str)
        or not content
        or len(content) > MAX_RESPONSE_CHARS
        or not isinstance(content_sha256, str)
        or hashlib.sha256(content.encode("utf-8")).hexdigest()
        != content_sha256
    ):
        return None
    return {
        "role": role,
        "request_sha256": request_sha256,
        "content": content,
        "content_sha256": content_sha256,
        "run_id": run_id,
        "goal_sha256": goal_sha256(goal),
    }


def load_response_cache(
    raw: object,
    *,
    run_id: str,
    goal: str,
) -> dict[str, dict[str, str]]:
    """Load bounded cache entries valid for this exact RunRecord identity."""
    if not isinstance(raw, dict):
        return {}
    result: dict[str, dict[str, str]] = {}
    total_chars = 0
    for request_sha256, raw_entry in list(raw.items())[-MAX_CACHE_ENTRIES:]:
        if (
            not isinstance(request_sha256, str)
            or len(request_sha256) != 64
            or any(char not in "0123456789abcdef" for char in request_sha256)
            or not isinstance(raw_entry, dict)
        ):
            continue
        role = raw_entry.get("role")
        if not isinstance(role, str):
            continue
        entry = valid_response_entry(
            raw_entry,
            request_sha256=request_sha256,
            role=role,
            run_id=run_id,
            goal=goal,
        )
        if entry is None:
            continue
        if total_chars + len(entry["content"]) > MAX_CACHE_CHARS:
            continue
        result[request_sha256] = entry
        total_chars += len(entry["content"])
    return result


def add_response_entry(
    current: object,
    entry: object,
    *,
    run_id: str,
    goal: str,
) -> dict[str, dict[str, str]]:
    """Return a new bounded cache, dropping stale or malformed entries."""
    cache = load_response_cache(current, run_id=run_id, goal=goal)
    if not isinstance(entry, dict):
        return cache
    key = entry.get("request_sha256")
    role = entry.get("role")
    if not isinstance(key, str) or not isinstance(role, str):
        return cache
    valid = valid_response_entry(
        entry, request_sha256=key, role=role,
        run_id=run_id, goal=goal,
    )
    if valid is None:
        return cache
    cache[key] = valid
    while len(cache) > MAX_CACHE_ENTRIES or sum(
        len(item["content"]) for item in cache.values()
    ) > MAX_CACHE_CHARS:
        cache.pop(next(iter(cache)))
    return cache


__all__ = [
    "MAX_CACHE_CHARS", "MAX_CACHE_ENTRIES", "MAX_RESPONSE_CHARS",
    "PLANNING_RESPONSE_ROLES", "add_response_entry", "goal_sha256",
    "load_response_cache", "valid_response_entry",
]
