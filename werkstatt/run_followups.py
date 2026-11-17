"""Checkpoint reconciliation for explicitly accepted chat write requests."""
from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256
from typing import Any

from werkstatt.event_store import EventStore
from werkstatt.phase_state import PhaseState
from werkstatt.state import RunState


class FollowupReconciliationError(RuntimeError):
    """A confirmed follow-up could not be safely added to its run."""


def retain_followup_history(
    requests: list[dict[str, Any]], *, resolved_limit: int = 50,
) -> list[dict[str, Any]]:
    """Keep every unresolved request and only bound resolved history.

    A fixed tail slice can silently discard confirmed work when more than
    ``resolved_limit`` requests arrive before the next reconciliation. Unknown
    statuses are treated as unresolved so new states fail safe.
    """
    if resolved_limit < 0:
        raise ValueError("resolved_limit darf nicht negativ sein")
    if not isinstance(requests, list) or any(
        not isinstance(item, dict) for item in requests
    ):
        raise FollowupReconciliationError(
            "Follow-up-Ledger enthaelt ungueltige Eintraege",
        )
    resolved = [
        item for item in requests
        if isinstance(item, dict) and item.get("status") in {"applied", "rejected"}
    ]
    unresolved = [
        item for item in requests
        if isinstance(item, dict) and item.get("status") not in {"applied", "rejected"}
    ]
    retained_resolved = resolved[-resolved_limit:] if resolved_limit else []
    keep_ids = {id(item) for item in (*unresolved, *retained_resolved)}
    return [item for item in requests if id(item) in keep_ids]


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
        checkpoint["chat_followup_requests"] = retain_followup_history(updated)
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
    """Prepare one accepted follow-up for checkpointed role dispatch.

    Planning is intentionally not performed here. The durable record contains
    only the bounded child goal and parent-plan identity; the coordinator
    selects the needed roles on the next iteration.
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

    active = active_chat_followup(phase_state)
    if active is not None:
        restore_chat_followup_parent(state, phase_state)
        return False

    # Recover the narrow crash window after the phase record reached a terminal
    # state but before the RunRecord ledger CAS completed.
    terminal = {
        item.get("proposal_id"): item.get("status")
        for item in phase_state.data.get("chat_followup_checkpoints", [])
        if isinstance(item, dict)
        and item.get("status") in {"applied", "rejected"}
    } if isinstance(phase_state.data.get("chat_followup_checkpoints", []), list) else {}
    for item in requests:
        if not isinstance(item, dict) or item.get("status") not in {"planning", "pending"}:
            continue
        final_status = terminal.get(item.get("proposal_id"))
        if final_status in {"applied", "rejected"}:
            _append_checkpoint_status(store, project, run_id, str(item["proposal_id"]), final_status)
            _append_chat_disposition(
                item, project, run_id, final_status,
                "Folgeauftrag ist freigegeben und in den Task-Graph aufgenommen."
                if final_status == "applied" else
                "Der Folgeauftrag wurde im Plan-Gate abgelehnt.",
                task_ids=item.get("task_ids") if isinstance(item.get("task_ids"), list) else None,
            )

    handled_request = False
    for item in requests:
        if handled_request:
            break
        if not isinstance(item, dict):
            raise FollowupReconciliationError(
                "Follow-up-Ledger enthaelt einen ungueltigen Eintrag",
            )
        status = item.get("status")
        if status not in {"received", "planning", "pending", "applied", "rejected"}:
            raise FollowupReconciliationError(
                f"Follow-up hat unbekannten Status: {status!r}",
            )
        proposal_id = item.get("proposal_id")
        if isinstance(proposal_id, str) and status in {"applied", "rejected"}:
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
        if status != "received":
            continue
        request = item.get("request")
        if (
            not isinstance(request, str) or not request.strip()
            or not isinstance(proposal_id, str) or not proposal_id.strip()
        ):
            raise FollowupReconciliationError("Follow-up hat keinen Auftrag/Proposal")

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
            handled_request = True
            continue

        parent_goal = str(phase_data.get("aufgabe") or state.aufgabe)
        parent_fingerprint = phase_state.approved_plan_fingerprint()
        if not parent_fingerprint or not phase_state.approved_plan_is_current():
            raise FollowupReconciliationError(
                "Der freigegebene Hauptplan ist vor dem Chat-Folgeauftrag nicht aktuell",
            )
        checkpoints = phase_state.data.setdefault("chat_followup_checkpoints", [])
        if not isinstance(checkpoints, list):
            raise FollowupReconciliationError(
                "Chat-Follow-up-Checkpoint ist ungueltig",
            )
        checkpoint = {
            "schema_version": 1,
            "proposal_id": proposal_id,
            "run_id": run_id,
            "project": project,
            "parent_goal": parent_goal,
            "parent_goal_sha256": sha256(parent_goal.encode("utf-8")).hexdigest(),
            "parent_plan_sha256": parent_fingerprint,
            "planner_goal": request.strip(),
            "planner_goal_sha256": sha256(request.strip().encode("utf-8")).hexdigest(),
            "status": "roles_pending",
            "candidate": None,
            "candidate_sha256": None,
            "candidate_chars": 0,
        }
        checkpoints.append(checkpoint)
        phase_state.data["chat_followup_checkpoints"] = (
            _retain_chat_followup_checkpoints(checkpoints)
        )
        phase_state.save()
        _append_checkpoint_status(
            store, project, run_id, proposal_id, "planning",
        )
        restore_chat_followup_parent(state, phase_state)
        handled_request = True
    return False


def active_chat_followup(phase_state: PhaseState) -> dict[str, Any] | None:
    """Return the newest unfinished, durable chat-follow-up checkpoint."""
    records = phase_state.data.get("chat_followup_checkpoints")
    if not isinstance(records, list):
        return None
    return next((item for item in reversed(records) if (
        isinstance(item, dict)
        and item.get("status") in {"roles_pending", "candidate_pending_approval"}
        and isinstance(item.get("proposal_id"), str)
        and isinstance(item.get("planner_goal"), str)
    )), None)


def _retain_chat_followup_checkpoints(
    records: list[dict[str, Any]], *, resolved_limit: int = 50,
) -> list[dict[str, Any]]:
    """Bound terminal checkpoint history without dropping unfinished work."""
    if any(not isinstance(item, dict) for item in records):
        raise FollowupReconciliationError("Chat-Follow-up-Checkpoint ist ungueltig")
    terminal = [item for item in records if item.get("status") in {"applied", "rejected"}]
    unresolved = [item for item in records if item.get("status") not in {"applied", "rejected"}]
    retained = terminal[-resolved_limit:] if resolved_limit else []
    keep = {id(item) for item in (*unresolved, *retained)}
    return [item for item in records if id(item) in keep]


def restore_chat_followup_parent(state: RunState, phase_state: PhaseState) -> None:
    """Restore the approved parent goal and graph after child planning."""
    data = phase_state.data
    state.aufgabe = str(data.get("aufgabe") or "")
    state.tasks = [dict(item) for item in data.get("tasks", []) if isinstance(item, dict)]
    state.tests = list(data.get("tests", []))
    state.akzeptanzkriterien = list(data.get("akzeptanzkriterien", []))
    state.phasen = list(data.get("phasen", []))
    state.architect_prosa = str(data.get("architect_prosa") or "")
    state.criteria_replan_id = None


def prepare_chat_followup_roles(state: RunState, phase_state: PhaseState) -> dict[str, Any] | None:
    """Load an isolated follow-up goal for the planner role coordinator."""
    record = active_chat_followup(phase_state)
    if record is None or record.get("status") != "roles_pending":
        return None
    if (
        record.get("run_id") != phase_state.run_id
        or record.get("project") != phase_state.project_name
        or record.get("parent_goal") != phase_state.data.get("aufgabe")
        or record.get("parent_goal_sha256") != sha256(
            str(phase_state.data.get("aufgabe", "")).encode("utf-8"),
        ).hexdigest()
        or record.get("parent_plan_sha256") != phase_state.approved_plan_fingerprint()
        or not phase_state.approved_plan_is_current()
        or record.get("planner_goal_sha256") != sha256(
            str(record.get("planner_goal", "")).encode("utf-8"),
        ).hexdigest()
    ):
        raise FollowupReconciliationError("Chat-Folgeauftrag ist veraltet oder veraendert")
    restore_chat_followup_parent(state, phase_state)
    state.aufgabe = str(record["planner_goal"])
    state.tasks = []
    state.tests = []
    state.akzeptanzkriterien = []
    state.phasen = []
    state.architect_prosa = ""
    state.scout_auftrag = {}
    state.scout_api_auszug = {}
    state.explorer_context = {}
    state.explorer_findings = {}
    state.auftrag_bereits_erfuellt = False
    state.auftrag_bereits_erfuellt_bestaetigt = False
    state.auftrag_bereits_erfuellt_quelle = ""
    state.coordinator_setup_context_ready = False
    state.planner_role_artifacts = {}
    state.planning_response_cache = {}
    return record


def store_chat_followup_candidate(
    state: RunState, phase_state: PhaseState, *, run_id: str,
) -> str:
    """Persist a bounded candidate separately from the approved parent graph."""
    record = active_chat_followup(phase_state)
    if (
        record is None or record.get("status") != "roles_pending"
        or record.get("planner_goal") != state.aufgabe
        or record.get("run_id") != run_id
        or phase_state.run_id != run_id
        or record.get("parent_plan_sha256") != phase_state.approved_plan_fingerprint()
        or not phase_state.approved_plan_is_current()
    ):
        raise ValueError("Chat-Follow-up-Rollencheckpoint ist nicht aktuell")
    payload = {
        "schema_version": 1,
        "run_id": run_id,
        "project": phase_state.project_name,
        "proposal_id": record["proposal_id"],
        "planner_goal_sha256": record["planner_goal_sha256"],
        "tasks": deepcopy(state.tasks),
        "tests": deepcopy(state.tests or []),
        "criteria": deepcopy(state.akzeptanzkriterien or []),
        "phases": deepcopy(state.phasen or []),
        "architect_prose": state.architect_prosa or "",
        "preflight_findings": deepcopy(state.preflight_fehler or []),
    }
    try:
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise ValueError("Chat-Follow-up-Kandidat ist ungueltig") from exc
    if not payload["tasks"] or len(encoded) > 200_000:
        raise ValueError("Chat-Follow-up-Kandidat fehlt oder ist zu gross")
    digest = sha256(encoded).hexdigest()
    record.update({"candidate": payload, "candidate_sha256": digest,
                   "candidate_chars": len(encoded),
                   "status": "candidate_pending_approval"})
    phase_state.save()
    restore_chat_followup_parent(state, phase_state)
    return digest


def apply_chat_followup_candidate(
    state: RunState, phase_state: PhaseState, store: EventStore,
    project: str, run_id: str,
) -> bool:
    """Validate, plan-gate, and append a saved Chat follow-up candidate."""
    from werkstatt.audit import audit
    from werkstatt.gates import _human_gate_plan, _plan_gate

    record = active_chat_followup(phase_state)
    if record is None or record.get("status") != "candidate_pending_approval":
        return False
    restore_chat_followup_parent(state, phase_state)
    proposal_id = str(record["proposal_id"])
    already_added = [task for task in phase_state.data.get("tasks", [])
                     if isinstance(task, dict) and task.get("source_followup_id") == proposal_id]
    if already_added:
        ids = [str(task["id"]) for task in already_added]
        _append_checkpoint_status(store, project, run_id, proposal_id, "applied", task_ids=ids)
        record["status"] = "applied"
        phase_state.save()
        item = _followup_ledger_item(store, project, run_id, proposal_id)
        if item is not None:
            _append_chat_disposition(item, project, run_id, "applied",
                "Folgeauftrag ist freigegeben und in den Task-Graph aufgenommen.",
                task_ids=ids)
        return True
    payload = record.get("candidate")
    try:
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError):
        return False
    if (
        record.get("run_id") != run_id or record.get("project") != project
        or record.get("parent_goal") != phase_state.data.get("aufgabe")
        or record.get("parent_goal_sha256") != sha256(
            str(phase_state.data.get("aufgabe", "")).encode("utf-8"),
        ).hexdigest()
        or record.get("parent_plan_sha256") != phase_state.approved_plan_fingerprint()
        or not phase_state.approved_plan_is_current()
        or len(encoded) > 200_000 or len(encoded) != record.get("candidate_chars")
        or sha256(encoded).hexdigest() != record.get("candidate_sha256")
        or not isinstance(payload, dict) or payload.get("schema_version") != 1
        or payload.get("run_id") != run_id or payload.get("project") != project
        or payload.get("proposal_id") != proposal_id
        or payload.get("planner_goal_sha256") != record.get("planner_goal_sha256")
        or not isinstance(payload.get("tasks"), list) or not payload["tasks"]
        or any(not isinstance(item, dict) for item in payload["tasks"])
        or not isinstance(payload.get("tests"), list)
        or not isinstance(payload.get("criteria"), list)
        or not isinstance(payload.get("phases"), list)
        or any(not isinstance(item, dict) for item in payload["phases"])
        or not isinstance(payload.get("architect_prose"), str)
    ):
        return False
    addition = deepcopy(state)
    addition.aufgabe = str(record["planner_goal"])
    addition.tasks = deepcopy(payload["tasks"])
    addition.tests = deepcopy(payload["tests"])
    addition.akzeptanzkriterien = deepcopy(payload["criteria"])
    addition.phasen = deepcopy(payload["phases"])
    addition.architect_prosa = payload["architect_prose"]
    candidate, new_tasks, criteria, tests, phases = _extend_candidate(
        state, addition, proposal_id,
    )
    if not new_tasks or not _plan_gate(addition) or not _plan_gate(candidate):
        return False
    candidate.last_reject_kind = ""
    candidate.last_reject_reason = ""
    gate_result = _human_gate_plan(candidate, kontext="chat_followup")
    if gate_result == 2:
        raise FollowupReconciliationError("Chat-Folgeauftrag wartet auf Plan-Gate")
    if gate_result != 0:
        if getattr(candidate, "last_reject_kind", "") != "plan":
            raise FollowupReconciliationError("Chat-Folgeauftrag Plan-Gate blieb unbeantwortet")
        record["status"] = "rejected"
        phase_state.save()
        _append_checkpoint_status(store, project, run_id, proposal_id, "rejected")
        item = _followup_ledger_item(store, project, run_id, proposal_id)
        if item is not None:
            _append_chat_disposition(item, project, run_id, "rejected",
                "Der Folgeauftrag wurde im Plan-Gate abgelehnt.")
        return True
    ids = phase_state.append_followup_tasks(
        new_tasks, criteria=criteria, tests=tests, phases=phases,
        followup_id=proposal_id,
    )
    state.tasks, state.tests = candidate.tasks, candidate.tests
    state.akzeptanzkriterien, state.phasen = candidate.akzeptanzkriterien, candidate.phasen
    state.architect_prosa = candidate.architect_prosa
    record["status"] = "applied"
    phase_state.save()
    _append_checkpoint_status(store, project, run_id, proposal_id, "applied", task_ids=ids)
    item = _followup_ledger_item(store, project, run_id, proposal_id)
    if item is not None:
        _append_chat_disposition(item, project, run_id, "applied",
            f"Folgeauftrag ist freigegeben und in den Task-Graph aufgenommen ({len(ids)} Task(s)).",
            task_ids=ids)
    audit("loop_chat_followup_applied", {
        "proposal_id": proposal_id, "task_ids": ids,
        "decision_summary": "Separater Rollen-Kandidat wurde geprueft und am Plan-Gate freigegeben.",
        "next_step": "Die neuen Tasks werden am sicheren Checkpoint ausgefuehrt.",
    }, state.project_dir, project, run_id=run_id,
       audit_id=f"RUN-{run_id}-CHAT-FOLLOWUP-APPLIED-{sha256(proposal_id.encode()).hexdigest()[:10]}")
    return True


def _followup_ledger_item(
    store: EventStore, project: str, run_id: str, proposal_id: str,
) -> dict[str, Any] | None:
    record = store.get_run_record(project, run_id)
    checkpoint = record.get("checkpoint") if isinstance(record, dict) else None
    requests = checkpoint.get("chat_followup_requests") if isinstance(checkpoint, dict) else None
    if not isinstance(requests, list):
        return None
    return next((dict(item) for item in requests if (
        isinstance(item, dict) and item.get("proposal_id") == proposal_id
    )), None)


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
