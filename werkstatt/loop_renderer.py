"""Loop-Renderer (CI-Optik). Phase 18, 2026-10-23.

Schreibt lesbare Statuszeilen in die Konsole:
  [1/5] Explorer        ... 3 files
  [2/5] Planner         ... 4 tasks
  [3/5] Builder         ... 2 patches
  [4/5] Reviewer        ... OK
  [5/5] Human-Gate      ... approve

Statt roher `AUDIT: ...`-Zeilen.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime

# M-302 + M-321: Rich (optional). Fallback auf Plain.
# M-321: force_terminal=False, damit Rich auch in Pipes (tee/Log)
# strukturiert rendert, aber ohne ANSI-Codes.

_force_pretty = os.environ.get("WERKSTATT_RENDER") == "pretty"
_is_tty = sys.stdout.isatty()

try:
    from rich.console import Console as _RichConsole  # type: ignore[import-not-found]
    _HAS_RICH = True
    _console = _RichConsole(
        force_terminal=False,
        no_color=(not _is_tty) or not bool(os.environ.get("FORCE_COLOR")),
        width=100,
    )
except ImportError:
    _HAS_RICH = False
    _console = None

# ANSI-Farben (nur wenn echtes Terminal, sonst Plain)
USE_COLOR = _is_tty

# M-301 + M-321: CI-Modus (kein TTY, kein WERKSTATT_RENDER=pretty)
# -> plain line-by-line mit Zeitstempel.
IS_CI = (not _is_tty) and (not _force_pretty)


def _emit(text: str) -> None:
    """Zentraler Output. TTY: plain. CI: mit Zeitstempel."""
    if IS_CI:
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {text}")
    else:
        print(text)


def group_start(name: str) -> None:
    """Phasen-Header: CI ::group::, TTY+Rich Panel, sonst Plain."""
    if IS_CI:
        print(f"::group::{name}")
    elif _HAS_RICH and _console is not None:
        _console.rule(f"[bold cyan]{name}[/]")
    else:
        _emit(f"--- {name} ---")


def group_end() -> None:
    """Phasen-Ende: CI ::endgroup::, sonst nichts."""
    if IS_CI:
        print("::endgroup::")


def heartbeat(label: str, elapsed_s: int) -> None:
    """CI: Lebenszeichen fuer langlaufende Calls."""
    _emit(f"  · {label} — {elapsed_s}s")


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

TOTAL_PHASES = 5


def header(title: str) -> None:
    """Zeigt den Loop-Header (einmal pro Lauf)."""
    _emit("")
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
    """Zeigt einen Loop-Schritt (z.B. [1/5] Explorer ... 3 files (1.2s))."""
    marker = _green("✓") if ok else _red("✗")
    label = f"[{phase_nr}/{TOTAL_PHASES}]"
    name_padded = name.ljust(14)
    timing = f" ({elapsed_s:.1f}s)" if elapsed_s is not None else ""
    if detail:
        _emit(f"  {_dim(label)} {marker} {_bold(name_padded)} {_dim('...')} {detail}{timing}")
    else:
        _emit(f"  {_dim(label)} {marker} {_bold(name_padded)}{timing}")


def task(nr: int, total: int, name: str) -> None:
    """Zeigt einen Task im Task-Loop."""
    label = f"[{nr}/{total}]"
    _emit(f"  {_dim(label)} {_cyan('→')} {name}")


def task_ok(nr: int, total: int, elapsed_s: float | None = None) -> None:
    label = f"[{nr}/{total}]"
    timing = f" ({elapsed_s:.1f}s)" if elapsed_s is not None else ""
    _emit(f"  {_dim(label)} {_green('✓')} task ok{timing}")


def task_failed(nr: int, total: int, reason: str = "") -> None:
    label = f"[{nr}/{total}]"
    extra = f" — {reason}" if reason else ""
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
    _emit(_bold("═" * 60))
    if success:
        _emit(_green(_bold("  ✓ LOOP ERFOLGREICH")))
    else:
        _emit(_red(_bold("  ✗ LOOP FEHLGESCHLAGEN")))
    _emit(f"  Tasks: {tasks_ok}/{tasks_total}")
    _emit(_bold("═" * 60))
    _emit("")
