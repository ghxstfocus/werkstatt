"""Rich-Setup, Farben, Modus-Wahl (OP-138 Phase 2a)."""
from __future__ import annotations

import os
import sys as _sys

from .tee import _TeeWriter

# === Modus-Wahl ===
_render_mode_raw = os.environ.get("WERKSTATT_RENDER", "").lower()
_is_tty = _sys.stdout.isatty()
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
    from rich.progress import (  # type: ignore[import-not-found]
        Progress as _RichProgress,
    )
    from rich.spinner import Spinner as _RichSpinner  # type: ignore[import-not-found]
    from rich.syntax import Syntax as _RichSyntax  # type: ignore[import-not-found]
    _HAS_RICH = True
except ImportError:
    _HAS_RICH = False
    _RichConsole = None  # type: ignore[assignment,misc]
    _RichLive = None  # type: ignore[assignment,misc]
    _RichPanel = None  # type: ignore[assignment,misc]
    _RichProgress = None  # type: ignore[assignment,misc]
    _RichSpinner = None  # type: ignore[assignment,misc]
    _RichSyntax = None  # type: ignore[assignment,misc]
    BarColumn = None  # type: ignore[assignment,misc]
    SpinnerColumn = None  # type: ignore[assignment,misc]
    TaskProgressColumn = None  # type: ignore[assignment,misc]
    TextColumn = None  # type: ignore[assignment,misc]


_use_rich = _HAS_RICH and RENDER_MODE in ("pretty", "live")
if _use_rich:
    _console: _RichConsole = _RichConsole(  # type: ignore[misc,call-arg]
        file=_TeeWriter(_sys.stdout),
        force_terminal=(RENDER_MODE == "live"), width=100,
    )
else:
    _console = _RichConsole(quiet=True)  # type: ignore[misc,call-arg]


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
