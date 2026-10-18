"""W36-RP-b (2026-10-18): Tests fuer die conftest.py-Fixture
_no_gefaehrliche_subprocess.

Die Fixture blockiert gefaehrliche Kommandos
(rm, curl, wget, sudo, bash -c, etc.) in allen
Tests. Legitime Kommandos (git, pytest, ruff,
mypy, python, cat) bleiben erlaubt.

W51c-b-Lehre: ein Schutz, der nicht getestet
ist, ist kein Schutz.
"""
from __future__ import annotations

import subprocess

import pytest


def test_gefaehrliches_subprocess_wird_blockiert() -> None:
    """W36-RP-b T-1: rm wird blockiert."""
    with pytest.raises(AssertionError, match="gefaehrliches"):
        subprocess.run(["rm", "-rf", "/tmp/x"], check=False)


def test_legitimes_subprocess_wird_erlaubt() -> None:
    """W36-RP-b T-2: git --version laeuft durch
    (kein AssertionError)."""
    try:
        subprocess.run(
            ["git", "--version"],
            capture_output=True, timeout=5,
            check=False)
    except AssertionError:
        pytest.fail(
            "git --version wurde faelschlich blockiert")


def test_sudo_wrapper_wird_blockiert() -> None:
    """W36-RP-b T-3: sudo rm wird als Wrapper
    erkannt und blockiert."""
    with pytest.raises(AssertionError, match="gefaehrliches"):
        subprocess.run(["sudo", "rm", "-rf", "/tmp/x"], check=False)


def test_bash_c_wird_blockiert() -> None:
    """W36-RP-b T-4: bash -c 'rm ...' wird blockiert."""
    with pytest.raises(AssertionError, match="gefaehrliches"):
        subprocess.run(["bash", "-c", "rm -rf /tmp/x"], check=False)
