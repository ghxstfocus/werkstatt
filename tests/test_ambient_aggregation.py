"""OP-301: aggregate_ambient() + /ambient-Endpoint."""
import json
import sqlite3
from datetime import UTC, datetime, timedelta

from werkstatt.event_store import EventStore


def _store(tmp_path, monkeypatch):
    db = tmp_path / ".werkstatt" / "events.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    from werkstatt.projection import Projector
    Projector(db_pfad=db)  # OP-306c: 9-Spalten-Schema (project)
    s = EventStore(db)
    from werkstatt.web import inspector as _insp
    monkeypatch.setattr(_insp, "EventStore", lambda: s)
    return s, db


def _event(db, run_id, kind, payload=None, ts=None):
    if ts is None:
        ts = datetime.now(UTC).isoformat()
    with sqlite3.connect(str(db)) as c:
        c.execute(
            "INSERT INTO events (run_id, kind, phase, status, payload, ts) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (run_id, kind, None, None,
             json.dumps(payload or {}, ensure_ascii=False), ts),
        )
        c.commit()


def test_ambient_leer(tmp_path, monkeypatch):
    _s, _ = _store(tmp_path, monkeypatch)
    from werkstatt.web.inspector import aggregate_ambient
    aus = aggregate_ambient("werkstatt")
    assert aus["loop_status"] == "idle"
    assert aus["last_run"] is None
    assert aus["tokens"] == {"loop_total": 0, "chat_total": 0}
    assert aus["gates_open"] == 0


def test_ambient_running_via_heartbeat(tmp_path, monkeypatch):
    _s, db = _store(tmp_path, monkeypatch)
    _event(db, "r1", "heartbeat", {})
    from werkstatt.web.inspector import aggregate_ambient
    aus = aggregate_ambient("werkstatt")
    assert aus["loop_status"] == "running"


def test_ambient_done_via_loop_erfolg(tmp_path, monkeypatch):
    """OP-301: loop_erfolg.payload ohne erfolg-Feld -> semantisch done."""
    _s, db = _store(tmp_path, monkeypatch)
    alt = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
    _event(db, "r1", "heartbeat", {}, ts=alt)
    _event(db, "r1", "loop_erfolg", {"project_name": "werkstatt"}, ts=alt)
    from werkstatt.web.inspector import aggregate_ambient
    aus = aggregate_ambient("werkstatt")
    assert aus["loop_status"] == "done"
    assert aus["last_run"]["run_id"] == "r1"
    assert aus["last_run"]["erfolg"] is True


def test_ambient_failed_via_loop_failed(tmp_path, monkeypatch):
    """OP-301: loop_failed-Event -> status failed."""
    _s, db = _store(tmp_path, monkeypatch)
    alt = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
    _event(db, "r1", "loop_failed", {}, ts=alt)
    from werkstatt.web.inspector import aggregate_ambient
    aus = aggregate_ambient("werkstatt")
    assert aus["loop_status"] == "failed"
    assert aus["last_run"]["erfolg"] is False


def test_ambient_gates_distinct(tmp_path, monkeypatch):
    _s, db = _store(tmp_path, monkeypatch)
    # 2 offene Gates, eins beantwortet, eins expired -> 0 offen
    _event(db, "r1", "gate_open", {"gate_id": "g1"})
    _event(db, "r1", "gate_open", {"gate_id": "g1"})  # Duplikat
    _event(db, "r1", "gate_open", {"gate_id": "g2"})
    _event(db, "r1", "gate_answered", {"gate_id": "g1"})
    _event(db, "r1", "gate_expired", {"gate_id": "g2"})
    from werkstatt.web.inspector import aggregate_ambient
    aus = aggregate_ambient("werkstatt")
    assert aus["gates_open"] == 0


def test_ambient_gates_ein_offen(tmp_path, monkeypatch):
    _s, db = _store(tmp_path, monkeypatch)
    _event(db, "r1", "gate_open", {"gate_id": "g1"})
    _event(db, "r1", "gate_open", {"gate_id": "g2"})
    _event(db, "r1", "gate_answered", {"gate_id": "g1"})
    from werkstatt.web.inspector import aggregate_ambient
    aus = aggregate_ambient("werkstatt")
    assert aus["gates_open"] == 1


def test_endpoint_registriert():
    from werkstatt.web import app as web_app
    routes = [r.path for r in web_app.app.routes if hasattr(r, "path")]
    assert "/api/projects/{name}/ambient" in routes

def test_ambient_letztes_terminal_gewinnt(tmp_path, monkeypatch):
    """OP-371: Neuestes Terminal-Event entscheidet, nicht loop_erfolg-Prioritaet.

    Live-Bug 2026-11-08 22:10: ambient('werkstatt') zeigte 'done'
    (loop_erfolg 01:26), obwohl um 19:41 loop_failed das letzte
    Terminal-Event war. Nach Fix: 'failed'.
    """
    from werkstatt.web.inspector import aggregate_ambient
    _s, db = _store(tmp_path, monkeypatch)
    alt = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
    _event(db, "r-old", "loop_erfolg", {}, ts=alt)
    _event(db, "r-new", "loop_failed", {}, ts=datetime.now(UTC).isoformat())
    aus = aggregate_ambient("werkstatt")
    assert aus["loop_status"] == "failed"
    assert aus["last_run"]["run_id"] == "r-new"
    assert aus["last_run"]["erfolg"] is False


def test_ambient_letzter_erfolg_gewinnt_wenn_neuer(tmp_path, monkeypatch):
    """OP-371: Auch umgekehrt — loop_erfolg nach loop_failed -> done."""
    from werkstatt.web.inspector import aggregate_ambient
    _s, db = _store(tmp_path, monkeypatch)
    alt = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
    _event(db, "r-old", "loop_failed", {}, ts=alt)
    _event(db, "r-new", "loop_erfolg", {}, ts=datetime.now(UTC).isoformat())
    aus = aggregate_ambient("werkstatt")
    assert aus["loop_status"] == "done"
    assert aus["last_run"]["run_id"] == "r-new"
    assert aus["last_run"]["erfolg"] is True

def test_ambient_terminal_event_ohne_run_id_ignoriert(tmp_path, monkeypatch):
    """Terminal-Event mit leerer run_id darf nicht als 'letzter Run' zaehlen.

    Pre-OP-303-Aera (Loop-Bug): loop_erfolg wurde geschrieben, aber
    set_run_id() nicht aufgerufen. Diese Events sind ehrlich: kein
    zuordenbarer Run. aggregate_ambient muss sie ignorieren statt
    last_run={run_id: ''} zu zeigen.
    """
    from werkstatt.web.inspector import aggregate_ambient
    _s, db = _store(tmp_path, monkeypatch)
    # Terminal-Event mit leerer run_id (pre-OP-303)
    _event(db, "", "loop_erfolg", {}, ts=datetime.now(UTC).isoformat())
    aus = aggregate_ambient("werkstatt")
    assert aus["loop_status"] == "idle"
    assert aus["last_run"] is None

