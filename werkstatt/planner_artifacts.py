"""Bounded, run-scoped outputs for resumable planner role handoffs."""
from __future__ import annotations

import hashlib
import json
from typing import Any

ARTIFACT_SCHEMA = "planner_role_artifact_v1"
MAX_ARTIFACT_CHARS = 60_000
MAX_ARTIFACTS = 4
_ROLE_OUTPUT_TYPES = {
    "scout": dict,
    "architect": str,
    "planner_split": dict,
    "planner_handoff": dict,
}


def _canonical(value: Any) -> str | None:
    try:
        return json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        )
    except (TypeError, ValueError):
        return None


def value_sha256(value: Any) -> str | None:
    encoded = _canonical(value)
    if encoded is None:
        return None
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def goal_sha256(goal: str) -> str:
    return hashlib.sha256(goal.encode("utf-8")).hexdigest()


def make_role_artifact(
    role: str,
    output: Any,
    *,
    run_id: str,
    goal: str,
    input_sha256: str,
) -> dict[str, Any] | None:
    """Create an artifact only for a known role and bounded output."""
    expected_type = _ROLE_OUTPUT_TYPES.get(role)
    encoded = _canonical(output)
    output_sha256 = value_sha256(output)
    if (
        expected_type is None
        or not isinstance(run_id, str) or not run_id
        or not isinstance(goal, str) or not goal
        or not isinstance(input_sha256, str)
        or len(input_sha256) != 64
        or any(char not in "0123456789abcdef" for char in input_sha256)
        or not isinstance(output, expected_type)
        or encoded is None or not encoded or len(encoded) > MAX_ARTIFACT_CHARS
        or output_sha256 is None
    ):
        return None
    return {
        "schema": ARTIFACT_SCHEMA,
        "role": role,
        "run_id": run_id,
        "goal_sha256": goal_sha256(goal),
        "input_sha256": input_sha256,
        "output": output,
        "output_sha256": output_sha256,
    }


def validate_role_artifact(
    raw: object,
    *,
    role: str,
    run_id: str,
    goal: str,
    input_sha256: str,
) -> dict[str, Any] | None:
    """Validate identity, exact inputs, output type, digest, and size."""
    if not isinstance(raw, dict):
        return None
    expected_type = _ROLE_OUTPUT_TYPES.get(role)
    output = raw.get("output")
    encoded = _canonical(output)
    output_sha256 = value_sha256(output)
    if (
        expected_type is None
        or raw.get("schema") != ARTIFACT_SCHEMA
        or raw.get("role") != role
        or raw.get("run_id") != run_id
        or raw.get("goal_sha256") != goal_sha256(goal)
        or raw.get("input_sha256") != input_sha256
        or not isinstance(output, expected_type)
        or encoded is None or not encoded or len(encoded) > MAX_ARTIFACT_CHARS
        or raw.get("output_sha256") != output_sha256
    ):
        return None
    return {
        "schema": ARTIFACT_SCHEMA,
        "role": role,
        "run_id": run_id,
        "goal_sha256": goal_sha256(goal),
        "input_sha256": input_sha256,
        "output": output,
        "output_sha256": output_sha256,
    }


def load_role_artifacts(
    raw: object,
    *,
    run_id: str,
    goal: str,
) -> dict[str, dict[str, Any]]:
    """Discard unknown, stale, oversized, or hash-invalid role artifacts."""
    if not isinstance(raw, dict):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for role in ("scout", "architect", "planner_split", "planner_handoff"):
        artifact = raw.get(role)
        if not isinstance(artifact, dict):
            continue
        input_sha256 = artifact.get("input_sha256")
        if not isinstance(input_sha256, str):
            continue
        valid = validate_role_artifact(
            artifact,
            role=role,
            run_id=run_id,
            goal=goal,
            input_sha256=input_sha256,
        )
        if valid is not None:
            result[role] = valid
    return result


def add_role_artifact(
    current: object,
    artifact: object,
    *,
    run_id: str,
    goal: str,
) -> dict[str, dict[str, Any]]:
    """Return the small validated artifact map for this run and goal."""
    result = load_role_artifacts(current, run_id=run_id, goal=goal)
    if not isinstance(artifact, dict):
        return result
    role = artifact.get("role")
    input_sha256 = artifact.get("input_sha256")
    if not isinstance(role, str) or not isinstance(input_sha256, str):
        return result
    valid = validate_role_artifact(
        artifact,
        role=role,
        run_id=run_id,
        goal=goal,
        input_sha256=input_sha256,
    )
    if valid is None:
        return result
    result[role] = valid
    while len(result) > MAX_ARTIFACTS:
        result.pop(next(iter(result)))
    return result


__all__ = [
    "ARTIFACT_SCHEMA",
    "MAX_ARTIFACTS",
    "MAX_ARTIFACT_CHARS",
    "add_role_artifact",
    "goal_sha256",
    "load_role_artifacts",
    "make_role_artifact",
    "validate_role_artifact",
    "value_sha256",
]
