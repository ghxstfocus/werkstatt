"""FastAPI-App mit REST-Handlern fuer die Werkstatt-Web-UI.

Stellt Endpunkte fuer Projekt-Status, Phasen-Snapshot und Loop-Steuerung
bereit. Die Handler sind bewusst synchron (``def``), damit FastAPI sie im
Threadpool ausfuehrt; die Prozess-Registry ist ein einfaches dict ohne Lock.
"""

import asyncio
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from werkstatt.event_store import EventStore
from werkstatt.phase_state import PhaseState
from werkstatt.web import audit_panel, auth, shell, terminal_proxy, ws

__all__ = ["app", "create_app"]

_PROJEKTNAME_MUSTER = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_RUN_ID_MUSTER = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")

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


def _pruefe_run_id(run_id: str) -> str:
    """Validiert eine Run-ID gegen Injection und unsinnig lange Strings.

    Die Run-ID fliesst in eine SQL-Query (parametrisiert) und in Logs;
    die Validierung ist die zweite Verteidigungslinie und verhindert
    Log-Injection ueber unsinnig lange Strings.
    """
    if not isinstance(run_id, str) or not _RUN_ID_MUSTER.fullmatch(run_id):
        raise HTTPException(status_code=400, detail="ungueltige run_id")
    return run_id


_SESSION_ID_MUSTER = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


def _pruefe_session_id(session_id: str) -> str:
    """Validiert eine Chat-Session-ID (SQL-Injection-Schutz)."""
    if not isinstance(session_id, str) or not _SESSION_ID_MUSTER.fullmatch(session_id):
        raise HTTPException(status_code=400, detail="ungueltige session_id")
    return session_id


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


