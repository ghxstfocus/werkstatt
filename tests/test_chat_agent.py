"""Tests fuer OP-231: chat_loop mit Mock-LLM."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from werkstatt import chat_agent
from werkstatt.chat_session import ChatSession


@pytest.fixture
def session(tmp_path: Path) -> ChatSession:
    return ChatSession("demo", "sess-1", db_pfad=tmp_path / "chat.db")


@pytest.fixture
def fake_llm(monkeypatch):
    antworten: list[dict[str, Any]] = []

    def _set(*items: dict[str, Any]) -> None:
        antworten.clear()
        antworten.extend(items)

    def _fake(messages, tools=None):
        if not antworten:
            raise AssertionError("fake_llm: keine Antwort mehr")
        return {"choices": [{"message": antworten.pop(0)}]}

    monkeypatch.setattr(chat_agent, "_deepseek_chat", _fake)
    return _set


def test_chat_loop_ohne_tool(session, fake_llm) -> None:
    fake_llm({"role": "assistant", "content": "Hallo!"})
    antwort = chat_agent.chat_loop(session, "Hi")
    assert antwort == "Hallo!"
    evs = session.load()
    assert [e["kind"] for e in evs] == ["user", "assistant"]
    assert evs[0]["payload"]["text"] == "Hi"
    assert evs[1]["payload"]["text"] == "Hallo!"


def test_chat_loop_mit_tool_call(session, fake_llm) -> None:
    fake_llm(
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": "c1",
                "type": "function",
                "function": {
                    "name": "read_file",
                    "arguments": json.dumps({"path": "pyproject.toml"}),
                },
            }],
        },
        {"role": "assistant", "content": "Datei gelesen."},
    )
    antwort = chat_agent.chat_loop(session, "Was steht drin?")
    assert "gelesen" in antwort
    kinds = [e["kind"] for e in session.load()]
    assert kinds == ["user", "tool_call", "tool_result", "assistant"]
    tr = next(e for e in session.load() if e["kind"] == "tool_result")
    assert tr["payload"]["tool_call_id"] == "c1"
    assert tr["payload"]["name"] == "read_file"
    assert len(tr["payload"]["content"]) > 0


def test_chat_loop_max_rounds(session, fake_llm) -> None:
    wieder = {
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": "cx",
            "type": "function",
            "function": {"name": "diagnose", "arguments": "{}"},
        }],
    }
    fake_llm(*([wieder] * 3))
    antwort = chat_agent.chat_loop(session, "loop", max_rounds=3)
    assert "max_rounds" in antwort


def test_chat_loop_unbekanntes_tool(session, fake_llm) -> None:
    fake_llm(
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": "bad",
                "type": "function",
                "function": {
                    "name": "write_file",
                    "arguments": json.dumps({"path": "x"}),
                },
            }],
        },
        {"role": "assistant", "content": "Konnte nicht schreiben."},
    )
    chat_agent.chat_loop(session, "schreib")
    tr = next(e for e in session.load() if e["kind"] == "tool_result")
    assert "nicht in Registry" in tr["payload"]["content"]


def test_chat_loop_ungueltiges_json_im_tool_call(session, fake_llm) -> None:
    fake_llm(
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": "u1",
                "type": "function",
                "function": {
                    "name": "read_file",
                    "arguments": "KEIN JSON",
                },
            }],
        },
        {"role": "assistant", "content": "ok"},
    )
    antwort = chat_agent.chat_loop(session, "x")
    assert antwort == "ok"


def test_on_chunk_callback_wird_gerufen(session, fake_llm) -> None:
    fake_llm({"role": "assistant", "content": "Antwort"})
    chunks: list[str] = []
    chat_agent.chat_loop(session, "x", on_chunk=chunks.append)
    assert chunks == ["Antwort"]


def test_on_tool_callbacks(session, fake_llm) -> None:
    fake_llm(
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": "c1",
                "type": "function",
                "function": {
                    "name": "read_file",
                    "arguments": json.dumps({"path": "pyproject.toml"}),
                },
            }],
        },
        {"role": "assistant", "content": "done"},
    )
    calls: list[tuple[str, dict]] = []
    results: list[tuple[str, str]] = []
    chat_agent.chat_loop(
        session, "x",
        on_tool_call=lambda n, a: calls.append((n, a)),
        on_tool_result=lambda n, r: results.append((n, r)),
    )
    assert calls and calls[0][0] == "read_file"
    assert calls[0][1] == {"path": "pyproject.toml"}
    assert results and results[0][0] == "read_file"
    assert len(results[0][1]) > 0


def test_baue_messages_aus_session(session) -> None:
    session.append("user", {"text": "a"})
    session.append("assistant", {"text": "b"})
    session.append("job_turn", {
        "job_id": "job-1",
        "user_text": "c",
        "assistant_text": "d",
    })
    msgs = chat_agent._baue_messages(session.load())
    assert msgs == [
        {"role": "user", "content": "a"},
        {"role": "assistant", "content": "b"},
        {"role": "user", "content": "c"},
        {"role": "assistant", "content": "d"},
    ]

def test_chat_tool_uses_explicit_project_root(session, fake_llm, tmp_path) -> None:
    (tmp_path / "project-only.txt").write_text(
        "ausgewaehltes Projekt", encoding="utf-8",
    )
    fake_llm(
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": "project-read",
                "type": "function",
                "function": {
                    "name": "read_file",
                    "arguments": json.dumps({"path": "project-only.txt"}),
                },
            }],
        },
        {"role": "assistant", "content": "gelesen"},
    )

    chat_agent.chat_loop(
        session, "lies die Datei",
        project_dir=tmp_path,
    )

    tr = next(e for e in session.load() if e["kind"] == "tool_result")
    assert tr["payload"]["content"] == "ausgewaehltes Projekt"


def test_system_prompt_routes_next_work_questions_through_selector() -> None:
    assert "next_op" in chat_agent._SYSTEM_PROMPT
    assert "Bei Mehrdeutigkeit fragst du" in chat_agent._SYSTEM_PROMPT
    assert "veraendert nichts" in chat_agent._SYSTEM_PROMPT

def test_system_prompt_requires_verified_file_line_citations() -> None:
    assert "grep" in chat_agent._SYSTEM_PROMPT
    assert "Zeichen-Offsets und keine Zeilennummern" in chat_agent._SYSTEM_PROMPT
    assert "Erfinde keine Zeilenangaben" in chat_agent._SYSTEM_PROMPT

def test_chat_loop_cancelled_before_request_does_not_call_llm(session) -> None:
    with pytest.raises(chat_agent.ChatCancelled):
        chat_agent.chat_loop(
            session, "Abbrechen", cancel_check=lambda: True,
        )

    assert session.load() == []

def test_chat_stream_stops_when_cancel_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests = pytest.importorskip("requests")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    checks = 0

    def _cancel() -> bool:
        nonlocal checks
        checks += 1
        return checks >= 3

    class _Response:
        closed = False

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            self.closed = True

        def raise_for_status(self) -> None:
            return None

        def iter_lines(self):
            yield b"data: {}"
            yield b"data: {}"

    response = _Response()
    monkeypatch.setattr(requests, "post", lambda *_args, **_kwargs: response)

    with pytest.raises(chat_agent.ChatCancelled):
        chat_agent._deepseek_chat_stream([], cancel_check=_cancel)

    assert response.closed is True



def test_debugger_mode_is_recorded_and_adds_debugger_only_tools(
    session, fake_llm, monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests_seen: list[tuple[list[dict[str, Any]], list[dict[str, Any]]]] = []

    def _capture(messages, tools=None):
        requests_seen.append((messages, tools or []))
        return {"choices": [{"message": {"role": "assistant", "content": "Diagnose."}}]}

    monkeypatch.setattr(chat_agent, "_deepseek_chat", _capture)
    chat_agent.chat_loop(session, "Untersuche den Fehler", mode="debugger")

    system_prompt = requests_seen[0][0][0]["content"]
    tool_names = {
        item["function"]["name"] for item in requests_seen[0][1]
    }
    user_event = next(event for event in session.load() if event["kind"] == "user")
    assert "write_temp_test" in system_prompt
    assert "pytest_run" in tool_names
    assert "read_file" in tool_names
    assert user_event["payload"]["mode"] == "debugger"
