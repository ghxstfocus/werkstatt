"""Crash-window regression tests for run inbox checkpoint projection."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

from werkstatt.event_store import EventStore
from werkstatt.phases.tasks import _persist_run_checkpoint


def test_reclaimed_notice_is_not_projected_twice_after_checkpoint_before_ack(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = EventStore(tmp_path / "events.db")
    store.create_run_record("demo", "run-inbox-replay", "Continue task")
    seq = store.enqueue_run_message(
        "demo",
        "run-inbox-replay",
        "chat-job:job-1",
        "job_notice",
        {"job_id": "job-1", "session_id": "session-1", "mode": "read"},
    )
    phase_state = SimpleNamespace(data={
        "tasks": [{"id": "task-1", "status": "done"}],
    })
    acknowledge = store.acknowledge_run_message
    monkeypatch.setattr(
        store,
        "acknowledge_run_message",
        lambda *_args: False,
    )

    with pytest.raises(RuntimeError, match="Run-Inbox-Lease verloren"):
        _persist_run_checkpoint(
            store,
            "demo",
            "run-inbox-replay",
            phase_state,
            {"id": "task-2"},
        )

    record = store.get_run_record("demo", "run-inbox-replay")
    assert record is not None
    assert record["checkpoint"]["inbox_offset"] == seq
    assert len(record["checkpoint"]["job_notices"]) == 1

    # Simulate lease expiry after process death between checkpoint write and ack.
    with sqlite3.connect(store.db_pfad) as connection:
        connection.execute(
            "UPDATE run_inbox SET lease_until=0 WHERE project=? AND run_id=?",
            ("demo", "run-inbox-replay"),
        )
    monkeypatch.setattr(store, "acknowledge_run_message", acknowledge)

    _persist_run_checkpoint(
        store,
        "demo",
        "run-inbox-replay",
        phase_state,
        {"id": "task-2"},
    )

    recovered = store.get_run_record("demo", "run-inbox-replay")
    assert recovered is not None
    assert recovered["checkpoint"]["inbox_offset"] == seq
    assert len(recovered["checkpoint"]["job_notices"]) == 1
    assert store.claim_run_message("demo", "run-inbox-replay", "next-worker") is None
