from __future__ import annotations

from types import SimpleNamespace

from werkstatt import planner
from werkstatt.roles import scout_execution
from werkstatt.roles.scout_execution import ScoutCheckpointResult


def _state(tmp_path):
    return SimpleNamespace(
        api_key="test-key",
        project_dir=tmp_path,
        project_name="demo",
        run_id="run-1",
        aufgabe="Inspect the current source",
        explorer_context={"key_files": [{"file": "src/a.py"}]},
        planner_role_artifacts={},
        planner_role_artifact_callback=None,
        planner_coordinator_role=None,
        planner_coordinator_source_evidence=(),
        planner_step_yielded=False,
        planner_yielded_after_role=None,
        planner_plan_candidate_ready=False,
        architect_required_source_files=[],
        akzeptanzkriterien=[],
        tasks=[],
        tests=[],
        phasen=[],
    )


def _result(report):
    return ScoutCheckpointResult(
        report=report,
        skip_path=None,
        route_reason="evidence_needed",
        source="Scout",
        code_index={},
        input_sha256="a" * 64,
        reused_artifact=False,
        artifact_persisted=False,
    )


def test_selected_scout_persists_current_artifact_and_yields(
    tmp_path, monkeypatch,
):
    state = _state(tmp_path)
    state.planner_action_role = "scout"
    report = {"auftrag_prosa": "Investigate the current source."}
    persisted = []
    events = []
    state.planner_role_artifact_callback = persisted.append
    monkeypatch.setattr(
        scout_execution,
        "run_scout_checkpoint",
        lambda *_args, **_kwargs: _result(report),
    )
    monkeypatch.setattr(
        planner, "_pruefe_api_widerspruch", lambda *_args: [],
    )
    monkeypatch.setattr(
        planner, "audit", lambda kind, *_args, **_kwargs: events.append(kind),
    )

    assert scout_execution.run_scout_role_checkpoint(
        state, goal=state.aufgabe,
    ) is True

    assert len(persisted) == 1
    assert persisted[0]["role"] == "scout"
    assert state.planner_role_artifacts["scout"] == persisted[0]
    assert state.scout_auftrag == report
    assert state.planner_step_yielded is True
    assert state.planner_yielded_after_role == "scout"
    assert "planner_role_artifact_persisted" in events


def test_atomic_scout_graph_stays_candidate_for_plan_gate(
    tmp_path, monkeypatch,
):
    state = _state(tmp_path)
    state.planner_action_role = "scout"
    report = {
        "auftrag_prosa": "Apply the exact current-source replacements.",
        "atomarer_plan": True,
    }
    state.planner_role_artifact_callback = lambda _artifact: None
    candidates = []
    monkeypatch.setattr(
        scout_execution,
        "run_scout_checkpoint",
        lambda *_args, **_kwargs: _result(report),
    )
    monkeypatch.setattr(
        planner, "_pruefe_api_widerspruch", lambda *_args: [],
    )
    monkeypatch.setattr(
        planner, "_atomarer_scout_plan_freigabefaehig",
        lambda *_args: (True, "exact_current_line_evidence"),
    )
    monkeypatch.setattr(
        planner, "_tasks_aus_betroffenen_stellen",
        lambda *_args, **_kwargs: [{
            "id": "t1", "task_files": ["src/a.py"],
        }],
    )
    monkeypatch.setattr(
        planner, "_validate_criteria_coverage", lambda *_args: None,
    )
    monkeypatch.setattr(planner, "_publish_role_checkpoint", lambda *_a: None)
    monkeypatch.setattr(planner, "audit", lambda *_a, **_kw: None)

    assert scout_execution.run_scout_role_checkpoint(
        state,
        goal=state.aufgabe,
        mark_plan_candidate=lambda: candidates.append(True),
    ) is True

    assert candidates == [True]
    assert state.tasks[0]["criterion_refs"] == ["AC1"]
    assert state.akzeptanzkriterien
    assert state.planner_step_yielded is False


def test_scout_completion_claim_stays_unconfirmed_for_architect(
    tmp_path, monkeypatch,
):
    state = _state(tmp_path)
    report = {
        "auftrag_prosa": "The requested outcome appears to exist.",
        "bereits_erfuellt": True,
        "begruendung_erfuellt": "A source excerpt suggests this.",
    }
    state.planner_role_artifact_callback = lambda _artifact: None
    events = []
    monkeypatch.setattr(
        scout_execution,
        "run_scout_checkpoint",
        lambda *_args, **_kwargs: _result(report),
    )
    monkeypatch.setattr(
        planner, "_pruefe_api_widerspruch", lambda *_args: [],
    )
    monkeypatch.setattr(
        planner, "audit",
        lambda kind, payload, *_args, **_kwargs: events.append((kind, payload)),
    )

    assert scout_execution.run_scout_role_checkpoint(
        state, goal=state.aufgabe,
    ) is True

    assert state.scout_auftrag["bereits_erfuellt"] is True
    assert getattr(state, "auftrag_bereits_erfuellt", False) is False
    assert state.planner_step_yielded is True
    completion_event = next(
        payload for kind, payload in events
        if kind == "auftrag_bereits_erfuellt"
    )
    assert completion_event["unbestaetigt"] is True
    assert completion_event["naechste_rolle"] == "architect"
