from __future__ import annotations

from werkstatt import loop
from werkstatt.roles.planner_dispatch import prepare_direct_builder_context
from werkstatt.state import RunState


def test_selected_scout_and_architect_actions_dispatch_directly_to_role_runner(
    monkeypatch,
):
    calls = []

    def run_planner(state, *, stop_after_role):
        calls.append((state, stop_after_role))
        return True

    monkeypatch.setattr("werkstatt.planner.run_planner", run_planner)
    state = RunState(aufgabe="Inspect a project source")

    assert loop._run_selected_planner_role_action(state, "planner_scout")
    assert loop._run_selected_planner_role_action(state, "planner_architect")
    assert calls == [(state, "scout"), (state, "architect")]


def test_planner_dispatch_action_cannot_use_direct_role_dispatch(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("non-role actions must use their selected executor")

    monkeypatch.setattr("werkstatt.planner.run_planner", forbidden)
    assert not loop._run_selected_planner_role_action(
        RunState(aufgabe="Build"), "planner_dispatch",
    )


def test_checkpoint_dispatch_sends_information_roles_directly(monkeypatch):
    role_actions = []
    state = RunState(aufgabe="Inspect sources")
    phase_state = object()
    assert not hasattr(loop, "_phase_plan_and_preflight")

    monkeypatch.setattr(
        loop, "_run_selected_planner_role_action",
        lambda _state, action: role_actions.append(action) or True,
    )

    assert loop._dispatch_planner_checkpoint_action(
        state, "planner_scout", "Inspect sources", "sample", phase_state,
    ) == (0, False)
    assert loop._dispatch_planner_checkpoint_action(
        state, "planner_architect", "Inspect sources", "sample", phase_state,
    ) == (0, False)
    assert role_actions == ["planner_scout", "planner_architect"]


def test_checkpoint_dispatch_rejects_legacy_planner_dispatch(
    monkeypatch,
):
    state = RunState(aufgabe="Build the requested change")
    monkeypatch.setattr(
        loop, "_run_selected_planner_role_action",
        lambda *_args: (_ for _ in ()).throw(
            AssertionError("legacy dispatch must not enter the Planner"),
        ),
    )
    monkeypatch.setattr(loop, "audit", lambda *_args, **_kwargs: True)

    assert loop._dispatch_planner_checkpoint_action(
        state, "planner_dispatch", "Build the requested change", "sample",
        object(),
    ) == (1, False)


def test_planner_split_runs_as_role_checkpoint_and_validates_candidate(
    monkeypatch,
):
    calls = []
    state = RunState(aufgabe="Build the approved graph")

    def run_planner(actual_state, *, stop_after_role):
        calls.append((actual_state, stop_after_role))
        actual_state.tasks = [{"id": "t1", "action": "read"}]
        actual_state.planner_step_yielded = True
        actual_state.planner_yielded_after_role = "planner_split"
        return True

    monkeypatch.setattr("werkstatt.planner.run_planner", run_planner)
    monkeypatch.setattr(loop, "_plan_gate", lambda _state: True)

    assert loop._dispatch_planner_checkpoint_action(
        state, "planner_split", state.aufgabe, "sample", object(),
    ) == (0, False)
    assert calls == [(state, "planner_split")]
    assert state.planner_plan_candidate_ready is True


def test_planner_split_waits_for_refreshed_architect_checkpoint(monkeypatch):
    state = RunState(aufgabe="Build from Architect evidence")

    def run_planner(actual_state, *, stop_after_role):
        assert stop_after_role == "planner_split"
        actual_state.planner_step_yielded = True
        actual_state.planner_yielded_after_role = "architect"
        return True

    monkeypatch.setattr("werkstatt.planner.run_planner", run_planner)
    monkeypatch.setattr(
        loop, "_plan_gate",
        lambda *_args: (_ for _ in ()).throw(
            AssertionError("no task candidate exists yet"),
        ),
    )

    assert loop._dispatch_planner_checkpoint_action(
        state, "planner_split", state.aufgabe, "sample", object(),
    ) == (0, False)
    assert state.planner_plan_candidate_ready is False


def test_planner_split_candidate_still_fails_closed_at_plan_gate(monkeypatch):
    state = RunState(aufgabe="Build the approved graph")
    state.tasks = [{"id": "t1"}]
    monkeypatch.setattr(
        "werkstatt.planner.run_planner", lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(loop, "_plan_gate", lambda _state: False)

    assert loop._dispatch_planner_checkpoint_action(
        state, "planner_split", state.aufgabe, "sample", object(),
    ) == (1, False)
    assert state.planner_plan_candidate_ready is False


def test_direct_builder_action_builds_candidate_without_plan_phase(
    tmp_path, monkeypatch,
):
    target = tmp_path / "src" / "settings.py"
    target.parent.mkdir()
    target.write_text("FEATURE_ENABLED = False\n", encoding="utf-8")
    goal = "Aktualisiere das Modul src/settings.py"
    context, reason = prepare_direct_builder_context(goal, tmp_path)
    assert context is not None, reason

    state = RunState(
        aufgabe=goal,
        project_dir=tmp_path,
        project_name="sample_app",
        explorer_context=context,
    )
    checkpoints = []
    state.planner_checkpoint_callback = checkpoints.append
    monkeypatch.setattr(
        loop, "_call_hook", lambda *_args, **_kwargs: {"allow": True},
    )

    assert loop._dispatch_planner_checkpoint_action(
        state, "planner_direct", goal, "sample_app", object(),
    ) == (0, False)
    assert state.planner_plan_candidate_ready is True
    assert len(state.tasks) == 1
    assert state.tasks[0]["task_files"] == ["src/settings.py"]
    assert state.akzeptanzkriterien == [goal]
    assert [record["role"] for record in checkpoints] == [
        "scout", "architect", "planner_split",
    ]
    assert all(record["status"] == "skipped" for record in checkpoints)


def test_direct_builder_action_fails_closed_when_source_changes(
    tmp_path, monkeypatch,
):
    target = tmp_path / "src" / "settings.py"
    target.parent.mkdir()
    target.write_text("FEATURE_ENABLED = False\n", encoding="utf-8")
    goal = "Aktualisiere das Modul src/settings.py"
    context, reason = prepare_direct_builder_context(goal, tmp_path)
    assert context is not None, reason
    target.write_text("FEATURE_ENABLED = True\n", encoding="utf-8")

    state = RunState(
        aufgabe=goal,
        project_dir=tmp_path,
        project_name="sample_app",
        explorer_context=context,
    )

    assert loop._dispatch_planner_checkpoint_action(
        state, "planner_direct", goal, "sample_app", object(),
    ) == (1, False)
    assert state.planner_plan_candidate_ready is False
    assert state.tasks == []
