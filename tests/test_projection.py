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

def test_schema_migration_event_id(tmp_path, monkeypatch):
    """OP-323c: Projector muss fehlende event_id-Spalte nachruesten."""
    from werkstatt import projection
    monkeypatch.setattr(projection, "_werkstatt_home", lambda: tmp_path)

    # Alte EventStore-Inits nachbilden: Tabelle OHNE event_id
    db = tmp_path / ".werkstatt" / "events.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    import sqlite3
    with sqlite3.connect(str(db)) as c:
        c.execute(
            "CREATE TABLE events ("
            "seq INTEGER PRIMARY KEY AUTOINCREMENT, "
            "run_id TEXT NOT NULL, kind TEXT NOT NULL, "
            "phase TEXT, status TEXT, payload TEXT NOT NULL, ts TEXT NOT NULL)"
        )
        c.execute("INSERT INTO events (run_id, kind, payload, ts) "
                  "VALUES ('old', 'test', '{}', 't0')")

    # Projector init sollte ALTER COLUMN machen + Rebuild funktionieren
    from werkstatt.projection import Projector
    proj = Projector()
    cols = {r[1] for r in sqlite3.connect(str(db)).execute(
        "PRAGMA table_info(events)"
    )}
    assert "event_id" in cols

    # Rebuild mit JSONL-Event
    d = tmp_path / "audit-logs"
    d.mkdir(exist_ok=True)
    import json
    (d / "semantic-2026-11-08.jsonl").write_text(
        json.dumps({"audit_id": "a1", "event_id": "e1", "run_id": "r1",
                    "kind": "loop_ended", "timestamp": "t1"}) + "\n"
    )
    r = proj.rebuild()
    assert r["eingefuegt"] == 1

def test_schema_migration_project(tmp_path):
    """OP-306c: ALTER TABLE project bei DB mit event_id (mittleres Alter).

    Bestehende Zeilen bekommen DEFAULT 'werkstatt' (ehrlich: alle
    historischen Events stammen aus Werkstatt). Zweiter Projector-Aufruf
    ist idempotent (PRAGMA-Check, kein ALTER-Fehler).
    """
    db = tmp_path / "events.db"
    with sqlite3.connect(str(db)) as c:
        c.execute(
            "CREATE TABLE events ("
            "seq INTEGER PRIMARY KEY AUTOINCREMENT, "
            "event_id TEXT, "
            "run_id TEXT NOT NULL, "
            "kind TEXT NOT NULL, "
            "phase TEXT, "
            "status TEXT, "
            "payload TEXT NOT NULL, "
            "ts TEXT NOT NULL)"
        )
        c.execute(
            "INSERT INTO events (event_id, run_id, kind, payload, ts) "
            "VALUES ('e1', 'r1', 'loop_ended', '{}', '2026-11-08T00:00:00')"
        )
        c.commit()

    from werkstatt.projection import Projector
    Projector(db_pfad=db)

    with sqlite3.connect(str(db)) as c:
        cols = {r[1] for r in c.execute("PRAGMA table_info(events)")}
        assert "project" in cols, "project-Spalte fehlt nach Migration"
        projekte = c.execute("SELECT DISTINCT project FROM events").fetchall()
        assert projekte == [("werkstatt",)], (
            f"historische Zeilen muessen 'werkstatt' haben: {projekte}"
        )
        indexes = {
            r[0] for r in c.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            )
        }
        assert "idx_events_project_seq" in indexes, (
            f"project-Index fehlt: {indexes}"
        )

    # Idempotent: zweiter Aufruf darf nicht crashen
    Projector(db_pfad=db)

