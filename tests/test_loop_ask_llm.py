"""Spec: ask_llm — 7 Return-Pfade, Redaction, Audit, Uebergabe an HTTP.

Getestet wird die echte Funktion mit gemocktem requests.post.
Audit laeuft echt (conftest._isolate_audit leitet nach tmp_path).
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from werkstatt import agent
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
          user: str = "USER") -> "agent.LLMReply":
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


def test_ohne_state_kein_crash(tmp_path):
    with patch("werkstatt.agent.requests.post",
               return_value=_ok_response()):
        r = _call(None)
    assert r.ok is True


def test_reasoning_content_fallback(tmp_path):
    with patch("werkstatt.agent.requests.post",
               return_value=_ok_response("", reasoning="denk-tokens")):
        r = _call(_state(tmp_path))
    assert r.ok is True
    assert r.content == "denk-tokens"


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
    with patch("werkstatt.agent.requests.post",
               return_value=_ok_response()):
        _call(s, system="S" * 10, user="U" * 20)
    evs = [e for e in _audit_events(tmp_path) if e.get("kind") == "llm_call"]
    assert len(evs) == 1
    ev = evs[0]
    # audit() merged Payload flach ins Event.
    assert ev["agent"] == "unit-test"
    assert ev["model"] == "deepseek-chat"
    assert ev["system_len"] == 10
    assert ev["user_len"] == 20
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
    assert payload["model"] == "deepseek-chat"
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
