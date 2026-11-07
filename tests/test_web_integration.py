from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from werkstatt.web.app import create_app


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app())


def test_static_mount(client):
    r = client.get("/static/layout.css")
    assert r.status_code == 200
    assert "text/css" in r.headers.get("content-type", "")


def test_layout_served(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "<!DOCTYPE" in r.text
    assert "tabs.js" in r.text
    assert "terminal.js" in r.text
    assert "audit.js" in r.text
    assert "chat.js" in r.text
    assert "layout.css" in r.text


def test_ws_terminal(client):
    # Endpoint akzeptiert WS-Connect, sendet aber keine Antwort auf
    # Client-Nachrichten. Antworten kommen nur als Emitter-Events
    # (siehe terminal_proxy._sender -> queue.get()). Test verifiziert
    # den Connect-Handshake, nicht Ping-Pong (existiert nicht).
    with client.websocket_connect("/ws/terminal/werkstatt") as websocket:
        websocket.send_json({"type": "ping"})
        # Kein receive_json(): Endpoint antwortet nicht, das waere ein
        # Deadlock. Bei erfolgreichem with-Exit ist der Connect ok.
        websocket.close()


def test_chat_post(client):
    """OP-231: alte /api/chat/{id}-Route ersetzt durch /chat/new."""
    r = client.post("/api/projects/werkstatt/chat/new")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    assert "session_id" in r.json()


def test_audit_history(client):
    r = client.get("/api/projects/werkstatt/audit")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
