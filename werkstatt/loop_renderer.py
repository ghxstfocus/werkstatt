"""Loop-Renderer — drei Modi (ci/pretty/live).

Modi:
  ci     (Default, kein TTY, oder WERKSTATT_RENDER=ci):
         Plain line-by-line mit Zeitstempel. RERUN-kompatibel.
  pretty (WERKSTATT_RENDER=pretty, kein TTY, oder WERKSTATT_RENDER=pretty):
         rich-Boxen, Farben, aber kein Live-Update. Fuer Logs/Screenshots.
  live   (TTY, oder WERKSTATT_RENDER=live):
         rich.Live + Spinner. Voller Effekt: blinkt, aktualisiert sich.

Default: ci — damit RERUN-Logs und Tests unveraendert bleiben.

API:
  Alt (stabil, in loop.py benutzt):
    header, step, task, task_ok, task_failed, footer,
    group_start, group_end, heartbeat, plan
  Neu (live/pretty):
    spinner_start, spinner_update, spinner_stop,
    panel_plan, panel_diff
"""
from __future__ import annotations
import re

import contextvars
import os
import sys
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

# === Modus-Wahl ===
_render_mode_raw = os.environ.get("WERKSTATT_RENDER", "").lower()
_is_tty = sys.stdout.isatty()
_in_test = os.environ.get("WERKSTATT_IN_TEST") == "1"

if _in_test or _render_mode_raw == "ci":
    RENDER_MODE = "ci"
elif _render_mode_raw == "live":
    RENDER_MODE = "live"
elif _render_mode_raw == "pretty":
    RENDER_MODE = "pretty"
elif _is_tty:
    RENDER_MODE = "live"
else:
    RENDER_MODE = "ci"


# Tee-Stream fuer Live-Log-Mitschnitt (Terminal-Panel im Browser).
# Set durch loop.main(), schreibt alle Render-Zeilen in eine Datei.
_TEE_STREAM: TextIO | None = None
_TEE_LOCK = threading.Lock()
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def set_tee_stream(stream: TextIO | None) -> None:
    """Setzt/loescht das Tee-Ziel. Schreibt jede Render-Zeile dort hin."""
    global _TEE_STREAM
    with _TEE_LOCK:
        _TEE_STREAM = stream


def _tee(text: str) -> None:
    """Schreibt text (ANSI-frei, GH-Actions-Prefixe entfernt) in Tee-Stream."""
    if _TEE_STREAM is None:
        return
    try:
        clean = _ANSI_RE.sub("", text)
        # Bugfix 2026-11-03: ::log::/::group::/::endgroup:: sind
        # GH-Actions-Syntax, nicht user-facing. Aus dem Logfile
        # entfernen, sonst liest es sich wie Maschinencode.
        if clean.startswith("::log::"):
            clean = clean[len("::log::"):].lstrip()
        elif clean.startswith("::group::") or clean.startswith("::endgroup::"):
            return
        if not clean:
            return
        with _TEE_LOCK:
            _TEE_STREAM.write(clean + "\n")
            _TEE_STREAM.flush()
    except (OSError, ValueError):
        pass

IS_CI = RENDER_MODE == "ci"
IS_LIVE = RENDER_MODE == "live"

# === rich-Import (optional) ===
try:
    from rich.console import Console as _RichConsole  # type: ignore[import-not-found]
    from rich.live import Live as _RichLive  # type: ignore[import-not-found]
    from rich.panel import Panel as _RichPanel  # type: ignore[import-not-found]
    from rich.progress import (  # type: ignore[import-not-found]
        BarColumn,
        SpinnerColumn,
        TaskProgressColumn,
        TextColumn,
    )
    from rich.progress import (
        Progress as _RichProgress,
    )
    from rich.spinner import Spinner as _RichSpinner  # type: ignore[import-not-found]
    from rich.syntax import Syntax as _RichSyntax  # type: ignore[import-not-found]
    _HAS_RICH = True
