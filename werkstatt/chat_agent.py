"""Chat-Agent (OP-231, ADR-0008). Eigener read-only Agent.

Eigener System-Prompt, eigener LLM-Loop, eigene Tool-Registry
(chat_tools.py). Nutzt ChatSession (OP-230) fuer Persistenz.
Token-Streaming ueber on_chunk-Callback.
"""
from __future__ import annotations

import json
import os
from collections.abc import Callable
from typing import Any

from werkstatt.chat_session import ChatSession
from werkstatt.chat_tools import CHAT_TOOLS, execute_tool, openai_schemas

__all__ = ["chat_loop"]

_DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
_DEFAULT_MODEL = "deepseek-chat"
_DEFAULT_MAX_ROUNDS = 5

_SYSTEM_PROMPT = """Du bist der Werkstatt-Chat-Agent. Der Nutzer \
arbeitet am Projekt "Werkstatt" (Coding-Loop, Gates, Tests). Du \
diagnostizierst und erklaerst. Du schreibst NIEMALS Dateien, committest \
NICHT, startest KEINE Loops. Dafuer gibt es den Coding-Loop, nicht dich.

Verfuegbare Tools (read-only): read_file, grep, git_log, git_diff, \
audit_query, pytest_collect, diagnose, read_status.

Wenn der Nutzer eine Frage zu Projektzustand, Tests, Diffs, Logs \
stellt: NUTZE die Tools statt zu raten. Zitiere konkrete Datei- und \
Commit-Referenzen. Wenn du unsicher bist, lies nach."""


def _baue_messages(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    msgs: list[dict[str, Any]] = []
    for ev in events:
        kind = ev.get("kind")
        p = ev.get("payload") or {}
        if kind == "user":
            msgs.append({"role": "user", "content": p.get("text", "")})
        elif kind == "assistant":
            msgs.append({"role": "assistant", "content": p.get("text", "")})
        elif kind == "tool_call":
            msgs.append({
                "role": "assistant",
                "content": None,
                "tool_calls": p.get("tool_calls", []),
            })
        elif kind == "tool_result":
            msgs.append({
                "role": "tool",
                "tool_call_id": p.get("tool_call_id", "?"),
                "content": p.get("content", ""),
            })
    return msgs


def _deepseek_chat_stream(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    on_chunk: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Echtes Token-Streaming. Ruft on_chunk pro Content-Delta."""
    import requests

    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY nicht gesetzt")
    body: dict[str, Any] = {
        "model": os.environ.get("DEEPSEEK_MODEL", _DEFAULT_MODEL),
        "messages": messages,
        "temperature": 0.0,
        "stream": True,
    }
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"

    content_acc = ""
    tool_calls_acc: dict[int, dict[str, Any]] = {}
    with requests.post(
        _DEEPSEEK_URL,
        json=body,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=300,
        stream=True,
    ) as resp:
        resp.raise_for_status()
        for raw in resp.iter_lines():
            if not raw:
                continue
            if not raw.startswith(b"data: "):
                continue
            data = raw[len(b"data: "):]
            if data == b"[DONE]":
                break
            try:
                obj = json.loads(data)
            except json.JSONDecodeError:
                continue
            choices = obj.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}
            if delta.get("content"):
                content_acc += delta["content"]
                if on_chunk is not None:
                    on_chunk(delta["content"])
            for tc in delta.get("tool_calls") or []:
                idx = int(tc.get("index", 0))
                slot = tool_calls_acc.setdefault(idx, {
                    "id": "",
                    "type": "function",
                    "function": {"name": "", "arguments": ""},
                })
                if tc.get("id"):
                    slot["id"] = tc["id"]
                fn = tc.get("function") or {}
                if fn.get("name"):
                    slot["function"]["name"] += fn["name"]
                if fn.get("arguments"):
                    slot["function"]["arguments"] += fn["arguments"]

    msg: dict[str, Any] = {"role": "assistant"}
    msg["content"] = content_acc or None
    if tool_calls_acc:
        msg["tool_calls"] = [tool_calls_acc[i] for i in sorted(tool_calls_acc)]
    return msg


def _deepseek_chat(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Non-streaming Wrapper. Test-Boundary (monkeypatch-Attr)."""
    return {"choices": [{"message": _deepseek_chat_stream(messages, tools, None)}]}


def chat_loop(
    session: ChatSession,
    message: str,
    tools: dict[str, dict[str, Any]] | None = None,
    mode: str = "read",
    on_chunk: Callable[[str], None] | None = None,
    on_tool_call: Callable[[str, dict[str, Any]], None] | None = None,
    on_tool_result: Callable[[str, str], None] | None = None,
    max_rounds: int = _DEFAULT_MAX_ROUNDS,
) -> str:
    """User-Nachricht -> LLM-Loop -> Assistant-Antwort."""
    tools = tools if tools is not None else CHAT_TOOLS
    session.append("user", {"text": message})
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        *_baue_messages(session.load()),
    ]
    schemas = openai_schemas(tools, mode=mode)

    for _ in range(max_rounds):
        resp = _deepseek_chat(messages, tools=schemas)
        msg = resp["choices"][0]["message"]
        tool_calls = msg.get("tool_calls") or []
        if not tool_calls:
            antwort = str(msg.get("content") or "")
            if on_chunk is not None and antwort:
                on_chunk(antwort)
            session.append("assistant", {"text": antwort})
            return antwort

        session.append("tool_call", {"tool_calls": tool_calls})
        messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": tool_calls,
        })
        for tc in tool_calls:
            tc_id = tc.get("id", "?")
            fn = tc.get("function") or {}
            name = str(fn.get("name", ""))
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            if not isinstance(args, dict):
                args = {}
            if on_tool_call is not None:
                on_tool_call(name, args)
            ergebnis = execute_tool(name, args, tools, mode=mode)
            if on_tool_result is not None:
                on_tool_result(name, ergebnis)
            session.append("tool_result", {
                "tool_call_id": tc_id,
                "name": name,
                "content": ergebnis,
            })
            messages.append({
                "role": "tool",
                "tool_call_id": tc_id,
                "content": ergebnis,
            })

    fail = f"[chat_loop: max_rounds={max_rounds} erreicht, keine finale Antwort]"
    session.append("assistant", {"text": fail})
    return fail
