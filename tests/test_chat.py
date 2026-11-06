"""Tests fuer werkstatt.web.chat (OP-084 Endpoint-Verdrahtung)."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from werkstatt.web import auth
    from werkstatt.web.app import create_app
    auth.set_auth_disabled(True)
    return TestClient(create_app())


def test_post_chat_antwort_feld(client):
    """POST /api/chat/{chat_id} liefert antwort-Feld.

    Mockt chat_agent._deepseek_chat — kein Live-LLM-Call im Test.
    """
    from werkstatt.web import chat_agent
    calls = []
    def fake_chat(messages, tools=None):
        calls.append(messages)
        if len(calls) == 1:
            return {"choices": [{"message": {
                "role": "assistant", "content": "",
                "tool_calls": [{
                    "id": "tc1", "type": "function",
                    "function": {"name": "list_open_ops",
                                 "arguments": "{}"},
                }],
            }}]}
        return {"choices": [{"message": {
            "role": "assistant",
            "content": "Die naechste offene OP ist OP-045.",
        }}]}

    with patch.object(chat_agent, "_deepseek_chat", fake_chat):
        r = client.post("/api/chat/admin", json={"text": "? welche OPs sind offen"})

    assert r.status_code == 200
    daten = r.json()
    assert "antwort" in daten
    assert isinstance(daten["antwort"], str)
    assert "OP-" in daten["antwort"]


def test_post_chat_unbekannter_chat(client):
    """Unbekannter chat_id -> 404."""
    r = client.post("/api/chat/unknown", json={"text": "test"})
    assert r.status_code == 404


def test_post_chat_ruft_chat_agent(client):
    """post_chat delegiert an chat_agent.verarbeite."""
    with patch("werkstatt.web.chat_agent.verarbeite") as mock:
        mock.return_value = "MOCK-ANTWORT"
        r = client.post("/api/chat/admin", json={"text": "hallo"})
        assert r.status_code == 200
        assert r.json()["antwort"] == "MOCK-ANTWORT"
        mock.assert_called_once()
        # Erster Parameter ist der Text
        args, _kwargs = mock.call_args
        assert args[0] == "hallo"


def test_post_chat_agent_crash_wird_gefangen(client):
    """Crash im chat_agent -> Endpoint antwortet trotzdem 200."""
    with patch("werkstatt.web.chat_agent.verarbeite") as mock:
        mock.side_effect = RuntimeError("test-crash")
        r = client.post("/api/chat/admin", json={"text": "hallo"})
        assert r.status_code == 200
        daten = r.json()
        assert "Chat-Agent-Fehler" in daten["antwort"]
        assert "RuntimeError" in daten["antwort"]