except ImportError:
    _HAS_RICH = False

# OP-111-Vorbereitung: Rich-Console-Wrapper, der stdout UND tee bedient.
# Problem: _console.print() schrieb bisher nur an sys.stdout — der
# Loop-Footer (LOOP FEHLGESCHLAGEN) landete nicht im Render-Log.
class _TeeWriter:
    """File-Wrapper: schreibt an stdout + ruft _tee pro Zeile."""
    def __init__(self, base):
        self._base = base
    def write(self, text):
        n = self._base.write(text)
        for line in text.split("\n"):
            line = line.rstrip()
            if line:
                _tee(line)
        return n
    def flush(self):
        return self._base.flush()
    def isatty(self):
        return self._base.isatty()
    def fileno(self):
        return self._base.fileno()

# rich nur im pretty/live-Modus aktiv
_use_rich = _HAS_RICH and RENDER_MODE in ("pretty", "live")
if _use_rich:
    import sys as _sys
    _console: _RichConsole = _RichConsole(
        file=_TeeWriter(_sys.stdout),
        force_terminal=(RENDER_MODE == "live"), width=100,
    )
else:
    # Dummy-Console, die ins Nichts schreibt. Spart None-Checks an
    # allen .print()-Aufrufen.
    _console = _RichConsole(quiet=True)


# === Farben (ANSI, nur bei TTY oder live/pretty) ===
USE_COLOR = (_is_tty or RENDER_MODE in ("pretty", "live")) and not IS_CI


def _c(code: str, text: str) -> str:
    if not USE_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"


def _green(t: str) -> str: return _c("32", t)
def _yellow(t: str) -> str: return _c("33", t)
def _red(t: str) -> str: return _c("31", t)
def _cyan(t: str) -> str: return _c("36", t)
def _bold(t: str) -> str: return _c("1", t)
def _dim(t: str) -> str: return _c("2", t)


def _emit_raw(text: str) -> None:
    """Direkter stdout-Schreibpfad. CI: mit Zeitstempel. Sonst: plain.

    Bugfix 2026-11-03: vorher wurde _tee doppelt gerufen (einmal
    mit Timestamp, einmal clean) -> jede Zeile 2x im Log.
    Jetzt: stdout bekommt Timestamp (CI), _tee bekommt nur clean.
    """
    if IS_CI:
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {text}", flush=True)
    else:
        print(text, flush=True)
    _tee(text)
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
            except Exception:  # noqa: BLE001, S110
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
    """Sendet ein strukturiertes Event an den Emitter.

    Ein fehlender Emitter (kein Projekt-Kontext) oder ein defekter
    Subscriber darf den Loop nie abbrechen.
    """
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


# ============================================================
# Live-Spinner (nur RENDER_MODE=live)
# ============================================================

_live: _RichLive | None = None
_spinner_text = ""
_live_lock = threading.Lock()


def spinner_start(label: str, detail: str = "") -> None:
    """Startet einen Live-Spinner (nur RENDER_MODE=live).

    In ci/pretty: No-Op. In live: Live-Bereich mit Spinner + Text.
    """
    global _live, _spinner_text
    _publish("spinner", label, state="start", label=label, detail=detail)
    if not IS_LIVE or not _HAS_RICH:
        # Fallback: Heartbeat-Zeile
        _emit(f"  · {label} ... {detail}" if detail else f"  · {label} ...")
        return

    with _live_lock:
        # M-377: idempotent — wenn schon aktiv, nur updaten.
        if _live is not None:
            _spinner_text = f"{label}" + (f" · {detail}" if detail else "")
            _live.update(_RichSpinner("dots", text=_spinner_text, style="cyan"))
            return
        _spinner_text = f"{label}" + (f" · {detail}" if detail else "")
        _spinner = _RichSpinner("dots", text=_spinner_text, style="cyan")
        _live = _RichLive(_spinner, console=_console, refresh_per_second=10, transient=True)
        try:
            _live.start()
        except Exception:  # noqa: BLE001
            # Falls rich trotzdem crasht: Live deaktivieren, kein Loop-Abbruch.
            _live = None


