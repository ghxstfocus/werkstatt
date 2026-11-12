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
        if "ls-files" in args:
            return subprocess.CompletedProcess(args, 0, b"", b"")
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


def test_failure_record_fingerprint_tracks_untracked_file_contents(
    tmp_path: Path, monkeypatch,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    artifact_root = tmp_path / "werkstatt"
    untracked = project / "new_source.py"
    untracked.write_text("value = 1\n", encoding="utf-8")
    monkeypatch.setattr(failure_record, "_audit_root", lambda: artifact_root)

    def fake_git_output(_project_dir, *args):
        if args == ("status", "--porcelain=v1", "--untracked-files=all"):
            return b"?? new_source.py\n"
        if args == ("diff", "--binary", "HEAD"):
            return b""
        if args == ("ls-files", "--others", "--exclude-standard", "-z"):
            return b"new_source.py\0"
        if args == ("rev-parse", "--verify", "HEAD"):
            return b"abc123\n"
        raise AssertionError(args)

    monkeypatch.setattr(failure_record, "_git_output", fake_git_output)
    state = SimpleNamespace(
        run_id="run-1",
        project_name="demo",
        project_dir=project,
        last_verify_results=[],
    )

    before = failure_record.create_failure_record(state, stage="phase_end")
    untracked.write_text("value = 2\n", encoding="utf-8")
    after = failure_record.create_failure_record(state, stage="phase_end")

    assert before["worktree_fingerprint"] != after["worktree_fingerprint"]

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
            "worktree_fingerprint": None,
            "failed_stages": [
                {"stage_id": "pytest", "exit_code": 1,
                 "error_excerpt": "AssertionError"},
            ],
        },
    )
    recovery_calls = []
    monkeypatch.setattr(
        finalize, "_reflection_loop",
        lambda *_args, **_kwargs: recovery_calls.append(True) or True,
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
    assert gate_failures[-1][1]["recovery_blocked"] == (
        "failure_record_provenance_missing"
    )
    assert gate_failures[-1][1]["missing_provenance"] == [
        "worktree_fingerprint",
    ]
    assert recovery_calls == []
    assert not any(item[0] == "loop_erfolg" for item in events)


def test_phase_finalize_repairs_failed_phase_end_verify_in_same_run(
    tmp_path: Path, monkeypatch,
) -> None:
    events = []
    verify_results = iter([False, True])
    recovery_calls = []
    monkeypatch.setattr(finalize, "group_start", lambda *_args: None)
    monkeypatch.setattr(finalize, "group_end", lambda: None)
    monkeypatch.setattr(finalize, "audit", lambda *args: events.append(args))
    monkeypatch.setattr(finalize, "_human_gate", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(
        finalize, "_verify_patches",
        lambda *_args, **_kwargs: next(verify_results),
    )
    monkeypatch.setattr(finalize, "summary", lambda *_args: None)
    monkeypatch.setattr(
        "werkstatt.progress.append", lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        finalize,
        "create_failure_record",
        lambda *_args, **_kwargs: {
            "failure_id": "failure-1",
            "artifact_ref": "audit-logs/run-1/failures/phase_end.json",
            "work_sha": "abc123",
            "worktree_fingerprint": "fingerprint-1",
            "failed_stages": [
                {
                    "stage_id": "pytest_regression",
                    "exit_code": 1,
                    "error_excerpt": "tests/test_example.py::test_case AssertionError",
                },
            ],
        },
    )

    def recover(_state, *, error_context, phase, verify_stage_ids):
        recovery_calls.append(
            (error_context, phase, verify_stage_ids)
        )
        return True

    monkeypatch.setattr(finalize, "_reflection_loop", recover)
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
        last_verify_errors=["pytest_regression: AssertionError"],
    )

    result = finalize._phase_finalize(state, 1, [task], "demo", phase_state)

    assert result == 0
    assert recovery_calls and recovery_calls[0][1] == "phase_end"
    assert "pytest_regression" in recovery_calls[0][0]
    assert recovery_calls[0][2] == {"pytest_regression"}
    assert any(item[0] == "loop_verify_recovered" for item in events)
    assert any(item[0] == "loop_erfolg" for item in events)
    assert not any(item[0] == "loop_gate_failed" for item in events)



def test_phase_finalize_continues_when_full_verify_finds_another_stage(
    tmp_path: Path, monkeypatch,
) -> None:
    events = []
    verify_results = iter([False, False, True])
    recovery_stage_ids = []
    failure_records = iter([
        {
            "failure_id": "failure-1",
            "artifact_ref": "audit-logs/run-1/failures/first.json",
            "work_sha": "abc123",
            "worktree_fingerprint": "fingerprint-a",
            "failed_stages": [
                {"stage_id": "ruff", "exit_code": 1, "error_excerpt": "F401"},
            ],
        },
        {
            "failure_id": "failure-2",
            "artifact_ref": "audit-logs/run-1/failures/second.json",
            "work_sha": "abc123",
            "worktree_fingerprint": "fingerprint-b",
            "failed_stages": [
                {
                    "stage_id": "pytest_regression",
                    "exit_code": 1,
                    "error_excerpt": "AssertionError: second issue",
                },
            ],
        },
    ])
    monkeypatch.setattr(finalize, "group_start", lambda *_args: None)
    monkeypatch.setattr(finalize, "group_end", lambda: None)
    monkeypatch.setattr(finalize, "audit", lambda *args: events.append(args))
    monkeypatch.setattr(finalize, "_human_gate", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(
        finalize, "_verify_patches",
        lambda *_args, **_kwargs: next(verify_results),
    )
    monkeypatch.setattr(
        finalize, "create_failure_record",
        lambda *_args, **_kwargs: next(failure_records),
    )
    monkeypatch.setattr(
        finalize, "_reflection_loop",
        lambda _state, *, verify_stage_ids, **_kwargs: (
            recovery_stage_ids.append(verify_stage_ids) or True
        ),
    )
    monkeypatch.setattr(finalize, "summary", lambda *_args: None)
    monkeypatch.setattr(
        "werkstatt.progress.append", lambda *_args, **_kwargs: None,
    )

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
        last_verify_errors=["ruff: F401"],
    )

    result = finalize._phase_finalize(state, 1, [task], "demo", phase_state)

    assert result == 0
    assert recovery_stage_ids == [{"ruff"}, {"pytest_regression"}]
    assert sum(
        item[0] == "loop_verify_recovery_started" for item in events
    ) == 2
    assert any(item[0] == "loop_verify_recovered" for item in events)
    assert any(item[0] == "loop_erfolg" for item in events)
    assert not any(item[0] == "loop_gate_failed" for item in events)


def test_phase_finalize_stops_on_repeated_failure_at_same_worktree(
    tmp_path: Path, monkeypatch,
) -> None:
    events = []
    verify_results = iter([False, False])
    record = {
        "failure_id": "failure-repeat",
        "artifact_ref": "audit-logs/run-1/failures/repeated.json",
        "work_sha": "abc123",
        "worktree_fingerprint": "unchanged",
        "failed_stages": [
            {"stage_id": "pytest_regression", "exit_code": 1,
             "error_excerpt": "AssertionError: unchanged"},
        ],
    }
    monkeypatch.setattr(finalize, "group_start", lambda *_args: None)
    monkeypatch.setattr(finalize, "group_end", lambda: None)
    monkeypatch.setattr(finalize, "audit", lambda *args: events.append(args))
    monkeypatch.setattr(finalize, "_human_gate", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(
        finalize, "_verify_patches",
        lambda *_args, **_kwargs: next(verify_results),
    )
    monkeypatch.setattr(
        finalize, "create_failure_record",
        lambda *_args, **_kwargs: dict(record),
    )
    recovery_calls = []
    monkeypatch.setattr(
        finalize, "_reflection_loop",
        lambda *_args, **_kwargs: recovery_calls.append(True) or True,
    )
    monkeypatch.setattr(finalize, "summary", lambda *_args: None)
    monkeypatch.setattr(
        "werkstatt.progress.append", lambda *_args, **_kwargs: None,
    )

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
        last_verify_errors=["pytest_regression: AssertionError"],
    )

    result = finalize._phase_finalize(state, 1, [task], "demo", phase_state)

    assert result == 1
    assert len(recovery_calls) == 1
    stalled = [
        item for item in events
        if item[0] == "loop_verify_recovery_stalled"
    ]
    assert stalled
    assert stalled[-1][1]["reason"] == "same_failure_and_worktree_recurred"
    assert not any(item[0] == "loop_erfolg" for item in events)



def test_phase_finalize_stops_when_worktree_does_not_change_even_if_error_text_changes(
    tmp_path: Path, monkeypatch,
) -> None:
    events = []
    verify_results = iter([False, False])
    records = iter([
        {
            "failure_id": "failure-first",
            "artifact_ref": "audit-logs/run-1/failures/first.json",
            "work_sha": "abc123",
            "worktree_fingerprint": "unchanged",
            "failed_stages": [
                {"stage_id": "pytest_regression", "exit_code": 1,
                 "error_excerpt": "AssertionError: first output"},
            ],
        },
        {
            "failure_id": "failure-second",
            "artifact_ref": "audit-logs/run-1/failures/second.json",
            "work_sha": "abc123",
            "worktree_fingerprint": "unchanged",
            "failed_stages": [
                {"stage_id": "pytest_regression", "exit_code": 1,
                 "error_excerpt": "AssertionError: different output"},
            ],
        },
    ])
    monkeypatch.setattr(finalize, "group_start", lambda *_args: None)
    monkeypatch.setattr(finalize, "group_end", lambda: None)
    monkeypatch.setattr(finalize, "audit", lambda *args: events.append(args))
    monkeypatch.setattr(finalize, "_human_gate", lambda *_args, **_kwargs: 0)
    monkeypatch.setattr(
        finalize, "_verify_patches",
        lambda *_args, **_kwargs: next(verify_results),
    )
    monkeypatch.setattr(
        finalize, "create_failure_record",
        lambda *_args, **_kwargs: next(records),
    )
    recovery_calls = []
    monkeypatch.setattr(
        finalize, "_reflection_loop",
        lambda *_args, **_kwargs: recovery_calls.append(True) or True,
    )
    monkeypatch.setattr(finalize, "summary", lambda *_args: None)
    monkeypatch.setattr(
        "werkstatt.progress.append", lambda *_args, **_kwargs: None,
    )

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
        last_verify_errors=["pytest_regression: AssertionError"],
    )

    result = finalize._phase_finalize(state, 1, [task], "demo", phase_state)

    assert result == 1
    assert len(recovery_calls) == 1
    stalled = [
        item for item in events
        if item[0] == "loop_verify_recovery_stalled"
    ]
    assert stalled
    assert stalled[-1][1]["reason"] == "worktree_unchanged_after_repair"
    assert not any(item[0] == "loop_erfolg" for item in events)



