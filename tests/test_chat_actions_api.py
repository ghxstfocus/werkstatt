"""API tests for chat initiated, explicitly confirmed loop actions."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest


def test_confirmed_chat_action_uses_control_api_once(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from werkstatt import chat_session
    from werkstatt.web import app as app_modul

    if app_modul.os.name != "posix":
        pytest.skip("Loop-Pause wird nur unter POSIX unterstuetzt")
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    monkeypatch.setattr(app_modul, "_PROJECTS_BASE", tmp_path)
    db_path = tmp_path / "sessions.db"
    monkeypatch.setattr(chat_session, "_db_pfad", lambda _project: db_path)

    session_id = "a" * 32
    proposal_id = "b" * 32
    session = chat_session.ChatSession("demo", session_id, db_pfad=db_path)
    session.append("loop_action_proposed", {
        "proposal_id": proposal_id,
        "project": "demo",
        "action": "pause",
        "arguments": {},
        "summary": "Loop pausieren",
        "expires_at": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
    })

    process = SimpleNamespace(pid=12345, poll=lambda: None)
    monkeypatch.setattr(app_modul, "_PAUSIERTE_LOOPS", set())
    monkeypatch.setattr(app_modul, "_LOOP_RUN_IDS", {"demo": "demo-run"})
    monkeypatch.setitem(app_modul._LAUFENDE_LOOPS, "demo", process)
    monkeypatch.setattr(app_modul.os, "killpg", lambda *_args: calls.append(_args))
    monkeypatch.setattr(app_modul, "_audit_web_loop_event", lambda *_args: True)
    monkeypatch.setattr(app_modul, "_loop_registry", lambda: SimpleNamespace(
        set_state=lambda *_args: None,
        read=lambda _project: None,
    ))
    calls: list[tuple[Any, ...]] = []

    response = TestClient(app_modul.app).post(
        f"/api/projects/demo/chat/actions/{proposal_id}",
        json={"session_id": session_id, "decision": "confirm"},
    )
    assert response.status_code == 200
    assert response.json()["state"] == "completed"
    assert calls

    repeated = TestClient(app_modul.app).post(
        f"/api/projects/demo/chat/actions/{proposal_id}",
        json={"session_id": session_id, "decision": "confirm"},
    )
    assert repeated.status_code == 200
    assert repeated.json()["state"] == "completed"
    assert len(calls) == 1


def test_rejected_chat_action_has_no_loop_side_effect(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from werkstatt import chat_session
    from werkstatt.web import app as app_modul

    monkeypatch.setattr(app_modul, "_PROJECTS_BASE", tmp_path)
    db_path = tmp_path / "sessions.db"
    monkeypatch.setattr(chat_session, "_db_pfad", lambda _project: db_path)
    session_id = "c" * 32
    proposal_id = "d" * 32
    session = chat_session.ChatSession("demo", session_id, db_pfad=db_path)
    session.append("loop_action_proposed", {
        "proposal_id": proposal_id,
        "project": "demo",
        "action": "stop",
        "arguments": {},
        "expires_at": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
    })

    response = TestClient(app_modul.app).post(
        f"/api/projects/demo/chat/actions/{proposal_id}",
        json={"session_id": session_id, "decision": "reject"},
    )
    assert response.status_code == 200
    assert response.json()["state"] == "rejected"
    assert [event["kind"] for event in session.load()][-1] == "loop_action_rejected"