def spinner_update(label: str, detail: str = "") -> None:
    """Aktualisiert den Live-Spinner (nur RENDER_MODE=live)."""
    global _spinner_text
    _publish("spinner", label, state="update", label=label, detail=detail)
    if not IS_LIVE or not _HAS_RICH or _live is None:
        return
    with _live_lock:
        _spinner_text = f"{label}" + (f" · {detail}" if detail else "")
        _live.update(_RichSpinner("dots", text=_spinner_text, style="cyan"))


def spinner_stop(final_label: str = "") -> None:
    """Beendet den Live-Spinner (nur RENDER_MODE=live)."""
    global _live
    if not IS_LIVE or not _HAS_RICH or _live is None:
        return
    with _live_lock:
        if _live is not None:
            try:
                _live.stop()
            except Exception:  # noqa: BLE001, S110
                # Live-Objekt ist bereits gestoppt oder ungueltig.
                pass
        _live = None


# ============================================================
# Alte API (stabil)
# ============================================================

def group_start(name: str) -> None:
    """Phasen-Header."""
    if IS_CI:
        print(f"::group::{name}")
    elif _use_rich:
        _console.rule(f"[bold cyan]{name}[/]")
    else:
        _emit(f"--- {name} ---")


def group_end() -> None:
    if IS_CI:
        print("::endgroup::")


_LAST_HEARTBEAT: dict[str, int] = {}


def heartbeat(label: str, elapsed_s: int) -> None:
    """Lebenszeichen fuer langlaufende Calls.

    Fix BA 2026-10-31: Fallback auf log_line, wenn kein Spinner
    aktiv ist. Sonst landet der Heartbeat waehrend pytest_changed
    (30+ s) im leeren Spinner (spinner_update ist No-Op ohne
    laufenden Spinner) -- Live-Beleg 2026-10-31 13:04:
    verify_failed nach 30 s Stille.
    Throttle: max. alle 5 s dieselbe Zeile.
    """
    if IS_LIVE and _live is not None:
        spinner_update(label, f"{elapsed_s}s")
        return
    _last = _LAST_HEARTBEAT.get(label, -999)
    # Bugfix 2026-11-03: In CI erst ab 30s und dann alle 15s
    # (vorher 5s -> Log-Spam bei pytest_changed). In non-CI
    # 5s-Throttle. _publish nur wenn tatsaechlich ausgegeben.
    if IS_CI:
        if elapsed_s < 30 or elapsed_s - _last < 15:
            return
    else:
        if elapsed_s - _last < 5:
            return
    _LAST_HEARTBEAT[label] = elapsed_s
    _emit(f"  · {label} ({elapsed_s}s)")
    _publish("heartbeat", label, label=label, elapsed_s=elapsed_s)


TOTAL_PHASES = 5


def header(title: str) -> None:
    """Zeigt den Loop-Header (einmal pro Lauf)."""
    _emit("")
    if _use_rich:
        _console.print(_RichPanel(
            f"[bold]Werkstatt Loop[/] — {title}",
            title="[cyan]Loop[/]",
            border_style="cyan",
        ))
    else:
        _emit(_bold("═" * 60))
        _emit(_bold(f"  WERKSTATT LOOP — {title}"))
        _emit(_bold("═" * 60))
    _emit("")


def step(
    phase_nr: int,
    name: str,
    detail: str = "",
    ok: bool = True,
    elapsed_s: float | None = None,
) -> None:
    """Zeigt einen Loop-Schritt."""
    marker = _green("✓") if ok else _red("✗")
    label = f"[{phase_nr}/{TOTAL_PHASES}]"
    name_padded = name.ljust(14)
    timing = f" ({elapsed_s:.1f}s)" if elapsed_s is not None else ""
    if detail:
        _emit(f"  {_dim(label)} {marker} {_bold(name_padded)} {_dim('...')} {detail}{timing}")
    else:
        _emit(f"  {_dim(label)} {marker} {_bold(name_padded)}{timing}")


