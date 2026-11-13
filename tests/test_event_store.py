"""Tests fuer den Event-Store (OP-122): append+query, kind-Filter, since_seq-Export."""

import json
import sqlite3
import time
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest

from werkstatt.event_store import EventStore


def test_append_und_query_liefert_seq_reihenfolge(tmp_path: Path) -> None:
    store = EventStore(db_pfad=tmp_path / "events.db")

    seq_erst = store.append(
        "run-a",
        "phase_start",
        "explorer",
        "ok",
        {"text": "Explorer startet", "zaehler": 1},
    )
    seq_zweit = store.append(
        "run-a",
        "builder_ok",
        "builder",
        "ok",
        {"text": "Builder fertig", "verschachtelt": {"t": "t1"}},
    )

    assert seq_zweit > seq_erst
    assert seq_erst >= 1

    zeilen = store.query("run-a")
    assert len(zeilen) == 2
    assert [z["seq"] for z in zeilen] == [seq_erst, seq_zweit]
    assert zeilen[0]["kind"] == "phase_start"
    assert zeilen[0]["phase"] == "explorer"
    assert zeilen[0]["status"] == "ok"
    assert zeilen[1]["payload"] == {
        "text": "Builder fertig",
        "verschachtelt": {"t": "t1"},
    }
    assert zeilen[0]["run_id"] == "run-a"
    assert isinstance(zeilen[0]["ts"], str)

    assert store.query("run-b") == []


def test_query_kind_filter(tmp_path: Path) -> None:
    store = EventStore(db_pfad=tmp_path / "events.db")

    store.append("run-c", "phase_start", "explorer", "ok", {"text": "a"})
    store.append("run-c", "builder_ok", "builder", "ok", {"text": "b"})
    store.append("run-c", "phase_start", "architect", "ok", {"text": "c"})
    store.append("run-c", "verify_fail", "verify", "fehler", {"text": "d"})

    nur_start = store.query("run-c", kind="phase_start")

    assert len(nur_start) == 2
    assert all(z["kind"] == "phase_start" for z in nur_start)
    assert [z["phase"] for z in nur_start] == ["explorer", "architect"]
    assert len(store.query("run-c")) == 4
    assert store.query("run-c", kind="gibt_es_nicht") == []


def test_query_since_seq_export(tmp_path: Path) -> None:
    store = EventStore(db_pfad=tmp_path / "events.db")

    seq_erst = store.append("run-d", "phase_start", "explorer", "ok", {"text": "a"})
    seq_zweit = store.append("run-d", "builder_ok", "builder", "ok", {"text": "b"})
    seq_dritt = store.append("run-d", "phase_start", "architect", "ok", {"text": "c"})

    export = store.query("run-d", since_seq=seq_erst)
    assert [z["seq"] for z in export] == [seq_zweit, seq_dritt]

    export_leer = store.query("run-d", since_seq=seq_dritt)
    assert export_leer == []

    export_json = json.dumps(export, default=str)
    assert json.loads(export_json)[0]["seq"] == seq_zweit

def test_append_with_event_id_is_idempotent_and_project_scoped(
    tmp_path: Path,
) -> None:
    store = EventStore(db_pfad=tmp_path / "events.db")

    first = store.append(
        "run-a", "chat_job_queued", "chat", "queued",
        {"job_id": "job-1"}, event_id="chat-job:job-1:1", project="demo",
    )
    retry = store.append(
        "run-a", "chat_job_queued", "chat", "queued",
        {"job_id": "job-1", "retry": True},
        event_id="chat-job:job-1:1", project="demo",
    )

    assert retry == first
    events = store.query("run-a", project="demo")
    assert len(events) == 1
    assert events[0]["payload"] == {"job_id": "job-1"}
    assert store.query("run-a", project="other") == []



def test_run_record_wrong_target_retry_does_not_mutate_base_commit(
    tmp_path: Path,
) -> None:
    store = EventStore(db_pfad=tmp_path / "events.db")
    store.create_run_record("demo", "run-target", "Original target")

    with pytest.raises(ValueError, match="anderem Ziel"):
        store.create_run_record(
            "demo", "run-target", "Different target", base_commit="wrong-pin",
        )

    record = store.create_run_record(
        "demo", "run-target", "Original target", base_commit="correct-pin",
    )
    assert record["base_commit"] == "correct-pin"


