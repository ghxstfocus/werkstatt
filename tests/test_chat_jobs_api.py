"""REST-Schnittstelle fuer persistente Chatjobs (OP-397)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from werkstatt.chat_jobs import ChatJobStore


@pytest.fixture
def client_and_base(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Any, Path]:
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from werkstatt.web import app as app_modul

    monkeypatch.setattr(app_modul, "_PROJECTS_BASE", tmp_path)
    return TestClient(app_modul.app), tmp_path


def test_chat_job_create_acknowledges_without_waiting_for_worker(
    client_and_base: tuple[Any, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _base = client_and_base
    from werkstatt import chat_jobs

    def _accepted(*args: Any, **kwargs: Any) -> dict[str, Any]:
        assert kwargs["db_path"].name == "demo.db"
        assert isinstance(kwargs["context_seq"], int)
        return {
            "job": {"job_id": "a" * 32, "state": "queued"},
            "created": True,
        }

    monkeypatch.setattr(chat_jobs, "enqueue_chat_job", _accepted)
    response = client.post(
        "/api/projects/demo/chat/jobs",
        json={
            "session_id": "session-1",
            "message": "Pruefe den letzten Run",
            "mode": "read",
            "idempotency_key": "request-key-0001",
        },
    )

    assert response.status_code == 202
    assert response.json() == {
        "job_id": "a" * 32, "state": "queued", "created": True,
    }


def test_chat_job_rejects_write_mode_without_gate(
    client_and_base: tuple[Any, Path],
) -> None:
    client, _base = client_and_base
    response = client.post(
        "/api/projects/demo/chat/jobs",
        json={
            "session_id": "session-1",
            "message": "Aendere Code",
            "mode": "write",
            "idempotency_key": "request-key-0002",
        },
    )

    assert response.status_code == 400
    assert "nur read-Modus" in response.json()["detail"]


def test_chat_job_get_replays_persisted_events(
    client_and_base: tuple[Any, Path],
) -> None:
    client, base = client_and_base
    db_path = base / ".werkstatt" / "chat-jobs" / "demo.db"
    store = ChatJobStore(db_path)
    job, _created = store.create(
        "session-1", "Frage", "read", "request-key-0003",
    )
    assert store.claim(job["job_id"])

    hidden = client.get(
        f"/api/projects/demo/chat/jobs/{job['job_id']}?session_id=other-session",
    )
    assert hidden.status_code == 404

    response = client.get(
        f"/api/projects/demo/chat/jobs/{job['job_id']}?session_id=session-1&since_seq=1",
    )

    assert response.status_code == 200
    result = response.json()
    assert result["state"] == "running"
    assert [event["kind"] for event in result["events"]] == ["started"]


def test_chat_job_get_rejects_cross_project_unknown_job(
    client_and_base: tuple[Any, Path],
) -> None:
    client, _base = client_and_base
    response = client.get(
        f"/api/projects/demo/chat/jobs/{'b' * 32}?session_id=session-1",
    )

    assert response.status_code == 404

def test_chat_job_rejects_same_idempotency_key_with_different_message(
    client_and_base: tuple[Any, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _base = client_and_base
    from werkstatt import chat_jobs

    monkeypatch.setattr(chat_jobs, "_dispatch_pending", lambda *_args: None)
    payload = {
        "session_id": "session-1",
        "message": "Erste Frage",
        "mode": "read",
        "idempotency_key": "request-key-same-001",
    }
    first = client.post("/api/projects/demo/chat/jobs", json=payload)
    payload["message"] = "Andere Frage mit demselben Key"
    second = client.post("/api/projects/demo/chat/jobs", json=payload)

    assert first.status_code == 202
    assert second.status_code == 409
    assert "andere Anfrage" in second.json()["detail"]

def test_chat_job_reconnect_includes_persisted_failures(
    client_and_base: tuple[Any, Path],
) -> None:
    client, base = client_and_base
    store = ChatJobStore(base / ".werkstatt" / "chat-jobs" / "demo.db")
    job, _created = store.create(
        "session-1", "Pruefe den Loop", "read", "request-key-fail-001",
    )
    assert store.claim(job["job_id"], "worker-test")
    assert store.finish(job["job_id"], error="RuntimeError: Provider offline")

    response = client.get(
        "/api/projects/demo/chat/jobs?session_id=session-1",
    )

    assert response.status_code == 200
    jobs = response.json()["jobs"]
    assert len(jobs) == 1
    assert jobs[0]["job_id"] == job["job_id"]
    assert jobs[0]["state"] == "failed"
    assert jobs[0]["error"] == "RuntimeError: Provider offline"

def test_chat_job_cancel_endpoint_is_session_scoped_and_persistent(
    client_and_base: tuple[Any, Path],
) -> None:
    client, base = client_and_base
    store = ChatJobStore(base / ".werkstatt" / "chat-jobs" / "demo.db")
    job, _created = store.create(
        "session-1", "Pruefe den Loop", "read", "request-key-api-cancel-001",
    )

    hidden = client.post(
        f"/api/projects/demo/chat/jobs/{job['job_id']}/cancel",
        json={"session_id": "other-session"},
    )
    assert hidden.status_code == 404

    response = client.post(
        f"/api/projects/demo/chat/jobs/{job['job_id']}/cancel",
        json={"session_id": "session-1"},
    )
    assert response.status_code == 200
    assert response.json() == {"job_id": job["job_id"], "state": "cancelled"}
    saved = store.get(job["job_id"])
    assert saved is not None
    assert saved["state"] == "cancelled"

def test_running_job_cancel_endpoint_requests_worker_stop(
    client_and_base: tuple[Any, Path],
) -> None:
    client, base = client_and_base
    store = ChatJobStore(base / ".werkstatt" / "chat-jobs" / "demo.db")
    job, _created = store.create(
        "session-1", "Pruefe den Loop", "read", "request-key-api-cancel-002",
    )
    assert store.claim(job["job_id"], "worker-test")

    response = client.post(
        f"/api/projects/demo/chat/jobs/{job['job_id']}/cancel",
        json={"session_id": "session-1"},
    )

    assert response.status_code == 200
    assert response.json()["state"] == "cancelling"
    assert store.cancellation_requested(job["job_id"], "worker-test")

