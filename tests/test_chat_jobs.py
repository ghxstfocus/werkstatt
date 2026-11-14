"""Persistente Chat-Job-Zustaende und Event-Replay (OP-397)."""
from __future__ import annotations

import hashlib
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from werkstatt.chat_jobs import ChatJobStore


def test_create_is_idempotent_and_survives_store_reopen(tmp_path: Path) -> None:
    db = tmp_path / "jobs.db"
    first, created = ChatJobStore(db).create(
        "session-a", "Pruefe Status", "read", "request-key-0001",
        context_seq=7, run_id="run-original",
    )
    duplicate, duplicate_created = ChatJobStore(db).create(
        "session-a", "Pruefe Status", "read", "request-key-0001",
        context_seq=99, run_id="run-retry",
    )

    assert created is True
    assert duplicate_created is False
    assert duplicate["job_id"] == first["job_id"]
    assert duplicate["state"] == "queued"
    assert first["context_seq"] == duplicate["context_seq"] == 7
    assert first["run_id"] == duplicate["run_id"] == "run-original"
    assert ChatJobStore(db).get(first["job_id"])["events"][0]["kind"] == "queued"


def test_claim_is_single_winner_and_completion_is_persisted(tmp_path: Path) -> None:
    store = ChatJobStore(tmp_path / "jobs.db")
    job, _ = store.create("session-a", "Frage", "read", "request-key-0002")

    assert store.claim(job["job_id"]) is True
    assert store.claim(job["job_id"]) is False
    assert store.finish(job["job_id"], answer="Erledigt") is True
    assert store.finish(job["job_id"], answer="Doppelt") is False

    current = store.get(job["job_id"])
    assert current is not None
    assert current["state"] == "succeeded"
    assert current["answer"] == "Erledigt"
    assert [event["kind"] for event in current["events"]] == [
        "queued", "started", "succeeded",
    ]


def test_event_replay_cursor_returns_only_new_events(tmp_path: Path) -> None:
    store = ChatJobStore(tmp_path / "jobs.db")
    job, _ = store.create("session-a", "Frage", "read", "request-key-0003")
    first = store.get(job["job_id"])
    assert first is not None
    cursor = first["events"][-1]["seq"]
    store.claim(job["job_id"])
    store.append_event(job["job_id"], "chunk", {"text": "Teil"})

    replay = store.get(job["job_id"], since_seq=cursor)
    assert replay is not None
    assert [event["kind"] for event in replay["events"]] == ["started", "chunk"]
    assert replay["events"][-1]["payload"] == {"text": "Teil"}


def test_run_job_uses_snapshot_and_merges_completed_turn_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from werkstatt import chat_agent, chat_jobs, chat_session

    db_path = tmp_path / "jobs.db"
    chat_db = tmp_path / "chat.db"
    monkeypatch.setattr(chat_session, "_db_pfad", lambda _project: chat_db)
    parent = chat_session.ChatSession("demo", "session-a")
    parent.append("user", {"text": "Vorherige Frage"})
    parent.append("assistant", {"text": "Vorherige Antwort"})
    context_seq = parent.max_seq()
    job, _ = ChatJobStore(db_path).create(
        "session-a", "Neue Frage", "read", "request-key-snapshot-001",
        context_seq=context_seq,
    )
    parent.append("user", {"text": "Spaeter eingereicht"})
    gesehen: list[tuple[str, list[str]]] = []

    def _fake_chat_loop(session, message, **_kwargs):
        gesehen.append((
            session.session_id,
            [event["payload"].get("text", "") for event in session.load()],
        ))
        assert message == "Neue Frage"
        session.append("user", {"text": message, "job_id": job["job_id"]})
        session.append("assistant", {"text": "Neue Antwort"})
        return "Neue Antwort"

    monkeypatch.setattr(chat_agent, "chat_loop", _fake_chat_loop)
    monkeypatch.setattr(chat_jobs, "_WORKER_ID", "worker-test")

    assert chat_jobs._run_job(db_path, "demo", tmp_path, job["job_id"]) is True
    assert gesehen == [(
        job["job_id"], ["Vorherige Frage", "Vorherige Antwort"],
    )]
    assert chat_session.ChatSession(
        "demo", job["job_id"],
    ).load() == []
    merged = parent.load()
    job_turns = [event for event in merged if event["kind"] == "job_turn"]
    assert len(job_turns) == 1
    assert job_turns[0]["payload"]["user_text"] == "Neue Frage"
    assert job_turns[0]["payload"]["assistant_text"] == "Neue Antwort"
    result = ChatJobStore(db_path).get(job["job_id"])
    assert result is not None
    assert result["state"] == "succeeded"


