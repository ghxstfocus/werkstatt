from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from werkstatt import chat_tools, reflection, reflection_chat


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
    )


def test_scoped_files_reject_paths_outside_project() -> None:
    assert reflection_chat._scoped_files({"task_files": ["../outside.py"]}) == []
    assert reflection_chat._scoped_files({"task_files": ["C:/outside.py"]}) == []
    assert reflection_chat._scoped_files({"task_files": ["pkg/file.py"]}) == [
        "pkg/file.py",
    ]


def test_parse_task_accepts_only_authorized_files() -> None:
    valid = json.dumps({
        "decision": "task",
        "task": {
            "name": "Narrow type repair",
            "description": "Fix the incompatible assignment using the reported type.",
            "task_files": ["werkstatt/sample.py"],
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
    }
    assert reflection_chat._parse_task(
        invalid, ["werkstatt/sample.py", "tests/test_sample.py"],
    ) is None


def test_reflection_mode_exposes_only_read_tools(tmp_path: Path) -> None:
    reflection_names = {
        item["function"]["name"]
        for item in chat_tools.openai_schemas(mode="reflection")
    }
    read_names = {
        item["function"]["name"]
        for item in chat_tools.openai_schemas(mode="read")
    }
    assert reflection_names == read_names - {"request_loop_action"}
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
    calls: dict[str, object] = {}

    class FakeSession:
        def __init__(self, project: str, session_id: str) -> None:
            calls["parent"] = (project, session_id)

        def snapshot_to(self, target_session_id: str) -> object:
            calls["snapshot"] = target_session_id
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
        },
    }

    def fake_chat_loop(session, message, **kwargs):
        calls["tools"] = set(kwargs["tools"])
        calls["mode"] = kwargs["mode"]
        calls["message"] = message
        calls["session"] = session
        calls["project_dir"] = kwargs["project_dir"]
        kwargs["on_llm_call"]()
        return json.dumps(expected)

    monkeypatch.setattr("werkstatt.chat_agent.chat_loop", fake_chat_loop)
    result = reflection_chat.ask_project_chat_for_builder_task(state)

    assert result == expected["task"]
    assert calls["mode"] == "reflection"
    assert "request_loop_action" not in calls["tools"]
    assert "write_temp_test" not in calls["tools"]
    assert "mypy: sample.py:10 incompatible type" in calls["message"]
    assert "AC-1" in calls["message"]
    assert "test_expected" in calls["message"]
    assert "Keep the public API stable" in calls["message"]
    assert calls["deleted"] == calls["snapshot"]
    assert calls["job_turn"]
    assert state.llm_calls == 1


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
    }


def test_reflection_uses_chat_task_once_and_restores_original_task(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = _state(tmp_path)
    original = state.aktuelle_task
    calls: list[dict[str, object]] = []

    def fake_core(_state, **kwargs):
        calls.append({"task": dict(_state.aktuelle_task), **kwargs})
        return len(calls) == 2

    monkeypatch.setattr(reflection, "_reflection_loop_core", fake_core)
    monkeypatch.setattr(
        reflection_chat,
        "ask_project_chat_for_builder_task",
        lambda _state: {
            "name": "Narrow type repair",
            "description": "Use the expected type from the failing check.",
            "task_files": ["werkstatt/sample.py"],
        },
    )
    monkeypatch.setattr(reflection, "audit", lambda *args, **kwargs: True)

    assert reflection._reflection_loop(state, max_runden=2) is True
    assert calls[1]["task"]["name"] == "Narrow type repair"
    assert calls[1]["task"]["task_files"] == ["werkstatt/sample.py"]
    assert calls[1]["task"]["acceptance_criteria"] == ["AC-1"]
    assert calls[1]["max_runden"] == 1
    assert state.aktuelle_task is original


def test_reflection_does_not_ask_chat_when_run_budget_is_exhausted(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = _state(tmp_path)
    state.budget_exhausted_reason = "max_llm_calls"
    monkeypatch.setattr(reflection, "_reflection_loop_core", lambda *_a, **_k: False)
    monkeypatch.setattr(
        reflection_chat, "ask_project_chat_for_builder_task",
        lambda _state: pytest.fail("Chat must not bypass the exhausted run budget"),
    )
    monkeypatch.setattr(reflection, "audit", lambda *args, **kwargs: True)

    assert reflection._reflection_loop(state) is False


def test_phase_end_exhaustion_asks_chat_then_retries_scoped_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state = _state(tmp_path)
    state.reviewer_bugs = [{
        "file": "werkstatt/sample.py",
        "severity": "high",
        "description": "The sample fails the phase review.",
    }]
    state.tasks = [{"task_files": ["werkstatt/sample.py"]}]
    original_task = state.aktuelle_task
    core_calls: list[dict[str, object]] = []

    def fake_core(_state):
        core_calls.append({
            "task": dict(_state.aktuelle_task),
            "bugs": list(_state.reviewer_bugs),
        })
        return len(core_calls) == 2

    monkeypatch.setattr(reflection, "_phase_end_reflection_core", fake_core)
    monkeypatch.setattr(
        reflection_chat,
        "ask_project_chat_for_builder_task",
        lambda _state: {
            "name": "Repair phase-review finding",
            "description": "Correct the reported phase-review defect.",
            "task_files": ["werkstatt/sample.py"],
        },
    )
    monkeypatch.setattr(reflection, "audit", lambda *args, **kwargs: True)

    assert reflection._phase_end_reflection(state) is True
    assert len(core_calls) == 2
    assert core_calls[1]["task"]["name"] == "Repair phase-review finding"
    assert core_calls[1]["bugs"][0]["description"] == (
        "Correct the reported phase-review defect."
    )
    assert state.aktuelle_task is original_task


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
    monkeypatch.setattr(reflection, "_phase_end_reflection_core", lambda _s: False)
    monkeypatch.setattr(
        reflection_chat, "ask_project_chat_for_builder_task",
        lambda _state: pytest.fail("Chat must not receive out-of-plan file scope"),
    )
    monkeypatch.setattr(reflection, "audit", lambda *args, **kwargs: True)

    assert reflection._phase_end_reflection(state) is False
