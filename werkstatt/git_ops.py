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


def _git_worktree_marker_exists(pd: Path) -> bool:
    """Erkennt ein Git-Repository oder einen Worktree am Projekt-Root."""
    try:
        (Path(pd) / ".git").lstat()
    except FileNotFoundError:
        return False
    except OSError:
        return True
    return True


def _git_dirty(pd: Path) -> bool:
    """Prueft Aenderungen; Git-Fehler in erkennbaren Repos sind unsicher."""
    try:
        res = subprocess.run(
            ["git", "-C", str(pd), "status", "--porcelain"],
            capture_output=True, text=True, timeout=10, check=False,
        )
    except Exception:
        return _git_worktree_marker_exists(pd)
    if res.returncode == 0:
        return bool(res.stdout.strip())
    return _git_worktree_marker_exists(pd)


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


def _git_stash_owned(pd: Path) -> str | None:
    """Create a uniquely marked stash and return its exact commit if verifiable.

    A changed refs/stash alone does not prove ownership: another actor can
    add a stash while this command runs. Match the per-call marker in the
    reflog subject and require exactly one valid commit.
    """
    marker = f"werkstatt-loop:{uuid.uuid4().hex}"
    try:
        subprocess.run(
            ["git", "-C", str(pd), "stash", "push", "-u", "-m", marker],
            capture_output=True, text=True, timeout=30, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        # The command may have created the stash before timing out. Inspect
        # by unique marker; never infer ownership from refs/stash.
        pass

    try:
        listed = subprocess.run(
            ["git", "-C", str(pd), "stash", "list", "--format=%H%x09%gs"],
            capture_output=True, text=True, timeout=10, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if listed.returncode != 0:
        return None

    matches: list[str] = []
    for line in listed.stdout.splitlines():
        commit, separator, subject = line.partition("\t")
        if not separator or marker not in subject:
            continue
        if (
            len(commit) not in (40, 64)
            or any(char not in "0123456789abcdefABCDEF" for char in commit)
        ):
            return None
        matches.append(commit)
    return matches[0] if len(matches) == 1 else None


def _git_stash(pd: Path) -> bool:
    """M-353b: Legacy-Wrapper fuer den Bool-Erfolg des Stash-Pushs."""
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
    "_git_stash_owned",
    "_git_stash_pop",
]