def _registriere_event_routen(app: FastAPI) -> None:
    """Registriert den Event-Query-Endpoint fuer einen Run."""

    @app.get("/api/runs/{run_id}/events")
    def run_events(
        run_id: str,
        since_seq: int | None = None,
        kind: str | None = None,
    ) -> list[dict[str, Any]]:
        """Liefert Events eines Runs, optional gefiltert."""
        geprueft = _pruefe_run_id(run_id)
        return EventStore().query(geprueft, since_seq=since_seq, kind=kind)


    @app.get("/api/runs/{run_id}/gates")
    def run_gates(run_id: str) -> list[dict[str, Any]]:
        """Listet offene Gates: gate_open ohne passende gate_answered."""
        geprueft = _pruefe_run_id(run_id)
        store = EventStore()
        opens = store.query(geprueft, kind="gate_open")
        beantwortet = {
            (ev.get("payload") or {}).get("gate_id")
            for ev in store.query(geprueft, kind="gate_answered")
        }
        ergebnis: list[dict[str, Any]] = []
        for ev in opens:
            payload = ev.get("payload") or {}
            gid = payload.get("gate_id")
            if gid in beantwortet:
                continue
            ergebnis.append({
                "gate_id": gid,
                "prompt": payload.get("prompt"),
                "optionen": payload.get("optionen"),
                "seq": ev.get("seq"),
                "ts": ev.get("ts"),
            })
        return ergebnis

    @app.post("/api/runs/{run_id}/gate")
    def run_gate_answer(
        run_id: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        """Beantwortet ein offenes Gate: {gate_id, answer}."""
        geprueft = _pruefe_run_id(run_id)
        gate_id = body.get("gate_id")
        answer = body.get("answer")
        if not isinstance(gate_id, str) or not gate_id:
            raise HTTPException(status_code=400, detail="gate_id fehlt")
        if not isinstance(answer, str) or not answer:
            raise HTTPException(status_code=400, detail="answer fehlt")
        store = EventStore()
        offen = {
            (ev.get("payload") or {}).get("gate_id")
            for ev in store.query(geprueft, kind="gate_open")
        }
        beantwortet = {
            (ev.get("payload") or {}).get("gate_id")
            for ev in store.query(geprueft, kind="gate_answered")
        }
        if gate_id not in offen:
            raise HTTPException(status_code=404, detail="gate nicht offen")
        if gate_id in beantwortet:
            raise HTTPException(status_code=409, detail="gate schon beantwortet")
        store.append(
            run_id=geprueft,
            kind="gate_answered",
            payload={"gate_id": gate_id, "answer": answer},
        )
        return {"ok": True, "gate_id": gate_id}


class AuthMiddleware:
    """Prueft Session-Cookie. Public: /login, /api/auth/*, /static/*."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
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

    # WICHTIG: shell.router VOR ws.router — sonst matcht
    # /ws/{tab_id} aus ws.router den /ws/shell-Request und der
    # PTY-Handler wird nie erreicht (Starlette matcht in Reihenfolge).
    app.include_router(shell.router)
    app.include_router(ws.router)
    app.include_router(audit_panel.router)
    app.include_router(terminal_proxy.router)
    _registriere_event_routen(app)

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
        import secrets as _secrets
        import time as _time
        run_id = (
            f"{projektname}-{_time.strftime('%Y%m%d-%H%M%S')}"
            f"-{_secrets.token_hex(4)}"
        )
        prozess = subprocess.Popen(
            [sys.executable, "-m", "werkstatt.loop",
             "--project", projektname,
             "--headless",
             "--run-id", run_id],
        )
        _LAUFENDE_LOOPS[projektname] = prozess
        return {
            "gestartet": True,
            "pid": prozess.pid,
            "run_id": run_id,
        }

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

    @app.get("/api/projects/{name}/tokens")
    def project_tokens(name: str, run_id: str | None = None) -> dict[str, Any]:
        """Token-Verbrauch: Loop (pro Run) und Chat (pro Projekt)."""
        from werkstatt.web import inspector as _insp
        projekt = _pruefe_projektname(name)
        return _insp.aggregate_tokens(projekt, run_id=run_id)

    @app.get("/api/projects/{name}/chat/sessions")
    def chat_sessions(name: str) -> dict[str, Any]:
        """Listet alle Chat-Session-IDs eines Projekts."""
        from werkstatt import chat_session as _cs
        projekt = _pruefe_projektname(name)
        return {"sessions": _cs.list_sessions(projekt)}

    @app.get("/api/projects/{name}/chat/history")
    def chat_history(name: str, session_id: str) -> dict[str, Any]:
        """Liefert die Event-Historie einer Session."""
        from werkstatt import chat_session as _cs
        projekt = _pruefe_projektname(name)
        sid = _pruefe_session_id(session_id)
        return {"events": _cs.ChatSession(projekt, sid).load()}

    @app.post("/api/projects/{name}/chat/new")
    def chat_new(name: str) -> dict[str, Any]:
        """Erzeugt eine neue (leere) Session-ID."""
        import uuid as _uuid
        _pruefe_projektname(name)
        return {"session_id": _uuid.uuid4().hex}

    @app.post("/api/projects/{name}/chat")
    def chat_send(name: str, body: dict[str, Any]) -> dict[str, Any]:
        """Sendet Nachricht, antwortet non-streaming."""
        from werkstatt import chat_agent as _ca
        from werkstatt import chat_session as _cs
        projekt = _pruefe_projektname(name)
        session_id = body.get("session_id")
        message = body.get("message")
        mode = str(body.get("mode", "read"))
        if not isinstance(session_id, str) or not session_id:
            raise HTTPException(status_code=400, detail="session_id fehlt")
        if not isinstance(message, str) or not message:
            raise HTTPException(status_code=400, detail="message fehlt")
        if mode not in ("read", "write"):
            raise HTTPException(status_code=400, detail="mode ungueltig")
        sid = _pruefe_session_id(session_id)
        session = _cs.ChatSession(projekt, sid)
        try:
            antwort = _ca.chat_loop(session, message, mode=mode)
        except RuntimeError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return {"session_id": sid, "antwort": antwort}

    @app.websocket("/api/projects/{name}/chat/stream")
    async def chat_stream(websocket: WebSocket, name: str) -> None:
        """Streaming-Chat: Client sendet {session_id, message, mode},
        Server sendet {type: chunk|tool_call|tool_result|done|error}."""
        from werkstatt import chat_agent as _ca
        from werkstatt import chat_session as _cs
        from werkstatt.web.auth import is_auth_disabled, is_authed_ws

        if not is_auth_disabled() and not is_authed_ws(websocket):
            await websocket.close(code=1008)
            return
        try:
            projekt = _pruefe_projektname(name)
        except HTTPException:
            await websocket.accept()
            await websocket.close(code=1008)
            return

        await websocket.accept()
        loop = asyncio.get_running_loop()

        async def _send(daten: dict[str, Any]) -> None:
            await websocket.send_json(daten)

        def _sync_send(daten: dict[str, Any]) -> None:
            fut = asyncio.run_coroutine_threadsafe(_send(daten), loop)
            try:
                fut.result(timeout=10)
            except Exception:
                pass

        try:
            while True:
                roh = await websocket.receive_json()
                if not isinstance(roh, dict):
                    await _send({"type": "error", "detail": "ungueltiges JSON"})
                    continue
                try:
                    sid = _pruefe_session_id(roh.get("session_id", ""))
                    message = roh.get("message")
                    if not isinstance(message, str) or not message:
                        raise HTTPException(status_code=400, detail="message fehlt")
                    mode = str(roh.get("mode", "read"))
                    if mode not in ("read", "write"):
                        raise HTTPException(status_code=400, detail="mode ungueltig")
                except HTTPException as exc:
                    await _send({"type": "error", "detail": str(exc.detail)})
                    continue

                session = _cs.ChatSession(projekt, sid)

                def on_chunk(text: str) -> None:
                    _sync_send({"type": "chunk", "text": text})

                def on_tool_call(n: str, a: dict[str, Any]) -> None:
                    _sync_send({"type": "tool_call", "name": n, "args": a})

                def on_tool_result(n: str, r: str) -> None:
                    _sync_send({"type": "tool_result", "name": n, "content": r})

                try:
                    antwort = await asyncio.to_thread(
                        _ca.chat_loop, session, message,
                        mode=mode,
                        on_chunk=on_chunk,
                        on_tool_call=on_tool_call,
                        on_tool_result=on_tool_result,
                    )
                except RuntimeError as exc:
                    await _send({"type": "error", "detail": str(exc)})
                    continue
                await _send({"type": "done", "antwort": antwort})
        except WebSocketDisconnect:
            return

    return app


app = create_app()