def task(nr: int, total: int, name: str) -> None:
    """Startet einen Task."""
    label = f"[{nr}/{total}]"
    if IS_LIVE and _HAS_RICH:
        spinner_start(f"Task {nr}/{total}", name[:50])
    else:
        _emit_raw(f"  {_dim(label)} {_cyan('→')} {name}")
    _publish("task_started", f"Task {nr}/{total}: {name}", nr=nr, total=total, name=name)


def task_ok(nr: int, total: int, elapsed_s: float | None = None) -> None:
    label = f"[{nr}/{total}]"
    timing = f" ({elapsed_s:.1f}s)" if elapsed_s is not None else ""
    if IS_LIVE and _HAS_RICH:
        spinner_stop()
    _emit_raw(f"  {_dim(label)} {_green('✓')} task ok{timing}")
    _publish("task_done", f"Task {nr}/{total}: ok{timing}", nr=nr, total=total, ok=True, elapsed_s=elapsed_s)


def task_failed(nr: int, total: int, reason: str = "") -> None:
    label = f"[{nr}/{total}]"
    extra = f" — {reason}" if reason else ""
    if IS_LIVE and _HAS_RICH:
        spinner_stop()
    _emit_raw(f"  {_dim(label)} {_red('✗')} task failed{extra}")
    _publish("task_done", f"Task {nr}/{total}: failed{extra}", nr=nr, total=total, ok=False, reason=reason)


def hook(name: str, ok: bool, reason: str = "") -> None:
    """Zeigt einen Hook-Aufruf."""
    marker = _green("✓") if ok else _yellow("!")
    extra = f" — {reason}" if reason and not ok else ""
    _emit(f"           {marker} hook: {name}{extra}")


def patch(file: str, action: str = "create") -> None:
    """Zeigt einen angewendeten Patch."""
    icon = "＋" if action == "create" else "✎"
    _emit(f"           {icon} {file}")


def footer(success: bool, tasks_total: int, tasks_ok: int) -> None:
    """Zeigt den Loop-Abschluss."""
    _emit("")
    if _use_rich:
        style = "green" if success else "red"
        text = "✓ LOOP ERFOLGREICH" if success else "✗ LOOP FEHLGESCHLAGEN"
        _console.print(_RichPanel(
            f"[bold {style}]{text}[/]\n"
            f"  Tasks: {tasks_ok}/{tasks_total}",
            border_style=style,
        ))
    else:
        _emit(_bold("═" * 60))
        if success:
            _emit(_green(_bold("  ✓ LOOP ERFOLGREICH")))
        else:
            _emit(_red(_bold("  ✗ LOOP FEHLGESCHLAGEN")))
        _emit(f"  Tasks: {tasks_ok}/{tasks_total}")
        _emit(_bold("═" * 60))
    _emit("")
    _publish("summary", "", success=success, tasks_total=tasks_total, tasks_ok=tasks_ok)


# ============================================================
# Neue API: Panels
# ============================================================

def panel_plan(phasen, tasks, tests, akzeptanzkriterien) -> None:
    """Zeigt den Plan (Box in pretty/live, Plain in ci)."""
    if _use_rich:
        _render_plan_rich(phasen, tasks, tests, akzeptanzkriterien)
    else:
        _render_plan_plain(phasen, tasks, tests, akzeptanzkriterien)


def _emit_wrapped(text: str, width: int = 88, indent: str = "       ") -> None:
    """Bugfix 2026-11-03: Text auf width umbrechen, jede Zeile indent."""
    import textwrap as _tw
    if not text:
        return
    for line in _tw.wrap(text, width=width):
        _emit(f"{indent}{line}")


