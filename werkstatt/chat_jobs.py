"""Persistente Hintergrundjobs fuer Projekt-Chat (OP-397).

Der HTTP-Request nimmt einen Auftrag nur an. Ein Worker fuehrt den
read-only Chat-Aufruf aus; Status und Ereignisse bleiben in SQLite
abrufbar und koennen nach einem UI-Reconnect wieder abgespielt werden.
"""
from __future__ import annotations

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
                " context_seq INTEGER,"
                " UNIQUE(session_id, idempotency_key));"
                "CREATE TABLE IF NOT EXISTS job_events ("
                " seq INTEGER PRIMARY KEY AUTOINCREMENT,"
                " job_id TEXT NOT NULL, kind TEXT NOT NULL,"
                " payload TEXT NOT NULL, ts TEXT NOT NULL,"
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
            conn.commit()

    def create(
        self, session_id: str, message: str, mode: str, idempotency_key: str,
        *, context_seq: int | None = None,
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
                "mode,state,created_at,updated_at,context_seq) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                (job_id, session_id, idempotency_key, message, mode,
                 "queued", now, now,
                 None if context_seq is None else max(0, context_seq)),
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
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT cancel_requested FROM jobs "
                "WHERE job_id=? AND state='running' AND worker_id=?",
                (job_id, worker_id),
            ).fetchone()
        return bool(row and row["cancel_requested"])

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
                "seq": event["seq"], "kind": event["kind"],
                "payload": payload, "ts": event["ts"],
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
            project_dir=project_dir,
            cancel_check=cancel_check,
            on_chunk=lambda text: event("chunk", text=text),
            on_tool_call=lambda name, args: event(
                "tool_call", name=name, args=args,
            ),
            on_tool_result=lambda name, content: event(
                "tool_result", name=name, content=content,
            ),
            request_id=job_id,
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
        heartbeat_stop.set()
        heartbeat_thread.join(timeout=_WORKER_HEARTBEAT_SECONDS + 1)
        _dispatch_pending(db_path, project, project_dir)
    return True


def _dispatch_pending(
    db_path: Path, project: str, project_dir: Path,
) -> None:
    store = ChatJobStore(db_path)
    store.recover_abandoned_jobs()
    for job in store.queued():
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
    completed = ChatJobStore(path).succeeded_for_session(session_id)
    if not completed:
        return 0
    from werkstatt.chat_session import ChatSession

    session = ChatSession(project, session_id)
    added = 0
    for job in completed:
        job_id = str(job["job_id"])
        if job.get("answer") is not None and session.append_job_turn(
            job_id, str(job["message"]), str(job["answer"]),
        ):
            added += 1
    for job in ChatJobStore(path).terminal_for_session(session_id):
        session.delete_snapshot(str(job["job_id"]))
    return added


def resume_chat_jobs(
    project: str, project_dir: Path, *, db_path: Path | None = None,
) -> None:
    """Re-dispatch queued jobs and expire leases lost in a server restart."""
    path = Path(db_path) if db_path else _db_path(project)
    _dispatch_pending(path, project, Path(project_dir))


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
) -> dict[str, Any]:
    """Persistiert einen Job mit festem Kontext-Wasserstand und dispatcht ihn."""
    path = Path(db_path) if db_path else _db_path(project)
    store = ChatJobStore(path)
    job, created = store.create(
        session_id, message, mode, idempotency_key,
        context_seq=context_seq,
    )
    _dispatch_pending(path, project, Path(project_dir))
    return {"job": job, "created": created}
