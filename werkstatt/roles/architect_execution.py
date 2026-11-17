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


def run_architect_role_checkpoint(state: Any, *, goal: str) -> bool:
    """Run only Architect from the current coordinator-selected checkpoint.

    This entry point consumes a fresh, run-bound Scout artifact or verified
    Explorer source evidence. Missing/stale upstream evidence yields back to
    Scout so the coordinator can make the next choice; it never re-enters the
    multi-role Planner runner.
    """
    from pathlib import Path

    from werkstatt import planner
    from werkstatt.architect import build_architect_docs_context_v2
    from werkstatt.checkpoint_coordinator import apply_checkpoint_role_choice
    from werkstatt.planner_artifacts import (
        make_role_artifact,
        validate_role_artifact,
    )
    from werkstatt.roles.planner_dispatch import scout_route_decision

    project_dir = Path(state.project_dir)
    project_name = state.project_name
    state.planner_step_yielded = False
    state.planner_yielded_after_role = None
    if not isinstance(goal, str) or not goal.strip() or not state.api_key:
        planner.audit(
            "planner_architect_handoff_missing",
            {"reason": "goal_or_api_key_missing"}, project_dir, project_name,
        )
        return False

    explorer_context = state.explorer_context
    skip_path, route_reason = scout_route_decision(
        goal, explorer_context, project_dir,
    )
    coordinator_role = getattr(state, "planner_coordinator_role", None)
    source_evidence = tuple(
        item for item in getattr(
            state, "planner_coordinator_source_evidence", (),
        ) if isinstance(item, dict)
    )
    if coordinator_role == "architect":
        route = apply_checkpoint_role_choice(
            project_dir,
            role="architect",
            deterministic_skip_path=skip_path,
            source_evidence=source_evidence,
            deterministic_reason=route_reason,
        )
        skip_path = route["skip_path"]
        route_reason = route["reason"]
        if skip_path:
            state.architect_required_source_files = route["source_files"]
        else:
            planner.audit(
                "planner_architect_handoff_missing",
                {
                    "reason": "coordinator_source_evidence_stale",
                    "next_role": "scout",
                }, project_dir, project_name,
            )
            state.planner_step_yielded = True
            state.planner_yielded_after_role = "scout"
            return True

    key_files = [
        item["file"]
        for item in (
            explorer_context.get("key_files", [])
            if isinstance(explorer_context, dict) else []
        )
        if isinstance(item, dict) and isinstance(item.get("file"), str)
    ]
    code_index = planner._baue_api_index(project_dir)
    state.api_index_cache = code_index
    scout_input_sha256: str | None = None
    if skip_path:
        source_files = list(dict.fromkeys(
            [*getattr(state, "architect_required_source_files", []), skip_path]
        ))
        state.architect_required_source_files = source_files
        scout_report: dict[str, Any] = {
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
            "quellenrolle": "deterministischer_explorer_handoff",
        }
        planner.audit(
            "planner_scout_skipped",
            {"grund": route_reason, "datei": skip_path,
             "architect": "wird_aufgerufen"},
            project_dir, project_name,
        )
    else:
        scout_input_sha256 = planner._scout_input_fingerprint(
            state, goal, code_index, key_files,
        )
        artifacts = getattr(state, "planner_role_artifacts", {})
        scout_artifact = None
        if scout_input_sha256 and isinstance(artifacts, dict):
            scout_artifact = validate_role_artifact(
                artifacts.get("scout"),
                role="scout",
                run_id=getattr(state, "run_id", "") or "",
                goal=goal,
                input_sha256=scout_input_sha256,
            )
        if scout_artifact is None or not isinstance(
            scout_artifact.get("output"), dict,
        ):
            planner.audit(
                "planner_architect_handoff_missing",
                {
                    "reason": (
                        "scout_input_fingerprint_unavailable"
                        if scout_input_sha256 is None
                        else "current_scout_artifact_missing_or_stale"
                    ),
                    "next_role": "scout",
                }, project_dir, project_name,
            )
            state.planner_step_yielded = True
            state.planner_yielded_after_role = "scout"
            return True
        scout_report = scout_artifact["output"]
        if not planner._scout_report_hat_architect_auftrag(scout_report):
            planner.audit(
                "planner_scout_json_fehler",
                {"grund": "auftrag_prosa_fehlt"}, project_dir, project_name,
            )
            return False
        state.architect_required_source_files = list(dict.fromkeys(
            item.get("pfad")
            for item in scout_report.get("relevante_dateien", [])
            if isinstance(item, dict)
            and isinstance(item.get("pfad"), str)
            and item.get("pfad")
        ))
        state.scout_auftrag = dict(scout_report)
        api_excerpt = scout_report.get("api_auszug") or {}
        state.scout_api_auszug = (
            api_excerpt if isinstance(api_excerpt, dict) else {}
        )
        contradictions = planner._pruefe_api_widerspruch(
            scout_report, code_index,
        )
        if contradictions:
            state.scout_auftrag["api_widersprueche"] = contradictions
            planner.audit(
                "planner_scout_api_widerspruch",
                {"anzahl": len(contradictions),
                 "widersprueche": contradictions},
                project_dir, project_name,
            )

    state.scout_auftrag = dict(scout_report)
    api_excerpt = scout_report.get("api_auszug") or {}
    state.scout_api_auszug = (
        api_excerpt if isinstance(api_excerpt, dict) else {}
    )

    docs_text, docs_manifest = build_architect_docs_context_v2(
        state.docs or {},
    )
    task_prefix = f"## AUFGABE\n{goal}\n\n## KONTEXT (nur relevanter Auszug)\n"
    for section in docs_manifest.get("sections", []):
        if section.get("status") == "included_optional":
            section["prompt_start"] += len(task_prefix)
            section["prompt_end"] += len(task_prefix)
    state.architect_project_docs_manifest = docs_manifest
    user_content = task_prefix + docs_text

    from werkstatt import progress
    from werkstatt.phase_state import PhaseState

    completed = planner._erledigte_punkte(project_dir)
    recent_progress = progress.read_recent(project_dir, n=10)
    phase_state = PhaseState(
        project_name, base_dir=project_dir / ".werkstatt",
    )
    task_status: list[dict[str, Any]] = []
    previous_failures: list[dict[str, Any]] = []
    if phase_state.exists() and phase_state.load():
        task_status = [
            {
                "id": task.get("id"), "name": task.get("name", ""),
                "status": task.get("status"), "failure": task.get("failure"),
            }
            for task in phase_state.data.get("tasks", [])
            if isinstance(task, dict)
        ]
        previous_failures = [
            task for task in phase_state.data.get("tasks", [])
            if isinstance(task, dict) and task.get("status") == "failed"
        ]
    preflight = list(getattr(state, "preflight_fehler", []) or [])
    follow_up = list(getattr(state, "follow_up_fehler", []) or [])
    migration_status = planner._migrations_stand(project_dir)
    planner_info = getattr(state, "last_planner_info", None)
    sections: list[tuple[str, str]] = []
    if preflight:
        sections.append((
            "PREFLIGHT-FEHLER (aktuelle Pflichtbefunde)",
            planner.json.dumps(preflight, ensure_ascii=False),
        ))
    if completed:
        sections.append(("BEREITS ERLEDIGT (nicht erneut planen)", completed))
    if previous_failures:
        sections.append((
            "VORHERIGE FEHLSCHLAEGE",
            planner.json.dumps(previous_failures, ensure_ascii=False),
        ))
    if recent_progress:
        sections.append((
            "PROJEKT-FORTSCHRITT (letzte 10 Eintraege; nachrangige Historie)",
            recent_progress,
        ))
    if task_status:
        sections.append((
            "PHASE-STATE", planner.json.dumps(task_status, ensure_ascii=False),
        ))
    if follow_up:
        sections.append((
            "FOLLOW-UP AUS VORHERIGER PHASE",
            planner.json.dumps(follow_up, ensure_ascii=False),
        ))
    if migration_status:
        sections.append(("MIGRATIONSSTAND", migration_status))
    if planner_info:
        sections.append((
            "ABGELEHNTER PLAN",
            planner.json.dumps(planner_info, ensure_ascii=False),
        ))
    (
        state.architect_execution_context,
        execution_manifest,
    ) = planner._budget_architect_execution_context(sections)
    state.architect_execution_context_manifest = execution_manifest
    planner.audit(
        "planner_architect_context_budget", execution_manifest,
        project_dir, project_name,
    )

    state.architect_reasoning_enabled, reasoning_reason = (
        planner.architect_reasoning_route(goal, skip_path)
    )
    planner.audit(
        "planner_architect_reasoning_route",
        {
            "thinking": state.architect_reasoning_enabled,
            "reason": reasoning_reason,
            "task_chars": len(goal),
            "scout_skip_path": skip_path,
            "scout_route_reason": route_reason,
        }, project_dir, project_name,
    )
    if not planner._validate_contract_or_audit(
        "scout", "architect", state, project_dir, project_name,
    ):
        planner._publish_role_checkpoint(
            state, "architect", "failed", "scout_contract_rejected",
            scout_report,
        )
        return False

    result = run_architect_checkpoint(
        state,
        goal=goal,
        user_content=user_content,
        explorer_context=(
            explorer_context if isinstance(explorer_context, dict) else None
        ),
        scout_report=scout_report,
        scout_input_sha256=scout_input_sha256,
        services=ArchitectRoleServices(
            input_fingerprint=planner._architect_input_fingerprint,
            validate_artifact=validate_role_artifact,
            make_artifact=make_role_artifact,
            run_architect=planner.run_architect,
            validate_contract=planner._validate_contract_or_audit,
            publish_checkpoint=planner._publish_role_checkpoint,
            audit_call=planner.audit,
        ),
    )
    if result.failure_reason is not None:
        return False

    planner._persist_planner_split_handoff(
        state,
        goal=goal,
        scout_report=scout_report,
        architect_scout_report=getattr(state, "scout_auftrag", scout_report),
        scout_input_sha256=scout_input_sha256,
        architect_prose=result.output,
        architect_input_sha256=result.input_sha256,
    )
    state.planner_step_yielded = True
    state.planner_yielded_after_role = "architect"
    return True