def test_run_record_starting_transitions_to_running_once(
    tmp_path: Path,
) -> None:
    store = EventStore(db_pfad=tmp_path / "events.db")
    starting = store.create_run_record(
        "demo", "run-starting", "Build feature", status="starting",
    )
    assert starting["status"] == "starting"

    running = store.create_run_record("demo", "run-starting", "Build feature")
    assert running["status"] == "running"
    assert not store.transition_run_status(
        "demo", "run-starting",
        expected_status="starting", status="failed",
    )


def test_run_record_pins_versioned_start_context_across_worker_retry(
    tmp_path: Path,
) -> None:
    store = EventStore(db_pfad=tmp_path / "events.db")
    context = {
        "schema_version": 1,
        "goal": "Continue OP-397",
        "source": {"kind": "github", "pinned_sha": "abc123"},
    }

    starting = store.create_run_record(
        "demo", "run-context", "Continue OP-397", status="starting",
        base_commit="abc123", start_context=context,
    )
    assert starting["start_context"] == context
    assert starting["start_context_version"] == 1

    with pytest.raises(ValueError, match="anderem Startkontext"):
        store.create_run_record(
            "demo", "run-context", "Continue OP-397",
            start_context={**context, "goal": "Different task"},
        )
    unchanged = store.get_run_record("demo", "run-context")
    assert unchanged is not None
    assert unchanged["status"] == "starting"
    assert unchanged["start_context"] == context

    # The worker retry must not erase the originating request or repin it.
    running = store.create_run_record(
        "demo", "run-context", "Continue OP-397", base_commit="def456",
    )
    assert running["status"] == "running"
    assert running["base_commit"] == "abc123"
    assert running["start_context"] == context

def test_run_status_transition_uses_compare_and_swap(
    tmp_path: Path,
) -> None:
    store = EventStore(db_pfad=tmp_path / "events.db")
    store.create_run_record(
        "demo", "run-transition", "Build feature", status="starting",
    )

    assert store.transition_run_status(
        "demo", "run-transition",
        expected_status="starting", status="failed",
    )
    assert not store.transition_run_status(
        "demo", "run-transition",
        expected_status="starting", status="running",
    )
    record = store.get_run_record("demo", "run-transition")
    assert record is not None
    assert record["status"] == "failed"
    assert record["checkpoint_version"] == 0


def test_run_record_checkpoint_is_compare_and_swap(tmp_path: Path) -> None:
    store = EventStore(db_pfad=tmp_path / "events.db")
    record = store.create_run_record(
        "demo", "run-1", "Repair the loop",
    )
    assert record["checkpoint_version"] == 0
    pinned = store.create_run_record(
        "demo", "run-1", "Repair the loop", base_commit="abc123",
    )
    assert pinned["base_commit"] == "abc123"
    resumed = store.create_run_record(
        "demo", "run-1", "Repair the loop", base_commit="def456",
    )
    assert resumed["base_commit"] == "abc123"

    version = store.update_run_checkpoint(
        "demo", "run-1", {"next_action": "verify"}, expected_version=0,
    )
    assert version == 1
    current = store.get_run_record("demo", "run-1")
    assert current is not None
    assert current["checkpoint"] == {"next_action": "verify"}

    with pytest.raises(RuntimeError, match="parallel geaendert"):
        store.update_run_checkpoint(
            "demo", "run-1", {"next_action": "stale"}, expected_version=0,
        )


def test_run_inbox_is_idempotent_and_fenced_after_lease_recovery(
    tmp_path: Path,
) -> None:
    store = EventStore(db_pfad=tmp_path / "events.db")
    store.create_run_record("demo", "run-2", "Handle user follow-up")

    first = store.enqueue_run_message(
        "demo", "run-2", "msg-1", "question", {"text": "What changed?"},
    )
    retry = store.enqueue_run_message(
        "demo", "run-2", "msg-1", "question", {"text": "What changed?"},
    )
    assert retry == first

    old_worker = store.claim_run_message(
        "demo", "run-2", "worker-old", lease_seconds=0.01,
    )
    assert old_worker is not None
    time.sleep(0.03)

    new_worker = store.claim_run_message(
        "demo", "run-2", "worker-new", lease_seconds=10,
    )
    assert new_worker is not None
    assert new_worker["fencing_token"] > old_worker["fencing_token"]
    assert not store.acknowledge_run_message(
        first, "worker-old", old_worker["fencing_token"],
    )
    assert store.acknowledge_run_message(
        first, "worker-new", new_worker["fencing_token"],
    )
    assert store.claim_run_message(
        "demo", "run-2", "worker-third",
    ) is None


