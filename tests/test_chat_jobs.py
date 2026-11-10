"""Persistente Chat-Job-Zustaende und Event-Replay (OP-397)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from werkstatt.chat_jobs import ChatJobStore


def test_create_is_idempotent_and_survives_store_reopen(tmp_path: Path) -> None:
    db = tmp_path / "jobs.db"
    first, created = ChatJobStore(db).create(
        "session-a", "Pruefe Status", "read", "request-key-0001",
    )
    duplicate, duplicate_created = ChatJobStore(db).create(
        "session-a", "Pruefe Status", "read", "request-key-0001",
    )

    assert created is True
    assert duplicate_created is False
    assert duplicate["job_id"] == first["job_id"]
    assert duplicate["state"] == "queued"
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


def test_claim_serializes_turns_within_one_session(tmp_path: Path) -> None:
    store = ChatJobStore(tmp_path / "jobs.db")
    first, _ = store.create("session-a", "Erste Frage", "read", "request-key-a001")
    second, _ = store.create("session-a", "Zweite Frage", "read", "request-key-a002")

    assert store.claim(first["job_id"]) is True
    assert store.claim(second["job_id"]) is False
    assert store.finish(first["job_id"], answer="Erledigt") is True
    assert store.claim(second["job_id"]) is True


def test_jobs_in_different_sessions_can_run_in_parallel(tmp_path: Path) -> None:
    store = ChatJobStore(tmp_path / "jobs.db")
    first, _ = store.create("session-a", "Frage A", "read", "request-key-b001")
    second, _ = store.create("session-b", "Frage B", "read", "request-key-b002")

    assert store.claim(first["job_id"]) is True
    assert store.claim(second["job_id"]) is True


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
        def submit(self, *_args: object) -> Future[None]:
            future: Future[None] = Future()
            future.set_result(None)
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
    assert store.heartbeat(job["job_id"], "worker-a") is True

