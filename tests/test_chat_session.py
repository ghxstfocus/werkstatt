"""Tests fuer OP-230: Chat-Session-Store."""
from __future__ import annotations

from pathlib import Path

import pytest

from werkstatt.chat_session import (
    ChatSession,
    derive_messages,
    fork,
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
