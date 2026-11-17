from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

from werkstatt import failure_record
from werkstatt.roles import checkpoint_actions as finalize
from werkstatt.roles import complete_run
from werkstatt.roles.verify_recovery import _error_context


def test_finalize_requires_coordinator_checkpoints_and_does_not_run_legacy_chain(
    tmp_path: Path, monkeypatch,
) -> None:
    events = []
    monkeypatch.setattr(complete_run, "audit", lambda *args: events.append(args))
    state = SimpleNamespace(project_dir=tmp_path, project_name="demo")
    phase_state = SimpleNamespace(data={})

    result = complete_run.run_completion_checkpoint(
        state, 0, [], "demo", phase_state,
    )

    assert result == 3
    assert events[-1][0] == "loop_phase"
    assert events[-1][1]["phase"] == "finalize_run"
    assert events[-1][1]["status"] == "checkpoint_missing"


def test_failure_record_persists_bounded_sanitized_verify_evidence(
    tmp_path: Path, monkeypatch,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / ".git").mkdir()
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
    (project / ".git").mkdir()
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
    (project / ".git").mkdir()
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



















def test_failure_record_hashes_small_non_git_project_tree(
    tmp_path: Path, monkeypatch,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "app.py").write_text("value = 1\n", encoding="utf-8")
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
    assert isinstance(result["worktree_fingerprint"], str)
    assert len(result["worktree_fingerprint"]) == 64
    artifact = artifact_root / result["artifact_ref"]
    persisted = json.loads(artifact.read_text(encoding="utf-8"))
    assert persisted["work_sha"] is None
    assert persisted["worktree_fingerprint"] == result["worktree_fingerprint"]


def test_unversioned_fingerprint_fails_closed_at_entry_bound(
    tmp_path: Path, monkeypatch,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "one.py").write_text("value = 1\n", encoding="utf-8")
    monkeypatch.setattr(failure_record, "_UNVERSIONED_MAX_ENTRIES", 0)

    assert failure_record._worktree_fingerprint(project) is None


def test_git_output_marks_command_failure_as_unavailable(
    tmp_path: Path, monkeypatch,
) -> None:
    (tmp_path / ".git").mkdir()

    def fail(*_args, **_kwargs):
        raise subprocess.TimeoutExpired("git status", 1)

    monkeypatch.setattr(failure_record.subprocess, "run", fail)

    assert failure_record._git_output(tmp_path, "status") is None
    assert failure_record._worktree_fingerprint(tmp_path) is None


def test_verify_recovery_role_context_is_bounded_and_structured() -> None:
    errors = [f"stage_{index}: {('failure evidence ' * 40)}" for index in range(16)]

    context = _error_context(errors)

    assert len(context) <= 1200
    payload = json.loads(context)
    assert payload["source"] == "verify"
    assert 1 <= len(payload["errors"]) <= 8
    assert all(len(error) <= 240 for error in payload["errors"])



def test_post_commit_snapshot_rejects_head_drift(tmp_path: Path, monkeypatch) -> None:
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, "new-head\n", "")

    monkeypatch.setattr(finalize.subprocess, "run", fake_run)

    ok, evidence = finalize._post_commit_snapshot_check(tmp_path, "old-head")

    assert not ok
    assert evidence["reason"] == "head_changed_during_post_commit_verify"
    assert evidence["expected_sha"] == "old-head"
    assert len(calls) == 1


def test_post_commit_snapshot_rejects_dirty_worktree(tmp_path: Path, monkeypatch) -> None:
    def fake_run(args, **kwargs):
        output = "abc123\n" if args[1:3] == ["rev-parse", "HEAD"] else " M app.py\n"
        return subprocess.CompletedProcess(args, 0, output, "")

    monkeypatch.setattr(finalize.subprocess, "run", fake_run)

    ok, evidence = finalize._post_commit_snapshot_check(tmp_path, "abc123")

    assert not ok
    assert evidence["reason"] == "worktree_changed_during_post_commit_verify"
    assert evidence["dirty_paths"] == ["app.py"]
