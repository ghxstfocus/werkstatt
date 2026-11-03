"""PTY-Shell fuer Browser-Terminal (Stellschraube 2026-11-04).

Echtes PTY mit /bin/bash -l. Jede WS-Verbindung bekommt eine eigene
Session. Resize via termios.TIOCSWINSZ. Auth-Cookie im Handshake.

SICHERHEIT:
- Der PTY-Prozess laeuft als der User, unter dem der Server laeuft.
  Aktuell root — der Browser-User hat damit root-Shell.
- Auth-Token im Cookie ist die einzige Barriere.
- Token-leak = voller Server-Zugriff. Darum:
  * MAX_SESSIONS_PER_PROJECT begrenzt parallele Shells
  * SESSION_TIMEOUT_S schliesst inaktive Shells
  * WERKSTATT_SHELL_ENABLED=false deaktiviert Shell komplett
  * jede abgeschickte Zeile landet in audit-logs/shell-YYYY-MM-DD.jsonl

Der Endpoint ist /ws/shell (nicht /ws/terminal/* — das bleibt Audit-Tail).
"""
from __future__ import annotations

import asyncio
import fcntl
import json
import os
import pty
import struct
import termios
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from werkstatt.web.auth import is_auth_disabled, is_authed_ws

__all__ = ["PTYSession", "mount_shell", "router"]

router = APIRouter()

# Limits — Tests koennen sie via monkeypatch aendern.
MAX_SESSIONS_PER_PROJECT: int = 3
SESSION_TIMEOUT_S: float = 3600.0
SHELL_BIN: str = "/bin/bash"

_AKTIVE_SESSIONS: dict[str, int] = {}


def _shell_enabled() -> bool:
    return os.environ.get("WERKSTATT_SHELL_ENABLED", "true").lower() != "false"


def _audit_shell_event(kind: str, data: dict[str, Any]) -> None:
    """Loggt Shell-Events in audit-logs/shell-YYYY-MM-DD.jsonl."""
    try:
        heute = time.strftime("%Y-%m-%d")
        p = Path("audit-logs") / f"shell-{heute}.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
            "kind": kind,
            **data,
        }
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except OSError:
        pass


