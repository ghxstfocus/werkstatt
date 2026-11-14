"""Gate-Web-API: Antworten muessen zur offenen Gate-Spezifikation passen."""
from __future__ import annotations

from typing import Any

import pytest


def _gate_client(
    monkeypatch: pytest.MonkeyPatch,
    *,
    optionen: str = "jn",
    typ: str = "jna",
) -> tuple[Any, list[tuple[str, dict[str, Any]]]]:
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from werkstatt.web import app as app_modul

    gate_open = {
        "payload": {
            "gate_id": "gate-1",
            "optionen": optionen,
            "typ": typ,
        },
    }

    class _Store:
        def query(
            self,
            run_id: str,
            *,
            kind: str | None = None,
            project: str | None = None,
        ) -> list[dict[str, Any]]:
            assert run_id == "demo-run"
            return (
                [gate_open]
                if kind == "gate_open" and project == "werkstatt"
                else []
            )

    monkeypatch.setattr(app_modul, "EventStore", _Store)
    audit_events: list[tuple[str, dict[str, Any]]] = []
    import werkstatt.audit as audit_module

    monkeypatch.setattr(
        audit_module,
        "audit",
        lambda kind, payload, *_args: audit_events.append((kind, payload)),
    )
    from werkstatt.projection import Projector

    monkeypatch.setattr(Projector, "tail", lambda _self: None)
    return TestClient(app_modul.app), audit_events


def test_gate_api_rejects_unoffered_answer_without_approving(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, audit_events = _gate_client(monkeypatch, optionen="n")

    response = client.post(
        "/api/runs/demo-run/gate",
        json={"gate_id": "gate-1", "answer": "j"},
    )

    assert response.status_code == 422
    assert audit_events == []


def test_gate_api_accepts_only_selected_button_option(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, audit_events = _gate_client(monkeypatch, optionen="jn")

    response = client.post(
        "/api/runs/demo-run/gate",
        json={"gate_id": "gate-1", "answer": "J"},
    )

    assert response.status_code == 200
    assert audit_events[0][0] == "gate_answered"
    assert audit_events[0][1]["answer"] == "j"


def test_gate_api_keeps_free_text_gate_answers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, audit_events = _gate_client(monkeypatch, optionen="", typ="freitext")
    reason = "Der Plan braucht noch einen konkreten Verify-Schritt."

    response = client.post(
        "/api/runs/demo-run/gate",
        json={"gate_id": "gate-1", "answer": reason},
    )

    assert response.status_code == 200
    assert audit_events[0][1]["answer"] == reason


def test_gate_api_rejects_blank_free_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, audit_events = _gate_client(monkeypatch, typ="freitext")

    response = client.post(
        "/api/runs/demo-run/gate",
        json={"gate_id": "gate-1", "answer": "   "},
    )

    assert response.status_code == 400
    assert audit_events == []
