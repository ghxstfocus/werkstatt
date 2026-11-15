import hashlib
import json
import time

from tests.factories import mk_state
from werkstatt import agent


class _DummyResponse:
    status_code = 200

    def json(self):
        return {"choices": [{"message": {"content": "ok"}}]}


def test_heartbeat_bei_langem_call(capsys, monkeypatch):
    def fake_post(*args, **kwargs):
        time.sleep(1.5)
        return _DummyResponse()

    monkeypatch.setattr(agent.requests, "post", fake_post)

    agent.ask_llm(
        api_key="x",
        system_prompt="s",
        user_content="u",
        model="m",
        temperature=0.0,
        state=None,
    )

    out = capsys.readouterr().out
    assert sum(1 for line in out.splitlines() if "laeuft" in line) >= 1


def test_heartbeat_bei_schnellem_call(capsys, monkeypatch):
    def fake_post(*args, **kwargs):
        return _DummyResponse()

    monkeypatch.setattr(agent.requests, "post", fake_post)

    agent.ask_llm(
        api_key="x",
        system_prompt="s",
        user_content="u",
        model="m",
        temperature=0.0,
        state=None,
    )

    out = capsys.readouterr().out
    assert sum(1 for line in out.splitlines() if "laeuft" in line) <= 1


def test_heartbeat_stage_name_builder(capsys):
    thread, stop_event = agent._heartbeat_start("Builder")
    time.sleep(1.5)
    stop_event.set()
    thread.join(timeout=2.0)

    out = capsys.readouterr().out
    assert "Builder" in out


def test_llm_call_binds_context_manifest_to_exact_sent_prompt(
    monkeypatch, tmp_path,
) -> None:
    events = []
    monkeypatch.setattr(agent, "audit", lambda kind, payload, *_a: events.append(
        (kind, payload),
    ))
    monkeypatch.setattr(agent.requests, "post", lambda *_a, **_kw: _DummyResponse())
    state = mk_state(project_dir=tmp_path, project_name="manifest-test")
    manifest = {
        "budget_event": "builder_context_budget",
        "included_sections": ["TASK", "SOURCE"],
        "omitted_sections": ["OPTIONAL_HISTORY"],
        "user": "must not be copied into audit",
    }

    agent.ask_llm(
        api_key="x",
        system_prompt="system payload",
        user_content="user payload",
        model="m",
        temperature=0.0,
        state=state,
        aufgabe="builder",
        redact=False,
        context_manifest=manifest,
    )

    call = next(payload for kind, payload in events if kind == "llm_call")
    expected_manifest = {
        "budget_event": "builder_context_budget",
        "included_sections": ["TASK", "SOURCE"],
        "omitted_sections": ["OPTIONAL_HISTORY"],
    }
    encoded_manifest = json.dumps(
        expected_manifest, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"),
    )
    assert call["context_manifest"] == expected_manifest
    assert call["context_manifest_sha256"] == hashlib.sha256(
        encoded_manifest.encode("utf-8"),
    ).hexdigest()
    assert call["user_sha256"] == hashlib.sha256(
        b"user payload",
    ).hexdigest()
