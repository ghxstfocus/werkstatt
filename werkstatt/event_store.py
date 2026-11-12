"""Append-only Event-Store (SQLite) fuer Loop-Events.

Ein Datensatz pro `_publish`-Aufruf, monotone `seq` als Cursor fuer
inkrementelles Polling. Die JSONL-Audit-Datei bleibt unabhaengig davon
als Export bestehen.
"""

from __future__ import annotations

import json
import sqlite3
import time
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
        conn.execute("PRAGMA foreign_keys=ON")
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
            conn.execute(
                "CREATE TABLE IF NOT EXISTS run_records ("
                "project TEXT NOT NULL, "
                "run_id TEXT NOT NULL, "
                "status TEXT NOT NULL, "
                "target TEXT NOT NULL DEFAULT '', "
                "base_commit TEXT, "
                "checkpoint_json TEXT NOT NULL DEFAULT '{}', "
                "checkpoint_version INTEGER NOT NULL DEFAULT 0, "
                "updated_at TEXT NOT NULL, "
                "PRIMARY KEY (project, run_id))"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS run_inbox ("
                "seq INTEGER PRIMARY KEY AUTOINCREMENT, "
                "project TEXT NOT NULL, "
                "run_id TEXT NOT NULL, "
                "message_id TEXT NOT NULL, "
                "kind TEXT NOT NULL, "
                "payload TEXT NOT NULL, "
                "status TEXT NOT NULL DEFAULT 'pending', "
                "lease_owner TEXT, "
                "lease_until REAL, "
                "fencing_token INTEGER NOT NULL DEFAULT 0, "
                "created_at TEXT NOT NULL, "
                "UNIQUE (project, run_id, message_id), "
                "FOREIGN KEY (project, run_id) "
                "REFERENCES run_records(project, run_id))"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_run_inbox_claim "
                "ON run_inbox(project, run_id, status, seq)"
            )
            conn.commit()


    def create_run_record(
        self,
        project: str,
        run_id: str,
        target: str,
        *,
        base_commit: str | None = None,
        status: str = "running",
    ) -> dict[str, Any]:
        """Create the durable run identity once; retries return the same record."""
        now = datetime.now(UTC).isoformat()
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO run_records "
                "(project, run_id, status, target, base_commit, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (project, run_id, status, target, base_commit, now),
            )
            row = conn.execute(
                "SELECT project, run_id, status, target, base_commit, "
                "checkpoint_json, checkpoint_version, updated_at "
                "FROM run_records WHERE project=? AND run_id=?",
                (project, run_id),
            ).fetchone()
            conn.commit()
        if row is None:
            raise sqlite3.IntegrityError("RunRecord konnte nicht angelegt werden")
        if row[3] != target:
            raise ValueError("Run-ID existiert bereits mit anderem Ziel")
        return self._run_record_from_row(row)

    @staticmethod
    def _run_record_from_row(row: tuple[Any, ...]) -> dict[str, Any]:
        try:
            checkpoint = json.loads(row[5])
        except (TypeError, json.JSONDecodeError):
            checkpoint = {}
        return {
            "project": row[0],
            "run_id": row[1],
            "status": row[2],
            "target": row[3],
            "base_commit": row[4],
            "checkpoint": checkpoint,
            "checkpoint_version": int(row[6]),
            "updated_at": row[7],
        }

    def get_run_record(
        self, project: str, run_id: str,
    ) -> dict[str, Any] | None:
        """Return the persisted run snapshot, if it exists."""
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT project, run_id, status, target, base_commit, "
                "checkpoint_json, checkpoint_version, updated_at "
                "FROM run_records WHERE project=? AND run_id=?",
                (project, run_id),
            ).fetchone()
        return self._run_record_from_row(row) if row is not None else None

    def update_run_checkpoint(
        self,
        project: str,
        run_id: str,
        checkpoint: dict[str, Any],
        *,
        expected_version: int,
        status: str | None = None,
    ) -> int:
        """Compare-and-swap checkpoint; return next version or raise on stale state."""
        now = datetime.now(UTC).isoformat()
        checkpoint_json = json.dumps(checkpoint, ensure_ascii=False)
        with closing(self._connect()) as conn:
            cur = conn.execute(
                "UPDATE run_records SET checkpoint_json=?, "
                "checkpoint_version=checkpoint_version+1, "
                "status=COALESCE(?, status), updated_at=? "
                "WHERE project=? AND run_id=? AND checkpoint_version=?",
                (
                    checkpoint_json, status, now, project, run_id,
                    expected_version,
                ),
            )
            if cur.rowcount != 1:
                conn.rollback()
                raise RuntimeError("RunCheckpoint fehlt oder wurde parallel geaendert")
            row = conn.execute(
                "SELECT checkpoint_version FROM run_records "
                "WHERE project=? AND run_id=?",
                (project, run_id),
            ).fetchone()
            conn.commit()
        return int(row[0])

    def enqueue_run_message(
        self,
        project: str,
        run_id: str,
        message_id: str,
        kind: str,
        payload: dict[str, Any],
    ) -> int:
        """Durably enqueue a run message; identical retries return its sequence."""
        payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        now = datetime.now(UTC).isoformat()
        with closing(self._connect()) as conn:
            record = conn.execute(
                "SELECT 1 FROM run_records WHERE project=? AND run_id=?",
                (project, run_id),
            ).fetchone()
            if record is None:
                raise ValueError("RunRecord fehlt; Inbox-Nachricht nicht angenommen")
            conn.execute(
                "INSERT OR IGNORE INTO run_inbox "
                "(project, run_id, message_id, kind, payload, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (project, run_id, message_id, kind, payload_json, now),
            )
            row = conn.execute(
                "SELECT seq, kind, payload FROM run_inbox "
                "WHERE project=? AND run_id=? AND message_id=?",
                (project, run_id, message_id),
            ).fetchone()
            conn.commit()
        if row is None:
            raise ValueError("RunRecord fehlt; Inbox-Nachricht nicht angenommen")
        if row[1] != kind or row[2] != payload_json:
            raise ValueError("message_id wurde mit anderem Inhalt wiederverwendet")
        return int(row[0])

    def claim_run_message(
        self,
        project: str,
        run_id: str,
        worker_id: str,
        *,
        lease_seconds: float = 30.0,
    ) -> dict[str, Any] | None:
        """Claim the oldest available message; each claim increments its fence."""
        if lease_seconds <= 0:
            raise ValueError("lease_seconds muss positiv sein")
        now = time.time()
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT seq, message_id, kind, payload, fencing_token "
                "FROM run_inbox WHERE project=? AND run_id=? "
                "AND (status='pending' OR "
                "(status='leased' AND lease_until<=?)) "
                "ORDER BY seq LIMIT 1",
                (project, run_id, now),
            ).fetchone()
            if row is None:
                conn.commit()
                return None
            fence = int(row[4]) + 1
            cur = conn.execute(
                "UPDATE run_inbox SET status='leased', lease_owner=?, "
                "lease_until=?, fencing_token=? WHERE seq=? AND fencing_token=?",
                (worker_id, now + lease_seconds, fence, row[0], row[4]),
            )
            if cur.rowcount != 1:
                conn.rollback()
                return None
            conn.commit()
        try:
            payload = json.loads(row[3])
        except (TypeError, json.JSONDecodeError):
            payload = {}
        return {
            "seq": int(row[0]),
            "message_id": row[1],
            "kind": row[2],
            "payload": payload,
            "worker_id": worker_id,
            "fencing_token": fence,
        }

    def acknowledge_run_message(
        self,
        seq: int,
        worker_id: str,
        fencing_token: int,
    ) -> bool:
        """Acknowledge only the currently fenced lease holder."""
        with closing(self._connect()) as conn:
            cur = conn.execute(
                "UPDATE run_inbox SET status='acked', lease_owner=NULL, "
                "lease_until=NULL WHERE seq=? AND status='leased' "
                "AND lease_owner=? AND fencing_token=?",
                (seq, worker_id, fencing_token),
            )
            conn.commit()
        return cur.rowcount == 1

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
                conn.execute(
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
