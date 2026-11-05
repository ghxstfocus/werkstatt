"""Progress + Heartbeat + Task-Progress (OP-138 Phase 2b)."""
from __future__ import annotations

import threading

from . import emit as _emit_m
from . import rich as _rich
from . import spinner as _spin

_PROGRESS_STATE: dict[str, str] = {}


_PROGRESS_LOCK = threading.Lock()


def _emit_progress(label: str, step: str, detail: str = "") -> None:
    """Strukturierter Progress-Event aus Sub-Komponenten.

    Live:   ueberschreibt die Zeile pro label (kein \n).
    CI/plain: sequenzielle Zeilen mit \n (via _emit_raw).
    Leerer step: no-op (stille Events erlaubt).

    Verwendung: `_emit_progress("Builder", "start", zieldatei)`
    """
    if not step:
        return
    line = f"[{label}] {step}"
    if detail:
        line += f" {detail}"

    if _rich.IS_LIVE:
        with _PROGRESS_LOCK:
            _PROGRESS_STATE[label] = line
            _emit_m._progress_write(line)
        _emit_m._publish("progress", line, label=label, step=step, detail=detail)
    else:
        _emit_m._emit_raw(line)
        _emit_m._publish("progress", line, label=label, step=step, detail=detail)


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
    if _rich.IS_LIVE and _spin._live is not None:
        _spin.spinner_update(label, f"{elapsed_s}s")
        return
    _last = _LAST_HEARTBEAT.get(label, -999)
    # Bugfix 2026-11-03: In CI erst ab 30s und dann alle 15s
    # (vorher 5s -> Log-Spam bei pytest_changed). In non-CI
    # 5s-Throttle. _publish nur wenn tatsaechlich ausgegeben.
    if _rich.IS_CI:
        if elapsed_s < 30 or elapsed_s - _last < 15:
            return
    else:
        if elapsed_s - _last < 5:
            return
    _LAST_HEARTBEAT[label] = elapsed_s
    _emit_m._emit(f"  · {label} ({elapsed_s}s)")
    _emit_m._publish("heartbeat", label, label=label, elapsed_s=elapsed_s)


def progress_task(nr: int, total: int, name: str):
    """Context-Manager fuer einen Task mit Fortschrittsbalken (nur live)."""
    if _rich.IS_LIVE and _rich._HAS_RICH:
        return _rich._RichProgress(
            _rich.SpinnerColumn(),
            _rich.TextColumn(f"[cyan]{nr}/{total}[/] {name[:40]}"),
            _rich.BarColumn(),
            _rich.TaskProgressColumn(),
            transient=True,
        )
    return _null_progress()


class _null_progress:
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def add_task(self, *a, **kw): return 0
    def update(self, *a, **kw): pass
    def advance(self, *a, **kw): pass
