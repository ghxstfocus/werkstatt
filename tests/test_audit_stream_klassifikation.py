"""OP-321: JSONL-Trennung stream vs. semantic + event_id."""
import json
from pathlib import Path


def _list_jsonl(tmp_path, prefix):
    d = tmp_path / "audit-logs"
    if not d.exists():
        return []
    return sorted(d.glob(f"{prefix}*.jsonl"))


def _read(pfad):
    return [json.loads(line) for line in pfad.read_text().splitlines() if line.strip()]


def test_stream_kinds_vollstaendig():
    from werkstatt.audit import _STREAM_KINDS
    assert _STREAM_KINDS == frozenset({
        "log_line", "progress", "spinner",
        "heartbeat", "task_started", "task_done",
    })


def test_semantic_geht_nach_agent_pipeline(tmp_path, monkeypatch):
    from werkstatt import audit as A
    monkeypatch.setattr(A, "_werkstatt_home", lambda: tmp_path)
    A.audit("loop_ended", {"erfolg": True}, Path("."), "test")
    assert len(_list_jsonl(tmp_path, "agent-pipeline")) == 1
    assert _list_jsonl(tmp_path, "stream") == []
    events = _read(_list_jsonl(tmp_path, "agent-pipeline")[0])
    assert len(events) == 1
    assert events[0]["kind"] == "loop_ended"
    assert "event_id" in events[0]
    assert len(events[0]["event_id"]) == 16


def test_stream_geht_nach_stream_jsonl(tmp_path, monkeypatch):
    from werkstatt import audit as A
    monkeypatch.setattr(A, "_werkstatt_home", lambda: tmp_path)
    A.stream("log_line", {"text": "x"}, Path("."), "test")
    assert len(_list_jsonl(tmp_path, "stream")) == 1
    assert _list_jsonl(tmp_path, "agent-pipeline") == []
    events = _read(_list_jsonl(tmp_path, "stream")[0])
    assert events[0]["kind"] == "log_line"
    assert "event_id" in events[0]


def test_stream_fail_closed_semantic(tmp_path, monkeypatch):
    """Unbekannter Kind via stream() landet trotzdem in Semantic."""
    from werkstatt import audit as A
    monkeypatch.setattr(A, "_werkstatt_home", lambda: tmp_path)
    A.stream("loop_ended", {"erfolg": True}, Path("."), "test")
    assert len(_list_jsonl(tmp_path, "agent-pipeline")) == 1
    assert _list_jsonl(tmp_path, "stream") == []


def test_event_id_deterministisch():
    from werkstatt.audit import _event_id
    a = _event_id("run1", "aid1")
    b = _event_id("run1", "aid1")
    c = _event_id("run2", "aid1")
    d = _event_id("run1", "aid2")
    assert a == b
    assert a != c
    assert a != d
    assert len(a) == 16
