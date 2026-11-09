"""WebSocket-Registry fuer Tab-Kanaele.

Der ConnectionManager haelt pro Tab (``tab_id``) die offenen
WebSocket-Verbindungen. Die Isolationseinheit ist ausschliesslich
``tab_id`` — eine Projekt-Zuordnung findet hier bewusst nicht statt.
"""

import re

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

__all__ = ["ConnectionManager", "manager", "router"]

_TAB_ID_MUSTER = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class ConnectionManager:
    """Registry offener WebSocket-Verbindungen je Tab."""

    def __init__(self) -> None:
        self._verbindungen: dict[str, set[WebSocket]] = {}

    def connect(self, tab_id: str, websocket: WebSocket) -> None:
        """Registriert ein Socket fuer einen Tab.

        Das ``accept()`` erfolgt im Endpoint, nicht hier — Trennung von
        Transport und Registry.
        """
        self._verbindungen.setdefault(tab_id, set()).add(websocket)

    def disconnect(self, tab_id: str, websocket: WebSocket) -> None:
        """Entfernt ein Socket; leere Tab-Sets werden aufgeraeumt."""
        sockets = self._verbindungen.get(tab_id)
        if sockets is None:
            return
        sockets.discard(websocket)
        if not sockets:
            self._verbindungen.pop(tab_id, None)

    def count(self, tab_id: str) -> int:
        """Anzahl offener Verbindungen fuer einen Tab."""
        return len(self._verbindungen.get(tab_id, ()))

    def tab_ids(self) -> list[str]:
        """Sortierte Liste aller bekannten Tab-IDs."""
        return sorted(self._verbindungen)

    async def broadcast(self, tab_id: str, nachricht: str) -> int:
        """Sendet ``nachricht`` an alle Sockets eines Tabs.

        Tote Verbindungen werden entfernt und brechen den Broadcast
        nicht ab. Rueckgabe ist die Zahl erfolgreicher Sends.
        """
        gesendet = 0
        for socket in list(self._verbindungen.get(tab_id, ())):
            try:
                await socket.send_text(nachricht)
            except (RuntimeError, WebSocketDisconnect):
                self.disconnect(tab_id, socket)
                continue
            gesendet += 1
        return gesendet


def _pruefe_tab_id(tab_id: str) -> bool:
    """Prueft, ob ``tab_id`` dem erlaubten Muster entspricht."""
    return isinstance(tab_id, str) and _TAB_ID_MUSTER.fullmatch(tab_id) is not None


async def websocket_kanaele(websocket: WebSocket, tab_id: str) -> None:
    """Endpunkt-Handler fuer einen Tab-Kanal.

    Prueft die Tab-ID, akzeptiert die Verbindung, registriert sie im
    Manager und liest Nachrichten bis zum Disconnect.
    """
    if not _pruefe_tab_id(tab_id):
        await websocket.close(code=1008)
        return

    from werkstatt.web.auth import require_ws_auth

    if not await require_ws_auth(websocket):
        return

    await websocket.accept()
    manager.connect(tab_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(tab_id, websocket)
    except RuntimeError:
        manager.disconnect(tab_id, websocket)


router = APIRouter()
manager = ConnectionManager()


@router.websocket("/ws/{tab_id}")
async def ws_tab(websocket: WebSocket, tab_id: str) -> None:
    """WebSocket-Endpoint fuer einen Tab-Kanal unter ``/ws/{tab_id}``."""
    await websocket_kanaele(websocket, tab_id)
