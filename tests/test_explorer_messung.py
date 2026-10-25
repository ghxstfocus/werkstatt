"""Tests fuer M-338-Fix / M-373: Explorer-Messung."""
from pathlib import Path

from werkstatt.explorer import _extract_dateien, _messen


def test_extract_dateien_ruff_concise() -> None:
    stdout = (
        "pipeline.py:3825:13: PIE810 Call `startswith` once\n"
        "pipeline.py:5194:13: F841 Local variable unused\n"
        "tools/audit.py:73:17: SIM102 nested if\n"
        "tests/test_audit.py:43:5: RUF059 unused\n"
    )
    dateien = _extract_dateien(stdout)
    assert dateien == [
        "pipeline.py",
        "tools/audit.py",
        "tests/test_audit.py",
    ]


def test_extract_dateien_leer_bei_keinem_py() -> None:
    assert _extract_dateien("") == []
    assert _extract_dateien("keine fehler") == []


def test_extract_dateien_dedupliziert() -> None:
    stdout = (
        "pipeline.py:1:1: A\n"
        "pipeline.py:2:1: B\n"
        "tools/audit.py:3:1: C\n"
    )
    assert _extract_dateien(stdout) == ["pipeline.py", "tools/audit.py"]


def test_messen_ruff_ruft_run_readonly(tmp_path: Path) -> None:
    """Messung mit 'ruff'-Trigger gibt 'ruff'-Key zurueck."""
    m = _messen("Beseitige die ruff-Fehler", tmp_path)
    assert "ruff" in m
    # In leerem Verzeichnis: 0 Fehler, aber Key existiert
    assert "stdout" in m["ruff"]
    assert "dateien" in m["ruff"]


def test_messen_ohne_trigger_leer(tmp_path: Path) -> None:
    m = _messen("Refaktoriere das Modul", tmp_path)
    assert m == {}


def test_messen_pytest_trigger(tmp_path: Path) -> None:
    m = _messen("Repariere den pytest-Fehler", tmp_path)
    assert "pytest" in m
