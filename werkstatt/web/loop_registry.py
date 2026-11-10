"""Persistent registry for web-started loop processes.

The web server may restart while a loop keeps running. This registry keeps
ownership and process identity outside the server process so another worker
can recover control without starting a second writer.
"""
from __future__ import annotations

import os
import signal
import sqlite3
import subprocess
import time
from contextlib import closing
from pathlib import Path
from typing import Any

_STARTING_TTL_SECONDS = 60.0


def _process_snapshot(pid: int) -> tuple[str, str] | None:
    """Return Linux process start time and state, avoiding PID-reuse control."""
    stat_path = Path("/proc") / str(pid) / "stat"
    try:
        stat = stat_path.read_text(encoding="ascii")
    except (OSError, UnicodeError):
        return None
    # comm (field 2) may contain spaces or parentheses; fields after the final
    # ')' start at field 3 (state), so starttime (field 22) is offset 19.
    end_comm = stat.rfind(")")
    if end_comm < 0:
        return None
    fields = stat[end_comm + 1 :].split()
    if len(fields) <= 19:
        return None
    return fields[19], fields[0]


def _pid_alive(pid: int | None, identity: str | None = None) -> bool:
    if pid is None or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass
    except OSError:
        return False

    snapshot = _process_snapshot(pid)
    if snapshot is None:
        # On Linux, inability to inspect an expected process identity means
        # we cannot safely signal this PID. Other POSIX platforms use kill(0).
        if identity is not None and os.name == "posix" and Path("/proc").is_dir():
            return False
        return True
    started, state = snapshot
    if state == "Z":
        return False
    return identity is None or started == identity


class LoopProcessRegistry:
    """Cross-worker, restart-safe ownership record for loop subprocesses."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=FULL")
        conn.execute("PRAGMA busy_timeout=10000")
        return conn

    def _init_schema(self) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS loop_processes ("
                "project TEXT PRIMARY KEY, "
                "run_id TEXT NOT NULL, "
                "pid INTEGER, "
                "process_identity TEXT, "
                "state TEXT NOT NULL, "
                "updated_at REAL NOT NULL)"
            )
            conn.commit()

    @staticmethod
    def _record(row: tuple[Any, ...] | None) -> dict[str, Any] | None:
        if row is None:
            return None
        return {
            "project": str(row[0]),
            "run_id": str(row[1]),
            "pid": int(row[2]) if row[2] is not None else None,
            "process_identity": (
                str(row[3]) if row[3] is not None else None
            ),
            "state": str(row[4]),
            "updated_at": float(row[5]),
        }

    def read(self, project: str) -> dict[str, Any] | None:
        """Read state and mark exited or expired reservations idle."""
        now = time.time()
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT project, run_id, pid, process_identity, state, updated_at "
                "FROM loop_processes WHERE project = ?",
                (project,),
            ).fetchone()
            record = self._record(row)
            if record is None:
                conn.commit()
                return None
            state = record["state"]
            expired_start = (
                state == "starting"
                and now - record["updated_at"] > _STARTING_TTL_SECONDS
            )
            dead_process = (
                state in ("running", "paused")
                and not _pid_alive(record["pid"], record["process_identity"])
            )
            if expired_start or dead_process:
                conn.execute(
                    "UPDATE loop_processes SET state='idle', pid=NULL, "
                    "process_identity=NULL, updated_at=? WHERE project=?",
                    (now, project),
                )
                record.update({
                    "state": "idle",
                    "pid": None,
                    "process_identity": None,
                    "updated_at": now,
                })
            conn.commit()
        return record

    def reserve(self, project: str, run_id: str) -> tuple[bool, dict[str, Any] | None]:
        """Atomically reserve a project before spawning its loop."""
        now = time.time()
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT project, run_id, pid, process_identity, state, updated_at "
                "FROM loop_processes WHERE project = ?",
                (project,),
            ).fetchone()
            existing = self._record(row)
            if existing is not None:
                state = existing["state"]
                starting_live = (
                    state == "starting"
                    and now - existing["updated_at"] <= _STARTING_TTL_SECONDS
                )
                process_live = (
                    state in ("running", "paused")
                    and _pid_alive(existing["pid"], existing["process_identity"])
                )
                if starting_live or process_live:
                    conn.commit()
                    return False, existing
            conn.execute(
                "INSERT INTO loop_processes "
                "(project, run_id, pid, process_identity, state, updated_at) "
                "VALUES (?, ?, NULL, NULL, 'starting', ?) "
                "ON CONFLICT(project) DO UPDATE SET "
                "run_id=excluded.run_id, pid=NULL, process_identity=NULL, "
                "state='starting', updated_at=excluded.updated_at",
                (project, run_id, now),
            )
            conn.commit()
        return True, None

    def register(self, project: str, run_id: str, pid: int) -> str | None:
        """Publish the spawned PID only if this request owns the reservation."""
        snapshot = _process_snapshot(pid)
        identity = snapshot[0] if snapshot else None
        with closing(self._connect()) as conn:
            cur = conn.execute(
                "UPDATE loop_processes SET pid=?, process_identity=?, "
                "state='running', updated_at=? "
                "WHERE project=? AND run_id=? AND state='starting'",
                (pid, identity, time.time(), project, run_id),
            )
            conn.commit()
            if cur.rowcount != 1:
                raise RuntimeError("Loop-Reservierung ging vor Registrierung verloren")
        return identity

    def set_state(self, project: str, run_id: str, state: str) -> bool:
        if state not in ("running", "paused", "idle"):
            raise ValueError(f"ungueltiger Loop-Zustand: {state}")
        with closing(self._connect()) as conn:
            cur = conn.execute(
                "UPDATE loop_processes SET state=?, "
                "pid=CASE WHEN ?='idle' THEN NULL ELSE pid END, "
                "process_identity=CASE WHEN ?='idle' THEN NULL "
                "ELSE process_identity END, updated_at=? "
                "WHERE project=? AND run_id=?",
                (state, state, state, time.time(), project, run_id),
            )
            conn.commit()
            return cur.rowcount == 1


class AttachedLoopProcess:
    """Popen-compatible control handle recovered after a web-server restart."""

    def __init__(self, pid: int, process_identity: str | None = None) -> None:
        self.pid = pid
        self.process_identity = process_identity

    def poll(self) -> int | None:
        return None if _pid_alive(self.pid, self.process_identity) else 0

    def wait(self, timeout: float | None = None) -> int:
        deadline = None if timeout is None else time.monotonic() + timeout
        while self.poll() is None:
            if deadline is not None and time.monotonic() >= deadline:
                raise subprocess.TimeoutExpired(["loop", str(self.pid)], timeout)
            time.sleep(0.05)
        return 0

    def terminate(self) -> None:
        os.kill(self.pid, signal.SIGTERM)

    def kill(self) -> None:
        os.kill(self.pid, signal.SIGKILL)


__all__ = ["AttachedLoopProcess", "LoopProcessRegistry"]
