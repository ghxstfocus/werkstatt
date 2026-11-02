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
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from werkstatt.loop_renderer import get_emitter

__all__ = ["mount_terminal_proxy", "router"]

router = APIRouter()

_PROJECT_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
_QUEUE_MAXSIZE = 1000


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


@router.websocket("/ws/terminal/{project}")
async def terminal_ws(websocket: WebSocket, project: str) -> None:
    """Streamt Terminal-Events eines Projekts als JSON-Text ueber WebSocket."""
    if not _PROJECT_RE.match(project):
        await websocket.close(code=1008)
        return

    await websocket.accept()

    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=_QUEUE_MAXSIZE)
    loop = asyncio.get_running_loop()
    unsubscribe = get_emitter(project).subscribe(_make_bridge(loop, queue))

    async def _sender() -> None:
        while True:
            event = await queue.get()
            await websocket.send_text(json.dumps(event))

    async def _receiver() -> None:
        while True:
            await websocket.receive_text()

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
        unsubscribe()


def mount_terminal_proxy(app: Any) -> None:
    """Haengt den Terminal-Proxy-Router an die FastAPI-App."""
    app.include_router(router)
