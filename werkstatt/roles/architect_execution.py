"""Run or resume the Architect role from a validated Scout handoff."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ArchitectRoleServices:
    """Planner-owned adapters used by this isolated role worker."""

    input_fingerprint: Callable[..., str | None]
    validate_artifact: Callable[..., dict[str, Any] | None]
    make_artifact: Callable[..., dict[str, Any] | None]
    run_architect: Callable[..., bool]
    validate_contract: Callable[..., bool]
    publish_checkpoint: Callable[..., None]
    audit_call: Callable[..., Any]


@dataclass(frozen=True)
class ArchitectCheckpointResult:
    """Bounded result consumed by the task-graph compiler checkpoint."""

    output: str
    input_sha256: str | None
    saved_artifact: dict[str, Any] | None
    artifact_persisted: bool
    failure_reason: str | None = None


def run_architect_checkpoint(
    state: Any,
    *,
    goal: str,
    user_content: str,
    explorer_context: dict | None,
    scout_report: dict | None,
    scout_input_sha256: str | None,
    services: ArchitectRoleServices,
) -> ArchitectCheckpointResult:
    """Execute only Architect handoff validation, call/replay and persistence.

    Role routing remains with the coordinator. This worker does not select
    Scout, Planner-Split, Builder or authorize a plan; it only consumes the
    current Scout evidence and returns a validated Architect artifact.
    """
    project_dir = state.project_dir
    project_name = state.project_name
    state.architect_skills_block = ""

    if not services.validate_contract("scout", "architect", state, project_dir, project_name):
        services.publish_checkpoint(
            state, "architect", "failed", "scout_contract_rejected",
            scout_report,
        )
        return ArchitectCheckpointResult("", None, None, False, "scout_contract_rejected")

    input_sha256 = services.input_fingerprint(
        state, goal, user_content, explorer_context, scout_input_sha256,
    )
    role_artifacts = getattr(state, "planner_role_artifacts", {})
    saved = None
    if input_sha256 and isinstance(role_artifacts, dict):
        saved = services.validate_artifact(
            role_artifacts.get("architect"),
            role="architect",
            run_id=getattr(state, "run_id", "") or "",
            goal=goal,
            input_sha256=input_sha256,
        )

    if saved is not None:
        from werkstatt.architect import _pruefe_architect_api_referenzen

        cached_output = saved["output"]
        api_findings = _pruefe_architect_api_referenzen(
            cached_output, getattr(state, "api_index_cache", {}) or {},
        )
        if len(cached_output.strip()) < 50 or api_findings:
            services.audit_call("planner_role_artifact_rejected", {
                "role": "architect",
                "reason": (
                    "architect_output_too_short"
                    if len(cached_output.strip()) < 50
                    else "current_api_preflight_failed"
                ),
                "finding_count": len(api_findings),
            }, project_dir, project_name)
            saved = None

    if saved is not None:
        output = saved["output"]
        state.architect_prosa = output
        services.audit_call("planner_role_artifact_reused", {
            "role": "architect",
            "input_sha256": input_sha256,
            "output_sha256": saved["output_sha256"],
        }, project_dir, project_name)
        services.publish_checkpoint(
            state, "architect", "completed", "validated_checkpoint_artifact",
            {"input_sha256": input_sha256}, output,
        )
    else:
        services.publish_checkpoint(
            state, "architect", "running", "scout_handoff_ready",
            {"goal": goal, "user_context": user_content,
             "scout_report": scout_report},
        )
        if not services.run_architect(
            state, goal, user_content, state.api_key, explorer_context,
        ):
            services.publish_checkpoint(
                state, "architect", "failed", "architect_call_failed",
                scout_report,
            )
            return ArchitectCheckpointResult(
                "", input_sha256, None, False, "architect_call_failed",
            )
        output = state.architect_prosa
        services.publish_checkpoint(
            state, "architect", "completed", "architect_prose_received",
            {"goal": goal, "user_context": user_content,
             "scout_report": scout_report}, output,
        )

    if not services.validate_contract(
        "architect", "planner", state, project_dir, project_name,
    ):
        services.publish_checkpoint(
            state, "planner_split", "failed", "architect_contract_rejected",
            output,
        )
        return ArchitectCheckpointResult(
            output, input_sha256, saved, False, "architect_contract_rejected",
        )

    artifact_persisted = False
    if saved is None and input_sha256 and getattr(state, "run_id", None):
        artifact = services.make_artifact(
            "architect", output, run_id=state.run_id, goal=goal,
            input_sha256=input_sha256,
        )
        artifact_callback = getattr(
            state, "planner_role_artifact_callback", None,
        )
        if artifact is not None and callable(artifact_callback):
            artifact_callback(artifact)
            artifact_persisted = True
            role_artifacts = dict(role_artifacts or {})
            role_artifacts["architect"] = artifact
            state.planner_role_artifacts = role_artifacts
            services.audit_call("planner_role_artifact_persisted", {
                "role": "architect",
                "input_sha256": input_sha256,
                "output_sha256": artifact["output_sha256"],
            }, project_dir, project_name)

    action_role = getattr(state, "planner_action_role", None)
    if (
        action_role in {"architect", "planner_split", "planner_dispatch"}
        and saved is None and not artifact_persisted
    ):
        services.audit_call("planner_role_artifact_unbound", {
            "role": "architect",
            "reason": "current_inputs_or_persistence_unavailable",
        }, project_dir, project_name)
        return ArchitectCheckpointResult(
            output, input_sha256, saved, False,
            "current_inputs_or_persistence_unavailable",
        )

    return ArchitectCheckpointResult(
        output, input_sha256, saved, artifact_persisted,
    )
