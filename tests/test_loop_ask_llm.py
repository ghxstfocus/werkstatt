"""Spec: ask_llm — 7 Return-Pfade, Redaction, Audit, Uebergabe an HTTP.

Getestet wird die echte Funktion mit gemocktem requests.post.
Audit laeuft echt (conftest._isolate_audit leitet nach tmp_path).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

from werkstatt import agent
from werkstatt import audit as audit_mod
from werkstatt.state import RunState

# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------

def _state(tmp_path: Path) -> RunState:
    """Minimaler RunState mit den Feldern, die ask_llm anfasst."""
    return RunState(
        block_id="t",
        aufgabe="test",
        start_ts="2026-10-30T00:00:00Z",
        docs={},
        agents={},
        always={},
        optional={},
        file_whitelist=[],
        api_key="sk-test",
        budget={},
        agent_docs={},
        project_dir=tmp_path,
        project_name="testproj",
        max_total_llm_s=240,
    )


def _ok_response(content: str = "hi",
                 reasoning: str | None = None) -> MagicMock:
    msg: dict = {"content": content}
    if reasoning is not None:
        msg["reasoning_content"] = reasoning
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = {"choices": [{"message": msg}]}
    r.text = content
    return r


def _http(code: int, text: str = "") -> MagicMock:
    r = MagicMock()
    r.status_code = code
    r.text = text
    r.json.side_effect = ValueError("nicht json")
    return r


def _audit_events(project_dir: Path) -> list[dict]:
    """Liest alle audit-Events.

    conftest._isolate_audit patcht werkstatt.audit._werkstatt_home
    auf tmp_path; audit schreibt dann nach
    tmp_path/audit-logs/agent-pipeline-<tag>.jsonl.
    """
    out: list[dict] = []
    logs = project_dir / "audit-logs"
    if not logs.is_dir():
        return out
    for f in sorted(logs.glob("agent-pipeline-*.jsonl")):
        for line in f.read_text().splitlines():
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _call(state: RunState | None = None,
          system: str = "SYS",
          user: str = "USER",
          progress_context: dict | None = None) -> agent.LLMReply:
    return agent.ask_llm(
        api_key="sk-test",
        system_prompt=system,
        user_content=user,
        model="deepseek-chat",
        temperature=0.3,
        timeout=120,
        state=state,
        aufgabe="unit-test",
        max_tokens=1024,
        progress_context=progress_context,
    )


# ---------------------------------------------------------------------
# A. Erfolg + Uebergabe
# ---------------------------------------------------------------------

def test_ok_200_content(tmp_path):
    with patch("werkstatt.agent.requests.post",
               return_value=_ok_response("antwort")):
        r = _call(_state(tmp_path))
    assert r.ok is True
    assert r.content == "antwort"
    assert r.error == ""


def test_system_len_user_len_gesetzt(tmp_path):
    sys_p = "S" * 42
    usr_p = "U" * 77
    with patch("werkstatt.agent.requests.post",
               return_value=_ok_response()):
        r = _call(_state(tmp_path), system=sys_p, user=usr_p)
    assert r.system_len == 42
    assert r.user_len == 77


def test_state_llm_calls_zaehlt_einmal(tmp_path):
    s = _state(tmp_path)
    with patch("werkstatt.agent.requests.post",
               return_value=_ok_response()):
        _call(s)
    assert s.llm_calls == 1


def test_run_llm_call_budget_blocks_before_network(tmp_path):
    s = _state(tmp_path)
    s.budget = {"max_llm_calls": 1}
    s.llm_calls = 1
    with patch("werkstatt.agent.requests.post") as post:
        reply = _call(s)
    post.assert_not_called()
    assert reply.ok is False
    assert "Aufrufbudget erreicht" in reply.error
    assert s.llm_calls == 1
    assert s.budget_exhausted_reason == reply.error


def test_exhausted_budget_allows_only_checkpoint_claimed_chat_builder(
    monkeypatch, tmp_path,
):
    from werkstatt.event_store import EventStore

    s = _state(tmp_path)
    s.run_id = "test-run-1"
    s.budget = {"max_llm_calls": 1}
    s.llm_calls = 1
    s.budget_exhausted_reason = "max_llm_calls"
    s.reflection_chat_builder_reserve_active = True
    store = EventStore(tmp_path / "events.db")
    store.create_run_record(s.project_name, s.run_id, s.aufgabe, status="running")
    monkeypatch.setattr("werkstatt.event_store.EventStore", lambda: store)
    prompt = "builder prompt"
    system = "builder system"
    context = {
        "budget_event": "builder_context_budget",
        "required_context_complete": True,
        "user_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "system_sha256": hashlib.sha256(system.encode()).hexdigest(),
    }
    with patch(
        "werkstatt.agent.requests.post", return_value=_ok_response("patch"),
    ) as post:
        reply = agent.ask_llm(
            "sk-test", system, prompt, "deepseek-chat", 0.2,
            state=s, aufgabe="builder", context_manifest=context,
        )
        second_reply = agent.ask_llm(
            "sk-test", system, prompt, "deepseek-chat", 0.2,
            state=s, aufgabe="builder", context_manifest=context,
        )
    assert reply.ok is True
    assert second_reply.ok is False
    assert second_reply.error == "reflection_builder_reserve_exhausted"
    post.assert_called_once()
    assert s.llm_calls == 2


def test_chat_builder_provider_timeout_uses_remaining_reserve(
    monkeypatch, tmp_path,
):
    from datetime import UTC, datetime, timedelta

    from werkstatt.event_store import EventStore

    s = _state(tmp_path)
    s.run_id = "test-run-timeout"
    s.budget = {"max_llm_calls": 1}
    s.llm_calls = 1
    s.budget_exhausted_reason = "max_llm_calls"
    s.reflection_chat_builder_reserve_active = True
    store = EventStore(tmp_path / "events.db")
    store.create_run_record(s.project_name, s.run_id, s.aufgabe, status="running")
    record = store.get_run_record(s.project_name, s.run_id)
    assert record is not None
    checkpoint = dict(record["checkpoint"])
    checkpoint["reflection_chat_builder_expires_at"] = (
        datetime.now(UTC) + timedelta(seconds=8)
    ).isoformat()
    store.update_run_checkpoint(
        s.project_name, s.run_id, checkpoint,
        expected_version=record["checkpoint_version"],
    )
    monkeypatch.setattr("werkstatt.event_store.EventStore", lambda: store)
    prompt = "builder prompt"
    system = "builder system"
    context = {
        "budget_event": "builder_context_budget",
        "required_context_complete": True,
        "user_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "system_sha256": hashlib.sha256(system.encode()).hexdigest(),
    }
    with patch(
        "werkstatt.agent.requests.post", return_value=_ok_response("patch"),
    ) as post:
        reply = agent.ask_llm(
            "sk-test", system, prompt, "deepseek-chat", 0.2,
            state=s, aufgabe="builder", context_manifest=context,
        )
    assert reply.ok is True
    connect_timeout, read_timeout = post.call_args.kwargs["timeout"]
    assert connect_timeout + read_timeout <= 8


def test_exhausted_budget_does_not_reserve_chat_for_other_roles(
    monkeypatch, tmp_path,
):
    from werkstatt import reflection_chat

    s = _state(tmp_path)
    s.budget = {"max_llm_calls": 1}
    s.llm_calls = 1
    s.budget_exhausted_reason = "max_llm_calls"
    s.reflection_chat_builder_reserve_active = True
    with (
        patch.object(
            reflection_chat, "claim_recovery_builder_call",
        ) as reserve,
        patch("werkstatt.agent.requests.post") as post,
    ):
        reply = agent.ask_llm(
            "sk-test", "system", "user", "deepseek-chat", 0.2,
            state=s, aufgabe="reviewer",
        )
    reserve.assert_not_called()
    post.assert_not_called()
    assert reply.ok is False
    assert reply.error == "max_llm_calls"


def test_run_time_budget_blocks_before_network(tmp_path):
    s = _state(tmp_path)
    s.budget = {"max_minutes": 1}
    s.start_monotonic = 1.0
    with (
        patch("werkstatt.agent.time.monotonic", return_value=62.0),
        patch("werkstatt.agent.requests.post") as post,
    ):
        reply = _call(s)
    post.assert_not_called()
    assert reply.ok is False
    assert "Zeitbudget erreicht" in reply.error
    assert s.llm_calls == 0
    assert s.budget_exhausted_reason == reply.error


def test_ohne_state_kein_crash(tmp_path):
    with patch("werkstatt.agent.requests.post",
               return_value=_ok_response()):
        r = _call(None)
    assert r.ok is True


def test_reasoning_content_fail_loud(tmp_path):
    """2026-11-05: Leerer content + reasoning_content vorhanden
    -> ok=False (Fail-loud). Vorher wurde reasoning als content
    akzeptiert, was das Denkprotokoll an den Planner-Split gab."""
    with patch("werkstatt.agent.requests.post",
               return_value=_ok_response("", reasoning="denk-tokens")):
        r = _call(_state(tmp_path))
    assert r.ok is False
    assert "leerer content" in (r.error or "")
    assert "reasoning_content" in (r.error or "")


# ---------------------------------------------------------------------
# B. Redaction
# ---------------------------------------------------------------------

def test_redaction_user_content(tmp_path):
    # Auflage 2195: nur oeffentliche IPs werden maskiert.
    ip = "8.8.8.8"
    with patch("werkstatt.agent.requests.post",
               return_value=_ok_response()) as mock_post:
        _call(_state(tmp_path), user=f"Host {ip} meldet")
    gesendet = mock_post.call_args.kwargs["json"]["messages"][1]["content"]
    assert ip not in gesendet


def test_redaction_system_prompt(tmp_path):
    # Auflage 2195: nur oeffentliche IPs werden maskiert.
    ip = "8.8.8.8"
    with patch("werkstatt.agent.requests.post",
               return_value=_ok_response()) as mock_post:
        _call(_state(tmp_path), system=f"Scanner auf {ip}")
    gesendet = mock_post.call_args.kwargs["json"]["messages"][0]["content"]
    assert ip not in gesendet


def test_system_len_nach_redaction(tmp_path):
    # Wenn Redaction greift, ist system_len kleiner als Original.
    original = "Host 192.168.178.117 meldet"
    with patch("werkstatt.agent.requests.post",
               return_value=_ok_response()):
        r = _call(_state(tmp_path), system=original)
    assert r.system_len <= len(original)
    assert r.system_len > 0


# ---------------------------------------------------------------------
# C. Audit
# ---------------------------------------------------------------------

def test_audit_llm_call(tmp_path):
    s = _state(tmp_path)
    s.run_id = "state-owned-run"
    previous_run_id = audit_mod.get_run_id()
    audit_mod.set_run_id("other-global-run")
    with patch("werkstatt.agent.requests.post",
               return_value=_ok_response()) as post:
        try:
            _call(s, system="S" * 10, user="U" * 20)
        finally:
            audit_mod.set_run_id(previous_run_id)
    evs = [e for e in _audit_events(tmp_path) if e.get("kind") == "llm_call"]
    assert len(evs) == 1
    ev = evs[0]
    # audit() merged Payload flach ins Event.
    assert ev["agent"] == "unit-test"
    assert ev["run_id"] == "state-owned-run"
    assert ev["model"] == "deepseek-flash"
    assert ev["system_len"] == 10
    assert ev["user_len"] == 20
    sent = post.call_args.kwargs["json"]["messages"]
    assert ev["system_sha256"] == hashlib.sha256(
        sent[0]["content"].encode("utf-8")
    ).hexdigest()
    assert ev["user_sha256"] == hashlib.sha256(
        sent[1]["content"].encode("utf-8")
    ).hexdigest()
    assert ev["max_tokens"] == 1024


def test_audit_kein_llm_call_bei_state_none(tmp_path):
    with patch("werkstatt.agent.requests.post",
               return_value=_ok_response()):
        _call(None)
    evs = [e for e in _audit_events(tmp_path) if e.get("kind") == "llm_call"]
    assert evs == []


# ---------------------------------------------------------------------
# D. Prompt-Dump
# ---------------------------------------------------------------------

def test_dump_aus_wenn_env_nicht_gesetzt(tmp_path, monkeypatch):
    monkeypatch.delenv("WERKSTATT_PROMPT_DUMP", raising=False)
    dump_dir = Path("/tmp/werkstatt-prompts")
    vorher = set(dump_dir.glob("unit-test_*")) if dump_dir.exists() else set()
    with patch("werkstatt.agent.requests.post",
               return_value=_ok_response()):
        _call(_state(tmp_path))
    nachher = set(dump_dir.glob("unit-test_*")) if dump_dir.exists() else set()
    assert nachher == vorher


def test_dump_an_wenn_env_gesetzt(tmp_path, monkeypatch):
    monkeypatch.setenv("WERKSTATT_PROMPT_DUMP", "1")
    dump_dir = Path("/tmp/werkstatt-prompts")
    vorher = set(dump_dir.glob("unit-test_*")) if dump_dir.exists() else set()
    with patch("werkstatt.agent.requests.post",
               return_value=_ok_response()):
        _call(_state(tmp_path))
    nachher = set(dump_dir.glob("unit-test_*")) if dump_dir.exists() else set()
    neu = nachher - vorher
    # 3 Dateien pro Call: *_system.txt, *_user.txt, *_meta.txt
    assert len(neu) == 3


# ---------------------------------------------------------------------
# E. Fehlerpfade
# ---------------------------------------------------------------------

def test_http_400_kein_retry(tmp_path):
    with patch("werkstatt.agent.requests.post",
               return_value=_http(400, "bad")) as mock_post:
        r = _call(_state(tmp_path))
    assert r.ok is False
    assert "400" in r.error
    assert mock_post.call_count == 1


def test_http_500_retry_dann_fehler(tmp_path):
    s = _state(tmp_path)
    with patch("werkstatt.agent.requests.post",
               return_value=_http(500, "boom")) as mock_post, \
         patch("werkstatt.agent.time.sleep"):
        r = _call(s)
    assert r.ok is False
    assert "500" in r.error
    assert mock_post.call_count == 2
    assert s.llm_calls == 1  # Retries zaehlen nicht


def test_http_429_retry_dann_ok(tmp_path):
    responses = [_http(429, "ratelimit"), _ok_response("endlich")]
    with patch("werkstatt.agent.requests.post",
               side_effect=responses) as mock_post, \
         patch("werkstatt.agent.time.sleep"):
        r = _call(_state(tmp_path))
    assert r.ok is True
    assert r.content == "endlich"
    assert mock_post.call_count == 2


def test_request_exception_alle_versuche(tmp_path):
    with patch("werkstatt.agent.requests.post",
               side_effect=requests.ConnectionError("no net")) as mock_post, \
         patch("werkstatt.agent.time.sleep"):
        r = _call(_state(tmp_path))
    assert r.ok is False
    assert "no net" in r.error
    assert mock_post.call_count == 2


def test_timeout_read_retry(tmp_path):
    responses = [requests.Timeout("slow"), _ok_response("ok")]
    with patch("werkstatt.agent.requests.post",
               side_effect=responses), \
         patch("werkstatt.agent.time.sleep"):
        r = _call(_state(tmp_path))
    assert r.ok is True


def test_timeout_read_audit_event(tmp_path):
    s = _state(tmp_path)
    responses = [requests.Timeout("slow"), _ok_response("ok")]
    with patch("werkstatt.agent.requests.post",
               side_effect=responses), \
         patch("werkstatt.agent.time.sleep"):
        _call(s)
    evs = [e for e in _audit_events(tmp_path)
           if e.get("kind") == "llm_timeout_read"]
    assert len(evs) == 1
    assert evs[0]["versuch"] == 1


def test_gesamt_timeout_vor_erstem_versuch(tmp_path):
    s = _state(tmp_path)
    s.max_total_llm_s = 0
    with patch("werkstatt.agent.requests.post") as mock_post:
        r = _call(s)
    assert r.ok is False
    assert "Gesamt-Timeout" in r.error
    assert mock_post.call_count == 0
    evs = [e for e in _audit_events(tmp_path)
           if e.get("kind") == "llm_timeout_gesamt"]
    assert len(evs) == 1


def test_leere_antwort(tmp_path):
    with patch("werkstatt.agent.requests.post",
               return_value=_ok_response("", reasoning="")):
        r = _call(_state(tmp_path))
    assert r.ok is False
    assert "leere Antwort" in r.error


def test_parsing_fehler_json(tmp_path):
    r_mock = MagicMock()
    r_mock.status_code = 200
    r_mock.text = "kein json"
    r_mock.json.side_effect = ValueError("kaputt")
    with patch("werkstatt.agent.requests.post", return_value=r_mock):
        r = _call(_state(tmp_path))
    assert r.ok is False
    assert "Parsing" in r.error


def test_parsing_fehler_choices_fehlt(tmp_path):
    r_mock = MagicMock()
    r_mock.status_code = 200
    r_mock.text = "{}"
    r_mock.json.return_value = {}
    with patch("werkstatt.agent.requests.post", return_value=r_mock):
        r = _call(_state(tmp_path))
    assert r.ok is False
    assert "Parsing" in r.error


# ---------------------------------------------------------------------
# F. Uebergabe an HTTP
# ---------------------------------------------------------------------

def test_payload_korrekt(tmp_path):
    with patch("werkstatt.agent.requests.post",
               return_value=_ok_response()) as mock_post:
        _call(_state(tmp_path), system="SYS", user="USR")
    args = mock_post.call_args
    # URL
    assert args.args[0] == agent.DEEPSEEK_API_URL
    # Headers
    headers = args.kwargs["headers"]
    assert headers["Authorization"] == "Bearer sk-test"
    assert headers["Content-Type"] == "application/json"
    # Payload
    payload = args.kwargs["json"]
    assert payload["model"] == "deepseek-flash"
    assert payload["temperature"] == 0.3
    assert payload["max_tokens"] == 1024
    msgs = payload["messages"]
    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"] == "SYS"
    assert msgs[1]["role"] == "user"
    assert msgs[1]["content"] == "USR"
    # Timeout als (connect, read)-Tupel
    timeout = args.kwargs["timeout"]
    assert isinstance(timeout, tuple)
    assert len(timeout) == 2

def test_llm_usage_hat_stabile_rolle_ohne_agent_zu_ueberschreiben(tmp_path):
    """OP-383: Rolle lebt im Payload; Audit-Agent bleibt stabil."""
    state = _state(tmp_path)
    response = _ok_response("antwort")
    response.json.return_value["usage"] = {
        "prompt_tokens": 12,
        "completion_tokens": 5,
        "total_tokens": 17,
    }
    with patch("werkstatt.agent.requests.post", return_value=response):
        agent.ask_llm(
            api_key="sk-test",
            system_prompt="SYS",
            user_content="USER",
            model="deepseek-chat",
            temperature=0.0,
            state=state,
            aufgabe="planner-split",
            context_manifest={
                "budget_event": "planner_split_context_budget",
                "required_context_complete": True,
                "user_sha256": hashlib.sha256(b"USER").hexdigest(),
                "system_sha256": hashlib.sha256(b"SYS").hexdigest(),
            },
        )

    usage = [
        event for event in _audit_events(tmp_path)
        if event.get("kind") == "llm_usage"
    ]
    assert len(usage) == 1
    assert usage[0]["rolle"] == "planner"
    assert usage[0]["agent"] == "agent_pipeline"
    assert usage[0]["prompt_tokens"] == 12


def test_builder_request_overrides_reasoner_to_flash_and_disables_thinking(tmp_path):
    with patch(
        "werkstatt.agent.requests.post",
        return_value=_ok_response("antwort"),
    ) as mock_post:
        reply = agent.ask_llm(
            api_key="sk-test",
            system_prompt="SYS",
            user_content="USR",
            model="deepseek-reasoner",
            temperature=0.2,
            state=_state(tmp_path),
            aufgabe="builder",
            heartbeat=False,
            context_manifest={
                "budget_event": "builder_context_budget",
                "required_context_complete": True,
                "user_sha256": hashlib.sha256(b"USR").hexdigest(),
                    "system_sha256": hashlib.sha256(b"SYS").hexdigest(),
            },
        )

    payload = mock_post.call_args.kwargs["json"]
    assert reply.ok
    assert payload["model"] == "deepseek-flash"
    assert payload["thinking"] == {"type": "disabled"}
    assert payload["temperature"] == 0.2


def test_architect_request_uses_pro_thinking_without_temperature(tmp_path):
    with patch(
        "werkstatt.agent.requests.post",
        return_value=_ok_response("Plan"),
    ) as mock_post:
        reply = agent.ask_llm(
            api_key="sk-test",
            system_prompt="SYS",
            user_content="USR",
            model="deepseek-reasoner",
            temperature=0.2,
            state=_state(tmp_path),
            aufgabe="architect",
            heartbeat=False,
            context_manifest={
                "budget_event": "planner_architect_context_budget",
                "required_context_complete": True,
                "user_sha256": hashlib.sha256(b"USR").hexdigest(),
                    "system_sha256": hashlib.sha256(b"SYS").hexdigest(),
            },
        )

    payload = mock_post.call_args.kwargs["json"]
    assert reply.ok
    assert payload["model"] == "deepseek-v4-pro"
    assert payload["thinking"] == {"type": "enabled"}
    assert payload["reasoning_effort"] == "high"
    assert "temperature" not in payload


def test_builder_progress_events_include_task_and_file_without_prompt_content(tmp_path):
    state = _state(tmp_path)
    state.aktuelle_task = {
        "id": "task-7",
        "name": "Parser robust machen",
        "task_files": ["src/parser.py"],
    }
    with patch(
        "werkstatt.agent.requests.post",
        return_value=_ok_response("patch"),
    ):
        _call(
            state,
            user="SECRET PROMPT CONTENT",
            progress_context={"files": ["src/parser.py"]},
        )

    events = _audit_events(tmp_path)
    start = next(event for event in events if event.get("kind") == "llm_call_start")
    end = next(event for event in events if event.get("kind") == "llm_call_end")
    for event in (start, end):
        assert event["task_id"] == "task-7"
        assert event["task_name"] == "Parser robust machen"
        assert event["files"] == ["src/parser.py"]
        assert "SECRET PROMPT CONTENT" not in json.dumps(event)


def test_builder_heartbeat_event_contains_task_and_file(monkeypatch, tmp_path):
    state = _state(tmp_path)
    state.aktuelle_task = {
        "id": "task-8",
        "name": "API robust machen",
        "task_files": ["werkstatt/api.py"],
    }
    clock = iter([100.0, 115.0])
    monkeypatch.setattr(agent.time, "monotonic", lambda: next(clock))
    emitted = []

    class _StopEvent:
        stopped = False

        def is_set(self):
            return self.stopped

        def wait(self, _seconds):
            self.stopped = True

    stop_event = _StopEvent()

    class _Thread:
        def __init__(self, *, target, **_kwargs):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr(agent.threading, "Event", lambda: stop_event)
    monkeypatch.setattr(agent.threading, "Thread", _Thread)
    monkeypatch.setattr(
        agent,
        "audit",
        lambda kind, payload, project_dir, project_name: emitted.append(
            (kind, payload, project_dir, project_name)
        ) or True,
    )

    thread, actual_stop = agent._heartbeat_start(
        "builder",
        state=state,
        progress_context={"files": ["werkstatt/api.py"]},
    )
    thread.start()

    assert actual_stop is stop_event
    assert len(emitted) == 1
    kind, payload, project_dir, project_name = emitted[0]
    assert kind == "llm_call_heartbeat"
    assert payload["agent"] == "builder"
    assert payload["elapsed_s"] == 15
    assert payload["task_id"] == "task-8"
    assert payload["task_name"] == "API robust machen"
    assert payload["files"] == ["werkstatt/api.py"]
    assert project_dir == tmp_path
    assert project_name == "testproj"
    assert "reasoning" not in json.dumps(payload).lower()
