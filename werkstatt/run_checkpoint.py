"""Durable inbox and follow-up reconciliation at coordinator checkpoints."""
from __future__ import annotations

import sqlite3
from hashlib import sha256
from pathlib import Path
from typing import Any

from werkstatt.event_store import EventStore
from werkstatt.phases._common import audit
from werkstatt.state import RunState, check_run_lease


def persist_run_checkpoint(
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
