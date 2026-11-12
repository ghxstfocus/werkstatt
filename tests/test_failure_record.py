from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

from werkstatt import failure_record
from werkstatt.phases import finalize


def test_failure_record_persists_bounded_sanitized_verify_evidence(
    tmp_path: Path, monkeypatch,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    artifact_root = tmp_path / "werkstatt"
    monkeypatch.setattr(failure_record, "_audit_root", lambda: artifact_root)

    def fake_run(args, **kwargs):
        if "rev-parse" in args:
            return subprocess.CompletedProcess(args, 0, b"abc123\n", b"")
        if "status" in args:
            return subprocess.CompletedProcess(args, 0, b" M app.py\n", b"")
        if "diff" in args:
            return subprocess.CompletedProcess(args, 0, b"diff --git app.py\n", b"")
        raise AssertionError(args)

    monkeypatch.setattr(failure_record.subprocess, "run", fake_run)
    state = SimpleNamespace(
        run_id="run-1",
        project_name="demo",
        project_dir=project,
        last_verify_results=[
            {"stage_id": "pytest", "exit_code": 1, "ok": False,
             "error_excerpt": "API_KEY=supersecret Bearer abc1234"},
            {"stage_id": "ruff", "exit_code": 0, "ok": True,
             "error_excerpt": ""},
        ],
    )

    result = failure_record.create_failure_record(state, stage="phase_end")

    artifact = artifact_root / result["artifact_ref"]
    persisted = json.loads(artifact.read_text(encoding="utf-8"))
    assert result["work_sha"] == "abc123"
    assert persisted["run_id"] == "run-1"
    assert persisted["failed_stages"] == [{
        "stage_id": "pytest",
        "exit_code": 1,
        "error_excerpt": "API_KEY=[REDACTED] Bearer [REDACTED]",
    }]
    assert persisted["worktree_fingerprint"] == result["worktree_fingerprint"]
    assert "supersecret" not in artifact.read_text(encoding="utf-8")


def test_failure_record_hashes_untrusted_run_id_for_artifact_path(
    tmp_path: Path, monkeypatch,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    artifact_root = tmp_path / "werkstatt"
    monkeypatch.setattr(failure_record, "_audit_root", lambda: artifact_root)
    monkeypatch.setattr(failure_record, "_git_output", lambda *_args: b"")
    state = SimpleNamespace(
        run_id="../../outside",
        project_name="demo",
        project_dir=project,
        last_verify_results=[],
    )

    result = failure_record.create_failure_record(state, stage="phase_end")

    assert (artifact_root / result["artifact_ref"]).is_file()
    assert result["run_id"] == "../../outside"
    assert ".." not in Path(result["artifact_ref"]).parts


def test_phase_finalize_attaches_failure_record_and_never_marks_success(
    tmp_path: Path, monkeypatch,
) -> None:
    events = []
    monkeypatch.setattr(finalize, "group_start", lambda *_args: None)
    monkeypatch.setattr(finalize, "group_end", lambda: None)
    monkeypatch.setattr(finalize, "audit", lambda *args: events.append(args))
    monkeypatch.setattr(finalize, "_human_gate", lambda *_args, **_kwargs: 2)
    monkeypatch.setattr(finalize, "_verify_patches", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(
        finalize,
        "create_failure_record",
        lambda *_args, **_kwargs: {
            "artifact_ref": "audit-logs/run-1/failures/phase_end.json",
            "work_sha": "abc123",
        },
    )
    monkeypatch.setattr(finalize, "summary", lambda *_args: None)
    monkeypatch.setattr("werkstatt.progress.append", lambda *_args, **_kwargs: None)

    task = {"id": "task-1"}
    phase_state = SimpleNamespace(
        data={"tasks": [{"id": "task-1", "status": "done"}]},
        get_task=lambda _task_id: {"status": "done"},
    )
    state = SimpleNamespace(
        project_dir=tmp_path,
        project_name="demo",
        run_id="run-1",
        tasks=[task],
        applied_count=0,
        reviewer_bugs=[],
        progress_written_at_commit=True,
        last_verify_results=[],
    )

    result = finalize._phase_finalize(
        state, 1, [task], "demo", phase_state,
    )

    gate_failures = [item for item in events if item[0] == "loop_gate_failed"]
    assert result == 1
    assert gate_failures
    assert gate_failures[-1][1]["failure_record"]["work_sha"] == "abc123"
    assert not any(item[0] == "loop_erfolg" for item in events)
