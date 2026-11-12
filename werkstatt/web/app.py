"""FastAPI-App mit REST-Handlern fuer die Werkstatt-Web-UI.

Stellt Endpunkte fuer Projekt-Status, Phasen-Snapshot und Loop-Steuerung
bereit. Die Handler sind bewusst synchron (``def``), damit FastAPI sie im
Threadpool ausfuehrt; Start und Stop pro Projekt werden serialisiert.
"""

import asyncio
import os
import re
import signal
import sqlite3
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from werkstatt.event_store import EventStore
from werkstatt.phase_state import PhaseState
from werkstatt.validierung import pruefe_ref as _pruefe_ref_kern
from werkstatt.web import audit_panel, auth, terminal_proxy, ws
from werkstatt.web.op_selector import (
    load_accepted_adr_ids,
    parse_completed_op_ids,
    select_next_op,
)

__all__ = ["app", "create_app"]

_PROJEKTNAME_MUSTER = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_RUN_ID_MUSTER = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")

# OP-305: Basis fuer Multi-Projekt-Pfade (testbar via monkeypatch)
_PROJECTS_BASE = Path("/opt")

_LAUFENDE_LOOPS: dict[str, Any] = {}
_LOOP_LOG_HANDLES: dict[str, Any] = {}
_LOOP_RUN_IDS: dict[str, str] = {}
_PAUSIERTE_LOOPS: set[str] = set()
_LOOP_PROCESS_STATES = ("running", "paused", "pausing", "resuming", "stopping")
_LOOP_REGISTRY_PATH = (
    Path(__file__).resolve().parents[2] / ".werkstatt" / "web-loop-registry.db"
)
_LOOP_LOCKS: dict[str, Any] = {}
_LOOP_LOCKS_GUARD = threading.Lock()


def _projekt_loop_lock(projektname: str) -> Any:
    """Serialisiert Start/Stop fuer ein Projekt ueber Threadpool-Requests."""
    with _LOOP_LOCKS_GUARD:
        return _LOOP_LOCKS.setdefault(projektname, threading.RLock())


def _loop_registry() -> Any:
    """Shared SQLite-Registry; Tests erhalten sie unter ihrem PROJECTS_BASE."""
    from werkstatt.web.loop_registry import LoopProcessRegistry

    path = _LOOP_REGISTRY_PATH
    if _PROJECTS_BASE != Path("/opt"):
        path = _PROJECTS_BASE / ".werkstatt" / "web-loop-registry.db"
    return LoopProcessRegistry(path)


def _loop_prozess(projektname: str) -> Any | None:
    """Liefert den lokalen oder nach Server-Neustart wiedergefundenen Loop."""
    prozess = _LAUFENDE_LOOPS.get(projektname)
    if prozess is not None and prozess.poll() is None:
        record = _loop_registry().read(projektname)
        if (
            record is not None
            and record["state"] in _LOOP_PROCESS_STATES
            and record.get("pid") == prozess.pid
            and (
                not _LOOP_RUN_IDS.get(projektname)
                or _LOOP_RUN_IDS[projektname] == record["run_id"]
            )
        ):
            _LOOP_RUN_IDS[projektname] = record["run_id"]
            if record["state"] == "paused":
                _PAUSIERTE_LOOPS.add(projektname)
            else:
                _PAUSIERTE_LOOPS.discard(projektname)
        return prozess
    if prozess is not None:
        _LAUFENDE_LOOPS.pop(projektname, None)
        _PAUSIERTE_LOOPS.discard(projektname)
        log_fh = _LOOP_LOG_HANDLES.pop(projektname, None)
        if log_fh is not None:
            try:
                log_fh.close()
            except OSError:
                pass

    registry = _loop_registry()
    record = registry.read(projektname)
    if not record or record["state"] not in _LOOP_PROCESS_STATES:
        return None
    pid = record.get("pid")
    if pid is None:
        return None
    from werkstatt.web.loop_registry import AttachedLoopProcess

    recovered = AttachedLoopProcess(pid, record.get("process_identity"))
    if recovered.poll() is not None:
        registry.set_state(projektname, record["run_id"], "idle")
        return None
    _LAUFENDE_LOOPS[projektname] = recovered
    _LOOP_RUN_IDS[projektname] = record["run_id"]
    if record["state"] == "paused":
        _PAUSIERTE_LOOPS.add(projektname)
    else:
        _PAUSIERTE_LOOPS.discard(projektname)
    return recovered


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


def _completed_op_ids(project_dir: Path, status_text: str) -> set[str]:
    """Liest explizite Abschlussbelege aus der Projekt-Historie."""
    progress_path = project_dir / "PROGRESS.md"
    try:
        progress_text = progress_path.read_text(
            encoding="utf-8", errors="replace",
        )
    except OSError:
        progress_text = ""
    return parse_completed_op_ids(progress_text, status_text)

