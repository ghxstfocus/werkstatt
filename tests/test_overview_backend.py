"""OP-306b Etappe 1: aggregate_overview() + /api/overview."""
import sqlite3
from datetime import UTC, datetime, timedelta


def _setup_base(tmp_path, monkeypatch, projekte):
    """Erzeugt _PROJECTS_BASE-Struktur mit docs/STATUS.md pro Projekt."""
    base = tmp_path / "opt"
    base.mkdir()
    for name in projekte:
        p = base / name / "docs"
        p.mkdir(parents=True)
        (p / "STATUS.md").write_text(
            "## Offene Punkte\n\n### OP-001: Test\n\n- **Status:** open\n",
            encoding="utf-8",
        )
    from werkstatt.web import inspector as _insp
    monkeypatch.setattr(_insp, "_PROJECTS_BASE", base)
    return base


def _store(tmp_path, monkeypatch):
    from werkstatt.event_store import EventStore
    from werkstatt.projection import Projector
    db = tmp_path / ".werkstatt" / "events.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    Projector(db_pfad=db)
    s = EventStore(db)
    from werkstatt.web import inspector as _insp
    monkeypatch.setattr(_insp, "EventStore", lambda: s)
    return s, db


def _event(db, run_id, kind, project, ts=None):
    if ts is None:
        ts = datetime.now(UTC).isoformat()
    with sqlite3.connect(str(db)) as c:
        c.execute(
            "INSERT INTO events "
            "(run_id, kind, phase, status, payload, ts, project) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (run_id, kind, None, None, "{}", ts, project),
        )
        c.commit()


def test_overview_leere_basis(tmp_path, monkeypatch):
    """Keine Projekt-Verzeichnisse -> projekte=[] und top_3=[]."""
    base = tmp_path / "opt"
    base.mkdir()
    from werkstatt.web import inspector as _insp
    monkeypatch.setattr(_insp, "_PROJECTS_BASE", base)
    _store(tmp_path, monkeypatch)
    aus = _insp.aggregate_overview()
    assert aus["projekte"] == []
    assert aus["top_3"] == []
    assert "generated_at" in aus


def test_overview_liefert_projekte_mit_kpi(tmp_path, monkeypatch):
    """Zwei Projekte, Status.md mtime als ISO-Zeit."""
    _setup_base(tmp_path, monkeypatch, ["a", "b"])
    _store(tmp_path, monkeypatch)
    from werkstatt.web import inspector as _insp
    aus = _insp.aggregate_overview()
    namen = [p["name"] for p in aus["projekte"]]
    assert namen == ["a", "b"]
    for p in aus["projekte"]:
        assert p["ops_offen"] == 1
        assert p["loop_status"] == "idle"
        assert p["status_md_mtime"] is not None
        assert isinstance(p["runs_30d"], list)
        assert len(p["runs_30d"]) == 30


def test_overview_sparkline_buckets(tmp_path, monkeypatch):
    """3 Runs heute + 2 gestern -> sparkline[-1]=3, sparkline[-2]=2."""
    _setup_base(tmp_path, monkeypatch, ["a"])
    _s, db = _store(tmp_path, monkeypatch)
    heute = datetime.now(UTC).isoformat()
    gestern = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    for _ in range(3):
        _event(db, "run-h", "loop_erfolg", "a", ts=heute)
    for _ in range(2):
        _event(db, "run-g", "loop_failed", "a", ts=gestern)
    from werkstatt.web import inspector as _insp
    aus = _insp.aggregate_overview()
    p = aus["projekte"][0]
    assert p["runs_30d"][-1] == 3, f"heute: {p['runs_30d'][-1]}"
    assert p["runs_30d"][-2] == 2, f"gestern: {p['runs_30d'][-2]}"
    assert sum(p["runs_30d"]) == 5
    assert p["runs_30d_total"] == 5


def test_overview_top3_sortiert_nach_runs(tmp_path, monkeypatch):
    """Projekt mit mehr Runs steht in top_3 vor leerem Projekt."""
    _setup_base(tmp_path, monkeypatch, ["leer", "aktiv", "mittel"])
    _s, db = _store(tmp_path, monkeypatch)
    heute = datetime.now(UTC).isoformat()
    for _ in range(5):
        _event(db, "run-a", "loop_erfolg", "aktiv", ts=heute)
    for _ in range(2):
        _event(db, "run-m", "loop_erfolg", "mittel", ts=heute)
    from werkstatt.web import inspector as _insp
    aus = _insp.aggregate_overview()
    top = aus["top_3"]
    assert top[0] == "aktiv"
    assert top[1] == "mittel"
    assert "leer" not in top


def test_overview_letzter_run_ignoriert_leere_run_id(tmp_path, monkeypatch):
    """OP-374-a: leere run_id darf nicht als letzter Run auftauchen."""
    _setup_base(tmp_path, monkeypatch, ["a"])
    _s, db = _store(tmp_path, monkeypatch)
    _event(db, "echter-run", "loop_erfolg", "a",
           ts="2026-11-01T00:00:00+00:00")
    _event(db, "", "loop_phase", "a", ts="2026-11-02T00:00:00+00:00")
    from werkstatt.web import inspector as _insp
    aus = _insp.aggregate_overview()
    p = aus["projekte"][0]
    assert p["letzter_run"] is not None
    assert p["letzter_run"]["run_id"] == "echter-run"
