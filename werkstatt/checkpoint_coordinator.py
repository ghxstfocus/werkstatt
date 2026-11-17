"""LLM advice for ambiguous, evidence-bounded checkpoint choices."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from werkstatt.audit import audit
from werkstatt.state import RunState

_SYSTEM = (
    "Du bist der Projektkoordinator am Werkstatt-Checkpoint. Waehle genau "
    "eine Rolle aus allowed_roles anhand von Ziel, aktueller Beleglage und "
    "Informationsbedarf. Nutze Scout nur, wenn zusaetzliche Untersuchung "
    "den naechsten sicheren Schritt verbessert; wenn aktuelle, hashgebundene "
    "Quellbelege fuer den Architect reichen, darfst du Architect waehlen. "
    "Aendere weder Ziel noch Scope. Erfinde keine Belege. Antworte nur als "
    "JSON mit role und reason_code; gib keine Gedankengaenge aus."
)
_REASON_CODES = frozenset({
    "source_evidence_sufficient",
    "more_repository_evidence_needed",
})
_MAX_CONTEXT_CHARS = 12_000
_EXPLICIT_SOURCE_PATH = re.compile(
    r"(?<![\w.-])(?:[\w.-]+/)*[\w.-]+\.(?:py|md|yaml|yml|toml|json|"
    r"css|html|js)",
    re.IGNORECASE,
)


def _source_evidence_is_current(
    project_dir: Path, records: tuple[dict[str, str | bool], ...],
) -> bool:
    """Rebind the model's source manifest to current bytes before sending."""
    if not records or len(records) > 4:
        return False
    try:
        root = project_dir.resolve(strict=True)
        for record in records:
            path = record.get("path")
            digest = record.get("sha256")
            if (
                record.get("complete") is not True
                or not isinstance(path, str)
                or not isinstance(digest, str)
                or not re.fullmatch(r"[0-9a-f]{64}", digest)
            ):
                return False
            relative = Path(path)
            if relative.is_absolute() or ".." in relative.parts:
                return False
            resolved = (root / relative).resolve(strict=True)
            resolved.relative_to(root)
            if not resolved.is_file():
                return False
            if hashlib.sha256(resolved.read_bytes()).hexdigest() != digest:
                return False
    except (OSError, RuntimeError, ValueError, TypeError):
        return False
    return True


def apply_checkpoint_role_choice(
    project_dir: Path,
    *,
    role: str | None,
    deterministic_skip_path: str | None,
    source_evidence: tuple[dict[str, Any], ...],
    deterministic_reason: str,
) -> dict[str, Any]:
    """Apply the selected Scout/Architect branch after rechecking its proof."""
    if role == "scout":
        return {
            "skip_path": None,
            "reason": "project_coordinator_selected_scout",
            "source_files": [],
        }
    if role != "architect":
        return {
            "skip_path": deterministic_skip_path,
            "reason": deterministic_reason,
            "source_files": [],
        }
    source_paths = tuple(
        record["path"] for record in source_evidence
        if isinstance(record.get("path"), str)
    )
    if (
        deterministic_skip_path
        and deterministic_skip_path in source_paths
        and _source_evidence_is_current(project_dir, source_evidence)
    ):
        return {
            "skip_path": deterministic_skip_path,
            "reason": "project_coordinator_current_source_evidence",
            "source_files": sorted(set(source_paths)),
        }
    return {
        "skip_path": None,
        "reason": "coordinator_source_evidence_stale",
        "source_files": [],
    }


