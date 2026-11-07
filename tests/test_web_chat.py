"""Tests fuer OP-231: Chat-Endpoints in web/app.py."""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def app_client(tmp_path: Path, monkeypatch):
    from fastapi.testclient import TestClient

    from werkstatt import chat_session as cs_mod
    from werkstatt.web import auth
    from werkstatt.web.app import create_app

    monkeypatch.setattr(auth, "is_auth_disabled", lambda: True)
    monkeypatch.setattr(
        cs_mod, "_db_pfad",
        lambda projekt: tmp_path / f"{projekt}-chat.db",
    )
    return TestClient(create_app())


def test_sessions_leer(app_client) -> None:
    r = app_client.get("/api/projects/demo/chat/sessions")
    assert r.status_code == 200
    assert r.json() == {"sessions": []}


def test_new_liefert_session_id(app_client) -> None:
    r = app_client.post("/api/projects/demo/chat/new")
    assert r.status_code == 200
    sid = r.json()["session_id"]
    assert isinstance(sid, str) and len(sid) > 0


def test_new_und_sessions_liste(app_client) -> None:
    sid = app_client.post("/api/projects/demo/chat/new").json()["session_id"]
    from werkstatt.chat_session import ChatSession
    ChatSession("demo", sid).append("user", {"text": "hi"})
    r = app_client.get("/api/projects/demo/chat/sessions")
    assert r.status_code == 200
    assert r.json()["sessions"] == [sid]


def test_history_leer(app_client) -> None:
    sid = app_client.post("/api/projects/demo/chat/new").json()["session_id"]
    r = app_client.get(
        f"/api/projects/demo/chat/history?session_id={sid}"
    )
    assert r.status_code == 200
    assert r.json() == {"events": []}


def test_history_mit_events(app_client) -> None:
    from werkstatt.chat_session import ChatSession
    sid = app_client.post("/api/projects/demo/chat/new").json()["session_id"]
    ChatSession("demo", sid).append("user", {"text": "frage"})
    r = app_client.get(
        f"/api/projects/demo/chat/history?session_id={sid}"
    )
    assert r.status_code == 200
    events = r.json()["events"]
    assert len(events) == 1
    assert events[0]["kind"] == "user"
    assert events[0]["payload"]["text"] == "frage"


def test_history_ungueltige_session_id(app_client) -> None:
    r = app_client.get(
        "/api/projects/demo/chat/history?session_id=../../etc/passwd"
    )
    assert r.status_code == 400


def test_send_ohne_session_id(app_client) -> None:
    r = app_client.post(
        "/api/projects/demo/chat",
        json={"message": "hi"},
    )
    assert r.status_code == 400


def test_send_ohne_message(app_client) -> None:
    sid = app_client.post("/api/projects/demo/chat/new").json()["session_id"]
    r = app_client.post(
        "/api/projects/demo/chat",
        json={"session_id": sid},
    )
    assert r.status_code == 400


def test_send_ungueltiger_mode(app_client) -> None:
    sid = app_client.post("/api/projects/demo/chat/new").json()["session_id"]
    r = app_client.post(
        "/api/projects/demo/chat",
        json={"session_id": sid, "message": "hi", "mode": "admin"},
    )
    assert r.status_code == 400


def test_send_ohne_api_key_liefert_500(app_client, monkeypatch) -> None:
    from werkstatt import chat_agent as ca

    def _boom(*_a, **_k):
        raise RuntimeError("DEEPSEEK_API_KEY nicht gesetzt")

    monkeypatch.setattr(ca, "chat_loop", _boom)
    sid = app_client.post("/api/projects/demo/chat/new").json()["session_id"]
    r = app_client.post(
        "/api/projects/demo/chat",
        json={"session_id": sid, "message": "hi"},
    )
    assert r.status_code == 500
    assert "API_KEY" in r.json()["detail"]


def test_send_mit_mock_liefert_antwort(app_client, monkeypatch) -> None:
    from werkstatt import chat_agent as ca

    def _fake(session, message, mode="read", **_k):
        session.append("user", {"text": message})
        session.append("assistant", {"text": "antwort"})
        return "antwort"

    monkeypatch.setattr(ca, "chat_loop", _fake)
    sid = app_client.post("/api/projects/demo/chat/new").json()["session_id"]
    r = app_client.post(
        "/api/projects/demo/chat",
        json={"session_id": sid, "message": "hi"},
    )
    assert r.status_code == 200
    assert r.json()["session_id"] == sid
    assert r.json()["antwort"] == "antwort"
