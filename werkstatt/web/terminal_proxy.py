"""WebSocket-Proxy fuer Terminal-Events.

Transportweg: In-Process-Emitter-Registry aus ``werkstatt.loop_renderer``;
der Loop laeuft im selben Prozess (Worker-Thread). Kein Datei-Tailing,
kein Polling. Cross-Prozess-JSONL ist Folge-OP.
"""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

__all__ = ["mount_terminal_proxy", "router"]

router = APIRouter()

_PROJECT_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
_QUEUE_MAXSIZE = 1000

_AUDIT_GLOB = "agent-pipeline-*.jsonl"
_RENDER_LOG_GLOB = "loop-render-*.log"


def _render_log_verzeichnis() -> Path:
    """Verzeichnis mit loop-render-*.log (Monkeypatch-Anker fuer Tests)."""
    return Path("logs")

_POLL_INTERVALL_S: float = 1.0
# Replay-Steuerung: False (Production) = kein Replay historischer
# Zeilen beim ersten Poll. True (Tests) = von offset=0 lesen.
# Ohne diese Trennung gibt es ein Timing-Race: der Erstfund-Poll
# kann VOR dem Test-Schreiben laufen und springt dann hinter die
# Test-Zeile.
_REPLAY_HISTORIE: bool = False

_MAX_ZEILEN_PRO_TICK: int = 500
_AKTIVE_VERBINDUNGEN: dict[str, int] = {}



# Fortschritts-Filter: nur diese Kinds kommen ins Terminal-Panel.
# Debug-Rauschen (builder_file_context, llm_call, command_executed)
# bleibt im Audit-Panel, nicht im Terminal.
_TERMINAL_KIND_PREFIXE = (
    "loop_task_", "loop_phase", "loop_verify_",
    "loop_reflection_", "loop_patch_", "loop_plan_gate_",
    "loop_human_gate_", "loop_erfolg", "loop_rollback",
    # Loop-Phasen
    "loop_",
    # Planner / Architect
    "planner_",
    # Reviewer
    "reviewer_",
    # Builder
    "builder_",
    # Explorer
    "explorer_",
    # LLM-Calls
    "llm_",
    # Commands
    "command_",
    # Verify
    "verify_",
    # ADR-Mini
    "adr_mini_",
    # Committer
    "committer_",
    # Web
    "web_",
    # Doku
    "doku_",
    # Sonstige
    "quelle_invalid", "mess_protokoll_limit_erreicht",
    "progress_write_failed",
)


def _ist_terminal_wuerdig(event: dict[str, Any]) -> bool:
    """True = Fortschritt, False = Debug-Noise."""
    kind = str(event.get("kind", "") or "")
    if not kind:
        return False
    for prefix in _TERMINAL_KIND_PREFIXE:
        if kind.startswith(prefix):
            return True
    return False

def _audit_log_verzeichnis(project: str) -> Path:
    """Ermittelt das Audit-Log-Verzeichnis fuer ein Projekt.

    Liest ``projects/.yaml`` (relativ zum CWD) und entnimmt das Feld
    ``home``. Faellt bei fehlender Datei, fehlendem Feld oder
    Parse-Fehler auf ``Path.cwd() / "audit-logs"`` zurueck.
    """
    try:
        from werkstatt.paths import audit_logs_dir as _audit_logs_dir
        return _audit_logs_dir(project)
    except (OSError, ValueError, TypeError):
        return Path.cwd() / "audit-logs"


def _normalisiere_zeile(zeile: str) -> dict[str, Any] | None:
    """Normalisiert eine JSONL-Zeile zu einem einheitlichen Event-Schema."""
    roh = zeile.strip()
    if not roh:
        return None
    try:
        obj = json.loads(roh)
    except json.JSONDecodeError:
        return {"typ": "audit", "event": {"typ": "log", "text": roh}}
    return {"typ": "audit", "event": obj}


def _lese_neue_zeilen(pfad: Path, offset: int) -> tuple[list[str], int]:
    """Liest neue vollstaendige Zeilen ab ``offset`` (Tail-Semantik)."""
    try:
        with pfad.open(encoding="utf-8", errors="replace") as f:
            f.seek(offset)
            zeilen: list[str] = []
            letzte_start = offset
            for _ in range(_MAX_ZEILEN_PRO_TICK):
                start = f.tell()
                zeile = f.readline()
                if not zeile:
                    return zeilen, f.tell()
                if not zeile.endswith("\n"):
                    return zeilen, start
                zeilen.append(zeile)
                letzte_start = f.tell()
            return zeilen, letzte_start
    except OSError:
        return [], offset


async def _tail_poll_queue(
    verzeichnis: Path,
    queue: asyncio.Queue[dict[str, Any]],
    stopp: asyncio.Event,
) -> None:
    """Pollt das Audit-Log-Verzeichnis und schiebt neue Events in die Queue."""
    aktueller_pfad: Path | None = None
    inode: int = -1
    offset: int = 0
    # Beim ersten Fund ans Datei-Ende springen: kein Replay historischer
    # Zeilen. Historie zeigt das Audit-Panel (History-Sidebar via REST).
    _erster_fund = True
    while not stopp.is_set():
        try:
            kandidaten = sorted(verzeichnis.glob(_AUDIT_GLOB))
        except OSError:
            kandidaten = []
        if kandidaten:
            neuester = kandidaten[-1]
            try:
                neuer_inode = neuester.stat().st_ino
            except OSError:
                neuer_inode = -1
            if neuester != aktueller_pfad or neuer_inode != inode:
                aktueller_pfad = neuester
                inode = neuer_inode
                if _erster_fund and not _REPLAY_HISTORIE:

                    try:

                        offset = aktueller_pfad.stat().st_size

                    except OSError:

                        offset = 0

                    _erster_fund = False

                else:

                    offset = 0
            if aktueller_pfad is not None:
                zeilen, offset = _lese_neue_zeilen(aktueller_pfad, offset)
                for zeile in zeilen:
                    event = _normalisiere_zeile(zeile)

                    if event is not None and not _ist_terminal_wuerdig(event.get("event", {})):

                        event = None
                    if event is not None:
                        _safe_put(queue, event)
        try:
            await asyncio.wait_for(stopp.wait(), timeout=_POLL_INTERVALL_S)
        except TimeoutError:
            continue


