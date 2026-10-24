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

import os
import sys
import threading
from datetime import datetime

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

# rich nur im pretty/live-Modus aktiv
_use_rich = _HAS_RICH and RENDER_MODE in ("pretty", "live")
if _use_rich:
    _console = _RichConsole(force_terminal=(RENDER_MODE == "live"), width=100)
else:
    _console = None


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


def _emit(text: str) -> None:
    """Zentraler Output. CI: mit Zeitstempel. Sonst: plain."""
    if IS_CI:
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {text}", flush=True)
    else:
        print(text, flush=True)


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


def heartbeat(label: str, elapsed_s: int) -> None:
    """Lebenszeichen fuer langlaufende Calls."""
    if IS_LIVE:
        spinner_update(label, f"{elapsed_s}s")
    else:
        _emit(f"  · {label} — {elapsed_s}s")


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
        _emit(f"  {_dim(label)} {_cyan('→')} {name}")


def task_ok(nr: int, total: int, elapsed_s: float | None = None) -> None:
    label = f"[{nr}/{total}]"
    timing = f" ({elapsed_s:.1f}s)" if elapsed_s is not None else ""
    if IS_LIVE and _HAS_RICH:
        spinner_stop()
    _emit(f"  {_dim(label)} {_green('✓')} task ok{timing}")


def task_failed(nr: int, total: int, reason: str = "") -> None:
    label = f"[{nr}/{total}]"
    extra = f" — {reason}" if reason else ""
    if IS_LIVE and _HAS_RICH:
        spinner_stop()
    _emit(f"  {_dim(label)} {_red('✗')} task failed{extra}")


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


# ============================================================
# Neue API: Panels
# ============================================================

def panel_plan(phasen, tasks, tests, akzeptanzkriterien) -> None:
    """Zeigt den Plan (Box in pretty/live, Plain in ci)."""
    if _use_rich:
        _render_plan_rich(phasen, tasks, tests, akzeptanzkriterien)
    else:
        _render_plan_plain(phasen, tasks, tests, akzeptanzkriterien)


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
        _emit("")
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
        body.append("")
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