def current_explicit_source_evidence(
    state: RunState, *, max_files: int = 4,
) -> tuple[dict[str, str | bool], ...]:
    """Return only complete Explorer sources explicitly named by the goal."""
    paths = tuple(dict.fromkeys(_EXPLICIT_SOURCE_PATH.findall(state.aufgabe)))
    if not paths or len(paths) > max_files:
        return ()
    context = state.explorer_context
    key_files = context.get("key_files") if isinstance(context, dict) else None
    if not isinstance(key_files, list):
        return ()
    records: list[dict[str, str | bool]] = []
    for path in paths:
        matches = [
            item for item in key_files
            if isinstance(item, dict) and item.get("file") == path
        ]
        if len(matches) != 1:
            return ()
        item = matches[0]
        digest = item.get("source_sha256")
        if (
            item.get("source_complete") is not True
            or not isinstance(digest, str)
            or not re.fullmatch(r"[0-9a-f]{64}", digest)
        ):
            return ()
        records.append({"path": path, "sha256": digest, "complete": True})
    result = tuple(records)
    return result if _source_evidence_is_current(state.project_dir, result) else ()


def recommend_checkpoint_role(
    state: RunState,
    *,
    allowed_roles: tuple[str, ...],
    deterministic_role: str,
    evidence: tuple[str, ...],
    source_evidence: tuple[dict[str, str | bool], ...] = (),
) -> dict[str, Any]:
    """Ask the shared Chat model only when two validated choices exist.

    A deterministic recommendation remains the fallback. The model can select
    only a role already validated by the caller from current checkpoint facts.
    """
    result: dict[str, Any] = {
        "role": deterministic_role,
        "source": "deterministic_fallback",
        "reason_code": "model_not_used",
        "allowed_roles": list(allowed_roles),
        "source_evidence": list(source_evidence),
    }
    if (
        len(allowed_roles) < 2
        or deterministic_role not in allowed_roles
        or not isinstance(state.api_key, str)
        or not state.api_key.strip()
    ):
        return result
    if not _source_evidence_is_current(state.project_dir, source_evidence):
        result["reason_code"] = "coordinator_source_evidence_missing_or_stale"
        return result

    user_payload = {
        "run_id": str(state.run_id or "")[:160],
        "goal": state.aufgabe,
        "allowed_roles": list(allowed_roles),
        "verified_evidence_types": list(evidence),
        "current_source_evidence": list(source_evidence),
        "deterministic_default": deterministic_role,
    }
    user_content = json.dumps(
        user_payload, ensure_ascii=False, sort_keys=True,
    )
    measured_chars = len(_SYSTEM) + len(user_content)
    audit(
        "project_coordinator_context_budget",
        {
            "max_chars": _MAX_CONTEXT_CHARS,
            "system_chars": len(_SYSTEM),
            "user_chars": len(user_content),
            "actual_chars": measured_chars,
            "required_context_complete": measured_chars <= _MAX_CONTEXT_CHARS,
            "allowed_role_count": len(allowed_roles),
            "evidence_type_count": len(evidence),
            "source_evidence_count": len(source_evidence),
            "provider_request_sent": False,
        },
        state.project_dir,
        state.project_name,
        run_id=state.run_id,
    )
    if measured_chars > _MAX_CONTEXT_CHARS:
        result["reason_code"] = "coordinator_context_budget_exceeded"
        return result

    from werkstatt.agent import ask_llm

    manifest = {
        "budget_event": "project_coordinator_context_budget",
        "required_context_complete": True,
        "user_sha256": hashlib.sha256(
            user_content.encode("utf-8"),
        ).hexdigest(),
        "system_sha256": hashlib.sha256(_SYSTEM.encode("utf-8")).hexdigest(),
        "source": "persisted_checkpoint_and_validated_role_evidence",
    }
    try:
        reply = ask_llm(
            state.api_key,
            _SYSTEM,
            user_content,
            model="deepseek-flash",
            temperature=0.0,
            timeout=30,
            state=state,
            aufgabe="project-coordinator",
            rolle="project-coordinator",
            heartbeat=False,
            max_tokens=120,
            redact=True,
            progress_context={
                "run_id": state.run_id,
                "task_name": "Checkpoint: Scout oder Architect waehlen",
            },
            context_manifest=manifest,
            reasoning_override=True,
        )
    except Exception as exc:  # noqa: BLE001 - preserve bounded fallback
        result["reason_code"] = f"coordinator_model_error:{type(exc).__name__}"
        return result
    if not reply.ok:
        result["reason_code"] = "coordinator_model_unavailable"
        return result
    try:
        parsed = json.loads(reply.content)
    except (TypeError, json.JSONDecodeError):
        result["reason_code"] = "coordinator_invalid_response"
        return result
    if not isinstance(parsed, dict):
        result["reason_code"] = "coordinator_invalid_response"
        return result
    role = parsed.get("role")
    reason_code = parsed.get("reason_code")
    role_reason_is_valid = (
        (role == "scout" and reason_code == "more_repository_evidence_needed")
        or (role == "architect" and reason_code == "source_evidence_sufficient")
    )
    if (
        role not in allowed_roles
        or reason_code not in _REASON_CODES
        or not role_reason_is_valid
    ):
        result["reason_code"] = "coordinator_action_rejected"
        return result
    result.update({
        "role": role,
        "source": "project_chat_model",
        "reason_code": reason_code,
        "request_sha256": reply.request_sha256,
    })
    return result


