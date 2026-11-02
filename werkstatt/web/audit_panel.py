"""Audit-Panel: REST-History und Live-Stream fuer audit()-Events."""

from __future__ import annotations

import asyncio
import json
import threading
from collections import deque
from pathlib import Path
from typing import Any

from fastapi import (
    APIRouter,
    FastAPI,
    Query,
    WebSocket,
    WebSocketDisconnect,
)

from werkstatt.loop_renderer import TerminalEmitter

__all__ = ["create_app", "router", "veroeffentliche"]

router = APIRouter()

AUDIT_UNTERVERZEICHNIS = "audit-logs"
STANDARD_LIMIT = 200
MAX_LIMIT = 5000
LIVE_PUFFER_MAX = 500
WS_QUEUE_MAX = 1000

_abonnenten: set[asyncio.Queue[dict[str, Any]]] = set()
_live_puffer: deque[dict[str, Any]] = deque(maxlen=LIVE_PUFFER_MAX)
_bus_lock = threading.Lock()
_bus_loop: asyncio.AbstractEventLoop | None = None
_bridge_thread: threading.Thread | None = None
_bridge_stop: threading.Event | None = None
_bridge_queue: Any = None

router = APIRouter(tags=["audit"])


def _als_dict(event: Any) -> dict[str, Any]:
    """Normalisiert ein rohes Emitter-/Datei-Objekt zu einem flachen dict."""
    if isinstance(event, dict):
        daten = dict(event)
        daten.setdefault("kind", "emitter_event")
        return daten
    return {"kind": "emitter_event", "payload": event}


def _verteile(
    abonnenten: list[asyncio.Queue[dict[str, Any]]],
    daten: dict[str, Any],
) -> None:
    """Verteilt ein Event an alle Abonnenten-Queues (im Bus-Loop)."""
    for queue in abonnenten:
        try:
            queue.put_nowait(daten)
        except asyncio.QueueFull:
            pass


def veroeffentliche(event: Any) -> None:
    """Oeffentliche Emitter-Bridge: legt ein Live-Event in den Bus."""
    daten = _als_dict(event)
    with _bus_lock:
        _live_puffer.append(daten)
        abonnenten = list(_abonnenten)
    loop = _bus_loop
    if loop is not None and not loop.is_closed():
        loop.call_soon_threadsafe(_verteile, abonnenten, daten)


def _audit_pfad(home: Path, project_name: str) -> Path:
    return home / AUDIT_UNTERVERZEICHNIS / f"{project_name}.jsonl"


def _lese_events(verzeichnis: Path) -> list[dict[str, Any]]:
    """Liest alle .jsonl-Dateien aus audit-logs/.

    Zwei Datei-Konventionen:
    - agent-pipeline-YYYY-MM-DD.jsonl (echte Loop-Logs)
    - YYYY-MM-DD.jsonl (Testdaten / manuell)
    Keine Truncation hier — Limit wird in get_audit angewendet.
    """
    if not verzeichnis.is_dir():
        return []
    dateien: set[Path] = set()
    dateien.update(verzeichnis.glob("agent-pipeline-*.jsonl"))
    dateien.update(verzeichnis.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].jsonl"))
    alle: list[dict[str, Any]] = []
    for pfad in sorted(dateien):
        try:
            with pfad.open("r", encoding="utf-8") as fh:
                for zeile in fh:
                    zeile = zeile.strip()
                    if not zeile:
                        continue
                    try:
                        obj = json.loads(zeile)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(obj, dict):
                        alle.append(obj)
        except OSError:
            continue
    return alle


@router.get("/api/projects/{name}/audit")
def get_audit(
    name: str,
    limit: int = Query(STANDARD_LIMIT, ge=1, le=MAX_LIMIT),
    kind: str | None = Query(default=None),
    run_id: str | None = Query(default=None),
    datum_von: str | None = Query(default=None),
    datum_bis: str | None = Query(default=None),
) -> dict[str, Any]:
    """REST-History: liefert Audit-Events mit optionalen Filtern."""
    home = _aktuelles_home()
    verzeichnis = home / AUDIT_UNTERVERZEICHNIS
    alle = _lese_events(verzeichnis)

    # Sortiere nach ts (ISO-String reicht lexikografisch)
    alle.sort(key=lambda e: str(e.get("ts", "")))

    gefiltert: list[dict[str, Any]] = []
    for e in alle:
        if kind is not None and str(e.get("kind", "")) != kind:
            continue
        if run_id is not None and str(e.get("run_id", "")) != run_id:
            continue
        ts = str(e.get("ts", ""))
        datum = ts[:10] if len(ts) >= 10 else ""
        if datum_von is not None and datum < datum_von:
            continue
        if datum_bis is not None and datum > datum_bis:
            continue
        gefiltert.append(e)

    if len(gefiltert) > limit:
        gefiltert = gefiltert[-limit:]

    return {"project": name, "events": gefiltert, "anzahl": len(gefiltert)}


@router.websocket("/api/projects/{name}/audit/stream")
async def ws_audit_stream(websocket: WebSocket, name: str) -> None:
    """WS-Live-Stream: sendet neue Audit-Events eines Projekts."""
    await websocket.accept()
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=WS_QUEUE_MAX)
    with _bus_lock:
        _abonnenten.add(queue)
        backlog = list(_live_puffer)
    try:
        for event in backlog:
            await websocket.send_json(event)
        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        pass
    finally:
        with _bus_lock:
            _abonnenten.discard(queue)


_home_kontext: Path | None = None


def _aktuelles_home() -> Path:
    """Liefert das Projekt-Home fuer Audit-Logs.

    Reihenfolge: explizit gesetzt -> CWD (Projekt-Root) -> $HOME/.werkstatt.
    CWD-Fallback: in der Werkstatt liegen audit-logs/ im Projekt-Root,
    nicht unter $HOME/.werkstatt. Frueher lieferte die Funktion immer
    $HOME/.werkstatt -> /api/projects/*/audit fand nichts.
    """
    if _home_kontext is not None:
        return _home_kontext
    cwd = Path.cwd()
    if (cwd / "audit-logs").is_dir():
        return cwd
    return Path.home() / ".werkstatt"


def create_app(
    home: Path | None = None,
    emitter: TerminalEmitter | None = None,
) -> FastAPI:
    """Erzeugt eine FastAPI-App mit Audit-Panel-Routen."""
    global _home_kontext
    if home is not None:
        _home_kontext = home
    app = FastAPI(title="Werkstatt Audit-Panel")
    app.include_router(router)
    if emitter is not None:
        try:
            emitter.subscribe(veroeffentliche)
        except Exception:
            pass
    return app
