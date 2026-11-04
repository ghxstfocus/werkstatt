"""Append-only Event-Store (SQLite) fuer Loop-Events.

Ein Datensatz pro `_publish`-Aufruf, monotone `seq` als Cursor fuer
inkrementelles Polling. Die JSONL-Audit-Datei bleibt unabhaengig davon
als Export bestehen.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from werkstatt.paths import werkstatt_home

__all__ = ["EventStore"]


class EventStore:
    """Append-only Event-Store auf SQLite-Basis."""

    def __init__(self, db_pfad: Path | None = None) -> None:
        if db_pfad is None:
            db_pfad = werkstatt_home() / ".werkstatt" / "events.db"
        self.db_pfad = Path(db_pfad)
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
                "run_id TEXT NOT NULL, "
                "kind TEXT NOT NULL, "
                "phase TEXT, "
                "status TEXT, "
                "payload TEXT NOT NULL, "
                "ts TEXT NOT NULL)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_run_seq "
                "ON events(run_id, seq)"
            )
            conn.commit()

    def append(
        self,
        run_id: str,
        kind: str,
        phase: str | None = None,
        status: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> int:
        """Fuegt ein Event an und liefert die vergebene `seq`."""
        ts = datetime.now(UTC).isoformat()
        payload_json = json.dumps(payload or {}, ensure_ascii=False)
        with closing(self._connect()) as conn:
            cur = conn.execute(
                "INSERT INTO events (run_id, kind, phase, status, payload, ts) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (run_id, kind, phase, status, payload_json, ts),
            )
            conn.commit()
            return int(cur.lastrowid or 0)

    def query(
        self,
        run_id: str,
        since_seq: int | None = None,
        limit: int = 500,
        kind: str | None = None,
    ) -> list[dict[str, Any]]:
        """Liefert Events eines Runs mit `seq > since_seq`, aufsteigend."""
        if since_seq is None:
            since_seq = 0
        sql = (
            "SELECT seq, run_id, kind, phase, status, payload, ts "
            "FROM events WHERE run_id = ? AND seq > ?"
        )
        params: list[Any] = [run_id, since_seq]
        if kind is not None:
            sql += " AND kind = ?"
            params.append(kind)
        sql += " ORDER BY seq ASC LIMIT ?"
        params.append(limit)
        with closing(self._connect()) as conn:
            rows = conn.execute(sql, params).fetchall()
        ergebnis: list[dict[str, Any]] = []
        for seq, rid, kind_wert, phase, status, payload, ts in rows:
            try:
                payload_obj = json.loads(payload)
            except json.JSONDecodeError:
                payload_obj = {}
            ergebnis.append(
                {
                    "seq": seq,
                    "run_id": rid,
                    "kind": kind_wert,
                    "phase": phase,
                    "status": status,
                    "payload": payload_obj,
                    "ts": ts,
                }
            )
        return ergebnis
