"""Execute Scout capability from current Explorer evidence and role artifacts."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ScoutRoleServices:
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
    skip_path: str | None,
    route_reason: str,
    services: ScoutRoleServices,
) -> ScoutCheckpointResult:
    """Run or reuse Scout, or return the validated narrow-source route.

    This worker owns Scout routing, current-input fingerprinting, artifact
    reuse, the provider call, and its role checkpoint. Downstream planning
    decisions consume only the returned report and provenance.
    """
    project_dir = state.project_dir
    project_name = state.project_name
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


def run_scout_role_checkpoint(
    state: Any,
    *,
    goal: str,
    mark_plan_candidate: Callable[[], None] | None = None,
) -> bool:
    """Run only the Scout role selected by the persisted run coordinator.

    The Planner module still supplies shared prompt/fingerprint helpers, but
    Scout execution no longer enters its multi-role compatibility workflow.
    This boundary persists the Scout result and yields for a fresh coordinator
    decision, except when a fully validated atomic plan is produced; that plan
    remains an unapproved candidate for the existing gates.
    """
    from werkstatt import planner as shared
    from werkstatt.checkpoint_coordinator import apply_checkpoint_role_choice
    from werkstatt.planner_artifacts import (
        make_role_artifact,
        validate_role_artifact,
    )
    from werkstatt.roles.builder_direct import (
        build_direct_edit_plan as deterministic_literal_replace_plan,
    )
    from werkstatt.roles.planner_dispatch import scout_route_decision

    state.planner_step_yielded = False
    state.planner_yielded_after_role = None
    explorer_context = state.explorer_context
    key_files = [
        item["file"]
        for item in (
            explorer_context.get("key_files", [])
            if isinstance(explorer_context, dict) else []
        )
        if isinstance(item, dict) and isinstance(item.get("file"), str)
    ]
    skip_path, route_reason = scout_route_decision(
        goal, explorer_context, state.project_dir,
    )
    coordinator_role = getattr(state, "planner_coordinator_role", None)
    if coordinator_role in {"scout", "architect"}:
        source_evidence = tuple(
            item for item in getattr(
                state, "planner_coordinator_source_evidence", (),
            )
            if isinstance(item, dict)
        )
        route = apply_checkpoint_role_choice(
            state.project_dir,
            role=coordinator_role,
            deterministic_skip_path=skip_path,
            source_evidence=source_evidence,
            deterministic_reason=route_reason,
        )
        skip_path = route["skip_path"]
        route_reason = route["reason"]
        if coordinator_role == "architect" and skip_path:
            state.architect_required_source_files = route["source_files"]

    result = run_scout_checkpoint(
        state,
        goal=goal,
        api_key=state.api_key,
        key_files=key_files,
        skip_path=skip_path,
        route_reason=route_reason,
        services=ScoutRoleServices(
            direct_plan=deterministic_literal_replace_plan,
            build_index=shared._baue_api_index,
            input_fingerprint=shared._scout_input_fingerprint,
            validate_artifact=validate_role_artifact,
            run_scout=shared._run_scout,
            publish_checkpoint=shared._publish_role_checkpoint,
            audit_call=shared.audit,
        ),
    )
    if result.failure_reason is not None or not isinstance(result.report, dict):
        return False

    report = result.report
    if report.get("bereits_erfuellt") is True:
        reason = str(report.get("begruendung_erfuellt") or "")[:300]
        shared.audit(
            "auftrag_bereits_erfuellt",
            {
                "quelle": "scout",
                "begruendung": reason,
                "unbestaetigt": True,
                "naechste_rolle": "architect",
            },
            state.project_dir,
            state.project_name,
        )

    from werkstatt.architect_context import scout_report_has_architect_assignment

    if not scout_report_has_architect_assignment(report):
        shared.audit(
            "planner_scout_json_fehler",
            {"grund": "auftrag_prosa_fehlt"},
            state.project_dir,
            state.project_name,
        )
        return False

    api_excerpt = report.get("api_auszug") or {}
    state.scout_auftrag = dict(report)
    state.scout_api_auszug = api_excerpt if isinstance(api_excerpt, dict) else {}
    contradictions = shared._pruefe_api_widerspruch(
        report, result.code_index,
    )
    if contradictions:
        shared.audit(
            "planner_scout_api_widerspruch",
            {"anzahl": len(contradictions), "widersprueche": contradictions},
            state.project_dir,
            state.project_name,
        )
        state.scout_auftrag["api_widersprueche"] = contradictions

    if not skip_path and result.input_sha256 and getattr(state, "run_id", None):
        artifact = make_role_artifact(
            "scout",
            report,
            run_id=state.run_id,
            goal=goal,
            input_sha256=result.input_sha256,
        )
        callback = getattr(state, "planner_role_artifact_callback", None)
        if artifact is not None and callable(callback):
            callback(artifact)
            artifacts = getattr(state, "planner_role_artifacts", {})
            artifacts = dict(artifacts) if isinstance(artifacts, dict) else {}
            artifacts["scout"] = artifact
            state.planner_role_artifacts = artifacts
            shared.audit(
                "planner_role_artifact_persisted",
                {
                    "role": "scout",
                    "input_sha256": result.input_sha256,
                    "output_sha256": artifact["output_sha256"],
                },
                state.project_dir,
                state.project_name,
            )
        elif not result.reused_artifact:
            shared.audit(
                "planner_role_artifact_unbound",
                {"role": "scout", "reason": "artifact_callback_missing"},
                state.project_dir,
                state.project_name,
            )
            return False

    if report.get("atomarer_plan") is True:
        atomic_ok, atomic_reason = shared._atomarer_scout_plan_freigabefaehig(
            report, state.project_dir,
        )
        tasks = (
            shared._tasks_aus_betroffenen_stellen(
                report, goal, quelle=result.source,
            ) if atomic_ok else []
        )
        if tasks:
            state.akzeptanzkriterien = [
                "Alle eindeutig belegten Ersetzungen im atomaren Plan sind umgesetzt."
            ]
            for task in tasks:
                task["criterion_refs"] = ["AC1"]
            shared._validate_criteria_coverage(tasks, state.akzeptanzkriterien)
            state.tasks = tasks
            state.tests = []
            state.phasen = []
            state.architect_prosa = f"[atomarer Plan: {result.source}]"
            state.architect_required_source_files = list(dict.fromkeys(
                task["task_files"][0]
                for task in tasks
                if isinstance(task.get("task_files"), list)
                and task["task_files"]
            ))
            shared._publish_role_checkpoint(
                state, "architect", "skipped",
                "deterministic_atomic_plan_evidence_sufficient",
                report, tasks,
            )
            shared._publish_role_checkpoint(
                state, "planner_split", "skipped",
                "deterministic_atomic_plan_already_task_graph",
                tasks, tasks,
            )
            shared.audit(
                "planner_atomarer_plan",
                {
                    "tasks": len(tasks),
                    "dateien": [task["task_files"][0] for task in tasks],
                    "validierung": atomic_reason,
                    "quelle": result.source,
                    "architect": "uebersprungen",
                },
                state.project_dir,
                state.project_name,
            )
            if mark_plan_candidate is None:
                shared.audit(
                    "planner_atomarer_plan_verworfen",
                    {"grund": "plan_candidate_callback_missing"},
                    state.project_dir,
                    state.project_name,
                )
                return False
            mark_plan_candidate()
            return True
        shared.audit(
            "planner_atomarer_plan_verworfen",
            {"grund": atomic_reason},
            state.project_dir,
            state.project_name,
        )

    state.planner_step_yielded = True
    state.planner_yielded_after_role = "scout"
    return True
