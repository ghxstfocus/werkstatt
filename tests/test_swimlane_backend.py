"""OP-381i: aggregate_swimlane Backend.

Verbotenes Verhalten:
- aggregate_swimlane liefert keine Lanes (UI kann nichts rendern)
- llm_call_start/llm_call_end werden nicht als ein Balken gruppiert
  (Timeline zeigt 4x-Rauschen statt einem LLM-Call)
- Aktiv-Rolle nicht markiert (User sieht nicht wer JETZT arbeitet)
- migrated-Datei wird gelesen (statische Dumps aus OP-323)
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


def test_swimlane_lanes_pro_rolle(projektion, tmp_path):
    """Explorer + Builder: 2 Lanes mit je einem Balken."""
    jetzt = datetime.now(UTC)
    _schreibe(tmp_path, [
        {"kind": "loop_started", "run_id": "r1", "project": "werkstatt",
         "timestamp": jetzt.isoformat(), "agent": "agent_pipeline"},
        {"kind": "loop_explorer_suchbegriffe", "run_id": "r1",
         "project": "werkstatt",
         "timestamp": (jetzt + timedelta(seconds=1)).isoformat(),
         "agent": "agent_pipeline", "anzahl": 1, "begriffe": ["x"]},
        {"kind": "builder_patch_updated", "run_id": "r1",
         "project": "werkstatt",
         "timestamp": (jetzt + timedelta(seconds=3)).isoformat(),
         "agent": "builder"},
    ])
    sw = inspector.aggregate_swimlane("werkstatt")
    lanes = {l["rolle"]: l for l in sw["lanes"]}
    assert "explorer" in lanes, f"Explorer-Lane fehlt: {list(lanes)}"
    assert "builder" in lanes, f"Builder-Lane fehlt: {list(lanes)}"
    assert len(lanes["explorer"]["balken"]) >= 1
    assert len(lanes["builder"]["balken"]) >= 1


def test_swimlane_start_end_paar_als_ein_balken(projektion, tmp_path):
    """llm_call_start + llm_call_end = ein Balken mit dauer_s."""
    jetzt = datetime.now(UTC)
    _schreibe(tmp_path, [
        {"kind": "llm_call_start", "run_id": "r1", "project": "werkstatt",
         "timestamp": jetzt.isoformat(), "agent": "explorer",
         "model": "deepseek-chat"},
        {"kind": "llm_call_end", "run_id": "r1", "project": "werkstatt",
         "timestamp": (jetzt + timedelta(seconds=5)).isoformat(),
         "agent": "explorer", "ok": True, "elapsed_s": 5.0},
    ])
    sw = inspector.aggregate_swimlane("werkstatt")
    # Explorer-Lane: der llm_call_start/end ist EIN Balken (dauer ~5s)
    explorer_balken = [
        b for lane in sw["lanes"] if lane["rolle"] == "explorer"
        for b in lane["balken"]
    ]
    llm_balken = [b for b in explorer_balken if b["kind"] == "llm_call_start"]
    assert len(llm_balken) == 1, f"erwartet 1 llm-Balken, gefunden {len(llm_balken)}"
    assert llm_balken[0]["dauer_s"] >= 4.0
    assert llm_balken[0]["end_ts"], "end_ts muss aus dem Paar kommen"


def test_swimlane_aktiv_rolle(projektion, tmp_path):
    """Aktive Rolle aus letztem 'in progress'-Event."""
    jetzt = datetime.now(UTC)
    _schreibe(tmp_path, [
        {"kind": "loop_started", "run_id": "r1", "project": "werkstatt",
         "timestamp": (jetzt - timedelta(seconds=20)).isoformat(),
         "agent": "agent_pipeline"},
        {"kind": "llm_call_start", "run_id": "r1", "project": "werkstatt",
         "timestamp": (jetzt - timedelta(seconds=3)).isoformat(),
         "agent": "architect", "model": "deepseek-reasoner"},
    ])
    sw = inspector.aggregate_swimlane("werkstatt")
    assert sw["aktiv"].get("rolle") == "architect"


def test_swimlane_ignoriert_migrated(projektion, tmp_path):
    """-migrated-*-Datei wird nicht gelesen."""
    jetzt = datetime.now(UTC).isoformat()
    d = tmp_path / "audit-logs"
    d.mkdir(exist_ok=True)
    # Echte Tagesdatei
    with (d / "agent-pipeline-2026-11-09.jsonl").open("w") as fh:
        fh.write(json.dumps({
            "kind": "loop_started", "run_id": "r1", "project": "werkstatt",
            "timestamp": jetzt, "agent": "agent_pipeline",
        }) + "\n")
    # Migrated-Datei (alphabetisch letzter - darf NICHT gelesen werden)
    with (d / "agent-pipeline-migrated-2026-11-09.jsonl").open("w") as fh:
        fh.write(json.dumps({
            "kind": "fake_migrated_event", "run_id": "r-alt",
            "project": "werkstatt", "timestamp": jetzt,
            "agent": "agent_pipeline",
        }) + "\n")
    sw = inspector.aggregate_swimlane("werkstatt")
    assert sw["run_id"] == "r1", (
        f"migrated-Datei wurde gelesen, run_id war {sw['run_id']}"
    )
