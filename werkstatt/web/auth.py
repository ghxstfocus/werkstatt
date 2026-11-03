"""Auth fuer Dashboard-Zugang (Stellschraube 2026-11-04).

Single-Token-Auth:
- Token aus WERKSTATT_AUTH_TOKEN (env) oder .werkstatt/auth-token (mode 0600).
- Wird beim ersten Aufruf generiert (secrets.token_urlsafe(32)).
- Login setzt httponly-Cookie (SameSite=strict, Secure wenn HTTPS).
- Middleware prueft Cookie auf allen Routen ausser /login, /api/auth/*,
  /static/*.
- WS prueft Cookie im Handshake (is_authed_ws).
- Konstantzeit-Vergleich via secrets.compare_digest.
- Test-Schalter: set_auth_disabled(True) schaltet Middleware-Check aus
  (conftest macht das autouse fuer alle Tests; Auth-Tests heben es auf).

Kein Multi-User, kein Passwort-Hashing — ein Token, eine Session.
Bei Bedarf spaeter erweiterbar auf mehrere Tokens/User.
"""
from __future__ import annotations

import os
import secrets
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

__all__ = [
    "COOKIE_NAME",
    "_reset_token_cache_for_tests",
    "check_token",
    "clear_session_cookie",
    "get_token",
    "is_auth_disabled",
    "is_authed",
    "is_authed_ws",
    "is_public_path",
    "make_login_router",
    "set_auth_disabled",
    "set_session_cookie",
]

COOKIE_NAME = "werkstatt_session"
TOKEN_FILE = Path(".werkstatt") / "auth-token"
PUBLIC_PATHS = frozenset({
    "/login",
    "/api/auth/login",
    "/api/auth/logout",
    "/favicon.ico",
})
PUBLIC_PREFIXES = ("/static/",)

_TOKEN: str | None = None
_AUTH_DISABLED: bool = False


def _reset_token_cache_for_tests() -> None:
    """Setzt den Token-Cache zurueck (nur Tests)."""
    global _TOKEN
    _TOKEN = None


def set_auth_disabled(disabled: bool) -> None:
    """Schaltet den Auth-Middleware-Check aus (nur Tests)."""
    global _AUTH_DISABLED
    _AUTH_DISABLED = disabled


def is_auth_disabled() -> bool:
    return _AUTH_DISABLED


def get_token() -> str:
    """Liefert den Auth-Token.

    Reihenfolge: WERKSTATT_AUTH_TOKEN env -> .werkstatt/auth-token ->
    generieren und persistieren. Persistenz-Fehler sind fatal, damit der
    Token nicht bei jedem Neustart wechselt.
    """
    global _TOKEN
    if _TOKEN is not None:
        return _TOKEN
    env_token = os.environ.get("WERKSTATT_AUTH_TOKEN", "").strip()
    if env_token:
        _TOKEN = env_token
        return _TOKEN
    if TOKEN_FILE.exists():
        try:
            content = TOKEN_FILE.read_text(encoding="utf-8").strip()
            if content:
                _TOKEN = content
                return _TOKEN
        except OSError:
            pass
    new_token = secrets.token_urlsafe(32)
    try:
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(new_token + "\n", encoding="utf-8")
        try:
            TOKEN_FILE.chmod(0o600)
        except OSError:
            pass
    except OSError as exc:
        raise RuntimeError(
            f"kann Auth-Token nicht schreiben: {TOKEN_FILE}: {exc}"
        ) from exc
    _TOKEN = new_token
    return _TOKEN


def check_token(candidate: str) -> bool:
    if not candidate:
        return False
    return secrets.compare_digest(candidate, get_token())


def is_authed(request: Request) -> bool:
    cookie = request.cookies.get(COOKIE_NAME, "")
    if not cookie:
        return False
    return secrets.compare_digest(cookie, get_token())


def is_authed_ws(websocket: Any) -> bool:
    cookie = websocket.cookies.get(COOKIE_NAME, "")
    if not cookie:
        return False
    return secrets.compare_digest(cookie, get_token())


def is_public_path(path: str) -> bool:
    if path in PUBLIC_PATHS:
        return True
    return any(path.startswith(p) for p in PUBLIC_PREFIXES)


def _ist_https(request: Request) -> bool:
    """HTTPS-Erkennung, inkl. Reverse-Proxy (X-Forwarded-Proto)."""
    if request.url.scheme == "https":
        return True
    forwarded = request.headers.get("x-forwarded-proto", "")
    return forwarded.lower() == "https"


