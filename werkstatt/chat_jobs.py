"""Persistente Hintergrundjobs fuer Projekt-Chat (OP-397).

Der HTTP-Request nimmt einen Auftrag nur an. Ein Worker fuehrt den
read-only Chat-Aufruf aus; Status und Ereignisse bleiben in SQLite
abrufbar und koennen nach einem UI-Reconnect wieder abgespielt werden.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from werkstatt.paths import werkstatt_home

__all__ = ["ChatJobStore", "enqueue_chat_job"]

_EXECUTOR = ThreadPoolExecutor(max_workers=8, thread_name_prefix="werkstatt-chat")
_FUTURES: dict[str, Future[None]] = {}
_FUTURES_LOCK = threading.Lock()


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
                " updated_at TEXT NOT NULL,"
                " UNIQUE(session_id, idempotency_key));"
                "CREATE TABLE IF NOT EXISTS job_events ("
                " seq INTEGER PRIMARY KEY AUTOINCREMENT,"
                " job_id TEXT NOT NULL, kind TEXT NOT NULL,"
                " payload TEXT NOT NULL, ts TEXT NOT NULL,"
                " FOREIGN KEY(job_id) REFERENCES jobs(job_id));"
                "CREATE INDEX IF NOT EXISTS idx_chat_job_events "
                "ON job_events(job_id, seq);"
            )
            conn.commit()

    def create(
        self, session_id: str, message: str, mode: str, idempotency_key: str,
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
                conn.commit()
                return dict(row), False
            job_id = uuid.uuid4().hex
            conn.execute(
                "INSERT INTO jobs(job_id,session_id,idempotency_key,message,"
                "mode,state,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                (job_id, session_id, idempotency_key, message, mode,
                 "queued", now, now),
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

    def queued(self) -> list[dict[str, Any]]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE state='queued' ORDER BY created_at,job_id",
            ).fetchall()
        return [dict(row) for row in rows]

    def claim(self, job_id: str) -> bool:
        now = _now()
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            cur = conn.execute(
                "UPDATE jobs SET state='running',updated_at=? "
                "WHERE job_id=? AND state='queued'",
                (now, job_id),
            )
            if cur.rowcount:
                conn.execute(
                    "INSERT INTO job_events(job_id,kind,payload,ts) "
                    "VALUES(?,?,?,?)",
                    (job_id, "started", "{}", now),
                )
            conn.commit()
            return cur.rowcount == 1

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
        error: str | None = None,
    ) -> bool:
        state = "failed" if error is not None else "succeeded"
        now = _now()
        payload = {"error": error} if error is not None else {"answer": answer or ""}
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            cur = conn.execute(
                "UPDATE jobs SET state=?,answer=?,error=?,updated_at=? "
                "WHERE job_id=? AND state='running'",
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
                "AND state IN ('queued','running') ORDER BY created_at,job_id",
                (session_id,),
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
) -> None:
    store = ChatJobStore(db_path)
    if not store.claim(job_id):
        return
    job = store.get(job_id)
    if job is None:
        return

    from werkstatt.chat_agent import chat_loop
    from werkstatt.chat_session import ChatSession

    def event(kind: str, **payload: Any) -> None:
        store.append_event(job_id, kind, payload)

    try:
        answer = chat_loop(
            ChatSession(project, job["session_id"]),
            job["message"],
            mode=job["mode"],
            project_dir=project_dir,
            on_chunk=lambda text: event("chunk", text=text),
            on_tool_call=lambda name, args: event(
                "tool_call", name=name, args=args,
            ),
            on_tool_result=lambda name, content: event(
                "tool_result", name=name, content=content,
            ),
        )
        store.finish(job_id, answer=answer)
    except Exception as exc:
        store.finish(
            job_id, error=f"{type(exc).__name__}: {exc}",
        )


def _dispatch_pending(
    db_path: Path, project: str, project_dir: Path,
) -> None:
    store = ChatJobStore(db_path)
    for job in store.queued():
        key = f"{db_path.resolve()}:{job['job_id']}"
        with _FUTURES_LOCK:
            current = _FUTURES.get(key)
            if current is not None and not current.done():
                continue
            _FUTURES[key] = _EXECUTOR.submit(
                _run_job, db_path, project, project_dir, job["job_id"],
            )


def resume_chat_jobs(
    project: str, project_dir: Path, *, db_path: Path | None = None,
) -> None:
    """Re-dispatch queued jobs after a server restart or client reconnect."""
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
) -> dict[str, Any]:
    """Persistiert den Job und startet queued Jobs ausserhalb des Requests."""
    path = Path(db_path) if db_path else _db_path(project)
    store = ChatJobStore(path)
    job, created = store.create(
        session_id, message, mode, idempotency_key,
    )
    _dispatch_pending(path, project, Path(project_dir))
    return {"job": job, "created": created}
