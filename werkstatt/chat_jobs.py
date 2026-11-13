"""Persistente Hintergrundjobs fuer Projekt-Chat (OP-397).

Der HTTP-Request nimmt einen Auftrag nur an. Ein Worker fuehrt den
read-only Chat-Aufruf aus; Status und Ereignisse bleiben in SQLite
abrufbar und koennen nach einem UI-Reconnect wieder abgespielt werden.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
import uuid
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from werkstatt.paths import werkstatt_home

__all__ = ["ChatJobStore", "IdempotencyConflict", "enqueue_chat_job"]


class IdempotencyConflict(ValueError):
    """Raised when a key is reused for a different chat request."""

_EXECUTOR = ThreadPoolExecutor(max_workers=8, thread_name_prefix="werkstatt-chat")
_FUTURES: dict[str, Future[bool]] = {}
_FUTURES_LOCK = threading.RLock()
_WORKER_ID = f"{os.getpid()}:{uuid.uuid4().hex}"
_WORKER_LEASE_SECONDS = 90
_WORKER_HEARTBEAT_SECONDS = 15


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


def _db_path(project: str) -> Path:
    return werkstatt_home() / ".werkstatt" / "chat-jobs" / f"{project}.db"


class ChatJobStore:
    """SQLite job/event store, isolated by project."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_schema(self) -> None:
        with closing(self._connect()) as conn:
            conn.executescript(
                "CREATE TABLE IF NOT EXISTS jobs ("
                " job_id TEXT PRIMARY KEY, session_id TEXT NOT NULL,"
                " idempotency_key TEXT NOT NULL, message TEXT NOT NULL,"
                " mode TEXT NOT NULL, state TEXT NOT NULL,"
                " answer TEXT, error TEXT, created_at TEXT NOT NULL,"
                " updated_at TEXT NOT NULL, worker_id TEXT,"
                " heartbeat_at TEXT, cancel_requested INTEGER NOT NULL DEFAULT 0,"
                " context_seq INTEGER, run_id TEXT, project TEXT,"
                " run_inbox_enqueued INTEGER NOT NULL DEFAULT 0,"
                " run_result_enqueued INTEGER NOT NULL DEFAULT 0,"
                " run_snapshot_source TEXT,run_snapshot_path TEXT,"
                " run_snapshot_head TEXT,run_snapshot_fingerprint TEXT,"
                " UNIQUE(session_id, idempotency_key));"
                "CREATE TABLE IF NOT EXISTS job_events ("
                " seq INTEGER PRIMARY KEY AUTOINCREMENT,"
                " job_id TEXT NOT NULL, kind TEXT NOT NULL,"
                " payload TEXT NOT NULL, ts TEXT NOT NULL,"
                " projected INTEGER NOT NULL DEFAULT 0,"
                " FOREIGN KEY(job_id) REFERENCES jobs(job_id));"
                "CREATE INDEX IF NOT EXISTS idx_chat_job_events "
                "ON job_events(job_id, seq);"
            )
            columns = {
                str(row["name"]) for row in conn.execute("PRAGMA table_info(jobs)")
            }
            if "worker_id" not in columns:
                conn.execute("ALTER TABLE jobs ADD COLUMN worker_id TEXT")
            if "heartbeat_at" not in columns:
                conn.execute("ALTER TABLE jobs ADD COLUMN heartbeat_at TEXT")
            if "cancel_requested" not in columns:
                conn.execute(
                    "ALTER TABLE jobs ADD COLUMN cancel_requested INTEGER "
                    "NOT NULL DEFAULT 0"
                )
            if "context_seq" not in columns:
                conn.execute(
                    "ALTER TABLE jobs ADD COLUMN context_seq INTEGER"
                )
            if "run_id" not in columns:
                conn.execute("ALTER TABLE jobs ADD COLUMN run_id TEXT")
            if "project" not in columns:
                conn.execute("ALTER TABLE jobs ADD COLUMN project TEXT")
            if "run_inbox_enqueued" not in columns:
                conn.execute(
                    "ALTER TABLE jobs ADD COLUMN run_inbox_enqueued INTEGER "
                    "NOT NULL DEFAULT 0"
                )
            if "run_result_enqueued" not in columns:
                conn.execute(
                    "ALTER TABLE jobs ADD COLUMN run_result_enqueued INTEGER "
                    "NOT NULL DEFAULT 0"
                )
            for column in (
                "run_snapshot_source",
                "run_snapshot_path",
                "run_snapshot_head",
                "run_snapshot_fingerprint",
            ):
                if column not in columns:
                    conn.execute(f"ALTER TABLE jobs ADD COLUMN {column} TEXT")
            event_columns = {
                str(row["name"])
                for row in conn.execute("PRAGMA table_info(job_events)")
            }
            if "projected" not in event_columns:
                conn.execute(
                    "ALTER TABLE job_events ADD COLUMN projected INTEGER "
                    "NOT NULL DEFAULT 0"
                )
            if "audited" not in event_columns:
                conn.execute(
                    "ALTER TABLE job_events ADD COLUMN audited INTEGER "
                    "NOT NULL DEFAULT 0"
                )
            conn.commit()

    def create(
        self, session_id: str, message: str, mode: str, idempotency_key: str,
        *, context_seq: int | None = None, run_id: str | None = None,
        project: str | None = None,
    ) -> tuple[dict[str, Any], bool]:
        """Atomar anlegen; wiederholter Key liefert den bestehenden Job."""
        now = _now()
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM jobs WHERE session_id=? AND idempotency_key=?",
                (session_id, idempotency_key),
            ).fetchone()
            if row:
                if row["message"] != message or row["mode"] != mode:
                    conn.rollback()
                    raise IdempotencyConflict(
                        "idempotency_key wurde bereits fuer eine andere Anfrage verwendet",
                    )
                conn.commit()
                return dict(row), False
            job_id = uuid.uuid4().hex
            conn.execute(
                "INSERT INTO jobs(job_id,session_id,idempotency_key,message,"
                "mode,state,created_at,updated_at,context_seq,run_id,project) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (job_id, session_id, idempotency_key, message, mode,
                 "queued", now, now,
                 None if context_seq is None else max(0, context_seq),
                 run_id, project),
            )
            conn.execute(
                "INSERT INTO job_events(job_id,kind,payload,ts) VALUES(?,?,?,?)",
                (job_id, "queued", json.dumps({"message": message}), now),
            )
            row = conn.execute(
                "SELECT * FROM jobs WHERE job_id=?", (job_id,),
            ).fetchone()
            conn.commit()
        assert row is not None
        return dict(row), True

    def succeeded_for_session(self, session_id: str) -> list[dict[str, Any]]:
        """Liefert erfolgreiche Jobs fuer idempotente Session-Reconciliation."""
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE session_id=? AND state='succeeded' "
                "ORDER BY rowid",
                (session_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def terminal_for_session(self, session_id: str) -> list[dict[str, Any]]:
        """Liefert beendete Jobs fuer Branch-Bereinigung."""
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT job_id,state FROM jobs WHERE session_id=? "
                "AND state IN ('succeeded','failed','cancelled') ORDER BY rowid",
                (session_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def queued(self) -> list[dict[str, Any]]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE state='queued' ORDER BY rowid",
            ).fetchall()
        return [dict(row) for row in rows]

    def pending_run_inbox(
        self,
        project: str,
        *,
        limit: int = 500,
        after_rowid: int = 0,
    ) -> list[dict[str, Any]]:
        """Returns a stable page of run-bound jobs with unfinished handoffs."""
        if limit < 1:
            return []
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT rowid AS outbox_seq,job_id,session_id,mode,context_seq,run_id "
                "FROM jobs WHERE project=? AND run_id IS NOT NULL "
                "AND run_inbox_enqueued=0 AND rowid>? ORDER BY rowid LIMIT ?",
                (project, max(0, after_rowid), limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def mark_run_inbox_enqueued(self, job_id: str) -> bool:
        """Marks the outbox delivered only after the idempotent inbox write."""
        with closing(self._connect()) as conn:
            cur = conn.execute(
                "UPDATE jobs SET run_inbox_enqueued=1,updated_at=? "
                "WHERE job_id=? AND run_inbox_enqueued=0",
                (_now(), job_id),
            )
            conn.commit()
            return cur.rowcount == 1

    def pending_run_results(
        self,
        project: str,
        *,
        limit: int = 500,
        after_rowid: int = 0,
    ) -> list[dict[str, Any]]:
        """Returns terminal run-bound jobs whose result handoff is pending."""
        if limit < 1:
            return []
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT rowid AS outbox_seq,job_id,session_id,mode,context_seq,"
                "run_id,state,answer,error FROM jobs WHERE project=? "
                "AND run_id IS NOT NULL AND run_inbox_enqueued=1 "
                "AND run_result_enqueued=0 "
                "AND state IN ('succeeded','failed','cancelled') "
                "AND rowid>? ORDER BY rowid LIMIT ?",
                (project, max(0, after_rowid), limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def mark_run_result_enqueued(self, job_id: str) -> bool:
        """Marks a terminal-result outbox delivered after the inbox write."""
        with closing(self._connect()) as conn:
            cur = conn.execute(
                "UPDATE jobs SET run_result_enqueued=1,updated_at=? "
                "WHERE job_id=? AND run_result_enqueued=0 "
                "AND state IN ('succeeded','failed','cancelled')",
                (_now(), job_id),
            )
            conn.commit()
            return cur.rowcount == 1

    def set_run_snapshot(
        self,
        job_id: str,
        source: Path,
        snapshot_path: Path,
        head: str,
        fingerprint: str,
    ) -> bool:
        """Attach one immutable checkpoint snapshot to a queued run-bound job."""
        values = (
            str(Path(source).resolve()),
            str(Path(snapshot_path).resolve()),
            head,
            fingerprint,
        )
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT state,run_id,run_snapshot_source,run_snapshot_path,"
                "run_snapshot_head,run_snapshot_fingerprint "
                "FROM jobs WHERE job_id=?",
                (job_id,),
            ).fetchone()
            if row is None or row["state"] != "queued" or not row["run_id"]:
                conn.rollback()
                return False
            previous = tuple(row[key] for key in (
                "run_snapshot_source",
                "run_snapshot_path",
                "run_snapshot_head",
                "run_snapshot_fingerprint",
            ))
            if any(value is not None for value in previous) and previous != values:
                conn.rollback()
                return False
            conn.execute(
                "UPDATE jobs SET run_snapshot_source=?,run_snapshot_path=?,"
                "run_snapshot_head=?,run_snapshot_fingerprint=?,updated_at=? "
                "WHERE job_id=? AND state='queued'",
                (*values, _now(), job_id),
            )
            conn.commit()
            return True

    def fail_queued(
        self,
        job_id: str,
        error: str,
        *,
        reason: str = "run_snapshot_failed",
    ) -> bool:
        """Finish an unstarted job with a durable handoff failure."""
        now = _now()
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            cur = conn.execute(
                "UPDATE jobs SET state='failed',error=?,updated_at=? "
                "WHERE job_id=? AND state='queued'",
                (error, now, job_id),
            )
            if cur.rowcount:
                conn.execute(
                    "INSERT INTO job_events(job_id,kind,payload,ts) "
                    "VALUES(?,?,?,?)",
                    (
                        job_id,
                        "failed",
                        json.dumps({"error": error, "reason": reason}),
                        now,
                    ),
                )
            conn.commit()
            return cur.rowcount == 1

    def claim(self, job_id: str, worker_id: str = "test-worker") -> bool:
        """Beansprucht atomar einen Job; Session-Kontext bleibt pro Job isoliert."""
        now = _now()
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            job = conn.execute(
                "SELECT session_id FROM jobs "
                "WHERE job_id=? AND state='queued'",
                (job_id,),
            ).fetchone()
            if job is None:
                conn.commit()
                return False
            cur = conn.execute(
                "UPDATE jobs SET state='running',updated_at=?,worker_id=?,"
                "heartbeat_at=? WHERE job_id=? AND state='queued'",
                (now, worker_id, now, job_id),
            )
            if cur.rowcount:
                conn.execute(
                    "INSERT INTO job_events(job_id,kind,payload,ts) "
                    "VALUES(?,?,?,?)",
                    (job_id, "started", "{}", now),
                )
            conn.commit()
            return cur.rowcount == 1

    def request_cancel(
        self, job_id: str, session_id: str,
    ) -> dict[str, Any] | None:
        """Bricht queued sofort ab oder fordert kooperativen Worker-Abbruch an."""
        now = _now()
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT state,cancel_requested FROM jobs "
                "WHERE job_id=? AND session_id=?",
                (job_id, session_id),
            ).fetchone()
            if row is None:
                conn.commit()
                return None
            state = str(row["state"])
            if state == "queued":
                conn.execute(
                    "UPDATE jobs SET state='cancelled',updated_at=? "
                    "WHERE job_id=? AND state='queued'",
                    (now, job_id),
                )
                conn.execute(
                    "INSERT INTO job_events(job_id,kind,payload,ts) "
                    "VALUES(?,?,?,?)",
                    (job_id, "cancelled", json.dumps({"reason": "cancelled_queued"}), now),
                )
                state = "cancelled"
            elif state == "running" and not row["cancel_requested"]:
                conn.execute(
                    "UPDATE jobs SET cancel_requested=1,updated_at=? "
                    "WHERE job_id=? AND state='running'",
                    (now, job_id),
                )
                conn.execute(
                    "INSERT INTO job_events(job_id,kind,payload,ts) "
                    "VALUES(?,?,?,?)",
                    (job_id, "cancel_requested", "{}", now),
                )
                state = "cancelling"
            elif state == "running":
                state = "cancelling"
            conn.commit()
            return {"job_id": job_id, "state": state}

    def cancellation_requested(self, job_id: str, worker_id: str) -> bool:
        """Beendet stale Worker fail-closed bei Cancel oder verlorenem Lease."""
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT state,worker_id,cancel_requested FROM jobs WHERE job_id=?",
                (job_id,),
            ).fetchone()
        return (
            row is None
            or row["state"] != "running"
            or row["worker_id"] != worker_id
            or bool(row["cancel_requested"])
        )

    def heartbeat(self, job_id: str, worker_id: str) -> bool:
        """Erneuert die Lease nur fuer den Worker, der den Job beansprucht hat."""
        now = _now()
        with closing(self._connect()) as conn:
            cur = conn.execute(
                "UPDATE jobs SET heartbeat_at=?,updated_at=? "
                "WHERE job_id=? AND state='running' AND worker_id=?",
                (now, now, job_id, worker_id),
            )
            conn.commit()
            return cur.rowcount == 1

    def recover_abandoned_jobs(
        self,
        *,
        lease_seconds: int = _WORKER_LEASE_SECONDS,
        now: datetime | None = None,
    ) -> int:
        """Markiert Jobs mit abgelaufener Worker-Lease als fehlgeschlagen."""
        current = now or datetime.now(UTC)
        cutoff = (current - timedelta(seconds=lease_seconds)).isoformat(
            timespec="milliseconds",
        )
        timestamp = current.isoformat(timespec="milliseconds")
        error = "Worker-Lease abgelaufen; Job nach Prozessunterbrechung beendet."
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            rows = conn.execute(
                "SELECT job_id FROM jobs WHERE state='running' "
                "AND COALESCE(heartbeat_at,updated_at) < ?",
                (cutoff,),
            ).fetchall()
            for row in rows:
                job_id = str(row["job_id"])
                cur = conn.execute(
                    "UPDATE jobs SET state='failed',error=?,updated_at=?,"
                    "worker_id=NULL WHERE job_id=? AND state='running' "
                    "AND COALESCE(heartbeat_at,updated_at) < ?",
                    (error, timestamp, job_id, cutoff),
                )
                if cur.rowcount:
                    conn.execute(
                        "INSERT INTO job_events(job_id,kind,payload,ts) "
                        "VALUES(?,?,?,?)",
                        (
                            job_id, "failed",
                            json.dumps({"error": error, "reason": "worker_lease_expired"}),
                            timestamp,
                        ),
                    )
            conn.commit()
            return len(rows)

    def append_event(
        self, job_id: str, kind: str, payload: dict[str, Any] | None = None,
    ) -> int:
        now = _now()
        with closing(self._connect()) as conn:
            cur = conn.execute(
                "INSERT INTO job_events(job_id,kind,payload,ts) VALUES(?,?,?,?)",
                (job_id, kind, json.dumps(payload or {}, ensure_ascii=False), now),
            )
            conn.execute(
                "UPDATE jobs SET updated_at=? WHERE job_id=?",
                (now, job_id),
            )
            conn.commit()
            return int(cur.lastrowid or 0)

    def project_pending_events(
        self, session_id: str | None = None, *,
        job_id: str | None = None, limit: int = 500,
    ) -> int:
        """Projiziert Run-gebundene Job-Events idempotent aus SQLite nach JSONL."""
        from werkstatt.audit import audit
        from werkstatt.projection import Projector

        projector = Projector()
        try:
            projector.tail()
            with closing(self._connect()) as conn:
                conn.execute(
                    "UPDATE job_events SET projected=1 "
                    "WHERE audited=1 AND projected=0"
                )
                conn.commit()
        except (OSError, sqlite3.Error, ValueError):
            pass

        sql = (
            "SELECT e.seq,e.job_id,e.kind,e.payload,e.ts,"
            "j.project,j.session_id,j.run_id "
            "FROM job_events e JOIN jobs j ON j.job_id=e.job_id "
            "WHERE e.audited=0 AND j.project IS NOT NULL AND j.run_id IS NOT NULL"
        )
        params: list[Any] = []
        if session_id is not None:
            sql += " AND j.session_id=?"
            params.append(session_id)
        if job_id is not None:
            sql += " AND e.job_id=?"
            params.append(job_id)
        sql += " ORDER BY e.seq LIMIT ?"
        params.append(max(1, limit))
        with closing(self._connect()) as conn:
            rows = conn.execute(sql, params).fetchall()
        if not rows:
            return 0

        audited = 0
        statuses = {
            "queued": "queued",
            "started": "running",
            "succeeded": "ok",
            "failed": "failed",
            "cancelled": "cancelled",
            "cancel_requested": "running",
            "branch_cleanup_failed": "failed",
            "run_snapshot_cleanup_failed": "failed",
        }
        for row in rows:
            event_id = f"chat-job:{row['job_id']}:{row['seq']}"
            # The JSONL timeline is git-visible. Persist lifecycle metadata,
            # never prompts, assistant text, tool arguments, or tool results.
            event_payload = {
                "job_id": row["job_id"],
                "session_id": row["session_id"],
                "job_event_seq": row["seq"],
                "job_event_kind": row["kind"],
                "status": statuses.get(str(row["kind"]), "running"),
            }
            try:
                audit_kind = (
                    "chat_job_run_snapshot_cleanup_failed"
                    if row["kind"] == "run_snapshot_cleanup_failed"
                    else f"chat_job_{row['kind']}"
                )
                written = audit(
                    audit_kind,
                    event_payload,
                    Path("."),
                    str(row["project"]),
                    run_id=str(row["run_id"]),
                    event_id=event_id,
                )
                if not written:
                    break
            except (OSError, TypeError, ValueError):
                break

            read_model_ok = False
            try:
                projector.tail()
                read_model_ok = True
            except (OSError, sqlite3.Error, ValueError):
                pass
            with closing(self._connect()) as conn:
                conn.execute(
                    "UPDATE job_events SET audited=1,projected=? "
                    "WHERE job_id=? AND seq=?",
                    (int(read_model_ok), row["job_id"], row["seq"]),
                )
                conn.commit()
            audited += 1
        return audited

    def finish(
        self, job_id: str, *, answer: str | None = None,
        error: str | None = None, cancelled: bool = False,
    ) -> bool:
        now = _now()
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT cancel_requested FROM jobs "
                "WHERE job_id=? AND state='running'",
                (job_id,),
            ).fetchone()
            if row is None:
                conn.commit()
                return False
            was_cancelled = cancelled or bool(row["cancel_requested"])
            state = "cancelled" if was_cancelled else (
                "failed" if error is not None else "succeeded"
            )
            error = (
                "Auftrag abgebrochen." if was_cancelled else error
            )
            payload = (
                {"reason": "cancelled"} if was_cancelled
                else {"error": error} if error is not None
                else {"answer": answer or ""}
            )
            cur = conn.execute(
                "UPDATE jobs SET state=?,answer=?,error=?,updated_at=?,"
                "worker_id=NULL WHERE job_id=? AND state='running'",
                (state, answer, error, now, job_id),
            )
            if cur.rowcount:
                conn.execute(
                    "INSERT INTO job_events(job_id,kind,payload,ts) "
                    "VALUES(?,?,?,?)",
                    (job_id, state, json.dumps(payload, ensure_ascii=False), now),
                )
            conn.commit()
            return cur.rowcount == 1

    def active_for_session(self, session_id: str) -> list[dict[str, Any]]:
        """Liefert queued/running Jobs fuer UI-Reconnect in Erstellreihenfolge."""
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE session_id=? "
                "AND state IN ('queued','running') ORDER BY rowid",
                (session_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def reconnect_for_session(
        self, session_id: str, *, failed_limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Aktive Jobs plus letzte Fehler einer Session in Erstellreihenfolge."""
        self.project_pending_events(session_id)
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE session_id=? AND ("
                "state IN ('queued','running') OR job_id IN ("
                "SELECT job_id FROM jobs WHERE session_id=? "
                "AND state IN ('failed','cancelled') "
                "ORDER BY rowid DESC LIMIT ?)) ORDER BY rowid",
                (session_id, session_id, max(0, failed_limit)),
            ).fetchall()
        return [dict(row) for row in rows]

    def get(
        self, job_id: str, *, since_seq: int = 0,
    ) -> dict[str, Any] | None:
        self.project_pending_events(job_id=job_id)
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT * FROM jobs WHERE job_id=?", (job_id,),
            ).fetchone()
            if row is None:
                return None
            events = conn.execute(
                "SELECT seq,kind,payload,ts FROM job_events "
                "WHERE job_id=? AND seq>? ORDER BY seq",
                (job_id, max(0, since_seq)),
            ).fetchall()
        result = dict(row)
        result["events"] = []
        for event in events:
            try:
                payload = json.loads(event["payload"])
            except json.JSONDecodeError:
                payload = {}
            result["events"].append({
                "seq": event["seq"],
                "kind": event["kind"],
                "payload": payload,
                "ts": event["ts"],
                "job_id": job_id,
                "session_id": result["session_id"],
                "run_id": result.get("run_id"),
            })
        return result


def _run_job(
    db_path: Path, project: str, project_dir: Path, job_id: str,
) -> bool:
    store = ChatJobStore(db_path)
    if not store.claim(job_id, _WORKER_ID):
        return False
    job = store.get(job_id)
    if job is None:
        return True

    from werkstatt.chat_agent import ChatCancelled, chat_loop
    from werkstatt.chat_session import ChatSession

    def event(kind: str, **payload: Any) -> None:
        store.append_event(job_id, kind, payload)

    def cancel_check() -> bool:
        return store.cancellation_requested(job_id, _WORKER_ID)

    heartbeat_stop = threading.Event()

    def maintain_lease() -> None:
        while not heartbeat_stop.wait(_WORKER_HEARTBEAT_SECONDS):
            try:
                if not store.heartbeat(job_id, _WORKER_ID):
                    return
            except sqlite3.Error:
                continue

    heartbeat_thread = threading.Thread(
        target=maintain_lease,
        name=f"werkstatt-chat-heartbeat-{job_id[:8]}",
        daemon=True,
    )
    parent_session: ChatSession | None = None
    worker_session: ChatSession | None = None
    heartbeat_thread.start()
    try:
        chat_project_dir = Path(project_dir)
        if job.get("run_id"):
            from werkstatt.run_snapshot import validate_project_snapshot

            source_value = job.get("run_snapshot_source")
            snapshot_value = job.get("run_snapshot_path")
            if (
                not source_value
                or not snapshot_value
                or not job.get("run_snapshot_head")
                or not job.get("run_snapshot_fingerprint")
            ):
                raise RuntimeError(
                    "Run-gebundener Chatjob hat keinen Checkpoint-Snapshot.",
                )
            snapshot = validate_project_snapshot(
                Path(snapshot_value),
                Path(source_value),
                project,
                str(job["run_id"]),
                job_id,
            )
            if (
                snapshot.head != job["run_snapshot_head"]
                or snapshot.fingerprint != job["run_snapshot_fingerprint"]
            ):
                raise RuntimeError("Run-Snapshot-Metadaten stimmen nicht ueberein.")
            chat_project_dir = snapshot.path
        parent_session = ChatSession(project, job["session_id"])
        context_seq = job.get("context_seq")
        worker_session = parent_session.snapshot_to(
            job_id,
            at_seq=None if context_seq is None else int(context_seq),
        )
        answer = chat_loop(
            worker_session,
            job["message"],
            mode=job["mode"],
            project_dir=chat_project_dir,
            cancel_check=cancel_check,
            on_chunk=lambda text: event("chunk", text=text),
            on_tool_call=lambda name, args: event(
                "tool_call", name=name, args=args,
            ),
            on_tool_result=lambda name, content: event(
                "tool_result", name=name, content=content,
            ),
            request_id=job_id,
            origin_session_id=str(job["session_id"]),
        )
        if store.finish(job_id, answer=answer):
            parent_session.append_job_turn(job_id, job["message"], answer)
    except ChatCancelled:
        store.finish(job_id, cancelled=True)
    except Exception as exc:
        store.finish(
            job_id, error=f"{type(exc).__name__}: {exc}",
        )
    finally:
        if parent_session is not None and worker_session is not None:
            try:
                parent_session.delete_snapshot(job_id)
            except (OSError, sqlite3.Error) as exc:
                store.append_event(
                    job_id, "branch_cleanup_failed", {"error": str(exc)},
                )
        if job.get("run_id") and job.get("run_snapshot_path"):
            try:
                from werkstatt.run_snapshot import remove_project_snapshot

                remove_project_snapshot(
                    Path(job["run_snapshot_path"]),
                    project,
                    str(job["run_id"]),
                    job_id,
                )
            except (OSError, RuntimeError, ValueError) as exc:
                store.append_event(
                    job_id, "run_snapshot_cleanup_failed", {"error": str(exc)},
                )
        heartbeat_stop.set()
        heartbeat_thread.join(timeout=_WORKER_HEARTBEAT_SECONDS + 1)
        resume_chat_jobs(project, project_dir, db_path=db_path)
    return True


def _dispatch_pending(
    db_path: Path, project: str, project_dir: Path,
) -> None:
    store = ChatJobStore(db_path)
    store.recover_abandoned_jobs()
    for job in store.queued():
        if job.get("run_id"):
            if (
                not job.get("run_inbox_enqueued")
                or not job.get("run_snapshot_source")
                or not job.get("run_snapshot_path")
                or not job.get("run_snapshot_head")
                or not job.get("run_snapshot_fingerprint")
                or not job.get("project")
            ):
                continue
            try:
                from werkstatt.event_store import EventStore

                acknowledged = EventStore().run_message_acknowledged(
                    str(job["project"]),
                    str(job["run_id"]),
                    f"chat-job:{job['job_id']}",
                )
            except (OSError, RuntimeError, sqlite3.Error, ValueError):
                acknowledged = False
            if not acknowledged:
                continue
        key = f"{db_path.resolve()}:{job['job_id']}"
        with _FUTURES_LOCK:
            current = _FUTURES.get(key)
            if current is not None and not current.done():
                continue
            future = _EXECUTOR.submit(
                _run_job, db_path, project, project_dir, job["job_id"],
            )
            _FUTURES[key] = future
            future.add_done_callback(
                _future_cleanup_callback(key, db_path, project, project_dir),
            )



def _forget_future(key: str, future: Future[bool]) -> None:
    """Entfernt abgeschlossene Futures ohne neuere Eintraege zu loeschen."""
    with _FUTURES_LOCK:
        if _FUTURES.get(key) is future:
            _FUTURES.pop(key, None)


def _future_cleanup_callback(
    key: str, db_path: Path, project: str, project_dir: Path,
) -> Callable[[Future[bool]], None]:
    """Bereinigt Futures und versucht nach einem Claim-Rennen erneut zu dispatchen."""
    def cleanup(future: Future[bool]) -> None:
        _forget_future(key, future)
        try:
            claim_lost = future.result() is False
        except Exception:
            claim_lost = False
        if claim_lost:
            _dispatch_pending(db_path, project, project_dir)

    return cleanup

def sync_completed_job_turns(
    project: str, session_id: str, *, db_path: Path | None = None,
) -> int:
    """Reconciles successful jobs into the parent transcript after a crash."""
    path = Path(db_path) if db_path else _db_path(project)
    store = ChatJobStore(path)
    completed = store.succeeded_for_session(session_id)
    from werkstatt.chat_session import ChatSession

    session = ChatSession(project, session_id)
    added = 0
    for job in completed:
        job_id = str(job["job_id"])
        if job.get("answer") is not None and session.append_job_turn(
            job_id, str(job["message"]), str(job["answer"]),
        ):
            added += 1
    for job in store.terminal_for_session(session_id):
        session.delete_snapshot(str(job["job_id"]))
    return added


def reconcile_run_inbox(
    project: str,
    *,
    db_path: Path | None = None,
    event_store: Any | None = None,
    limit: int = 500,
) -> int:
    """Replays the chat-job outbox into the run inbox using stable message IDs."""
    path = Path(db_path) if db_path else _db_path(project)
    store = ChatJobStore(path)
    if event_store is None:
        from werkstatt.event_store import EventStore

        event_store = EventStore()

    reconciled = 0
    after_rowid = 0
    while True:
        jobs = store.pending_run_inbox(
            project, limit=limit, after_rowid=after_rowid,
        )
        if not jobs:
            break
        after_rowid = int(jobs[-1]["outbox_seq"])
        for job in jobs:
            run_id = str(job["run_id"])
            if event_store.get_run_record(project, run_id) is None:
                continue
            job_id = str(job["job_id"])
            event_store.enqueue_run_message(
                project,
                run_id,
                f"chat-job:{job_id}",
                "job_notice",
                {
                    "job_id": job_id,
                    "session_id": str(job["session_id"]),
                    "mode": str(job["mode"]),
                    "context_seq": job["context_seq"],
                },
            )
            if store.mark_run_inbox_enqueued(job_id):
                reconciled += 1

    after_rowid = 0
    while True:
        results = store.pending_run_results(
            project, limit=limit, after_rowid=after_rowid,
        )
        if not results:
            return reconciled
        after_rowid = int(results[-1]["outbox_seq"])
        for result in results:
            run_id = str(result["run_id"])
            if event_store.get_run_record(project, run_id) is None:
                continue
            job_id = str(result["job_id"])
            answer = str(result.get("answer") or "")
            error = str(result.get("error") or "")
            payload = {
                "job_id": job_id,
                "session_id": str(result["session_id"]),
                "mode": str(result["mode"]),
                "context_seq": result["context_seq"],
                "state": str(result["state"]),
                "answer_sha256": hashlib.sha256(
                    answer.encode("utf-8"),
                ).hexdigest() if answer else None,
                "error_sha256": hashlib.sha256(
                    error.encode("utf-8"),
                ).hexdigest() if error else None,
            }
            event_store.enqueue_run_message(
                project,
                run_id,
                f"chat-job:{job_id}:result",
                "job_result_notice",
                payload,
            )
            if store.mark_run_result_enqueued(job_id):
                reconciled += 1


def resume_chat_jobs(
    project: str, project_dir: Path, *, db_path: Path | None = None,
) -> None:
    """Reconciles run notices/results before dispatching after restart."""
    path = Path(db_path) if db_path else _db_path(project)
    # Expired workers become terminal before their result outbox is replayed.
    ChatJobStore(path).recover_abandoned_jobs()
    reconcile_run_inbox(project, db_path=path)
    _dispatch_pending(path, project, Path(project_dir))


def fail_uncheckpointed_jobs_for_inactive_run(
    project: str,
    active_run_id: str | None,
    *,
    db_path: Path | None = None,
    event_store: Any | None = None,
) -> int:
    """Fail queued run jobs whose run ended before a durable safe handoff.

    Jobs with a fully bound snapshot and an acknowledged inbox message remain
    eligible for replay even after their originating loop has exited. Jobs
    attached to the active run, including an ambiguous/orphaned run, are left
    untouched. Unknown checkpoint state is treated as unproven and reported
    as a visible failure rather than left queued forever.
    """
    store = ChatJobStore(Path(db_path) if db_path else _db_path(project))
    if event_store is None:
        from werkstatt.event_store import EventStore

        event_store = EventStore()

    failed = 0
    for job in store.queued():
        run_id = job.get("run_id")
        if not isinstance(run_id, str) or not run_id or run_id == active_run_id:
            continue
        if job.get("project") != project:
            continue
        snapshot_bound = all(
            isinstance(job.get(field), str) and bool(job[field])
            for field in (
                "run_snapshot_source",
                "run_snapshot_path",
                "run_snapshot_head",
                "run_snapshot_fingerprint",
            )
        )
        try:
            acknowledged = event_store.run_message_acknowledged(
                project, run_id, f"chat-job:{job['job_id']}",
            )
        except (OSError, RuntimeError, sqlite3.Error, ValueError):
            acknowledged = False
        if snapshot_bound and acknowledged:
            continue
        error = (
            f"Der zugeordnete Run {run_id} endete, bevor die Chat-Anfrage "
            "an einem bestaetigten Checkpoint mit stabilem Snapshot "
            "uebernommen wurde. Bitte sende den Auftrag erneut."
        )
        if store.fail_queued(
            str(job["job_id"]),
            error,
            reason="run_ended_before_checkpoint",
        ):
            failed += 1
    return failed


def enqueue_chat_job(
    project: str,
    project_dir: Path,
    session_id: str,
    message: str,
    mode: str,
    idempotency_key: str,
    *,
    db_path: Path | None = None,
    context_seq: int | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Persists a job with a fixed context watermark and reconciles its inbox."""
    path = Path(db_path) if db_path else _db_path(project)
    store = ChatJobStore(path)
    job, created = store.create(
        session_id, message, mode, idempotency_key,
        context_seq=context_seq,
        run_id=run_id,
        project=project,
    )
    reconcile_run_inbox(project, db_path=path)
    _dispatch_pending(path, project, Path(project_dir))
    return {"job": job, "created": created}
