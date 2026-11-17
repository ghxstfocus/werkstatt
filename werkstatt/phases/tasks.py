"""Checkpoint task executor and evidence-based task recovery."""
from __future__ import annotations

import sqlite3
import time
from hashlib import sha256
from pathlib import Path
from typing import Any

from werkstatt.checkpoint_coordinator import (
    choose_task_checkpoint_action as _checkpoint_decision_payload,
)
from werkstatt.event_store import EventStore
from werkstatt.render import (
    group_end,
    group_start,
    task,
    task_done,
    task_ok,
    task_started,
)
from werkstatt.state import RunState, check_run_lease

from ._common import (
    _apply_one_patch,
    _call_hook,
    _delete_ziel_erlaubt,
    _get_git_diff_for_hook,
    _reset_task_state,
    _reviewer_rejected_payload,
    _ruff_fix_changed,
    _run_with_progress,
    _task_ende,
    _verify_patches,
    _with_spinner,
    audit,
    run_builder,
    run_reviewer,
)


def _audit_task_ok(
    transitioned: bool,
    task_id: str,
    task_name: str,
    project_dir: Path,
    project_name: str,
    *,
    via: str | None = None,
) -> None:
    """Emit a timeline success only after a new done transition."""
    if not transitioned:
        return
    payload = {
        "task_id": task_id,
        "name": task_name,
        "status": "done",
        "result_summary": "Task abgeschlossen und im Phase-State als erledigt markiert.",
        "evidence": ["Phase-State: done"],
    }
    if via:
        payload["via"] = via
    audit("loop_task_ok", payload, project_dir, project_name)


def _read_dependency_sources(
    state: RunState,
    phase_state: Any,
    task: dict[str, Any],
) -> tuple[list[dict[str, Any]], str]:
    """Build exact current excerpts from this task's completed read ancestors."""
    dependencies = task.get("dependencies")
    if not isinstance(dependencies, list):
        return [], "task_dependencies_invalid"
    by_id = {
        record.get("id"): record
        for record in phase_state.data.get("tasks", [])
        if isinstance(record, dict) and isinstance(record.get("id"), str)
    }
    ordered: list[dict[str, Any]] = []
    seen: set[str] = set()

    def visit(task_id: object) -> bool:
        if not isinstance(task_id, str) or task_id in seen:
            return True
        seen.add(task_id)
        dependency = by_id.get(task_id)
        if not isinstance(dependency, dict):
            return False
        ancestors = dependency.get("dependencies") or []
        if not isinstance(ancestors, list):
            return False
        if not all(visit(ancestor) for ancestor in ancestors):
            return False
        if dependency.get("action") == "read":
            ordered.append(dependency)
        return True

    if not all(visit(task_id) for task_id in dependencies):
        return [], "read_dependency_missing"
    if not ordered:
        return [], ""

    from werkstatt.explorer import (
        _datei_inhalt_mit_fundstellen,
        _source_content_tokens,
    )

    recorder = getattr(phase_state, "task_read_evidence_is_current", None)
    if not callable(recorder):
        return [], "read_dependency_evidence_unavailable"
    task_text = " ".join((
        str(task.get("name", "")), str(task.get("description", "")),
    ))
    search_terms = sorted(_source_content_tokens(task_text))[:40]
    sources: list[dict[str, Any]] = []
    for dependency in ordered:
        dependency_id = dependency.get("id")
        evidence = dependency.get("read_evidence")
        if (
            not isinstance(dependency_id, str)
            or recorder(dependency_id, evidence) is not True
            or not isinstance(evidence, dict)
        ):
            return [], "read_dependency_evidence_stale"
        files = evidence.get("files")
        if not isinstance(files, dict):
            return [], "read_dependency_evidence_invalid"
        for relative_path in evidence.get("task_files", []):
            recorded = files.get(relative_path)
            if not isinstance(recorded, dict):
                return [], "read_dependency_file_evidence_missing"
            excerpt = _datei_inhalt_mit_fundstellen(
                Path(state.project_dir), relative_path, search_terms,
            )
            if (
                excerpt.get("source_sha256") != recorded.get("sha256")
                or excerpt.get("reason") == "source_unavailable"
            ):
                return [], "read_dependency_source_changed_or_unavailable"
            sources.append({
                "read_task_id": dependency_id,
                "file": relative_path,
                "source_sha256": recorded.get("sha256"),
                "source_bytes": recorded.get("bytes"),
                "line_ranges": excerpt.get("line_ranges", []),
                "total_lines": excerpt.get("total_lines"),
                "complete": excerpt.get("complete") is True,
                "excerpt": excerpt.get("text", ""),
            })
    return sources, ""


# Compatibility export; policy lives with the checkpoint coordinator.

