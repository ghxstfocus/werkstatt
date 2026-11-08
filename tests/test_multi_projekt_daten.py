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

# ---------------------------------------------------------------------------
# OP-306c Etappe 3b: aggregate_ambient filtert heartbeat/loop_*/gates
# ---------------------------------------------------------------------------

def test_aggregate_ambient_filtert_projekt_heartbeat(tmp_path, monkeypatch):
    _s, db = _store(tmp_path, monkeypatch)
    jetzt = datetime.now(UTC).isoformat()
    _event(db, "run-a", "heartbeat", {}, ts=jetzt, project="a")
    _event(db, "run-b", "heartbeat", {}, ts=jetzt, project="b")
    from werkstatt.web.inspector import aggregate_ambient
    assert aggregate_ambient("a")["loop_status"] == "running"
    assert aggregate_ambient("b")["loop_status"] == "running"
    assert aggregate_ambient("test16")["loop_status"] == "idle"


def test_aggregate_ambient_filtert_projekt_loop_erfolg(tmp_path, monkeypatch):
    _s, db = _store(tmp_path, monkeypatch)
    _event(db, "run-a", "loop_erfolg", {}, project="a")
    from werkstatt.web.inspector import aggregate_ambient
    assert aggregate_ambient("a")["loop_status"] == "done"
    assert aggregate_ambient("b")["loop_status"] == "idle"


def test_aggregate_ambient_filtert_projekt_gates(tmp_path, monkeypatch):
    _s, db = _store(tmp_path, monkeypatch)
    _event(db, "run-a", "gate_open", {"gate_id": "ga"}, project="a")
    _event(db, "run-b", "gate_open", {"gate_id": "gb"}, project="b")
    from werkstatt.web.inspector import aggregate_ambient
    assert aggregate_ambient("a")["gates_open"] == 1
    assert aggregate_ambient("b")["gates_open"] == 1
    assert aggregate_ambient("test16")["gates_open"] == 0


def test_aggregate_timeline_filtert_projekt(tmp_path, monkeypatch):
    """JSONL mit 2 Projekten, je Phase + Kind. timeline('a') sieht nur a.

    Kind-Events sind Pflicht: leere Phasen ohne Kinder werden vom
    Aggregator rausgefiltert (0 Kinder + <2s Dauer).
    """
    from werkstatt.web import inspector as _insp
    monkeypatch.setattr(_insp, "werkstatt_home", lambda: tmp_path)
    al = tmp_path / "audit-logs"
    al.mkdir()
    events = [
        {"run_id": "run-a", "kind": "loop_phase", "project": "a",
         "ts": "2026-11-08T00:00:00", "payload": {"phase": "explorer"}},
        {"run_id": "run-a", "kind": "task_started", "project": "a",
         "ts": "2026-11-08T00:00:01", "payload": {"task_id": "t1"}},
        {"run_id": "run-b", "kind": "loop_phase", "project": "b",
         "ts": "2026-11-08T00:00:02", "payload": {"phase": "builder"}},
        {"run_id": "run-b", "kind": "task_started", "project": "b",
         "ts": "2026-11-08T00:00:03", "payload": {"task_id": "t2"}},
    ]
    with (al / "agent-pipeline-2026-11-08.jsonl").open("w") as fh:
        for ev in events:
            fh.write(json.dumps(ev) + "\n")
    knoten_a = _insp.aggregate_timeline("a")
    knoten_b = _insp.aggregate_timeline("b")
    phasen_a = [k for k in knoten_a
                if k.get("kind") == "phase" and k.get("phase") == "explorer"]
    phasen_b = [k for k in knoten_b
                if k.get("kind") == "phase" and k.get("phase") == "builder"]
    assert len(phasen_a) == 1, f"a-timeline sollte explorer-Phase haben: {knoten_a}"
    assert len(phasen_b) == 1, f"b-timeline sollte builder-Phase haben: {knoten_b}"
    builder_in_a = [k for k in knoten_a if k.get("phase") == "builder"]
    explorer_in_b = [k for k in knoten_b if k.get("phase") == "explorer"]
    assert not builder_in_a, f"a-timeline darf b-Phase nicht sehen: {builder_in_a}"
    assert not explorer_in_b, f"b-timeline darf a-Phase nicht sehen: {explorer_in_b}"