def choose_planner_checkpoint_action(
    state: RunState,
    *,
    phase_data: dict[str, Any],
    planner_role_stage: str | None,
    plan_checkpoint_complete: bool,
    plan_goal_matches: bool,
    plan_run_matches: bool,
    plan_project_matches: bool,
    plan_fingerprint_matches: bool,
    explicit_source_context_ready: bool,
    preserve_failed_tasks_on_setup: bool,
) -> dict[str, Any]:
    """Select the next bounded planning role from current evidence.

    This is policy only: the caller owns loading and persisting checkpoints,
    while the selected action is dispatched by the run executor.
    """
    from werkstatt.roles.planner_dispatch import (
        choose_next_planner_role,
        direct_builder_route_decision,
        scout_route_decision,
    )

    task_records = phase_data.get("tasks")
    task_count = len(task_records) if isinstance(task_records, list) else 0
    scout_skip_target, scout_route_reason = scout_route_decision(
        state.aufgabe, state.explorer_context, state.project_dir,
    )
    direct_builder_ready, direct_builder_reason = direct_builder_route_decision(
        state.aufgabe, scout_skip_target, state.project_dir,
        explorer_context=state.explorer_context,
    )
    available: set[str] = set()
    if isinstance(state.aufgabe, str) and state.aufgabe.strip():
        available.add("user_goal")
    if state.preflight_checkpoint_ready:
        available.add("preflight_findings")
    dispatch = (
        state.explorer_context.get("dispatch")
        if isinstance(state.explorer_context, dict) else None
    )
    if isinstance(dispatch, dict) and dispatch.get("evidence_kind") == "explicit_source_read":
        available.add("explicit_source_evidence")
    elif isinstance(state.explorer_context, dict) and state.explorer_context:
        available.update({"project_inventory", "explorer_evidence"})
    if scout_skip_target:
        available.add("explorer_source_evidence")
    # Stage markers are progress telemetry, not evidence. Only persisted,
    # run/goal/hash-validated role artifacts can unlock a downstream role.
    role_artifacts = getattr(state, "planner_role_artifacts", {})
    if not isinstance(role_artifacts, dict):
        role_artifacts = {}
    scout_artifact = role_artifacts.get("scout")
    scout_report = (
        scout_artifact.get("output")
        if isinstance(scout_artifact, dict) else None
    )
    if isinstance(scout_report, dict):
        available.update({"scout_report", "current_source_evidence"})
        if scout_report.get("bereits_erfuellt") is True:
            available.add("goal_already_fulfilled")
    architect_artifact = role_artifacts.get("architect")
    architect_output = (
        architect_artifact.get("output")
        if isinstance(architect_artifact, dict) else None
    )
    if isinstance(architect_output, str) and len(architect_output.strip()) >= 50:
        available.update({
            "architect_plan", "architect_prose", "acceptance_criteria",
            "current_source_manifest",
        })
    if direct_builder_ready:
        available.update({"explicit_user_edit", "unique_current_source"})

    role_decision = choose_next_planner_role(
        scout_skip_path=scout_skip_target,
        available_evidence=available,
        direct_builder_ready=direct_builder_ready,
    )
    model_choice: dict[str, Any] | None = None
    selected_role = role_decision.role
    if (
        not role_decision.missing_inputs
        and not role_artifacts.get("scout")
        and role_decision.role == "architect"
        and scout_skip_target
    ):
        from werkstatt.roles.planner_dispatch import (
            current_direct_source_sha256,
            explorer_source_sha256,
        )

        source_evidence: tuple[dict[str, str | bool], ...] = ()
        source_hash = explorer_source_sha256(
            state.explorer_context, scout_skip_target,
        )
        current_hash = current_direct_source_sha256(
            scout_skip_target, state.project_dir,
        )
        if source_hash and source_hash == current_hash:
            source_evidence = ({
                "path": scout_skip_target,
                "sha256": current_hash,
                "complete": True,
            },)
        model_choice = recommend_checkpoint_role(
            state,
            allowed_roles=("architect", "scout"),
            deterministic_role="architect",
            evidence=role_decision.available_evidence,
            source_evidence=source_evidence,
        )
        selected_role = model_choice.get("role", role_decision.role)

    if role_decision.missing_inputs:
        goal_sha256 = hashlib.sha256(state.aufgabe.encode("utf-8")).hexdigest()
        refresh_count = phase_data.get("planner_evidence_refresh_count", 0)
        already_refreshed = (
            phase_data.get("planner_evidence_refresh_goal_sha256") == goal_sha256
            and isinstance(refresh_count, int)
            and not isinstance(refresh_count, bool)
            and refresh_count >= 1
        )
        next_role = "stop_missing_evidence" if already_refreshed else "refresh_evidence"
        reason = (
            "planner_role_required_evidence_unavailable_after_refresh"
            if already_refreshed
            else "planner_role_required_evidence_missing"
        )
    elif selected_role is None:
        next_role = "split"
        reason = "planner_dispatch_missing_graph_checkpoint"
    else:
        next_role = {
            "scout": "scout",
            "architect": "architect",
            "planner_split": "split",
            "builder_direct": "direct",
        }[selected_role]
        reason = (
            "scout_skipped:" + scout_route_reason
            if selected_role == "architect"
            and not role_artifacts.get("scout")
            and scout_route_reason
            else role_decision.reason
        )
        if model_choice is not None and selected_role != role_decision.role:
            reason = "project_coordinator_selected_scout"

    if (
        next_role in {"architect", "split", "dispatch"}
        and not state.preflight_checkpoint_ready
        and not state.preflight_checkpoint_skipped
    ):
        return {
            "decision": "collect_required_planning_evidence",
            "coordinator_action": "plan_preflight",
            "reason": "selected_role_requires_current_measurements",
            "next_executor": "preflight",
            "decision_basis": {
                "setup_context_ready": True,
                "selected_planner_role": selected_role,
                "planner_role_decision_reason": role_decision.reason,
                "planner_role_evidence": list(role_decision.available_evidence),
                "preflight_checkpoint_current": False,
                "preflight_trigger": "architect_or_task_graph_work_selected",
                "plan_checkpoint_complete": plan_checkpoint_complete,
                "plan_goal_matches": plan_goal_matches,
                "plan_run_matches": plan_run_matches,
                "plan_project_matches": plan_project_matches,
                "task_count": task_count,
            },
        }

    action = (
        "refresh_project_evidence" if next_role == "refresh_evidence"
        else "stop_missing_evidence" if next_role == "stop_missing_evidence"
        else f"planner_{next_role}"
    )
    decision: dict[str, Any] = {
        "decision": "prepare_approved_work_graph",
        "coordinator_action": action,
        "reason": reason,
        "next_executor": (
            "project_context_tools" if next_role == "refresh_evidence"
            else "coordinator" if next_role == "stop_missing_evidence"
            else f"planner_{next_role}"
        ),
        "decision_basis": {
            "setup_context_ready": True,
            "setup_context_source": (
                "direct_current_source_tool"
                if isinstance(dispatch, dict)
                and dispatch.get("selected") == "direct_builder"
                and dispatch.get("reason") == "direct_builder_current_source_evidence"
                else "scout_owned_graphify_retrieval"
                if next_role == "scout" and not state.coordinator_setup_context_ready
                else "explicit_current_sources"
                if explicit_source_context_ready else "fresh_explorer"
            ),
            "setup_checkpoint_complete": phase_data.get("setup_complete") is True,
            "plan_checkpoint_complete": plan_checkpoint_complete,
            "preflight_checkpoint_current": state.preflight_checkpoint_ready,
            "preflight_policy": (
                "skip_low_risk_direct_builder"
                if state.preflight_checkpoint_skipped else "current_checkpoint"
            ),
            "plan_goal_matches": plan_goal_matches,
            "plan_run_matches": plan_run_matches,
            "plan_project_matches": plan_project_matches,
            "plan_fingerprint_matches": plan_fingerprint_matches,
            "task_count": task_count,
            "planner_role_stage": planner_role_stage,
            "planner_role_decision": role_decision.role,
            "planner_role_selected": selected_role,
            "planner_role_decision_reason": role_decision.reason,
            "planner_role_available_evidence": list(role_decision.available_evidence),
            "planner_role_required_evidence": list(role_decision.required_evidence),
            "planner_role_missing_evidence": list(role_decision.missing_evidence),
            "planner_role_missing_inputs": list(role_decision.missing_inputs),
            "scout_route_reason": scout_route_reason,
            "direct_builder_ready": direct_builder_ready,
            "direct_builder_reason": direct_builder_reason,
        },
    }
    if model_choice is not None:
        decision["coordinator_model_choice"] = model_choice
    if next_role == "refresh_evidence" and preserve_failed_tasks_on_setup:
        decision["preserve_failed_tasks_on_setup"] = True
    return decision


