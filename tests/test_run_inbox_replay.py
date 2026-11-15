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
    assert record["checkpoint"]["job_notice_offset"] == seq
    assert "inbox_offset" not in record["checkpoint"]
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
    assert recovered["checkpoint"]["job_notice_offset"] == seq
    assert len(recovered["checkpoint"]["job_notices"]) == 1
    assert store.claim_run_message("demo", "run-inbox-replay", "next-worker") is None


def test_job_notice_consumer_does_not_consume_questions_or_controls(
    tmp_path: Path,
) -> None:
    store = EventStore(tmp_path / "events.db")
    store.create_run_record("demo", "run-inbox-kinds", "Continue task")
    question_seq = store.enqueue_run_message(
        "demo",
        "run-inbox-kinds",
        "question-1",
        "question",
        {"text": "What changed?"},
    )
    notice_seq = store.enqueue_run_message(
        "demo",
        "run-inbox-kinds",
        "job-1",
        "job_notice",
        {"job_id": "job-1", "session_id": "session-1", "mode": "read"},
    )
    phase_state = SimpleNamespace(data={"tasks": []})

    _persist_run_checkpoint(
        store,
        "demo",
        "run-inbox-kinds",
        phase_state,
        None,
    )

    record = store.get_run_record("demo", "run-inbox-kinds")
    assert record is not None
    checkpoint = record["checkpoint"]
    assert checkpoint["job_notice_offset"] == notice_seq
    assert "inbox_offset" not in checkpoint
    assert [item["seq"] for item in checkpoint["job_notices"]] == [notice_seq]

    # The job-notice consumer must leave the other message for its own consumer.
    question = store.claim_run_message(
        "demo", "run-inbox-kinds", "question-worker", kind="question",
    )
    assert question is not None
    assert question["seq"] == question_seq
    assert question["payload"] == {"text": "What changed?"}


def test_checkpoint_preserves_more_than_fifty_unresolved_chat_followups(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from werkstatt.phases import tasks

    store = EventStore(tmp_path / "events.db")
    store.create_run_record(
        "demo", "run-many-followups", "Main objective", base_commit="a" * 40,
    )
    for index in range(60):
        proposal_id = f"proposal-{index}"
        store.enqueue_run_message(
            "demo",
            "run-many-followups",
            f"chat-followup:{proposal_id}",
            "chat_followup_request",
            {
                "proposal_id": proposal_id,
                "project": "demo",
                "session_id": "session-many",
                "parent_run_id": "run-many-followups",
                "base_commit": "a" * 40,
                "request": f"Request {index}",
            },
        )
    monkeypatch.setattr(tasks, "audit", lambda *_args, **_kwargs: True)
    phase_state = SimpleNamespace(data={"tasks": []})

    for _ in range(3):
        _persist_run_checkpoint(
            store,
            "demo",
            "run-many-followups",
            phase_state,
            None,
        )

    record = store.get_run_record("demo", "run-many-followups")
    assert record is not None
    requests = record["checkpoint"]["chat_followup_requests"]
    assert len(requests) == 60
    assert {item["proposal_id"] for item in requests} == {
        f"proposal-{index}" for index in range(60)
    }
    assert all(item["status"] == "received" for item in requests)
