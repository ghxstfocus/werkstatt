from __future__ import annotations

import hashlib

from werkstatt.planner_replay import (
    add_response_entry,
    load_response_cache,
)


def _entry(*, run_id: str = "run-1", goal: str = "goal") -> dict[str, str]:
    content = '{"ziel":"checked"}'
    return {
        "role": "scout",
        "request_sha256": "a" * 64,
        "content": content,
        "content_sha256": hashlib.sha256(content.encode()).hexdigest(),
        "run_id": run_id,
        "goal_sha256": hashlib.sha256(goal.encode()).hexdigest(),
    }


def test_response_cache_is_bound_to_exact_run_and_goal():
    cache = add_response_entry(
        {}, _entry(), run_id="run-1", goal="goal",
    )

    assert list(load_response_cache(
        cache, run_id="run-1", goal="goal",
    )) == ["a" * 64]
    assert load_response_cache(cache, run_id="run-2", goal="goal") == {}
    assert load_response_cache(cache, run_id="run-1", goal="other") == {}


def test_response_cache_rejects_changed_output_hash_and_unknown_role():
    valid = _entry()
    tampered = {**valid, "content": "different"}
    unknown = {**valid, "role": "builder"}

    assert load_response_cache(
        {"a" * 64: tampered}, run_id="run-1", goal="goal",
    ) == {}
    assert load_response_cache(
        {"a" * 64: unknown}, run_id="run-1", goal="goal",
    ) == {}


def test_planning_response_survives_phase_state_reload_only_for_same_run(
    tmp_path,
):
    from werkstatt.loop import _persist_planning_response_cache
    from werkstatt.phase_state import PhaseState

    phase = PhaseState("demo", base_dir=tmp_path)
    phase.run_id = "run-1"
    phase.data = {"project": "demo", "aufgabe": "goal", "tasks": []}
    phase.save()
    _persist_planning_response_cache(
        phase, _entry(), run_id="run-1", goal="goal",
    )

    resumed = PhaseState("demo", base_dir=tmp_path)
    assert resumed.load()
    cache = load_response_cache(
        resumed.data.get("planner_response_cache"),
        run_id="run-1", goal="goal",
    )
    assert cache["a" * 64]["content"] == '{"ziel":"checked"}'
    assert load_response_cache(
        resumed.data.get("planner_response_cache"),
        run_id="run-2", goal="goal",
    ) == {}
