"""Tests fuer tools/quality_gate.py (M-331b).

Prueft, dass der Gate bei rotem pytest (failed > 0) fail-closed
ist: delta.pytest = 1, ok = False.
"""
from __future__ import annotations

from unittest.mock import patch

from tools import quality_gate

_BASE = quality_gate.BASELINE["pytest"]


def _prepare_tree(tmp_path):
    (tmp_path / "tests").mkdir(exist_ok=True)
    (tmp_path / "tests" / "test_audit_warnung.py").write_text(
        "# fixture for the dedicated audit catalog test\n",
        encoding="utf-8",
    )



def _pytest_out(passed: int, failed: int = 0) -> str:
    """Erzeugt pytest-Output-String fuer Mocks."""
    if failed:
        return f"{passed} passed, {failed} failed in 14s"
    return f"{passed} passed in 14s"


def _mock_run_factory(pytest_output: str):
    """Erzeugt _run-Mock: pytest liefert pytest_output, andere Baseline.

    Pytest wird als `sys.executable -m pytest` gestartet, damit das Gate
    dieselbe Python-Umgebung wie den aufrufenden Loop verwendet.
    """
    def _mock_run(cmd, cwd, env=None):
        cmd_str = " ".join(str(c) for c in cmd)
        # Spezifischere Regel zuerst:
        if "test_katalog_enthaelt_alle_code_kinds" in cmd_str:
            return 0, "1 passed in 0.1s"
        if "-m pytest" in cmd_str:
            return 0, pytest_output
        if "-m ruff" in cmd_str:
            return 0, f"Found {quality_gate.BASELINE['ruff']} errors."
        if "-m mypy" in cmd_str:
            return 0, f"Found {quality_gate.BASELINE['mypy']} errors."
        return 0, ""
    return _mock_run


def test_gate_failed_macht_rot(tmp_path):
    """M-331b: 1 failed -> delta.pytest > 0 -> ok=False."""
    pytest_out = _pytest_out(_BASE, failed=1)
    with patch.object(quality_gate, "_run", side_effect=_mock_run_factory(pytest_out)):
        _prepare_tree(tmp_path)
        result = quality_gate.check_all(tmp_path)

    assert result["current"]["pytest"]["failed"] == 1
    assert result["delta"]["pytest"] == 1, f"delta.pytest={result['delta']['pytest']}"
    assert result["ok"] is False, "gate muss rot sein bei 1 failed"
    assert result["regression"] is True


def test_gate_all_green_ist_ok(tmp_path):
    """M-331b: 1361 passed, 0 failed -> delta.pytest=0 -> ok=True."""
    pytest_out = _pytest_out(_BASE)
    with patch.object(quality_gate, "_run", side_effect=_mock_run_factory(pytest_out)):
        _prepare_tree(tmp_path)
        result = quality_gate.check_all(tmp_path)

    assert result["current"]["pytest"]["failed"] == 0
    assert result["delta"]["pytest"] == 0
    assert result["ok"] is True


def test_gate_passed_unter_baseline_macht_rot(tmp_path):
    """M-331b: passed < baseline -> delta.pytest > 0 -> ok=False."""
    pytest_out = _pytest_out(_BASE - 1)  # passed < Baseline
    with patch.object(quality_gate, "_run", side_effect=_mock_run_factory(pytest_out)):
        _prepare_tree(tmp_path)
        result = quality_gate.check_all(tmp_path)

    assert result["delta"]["pytest"] == 1
    assert result["ok"] is False