def test_run_inbox_rejects_orphan_and_idempotency_conflict(
    tmp_path: Path,
) -> None:
    store = EventStore(db_pfad=tmp_path / "events.db")
    with pytest.raises(ValueError, match="RunRecord fehlt"):
        store.enqueue_run_message(
            "demo", "missing-run", "msg-1", "question", {"text": "hello"},
        )

    store.create_run_record("demo", "run-3", "Follow-up")
    store.enqueue_run_message(
        "demo", "run-3", "msg-1", "question", {"text": "first"},
    )
    with pytest.raises(ValueError, match="wiederverwendet"):
        store.enqueue_run_message(
            "demo", "run-3", "msg-1", "question", {"text": "different"},
        )


def test_run_inbox_rejects_new_messages_after_terminal_status(
    tmp_path: Path,
) -> None:
    store = EventStore(db_pfad=tmp_path / "events.db")
    store.create_run_record("demo", "run-terminal-inbox", "Originalauftrag")
    seq = store.enqueue_run_message(
        "demo", "run-terminal-inbox", "msg-before-end", "question",
        {"text": "accepted while active"},
    )
    store.update_run_checkpoint(
        "demo", "run-terminal-inbox", {"done": True},
        expected_version=0, status="completed",
    )

    assert store.enqueue_run_message(
        "demo", "run-terminal-inbox", "msg-before-end", "question",
        {"text": "accepted while active"},
    ) == seq
    with pytest.raises(ValueError, match="nicht mehr aktiv"):
        store.enqueue_run_message(
            "demo", "run-terminal-inbox", "msg-after-end", "question",
            {"text": "must not be stranded"},
        )


def test_task_checkpoint_consumes_chat_notice_with_run_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from werkstatt.phases import tasks

    audit_events: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def _audit(*args: object, **kwargs: object) -> bool:
        audit_events.append((args, kwargs))
        return True

    monkeypatch.setattr(tasks, "audit", _audit)

    store = EventStore(db_pfad=tmp_path / "events.db")
    store.create_run_record("demo", "run-inbox", "Continue the approved task")
    seq = store.enqueue_run_message(
        "demo",
        "run-inbox",
        "chat-job:job-1",
        "job_notice",
        {
            "job_id": "job-1",
            "session_id": "session-1",
            "mode": "read",
            "context_seq": 7,
        },
    )
    phase_state = SimpleNamespace(data={
        "tasks": [
            {"id": "t1", "status": "done"},
            {"id": "t2", "status": "pending"},
        ],
    })

    tasks._persist_run_checkpoint(
        store, "demo", "run-inbox", phase_state, {"id": "t2"},
    )

    record = store.get_run_record("demo", "run-inbox")
    assert record is not None
    assert record["checkpoint_version"] == 1
    assert record["checkpoint"]["safe_point"]["next_task_id"] == "t2"
    assert record["checkpoint"]["safe_point"]["completed_task_ids"] == ["t1"]
    assert record["checkpoint"]["job_notice_offset"] == seq
    assert "inbox_offset" not in record["checkpoint"]
    assert record["checkpoint"]["job_notices"] == [
        {
            "seq": seq,
            "job_id": "job-1",
            "message_id": "chat-job:job-1",
            "mode": "read",
            "session_id": "session-1",
            "context_seq": 7,
        },
    ]
    assert len(audit_events) == 1
    payload = audit_events[0][0][1]
    assert isinstance(payload, dict)
    assert payload["job_id"] == "job-1"
    assert payload["context_seq"] == 7
    assert payload["decision_summary"].startswith(
        "Das Run-Hauptziel bleibt unveraendert"
    )
    assert audit_events[0][1]["audit_id"] == f"RUN-run-inbox-CHAT-{seq}"
    assert store.claim_run_message(
        "demo", "run-inbox", "worker-next",
    ) is None


