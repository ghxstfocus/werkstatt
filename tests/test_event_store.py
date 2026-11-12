"""Tests fuer den Event-Store (OP-122): append+query, kind-Filter, since_seq-Export."""

import json
import time
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



def test_run_record_checkpoint_is_compare_and_swap(tmp_path: Path) -> None:
    store = EventStore(db_pfad=tmp_path / "events.db")
    record = store.create_run_record(
        "demo", "run-1", "Repair the loop", base_commit="abc123",
    )
    assert record["checkpoint_version"] == 0
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


def test_task_checkpoint_consumes_chat_notice_with_run_record(
    tmp_path: Path,
) -> None:
    from werkstatt.phases.tasks import _persist_run_checkpoint

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

    _persist_run_checkpoint(
        store, "demo", "run-inbox", phase_state, {"id": "t2"},
    )

    record = store.get_run_record("demo", "run-inbox")
    assert record is not None
    assert record["checkpoint_version"] == 1
    assert record["checkpoint"]["safe_point"]["next_task_id"] == "t2"
    assert record["checkpoint"]["safe_point"]["completed_task_ids"] == ["t1"]
    assert record["checkpoint"]["inbox_offset"] == seq
    assert record["checkpoint"]["job_notices"] == [
        {
            "seq": seq,
            "job_id": "job-1",
            "mode": "read",
            "session_id": "session-1",
        },
    ]
    assert store.claim_run_message(
        "demo", "run-inbox", "worker-next",
    ) is None


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
    token = store.acquire_run_lease("demo", "legacy", "worker")
    assert token == 1