def _persist_run_checkpoint(
    store: EventStore,
    project_name: str,
    run_id: str,
    phase_state: Any,
    next_task: dict[str, Any] | None,
    *,
    run_state: RunState | None = None,
) -> None:
    """Persist task-boundary state and acknowledge only observed chat notices."""
    if run_state is not None:
        check_run_lease(run_state)
    record = store.get_run_record(project_name, run_id)
    if record is None:
        return

    worker_id = f"loop:{run_id}"
    notices: list[dict[str, object]] = []
    claimed: list[dict[str, Any]] = []
    for _ in range(20):
        message = store.claim_run_message(
            project_name, run_id, worker_id, lease_seconds=120,
            kind="job_notice",
        )
        if message is None:
            break
        if message["kind"] != "job_notice":
            break
        claimed.append(message)
        payload = message["payload"]
        notices.append({
            "seq": message["seq"],
            "message_id": message["message_id"],
            "job_id": payload.get("job_id"),
            "mode": payload.get("mode"),
            "session_id": payload.get("session_id"),
            "context_seq": payload.get("context_seq"),
        })

    job_results: list[dict[str, object]] = []
    for _ in range(20):
        message = store.claim_run_message(
            project_name, run_id, worker_id, lease_seconds=120,
            kind="job_result_notice",
        )
        if message is None:
            break
        claimed.append(message)
        payload = message["payload"]
        job_results.append({
            "seq": message["seq"],
            "message_id": message["message_id"],
            "job_id": payload.get("job_id"),
            "mode": payload.get("mode"),
            "session_id": payload.get("session_id"),
            "context_seq": payload.get("context_seq"),
            "state": payload.get("state"),
            "answer_sha256": payload.get("answer_sha256"),
            "error_sha256": payload.get("error_sha256"),
        })

    followups: list[dict[str, object]] = []
    for _ in range(20):
        message = store.claim_run_message(
            project_name, run_id, worker_id, lease_seconds=120,
            kind="chat_followup_request",
        )
        if message is None:
            break
        payload = message["payload"]
        if (
            payload.get("project") != project_name
            or payload.get("parent_run_id") != run_id
            or not isinstance(payload.get("session_id"), str)
            or not isinstance(payload.get("proposal_id"), str)
            or payload.get("base_commit") != record.get("base_commit")
        ):
            raise RuntimeError(
                f"Chat-Folgeauftrag {message['message_id']} passt nicht "
                "zum gebundenen Projekt, Run oder Basis-Commit",
            )
        claimed.append(message)
        request = payload.get("request", "")
        if not isinstance(request, str):
            raise TypeError(
                f"Chat-Folgeauftrag {message['message_id']} hat keinen "
                "gültigen Text",
            )
        if not request.strip():
            raise ValueError(
                f"Chat-Folgeauftrag {message['message_id']} hat leeren Text",
            )
        followups.append({
            "seq": message["seq"],
            "message_id": message["message_id"],
            "proposal_id": payload["proposal_id"],
            "session_id": payload["session_id"],
            "request": request,
            "op_id": payload.get("op_id"),
            "base_commit": payload.get("base_commit"),
            "queued_at_checkpoint_version": payload.get("checkpoint_version"),
            "status": "received",
        })

    checkpoint = dict(record["checkpoint"])
    prior_followups = checkpoint.get("chat_followup_requests", [])
    if not isinstance(prior_followups, list):
        raise TypeError("Follow-up-Ledger im Checkpoint ist ungueltig")
    prior_followup_seqs = {
        item.get("seq") for item in prior_followups
        if isinstance(item, dict) and isinstance(item.get("seq"), int)
    }
    new_followups = [
        item for item in followups
        if isinstance(item.get("seq"), int)
        and item.get("seq") not in prior_followup_seqs
    ]
    for item in new_followups:
        seq = item["seq"]
        audit_item = {
            key: value for key, value in item.items() if key != "request"
        }
        audit_item["request_sha256"] = sha256(
            str(item["request"]).encode("utf-8"),
        ).hexdigest()
        audit_result = audit(
            "loop_chat_followup_queued",
            {
                **audit_item,
                "result_summary": (
                    "Ein bestätigter Chat-Folgeauftrag wurde am sicheren "
                    "Checkpoint sichtbar gemacht."
                ),
                "decision_summary": (
                    "Das aktive Hauptziel bleibt bestehen; dieser Eintrag "
                    "wird noch nicht automatisch in den Task-Graph übernommen."
                ),
                "next_step": (
                    "Anliegen, Abhängigkeiten und Freigabeumfang mit dem "
                    "aktiven Ziel abgleichen, bevor Tasks geändert werden."
                ),
            },
            run_state.project_dir if run_state is not None else Path.cwd(),
            project_name,
            run_id=run_id,
            audit_id=f"RUN-{run_id}-CHAT-FOLLOWUP-{seq}",
        )
        if audit_result is False:
            raise RuntimeError(
                f"Chat-Folgeauftrag {item.get('proposal_id')} konnte "
                "nicht auditiert werden",
            )
    from werkstatt.run_followups import retain_followup_history

    checkpoint["chat_followup_requests"] = retain_followup_history(
        prior_followups + new_followups,
    )
    # The legacy shared cursor could skip non-job inbox messages. Consumers
    # now keep independent cursors, so do not expose that ambiguous offset.
    checkpoint.pop("inbox_offset", None)
    try:
        notice_offset = int(checkpoint.get("job_notice_offset", 0))
    except (TypeError, ValueError):
        notice_offset = 0
    prior_notices = checkpoint.get("job_notices", [])
    if not isinstance(prior_notices, list):
        prior_notices = []
    prior_notice_seqs = {
        item.get("seq") for item in prior_notices
        if isinstance(item, dict) and isinstance(item.get("seq"), int)
    }
    # This consumer handles job notices only. Its cursor must not advance the
    # shared inbox cursor past questions or controls that another consumer has
    # not handled. Prior seq values also migrate checkpoints written by the
    # previous shared-offset implementation without replaying stored notices.
    snapshot_by_seq: dict[int, dict[str, object]] = {}
    snapshot_errors: dict[int, str] = {}
    if run_state is not None and claimed:
        from werkstatt.chat_jobs import ChatJobStore, _db_path
        from werkstatt.run_snapshot import SnapshotError, create_project_snapshot

        jobs = ChatJobStore(_db_path(project_name))
        for message in claimed:
            payload = message["payload"]
            job_id = payload.get("job_id")
            seq = message.get("seq")
            if not isinstance(job_id, str) or not isinstance(seq, int):
                continue
            job = jobs.get(job_id)
            if job is None:
                continue
            if (
                job.get("run_id") != run_id
                or job.get("project") != project_name
                or job.get("state") != "queued"
            ):
                continue
            try:
                source = Path(run_state.project_dir).resolve()
                snapshot = create_project_snapshot(
                    source, project_name, run_id, job_id,
                )
                if not jobs.set_run_snapshot(
                    job_id,
                    source,
                    snapshot.path,
                    snapshot.head,
                    snapshot.fingerprint,
                ):
                    raise SnapshotError(
                        "Chatjob konnte den Checkpoint-Snapshot nicht binden.",
                    )
                snapshot_by_seq[seq] = {
                    "snapshot_path": str(snapshot.path),
                    "snapshot_head": snapshot.head,
                    "snapshot_fingerprint": snapshot.fingerprint,
                }
            except (OSError, RuntimeError, ValueError, sqlite3.Error) as exc:
                reason = f"Run-Snapshot am sicheren Checkpoint fehlgeschlagen: {exc}"
                jobs.fail_queued(job_id, reason)
                snapshot_errors[seq] = reason

    for notice in notices:
        seq = notice.get("seq")
        if isinstance(seq, int):
            notice.update(snapshot_by_seq.get(seq, {}))
            if seq in snapshot_errors:
                notice["snapshot_error"] = snapshot_errors[seq]

    notices_above_offset: list[dict[str, object]] = []
    for notice in notices:
        seq = notice.get("seq")
        if (
            isinstance(seq, int)
            and seq > notice_offset
            and seq not in prior_notice_seqs
        ):
            notices_above_offset.append(notice)
    notices = notices_above_offset

    # Ein Hintergrundjob ist eine neue Eingabe in den laufenden Run. Er wird
    # am sicheren Punkt sichtbar gemacht, ohne Ziel oder Task-Graph implizit
    # zu aendern. Die stabile Audit-ID macht Wiederholungen nach einem Crash
    # zwischen Audit und Checkpoint in der Projektion idempotent.
    for notice in notices:
        seq = notice.get("seq")
        audit_result = audit(
            "loop_chat_job_observed",
            {
                "message_id": notice.get("message_id"),
                "job_id": notice.get("job_id"),
                "mode": notice.get("mode"),
                "session_id": notice.get("session_id"),
                "context_seq": notice.get("context_seq"),
                "result_summary": (
                    "Der laufende Run hat einen parallelen Chat-Job am "
                    "sicheren Checkpoint erkannt."
                ),
                "decision_summary": (
                    "Das Run-Hauptziel bleibt unveraendert; der Lese- oder "
                    "Diagnosejob wird separat in seiner Chat-Session bearbeitet."
                ),
                "evidence": [
                    f"Chat-Job {notice.get('job_id') or '?'}",
                    f"Modus: {notice.get('mode') or 'unbekannt'}",
                    f"Run-Inbox-Sequenz: {seq}",
                ],
                "next_step": (
                    "Aktiven Task-Graph fortsetzen und das Chat-Ergebnis "
                    "bei seiner Rueckkehr gegen das Run-Ziel abgleichen."
                ),
            },
            run_state.project_dir if run_state is not None else Path.cwd(),
            project_name,
            run_id=run_id,
            audit_id=f"RUN-{run_id}-CHAT-{seq}",
        )
        if audit_result is False:
            raise RuntimeError(
                f"Chat-Job {notice.get('job_id')} konnte nicht auditiert werden",
            )

    checkpoint["job_notices"] = (prior_notices + notices)[-50:]
    try:
        result_offset = int(checkpoint.get("job_result_offset", 0))
    except (TypeError, ValueError):
        result_offset = 0
    prior_results = checkpoint.get("job_results", [])
    if not isinstance(prior_results, list):
        prior_results = []
    prior_result_seqs = {
        item.get("seq") for item in prior_results
        if isinstance(item, dict) and isinstance(item.get("seq"), int)
    }
    results_above_offset: list[dict[str, object]] = []
    result_seqs_above_offset: list[int] = []
    for result in job_results:
        seq = result.get("seq")
        if (
            isinstance(seq, int)
            and seq > result_offset
            and seq not in prior_result_seqs
        ):
            results_above_offset.append(result)
            result_seqs_above_offset.append(seq)
    for result in results_above_offset:
        seq = result.get("seq")
        audit_result = audit(
            "loop_chat_job_result_observed",
            {
                "job_id": result.get("job_id"),
                "mode": result.get("mode"),
                "session_id": result.get("session_id"),
                "context_seq": result.get("context_seq"),
                "state": result.get("state"),
                "answer_sha256": result.get("answer_sha256"),
                "error_sha256": result.get("error_sha256"),
                "result_summary": (
                    "Ein paralleler Chat-Job ist beendet; sein Ergebnis bleibt "
                    "in derselben Chat-Session abrufbar."
                ),
                "decision_summary": (
                    "Der Lauf uebernimmt keine Ziel- oder Diff-Aenderung aus "
                    "Job-Metadaten; das freigegebene Hauptziel bleibt erhalten."
                ),
                "evidence": [
                    f"Chat-Job {result.get('job_id') or '?'}",
                    f"Status: {result.get('state') or 'unbekannt'}",
                    f"Run-Inbox-Sequenz: {seq}",
                ],
                "next_step": (
                    "Freigegebene Arbeit fortsetzen; den Chat-Ergebnisinhalt "
                    "bei einer tatsaechlichen Ziel- oder Scope-Aenderung "
                    "gesondert abstimmen."
                ),
            },
            run_state.project_dir if run_state is not None else Path.cwd(),
            project_name,
            run_id=run_id,
            audit_id=f"RUN-{run_id}-CHAT-RESULT-{seq}",
        )
        if audit_result is False:
            raise RuntimeError(
                f"Chat-Job-Ergebnis {result.get('job_id')} "
                "konnte nicht auditiert werden",
            )
    checkpoint["job_results"] = (prior_results + results_above_offset)[-50:]
    if result_seqs_above_offset:
        checkpoint["job_result_offset"] = max(
            result_offset,
            max(result_seqs_above_offset),
        )
    checkpoint["safe_point"] = {
        "kind": "coordinator_checkpoint",
        "next_task_id": next_task.get("id") if next_task else None,
        "completed_task_ids": [
            task_record.get("id")
            for task_record in phase_state.data.get("tasks", [])
            if isinstance(task_record, dict)
            and task_record.get("status") == "done"
        ],
    }
    if claimed:
        checkpoint["job_notice_offset"] = max(
            notice_offset,
            max(
                (int(message["seq"]) for message in claimed
                 if message["kind"] == "job_notice"),
                default=notice_offset,
            ),
        )
        checkpoint["job_result_offset"] = max(
            result_offset,
            max(
                (int(message["seq"]) for message in claimed
                 if message["kind"] == "job_result_notice"),
                default=result_offset,
            ),
        )
    if run_state is not None:
        check_run_lease(run_state)
    store.update_run_checkpoint(
        project_name,
        run_id,
        checkpoint,
        expected_version=record["checkpoint_version"],
    )
    # Reflect durable follow-up intake in the originating chat. The event key
    # makes checkpoint retries safe, while the checkpoint remains authoritative.
    if run_state is not None:
        from werkstatt.chat_session import ChatSession

        for item in checkpoint["chat_followup_requests"]:
            if not isinstance(item, dict) or item.get("status") != "received":
                continue
            session_id = item.get("session_id")
            proposal_id = item.get("proposal_id")
            if not isinstance(session_id, str) or not isinstance(proposal_id, str):
                continue
            ChatSession(project_name, session_id).append_once(
                f"loop-followup-checkpoint:{run_id}:{proposal_id}",
                "loop_followup_checkpointed",
                {
                    "proposal_id": proposal_id,
                    "run_id": run_id,
                    "status": "received",
                    "detail": (
                        "Der Loop hat den Folgeauftrag am sicheren Checkpoint "
                        "aufgenommen. Die inhaltliche Einordnung steht noch "
                        "aus; Hauptziel und laufende Tasks bleiben unverändert."
                    ),
                },
            )
    for message in claimed:
        if run_state is not None:
            check_run_lease(run_state)
        if not store.acknowledge_run_message(
            message["seq"], worker_id, message["fencing_token"],
        ):
            raise RuntimeError(
                f"Run-Inbox-Lease verloren: {message['message_id']}",
            )
    if run_state is not None and claimed:
        from werkstatt.chat_jobs import resume_chat_jobs

        resume_chat_jobs(
            project_name,
            Path(run_state.project_dir),
        )


