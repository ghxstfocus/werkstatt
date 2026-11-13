"""Chat-Agent (OP-231, ADR-0008). Eigener read-only Agent.

Eigener System-Prompt, eigener LLM-Loop, eigene Tool-Registry
(chat_tools.py). Nutzt ChatSession (OP-230) fuer Persistenz.
Token-Streaming ueber on_chunk-Callback.
"""
from __future__ import annotations

import hashlib
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
_DEFAULT_MAX_ROUNDS: int | None = None


class ChatCancelled(RuntimeError):
    """Chat-Auftrag wurde kooperativ abgebrochen."""


def _check_cancel(cancel_check: Callable[[], bool] | None) -> None:
    if cancel_check is not None and cancel_check():
        raise ChatCancelled("Chat-Auftrag abgebrochen")


def _repeated_tool_cycle(
    fingerprints: list[str], *, max_period: int = 3,
) -> tuple[str, ...] | None:
    """Find repeated suffix cycles without imposing a total round limit."""
    for period in range(1, min(max_period, len(fingerprints) // 2) + 1):
        previous = fingerprints[-2 * period:-period]
        current = fingerprints[-period:]
        if previous == current:
            return tuple(current)
    return None


_DEBUGGER_PROMPT = """Der Mensch hat diesen Turn im Debug-Modus gestartet.
Du darfst Projekt-Tests mit pytest_run ausfuehren und temporaere Tests
ausschliesslich unter .werkstatt/temp_tests/ mit write_temp_test anlegen.
Du darfst keine Produktionsdatei bearbeiten. Gate-Daten sind Kontext:
du beantwortest oder bestaetigst kein Gate. Ein Patch braucht spaeter eine
separate, einmalige Freigabe fuer den exakten Diff und bleibt an Projekt
und Run gebunden. Wenn du einen konkreten Fix vorschlaegst, nutze
propose_debugger_fix mit belegtem Run, vollstaendigem Git-Diff,
Dateiliste und Ursache. Das Tool speichert nur einen Vorschlag; schreibe
niemals Produktionsdateien. Erklaere danach Hash und Freigabeschritt."""

_SYSTEM_PROMPT = """Du bist der Chat-Agent fuer das aktuell ausgewaehlte Projekt.
Du untersuchst das Repo mit projektgebundenen Tools und erklaerst deine Aussagen
mit Datei-, Zeilen-, Run- oder Test-Belegen. Fuer Dateizeilen nutze grep, um den
genauen Pfad und die Zeilennummer zu verifizieren; read_file start/end sind
Zeichen-Offsets und keine Zeilennummern. Erfinde keine Zeilenangaben. Wenn ein
Beleg fehlt, sage das offen. Du schreibst keine Dateien und commitest nicht.
Loop-Steuerung darfst du nur ueber request_loop_action anfragen;
dieses Tool legt ausschliesslich einen befristeten Vorschlag an und fuehrt nichts aus.

Verfuegbare Tools: read_file, grep, git_log, git_diff, audit_query,
pytest_collect, diagnose, read_status, next_op, request_loop_action und im
Debug-Modus propose_debugger_fix.

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


_CHAT_HISTORY_CHAR_BUDGET = 24_000
_CHAT_HISTORY_COMPACT_NOTE = (
    "Aeltere Dialogturns oder Werkzeugdetails wurden fuer das Kontextbudget "
    "gekuerzt. Der vollstaendige Verlauf bleibt gespeichert. Behandle die "
    "Zusammenfassung nicht als aktuelle Repo-Evidenz; lies benoetigte Fakten "
    "bei Bedarf erneut mit den Projektwerkzeugen."
)


def _ereignis_messages(ev: dict[str, Any]) -> list[dict[str, Any]]:
    kind = ev.get("kind")
    p = ev.get("payload") or {}
    if kind == "user":
        return [{"role": "user", "content": str(p.get("text", ""))}]
    if kind == "assistant":
        return [{"role": "assistant", "content": str(p.get("text", ""))}]
    if kind == "job_turn":
        return [
            {"role": "user", "content": str(p.get("user_text", ""))},
            {"role": "assistant", "content": str(p.get("assistant_text", ""))},
        ]
    if kind == "tool_call":
        return [{
            "role": "assistant",
            "content": None,
            "tool_calls": p.get("tool_calls", []),
        }]
    if kind == "tool_result":
        return [{
            "role": "tool",
            "tool_call_id": p.get("tool_call_id", "?"),
            "content": str(p.get("content", "")),
        }]
    return []


def _dialog_turns(events: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    turns: list[list[dict[str, Any]]] = []
    pending: list[dict[str, Any]] = []
    for event in events:
        kind = event.get("kind")
        if kind == "user":
            if pending:
                turns.append(pending)
            pending = _ereignis_messages(event)
        elif kind == "assistant":
            if pending:
                pending.extend(_ereignis_messages(event))
                turns.append(pending)
                pending = []
            else:
                turns.append(_ereignis_messages(event))
        elif kind == "job_turn":
            if pending:
                turns.append(pending)
                pending = []
            turns.append(_ereignis_messages(event))
        # Alte Tool-Traces bleiben persistent, werden aber nicht erneut
        # in den Prompt kopiert. Der finale Assistant-Turn traegt die Antwort.
    if pending:
        turns.append(pending)
    return turns


def _message_chars(turn: list[dict[str, Any]]) -> int:
    return sum(len(str(message.get("content") or "")) for message in turn)


def _kuerze_turn(turn: list[dict[str, Any]], budget: int) -> list[dict[str, Any]]:
    if not turn or budget <= 0:
        return []
    anteil = max(1, budget // len(turn))
    gekuerzt: list[dict[str, Any]] = []
    for message in turn:
        item = dict(message)
        content = str(item.get("content") or "")
        if len(content) > anteil:
            marker = "\\n[… gekuerzt; vollstaendig im Chatverlauf …]\\n"
            if anteil <= len(marker):
                item["content"] = content[:anteil]
            else:
                rest = anteil - len(marker)
                anfang = rest // 2
                ende = rest - anfang
                item["content"] = content[:anfang] + marker + (content[-ende:] if ende else "")
        gekuerzt.append(item)
    # Marker duerfen den harten Zeichenrahmen auch bei kleinen Restbudgets nicht sprengen.
    verbleibend = budget
    bounded: list[dict[str, Any]] = []
    for item in gekuerzt:
        if verbleibend <= 0:
            break
        textwert = str(item.get("content") or "")
        if len(textwert) > verbleibend:
            item["content"] = textwert[:verbleibend]
        bounded.append(item)
        verbleibend -= len(str(item.get("content") or ""))
    return bounded

def _baue_messages(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Baut bounded Chat-Historie; persistente Events bleiben unveraendert."""
    letzter_user = max(
        (index for index, event in enumerate(events) if event.get("kind") == "user"),
        default=-1,
    )
    if letzter_user < 0:
        historie, aktueller_turn = events, []
    else:
        historie = events[:letzter_user]
        aktueller_turn = events[letzter_user:]

    turns = _dialog_turns(historie)
    gewaehlte_turns: list[list[dict[str, Any]]] = []
    rest = _CHAT_HISTORY_CHAR_BUDGET
    gekuerzt = any(
        event.get("kind") in {"tool_call", "tool_result"} for event in historie
    )
    for turn in reversed(turns):
        groesse = _message_chars(turn)
        if groesse <= rest:
            gewaehlte_turns.append(turn)
            rest -= groesse
            continue
        if rest > 0 and not gewaehlte_turns:
            gewaehlte_turns.append(_kuerze_turn(turn, rest))
            rest = 0
        gekuerzt = True
        break

    msgs: list[dict[str, Any]] = []
    if gekuerzt:
        msgs.append({"role": "system", "content": _CHAT_HISTORY_COMPACT_NOTE})
    for turn in reversed(gewaehlte_turns):
        msgs.extend(turn)
    for event in aktueller_turn:
        msgs.extend(_ereignis_messages(event))
    return msgs



_CHAT_ACTIVE_TOOL_CHAR_BUDGET = 24_000
_CHAT_ACTIVE_TOOL_RECENT_BUDGET = 18_000
_CHAT_ACTIVE_TOOL_SUMMARY_BUDGET = 6_000
_CHAT_ACTIVE_TOOL_SUMMARY_MARKER = "[Verdichtete Werkzeughistorie]"


def _message_size(message: dict[str, Any]) -> int:
    size = len(str(message.get("content") or ""))
    calls = message.get("tool_calls")
    if calls:
        size += len(json.dumps(calls, ensure_ascii=False, default=str))
    return size


def _komprimiere_text(text: str, budget: int) -> str:
    if len(text) <= budget:
        return text
    marker = "\n[… gekürzt; vollständiger Beleg bleibt gespeichert …]\n"
    if budget <= len(marker):
        return text[:budget]
    rest = budget - len(marker)
    anfang = rest // 2
    ende = rest - anfang
    return text[:anfang] + marker + (text[-ende:] if ende else "")


def _runde_zusammenfassen(runde: list[dict[str, Any]]) -> str:
    calls = {
        str(call.get("id", "?")): call.get("function") or {}
        for message in runde
        for call in (message.get("tool_calls") or [])
    }
    teile: list[str] = []
    for result in runde:
        if result.get("role") != "tool":
            continue
        fn = calls.get(str(result.get("tool_call_id", "?")), {})
        name = str(fn.get("name", "unbekanntes Tool"))
        args = _komprimiere_text(str(fn.get("arguments", "{}")), 180)
        output = _komprimiere_text(str(result.get("content") or ""), 420)
        teile.append(f"- {name}({args}) -> {output}")
    return "\n".join(teile)


def _kuerze_werkzeugrunde(
    runde: list[dict[str, Any]], budget: int,
) -> list[dict[str, Any]]:
    gekuerzt = [dict(message) for message in runde]
    call_size = sum(
        _message_size(message) for message in gekuerzt
        if message.get("role") != "tool"
    )
    result_indices = [
        index for index, message in enumerate(gekuerzt)
        if message.get("role") == "tool"
    ]
    rest = max(0, budget - call_size)
    anteil = rest // max(1, len(result_indices))
    for index in result_indices:
        content = str(gekuerzt[index].get("content") or "")
        gekuerzt[index]["content"] = _komprimiere_text(content, anteil)
    return gekuerzt


def _begrenze_aktiven_turn(
    messages: list[dict[str, Any]], turn_start: int,
) -> list[dict[str, Any]]:
    """Verdichtet abgeschlossene Werkzeugrunden; der persistente Event-Store bleibt vollstaendig."""
    prefix = messages[:turn_start + 1]
    tail = messages[turn_start + 1:]
    runden: list[list[dict[str, Any]]] = []
    loose: list[dict[str, Any]] = []
    aktuell: list[dict[str, Any]] | None = None
    for message in tail:
        if message.get("role") == "assistant" and message.get("tool_calls"):
            if aktuell:
                runden.append(aktuell)
            aktuell = [message]
        elif message.get("role") == "tool" and aktuell is not None:
            aktuell.append(message)
        else:
            if aktuell:
                runden.append(aktuell)
                aktuell = None
            loose.append(message)
    if aktuell:
        runden.append(aktuell)

    carry = [
        str(message.get("content") or "")
        for message in loose
        if message.get("role") == "system"
        and _CHAT_ACTIVE_TOOL_SUMMARY_MARKER in str(message.get("content") or "")
    ]
    notes = [
        message for message in loose
        if not (message.get("role") == "system" and
                _CHAT_ACTIVE_TOOL_SUMMARY_MARKER in str(message.get("content") or ""))
    ]
    raw_rounds: list[list[dict[str, Any]]] = []
    raw_size = 0
    for round_messages in reversed(runden):
        size = sum(_message_size(message) for message in round_messages)
        if raw_size + size <= _CHAT_ACTIVE_TOOL_RECENT_BUDGET:
            raw_rounds.append(round_messages)
            raw_size += size
            continue
        if not raw_rounds:
            raw_rounds.append(_kuerze_werkzeugrunde(
                round_messages, _CHAT_ACTIVE_TOOL_RECENT_BUDGET,
            ))
        break
    raw_rounds.reverse()
    raw_ids = {id(message) for round_messages in raw_rounds for message in round_messages}

    older_summaries = [
        _runde_zusammenfassen(round_messages)
        for round_messages in runden
        if not all(id(message) in raw_ids for message in round_messages)
    ]
    summary = "\n".join(part for part in carry + older_summaries if part)
    summary = _komprimiere_text(summary, _CHAT_ACTIVE_TOOL_SUMMARY_BUDGET)
    suffix: list[dict[str, Any]] = []
    if summary:
        suffix.append({
            "role": "system",
            "content": (
                _CHAT_ACTIVE_TOOL_SUMMARY_MARKER + ": Vollständige frühere "
                "Werkzeugausgaben bleiben im gespeicherten Verlauf. Diese "
                "Auszüge sind Hinweise, keine aktuelle Repo-Evidenz; bei Bedarf "
                "gezielt erneut lesen.\n" + summary
            ),
        })
    for round_messages in raw_rounds:
        suffix.extend(dict(message) for message in round_messages)
    if notes:
        suffix.append(dict(notes[-1]))
    if sum(_message_size(message) for message in suffix) > _CHAT_ACTIVE_TOOL_CHAR_BUDGET:
        overflow = sum(_message_size(message) for message in suffix) - _CHAT_ACTIVE_TOOL_CHAR_BUDGET
        for message in suffix:
            if overflow <= 0:
                break
            if message.get("role") != "tool":
                continue
            content = str(message.get("content") or "")
            reduction = min(overflow, len(content))
            message["content"] = _komprimiere_text(content, len(content) - reduction)
            overflow -= reduction
    return [*prefix, *suffix]


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


def _finalisiere_chat(
    messages: list[dict[str, Any]],
    session: ChatSession,
    *,
    grund: str,
    on_chunk: Callable[[str], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> str:
    """Schliesst einen Werkzeugturn anhand belegter Ergebnisse ab."""
    _check_cancel(cancel_check)
    _abschluss_prompt = (
        "Formuliere jetzt die abschliessende Antwort fuer den Nutzer. "
        "Verwende ausschliesslich vorhandene Nachrichten und Werkzeugergebnisse; "
        "fuehre keine neuen Werkzeuge aus und behaupte keine ungeprueften Fakten. "
        "Nenne klar, was belegt ist und was noch offen bleibt. "
        "Gib keine internen Gedankengaenge wieder."
    )
    if grund == "stagnation":
        _abschluss_prompt += (
            " Derselbe Werkzeugaufruf hat wiederholt dasselbe Ergebnis geliefert. "
            "Wiederhole ihn nicht; erklaere den belegten Stand und den naechsten "
            "sinnvollen Schritt."
        )
    else:
        _abschluss_prompt += (
            " Der Werkzeug-Arbeitsschritt ist an seiner expliziten Obergrenze "
            "angekommen; kennzeichne verbleibende Pruefungen als offen."
        )
    _abschluss_messages = [
        *messages,
        {"role": "user", "content": _abschluss_prompt},
    ]
    if cancel_check is None:
        _resp = _deepseek_chat(_abschluss_messages)
    else:
        _resp = _deepseek_chat(
            _abschluss_messages, cancel_check=cancel_check,
        )
    _usage = _resp.get("usage")
    if _usage and _usage.get("total_tokens"):
        session.append("token_usage", _usage)
    _msg = _resp["choices"][0]["message"]
    _answer = str(_msg.get("content") or "").strip()
    if not _answer:
        _answer = (
            "Ich konnte die Prüfung nicht sauber abschließen. "
            "Der bisherige Stand und die offenen Punkte bleiben im Chatverlauf "
            "sichtbar; bitte starte den Auftrag erneut oder grenze ihn ein."
        )
    if on_chunk is not None:
        on_chunk(_answer)
    session.append("assistant", {"text": _answer})
    return _answer


def chat_loop(
    session: ChatSession,
    message: str,
    tools: dict[str, dict[str, Any]] | None = None,
    mode: str = "read",
    on_chunk: Callable[[str], None] | None = None,
    on_tool_call: Callable[[str, dict[str, Any]], None] | None = None,
    on_tool_result: Callable[[str, str], None] | None = None,
    max_rounds: int | None = _DEFAULT_MAX_ROUNDS,
    project_dir: Path | str | None = None,
    request_id: str | None = None,
    cancel_check: Callable[[], bool] | None = None,
    origin_session_id: str | None = None,
) -> str:
    """User-Nachricht -> LLM-Loop -> Assistant-Antwort."""
    tools = tools if tools is not None else CHAT_TOOLS
    _check_cancel(cancel_check)
    user_payload: dict[str, Any] = {"text": message, "mode": mode}
    if request_id is not None:
        user_payload["job_id"] = request_id
    session.append("user", user_payload)
    _project_context = f"Aktives Projekt: {session.project}."
    if project_dir is not None:
        _project_context += (
            f" Projektwurzel: {Path(project_dir).expanduser().resolve()}."
        )
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                _SYSTEM_PROMPT
                + ("\\n" + _DEBUGGER_PROMPT if mode == "debugger" else "")
                + "\\n" + _project_context
            ),
        },
        *_baue_messages(session.load()),
    ]
    schemas = openai_schemas(tools, mode=mode)
    _active_turn_start = max(
        index for index, item in enumerate(messages) if item.get("role") == "user"
    )

    if max_rounds is not None and max_rounds < 0:
        raise ValueError("max_rounds darf nicht negativ sein")
    _rounds = 0
    _recent_tool_fingerprints: list[str] = []
    _warned_tool_cycles: set[tuple[str, ...]] = set()
    while max_rounds is None or _rounds < max_rounds:
        _check_cancel(cancel_check)
        _rounds += 1
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
        _round_evidence: list[tuple[str, str, str]] = []
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
            _round_evidence.append((
                name,
                json.dumps(args, ensure_ascii=False, sort_keys=True, default=str),
                str(ergebnis),
            ))
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

        messages = _begrenze_aktiven_turn(messages, _active_turn_start)
        _fingerprint = hashlib.sha256(
            json.dumps(
                _round_evidence, ensure_ascii=False, sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        _recent_tool_fingerprints.append(_fingerprint)
        _recent_tool_fingerprints = _recent_tool_fingerprints[-6:]
        _cycle = _repeated_tool_cycle(_recent_tool_fingerprints)
        if _cycle is not None:
            if _cycle in _warned_tool_cycles:
                return _finalisiere_chat(
                    messages, session, grund="stagnation",
                    on_chunk=on_chunk, cancel_check=cancel_check,
                )
            _warned_tool_cycles.add(_cycle)
            messages.append({
                "role": "system",
                "content": (
                    "Fortschrittskontrolle: Ein Werkzeugzyklus wiederholt "
                    "sich mit denselben Eingaben und Ergebnissen. Waehle "
                    "einen anderen, gezielten Pruefschritt oder beende mit "
                    "den vorhandenen Belegen und offenen Punkten."
                ),
            })

    return _finalisiere_chat(
        messages, session, grund="round_limit",
        on_chunk=on_chunk, cancel_check=cancel_check,
    )
