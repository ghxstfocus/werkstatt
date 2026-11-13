"""Append-only Event-Store (SQLite) fuer Loop-Events.

Ein Datensatz pro `_publish`-Aufruf, monotone `seq` als Cursor fuer
inkrementelles Polling. Die JSONL-Audit-Datei bleibt unabhaengig davon
als Export bestehen.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Self

from werkstatt.paths import werkstatt_home

__all__ = ["EventStore", "RunLeaseLost"]


class RunLeaseLost(RuntimeError):
    """Der Worker ist nicht mehr Inhaber der aktuellen Run-Lease."""


class RunLeaseBusy(RuntimeError):
    """Ein anderer Worker haelt die aktive Run-Lease."""


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
                "lease_owner TEXT, "
                "lease_until REAL, "
                "fencing_token INTEGER NOT NULL DEFAULT 0, "
                "PRIMARY KEY (project, run_id))"
            )
            run_columns = {
                str(row[1]) for row in conn.execute(
                    "PRAGMA table_info(run_records)"
                )
            }
            for column, definition in (
                ("lease_owner", "TEXT"),
                ("lease_until", "REAL"),
                ("fencing_token", "INTEGER NOT NULL DEFAULT 0"),
            ):
                if column not in run_columns:
                    conn.execute(
                        f"ALTER TABLE run_records ADD COLUMN {column} {definition}"
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
            # The Web API publishes the durable run identity before Popen so
            # chat jobs can attach during startup. The worker later fills the
            # exact checkout HEAD without replacing an already pinned base.
            if base_commit is not None:
                conn.execute(
                    "UPDATE run_records SET base_commit=?, updated_at=? "
                    "WHERE project=? AND run_id=? AND target=? "
                    "AND base_commit IS NULL",
                    (base_commit, now, project, run_id, target),
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

    def acquire_run_lease(
        self,
        project: str,
        run_id: str,
        worker_id: str,
        *,
        lease_seconds: float = 30.0,
    ) -> int | None:
        """Acquire an expired/unowned run lease and return its fence.

        Re-acquisition by the same owner renews the current fence. A different
        live owner is never displaced, and expiry advances the fencing token.
        """
        if not worker_id.strip():
            raise ValueError("worker_id darf nicht leer sein")
        if lease_seconds <= 0:
            raise ValueError("lease_seconds muss positiv sein")
        now = time.time()
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT lease_owner, lease_until, fencing_token "
                "FROM run_records WHERE project=? AND run_id=?",
                (project, run_id),
            ).fetchone()
            if row is None:
                conn.rollback()
                raise ValueError("RunRecord fehlt; Lease nicht angelegt")
            owner, lease_until, token = row
            if owner == worker_id:
                if lease_until is None or float(lease_until) <= now:
                    conn.rollback()
                    return None
                conn.execute(
                    "UPDATE run_records SET lease_until=?, updated_at=? "
                    "WHERE project=? AND run_id=? AND lease_owner=? "
                    "AND fencing_token=?",
                    (
                        now + lease_seconds, datetime.now(UTC).isoformat(),
                        project, run_id, worker_id, int(token),
                    ),
                )
                conn.commit()
                return int(token)
            if lease_until is not None and float(lease_until) > now:
                conn.commit()
                return None
            next_token = int(token) + 1
            conn.execute(
                "UPDATE run_records SET lease_owner=?, lease_until=?, "
                "fencing_token=?, updated_at=? WHERE project=? AND run_id=?",
                (
                    worker_id, now + lease_seconds, next_token,
                    datetime.now(UTC).isoformat(), project, run_id,
                ),
            )
            conn.commit()
        return next_token

    def renew_run_lease(
        self,
        project: str,
        run_id: str,
        worker_id: str,
        fencing_token: int,
        *,
        lease_seconds: float = 30.0,
    ) -> bool:
        """Renew only a still-live lease with the same fencing token."""
        if lease_seconds <= 0:
            raise ValueError("lease_seconds muss positiv sein")
        now = time.time()
        with closing(self._connect()) as conn:
            cur = conn.execute(
                "UPDATE run_records SET lease_until=?, updated_at=? "
                "WHERE project=? AND run_id=? AND lease_owner=? "
                "AND fencing_token=? AND lease_until>?",
                (
                    now + lease_seconds, datetime.now(UTC).isoformat(),
                    project, run_id, worker_id, fencing_token, now,
                ),
            )
            conn.commit()
        return cur.rowcount == 1

    def assert_run_lease(
        self,
        project: str,
        run_id: str,
        worker_id: str,
        fencing_token: int,
    ) -> None:
        """Raise when this worker no longer has the exclusive live run lease."""
        now = time.time()
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT 1 FROM run_records WHERE project=? AND run_id=? "
                "AND lease_owner=? AND fencing_token=? AND lease_until>?",
                (project, run_id, worker_id, fencing_token, now),
            ).fetchone()
        if row is None:
            raise RunLeaseLost(
                f"Run-Lease verloren: project={project}, run_id={run_id}"
            )

    def release_run_lease(
        self,
        project: str,
        run_id: str,
        worker_id: str,
        fencing_token: int,
    ) -> bool:
        """Release only the matching owner; stale workers cannot clear a new lease."""
        with closing(self._connect()) as conn:
            cur = conn.execute(
                "UPDATE run_records SET lease_owner=NULL, lease_until=NULL, "
                "updated_at=? WHERE project=? AND run_id=? AND lease_owner=? "
                "AND fencing_token=?",
                (
                    datetime.now(UTC).isoformat(),
                    project, run_id, worker_id, fencing_token,
                ),
            )
            conn.commit()
        return cur.rowcount == 1


    def run_lease(
        self,
        project: str,
        run_id: str,
        worker_id: str,
        *,
        lease_seconds: float = 30.0,
    ) -> RunLeaseGuard:
        """Create a renewable fenced lease guard for one worker."""
        return RunLeaseGuard(self, project, run_id, worker_id, lease_seconds)


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
        kind: str | None = None,
    ) -> dict[str, Any] | None:
        """Claim the oldest available message, optionally by consumer kind."""
        if lease_seconds <= 0:
            raise ValueError("lease_seconds muss positiv sein")
        now = time.time()
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            sql = (
                "SELECT seq, message_id, kind, payload, fencing_token "
                "FROM run_inbox WHERE project=? AND run_id=? "
                "AND (status='pending' OR "
                "(status='leased' AND lease_until<=?))"
            )
            params: list[Any] = [project, run_id, now]
            if kind is not None:
                sql += " AND kind=?"
                params.append(kind)
            sql += " ORDER BY seq LIMIT 1"
            row = conn.execute(sql, params).fetchone()
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


class RunLeaseGuard:
    """Renew a run lease during long model/tool calls and fail closed on loss."""

    def __init__(
        self,
        store: EventStore,
        project: str,
        run_id: str,
        worker_id: str,
        lease_seconds: float,
    ) -> None:
        if lease_seconds <= 0:
            raise ValueError("lease_seconds muss positiv sein")
        self.store = store
        self.project = project
        self.run_id = run_id
        self.worker_id = worker_id
        self.lease_seconds = lease_seconds
        self.fencing_token: int | None = None
        self._stop = threading.Event()
        self._lost = threading.Event()
        self._thread: threading.Thread | None = None

    def __enter__(self) -> Self:
        token = self.store.acquire_run_lease(
            self.project,
            self.run_id,
            self.worker_id,
            lease_seconds=self.lease_seconds,
        )
        if token is None:
            raise RunLeaseBusy(
                f"Run bereits durch Worker belegt: {self.project}/{self.run_id}"
            )
        self.fencing_token = token
        self._thread = threading.Thread(
            target=self._heartbeat,
            name=f"run-lease-{self.run_id[:12]}",
            daemon=True,
        )
        self._thread.start()
        return self

    def assert_owned(self) -> None:
        if self._lost.is_set() or self.fencing_token is None:
            raise RunLeaseLost(
                f"Run-Lease verloren: project={self.project}, run_id={self.run_id}"
            )
        try:
            self.store.assert_run_lease(
                self.project, self.run_id, self.worker_id, self.fencing_token,
            )
        except RunLeaseLost:
            self._lost.set()
            raise

    def _heartbeat(self) -> None:
        interval = min(10.0, max(0.05, self.lease_seconds / 3))
        while not self._stop.wait(interval):
            if self.fencing_token is None:
                self._lost.set()
                return
            try:
                renewed = self.store.renew_run_lease(
                    self.project,
                    self.run_id,
                    self.worker_id,
                    self.fencing_token,
                    lease_seconds=self.lease_seconds,
                )
            except Exception:
                renewed = False
            if not renewed:
                self._lost.set()
                return

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        if self.fencing_token is not None:
            try:
                self.store.release_run_lease(
                    self.project,
                    self.run_id,
                    self.worker_id,
                    self.fencing_token,
                )
            except Exception:
                # An expired lease is recoverable by its timestamp. Cleanup
                # must not hide the run's original failure.
                pass

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> Literal[False]:
        self.close()
        return False
