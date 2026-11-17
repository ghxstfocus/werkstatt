"""Task-scoped deterministic Verify role for a coordinator checkpoint."""
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from werkstatt.state import RunState, check_run_lease


@dataclass(frozen=True)
class TaskVerifyResult:
    """Result of one Verify action, including criterion-bound evidence."""

    verify_ok: bool
    evidence_recorded: bool


def verify_failure_detail(state: RunState) -> str | None:
    """Return a bounded JSON summary of current hard Verify errors."""
    errors = getattr(state, "last_verify_errors", None)
    if not isinstance(errors, list):
        return None
    cleaned = [
        error.strip()[:240]
        for error in errors[:4]
        if isinstance(error, str) and error.strip()
    ]
    if not cleaned:
        return None
    evidence: dict[str, Any] = {"source": "verify", "errors": []}
    for error in cleaned:
        candidate = {"source": "verify", "errors": [*evidence["errors"], error]}
        encoded = json.dumps(candidate, ensure_ascii=False, sort_keys=True)
        if len(encoded) > 1200:
            break
        evidence = candidate
    if not evidence["errors"]:
        return None
    return json.dumps(evidence, ensure_ascii=False, sort_keys=True)


def record_task_verify_evidence(
    state: RunState,
    phase_state: Any,
    task_id: str,
    *,
    audit_call: Callable[..., Any],
) -> bool:
    """Persist successful Verify stages for criterion-linked tasks only."""
    task_record = phase_state.get_task(task_id) if phase_state is not None else None
    if not isinstance(task_record, dict):
        return True
    refs = task_record.get("criterion_refs")
    if not isinstance(refs, list) or not refs:
        return True
    recorder = getattr(phase_state, "record_task_verify_evidence", None)
    recorded = False
    if callable(recorder):
        try:
            recorded = recorder(
                task_id,
                getattr(state, "last_verify_results", None),
                phase="post_build",
            ) is True
        except (OSError, RuntimeError, TypeError, ValueError):
            recorded = False
    stage_ids = [
        result.get("stage_id")
        for result in (getattr(state, "last_verify_results", None) or [])
        if isinstance(result, dict)
        and result.get("ok") is True
        and isinstance(result.get("exit_code"), int)
        and not isinstance(result.get("exit_code"), bool)
        and result.get("exit_code") == 0
        and isinstance(result.get("stage_id"), str)
    ]
    payload = {
        "task_id": task_id,
        "criterion_refs": refs[:30],
        "stage_ids": stage_ids[:50],
    }
    if recorded:
        audit_call(
            "loop_criteria_task_verify_evidence",
            payload,
            state.project_dir,
            state.project_name,
        )
    else:
        audit_call(
            "loop_criteria_task_verify_evidence_missing",
            {**payload, "reason": "no_successful_task_verify_stages"},
            state.project_dir,
            state.project_name,
        )
    return recorded


def run_task_verify_checkpoint(
    state: RunState,
    phase_state: Any,
    task_id: str,
    *,
    verify: Callable[..., Any],
    audit_call: Callable[..., Any],
) -> TaskVerifyResult:
    """Run post-build Verify once and bind any successful criterion evidence."""
    verify_ok = bool(verify(state, phase="post_build"))
    check_run_lease(state)
    evidence_recorded = (
        record_task_verify_evidence(
            state, phase_state, task_id, audit_call=audit_call,
        )
        if verify_ok else False
    )
    return TaskVerifyResult(verify_ok, evidence_recorded)


__all__ = [
    "TaskVerifyResult",
    "record_task_verify_evidence",
    "run_task_verify_checkpoint",
    "verify_failure_detail",
]
