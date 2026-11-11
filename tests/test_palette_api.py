"""OP-302: aggregate_palette + /palette-Endpoint."""


def test_palette_leer_liefert_aktionen(tmp_path, monkeypatch):
    """Bei leerem q: Aktionen als Hint."""
    from werkstatt.web import inspector as _insp
    monkeypatch.setattr(_insp, "parse_ops", lambda *a, **k: [])
    aus = _insp.aggregate_palette("werkstatt", "")
    assert len(aus["actions"]) > 0
    titel = [a["titel"] for a in aus["actions"]]
    assert any("Loop" in t for t in titel)


def test_palette_op_treffer(tmp_path, monkeypatch):
    from werkstatt.web import inspector as _insp
    monkeypatch.setattr(_insp, "parse_ops", lambda *a, **k: [
        {"id": "OP-303", "titel": "Loop-Start-Button", "status": "open",
         "blockiert_von": ""},
        {"id": "OP-304", "titel": "Shortcut Help", "status": "open",
         "blockiert_von": ""},
    ])
    aus = _insp.aggregate_palette("werkstatt", "loop")
    titel = [o["titel"] for o in aus["ops"]]
    assert any("Loop-Start" in t for t in titel)
    # OP-304 soll nicht matchen (Shortcut Help)
    assert not any("Shortcut" in t for t in titel)


def test_palette_filter_leerzeichen_egal(tmp_path, monkeypatch):
    from werkstatt.web import inspector as _insp
    monkeypatch.setattr(_insp, "parse_ops", lambda *a, **k: [
        {"id": "OP-303", "titel": "Loop-Start-Button", "status": "open",
         "blockiert_von": "OP-301"},
    ])
    aus = _insp.aggregate_palette("werkstatt", "  LOOP  ")
    assert len(aus["ops"]) == 1


def test_palette_endpoint_registriert():
    from werkstatt.web import app as web_app
    routes = [r.path for r in web_app.app.routes if hasattr(r, "path")]
    assert "/api/projects/{name}/palette" in routes

def test_palette_run_suche_bleibt_projektisoliert(tmp_path, monkeypatch):
    from werkstatt.event_store import EventStore
    from werkstatt.web import inspector as _insp

    es = EventStore(db_pfad=tmp_path / "events.db")
    monkeypatch.setattr(_insp, "EventStore", lambda: es)
    es.append("shared-demo", "loop_started", payload={}, project="demo")
    es.append("shared-foreign", "loop_started", payload={}, project="anderes-projekt")

    aus = _insp.aggregate_palette("demo", "shared")
    run_ids = [item["titel"] for item in aus["runs"]]
    assert run_ids == ["shared-demo"]
