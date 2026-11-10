"""OP-383: Rollen-Telemetrie und JSON-Payload-Aggregation."""
from __future__ import annotations

import json
import sqlite3
from types import SimpleNamespace

import pytest

from werkstatt.agent import _rolle_aus_aufgabe
from werkstatt.web import inspector


@pytest.mark.parametrize(
    ("aufgabe", "expected"),
    [
        ("architect", "architect"),
        ("planner-split-single", "planner"),
        ("builder", "builder"),
        ("reviewer", "reviewer"),
        ("explorer", "explorer"),
        ("scout", "scout"),
        ("free-form task", "unbekannt"),
    ],
)
def test_rolle_aus_aufgabe(aufgabe, expected):
    assert _rolle_aus_aufgabe(aufgabe) == expected


def test_aggregate_tokens_per_rolle_summiert_und_misst_spitze(
    monkeypatch, tmp_path,
):
    db_path = tmp_path / "events.sqlite"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE events "
            "(run_id TEXT, kind TEXT, project TEXT, payload TEXT)"
        )
        events = [
            {"rolle": "architect", "prompt_tokens": 100,
             "completion_tokens": 20, "total_tokens": 120},
            {"rolle": "architect", "prompt_tokens": 240,
             "completion_tokens": 30, "total_tokens": 270},
            {"rolle": "planner", "prompt_tokens": 40,
             "completion_tokens": 10, "total_tokens": 50},
        ]
        conn.executemany(
            "INSERT INTO events VALUES (?, 'llm_usage', 'demo', ?)",
            [("run-1", json.dumps(event)) for event in events],
        )
    monkeypatch.setattr(
        inspector, "EventStore",
        lambda: SimpleNamespace(db_pfad=str(db_path)),
    )

    result = inspector.aggregate_tokens_per_rolle("demo", "run-1")

    assert result == {
        "architect": {
            "calls": 2, "prompt": 340, "completion": 50, "total": 390,
            "max_prompt": 240,
        },
        "planner": {
            "calls": 1, "prompt": 40, "completion": 10, "total": 50,
            "max_prompt": 40,
        },
    }


def test_aggregate_tokens_per_rolle_ignoriert_ungueltige_payloads(
    monkeypatch, tmp_path,
):
    db_path = tmp_path / "events.sqlite"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE events "
            "(run_id TEXT, kind TEXT, project TEXT, payload TEXT)"
        )
        conn.executemany(
            "INSERT INTO events VALUES (?, 'llm_usage', 'demo', ?)",
            [("run-1", "{malformed"), ("run-1", "[]")],
        )
    monkeypatch.setattr(
        inspector, "EventStore",
        lambda: SimpleNamespace(db_pfad=str(db_path)),
    )

    assert inspector.aggregate_tokens_per_rolle("demo", "run-1") == {}
