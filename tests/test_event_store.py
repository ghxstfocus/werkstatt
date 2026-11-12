"""Tests fuer den Event-Store (OP-122): append+query, kind-Filter, since_seq-Export."""

import json
import time
from pathlib import Path

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
