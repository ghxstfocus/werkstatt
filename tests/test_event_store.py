"""Tests fuer den Event-Store (OP-122): append+query, kind-Filter, since_seq-Export."""

import json
from pathlib import Path

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

