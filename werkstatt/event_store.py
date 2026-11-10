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
                "ts TEXT NOT NULL, "
                "event_id TEXT, "
                "project TEXT NOT NULL DEFAULT 'werkstatt')"
            )
            columns = {
                str(row[1]) for row in conn.execute("PRAGMA table_info(events)")
            }
            if "event_id" not in columns:
                conn.execute("ALTER TABLE events ADD COLUMN event_id TEXT")
            if "project" not in columns:
                conn.execute(
                    "ALTER TABLE events ADD COLUMN project TEXT NOT NULL "
                    "DEFAULT 'werkstatt'"
                )
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_events_event_id "
                "ON events(event_id)"
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
        *,
        event_id: str | None = None,
        project: str = "werkstatt",
    ) -> int:
        """Fuegt ein Event an; optionale Event-ID macht Retries idempotent."""
        ts = datetime.now(UTC).isoformat()
        payload_json = json.dumps(payload or {}, ensure_ascii=False)
        with closing(self._connect()) as conn:
            if event_id is None:
                cur = conn.execute(
                    "INSERT INTO events "
                    "(run_id, kind, phase, status, payload, ts, project) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (run_id, kind, phase, status, payload_json, ts, project),
                )
                seq = int(cur.lastrowid or 0)
            else:
                cur = conn.execute(
                    "INSERT OR IGNORE INTO events "
                    "(run_id, kind, phase, status, payload, ts, event_id, project) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        run_id, kind, phase, status, payload_json, ts,
                        event_id, project,
                    ),
                )
                row = (
                    conn.execute(
                        "SELECT seq FROM events WHERE event_id=?", (event_id,),
                    ).fetchone()
                )
                if row is None:
                    raise sqlite3.IntegrityError(
                        "Event-ID wurde ignoriert, aber nicht gefunden",
                    )
                seq = int(row[0])
            conn.commit()
            return seq

    def query(
        self,
        run_id: str,
        since_seq: int | None = None,
        limit: int = 500,
        kind: str | None = None,
        project: str | None = None,
    ) -> list[dict[str, Any]]:
        """Liefert Events eines Runs mit `seq > since_seq`, aufsteigend."""
        if since_seq is None:
            since_seq = 0
        sql = (
            "SELECT seq, run_id, kind, phase, status, payload, ts, project "
            "FROM events WHERE run_id = ? AND seq > ?"
        )
        params: list[Any] = [run_id, since_seq]
        if kind is not None:
            sql += " AND kind = ?"
            params.append(kind)
        if project is not None:
            sql += " AND project = ?"
            params.append(project)
        sql += " ORDER BY seq ASC LIMIT ?"
        params.append(limit)
        with closing(self._connect()) as conn:
            rows = conn.execute(sql, params).fetchall()
        ergebnis: list[dict[str, Any]] = []
        for seq, rid, kind_wert, phase, status, payload, ts, project_name in rows:
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
                    "project": project_name,
                }
            )
        return ergebnis
