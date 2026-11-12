"""Chat-Gates: Run-Bezug, Session-Replay und Antworten bleiben gekoppelt."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest


class _GateStore:
    def __init__(self) -> None:
        self.events = [
            {
                "kind": "gate_open",
                "run_id": "demo-run",
                "payload": {
                    "gate_id": "gate-1",
                    "prompt": "Plan freigeben?",
                    "optionen": "jn",
                    "typ": "jna",
                },
            },
        ]

    def query(
        self, run_id: str, *, kind: str | None = None,
    ) -> list[dict[str, Any]]:
        assert run_id == "demo-run"
        return [
            event for event in self.events
            if kind is None or event["kind"] == kind
        ]


def _client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[Any, _GateStore, Any]:
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from werkstatt import chat_session
    from werkstatt.web import app as app_modul
    from werkstatt.web import inspector

    project_dir = tmp_path / "demo"
    project_dir.mkdir()
    monkeypatch.setattr(app_modul, "_PROJECTS_BASE", tmp_path)
    db_path = tmp_path / "chat-sessions.db"
    monkeypatch.setattr(chat_session, "_db_pfad", lambda _project: db_path)
    monkeypatch.setattr(
        app_modul,
        "_loop_registry",
        lambda: SimpleNamespace(read=lambda _project: {
            "project": "demo", "run_id": "demo-run", "state": "running",
        }),
    )
    monkeypatch.setattr(
        inspector,
        "aggregate_gate_context",
        lambda _project, run_id=None: {
            "run_id": run_id,
            "offene_gates": [{
                "gate_id": "gate-1",
                "prompt": "Plan freigeben?",
                "optionen": "jn",
                "typ": "jna",
            }],
            "plan": {"text": "Erst testen, dann implementieren."},
            "verify": {"status": "ok"},
            "reviewer": None,
            "empfehlung": "j",
            "empfehlung_grund": "Verify gruen",
            "diff_stat": "1 Datei geaendert",
            "diff": "",
        },
    )
    store = _GateStore()
    monkeypatch.setattr(app_modul, "EventStore", lambda: store)

    from werkstatt.web import auth
    monkeypatch.setattr(auth, "is_auth_disabled", lambda: True)

    from werkstatt import audit as audit_module

    def _audit(kind: str, payload: dict[str, Any], *_args: Any) -> bool:
        store.events.append({
            "kind": kind,
            "run_id": payload.get("run_id"),
            "payload": dict(payload),
        })
        return True

    monkeypatch.setattr(audit_module, "audit", _audit)
    from werkstatt.projection import Projector
    monkeypatch.setattr(Projector, "tail", lambda _self: None)
    return TestClient(app_modul.app), store, chat_session


def test_gate_sync_persists_one_card_and_replays_decision(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    client, store, chat_session = _client(monkeypatch, tmp_path)
    body = {"session_id": "a" * 32, "run_id": "demo-run"}

    first = client.post("/api/projects/demo/chat/gates/sync", json=body)
    second = client.post("/api/projects/demo/chat/gates/sync", json=body)

    assert first.status_code == second.status_code == 200
    assert [event["kind"] for event in first.json()["events"]] == ["gate_card"]
    session = chat_session.ChatSession(
        "demo", body["session_id"], db_pfad=tmp_path / "chat-sessions.db",
    )
    assert [event["kind"] for event in session.load()] == ["gate_card"]

    answered = client.post(
        "/api/projects/demo/chat/gates/answer",
        json={
            **body,
            "gate_id": "gate-1",
            "answer": "j",
        },
    )
    assert answered.status_code == 200
    assert store.events[-1]["kind"] == "gate_answered"
    assert store.events[-1]["payload"]["session_id"] == body["session_id"]

    replay = client.post("/api/projects/demo/chat/gates/sync", json=body)
    assert replay.status_code == 200
    assert [event["kind"] for event in replay.json()["events"]] == [
        "gate_card", "gate_decision",
    ]
    assert [event["kind"] for event in session.load()] == [
        "gate_card", "gate_decision",
    ]


def test_chat_gate_rejects_run_from_another_project(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    client, _store, _chat_session = _client(monkeypatch, tmp_path)
    from werkstatt.web import app as app_modul

    monkeypatch.setattr(
        app_modul,
        "_loop_registry",
        lambda: SimpleNamespace(read=lambda _project: {
            "project": "demo", "run_id": "other-run", "state": "running",
        }),
    )

    response = client.post(
        "/api/projects/demo/chat/gates/sync",
        json={"session_id": "b" * 32, "run_id": "demo-run"},
    )

    assert response.status_code == 404
