"""OP-323: Flush-Hook, Endpoint, Integration.

Wichtig: Der Flush-Hook ruft Projector() ohne db_pfad -> Default
(_werkstatt_home()/.werkstatt/events.db). Darum monkeypatchen wir
_werkstatt_home in BEIDEN Modulen (audit + projection) auf tmp_path.
Dann ist der Projektor-Pfad deterministisch.
"""
import sqlite3
from pathlib import Path


def _patch_home(monkeypatch, tmp_path):
    from werkstatt import audit as A
    from werkstatt import projection
    monkeypatch.setattr(A, "_werkstatt_home", lambda: tmp_path)
    monkeypatch.setattr(projection, "_werkstatt_home", lambda: tmp_path)


def _db_pfad(tmp_path):
    return tmp_path / ".werkstatt" / "events.db"


def test_flush_hook_trigger(tmp_path, monkeypatch):
    """Nach 10 audit()-Calls wird Projector.tail() gerufen."""
    from werkstatt import audit as A
    _patch_home(monkeypatch, tmp_path)
    monkeypatch.setattr(A, "_EVENT_COUNTER", 0)
    monkeypatch.setattr(A, "_FLUSH_INTERVAL", 10)

    for i in range(10):
        A.audit("loop_ended", {"i": i}, Path("."), "test")

    from werkstatt.projection import Projector
    proj = Projector()  # Default-Pfad via monkeypatch
    st = proj.status()
    
    # DEBUG
    print("\n--- DEBUG ---")
    print(f"A home: {A._werkstatt_home()}")
    from werkstatt import projection as _p
    print(f"P home: {_p._werkstatt_home()}")
    print(f"counter: {A._EVENT_COUNTER}")
    print(f"interval: {A._FLUSH_INTERVAL}")
    al = tmp_path / "audit-logs"
    print(f"audit-logs exists: {al.exists()}")
    if al.exists():
        for f in sorted(al.iterdir()):
            print(f"  {f.name} ({f.stat().st_size} B)")
    print(f"db_pfad: {proj.db_pfad}")
    print(f"db exists: {proj.db_pfad.exists()}")
    print(f"status: {st}")
    print("--- END DEBUG ---")
    
    assert st["sqlite_rows"] == 10, f"sqlite_rows={st['sqlite_rows']}"


def test_flush_nicht_bei_9(tmp_path, monkeypatch):
    from werkstatt import audit as A
    _patch_home(monkeypatch, tmp_path)
    monkeypatch.setattr(A, "_EVENT_COUNTER", 0)
    monkeypatch.setattr(A, "_FLUSH_INTERVAL", 10)

    for i in range(9):
        A.audit("loop_ended", {"i": i}, Path("."), "test")

    from werkstatt.projection import Projector
    assert Projector().status()["sqlite_rows"] == 0


def test_status_endpoint_vorhanden():
    """Endpoint registriert."""
    from werkstatt.web import app as web_app
    routes = [r.path for r in web_app.app.routes if hasattr(r, "path")]
    assert "/api/projects/{name}/projection/status" in routes


def test_stream_write_landet_in_sqlite(tmp_path, monkeypatch):
    """stream() + Flush -> SQLite hat den stream-Kind."""
    from werkstatt import audit as A
    _patch_home(monkeypatch, tmp_path)
    monkeypatch.setattr(A, "_EVENT_COUNTER", 0)
    monkeypatch.setattr(A, "_FLUSH_INTERVAL", 5)

    for i in range(5):
        A.stream("log_line", {"i": i}, Path("."), "test")

    with sqlite3.connect(str(_db_pfad(tmp_path))) as c:
        rows = c.execute("SELECT kind FROM events").fetchall()
    assert len(rows) == 5, f"rows={len(rows)}"
    assert all(r[0] == "log_line" for r in rows)
