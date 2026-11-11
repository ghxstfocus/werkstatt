"""Chat-Agent (OP-231, ADR-0008). Eigener read-only Agent.

Eigener System-Prompt, eigener LLM-Loop, eigene Tool-Registry
(chat_tools.py). Nutzt ChatSession (OP-230) fuer Persistenz.
Token-Streaming ueber on_chunk-Callback.
"""
from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from werkstatt.chat_session import ChatSession
from werkstatt.chat_tools import CHAT_TOOLS, execute_tool, openai_schemas
from werkstatt.model_routing import route_for_role

__all__ = ["chat_loop"]

_DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
_DEFAULT_MAX_ROUNDS = 5


class ChatCancelled(RuntimeError):
    """Chat-Auftrag wurde kooperativ abgebrochen."""


def _check_cancel(cancel_check: Callable[[], bool] | None) -> None:
    if cancel_check is not None and cancel_check():
        raise ChatCancelled("Chat-Auftrag abgebrochen")


_SYSTEM_PROMPT = """Du bist der Chat-Agent fuer das aktuell ausgewaehlte Projekt.
Du untersuchst das Repo mit projektgebundenen Tools und erklaerst deine Aussagen
mit Datei-, Zeilen-, Run- oder Test-Belegen. Fuer Dateizeilen nutze grep, um den
genauen Pfad und die Zeilennummer zu verifizieren; read_file start/end sind
Zeichen-Offsets und keine Zeilennummern. Erfinde keine Zeilenangaben. Wenn ein
Beleg fehlt, sage das offen. Du schreibst keine Dateien und commitest nicht.
Loop-Steuerung darfst du nur ueber request_loop_action anfragen;
dieses Tool legt ausschliesslich einen befristeten Vorschlag an und fuehrt nichts aus.

Verfuegbare Tools: read_file, grep, git_log, git_diff, audit_query,
pytest_collect, diagnose, read_status, next_op und request_loop_action.

Wenn der Nutzer nach offenen OPs oder dem naechsten sinnvollen Arbeitsschritt
fragt, nutze next_op. Erklaere Kandidaten, Abhaengigkeiten, Pruefnachweise
und Ausschlussgruende aus der Tool-Antwort. Bei Mehrdeutigkeit fragst du,
welchen Kandidaten der Nutzer meint. Erfinde keine Prioritaet und behaupte
keine Freigabe. Das Tool startet keinen Run und veraendert nichts.

Wenn der Nutzer einen Loop starten, pausieren, fortsetzen oder stoppen will,
rufe request_loop_action mit der konkret gemeinten Aktion auf. Starte oder
veraendere niemals selbst etwas, behaupte keine Freigabe und bitte den Nutzer,
die angezeigte konkrete Aktion in der UI zu bestaetigen. Bei einem Start ohne
konkreten Auftrag muss ein eindeutiger, startfaehiger STATUS-OP aufgeloest sein;
bei Mehrdeutigkeit frage nach.

Bei Projekt-, Test-, Diff- oder Laufzeitfragen nutze die passenden Tools
statt zu raten. Wenn Belege fehlen, sage, was noch geprueft werden muss."""


def _baue_messages(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    msgs: list[dict[str, Any]] = []
    for ev in events:
        kind = ev.get("kind")
        p = ev.get("payload") or {}
        if kind == "user":
            msgs.append({"role": "user", "content": p.get("text", "")})
        elif kind == "assistant":
            msgs.append({"role": "assistant", "content": p.get("text", "")})
        elif kind == "job_turn":
            msgs.extend([
                {"role": "user", "content": p.get("user_text", "")},
                {"role": "assistant", "content": p.get("assistant_text", "")},
            ])
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
    cancel_check: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    """Echtes Token-Streaming. Ruft on_chunk pro Content-Delta."""
    import requests

    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY nicht gesetzt")
    _route = route_for_role("chat")
    body: dict[str, Any] = {
        "model": _route.model,
        "thinking": {"type": _route.thinking},
        "messages": messages,
        "temperature": 0.0,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    if tools:
        body["tools"] = tools
        body["tool_choice"] = "auto"

    _check_cancel(cancel_check)
    content_acc = ""
    tool_calls_acc: dict[int, dict[str, Any]] = {}
    usage_acc: dict[str, Any] | None = None
    _provider_model = _route.model
    with requests.post(
        _DEEPSEEK_URL,
        json=body,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=(10, 30),
        stream=True,
    ) as resp:
        resp.raise_for_status()
        for raw in resp.iter_lines():
            _check_cancel(cancel_check)
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
            if obj.get("model"):
                _provider_model = str(obj["model"])
            _u = obj.get("usage")
            if isinstance(_u, dict) and _u.get("total_tokens"):
                usage_acc = {
                    "prompt_tokens": int(_u.get("prompt_tokens", 0) or 0),
                    "completion_tokens": int(_u.get("completion_tokens", 0) or 0),
                    "total_tokens": int(_u.get("total_tokens", 0) or 0),
                    "model": _route.model,
                    "provider_model": _provider_model,
                }
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

    _check_cancel(cancel_check)
    msg: dict[str, Any] = {"role": "assistant"}
    msg["content"] = content_acc or None
    if tool_calls_acc:
        msg["tool_calls"] = [tool_calls_acc[i] for i in sorted(tool_calls_acc)]
    if usage_acc is not None:
        msg["_usage"] = usage_acc
    return msg


def _deepseek_chat(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    """Non-streaming Wrapper. Test-Boundary (monkeypatch-Attr)."""
    inner = _deepseek_chat_stream(messages, tools, None, cancel_check)
    usage = inner.pop("_usage", None)
    return {"choices": [{"message": inner}], "usage": usage}


def chat_loop(
    session: ChatSession,
    message: str,
    tools: dict[str, dict[str, Any]] | None = None,
    mode: str = "read",
    on_chunk: Callable[[str], None] | None = None,
    on_tool_call: Callable[[str, dict[str, Any]], None] | None = None,
    on_tool_result: Callable[[str, str], None] | None = None,
    max_rounds: int = _DEFAULT_MAX_ROUNDS,
    project_dir: Path | str | None = None,
    request_id: str | None = None,
    cancel_check: Callable[[], bool] | None = None,
    origin_session_id: str | None = None,
) -> str:
    """User-Nachricht -> LLM-Loop -> Assistant-Antwort."""
    tools = tools if tools is not None else CHAT_TOOLS
    _check_cancel(cancel_check)
    user_payload: dict[str, Any] = {"text": message}
    if request_id is not None:
        user_payload["job_id"] = request_id
    session.append("user", user_payload)
    _project_context = f"Aktives Projekt: {session.project}."
    if project_dir is not None:
        _project_context += (
            f" Projektwurzel: {Path(project_dir).expanduser().resolve()}."
        )
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _SYSTEM_PROMPT + "\n" + _project_context},
        *_baue_messages(session.load()),
    ]
    schemas = openai_schemas(tools, mode=mode)

    for _ in range(max_rounds):
        _check_cancel(cancel_check)
        if cancel_check is None:
            resp = _deepseek_chat(messages, tools=schemas)
        else:
            resp = _deepseek_chat(
                messages, tools=schemas, cancel_check=cancel_check,
            )
        _usage = resp.get("usage")
        if _usage and _usage.get("total_tokens"):
            session.append("token_usage", _usage)
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
            _check_cancel(cancel_check)
            if on_tool_call is not None:
                on_tool_call(name, args)
            ergebnis = execute_tool(
                name, args, tools, mode=mode,
                project_dir=project_dir, project_name=session.project,
                session_id=origin_session_id or session.session_id,
            )
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
