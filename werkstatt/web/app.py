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
from werkstatt.validierung import pruefe_ref as _pruefe_ref_kern
from werkstatt.web import audit_panel, auth, terminal_proxy, ws

__all__ = ["app", "create_app"]

_PROJEKTNAME_MUSTER = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_RUN_ID_MUSTER = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")

# OP-305: Basis fuer Multi-Projekt-Pfade (testbar via monkeypatch)
_PROJECTS_BASE = Path("/opt")

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


def _pruefe_ref(ref: str) -> str:
    """HTTP-Adapter um werkstatt.validierung.pruefe_ref.

    Wandelt ValueError in HTTPException(400), damit der Endpoint
    einheitlich mit _pruefe_projektname und _pruefe_run_id antwortet.
    """
    try:
        return _pruefe_ref_kern(ref)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
        abgelaufen = {
            (ev.get("payload") or {}).get("gate_id")
            for ev in store.query(geprueft, kind="gate_expired")
        }
        if gate_id not in offen:
            raise HTTPException(status_code=404, detail="gate nicht offen")
        if gate_id in abgelaufen:
            raise HTTPException(status_code=410,
                                detail="gate abgelaufen (timeout)")
        if gate_id in beantwortet:
            raise HTTPException(status_code=409, detail="gate schon beantwortet")
        # OP-323c: audit() statt store.append() + flush fuer wait()
        from pathlib import Path as _Path

        from werkstatt.audit import audit
        from werkstatt.projection import Projector as _Projector
        audit("gate_answered", {
            "gate_id": gate_id,
            "answer": answer,
            "run_id": geprueft,
        }, _Path("."), "werkstatt")
        try:
            _Projector().tail()
        except Exception:
            pass
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

    @app.get("/api/overview")
    def overview() -> dict[str, Any]:
        """OP-306b Etappe 1: Projekt-Liste + Sparkline + KPI."""
        from werkstatt.web import inspector as _insp
        return _insp.aggregate_overview()

    @app.get("/api/projects/{name}/state")
    def project_state(name: str) -> dict[str, Any]:
        """Liefert den Phasen-Snapshot eines Projekts."""
        projektname = _pruefe_projektname(name)
        return _phasen_snapshot(projektname)

    @app.post("/api/projects/create")
    def project_create(body: dict[str, Any]) -> dict[str, Any]:
        """OP-305: Neues Projekt anlegen (scaffold)."""
        import re as _re
        name = str(body.get("name") or "").strip()
        pfad = str(body.get("pfad") or "").strip()
        if not _re.fullmatch(r"[a-z][a-z0-9_-]{0,50}", name):
            raise HTTPException(
                status_code=400,
                detail="Projektname ungueltig: a-z, 0-9, _, - (max 51)",
            )
        if not pfad.startswith("/opt/"):
            raise HTTPException(
                status_code=400,
                detail="Pfad muss unter /opt/ liegen",
            )
        try:
            projekt_dir = Path(pfad).resolve()
        except (OSError, RuntimeError) as exc:
            raise HTTPException(status_code=400, detail=f"Pfad ungueltig: {exc}")
        if not str(projekt_dir).startswith("/opt/"):
            raise HTTPException(
                status_code=400,
                detail="Pfad muss unter /opt/ bleiben (Symlink?)",
            )
        if projekt_dir.exists():
            if not projekt_dir.is_dir():
                raise HTTPException(
                    status_code=409,
                    detail="Pfad existiert und ist keine Verzeichnis",
                )
            try:
                if any(projekt_dir.iterdir()):
                    raise HTTPException(
                        status_code=409,
                        detail="Zielverzeichnis nicht leer",
                    )
            except OSError as exc:
                raise HTTPException(status_code=500, detail=f"Lesen: {exc}")
        projekt_dir.mkdir(parents=True, exist_ok=True)
        from werkstatt.scaffold import scaffold
        try:
            bericht = scaffold(name, projekt_dir)
        except (FileNotFoundError, NotADirectoryError) as exc:
            raise HTTPException(status_code=500, detail=str(exc))
        return {
            "ok": True,
            "name": name,
            "pfad": str(projekt_dir),
            "bericht": bericht,
        }

    @app.post("/api/projects/{name}/start")
    def project_start(name: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        """Startet den Loop fuer ein Projekt als Subprozess.

        OP-303: optionaler body {aufgabe: str} oder {op_id: "OP-303"}.
        Ohne aufgabe: Loop liest selbst die naechste OP aus STATUS.md.
        """
        projektname = _pruefe_projektname(name)
        # OP-305: Projekt muss minimal initialisiert sein (STATUS.md da),
        # sonst startet der Loop ins Leere (oder falschen Kontext).
        _pd = _PROJECTS_BASE / projektname
        if not (_pd / "docs" / "STATUS.md").is_file():
            raise HTTPException(
                status_code=404,
                detail=f"Projekt {projektname!r} hat kein docs/STATUS.md",
            )
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
        args = [sys.executable, "-m", "werkstatt.loop",
                "--project", projektname,
                "--headless",
                "--run-id", run_id]
        aufgabe = ""
        op_id = ""
        if body and isinstance(body, dict):
            op_id = str(body.get("op_id") or "").strip()
            aufgabe = str(body.get("aufgabe") or "").strip()
            if op_id and not aufgabe:
                # aus STATUS.md ziehen
                from werkstatt.web import inspector as _insp
                for op in _insp.parse_ops(_PROJECTS_BASE / projektname):
                    if op.get("id") == op_id:
                        aufgabe = f"{op_id}: {op.get('titel', '')}"
                        break
        if aufgabe:
            args.extend(["--aufgabe", aufgabe])
        prozess = subprocess.Popen(args)
        _LAUFENDE_LOOPS[projektname] = prozess
        return {
            "gestartet": True,
            "pid": prozess.pid,
            "run_id": run_id,
            "aufgabe": aufgabe or "(automatisch aus STATUS.md)",
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

    @app.get("/api/projects/{name}/gate/context")
    def gate_context(name: str, run_id: str | None = None) -> dict[str, Any]:
        from werkstatt.web import inspector as _insp
        projekt = _pruefe_projektname(name)
        return _insp.aggregate_gate_context(projekt, run_id=run_id)

    @app.get("/api/projects/{name}/plan/versions")
    def plan_versions(name: str, run_id: str | None = None) -> dict[str, Any]:
        from werkstatt.web import inspector as _insp
        projekt = _pruefe_projektname(name)
        return {"versionen": _insp.aggregate_plan_versions(projekt, run_id=run_id)}

    @app.get("/api/projects/{name}/handoffs")
    def handoffs(name: str, run_id: str | None = None) -> dict[str, Any]:
        from werkstatt.web import inspector as _insp
        projekt = _pruefe_projektname(name)
        return {"handoffs": _insp.aggregate_handoffs(projekt, run_id=run_id)}

    @app.get("/api/projects/{name}/role/{rolle}")
    def project_role_events(name: str, rolle: str,
                            run_id: str | None = None) -> dict[str, Any]:
        """Events einer Rolle (builder/reviewer/verify/explorer/...)."""
        from werkstatt.web import inspector as _insp
        projekt = _pruefe_projektname(name)
        if rolle not in ("explorer", "scout", "planner", "architect",
                          "builder", "reviewer", "verify", "reflection",
                          "phase_review", "llm"):
            raise HTTPException(status_code=400, detail="unbekannte rolle")
        return _insp.aggregate_role_events(projekt, rolle, run_id=run_id)

    @app.get("/api/projects/{name}/evidence")
    def evidence_links(name: str, run_id: str | None = None) -> dict[str, Any]:
        from werkstatt.web import inspector as _insp
        projekt = _pruefe_projektname(name)
        return {"links": _insp.aggregate_evidence_links(projekt, run_id=run_id)}

    @app.get("/api/projects/{name}/diff")
    def project_diff(name: str, ref: str = "HEAD") -> dict[str, Any]:
        """git diff gegen ref (default HEAD), als Text + Stat."""
        import subprocess as _sp
        projektname = _pruefe_projektname(name)
        ref = _pruefe_ref(ref)
        basis = _PROJECTS_BASE / projektname
        try:
            stat = _sp.run(
                ["git", "diff", "--stat", ref, "--"],
                capture_output=True, text=True, timeout=10,
                cwd=str(basis), check=False,
            ).stdout
            diff = _sp.run(
                ["git", "diff", ref, "--"],
                capture_output=True, text=True, timeout=20,
                cwd=str(basis), check=False,
            ).stdout
        except (_sp.TimeoutExpired, OSError) as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return {"ref": ref, "stat": stat[:20_000], "diff": diff[:200_000]}

    @app.get("/api/projects/{name}/verify")
    def project_verify(name: str) -> dict[str, Any]:
        """Letzte Verify-Ausgabe aus audit-logs/ (verify_*)."""
        import json as _json
        _pruefe_projektname(name)
        aus: dict[str, Any] = {"events": [], "anzahl": 0}
        basis = Path.cwd() / "audit-logs"
        if not basis.is_dir():
            return aus
        kandidaten = sorted(basis.glob("agent-pipeline-*.jsonl"))
        if not kandidaten:
            return aus
        try:
            with kandidaten[-1].open(encoding="utf-8", errors="replace") as f:
                for zeile in f:
                    zeile = zeile.strip()
                    if not zeile:
                        continue
                    try:
                        obj = _json.loads(zeile)
                    except _json.JSONDecodeError:
                        continue
                    if isinstance(obj, dict) and str(obj.get("kind", "")).startswith("verify_"):
                        aus["events"].append(obj)
                        if len(aus["events"]) >= 200:
                            break
        except OSError:
            pass
        aus["anzahl"] = len(aus["events"])
        return aus

    @app.get("/api/projects/{name}/files")
    def project_files(name: str, pfad: str = "") -> dict[str, Any]:
        """Datei-Browser unterhalb des Projekt-Roots."""
        projektname = _pruefe_projektname(name)
        basis = (_PROJECTS_BASE / projektname).resolve()
        ziel = (basis / pfad).resolve() if pfad else basis
        try:
            ziel.relative_to(basis)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Pfad ausserhalb Projekt") from exc
        if not ziel.exists():
            raise HTTPException(status_code=404, detail="Pfad nicht gefunden")
        if ziel.is_file():
            try:
                inhalt = ziel.read_text(encoding="utf-8", errors="replace")[:50_000]
            except OSError as exc:
                raise HTTPException(status_code=500, detail=str(exc)) from exc
            return {"pfad": pfad, "typ": "file", "inhalt": inhalt}
        eintraege: list[dict[str, Any]] = []
        try:
            for kind in sorted(ziel.iterdir(), key=lambda x: (x.is_file(), x.name)):
                if kind.name.startswith(".") and kind.name not in (".werkstatt",):
                    continue
                if kind.name in ("__pycache__", "node_modules", ".git"):
                    continue
                eintraege.append({
                    "name": kind.name,
                    "typ": "dir" if kind.is_dir() else "file",
                    "groesse": kind.stat().st_size if kind.is_file() else 0,
                })
        except OSError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return {"pfad": pfad, "typ": "dir", "eintraege": eintraege[:500]}

    @app.get("/api/projects/{name}/ops")
    def project_ops(name: str) -> dict[str, Any]:
        """OPs aus docs/STATUS.md des AKTIVEN Projekts (Runs-Liste)."""
        from werkstatt.web import inspector as _insp
        projektname = _pruefe_projektname(name)
        # OP-305: projekt-spezifischer Pfad statt globaler Fallback
        projekt_dir = _PROJECTS_BASE / projektname
        return {"ops": _insp.parse_ops(projekt_dir)}

    @app.get("/api/projects/{name}/ops/run-status")
    def project_ops_run_status(name: str) -> dict[str, Any]:
        """OP-303: Run-Status pro OP."""
        from werkstatt.web import inspector as _insp
        projekt = _pruefe_projektname(name)
        return {"run_status": _insp.aggregate_ops_run_status(projekt)}

    @app.get("/api/projects/{name}/palette")
    def project_palette(name: str, q: str = "") -> dict[str, Any]:
        """OP-302: Server-Filter fuer Command Palette."""
        from werkstatt.web import inspector as _insp
        projekt = _pruefe_projektname(name)
        return _insp.aggregate_palette(projekt, q)

    @app.get("/api/projects/{name}/timeline")
    def project_timeline(name: str, run_id: str | None = None) -> dict[str, Any]:
        """Phasen-Knoten aus Event-Store + JSONL-Audit."""
        from werkstatt.web import inspector as _insp
        projekt = _pruefe_projektname(name)
        knoten = _insp.aggregate_timeline(projekt, run_id=run_id)
        st = _insp.aggregate_status(projekt)
        return {"run_id": run_id or st.get("run_id"), "knoten": knoten}

    @app.get("/api/projects/{name}/status")
    def project_status(name: str) -> dict[str, Any]:
        """Tasks/Verify/Drift/Phase fuer Statusleiste."""
        from werkstatt.web import inspector as _insp
        projekt = _pruefe_projektname(name)
        return _insp.aggregate_status(projekt)

    @app.get("/api/projects/{name}/projection/status")
    def projection_status(name: str) -> dict[str, Any]:
        """OP-323: JSONL vs. SQLite Divergenz."""
        _pruefe_projektname(name)
        from werkstatt.projection import Projector
        return Projector().status()

    @app.get("/api/projects/{name}/ambient")
    def ambient(name: str) -> dict[str, Any]:
        """OP-301: Loop-Status + letzter Run + Tokens + Gates."""
        from werkstatt.web import inspector as _insp
        projekt = _pruefe_projektname(name)
        return _insp.aggregate_ambient(projekt)

    @app.get("/api/projects/{name}/chat/sessions")
    def chat_sessions(name: str) -> dict[str, Any]:
        """Listet alle Chat-Session-IDs eines Projekts."""
        from werkstatt import chat_session as _cs
        projekt = _pruefe_projektname(name)
        return {"sessions": _cs.list_sessions(projekt, mit_inhalt=True)}

    @app.get("/api/projects/{name}/chat/history")
    def chat_history(name: str, session_id: str) -> dict[str, Any]:
        """Liefert die Event-Historie einer Session."""
        from werkstatt import chat_session as _cs
        projekt = _pruefe_projektname(name)
        sid = _pruefe_session_id(session_id)
        return {"events": _cs.ChatSession(projekt, sid).load()}

    @app.post("/api/projects/{name}/chat/new")
    def chat_new(name: str) -> dict[str, Any]:
        """Erzeugt eine neue Session mit Marker-Event (damit sie in
        list_sessions erscheint, auch ohne Nachricht)."""
        import uuid as _uuid

        from werkstatt import chat_session as _cs
        projekt = _pruefe_projektname(name)
        sid = _uuid.uuid4().hex
        _cs.ChatSession(projekt, sid).append("session_start", {})
        return {"session_id": sid}

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
