from __future__ import annotations

import hashlib
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from werkstatt import loop as loop_module
from werkstatt.loop import _run_scoped_phase_state
from werkstatt.phase_state import PhaseState


def test_direct_loop_checkpoint_is_run_scoped_and_resumable(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    first = _run_scoped_phase_state("sample", project_dir, "run-1")
    first.data["aufgabe"] = "Goal one"
    first.save()

    resumed = _run_scoped_phase_state("sample", project_dir, "run-1")
    second = _run_scoped_phase_state("sample", project_dir, "run-2")

    expected_key = hashlib.sha256(b"run-1").hexdigest()[:32]
    assert first.path.parent == project_dir / ".werkstatt" / "runs" / expected_key
    assert resumed.data["aufgabe"] == "Goal one"
    assert resumed.run_id == "run-1"
    assert second.run_id == "run-2"
    assert second.path != first.path
    assert second.data == {}


def test_direct_loop_rejects_checkpoint_from_another_run(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    wrong_run = "run-1"
    wrong_key = hashlib.sha256(b"run-2").hexdigest()[:32]
    checkpoint = PhaseState(
        "sample",
        base_dir=project_dir / ".werkstatt" / "runs" / wrong_key,
    )
    checkpoint.run_id = wrong_run
    checkpoint.data["project"] = "sample"
    checkpoint.save()

    with pytest.raises(ValueError, match="anderen Run-ID"):
        _run_scoped_phase_state("sample", project_dir, "run-2")


def test_run_pipeline_loop_supplies_run_scoped_checkpoint_when_omitted(
    tmp_path, monkeypatch,
):
    calls = {}

    class Lease:
        def assert_owned(self):
            return None

    class Store:
        def get_run_record(self, _project, _run_id):
            return None

        def create_run_record(self, *_args, **_kwargs):
            return None

        @contextmanager
        def run_lease(self, *_args, **_kwargs):
            yield Lease()

    project_dir = tmp_path / "project"
    project_dir.mkdir()
    state = SimpleNamespace(
        project_dir=project_dir,
        project_name="sample",
        run_id=None,
    )

    def impl(_project, _goal, _states, *, phasen_state, phase_state):
        calls["phase_state"] = phase_state
        return 0

    monkeypatch.setattr(loop_module, "EventStore", Store)
    monkeypatch.setattr(loop_module, "_git_head", lambda _root: "base-sha")
    monkeypatch.setattr(loop_module, "_run_pipeline_loop_impl", impl)

    assert loop_module.run_pipeline_loop(
        "sample", "goal", [state],
    ) == 0

    checkpoint = calls["phase_state"]
    assert isinstance(checkpoint, PhaseState)
    assert checkpoint.run_id == state.run_id
    assert checkpoint.base_dir.parent == project_dir / ".werkstatt" / "runs"
    assert state.run_lease_check is None
