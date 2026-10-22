"""Gekapselte subprocess-Aufrufe (A2).

Shell-Bypass fuer git / ruff / Mess-Kommandos.
Ersetzt 30 verstreute subprocess.run-Aufrufe in
pipeline.py.

Design (M-A2, M-173..M-177):
  - Alle: check=False, capture_output=True, text=True,
    env=subprocess_env().
  - Aufrufer prueft .returncode selbst.
  - Keine Exceptions ausser subprocess.TimeoutExpired.
  - CompletedProcess als Rueckgabe.

Kategorien (M-181):
  git    22x  (run_git)
  ruff    3x  (run_ruff)
  mess    5x  (run_test)
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from werkstatt.subprocess_env import subprocess_env


def run_git(
    args: list[str],
    cwd: Path,
    timeout: int = 30,
) -> subprocess.CompletedProcess[str]:
    """git-Aufruf. env=subprocess_env(), check=False."""
    return subprocess.run(
        args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        env=subprocess_env(),
    )


def run_ruff(
    args: list[str],
    cwd: Path,
    timeout: int = 60,
) -> subprocess.CompletedProcess[str]:
    """ruff-Aufruf (check/format). env=subprocess_env()."""
    return subprocess.run(
        args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        env=subprocess_env(),
    )


def run_test(
    argv: list[str],
    cwd: Path,
    timeout: int = 300,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Mess-Kommando (pytest, sed, read_file).

    env=None -> voller os.environ (Kompatibilitaet Z.3269
    bis M-187-Fix). env=subprocess_env() wenn explizit.

    Aufrufer prueft .returncode.
    """
    if env is not None:
        return subprocess.run(
            argv, cwd=str(cwd), capture_output=True,
            text=True, timeout=timeout, check=False,
            env=env,
        )
    return subprocess.run(
        argv, cwd=str(cwd), capture_output=True,
        text=True, timeout=timeout, check=False,
    )