def _render_plan_plain(phasen, tasks, tests, akzeptanzkriterien) -> None:
    _emit("")
    _emit("=" * 62)
    _emit(f"  PLAN — {len(phasen)} Phasen, {len(tasks)} Tasks")
    _emit("=" * 62)
    for _p in phasen:
        _emit(f"Phase {_p.get('id', '?')}: {_p.get('titel', '')}")
        for _t in tasks:
            if isinstance(_t, dict) and _t.get("phase_id") == _p.get("id"):
                _files = ", ".join(_t.get("task_files", [])) or "(keine)"
                _emit(f"  {_t.get('id')} [{_t.get('action', '?')}] {_t.get('name', '')[:60]}")
                _emit(f"       Zieldatei: {_files}")
                _desc = (_t.get("description") or "").strip().replace("\n", " ")
                if _desc:
                    _emit_wrapped(_desc)
        _emit("")
    # M-410b: Tasks ohne phase_id (flacher Plan, z.B. Architect)
    _ohne_phase = [
        _t for _t in tasks
        if isinstance(_t, dict) and not _t.get("phase_id")
    ]
    if _ohne_phase:
        _emit("")
        for _t in _ohne_phase:
            _files = ", ".join(_t.get("task_files", [])) or "(keine)"
            _emit(f"  {_t.get('id')} [{_t.get('action', '?')}] {_t.get('name', '')[:60]}")
            _emit(f"       Zieldatei: {_files}")
            _desc = (_t.get("description") or "").strip().replace("\n", " ")
            if _desc:
                _emit_wrapped(_desc)

    if tests:
        _emit(f"Tests ({len(tests)}):")
        for _t in tests:
            _emit(f"  - {_t}")
    if akzeptanzkriterien:
        _emit(f"Akzeptanzkriterien ({len(akzeptanzkriterien)}):")
        for _a in akzeptanzkriterien:
            _emit(f"  - {_a}")
    _emit("")


def _render_plan_rich(phasen, tasks, tests, akzeptanzkriterien) -> None:
    body = []
    for _p in phasen:
        body.append(f"[bold cyan]Phase {_p.get('id', '?')}[/]: {_p.get('titel', '')}")
        for _t in tasks:
            if isinstance(_t, dict) and _t.get("phase_id") == _p.get("id"):
                _files = ", ".join(_t.get("task_files", [])) or "(keine)"
                _action = _t.get("action", "?")
                _color = {"create": "green", "update": "yellow", "read": "dim"}.get(_action, "white")
                body.append(
                    f"  [{_color}]{_t.get('id')} [{_action}][/] {_t.get('name', '')[:55]}"
                )
                body.append(f"       [dim]→ {_files}[/]")
                _desc = (_t.get("description") or "").strip().replace("\n", " ")
                if _desc:
                    body.append(f"       [dim]{_desc[:800]}[/]")
        body.append("")
    # M-410c: Tasks ohne phase_id (flacher Plan, z.B. Architect)
    _ohne_phase = [
        _t for _t in tasks
        if isinstance(_t, dict) and not _t.get("phase_id")
    ]
    if _ohne_phase:
        body.append("")
        for _t in _ohne_phase:
            _files = ", ".join(_t.get("task_files", [])) or "(keine)"
            _action = _t.get("action", "?")
            _color = {"create": "green", "update": "yellow",
                      "read": "dim", "architect": "magenta"}.get(_action, "white")
            body.append(
                f"  [{_color}]{_t.get('id')} [{_action}][/] "
                f"{_t.get('name', '')[:55]}"
            )
            body.append(f"       [dim]→ {_files}[/]")
            _desc = (_t.get("description") or "").strip().replace("\n", " ")
            if _desc:
                body.append(f"       [dim]{_desc[:800]}[/]")

    if tests:
        body.append(f"[bold]Tests ({len(tests)}):[/]")
        for _t in tests:
            body.append(f"  [dim]-[/] {_t}")
    if akzeptanzkriterien:
        body.append(f"[bold]Akzeptanzkriterien ({len(akzeptanzkriterien)}):[/]")
        for _a in akzeptanzkriterien:
            body.append(f"  [dim]-[/] {_a}")
    _console.print(_RichPanel(
        "\n".join(body),
        title=f"[bold cyan]PLAN[/] — {len(phasen)} Phasen, {len(tasks)} Tasks",
        border_style="cyan",
    ))


