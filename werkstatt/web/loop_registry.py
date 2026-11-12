"""Persistent registry for web-started loop processes.

The web server may restart while a loop keeps running. This registry keeps
ownership and process identity outside the server process so another worker
can recover control without starting a second writer.
"""
from __future__ import annotations

import json
import os
import signal
import sqlite3
import subprocess
import sys
import time
from contextlib import closing
from pathlib import Path
from typing import Any

_STARTING_TTL_SECONDS = 60.0
_CONTROL_TRANSITION_TTL_SECONDS = 15.0
_STOP_RETRY_SECONDS = 30.0
_LIVE_STATES = ("running", "paused", "pausing", "resuming", "stopping")
_ALLOWED_TRANSITIONS = {
    ("running", "pausing"),
    ("paused", "resuming"),
    ("running", "stopping"),
    ("paused", "stopping"),
    ("pausing", "running"),
    ("pausing", "paused"),
    ("resuming", "paused"),
    ("resuming", "running"),
    ("stopping", "idle"),
}


def _decode_context(raw: Any) -> dict[str, Any]:
    """Decode persisted start metadata without making registry reads fail."""
    if not isinstance(raw, str):
        return {}
    try:
        value = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


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


def _worker_command_matches(
    argv: list[str],
    project: str,
    run_id: str,
) -> bool:
    """Match the exact CLI identity used by the web-spawned loop."""
    if len(argv) < 3 or argv[1:3] != ["-m", "werkstatt.loop"]:
        return False
    required = (
        ("--project", project),
        ("--run-id", run_id),
    )
    return all(
        any(
            argv[index] == option and argv[index + 1] == value
            for index in range(len(argv) - 1)
        )
        for option, value in required
    )


