"""OP-306b: Backend-Aggregation fuer die Werkstatt-Overview."""
import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from werkstatt.web import inspector


def _events_db(path: Path, rows=()) -> SimpleNamespace:
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE events (seq INTEGER PRIMARY KEY AUTOINCREMENT, "
            "run_id TEXT NOT NULL, kind TEXT NOT NULL, ts TEXT NOT NULL, "
            "project TEXT NOT NULL, payload TEXT NOT NULL, "
            "origin_verified INTEGER NOT NULL DEFAULT 0)"
        )
        now = datetime.now(UTC)
        for row in rows:
            run_id, kind, project, payload, age_days, *verification = row
            origin_verified = verification[0] if verification else 1
            ts = (now - timedelta(days=age_days)).isoformat()
            conn.execute(
                "INSERT INTO events(run_id, kind, ts, project, payload, "
                "origin_verified) VALUES (?, ?, ?, ?, ?, ?)",
                (run_id, kind, ts, project, json.dumps(payload), origin_verified),
            )
    return SimpleNamespace(db_pfad=path)


def test_run_verteilung_dedupliziert_terminalevents_und_stopps(tmp_path: Path):
    es = _events_db(tmp_path / "events.db", [
        ("ok-1", "loop_erfolg", "demo", {}, 0),
        ("ok-1", "loop_ended", "demo", {}, 0),
        ("fail-1", "loop_failed", "werkstatt", {}, 0),
        # Legacy stop event has project in payload but default DB project.
        ("abort-1", "web_loop_stopped", "werkstatt", {"project": "demo"}, 0),
        ("abort-1", "loop_ended", "demo", {}, 0),
    ])
    summary = inspector._run_verteilung_30d(es, "demo")
    assert summary == {
        "erfolg": 1, "fehlgeschlagen": 0, "abgebrochen": 1,
        "unverified": 0, "gesamt": 2,
    }


def test_neuester_terminalstatus_entscheidet_je_run(tmp_path: Path):
    es = _events_db(tmp_path / "events.db", [
        ("retry-success", "loop_failed", "demo", {}, 0),
        ("retry-success", "loop_ended", "demo", {}, 0),
        ("retry-failed", "loop_ended", "demo", {}, 0),
        ("retry-failed", "loop_failed", "demo", {}, 0),
    ])
    assert inspector._run_verteilung_30d(es, "demo") == {
        "erfolg": 1, "fehlgeschlagen": 1, "abgebrochen": 0,
        "unverified": 0, "gesamt": 2,
    }


def test_aeltere_runs_fliessen_nicht_in_30_tage_quote(tmp_path: Path):
    es = _events_db(tmp_path / "events.db", [
        ("old", "loop_ended", "demo", {}, 45),
        ("new", "loop_failed", "demo", {}, 0),
    ])
    assert inspector._run_verteilung_30d(es, "demo") == {
        "erfolg": 0, "fehlgeschlagen": 1, "abgebrochen": 0,
        "unverified": 0, "gesamt": 1,
    }


def test_projekte_bleiben_in_der_ergebnisverteilung_getrennt(tmp_path: Path):
    es = _events_db(tmp_path / "events.db", [
        ("a", "loop_ended", "alpha", {}, 0),
        ("b", "loop_failed", "beta", {}, 0),
    ])
    assert inspector._run_verteilung_30d(es, "alpha")["erfolg"] == 1
    assert inspector._run_verteilung_30d(es, "alpha")["fehlgeschlagen"] == 0


def test_weekly_ranking_zaehlt_eindeutige_runs(tmp_path: Path):
    es = _events_db(tmp_path / "events.db", [
        ("same", "loop_erfolg", "demo", {}, 0),
        ("same", "loop_ended", "demo", {}, 0),
        ("old", "loop_ended", "demo", {}, 12),
    ])
    assert inspector._runs_7d(es, "demo") == 1


