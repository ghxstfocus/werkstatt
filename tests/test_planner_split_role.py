from types import SimpleNamespace

from werkstatt import planner
from werkstatt.roles.planner_split import (
    PlannerSplitInput,
    build_context_manifest,
    run_planner_split_checkpoint,
    run_planner_split_role,
)


def _request(*, scope="task_graph", task_id=None):
    system = "task graph role contract"
    user = "approved goal and architect handoff"
    manifest = build_context_manifest(
        system_prompt=system,
        user_prompt=user,
        key_files=["werkstatt/loop.py"],
        source_evidence={"sources": []},
        source_context="",
        sections=[{"name": "architect_prose", "status": "required_included"}],
        scope=scope,
        task_id=task_id,
    )
    return PlannerSplitInput(
        api_key="secret-for-provider",
        system_prompt=system,
        user_prompt=user,
        state=object(),
        context_manifest=manifest,
    )


def test_planner_split_role_sends_only_explicit_prompt_packet():
    request = _request()
    calls = []

    def ask_llm(*args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(ok=True, content='{"tasks": []}')

    result = run_planner_split_role(
        request,
        ask_llm_call=ask_llm,
        spinner_call=lambda _label, call: call(),
    )

    assert result.ok is True
    assert result.content == '{"tasks": []}'
    assert len(calls) == 1
    args, kwargs = calls[0]
    assert args == (
        "secret-for-provider",
        request.system_prompt,
        request.user_prompt,
    )
    assert kwargs["aufgabe"] == "planner-split"
    assert kwargs["max_tokens"] == 8000
    assert kwargs["context_manifest"] == request.context_manifest
    assert kwargs["state"] is request.state


def test_planner_split_role_rejects_stale_manifest_before_provider_call():
    request = _request()
    calls = []
    stale_manifest = dict(request.context_manifest)
    stale_manifest["user_sha256"] = "stale"
    stale_request = PlannerSplitInput(
        api_key=request.api_key,
        system_prompt=request.system_prompt,
        user_prompt=request.user_prompt,
        state=request.state,
        context_manifest=stale_manifest,
    )

    result = run_planner_split_role(
        stale_request,
        ask_llm_call=lambda *args, **kwargs: calls.append((args, kwargs)),
        spinner_call=lambda _label, call: call(),
    )

    assert result.ok is False
    assert result.error == "planner_split_input_manifest_mismatch"
    assert calls == []


def test_oversized_task_uses_the_same_worker_on_demand():
    request = _request(scope="single_task", task_id="t7")
    calls = []

    result = run_planner_split_role(
        request,
        ask_llm_call=lambda *args, **kwargs: (
            calls.append((args, kwargs))
            or SimpleNamespace(ok=True, content='{"tasks": []}')
        ),
        spinner_call=lambda _label, call: call(),
    )

    assert result.ok is True
    assert calls[0][1]["max_tokens"] == 4000
    assert calls[0][1]["context_manifest"]["scope"] == "single_task"
    assert calls[0][1]["context_manifest"]["task_id"] == "t7"


def test_split_checkpoint_runs_from_current_handoff_and_yields_to_coordinator(
    tmp_path, monkeypatch,
):
    state = SimpleNamespace(
        api_key="test-key",
        project_dir=tmp_path,
        project_name="demo",
        run_id="run-1",
        explorer_context={"key_files": [{"file": "src/a.py"}]},
        architect_prose="A" * 80,
        scout_auftrag={},
        architect_scout_source_manifest={},
        planner_step_yielded=False,
        planner_yielded_after_role=None,
        akzeptanzkriterien=["AC1"],
        tasks=[],
        phasen=["legacy"],
        tests=["legacy"],
    )
    handoff = {
        "architect_prose": "A" * 80,
        "architect_scout_report": {"auftrag_prosa": "evidence"},
        "source_manifest": {"sources": []},
        "key_files": ["src/a.py"],
        "architect_input_sha256": "a" * 64,
    }
    checkpoints = []
    events = []
    monkeypatch.setattr(
        planner, "_load_current_planner_split_handoff",
        lambda _state, _goal: handoff,
    )
    monkeypatch.setattr(
        planner, "_publish_role_checkpoint",
        lambda _state, *args: checkpoints.append(args),
    )
    monkeypatch.setattr(
        planner, "_zerlege_in_sub_tasks",
        lambda *_args, **_kwargs: [{
            "id": "t1", "action": "update", "criterion_refs": ["AC1"],
        }],
    )
    monkeypatch.setattr(
        planner, "_normalisiere_task_files", lambda tasks, *_args: tasks,
    )
    monkeypatch.setattr(
        planner, "audit", lambda kind, *_args, **_kwargs: events.append(kind),
    )

    assert run_planner_split_checkpoint(state, goal="approved goal") is True
    assert [record[0] for record in checkpoints] == [
        "planner_split", "planner_split",
    ]
    assert [record[1] for record in checkpoints] == ["running", "completed"]
    assert state.tasks[0]["id"] == "t1"
    assert state.phasen == []
    assert state.tests == []
    assert state.planner_step_yielded is True
    assert state.planner_yielded_after_role == "planner_split"
    assert "planner_plan_erstellt" in events
