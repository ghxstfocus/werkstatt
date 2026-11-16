from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from werkstatt import chat_tools, reflection, reflection_chat


def _source_evidence() -> list[dict[str, object]]:
    quote = "def expected():\n    return 1"
    return [{
        "file": "werkstatt/sample.py",
        "start": 0,
        "end": len(quote),
        "quote": quote,
    }]


def _verified_source_evidence(tmp_path: Path) -> list[dict[str, object]]:
    return [{
        **_source_evidence()[0],
        "source_sha256": hashlib.sha256(
            (tmp_path / "werkstatt" / "sample.py").read_bytes(),
        ).hexdigest(),
    }]


@pytest.mark.parametrize(
    ("context", "expected"),
    [
        ({"origin": "chat", "origin_session_id": "chat-session_1"}, "chat-session_1"),
        ({"origin": "web", "origin_session_id": "chat-session_1"}, None),
        ({"origin": "chat", "origin_session_id": "../outside"}, None),
    ],
)
def test_originating_chat_session_is_validated(context, expected):
    assert reflection_chat.originating_chat_session_id(
        {"start_context": context},
    ) == expected


def _state(tmp_path: Path) -> SimpleNamespace:
    source_file = tmp_path / "werkstatt" / "sample.py"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_bytes(b"def expected():\n    return 1\n")
    test_file = tmp_path / "tests" / "test_sample.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_bytes(b"def test_expected():\n    assert True\n")
    return SimpleNamespace(
        project_name="alpha",
        project_dir=tmp_path,
        run_id="alpha-run-1",
        chat_origin_session_id="chat-session_1",
        api_key="test-key",
        budget={},
        llm_calls=0,
        start_monotonic=0.0,
        budget_exhausted_reason="",
        aktuelle_task={
            "id": "task-1",
            "name": "Fix failing check",
            "description": "Repair the current check failure.",
            "task_files": ["werkstatt/sample.py", "tests/test_sample.py"],
            "acceptance_criteria": ["AC-1"],
            "action": "update",
        },
        aufgabe="Fix the reported failure.",
        phase_id="build",
        tests=["pytest tests/test_sample.py::test_expected"],
        architect_prosa="Keep the public API stable.",
        last_verify_errors=["mypy: sample.py:10 incompatible type"],
        reviewer_bugs=[],
        reflection_history=[],
        reflection_chat_attempts=set(),
        reflection_chat_calls=0,
        reflection_chat_evidence=[],
    )


def _install_run_store(monkeypatch, state, tmp_path: Path):
    from werkstatt.event_store import EventStore

    store = EventStore(tmp_path / "events.db")
    store.create_run_record(
        state.project_name, state.run_id, state.aufgabe, status="running",
    )
    monkeypatch.setattr("werkstatt.event_store.EventStore", lambda: store)
    return store


def test_scoped_files_reject_paths_outside_project() -> None:
    assert reflection_chat._scoped_files({"task_files": ["../outside.py"]}) == []
    assert reflection_chat._scoped_files({"task_files": ["C:/outside.py"]}) == []
    assert reflection_chat._scoped_files({"task_files": ["pkg/file.py"]}) == [
        "pkg/file.py",
    ]


def test_reflection_evidence_keeps_required_sources_whole_and_marks_optional_omissions(
    tmp_path: Path,
) -> None:
    state = _state(tmp_path)
    state.aufgabe = "Ziel: " + ("vollstaendige Anforderung. " * 80)
    state.aktuelle_task["description"] = "Task: " + ("vollstaendige Beschreibung. " * 80)
    state.last_verify_errors = ["Fehlerbeleg " + ("x" * 1200) for _ in range(4)]
    state.architect_prosa = "optional " + ("Architekturhinweis. " * 1600)

    evidence = reflection_chat._readable_evidence(state)

    assert evidence["context_status"] == "complete_required"
    assert evidence["goal"] == state.aufgabe
    assert evidence["task"]["description"] == state.aktuelle_task["description"]
    assert evidence["verify_errors"] == state.last_verify_errors
    assert evidence["context_budget"]["omitted_optional"] == [
        "architect_constraints",
    ]
    assert evidence["context_budget"]["omissions_are_not_negative_evidence"]
    assert evidence["context_budget"]["sources"]["architect_constraints"]["chars"] > 24_000
    assert evidence["context_budget"]["sources"]["architect_constraints"]["sha256"]


