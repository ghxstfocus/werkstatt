from __future__ import annotations

import json
from pathlib import Path

import pytest

from werkstatt.loop_renderer import TerminalEmitter

pytest.importorskip("httpx")
pytest.importorskip("fastapi.testclient")

from fastapi.testclient import TestClient

from werkstatt.web.audit_panel import create_app


def _schreibe_tag(verzeichnis: Path, datum: str, events: list[dict]) -> None:
    verzeichnis.mkdir(parents=True, exist_ok=True)
    ziel = verzeichnis / f"{datum}.jsonl"
    with ziel.open("w", encoding="utf-8", newline="\n") as fh:
        for event in events:
            fh.write(json.dumps(event, sort_keys=True) + "\n")


def _app_mit_client(home: Path, emitter: TerminalEmitter | None = None) -> TestClient:
    return TestClient(create_app(home=home, emitter=emitter))


def test_history_rest_filter(tmp_path: Path) -> None:
    audit_dir = tmp_path / "audit-logs"
    _schreibe_tag(
        audit_dir,
        "2026-11-01",
        [
            {
                "ts": "2026-11-01T10:00:00",
                "kind": "task_ok",
                "run_id": "a",
                "payload": {"task": "t1"},
            },
            {
                "ts": "2026-11-01T10:05:00",
                "kind": "task_ok",
                "run_id": "b",
                "payload": {"task": "t2"},
            },
        ],
    )
    _schreibe_tag(
        audit_dir,
        "2026-11-02",
        [
            {
                "ts": "2026-11-02T09:00:00",
                "kind": "veto",
                "run_id": "a",
                "payload": {"grund": "spec"},
            },
            {
                "ts": "2026-11-02T09:30:00",
                "kind": "phase_ende",
                "run_id": "c",
                "payload": {"rc": 1},
            },
        ],
    )

    with _app_mit_client(tmp_path) as client:
        antwort = client.get("/api/projects/demo/audit")
        assert antwort.status_code == 200
        daten = antwort.json()
        assert daten["anzahl"] == 4
        events = daten["events"]
        assert len(events) == 4
        assert [e["kind"] for e in events] == [
            "task_ok",
            "task_ok",
            "veto",
            "phase_ende",
        ]

        antwort = client.get("/api/projects/demo/audit", params={"limit": 2})
        assert antwort.status_code == 200
        daten = antwort.json()
        assert daten["anzahl"] == 2
        assert [e["kind"] for e in daten["events"]] == ["veto", "phase_ende"]

        antwort = client.get("/api/projects/demo/audit", params={"kind": "task_ok"})
        assert antwort.status_code == 200
        assert antwort.json()["anzahl"] == 2

        antwort = client.get("/api/projects/demo/audit", params={"run_id": "a"})
        assert antwort.status_code == 200
        daten = antwort.json()
        assert daten["anzahl"] == 2
        assert all(e["run_id"] == "a" for e in daten["events"])

        antwort = client.get(
            "/api/projects/demo/audit",
            params={"kind": "task_ok", "run_id": "b"},
        )
        assert antwort.status_code == 200
        assert antwort.json()["anzahl"] == 1

        antwort = client.get(
            "/api/projects/demo/audit", params={"datum_von": "2026-11-02"}
        )
        assert antwort.status_code == 200
        assert antwort.json()["anzahl"] == 2

        antwort = client.get(
            "/api/projects/demo/audit", params={"datum_bis": "2026-11-01"}
        )
        assert antwort.status_code == 200
        assert antwort.json()["anzahl"] == 2

        antwort = client.get(
            "/api/projects/demo/audit",
            params={"datum_von": "2026-11-01", "datum_bis": "2026-11-01"},
        )
        assert antwort.status_code == 200
        assert antwort.json()["anzahl"] == 2

        antwort = client.get("/api/projects/demo/audit", params={"limit": 0})
        assert antwort.status_code == 422