def test_task_checkpoint_persists_chat_followup_without_replacing_goal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from werkstatt import chat_session
    from werkstatt.phases import tasks

    audit_events: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def _audit(*args: object, **kwargs: object) -> bool:
        audit_events.append((args, kwargs))
        return True

    monkeypatch.setattr(tasks, "audit", _audit)
    chat_db = tmp_path / "chat.db"
    monkeypatch.setattr(chat_session, "_db_pfad", lambda _project: chat_db)
    store = EventStore(db_pfad=tmp_path / "events.db")
    store.create_run_record(
        "demo", "run-followup", "Keep original goal", base_commit="abc123",
    )
    seq = store.enqueue_run_message(
        "demo", "run-followup", "chat-followup:proposal-1",
        "chat_followup_request", {
            "proposal_id": "proposal-1",
            "project": "demo",
            "session_id": "session-1",
            "parent_run_id": "run-followup",
            "base_commit": "abc123",
            "checkpoint_version": 0,
            "request": "Check the ADRs",
            "op_id": "OP-401",
        },
    )

    tasks._persist_run_checkpoint(
        store,
        "demo",
        "run-followup",
        SimpleNamespace(data={"tasks": []}),
        {"id": "next-task"},
        run_state=SimpleNamespace(project_dir=tmp_path),
    )

    record = store.get_run_record("demo", "run-followup")
    assert record is not None
    assert record["target"] == "Keep original goal"
    assert record["checkpoint"]["chat_followup_requests"] == [{
        "seq": seq,
        "message_id": "chat-followup:proposal-1",
        "proposal_id": "proposal-1",
        "session_id": "session-1",
        "request": "Check the ADRs",
        "op_id": "OP-401",
        "base_commit": "abc123",
        "queued_at_checkpoint_version": 0,
        "status": "received",
    }]
    assert store.run_message_acknowledged(
        "demo", "run-followup", "chat-followup:proposal-1",
    )
    assert audit_events[0][1]["audit_id"] == (
        f"RUN-run-followup-CHAT-FOLLOWUP-{seq}"
    )
    audit_payload = audit_events[0][0][1]
    assert "request" not in audit_payload
    assert audit_payload["request_sha256"] == sha256(
        b"Check the ADRs",
    ).hexdigest()
    chat = chat_session.ChatSession("demo", "session-1", db_pfad=chat_db)
    checkpoint_events = [
        event for event in chat.load()
        if event["kind"] == "loop_followup_checkpointed"
    ]
    assert len(checkpoint_events) == 1
    assert checkpoint_events[0]["payload"]["proposal_id"] == "proposal-1"
    assert "Einordnung steht noch aus" in checkpoint_events[0]["payload"]["detail"]

    tasks._persist_run_checkpoint(
        store,
        "demo",
        "run-followup",
        SimpleNamespace(data={"tasks": []}),
        {"id": "next-task"},
        run_state=SimpleNamespace(project_dir=tmp_path),
    )
    assert len([
        event for event in chat.load()
        if event["kind"] == "loop_followup_checkpointed"
    ]) == 1


