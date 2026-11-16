"""Goal-bound checkpoint replanning for uncovered approved criteria."""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

from werkstatt.phase_state import PhaseState
from werkstatt.state import RunState

_REPLANNABLE_FAILURES = {
    "builder_failed",
    "reflection_ohne_apply",
    "patch_not_applied_nach_reflection",
}


def eligible_failed_task_ids(
    phase_state: PhaseState,
    uncovered: object,
) -> list[str]:
    """Return failed criterion tasks safe for a gated replacement plan."""
    if (
        not isinstance(uncovered, list) or not uncovered
        or any(
            not isinstance(ref, str)
            or not ref.startswith("AC")
            or not ref[2:].isdigit()
            or int(ref[2:]) <= 0
            for ref in uncovered
        )
        or len(set(uncovered)) != len(uncovered)
    ):
        return []
    tasks = phase_state.data.get("tasks")
    if not isinstance(tasks, list):
        return []
    failed = [
        task for task in tasks
        if isinstance(task, dict) and task.get("status") == "failed"
    ]
    if not failed:
        return []
    task_ids: list[str] = []
    for task in failed:
        task_id = task.get("id")
        refs = task.get("criterion_refs")
        if (
            not isinstance(task_id, str)
            or task.get("failure") not in _REPLANNABLE_FAILURES
            or not isinstance(refs, list)
            or not refs
            or any(not isinstance(ref, str) for ref in refs)
        ):
            return []
        task_ids.append(task_id)
    if not any(
        isinstance(ref, str) and ref.startswith("AC")
        and ref[2:].isdigit() and int(ref[2:]) > 0
        for ref in uncovered
    ):
        return []
    # Recovery may leave both failed criteria and criteria the approved plan
    # never assigned. Re-plan the complete uncovered set; retain failed tasks
    # as superseded history only after the replacement plan is approved.
    # Unknown failure classes remain a hard stop.
    return sorted(task_ids)


def _record_attempt(
    phase_state: PhaseState,
    replan_id: str,
    status: str,
    **details: Any,
) -> None:
    records = phase_state.data.setdefault("criteria_replans", [])
    if not isinstance(records, list):
        raise TypeError("criteria_replans checkpoint is invalid")
    for item in records:
        if isinstance(item, dict) and item.get("replan_id") == replan_id:
            item.update({"status": status, **details})
            phase_state.save()
            return
    records.append({"replan_id": replan_id, "status": status, **details})
    phase_state.save()


