from __future__ import annotations

from types import SimpleNamespace

from werkstatt.planner_recovery import replan_task_graph_from_architect
from werkstatt.task_graph import TaskGraphError


def _state(tmp_path):
    return SimpleNamespace(
        project_dir=tmp_path,
        project_name="alpha",
        api_key="test-key",
        architect_prosa="## werkstatt/sample.py\nUpdate one function.",
        explorer_context={"key_files": [{"file": "werkstatt/sample.py"}]},
        akzeptanzkriterien=["AC1: Verhalten bleibt korrekt"],
        aufgabe="Korrigiere werkstatt/sample.py",
        tasks=[{"id": "old", "task_files": ["werkstatt/old.py"]}],
        architect_scout_source_manifest={"sources": []},
        phasen=["old-phase"],
        tests=["old-test"],
    )


def test_recovery_role_replaces_graph_only_after_valid_compile(tmp_path) -> None:
    state = _state(tmp_path)
    new_graph = [{"id": "new", "task_files": ["werkstatt/sample.py"]}]
    audit_events = []
    compile_calls = []

    def compile_graph(*args, **kwargs):
        compile_calls.append((args, kwargs))
        return new_graph

    result = replan_task_graph_from_architect(
        state,
        {"regel": "TASK_GRAPH", "fakt": "missing dependency"},
        compile_graph=compile_graph,
        normalize_task_files=lambda tasks, *_args: tasks,
        audit_call=lambda *args: audit_events.append(args),
    )

    assert result is True
    assert state.tasks is new_graph
    assert state.akzeptanzkriterien == ["AC1: Verhalten bleibt korrekt"]
    assert state.phasen == []
    assert state.tests == []
    assert compile_calls[0][1]["preserve_criteria"] == [
        "AC1: Verhalten bleibt korrekt",
    ]
    assert audit_events[-1][0] == "loop_plan_reflection"


def test_recovery_role_keeps_current_graph_on_compile_rejection(tmp_path) -> None:
    state = _state(tmp_path)
    old_graph = state.tasks
    criteria = list(state.akzeptanzkriterien)
    audit_events = []

    def compile_graph(*_args, **_kwargs):
        raise TaskGraphError("criteria changed")

    result = replan_task_graph_from_architect(
        state,
        {"regel": "ACCEPTANCE_COVERAGE"},
        compile_graph=compile_graph,
        normalize_task_files=lambda tasks, *_args: tasks,
        audit_call=lambda *args: audit_events.append(args),
    )

    assert result is False
    assert state.tasks is old_graph
    assert state.akzeptanzkriterien == criteria
    assert audit_events[-1][1]["reason"] == "split_contract_rejected"


def test_recovery_role_rejects_unrelated_gate_before_compiler(tmp_path) -> None:
    state = _state(tmp_path)
    called = False

    def compile_graph(*_args, **_kwargs):
        nonlocal called
        called = True
        return []

    result = replan_task_graph_from_architect(
        state,
        {"regel": "TASK_FILE"},
        compile_graph=compile_graph,
        normalize_task_files=lambda tasks, *_args: tasks,
        audit_call=lambda *_args: None,
    )

    assert result is False
    assert called is False