def panel_diff(diff_text: str, title: str = "HUMAN GATE") -> None:
    """Zeigt den Diff (Box mit Syntax-Highlighting)."""
    if _use_rich:
        _console.print(_RichPanel(
            _RichSyntax(diff_text, "diff", theme="monokai", line_numbers=False),
            title=f"[bold yellow]{title}[/]",
            border_style="yellow",
        ))
    else:
        _emit("")
        _emit("=" * 62)
        _emit(f"  {title}")
        _emit("=" * 62)
        for line in diff_text.splitlines():
            _emit(line)
        _emit("=" * 62)
        _emit("")


# Alias (Rueckwaertskompatibilitaet)
plan = panel_plan


# ============================================================
# Progress-Bar (nur live)
# ============================================================

def progress_task(nr: int, total: int, name: str):
    """Context-Manager fuer einen Task mit Fortschrittsbalken (nur live)."""
    if IS_LIVE and _HAS_RICH:
        return _RichProgress(
            SpinnerColumn(),
            TextColumn(f"[cyan]{nr}/{total}[/] {name[:40]}"),
            BarColumn(),
            TaskProgressColumn(),
            transient=True,
        )
    return _null_progress()


class _null_progress:
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def add_task(self, *a, **kw): return 0
    def update(self, *a, **kw): pass
    def advance(self, *a, **kw): pass

def _with_spinner(label: str, fn):
    """M-455: Fuehrt fn aus, mit Spinner + Heartbeat alle 2s.

    Zeigt dem Nutzer, dass der Loop laeuft (nicht haengt).
    """
    import threading as _th
    import time as _time

    try:
        spinner_start(label)
    except Exception:  # noqa: BLE001, S110
        pass

    _start = _time.monotonic()
    _done = _th.Event()
    _result: list = [None]
    _exc: list = [None]

    def _worker():
        try:
            _result[0] = fn()
        except Exception as e:  # noqa: BLE001
            _exc[0] = e
        finally:
            _done.set()

    def _heartbeat_loop():
        _last = -1
        while not _done.is_set():
            _el = int(_time.monotonic() - _start)
            if _el // 2 > _last // 2:
                try:
                    heartbeat(label, _el)
                except Exception:  # noqa: BLE001, S110
                    pass
                _last = _el
            _done.wait(timeout=0.5)

    _t = _th.Thread(target=_worker, daemon=True)
    _hb = _th.Thread(target=_heartbeat_loop, daemon=True)
    _t.start()
    _hb.start()
    _t.join()
    _hb.join(timeout=1)

    try:
        spinner_stop()
    except Exception:  # noqa: BLE001, S110
        pass

    # M-456: permanente Log-Zeile.
    try:
        _elapsed = _time.monotonic() - _start
        log_line(label, elapsed_s=_elapsed, ok=(_exc[0] is None))
    except Exception:  # noqa: BLE001, S110
        pass

    if _exc[0] is not None:
        raise _exc[0]
    return _result[0]

# _with_spinner_log_line

# ============================================================
# M-456: Erweiterte Render-API (log_line, task_started, summary)
# ============================================================

def _timestamp() -> str:
    """HH:MM:SS fuer permanente Log-Zeilen."""
    import datetime as _dt
    return _dt.datetime.now().strftime("%H:%M:%S")


