"""Persistente Chat-Job-Zustaende und Event-Replay (OP-397)."""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

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


