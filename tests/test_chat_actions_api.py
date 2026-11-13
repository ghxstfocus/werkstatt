"""API tests for chat initiated, explicitly confirmed loop actions."""
from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest


def test_confirmed_chat_action_uses_control_api_once(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from werkstatt import chat_session
    from werkstatt.web import app as app_modul

    if app_modul.os.name != "posix":
        pytest.skip("Loop-Pause wird nur unter POSIX unterstuetzt")
    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    monkeypatch.setattr(app_modul, "_PROJECTS_BASE", tmp_path)
    db_path = tmp_path / "sessions.db"
    monkeypatch.setattr(chat_session, "_db_pfad", lambda _project: db_path)
    session_id = "a" * 32
    proposal_id = "b" * 32
    session = chat_session.ChatSession("demo", session_id, db_pfad=db_path)
    session.append("loop_action_proposed", {
        "proposal_id": proposal_id,
        "project": "demo",
        "action": "pause",
        "arguments": {},
        "summary": "Loop pausieren",
        "expires_at": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
    })

    calls: list[tuple[Any, ...]] = []
    process = SimpleNamespace(pid=12345, poll=lambda: None)
    record: dict[str, Any] = {
        "project": "demo",
        "run_id": "demo-run",
        "pid": process.pid,
        "state": "running",
    }

    def transition(
        project: str, run_id: str, expected: str, target: str,
    ) -> bool:
        if (
            project != "demo"
            or run_id != record["run_id"]
            or record["state"] != expected
        ):
            return False
        record["state"] = target
        return True

    monkeypatch.setattr(app_modul, "_PAUSIERTE_LOOPS", set())
    monkeypatch.setattr(app_modul, "_LOOP_RUN_IDS", {"demo": "demo-run"})
    monkeypatch.setitem(app_modul._LAUFENDE_LOOPS, "demo", process)
    monkeypatch.setattr(app_modul.os, "killpg", lambda *_args: calls.append(_args))
    monkeypatch.setattr(app_modul, "_audit_web_loop_event", lambda *_args: True)
    monkeypatch.setattr(app_modul, "_loop_registry", lambda: SimpleNamespace(
        set_state=lambda *_args: None,
        read=lambda _project: dict(record),
        transition=transition,
    ))

    response = TestClient(app_modul.app).post(
        f"/api/projects/demo/chat/actions/{proposal_id}",
        json={"session_id": session_id, "decision": "confirm"},
    )
    assert response.status_code == 200
    assert response.json()["state"] == "completed"
    assert calls

    repeated = TestClient(app_modul.app).post(
        f"/api/projects/demo/chat/actions/{proposal_id}",
        json={"session_id": session_id, "decision": "confirm"},
    )
    assert repeated.status_code == 200
    assert repeated.json()["state"] == "completed"
    assert len(calls) == 1


@pytest.mark.parametrize(
    (
        "arguments", "task_preview", "expected_request", "expected_op_id",
        "expected_status",
    ),
    [
        ({"aufgabe": "Testauftrag"}, "", "Testauftrag", None, 200),
        (
            {"op_id": "OP-372"},
            "### OP-372: Projection-Status\n- **Status:** open\nAkzeptanzkriterien",
            "### OP-372: Projection-Status\n- **Status:** open\nAkzeptanzkriterien",
            "OP-372",
            200,
        ),
        ({"op_id": "OP-372"}, "", "", "OP-372", 409),
    ],
)
def test_confirmed_start_queues_followup_for_busy_loop(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    arguments: dict[str, str], task_preview: str,
    expected_request: str, expected_op_id: str | None, expected_status: int,
) -> None:
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from werkstatt import chat_session
    from werkstatt.event_store import EventStore
    from werkstatt.web import app as app_modul

    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    monkeypatch.setattr(app_modul, "_PROJECTS_BASE", tmp_path)
    db_path = tmp_path / "sessions.db"
    monkeypatch.setattr(chat_session, "_db_pfad", lambda _project: db_path)
    event_store = EventStore(db_pfad=tmp_path / "events.db")
    event_store.create_run_record(
        "demo", "existing-run", "Originalauftrag", base_commit="abc123",
    )
    monkeypatch.setattr(app_modul, "EventStore", lambda: event_store)

    session_id = "1" * 32
    proposal_id = "2" * 32
    session = chat_session.ChatSession("demo", session_id, db_pfad=db_path)
    session.append("loop_action_proposed", {
        "proposal_id": proposal_id,
        "project": "demo",
        "action": "start",
        "arguments": arguments,
        "task_preview": task_preview,
        "summary": "Loop starten",
        "expires_at": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
    })

    process = SimpleNamespace(pid=12345, poll=lambda: None)
    record: dict[str, Any] = {
        "project": "demo",
        "run_id": "existing-run",
        "pid": process.pid,
        "state": "running",
    }
    monkeypatch.setattr(app_modul, "_LOOP_RUN_IDS", {"demo": "existing-run"})
    monkeypatch.setitem(app_modul._LAUFENDE_LOOPS, "demo", process)
    monkeypatch.setattr(app_modul, "_loop_registry", lambda: SimpleNamespace(
        read=lambda _project: dict(record),
    ))

    response = TestClient(app_modul.app).post(
        f"/api/projects/demo/chat/actions/{proposal_id}",
        json={"session_id": session_id, "decision": "confirm"},
    )

    assert response.status_code == expected_status
    if expected_status == 409:
        assert "keinen gespeicherten Aufgabeninhalt" in response.json()["detail"]
        assert event_store.claim_run_message(
            "demo", "existing-run", "test", kind="chat_followup_request",
        ) is None
        return
    payload = response.json()
    assert payload["state"] == "queued"
    assert payload["result"]["run_id"] == "existing-run"
    message = event_store.claim_run_message(
        "demo", "existing-run", "test", kind="chat_followup_request",
    )
    assert message is not None
    assert message["payload"] == {
        "proposal_id": proposal_id,
        "project": "demo",
        "session_id": session_id,
        "parent_run_id": "existing-run",
        "base_commit": "abc123",
        "checkpoint_version": 0,
        "request": expected_request,
        "op_id": expected_op_id,
    }
    events = session.load()
    assert events[-1]["kind"] == "loop_action_queued"
    assert not any(event["kind"] == "loop_action_completed" for event in events)

    repeated = TestClient(app_modul.app).post(
        f"/api/projects/demo/chat/actions/{proposal_id}",
        json={"session_id": session_id, "decision": "confirm"},
    )
    assert repeated.status_code == 200
    assert repeated.json()["state"] == "queued"
    assert repeated.json()["result"] == payload["result"]


def test_confirmed_start_replays_handoff_after_request_crash(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from werkstatt import chat_session
    from werkstatt.event_store import EventStore
    from werkstatt.web import app as app_modul

    (tmp_path / "demo").mkdir()
    monkeypatch.setattr(app_modul, "_PROJECTS_BASE", tmp_path)
    db_path = tmp_path / "sessions.db"
    monkeypatch.setattr(chat_session, "_db_pfad", lambda _project: db_path)
    event_store = EventStore(db_pfad=tmp_path / "events.db")
    event_store.create_run_record(
        "demo", "existing-run", "Originalauftrag", base_commit="abc123",
    )
    monkeypatch.setattr(app_modul, "EventStore", lambda: event_store)

    session_id = "3" * 32
    proposal_id = "4" * 32
    session = chat_session.ChatSession("demo", session_id, db_pfad=db_path)
    session.append("loop_action_proposed", {
        "proposal_id": proposal_id,
        "project": "demo",
        "action": "start",
        "arguments": {"aufgabe": "Testauftrag"},
        "expires_at": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
    })
    # Simulate a web worker stopping after the durable confirmation but
    # before it enqueues the follow-up into the active run.
    claimed = session.resolve_loop_action(proposal_id, "confirm")
    assert claimed is not None and claimed[1] == "claimed"

    process = SimpleNamespace(pid=12345, poll=lambda: None)
    monkeypatch.setattr(app_modul, "_LOOP_RUN_IDS", {"demo": "existing-run"})
    monkeypatch.setitem(app_modul._LAUFENDE_LOOPS, "demo", process)
    monkeypatch.setattr(app_modul, "_loop_registry", lambda: SimpleNamespace(
        read=lambda _project: {
            "project": "demo",
            "run_id": "existing-run",
            "pid": process.pid,
            "state": "running",
        },
    ))

    response = TestClient(app_modul.app).post(
        f"/api/projects/demo/chat/actions/{proposal_id}",
        json={"session_id": session_id, "decision": "confirm"},
    )

    assert response.status_code == 200
    assert response.json()["state"] == "queued"
    message = event_store.claim_run_message(
        "demo", "existing-run", "test", kind="chat_followup_request",
    )
    assert message is not None
    assert message["message_id"] == f"chat-followup:{proposal_id}"
    assert sum(
        event["kind"] == "loop_action_queued"
        for event in session.load()
    ) == 1


def test_confirmed_start_recovers_existing_run_without_queueing_it_again(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from werkstatt import chat_session
    from werkstatt.web import app as app_modul

    (tmp_path / "demo").mkdir()
    monkeypatch.setattr(app_modul, "_PROJECTS_BASE", tmp_path)
    db_path = tmp_path / "sessions.db"
    monkeypatch.setattr(chat_session, "_db_pfad", lambda _project: db_path)
    session_id = "5" * 32
    proposal_id = "6" * 32
    session = chat_session.ChatSession("demo", session_id, db_pfad=db_path)
    session.append("loop_action_proposed", {
        "proposal_id": proposal_id,
        "project": "demo",
        "action": "start",
        "arguments": {"aufgabe": "Testauftrag"},
        "expires_at": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
    })
    assert session.resolve_loop_action(proposal_id, "confirm")[1] == "claimed"
    monkeypatch.setattr(app_modul, "_loop_registry", lambda: SimpleNamespace(
        read=lambda _project: {
            "run_id": "demo-started-run",
            "pid": 12345,
            "state": "running",
            "context": {"proposal_id": proposal_id},
        },
    ))

    response = TestClient(app_modul.app).post(
        f"/api/projects/demo/chat/actions/{proposal_id}",
        json={"session_id": session_id, "decision": "confirm"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "proposal_id": proposal_id,
        "state": "completed",
        "result": {
            "gestartet": True,
            "run_id": "demo-started-run",
            "wiederhergestellt": True,
            "pid": 12345,
        },
    }
    events = session.load()
    assert sum(event["kind"] == "loop_action_completed" for event in events) == 1
    assert not any(event["kind"] == "loop_action_queued" for event in events)


def test_reject_retry_does_not_replay_already_confirmed_start(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from werkstatt import chat_session
    from werkstatt.web import app as app_modul

    (tmp_path / "demo").mkdir()
    monkeypatch.setattr(app_modul, "_PROJECTS_BASE", tmp_path)
    db_path = tmp_path / "sessions.db"
    monkeypatch.setattr(chat_session, "_db_pfad", lambda _project: db_path)
    session_id = "7" * 32
    proposal_id = "8" * 32
    session = chat_session.ChatSession("demo", session_id, db_pfad=db_path)
    session.append("loop_action_proposed", {
        "proposal_id": proposal_id,
        "project": "demo",
        "action": "start",
        "arguments": {"aufgabe": "Testauftrag"},
        "expires_at": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
    })
    assert session.resolve_loop_action(proposal_id, "confirm")[1] == "claimed"

    response = TestClient(app_modul.app).post(
        f"/api/projects/demo/chat/actions/{proposal_id}",
        json={"session_id": session_id, "decision": "reject"},
    )

    assert response.status_code == 200
    assert response.json()["state"] == "confirmed"
    assert not any(
        event["kind"] in {"loop_action_queued", "loop_action_completed"}
        for event in session.load()
    )


def test_rejected_chat_action_has_no_loop_side_effect(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from werkstatt import chat_session
    from werkstatt.web import app as app_modul

    monkeypatch.setattr(app_modul, "_PROJECTS_BASE", tmp_path)
    db_path = tmp_path / "sessions.db"
    monkeypatch.setattr(chat_session, "_db_pfad", lambda _project: db_path)
    session_id = "c" * 32
    proposal_id = "d" * 32
    session = chat_session.ChatSession("demo", session_id, db_pfad=db_path)
    session.append("loop_action_proposed", {
        "proposal_id": proposal_id,
        "project": "demo",
        "action": "stop",
        "arguments": {},
        "expires_at": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
    })

    response = TestClient(app_modul.app).post(
        f"/api/projects/demo/chat/actions/{proposal_id}",
        json={"session_id": session_id, "decision": "reject"},
    )
    assert response.status_code == 200
    assert response.json()["state"] == "rejected"
    assert [event["kind"] for event in session.load()][-1] == "loop_action_rejected"


def test_debugger_action_rejects_tampered_patch_before_start(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from werkstatt import chat_session
    from werkstatt.web import app as app_modul

    monkeypatch.setattr(app_modul, "_PROJECTS_BASE", tmp_path)
    db_path = tmp_path / "sessions.db"
    monkeypatch.setattr(chat_session, "_db_pfad", lambda _project: db_path)
    session_id = "e" * 32
    proposal_id = "f" * 32
    session = chat_session.ChatSession("demo", session_id, db_pfad=db_path)
    payload = {
        "signatur": "regression-demo",
        "ursache_tag": "fixture",
        "diff": (
            "diff --git a/pkg/demo.py b/pkg/demo.py\n"
            "--- a/pkg/demo.py\n+++ b/pkg/demo.py\n"
            "@@ -1 +1 @@\n-old = 1\n+new = 2\n"
        ),
        "betroffene_dateien": ["pkg/demo.py"],
        "confidence": 0.9,
        "project": "demo",
        "run_id": "demo-run-123",
        "base_head": "a" * 40,
        "patch_hash": "0" * 64,
    }
    session.append("loop_action_proposed", {
        "proposal_id": proposal_id,
        "project": "demo",
        "action": "start",
        "arguments": {"debugger_fix": payload},
        "expires_at": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
    })

    response = TestClient(app_modul.app).post(
        f"/api/projects/demo/chat/actions/{proposal_id}",
        json={"session_id": session_id, "decision": "confirm"},
    )
    assert response.status_code == 400
    assert "Debugger-Freigabe ungueltig" in response.json()["detail"]
    assert [event["kind"] for event in session.load()][-1] == "loop_action_failed"


def test_chat_start_persists_chat_origin_and_selection_reason(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from werkstatt import chat_session
    from werkstatt.web import app as app_modul

    docs = tmp_path / "demo" / "docs"
    docs.mkdir(parents=True)
    (docs / "STATUS.md").write_text(
        "### OP-321: Chat-gesteuerter Start\n"
        "- **Status:** open\n"
        "- **Akzeptanzkriterien:** Ergebnis belegbar.\n"
        "- **Tests:** pytest -q tests/test_321.py\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(app_modul, "_PROJECTS_BASE", tmp_path)
    db_path = tmp_path / "sessions.db"
    monkeypatch.setattr(chat_session, "_db_pfad", lambda _project: db_path)
    app_modul._LAUFENDE_LOOPS.clear()
    app_modul._LOOP_RUN_IDS.clear()
    app_modul._PAUSIERTE_LOOPS.clear()

    class _Started:
        pid = os.getpid()

        def poll(self) -> None:
            return None

    monkeypatch.setattr(
        app_modul.subprocess,
        "Popen",
        lambda *_args, **_kwargs: _Started(),
    )

    session_id = "a" * 32
    proposal_id = "b" * 32
    selection_reason = ["Nutzer hat OP-321 im Chat angefordert."]
    session = chat_session.ChatSession("demo", session_id, db_pfad=db_path)
    session.append("loop_action_proposed", {
        "proposal_id": proposal_id,
        "project": "demo",
        "action": "start",
        "arguments": {"op_id": "OP-321"},
        "selection_reason": selection_reason,
        "expires_at": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
    })

    client = TestClient(app_modul.app)
    response = client.post(
        f"/api/projects/demo/chat/actions/{proposal_id}",
        json={"session_id": session_id, "decision": "confirm"},
    )

    assert response.status_code == 200
    assert response.json()["state"] == "completed"
    context = client.get("/api/projects/demo/loop").json()["run_context"]
    assert context["origin"] == "chat"
    assert context["origin_session_id"] == session_id
    assert context["proposal_id"] == proposal_id
    assert context["selection_reason"] == selection_reason
    assert context["op_id"] == "OP-321"
    log_handle = app_modul._LOOP_LOG_HANDLES.pop("demo", None)
    if log_handle is not None:
        log_handle.close()
    app_modul._LAUFENDE_LOOPS.clear()
    app_modul._LOOP_RUN_IDS.clear()
