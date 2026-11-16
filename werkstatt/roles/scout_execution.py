"""Execute Scout capability from current Explorer evidence and role artifacts."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ScoutRoleServices:
    route: Callable[..., tuple[str | None, str]]
    direct_plan: Callable[..., tuple[dict | None, str]]
    build_index: Callable[..., dict]
    input_fingerprint: Callable[..., str | None]
    validate_artifact: Callable[..., dict | None]
    run_scout: Callable[..., dict | None]
    publish_checkpoint: Callable[..., None]
    audit_call: Callable[..., Any]


@dataclass(frozen=True)
class ScoutCheckpointResult:
    report: dict | None
    skip_path: str | None
    route_reason: str
    source: str
    code_index: dict
    input_sha256: str | None
    reused_artifact: bool
    artifact_persisted: bool
    failure_reason: str | None = None


def run_scout_checkpoint(
    state: Any,
    *,
    goal: str,
    api_key: str,
    key_files: list[str],
    services: ScoutRoleServices,
) -> ScoutCheckpointResult:
    """Run or reuse Scout, or return the validated narrow-source route.

    This worker owns Scout routing, current-input fingerprinting, artifact
    reuse, the provider call, and its role checkpoint. Downstream planning
    decisions consume only the returned report and provenance.
    """
    project_dir = state.project_dir
    project_name = state.project_name
    skip_path, route_reason = services.route(
        goal, getattr(state, "explorer_context", None), project_dir,
    )
    source = "Scout"
    code_index: dict = {}
    input_sha256: str | None = None
    reused_artifact = False
    artifact_persisted = False
    report: dict | None

    if skip_path:
        report, direct_reason = services.direct_plan(
            goal, skip_path, project_dir,
        )
        if (
            getattr(state, "planner_action_role", None) == "builder_direct"
            and report is None
        ):
            services.audit_call("planner_role_dispatch_decision", {
                "next_role": None,
                "reason": "direct_builder_source_evidence_changed",
                "direct_builder_reason": direct_reason,
                "basis": "revalidated_current_target",
            }, project_dir, project_name)
            return ScoutCheckpointResult(
                None, skip_path, direct_reason, source, code_index, None,
                False, False, "direct_builder_source_evidence_changed",
            )
        if report is not None:
            source = "deterministische_literal_ersetzung"
            route_reason = direct_reason
        else:
            state.architect_required_source_files = [skip_path]
            report = {
                "ziel": goal,
                "relevante_dateien": [{
                    "pfad": skip_path,
                    "warum": "explorer_hat_explizites_einzeldateiziel_bestaetigt",
                }],
                "api_auszug": {},
                "vorgeschlagene_aenderungen": [],
                "risiken": [],
                "auftrag_prosa": goal,
                "bereits_erfuellt": False,
                "atomarer_plan": False,
            }
        services.audit_call("planner_scout_skipped", {
            "grund": route_reason,
            "datei": skip_path,
            "architect": (
                "wird_nach_evidenzpruefung_uebersprungen"
                if source != "Scout" else "wird_aufgerufen"
            ),
        }, project_dir, project_name)
        services.publish_checkpoint(
            state, "scout", "skipped", route_reason,
            {"goal": goal, "explorer": state.explorer_context}, report,
        )
    else:
        services.audit_call("planner_scout_required", {
            "grund": route_reason,
        }, project_dir, project_name)
        code_index = services.build_index(project_dir)
        input_sha256 = services.input_fingerprint(
            state, goal, code_index, key_files,
        )
        role_artifacts = getattr(state, "planner_role_artifacts", {})
        saved = None
        if input_sha256 and isinstance(role_artifacts, dict):
            saved = services.validate_artifact(
                role_artifacts.get("scout"),
                role="scout",
                run_id=getattr(state, "run_id", "") or "",
                goal=goal,
                input_sha256=input_sha256,
            )
        if saved is not None:
            reused_artifact = True
            report = saved["output"]
            services.audit_call("planner_role_artifact_reused", {
                "role": "scout",
                "input_sha256": input_sha256,
                "output_sha256": saved["output_sha256"],
            }, project_dir, project_name)
            services.publish_checkpoint(
                state, "scout", "completed", "validated_checkpoint_artifact",
                {"input_sha256": input_sha256}, report,
            )
        else:
            services.publish_checkpoint(
                state, "scout", "running", route_reason,
                {"goal": goal, "explorer": state.explorer_context,
                 "input_sha256": input_sha256},
            )
            report = services.run_scout(
                state, goal, code_index, key_files, api_key,
            )

    if not isinstance(report, dict):
        services.publish_checkpoint(
            state, "scout", "failed", "structured_report_missing",
            {"goal": goal, "explorer": state.explorer_context},
        )
        services.audit_call(
            "planner_scout_json_fehler",
            {"grund": "kein_structured_scout_report"},
            project_dir,
            project_name,
        )
        return ScoutCheckpointResult(
            None, skip_path, route_reason, source, code_index,
            input_sha256, reused_artifact, artifact_persisted,
            "structured_report_missing",
        )

    if not skip_path:
        services.publish_checkpoint(
            state,
            "scout",
            "completed",
            (
                "validated_checkpoint_artifact"
                if reused_artifact else "structured_report_received"
            ),
            {"goal": goal, "explorer": state.explorer_context}, report,
        )

    return ScoutCheckpointResult(
        report=report,
        skip_path=skip_path,
        route_reason=route_reason,
        source=source,
        code_index=code_index,
        input_sha256=input_sha256,
        reused_artifact=reused_artifact,
        artifact_persisted=artifact_persisted,
    )
