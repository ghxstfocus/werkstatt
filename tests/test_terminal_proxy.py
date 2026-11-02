from __future__ import annotations

from typing import Any

from werkstatt import loop_renderer as renderer


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
        assert "Hallo Terminal" in capsys.readouterr().out
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
        assert len(events_a) == 1
        assert events_a[0]["type"] == "task_started"
        assert events_a[0]["nr"] == 2
        assert events_a[0]["total"] == 5
        assert events_a[0]["name"] == "Terminal-Proxy bauen"
        assert events_a[0]["project"] == "projekt-a"
        assert events_b == []
    finally:
        renderer.set_project("default")
        unsub_a()
        unsub_b()
