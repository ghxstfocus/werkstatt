from __future__ import annotations

from werkstatt.planner_artifacts import (
    MAX_ARTIFACT_CHARS,
    add_role_artifact,
    load_role_artifacts,
    make_role_artifact,
    validate_role_artifact,
)


def _artifact(input_sha256: str = "a" * 64):
    return make_role_artifact(
        "scout",
        {"auftrag_prosa": "Change the target."},
        run_id="run-1",
        goal="goal",
        input_sha256=input_sha256,
    )


def test_role_artifact_reuses_only_exact_run_goal_input_and_output():
    artifact = _artifact()
    assert artifact is not None
    cache = add_role_artifact(
        {}, artifact, run_id="run-1", goal="goal",
    )

    assert load_role_artifacts(
        cache, run_id="run-1", goal="goal",
    )["scout"] == artifact
    assert load_role_artifacts(cache, run_id="run-2", goal="goal") == {}
    assert load_role_artifacts(cache, run_id="run-1", goal="other") == {}

    assert validate_role_artifact(
        artifact,
        role="scout",
        run_id="run-1",
        goal="goal",
        input_sha256="b" * 64,
    ) is None
    changed_output = dict(artifact, output={"auftrag_prosa": "tampered"})
    assert load_role_artifacts(
        {"scout": changed_output}, run_id="run-1", goal="goal",
    ) == {}


def test_role_artifact_rejects_unknown_role_wrong_shape_and_oversized_output():
    assert make_role_artifact(
        "builder", {"task": "write"}, run_id="run-1", goal="goal",
        input_sha256="a" * 64,
    ) is None
    assert make_role_artifact(
        "scout", "not a scout report", run_id="run-1", goal="goal",
        input_sha256="a" * 64,
    ) is None
    assert make_role_artifact(
        "scout", {"text": "x" * MAX_ARTIFACT_CHARS},
        run_id="run-1", goal="goal", input_sha256="a" * 64,
    ) is None


def test_scout_input_fingerprint_changes_with_any_candidate_evidence(tmp_path):
    from types import SimpleNamespace

    from werkstatt.planner import _scout_input_fingerprint

    state = SimpleNamespace(
        project_dir=tmp_path,
        docs={"status": "OP-1"},
        explorer_context={"key_files": [{"file": "a.py", "source_sha256": "a"}]},
    )
    original = _scout_input_fingerprint(state, "goal", {"a.py": []}, ["a.py"])
    assert original

    state.explorer_context["key_files"][0]["source_sha256"] = "b"
    changed = _scout_input_fingerprint(state, "goal", {"a.py": []}, ["a.py"])
    assert changed and changed != original


def test_role_artifact_persists_and_reloads_only_for_bound_run(tmp_path):
    from werkstatt.loop import _persist_planner_role_artifact
    from werkstatt.phase_state import PhaseState

    phase_state = PhaseState("demo", base_dir=tmp_path)
    phase_state.run_id = "run-1"
    phase_state.data = {"project": "demo", "setup_complete": True}
    phase_state.save()
    artifact = _artifact()

    _persist_planner_role_artifact(
        phase_state, artifact, run_id="run-1", goal="goal",
    )
    resumed = PhaseState("demo", base_dir=tmp_path)
    assert resumed.load() is True
    assert resumed.run_id == "run-1"
    assert load_role_artifacts(
        resumed.data["planner_role_artifacts"],
        run_id="run-1", goal="goal",
    )["scout"] == artifact


def test_handoff_artifact_survives_store_with_scout_and_architect_outputs():
    from werkstatt.planner_artifacts import add_role_artifact

    artifacts = {}
    for role, output, input_hash in (
        ("scout", {"auftrag_prosa": "Inspect current behavior."}, "a" * 64),
        ("architect", "A" * 60, "b" * 64),
        ("planner_handoff", {"architect_input_sha256": "b" * 64}, "c" * 64),
    ):
        artifact = make_role_artifact(
            role, output, run_id="run-1", goal="goal",
            input_sha256=input_hash,
        )
        assert artifact is not None
        artifacts = add_role_artifact(
            artifacts, artifact, run_id="run-1", goal="goal",
        )

    loaded = load_role_artifacts(
        artifacts, run_id="run-1", goal="goal",
    )
    assert set(loaded) == {"scout", "architect", "planner_handoff"}
