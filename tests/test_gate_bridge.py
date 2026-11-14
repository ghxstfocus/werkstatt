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


def test_signal_open_schreibt_korrektes_projekt(store):
    gate_bridge.signal_open(
        "run-shared", "plan-project", "Approve?", project="projekt-a",
    )

    events = store.query(
        "run-shared", kind="gate_open", project="projekt-a",
    )
    assert len(events) == 1
    assert events[0]["payload"]["gate_id"] == "plan-project"
    assert store.query(
        "run-shared", kind="gate_open", project="werkstatt",
    ) == []


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


# =====================================================================
# OP-381c Etappe 1: Backend typ-Feld (jna | freitext)
# =====================================================================


def test_signal_open_setzt_typ_default_jna(store):
    """signal_open ohne typ -> Payload-Feld typ='jna' (rueckwaertskompatibel)."""
    gate_bridge.signal_open("r1", "plan-abc", "Approve?")
    evs = store.query("r1", kind="gate_open")
    assert len(evs) == 1
    pa = evs[0].get("payload") or {}
    assert pa.get("typ") == "jna", (
        f"AK n: Default-typ MUSS 'jna' sein, war {pa.get('typ')!r}"
    )


def test_signal_open_setzt_typ_freitext(store):
    """signal_open mit typ='freitext' -> Payload-Feld typ='freitext'."""
    gate_bridge.signal_open("r1", "plan-abc", "Reject-Grund?", typ="freitext")
    evs = store.query("r1", kind="gate_open")
    assert len(evs) == 1
    pa = evs[0].get("payload") or {}
    assert pa.get("typ") == "freitext", (
        f"AK l: signal_open muss typ durchreichen, war {pa.get('typ')!r}"
    )


def test_frage_gate_plan_reason_setzt_typ_freitext(store, monkeypatch):
    """_frage_gate('plan_reason') -> signal_open bekommt typ='freitext'.

    Regress-Barriere (AK m): bei Entfernen der Ableitung in _frage_gate
    landet typ='jna' im Payload und der Test wird rot.
    """
    aufrufe: list[dict] = []

    def _fake_signal(run_id, gate_id, prompt, optionen="jna", typ="jna", project="werkstatt"):
        aufrufe.append({"typ": typ, "project": project})
        # sofort antworten, damit wait() nicht blockiert
        store.append(
            run_id=run_id, kind="gate_answered",
            payload={"gate_id": gate_id, "answer": "zu kaputt"},
        )

    monkeypatch.setattr(gate_bridge, "signal_open", _fake_signal)
    set_run_id("test-run-plan-reason")
    monkeypatch.setattr(gates, "_HEADLESS", True)
    try:
        antwort = gates._frage_gate("plan_reason", "Reject-Grund?")
    finally:
        set_run_id("")

    assert antwort == "zu kaputt"
    assert len(aufrufe) == 1
    assert aufrufe[0]["typ"] == "freitext", (
        f"AK m: plan_reason MUSS typ='freitext' bekommen, "
        f"war {aufrufe[0]['typ']!r}"
    )
    assert aufrufe[0]["project"] == "werkstatt"


def test_frage_gate_bindet_open_und_answer_an_projekt(store, monkeypatch):
    run_id = "shared-gate-run"
    monkeypatch.setattr("werkstatt.audit.get_run_id", lambda: run_id)
    monkeypatch.setattr(gates, "_HEADLESS", True)
    projects = []

    def signal(run, gate, _prompt, _options="jna", typ="jna", project="werkstatt"):
        projects.append(project)
        store.append(
            run_id=run, kind="gate_answered",
            payload={"gate_id": gate, "answer": "j"}, project=project,
        )

    monkeypatch.setattr(gate_bridge, "signal_open", signal)
    try:
        assert gates._frage_gate(
            "plan", "Approve?", project_name="projekt-a",
        ) == "j"
    finally:
        monkeypatch.setattr(gates, "_HEADLESS", False)

    assert projects == ["projekt-a"]


def test_gate_bridge_wait_isoliert_antworten_nach_projekt(store):
    store.append(
        run_id="shared-run", kind="gate_answered",
        payload={"gate_id": "plan-1", "answer": "n"}, project="projekt-a",
    )
    store.append(
        run_id="shared-run", kind="gate_answered",
        payload={"gate_id": "plan-1", "answer": "j"}, project="projekt-b",
    )

    assert gate_bridge._finde_antwort(
        store, "shared-run", "plan-1", "projekt-a",
    ) == "n"
    assert gate_bridge._finde_antwort(
        store, "shared-run", "plan-1", "projekt-b",
    ) == "j"


def test_frage_gate_timeout_bleibt_dem_projekt_zugeordnet(store, monkeypatch):
    from werkstatt import event_store
    from werkstatt.state import RunState

    run_id = "demo-timeout-run"
    set_run_id(run_id)
    monkeypatch.setattr(gates, "_HEADLESS", True)
    monkeypatch.setattr(gate_bridge, "signal_open", lambda *_a, **_kw: None)
    monkeypatch.setattr(gate_bridge, "_flush_projection", lambda: None)
    monkeypatch.setattr(
        gate_bridge, "wait",
        lambda *_a, **_kw: (_ for _ in ()).throw(gate_bridge.GateTimeout()),
    )
    monkeypatch.setattr(event_store, "EventStore", lambda: store)
    state = RunState(project_name="demo")
    try:
        assert gates._frage_gate(
            "plan", "Approve?", project_name="demo", state=state,
        ) == "n"
    finally:
        set_run_id("")

    assert state.gate_timed_out is True
    events = store.query(run_id, kind="loop_gate_timeout", project="demo")
    assert len(events) == 1


def test_expire_for_run_ist_auf_projekt_begrenzt(store, monkeypatch):
    from werkstatt import audit

    store.append(
        run_id="shared-run", kind="gate_open",
        payload={"gate_id": "plan-1"}, project="projekt-a",
    )
    store.append(
        run_id="shared-run", kind="gate_open",
        payload={"gate_id": "plan-1"}, project="projekt-b",
    )
    expired_projects = []
    monkeypatch.setattr(
        audit, "audit",
        lambda _kind, payload, _path, project: expired_projects.append(
            (project, payload["gate_id"]),
        ),
    )

    assert gate_bridge.expire_for_run(
        "shared-run", project="projekt-a",
    ) == 1
    assert expired_projects == [("projekt-a", "plan-1")]
