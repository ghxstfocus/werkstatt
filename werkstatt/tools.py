"""Tools fuer Rollen. Read-only vs. write.

Read-only (Explorer, Planner, Reviewer):
  ruff check, pytest -q, grep, find, cat, ls,
  git status/diff/log, py_compile.

Write (nur Builder):
  ruff check --fix.

Deny (immer): rm, git commit/push, pip install, sudo, curl, wget.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

READONLY_ALLOWED = [
    "ruff check", "ruff --version",
    "pytest -q", "pytest --collect-only",
    "python3 -m pytest", "python3 -m py_compile",
    "grep", "find", "cat", "ls", "wc", "head", "tail",
    "git status", "git diff", "git log",
]

WRITE_ALLOWED = ["ruff check --fix", "ruff format"]

DENY = [
    "rm ", "rm -", "git commit", "git push", "git reset --hard",
    "pip install", "pip3 install", "sudo", "curl", "wget",
    "chmod", "chown", "mkfs", "dd ",
]


def _find_tool(name: str, cwd: Path) -> str:
    """M-387: Findet ein Tool im venv des Zielprojekts, sonst PATH.

    Das Zielprojekt hat seine eigene Tool-Version in .venv/bin/.
    Der Loop muss gegen DIESE Version pruefen, nicht gegen die
    System-Version (Reproduzierbarkeit, CI-Konsistenz).
    """
    venv_bin = Path(cwd) / ".venv" / "bin" / name
    if venv_bin.exists():
        return str(venv_bin)
    return name


def _run(cmd: str, cwd: Path, allowed: list[str]) -> dict[str, Any]:
    """Fuehrt cmd aus, wenn er in allowed ist und nicht in DENY."""
    cmd = cmd.strip()
    if not cmd:
        return {"ok": False, "error": "leerer Befehl"}
    # Deny zuerst
    for d in DENY:
        if cmd.startswith(d) or f" {d}" in f" {cmd} ":
            return {"ok": False, "error": f"blockiert (deny): {d.strip()}"}
    # Allow
    if not any(cmd == a or cmd.startswith(a + " ") for a in allowed):
        return {"ok": False, "error": f"nicht erlaubt: {cmd}"}
    # M-387: Tool aus venv nehmen, wenn vorhanden
    _parts = cmd.split()
    _parts[0] = _find_tool(_parts[0], Path(cwd))
    try:
        res = subprocess.run(
            _parts, cwd=str(cwd), capture_output=True,
            text=True, timeout=120, check=False,
        )
        return {
            "ok": res.returncode == 0,
            "rc": res.returncode,
            "stdout": res.stdout[:5000],
            "stderr": res.stderr[:2000],
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Timeout (120s)"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def run_readonly(cmd: str, cwd: Path) -> dict[str, Any]:
    """Read-only Tool fuer Explorer/Planner/Reviewer."""
    return _run(cmd, cwd, READONLY_ALLOWED)


def run_write(cmd: str, cwd: Path) -> dict[str, Any]:
    """Write-Tool fuer den Builder."""
    return _run(cmd, cwd, READONLY_ALLOWED + WRITE_ALLOWED)
