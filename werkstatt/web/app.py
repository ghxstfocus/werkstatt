"""FastAPI-App mit REST-Handlern fuer die Werkstatt-Web-UI.

Stellt Endpunkte fuer Projekt-Status, Phasen-Snapshot und Loop-Steuerung
bereit. Die Handler sind bewusst synchron (``def``), damit FastAPI sie im
Threadpool ausfuehrt; die Prozess-Registry ist ein einfaches dict ohne Lock.
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from werkstatt.phase_state import PhaseState
from werkstatt.web import audit_panel, auth, chat, shell, terminal_proxy, ws

__all__ = ["app", "create_app"]

_PROJEKTNAME_MUSTER = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

_LAUFENDE_LOOPS: dict[str, subprocess.Popen] = {}


def _pruefe_projektname(name: str) -> str:
    """Validiert einen Projektnamen gegen Pfad-Traversal.

    Der Projektname fliesst sowohl in Subprozess-Argv als auch in
    Dateipfade (``load_project_config``). Bei Verstoss wird eine
    HTTP-400-Antwort ausgeloest.
    """
    if not isinstance(name, str) or not _PROJEKTNAME_MUSTER.fullmatch(name):
        raise HTTPException(status_code=400, detail="ungueltiger Projektname")
    return name


def _phasen_snapshot(name: str) -> dict[str, Any]:
    """Liest den zentralen Phasen-State read-only als JSON-taugliches dict.

    Baut eine PhaseState-Instanz fuer das Projekt und ruft ``load()``
    als Instanz-Methode. Fehlende Datei ist ein normaler Zustand fuer
    das Frontend und wird als ``{"verfuegbar": False, ...}`` zurueck-
    gegeben, nicht als 500er.
    """
    try:
        phase_state = PhaseState(name)
        if not phase_state.exists():
            return {"verfuegbar": False, "fehler": "phase_state fehlt"}
        phase_state.load()
    except (FileNotFoundError, OSError, ValueError, KeyError, RuntimeError) as fehler:
        return {"verfuegbar": False, "fehler": str(fehler)}

    naechste_task_id: Any = None
    try:
        naechster = phase_state.get_next_task()
    except (AttributeError, KeyError, IndexError, ValueError, StopIteration):
        naechster = None

    if naechster is not None:
        naechste_task_id = getattr(naechster, "task_id", None)
        if naechste_task_id is None and isinstance(naechster, dict):
            naechste_task_id = naechster.get("task_id")

    return {
        "verfuegbar": True,
        "state_typ": type(phase_state).__name__,
        "naechste_task_id": naechste_task_id,
    }


class AuthMiddleware:
    """Prueft Session-Cookie. Public: /login, /api/auth/*, /static/*."""

    def __init__(self, app):  # type: ignore[no-untyped-def]
        self.app = app

    async def __call__(self, scope, receive, send):  # type: ignore[no-untyped-def]
        from starlette.requests import Request

        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        if auth.is_auth_disabled():
            return await self.app(scope, receive, send)
        request = Request(scope)
        if request.method == "OPTIONS":
            return await self.app(scope, receive, send)
        if auth.is_public_path(request.url.path):
            return await self.app(scope, receive, send)
        if auth.is_authed(request):
            return await self.app(scope, receive, send)
        accept = request.headers.get("accept", "")
        if "text/html" in accept:
            from starlette.responses import RedirectResponse
            response = RedirectResponse("/login", status_code=303)
        else:
            from starlette.responses import JSONResponse
            response = JSONResponse(
                {"ok": False, "fehler": "unauthorized"},
                status_code=401,
            )
        return await response(scope, receive, send)


def create_app() -> FastAPI:
    """Erzeugt und konfiguriert die FastAPI-Anwendung."""
    app = FastAPI(title="Werkstatt")
    app.add_middleware(AuthMiddleware)
    app.include_router(auth.make_login_router())
    # Audit-Panel: Home auf Projekt-Root setzen, damit
    # /api/projects/*/audit die audit-logs/ findet.
    from werkstatt.web import audit_panel as _ap
    _ap._home_kontext = Path.cwd()

    app.include_router(ws.router)
    app.include_router(chat.router)
    app.include_router(audit_panel.router)
    app.include_router(terminal_proxy.router)
    app.include_router(shell.router)

    # Layout/CSS/JS liegen in /opt/werkstatt/static/ (Projekt-Root),
    # nicht in werkstatt/web/static/ (Modul-Package).
    static_dir = Path(__file__).resolve().parent.parent.parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/")
    def index() -> FileResponse:
        """Liefert das HTML-Layout der Web-UI."""
        return FileResponse(str(static_dir / "layout.html"))

    @app.get("/api/projects/{name}/state")
    def project_state(name: str) -> dict[str, Any]:
        """Liefert den Phasen-Snapshot eines Projekts."""
        projektname = _pruefe_projektname(name)
        return _phasen_snapshot(projektname)

    @app.post("/api/projects/{name}/start")
    def project_start(name: str) -> dict[str, Any]:
        """Startet den Loop fuer ein Projekt als Subprozess."""
        projektname = _pruefe_projektname(name)
        laufend = _LAUFENDE_LOOPS.get(projektname)
        if laufend is not None and laufend.poll() is None:
            return {"gestartet": False, "pid": laufend.pid,
                    "grund": "laeuft_bereits"}
        prozess = subprocess.Popen(
            [sys.executable, "-m", "werkstatt.loop", "--project", projektname],
        )
        _LAUFENDE_LOOPS[projektname] = prozess
        return {"gestartet": True, "pid": prozess.pid}

    @app.post("/api/projects/{name}/stop")
    def project_stop(name: str) -> dict[str, Any]:
        """Stoppt den laufenden Loop eines Projekts."""
        projektname = _pruefe_projektname(name)
        prozess = _LAUFENDE_LOOPS.get(projektname)
        if prozess is None or prozess.poll() is not None:
            raise HTTPException(status_code=404, detail="kein laufender Loop")
        prozess.terminate()
        returncode = prozess.wait()
        _LAUFENDE_LOOPS.pop(projektname, None)
        return {"gestoppt": True, "returncode": returncode}

    return app


app = create_app()
