"""Checkpoint synchronization tests for run-bound chat jobs (OP-401)."""
from __future__ import annotations

import subprocess
from concurrent.futures import Future
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from werkstatt import run_snapshot
from werkstatt.chat_jobs import ChatJobStore
from werkstatt.event_store import EventStore


def _repo(path: Path) -> Path:
    path.mkdir()
    for args in (
        ("init", "-q"),
        ("config", "user.email", "tests@example.invalid"),
        ("config", "user.name", "Werkstatt Tests"),
    ):
        subprocess.run(["git", *args], cwd=path, check=True)
    (path / "README.md").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=path, check=True)
    return path


def test_run_job_dispatch_waits_for_snapshot_and_checkpoint_ack(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from werkstatt import chat_jobs, event_store

    class _RecordingExecutor:
        def __init__(self) -> None:
            self.submitted: list[tuple[Any, ...]] = []

        def submit(self, *args: Any) -> Future[bool]:
            self.submitted.append(args)
            return Future()

    events = EventStore(tmp_path / "events.db")
    events.create_run_record("demo", "run-1", "Read current progress")
    jobs = ChatJobStore(tmp_path / "jobs.db")
    job, _created = jobs.create(
        "session-1",
        "Read current progress",
        "read",
        "request-key-checkpoint-001",
        run_id="run-1",
        project="demo",
    )
    events.enqueue_run_message(
        "demo",
        "run-1",
        f"chat-job:{job['job_id']}",
        "job_notice",
        {"job_id": job["job_id"]},
    )
    assert jobs.mark_run_inbox_enqueued(job["job_id"])

    monkeypatch.setattr(event_store, "EventStore", lambda: events)
    executor = _RecordingExecutor()
    monkeypatch.setattr(chat_jobs, "_EXECUTOR", executor)
    monkeypatch.setattr(chat_jobs, "_FUTURES", {})

    chat_jobs._dispatch_pending(jobs.db_path, "demo", tmp_path)
    assert executor.submitted == []

    assert jobs.set_run_snapshot(
        job["job_id"],
        tmp_path,
        tmp_path / "snapshot",
        "base-sha",
        "tree-hash",
    )
    chat_jobs._dispatch_pending(jobs.db_path, "demo", tmp_path)
    assert executor.submitted == []

    message = events.claim_run_message("demo", "run-1", "loop-worker")
    assert message is not None
    assert events.acknowledge_run_message(
        message["seq"], "loop-worker", message["fencing_token"],
    )
    chat_jobs._dispatch_pending(jobs.db_path, "demo", tmp_path)

    assert [item[-1] for item in executor.submitted] == [job["job_id"]]


def test_checkpoint_captures_run_tree_before_ack_and_resumes_jobs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from werkstatt import chat_jobs
    from werkstatt.phases import tasks

    project_dir = _repo(tmp_path / "project")
    (project_dir / "README.md").write_text("checkpoint state\n", encoding="utf-8")
    events = EventStore(tmp_path / "events.db")
    events.create_run_record("demo", "run-2", "Read project state")
    job_db = tmp_path / "jobs.db"
    jobs = ChatJobStore(job_db)
    job, _created = jobs.create(
        "session-1",
        "Read project state",
        "read",
        "request-key-checkpoint-002",
        run_id="run-2",
        project="demo",
    )
    inbox_seq = events.enqueue_run_message(
        "demo",
        "run-2",
        f"chat-job:{job['job_id']}",
        "job_notice",
        {
            "job_id": job["job_id"],
            "session_id": "session-1",
            "mode": "read",
        },
    )
    assert jobs.mark_run_inbox_enqueued(job["job_id"])
    monkeypatch.setattr(chat_jobs, "_db_path", lambda _project: job_db)
    monkeypatch.setattr(run_snapshot, "werkstatt_home", lambda: tmp_path / "state")
    monkeypatch.setattr(tasks, "check_run_lease", lambda _state: None)
    resumed: list[tuple[str, Path]] = []
    monkeypatch.setattr(
        chat_jobs,
        "resume_chat_jobs",
        lambda project, path: resumed.append((project, Path(path))),
    )

    tasks._persist_run_checkpoint(
        events,
        "demo",
        "run-2",
        SimpleNamespace(data={"tasks": [{"id": "task-1", "status": "done"}]}),
        {"id": "task-2"},
        run_state=SimpleNamespace(project_dir=project_dir),
    )

    saved = jobs.get(job["job_id"])
    assert saved is not None
    snapshot = run_snapshot.validate_project_snapshot(
        Path(saved["run_snapshot_path"]),
        project_dir,
        "demo",
        "run-2",
        job["job_id"],
    )
    assert (snapshot.path / "README.md").read_text() == "checkpoint state\n"
    assert events.run_message_acknowledged(
        "demo", "run-2", f"chat-job:{job['job_id']}",
    )
    record = events.get_run_record("demo", "run-2")
    assert record is not None
    notice = record["checkpoint"]["job_notices"][0]
    assert notice["seq"] == inbox_seq
    assert notice["snapshot_head"] == snapshot.head
    assert notice["snapshot_fingerprint"] == snapshot.fingerprint
    assert resumed == [("demo", project_dir)]


def test_run_job_uses_then_removes_checkpoint_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from werkstatt import chat_agent, chat_jobs, chat_session

    project_dir = _repo(tmp_path / "project")
    (project_dir / "README.md").write_text("captured state\n", encoding="utf-8")
    monkeypatch.setattr(run_snapshot, "werkstatt_home", lambda: tmp_path / "state")
    snapshot = run_snapshot.create_project_snapshot(
        project_dir, "demo", "run-3", "job-3",
    )
    chat_db = tmp_path / "chat.db"
    monkeypatch.setattr(chat_session, "_db_pfad", lambda _project: chat_db)
    jobs = ChatJobStore(tmp_path / "jobs.db")
    job, _created = jobs.create(
        "session-1",
        "Read captured state",
        "read",
        "request-key-checkpoint-003",
        run_id="run-3",
        project="demo",
    )
    assert jobs.set_run_snapshot(
        job["job_id"],
        project_dir,
        snapshot.path,
        snapshot.head,
        snapshot.fingerprint,
    )
    seen: list[tuple[Path, str]] = []

    def fake_chat_loop(_session: Any, _message: str, **kwargs: Any) -> str:
        chat_project_dir = Path(kwargs["project_dir"])
        seen.append((
            chat_project_dir,
            (chat_project_dir / "README.md").read_text(encoding="utf-8"),
        ))
        return "Snapshot geprueft"

    monkeypatch.setattr(chat_agent, "chat_loop", fake_chat_loop)
    monkeypatch.setattr(chat_jobs, "_WORKER_ID", "worker-snapshot")
    monkeypatch.setattr(chat_jobs, "resume_chat_jobs", lambda *_args, **_kwargs: None)

    assert chat_jobs._run_job(
        jobs.db_path, "demo", project_dir, job["job_id"],
    )
    result = jobs.get(job["job_id"])
    assert result is not None
    assert result["state"] == "succeeded", (result.get("error"), result.get("events"))
    assert seen == [(snapshot.path, "captured state\n")]
    assert not snapshot.path.exists()