def test_sparkline_hat_30_buckets_und_dedupliziert(tmp_path: Path):
    es = _events_db(tmp_path / "events.db", [
        ("same", "loop_erfolg", "demo", {}, 0),
        ("same", "loop_ended", "demo", {}, 0),
        ("other", "loop_failed", "demo", {}, 0),
    ])
    values = inspector._sparkline_30d(es, "demo")
    assert len(values) == 30
    assert sum(values) == 2


def test_sparkline_ignoriert_events_ohne_run_id(tmp_path: Path):
    es = _events_db(tmp_path / "events.db", [
        ("", "loop_ended", "demo", {}, 0),
        ("", "loop_failed", "demo", {}, 0),
        ("bekannt", "loop_ended", "demo", {}, 0),
    ])
    assert sum(inspector._sparkline_30d(es, "demo")) == 1
    assert inspector._run_verteilung_30d(es, "demo")["gesamt"] == 1


def test_unverifizierter_run_zaehlt_nicht_als_erfolg(tmp_path: Path):
    es = _events_db(tmp_path / "events.db", [
        ("legacy", "loop_ended", "demo", {}, 0, 0),
        ("known", "loop_erfolg", "demo", {}, 0, 1),
    ])
    assert inspector._run_verteilung_30d(es, "demo") == {
        "erfolg": 1, "fehlgeschlagen": 0, "abgebrochen": 0,
        "unverified": 1, "gesamt": 2,
    }


def test_leere_eventdaten_liefern_nullsummen(tmp_path: Path):
    es = _events_db(tmp_path / "events.db")
    assert inspector._run_verteilung_30d(es, "demo") == {
        "erfolg": 0, "fehlgeschlagen": 0, "abgebrochen": 0,
        "unverified": 0, "gesamt": 0,
    }
    assert inspector._runs_7d(es, "demo") == 0
    assert sum(inspector._sparkline_30d(es, "demo")) == 0


def test_aggregate_overview_baut_project_cards_und_weekly_top3(
    tmp_path: Path, monkeypatch,
):
    db = tmp_path / "events.db"
    rows = []
    for project, count in (("alpha", 3), ("beta", 2), ("gamma", 1)):
        for i in range(count):
            rows.append((f"{project}-{i}", "loop_ended", project, {}, 0))
    es = _events_db(db, rows)
    projects = []
    for name in ("alpha", "beta", "gamma"):
        path = tmp_path / name
        (path / "docs").mkdir(parents=True)
        (path / "docs" / "STATUS.md").write_text("## Open\n", encoding="utf-8")
        projects.append(path)
    monkeypatch.setattr(inspector, "EventStore", lambda: es)
    monkeypatch.setattr(inspector, "_scan_projekte", lambda: projects)
    monkeypatch.setattr(inspector, "parse_ops", lambda _p: [{"status": "open"}])
    monkeypatch.setattr(
        inspector, "aggregate_ambient",
        lambda _n: {"loop_status": "idle", "last_run": None},
    )

    result = inspector.aggregate_overview()
    assert result["top_3"] == ["alpha", "beta", "gamma"]
    assert result["ergebnisse_30d"]["erfolg"] == 6
    assert [p["runs_7d_total"] for p in result["projekte"]] == [3, 2, 1]
    assert [p["erfolgsquote_30d"] for p in result["projekte"]] == [1.0, 1.0, 1.0]
    assert all(p["ops_offen"] == 1 for p in result["projekte"])


def test_overview_ohne_projekte_hat_leere_metriken(
    tmp_path: Path, monkeypatch,
):
    monkeypatch.setattr(
        inspector, "EventStore",
        lambda: SimpleNamespace(db_pfad=tmp_path / "unused.db"),
    )
    monkeypatch.setattr(inspector, "_scan_projekte", list)
    result = inspector.aggregate_overview()
    assert result["projekte"] == []
    assert result["top_3"] == []
    assert result["ergebnisse_30d"] == {
        "erfolg": 0, "fehlgeschlagen": 0, "abgebrochen": 0,
        "unverified": 0, "gesamt": 0,
    }
