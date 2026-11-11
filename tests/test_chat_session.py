"""Tests fuer OP-230: Chat-Session-Store."""
from __future__ import annotations

from pathlib import Path

import pytest

from werkstatt.chat_session import (
    ChatSession,
    derive_messages,
    fork,
    list_session_summaries,
    list_sessions,
)


@pytest.fixture
def db(tmp_path: Path) -> Path:
    return tmp_path / "chat-sessions.db"


def test_append_und_load_runde(db: Path) -> None:
    s = ChatSession("demo", "s1", db_pfad=db)
    s.append("user", {"text": "hallo"})
    s.append("assistant", {"text": "hi"})
    geladen = s.load()
    assert [e["kind"] for e in geladen] == ["user", "assistant"]
    assert geladen[0]["payload"]["text"] == "hallo"
    assert geladen[1]["payload"]["text"] == "hi"
    assert geladen[0]["seq"] < geladen[1]["seq"]


def test_persistenz_ueber_neue_instanz(db: Path) -> None:
    ChatSession("demo", "s1", db_pfad=db).append("user", {"text": "x"})
    wieder = ChatSession("demo", "s1", db_pfad=db)
    assert len(wieder.load()) == 1


def test_list_sessions(db: Path) -> None:
    ChatSession("demo", "s1", db_pfad=db).append("user", {"text": "a"})
    ChatSession("demo", "s2", db_pfad=db).append("user", {"text": "b"})
    assert list_sessions("demo", db_pfad=db) == ["s1", "s2"]


def test_list_sessions_leer(db: Path) -> None:
    assert list_sessions("demo", db_pfad=db) == []


def test_fork_kopiert_bis_at_seq(db: Path) -> None:
    s = ChatSession("demo", "s1", db_pfad=db)
    s.append("user", {"text": "frage 1"})
    s.append("assistant", {"text": "antwort 1"})
    s.append("user", {"text": "frage 2"})

    neue_id = fork("demo", "s1", at_seq=2, db_pfad=db)
    assert neue_id != "s1"
    kopie = ChatSession("demo", neue_id, db_pfad=db).load()
    assert [e["payload"]["text"] for e in kopie] == [
        "frage 1", "antwort 1",
    ]
    assert len(s.load()) == 3


def test_fork_ohne_at_seq_kopiert_alles(db: Path) -> None:
    s = ChatSession("demo", "s1", db_pfad=db)
    s.append("user", {"text": "a"})
    s.append("assistant", {"text": "b"})
    neue_id = fork("demo", "s1", db_pfad=db)
    kopie = ChatSession("demo", neue_id, db_pfad=db).load()
    assert len(kopie) == 2


def test_snapshot_to_is_stable_and_limited_to_context_watermark(db: Path) -> None:
    parent = ChatSession("demo", "parent", db_pfad=db)
    parent.append("user", {"text": "Frage 1"})
    cutoff = parent.max_seq()
    parent.append("assistant", {"text": "Antwort 1"})
    branch = parent.snapshot_to("job-1", at_seq=cutoff)
    parent.append("user", {"text": "spaeter eingereicht"})

    assert [event["payload"]["text"] for event in branch.load()] == ["Frage 1"]
    assert parent.snapshot_to("job-1", at_seq=parent.max_seq()).load() == branch.load()


def test_job_snapshot_is_hidden_from_session_list_and_cleaned(db: Path) -> None:
    parent = ChatSession("demo", "parent", db_pfad=db)
    parent.append("user", {"text": "Frage"})
    branch = parent.snapshot_to("job-branch", at_seq=parent.max_seq())
    branch.append("user", {"text": "Jobfrage"})

    assert list_sessions("demo", db_pfad=db) == ["parent"]
    assert list_sessions("demo", db_pfad=db, mit_inhalt=True) == ["parent"]
    assert parent.delete_snapshot("job-branch") is True
    assert parent.delete_snapshot("job-branch") is False
    assert branch.load() == []
    assert parent.load()[0]["payload"]["text"] == "Frage"


def test_append_job_turn_is_idempotent_and_reconstructs_history(db: Path) -> None:
    session = ChatSession("demo", "parent", db_pfad=db)

    assert session.append_job_turn("job-1", "Frage", "Antwort")
    assert session.append_job_turn("job-1", "Frage", "Antwort") is False
    events = session.load()
    assert len(events) == 1
    assert events[0]["kind"] == "job_turn"
    assert derive_messages(events) == [
        {"role": "user", "content": "Frage"},
        {"role": "assistant", "content": "Antwort"},
    ]


def test_derive_messages_mapping(db: Path) -> None:
    s = ChatSession("demo", "s1", db_pfad=db)
    s.append("user", {"text": "was ist x?"})
    s.append("tool_call", {"tool_calls": [
        {"id": "t1", "name": "read_file"},
    ]})
    s.append("tool_result", {"content": "inhalt"})
    s.append("assistant", {"text": "x ist y"})
    s.append("unbekannt", {"foo": "bar"})

    msgs = derive_messages(s.load())
    assert len(msgs) == 4
    assert msgs[0] == {"role": "user", "content": "was ist x?"}
    assert msgs[1]["role"] == "assistant"
    assert msgs[1]["tool_calls"] == [{"id": "t1", "name": "read_file"}]
    assert msgs[2] == {"role": "tool", "content": "inhalt"}
    assert msgs[3] == {"role": "assistant", "content": "x ist y"}


def test_resolve_loop_action_is_session_bound_and_one_time(db: Path) -> None:
    from datetime import UTC, datetime, timedelta

    session = ChatSession("demo", "s1", db_pfad=db)
    proposal_id = "a" * 32
    session.append("loop_action_proposed", {
        "proposal_id": proposal_id,
        "project": "demo",
        "action": "stop",
        "arguments": {},
        "expires_at": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
    })

    proposal, status, _ = session.resolve_loop_action(proposal_id, "confirm")
    assert proposal["project"] == "demo"
    assert status == "claimed"
    _, duplicate_status, _ = session.resolve_loop_action(proposal_id, "confirm")
    assert duplicate_status == "confirmed"
    assert [event["kind"] for event in session.load()].count("loop_action_confirmed") == 1

    other = ChatSession("demo", "s2", db_pfad=db)
    assert other.resolve_loop_action(proposal_id, "confirm") is None


def test_session_summaries_use_first_request_and_recent_activity(db: Path) -> None:
    older = ChatSession("demo", "older", db_pfad=db)
    older.append("user", {"text": "  Fehler   im Loop\nbitte prüfen "})
    older.append("assistant", {"text": "Ich sehe nach."})
    newer = ChatSession("demo", "newer", db_pfad=db)
    newer.append_job_turn("job-1", "Fasse den letzten Run zusammen", "Der Run ist gruen.")

    summaries = list_session_summaries("demo", db_pfad=db)

    assert [item["session_id"] for item in summaries] == ["newer", "older"]
    assert summaries[0]["title"] == "Fasse den letzten Run zusammen"
    assert summaries[1]["title"] == "Fehler im Loop bitte prüfen"
    assert summaries[0]["updated_at"]