def test_sync_completed_job_turns_repairs_missing_parent_projection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from werkstatt import chat_jobs, chat_session

    chat_db = tmp_path / "chat.db"
    monkeypatch.setattr(chat_session, "_db_pfad", lambda _project: chat_db)
    store = ChatJobStore(tmp_path / "jobs.db")
    job, _ = store.create(
        "session-a", "Frage", "read", "request-key-reconcile-001",
    )
    assert store.claim(job["job_id"])
    assert store.finish(job["job_id"], answer="Antwort")

    assert chat_jobs.sync_completed_job_turns(
        "demo", "session-a", db_path=store.db_path,
    ) == 1
    assert chat_jobs.sync_completed_job_turns(
        "demo", "session-a", db_path=store.db_path,
    ) == 0
    events = chat_session.ChatSession(
        "demo", "session-a", db_pfad=chat_db,
    ).load()
    assert [event["kind"] for event in events] == ["job_turn"]


def test_job_failure_is_visible_and_terminal(tmp_path: Path) -> None:
    store = ChatJobStore(tmp_path / "jobs.db")
    job, _ = store.create("session-a", "Frage", "read", "request-key-0004")
    store.claim(job["job_id"])

    assert store.finish(job["job_id"], error="RuntimeError: LLM nicht verfuegbar")
    failed = store.get(job["job_id"])

    assert failed is not None
    assert failed["state"] == "failed"
    assert failed["error"] == "RuntimeError: LLM nicht verfuegbar"
    assert failed["events"][-1]["payload"]["error"].startswith("RuntimeError")


def test_inactive_run_fails_uncheckpointed_jobs_but_preserves_safe_replay(
    tmp_path: Path,
) -> None:
    from werkstatt.chat_jobs import fail_uncheckpointed_jobs_for_inactive_run

    store = ChatJobStore(tmp_path / "jobs.db")
    uncheckpointed, _ = store.create(
        "session-a", "Frage vor Run-Ende", "read",
        "request-key-orphan-001", run_id="run-finished", project="demo",
    )
    replayable, _ = store.create(
        "session-a", "Frage mit Checkpoint", "read",
        "request-key-orphan-002", run_id="run-finished", project="demo",
    )
    active, _ = store.create(
        "session-a", "Frage im aktiven Run", "read",
        "request-key-orphan-003", run_id="run-active", project="demo",
    )
    assert store.set_run_snapshot(
        replayable["job_id"], tmp_path, tmp_path / "snapshot",
        "base-head", "fingerprint",
    )

    class _Events:
        def run_message_acknowledged(
            self, project: str, run_id: str, message_id: str,
        ) -> bool:
            return (
                project == "demo"
                and run_id == "run-finished"
                and message_id == f"chat-job:{replayable['job_id']}"
            )

    failed = fail_uncheckpointed_jobs_for_inactive_run(
        "demo", "run-active", db_path=store.db_path, event_store=_Events(),
    )

    assert failed == 1
    failed_job = store.get(uncheckpointed["job_id"])
    replayable_job = store.get(replayable["job_id"])
    active_job = store.get(active["job_id"])
    assert failed_job is not None and failed_job["state"] == "failed"
    assert "Bitte sende den Auftrag erneut" in failed_job["error"]
    assert failed_job["events"][-1]["payload"]["reason"] == "run_ended_before_checkpoint"
    assert replayable_job is not None and replayable_job["state"] == "queued"
    assert active_job is not None and active_job["state"] == "queued"


def test_claim_allows_independent_turns_within_one_session(tmp_path: Path) -> None:
    store = ChatJobStore(tmp_path / "jobs.db")
    first, _ = store.create("session-a", "Erste Frage", "read", "request-key-a001")
    second, _ = store.create("session-a", "Zweite Frage", "read", "request-key-a002")

    assert store.claim(first["job_id"]) is True
    assert store.claim(second["job_id"]) is True