def replan_unassigned_criteria(
    state: RunState,
    phase_state: PhaseState,
) -> bool:
    """Re-plan uncovered approved criteria after an exhausted safe graph.

    Existing completed task records and their evidence remain untouched.
    Allowlisted failed records are retained as superseded history only after
    the candidate graph passes both approval gates.
    """
    records = phase_state.data.get("criteria_replans", [])
    phase_tasks = phase_state.data.get("tasks", [])
    if isinstance(records, list) and isinstance(phase_tasks, list):
        for record in records:
            if (
                not isinstance(record, dict)
                or record.get("status") not in {"planning", "pending", "failed"}
            ):
                continue
            replan_id = record.get("replan_id")
            if not isinstance(replan_id, str):
                continue
            additions = [
                task for task in phase_tasks
                if isinstance(task, dict)
                and task.get("source_followup_id") == replan_id
            ]
            if not additions:
                continue
            replaced = record.get("replaced_task_ids", [])
            if isinstance(replaced, list) and replaced:
                phase_state.supersede_failed_tasks(
                    replaced, replan_id=replan_id,
                )
            state.tasks = [
                dict(task) for task in phase_state.data.get("tasks", [])
                if isinstance(task, dict)
            ]
            state.tests = list(phase_state.data.get("tests", []))
            state.akzeptanzkriterien = list(
                phase_state.data.get("akzeptanzkriterien", []),
            )
            state.phasen = list(phase_state.data.get("phasen", []))
            _record_attempt(
                phase_state, replan_id, "applied_after_resume",
                task_ids=[task.get("id") for task in additions],
            )
            return True

    progress = phase_state.criteria_progress()
    task_progress = phase_state.progress()
    uncovered = progress.get("uncovered")
    graph_terminal = (
        task_progress.get("pending", 0) == 0
        and task_progress.get("blocked", 0) == 0
    )
    unassigned_case = (
        progress.get("valid") is False
        and progress.get("error") == "criteria_not_assigned"
        and graph_terminal
    )
    replaced_task_ids = (
        eligible_failed_task_ids(phase_state, uncovered)
        if (
            (
                progress.get("valid") is True
                or progress.get("error") == "criteria_not_assigned"
            )
            and task_progress.get("failed", 0) > 0
            and graph_terminal
        )
        else []
    )
    failed_case = bool(replaced_task_ids)
    if (
        progress.get("tracked") is not True
        or not isinstance(uncovered, list)
        or not uncovered
        or task_progress.get("total", 0) <= 0
        or not (unassigned_case or failed_case)
    ):
        return False
    replan_mode = (
        "failed_and_unassigned_criteria" if failed_case and unassigned_case
        else "failed_criteria_recovery" if failed_case
        else "unassigned_criteria"
    )

    criteria = phase_state.data.get("akzeptanzkriterien")
    if not isinstance(criteria, list):
        return False
    missing_refs = [
        ref for ref in progress["uncovered"]
        if isinstance(ref, str)
        and ref.startswith("AC")
        and ref[2:].isdigit()
        and 1 <= int(ref[2:]) <= len(criteria)
    ]
    if len(missing_refs) != len(progress["uncovered"]):
        return False
    missing_criteria = [criteria[int(ref[2:]) - 1] for ref in missing_refs]
    failed_task_details = [
        {
            "id": task.get("id"),
            "name": str(task.get("name") or "")[:200],
            "action": task.get("action"),
            "task_files": [
                str(path)[:240] for path in task.get("task_files", [])[:12]
                if isinstance(path, str)
            ] if isinstance(task.get("task_files"), list) else [],
            "failure": task.get("failure"),
            "failure_detail": str(task.get("failure_detail") or "")[:1200],
        }
        for task in phase_state.data.get("tasks", [])
        if isinstance(task, dict) and task.get("id") in replaced_task_ids
    ]
    graph_identity = [
        (task.get("id"), task.get("status"))
        for task in phase_state.data.get("tasks", [])
        if isinstance(task, dict)
    ]
    signature = json.dumps(
        {
            "run_id": state.run_id,
            "mode": replan_mode,
            "uncovered": list(zip(missing_refs, missing_criteria)),
            "task_graph": graph_identity,
            "replaced_task_ids": replaced_task_ids,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    replan_id = "criteria-replan-" + hashlib.sha256(
        signature.encode("utf-8"),
    ).hexdigest()[:20]
    existing_records = phase_state.data.get("criteria_replans", [])
    if not isinstance(existing_records, list):
        raise TypeError("criteria_replans checkpoint is invalid")
    prior = next((
        item for item in existing_records
        if isinstance(item, dict) and item.get("replan_id") == replan_id
    ), None)
    existing_additions = [
        task for task in phase_state.data.get("tasks", [])
        if isinstance(task, dict)
        and task.get("source_followup_id") == replan_id
    ]
    if (
        failed_case
        and task_progress.get("pending", 0) > 0
        and not existing_additions
    ):
        return False
    if existing_additions:
        if replaced_task_ids:
            phase_state.supersede_failed_tasks(
                replaced_task_ids, replan_id=replan_id,
            )
        state.tasks = [
            dict(task) for task in phase_state.data.get("tasks", [])
            if isinstance(task, dict)
        ]
        state.tests = list(phase_state.data.get("tests", []))
        state.akzeptanzkriterien = list(criteria)
        _record_attempt(
            phase_state, replan_id, "applied_after_resume",
            task_ids=[task.get("id") for task in existing_additions],
        )
        return True
    if prior is not None and prior.get("status") in {"failed", "rejected"}:
        return False

    _record_attempt(
        phase_state, replan_id, "planning",
        criteria_refs=missing_refs,
        mode=replan_mode,
        replaced_task_ids=replaced_task_ids,
    )
    from werkstatt.audit import audit

    audit(
        "loop_phase",
        {
            "phase": "criteria_replan",
            "status": "start",
            "replan_id": replan_id,
            "criteria_refs": missing_refs,
            "mode": replan_mode,
            "replaced_task_ids": replaced_task_ids,
            "reason": (
                "failed_task_recovery_exhausted"
                if failed_case else
                "finished_graph_left_approved_criteria_unassigned"
            ),
        },
        state.project_dir,
        state.project_name,
    )

    base_calls = state.llm_calls
    addition = deepcopy(state)
    addition.aufgabe = (
        f"{state.aufgabe}\n\n"
        "## Checkpoint-Neuplanung: nur offene bestehende Kriterien\n"
        + (
            "Vorherige Tasks sind nach ihrer Recovery fehlgeschlagen. Nutze "
            "die protokollierte Fehlerursache, um denselben Fehlansatz nicht "
            "zu wiederholen; plane eine begruendete, andere oder gezieltere "
            "Vorgehensweise und nenne benoetigte fehlende Informationen.\n"
            "Fehlgeschlagene Task-Belege (JSON):\n"
            + json.dumps(failed_task_details, ensure_ascii=False, sort_keys=True)
            + "\n"
            if failed_case else
            "Der freigegebene Task-Graph ist erledigt.\n"
        )
        + "Ergaenze ausschliesslich "
        "Tasks, die die folgenden bereits freigegebenen Akzeptanzkriterien "
        "erfuellen. Aendere oder erweitere weder Nutzerziel noch Kriterien. "
        "Verwende fuer diese Kriterien ausschliesslich die exakt angegebenen "
        "Kriterientexte und ordne jedem Task die passenden criterion_refs zu.\n"
        + "\n".join(
            f"- {ref}: {text}"
            for ref, text in zip(missing_refs, missing_criteria)
        )
    )
    addition.tasks = []
    addition.tests = []
    addition.akzeptanzkriterien = []
    addition.phasen = []
    addition.architect_prosa = ""
    addition.scout_auftrag = {}
    addition.scout_api_auszug = {}
    addition.explorer_context = {}
    addition.explorer_findings = {}

    try:
        from werkstatt.gates import _human_gate_plan, _plan_gate
        from werkstatt.planner import run_planner
        from werkstatt.run_followups import _extend_candidate

        if not run_planner(addition):
            raise RuntimeError("criteria_replan_planner_failed")
        if addition.akzeptanzkriterien != missing_criteria:
            raise ValueError("criteria_replan_changed_approved_criteria")
        if not addition.tasks or not _plan_gate(addition):
            raise ValueError("criteria_replan_candidate_invalid")

        candidate, new_tasks, _combined, tests, phases = _extend_candidate(
            state, addition, replan_id,
        )
        local_to_original = {
            f"AC{len(criteria) + index}": ref
            for index, ref in enumerate(missing_refs, 1)
        }
        remapped_by_id: dict[str, list[str]] = {}
        for task in new_tasks:
            refs = task.get("criterion_refs")
            if not isinstance(refs, list) or not refs:
                raise ValueError("criteria_replan_task_without_criteria")
            remapped: list[str] = []
            for ref in refs:
                original_ref = local_to_original.get(ref)
                if original_ref is None:
                    raise ValueError("criteria_replan_task_outside_missing_criteria")
                remapped.append(original_ref)
            task["criterion_refs"] = remapped
            remapped_by_id[str(task["id"])] = remapped
        for task in candidate.tasks:
            if isinstance(task, dict) and str(task.get("id")) in remapped_by_id:
                task["criterion_refs"] = remapped_by_id[str(task["id"])]
        candidate.akzeptanzkriterien = list(criteria)
        if not _plan_gate(candidate):
            raise ValueError("criteria_replan_combined_graph_invalid")
        gate_result = _human_gate_plan(
            candidate, kontext="criteria_replan",
        )
        if gate_result != 0:
            _record_attempt(
                phase_state, replan_id,
                "pending" if gate_result == 2 else "rejected",
                gate_result=gate_result,
            )
            audit(
                "loop_phase",
                {
                    "phase": "criteria_replan",
                    "status": "pending" if gate_result == 2 else "rejected",
                    "replan_id": replan_id,
                    "criteria_refs": missing_refs,
                },
                state.project_dir,
                state.project_name,
            )
            return False

        task_ids = phase_state.append_followup_tasks(
            new_tasks,
            criteria=list(criteria),
            tests=tests,
            phases=phases,
            followup_id=replan_id,
        )
        if replaced_task_ids:
            phase_state.supersede_failed_tasks(
                replaced_task_ids, replan_id=replan_id,
            )
        state.tasks = [
            dict(task) for task in phase_state.data.get("tasks", [])
            if isinstance(task, dict)
        ]
        state.tests = list(phase_state.data.get("tests", []))
        state.akzeptanzkriterien = list(criteria)
        state.phasen = list(phase_state.data.get("phasen", []))
        state.architect_prosa = candidate.architect_prosa
        _record_attempt(
            phase_state, replan_id, "applied", task_ids=task_ids,
        )
        audit(
            "loop_phase",
            {
                "phase": "criteria_replan",
                "status": "approved",
                "replan_id": replan_id,
                "criteria_refs": missing_refs,
                "task_ids": task_ids,
                "llm_calls": max(0, addition.llm_calls - base_calls),
            },
            state.project_dir,
            state.project_name,
        )
        return True
    except (ImportError, OSError, RuntimeError, TypeError, ValueError) as exc:
        _record_attempt(
            phase_state, replan_id, "failed",
            reason=str(exc)[:300],
        )
        audit(
            "loop_phase",
            {
                "phase": "criteria_replan",
                "status": "failed",
                "replan_id": replan_id,
                "criteria_refs": missing_refs,
                "reason": type(exc).__name__,
            },
            state.project_dir,
            state.project_name,
        )
        return False
    finally:
        state.llm_calls = max(state.llm_calls, addition.llm_calls)
        if addition.budget_exhausted_reason:
            state.budget_exhausted_reason = addition.budget_exhausted_reason
