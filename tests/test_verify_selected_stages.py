
from __future__ import annotations

import json
import subprocess

from werkstatt import verify
from werkstatt.state import RunState


def _state(project_dir):
    contract_dir = project_dir / ".werkstatt"
    contract_dir.mkdir()
    (contract_dir / "verify.json").write_text(
        json.dumps({
            "stages": [
                {
                    "id": "pytest_regression",
                    "command": ["python3", "-m", "pytest", "-q"],
                    "phase": "phase_end",
                    "hart": True,
                },
                {
                    "id": "ruff",
                    "command": ["python3", "-m", "ruff", "check", "."],
                    "phase": "phase_end",
                    "hart": True,
                },
            ],
        }),
        encoding="utf-8",
    )
    return RunState(project_dir=project_dir)


def test_verify_only_runs_selected_failed_stages(tmp_path, monkeypatch):
    state = _state(tmp_path)
    calls = []
    monkeypatch.setattr(verify, "audit", lambda *_args, **_kwargs: None)

    def run_stage(command, *_args, **_kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(verify, "_verify_stage_with_heartbeat", run_stage)

    assert verify._verify_patches(
        state,
        phase="phase_end",
        stage_ids={"pytest_regression"},
    )
    assert len(calls) == 1
    assert calls[0][-2:] == ["pytest", "-q"]
    assert [item["stage_id"] for item in state.last_verify_results] == [
        "pytest_regression",
    ]


def test_verify_missing_selected_stage_fails_closed(tmp_path, monkeypatch):
    state = _state(tmp_path)
    calls = []
    monkeypatch.setattr(verify, "audit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        verify,
        "_verify_stage_with_heartbeat",
        lambda command, *_args, **_kwargs: calls.append(command),
    )

    assert not verify._verify_patches(
        state,
        phase="phase_end",
        stage_ids={"removed_stage"},
    )
    assert not calls
    assert state.last_verify_results[0]["ok"] is False
    assert "removed_stage" in state.last_verify_errors[0]


def test_verify_skipped_selected_stage_fails_closed(tmp_path, monkeypatch):
    state = _state(tmp_path)
    calls = []
    monkeypatch.setattr(verify, "audit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        verify,
        "_expand_cmd_placeholders",
        lambda command, *_args, **_kwargs: (
            None if command == ["{changed_py_files}"] else command
        ),
    )
    monkeypatch.setattr(
        verify,
        "_verify_stage_with_heartbeat",
        lambda command, *_args, **_kwargs: calls.append(command),
    )
    # Simulate a targeted contract stage gated by changed Python files.
    contract = json.loads(
        (tmp_path / ".werkstatt" / "verify.json").read_text(encoding="utf-8")
    )
    contract["stages"][0]["requires"] = "{changed_py_files}"
    (tmp_path / ".werkstatt" / "verify.json").write_text(
        json.dumps(contract),
        encoding="utf-8",
    )

    assert not verify._verify_patches(
        state,
        phase="phase_end",
        stage_ids={"pytest_regression"},
    )
    assert not calls
    assert state.last_verify_results[0]["ok"] is False
    assert "not executed" in state.last_verify_errors[0]