def test_reflection_handoff_includes_exact_recovery_failure_context(
    tmp_path: Path,
) -> None:
    state = _state(tmp_path)
    state.builder_failure_reason = "pytest failed: expected 2, got 1"

    evidence = reflection_chat._readable_evidence(
        state, failure_context="Reflection exhausted after stale patch",
    )

    assert evidence["recovery_failure"] == {
        "reflection_error_context": "Reflection exhausted after stale patch",
        "builder_failure_reason": "pytest failed: expected 2, got 1",
    }
    source = evidence["context_budget"]["sources"]["recovery_failure"]
    assert source["sha256"] == hashlib.sha256(
        json.dumps(evidence["recovery_failure"], ensure_ascii=False, sort_keys=True)
        .encode("utf-8"),
    ).hexdigest()


def test_reflection_chat_refuses_required_context_over_budget_before_session(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = _state(tmp_path)
    state.aktuelle_task["description"] = "required " * 20_000
    monkeypatch.setattr(
        "werkstatt.chat_session.ChatSession",
        lambda *_args: pytest.fail("Do not open a chat when required evidence is over budget"),
    )

    result = reflection_chat.ask_project_chat_for_builder_task(state)

    assert result is None
    assert state.reflection_chat_error == "required_context_over_budget"


def test_reflection_context_budget_block_is_audited_with_source_manifest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = _state(tmp_path)
    events: list[tuple[str, dict[str, object]]] = []
    manifest = {"goal": {"chars": 50_000, "sha256": "abc123"}}
    monkeypatch.setattr(reflection, "_reflection_loop_core", lambda *_a, **_k: False)
    monkeypatch.setattr(
        reflection_chat, "_readable_evidence",
        lambda _state, **_kwargs: {
            "context_status": "blocked_required_context_over_budget",
            "required_chars": 50_000,
            "max_chars": 18_000,
            "sources": manifest,
            "omitted_optional": [],
        },
    )
    monkeypatch.setattr(
        reflection, "audit",
        lambda kind, payload, *_a, **_k: events.append((kind, payload)),
    )

    assert reflection._reflection_loop(state) is False

    blocked = [
        payload for kind, payload in events
        if kind == "loop_reflection_chat_skipped"
    ]
    assert blocked == [{
        "reason": "required_context_over_budget",
        "context_budget": {
            "context_status": "blocked_required_context_over_budget",
            "required_chars": 50_000,
            "max_chars": 18_000,
            "sources": manifest,
            "omitted_optional": [],
        },
    }]


def test_phase_end_handoff_preserves_full_reviewer_finding(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = _state(tmp_path)
    finding = "Review-Beleg: " + ("konkreter Befund. " * 300)
    state.reviewer_bugs = [{
        "file": "werkstatt/sample.py",
        "severity": "high",
        "description": finding,
    }]
    state.tasks = [{"task_files": ["werkstatt/sample.py"]}]
    captured: dict[str, object] = {}
    monkeypatch.setattr(reflection, "_phase_end_reflection_core", lambda _s: False)

    def capture(_state, *, failure_context=None):
        captured["evidence"] = reflection_chat._readable_evidence(
            _state, failure_context=failure_context,
        )

    monkeypatch.setattr(
        reflection_chat, "ask_project_chat_for_builder_task", capture,
    )
    monkeypatch.setattr(reflection, "audit", lambda *_args, **_kwargs: True)

    assert reflection._phase_end_reflection(state) is False

    evidence = captured["evidence"]
    assert isinstance(evidence, dict)
    assert evidence["context_status"] == "complete_required"
    assert evidence["reviewer_bugs"][0]["description"] == finding


def test_parse_task_accepts_only_authorized_files() -> None:
    valid = json.dumps({
        "decision": "task",
        "task": {
            "name": "Narrow type repair",
            "description": "Fix the incompatible assignment using the reported type.",
            "task_files": ["werkstatt/sample.py"],
            "source_evidence": _source_evidence(),
        },
    })
    invalid = json.dumps({
        "decision": "task",
        "task": {
            "name": "Expand scope",
            "description": "Modify an unrelated module.",
            "task_files": ["werkstatt/other.py"],
        },
    })
    assert reflection_chat._parse_task(
        valid, ["werkstatt/sample.py", "tests/test_sample.py"],
    ) == {
        "name": "Narrow type repair",
        "description": "Fix the incompatible assignment using the reported type.",
        "task_files": ["werkstatt/sample.py"],
        "source_evidence": _source_evidence(),
    }
    assert reflection_chat._parse_task(
        invalid, ["werkstatt/sample.py", "tests/test_sample.py"],
    ) is None


def test_chat_source_evidence_must_match_current_authorized_excerpt(
    tmp_path: Path,
) -> None:
    _state(tmp_path)
    task = {"source_evidence": _source_evidence()}

    verified = reflection_chat._verify_source_evidence(
        task, ["werkstatt/sample.py"], tmp_path,
    )

    assert verified is not None
    assert verified[0]["source_sha256"] == hashlib.sha256(
        (tmp_path / "werkstatt" / "sample.py").read_bytes(),
    ).hexdigest()
    tampered = {"source_evidence": [{
        **_source_evidence()[0], "quote": "fabricated source",
    }]}
    assert reflection_chat._verify_source_evidence(
        tampered, ["werkstatt/sample.py"], tmp_path,
    ) is None
    assert reflection_chat._verify_source_evidence(
        task, ["tests/test_sample.py"], tmp_path,
    ) is None


@pytest.mark.parametrize("cached", [False, True])
def test_chat_source_evidence_must_be_inside_proposed_builder_scope(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    cached: bool,
) -> None:
    state = _state(tmp_path)
    _install_run_store(monkeypatch, state, tmp_path)
    outside_quote = "def test_expected():\n    assert True"
    answer = json.dumps({
        "decision": "task",
        "task": {
            "name": "Repair implementation",
            "description": "Fix the implementation using its own source evidence.",
            "task_files": ["werkstatt/sample.py"],
            "source_evidence": [{
                "file": "tests/test_sample.py",
                "start": 0,
                "end": len(outside_quote),
                "quote": outside_quote,
            }],
        },
    })

    class FakeSession:
        def __init__(self, _project: str, _session_id: str) -> None:
            pass

        def get_job_turn(self, _job_id: str) -> dict[str, str] | None:
            return {"assistant_text": answer, "user_text": ""} if cached else None

        def delete_snapshot(self, _job_id: str) -> bool:
            return True

        def snapshot_to(
            self, _job_id: str, *, at_seq: int | None = None,
        ) -> object:
            assert at_seq == 0
            return object()

        def append_job_turn(self, *_args: object) -> None:
            pass

    monkeypatch.setattr("werkstatt.chat_session.ChatSession", FakeSession)
    monkeypatch.setattr("werkstatt.audit.audit", lambda *_args, **_kwargs: True)
    if not cached:
        def fake_chat_loop(_session, _message, **kwargs):
            kwargs["on_model_request"]({
                "request_number": 1,
                "request_sha256": "c" * 64,
                "message_count": 2,
            })
            kwargs["on_llm_call"]()
            return answer

        monkeypatch.setattr("werkstatt.chat_agent.chat_loop", fake_chat_loop)

    assert reflection_chat.ask_project_chat_for_builder_task(state) is None
    assert state.reflection_chat_error == "source_evidence_unverified"


def test_reflection_mode_exposes_only_read_tools(tmp_path: Path) -> None:
    reflection_names = {
        item["function"]["name"]
        for item in chat_tools.openai_schemas(mode="reflection")
    }
    read_names = {
        item["function"]["name"]
        for item in chat_tools.openai_schemas(mode="read")
    }
    assert reflection_names == read_names - {
        "request_loop_action", "read_chat_history",
    }
    assert "request_loop_action" not in reflection_names
    assert "request_loop_action" in read_names
    assert chat_tools.execute_tool(
        "request_loop_action", {"action": "start"}, mode="reflection",
        project_dir=tmp_path,
    ).startswith("Fehler: Tool 'request_loop_action'")
    assert chat_tools.execute_tool(
        "write_temp_test", {"content": "pass"}, mode="reflection",
        project_dir=tmp_path,
    ).startswith("Fehler: Tool 'write_temp_test'")


def test_chat_request_uses_read_only_snapshot_and_records_turn(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = _state(tmp_path)
    store = _install_run_store(monkeypatch, state, tmp_path)
    state.budget_exhausted_reason = "max_llm_calls"
    state.budget = {"max_llm_calls": 1}
    state.llm_calls = 1
    calls: dict[str, object] = {}
    audit_events: list[tuple[str, dict[str, object], str | None]] = []
    monkeypatch.setattr(
        "werkstatt.audit.audit",
        lambda kind, payload, _directory, _project, **kwargs: audit_events.append(
            (kind, payload, kwargs.get("run_id")),
        ) or True,
    )

    class FakeSession:
        def __init__(self, project: str, session_id: str) -> None:
            calls["parent"] = (project, session_id)

        def snapshot_to(
            self, target_session_id: str, *, at_seq: int | None = None,
        ) -> object:
            calls["snapshot"] = target_session_id
            calls["snapshot_seq"] = at_seq
            return object()

        def get_job_turn(self, _job_id: str) -> dict[str, str] | None:
            prior = calls.get("prior")
            return prior if isinstance(prior, dict) else None

        def append_job_turn(self, *args: object) -> None:
            calls["job_turn"] = args

        def delete_snapshot(self, target_session_id: str) -> bool:
            calls["deleted"] = target_session_id
            return True

    monkeypatch.setattr(
        "werkstatt.chat_session.ChatSession", FakeSession,
    )
    expected = {
        "decision": "task",
        "task": {
            "name": "Narrow type repair",
            "description": "Use the expected type from the failing check.",
            "task_files": ["werkstatt/sample.py"],
            "source_evidence": _source_evidence(),
        },
    }

    def fake_chat_loop(session, message, **kwargs):
        calls["tools"] = set(kwargs["tools"])
        calls["mode"] = kwargs["mode"]
        calls["message"] = message
        calls["session"] = session
        calls["project_dir"] = kwargs["project_dir"]
        calls["max_rounds"] = kwargs["max_rounds"]
        calls["max_elapsed_s"] = kwargs["max_elapsed_s"]
        calls["allow_time_budget_finalize"] = kwargs[
            "allow_time_budget_finalize"
        ]
        kwargs["on_model_request"]({
            "request_number": 1,
            "request_sha256": "b" * 64,
            "message_count": 2,
        })
        kwargs["on_llm_call"]()
        return json.dumps(expected)

    monkeypatch.setattr("werkstatt.chat_agent.chat_loop", fake_chat_loop)
    state.builder_failure_reason = "pytest reported expected 2, got 1"
    result = reflection_chat.ask_project_chat_for_builder_task(
        state, failure_context="Reflection stopped after a stale patch.",
    )

    assert result == {
        **expected["task"],
        "source_evidence": _verified_source_evidence(tmp_path),
    }
    assert calls["mode"] == "reflection"
    assert "request_loop_action" not in calls["tools"]
    assert "write_temp_test" not in calls["tools"]
    assert "mypy: sample.py:10 incompatible type" in calls["message"]
    assert "Reflection stopped after a stale patch." in calls["message"]
    assert "pytest reported expected 2, got 1" in calls["message"]
    assert "AC-1" in calls["message"]
    assert "test_expected" in calls["message"]
    assert "Keep the public API stable" in calls["message"]
    assert calls["deleted"] == calls["snapshot"]
    assert calls["snapshot_seq"] == 0
    assert calls["job_turn"]
    assert state.llm_calls == 2
    assert calls["max_rounds"] == reflection_chat.REFLECTION_CHAT_MAX_CALLS - 1
    assert calls["max_elapsed_s"] == reflection_chat.REFLECTION_CHAT_MAX_ELAPSED_S
    assert calls["allow_time_budget_finalize"] is False
    prompt = calls["message"]
    assert isinstance(prompt, str)
    evidence_start = prompt.index("\n\nBELEGE:\n") + len("\n\nBELEGE:\n")
    evidence_text = prompt[evidence_start:]
    request_audit = audit_events[0][1]
    assert request_audit["evidence_prompt_span"] == {
        "unit": "unicode_codepoints",
        "start": evidence_start,
        "end": len(prompt),
        "sha256": hashlib.sha256(evidence_text.encode("utf-8")).hexdigest(),
    }
    assert request_audit["chat_prompt_chars"] == len(prompt)
    assert request_audit["chat_prompt_sha256"] == hashlib.sha256(
        prompt.encode("utf-8"),
    ).hexdigest()
    assert state.reflection_chat_calls == 1
    assert store.get_run_record("alpha", "alpha-run-1")["checkpoint"][
        "reflection_chat_recovery_calls"
    ] == 1
    assert "source_evidence" in calls["message"]
    assert "read_file-Auszug" in calls["message"]
    assert audit_events[0][0] == "loop_reflection_chat_model_request"
    assert audit_events[0][1]["evidence_sha256"]
    assert audit_events[0][1]["origin_history_snapshot_seq"] == 0
    assert audit_events[0][1]["request_sha256"] == "b" * 64
    assert audit_events[0][2] == "alpha-run-1"


def test_chat_request_reuses_completed_idempotent_job_turn(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = _state(tmp_path)
    answer = json.dumps({
        "decision": "task",
        "task": {
            "name": "Narrow type repair",
            "description": "Use the expected type from the failing check.",
            "task_files": ["werkstatt/sample.py"],
            "source_evidence": _source_evidence(),
        },
    })
    calls: dict[str, object] = {
        "prior": {"assistant_text": answer, "user_text": "prior prompt"},
    }

    class FakeSession:
        def __init__(self, _project: str, _session_id: str) -> None:
            pass

        def get_job_turn(self, _job_id: str):
            return calls["prior"]

    monkeypatch.setattr("werkstatt.chat_session.ChatSession", FakeSession)
    monkeypatch.setattr(
        "werkstatt.chat_agent.chat_loop",
        lambda *_args, **_kwargs: pytest.fail("Completed job must not call Chat again"),
    )

    result = reflection_chat.ask_project_chat_for_builder_task(state)

    assert result == {
        "name": "Narrow type repair",
        "description": "Use the expected type from the failing check.",
        "task_files": ["werkstatt/sample.py"],
        "source_evidence": _verified_source_evidence(tmp_path),
    }


def test_exhausted_run_chat_reserve_is_separately_bounded(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = _state(tmp_path)
    store = _install_run_store(monkeypatch, state, tmp_path)
    state.budget_exhausted_reason = "max_minutes"
    calls = {"deleted": False}

    class FakeSession:
        def __init__(self, _project: str, _session_id: str) -> None:
            pass

        def get_job_turn(self, _job_id: str):
            return None

        def snapshot_to(self, _job_id: str, *, at_seq: int | None = None):
            assert at_seq == 0
            return object()

        def delete_snapshot(self, _job_id: str) -> bool:
            calls["deleted"] = True
            return True

        def append_job_turn(self, *_args: object) -> None:
            pass

    monkeypatch.setattr("werkstatt.chat_session.ChatSession", FakeSession)

    def overrun_chat_loop(_session, _message, **kwargs):
        count_call = kwargs["on_llm_call"]
        for _ in range(reflection_chat.REFLECTION_CHAT_MAX_CALLS):
            count_call()
        with pytest.raises(RuntimeError, match="recovery_call_limit"):
            count_call()
        raise RuntimeError("recovery_call_limit")

    monkeypatch.setattr("werkstatt.chat_agent.chat_loop", overrun_chat_loop)

    assert reflection_chat.ask_project_chat_for_builder_task(state) is None
    assert state.reflection_chat_calls == reflection_chat.REFLECTION_CHAT_MAX_CALLS
    assert state.reflection_chat_error == "RuntimeError"
    assert calls["deleted"] is True
    assert store.get_run_record("alpha", "alpha-run-1")["checkpoint"][
        "reflection_chat_recovery_calls"
    ] == reflection_chat.REFLECTION_CHAT_MAX_CALLS


def test_recovery_chat_reserve_survives_new_runstate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = _state(tmp_path)
    store = _install_run_store(monkeypatch, state, tmp_path)
    for _ in range(reflection_chat.REFLECTION_CHAT_MAX_CALLS):
        reflection_chat._claim_recovery_chat_call(state)

    resumed = _state(tmp_path)
    with pytest.raises(RuntimeError, match="recovery_budget_exhausted"):
        reflection_chat._claim_recovery_chat_call(resumed)

    record = store.get_run_record("alpha", "alpha-run-1")
    assert record is not None
    assert record["checkpoint"]["reflection_chat_recovery_calls"] == (
        reflection_chat.REFLECTION_CHAT_MAX_CALLS
    )


def test_recovery_builder_reserve_is_single_use_and_survives_resume(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = _state(tmp_path)
    store = _install_run_store(monkeypatch, state, tmp_path)

    assert reflection_chat.claim_recovery_builder_call(state) == 1
    resumed = _state(tmp_path)
    with pytest.raises(RuntimeError, match="reserve_exhausted"):
        reflection_chat.claim_recovery_builder_call(resumed)

    checkpoint = store.get_run_record("alpha", "alpha-run-1")["checkpoint"]
    assert checkpoint["reflection_chat_builder_calls"] == 1
    assert checkpoint["reflection_chat_builder_expires_at"]


def test_recovery_builder_reserve_expiry_is_durable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from datetime import UTC, datetime, timedelta

    state = _state(tmp_path)
    store = _install_run_store(monkeypatch, state, tmp_path)
    record = store.get_run_record("alpha", "alpha-run-1")
    assert record is not None
    checkpoint = dict(record["checkpoint"])
    checkpoint["reflection_chat_builder_expires_at"] = (
        datetime.now(UTC) - timedelta(seconds=1)
    ).isoformat()
    store.update_run_checkpoint(
        "alpha", "alpha-run-1", checkpoint,
        expected_version=record["checkpoint_version"],
    )

    with pytest.raises(RuntimeError, match="reserve_expired"):
        reflection_chat.claim_recovery_builder_call(_state(tmp_path))


def test_reflection_uses_chat_task_once_and_restores_original_task(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = _state(tmp_path)
    original = state.aktuelle_task
    calls: list[dict[str, object]] = []

    def fake_core(_state, **kwargs):
        calls.append({
            "task": dict(_state.aktuelle_task),
            "source_evidence": list(_state.reflection_chat_evidence),
            **kwargs,
        })
        return len(calls) == 2

    monkeypatch.setattr(reflection, "_reflection_loop_core", fake_core)
    monkeypatch.setattr(
        reflection_chat,
        "ask_project_chat_for_builder_task",
        lambda _state, **_kwargs: {
            "name": "Narrow type repair",
            "description": "Use the expected type from the failing check.",
            "task_files": ["werkstatt/sample.py"],
            "source_evidence": _source_evidence(),
        },
    )
    monkeypatch.setattr(reflection, "audit", lambda *args, **kwargs: True)

    assert reflection._reflection_loop(state, max_runden=2) is True
    assert calls[1]["task"]["name"] == "Narrow type repair"
    assert calls[1]["task"]["task_files"] == ["werkstatt/sample.py"]
    assert calls[1]["task"]["acceptance_criteria"] == ["AC-1"]
    assert calls[1]["source_evidence"] == _source_evidence()
    assert calls[1]["max_runden"] == 2
    assert state.aktuelle_task is original
    assert state.reflection_chat_evidence == []


def test_reflection_asks_chat_from_bounded_reserve_when_run_budget_is_exhausted(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = _state(tmp_path)
    state.budget_exhausted_reason = "max_llm_calls"
    core_calls = []

    def fake_core(*_args, **_kwargs):
        core_calls.append(True)
        return len(core_calls) == 2

    monkeypatch.setattr(
        reflection, "_reflection_loop_core", fake_core,
    )
    monkeypatch.setattr(
        reflection_chat, "_readable_evidence",
        lambda _state, **_kwargs: {"context_status": "complete_required"},
    )
    monkeypatch.setattr(
        reflection_chat, "ask_project_chat_for_builder_task",
        lambda _state, **_kwargs: {
            "name": "Bounded repair",
            "description": "Fix the proven failure in the scoped file.",
            "task_files": ["werkstatt/sample.py"],
            "source_evidence": _source_evidence(),
        },
    )
    monkeypatch.setattr(reflection, "audit", lambda *args, **kwargs: True)

    assert reflection._reflection_loop(state) is True
    assert len(core_calls) == 2


def test_phase_end_exhaustion_asks_chat_then_retries_scoped_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = _state(tmp_path)
    state.budget_exhausted_reason = "max_minutes"
    state.reviewer_bugs = [{
        "file": "werkstatt/sample.py",
        "severity": "high",
        "description": "The sample fails the phase review.",
    }]
    state.tasks = [{"task_files": ["werkstatt/sample.py"]}]
    original_task = state.aktuelle_task
    core_calls: list[dict[str, object]] = []

    def fake_core(_state, *, builder_task_override=None):
        core_calls.append({
            "task": dict(_state.aktuelle_task),
            "bugs": list(_state.reviewer_bugs),
            "source_evidence": list(_state.reflection_chat_evidence),
            "builder_task_override": builder_task_override,
        })
        return len(core_calls) == 2

    monkeypatch.setattr(reflection, "_phase_end_reflection_core", fake_core)
    monkeypatch.setattr(
        reflection_chat,
        "ask_project_chat_for_builder_task",
        lambda _state, **_kwargs: {
            "name": "Repair phase-review finding",
            "description": "Correct the reported phase-review defect.",
            "task_files": ["werkstatt/sample.py"],
            "source_evidence": _source_evidence(),
        },
    )
    monkeypatch.setattr(reflection, "audit", lambda *args, **kwargs: True)

    assert reflection._phase_end_reflection(state) is True
    assert len(core_calls) == 2
    assert core_calls[1]["task"]["name"] == "Repair phase-review finding"
    assert core_calls[1]["bugs"][0]["description"] == (
        "The sample fails the phase review."
    )
    assert core_calls[1]["builder_task_override"]["description"] == (
        "Correct the reported phase-review defect."
    )
    assert core_calls[1]["source_evidence"] == _source_evidence()
    assert state.aktuelle_task is original_task
    assert state.reflection_chat_evidence == []
    assert state.reviewer_bugs[0]["description"] == (
        "The sample fails the phase review."
    )


def test_phase_end_core_uses_chat_task_without_rewriting_reviewer_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from werkstatt import reviewer

    state = _state(tmp_path)
    state.reviewer_bugs = [{
        "file": "werkstatt/sample.py",
        "severity": "high",
        "description": "Original phase-review evidence.",
    }]
    state.applied_count = 0
    state.patches = []
    proposed_name = "Evidence-driven repair " + ("x" * 217)
    assert len(proposed_name) == 240
    override = {
        "name": proposed_name,
        "description": "Apply the source-backed correction.",
        "task_files": ["werkstatt/sample.py"],
    }
    builder_tasks = []

    def run_builder(_state):
        builder_tasks.append(dict(_state.aktuelle_task))
        _state.patches = [{"file": "werkstatt/sample.py"}]
        return True

    monkeypatch.setattr(reflection, "run_builder", run_builder)
    monkeypatch.setattr(reflection, "check_run_lease", lambda _state: None)
    monkeypatch.setattr(
        reflection, "_apply_patches_with_diagnose",
        lambda *_args, **_kwargs: (1, {}),
    )
    monkeypatch.setattr(reflection, "_verify_patches", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(reviewer, "run_phase_end_review", lambda _state: True)
    monkeypatch.setattr(reflection, "audit", lambda *args, **kwargs: True)

    assert reflection._phase_end_reflection_core(
        state, builder_task_override=override,
    ) is True
    assert builder_tasks[0]["name"] == proposed_name
    assert builder_tasks[0]["description"] == "Apply the source-backed correction."
    assert builder_tasks[0]["task_files"] == ["werkstatt/sample.py"]
    assert state.reviewer_bugs == [{
        "file": "werkstatt/sample.py",
        "severity": "high",
        "description": "Original phase-review evidence.",
    }]


def test_phase_end_does_not_expand_chat_scope_beyond_planned_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = _state(tmp_path)
    state.reviewer_bugs = [{
        "file": "werkstatt/unplanned.py",
        "severity": "high",
        "description": "Outside the plan.",
    }]
    state.tasks = [{"task_files": ["werkstatt/sample.py"]}]
    monkeypatch.setattr(
        reflection, "_phase_end_reflection_core",
        lambda _s, **_kwargs: False,
    )
    monkeypatch.setattr(
        reflection_chat, "ask_project_chat_for_builder_task",
        lambda _state, **_kwargs: pytest.fail("Chat must not receive out-of-plan file scope"),
    )
    monkeypatch.setattr(reflection, "audit", lambda *args, **kwargs: True)

    assert reflection._phase_end_reflection(state) is False


def test_chat_recovery_cannot_override_declined_phase_review_gate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = _state(tmp_path)

    def declined_gate(_state):
        _state.reflection_chat_stop_reason = "human_gate_not_approved"
        return False

    monkeypatch.setattr(
        reflection, "_phase_end_reflection_core", declined_gate,
    )
    monkeypatch.setattr(
        reflection_chat, "ask_project_chat_for_builder_task",
        lambda _state, **_kwargs: pytest.fail("Chat must not override a declined gate"),
    )
    monkeypatch.setattr(reflection, "audit", lambda *args, **kwargs: True)

    assert reflection._phase_end_reflection(state) is False
