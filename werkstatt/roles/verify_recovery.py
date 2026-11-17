"""One bounded Builder repair selected from current Verify evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _error_context(errors: list[str]) -> str:
    evidence: dict[str, Any] = {"source": "verify", "errors": []}
    for error in errors[:8]:
        candidate = {"source": "verify", "errors": [*evidence["errors"], error[:240]]}
        if len(json.dumps(candidate, ensure_ascii=False, sort_keys=True)) > 1200:
            break
        evidence = candidate
    return json.dumps(evidence, ensure_ascii=False, sort_keys=True)


def run_verify_recovery(
    state: Any,
    phase_state: Any,
    task_id: str,
) -> dict[str, Any]:
    """Repair one current task Verify failure, then hand back for Verify again.

    It never falls back to an unrestricted reflection loop. Missing stage
    evidence, stale files, or exhausted budget fail closed for human review.
    """
    current_check = getattr(
        phase_state, "task_verify_failure_checkpoint_is_current", None,
    )
    task = phase_state.get_task(task_id)
    checkpoint = task.get("verify_failure_checkpoint") if isinstance(task, dict) else None
    if not callable(current_check) or current_check(task_id) is not True:
        return {"status": "human_review", "reason": "stale_checkpoint", "stage_ids": []}
    if not isinstance(checkpoint, dict):
        return {"status": "human_review", "reason": "checkpoint_missing", "stage_ids": []}

    errors = checkpoint.get("verify_errors")
    if not isinstance(errors, list) or not all(isinstance(item, str) for item in errors):
        return {"status": "human_review", "reason": "invalid_error_evidence", "stage_ids": []}
    state.last_verify_errors = errors

    from werkstatt.verify import _stage_ids

    configured = set(_stage_ids(Path(state.project_dir)))
    failed_stages = sorted({
        stage_id for stage_id in configured
        if any(
            error.startswith((f"{stage_id}:", f"{stage_id}-Fehler:"))
            for error in errors
        )
    })
    budget = state.budget if isinstance(state.budget, dict) else {}
    has_budget = any(
        isinstance(budget.get(key), int)
        and not isinstance(budget.get(key), bool)
        and budget[key] > 0
        for key in ("max_llm_calls", "max_minutes")
    )
    if not failed_stages:
        return {"status": "human_review", "reason": "stage_unmapped", "stage_ids": []}
    if not has_budget:
        return {"status": "human_review", "reason": "run_budget_exhausted", "stage_ids": failed_stages[:12]}

    from werkstatt.reflection import _reflection_loop_core

    repaired = bool(_reflection_loop_core(
        state,
        max_runden=1,
        error_context=_error_context(errors),
        phase="post_build",
        verify_stage_ids=set(failed_stages),
    ))
    recorder = getattr(phase_state, "record_task_build_checkpoint", None)
    if not repaired or not callable(recorder) or recorder(task_id) is not True:
        return {
            "status": "human_review",
            "reason": "repair_failed_or_unbound",
            "stage_ids": failed_stages[:12],
        }

    task = phase_state.get_task(task_id)
    if isinstance(task, dict):
        task.pop("verify_failure_checkpoint", None)
        phase_state.save()
    return {
        "status": "repair_handoff",
        "reason": "one_targeted_repair_completed",
        "stage_ids": failed_stages[:12],
        "checkpoint_sha256": str(checkpoint.get("evidence_sha256", ""))[:64],
    }


def run_phase_end_verify_recovery(
    state: Any, checkpoint: dict[str, Any],
) -> dict[str, Any]:
    """Run one targeted repair from persisted final-verify stage evidence."""
    failed_stages = checkpoint.get("failed_stages")
    if (
        not isinstance(failed_stages, list)
        or not failed_stages
        or any(not isinstance(item, dict) for item in failed_stages)
    ):
        return {"status": "failed", "reason": "invalid_failure_evidence"}
    stage_ids = list(dict.fromkeys(
        str(item.get("stage_id") or "?")[:120]
        for item in failed_stages if isinstance(item, dict)
    ))
    errors = [
        f"{item.get('stage_id')}: {str(item.get('error_excerpt') or '')[:500]}"
        for item in failed_stages if isinstance(item, dict)
    ][:8]
    budget = state.budget if isinstance(state.budget, dict) else {}
    has_budget = any(
        isinstance(budget.get(key), int)
        and not isinstance(budget.get(key), bool)
        and budget[key] > 0
        for key in ("max_llm_calls", "max_minutes")
    )
    if not has_budget:
        return {
            "status": "failed",
            "reason": "run_budget_exhausted",
            "stage_ids": stage_ids[:12],
        }
    state.last_verify_errors = errors
    from werkstatt.failure_record import _worktree_fingerprint
    from werkstatt.reflection import _reflection_loop_core

    project_dir = Path(state.project_dir)
    before = _worktree_fingerprint(project_dir)
    repaired = bool(_reflection_loop_core(
        state,
        max_runden=1,
        error_context=_error_context(errors),
        phase="phase_end",
        verify_stage_ids=set(stage_ids),
    ))
    after = _worktree_fingerprint(project_dir)
    changed = before is not None and after is not None and before != after
    return {
        "status": "repair_handoff" if repaired or changed else "failed",
        "reason": (
            "one_targeted_repair_completed" if repaired else
            "changed_worktree_requires_coordinator_verify" if changed else
            "repair_no_progress"
        ),
        "stage_ids": stage_ids[:12],
    }
