"""OP-381h: Timeline liefert Rollen pro Kind + Live-Aktiv-Status.

Verbotenes Verhalten:
- aggregate_timeline ohne 'rolle' an children -> UI kann nicht farbcodieren
- aggregate_timeline_aktiv meldet Rolle, obwohl letztes Event
  > 300s alt ist (haengender Run als 'laeuft' angezeigt)
- aggregate_timeline_aktiv meldet nichts, obwohl ein llm_call_start
  ohne Folge-Event vorliegt (aktive Rolle unsichtbar)

Fixture-Lehre 2026-11-09: alle werkstatt_home-Bindings patchen,
auch inspector.werkstatt_home (from-import-Bindung).
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


def test_kinder_haben_rolle(projektion, tmp_path):
    """Jedes Kind in knoten[].children[] hat 'rolle'."""
    jetzt = datetime.now(UTC).isoformat()
    _schreibe(tmp_path, [
        {"kind": "loop_phase", "phase": "vorbereitung", "run_id": "r1",
         "project": "werkstatt", "timestamp": jetzt, "agent": "agent_pipeline"},
        {"kind": "explorer_result", "run_id": "r1", "project": "werkstatt",
         "timestamp": jetzt, "agent": "explorer"},
        {"kind": "builder_patch_updated", "run_id": "r1", "project": "werkstatt",
         "timestamp": jetzt, "agent": "builder"},
        {"kind": "loop_verify_ok", "run_id": "r1", "project": "werkstatt",
         "timestamp": jetzt, "agent": "agent_pipeline"},
    ])
    knoten = inspector.aggregate_timeline("werkstatt")
    rollen = {}
    for k in knoten:
        for ch in k.get("children") or []:
            rollen[ch.get("kind")] = ch.get("rolle")
    assert rollen.get("explorer_result") == "explorer"
    assert rollen.get("builder_patch_updated") == "builder"
    assert rollen.get("loop_verify_ok") == "verify"


def test_aktiv_bei_offenem_llm_call(projektion, tmp_path):
    """Letztes Event = llm_call_start ohne Folge -> aktiv.rolle='architect'."""
    jetzt = datetime.now(UTC)
    _schreibe(tmp_path, [
        {"kind": "loop_started", "run_id": "r1", "project": "werkstatt",
         "timestamp": (jetzt - timedelta(seconds=20)).isoformat(),
         "agent": "agent_pipeline", "aufgabe_kurz": "x"},
        {"kind": "llm_call_start", "run_id": "r1", "project": "werkstatt",
         "timestamp": (jetzt - timedelta(seconds=5)).isoformat(),
         "agent": "architect", "model": "deepseek-reasoner"},
    ])
    aktiv = inspector.aggregate_timeline_aktiv("werkstatt")
    assert aktiv.get("rolle") == "architect"
    assert aktiv.get("kind") == "llm_call_start"
    assert 0 <= aktiv.get("seit_s", -1) <= 10


def test_stale_run_nicht_als_aktiv(projektion, tmp_path):
    """Letztes Event 10 Minuten alt -> kein 'aktiv' (haengt)."""
    jetzt = datetime.now(UTC)
    _schreibe(tmp_path, [
        {"kind": "llm_call_start", "run_id": "r1", "project": "werkstatt",
         "timestamp": (jetzt - timedelta(minutes=10)).isoformat(),
         "agent": "architect", "model": "deepseek-reasoner"},
    ])
    aktiv = inspector.aggregate_timeline_aktiv("werkstatt")
    assert aktiv == {}, (
        f"10 min altes llm_call_start darf NICHT als 'aktiv' gelten, "
        f"war {aktiv}"
    )


def test_kein_aktives_event(projektion, tmp_path):
    """Letztes Event = loop_failed -> aktiv leer."""
    jetzt = datetime.now(UTC).isoformat()
    _schreibe(tmp_path, [
        {"kind": "loop_started", "run_id": "r1", "project": "werkstatt",
         "timestamp": jetzt, "agent": "agent_pipeline"},
        {"kind": "loop_failed", "run_id": "r1", "project": "werkstatt",
         "timestamp": jetzt, "agent": "agent_pipeline"},
    ])
    aktiv = inspector.aggregate_timeline_aktiv("werkstatt")
    assert aktiv == {}