def test_failure_record_does_not_fabricate_git_provenance(
    tmp_path: Path, monkeypatch,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    artifact_root = tmp_path / "werkstatt"
    monkeypatch.setattr(failure_record, "_audit_root", lambda: artifact_root)
    monkeypatch.setattr(failure_record, "_git_output", lambda *_args: None)
    state = SimpleNamespace(
        run_id="run-no-git",
        project_name="demo",
        project_dir=project,
        last_verify_results=[
            {"stage_id": "pytest", "exit_code": 1, "ok": False,
             "error_excerpt": "AssertionError"},
        ],
    )

    result = failure_record.create_failure_record(state, stage="phase_end")

    assert result["artifact_ref"]
    assert result["work_sha"] is None
    assert result["worktree_fingerprint"] is None
    artifact = artifact_root / result["artifact_ref"]
    persisted = json.loads(artifact.read_text(encoding="utf-8"))
    assert persisted["work_sha"] is None
    assert persisted["worktree_fingerprint"] is None


def test_git_output_marks_command_failure_as_unavailable(
    tmp_path: Path, monkeypatch,
) -> None:
    def fail(*_args, **_kwargs):
        raise subprocess.TimeoutExpired("git status", 1)

    monkeypatch.setattr(failure_record.subprocess, "run", fail)

    assert failure_record._git_output(tmp_path, "status") is None
    assert failure_record._worktree_fingerprint(tmp_path) is None
