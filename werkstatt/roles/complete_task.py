"""Verify a task's current review dispatch and record its terminal outcome."""
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from werkstatt.state import RunState

CompletionStatus = Literal[
    "completed", "stale", "review_rejected", "failed",
]


@dataclass(frozen=True)
class TaskCompletionResult:
    """Small result returned to the run coordinator after one task action."""

    status: CompletionStatus
    tasks_ok_delta: int = 0
    diff_sha256: str | None = None
    reason: str = ""


@dataclass(frozen=True)
class TaskCompletionServices:
    """Adapters for project-specific review and checkpoint operations."""

    audit_call: Callable[..., Any]
    get_git_diff: Callable[..., str | None]
    reviewer_dispatch_decision: Callable[..., dict[str, Any]]
    review: Callable[[RunState, int], bool]
    task_end: Callable[..., bool]
    audit_task_ok: Callable[..., Any]
    reviewer_rejected_payload: Callable[..., dict[str, Any]]
    check_lease: Callable[[RunState], Any]


def complete_task_checkpoint(
    state: RunState,
    phase_state: Any,
    task: dict[str, Any],
    *,
    task_id: str,
    task_name: str,
    task_index: int,
    decision: str,
    decision_payload: dict[str, Any],
    services: TaskCompletionServices,
) -> TaskCompletionResult:
    """Complete one task after rechecking its evidence and review decision."""
    if decision not in {"review_task_checkpoint", "complete_task_checkpoint"}:
        return TaskCompletionResult("failed", reason="task_completion_action_invalid")
    if decision_payload.get("next_executor") not in {"reviewer", "task_completion"}:
        return TaskCompletionResult("failed", reason="task_completion_executor_invalid")

    record = phase_state.get_task(task_id)
    review_checkpoint = (
        record.get("review_checkpoint") if isinstance(record, dict) else None
    )
    current_check = getattr(
        phase_state, "task_review_checkpoint_is_current", None,
    )
    if (
        not isinstance(review_checkpoint, dict)
        or not callable(current_check)
        or current_check(task_id) is not True
    ):
        services.audit_call(
            "loop_coordinator_dispatch_stale",
            {
                "action": decision,
                "task_id": task_id,
                "reason": "review_checkpoint_verify_evidence_missing_or_stale",
            },
            state.project_dir,
            state.project_name,
        )
        return TaskCompletionResult("stale", reason="review_checkpoint_stale")

    review_warnings = review_checkpoint.get("verify_warnings")
    review_warnings = review_warnings if isinstance(review_warnings, list) else []
    try:
        current_diff = services.get_git_diff(
            project_dir=state.project_dir,
            task_files=task.get("task_files"),
        )
    except (OSError, RuntimeError, TypeError, ValueError):
        current_diff = None
    current_review = services.reviewer_dispatch_decision(
        task,
        current_diff,
        verify_warnings=review_warnings,
        recovery=bool(
            getattr(state, "reflection_chat_builder_reserve_active", False)
            or getattr(state, "reflection_chat_evidence", None)
        ),
    )
    should_review = current_review.get("invoke_reviewer") is True
    persisted_dispatch = decision_payload.get("review_dispatch")
    persisted_evidence = (
        persisted_dispatch.get("evidence")
        if isinstance(persisted_dispatch, dict) else None
    )
    current_evidence = current_review.get("evidence")
    current_sha = (
        current_evidence.get("diff_sha256")
        if isinstance(current_evidence, dict) else None
    )
    if (
        (decision == "review_task_checkpoint") != should_review
        or not isinstance(persisted_evidence, dict)
        or current_sha != persisted_evidence.get("diff_sha256")
    ):
        services.audit_call(
            "loop_coordinator_dispatch_stale",
            {
                "action": decision,
                "task_id": task_id,
                "reason": "review_dispatch_evidence_changed",
            },
            state.project_dir,
            state.project_name,
        )
        return TaskCompletionResult("stale", reason="review_dispatch_stale")

    if should_review:
        state.reviewer_bugs = []
        state.reviewer_deterministic_fail = False
        if not services.review(state, task_index):
            review_failure = json.dumps(
                state.reviewer_bugs or [], ensure_ascii=False,
            )[:1200]
            transitioned = services.task_end(
                state, phase_state, task_id, ok=False, name=task_name,
                failure="reviewer_rejected_at_checkpoint",
                failure_detail=review_failure,
            )
            if not transitioned:
                return TaskCompletionResult(
                    "failed", reason="reviewer_rejection_transition_failed",
                )
            services.audit_call(
                "loop_reviewer_rejected",
                services.reviewer_rejected_payload(
                    task_id, {"bugs": state.reviewer_bugs or []},
                ),
                state.project_dir,
                state.project_name,
            )
            phase_state.save()
            return TaskCompletionResult(
                "review_rejected", reason="reviewer_rejected_at_checkpoint",
            )
        services.check_lease(state)

    transitioned = services.task_end(
        state, phase_state, task_id, ok=True, name=task_name,
    )
    if not transitioned:
        return TaskCompletionResult("failed", reason="task_done_transition_failed")
    services.audit_task_ok(
        transitioned,
        task_id,
        task_name,
        state.project_dir,
        state.project_name,
        via=("reviewer_checkpoint" if should_review else "coordinator_checkpoint"),
    )
    services.audit_call(
        "loop_reviewer_checkpoint_completed",
        {
            "task_id": task_id,
            "reviewer_invoked": should_review,
            "decision": decision,
            "diff_sha256": current_sha,
        },
        state.project_dir,
        state.project_name,
    )
    phase_state.save()
    return TaskCompletionResult(
        "completed", tasks_ok_delta=1,
        diff_sha256=current_sha if isinstance(current_sha, str) else None,
    )


__all__ = [
    "CompletionStatus",
    "TaskCompletionResult",
    "TaskCompletionServices",
    "complete_task_checkpoint",
]
