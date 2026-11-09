"""OP-381d: aggregate_ambient und aggregate_gate_context liefern
dieselbe gates_open-Zahl.

Verbotenes Verhalten: ambient zaehlt projektweit (alle Runs),
context nur letzte_run_id — UI zeigt widerspruechliche Werte
(Live 2026-11-09: Ambient "2 Gates offen", Panel leer weil 0).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from werkstatt import audit as _audit
from werkstatt import projection as _proj
from werkstatt.web import inspector


@pytest.fixture
def isoliert(monkeypatch, tmp_path):
    """Alle werkstatt_home-Bindings patchen.

    Live-Bug 2026-11-09 22:20: Test war gruen solange die ECHTE DB
    keine offenen Gates hatte. Der 22:15-Loop liess ein Commit-Gate
    offen -> Test rot, weil er die echte DB las (Fixture fehlte
    inspector + _es). Lehre: alle 4 Bindings patchen, nicht nur 2.
    """
    from werkstatt import event_store as _es
    from werkstatt.web import inspector

    monkeypatch.setattr(_audit, "_werkstatt_home", lambda: tmp_path)
    monkeypatch.setattr(_proj, "_werkstatt_home", lambda: tmp_path)
    monkeypatch.setattr(_es, "werkstatt_home", lambda: tmp_path)
    monkeypatch.setattr(inspector, "werkstatt_home", lambda: tmp_path)
    return tmp_path


def _schreibe(tmp_path: Path, run_id: str, events: list[tuple[str, dict]]) -> None:
    d = tmp_path / "audit-logs"
    d.mkdir(exist_ok=True)
    f = d / "agent-pipeline-2026-11-09.jsonl"
    with f.open("a", encoding="utf-8") as fh:
        for kind, payload in events:
            fh.write(json.dumps({
                "kind": kind, "payload": payload, "run_id": run_id,
                "project": "werkstatt", "timestamp": "2026-11-09T10:00:00+00:00",
            }) + "\n")
    # Projektor anstossen
    from werkstatt.projection import Projector
    Projector().tail()


def test_ambient_und_gate_context_stimmen_ueberein(isoliert, tmp_path):
    """Kern-Invariante: ambient.gates_open == len(context.offene_gates)."""
    # 3 Gates insgesamt, 1 unbeantwortet im AKTUELLEN Run
    _schreibe(tmp_path, "run-abc", [
        ("gate_open", {"gate_id": "g1", "prompt": "?", "optionen": "jna"}),
        ("gate_answered", {"gate_id": "g1", "answer": "j"}),
        ("gate_open", {"gate_id": "g2", "prompt": "?", "optionen": "jna"}),
    ])
    # Alter Run mit einem offenen Gate
    _schreibe(tmp_path, "run-alt", [
        ("gate_open", {"gate_id": "g-alt", "prompt": "?", "optionen": "jna"}),
    ])
    _schreibe(tmp_path, "run-abc", [
        ("loop_failed", {"grund": "test"}),
    ])

    amb = inspector.aggregate_ambient("werkstatt")
    ctx = inspector.aggregate_gate_context("werkstatt")
    assert amb["gates_open"] == len(ctx.get("offene_gates") or []), (
        f"Widerspruch: ambient={amb['gates_open']}, "
        f"context={len(ctx.get('offene_gates') or [])}"
    )


def test_ambient_null_wenn_context_null(isoliert, tmp_path):
    """Wenn context 0 offene Gates hat, muss ambient auch 0 zeigen."""
    _schreibe(tmp_path, "run-x", [
        ("gate_open", {"gate_id": "g1", "prompt": "?", "optionen": "jna"}),
        ("gate_answered", {"gate_id": "g1", "answer": "j"}),
        ("loop_ended", {"erfolg": True}),
    ])
    amb = inspector.aggregate_ambient("werkstatt")
    ctx = inspector.aggregate_gate_context("werkstatt")
    assert len(ctx.get("offene_gates") or []) == 0
    assert amb["gates_open"] == 0, (
        f"ambient={amb['gates_open']} obwohl keine offenen Gates, "
        f"context={len(ctx.get('offene_gates') or [])}"
    )
