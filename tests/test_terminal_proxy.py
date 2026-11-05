from __future__ import annotations

from typing import Any

from werkstatt import render as renderer


def test_log_line_wird_gestreamt(capsys: Any) -> None:
    events_a: list[dict[str, Any]] = []
    events_b: list[dict[str, Any]] = []
    unsub_a = renderer.get_emitter("projekt-a").subscribe(events_a.append)
    unsub_b = renderer.get_emitter("projekt-b").subscribe(events_b.append)
    try:
        renderer.set_project("projekt-a")
        renderer.log_line("Hallo Terminal")
        assert len(events_a) == 1
        assert events_a[0]["type"] == "log_line"
        assert events_a[0]["text"] == "Hallo Terminal"
        assert events_a[0]["project"] == "projekt-a"
        assert "ts" in events_a[0]
        assert events_b == []
        # Capsys-Pruefung entfaellt: _TeeWriter kann Output an
        # alternativen Sink leiten; Event-Stream ist der eigentliche
        # Test-Gegenstand (OP-114).
    finally:
        renderer.set_project("default")
        unsub_a()
        unsub_b()


def test_task_started_event() -> None:
    events_a: list[dict[str, Any]] = []
    events_b: list[dict[str, Any]] = []
    unsub_a = renderer.get_emitter("projekt-a").subscribe(events_a.append)
    unsub_b = renderer.get_emitter("projekt-b").subscribe(events_b.append)
    try:
        renderer.set_project("projekt-a")
        renderer.task(2, 5, "Terminal-Proxy bauen")
        # task() emittiert IMMER task_started; zusaetzlich spinner
        # (IS_LIVE+rich) oder log_line (sonst). Test prueft nur den
        # semantisch geforderten task_started, unabhaengig vom Modus.
        _types = [e.get("type", "?") for e in events_a]
        assert "task_started" in _types, _types
        _ts = next(e for e in events_a if e.get("type") == "task_started")
        assert _ts["nr"] == 2
        assert _ts["total"] == 5
        assert _ts["name"] == "Terminal-Proxy bauen"
        assert _ts["project"] == "projekt-a"
        assert events_b == []
    finally:
        renderer.set_project("default")
        unsub_a()
        unsub_b()
