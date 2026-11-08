"""Emit-Pfad: stdout, Publish an Event-Emitter (OP-138 Phase 2b)."""
from __future__ import annotations

import contextvars
import sys
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from . import rich as _rich
from . import tee as _tee_mod

_PROGRESS_OPEN: bool = False


def _emit_raw(text: str) -> None:
    """Direkter stdout-Schreibpfad. CI: mit Zeitstempel. Sonst: plain.

    Bugfix 2026-11-03: vorher wurde _tee doppelt gerufen (einmal
    mit Timestamp, einmal clean) -> jede Zeile 2x im Log.
    Jetzt: stdout bekommt Timestamp (CI), _tee bekommt nur clean.
    """
    global _PROGRESS_OPEN
    if _PROGRESS_OPEN:
        try:
            sys.stdout.write("\n")
            sys.stdout.flush()
        except (OSError, ValueError):
            pass
        _PROGRESS_OPEN = False
    if _rich.IS_CI:
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {text}", flush=True)
    else:
        print(text, flush=True)
    _tee_mod._tee(text)


_PROJECT_CTX: contextvars.ContextVar[str] = contextvars.ContextVar(
    "werkstatt_project", default="default"
)


def get_project() -> str:
    """Projekt des aktuellen Threads/Contexts (Fallback: 'default')."""
    return _PROJECT_CTX.get()


def set_project(project: str) -> None:
    """Setzt das Projekt fuer den aktuellen Thread/Context."""
    if not project:
        project = "default"
    _PROJECT_CTX.set(project)


def _get_project() -> str:
    """Projektname aus dem aktuellen Context (Fallback: 'default')."""
    return get_project()


class TerminalEmitter:
    """Pro-Projekt-Event-Emitter mit Callback-Registry."""

    def __init__(self, project: str) -> None:
        self.project = project
        self._callbacks: list[Callable[[dict[str, Any]], None]] = []
        self._lock = threading.Lock()

    def emit(self, event: dict[str, Any]) -> None:
        event.setdefault("project", self.project)
        event.setdefault(
            "ts", datetime.now(UTC).isoformat(timespec="seconds")
        )
        with self._lock:
            callbacks = list(self._callbacks)
        for cb in callbacks:
            try:
                cb(event)
            except Exception:
                # Ein kaputter Client darf andere Clients nicht blockieren.
                pass

    def subscribe(
        self, callback: Callable[[dict[str, Any]], None]
    ) -> Callable[[], None]:
        with self._lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)

        def _unsub() -> None:
            self.unsubscribe(callback)

        return _unsub

    def unsubscribe(self, callback: Callable[[dict[str, Any]], None]) -> None:
        with self._lock:
            try:
                self._callbacks.remove(callback)
            except ValueError:
                pass

    def subscriber_count(self) -> int:
        with self._lock:
            return len(self._callbacks)


_EMITTERS: dict[str, TerminalEmitter] = {}


_EMITTERS_LOCK = threading.Lock()


def get_emitter(project: str | None = None) -> TerminalEmitter:
    """Liefert die pro-Projekt-Singleton-Instanz (thread-safe)."""
    name = project if project is not None else get_project()
    with _EMITTERS_LOCK:
        emitter = _EMITTERS.get(name)
        if emitter is None:
            emitter = TerminalEmitter(name)
            _EMITTERS[name] = emitter
        return emitter


def _get_emitter() -> TerminalEmitter | None:
    """Liefert den Emitter fuer das aktuelle Projekt, ohne einen neuen
    anzulegen. Wird von _publish aufgerufen — fehlender Emitter ist
    ein normaler Fall (kein Projekt-Kontext), kein Fehler.
    """
    project = _get_project()
    if not project or project == "default":
        return None
    return _EMITTERS.get(project)


def _publish(event_type: str, text: str, **extra: object) -> None:
    """Event an JSONL (autoritativ) + SQLite (Uebergang) + Emitter.

    OP-321: JSONL ist ab jetzt autoritativ (audit/stream). SQLite wird
    in OP-323 entfernt, sobald der Projektor (OP-322) die DB aus JSONL
    fuellt. Emitter bleibt unveraendert (WebSocket-Live-Kanal).

    Ein fehlender Emitter oder defekter Subscriber darf den Loop nie
    abbrechen.
    """
    from pathlib import Path as _Path

    from werkstatt.audit import _STREAM_KINDS, audit, get_run_id, stream

    # 1. JSONL (autoritativ, neu)
    project_name = _get_project() or "?"
    payload_j = {"text": text, **extra}
    try:
        if event_type in _STREAM_KINDS:
            stream(event_type, payload_j, _Path("."), project_name)
        else:
            audit(event_type, payload_j, _Path("."), project_name)
    except Exception:
        pass

    # 2. SQLite (Uebergangsphase, OP-323 entfernt das)
    try:
        from werkstatt.event_store import EventStore
        run_id = get_run_id()
        if run_id:
            phase = extra.get("phase")
            if not isinstance(phase, str):
                phase = None
            status = extra.get("status")
            if not isinstance(status, str):
                status = None
            EventStore().append(
                run_id=run_id,
                kind=event_type,
                phase=phase,
                status=status,
                payload={"text": text, **extra},
            )
    except Exception:
        pass

    # 3. Emitter (unveraendert)
    emitter = _get_emitter()
    if emitter is None:
        return
    event: dict[str, object] = {
        "type": event_type,
        "project": _get_project(),
        "text": text,
        "ts": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    event.update(extra)
    try:
        emitter.emit(event)
    except (RuntimeError, OSError, ValueError) as fehler:
        # Subscriber-Fehler sind selten und duerfen den Loop nicht
        # abbrechen. Wir protokollieren sie auf stderr, aber nicht
        # ueber den Emitter (sonst Endlos-Rekursion).
        import sys as _sys
        _sys.stderr.write(f"publish-fehler: {fehler!r}\n")


def _emit(text: str) -> None:
    """Zentraler Output. CI: mit Zeitstempel. Sonst: plain."""
    _emit_raw(text)
    _publish("log_line", text)


def _progress_write(line: str) -> None:
    """Live-Progress: ueberschreibt die Zeile (\r + clear-line)."""
    global _PROGRESS_OPEN
    try:
        sys.stdout.write("\r\x1b[K" + line)
        sys.stdout.flush()
        _PROGRESS_OPEN = True
    except (OSError, ValueError):
        pass
    _tee_mod._tee(line)