def test_task_checkpoint_rejects_non_text_followup_without_ack(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from werkstatt.phases import tasks

    monkeypatch.setattr(tasks, "audit", lambda *_args, **_kwargs: True)
    store = EventStore(db_pfad=tmp_path / "events.db")
    store.create_run_record("demo", "run-invalid-followup", "Keep goal")
    store.enqueue_run_message(
        "demo", "run-invalid-followup", "chat-followup:invalid",
        "chat_followup_request", {
            "proposal_id": "invalid",
            "project": "demo",
            "session_id": "session-1",
            "parent_run_id": "run-invalid-followup",
            "base_commit": None,
            "request": ["not", "text"],
        },
    )

    with pytest.raises(TypeError, match="gültigen Text"):
        tasks._persist_run_checkpoint(
            store,
            "demo",
            "run-invalid-followup",
            SimpleNamespace(data={"tasks": []}),
            {"id": "next-task"},
        )

    assert not store.run_message_acknowledged(
        "demo", "run-invalid-followup", "chat-followup:invalid",
    )


def test_task_checkpoint_retries_chat_notice_audit_idempotently(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from werkstatt.phases import tasks

    audit_ids: list[str] = []

    def _audit(*_args: object, **kwargs: object) -> bool:
        audit_ids.append(str(kwargs["audit_id"]))
        return True

    monkeypatch.setattr(tasks, "audit", _audit)
    store = EventStore(db_pfad=tmp_path / "events.db")
    store.create_run_record("demo", "run-replay", "Continue approved work")
    store.enqueue_run_message(
        "demo", "run-replay", "chat-job:job-replay", "job_notice",
        {"job_id": "job-replay", "mode": "debugger", "session_id": "s1"},
    )
    phase_state = SimpleNamespace(data={"tasks": []})

    tasks._persist_run_checkpoint(
        store, "demo", "run-replay", phase_state, None,
    )
    tasks._persist_run_checkpoint(
        store, "demo", "run-replay", phase_state, None,
    )

    assert audit_ids == ["RUN-run-replay-CHAT-1"]


def test_task_checkpoint_audits_chat_result_without_copying_answer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from werkstatt.phases import tasks

    audit_events: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def _audit(*args: object, **kwargs: object) -> bool:
        audit_events.append((args, kwargs))
        return True

    monkeypatch.setattr(tasks, "audit", _audit)
    store = EventStore(db_pfad=tmp_path / "events.db")
    store.create_run_record("demo", "run-result", "Keep the approved goal")
    seq = store.enqueue_run_message(
        "demo", "run-result", "chat-job:job-result:result", "job_result_notice",
        {
            "job_id": "job-result",
            "session_id": "session-result",
            "mode": "read",
            "context_seq": 9,
            "state": "succeeded",
            "answer_sha256": "a" * 64,
        },
    )

    tasks._persist_run_checkpoint(
        store, "demo", "run-result", SimpleNamespace(data={"tasks": []}), None,
    )

    record = store.get_run_record("demo", "run-result")
    assert record is not None
    assert record["checkpoint"]["job_result_offset"] == seq
    assert record["checkpoint"]["job_results"] == [{
        "seq": seq,
        "message_id": "chat-job:job-result:result",
        "job_id": "job-result",
        "mode": "read",
        "session_id": "session-result",
        "context_seq": 9,
        "state": "succeeded",
        "answer_sha256": "a" * 64,
        "error_sha256": None,
    }]
    kind, payload = audit_events[0][0][:2]
    assert kind == "loop_chat_job_result_observed"
    assert isinstance(payload, dict)
    assert payload["answer_sha256"] == "a" * 64
    assert "answer" not in payload
    assert audit_events[0][1]["audit_id"] == (
        f"RUN-run-result-CHAT-RESULT-{seq}"
    )
    assert store.claim_run_message(
        "demo", "run-result", "next-worker", kind="job_result_notice",
    ) is None


def test_chat_result_audit_failure_keeps_inbox_unacked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from werkstatt.phases import tasks

    monkeypatch.setattr(tasks, "audit", lambda *_args, **_kwargs: False)
    store = EventStore(db_pfad=tmp_path / "events.db")
    store.create_run_record("demo", "run-result-audit-fail", "Keep the goal")
    seq = store.enqueue_run_message(
        "demo", "run-result-audit-fail", "chat-job:result-fail:result",
        "job_result_notice", {"job_id": "result-fail", "state": "failed"},
    )

    with pytest.raises(RuntimeError, match="konnte nicht auditiert werden"):
        tasks._persist_run_checkpoint(
            store,
            "demo",
            "run-result-audit-fail",
            SimpleNamespace(data={"tasks": []}),
            None,
        )

    record = store.get_run_record("demo", "run-result-audit-fail")
    assert record is not None
    assert record["checkpoint_version"] == 0
    assert "job_result_offset" not in record["checkpoint"]
    with sqlite3.connect(store.db_pfad) as connection:
        status = connection.execute(
            "SELECT status FROM run_inbox WHERE seq=?", (seq,),
        ).fetchone()
    assert status == ("leased",)


def test_task_checkpoint_does_not_ack_chat_notice_if_audit_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from werkstatt.phases import tasks

    monkeypatch.setattr(tasks, "audit", lambda *_args, **_kwargs: False)
    store = EventStore(db_pfad=tmp_path / "events.db")
    store.create_run_record("demo", "run-audit-fail", "Continue approved work")
    seq = store.enqueue_run_message(
        "demo", "run-audit-fail", "chat-job:job-audit-fail", "job_notice",
        {"job_id": "job-audit-fail", "mode": "read", "session_id": "s1"},
    )

    with pytest.raises(RuntimeError, match="konnte nicht auditiert werden"):
        tasks._persist_run_checkpoint(
            store, "demo", "run-audit-fail", SimpleNamespace(data={"tasks": []}), None,
        )

    record = store.get_run_record("demo", "run-audit-fail")
    assert record is not None
    assert record["checkpoint_version"] == 0
    # The worker lease is deliberately left unacknowledged so recovery can retry it.
    with sqlite3.connect(store.db_pfad) as connection:
        status = connection.execute(
            "SELECT status FROM run_inbox WHERE seq=?", (seq,),
        ).fetchone()
    assert status == ("leased",)


def test_run_result_marks_terminal_status_with_exit_code(
    tmp_path: Path,
) -> None:
    from werkstatt.loop import _persist_run_result

    store = EventStore(db_pfad=tmp_path / "events.db")
    store.create_run_record("demo", "run-success", "Finish task")
    _persist_run_result(store, "demo", "run-success", 0)
    result = store.get_run_record("demo", "run-success")

    assert result is not None
    assert result["status"] == "completed"
    assert result["checkpoint"]["exit_code"] == 0
    assert result["checkpoint_version"] == 1


def test_failed_run_result_is_persisted(tmp_path: Path) -> None:
    from werkstatt.loop import _persist_run_result

    store = EventStore(db_pfad=tmp_path / "events.db")
    store.create_run_record("demo", "run-failed", "Repair task")
    _persist_run_result(store, "demo", "run-failed", 1)
    result = store.get_run_record("demo", "run-failed")

    assert result is not None
    assert result["status"] == "failed"
    assert result["checkpoint"]["exit_code"] == 1


def test_duplicate_terminal_run_result_does_not_rewrite_existing_record(
    tmp_path: Path,
) -> None:
    from werkstatt.loop import _persist_run_result

    store = EventStore(db_pfad=tmp_path / "events.db")
    store.create_run_record("demo", "run-terminal-duplicate", "Finish task")
    _persist_run_result(store, "demo", "run-terminal-duplicate", 0)

    # A stale or repeated caller cannot turn an already completed run into a
    # failed run, or replace its recorded exit code.
    _persist_run_result(store, "demo", "run-terminal-duplicate", 1)
    result = store.get_run_record("demo", "run-terminal-duplicate")

    assert result is not None
    assert result["status"] == "completed"
    assert result["checkpoint"]["exit_code"] == 0
    assert result["checkpoint_version"] == 1


def test_terminal_run_transition_refuses_unacknowledged_inbox(
    tmp_path: Path,
) -> None:
    store = EventStore(db_pfad=tmp_path / "events.db")
    store.create_run_record("demo", "run-finish-inbox", "Finish safely")
    store.enqueue_run_message(
        "demo", "run-finish-inbox", "followup-1",
        "chat_followup_request", {"request": "Check one more thing"},
    )

    assert store.finish_run_checkpoint(
        "demo", "run-finish-inbox", {"exit_code": 0},
        expected_version=0, status="completed",
    ) is None
    record = store.get_run_record("demo", "run-finish-inbox")
    assert record is not None
    assert record["status"] == "running"
    assert record["checkpoint_version"] == 0


def test_run_result_drains_message_arriving_during_terminal_cas(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from werkstatt import chat_session
    from werkstatt.loop import _persist_run_result
    from werkstatt.phases import tasks

    store = EventStore(db_pfad=tmp_path / "events.db")
    store.create_run_record(
        "demo", "run-final-race", "Finish safely", base_commit="abc123",
    )
    chat_db = tmp_path / "chat.db"
    monkeypatch.setattr(chat_session, "_db_pfad", lambda _project: chat_db)
    monkeypatch.setattr(tasks, "audit", lambda *_args, **_kwargs: True)
    original_finish = store.finish_run_checkpoint
    inserted = False

    def enqueue_at_finish(*args, **kwargs):
        nonlocal inserted
        if not inserted:
            inserted = True
            store.enqueue_run_message(
                "demo", "run-final-race", "followup-late",
                "chat_followup_request", {
                    "proposal_id": "proposal-late",
                    "project": "demo",
                    "session_id": "session-final",
                    "parent_run_id": "run-final-race",
                    "base_commit": "abc123",
                    "request": "Review the final diff",
                },
            )
        return original_finish(*args, **kwargs)

    monkeypatch.setattr(store, "finish_run_checkpoint", enqueue_at_finish)
    run_state = SimpleNamespace(project_dir=tmp_path, run_lease_check=None)
    phase_state = SimpleNamespace(data={"tasks": []})
    _persist_run_result(
        store, "demo", "run-final-race", 0,
        run_state=run_state, phase_state=phase_state,
    )

    record = store.get_run_record("demo", "run-final-race")
    assert record is not None
    assert record["status"] == "completed"
    assert record["checkpoint"]["chat_followup_requests"][0]["proposal_id"] == (
        "proposal-late"
    )
    assert store.run_message_acknowledged(
        "demo", "run-final-race", "followup-late",
    )
    session = chat_session.ChatSession("demo", "session-final", db_pfad=chat_db)
    assert any(
        event["kind"] == "loop_followup_checkpointed"
        and event["payload"]["proposal_id"] == "proposal-late"
        for event in session.load()
    )


def test_run_lease_excludes_other_workers_and_fences_takeover(tmp_path: Path) -> None:
    store = EventStore(db_pfad=tmp_path / "events.db")
    store.create_run_record("demo", "run-a", "goal")

    token_a = store.acquire_run_lease("demo", "run-a", "worker-a", lease_seconds=60)
    assert token_a == 1
    assert store.acquire_run_lease("demo", "run-a", "worker-b") is None
    store.assert_run_lease("demo", "run-a", "worker-a", token_a)

    with store._connect() as conn:
        conn.execute(
            "UPDATE run_records SET lease_until=? WHERE project=? AND run_id=?",
            (time.time() - 1, "demo", "run-a"),
        )
        conn.commit()

    token_b = store.acquire_run_lease("demo", "run-a", "worker-b")
    assert token_b == token_a + 1
    with pytest.raises(RuntimeError, match="Run-Lease verloren"):
        store.assert_run_lease("demo", "run-a", "worker-a", token_a)
    assert not store.renew_run_lease("demo", "run-a", "worker-a", token_a)
    assert store.renew_run_lease("demo", "run-a", "worker-b", token_b)


def test_run_lease_cannot_be_released_by_stale_worker(tmp_path: Path) -> None:
    store = EventStore(db_pfad=tmp_path / "events.db")
    store.create_run_record("demo", "run-a", "goal")
    old_token = store.acquire_run_lease("demo", "run-a", "worker-a", lease_seconds=1)
    assert old_token == 1
    with store._connect() as conn:
        conn.execute(
            "UPDATE run_records SET lease_until=? WHERE project=? AND run_id=?",
            (time.time() - 1, "demo", "run-a"),
        )
        conn.commit()

    new_token = store.acquire_run_lease("demo", "run-a", "worker-b")
    assert new_token == 2
    assert not store.release_run_lease("demo", "run-a", "worker-a", old_token)
    store.assert_run_lease("demo", "run-a", "worker-b", new_token)


def test_run_lease_schema_migrates_existing_run_records(tmp_path: Path) -> None:
    db = tmp_path / "events.db"
    import sqlite3

    with sqlite3.connect(db) as conn:
        conn.execute(
            "CREATE TABLE run_records ("
            "project TEXT NOT NULL, run_id TEXT NOT NULL, status TEXT NOT NULL, "
            "target TEXT NOT NULL DEFAULT '', base_commit TEXT, "
            "checkpoint_json TEXT NOT NULL DEFAULT '{}', "
            "checkpoint_version INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL, "
            "PRIMARY KEY (project, run_id))"
        )
        conn.execute(
            "INSERT INTO run_records (project, run_id, status, target, updated_at) "
            "VALUES ('demo', 'legacy', 'running', 'goal', 'now')"
        )

    store = EventStore(db_pfad=db)
    record = store.get_run_record("demo", "legacy")
    assert record is not None
    assert record["start_context"] == {}
    assert record["start_context_version"] == 0
    token = store.acquire_run_lease("demo", "legacy", "worker")
    assert token == 1
