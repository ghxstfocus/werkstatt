"""Tests fuer OP-202: gate_bridge + E2E (POST -> wait)."""
from __future__ import annotations

import threading
import time

import pytest

from werkstatt import gate_bridge, gates
from werkstatt.audit import set_run_id
from werkstatt.event_store import EventStore


@pytest.fixture
def store(monkeypatch, tmp_path):
    """OP-323c: JSONL-Umstellung. _flush_projection() ruft Projector() ->
    _werkstatt_home()/.werkstatt/events.db. Darum _werkstatt_home in audit
    und projection auf tmp_path patchen, damit alle Pfade konsistent sind."""
    from werkstatt import audit as _audit
    from werkstatt import projection as _proj

    monkeypatch.setattr(_audit, "_werkstatt_home", lambda: tmp_path)
    monkeypatch.setattr(_proj, "_werkstatt_home", lambda: tmp_path)

    s = EventStore(tmp_path / ".werkstatt" / "events.db")
    monkeypatch.setattr(gate_bridge, "EventStore", lambda: s)
    from werkstatt.web import app as _webapp
    monkeypatch.setattr(_webapp, "EventStore", lambda: s)
    return s


def _antworte_nach(store, run_id, gate_id, answer, delay=0.1):
    def _go():
        time.sleep(delay)
        store.append(
            run_id=run_id, kind="gate_answered",
            payload={"gate_id": gate_id, "answer": answer},
        )
    t = threading.Thread(target=_go, daemon=True)
    t.start()
    return t


def test_wait_liefert_antwort(store):
    _antworte_nach(store, "r1", "plan-abc", "j")
    assert gate_bridge.wait("r1", "plan-abc", timeout=2.0, poll_interval=0.05) == "j"


def test_wait_ignoriert_andere_gate_ids(store):
    store.append(run_id="r1", kind="gate_answered",
                 payload={"gate_id": "commit-xyz", "answer": "n"})
    _antworte_nach(store, "r1", "plan-abc", "j")
    assert gate_bridge.wait("r1", "plan-abc", timeout=2.0, poll_interval=0.05) == "j"


def test_wait_timeout_fail_closed(store):
    with pytest.raises(gate_bridge.GateTimeout):
        gate_bridge.wait("r1", "plan-abc", timeout=0.2, poll_interval=0.05)


def test_signal_open_schreibt_event(tmp_path, monkeypatch):
    """OP-323c: JSONL autoritativ + _flush_projection spiegelt nach events.db."""
    import sqlite3

    from werkstatt import audit as _A
    from werkstatt import projection as _P

    monkeypatch.setattr(_A, "_werkstatt_home", lambda: tmp_path)
    monkeypatch.setattr(_P, "_werkstatt_home", lambda: tmp_path)

    gate_bridge.signal_open("r1", "plan-abc", "Approve? [j/n/a]")

    jl = list((tmp_path / "audit-logs").glob("agent-pipeline-*.jsonl"))
    assert len(jl) == 1

    db = tmp_path / ".werkstatt" / "events.db"
    with sqlite3.connect(str(db)) as c:
        rows = c.execute(
            "SELECT payload FROM events WHERE kind='gate_open'"
        ).fetchall()
    assert len(rows) == 1
    import json
    payload = json.loads(rows[0][0])
    assert payload["gate_id"] == "plan-abc"


def test_make_gate_id_eindeutig():
    a = gate_bridge.make_gate_id("plan")
    b = gate_bridge.make_gate_id("plan")
    assert a.startswith("plan-") and b.startswith("plan-")
    assert a != b


def test_frage_gate_headless_liefert_antwort(store):
    set_run_id("r1")
    gates.set_headless(True)
    try:
        def _antworten():
            # OP-323c: 500x20ms = 10s, weil _flush_projection Zeit braucht.
            # In der Fixture laeuft audit -> JSONL -> Projector -> SQLite.
            for _i in range(500):
                opens = store.query("r1", kind="gate_open")
                if opens:
                    gid = opens[0]["payload"]["gate_id"]
                    store.append(run_id="r1", kind="gate_answered",
                                 payload={"gate_id": gid, "answer": "j"})
                    return
                time.sleep(0.02)
        t = threading.Thread(target=_antworten, daemon=True)
        t.start()
        # Timeout=10, sonst haengt der Test 300s (DEFAULT_TIMEOUT).
        assert gates._frage_gate("plan", "Approve? ", timeout=10.0) == "j"
    finally:
        gates.set_headless(False)
        set_run_id("")


