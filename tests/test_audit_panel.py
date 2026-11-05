from __future__ import annotations

import json
from pathlib import Path

import pytest

from werkstatt.render import TerminalEmitter

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


def test_aktuelles_home_ohne_kontext(monkeypatch, tmp_path):
    """OP-091: _aktuelles_home() crasht nicht wenn _home_kontext None ist."""
    import werkstatt.web.audit_panel as _ap
    monkeypatch.setattr(_ap, "_home_kontext", None)
    monkeypatch.chdir(tmp_path)
    result = _ap._aktuelles_home()
    assert isinstance(result, type(tmp_path))


def test_aktuelles_home_mit_kontext(monkeypatch, tmp_path):
    """OP-091: _home_kontext ueberschreibt CWD."""
    import werkstatt.web.audit_panel as _ap
    monkeypatch.setattr(_ap, "_home_kontext", tmp_path)
    assert _ap._aktuelles_home() == tmp_path


def test_lese_events_findet_agent_pipeline(tmp_path):
    """OP-091: Reader findet agent-pipeline-*.jsonl."""
    import json

    import werkstatt.web.audit_panel as _ap
    audit_dir = tmp_path / "audit-logs"
    audit_dir.mkdir()
    datei = audit_dir / "agent-pipeline-2026-11-03.jsonl"
    datei.write_text(
        json.dumps({"kind": "loop_erfolg", "project": "probe"}) + "\n",
        encoding="utf-8",
    )
    events = _ap._lese_events(audit_dir)
    assert len(events) == 1
    assert events[0]["kind"] == "loop_erfolg"