def _phase_tasks_loop(
    state: RunState,
    phase_state,
    task_index_offset: int = 0,
    *,
    coordinator_decision: dict[str, Any] | None = None,
) -> tuple[int, int, list]:
    """Execute one coordinator-selected task checkpoint.

    Each call may execute at most one worker action. The outer coordinator
    must reassess the persisted evidence before selecting another action.
    Return ``(rc, tasks_ok, tasks)``; the caller persists failures and
    dispatches again from the resulting checkpoint.
    """
    if task_index_offset < 0:
        raise ValueError("task_index_offset must be non-negative")
    pd = state.project_dir
    pn = state.project_name
    store = EventStore()

    # OP-381g: loop_phase-Marker fuer Timeline-Gruppierung.
    # Ohne diesen Marker landen alle Builder/Verify/Reflection/Reviewer-
    # Events unter dem letzten loop_phase-Knoten (Plan) statt in einem
    # eigenen "Build"-Knoten. Live-Bug 2026-11-09: 104 children unter
    # "Plan", Timeline-Gruppierung kaputt (aggregate_timeline schliesst
    # Knoten nur bei naechstem loop_phase-Event, siehe inspector.py Z.965).
    audit("loop_phase", {"phase": "build", "status": "start"}, pd, pn)

    # The compatibility executor processes the selected task and returns at
    # the next durable boundary for coordinator reassessment.
    tasks = state.tasks
    # Resume after a final-verify failure may find every planned task already
    # done. Count persisted work so finalization can re-run verification instead
    # of misclassifying the resumed run as having done no work.
    tasks_ok = sum(
        1 for task_record in phase_state.data.get("tasks", [])
        if isinstance(task_record, dict) and task_record.get("status") == "done"
    )
    state.tasks_ok_counter = tasks_ok
    i = task_index_offset
    task_steps = 0
    if coordinator_decision is None:
        audit(
            "loop_failed",
            {
                "reason": "task_checkpoint_requires_coordinator_decision",
                "executor": "task_checkpoint",
            },
            pd,
            pn,
        )
        phase_state.save()
        return 1, tasks_ok, tasks
    from werkstatt.agent import _enforce_run_budget
    # M-473: while-Loop statt for. Nach ADaPT-Split wird die
    # Schleife neu gestartet, damit Sub-Tasks gebaut werden.
    while True:
        check_run_lease(state)
        if _enforce_run_budget(state):
            phase_state.save()
            return 1, tasks_ok, tasks
        from werkstatt.audit import get_run_id
        run_id = get_run_id()
        if run_id:
            next_task = phase_state.get_next_task()
        else:
            next_task = phase_state.get_next_task()
        decision_payload = _checkpoint_decision_payload(
            phase_state, next_task, state=state,
        )
        if run_id:
            checkpoint_record = store.get_run_record(pn, run_id)
            checkpoint_version = (
                checkpoint_record.get("checkpoint_version")
                if checkpoint_record is not None else None
            )
            decision_payload["checkpoint_version"] = checkpoint_version
            decision_payload["evidence_source"] = (
                "PhaseState.progress + PhaseState.criteria_progress"
            )
            decision_payload["run_id"] = run_id
            decision_payload["checkpoint_id"] = (
                f"{run_id}:{checkpoint_version}"
                if checkpoint_version is not None else run_id
            )
            audit_result = audit(
                "loop_checkpoint_decision",
                decision_payload,
                pd,
                pn,
            )
            if audit_result is False:
                phase_state.save()
                return 1, tasks_ok, tasks
        fresh_decision = decision_payload.get("decision")
        fresh_action = {
            "execute_planned_task": "execute_task_checkpoint",
            "verify_task_checkpoint": "verify_task_checkpoint",
            "review_task_checkpoint": "review_task_checkpoint",
            "complete_task_checkpoint": "complete_task_checkpoint",
            "recover_verify_failure_checkpoint": "recover_verify_failure_checkpoint",
            "reject_stale_verify_failure_checkpoint": "reject_stale_verify_failure_checkpoint",
            "resolve_blocked_graph": "resolve_task_graph",
            "replan_unassigned_criteria": "replan_unassigned_criteria",
            "replan_failed_criteria": "replan_failed_criteria",
        }.get(fresh_decision) if isinstance(fresh_decision, str) else None
        dispatch_matches = (
            coordinator_decision.get("coordinator_action") == fresh_action
            and coordinator_decision.get("decision")
            == decision_payload.get("decision")
            and coordinator_decision.get("next_task_id")
            == decision_payload.get("next_task_id")
            and coordinator_decision.get("next_executor")
            == decision_payload.get("next_executor")
        )
        if not dispatch_matches:
            audit(
                "loop_coordinator_dispatch_stale",
                {
                    "requested_action": coordinator_decision.get(
                        "coordinator_action",
                    ),
                    "current_action": fresh_action,
                    "requested_task_id": coordinator_decision.get(
                        "next_task_id",
                    ),
                    "current_task_id": decision_payload.get(
                        "next_task_id",
                    ),
                },
                pd,
                pn,
            )
            phase_state.save()
            state.coordinator_dispatch_stale = True
            return 0, tasks_ok, tasks
        # The run coordinator owns the action choice. This worker only
        # revalidates that choice against the latest persisted checkpoint
        # after follow-up reconciliation, then executes the exact task.
        decision_payload = coordinator_decision

        decision = decision_payload["decision"]
        if task_steps >= 1:
            # A checkpoint may now request a different role (verify, review,
            # or recovery) after the previous action. Do not run that second
            # role under the stale coordinator decision.
            phase_state.save()
            return 0, tasks_ok, tasks
        if decision == "reject_invalid_task_action":
            audit(
                "state_contract_violation",
                {
                    "invariant": "checkpoint_action_has_registered_executor",
                    "decision": decision,
                    "task_id": next_task.get("id") if next_task else None,
                    "action": next_task.get("action") if next_task else None,
                },
                pd,
                pn,
            )
            phase_state.save()
            return 1, tasks_ok, tasks
        if decision in {
            "replan_unassigned_criteria",
            "replan_failed_criteria",
        }:
            from werkstatt.criteria_replan import replan_unassigned_criteria

            if not replan_unassigned_criteria(state, phase_state):
                phase_state.save()
                return 1, tasks_ok, tasks
            tasks = [
                task for task in state.tasks
                if not (
                    isinstance(task, dict)
                    and task.get("status") == "superseded"
                )
            ]
            tasks_ok = phase_state.progress().get("done", 0)
            # Criteria recovery is a coordination action, never a nested
            # planner call. Return to the run coordinator even for legacy
            # callers that requested an unbounded task loop.
            phase_state.save()
            return 0, tasks_ok, tasks
        if decision == "resolve_blocked_graph":
            # OP-163: unerfuellte Deps -> als blocked markieren.
            _pending_after = [
                _t_b for _t_b in phase_state.data.get("tasks", [])
                if isinstance(_t_b, dict)
                and _t_b.get("status") == "pending"
            ]
            for _t_b in _pending_after:
                _unmet = phase_state._unmet_dependencies(_t_b)
                _tid_b = _t_b.get("id", "?")
                phase_state.mark_blocked(
                    _tid_b, grund="deps:" + ",".join(_unmet),
                )
                audit("loop_task_blocked",
                      {"task_id": _tid_b, "unmet_deps": _unmet},
                      pd, pn)
            if _pending_after:
                phase_state.save()
            break
        if decision not in {
            "execute_planned_task",
            "verify_task_checkpoint",
            "review_task_checkpoint",
            "complete_task_checkpoint",
            "recover_verify_failure_checkpoint",
            "reject_stale_verify_failure_checkpoint",
        }:
            break
        if next_task is None:
            audit(
                "state_contract_violation",
                {
                    "invariant": "checkpoint_task_selection_consistent",
                    "decision": decision,
                    "reason": "execute_planned_task_without_task_node",
                },
                pd,
                pn,
            )
            phase_state.save()
            return 1, tasks_ok, tasks
        next_executor = decision_payload.get("next_executor")
        if next_executor not in {
            "read_only_task", "verify_only", "builder", "reviewer",
            "task_completion", "verify_recovery",
        }:
            audit(
                "state_contract_violation",
                {
                    "invariant": "checkpoint_executor_is_registered",
                    "decision": decision,
                    "task_id": next_task.get("id"),
                    "executor": next_executor,
                },
                pd,
                pn,
            )
            phase_state.save()
            return 1, tasks_ok, tasks
        task_obj = dict(next_task)  # Ephemere Handoff-Daten nicht persistieren.
        _verification_only = task_obj.get("verification_only") is True
        _review_checkpoint_action = decision in {
            "review_task_checkpoint", "complete_task_checkpoint",
        }
        _verify_recovery_action = decision == "recover_verify_failure_checkpoint"
        if not _verification_only and not _review_checkpoint_action and not _verify_recovery_action:
            i += 1
        task_steps += 1
        task_id = next_task.get("id", f"t{i}")
        phase_state.mark_running(task_id)
        task_name = task_obj.get("name", f"Task {i}") if isinstance(task_obj, dict) else str(task_obj)
        group_start(f"Task {i}/?: {task_name}")
        try:
            task_started(i, len(tasks), task_name)
        except Exception:
            pass
        _t_task = time.monotonic()
        task(i, len(tasks), task_name)
        audit("loop_task_start", {"task_id": task_id, "name": task_name}, pd, pn)

        # Builder role for the coordinator-selected write task.
        state.aktuelle_task = task_obj
        # OP-166: per-Task-State reset, sonst leaken Fehler aus
        # vorherigen Tasks in Reflection (Loop-Test-4 t7-Bug).
        _reset_task_state(state)

        if decision == "reject_stale_verify_failure_checkpoint":
            phase_state.mark_human_review(
                task_id,
                grund="verify_failure_checkpoint_stale",
            )
            audit(
                "loop_verify_recovery_checkpoint_rejected",
                {"task_id": task_id, "reason": "stale_file_evidence"},
                pd, pn,
            )
            group_end()
            return 0, tasks_ok, tasks

        if decision == "recover_verify_failure_checkpoint":
            from werkstatt.roles.verify_recovery import run_verify_recovery

            audit(
                "loop_verify_recovery_started",
                {"task_id": task_id},
                pd, pn,
            )
            recovery = run_verify_recovery(state, phase_state, task_id)
            if recovery.get("status") != "repair_handoff":
                phase_state.mark_human_review(
                    task_id,
                    grund=str(recovery.get("reason") or "verify_recovery_failed"),
                )
            audit(
                "loop_verify_recovery_result",
                {"task_id": task_id, "status": recovery.get("status"),
                 "reason": recovery.get("reason"),
                 "stage_ids": recovery.get("stage_ids", [])},
                pd, pn,
            )
            group_end()
            return 0, tasks_ok, tasks

        if decision in {
            "review_task_checkpoint", "complete_task_checkpoint",
        }:
            from werkstatt.review_dispatch import reviewer_dispatch_decision
            from werkstatt.reviewer import _get_git_diff
            from werkstatt.roles.complete_task import (
                TaskCompletionServices,
                complete_task_checkpoint,
            )

            completion = complete_task_checkpoint(
                state,
                phase_state,
                task_obj,
                task_id=str(task_id),
                task_name=task_name,
                task_index=i,
                decision=decision,
                decision_payload=decision_payload,
                services=TaskCompletionServices(
                    audit_call=audit,
                    get_git_diff=_get_git_diff,
                    reviewer_dispatch_decision=reviewer_dispatch_decision,
                    review=lambda current_state, task_index: _with_spinner(
                        f"Reviewer t{task_index}",
                        lambda: run_reviewer(current_state),
                    ),
                    task_end=_task_ende,
                    audit_task_ok=_audit_task_ok,
                    reviewer_rejected_payload=_reviewer_rejected_payload,
                    check_lease=check_run_lease,
                ),
            )
            if completion.status == "stale":
                phase_state.save()
                state.coordinator_dispatch_stale = True
                group_end()
                return 0, tasks_ok, tasks
            if completion.status == "failed":
                phase_state.save()
                group_end()
                return 1, tasks_ok, tasks
            if completion.status == "review_rejected":
                group_end()
                return 0, tasks_ok, tasks

            tasks_ok += completion.tasks_ok_delta
            state.tasks_ok_counter = tasks_ok
            group_end()
            return 0, tasks_ok, tasks

        if next_executor == "builder":
            read_sources, read_context_error = _read_dependency_sources(
                state, phase_state, task_obj,
            )
            if read_context_error:
                queue_stale_dependencies = getattr(
                    phase_state, "queue_stale_read_dependencies", None,
                )
                stale_dependencies = (
                    queue_stale_dependencies(task_id)
                    if callable(queue_stale_dependencies) else []
                )
                if stale_dependencies:
                    phase_state.update_task(task_id, "pending")
                    phase_state.save()
                    audit(
                        "loop_task_read_dependency_stale",
                        {"task_id": task_id,
                         "read_task_ids": stale_dependencies,
                         "reason": read_context_error},
                        pd, pn,
                    )
                    group_end()
                    return 0, tasks_ok, tasks
                audit(
                    "loop_task_read_dependency_failed",
                    {"task_id": task_id, "reason": read_context_error},
                    pd, pn,
                )
                _task_ende(
                    state, phase_state, task_id, ok=False, name=task_name,
                    failure=read_context_error,
                )
                group_end()
                continue
            if read_sources:
                task_obj["checkpoint_read_source_evidence"] = read_sources
                audit(
                    "loop_task_read_context",
                    {
                        "task_id": task_id,
                        "sources": [
                            {
                                "read_task_id": item["read_task_id"],
                                "file": item["file"],
                                "source_sha256": item["source_sha256"],
                                "line_ranges": item["line_ranges"],
                                "complete": item["complete"],
                            }
                            for item in read_sources
                        ],
                    },
                    pd, pn,
                )

        # M-306d Fix 1: Pro-Task action-Check. read-only Tasks
        # read their approved source scope and persist exact provenance.
        if next_executor == "read_only_task":
            from werkstatt.roles.read_only_task import read_task_scope_evidence

            read_evidence, read_error = read_task_scope_evidence(
                pd, task_obj.get("task_files"),
            )
            if not read_error:
                recorder = getattr(
                    phase_state, "record_task_read_evidence", None,
                )
                if not callable(recorder) or recorder(
                    task_id, read_evidence,
                ) is not True:
                    read_error = "read_task_evidence_not_persisted"
            if read_error:
                audit(
                    "loop_task_read_only",
                    {"task_id": task_id, "name": task_name,
                     "status": "failed", "reason": read_error},
                    pd, pn,
                )
                _task_ende(
                    state, phase_state, task_id, ok=False, name=task_name,
                    failure=read_error,
                )
                group_end()
                continue
            audit(
                "loop_task_read_only",
                {"task_id": task_id, "name": task_name,
                 "status": "read", "source_evidence": read_evidence},
                pd, pn,
            )
            _el_task = time.monotonic() - _t_task
            task_ok(i, len(tasks), elapsed_s=_el_task)
            group_end()
            tasks_ok += 1
            state.tasks_ok_counter = tasks_ok
            _audit_task_ok(
                _task_ende(state, phase_state, task_id, ok=True, name=task_name),
                task_id, task_name, pd, pn,
            )
            continue

        # Verify-Task: deterministische Pruefung ohne unnoetigen Reviewer-LLM.
        if next_executor == "verify_only":
            from werkstatt.roles.verify_task import (
                run_task_verify_checkpoint,
                verify_failure_detail,
            )
            _verify_result = run_task_verify_checkpoint(
                state,
                phase_state,
                task_id,
                verify=_verify_patches,
                audit_call=audit,
            )
            _v_ok = _verify_result.verify_ok
            _evidence_ok = _verify_result.evidence_recorded
            _el_task = time.monotonic() - _t_task
            if _v_ok and _evidence_ok:
                _build_checkpoint = (
                    task_obj.get("build_checkpoint")
                    if isinstance(task_obj, dict) else None
                )
                if (
                    coordinator_decision is not None
                    and isinstance(_build_checkpoint, dict)
                    and phase_state.task_build_checkpoint_is_current(task_id)
                    and phase_state.record_task_review_checkpoint(
                        task_id,
                        verify_warnings=getattr(
                            state, "last_verify_errors", [],
                        ),
                    )
                ):
                    _record = phase_state.get_task(task_id)
                    if isinstance(_record, dict):
                        _record.pop("verification_pending", None)
                        _record.pop("build_checkpoint", None)
                        phase_state.save()
                    group_end()
                    return 0, tasks_ok, tasks
                try:
                    task_done(i, len(tasks), task_name, elapsed_s=_el_task, ok=True)
                except Exception:
                    pass
                task_ok(i, len(tasks), elapsed_s=_el_task)
                group_end()
                if not _verification_only:
                    tasks_ok += 1
                state.tasks_ok_counter = tasks_ok
                _audit_task_ok(
                    _task_ende(state, phase_state, task_id, ok=True, name=task_name),
                    task_id, task_name, pd, pn,
                    via="verify_only",
                )
            else:
                if coordinator_decision is not None:
                    checkpointed = phase_state.record_task_verify_failure_checkpoint(
                        task_id,
                        getattr(state, "last_verify_errors", []),
                    )
                    if checkpointed:
                        audit(
                            "loop_task_verify_failure_checkpoint",
                            {"task_id": task_id, "phase": "post_build",
                             "error_count": min(
                                 8, len(getattr(state, "last_verify_errors", [])),
                             )},
                            pd, pn,
                        )
                    else:
                        phase_state.mark_human_review(
                            task_id,
                            grund="verify_failure_checkpoint_could_not_be_bound",
                        )
                        audit(
                            "loop_verify_recovery_result",
                            {"task_id": task_id, "status": "human_review",
                             "reason": "failure_evidence_unbound"},
                            pd, pn,
                        )
                    group_end()
                    return 0, tasks_ok, tasks
                group_end()
                _task_ende(
                    state, phase_state, task_id, ok=False,
                    name=task_name,
                    failure=("verify_evidence_missing" if _v_ok else "verify_failed"),
                    failure_detail=(
                        verify_failure_detail(state)
                        if not _v_ok else None
                    ),
                )
            continue

        debugger_fix = getattr(state, "debugger_fix_contract", None)
        if (
            debugger_fix is not None
            and isinstance(task_obj, dict)
            and task_obj.get("id") == "debugger-fix"
        ):
            from werkstatt.debugger_handoff import (
                DebuggerFix,
                DebuggerFixError,
                debugger_fix_loop_patches,
            )

            try:
                if not isinstance(debugger_fix, DebuggerFix):
                    raise DebuggerFixError(
                        "Debugger-Loop-Vertrag ist im RunState ungueltig."
                    )
                if sorted(task_obj.get("task_files") or []) != sorted(
                    debugger_fix.betroffene_dateien
                ):
                    raise DebuggerFixError(
                        "Debugger-Task-Dateiscope weicht vom freigegebenen Diff ab."
                    )
                state.patches = debugger_fix_loop_patches(
                    debugger_fix, pd,
                )
            except (DebuggerFixError, OSError, RuntimeError, ValueError) as exc:
                state.patches = []
                state.builder_failure_reason = "approved_debugger_diff_rejected"
                audit(
                    "loop_debugger_fix_rejected",
                    {"reason": type(exc).__name__, "task_id": task_id},
                    pd,
                    pn,
                )
                _builder_ok = False
            else:
                state.builder_failure_reason = ""
                audit(
                    "loop_debugger_fix_prepared",
                    {
                        "task_id": task_id,
                        "patch_hash": debugger_fix.patch_hash,
                        "files": list(debugger_fix.betroffene_dateien),
                    },
                    pd,
                    pn,
                )
                _builder_ok = True
        else:
            _builder_ok = _run_with_progress(
                lambda i=i: _with_spinner(
                    f"Builder t{i}", lambda: run_builder(state),
                ),
                i, len(tasks), task_name,
            )
        check_run_lease(state)
        if not _builder_ok:
            if (
                debugger_fix is not None
                and isinstance(task_obj, dict)
                and task_obj.get("id") == "debugger-fix"
            ):
                _task_ende(
                    state,
                    phase_state,
                    task_id,
                    ok=False,
                    name=task_name,
                    failure="approved_debugger_diff_rejected",
                    failure_detail=(
                        "Der freigegebene Debugger-Diff konnte nicht exakt "
                        "und innerhalb seines gebundenen Dateiscopes "
                        "vorbereitet werden."
                    ),
                )
                phase_state.save()
                return 1, tasks_ok, tasks
            # M-316 + M-317: Idempotenz-Erkennung NUR bei
            # action="create". Bei update: fail-closed (return 1).
            _loop_action = None
            if isinstance(task_obj, dict):
                _loop_action = task_obj.get("action")
            if _loop_action not in ("create", "update", "read"):
                # read-Task mit leerem Patch: echter Fehler (Builder
                # sollte hier nie laufen). Bei create/update: Idempotenz-
                # Pfad unten pruefen (M-318).
                # FIX AR 2026-10-31: continue statt return 1.
                audit("loop_builder_failed", {"task_id": i, "action": _loop_action}, pd, pn)
                _task_ende(
                    state, phase_state, task_id, ok=False, name=task_name,
                    failure="builder_failed",
                    failure_detail=str(
                        getattr(state, "builder_failure_reason", "") or ""
                    )[:1200],
                )
                continue

            # The failed Builder result is the checkpoint input for the next
            # coordinator decision. Recovery, Reviewer and Verify are never
            # started inside this Builder dispatch.
            failure_reason = str(
                getattr(state, "builder_failure_reason", "") or "builder_failed"
            )[:120]
            transitioned = _task_ende(
                state,
                phase_state,
                task_id,
                ok=False,
                name=task_name,
                failure=failure_reason,
                failure_detail=str(
                    getattr(state, "builder_failure_detail", "") or ""
                )[:1200],
            )
            audit(
                "loop_task_failed",
                {
                    "task_id": task_id,
                    "reason": "builder_failed_at_checkpoint",
                    "coordinator_reentry": True,
                    "transitioned": transitioned,
                },
                pd,
                pn,
            )
            phase_state.save()
            group_end()
            return 0, tasks_ok, tasks

        from werkstatt.roles.builder_apply import (
            BuilderApplyServices,
            apply_builder_patch_set,
        )

        apply_result = apply_builder_patch_set(
            state,
            task_obj,
            task_id=str(task_id),
            debugger_fix_bound=(
                debugger_fix is not None
                and isinstance(task_obj, dict)
                and task_obj.get("id") == "debugger-fix"
            ),
            services=BuilderApplyServices(
                audit_call=audit,
                call_hook=_call_hook,
                get_git_diff=_get_git_diff_for_hook,
                apply_one_patch=_apply_one_patch,
                delete_allowed=_delete_ziel_erlaubt,
                ruff_fix_changed=_ruff_fix_changed,
            ),
        )
        if apply_result.status == "antipattern_veto":
            audit(
                "loop_task_antipattern_veto",
                {
                    "task_id": task_id,
                    "count": apply_result.finding_count,
                    "kinds": list(apply_result.finding_kinds),
                    "files": list(apply_result.finding_files),
                },
                pd,
                pn,
            )
            reason = f"antipattern:{apply_result.reason}"
            phase_state.mark_vetoed(task_id, grund=reason)
            _task_ende(
                state, phase_state, task_id, ok=False, name=task_name,
                human_review=True, failure=reason,
            )
            phase_state.save()
            group_end()
            return 0, tasks_ok, tasks

        if apply_result.status == "already_fulfilled":
            audit(
                "auftrag_bereits_erfuellt",
                {"task_id": i, "name": task_name, "reason": "loop_flag_vor_hook"},
                pd,
                pn,
            )
            state.auftrag_bereits_erfuellt = False
            tasks_ok += 1
            state.tasks_ok_counter = tasks_ok
            _audit_task_ok(
                _task_ende(state, phase_state, task_id, ok=True, name=task_name),
                task_id, task_name, pd, pn,
                via="auftrag_bereits_erfuellt_pre_hook",
            )
            phase_state.save()
            group_end()
            return 0, tasks_ok, tasks

        if apply_result.status != "applied":
            failure = (
                f"hook_blocked: {apply_result.reason}"[:120]
                if apply_result.status == "hook_blocked"
                else "simplify_hook_blocked"
                if apply_result.status == "simplify_blocked"
                else apply_result.reason[:120] or "builder_apply_failed"
            )
            scope_rejected = apply_result.status == "scope_rejected"
            if scope_rejected and apply_result.reason == "unbound_approved_debugger_patch":
                audit(
                    "loop_debugger_fix_rejected",
                    {"reason": "unbound_exact_patch_marker", "task_id": task_id},
                    pd,
                    pn,
                )
            if scope_rejected:
                phase_state.mark_vetoed(task_id, grund=failure)
            transitioned = _task_ende(
                state,
                phase_state,
                task_id,
                ok=False,
                name=task_name,
                human_review=scope_rejected,
                failure=failure,
                failure_detail=apply_result.reason[:1200],
            )
            audit(
                "loop_task_failed",
                {
                    "task_id": task_id,
                    "reason": failure,
                    "coordinator_reentry": not scope_rejected,
                    "transitioned": transitioned,
                },
                pd,
                pn,
            )
            phase_state.save()
            group_end()
            return (1 if scope_rejected else 0), tasks_ok, tasks

        checkpointed = phase_state.record_task_build_checkpoint(task_id)
        if checkpointed:
            audit(
                "loop_task_build_checkpoint",
                {
                    "task_id": task_id,
                    "task_file_count": len(task_obj.get("task_files") or []),
                    "status": "verify_pending",
                },
                pd,
                pn,
            )
        else:
            phase_state.mark_human_review(
                task_id,
                grund="builder_checkpoint_unavailable",
            )
            audit(
                "loop_task_build_checkpoint",
                {
                    "task_id": task_id,
                    "task_file_count": len(task_obj.get("task_files") or []),
                    "status": "human_review",
                    "reason": "build_evidence_could_not_be_bound",
                },
                pd,
                pn,
            )
        phase_state.save()
        group_end()
        return 0, tasks_ok, tasks

    return 0, tasks_ok, tasks