def test_frage_gate_headless_ohne_run_id_wirft(store):
    set_run_id("")
    gates.set_headless(True)
    try:
        with pytest.raises(RuntimeError, match="headless"):
            gates._frage_gate("plan", "Approve? ")
    finally:
        gates.set_headless(False)


def test_frage_gate_interaktiv_nutzt_input(store, monkeypatch):
    gates.set_headless(False)
    monkeypatch.setattr("builtins.input", lambda _p: "j")
    assert gates._frage_gate("plan", "Approve? ") == "j"


def _patch_eventstore_to(tmp_path, monkeypatch):
    """OP-323c: Projector schreibt nach .werkstatt/events.db, nicht tmp_path/events.db."""
    db = tmp_path / ".werkstatt" / "events.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    # _werkstatt_home-Patch auch hier, damit audit() + flush() in tmp_path landen
    from werkstatt import audit as _audit
    from werkstatt import projection as _proj
    monkeypatch.setattr(_audit, "_werkstatt_home", lambda: tmp_path)
    monkeypatch.setattr(_proj, "_werkstatt_home", lambda: tmp_path)
    orig_init = EventStore.__init__
    def _init(self, db_pfad=None):
        orig_init(self, db_pfad or db)
    monkeypatch.setattr(EventStore, "__init__", _init)


def test_e2e_post_weckt_wait(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from werkstatt.web import auth
    from werkstatt.web.app import create_app

    monkeypatch.setattr(auth, "is_auth_disabled", lambda: True)
    _patch_eventstore_to(tmp_path, monkeypatch)

    run_id = "werkstatt-test-abc"
    client = TestClient(create_app())

    result: dict[str, str] = {}
    def _loop():
        gate_bridge.signal_open(run_id, "plan-abc", "Approve?", "jna")
        result["antwort"] = gate_bridge.wait(
            run_id, "plan-abc", timeout=5.0, poll_interval=0.05,
        )

    t = threading.Thread(target=_loop)
    t.start()
    time.sleep(0.3)
    r = client.post(f"/api/runs/{run_id}/gate",
                    json={"gate_id": "plan-abc", "answer": "j"})
    assert r.status_code == 200, r.text
    t.join(timeout=5.0)
    assert result.get("antwort") == "j"


def test_e2e_post_lehnt_unbekanntes_gate_ab(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from werkstatt.web import auth
    from werkstatt.web.app import create_app

    monkeypatch.setattr(auth, "is_auth_disabled", lambda: True)
    _patch_eventstore_to(tmp_path, monkeypatch)

    client = TestClient(create_app())
    r = client.post("/api/runs/werkstatt-test-xyz/gate",
                    json={"gate_id": "plan-unbekannt", "answer": "j"})
    assert r.status_code == 404


def test_e2e_get_gates_listet_offene(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from werkstatt.web import auth
    from werkstatt.web.app import create_app

    monkeypatch.setattr(auth, "is_auth_disabled", lambda: True)
    _patch_eventstore_to(tmp_path, monkeypatch)

    run_id = "werkstatt-test-offen"
    store = EventStore()
    store.append(run_id=run_id, kind="gate_open",
                 payload={"gate_id": "plan-aaa", "prompt": "Approve?", "optionen": "jna"})
    store.append(run_id=run_id, kind="gate_open",
                 payload={"gate_id": "commit-bbb", "prompt": "Commit?", "optionen": "jne"})
    store.append(run_id=run_id, kind="gate_answered",
                 payload={"gate_id": "plan-aaa", "answer": "j"})
    client = TestClient(create_app())
    r = client.get(f"/api/runs/{run_id}/gates")
    assert r.status_code == 200
    gids = {g["gate_id"] for g in r.json()}
    assert gids == {"commit-bbb"}