def log_line(
    label: str, detail: str = "",
    elapsed_s: float | None = None,
    ok: bool = True,
) -> None:
    """Permanente Zeile mit Zeitstempel. Ersetzt nicht, appends.

    Beispiel: [12:47:16] OK Explorer  . 3.1s . 8 files
    """
    ts = _timestamp()
    if IS_CI:
        status = "ok" if ok else "fail"
        _emit_raw(f"::log::{ts} {status} {label} {detail}")
    else:
        _el = f" · {elapsed_s:.1f}s" if elapsed_s is not None else ""
        if _use_rich:
            mark = "[green]OK[/]" if ok else "[red]X[/]"
            _console.print(
                f"[dim]{ts}[/] {mark} [bold]{label}[/]{_el}"
                + (f" · [dim]{detail}[/]" if detail else "")
            )
        else:
            mark = "OK" if ok else "X"
            _emit_raw(f"[{ts}] {mark} {label}{_el}" + (f" · {detail}" if detail else ""))
    _publish("log_line", label + (f" · {detail}" if detail else ""))
    _status_tee = "OK" if ok else "X"
    _tee(
        f"[{ts}] {_status_tee} {label}"
        + (f" · {detail}" if detail else "")
        + (f" · {elapsed_s:.1f}s" if elapsed_s is not None else "")
    )


def task_started(nr: int, total: int, name: str) -> None:
    """Permanente Zeile: Task startet."""
    ts = _timestamp()
    if IS_CI:
        print(f"::log::{ts} start Task {nr}/{total}: {name}")
        return
    if _use_rich:
        _console.print(
            f"[dim]{ts}[/] [cyan]>[/] [bold]Task {nr}/{total}[/]: {name} [dim](running)[/]"
        )
    else:
        print(f"[{ts}] > Task {nr}/{total}: {name} (running)")


def task_done(
    nr: int, total: int, name: str,
    elapsed_s: float | None = None,
    ok: bool = True, reason: str = "",
) -> None:
    """Permanente Zeile: Task fertig (ok oder failed)."""
    ts = _timestamp()
    _el = f" · {elapsed_s:.1f}s" if elapsed_s is not None else ""
    if IS_CI:
        status = "ok" if ok else "fail"
        print(f"::log::{ts} {status} Task {nr}/{total}: {name}{_el}")
        return
    mark_ok = "[green]OK[/]" if ok else "[red]X[/]"
    mark_plain = "OK" if ok else "X"
    suffix = f" [dim]({reason})[/]" if reason else ""
    if _use_rich:
        _console.print(
            f"[dim]{ts}[/] {mark_ok} [bold]Task {nr}/{total}[/]: {name}{_el}{suffix}"
        )
    else:
        print(f"[{ts}] {mark_plain} Task {nr}/{total}: {name}{_el}" + (f" ({reason})" if reason else ""))


def status_header(label: str, detail: str = "") -> None:
    """Ueberschreibbare Status-Zeile oben (nur live)."""
    if not IS_LIVE:
        return
    try:
        spinner_update(label, detail)
    except Exception:  # noqa: BLE001, S110
        pass


def summary(
    tasks_ok: int, tasks_failed: int,
    elapsed_s: float, task_details: list[dict] | None = None,
) -> None:
    """Zusammenfassung am Ende (permanent)."""
    ts = _timestamp()
    total = tasks_ok + tasks_failed
    _el = f"{elapsed_s:.1f}s"
    if IS_CI:
        print(f"::log::{ts} done {tasks_ok}/{total} tasks in {_el}")
        return
    if _use_rich:
        _console.print("")
        _console.print(
            f"[dim]{ts}[/] [bold green]Done[/] · {_el} · "
            f"[green]{tasks_ok}[/]/{total} Tasks"
            + (f" · [red]{tasks_failed} failed[/]" if tasks_failed else "")
        )
        for t in (task_details or []):
            mark = "[green]OK[/]" if t.get("ok") else "[red]X[/]"
            name = t.get("name", "?")
            el = f" · {t.get('elapsed_s', 0):.1f}s" if t.get("elapsed_s") else ""
            _console.print(f"  {mark} {name}{el}")
    else:
        print(f"[{ts}] Done · {_el} · {tasks_ok}/{total} Tasks" + (f" · {tasks_failed} failed" if tasks_failed else ""))

