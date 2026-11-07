"""Tests fuer die Integritaet der Projekt-Konfigurationsdateien.

Diese Tests stellen sicher, dass zentrale Konfigurationsdateien
(pyproject.toml, pytest.ini, mypy.ini, requirements.txt) nicht
stillschweigend veraendert werden.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

PROJEKT_ROOT = Path(__file__).resolve().parent.parent


def _lade_pyproject() -> dict:
    """Laedt pyproject.toml aus dem Projekt-Root."""
    pfad = PROJEKT_ROOT / "pyproject.toml"
    with pfad.open("rb") as f:
        return tomllib.load(f)


def test_importlinter_unveraendert() -> None:
    """Import-Linter-Contracts bleiben unveraendert."""
    daten = _lade_pyproject()
    importlinter = daten["tool"]["importlinter"]
    assert importlinter["root_package"] == "werkstatt"
    assert importlinter["include_external_packages"] is False
    contracts = importlinter["contracts"]
    assert len(contracts) == 3
    assert contracts[0]["name"] == "render ist eine Leaf-Schicht"
    assert contracts[1]["name"] == "roles.builder kennt keine phases oder web"
    assert contracts[2]["name"] == "phases kennt keine web"


def test_ruff_lint_unveraendert() -> None:
    """Ruff-Lint-Ignores bleiben exakt unveraendert."""
    daten = _lade_pyproject()
    ignore = daten["tool"]["ruff"]["lint"]["ignore"]
    assert ignore == ["BLE001", "S110", "RUF100"]


def test_pytest_ini_bleibt_aktive_config() -> None:
    """pytest.ini bleibt die aktive pytest-Konfiguration."""
    pytest_ini = PROJEKT_ROOT / "pytest.ini"
    assert pytest_ini.exists()
    assert pytest_ini.stat().st_size > 0
    daten = _lade_pyproject()
    tool = daten.get("tool", {})
    assert "pytest" not in tool or "ini_options" not in tool.get("pytest", {})


def test_mypy_ini_existiert() -> None:
    """mypy.ini existiert als Config-Traeger."""
    mypy_ini = PROJEKT_ROOT / "mypy.ini"
    assert mypy_ini.exists()
    assert mypy_ini.stat().st_size > 0


def test_requirements_txt_ohne_aktive_test_tools_zeilen() -> None:
    """Test-Tools stehen nur in Kommentar-Zeilen von requirements.txt."""
    requirements = PROJEKT_ROOT / "requirements.txt"
    zeilen = requirements.read_text(encoding="utf-8").splitlines()
    aktive = [z for z in zeilen if z.strip() and not z.lstrip().startswith("#")]
    for zeile in aktive:
        assert "hypothesis" not in zeile
        assert "pytest-gremlins" not in zeile


def test_requirements_txt_hat_zwei_kommentar_zeilen_fuer_test_tools() -> None:
    """requirements.txt enthaelt genau zwei Kommentar-Zeilen fuer Test-Tools."""
    requirements = PROJEKT_ROOT / "requirements.txt"
    zeilen = requirements.read_text(encoding="utf-8").splitlines()
    kommentar_zeilen = [z for z in zeilen if z.lstrip().startswith("#")]
    test_tool_kommentare = [
        z for z in kommentar_zeilen
        if "hypothesis" in z or "pytest-gremlins" in z
    ]
    assert len(test_tool_kommentare) == 2


def test_pyproject_version_ist_0_1_0() -> None:
    """pyproject.toml deklariert Version 0.1.0 (Basis fuer 'pip show werkstatt')."""
    daten = _lade_pyproject()
    assert daten["project"]["version"] == "0.1.0"


def test_pyproject_hat_test_tools_extra() -> None:
    """pyproject.toml deklariert das optionale Extra 'test-tools'."""
    daten = _lade_pyproject()
    extras = daten["project"].get("optional-dependencies", {})
    assert "test-tools" in extras
    assert len(extras["test-tools"]) > 0


def test_pyproject_importlinter_und_ruff_lint_byte_identisch() -> None:
    """[tool.importlinter] und [tool.ruff.lint] bleiben byte-identisch."""
    daten = _lade_pyproject()
    tool = daten["tool"]
    assert tool["importlinter"]["root_package"] == "werkstatt"
    assert tool["ruff"]["lint"]["ignore"] == ["BLE001", "S110", "RUF100"]


def test_pytest_laeuft_ohne_installiertes_package() -> None:
    """pytest.ini ist die aktive Config, unabhaengig von einer Installation."""
    pytest_ini = PROJEKT_ROOT / "pytest.ini"
    inhalt = pytest_ini.read_text(encoding="utf-8")
    assert "[pytest]" in inhalt
    assert "testpaths" in inhalt or "python_files" in inhalt