def test_jobs_in_different_sessions_can_run_in_parallel(tmp_path: Path) -> None:
    store = ChatJobStore(tmp_path / "jobs.db")
    first, _ = store.create("session-a", "Frage A", "read", "request-key-b001")
    second, _ = store.create("session-b", "Frage B", "read", "request-key-b002")

    assert store.claim(first["job_id"]) is True
    assert store.claim(second["job_id"]) is True


def test_dispatch_submits_same_session_jobs_independently(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from concurrent.futures import Future

    from werkstatt import chat_jobs

    class _RecordingExecutor:
        def __init__(self) -> None:
            self.submitted: list[tuple[object, ...]] = []

        def submit(self, *args: object) -> Future[bool]:
            self.submitted.append(args)
            return Future()

    db_path = tmp_path / "jobs.db"
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    store = ChatJobStore(db_path)
    first, _ = store.create("session-a", "Erste", "read", "request-key-run-001")
    second, _ = store.create("session-a", "Zweite", "read", "request-key-run-002")
    executor = _RecordingExecutor()
    monkeypatch.setattr(chat_jobs, "_EXECUTOR", executor)
    monkeypatch.setattr(chat_jobs, "_FUTURES", {})

    chat_jobs._dispatch_pending(db_path, "demo", project_dir)

    assert [args[-1] for args in executor.submitted] == [
        first["job_id"], second["job_id"],
    ]
def test_dispatch_retries_when_a_claim_race_future_finishes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from concurrent.futures import Future

    from werkstatt import chat_jobs

    class _RecordingExecutor:
        def __init__(self) -> None:
            self.submitted: list[tuple[object, ...]] = []

        def submit(self, *args: object) -> Future[bool]:
            self.submitted.append(args)
            return Future()

    db_path = tmp_path / "jobs.db"
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    store = ChatJobStore(db_path)
    first, _ = store.create("session-a", "Erste", "read", "request-key-race-001")
    second, _ = store.create("session-a", "Zweite", "read", "request-key-race-002")
    assert store.claim(first["job_id"], "worker-a")

    executor = _RecordingExecutor()
    futures: dict[str, Future[bool]] = {}
    monkeypatch.setattr(chat_jobs, "_EXECUTOR", executor)
    monkeypatch.setattr(chat_jobs, "_FUTURES", futures)
    second_key = f"{db_path.resolve()}:{second['job_id']}"
    lost_claim: Future[bool] = Future()
    futures[second_key] = lost_claim

    assert store.finish(first["job_id"], answer="Erste Antwort")
    chat_jobs._dispatch_pending(db_path, "demo", project_dir)
    assert executor.submitted == []

    lost_claim.add_done_callback(
        chat_jobs._future_cleanup_callback(
            second_key, db_path, "demo", project_dir,
        ),
    )
    lost_claim.set_result(False)

    assert len(executor.submitted) == 1
    assert executor.submitted[0][-1] == second["job_id"]


def test_queue_order_is_fifo_when_timestamps_collide(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from werkstatt import chat_jobs

    monkeypatch.setattr(chat_jobs, "_now", lambda: "2026-11-10T00:00:00+00:00")
    store = ChatJobStore(tmp_path / "jobs.db")
    first, _ = store.create("session-a", "First", "read", "request-key-c001")
    second, _ = store.create("session-a", "Second", "read", "request-key-c002")

    assert [job["job_id"] for job in store.queued()] == [
        first["job_id"], second["job_id"],
    ]
    assert [job["job_id"] for job in store.active_for_session("session-a")] == [
        first["job_id"], second["job_id"],
    ]

def test_completed_future_is_removed_from_registry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from concurrent.futures import Future

    from werkstatt import chat_jobs

    class _ImmediateExecutor:
        def submit(self, *_args: object) -> Future[bool]:
            future: Future[bool] = Future()
            future.set_result(True)
            return future

    db_path = tmp_path / "jobs.db"
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    store = ChatJobStore(db_path)
    job, _created = store.create(
        "session-a", "Frage", "read", "request-key-future-001",
    )
    monkeypatch.setattr(chat_jobs, "_EXECUTOR", _ImmediateExecutor())
    key = f"{db_path.resolve()}:{job['job_id']}"

    chat_jobs._dispatch_pending(db_path, "demo", project_dir)

    assert key not in chat_jobs._FUTURES

def test_expired_worker_lease_fails_job_and_persists_reason(tmp_path: Path) -> None:
    store = ChatJobStore(tmp_path / "jobs.db")
    job, _created = store.create(
        "session-a", "Frage", "read", "request-key-lease-001",
    )
    assert store.claim(job["job_id"], "worker-a")
    expired_at = datetime.now(UTC) + timedelta(seconds=91)

    assert store.recover_abandoned_jobs(now=expired_at) == 1
    failed = store.get(job["job_id"])
    assert failed is not None
    assert failed["state"] == "failed"
    assert failed["error"] == (
        "Worker-Lease abgelaufen; Job nach Prozessunterbrechung beendet."
    )
    assert failed["events"][-1]["payload"]["reason"] == "worker_lease_expired"
    assert store.cancellation_requested(job["job_id"], "worker-a")
    assert store.heartbeat(job["job_id"], "worker-a") is False


def test_live_worker_lease_is_not_expired_on_reconnect(tmp_path: Path) -> None:
    store = ChatJobStore(tmp_path / "jobs.db")
    job, _created = store.create(
        "session-a", "Frage", "read", "request-key-lease-002",
    )
    assert store.claim(job["job_id"], "worker-a")
    assert store.heartbeat(job["job_id"], "worker-a")
    reconnect_at = datetime.now(UTC) + timedelta(seconds=89)

    assert store.recover_abandoned_jobs(now=reconnect_at) == 0
    current = store.get(job["job_id"])
    assert current is not None
    assert current["state"] == "running"


def test_only_claiming_worker_can_renew_lease(tmp_path: Path) -> None:
    store = ChatJobStore(tmp_path / "jobs.db")
    job, _created = store.create(
        "session-a", "Frage", "read", "request-key-lease-003",
    )
    assert store.claim(job["job_id"], "worker-a")

    assert store.heartbeat(job["job_id"], "worker-b") is False
    assert store.cancellation_requested(job["job_id"], "worker-b") is True
    assert store.cancellation_requested(job["job_id"], "worker-a") is False
    assert store.heartbeat(job["job_id"], "worker-a") is True

def test_store_migrates_existing_jobs_table_for_worker_leases(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "legacy-jobs.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE jobs ("
            "job_id TEXT PRIMARY KEY,session_id TEXT NOT NULL,"
            "idempotency_key TEXT NOT NULL,message TEXT NOT NULL,"
            "mode TEXT NOT NULL,state TEXT NOT NULL,answer TEXT,error TEXT,"
            "created_at TEXT NOT NULL,updated_at TEXT NOT NULL,"
            "UNIQUE(session_id,idempotency_key))"
        )
        conn.execute(
            "CREATE TABLE job_events ("
            "seq INTEGER PRIMARY KEY AUTOINCREMENT,"
            "job_id TEXT NOT NULL,kind TEXT NOT NULL,"
            "payload TEXT NOT NULL,ts TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                "legacy-job", "session-a", "legacy-key", "Old question",
                "read", "queued", None, None, "2026-11-10", "2026-11-10",
            ),
        )

    ChatJobStore(db_path)
    with sqlite3.connect(db_path) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(jobs)")}
        event_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(job_events)")
        }
        context_seq = conn.execute(
            "SELECT context_seq FROM jobs WHERE job_id='legacy-job'",
        ).fetchone()[0]

    assert {
        "worker_id", "heartbeat_at", "cancel_requested", "context_seq",
        "run_id",
    } <= columns
    assert context_seq is None
    assert {"projected", "audited"} <= event_columns

