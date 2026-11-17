from __future__ import annotations

import hashlib

from werkstatt import loop, planner
from werkstatt.architect import _format_scout_source_evidence
from werkstatt.planner_artifacts import make_role_artifact
from werkstatt.state import RunState


def _state_with_persisted_handoff(tmp_path):
    source = tmp_path / "src" / "api.py"
    source.parent.mkdir(parents=True)
    source.write_text("def apply_change():\n    return True\n", encoding="utf-8")
    source_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
    goal = "Implement the behavior described in the Architect handoff."
    report = {
        "auftrag_prosa": "Implement the requested behavior safely.",
        "relevante_dateien": [{"pfad": "src/api.py", "zeilen": [1]}],
        "api_auszug": {},
    }
    prose = (
        "Implement the complete public behavior while preserving the API. "
        "Add validation and verify the result against the accepted goal."
    )
    _source_context, source_manifest = _format_scout_source_evidence(
        tmp_path, report,
    )
    state = RunState(
        aufgabe=goal,
        project_name="sample",
        project_dir=tmp_path,
        run_id="run-1",
        api_key="test-key",
        explorer_context={"key_files": [{
            "file": "src/api.py", "source_sha256": source_sha256,
        }]},
    )
    state.architect_scout_source_manifest = source_manifest
    state.planner_role_artifacts = {
        "scout": make_role_artifact(
            "scout", report, run_id="run-1", goal=goal,
            input_sha256="a" * 64,
        ),
        "architect": make_role_artifact(
            "architect", prose, run_id="run-1", goal=goal,
            input_sha256="b" * 64,
        ),
    }
    persisted = []
    state.planner_role_artifact_callback = persisted.append
    assert planner._persist_planner_split_handoff(
        state,
        goal=goal,
        scout_report=report,
        architect_scout_report=report,
        scout_input_sha256="a" * 64,
        architect_prose=prose,
        architect_input_sha256="b" * 64,
    )
    assert len(persisted) == 1
    return state, goal, source


def test_planner_handoff_is_persisted_and_bound_to_current_source(tmp_path):
    state, goal, _source = _state_with_persisted_handoff(tmp_path)

    handoff = planner._load_current_planner_split_handoff(state, goal)

    assert handoff is not None
    assert handoff["architect_prose"] == state.planner_role_artifacts[
        "architect"
    ]["output"]
    assert handoff["key_files"] == ["src/api.py"]


def test_planner_handoff_is_rejected_after_source_changes(tmp_path):
    state, goal, source = _state_with_persisted_handoff(tmp_path)
    source.write_text("def changed():\n    return False\n", encoding="utf-8")

    assert planner._load_current_planner_split_handoff(state, goal) is None


def test_planner_split_action_compiles_from_handoff_without_run_planner(
    tmp_path, monkeypatch,
):
    state, goal, _source = _state_with_persisted_handoff(tmp_path)

    def compile_graph(_prose, _files, _key, _project, _name, *, aufgabe, state):
        assert aufgabe == goal
        state.akzeptanzkriterien = [goal]
        return [{
            "id": "t1", "name": "Implement behavior", "action": "update",
            "task_files": ["src/api.py"], "criterion_refs": ["AC1"],
        }]

    monkeypatch.setattr(planner, "_zerlege_in_sub_tasks", compile_graph)
    monkeypatch.setattr(planner, "_normalisiere_task_files", lambda tasks, *_: tasks)
    monkeypatch.setattr(
        planner, "run_planner",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("current handoff must bypass the planner orchestrator"),
        ),
    )
    monkeypatch.setattr(loop, "_plan_gate", lambda _state: True)

    result = loop._dispatch_planner_checkpoint_action(
        state, "planner_split", goal, "sample", object(),
    )

    assert result == (0, False)
    assert state.planner_plan_candidate_ready is True
    assert state.planner_yielded_after_role == "planner_split"
    assert [task["id"] for task in state.tasks] == ["t1"]


def test_stale_handoff_returns_to_planner_for_role_refresh(tmp_path, monkeypatch):
    state, goal, source = _state_with_persisted_handoff(tmp_path)
    source.write_text("def changed():\n    return False\n", encoding="utf-8")
    calls = []

    def refresh_upstream(actual_state, *, stop_after_role):
        calls.append((actual_state, stop_after_role))
        actual_state.planner_step_yielded = True
        actual_state.planner_yielded_after_role = "architect"
        return True

    monkeypatch.setattr("werkstatt.planner.run_planner", refresh_upstream)

    result = loop._dispatch_planner_checkpoint_action(
        state, "planner_split", goal, "sample", object(),
    )

    assert result == (0, False)
    assert calls == [(state, "planner_split")]
    assert state.planner_plan_candidate_ready is False
