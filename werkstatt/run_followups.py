"""Checkpoint reconciliation for explicitly accepted chat write requests."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from typing import Any

from werkstatt.event_store import EventStore
from werkstatt.phase_state import PhaseState
from werkstatt.state import RunState


class FollowupReconciliationError(RuntimeError):
    """A confirmed follow-up could not be safely added to its run."""


def _append_checkpoint_status(
    store: EventStore,
    project: str,
    run_id: str,
    proposal_id: str,
    status: str,
    *,
    task_ids: list[str] | None = None,
) -> None:
    for _ in range(5):
        record = store.get_run_record(project, run_id)
        if record is None:
            raise FollowupReconciliationError("Run-Checkpoint fehlt")
        checkpoint = dict(record["checkpoint"])
        requests = checkpoint.get("chat_followup_requests", [])
        if not isinstance(requests, list):
            raise FollowupReconciliationError("Follow-up-Ledger ist ungueltig")
        found = False
        updated: list[dict[str, Any]] = []
        for item in requests:
            if not isinstance(item, dict):
                continue
            current = dict(item)
            if current.get("proposal_id") == proposal_id:
                found = True
                current["status"] = status
                if task_ids is not None:
                    current["task_ids"] = list(task_ids)
            updated.append(current)
        if not found:
            raise FollowupReconciliationError(
                f"Follow-up {proposal_id} fehlt im Run-Checkpoint",
            )
        checkpoint["chat_followup_requests"] = updated[-50:]
        try:
            store.update_run_checkpoint(
                project,
                run_id,
                checkpoint,
                expected_version=record["checkpoint_version"],
            )
            return
        except RuntimeError:
            continue
    raise FollowupReconciliationError("Follow-up-Checkpoint blieb konkurrierend")


def _extend_candidate(
    current: RunState,
    addition: RunState,
    proposal_id: str,
) -> tuple[RunState, list[dict[str, Any]], list[str], list[Any], list[dict[str, Any]]]:
    existing_criteria = list(current.akzeptanzkriterien or [])
    added_criteria = list(addition.akzeptanzkriterien or [])
    combined_criteria = existing_criteria + added_criteria
    prefix = "fu_" + sha256(proposal_id.encode("utf-8")).hexdigest()[:10] + "_"
    raw_tasks = [task for task in (addition.tasks or []) if isinstance(task, dict)]
    id_map = {
        str(task.get("id")): prefix + str(task.get("id"))
        for task in raw_tasks
    }
    raw_phases = [
        phase for phase in (addition.phasen or [])
        if isinstance(phase, dict) and isinstance(phase.get("id"), str)
    ]
    phase_id_map = {
        str(phase["id"]): prefix + "phase_" + str(phase["id"])
        for phase in raw_phases
    }
    criteria_map = {
        f"AC{index}": f"AC{len(existing_criteria) + index}"
        for index in range(1, len(added_criteria) + 1)
    }
    new_tasks: list[dict[str, Any]] = []
    for raw in raw_tasks:
        task = deepcopy(raw)
        original_id = str(task["id"])
        task["id"] = id_map[original_id]
        task["dependencies"] = [
            id_map.get(str(dep), str(dep))
            for dep in (task.get("dependencies") or [])
        ]
        task["criterion_refs"] = [
            criteria_map.get(str(ref), str(ref))
            for ref in (task.get("criterion_refs") or [])
        ]
        if task.get("phase_id") is not None:
            task["phase_id"] = phase_id_map.get(
                str(task["phase_id"]), task["phase_id"],
            )
        if task.get("parent_id") is not None:
            task["parent_id"] = id_map.get(
                str(task["parent_id"]),
                phase_id_map.get(str(task["parent_id"]), task["parent_id"]),
            )
        new_tasks.append(task)

    new_phases: list[dict[str, Any]] = []
    for raw_phase in raw_phases:
        phase = deepcopy(raw_phase)
        phase_id = str(phase["id"])
        phase["id"] = phase_id_map[phase_id]
        parent_id = phase.get("parent_id")
        if parent_id is not None:
            phase["parent_id"] = phase_id_map.get(str(parent_id), parent_id)
        phase_tasks = phase.get("tasks")
        if isinstance(phase_tasks, list):
            phase["tasks"] = [id_map.get(str(task_id), task_id) for task_id in phase_tasks]
        new_phases.append(phase)

    candidate = deepcopy(current)
    candidate.tasks = list(current.tasks or []) + new_tasks
    candidate.akzeptanzkriterien = combined_criteria
    candidate.tests = list(current.tests or []) + list(addition.tests or [])
    candidate.phasen = list(current.phasen or []) + new_phases
    candidate.architect_prosa = "\n\n".join(
        part for part in (
            getattr(current, "architect_prosa", ""),
            getattr(addition, "architect_prosa", ""),
        ) if isinstance(part, str) and part.strip()
    )
    return (
        candidate,
        new_tasks,
        combined_criteria,
        list(addition.tests or []),
        new_phases,
    )


def reconcile_chat_followups(
    state: RunState,
    phase_state: PhaseState,
    store: EventStore,
    project: str,
    run_id: str,
) -> bool:
    """Plan and approve durable follow-ups at a safe task checkpoint.

    Returns true when the in-memory task graph was extended. Planner failure
    leaves the durable request in ``received`` so a resumed run can retry it.
    """
    record = store.get_run_record(project, run_id)
    if record is None:
        return False
    requests = record["checkpoint"].get("chat_followup_requests", [])
    if not isinstance(requests, list):
        raise FollowupReconciliationError("Follow-up-Ledger ist ungueltig")

    # The durable phase file is authoritative on resume, including the crash
    # window after PhaseState.save() but before the checkpoint is marked applied.
    phase_data = phase_state.data
    if isinstance(phase_data.get("tasks"), list):
        state.tasks = [
            dict(task) for task in phase_data["tasks"]
            if isinstance(task, dict)
        ]
    if isinstance(phase_data.get("tests"), list):
        state.tests = list(phase_data["tests"])
    if isinstance(phase_data.get("akzeptanzkriterien"), list):
        state.akzeptanzkriterien = list(phase_data["akzeptanzkriterien"])
    if isinstance(phase_data.get("phasen"), list):
        state.phasen = list(phase_data["phasen"])

    from werkstatt.audit import audit
    from werkstatt.gates import _human_gate_plan, _plan_gate
    from werkstatt.planner import run_planner

    changed = False
    for item in requests:
        if not isinstance(item, dict):
            continue
        proposal_id = item.get("proposal_id")
        if isinstance(proposal_id, str) and item.get("status") in {
            "applied", "rejected",
        }:
            _append_chat_disposition(
                item,
                project,
                run_id,
                str(item["status"]),
                (
                    "Folgeauftrag ist freigegeben und in den Task-Graph aufgenommen."
                    if item["status"] == "applied"
                    else "Der Folgeauftrag wurde im Plan-Gate abgelehnt."
                ),
                task_ids=(
                    item.get("task_ids")
                    if isinstance(item.get("task_ids"), list) else None
                ),
            )
            continue
        if item.get("status") != "received":
            continue
        request = item.get("request")
        if (
            not isinstance(request, str) or not request.strip()
            or not isinstance(proposal_id, str) or not proposal_id.strip()
        ):
            raise FollowupReconciliationError("Follow-up hat keinen Auftrag/Proposal")

        task_marker = sha256(proposal_id.encode("utf-8")).hexdigest()[:10]
        already_added = [
            task for task in phase_state.data.get("tasks", [])
            if isinstance(task, dict)
            and task.get("source_followup_id") == proposal_id
        ]
        if already_added:
            _append_checkpoint_status(
                store, project, run_id, proposal_id, "applied",
                task_ids=[str(task["id"]) for task in already_added],
            )
            _append_chat_disposition(
                item,
                project,
                run_id,
                "applied",
                "Folgeauftrag ist freigegeben und in den Task-Graph aufgenommen.",
                task_ids=[str(task["id"]) for task in already_added],
            )
            continue

        addition = deepcopy(state)
        addition.aufgabe = request.strip()
        addition.tasks = []
        addition.tests = []
        addition.akzeptanzkriterien = []
        addition.phasen = []
        addition.architect_prosa = ""
        # A follow-up is a fresh planning request. Do not let the Architect
        # reuse Scout/Explorer evidence gathered for the original objective.
        addition.scout_auftrag = {}
        addition.scout_api_auszug = {}
        addition.explorer_context = {}
        addition.explorer_findings = {}
        addition.auftrag_bereits_erfuellt = False
        addition.auftrag_bereits_erfuellt_bestaetigt = False
        addition.auftrag_bereits_erfuellt_quelle = ""
        if not run_planner(addition):
            raise FollowupReconciliationError(
                f"Planung des bestaetigten Folgeauftrags {proposal_id} fehlgeschlagen",
            )
        if not addition.tasks or not _plan_gate(addition):
            raise FollowupReconciliationError(
                f"Folgeauftrag {proposal_id} lieferte keinen gueltigen Task-Plan",
            )

        candidate, new_tasks, criteria, tests, phases = _extend_candidate(
            state, addition, proposal_id,
        )
        if not new_tasks or not _plan_gate(candidate):
            raise FollowupReconciliationError(
                f"Kombinierter Task-Graph fuer {proposal_id} ist ungueltig",
            )
        candidate.last_reject_kind = ""
        candidate.last_reject_reason = ""
        gate_result = _human_gate_plan(candidate, kontext="chat_followup")
        if gate_result == 2:
            _append_chat_disposition(
                item,
                project,
                run_id,
                "pending",
                "Das Plan-Gate ist abgelaufen. Der Folgeauftrag bleibt offen und wird nicht als abgelehnt gewertet.",
            )
            continue
        if gate_result != 0:
            if getattr(candidate, "last_reject_kind", "") == "plan":
                _append_checkpoint_status(
                    store, project, run_id, proposal_id, "rejected",
                )
                _append_chat_disposition(
                    item,
                    project,
                    run_id,
                    "rejected",
                    "Der Folgeauftrag wurde im Plan-Gate abgelehnt; der bestehende Task-Graph laeuft weiter.",
                )
                continue
            raise FollowupReconciliationError(
                f"Plan-Gate fuer Folgeauftrag {proposal_id} wurde nicht beantwortet",
            )

        ids = phase_state.append_followup_tasks(
            new_tasks,
            criteria=criteria,
            tests=tests,
            phases=phases,
            followup_id=proposal_id,
        )
        state.tasks = candidate.tasks
        state.tests = candidate.tests
        state.akzeptanzkriterien = candidate.akzeptanzkriterien
        state.phasen = candidate.phasen
        state.architect_prosa = candidate.architect_prosa
        _append_checkpoint_status(
            store, project, run_id, proposal_id, "applied", task_ids=ids,
        )
        _append_chat_disposition(
            item,
            project,
            run_id,
            "applied",
            f"Folgeauftrag ist freigegeben und in den Task-Graph aufgenommen ({len(ids)} Task(s)).",
            task_ids=ids,
        )
        audit(
            "loop_chat_followup_applied",
            {
                "proposal_id": proposal_id,
                "task_ids": ids,
                "criteria_added": len(addition.akzeptanzkriterien or []),
                "decision_summary": (
                    "Der bestaetigte Folgeauftrag wurde geplant, der Graph "
                    "deterministisch geprueft und am Chat-Plan-Gate freigegeben."
                ),
                "next_step": "Die neuen Tasks werden am sicheren Checkpoint ausgefuehrt.",
            },
            state.project_dir,
            project,
            run_id=run_id,
            audit_id=f"RUN-{run_id}-CHAT-FOLLOWUP-APPLIED-{task_marker}",
        )
        changed = True
    return changed


def _append_chat_disposition(
    item: dict[str, Any],
    project: str,
    run_id: str,
    status: str,
    detail: str,
    *,
    task_ids: list[str] | None = None,
) -> None:
    session_id = item.get("session_id")
    proposal_id = item.get("proposal_id")
    if not isinstance(session_id, str) or not isinstance(proposal_id, str):
        return
    from werkstatt.chat_session import ChatSession

    ChatSession(project, session_id).append_once(
        f"loop-followup-disposition:{run_id}:{proposal_id}:{status}",
        "loop_followup_disposition",
        {
            "proposal_id": proposal_id,
            "run_id": run_id,
            "status": status,
            "detail": detail,
            "task_ids": task_ids or [],
        },
    )