def _find_run_workers(
    project: str,
    run_id: str,
) -> tuple[list[tuple[int, str]], bool]:
    """Find exact run processes; the bool says whether /proc was fully readable."""
    proc_root = Path("/proc")
    if not proc_root.is_dir():
        return [], False
    try:
        entries = list(proc_root.iterdir())
    except OSError:
        return [], False

    workers: list[tuple[int, str]] = []
    complete = True
    for entry in entries:
        if not entry.name.isdecimal():
            continue
        pid = int(entry.name)
        if pid == os.getpid():
            continue
        snapshot = _process_snapshot(pid)
        if snapshot is None:
            if entry.exists():
                complete = False
            continue
        identity, process_state = snapshot
        if process_state == "Z":
            continue
        try:
            raw = (entry / "cmdline").read_bytes()
        except FileNotFoundError:
            continue
        except OSError:
            complete = False
            continue
        argv = [os.fsdecode(part) for part in raw.split(b"\0") if part]
        if not _worker_command_matches(argv, project, run_id):
            continue
        try:
            if entry.stat().st_uid != os.geteuid():
                complete = False
                continue
            executable = (entry / "exe").resolve(strict=True)
        except FileNotFoundError:
            continue
        except (OSError, RuntimeError):
            complete = False
            continue
        if executable == Path(sys.executable).resolve():
            workers.append((pid, identity))
    return workers, complete


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
        # kill(0) failed for a reason other than ESRCH. The process may still
        # exist but be inaccessible; do not release its writer reservation.
        return True

    snapshot = _process_snapshot(pid)
    if snapshot is None:
        # Existence is known (kill(0) succeeded or was permission-denied),
        # but its identity cannot be checked. Keep the run fail-closed as live.
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
                "updated_at REAL NOT NULL, "
                "context_json TEXT NOT NULL DEFAULT '{}')"
            )
            columns = {
                str(row[1]) for row in conn.execute(
                    "PRAGMA table_info(loop_processes)"
                )
            }
            if "context_json" not in columns:
                conn.execute(
                    "ALTER TABLE loop_processes ADD COLUMN "
                    "context_json TEXT NOT NULL DEFAULT '{}'"
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
            "recovery_issue": (
                "worker_identity_ambiguous" if row[4] == "orphaned" else None
            ),
            "updated_at": float(row[5]),
            "context": _decode_context(row[6] if len(row) > 6 else None),
        }

    def read(self, project: str) -> dict[str, Any] | None:
        """Read state and mark exited or expired reservations idle."""
        now = time.time()
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT project, run_id, pid, process_identity, state, "
                "updated_at, context_json FROM loop_processes WHERE project = ?",
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
            process_snapshot = (
                _process_snapshot(record["pid"])
                if record["pid"] is not None
                else None
            )
            process_alive = _pid_alive(
                record["pid"], record["process_identity"],
            ) if state in _LIVE_STATES else False
            dead_process = state in _LIVE_STATES and not process_alive
            stale_control = (
                state in ("pausing", "resuming")
                and now - record["updated_at"] > _CONTROL_TRANSITION_TTL_SECONDS
                and process_alive
            )
            if stale_control:
                # Recover a worker crash between claiming the transition and
                # publishing its final state from the kernel process status.
                recovered_state = (
                    "paused"
                    if process_snapshot is not None
                    and process_snapshot[1] in ("T", "t")
                    else "running"
                )
                conn.execute(
                    "UPDATE loop_processes SET state=?, updated_at=? "
                    "WHERE project=? AND run_id=? AND state=?",
                    (
                        recovered_state, now, project,
                        record["run_id"], state,
                    ),
                )
                record.update({
                    "state": recovered_state,
                    "updated_at": now,
                })
                state = recovered_state
            if expired_start or state == "orphaned":
                workers, scan_complete = _find_run_workers(
                    project, record["run_id"],
                )
                if len(workers) == 1 and scan_complete:
                    pid, identity = workers[0]
                    conn.execute(
                        "UPDATE loop_processes SET state='running', pid=?, "
                        "process_identity=?, updated_at=? WHERE project=? "
                        "AND run_id=?",
                        (pid, identity, now, project, record["run_id"]),
                    )
                    record.update({
                        "state": "running",
                        "pid": pid,
                        "process_identity": identity,
                        "updated_at": now,
                    })
                    record.pop("recovery_issue", None)
                elif not workers and scan_complete:
                    conn.execute(
                        "UPDATE loop_processes SET state='idle', pid=NULL, "
                        "process_identity=NULL, updated_at=? WHERE project=? "
                        "AND run_id=?",
                        (now, project, record["run_id"]),
                    )
                    record.update({
                        "state": "idle",
                        "pid": None,
                        "process_identity": None,
                        "updated_at": now,
                    })
                    record.pop("recovery_issue", None)
                else:
                    conn.execute(
                        "UPDATE loop_processes SET state='orphaned', pid=NULL, "
                        "process_identity=NULL, updated_at=? WHERE project=? "
                        "AND run_id=?",
                        (now, project, record["run_id"]),
                    )
                    record.update({
                        "state": "orphaned",
                        "pid": None,
                        "process_identity": None,
                        "updated_at": now,
                        "recovery_issue": "worker_identity_ambiguous",
                    })
                state = record["state"]
            elif dead_process:
                conn.execute(
                    "UPDATE loop_processes SET state='idle', pid=NULL, "
                    "process_identity=NULL, updated_at=? WHERE project=? "
                    "AND run_id=?",
                    (now, project, record["run_id"]),
                )
                record.update({
                    "state": "idle",
                    "pid": None,
                    "process_identity": None,
                    "updated_at": now,
                })
            conn.commit()
        return record

    def reserve(
        self,
        project: str,
        run_id: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> tuple[bool, dict[str, Any] | None]:
        """Atomically reserve a project and persist its immutable start context."""
        now = time.time()
        context_json = json.dumps(
            context or {}, ensure_ascii=False, sort_keys=True,
        )
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT project, run_id, pid, process_identity, state, "
                "updated_at, context_json FROM loop_processes WHERE project = ?",
                (project,),
            ).fetchone()
            existing = self._record(row)
            if existing is not None:
                state = existing["state"]
                if state == "orphaned":
                    conn.commit()
                    return False, existing
                starting_live = (
                    state == "starting"
                    and now - existing["updated_at"] <= _STARTING_TTL_SECONDS
                )
                process_live = (
                    state in _LIVE_STATES
                    and _pid_alive(existing["pid"], existing["process_identity"])
                )
                if starting_live or process_live:
                    conn.commit()
                    return False, existing
            conn.execute(
                "INSERT INTO loop_processes "
                "(project, run_id, pid, process_identity, state, updated_at, "
                "context_json) VALUES (?, ?, NULL, NULL, 'starting', ?, ?) "
                "ON CONFLICT(project) DO UPDATE SET "
                "run_id=excluded.run_id, pid=NULL, process_identity=NULL, "
                "state='starting', updated_at=excluded.updated_at, "
                "context_json=excluded.context_json",
                (project, run_id, now, context_json),
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
        if state not in ("running", "paused", "idle", "orphaned"):
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

    def claim_stop(self, project: str, run_id: str) -> bool:
        """Atomically claim a stop or reclaim one abandoned for 30 seconds."""
        now = time.time()
        retry_before = now - _STOP_RETRY_SECONDS
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT state, updated_at FROM loop_processes "
                "WHERE project=? AND run_id=?",
                (project, run_id),
            ).fetchone()
            if row is None:
                conn.commit()
                return False
            state, updated_at = str(row[0]), float(row[1])
            if state in ("running", "paused"):
                cur = conn.execute(
                    "UPDATE loop_processes SET state='stopping', updated_at=? "
                    "WHERE project=? AND run_id=? AND state=?",
                    (now, project, run_id, state),
                )
            elif state == "stopping" and updated_at < retry_before:
                cur = conn.execute(
                    "UPDATE loop_processes SET updated_at=? "
                    "WHERE project=? AND run_id=? AND state='stopping' "
                    "AND updated_at=?",
                    (now, project, run_id, updated_at),
                )
            else:
                conn.commit()
                return False
            conn.commit()
            return cur.rowcount == 1

    def transition(
        self,
        project: str,
        run_id: str,
        expected_state: str,
        state: str,
    ) -> bool:
        """Compare-and-set a cross-worker loop control transition."""
        if (expected_state, state) not in _ALLOWED_TRANSITIONS:
            raise ValueError(
                f"ungueltiger Loop-Uebergang: {expected_state} -> {state}"
            )
        with closing(self._connect()) as conn:
            conn.execute("BEGIN IMMEDIATE")
            cur = conn.execute(
                "UPDATE loop_processes SET state=?, "
                "pid=CASE WHEN ?='idle' THEN NULL ELSE pid END, "
                "process_identity=CASE WHEN ?='idle' THEN NULL "
                "ELSE process_identity END, updated_at=? "
                "WHERE project=? AND run_id=? AND state=?",
                (
                    state, state, state, time.time(),
                    project, run_id, expected_state,
                ),
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
                raise subprocess.TimeoutExpired(
                    ["loop", str(self.pid)], timeout=timeout or 0.0
                )
            time.sleep(0.05)
        return 0

    def terminate(self) -> None:
        os.kill(self.pid, signal.SIGTERM)

    def kill(self) -> None:
        os.kill(self.pid, signal.SIGKILL)


__all__ = ["AttachedLoopProcess", "LoopProcessRegistry"]