def test_quality_gate_reports_mypy_diagnostic(tmp_path):
    diagnostic = (
        "werkstatt/example.py:12: error: type mismatch [arg-type]\n"
        "Found 1 error in 1 file (checked 2 source files)"
    )

    def mock_run(cmd, cwd, env=None):
        command = " ".join(str(part) for part in cmd)
        if "test_katalog_enthaelt_alle_code_kinds" in command:
            return 0, "1 passed in 0.1s"
        if "-m pytest" in command:
            return 0, _pytest_out(_BASE)
        if "-m ruff" in command:
            return 0, "All checks passed!"
        if "-m mypy" in command:
            return 1, diagnostic
        return 0, ""

    _prepare_tree(tmp_path)
    with patch.object(quality_gate, "_run", side_effect=mock_run):
        result = quality_gate.check_all(tmp_path)

    mypy = result["current"]["mypy"]
    assert mypy["errors"] == 1
    assert mypy["exit_code"] == 1
    assert mypy["diagnostic"] == diagnostic
    assert result["regression"] is True


def test_quality_gate_reports_pytest_start_failure(tmp_path):
    diagnostic = "ModuleNotFoundError: No module named pytest"

    def mock_run(cmd, cwd, env=None):
        command = " ".join(str(part) for part in cmd)
        if "test_katalog_enthaelt_alle_code_kinds" in command:
            return 1, diagnostic
        if "-m pytest" in command:
            return -1, diagnostic
        if "-m ruff" in command:
            return 0, "All checks passed!"
        if "-m mypy" in command:
            return 0, "Success: no issues found"
        return 0, ""

    _prepare_tree(tmp_path)
    with patch.object(quality_gate, "_run", side_effect=mock_run):
        result = quality_gate.check_all(tmp_path)

    pytest_result = result["current"]["pytest"]
    assert pytest_result["passed"] == 0
    assert pytest_result["failed"] == 1
    assert pytest_result["exit_code"] == -1
    assert pytest_result["diagnostic"] == diagnostic
    assert result["delta"]["pytest"] > 0
    assert result["regression"] is True


def test_quality_gate_reports_ruff_start_failure(tmp_path):
    diagnostic = "No module named ruff"

    def mock_run(cmd, cwd, env=None):
        command = " ".join(str(part) for part in cmd)
        if "test_katalog_enthaelt_alle_code_kinds" in command:
            return 0, "1 passed in 0.1s"
        if "-m pytest" in command:
            return 0, _pytest_out(_BASE)
        if "-m ruff" in command:
            return -1, diagnostic
        if "-m mypy" in command:
            return 0, "Success: no issues found"
        return 0, ""

    _prepare_tree(tmp_path)
    with patch.object(quality_gate, "_run", side_effect=mock_run):
        result = quality_gate.check_all(tmp_path)

    ruff = result["current"]["ruff"]
    assert ruff["errors"] == 999_999
    assert ruff["exit_code"] == -1
    assert ruff["diagnostic"] == diagnostic
    assert result["regression"] is True


def test_quality_gate_detects_python_syntax_error(tmp_path):
    _prepare_tree(tmp_path)
    source = tmp_path / "werkstatt"
    source.mkdir()
    (source / "broken.py").write_text("def broken(:\n", encoding="utf-8")
    with patch.object(
        quality_gate, "_run",
        side_effect=_mock_run_factory(_pytest_out(_BASE)),
    ):
        result = quality_gate.check_all(tmp_path)

    assert result["current"]["ast"]["errors"] == 1
    assert result["delta"]["ast"] == 1
    assert "broken.py" in result["current"]["ast"]["diagnostics"][0]
    assert result["regression"] is True


def test_quality_gate_fails_when_audit_catalog_test_fails(tmp_path):
    _prepare_tree(tmp_path)

    def mock_run(cmd, cwd, env=None):
        command = " ".join(str(part) for part in cmd)
        if "test_katalog_enthaelt_alle_code_kinds" in command:
            return 1, "0 passed, 1 failed in 0.1s"
        if "-m pytest" in command:
            return 0, _pytest_out(_BASE)
        if "-m ruff" in command:
            return 0, "All checks passed!"
        if "-m mypy" in command:
            return 0, "Success: no issues found"
        return 0, ""

    with patch.object(quality_gate, "_run", side_effect=mock_run):
        result = quality_gate.check_all(tmp_path)

    assert result["current"]["katalog"]["errors"] == 1
    assert result["delta"]["katalog"] == 1
    assert result["regression"] is True