def _safe_put(
    queue: asyncio.Queue[dict[str, Any]],
    event: dict[str, Any],
) -> None:
    """Nicht-blockierendes Einreihen mit Verdrängung des ältesten Events."""
    try:
        queue.put_nowait(event)
        return
    except asyncio.QueueFull:
        pass
    try:
        queue.get_nowait()
    except asyncio.QueueEmpty:
        pass
    try:
        queue.put_nowait(event)
    except asyncio.QueueFull:
        return


def _make_bridge(
    loop: asyncio.AbstractEventLoop,
    queue: asyncio.Queue[dict[str, Any]],
) -> Callable[[dict[str, Any]], None]:
    """Erzeugt eine thread-sichere Push-Bruecke vom Renderer in den Loop."""

    def _bridge(event: dict[str, Any]) -> None:
        try:
            loop.call_soon_threadsafe(_safe_put, queue, event)
        except RuntimeError:
            return

    return _bridge


async def _tail_poll_render_log(
    verzeichnis: Path,
    queue: asyncio.Queue[dict[str, Any]],
    stopp: asyncio.Event,
) -> None:
    """Tail-Poll auf logs/loop-render-*.log — plain text, ANSI-frei.

    Schreibt Events als {"typ": "render", "text": "..."} in die Queue.
    """
    aktueller_pfad: Path | None = None
    inode: int = -1
    offset: int = 0
    _erster_fund = True
    while not stopp.is_set():
        try:
            kandidaten = sorted(verzeichnis.glob(_RENDER_LOG_GLOB))
        except OSError:
            kandidaten = []
        if kandidaten:
            neuester = kandidaten[-1]
            try:
                neuer_inode = neuester.stat().st_ino
            except OSError:
                neuer_inode = -1
            if neuester != aktueller_pfad or neuer_inode != inode:
                aktueller_pfad = neuester
                inode = neuer_inode
                if _erster_fund and not _REPLAY_HISTORIE:
                    try:
                        offset = aktueller_pfad.stat().st_size
                    except OSError:
                        offset = 0
                    _erster_fund = False
                else:
                    offset = 0
            try:
                with aktueller_pfad.open(encoding="utf-8", errors="replace") as f:
                    f.seek(offset)
                    for _ in range(200):
                        zeile = f.readline()
                        if not zeile:
                            break
                        if not zeile.endswith("\n"):
                            break
                        offset = f.tell()
                        zeile = zeile.rstrip("\n")
                        if not zeile:
                            continue
                        _safe_put(queue, {"typ": "render", "text": zeile})
            except OSError:
                pass
        try:
            await asyncio.wait_for(stopp.wait(), timeout=_POLL_INTERVALL_S)
        except TimeoutError:
            pass


@router.websocket("/ws/terminal/{project}")
async def terminal_ws(websocket: WebSocket, project: str) -> None:
    """Streamt Audit-Events eines Projekts als JSON-Text ueber WebSocket.

    Transportweg: Tail-Poll auf ``audit-logs/agent-pipeline-*.jsonl``.
    Der Loop laeuft in einem anderen Prozess, deshalb kein In-Process-
    Emitter — die Datei ist die einzige verlaessliche Quelle.
    """
    from werkstatt.web.auth import is_auth_disabled, is_authed_ws
    if not is_auth_disabled() and not is_authed_ws(websocket):
        await websocket.close(code=1008)
        return

    if not _PROJECT_RE.match(project):
        await websocket.close(code=1008)
        return

    await websocket.accept()

    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=_QUEUE_MAXSIZE)
    stopp = asyncio.Event()
    verzeichnis = _audit_log_verzeichnis(project)

    # Verbindungszaehler fuer Tab-Lifecycle (Frontend + Test).
    _AKTIVE_VERBINDUNGEN[project] = _AKTIVE_VERBINDUNGEN.get(project, 0) + 1

    async def _sender() -> None:
        while True:
            event = await queue.get()
            await websocket.send_text(json.dumps(event))

    async def _receiver() -> None:
        while True:
            await websocket.receive_text()

    poll_task = asyncio.create_task(
        _tail_poll_queue(verzeichnis, queue, stopp)
    )


    poll_task_render = asyncio.create_task(


        _tail_poll_render_log(_render_log_verzeichnis(), queue, stopp)


    )
    try:
        done, pending = await asyncio.wait(
            {asyncio.create_task(_sender()), asyncio.create_task(_receiver())},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        for task in done:
            exc = task.exception()
            if exc is not None and not isinstance(exc, WebSocketDisconnect):
                raise exc
    except WebSocketDisconnect:
        pass
    finally:
        stopp.set()
        poll_task.cancel()

        poll_task_render.cancel()
        try:
            await poll_task
        except BaseException:  # Cleanup, Fehler egal
            pass
        _AKTIVE_VERBINDUNGEN[project] = max(
            0, _AKTIVE_VERBINDUNGEN.get(project, 1) - 1
        )


def mount_terminal_proxy(app: Any) -> None:
    """Haengt den Terminal-Proxy-Router an die FastAPI-App."""
    app.include_router(router)
