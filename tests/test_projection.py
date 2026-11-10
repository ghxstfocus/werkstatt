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

def test_insert_schreibt_project_in_spalte(tmp_path, monkeypatch):
    """OP-306c Etappe 2: _insert reicht project in Spalte durch, nicht payload.

    Zwei Events: eins mit project='test16' (JSONL-Feld), eins ohne.
    Erwartung: Spalte 1 = 'test16', Spalte 2 = Default 'werkstatt'.
    In beiden Faellen: payload enthaelt KEIN 'project'-Feld (single
    source of truth ist die Spalte).
    """
    from werkstatt import projection
    monkeypatch.setattr(projection, "_werkstatt_home", lambda: tmp_path)
    _write(tmp_path, "semantic-2026-11-08.jsonl", [
        {"audit_id": "a1", "event_id": "e1", "run_id": "r1",
         "kind": "loop_ended", "timestamp": "2026-11-08T00:00:00",
         "project": "test16"},
        {"audit_id": "a2", "event_id": "e2", "run_id": "r2",
         "kind": "loop_ended", "timestamp": "2026-11-08T00:00:01"},
    ])
    proj = _pj(tmp_path)
    proj.tail()
    with sqlite3.connect(str(tmp_path / "events.db")) as c:
        zeilen = c.execute(
            "SELECT project, payload FROM events ORDER BY seq"
        ).fetchall()
    assert len(zeilen) == 2
    assert zeilen[0][0] == "test16", (
        f"Spalte 1 soll 'test16' sein, ist {zeilen[0][0]!r}"
    )
    assert "project" not in json.loads(zeilen[0][1]), (
        "payload darf project nicht enthalten (single source of truth)"
    )
    assert zeilen[1][0] == "werkstatt", (
        f"Spalte 2 soll Default 'werkstatt' sein, ist {zeilen[1][0]!r}"
    )
    assert "project" not in json.loads(zeilen[1][1])

# ---------------------------------------------------------------------------
# OP-306c-Fix: Migrationsdateien ignorieren + fail-loud bei unbekanntem Checkpoint
# ---------------------------------------------------------------------------

def test_jsonl_files_ignoriert_migrated(tmp_path, monkeypatch):
    """migrated-*.jsonl sind statische Dumps, keine fortlaufende Quelle.

    Live-Bug 2026-11-08: Checkpoint MIGRATED-SEM-352017 stand in der
    alphabetisch letzten agent-pipeline-migrated-2026-11-08.jsonl Zeile
    33/33 — alle nachfolgenden Events wurden verworfen, Deadlock.
    """
    from werkstatt import projection
    monkeypatch.setattr(projection, "_werkstatt_home", lambda: tmp_path)
    d = tmp_path / "audit-logs"
    d.mkdir()
    (d / "agent-pipeline-2026-11-08.jsonl").write_text("")
    (d / "agent-pipeline-migrated-2026-11-08.jsonl").write_text("")
    (d / "stream-2026-11-08.jsonl").write_text("")
    (d / "stream-migrated-2026-11-08.jsonl").write_text("")
    (d / "semantic-2026-11-08.jsonl").write_text("")
    (d / "semantic-migrated-2026-11-08.jsonl").write_text("")
    p = _pj(tmp_path)
    namen = [f.name for f in p._jsonl_files()]
    assert "agent-pipeline-migrated-2026-11-08.jsonl" not in namen
    assert "stream-migrated-2026-11-08.jsonl" not in namen
    assert "semantic-migrated-2026-11-08.jsonl" not in namen
    assert "agent-pipeline-2026-11-08.jsonl" in namen
    assert "stream-2026-11-08.jsonl" in namen
    assert "semantic-2026-11-08.jsonl" in namen


def test_read_events_wirft_bei_unbekanntem_checkpoint(tmp_path, monkeypatch):
    """Fail-loud statt stumm 0 Events (verhindert Deadlock)."""
    from werkstatt import projection
    monkeypatch.setattr(projection, "_werkstatt_home", lambda: tmp_path)
    _write(tmp_path, "agent-pipeline-2026-11-08.jsonl", [
        {"audit_id": "a1", "event_id": "e1", "run_id": "r1",
         "kind": "loop_ended", "timestamp": "2026-11-08T00:00:00"},
    ])
    p = _pj(tmp_path)
    try:
        p._read_events(von_audit_id="GIBT-ES-NICHT")
    except ValueError as e:
        assert "GIBT-ES-NICHT" in str(e)
        assert "Reset in projection_state" in str(e)
    else:
        raise AssertionError("ValueError erwartet")


def test_tail_nach_reset_liest_alle_neuen_events(tmp_path, monkeypatch):
    """Checkpoint korrekt gesetzt -> tail() liest alle Events danach."""
    from werkstatt import projection
    monkeypatch.setattr(projection, "_werkstatt_home", lambda: tmp_path)
    _write(tmp_path, "agent-pipeline-2026-11-08.jsonl", [
        {"audit_id": "a1", "event_id": "e1", "run_id": "r1",
         "kind": "loop_started", "timestamp": "2026-11-08T00:00:00"},
        {"audit_id": "a2", "event_id": "e2", "run_id": "r1",
         "kind": "loop_erfolg", "timestamp": "2026-11-08T00:00:01"},
        {"audit_id": "a3", "event_id": "e3", "run_id": "r1",
         "kind": "summary", "timestamp": "2026-11-08T00:00:02"},
    ])
    p = _pj(tmp_path)
    import sqlite3 as _sq
    with _sq.connect(str(tmp_path / "events.db")) as c:
        c.execute(
            "INSERT INTO projection_state(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            ("last_audit_id", "a1"),
        )
        c.commit()
    res = p.tail()
    assert res["eingefuegt"] == 2, f"2 neue Events erwartet, {res}"
    with _sq.connect(str(tmp_path / "events.db")) as c:
        ck = c.execute(
            "SELECT value FROM projection_state WHERE key='last_audit_id'"
        ).fetchone()[0]
        n = c.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    assert ck == "a3", f"Checkpoint sollte a3 sein, ist {ck!r}"
    assert n == 2



def test_retry_duplicate_event_id_does_not_create_projection_drift(
    tmp_path, monkeypatch,
):
    from werkstatt import projection

    monkeypatch.setattr(projection, "_werkstatt_home", lambda: tmp_path)
    first = {
        "audit_id": "job-event-first",
        "event_id": "chat-job:job-1:1",
        "run_id": "run-a",
        "project": "demo",
        "kind": "chat_job_queued",
        "timestamp": "2026-11-11T12:00:00+00:00",
        "status": "queued",
        "job_id": "job-1",
        "job_event_seq": 1,
    }
    _write(tmp_path, "semantic-2026-11-11.jsonl", [first])
    proj = _pj(tmp_path)
    assert proj.tail()["eingefuegt"] == 1

    retry = {**first, "audit_id": "job-event-retry"}
    with (tmp_path / "audit-logs" / "semantic-2026-11-11.jsonl").open(
        "a", encoding="utf-8",
    ) as fh:
        fh.write(json.dumps(retry) + "\n")

    tail_retry = proj.tail()
    assert tail_retry == {"eingefuegt": 0, "uebersprungen": 1}
    status = proj.status()
    assert status["jsonl_events"] == 1
    assert status["sqlite_rows"] == 1
    assert status["diff"] == 0
    assert proj.tail() == {"eingefuegt": 0, "uebersprungen": 0}