def _accepted_adr_ids(project_dir: Path) -> set[str]:
    """Liefert angenommene Architekturentscheidungen des Projekts."""
    return load_accepted_adr_ids(project_dir / "docs" / "adr")


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
        answer = answer.strip()
        if not answer:
            raise HTTPException(status_code=400, detail="answer fehlt")
        if len(answer) > 20_000:
            raise HTTPException(status_code=413, detail="answer zu lang")

        store = EventStore()
        gate_events = store.query(geprueft, kind="gate_open")
        gate_event = next(
            (
                ev for ev in gate_events
                if (ev.get("payload") or {}).get("gate_id") == gate_id
            ),
            None,
        )
        if gate_event is None:
            raise HTTPException(status_code=404, detail="gate nicht offen")
        beantwortet = {
            (ev.get("payload") or {}).get("gate_id")
            for ev in store.query(geprueft, kind="gate_answered")
        }
        abgelaufen = {
            (ev.get("payload") or {}).get("gate_id")
            for ev in store.query(geprueft, kind="gate_expired")
        }
        if gate_id in abgelaufen:
            raise HTTPException(status_code=410,
                                detail="gate abgelaufen (timeout)")
        if gate_id in beantwortet:
            raise HTTPException(status_code=409, detail="gate schon beantwortet")

        gate_payload = gate_event.get("payload") or {}
        if gate_payload.get("typ") != "freitext":
            optionen = gate_payload.get("optionen", "jna")
            if (
                not isinstance(optionen, str)
                or not optionen
                or any(zeichen not in "jnea" for zeichen in optionen)
            ):
                raise HTTPException(
                    status_code=422, detail="Gate-Optionen ungueltig",
                )
            answer = answer.lower()
            if len(answer) != 1 or answer not in optionen:
                raise HTTPException(
                    status_code=422,
                    detail="answer ist keine angebotene Gate-Option",
                )

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


