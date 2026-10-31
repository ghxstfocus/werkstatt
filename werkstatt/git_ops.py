"""Git-Operationen fuer den Loop (Fix AZ Stufe 1).

Extraktion aus loop.py (2026-10-31). Reine subprocess-Wrapper,
kein audit, keine Querverweise. Re-Export in loop.py erhaelt
Test-Patches auf werkstatt.loop._git_*.
"""
from __future__ import annotations

import subprocess
from pathlib import Path


def _get_git_diff_for_hook() -> str:
    """Holt den aktuellen Git-Diff fuer Hooks."""
    try:
        res = subprocess.run(
            ["git", "diff", "HEAD", "--", ".", ":!PROGRESS.md"],
            cwd="/opt/werkstatt", capture_output=True, text=True,
            timeout=30, check=False,
        )
        return res.stdout[:10000]
    except Exception:  # noqa: BLE001
        return ""


def _git_dirty(pd: Path) -> bool:
    """M-353a: Prueft, ob das Zielprojekt uncommittete Aenderungen hat."""
    try:
        res = subprocess.run(
            ["git", "-C", str(pd), "status", "--porcelain"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        return bool(res.stdout.strip())
    except Exception:  # noqa: BLE001
        return False


def _git_head(pd: Path) -> str:
    """M-353a: Liefert den aktuellen HEAD-Commit."""
    try:
        res = subprocess.run(
            ["git", "-C", str(pd), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        return res.stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def _git_stash(pd: Path) -> bool:
    """M-353b: Sichert dirty tree via git stash."""
    try:
        res = subprocess.run(
            ["git", "-C", str(pd), "stash", "push", "-u",
             "-m", "werkstatt-loop"],
            capture_output=True, text=True, timeout=30, check=False,
        )
        return res.returncode == 0
    except Exception:  # noqa: BLE001
        return False


def _git_stash_pop(pd: Path) -> bool:
    """M-353b: Holt dirty tree zurueck (bei Erfolg).

    GOLD 2026-10-30: Wenn pop fehlschlaegt (Konflikt), drop den
    Stash. Sonst sammeln sich Stashes an -- Live-Beleg 2026-10-30:
    8 offene Stashes nach 8 RERUNs, alle 'werkstatt-loop'.
    """
    try:
        res = subprocess.run(
            ["git", "-C", str(pd), "stash", "pop"],
            capture_output=True, text=True, timeout=30, check=False,
        )
        if res.returncode == 0:
            return True
        subprocess.run(
            ["git", "-C", str(pd), "stash", "drop", "stash@{0}"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        return False
    except Exception:  # noqa: BLE001
        return False


def _git_stash_drop(pd: Path) -> bool:
    """M-353b: Verwirft dirty tree (bei Fehler)."""
    try:
        res = subprocess.run(
            ["git", "-C", str(pd), "stash", "drop"],
            capture_output=True, text=True, timeout=30, check=False,
        )
        return res.returncode == 0
    except Exception:  # noqa: BLE001
        return False


def _git_reset(pd: Path, ref: str) -> bool:
    """M-353c: Setzt Arbeitsbaum auf ref zurueck."""
    try:
        res = subprocess.run(
            ["git", "-C", str(pd), "reset", "--hard", ref],
            capture_output=True, text=True, timeout=30, check=False,
        )
        return res.returncode == 0
    except Exception:  # noqa: BLE001
        return False


__all__ = [
    "_get_git_diff_for_hook",
    "_git_dirty",
    "_git_head",
    "_git_reset",
    "_git_stash",
    "_git_stash_drop",
    "_git_stash_pop",
]
