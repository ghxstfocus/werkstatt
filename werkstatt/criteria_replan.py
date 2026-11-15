"""Goal-bound checkpoint replanning for criteria missing task coverage."""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

from werkstatt.phase_state import PhaseState
from werkstatt.state import RunState


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
    """Append and approve tasks only for criteria omitted by a finished plan.

    Existing completed task records and their evidence remain untouched. The
    candidate graph is plan-gated before it is appended to the phase checkpoint.
    """
    progress = phase_state.criteria_progress()
    task_progress = phase_state.progress()
    if (
        progress.get("tracked") is not True
        or progress.get("valid") is not False
        or progress.get("error") != "criteria_not_assigned"
        or not isinstance(progress.get("uncovered"), list)
        or not progress.get("uncovered")
        or task_progress.get("total", 0) <= 0
        or task_progress.get("done", 0) != task_progress.get("total", 0)
    ):
        return False

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
    graph_identity = [
        (task.get("id"), task.get("status"))
        for task in phase_state.data.get("tasks", [])
        if isinstance(task, dict)
    ]
    signature = json.dumps(
        {
            "run_id": state.run_id,
            "uncovered": list(zip(missing_refs, missing_criteria)),
            "task_graph": graph_identity,
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
    if existing_additions:
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
        phase_state, replan_id, "planning", criteria_refs=missing_refs,
    )
    from werkstatt.audit import audit

    audit(
        "loop_phase",
        {
            "phase": "criteria_replan",
            "status": "start",
            "replan_id": replan_id,
            "criteria_refs": missing_refs,
            "reason": "finished_graph_left_approved_criteria_unassigned",
        },
        state.project_dir,
        state.project_name,
    )

    base_calls = state.llm_calls
    addition = deepcopy(state)
    addition.aufgabe = (
        f"{state.aufgabe}\n\n"
        "## Checkpoint-Neuplanung: nur fehlende bestehende Kriterien\n"
        "Der freigegebene Task-Graph ist erledigt. Ergaenze ausschliesslich "
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
