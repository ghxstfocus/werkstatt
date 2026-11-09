"""OP-381e: UI-Aggregatoren sehen Events sofort (Read-Through).

Verbotenes Verhalten (Live-Bug 2026-11-09 19:10):
- audit() schreibt in JSONL, aber SQLite bleibt leer
  (weil _FLUSH_INTERVAL=100, kurzer Run < 100 Events).
- aggregate_ambient() liest SQLite und sah den aktuellen Run nicht.
- User sah "Fehler 22m" mit altem Run, obwohl Loop lief.

Nicht-Scope: aggregate_timeline liest JSONL direkt (kein SQLite-Lag).

Fix: _frische_projektion() ruft Projector().tail() vor SQLite-Reads.
Aufrufer: aggregate_ambient, aggregate_status, aggregate_gate_context.
NICHT aggregate_timeline (liest JSONL).
"""
from __future__ import annotations

import pytest

from werkstatt import audit as _audit
from werkstatt import event_store as _es
from werkstatt import paths as _paths
from werkstatt import projection as _proj
from werkstatt.audit import audit, set_run_id
from werkstatt.web import inspector


@pytest.fixture
def isoliert(monkeypatch, tmp_path):
    """Zentrale werkstatt_home-Quelle patchen (4 Modul-Bindings)."""
    monkeypatch.setattr(_paths, "werkstatt_home", lambda: tmp_path)
    monkeypatch.setattr(_audit, "_werkstatt_home", lambda: tmp_path)
    monkeypatch.setattr(_proj, "_werkstatt_home", lambda: tmp_path)
    monkeypatch.setattr(_es, "werkstatt_home", lambda: tmp_path)
    yield tmp_path
    try:
        set_run_id("")
    except Exception:  # noqa: BLE001
        pass


def test_ambient_sieht_neuen_run_nach_loop_failed(isoliert, tmp_path):
    """Nach audit(loop_failed) muss ambient den neuen Run sehen.

    Bug: aggregate_ambient liest _letzter_run_id aus SQLite. Ohne
    Read-Through bleibt SQLite leer (unter 100 Events), ambient
    zeigt den alten Run.
    """
    set_run_id("test-ambient-rt")
    audit("loop_failed", {"erfolg": False}, tmp_path, "werkstatt")

    amb = inspector.aggregate_ambient("werkstatt")
    lr = amb.get("last_run") or {}
    assert lr.get("run_id") == "test-ambient-rt", (
        f"Ambient muss neuen Run sehen, war {lr.get('run_id')!r}. "
        f"Ambient-keys: {list(amb.keys())}"
    )


def test_status_sieht_neuen_run(isoliert, tmp_path):
    """Nach audit(loop_failed) muss status den neuen Run sehen."""
    set_run_id("test-status-rt")
    audit("loop_failed", {"erfolg": False}, tmp_path, "werkstatt")

    st = inspector.aggregate_status("werkstatt")
    # aggregate_status liefert dict mit "run_id" oder "letzter_run"
    rid = st.get("run_id") or (st.get("letzter_run") or {}).get("run_id")
    assert rid == "test-status-rt", (
        f"Status muss neuen Run sehen, war {rid!r}. "
        f"Status-keys: {list(st.keys())}"
    )
