"""OP-303 Backend: parse_ops.blockiert_von + aggregate_ops_run_status."""
import json
import sqlite3
from datetime import UTC, datetime, timedelta


def _store(tmp_path, monkeypatch):
    db = tmp_path / ".werkstatt" / "events.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    from werkstatt.event_store import EventStore
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
            "INSERT INTO events "
            "(run_id, kind, phase, status, payload, ts, origin_verified) "
            "VALUES (?, ?, ?, ?, ?, ?, 1)",
            (run_id, kind, None, None,
             json.dumps(payload or {}, ensure_ascii=False), ts),
        )
        c.commit()


def test_parse_ops_blockiert_von(tmp_path):
    """OP mit 'Blockiert von: OP-XXX' -> blockiert_von enthaelt OP-XXX."""
    from werkstatt.web.inspector import parse_ops
    doc = tmp_path / "docs"
    doc.mkdir()
    (doc / "STATUS.md").write_text(
        "### OP-100: Test eins\n- **Status:** open\n- **Blockiert von:** OP-050, OP-051\n\n"
        "### OP-101: Test zwei\n- **Status:** open\n- **Blockiert von:** —\n",
        encoding="utf-8",
    )
    ops = parse_ops(tmp_path)
    ids = {o["id"]: o for o in ops}
    assert "OP-100" in ids
    assert "OP-050" in ids["OP-100"]["blockiert_von"]
    assert "OP-051" in ids["OP-100"]["blockiert_von"]
    assert ids["OP-101"]["blockiert_von"] == ""


def test_run_status_leer(tmp_path, monkeypatch):
    _s, _db = _store(tmp_path, monkeypatch)
    from werkstatt.web.inspector import aggregate_ops_run_status
    aus = aggregate_ops_run_status("werkstatt")
    assert aus == {}


def test_run_status_done(tmp_path, monkeypatch):
    _s, db = _store(tmp_path, monkeypatch)
    alt = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
    _event(db, "r1", "loop_started", {"op_id": "OP-303", "aufgabe_kurz": "x"}, ts=alt)
    _event(db, "r1", "loop_erfolg", {}, ts=alt)
    from werkstatt.web.inspector import aggregate_ops_run_status
    aus = aggregate_ops_run_status("werkstatt")
    assert "OP-303" in aus
    assert aus["OP-303"]["state"] == "done"
    assert aus["OP-303"]["run_id"] == "r1"


def test_run_status_kennzeichnet_historischen_erfolg_unverifiziert(
    tmp_path, monkeypatch,
):
    _s, db = _store(tmp_path, monkeypatch)
    alt = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
    _event(db, "r1", "loop_started", {"op_id": "OP-LEGACY"}, ts=alt)
    _event(db, "r1", "loop_erfolg", {}, ts=alt)
    with sqlite3.connect(str(db)) as conn:
        conn.execute(
            "UPDATE events SET origin_verified=0 WHERE run_id='r1'"
        )

    from werkstatt.web.inspector import aggregate_ops_run_status

    status = aggregate_ops_run_status("werkstatt")["OP-LEGACY"]
    assert status["state"] == "unverified"
    assert status["unverified"] is True


def test_run_status_failed(tmp_path, monkeypatch):
    _s, db = _store(tmp_path, monkeypatch)
    alt = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
    _event(db, "r1", "loop_started", {"op_id": "OP-304"}, ts=alt)
    _event(db, "r1", "loop_failed", {}, ts=alt)
    from werkstatt.web.inspector import aggregate_ops_run_status
    aus = aggregate_ops_run_status("werkstatt")
    assert aus["OP-304"]["state"] == "failed"


def test_run_status_running_via_heartbeat(tmp_path, monkeypatch):
    _s, db = _store(tmp_path, monkeypatch)
    _event(db, "r1", "loop_started", {"op_id": "OP-305"}, ts=datetime.now(UTC).isoformat())
    _event(db, "r1", "heartbeat", {})
    from werkstatt.web.inspector import aggregate_ops_run_status
    aus = aggregate_ops_run_status("werkstatt")
    assert aus["OP-305"]["state"] == "running"


def test_endpoint_registriert():
    from werkstatt.web import app as web_app
    routes = [r.path for r in web_app.app.routes if hasattr(r, "path")]
    assert "/api/projects/{name}/ops/run-status" in routes


def test_run_status_legacy_pipeline_start(tmp_path, monkeypatch):
    """OP-303: Legacy-Runs ohne loop_started nutzen pipeline_start-Fallback."""
    _s, db = _store(tmp_path, monkeypatch)
    alt = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
    _event(db, "r1", "pipeline_start", {"op_id": "OP-OLD"}, ts=alt)
    _event(db, "r1", "loop_erfolg", {}, ts=alt)
    from werkstatt.web.inspector import aggregate_ops_run_status
    aus = aggregate_ops_run_status("werkstatt")
    assert "OP-OLD" in aus
    assert aus["OP-OLD"]["state"] == "done"


def test_parse_ops_projekt_spezifisch(tmp_path):
    """OP-305: parse_ops(projekt_dir) liest aus dem uebergebenen Verzeichnis."""
    from werkstatt.web.inspector import parse_ops
    # Projekt A mit OP-100
    a = tmp_path / "projekt-a" / "docs"
    a.mkdir(parents=True)
    (a / "STATUS.md").write_text(
        "### OP-100: A-Projekt-OP\n- **Status:** open\n- **Blockiert von:** —\n",
        encoding="utf-8",
    )
    # Projekt B mit OP-200
    b = tmp_path / "projekt-b" / "docs"
    b.mkdir(parents=True)
    (b / "STATUS.md").write_text(
        "### OP-200: B-Projekt-OP\n- **Status:** open\n- **Blockiert von:** —\n",
        encoding="utf-8",
    )

    ops_a = parse_ops(tmp_path / "projekt-a")
    ops_b = parse_ops(tmp_path / "projekt-b")

    ids_a = {o["id"] for o in ops_a}
    ids_b = {o["id"] for o in ops_b}
    assert "OP-100" in ids_a
    assert "OP-200" not in ids_a
    assert "OP-200" in ids_b
    assert "OP-100" not in ids_b


def test_start_validierung_ohne_status_md(tmp_path, monkeypatch):
    """OP-305: /start lehnt Projekt ohne docs/STATUS.md ab."""
    from fastapi.testclient import TestClient

    from werkstatt.web import app as app_modul
    from werkstatt.web import auth

    # Auth deaktivieren (offizielle API)
    monkeypatch.setattr(auth, "_AUTH_DISABLED", True)
    # _PROJECTS_BASE auf tmp_path, damit /opt/ leer bleibt
    monkeypatch.setattr(app_modul, "_PROJECTS_BASE", tmp_path)

    client = TestClient(app_modul.create_app())
    # Projektname valide, aber kein <tmp_path>/<name>/docs/STATUS.md
    r = client.post("/api/projects/zzz-nicht-existent/start", json={})
    assert r.status_code == 404, r.text
    assert "STATUS.md" in r.text or "docs" in r.text