def test_queued_job_can_be_cancelled_once(tmp_path: Path) -> None:
    store = ChatJobStore(tmp_path / "jobs.db")
    job, _created = store.create(
        "session-a", "Frage", "read", "request-key-cancel-001",
    )

    result = store.request_cancel(job["job_id"], "session-a")

    assert result == {"job_id": job["job_id"], "state": "cancelled"}
    assert store.claim(job["job_id"]) is False
    cancelled = store.get(job["job_id"])
    assert cancelled is not None
    assert cancelled["state"] == "cancelled"
    assert cancelled["events"][-1]["kind"] == "cancelled"


def test_running_job_cancellation_is_cooperative_and_terminal(
    tmp_path: Path,
) -> None:
    store = ChatJobStore(tmp_path / "jobs.db")
    job, _created = store.create(
        "session-a", "Frage", "read", "request-key-cancel-002",
    )
    assert store.claim(job["job_id"], "worker-a")

    result = store.request_cancel(job["job_id"], "session-a")

    assert result == {"job_id": job["job_id"], "state": "cancelling"}
    assert store.cancellation_requested(job["job_id"], "worker-a")
    assert store.finish(job["job_id"], cancelled=True)
    cancelled = store.get(job["job_id"])
    assert cancelled is not None
    assert cancelled["state"] == "cancelled"
    assert cancelled["events"][-1]["kind"] == "cancelled"

