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

import sys

# ANSI-Farben (nur wenn Terminal, sonst Plain)
USE_COLOR = sys.stdout.isatty()

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
    print()
    print(_bold("═" * 60))
    print(_bold(f"  WERKSTATT LOOP — {title}"))
    print(_bold("═" * 60))
    print()


def step(phase_nr: int, name: str, detail: str = "", ok: bool = True) -> None:
    """Zeigt einen Loop-Schritt (z.B. [1/5] Explorer ... 3 files)."""
    marker = _green("✓") if ok else _red("✗")
    label = f"[{phase_nr}/{TOTAL_PHASES}]"
    name_padded = name.ljust(14)
    if detail:
        print(f"  {_dim(label)} {marker} {_bold(name_padded)} {_dim('...')} {detail}")
    else:
        print(f"  {_dim(label)} {marker} {_bold(name_padded)}")


def task(nr: int, total: int, name: str) -> None:
    """Zeigt einen Task im Task-Loop."""
    label = f"[{nr}/{total}]"
    print(f"  {_dim(label)} {_cyan('→')} {name}")


def task_ok(nr: int, total: int) -> None:
    label = f"[{nr}/{total}]"
    print(f"  {_dim(label)} {_green('✓')} task ok")


def task_failed(nr: int, total: int, reason: str = "") -> None:
    label = f"[{nr}/{total}]"
    extra = f" — {reason}" if reason else ""
    print(f"  {_dim(label)} {_red('✗')} task failed{extra}")


def hook(name: str, ok: bool, reason: str = "") -> None:
    """Zeigt einen Hook-Aufruf."""
    marker = _green("✓") if ok else _yellow("!")
    extra = f" — {reason}" if reason and not ok else ""
    print(f"           {marker} hook: {name}{extra}")


def patch(file: str, action: str = "create") -> None:
    """Zeigt einen angewendeten Patch."""
    icon = "＋" if action == "create" else "✎"
    print(f"           {icon} {file}")


def footer(success: bool, tasks_total: int, tasks_ok: int) -> None:
    """Zeigt den Loop-Abschluss."""
    print()
    print(_bold("═" * 60))
    if success:
        print(_green(_bold("  ✓ LOOP ERFOLGREICH")))
    else:
        print(_red(_bold("  ✗ LOOP FEHLGESCHLAGEN")))
    print(f"  Tasks: {tasks_ok}/{tasks_total}")
    print(_bold("═" * 60))
    print()
