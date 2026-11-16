"""Checkpoint-scoped task-graph recovery for planning gates."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable

from werkstatt.state import RunState
from werkstatt.task_graph import TaskGraphError


def replan_task_graph_from_architect(
    state: RunState,
    gate_feedback: dict,
    *,
    compile_graph: Callable[..., list[dict]] | None = None,
    normalize_task_files: Callable[..., list[dict]] | None = None,
    audit_call: Callable[..., object] | None = None,
) -> bool:
    """Retry only task-graph compilation from pinned planning evidence.

    Explorer, Scout, Architect prose, source evidence, and approved criteria
    remain bound to the current checkpoint. The task graph is replaced only
    after compilation and normalization both succeed.
    """
    if compile_graph is None or normalize_task_files is None or audit_call is None:
        from werkstatt import planner

        compile_graph = compile_graph or planner._zerlege_in_sub_tasks
        normalize_task_files = (
            normalize_task_files or planner._normalisiere_task_files
        )
        audit_call = audit_call or planner.audit
    assert compile_graph is not None
    assert normalize_task_files is not None
    assert audit_call is not None

    allowed_rules = {"TASK_GRAPH", "ACCEPTANCE_COVERAGE"}
    rule = gate_feedback.get("regel") if isinstance(gate_feedback, dict) else None
    explorer_ctx = state.explorer_context
    criteria = list(state.akzeptanzkriterien or [])
    if (
        rule not in allowed_rules
        or not state.api_key
        or not state.architect_prosa.strip()
        or not isinstance(explorer_ctx, dict)
        or not criteria
        or any(not isinstance(item, str) or not item.strip() for item in criteria)
    ):
        audit_call("loop_plan_reflection_abgebrochen", {
            "route": "planner_split_only",
            "reason": "required_checkpoint_evidence_missing_or_ineligible",
            "rule": rule,
            "architect_prose_present": bool(state.architect_prosa.strip()),
            "explorer_context_present": isinstance(explorer_ctx, dict),
            "criteria_count": len(criteria),
        }, state.project_dir, state.project_name)
        return False

    key_files = [
        item["file"]
        for item in (explorer_ctx.get("key_files") or [])
        if isinstance(item, dict)
        and isinstance(item.get("file"), str)
        and item["file"]
    ]
    previous_criteria = list(state.akzeptanzkriterien)
    try:
        tasks = compile_graph(
            state.architect_prosa,
            key_files,
            state.api_key,
            state.project_dir,
            state.project_name,
            aufgabe=state.aufgabe,
            state=state,
            gate_feedback=gate_feedback,
            preserve_criteria=criteria,
        )
    except TaskGraphError as exc:
        state.akzeptanzkriterien = previous_criteria
        audit_call("loop_plan_reflection_abgebrochen", {
            "route": "planner_split_only",
            "reason": "split_contract_rejected",
            "rule": rule,
            "error": str(exc)[:500],
        }, state.project_dir, state.project_name)
        return False

    if not tasks or state.akzeptanzkriterien != previous_criteria:
        state.akzeptanzkriterien = previous_criteria
        audit_call("loop_plan_reflection_abgebrochen", {
            "route": "planner_split_only",
            "reason": "split_failed_or_criteria_changed",
            "rule": rule,
        }, state.project_dir, state.project_name)
        return False

    normalized = normalize_task_files(
        tasks, explorer_ctx, state.project_dir, state.project_name,
    )
    if not normalized:
        audit_call("loop_plan_reflection_abgebrochen", {
            "route": "planner_split_only",
            "reason": "normalized_task_graph_empty",
            "rule": rule,
        }, state.project_dir, state.project_name)
        return False

    state.tasks = normalized
    state.phasen = []
    state.tests = []
    source_manifest = getattr(state, "architect_scout_source_manifest", {})
    source_manifest_sha256 = hashlib.sha256(
        json.dumps(
            source_manifest if isinstance(source_manifest, dict) else {},
            ensure_ascii=False,
            sort_keys=True,
        ).encode("utf-8"),
    ).hexdigest()
    audit_call("loop_plan_reflection", {
        "route": "planner_split_only",
        "rule": rule,
        "preserved_criteria": criteria,
        "task_ids": [task.get("id") for task in normalized],
        "source_manifest_sha256": source_manifest_sha256,
    }, state.project_dir, state.project_name)
    return True