def choose_task_checkpoint_action(
    phase_state: Any,
    next_task: dict[str, Any] | None,
    *,
    state: RunState | None = None,
) -> dict[str, Any]:
    """Describe the evidence-based next action at a persisted task boundary."""
    task_progress = phase_state.progress()
    criteria = phase_state.criteria_progress()
    evidence_check = getattr(
        phase_state, "task_verify_evidence_is_current", None,
    )
    file_hash_check = getattr(phase_state, "_task_file_hashes", None)
    verification_tasks: dict[str, list[str]] = {
        "current": [], "reverify_possible": [], "unverifiable": [],
    }
    phase_data = getattr(phase_state, "data", {})
    task_records = (
        phase_data.get("tasks", []) if isinstance(phase_data, dict) else []
    )
    if isinstance(task_records, list):
        for record in task_records:
            if (
                not isinstance(record, dict)
                or record.get("status") == "superseded"
                or not record.get("criterion_refs")
            ):
                continue
            task_id = record.get("id")
            if not isinstance(task_id, str) or not task_id.strip():
                verification_tasks["unverifiable"].append("<missing-task-id>")
                continue
            try:
                is_current = (
                    callable(evidence_check)
                    and evidence_check(task_id, record.get("verify_evidence"))
                    is True
                )
            except (OSError, RuntimeError, TypeError, ValueError):
                is_current = False
            if is_current:
                verification_tasks["current"].append(task_id[:120])
                continue
            try:
                can_reverify = (
                    callable(file_hash_check)
                    and isinstance(file_hash_check(record.get("task_files")), dict)
                )
            except (OSError, RuntimeError, TypeError, ValueError):
                can_reverify = False
            bucket = "reverify_possible" if can_reverify else "unverifiable"
            verification_tasks[bucket].append(task_id[:120])
    verify_total = sum(len(items) for items in verification_tasks.values())
    verification_snapshot: dict[str, Any] = {
        "required_task_count": verify_total,
        "current_count": len(verification_tasks["current"]),
        "reverify_possible_count": len(verification_tasks["reverify_possible"]),
        "unverifiable_count": len(verification_tasks["unverifiable"]),
    }
    for name, task_ids in verification_tasks.items():
        verification_snapshot[name] = task_ids[:20]
        verification_snapshot[f"{name}_omitted_count"] = max(
            0, len(task_ids) - 20,
        )
    verification_complete = (
        bool(verification_snapshot["required_task_count"])
        and verification_snapshot["current_count"] == verify_total
    )
    if next_task is not None:
        task_id = next_task.get("id")
        review_checkpoint = next_task.get("review_checkpoint")
        if next_task.get("verify_recovery_only") is True:
            if (
                next_task.get("verify_recovery_checkpoint_current") is True
                and isinstance(task_id, str)
            ):
                decision = "recover_verify_failure_checkpoint"
                executor = "verify_recovery"
                reason = "Aktuelle Verify-Fehlerbelege erlauben genau einen gezielten Recovery-Schritt."
            else:
                decision = "reject_stale_verify_failure_checkpoint"
                executor = None
                reason = "Verify-Recovery-Beleg ist veraltet oder passt nicht mehr zu den Taskdateien."
            review_dispatch = None
        elif (
            isinstance(review_checkpoint, dict)
            and next_task.get("verification_only") is not True
        ):
            if (
                not isinstance(task_id, str)
                or not callable(getattr(
                    phase_state, "task_review_checkpoint_is_current", None,
                ))
                or phase_state.task_review_checkpoint_is_current(task_id) is not True
            ):
                decision = "reject_stale_review_checkpoint"
                executor = None
                reason = "review_checkpoint_verify_evidence_missing_or_stale"
                review_dispatch = None
            else:
                review_task = dict(next_task)
                warnings = review_checkpoint.get("verify_warnings")
                review_warnings = warnings if isinstance(warnings, list) else []
                try:
                    from werkstatt.reviewer import _get_git_diff

                    diff = _get_git_diff(
                        project_dir=(state.project_dir if state else None),
                        task_files=review_task.get("task_files"),
                    )
                except (OSError, RuntimeError, TypeError, ValueError):
                    diff = None
                from werkstatt.review_dispatch import reviewer_dispatch_decision

                review_dispatch = reviewer_dispatch_decision(
                    review_task,
                    diff,
                    verify_warnings=review_warnings,
                    recovery=bool(
                        state is not None
                        and (
                            getattr(state, "reflection_chat_builder_reserve_active", False)
                            or getattr(state, "reflection_chat_evidence", None)
                        )
                    ),
                )
                if review_dispatch.get("invoke_reviewer") is True:
                    decision = "review_task_checkpoint"
                    executor = "reviewer"
                    reason = str(review_dispatch.get("reason") or "review_required")
                else:
                    decision = "complete_task_checkpoint"
                    executor = "task_completion"
                    reason = "current_verify_and_low_risk_diff_evidence_sufficient"
        else:
            raw_action = next_task.get("action", "update")
            action = str("update" if raw_action is None else raw_action)
            build_handoff = bool(
                next_task.get("verification_only") is True
                and isinstance(task_id, str)
                and callable(getattr(
                    phase_state, "task_build_checkpoint_is_current", None,
                ))
                and phase_state.task_build_checkpoint_is_current(task_id)
            )
            executor = (
                "verify_only"
                if next_task.get("verification_only") is True
                else {
                    "read": "read_only_task",
                    "verify": "verify_only",
                    "create": "builder",
                    "update": "builder",
                }.get(action)
            )
            review_dispatch = None
            if executor is None:
                decision = "reject_invalid_task_action"
                reason = f"Task-Aktion {action!r} hat keinen freigegebenen Executor."
            else:
                decision = (
                    "verify_task_checkpoint"
                    if build_handoff
                    else "execute_planned_task"
                )
                reason = (
                    "Verify fuer einen gebundenen Task-Checkpoint gewaehlt."
                    if build_handoff
                    else f"{executor} fuer naechsten abhaengigkeitsfreien Task "
                    "aus dem freigegebenen Graph gewaehlt."
                )
    elif task_progress.get("pending", 0):
        executor = None
        decision = "resolve_blocked_graph"
        reason = "Keine ausfuehrbare Task-Graph-Node; offene Tasks bleiben sichtbar."
    elif task_progress.get("blocked", 0):
        executor = None
        decision = "reject_blocked_graph"
        reason = (
            "Der Graph wurde aufgeloest, enthaelt aber weiterhin blockierte "
            "Tasks; der Checkpoint stoppt statt dieselben Tasks erneut "
            "aufzuloesen."
        )
    else:
        decision = None
        verify_failure = phase_data.get(
            "phase_end_verify_failure_checkpoint",
        ) if isinstance(phase_data, dict) else None
        verify_failure_status = (
            verify_failure.get("status")
            if isinstance(verify_failure, dict) else None
        )
        current_worktree = None
        if isinstance(verify_failure, dict) and state is not None:
            from werkstatt.failure_record import _worktree_fingerprint

            current_worktree = _worktree_fingerprint(Path(state.project_dir))
        if (
            isinstance(verify_failure, dict)
            and verify_failure_status == "pending"
            and state is not None
            and phase_state.phase_end_verify_failure_is_current(
                project_dir=Path(state.project_dir),
            )
        ):
            decision = "recover_phase_end_verify_checkpoint"
            executor = "verify_recovery"
            reason = "Aktuelle Phase-End-Verify-Belege erlauben einen gezielten Recovery-Schritt."
        elif (
            isinstance(verify_failure, dict)
            and verify_failure_status == "attempted"
            and verify_failure.get("worktree_sha256") == current_worktree
        ):
            decision = "reject_stalled_phase_end_verify_recovery"
            executor = None
            reason = "Phase-End-Verify blieb nach dem Recovery-Schritt auf demselben Worktree rot."
        else:
            executor = "phase_end_verify"
        if decision in {
            "recover_phase_end_verify_checkpoint",
            "reject_stalled_phase_end_verify_recovery",
        }:
            pass
        elif task_progress.get("failed", 0):
            from werkstatt.criteria_replan import eligible_failed_task_ids

            replannable = (
                criteria.get("tracked") is True
                and (
                    criteria.get("valid") is True
                    or criteria.get("error") == "criteria_not_assigned"
                )
                and eligible_failed_task_ids(
                    phase_state, criteria.get("uncovered"),
                )
            )
            if replannable:
                executor = "planner_and_plan_gate"
                decision = "replan_failed_criteria"
                reason = (
                    "Alle Tasks sind terminal; fehlgeschlagene, "
                    "kriteriumsgebundene Recovery ist erschoepft. "
                    "Nur bereits freigegebene offene Kriterien duerfen "
                    "neu geplant und erneut freigegeben werden."
                )
            else:
                decision = "verify_with_failed_tasks"
                reason = (
                    "Task-Graph erschoepft, aber mindestens ein Task "
                    "ist fehlgeschlagen und nicht sicher neu planbar."
                )
        elif (
            task_progress.get("total", 0) > 0
            and task_progress.get("done", 0) == task_progress.get("total", 0)
            and criteria.get("tracked") is True
            and criteria.get("error") == "criteria_not_assigned"
            and criteria.get("uncovered")
        ):
            executor = "planner_and_plan_gate"
            decision = "replan_unassigned_criteria"
            reason = (
                "Alle geplanten Tasks sind erledigt, aber explizite "
                "Akzeptanzkriterien sind keinem Task zugeordnet; nur diese "
                "Kriterien muessen am Checkpoint neu geplant werden."
            )
        elif criteria.get("tracked") and not criteria.get("valid"):
            decision = "verify_invalid_criteria_mapping"
            reason = "Kriterienzuordnung ist ungueltig oder unvollstaendig."
        elif criteria.get("tracked") and criteria.get("uncovered"):
            decision = "verify_with_open_criteria"
            reason = "Task-Graph erschoepft, aber Kriterienabdeckung ist unvollstaendig."
        elif (
            criteria.get("tracked") is True
            and criteria.get("valid") is True
            and not criteria.get("uncovered")
            and verification_snapshot["unverifiable_count"]
        ):
            executor = None
            decision = "reject_criteria_verify_scope_missing"
            reason = (
                "Kriterien und Taskstatus sind vollstaendig, aber fuer "
                f"{verification_snapshot['unverifiable_count']} kriteriumsgebundene "
                "Tasks fehlt ein aktueller Dateiscope fuer taskgebundene "
                "Verify-Belege. Phase-End-Verify wird nicht als Ersatz gewertet."
            )
        elif not criteria.get("tracked"):
            decision = "verify_untracked_criteria"
            reason = "Keine belegte Kriterienzuordnung; Abschluss darf Zielerreichung nicht behaupten."
        else:
            decision = "run_phase_end_verify"
            reason = "Task-Graph abgeschlossen; finale Verify entscheidet ueber den Abschluss."

    criteria_snapshot = {
        key: criteria.get(key)
        for key in ("tracked", "valid", "covered", "uncovered", "error")
    }
    candidate = bool(
        next_task is None
        and task_progress.get("failed", 0) == 0
        and task_progress.get("blocked", 0) == 0
        and task_progress.get("pending", 0) == 0
        and criteria.get("tracked")
        and criteria.get("valid")
        and not criteria.get("uncovered")
    )
    raw_verify = getattr(state, "last_verify_results", []) if state else []
    verify_evidence = []
    if isinstance(raw_verify, list):
        for result in raw_verify[-50:]:
            if not isinstance(result, dict):
                continue
            stage_id = result.get("stage_id")
            if not isinstance(stage_id, str):
                continue
            item: dict[str, Any] = {
                "stage_id": stage_id[:120],
                "ok": bool(result.get("ok", False)),
            }
            exit_code = result.get("exit_code")
            if isinstance(exit_code, int) and not isinstance(exit_code, bool):
                item["exit_code"] = exit_code
            artifact_hash = result.get("artifact_sha256")
            if isinstance(artifact_hash, str):
                item["artifact_sha256"] = artifact_hash[:128]
            verify_evidence.append(item)
    result = {
        "decision": decision,
        "reason": reason,
        "next_task_id": next_task.get("id") if next_task else None,
        "next_action": next_task.get("action") if next_task else None,
        "verification_only": bool(
            next_task and next_task.get("verification_only") is True
        ),
        "next_executor": executor,
        "task_progress": task_progress,
        "criteria_task_coverage": criteria_snapshot,
        "criteria_task_verification": verification_snapshot,
        "last_verify_evidence": verify_evidence,
        "goal_candidate_before_final_verify": candidate and verification_complete,
        "final_verify_required": True,
    }
    if next_task is not None and isinstance(
        next_task.get("review_checkpoint"), dict,
    ):
        result["review_dispatch"] = review_dispatch
    if decision in {
        "recover_verify_failure_checkpoint",
        "reject_stale_verify_failure_checkpoint",
    }:
        checkpoint = (
            next_task.get("verify_failure_checkpoint")
            if isinstance(next_task, dict) else None
        )
        if isinstance(checkpoint, dict):
            result["verify_recovery_evidence"] = {
                "current": (
                    isinstance(next_task, dict)
                    and next_task.get("verify_recovery_checkpoint_current") is True
                ),
                "sha256": str(checkpoint.get("evidence_sha256", ""))[:64],
                "error_count": min(
                    8,
                    len(checkpoint.get("verify_errors", []))
                    if isinstance(checkpoint.get("verify_errors"), list)
                    else 0,
                ),
            }
    return result
