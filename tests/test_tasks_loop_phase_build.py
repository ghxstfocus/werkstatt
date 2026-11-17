"""Runtime regressions for checkpoint-selected task dispatch."""
from __future__ import annotations

from tests.factories import coordinator_decision_for_task


def test_task_outcome_event_has_stable_id_and_state_evidence(
    monkeypatch, tmp_path,
):
    from werkstatt.roles import task_dispatch as tasks

    events = []
    monkeypatch.setattr(tasks, "audit", lambda *args: events.append(args))

    tasks._audit_task_ok(
        True, "t-build-api", "API bauen", tmp_path, "demo",
        via="reflection",
    )

    assert len(events) == 1
    kind, payload = events[0][:2]
    assert kind == "loop_task_ok"
    assert payload["task_id"] == "t-build-api"
    assert payload["status"] == "done"
    assert payload["result_summary"]
    assert payload["evidence"] == ["Phase-State: done"]
    assert payload["via"] == "reflection"


def test_task_outcome_event_omitted_without_done_transition(
    monkeypatch, tmp_path,
):
    from werkstatt.roles import task_dispatch as tasks

    events = []
    monkeypatch.setattr(tasks, "audit", lambda *args: events.append(args))

    tasks._audit_task_ok(
        False, "t-review", "Review", tmp_path, "demo",
    )

    assert events == []


def test_tasks_loop_resume_counts_persisted_done_tasks(monkeypatch, tmp_path):
    """Resume nach rotem Final-Verify muss erledigte Arbeit weiterzaehlen."""
    from werkstatt.phase_state import PhaseState
    from werkstatt.roles import task_dispatch as tasks
    from werkstatt.state import RunState

    planned = [{"id": "t1", "name": "Implementierung"}]
    phase_state = PhaseState("testproj", base_dir=tmp_path / ".werkstatt")
    phase_state.init_new("Final-Verify wiederholen", planned)
    phase_state.mark_done("t1")

    state = RunState(
        block_id="t", aufgabe="Final-Verify wiederholen",
        start_ts="2026-11-12T00:00:00Z", docs={}, agents={}, always={},
        optional={}, file_whitelist=[], api_key="sk-test", budget={},
        agent_docs={}, project_dir=tmp_path, project_name="testproj",
    )
    state.tasks = planned
    monkeypatch.setattr(
        "werkstatt.agent._enforce_run_budget", lambda _state: False,
    )
    events = []
    monkeypatch.setattr(tasks, "audit", lambda *args: events.append(args))

    rc, tasks_ok, returned_tasks = tasks.run_task_checkpoint(
        state, phase_state,
        coordinator_decision=coordinator_decision_for_task(phase_state, state),
    )

    assert rc == 0
    assert tasks_ok == 1
    assert returned_tasks == planned
    assert state.tasks_ok_counter == 1
    assert any(
        event[0] == "loop_phase"
        and event[1].get("phase") == "build"
        for event in events
    )


def test_builder_failure_returns_to_coordinator_without_inline_recovery(
    monkeypatch, tmp_path,
):
    from tests.factories import mk_state
    from werkstatt.phase_state import PhaseState
    from werkstatt.roles import task_dispatch as tasks

    source = tmp_path / "sample.py"
    source.write_text("value = 1\n", encoding="utf-8")
    planned = [{
        "id": "t1", "name": "Implementierung", "action": "update",
        "task_files": ["sample.py"],
    }]
    phase_state = PhaseState("testproj", base_dir=tmp_path / ".werkstatt")
    phase_state.init_new("Ziel", planned)
    state = mk_state(
        project_dir=tmp_path, project_name="testproj", aufgabe="Ziel",
        tasks=planned,
    )
    events = []
    worker_calls = []
    monkeypatch.setattr("werkstatt.audit.get_run_id", lambda: None)
    monkeypatch.setattr("werkstatt.agent._enforce_run_budget", lambda _state: False)
    monkeypatch.setattr(tasks, "audit", lambda *args, **_kwargs: events.append(args))
    monkeypatch.setattr("werkstatt.progress.append", lambda *_a, **_k: None)

    def builder_failed(*_args, **_kwargs):
        worker_calls.append("builder")
        state.builder_failure_reason = "invalid_patch_response"
        state.builder_failure_detail = "structured patch missing"
        return False

    monkeypatch.setattr(tasks, "_run_with_progress", builder_failed)
    monkeypatch.setattr(
        tasks, "run_reviewer",
        lambda *_a, **_k: worker_calls.append("reviewer") or True,
    )

    result = tasks.run_task_checkpoint(
        state,
        phase_state,
        coordinator_decision=coordinator_decision_for_task(
            phase_state, state,
        ),
    )

    assert result[0] == 0
    assert worker_calls == ["builder"]
    assert phase_state.get_task("t1")["status"] == "failed"
    assert any(
        event[0] == "loop_task_failed"
        and event[1].get("coordinator_reentry") is True
        for event in events
    )


def test_exhausted_budget_stops_before_worker_or_chat_recovery(
    monkeypatch, tmp_path,
):
    """Budget exhaustion is a coordinator boundary, not inline role recovery."""
    from werkstatt.phase_state import PhaseState
    from werkstatt.roles import task_dispatch as tasks
    from werkstatt.state import RunState

    planned = [{
        "id": "t1", "name": "Implementierung", "action": "update",
        "task_files": ["sample.py"],
    }]
    phase_state = PhaseState("testproj", base_dir=tmp_path / ".werkstatt")
    phase_state.init_new("Ziel", planned)
    state = RunState(
        aufgabe="Ziel", api_key="sk-test", budget={"max_llm_calls": 1},
        llm_calls=1, project_dir=tmp_path, project_name="testproj",
    )
    state.chat_origin_session_id = "session-1"
    state.tasks = planned
    worker_calls = []

    monkeypatch.setattr("werkstatt.audit.get_run_id", lambda: None)
    monkeypatch.setattr(
        "werkstatt.agent._enforce_run_budget",
        lambda current: setattr(
            current, "budget_exhausted_reason", "LLM-Aufrufbudget erreicht"
        ) or True,
    )
    monkeypatch.setattr(tasks, "audit", lambda *_args, **_kwargs: None)

    monkeypatch.setattr(
        tasks, "_run_with_progress",
        lambda *_args, **_kwargs: worker_calls.append("builder") or False,
    )

    rc, tasks_ok, _returned = tasks.run_task_checkpoint(
        state, phase_state,
        coordinator_decision=coordinator_decision_for_task(phase_state, state),
    )

    assert rc == 1
    assert tasks_ok == 0
    assert worker_calls == []
    assert phase_state.get_task("t1")["status"] == "pending"
