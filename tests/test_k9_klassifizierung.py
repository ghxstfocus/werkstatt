"""K9: _klassifiziere_fehler matcht Stage-Prefixes."""
from werkstatt.planner import _klassifiziere_fehler


def test_py_compile_changed() -> None:
    assert _klassifiziere_fehler("py_compile_changed", "") == "syntax"


def test_py_compile_core() -> None:
    assert _klassifiziere_fehler("py_compile_core", "") == "syntax"


def test_py_compile_exakt() -> None:
    assert _klassifiziere_fehler("py_compile", "") == "syntax"


def test_syntaxerror_ohne_stage() -> None:
    assert _klassifiziere_fehler("?", "SyntaxError: x") == "syntax"


def test_ruff_changed() -> None:
    assert _klassifiziere_fehler("ruff_changed", "") == "lint"


def test_ruff_exakt() -> None:
    assert _klassifiziere_fehler("ruff", "") == "lint"


def test_mypy_changed() -> None:
    assert _klassifiziere_fehler("mypy_changed", "") == "type"


def test_pytest_changed() -> None:
    assert _klassifiziere_fehler("pytest_changed", "") == "test"


def test_import_error() -> None:
    assert _klassifiziere_fehler("?", "ImportError: x") == "env"
    assert _klassifiziere_fehler("?", "ModuleNotFoundError: x") == "env"


def test_unbekannt() -> None:
    assert _klassifiziere_fehler("?", "irgendwas") == "unknown"
