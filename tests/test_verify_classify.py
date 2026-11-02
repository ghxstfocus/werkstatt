"""Tests fuer verify_classify (OP-077-Nachbereitung)."""
from __future__ import annotations

from werkstatt.verify_classify import (
    filtere_harte_verify_fehler,
    ist_harter_verify_fehler,
)


def test_ruff_f_klasse_ist_hart() -> None:
    assert ist_harter_verify_fehler("ruff_changed: F822 Undefined name")
    assert ist_harter_verify_fehler("ruff_changed: F401 unused import")
    assert ist_harter_verify_fehler("ruff_changed: F811 redefinition")


def test_ruff_style_ist_weich() -> None:
    assert not ist_harter_verify_fehler("ruff_changed: E501 line too long")
    assert not ist_harter_verify_fehler("ruff_changed: C901 too complex")
    assert not ist_harter_verify_fehler("ruff_changed: W291 trailing whitespace")


def test_py_compile_ist_hart() -> None:
    assert ist_harter_verify_fehler("py_compile_changed: SyntaxError")
    assert ist_harter_verify_fehler("py_compile_fallback: error")


def test_pytest_ist_hart() -> None:
    assert ist_harter_verify_fehler("pytest_changed: 2 failed")
    assert ist_harter_verify_fehler("pytest_regression: 5 passed 1 failed")


def test_mypy_ist_weich() -> None:
    assert not ist_harter_verify_fehler("mypy_changed: Missing positional")
    assert not ist_harter_verify_fehler("mypy_changed: 5 errors")


def test_filtere_harte_nur_harte() -> None:
    errors = [
        "ruff_changed: F822 Undefined name",
        "ruff_changed: E501 line too long",
        "py_compile_changed: SyntaxError",
        "mypy_changed: Missing positional",
        "pytest_changed: 1 failed",
    ]
    hart = filtere_harte_verify_fehler(errors)
    assert len(hart) == 3
    assert any("F822" in str(e) for e in hart)
    assert any("py_compile" in str(e) for e in hart)
    assert any("pytest" in str(e) for e in hart)
    assert not any("E501" in str(e) for e in hart)
    assert not any("mypy" in str(e) for e in hart)


def test_filtere_harte_leere_liste() -> None:
    assert filtere_harte_verify_fehler([]) == []
    assert filtere_harte_verify_fehler(None) == []
