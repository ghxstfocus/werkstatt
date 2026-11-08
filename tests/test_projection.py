"""OP-322: Projektor rebuild/tail/status (deterministisch, idempotent)."""
import hashlib
import json
import sqlite3


def _pj(tmp_path):
    from werkstatt.projection import Projector
    return Projector(db_pfad=tmp_path / "events.db")


def _write(tmp_path, name, events):
    d = tmp_path / "audit-logs"
    d.mkdir(exist_ok=True)
    with (d / name).open("w") as fh:
        for ev in events:
            fh.write(json.dumps(ev) + "\n")


def _hash(db):
    with sqlite3.connect(str(db)) as c:
        rows = c.execute(
            "SELECT event_id, run_id, kind, ts FROM events ORDER BY event_id"
        ).fetchall()
    h = hashlib.sha256()
    for r in rows:
        h.update(str(r).encode())
    return h.hexdigest()


def test_rebuild_deterministisch(tmp_path, monkeypatch):
    from werkstatt import projection
    monkeypatch.setattr(projection, "_werkstatt_home", lambda: tmp_path)
    _write(tmp_path, "semantic-2026-11-08.jsonl", [
        {"audit_id": "a1", "event_id": "e1", "run_id": "r1",
         "kind": "loop_ended", "timestamp": "2026-11-08T00:00:00"},
        {"audit_id": "a2", "event_id": "e2", "run_id": "r1",
         "kind": "loop_erfolg", "timestamp": "2026-11-08T00:00:01"},
    ])
    proj = _pj(tmp_path)
    r1 = proj.rebuild()
    h1 = _hash(tmp_path / "events.db")
    r2 = proj.rebuild()
    h2 = _hash(tmp_path / "events.db")
    assert r1["eingefuegt"] == 2
    assert r2["eingefuegt"] == 2
    assert h1 == h2


def test_tail_idempotent(tmp_path, monkeypatch):
    from werkstatt import projection
    monkeypatch.setattr(projection, "_werkstatt_home", lambda: tmp_path)
    _write(tmp_path, "semantic-2026-11-08.jsonl", [
        {"audit_id": "a1", "event_id": "e1", "run_id": "r1",
         "kind": "loop_ended", "timestamp": "t1"},
    ])
    proj = _pj(tmp_path)
    r1 = proj.tail()
    r2 = proj.tail()
    assert r1["eingefuegt"] == 1
    assert r2["eingefuegt"] == 0


def test_tail_inkrementell(tmp_path, monkeypatch):
    from werkstatt import projection
    monkeypatch.setattr(projection, "_werkstatt_home", lambda: tmp_path)
    _write(tmp_path, "semantic-2026-11-08.jsonl", [
        {"audit_id": "a1", "event_id": "e1", "run_id": "r1",
         "kind": "loop_ended", "timestamp": "t1"},
    ])
    proj = _pj(tmp_path)
    proj.tail()
    _write(tmp_path, "semantic-2026-11-09.jsonl", [
        {"audit_id": "a2", "event_id": "e2", "run_id": "r2",
         "kind": "loop_erfolg", "timestamp": "t2"},
    ])
    r = proj.tail()
    assert r["eingefuegt"] == 1


def test_status_divergenz(tmp_path, monkeypatch):
    from werkstatt import projection
    monkeypatch.setattr(projection, "_werkstatt_home", lambda: tmp_path)
    _write(tmp_path, "semantic-2026-11-08.jsonl", [
        {"audit_id": "a1", "event_id": "e1", "run_id": "r1",
         "kind": "loop_ended", "timestamp": "t1"},
        {"audit_id": "a2", "event_id": "e2", "run_id": "r1",
         "kind": "loop_erfolg", "timestamp": "t2"},
    ])
    proj = _pj(tmp_path)
    s0 = proj.status()
    assert s0["jsonl_events"] == 2
    assert s0["sqlite_rows"] == 0
    assert s0["diff"] == 2
    proj.rebuild()
    s1 = proj.status()
    assert s1["diff"] == 0


def test_event_id_fallback(tmp_path, monkeypatch):
    from werkstatt import projection
    monkeypatch.setattr(projection, "_werkstatt_home", lambda: tmp_path)
    _write(tmp_path, "semantic-2026-11-08.jsonl", [
        {"audit_id": "aid-x", "run_id": "r1",
         "kind": "loop_ended", "timestamp": "t1"},
    ])
    proj = _pj(tmp_path)
    proj.rebuild()
    with sqlite3.connect(str(tmp_path / "events.db")) as c:
        rows = c.execute("SELECT event_id FROM events").fetchall()
    assert len(rows) == 1
    assert rows[0][0] is not None
    assert len(rows[0][0]) == 16


def test_stream_und_semantic_beide(tmp_path, monkeypatch):
    from werkstatt import projection
    monkeypatch.setattr(projection, "_werkstatt_home", lambda: tmp_path)
    _write(tmp_path, "semantic-2026-11-08.jsonl", [
        {"audit_id": "a1", "event_id": "e1", "run_id": "r1",
         "kind": "loop_ended", "timestamp": "t1"},
    ])
    _write(tmp_path, "stream-2026-11-08.jsonl", [
        {"audit_id": "s1", "event_id": "se1", "run_id": "r1",
         "kind": "log_line", "timestamp": "t2"},
    ])
    proj = _pj(tmp_path)
    r = proj.rebuild()
    assert r["eingefuegt"] == 2
