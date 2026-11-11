"""Git-Operationen fuer den Loop (Fix AZ Stufe 1).

Extraktion aus loop.py (2026-10-31). Reine subprocess-Wrapper,
kein audit, keine Querverweise. Re-Export in loop.py erhaelt
Test-Patches auf werkstatt.loop._git_*.
"""
from __future__ import annotations

import subprocess
import uuid
from pathlib import Path


def _get_git_diff_for_hook() -> str:
    """Holt den aktuellen Git-Diff fuer Hooks."""
    try:
        res = subprocess.run(
            ["git", "diff", "HEAD", "--", ".", ":!PROGRESS.md"],
            cwd=str(__import__("werkstatt.paths", fromlist=["werkstatt_home"]).werkstatt_home()),
            capture_output=True, text=True,
            timeout=30, check=False,
        )
        return res.stdout[:10000]
    except Exception:
        return ""


def _git_dirty(pd: Path) -> bool:
    """M-353a: Prueft, ob das Zielprojekt uncommittete Aenderungen hat."""
    try:
        res = subprocess.run(
            ["git", "-C", str(pd), "status", "--porcelain"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        return bool(res.stdout.strip())
    except Exception:
        return False


def _git_head(pd: Path) -> str:
    """M-353a: Liefert den aktuellen HEAD-Commit."""
    try:
        res = subprocess.run(
            ["git", "-C", str(pd), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        return res.stdout.strip()
    except Exception:
        return ""


def _git_stash(pd: Path) -> bool:
    """M-353b: Sichert dirty tree via git stash."""
    try:
        marker = f"werkstatt-loop:{uuid.uuid4().hex}"
        res = subprocess.run(
            ["git", "-C", str(pd), "stash", "push", "-u", "-m", marker],
            capture_output=True, text=True, timeout=30, check=False,
        )
        return res.returncode == 0
    except Exception:
        return False


def _git_stash_pop(pd: Path, stash_ref: str | None = None) -> bool:
    """Restore only this run's stash; retain it if restoration conflicts."""
    if (
        not isinstance(stash_ref, str)
        or len(stash_ref) not in (40, 64)
        or any(char not in "0123456789abcdefABCDEF" for char in stash_ref)
    ):
        return False
    try:
        listed = subprocess.run(
            [
                "git", "-C", str(pd), "stash", "list",
                "--format=%gd%x09%H",
            ],
            capture_output=True, text=True, timeout=10, check=False,
        )
        if listed.returncode != 0:
            return False
        selector = ""
        for line in listed.stdout.splitlines():
            name, separator, commit = line.partition("\t")
            if not separator or commit.lower() != stash_ref.lower():
                continue
            if not name.startswith("stash@{") or not name.endswith("}"):
                return False
            if not name[7:-1].isdecimal():
                return False
            selector = name
            break
        if not selector:
            return False
        return subprocess.run(
            ["git", "-C", str(pd), "stash", "pop", "--index", selector],
            capture_output=True, text=True, timeout=30, check=False,
        ).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _git_reset(pd: Path, ref: str) -> bool:
    """M-353c: Setzt Arbeitsbaum auf ref zurueck."""
    try:
        res = subprocess.run(
            ["git", "-C", str(pd), "reset", "--hard", ref],
            capture_output=True, text=True, timeout=30, check=False,
        )
        return res.returncode == 0
    except Exception:
        return False


__all__ = [
    "_get_git_diff_for_hook",
    "_git_dirty",
    "_git_head",
    "_git_reset",
    "_git_stash",
    "_git_stash_pop",
]
