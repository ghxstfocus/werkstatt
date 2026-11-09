"""OP-381j: aggregate_live_feed Backend.

Verbotenes Verhalten:
- Steps nicht chronologisch sortiert (Log unlesbar)
- Aktiv-Step erscheint doppelt (in steps UND in aktiv)
- Naechster-Schritt-Heuristik fehlt (User sieht 'was kommt?')
- Run-Filter greift nicht (alte Runs mischen rein)
- Limit wirkt nicht (UI erschlaegt bei 200+ Events)
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from werkstatt import audit as _audit
from werkstatt import event_store as _es
from werkstatt import paths as _paths
from werkstatt import projection as _proj
from werkstatt.web import inspector


@pytest.fixture
def projektion(monkeypatch, tmp_path):
    monkeypatch.setattr(_paths, "werkstatt_home", lambda: tmp_path)
    monkeypatch.setattr(_audit, "_werkstatt_home", lambda: tmp_path)
    monkeypatch.setattr(_proj, "_werkstatt_home", lambda: tmp_path)
    monkeypatch.setattr(_es, "werkstatt_home", lambda: tmp_path)
    monkeypatch.setattr(inspector, "werkstatt_home", lambda: tmp_path)
    yield tmp_path


def _schreibe(tmp_path, events: list[dict]) -> None:
    d = tmp_path / "audit-logs"
    d.mkdir(exist_ok=True)
    with (d / "agent-pipeline-2026-11-09.jsonl").open("w", encoding="utf-8") as fh:
        for ev in events:
            fh.write(json.dumps(ev) + "\n")


def test_steps_chronologisch(projektion, tmp_path):
    """Steps sind aufsteigend sortiert (aelteste zuerst)."""
    jetzt = datetime.now(UTC)
    _schreibe(tmp_path, [
        {"kind": "loop_started", "run_id": "r1", "project": "werkstatt",
         "timestamp": (jetzt - timedelta(seconds=10)).isoformat(),
         "agent": "agent_pipeline"},
        {"kind": "explorer_result", "run_id": "r1", "project": "werkstatt",
         "timestamp": (jetzt - timedelta(seconds=5)).isoformat(),
         "agent": "explorer"},
        {"kind": "loop_failed", "run_id": "r1", "project": "werkstatt",
         "timestamp": jetzt.isoformat(), "agent": "agent_pipeline"},
    ])
    feed = inspector.aggregate_live_feed("werkstatt")
    steps = feed.get("steps") or []
    assert len(steps) == 3
    # kind-Reihenfolge
    assert steps[0]["kind"] == "loop_started"
    assert steps[1]["kind"] == "explorer_result"
    assert steps[2]["kind"] == "loop_failed"


def test_aktiv_bei_offenem_llm_call(projektion, tmp_path):
    """llm_call_start als letztes -> aktiv.rolle=architect."""
    jetzt = datetime.now(UTC)
    _schreibe(tmp_path, [
        {"kind": "loop_started", "run_id": "r1", "project": "werkstatt",
         "timestamp": (jetzt - timedelta(seconds=20)).isoformat(),
         "agent": "agent_pipeline"},
        {"kind": "llm_call_start", "run_id": "r1", "project": "werkstatt",
         "timestamp": (jetzt - timedelta(seconds=5)).isoformat(),
         "agent": "architect", "model": "deepseek-reasoner"},
    ])
    feed = inspector.aggregate_live_feed("werkstatt")
    assert feed["aktiv"].get("rolle") == "architect"
    assert feed["aktiv"].get("kind") == "llm_call_start"
    # Aktiv-Event NICHT in steps (doppelt vermeiden)
    kinds_in_steps = [s["kind"] for s in (feed.get("steps") or [])]
    assert "llm_call_start" not in kinds_in_steps


def test_naechster_aus_rolle(projektion, tmp_path):
    """aktiv=explorer -> naechster.rolle=scout."""
    jetzt = datetime.now(UTC)
    _schreibe(tmp_path, [
        {"kind": "llm_call_start", "run_id": "r1", "project": "werkstatt",
         "timestamp": (jetzt - timedelta(seconds=5)).isoformat(),
         "agent": "explorer"},
    ])
    feed = inspector.aggregate_live_feed("werkstatt")
    assert feed.get("naechster", {}).get("rolle") == "scout"


def test_limit(projektion, tmp_path):
    """40 Events, limit 10 -> 10 steps."""
    jetzt = datetime.now(UTC)
    events = []
    for i in range(40):
        events.append({
            "kind": f"event_{i}", "run_id": "r1", "project": "werkstatt",
            "timestamp": (jetzt - timedelta(seconds=40 - i)).isoformat(),
            "agent": "agent_pipeline",
        })
    _schreibe(tmp_path, events)
    feed = inspector.aggregate_live_feed("werkstatt", limit=10)
    assert len(feed.get("steps") or []) == 10


def test_run_filter(projektion, tmp_path):
    """Zwei Runs in einer Datei -> nur der letzte erscheint."""
    jetzt = datetime.now(UTC)
    _schreibe(tmp_path, [
        {"kind": "old_event", "run_id": "alt", "project": "werkstatt",
         "timestamp": (jetzt - timedelta(seconds=100)).isoformat(),
         "agent": "agent_pipeline"},
        {"kind": "loop_started", "run_id": "neu", "project": "werkstatt",
         "timestamp": (jetzt - timedelta(seconds=10)).isoformat(),
         "agent": "agent_pipeline"},
        {"kind": "loop_failed", "run_id": "neu", "project": "werkstatt",
         "timestamp": jetzt.isoformat(), "agent": "agent_pipeline"},
    ])
    feed = inspector.aggregate_live_feed("werkstatt")
    assert feed["run_id"] == "neu"
    kinds = [s["kind"] for s in feed.get("steps") or []]
    assert "old_event" not in kinds