def set_session_cookie(response: JSONResponse, secure: bool) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=get_token(),
        max_age=60 * 60 * 24 * 7,
        httponly=True,
        samesite="strict",
        secure=secure,
        path="/",
    )


def clear_session_cookie(response: JSONResponse) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


LOGIN_HTML = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Werkstatt &mdash; Login</title>
<style>
  * { box-sizing: border-box; }
  body { margin: 0; background: #1a1b1e; color: #e4e4e7;
         font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
         display: flex; align-items: center; justify-content: center;
         min-height: 100vh; }
  .login { background: #25262b; padding: 32px 40px; border-radius: 12px;
           box-shadow: 0 8px 32px rgba(0,0,0,0.5); width: 360px; }
  h1 { margin: 0 0 8px; font-size: 22px; font-weight: 500; }
  .sub { color: #9ca3af; font-size: 13px; margin: 0 0 24px; }
  label { display: block; font-size: 13px; color: #9ca3af;
          margin-bottom: 6px; }
  input { width: 100%; padding: 10px 12px; background: #1a1b1e;
          border: 1px solid #2c2e33; border-radius: 6px;
          color: #e4e4e7; font: inherit; outline: none;
          transition: border-color 0.15s; }
  input:focus { border-color: #4d6bfe; }
  button { width: 100%; margin-top: 16px; padding: 10px;
           background: #4d6bfe; color: #fff; border: none;
           border-radius: 6px; font: inherit; font-weight: 500;
           cursor: pointer; transition: background 0.15s; }
  button:hover { background: #5b78ff; }
  button:disabled { background: #374151; cursor: wait; }
  .fehler { color: #f87171; margin-top: 12px; font-size: 13px; }
</style>
</head>
<body>
<form class="login" id="login-form" autocomplete="off">
  <h1>Werkstatt</h1>
  <p class="sub">Anmeldung mit Access-Token</p>
  <label for="token">Token</label>
  <input type="password" id="token" name="token"
         placeholder="Token eingeben" autofocus required>
  <button type="submit" id="btn">Anmelden</button>
  <div id="fehler" class="fehler" hidden></div>
</form>
<script>
const form = document.getElementById("login-form");
const btn = document.getElementById("btn");
const fehler = document.getElementById("fehler");
form.addEventListener("submit", async (e) => {
  e.preventDefault();
  fehler.hidden = true;
  btn.disabled = true;
  const token = document.getElementById("token").value.trim();
  if (!token) { btn.disabled = false; return; }
  try {
    const r = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    });
    if (r.ok) {
      window.location.href = "/";
      return;
    }
    fehler.textContent = "Ungültiger Token.";
  } catch (err) {
    fehler.textContent = "Netzwerkfehler: " + err;
  }
  fehler.hidden = false;
  btn.disabled = false;
});
</script>
</body>
</html>
"""


def make_login_router() -> APIRouter:
    router = APIRouter()

    @router.get("/login")
    def login_page() -> HTMLResponse:
        return HTMLResponse(LOGIN_HTML)

    @router.post("/api/auth/login")
    async def login(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            return JSONResponse({"ok": False, "fehler": "invalid body"},
                                status_code=400)
        token = (body or {}).get("token", "") if isinstance(body, dict) else ""
        if not check_token(token):
            from werkstatt.audit import audit
            try:
                audit("web_login_fail",
                       {"ip": request.client.host if request.client else "?"},
                       Path.cwd(), "_web")
            except Exception:  # noqa: BLE001
                pass
            return JSONResponse({"ok": False, "fehler": "invalid token"},
                                status_code=401)
        response = JSONResponse({"ok": True})
        set_session_cookie(response, secure=_ist_https(request))
        from werkstatt.audit import audit
        try:
            audit("web_login_ok",
                   {"ip": request.client.host if request.client else "?"},
                   Path.cwd(), "_web")
        except Exception:  # noqa: BLE001, S110
            pass
        return response

    @router.post("/api/auth/logout")
    def logout(request: Request) -> JSONResponse:
        from werkstatt.audit import audit
        try:
            audit("web_logout",
                   {"ip": request.client.host if request.client else "?"},
                   Path.cwd(), "_web")
        except Exception:  # noqa: BLE001, S110
            pass
        response = JSONResponse({"ok": True})
        clear_session_cookie(response)
        return response

    return router
