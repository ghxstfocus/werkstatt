"""Tests fuer werkstatt.web.auth (Stellschraube 2026-11-04)."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from werkstatt.web import auth


@pytest.fixture(autouse=True)
def _auth_aktiv(monkeypatch, tmp_path):
    """Auth-Middleware aktiv, Token in tmp_path."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(auth, "_AUTH_DISABLED", False)
    monkeypatch.setattr(auth, "_TOKEN", None)
    monkeypatch.setattr(auth, "TOKEN_FILE", tmp_path / ".werkstatt" / "auth-token")
    yield
    monkeypatch.setattr(auth, "_AUTH_DISABLED", True)


def _client():
    from werkstatt.web.app import create_app
    return TestClient(create_app())


def test_token_wird_generiert_und_persistiert(tmp_path):
    tok = auth.get_token()
    assert len(tok) >= 32
    assert auth.TOKEN_FILE.exists()
    # mode 0600 (oder mindestens nicht world-readable)
    mode = os.stat(auth.TOKEN_FILE).st_mode & 0o777
    assert mode & 0o077 == 0, f"mode={oct(mode)} zu offen"
    # Reload liefert denselben Token
    auth._TOKEN = None
    assert auth.get_token() == tok


def test_token_aus_env(monkeypatch, tmp_path):
    monkeypatch.setenv("WERKSTATT_AUTH_TOKEN", "abc-from-env")
    auth._TOKEN = None
    assert auth.get_token() == "abc-from-env"


def test_check_token_konstantzeit():
    tok = auth.get_token()
    assert auth.check_token(tok)
    assert not auth.check_token("")
    assert not auth.check_token("falsch")
    assert not auth.check_token(tok + "x")


def test_login_page_ist_public():
    c = _client()
    r = c.get("/login")
    assert r.status_code == 200
    assert "Werkstatt" in r.text


def test_static_ist_public():
    c = _client()
    r = c.get("/static/layout.css")
    assert r.status_code == 200


def test_geschuetzte_route_ohne_cookie_401_api():
    c = _client()
    r = c.get("/api/projects/werkstatt/state",
              headers={"accept": "application/json"})
    assert r.status_code == 401


def test_geschuetzte_route_ohne_cookie_redirect_html():
    c = _client()
    r = c.get("/", headers={"accept": "text/html"},
              follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"


def test_login_mit_falschem_token_401():
    c = _client()
    r = c.post("/api/auth/login", json={"token": "falsch"})
    assert r.status_code == 401


def test_login_mit_richtigem_token_setzt_cookie():
    c = _client()
    tok = auth.get_token()
    r = c.post("/api/auth/login", json={"token": tok})
    assert r.status_code == 200
    assert auth.COOKIE_NAME in r.cookies


def test_nach_login_zugriff():
    c = _client()
    tok = auth.get_token()
    r = c.post("/api/auth/login", json={"token": tok})
    assert r.status_code == 200
    r2 = c.get("/api/projects/werkstatt/state")
    assert r2.status_code == 200


def test_logout_loescht_cookie():
    c = _client()
    tok = auth.get_token()
    c.post("/api/auth/login", json={"token": tok})
    r = c.post("/api/auth/logout")
    assert r.status_code == 200
    # Cookie geleert -> 401
    r2 = c.get("/api/projects/werkstatt/state",
               headers={"accept": "application/json"})
    assert r2.status_code == 401


def test_ws_ohne_cookie_schliesst_1008():
    c = _client()
    with pytest.raises(__import__('starlette.websockets', fromlist=['WebSocketDisconnect']).WebSocketDisconnect), c.websocket_connect("/ws/terminal/werkstatt"):
        pass


def test_ws_mit_cookie_verbindet():
    c = _client()
    tok = auth.get_token()
    c.post("/api/auth/login", json={"token": tok})
    # WS akzeptiert Cookie aus dem Client-Jar
    with c.websocket_connect("/ws/terminal/werkstatt") as ws:
        assert ws is not None
        ws.close()
