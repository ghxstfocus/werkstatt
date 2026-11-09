"""Spec-Tests fuer WS-Auth (OP-389).

Verhalten, das dieser Test verbietet:
- Ein WebSocket-Endpunkt akzeptiert den Handshake ohne gueltigen
  Auth-Cookie, obwohl die Auth-Middleware aktiv ist.
- Ein neuer WS-Endpunkt wird hinzugefuegt ohne Eintrag in WS_ROUTEN_SOURCE.

Vorbild-Fixture: tests/test_auth.py.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from werkstatt.web import auth

# Konkrete Test-Pfade (mit realen IDs, damit die Route matcht).
WS_PFADE = [
    "/ws/abc",
    "/api/projects/testprojekt/chat/stream",
    "/api/projects/testprojekt/audit/stream",
    "/ws/terminal/testprojekt",
]

# Source-Routen-Muster (Meta-Test: neue Routen ohne Eintrag = fail).
WS_ROUTEN_SOURCE = [
    "/ws/{tab_id}",
    "/api/projects/{name}/chat/stream",
    "/api/projects/{name}/audit/stream",
    "/ws/terminal/{project}",
]


@pytest.fixture(autouse=True)
def _auth_aktiv(monkeypatch, tmp_path):
    """Auth aktiv, Token in tmp_path (Muster aus test_auth.py)."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(auth, "_AUTH_DISABLED", False)
    monkeypatch.setattr(auth, "_TOKEN", None)
    monkeypatch.setattr(auth, "TOKEN_FILE", tmp_path / ".werkstatt" / "auth-token")
    yield
    monkeypatch.setattr(auth, "_AUTH_DISABLED", True)


def _client() -> TestClient:
    from werkstatt.web.app import create_app

    return TestClient(create_app())


@pytest.mark.parametrize("pfad", WS_PFADE)
def test_unauth_ws_wird_abgelehnt_vor_accept(pfad: str) -> None:
    """Ohne Cookie: WebSocketDisconnect(1008) VOR accept().

    pytest.fail im with-Block beweist: accept() wurde gerufen - dann
    ist der Auth-Check nicht (rechtzeitig) passiert.
    """
    client = _client()
    with (
        pytest.raises(WebSocketDisconnect) as excinfo,
        client.websocket_connect(pfad),
    ):
        pytest.fail(f"Socket auf {pfad} wurde ohne Auth akzeptiert")
    assert excinfo.value.code == 1008


@pytest.mark.parametrize("pfad", WS_PFADE)
def test_auth_ws_wird_akzeptiert(pfad: str) -> None:
    """Mit gueltigem Cookie: Handshake wird VOR accept durchgelassen.

    Wenn der Server trotz Cookie den Handshake verweigert, wirft
    ``websocket_connect`` bereits beim __enter__ - Test rot. Der Test
    verbietet nur den Auth-Fehler; jeder andere Close-Grund nach accept
    ist erlaubt.
    """
    client = _client()
    token = auth.get_token()
    client.cookies.set(auth.COOKIE_NAME, token)
    with client.websocket_connect(pfad):
        pass


@pytest.mark.parametrize("pfad", WS_PFADE)
def test_auth_disabled_ws_wird_akzeptiert(pfad: str) -> None:
    """_AUTH_DISABLED=True: ohne Cookie akzeptiert (Test-Workflow)."""
    auth.set_auth_disabled(True)
    try:
        client = _client()
        with client.websocket_connect(pfad):
            pass
    finally:
        auth.set_auth_disabled(False)


def test_ws_pfade_in_quelle_vollstaendig() -> None:
    """Meta-Test: jede @(app|router).websocket-Route muss in
    WS_ROUTEN_SOURCE eingetragen sein. Damit faellt ein neuer
    WS-Endpunkt ohne Auth-Test sofort auf.
    """
    quelle = Path(__file__).resolve().parent.parent / "werkstatt" / "web"
    muster = re.compile(r'@(?:app|router)\.websocket\(\s*"([^"]+)"')
    gefunden: set[str] = set()
    for py in quelle.glob("*.py"):
        for m in muster.finditer(py.read_text()):
            gefunden.add(m.group(1))
    erwartet = set(WS_ROUTEN_SOURCE)
    fehlend = gefunden - erwartet
    assert not fehlend, (
        f"Neue WS-Routen ohne Eintrag in WS_ROUTEN_SOURCE: {sorted(fehlend)}"
    )
    ueberzaehlig = erwartet - gefunden
    assert not ueberzaehlig, (
        f"WS_ROUTEN_SOURCE nennt Routen, die nicht mehr existieren: "
        f"{sorted(ueberzaehlig)}"
    )
