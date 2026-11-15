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
    monkeypatch.setattr(
        agent,
        "audit",
        lambda kind, payload, *_a, **_kw: events.append((kind, payload)),
    )
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


def test_context_manifest_bounds_total_nested_metadata_size() -> None:
    nested = "x" * 240
    for _ in range(5):
        nested = [nested] * 50

    cleaned = agent._safe_context_manifest({"branch": nested})

    assert cleaned is not None
    assert cleaned["_manifest_truncated"] is True
    assert len(json.dumps(cleaned, ensure_ascii=False)) < 32_000


def test_llm_request_is_not_sent_when_audit_write_fails(monkeypatch, tmp_path):
    state = mk_state(project_dir=tmp_path, project_name="audit-failure")
    monkeypatch.setattr(agent, "audit", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(
        agent.requests,
        "post",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Provider request must not be sent without audit"),
        ),
    )

    reply = agent.ask_llm(
        api_key="test-key",
        system_prompt="system",
        user_content="required role evidence",
        model="deepseek-chat",
        temperature=0.0,
        state=state,
        aufgabe="builder",
        context_manifest={
            "budget_event": "builder_context_budget",
            "required": ["task", "verify"],
        },
    )

    assert reply.ok is False
    assert reply.error == "llm_call_audit_failed; provider request was not sent"
    assert state.llm_calls == 1


def test_role_request_without_budget_evidence_is_blocked(monkeypatch, tmp_path):
    state = mk_state(project_dir=tmp_path, project_name="missing-context")
    events = []
    monkeypatch.setattr(
        agent,
        "audit",
        lambda kind, payload, *_args, **_kwargs: events.append((kind, payload)),
    )
    monkeypatch.setattr(
        agent.requests,
        "post",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Role request must have context evidence"),
        ),
    )

    reply = agent.ask_llm(
        api_key="test-key",
        system_prompt="system",
        user_content="task without role manifest",
        model="deepseek-chat",
        temperature=0.0,
        state=state,
        aufgabe="builder",
    )

    assert reply.ok is False
    assert reply.error == "role_context_evidence_missing; provider request was not sent"
    assert state.llm_calls == 1
    blocked = [payload for kind, payload in events if kind == "llm_context_blocked"]
    assert blocked == [{
        "agent": "builder",
        "reason": "required_role_context_evidence_missing",
        "missing": ["context_manifest.budget_event"],
        "provider_request_sent": False,
    }]


def test_role_request_without_run_state_is_blocked(monkeypatch):
    provider_calls = []
    monkeypatch.setattr(
        agent.requests,
        "post",
        lambda *_args, **_kwargs: provider_calls.append(True),
    )

    reply = agent.ask_llm(
        api_key="test-key",
        system_prompt="system",
        user_content="task without run state",
        model="deepseek-chat",
        temperature=0.0,
        state=None,
        aufgabe="builder",
        context_manifest={"budget_event": "builder_context_budget"},
    )

    assert reply.ok is False
    assert reply.error == "role_context_evidence_missing; provider request was not sent"
    assert provider_calls == []
