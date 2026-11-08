"""OP-306c: Projekt-Isolation in aggregate_*-Funktionen.

Verhaltens-Specs: "Wenn ich aggregate_X fuer Projekt A aufrufe,
sehe ich NUR A's Events, nicht die von Projekt B." Die Tests bauen
die DB ueber Projector auf (9 Spalten, inkl. project) und pruefen
das User-sichtbare Verhalten.

Bestehende Tests (test_ambient_aggregation.py etc.) bleiben gruen,
weil dortige _event()-Helper ohne project-Spalte INSERTen und
DEFAULT 'werkstatt' greift.
"""
import json
import sqlite3
from datetime import UTC, datetime

from werkstatt.event_store import EventStore
from werkstatt.projection import Projector


def _store(tmp_path, monkeypatch):
    """DB mit 9-Spalten-Schema (project, event_id) + EventStore-Mock."""
    db = tmp_path / ".werkstatt" / "events.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    Projector(db_pfad=db)  # legt 9 Spalten an
    s = EventStore(db)     # IF NOT EXISTS, aendert nichts
    from werkstatt.web import inspector as _insp
    monkeypatch.setattr(_insp, "EventStore", lambda: s)
    return s, db


def _event(db, run_id, kind, payload=None, ts=None, project="werkstatt"):
    if ts is None:
        ts = datetime.now(UTC).isoformat()
    with sqlite3.connect(str(db)) as c:
        c.execute(
            "INSERT INTO events "
            "(run_id, kind, phase, status, payload, ts, project) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (run_id, kind, None, None,
             json.dumps(payload or {}, ensure_ascii=False), ts, project),
        )
        c.commit()


def test_letzter_run_id_filtert_projekt(tmp_path, monkeypatch):
    _s, db = _store(tmp_path, monkeypatch)
    _event(db, "run-a", "loop_ended", project="a")
    _event(db, "run-b", "loop_ended", project="b")
    from werkstatt.web.inspector import _letzter_run_id
    assert _letzter_run_id(_s, "a") == "run-a"
    assert _letzter_run_id(_s, "b") == "run-b"


def test_aggregate_status_filtert_projekt(tmp_path, monkeypatch):
    _s, db = _store(tmp_path, monkeypatch)
    _event(db, "run-a", "task_started", project="a")
    _event(db, "run-a", "task_done", project="a")
    _event(db, "run-b", "task_started", project="b")
    from werkstatt.web.inspector import aggregate_status
    a = aggregate_status("a")
    b = aggregate_status("b")
    assert a["run_id"] == "run-a"
    assert a["tasks"] == {"started": 1, "done": 1}
    assert b["run_id"] == "run-b"
    assert b["tasks"] == {"started": 1, "done": 0}


def test_aggregate_tokens_filtert_projekt(tmp_path, monkeypatch):
    _s, db = _store(tmp_path, monkeypatch)
    _event(db, "run-a", "llm_usage", {
        "prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30,
    }, project="a")
    _event(db, "run-b", "llm_usage", {
        "prompt_tokens": 100, "completion_tokens": 200, "total_tokens": 300,
    }, project="b")
    from werkstatt.web.inspector import aggregate_tokens
    a = aggregate_tokens("a")
    b = aggregate_tokens("b")
    assert a["loop"]["total"] == 30
    assert b["loop"]["total"] == 300


def test_aggregate_ops_run_status_filtert_projekt(tmp_path, monkeypatch):
    _s, db = _store(tmp_path, monkeypatch)
    _event(db, "run-a", "loop_started", {"op_id": "OP-A"}, project="a")
    _event(db, "run-b", "loop_started", {"op_id": "OP-B"}, project="b")
    from werkstatt.web.inspector import aggregate_ops_run_status
    a = aggregate_ops_run_status("a")
    b = aggregate_ops_run_status("b")
    assert "OP-A" in a and "OP-B" not in a
    assert "OP-B" in b and "OP-A" not in b


def test_leeres_fremdprojekt_liefert_idle(tmp_path, monkeypatch):
    _s, db = _store(tmp_path, monkeypatch)
    _event(db, "run-a", "task_started", project="a")
    _event(db, "run-a", "loop_erfolg", project="a")
    from werkstatt.web.inspector import aggregate_ambient, aggregate_status
    st = aggregate_status("test16")
    assert st["run_id"] is None
    assert st["tasks"] == {"started": 0, "done": 0}
    am = aggregate_ambient("test16")
    assert am["loop_status"] == "idle"
    assert am["last_run"] is None


def test_default_ohne_projekt_arg_ist_werkstatt(tmp_path, monkeypatch):
    _s, db = _store(tmp_path, monkeypatch)
    _event(db, "run-w", "loop_ended", project="werkstatt")
    _event(db, "run-x", "loop_ended", project="other")
    from werkstatt.web.inspector import _letzter_run_id
    assert _letzter_run_id(_s) == _letzter_run_id(_s, "werkstatt")
    assert _letzter_run_id(_s) == "run-w"