# ---------------------------------------------------------------------------
# OP-381: Loop-UI-Interaktion (A + C)
# ---------------------------------------------------------------------------

def test_audit_events_mappt_timestamp_zu_ts(tmp_path, monkeypatch):
    """OP-381 Bug A: JSONL hat 'timestamp', Gate-Context liest 'ts'."""
    import json as _json

    from werkstatt.web import inspector as _insp
    monkeypatch.setattr(_insp, "werkstatt_home", lambda: tmp_path)
    al = tmp_path / "audit-logs"
    al.mkdir()
    with (al / "agent-pipeline-2026-11-09.jsonl").open("w") as fh:
        fh.write(_json.dumps({
            "run_id": "r1", "kind": "loop_plan_shown",
            "timestamp": "2026-11-09T00:00:00+00:00",
            "project": "werkstatt",
            "plan_text": "test plan",
        }) + "\n")
    events = _insp._audit_events(run_id="r1")
    assert len(events) == 1
    assert events[0].get("ts") == "2026-11-09T00:00:00+00:00"
    assert events[0].get("timestamp") == "2026-11-09T00:00:00+00:00"


def test_ambient_running_wenn_gate_open_kürzlich(tmp_path, monkeypatch):
    """OP-381 Bug C: Loop im Gate-Wait schreibt keinen Heartbeat — aber
    ein gate_open <300s soll ambient 'running' zeigen."""
    _s, db = _store(tmp_path, monkeypatch)
    jetzt = datetime.now(UTC).isoformat()
    _event(db, "run-gate", "gate_open",
           {"gate_id": "g1", "prompt": "test?", "optionen": "jna"},
           ts=jetzt, project="werkstatt")
    from werkstatt.web.inspector import aggregate_ambient
    aus = aggregate_ambient("werkstatt")
    assert aus["loop_status"] == "running", f"erwartet running, ist {aus['loop_status']}"
    assert aus.get("loop_phase") == "gate_wait"

def test_audit_events_ignoriert_migrated_dateien(tmp_path, monkeypatch):
    """OP-381 Bug B: -migrated-*.jsonl sind statische DB-Dumps, nicht
    fortlaufende Quelle. Sie duerfen den Default-Run nicht bestimmen."""
    import json as _json

    from werkstatt.web import inspector as _insp
    monkeypatch.setattr(_insp, "werkstatt_home", lambda: tmp_path)
    al = tmp_path / "audit-logs"
    al.mkdir()
    # Echte Tages-Datei mit aktuellem Run
    with (al / "agent-pipeline-2026-11-09.jsonl").open("w") as fh:
        fh.write(_json.dumps({
            "run_id": "run-aktuell", "kind": "loop_plan_shown",
            "timestamp": "2026-11-09T10:00:00+00:00",
            "project": "werkstatt", "plan_text": "neu",
        }) + "\n")
    # Migrated-Datei mit "spaeterem" run_id (alphabetisch nach Tagesdatei)
    with (al / "agent-pipeline-migrated-2026-11-09.jsonl").open("w") as fh:
        fh.write(_json.dumps({
            "run_id": "run-migriert", "kind": "loop_plan_shown",
            "timestamp": "2026-11-09T12:00:00+00:00",
            "project": "werkstatt", "plan_text": "alt",
        }) + "\n")

    events = _insp._audit_events()
    rids = {str(e.get("run_id", "")) for e in events}
    assert "run-aktuell" in rids, f"aktueller Run fehlt: {rids}"
    assert "run-migriert" not in rids, f"migrated-Run darf nicht dabei sein: {rids}"