def _audit_web_loop_event(
    projektname: str,
    run_id: str,
    kind: str,
    status: str,
    payload: dict[str, Any],
) -> bool:
    """Schreibt ein projektbezogenes Control-Event in JSONL und projiziert es."""
    from werkstatt.audit import audit
    from werkstatt.projection import Projector

    try:
        geschrieben = audit(
            kind, {**payload, "status": status},
            _PROJECTS_BASE / projektname, projektname, run_id=run_id,
        )
    except (OSError, RuntimeError, TypeError, ValueError):
        return False
    if not geschrieben:
        return False
    try:
        Projector().tail()
    except (OSError, RuntimeError, sqlite3.Error, ValueError):
        pass
    return True


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

        OP-303: body enthaelt entweder eine explizite {aufgabe: str}
        oder {op_id: "OP-303"}. Ohne beides wird kein leerer Run gestartet.
        """
        prepared_source = None
        launch_succeeded = False
        try:
            projektname = _pruefe_projektname(name)
            _pd = _PROJECTS_BASE / projektname
            # Bereits laufende Arbeit hat Vorrang vor der Validierung einer
            # neuen Eingabe. Der spaetere Lock um Popen schliesst die Race-Luecke.
            with _projekt_loop_lock(projektname):
                laufend = _loop_prozess(projektname)
                record = _loop_registry().read(projektname)
                if laufend is not None or (record and record["state"] == "starting"):
                    return {
                        "gestartet": False,
                        "pid": laufend.pid if laufend is not None else None,
                        "run_id": (
                            _LOOP_RUN_IDS.get(projektname)
                            or (record.get("run_id") if record else None)
                        ),
                        "grund": "laeuft_bereits",
                    }
            import secrets as _secrets
            import time as _time
            run_id = (
                f"{projektname}-{_time.strftime('%Y%m%d-%H%M%S')}"
                f"-{_secrets.token_hex(4)}"
            )
            args = [sys.executable, "-m", "werkstatt.loop",
                    "--project", projektname,
                    "--headless",
                    "--run-id", run_id,
                    "--fresh"]
            from werkstatt import project_sources as _project_sources
            try:
                prepared_source = _project_sources.prepare_github_run_worktree(
                    _pd, run_id,
                )
            except _project_sources.GitHubSyncError as exc:
                raise HTTPException(
                    status_code=409,
                    detail={"code": "github_sync_blocked", "message": str(exc)},
                ) from exc
            _source_pd = (
                prepared_source.worktree_path if prepared_source is not None else _pd
            )
            if not (_source_pd / "docs" / "STATUS.md").is_file():
                raise HTTPException(
                    status_code=404,
                    detail=f"Projekt {projektname!r} hat kein docs/STATUS.md",
                )
            if prepared_source is not None:
                args.extend(["--project-dir", str(prepared_source.worktree_path)])
            aufgabe = ""
            op_id = ""
            if body and isinstance(body, dict):
                op_id = str(body.get("op_id") or "").strip()
                aufgabe = str(body.get("aufgabe") or "").strip()
            if aufgabe:
                op_id = ""
    
            if op_id and not aufgabe:
                if not re.fullmatch(r"OP-\d+[a-z]?", op_id):
                    raise HTTPException(status_code=400, detail="ungueltige op_id")
                from werkstatt.web import inspector as _insp
                ops = _insp.parse_ops(_source_pd)
                auswahl = next((op for op in ops if op.get("id") == op_id), None)
                if auswahl is None:
                    raise HTTPException(status_code=404, detail="OP nicht offen oder nicht gefunden")
                if auswahl.get("status") != "open":
                    raise HTTPException(status_code=409, detail="OP ist nicht als offen markiert")
                _status_md = _source_pd / "docs" / "STATUS.md"
                try:
                    _status_text = _status_md.read_text(
                        encoding="utf-8", errors="replace",
                    )
                except OSError as exc:
                    raise HTTPException(
                        status_code=500, detail="STATUS.md nicht lesbar",
                    ) from exc
                _entscheidung = select_next_op(
                    _status_text,
                    _completed_op_ids(_source_pd, _status_text),
                    accepted_adrs=_accepted_adr_ids(_source_pd),
                )
                _ausgeschlossen: dict[str, Any] = next(
                    (
                        item for item in _entscheidung["ausgeschlossen"]
                        if item.get("id") == op_id
                    ),
                    {},
                )
                _blocker_grund = [
                    grund for grund in _ausgeschlossen.get("gruende", [])
                    if (
                        "Abhaengigkeiten" in grund
                        or "Blocker-Angabe" in grund
                        or "Unbekannte oder widerspruechliche Blocker" in grund
                        or "OP-ID kommt mehrfach" in grund
                        or "Status fehlt" in grund
                        or "Phase-3 gesperrt" in grund
                        or "ADR-Voraussetzungen" in grund
                        or "Architektur-Voraussetzung" in grund
                    )
                ]
                if _blocker_grund:
                    raise HTTPException(
                        status_code=409,
                        detail="OP ist blockiert: " + "; ".join(_blocker_grund),
                    )
    
                if not aufgabe:
                    # Volltext aus STATUS.md (nicht nur Titel): der Explorer
                    # braucht konkrete Symbole und Pfade als Suchbegriffe.
                    _status_md = _source_pd / "docs" / "STATUS.md"
                    try:
                        _status_text = _status_md.read_text(
                            encoding="utf-8", errors="replace")
                    except OSError as exc:
                        raise HTTPException(
                            status_code=500, detail="STATUS.md nicht lesbar",
                        ) from exc
                    _m_op = re.search(
                        rf"^### {re.escape(op_id)}:.*?(?=^### OP-|\Z)",
                        _status_text, re.MULTILINE | re.DOTALL)
                    if not _m_op:
                        raise HTTPException(status_code=404, detail="OP-Text nicht gefunden")
                    aufgabe = _m_op.group(0).strip()
    
            autonome_auswahl: dict[str, Any] | None = None
            if not aufgabe and not op_id:
                try:
                    status_text = (_source_pd / "docs" / "STATUS.md").read_text(
                        encoding="utf-8", errors="replace",
                    )
                except OSError as exc:
                    raise HTTPException(
                        status_code=500, detail="STATUS.md nicht lesbar",
                    ) from exc
                entscheidung = select_next_op(
                    status_text,
                    _completed_op_ids(_source_pd, status_text),
                    accepted_adrs=_accepted_adr_ids(_source_pd),
                )
                if entscheidung["zustand"] == "needs_input":
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "code": "autonomy_selection_required",
                            "message": entscheidung["begruendung"],
                            "kandidaten": entscheidung["kandidaten"],
                        },
                    )
                if entscheidung["zustand"] != "selected":
                    raise HTTPException(
                        status_code=422,
                        detail={
                            "code": "no_ready_op",
                            "message": entscheidung["begruendung"],
                            "ausgeschlossen": entscheidung["ausgeschlossen"],
                        },
                    )
                ausgewaehlt = entscheidung["auswahl"]
                ausgewaehlte_aufgabe = entscheidung["aufgabe"]
                if (
                    not isinstance(ausgewaehlt, dict)
                    or not isinstance(ausgewaehlt.get("id"), str)
                    or not re.fullmatch(r"OP-\d+[a-z]?", ausgewaehlt["id"])
                    or not isinstance(ausgewaehlte_aufgabe, str)
                    or not ausgewaehlte_aufgabe.strip()
                ):
                    raise HTTPException(
                        status_code=500,
                        detail="Selector lieferte eine ungueltige Auswahl.",
                    )
                autonome_auswahl = ausgewaehlt
                aufgabe = ausgewaehlte_aufgabe.strip()
                op_id = ausgewaehlt["id"]
    
            if not aufgabe:
                raise HTTPException(
                    status_code=422,
                    detail="aufgabe oder offene, nicht blockierte op_id erforderlich",
                )
            args.extend(["--aufgabe", aufgabe])
            # Der FastAPI-Threadpool kann parallele Start-Requests bedienen.
            # Recheck und Popen muessen atomar sein, sonst starten zwei Builder
            # gleichzeitig im selben Working Tree.
            with _projekt_loop_lock(projektname):
                laufend = _loop_prozess(projektname)
                record = _loop_registry().read(projektname)
                if laufend is not None or (record and record["state"] == "starting"):
                    return {
                        "gestartet": False,
                        "pid": laufend.pid if laufend is not None else None,
                        "run_id": (
                            _LOOP_RUN_IDS.get(projektname)
                            or (record.get("run_id") if record else None)
                        ),
                        "grund": "laeuft_bereits",
                    }
                _LAUFENDE_LOOPS.pop(projektname, None)
                _LOOP_RUN_IDS.pop(projektname, None)
                _PAUSIERTE_LOOPS.discard(projektname)
                _altes_log = _LOOP_LOG_HANDLES.pop(projektname, None)
                if _altes_log is not None:
                    try:
                        _altes_log.close()
                    except OSError:
                        pass
    
                registry = _loop_registry()
                run_context: dict[str, Any] = {
                    "schema_version": 1,
                    "goal": aufgabe,
                    "op_id": op_id or None,
                    "origin": "web",
                    "source": (
                        {
                            "kind": "github",
                            "repository": prepared_source.repository,
                            "branch": prepared_source.branch,
                            "base_sha": prepared_source.base_sha,
                            "pinned_sha": prepared_source.remote_sha,
                            "run_branch": prepared_source.run_branch,
                            "worktree": str(prepared_source.worktree_path),
                        }
                        if prepared_source is not None
                        else {"kind": "local"}
                    ),
                    "selection": autonome_auswahl,
                }
                reserviert, record = registry.reserve(
                    projektname, run_id, context=run_context,
                )
                if not reserviert:
                    return {
                        "gestartet": False,
                        "pid": record.get("pid") if record else None,
                        "run_id": record.get("run_id") if record else None,
                        "grund": "laeuft_bereits",
                    }
    
                if autonome_auswahl:
                    geschrieben = _audit_web_loop_event(
                        projektname, run_id, "web_op_selected", "selected",
                        {
                            "op_id": autonome_auswahl["id"],
                            "reason": autonome_auswahl["gruende"],
                            "priority": autonome_auswahl["prioritaet"],
                            "risk": autonome_auswahl["risiko"],
                            "project_goal_relevance": autonome_auswahl["projektziel_relevanz"],
                            "verification": autonome_auswahl["verifikation"],
                        },
                    )
                    if not geschrieben:
                        registry.set_state(projektname, run_id, "idle")
                        raise HTTPException(
                            status_code=500,
                            detail="Autonome Auswahl konnte nicht auditiert werden",
                        )
    
                # Log-File pro Run, stdout/stderr umleiten (sonst sind
                # Loop-Crashes unsichtbar). Handle bis zum Stop/Exit halten.
                _log_dir = _pd / ".werkstatt" / "logs"
                _log_fh = None
                try:
                    _log_dir.mkdir(parents=True, exist_ok=True)
                    _log_fh = (_log_dir / f"loop-{run_id}.log").open("ab")
                except OSError:
                    _log_fh = None
                try:
                    prozess = subprocess.Popen(
                        args,
                        stdout=_log_fh if _log_fh is not None else subprocess.DEVNULL,
                        stderr=subprocess.STDOUT,
                        start_new_session=(os.name == "posix"),
                    )
                except OSError as exc:
                    registry.set_state(projektname, run_id, "idle")
                    if _log_fh is not None:
                        _log_fh.close()
                    raise HTTPException(
                        status_code=500, detail=f"Loop konnte nicht starten: {exc}",
                    ) from exc
                try:
                    registry.register(projektname, run_id, prozess.pid)
                except (OSError, RuntimeError) as exc:
                    try:
                        if os.name == "posix":
                            os.killpg(prozess.pid, signal.SIGTERM)
                        else:
                            prozess.terminate()
                        prozess.wait(timeout=5)
                    except (OSError, ProcessLookupError, subprocess.TimeoutExpired):
                        pass
                    # Ein noch lebender Prozess muss seinen Worktree behalten.
                    if prozess.poll() is None:
                        launch_succeeded = True
                    registry.set_state(projektname, run_id, "idle")
                    if _log_fh is not None:
                        _log_fh.close()
                    raise HTTPException(
                        status_code=500,
                        detail=f"Loop-Registrierung fehlgeschlagen: {exc}",
                    ) from exc
                _LAUFENDE_LOOPS[projektname] = prozess
                _LOOP_RUN_IDS[projektname] = run_id
                if _log_fh is not None:
                    _LOOP_LOG_HANDLES[projektname] = _log_fh
                launch_succeeded = True
                return {
                    "gestartet": True,
                    "pid": prozess.pid,
                    "run_id": run_id,
                    "aufgabe": aufgabe,
                    "op_id": op_id or None,
                    "auswahl": autonome_auswahl,
                    "run_context": run_context,
                    "source": (
                        {
                            "repository": prepared_source.repository,
                            "branch": prepared_source.branch,
                            "base_sha": prepared_source.base_sha,
                            "pinned_sha": prepared_source.remote_sha,
                            "run_branch": prepared_source.run_branch,
                        }
                        if prepared_source is not None else None
                    ),
                }
    
    
        finally:
            if prepared_source is not None and not launch_succeeded:
                try:
                    _project_sources.remove_prepared_worktree(_pd, prepared_source)
                except _project_sources.GitHubSyncError:
                    import logging as _logging
                    _logging.getLogger(__name__).exception(
                        "Could not clean up failed GitHub run worktree for %s",
                        projektname,
                    )

    @app.get("/api/projects/{name}/loop")
    def project_loop_control(name: str) -> dict[str, Any]:
        """Liefert den Prozesszustand fuer die Projekt-Steuerung."""
        projektname = _pruefe_projektname(name)
        with _projekt_loop_lock(projektname):
            prozess = _loop_prozess(projektname)
            record = _loop_registry().read(projektname)
            if prozess is None:
                visible_state = (
                    record["state"]
                    if record and record["state"] in (
                        "starting", "pausing", "resuming", "stopping",
                    )
                    else "idle"
                )
                return {
                    "state": visible_state,
                    "pid": record.get("pid") if record and visible_state != "idle" else None,
                    "run_id": record.get("run_id") if record and visible_state != "idle" else None,
                    "run_context": (
                        record.get("context", {})
                        if record and visible_state != "idle" else None
                    ),
                }
            run_id = _LOOP_RUN_IDS.get(projektname)
            if (
                record is not None
                and record.get("run_id") == run_id
                and record["state"] in _LOOP_PROCESS_STATES
            ):
                state = record["state"]
            else:
                state = "paused" if projektname in _PAUSIERTE_LOOPS else "running"
            return {
                "state": state,
                "pid": prozess.pid,
                "run_id": run_id,
                "run_context": record.get("context", {}) if record else {},
            }

    def _audit_loop_control(
        projektname: str, prozess: Any, kind: str, status: str,
    ) -> bool:
        run_id = _LOOP_RUN_IDS.get(projektname)
        if not run_id:
            return False
        return _audit_web_loop_event(
            projektname, run_id, kind, status, {"pid": prozess.pid},
        )

    @app.post("/api/projects/{name}/pause")
    def project_pause(name: str) -> dict[str, Any]:
        """Pausiert den Loop-Prozess auf POSIX-Ebene."""
        projektname = _pruefe_projektname(name)
        if os.name != "posix":
            raise HTTPException(
                status_code=501, detail="Pause wird nur auf POSIX-Systemen unterstuetzt",
            )
        with _projekt_loop_lock(projektname):
            prozess = _loop_prozess(projektname)
            registry = _loop_registry()
            record = registry.read(projektname)
            if prozess is None:
                if record and record["state"] in ("pausing", "resuming", "stopping"):
                    raise HTTPException(
                        status_code=409,
                        detail=f"Loop-Kontrollaktion laeuft bereits: {record['state']}",
                    )
                raise HTTPException(status_code=404, detail="kein laufender Loop")
            run_id = _LOOP_RUN_IDS.get(projektname)
            if not record or record.get("run_id") != run_id:
                raise HTTPException(status_code=409, detail="Loop-Registry stimmt nicht mit Prozess ueberein")
            if record["state"] == "paused":
                return {"pausiert": True, "bereits_pausiert": True}
            if record["state"] != "running":
                raise HTTPException(
                    status_code=409,
                    detail=f"Loop kann gerade nicht pausiert werden: {record['state']}",
                )
            if not registry.transition(projektname, run_id, "running", "pausing"):
                raise HTTPException(status_code=409, detail="Loop-Zustand wurde parallel geaendert")
            try:
                os.killpg(prozess.pid, signal.SIGSTOP)
            except ProcessLookupError as exc:
                registry.transition(projektname, run_id, "pausing", "running")
                raise HTTPException(
                    status_code=409, detail="Loop wurde bereits beendet",
                ) from exc
            except OSError as exc:
                registry.transition(projektname, run_id, "pausing", "running")
                raise HTTPException(status_code=500, detail=f"Pause fehlgeschlagen: {exc}") from exc
            if not registry.transition(projektname, run_id, "pausing", "paused"):
                raise HTTPException(
                    status_code=409,
                    detail="Loop wurde pausiert, Registry-Zustand konnte nicht bestaetigt werden",
                )
            _PAUSIERTE_LOOPS.add(projektname)
            audit_ok = _audit_loop_control(
                projektname, prozess, "web_loop_paused", "paused",
            )
            return {"pausiert": True, "audit_event": audit_ok}

    @app.post("/api/projects/{name}/resume")
    def project_resume(name: str) -> dict[str, Any]:
        """Setzt einen pausierten POSIX-Loop fort."""
        projektname = _pruefe_projektname(name)
        if os.name != "posix":
            raise HTTPException(
                status_code=501, detail="Resume wird nur auf POSIX-Systemen unterstuetzt",
            )
        with _projekt_loop_lock(projektname):
            prozess = _loop_prozess(projektname)
            registry = _loop_registry()
            record = registry.read(projektname)
            if prozess is None:
                if record and record["state"] in ("pausing", "resuming", "stopping"):
                    raise HTTPException(
                        status_code=409,
                        detail=f"Loop-Kontrollaktion laeuft bereits: {record['state']}",
                    )
                raise HTTPException(status_code=404, detail="kein laufender Loop")
            run_id = _LOOP_RUN_IDS.get(projektname)
            if not record or record.get("run_id") != run_id:
                raise HTTPException(status_code=409, detail="Loop-Registry stimmt nicht mit Prozess ueberein")
            if record["state"] == "running":
                return {"fortgesetzt": True, "bereits_laufend": True}
            if record["state"] != "paused":
                raise HTTPException(
                    status_code=409,
                    detail=f"Loop kann gerade nicht fortgesetzt werden: {record['state']}",
                )
            if not registry.transition(projektname, run_id, "paused", "resuming"):
                raise HTTPException(status_code=409, detail="Loop-Zustand wurde parallel geaendert")
            try:
                os.killpg(prozess.pid, signal.SIGCONT)
            except ProcessLookupError as exc:
                registry.transition(projektname, run_id, "resuming", "paused")
                raise HTTPException(
                    status_code=409, detail="Loop wurde bereits beendet",
                ) from exc
            except OSError as exc:
                registry.transition(projektname, run_id, "resuming", "paused")
                raise HTTPException(
                    status_code=500, detail=f"Fortsetzen fehlgeschlagen: {exc}",
                ) from exc
            if not registry.transition(projektname, run_id, "resuming", "running"):
                raise HTTPException(
                    status_code=409,
                    detail="Loop wurde fortgesetzt, Registry-Zustand konnte nicht bestaetigt werden",
                )
            _PAUSIERTE_LOOPS.discard(projektname)
            audit_ok = _audit_loop_control(
                projektname, prozess, "web_loop_resumed", "running",
            )
            return {"fortgesetzt": True, "audit_event": audit_ok}

    @app.post("/api/projects/{name}/stop")
    def project_stop(name: str) -> dict[str, Any]:
        """Stoppt den Loop und seine Kindprozesse eines Projekts."""
        projektname = _pruefe_projektname(name)
        with _projekt_loop_lock(projektname):
            prozess = _loop_prozess(projektname)
            registry = _loop_registry()
            record = registry.read(projektname)
            if prozess is None:
                raise HTTPException(status_code=404, detail="kein laufender Loop")
            run_id = _LOOP_RUN_IDS.get(projektname, "")
            if not record or record.get("run_id") != run_id:
                raise HTTPException(status_code=409, detail="Loop-Registry stimmt nicht mit Prozess ueberein")
            state = record["state"]
            if state in ("pausing", "resuming"):
                raise HTTPException(
                    status_code=409,
                    detail=f"Loop-Kontrollaktion laeuft bereits: {state}",
                )
            if state not in ("running", "paused", "stopping"):
                raise HTTPException(
                    status_code=409,
                    detail=f"Loop kann gerade nicht gestoppt werden: {state}",
                )
            if not registry.claim_stop(projektname, run_id):
                raise HTTPException(
                    status_code=409,
                    detail="Loop-Kontrollaktion laeuft bereits oder Stop wird erneut versucht",
                )
            _PAUSIERTE_LOOPS.discard(projektname)
            if os.name == "posix":
                try:
                    # SIGCONT lets a process left paused by a prior stop
                    # receive SIGTERM. It is harmless for a running process.
                    os.killpg(prozess.pid, signal.SIGCONT)
                except ProcessLookupError:
                    pass
            try:
                if os.name == "posix":
                    os.killpg(prozess.pid, signal.SIGTERM)
                else:
                    prozess.terminate()
            except ProcessLookupError:
                pass
            try:
                returncode = prozess.wait(timeout=10)
            except subprocess.TimeoutExpired:
                if os.name == "posix":
                    try:
                        os.killpg(prozess.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                else:
                    prozess.kill()
                try:
                    returncode = prozess.wait(timeout=5)
                except subprocess.TimeoutExpired as exc:
                    raise HTTPException(
                        status_code=504, detail="Loop reagiert nicht auf Stop",
                    ) from exc
            audit_ok = False
            if run_id:
                try:
                    audit_ok = _audit_web_loop_event(
                        projektname, run_id, "web_loop_stopped", "stopped",
                        {"pid": prozess.pid},
                    )
                except (OSError, RuntimeError, sqlite3.Error, ValueError):
                    audit_ok = False
            registry.transition(projektname, run_id, "stopping", "idle")
            _LAUFENDE_LOOPS.pop(projektname, None)
            _LOOP_RUN_IDS.pop(projektname, None)
            _log_fh = _LOOP_LOG_HANDLES.pop(projektname, None)
            if _log_fh is not None:
                try:
                    _log_fh.close()
                except OSError:
                    pass
            return {
                "gestoppt": True, "returncode": returncode,
                "audit_event": audit_ok,
            }

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
        """Phasen-Knoten aus Event-Store + JSONL-Audit.

        OP-381h: zusaetzlich ``aktiv`` — welche Rolle arbeitet JETZT?
        Leer wenn nichts laeuft oder letztes Event > 300s alt (stale).
        """
        from werkstatt.web import inspector as _insp
        projekt = _pruefe_projektname(name)
        knoten = _insp.aggregate_timeline(projekt, run_id=run_id)
        st = _insp.aggregate_status(projekt)
        aktiv = _insp.aggregate_timeline_aktiv(projekt, run_id=run_id)
        return {
            "run_id": run_id or st.get("run_id"),
            "knoten": knoten,
            "aktiv": aktiv,
        }

    @app.get("/api/projects/{name}/swimlane")
    def project_swimlane(name: str, run_id: str | None = None) -> dict[str, Any]:
        """OP-381i: Swimlane-Wasserfall-Daten (Rollen-Lanes + Zeit-Balken)."""
        from werkstatt.web import inspector as _insp
        projekt = _pruefe_projektname(name)
        return _insp.aggregate_swimlane(projekt, run_id=run_id)

    @app.get("/api/projects/{name}/live-feed")
    def project_live_feed(
        name: str, run_id: str | None = None, limit: int = 30,
    ) -> dict[str, Any]:
        """OP-381j: Live-Feed fuer Control-Modus (vertikale Chronologie)."""
        from werkstatt.web import inspector as _insp
        projekt = _pruefe_projektname(name)
        if limit < 1 or limit > 200:
            raise HTTPException(status_code=400, detail="limit 1-200")
        return _insp.aggregate_live_feed(projekt, run_id=run_id, limit=limit)

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
        """Listet letzte Chats mit Vorschautitel und letzter Aktivitaet."""
        from werkstatt import chat_session as _cs
        projekt = _pruefe_projektname(name)
        details = _cs.list_session_summaries(projekt, limit=50)
        sessions = [item["session_id"] for item in details]
        return {"sessions": sessions, "summaries": details}

    @app.get("/api/projects/{name}/chat/history")
    def chat_history(name: str, session_id: str) -> dict[str, Any]:
        """Liefert die Event-Historie einer Session."""
        from werkstatt import chat_session as _cs
        from werkstatt.chat_jobs import sync_completed_job_turns

        projekt = _pruefe_projektname(name)
        sid = _pruefe_session_id(session_id)
        db_path = _PROJECTS_BASE / ".werkstatt" / "chat-jobs" / f"{projekt}.db"
        sync_completed_job_turns(projekt, sid, db_path=db_path)
        return {"events": _cs.ChatSession(projekt, sid).load()}

    @app.post("/api/projects/{name}/chat/jobs", status_code=202)
    def chat_job_create(name: str, body: dict[str, Any]) -> dict[str, Any]:
        """Persistiert Chat-Arbeit und kehrt sofort mit einer Job-ID zurueck."""
        from werkstatt.chat_jobs import (
            IdempotencyConflict,
            enqueue_chat_job,
            sync_completed_job_turns,
        )
        from werkstatt.chat_session import ChatSession

        projekt = _pruefe_projektname(name)
        session_id = body.get("session_id")
        message = body.get("message")
        mode = body.get("mode", "read")
        idempotency_key = body.get("idempotency_key")
        if not isinstance(session_id, str) or not session_id:
            raise HTTPException(status_code=400, detail="session_id fehlt")
        sid = _pruefe_session_id(session_id)
        if not isinstance(message, str) or not message.strip():
            raise HTTPException(status_code=400, detail="message fehlt")
        if len(message) > 20000:
            raise HTTPException(status_code=413, detail="message zu lang")
        if mode not in ("read", "debugger"):
            raise HTTPException(
                status_code=400,
                detail="Hintergrundjobs erlauben nur read- oder debugger-Modus",
            )
        if not isinstance(idempotency_key, str) or not re.fullmatch(
            r"[A-Za-z0-9_.:-]{8,128}", idempotency_key,
        ):
            raise HTTPException(status_code=400, detail="idempotency_key ungueltig")
        db_path = _PROJECTS_BASE / ".werkstatt" / "chat-jobs" / f"{projekt}.db"
        try:
            sync_completed_job_turns(projekt, sid, db_path=db_path)
            context_seq = ChatSession(projekt, sid).max_seq()
            loop_record = _loop_registry().read(projekt)
            run_id = (
                str(loop_record["run_id"])
                if loop_record is not None
                and loop_record["state"] in ("starting", "running", "paused")
                else None
            )
            accepted = enqueue_chat_job(
                projekt,
                (_PROJECTS_BASE / projekt).resolve(),
                sid,
                message.strip(),
                mode,
                idempotency_key,
                db_path=db_path,
                context_seq=context_seq,
                run_id=run_id,
            )
        except IdempotencyConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except (OSError, RuntimeError, sqlite3.Error, ValueError) as exc:
            raise HTTPException(
                status_code=500, detail=f"Chat-Job konnte nicht gestartet werden: {exc}",
            ) from exc
        job = accepted["job"]
        return {
            "job_id": job["job_id"],
            "state": job["state"],
            "created": accepted["created"],
            "run_id": job.get("run_id"),
        }

    @app.get("/api/projects/{name}/chat/jobs")
    def chat_jobs_active(name: str, session_id: str) -> dict[str, Any]:
        """Liefert aktive und letzte fehlgeschlagene Jobs fuer Reconnect."""
        from werkstatt.chat_jobs import (
            ChatJobStore,
            resume_chat_jobs,
            sync_completed_job_turns,
        )

        projekt = _pruefe_projektname(name)
        sid = _pruefe_session_id(session_id)
        db_path = _PROJECTS_BASE / ".werkstatt" / "chat-jobs" / f"{projekt}.db"
        try:
            resume_chat_jobs(
                projekt, (_PROJECTS_BASE / projekt).resolve(), db_path=db_path,
            )
            sync_completed_job_turns(projekt, sid, db_path=db_path)
            jobs = ChatJobStore(db_path).reconnect_for_session(sid)
        except (OSError, RuntimeError, sqlite3.Error, ValueError) as exc:
            raise HTTPException(
                status_code=500, detail=f"Chat-Jobs konnten nicht geladen werden: {exc}",
            ) from exc
        return {
            "jobs": [
                {"job_id": job["job_id"], "message": job["message"],
                 "state": job["state"], "error": job["error"],
                 "created_at": job["created_at"], "run_id": job["run_id"]}
                for job in jobs
            ],
        }

    @app.post("/api/projects/{name}/chat/jobs/{job_id}/cancel")
    def chat_job_cancel(
        name: str, job_id: str, body: dict[str, Any],
    ) -> dict[str, Any]:
        """Bricht einen wartenden Job ab oder fordert Worker-Abbruch an."""
        from werkstatt.chat_jobs import ChatJobStore, resume_chat_jobs

        projekt = _pruefe_projektname(name)
        if not re.fullmatch(r"[a-f0-9]{32}", job_id):
            raise HTTPException(status_code=400, detail="job_id ungueltig")
        session_id = body.get("session_id")
        if not isinstance(session_id, str) or not session_id:
            raise HTTPException(status_code=400, detail="session_id fehlt")
        sid = _pruefe_session_id(session_id)
        db_path = _PROJECTS_BASE / ".werkstatt" / "chat-jobs" / f"{projekt}.db"
        try:
            store = ChatJobStore(db_path)
            result = store.request_cancel(job_id, sid)
            if result is None:
                raise HTTPException(status_code=404, detail="Chat-Job nicht gefunden")
            resume_chat_jobs(
                projekt, (_PROJECTS_BASE / projekt).resolve(), db_path=db_path,
            )
        except HTTPException:
            raise
        except (OSError, RuntimeError, sqlite3.Error, ValueError) as exc:
            raise HTTPException(
                status_code=500, detail=f"Chat-Job konnte nicht abgebrochen werden: {exc}",
            ) from exc
        return result

    @app.get("/api/projects/{name}/chat/jobs/{job_id}")
    def chat_job_get(
        name: str, job_id: str, session_id: str, since_seq: int = 0,
    ) -> dict[str, Any]:
        """Liefert Jobstatus und Events nur fuer die zugehoerige Session."""
        from werkstatt.chat_jobs import ChatJobStore, resume_chat_jobs

        projekt = _pruefe_projektname(name)
        if not re.fullmatch(r"[a-f0-9]{32}", job_id):
            raise HTTPException(status_code=400, detail="job_id ungueltig")
        sid = _pruefe_session_id(session_id)
        if since_seq < 0:
            raise HTTPException(status_code=400, detail="since_seq ungueltig")
        db_path = _PROJECTS_BASE / ".werkstatt" / "chat-jobs" / f"{projekt}.db"
        try:
            store = ChatJobStore(db_path)
            job = store.get(job_id, since_seq=since_seq)
            if job is None or job["session_id"] != sid:
                raise HTTPException(status_code=404, detail="Chat-Job nicht gefunden")
            resume_chat_jobs(
                projekt, (_PROJECTS_BASE / projekt).resolve(), db_path=db_path,
            )
            job = store.get(job_id, since_seq=since_seq)
        except HTTPException:
            raise
        except (OSError, RuntimeError, sqlite3.Error, ValueError) as exc:
            raise HTTPException(
                status_code=500, detail=f"Chat-Job konnte nicht geladen werden: {exc}",
            ) from exc
        if job is None or job["session_id"] != sid:
            raise HTTPException(status_code=404, detail="Chat-Job nicht gefunden")
        return job

    @app.post("/api/projects/{name}/chat/actions/{proposal_id}")
    def chat_loop_action(name: str, proposal_id: str, body: dict[str, Any]) -> dict[str, Any]:
        """Bestaetigt oder verwirft genau einen sessiongebundenen Vorschlag."""
        from werkstatt.chat_session import ChatSession

        projekt = _pruefe_projektname(name)
        session_id = body.get("session_id")
        decision = body.get("decision")
        if not isinstance(session_id, str) or not session_id:
            raise HTTPException(status_code=400, detail="session_id fehlt")
        sid = _pruefe_session_id(session_id)
        if not re.fullmatch(r"[a-f0-9]{32}", proposal_id):
            raise HTTPException(status_code=400, detail="proposal_id ungueltig")
        if decision not in {"confirm", "reject"}:
            raise HTTPException(status_code=400, detail="decision muss confirm oder reject sein")
        session = ChatSession(projekt, sid)
        try:
            claimed = session.resolve_loop_action(proposal_id, decision)
        except (OSError, sqlite3.Error, ValueError) as exc:
            raise HTTPException(status_code=500, detail=f"Vorschlag konnte nicht aufgeloest werden: {exc}") from exc
        if claimed is None:
            raise HTTPException(status_code=404, detail="Vorschlag nicht gefunden")
        proposal, state, prior_result = claimed
        if state != "claimed":
            return {"proposal_id": proposal_id, "state": state, "result": prior_result}
        try:
            action = proposal.get("action")
            arguments = proposal.get("arguments") or {}
            if proposal.get("project") != projekt:
                raise HTTPException(status_code=404, detail="Vorschlag gehoert zu anderem Projekt")
            if action == "start":
                debugger_payload = arguments.get("debugger_fix")
                if debugger_payload is not None:
                    from werkstatt.debugger_handoff import (
                        DebuggerFixError,
                        debugger_fix_loop_task,
                        parse_debugger_fix,
                        validate_debugger_fix_checkout,
                    )
                    try:
                        fix = parse_debugger_fix(debugger_payload)
                    except (DebuggerFixError, TypeError) as exc:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Debugger-Freigabe ungueltig: {exc}",
                        ) from exc
                    if fix.project != projekt:
                        raise HTTPException(
                            status_code=404,
                            detail="Debugger-Fix gehoert zu anderem Projekt",
                        )
                    ok, detail = validate_debugger_fix_checkout(
                        fix,
                        _PROJECTS_BASE / projekt,
                        expected_project=projekt,
                    )
                    if not ok:
                        raise HTTPException(status_code=409, detail=detail)
                    arguments = {"aufgabe": debugger_fix_loop_task(fix)}
                result = project_start(projekt, arguments)
                if (
                    result.get("gestartet") is False
                    and result.get("grund") == "laeuft_bereits"
                ):
                    error = (
                        "Loop laeuft bereits; Auftrag wurde nicht gestartet "
                        "oder eingereiht."
                    )
                    session.append("loop_action_not_started", {
                        "proposal_id": proposal_id,
                        "error": error,
                        "result": result,
                    })
                    return {
                        "proposal_id": proposal_id,
                        "state": "not_started",
                        "detail": error,
                        "result": result,
                    }
            elif action == "pause":
                result = project_pause(projekt)
            elif action == "resume":
                result = project_resume(projekt)
            elif action == "stop":
                result = project_stop(projekt)
            else:
                raise HTTPException(status_code=400, detail="unbekannte Loop-Aktion")
            session.append("loop_action_completed", {"proposal_id": proposal_id, "result": result})
            return {"proposal_id": proposal_id, "state": "completed", "result": result}
        except HTTPException as exc:
            detail = exc.detail
            session.append("loop_action_failed", {"proposal_id": proposal_id, "error": str(detail)})
            raise
        except Exception as exc:
            session.append("loop_action_failed", {"proposal_id": proposal_id, "error": f"{type(exc).__name__}: {exc}"})
            raise HTTPException(status_code=500, detail=f"Loop-Aktion fehlgeschlagen: {exc}") from exc

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
        if mode not in ("read", "write", "debugger"):
            raise HTTPException(status_code=400, detail="mode ungueltig")
        sid = _pruefe_session_id(session_id)
        session = _cs.ChatSession(projekt, sid)
        try:
            projekt_dir = (_PROJECTS_BASE / projekt).resolve()
            antwort = _ca.chat_loop(
                session, message, mode=mode, project_dir=projekt_dir,
            )
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
                        project_dir=(_PROJECTS_BASE / projekt).resolve(),
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