class PTYSession:
    """Eine PTY-Session: bash-Subprozess + Master-FD + Reader-Task."""

    def __init__(self, websocket: WebSocket, project: str) -> None:
        self.websocket = websocket
        self.project = project
        self.master_fd: int = -1
        self.pid: int = -1
        self._stopp = asyncio.Event()
        self._reader_task: asyncio.Task[None] | None = None
        self._writer_task: asyncio.Task[None] | None = None
        self._proc: object = None
        self._puffer = ""
        self._start_ts = time.monotonic()

    def _oeffne_pty(self) -> None:
        """Oeffnet PTY mit subprocess.Popen + preexec_fn.

        bash -l -i: login + interactive. preexec_fn macht setsid +
        TIOCSCTTY, damit bash den PTY-Slave als controlling terminal
        sieht (sonst startet bash nicht interaktiv und gibt keinen
        Prompt aus).

        preexec_fn ist in Python als "not thread-safe" dokumentiert —
        im TestClient-Portal gibt es dennoch. Unsere preexec_fn ist
        minimal (2 syscalls, keine Python-Locks), deshalb akzeptabel.
        """
        import fcntl
        import subprocess
        import termios

        env = dict(os.environ)
        env["TERM"] = "xterm-256color"
        env["WERKSTATT_SHELL"] = "1"

        master_fd, slave_fd = pty.openpty()

        # setsid + TIOCSCTTY in preexec_fn: bash braucht controlling
        # terminal, um interaktiv zu werden.
        def _preexec() -> None:
            try:
                os.setsid()
                fcntl.ioctl(slave_fd, termios.TIOCSCTTY, 0)
            except OSError:
                pass

        proc = subprocess.Popen(
            [SHELL_BIN, "-l", "-i"],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            env=env,
            preexec_fn=_preexec,  # noqa: PLW1509 — 2 syscalls, keine Locks
            close_fds=False,
        )
        os.close(slave_fd)
        self.pid = proc.pid
        self._proc = proc
        self.master_fd = master_fd
        self._setze_winsize(80, 24)
        _audit_shell_event("shell_session_start",
                           {"pid": proc.pid, "project": self.project})

    def _setze_winsize(self, cols: int, rows: int) -> None:
        if self.master_fd < 0:
            return
        try:
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)
        except (OSError, ValueError):
            pass

    async def _reader(self) -> None:
        """Liest PTY-Output via select mit kurzem Timeout.

        os.read ohne Timeout waere blocking -> cancel() wirkt nicht,
        _cleanup wartet ewig, Tests/Sessions haengen. select() mit
        0.1s-Timeout bricht die Warteschleife nach jedem Tick ab.
        """
        import select

        while not self._stopp.is_set():
            if self.master_fd < 0:
                break
            try:
                r, _, _ = await asyncio.to_thread(
                    select.select, [self.master_fd], [], [], 0.1
                )
            except (OSError, ValueError):
                break
            if not r:
                continue
            try:
                data = os.read(self.master_fd, 4096)
            except OSError:
                break
            if not data:
                break
            try:
                await self.websocket.send_text(
                    data.decode("utf-8", errors="replace")
                )
            except Exception:  # noqa: BLE001
                break
        self._stopp.set()

    def _log_befehl(self, puffer: str) -> None:
        """Loggt abgeschickte Zeilen (Enter-getrennt) ins Audit."""
        zeilen = puffer.split("\r")
        for z in zeilen[:-1]:
            z = z.strip()
            if z:
                _audit_shell_event("shell_command",
                                   {"cmd": z[:500], "project": self.project})
        return zeilen[-1]

    async def run(self) -> None:
        self._oeffne_pty()
        self._reader_task = asyncio.create_task(self._reader())
        try:
            while not self._stopp.is_set():
                try:
                    msg = await asyncio.wait_for(
                        self.websocket.receive_text(),
                        timeout=1.0,
                    )
                except TimeoutError:
                    # Idle-Check
                    if self._session_alter() > SESSION_TIMEOUT_S:
                        _audit_shell_event(
                            "shell_session_timeout",
                            {"pid": self.pid, "project": self.project},
                        )
                        break
                    continue
                except WebSocketDisconnect:
                    break
                self._verarbeite_msg(msg)
        finally:
            await self._cleanup()

    def _verarbeite_msg(self, msg: str) -> None:
        try:
            daten = json.loads(msg)
        except json.JSONDecodeError:
            return
        if not isinstance(daten, dict):
            return
        typ = daten.get("typ")
        if typ == "input":
            data = str(daten.get("data", ""))
            self._puffer = self._log_befehl(self._puffer + data)
            if self.master_fd >= 0:
                try:
                    os.write(self.master_fd, data.encode("utf-8", "replace"))
                except OSError:
                    self._stopp.set()
        elif typ == "resize":
            cols = int(daten.get("cols", 80))
            rows = int(daten.get("rows", 24))
            if 10 <= cols <= 500 and 5 <= rows <= 200:
                self._setze_winsize(cols, rows)

    def _session_alter(self) -> float:
        return time.monotonic() - self._start_ts

    async def _cleanup(self) -> None:
        self._stopp.set()
        # PTY schliessen zuerst — sonst bleibt _reader in os.read/select
        # haengen bis zum SIGKILL.
        if self._reader_task is not None:
            self._reader_task.cancel()
            try:
                await asyncio.wait_for(self._reader_task, timeout=1.0)
            except (TimeoutError, asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
        if self._proc is not None and hasattr(self._proc, "terminate"):
            try:
                self._proc.terminate()  # type: ignore[attr-defined]
                for _ in range(20):
                    if self._proc.poll() is not None:  # type: ignore[attr-defined]
                        break
                    await asyncio.sleep(0.1)
                if self._proc.poll() is None:  # type: ignore[attr-defined]
                    self._proc.kill()  # type: ignore[attr-defined]
            except OSError:
                pass
        if self.master_fd >= 0:
            try:
                os.close(self.master_fd)
            except OSError:
                pass
            self.master_fd = -1
        _audit_shell_event("shell_session_end",
                           {"pid": self.pid, "project": self.project})

    def _pid_lebt(self) -> bool:
        if self.pid <= 0:
            return False
        try:
            os.kill(self.pid, 0)
            return True
        except OSError:
            return False


@router.websocket("/ws/shell")
async def shell_ws(websocket: WebSocket) -> None:
    """PTY-Shell via WebSocket. Auth via Cookie, max N Sessions.

    WICHTIG: Bei Ablehnung accept() + close(1008) — nicht close() allein.
    Starlette-TestClient verhaelt sich sonst unzuverlaessig (__enter__
    raised WebSocketDisconnect, aber receive_text blockiert).
    """
    project = "werkstatt"
    abgelehnt = (
        not _shell_enabled()
        or (not is_auth_disabled() and not is_authed_ws(websocket))
        or _AKTIVE_SESSIONS.get(project, 0) >= MAX_SESSIONS_PER_PROJECT
    )
    if abgelehnt:
        await websocket.accept()
        await websocket.close(code=1008)
        return

    await websocket.accept()
    _AKTIVE_SESSIONS[project] = _AKTIVE_SESSIONS.get(project, 0) + 1
    session = PTYSession(websocket, project)
    try:
        await session.run()
    finally:
        _AKTIVE_SESSIONS[project] = max(0, _AKTIVE_SESSIONS.get(project, 1) - 1)


def mount_shell(app: Any) -> None:
    app.include_router(router)
