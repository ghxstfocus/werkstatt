"""Chat-Session-Store (OP-230, SQLite, pro Projekt).

Append-only Event-Store fuer Chat-Historie. Die LLM-Historie wird
aus Events rekonstruiert (derive_messages), damit Sessions fork-faehig
sind: ein Fork ist eine neue Session, die die Events bis zu einem
bestimmten seq kopiert.

Abgrenzung zu werkstatt/event_store.py:
  event_store.py   -- Loop-Audit, global, ein events.db
  chat_session.py  -- Chat-Historie, pro Projekt eine DB
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from werkstatt.paths import werkstatt_home

__all__ = [
    "ChatSession",
    "derive_messages",
    "fork",
    "list_sessions",
]


def _db_pfad(project: str) -> Path:
    """Projekt-DB-Pfad (SOLL §5: SQLite pro Projekt)."""
    return werkstatt_home() / ".werkstatt" / project / "chat-sessions.db"


class ChatSession:
    """Append-only Chat-Session auf SQLite (pro Projekt)."""

    def __init__(
        self,
        project: str,
        session_id: str,
        db_pfad: Path | None = None,
    ) -> None:
        self.project = project
        self.session_id = session_id
        self.db_pfad = Path(db_pfad) if db_pfad else _db_pfad(project)
        self.db_pfad.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_pfad, timeout=5.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_schema(self) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS events ("
                "seq INTEGER PRIMARY KEY AUTOINCREMENT, "
                "session_id TEXT NOT NULL, "
                "ts TEXT NOT NULL, "
                "kind TEXT NOT NULL, "
                "payload TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_session_seq "
                "ON events(session_id, seq)"
            )
            conn.commit()

    def append(
        self, kind: str, payload: dict[str, Any] | None = None
    ) -> int:
        """Fuegt ein Event an und liefert die vergebene seq."""
        ts = datetime.now(UTC).isoformat()
        payload_json = json.dumps(payload or {}, ensure_ascii=False)
        with closing(self._connect()) as conn:
            cur = conn.execute(
                "INSERT INTO events (session_id, ts, kind, payload) "
                "VALUES (?, ?, ?, ?)",
                (self.session_id, ts, kind, payload_json),
            )
            conn.commit()
            return int(cur.lastrowid or 0)

    def load(self) -> list[dict[str, Any]]:
        """Liefert alle Events der Session, aufsteigend nach seq."""
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT seq, session_id, ts, kind, payload "
                "FROM events WHERE session_id = ? ORDER BY seq ASC",
                (self.session_id,),
            ).fetchall()
        ergebnis: list[dict[str, Any]] = []
        for seq, sid, ts, kind, payload in rows:
            try:
                payload_obj = json.loads(payload) if payload else {}
            except json.JSONDecodeError:
                payload_obj = {}
            ergebnis.append({
                "seq": seq,
                "session_id": sid,
                "ts": ts,
                "kind": kind,
                "payload": payload_obj,
            })
        return ergebnis


def list_sessions(project: str, db_pfad: Path | None = None) -> list[str]:
    """Alle Session-IDs im Projekt, sortiert."""
    pfad = Path(db_pfad) if db_pfad else _db_pfad(project)
    if not pfad.exists():
        return []
    with closing(sqlite3.connect(pfad)) as conn:
        rows = conn.execute(
            "SELECT DISTINCT session_id FROM events ORDER BY session_id"
        ).fetchall()
    return [str(r[0]) for r in rows]


def fork(
    project: str,
    parent_session_id: str,
    at_seq: int | None = None,
    db_pfad: Path | None = None,
) -> str:
    """Forkt eine Session in eine neue session_id und liefert diese.

    Kopiert Events [1..at_seq] (oder alle, wenn at_seq=None) aus der
    Parent-Session in eine neue Session. Parent bleibt unveraendert.
    """
    pfad = Path(db_pfad) if db_pfad else _db_pfad(project)
    parent = ChatSession(project, parent_session_id, db_pfad=pfad)
    alte = parent.load()
    if at_seq is not None:
        alte = [e for e in alte if e["seq"] <= at_seq]
    neue_id = uuid.uuid4().hex
    neu = ChatSession(project, neue_id, db_pfad=pfad)
    for ev in alte:
        neu.append(ev["kind"], ev["payload"])
    return neue_id


def derive_messages(
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Rekonstruiert LLM-Historie (OpenAI-Format) aus Events.

    Mapping:
      user        -> {"role": "user",      "content": text}
      assistant   -> {"role": "assistant", "content": text}
      tool_call   -> {"role": "assistant", "tool_calls": ...}
      tool_result -> {"role": "tool",      "content": ...}
    Unbekannte kinds werden ignoriert.
    """
    msgs: list[dict[str, Any]] = []
    for ev in events:
        kind = ev.get("kind")
        payload = ev.get("payload") or {}
        if kind == "user":
            msgs.append({
                "role": "user",
                "content": payload.get("text", ""),
            })
        elif kind == "assistant":
            msgs.append({
                "role": "assistant",
                "content": payload.get("text", ""),
            })
        elif kind == "tool_call":
            msgs.append({
                "role": "assistant",
                "tool_calls": payload.get("tool_calls", []),
            })
        elif kind == "tool_result":
            msgs.append({
                "role": "tool",
                "content": payload.get("content", ""),
            })
    return msgs
