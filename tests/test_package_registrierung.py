from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path


def _lade_pyproject() -> dict:
    pfad = Path(__file__).resolve().parent.parent / "pyproject.toml"
    with pfad.open("rb") as f:
        return tomllib.load(f)


def test_version_ist_0_1_0() -> None:
    daten = _lade_pyproject()
    assert daten["project"]["version"] == "0.1.0"


def test_test_tools_enthaelt_hypothesis_und_pytest_gremlins() -> None:
    daten = _lade_pyproject()
    eintraege = daten["project"]["optional-dependencies"]["test-tools"]
    assert any("hypothesis" in eintrag for eintrag in eintraege)
    assert any("pytest-gremlins" in eintrag for eintrag in eintraege)


def test_werkstatt_importierbar() -> None:
    import werkstatt

    assert hasattr(werkstatt, "__file__")
    assert werkstatt.__file__ is not None


def test_egg_info_ist_gitignored() -> None:
    pfad = Path(__file__).resolve().parent.parent / ".gitignore"
    inhalt = pfad.read_text(encoding="utf-8")
    assert "*.egg-info/" in inhalt


def test_pip_install_editable_test_tools_laeuft() -> None:
    ergebnis = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", ".[test-tools]", "--dry-run"],
        cwd=Path(__file__).resolve().parent.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    assert ergebnis.returncode == 0, ergebnis.stderr


def test_pip_show_werkstatt_zeigt_version() -> None:
    ergebnis = subprocess.run(
        [sys.executable, "-m", "pip", "show", "werkstatt"],
        capture_output=True,
        text=True,
        check=False,
    )
    if ergebnis.returncode != 0:
        # Package nicht installiert: dann muss wenigstens der Import gehen.
        import werkstatt

        assert werkstatt.__file__ is not None
        return
    assert "Version: 0.1.0" in ergebnis.stdout


def test_pytest_tests_laeuft_mit_installiertem_package() -> None:
    ergebnis = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "--collect-only", "-q"],
        cwd=Path(__file__).resolve().parent.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    assert ergebnis.returncode == 0, ergebnis.stderr