def test_sync_cleans_branch_for_failed_terminal_job(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from werkstatt import chat_jobs, chat_session

    chat_db = tmp_path / "chat.db"
    monkeypatch.setattr(chat_session, "_db_pfad", lambda _project: chat_db)
    parent = chat_session.ChatSession("demo", "session-a", db_pfad=chat_db)
    store = ChatJobStore(tmp_path / "jobs.db")
    job, _ = store.create(
        "session-a", "Frage", "read", "request-key-failed-branch-001",
    )
    parent.snapshot_to(job["job_id"])
    assert store.claim(job["job_id"])
    assert store.finish(job["job_id"], error="worker crashed")

    assert chat_jobs.sync_completed_job_turns(
        "demo", "session-a", db_path=store.db_path,
    ) == 0
    assert chat_session.ChatSession(
        "demo", job["job_id"], db_pfad=chat_db,
    ).load() == []
    assert parent.load() == []

def test_job_events_are_projected_to_timeline_exactly_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import werkstatt.audit as audit_mod
    from werkstatt import event_store, projection

    monkeypatch.setattr(audit_mod, "_werkstatt_home", lambda: tmp_path)
    monkeypatch.setattr(event_store, "werkstatt_home", lambda: tmp_path)
    monkeypatch.setattr(projection, "_werkstatt_home", lambda: tmp_path)
    store = ChatJobStore(tmp_path / "chat-jobs.db")
    job, _ = store.create(
        "session-a", "Frage", "read", "request-key-timeline-001",
        run_id="run-a", project="demo",
    )

    first = store.get(job["job_id"])
    assert first is not None
    assert store.project_pending_events() == 0

    timeline = event_store.EventStore(tmp_path / ".werkstatt" / "events.db")
    events = timeline.query("run-a", project="demo")
    assert len(events) == 1
    event = events[0]
    assert event["kind"] == "chat_job_queued"
    assert event["project"] == "demo"
    assert event["payload"]["job_id"] == job["job_id"]
    assert event["payload"]["session_id"] == "session-a"
    assert event["payload"]["job_event_kind"] == "queued"
    assert "Frage" not in str(event["payload"])
    assert store.project_pending_events() == 0
    projector = projection.Projector()
    projector.rebuild()
    rebuilt = timeline.query("run-a", project="demo")
    assert len(rebuilt) == 1
    assert rebuilt[0]["payload"]["job_id"] == job["job_id"]
    with sqlite3.connect(tmp_path / ".werkstatt" / "events.db") as conn:
        projected_ids = conn.execute(
            "SELECT event_id FROM events WHERE run_id=? AND kind=?",
            ("run-a", "chat_job_queued"),
        ).fetchall()
    assert projected_ids == [(f"chat-job:{job['job_id']}:1",)]




def test_run_inbox_outbox_replays_after_interrupted_handoff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from werkstatt import chat_jobs, event_store

    jobs_db = tmp_path / "chat-jobs.db"
    events = event_store.EventStore(tmp_path / "events.db")
    events.create_run_record("demo", "run-active", "Pruefe Repo")
    monkeypatch.setattr(event_store, "EventStore", lambda: events)
    dispatched: list[str] = []
    original_mark = ChatJobStore.mark_run_inbox_enqueued
    mark_calls = 0

    def _crash_after_inbox_write(store: ChatJobStore, job_id: str) -> bool:
        nonlocal mark_calls
        mark_calls += 1
        if mark_calls == 1:
            raise RuntimeError("simulierter Prozessabbruch nach Inbox-Commit")
        return original_mark(store, job_id)

    def _dispatch_after_reconcile(
        dispatch_db: Path, _project: str, _project_dir: Path,
    ) -> None:
        queued_jobs = ChatJobStore(dispatch_db).queued()
        assert len(queued_jobs) == 1
        dispatched.append(f"chat-job:{queued_jobs[0]['job_id']}")

    monkeypatch.setattr(ChatJobStore, "mark_run_inbox_enqueued", _crash_after_inbox_write)
    monkeypatch.setattr(chat_jobs, "_dispatch_pending", _dispatch_after_reconcile)

    with pytest.raises(RuntimeError, match="simulierter Prozessabbruch"):
        chat_jobs.enqueue_chat_job(
            "demo", tmp_path, "session-a", "Frage waehrend Run",
            "read", "request-key-outbox-001", db_path=jobs_db,
            context_seq=4, run_id="run-active",
        )

    persisted = ChatJobStore(jobs_db).queued()
    assert len(persisted) == 1
    job_id = str(persisted[0]["job_id"])
    assert dispatched == []

    chat_jobs.resume_chat_jobs("demo", tmp_path, db_path=jobs_db)

    assert dispatched == [f"chat-job:{job_id}"]
    message = events.claim_run_message(
        "demo", "run-active", "verify-worker", kind="job_notice",
    )
    assert message is not None
    assert message["message_id"] == f"chat-job:{job_id}"
    assert events.acknowledge_run_message(
        message["seq"], "verify-worker", message["fencing_token"],
    )
    assert events.claim_run_message(
        "demo", "run-active", "verify-worker", kind="job_notice",
    ) is None
    assert ChatJobStore(jobs_db).get(job_id)["run_inbox_enqueued"] == 1


def test_run_inbox_outbox_waits_for_run_record_then_reconciles(
    tmp_path: Path,
) -> None:
    from werkstatt import chat_jobs, event_store

    jobs_db = tmp_path / "chat-jobs.db"
    events = event_store.EventStore(tmp_path / "events.db")
    job, _ = ChatJobStore(jobs_db).create(
        "session-a", "Frage waehrend starting", "read",
        "request-key-outbox-002", context_seq=3,
        run_id="run-starting", project="demo",
    )

    assert chat_jobs.reconcile_run_inbox(
        "demo", db_path=jobs_db, event_store=events,
    ) == 0
    assert ChatJobStore(jobs_db).get(job["job_id"])["run_inbox_enqueued"] == 0

    events.create_run_record("demo", "run-starting", "Pruefe Repo")
    assert chat_jobs.reconcile_run_inbox(
        "demo", db_path=jobs_db, event_store=events,
    ) == 1
    assert chat_jobs.reconcile_run_inbox(
        "demo", db_path=jobs_db, event_store=events,
    ) == 0
    message = events.claim_run_message(
        "demo", "run-starting", "test-worker", kind="job_notice",
    )
    assert message is not None
    assert message["payload"] == {
        "job_id": job["job_id"],
        "session_id": "session-a",
        "mode": "read",
        "context_seq": 3,
    }


def test_run_inbox_outbox_fails_job_when_run_is_already_terminal(
    tmp_path: Path,
) -> None:
    from werkstatt import chat_jobs, event_store

    jobs_db = tmp_path / "chat-jobs.db"
    events = event_store.EventStore(tmp_path / "events.db")
    events.create_run_record("demo", "run-ended", "Pruefe Repo")
    events.update_run_checkpoint(
        "demo", "run-ended", {"done": True},
        expected_version=0, status="completed",
    )
    store = ChatJobStore(jobs_db)
    job, _ = store.create(
        "session-a", "Frage im Abschlussrennen", "read",
        "request-key-terminal-run", context_seq=3,
        run_id="run-ended", project="demo",
    )

    assert chat_jobs.reconcile_run_inbox(
        "demo", db_path=jobs_db, event_store=events,
    ) == 0
    failed = store.get(job["job_id"])
    assert failed["state"] == "failed"
    assert failed["events"][-1]["payload"]["reason"] == (
        "run_ended_before_checkpoint"
    )


def test_run_inbox_reconciles_terminal_chat_job_result_idempotently(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from werkstatt import chat_jobs, event_store

    jobs_db = tmp_path / "chat-jobs.db"
    events = event_store.EventStore(tmp_path / "events.db")
    events.create_run_record("demo", "run-result", "Pruefe Repo")
    monkeypatch.setattr(event_store, "EventStore", lambda: events)
    store = ChatJobStore(jobs_db)
    job, _ = store.create(
        "session-a", "Pruefe den Status", "read", "request-key-result-001",
        context_seq=12, run_id="run-result", project="demo",
    )

    assert chat_jobs.reconcile_run_inbox(
        "demo", db_path=jobs_db, event_store=events,
    ) == 1
    assert store.claim(job["job_id"], "chat-worker")
    assert store.finish(job["job_id"], answer="Belegte Antwort")
    assert chat_jobs.reconcile_run_inbox(
        "demo", db_path=jobs_db, event_store=events,
    ) == 1
    assert chat_jobs.reconcile_run_inbox(
        "demo", db_path=jobs_db, event_store=events,
    ) == 0

    result = events.claim_run_message(
        "demo", "run-result", "loop-worker", kind="job_result_notice",
    )
    assert result is not None
    assert result["message_id"] == f"chat-job:{job['job_id']}:result"
    assert result["payload"]["state"] == "succeeded"
    assert result["payload"]["context_seq"] == 12
    assert result["payload"]["answer_sha256"] == hashlib.sha256(
        b"Belegte Antwort",
    ).hexdigest()
    assert "Belegte Antwort" not in str(result["payload"])
    assert events.acknowledge_run_message(
        result["seq"], "loop-worker", result["fencing_token"],
    )


def test_result_handoff_race_with_run_termination_is_resolved(
    tmp_path: Path,
) -> None:
    from werkstatt import chat_jobs
    from werkstatt.event_store import RunNotActiveError

    class _RunFinishesDuringHandoff:
        def get_run_record(self, project: str, run_id: str) -> dict[str, str]:
            assert (project, run_id) == ("demo", "run-race")
            return {"status": "running"}

        def enqueue_run_message(self, *_args: Any, **_kwargs: Any) -> int:
            raise RunNotActiveError("Run ist nicht mehr aktiv")

    jobs_db = tmp_path / "chat-jobs.db"
    store = ChatJobStore(jobs_db)
    job, _ = store.create(
        "session-a", "Frage", "read", "request-key-result-race-001",
        run_id="run-race", project="demo",
    )
    assert store.mark_run_inbox_enqueued(job["job_id"])
    assert store.claim(job["job_id"], "chat-worker")
    assert store.finish(job["job_id"], answer="Antwort")

    assert chat_jobs.reconcile_run_inbox(
        "demo", db_path=jobs_db, event_store=_RunFinishesDuringHandoff(),
    ) == 1
    finished = store.get(job["job_id"])
    assert finished is not None
    assert finished["run_result_enqueued"] == 1
    assert finished["events"][-1]["kind"] == "run_result_handoff_skipped"
    assert finished["events"][-1]["payload"]["reason"] == (
        "run_ended_before_result_handoff"
    )


def test_resume_reconciles_result_of_abandoned_run_bound_chat_job(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from werkstatt import chat_jobs, event_store

    jobs_db = tmp_path / "chat-jobs.db"
    events = event_store.EventStore(tmp_path / "events.db")
    events.create_run_record("demo", "run-abandoned-chat", "Pruefe Repo")
    monkeypatch.setattr(event_store, "EventStore", lambda: events)
    store = ChatJobStore(jobs_db)
    job, _ = store.create(
        "session-a", "Pruefe den Status", "read", "request-key-result-002",
        run_id="run-abandoned-chat", project="demo",
    )
    chat_jobs.reconcile_run_inbox(
        "demo", db_path=jobs_db, event_store=events,
    )
    assert store.claim(job["job_id"], "lost-chat-worker")
    with sqlite3.connect(jobs_db) as connection:
        connection.execute(
            "UPDATE jobs SET heartbeat_at=? WHERE job_id=?",
            ((datetime.now(UTC) - timedelta(minutes=5)).isoformat(), job["job_id"]),
        )
        connection.commit()

    chat_jobs.resume_chat_jobs("demo", tmp_path, db_path=jobs_db)

    result = events.claim_run_message(
        "demo", "run-abandoned-chat", "loop-worker", kind="job_result_notice",
    )
    assert result is not None
    assert result["payload"]["state"] == "failed"
    assert result["payload"]["error_sha256"]
