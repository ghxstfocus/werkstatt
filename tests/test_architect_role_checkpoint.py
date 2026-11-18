from __future__ import annotations

from types import SimpleNamespace

from werkstatt.planner_artifacts import make_role_artifact
from werkstatt.roles.architect_execution import run_architect_role_checkpoint


def _state(tmp_path, *, artifacts=None):
    return SimpleNamespace(
        api_key="test-key",
        project_dir=tmp_path,
        project_name="demo",
        run_id="run-1",
        aufgabe="Inspect how the checkpoint coordinator chooses work",
        docs={},
        explorer_context={"key_files": []},
        planner_role_artifacts=artifacts or {},
        planner_step_yielded=False,
        planner_yielded_after_role=None,
        planner_role_artifact_callback=lambda _artifact: None,
        planner_checkpoint_callback=lambda _checkpoint: None,
        architect_required_source_files=[],
        architect_reasoning_enabled=False,
        architect_execution_context="",
        architect_execution_context_manifest={},
        architect_project_docs_manifest={},
        scout_auftrag={},
        scout_api_auszug={},
        tasks=[],
        tests=[],
        akzeptanzkriterien=[],
        phasen=[],
    )


def test_architect_role_consumes_current_scout_artifact_without_planner_runner(
    tmp_path, monkeypatch,
):
    from werkstatt import architect, architect_context, planner, progress
    from werkstatt.roles import planner_dispatch

    goal = "Inspect how the checkpoint coordinator chooses work"
    report = {
        "auftrag_prosa": "Check the current checkpoint decision evidence.",
        "relevante_dateien": [
            {"pfad": "werkstatt/loop.py", "zeilen": [50]},
            {"pfad": "werkstatt/roles/criteria_replan.py"},
        ],
    }
    scout_fingerprint = "b" * 64
    artifact = make_role_artifact(
        "scout", report, run_id="run-1", goal=goal,
        input_sha256=scout_fingerprint,
    )
    state = _state(tmp_path, artifacts={"scout": artifact})
    calls = []
    persisted = []

    monkeypatch.setattr(planner, "_baue_api_index", lambda _root: {})
    monkeypatch.setattr(
        planner, "_scout_input_fingerprint",
        lambda *_args: scout_fingerprint,
    )
    monkeypatch.setattr(planner, "_pruefe_api_widerspruch", lambda *_args: [])
    monkeypatch.setattr(
        architect_context, "scout_report_has_architect_assignment",
        lambda _r: True,
    )
    monkeypatch.setattr(
        architect_context, "completed_project_points", lambda _root: "",
    )
    monkeypatch.setattr(progress, "read_recent", lambda *_args, **_kwargs: "")
    monkeypatch.setattr(architect_context, "migration_status", lambda _root: "")
    monkeypatch.setattr(
        architect_context, "budget_architect_execution_context",
        lambda _sections: ("bounded execution context", {"chars": 27}),
    )
    monkeypatch.setattr(
        planner_dispatch, "architect_reasoning_route",
        lambda *_args: (False, "routine"),
    )
    monkeypatch.setattr(planner, "_validate_contract_or_audit", lambda *_args: True)
    monkeypatch.setattr(
        architect_context, "architect_input_fingerprint",
        lambda *_args: "c" * 64,
    )
    monkeypatch.setattr(planner, "_publish_role_checkpoint", lambda *_args: None)
    monkeypatch.setattr(planner, "audit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        architect, "build_architect_docs_context_v2",
        lambda _docs: ("bounded docs", {"sections": []}),
    )

    def run_architect(actual_state, _goal, _content, _key, _explorer):
        calls.append("architect")
        actual_state.architect_prosa = "A" * 80
        return True

    monkeypatch.setattr(planner, "run_architect", run_architect)
    monkeypatch.setattr(
        planner, "_persist_planner_split_handoff",
        lambda *_args, **_kwargs: persisted.append("handoff") or True,
    )
    monkeypatch.setattr(
        "werkstatt.roles.scout_execution.run_scout_role_checkpoint",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Architect must not call Scout"),
        ),
    )
    assert run_architect_role_checkpoint(state, goal=goal) is True
    assert calls == ["architect"]
    assert persisted == ["handoff"]
    assert state.scout_auftrag == report
    assert state.architect_required_source_files == []
    assert state.planner_step_yielded is True
    assert state.planner_yielded_after_role == "architect"


def test_architect_role_yields_to_scout_when_current_artifact_is_missing(
    tmp_path, monkeypatch,
):
    from werkstatt import planner

    state = _state(tmp_path)
    calls = []
    monkeypatch.setattr(planner, "_baue_api_index", lambda _root: {})
    monkeypatch.setattr(
        planner, "_scout_input_fingerprint", lambda *_args: "d" * 64,
    )
    monkeypatch.setattr(planner, "audit", lambda kind, *_args, **_kwargs: calls.append(kind))
    monkeypatch.setattr(
        planner, "run_architect",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("stale Scout evidence must block Architect"),
        ),
    )

    assert run_architect_role_checkpoint(state, goal=state.aufgabe) is True
    assert state.planner_step_yielded is True
    assert state.planner_yielded_after_role == "scout"
    assert calls == ["planner_architect_handoff_missing"]
