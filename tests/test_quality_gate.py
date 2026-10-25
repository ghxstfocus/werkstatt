"""Tests fuer tools/quality_gate.py (M-331b).

Prueft, dass der Gate bei rotem pytest (failed > 0) fail-closed
ist: delta.pytest = 1, ok = False.
"""
from __future__ import annotations

from unittest.mock import patch

from tools import quality_gate

_BASE = quality_gate.BASELINE["pytest"]


def _pytest_out(passed: int, failed: int = 0) -> str:
    """Erzeugt pytest-Output-String fuer Mocks."""
    if failed:
        return f"{passed} passed, {failed} failed in 14s"
    return f"{passed} passed in 14s"


def _mock_run_factory(pytest_output: str):
    """Erzeugt _run-Mock: pytest liefert pytest_output, andere Baseline.

    Wichtig: Substring-Pruefung ("test_audit_kinds" in cmd_str), nicht
    Exakt-Match in der Liste. Sonst matcht der pytest-Zweig auch fuer
    ["pytest", "tests/test_audit_kinds.py"], weil "test_audit_kinds"
    nicht exakt als Listenelement vorkommt.
    """
    def _mock_run(cmd, cwd, env=None):
        cmd_str = " ".join(str(c) for c in cmd)
        # Spezifischere Regel zuerst:
        if "test_audit_kinds" in cmd_str:
            return 0, "6 passed in 0.1s"
        if cmd_str.startswith("pytest"):
            return 0, pytest_output
        if "ruff" in cmd_str:
            return 0, "Found 13 errors."
        if "mypy" in cmd_str:
            return 0, "Found 11 errors."
        return 0, ""
    return _mock_run


def test_gate_failed_macht_rot(tmp_path):
    """M-331b: 1 failed -> delta.pytest > 0 -> ok=False."""
    pytest_out = _pytest_out(_BASE, failed=1)
    with patch.object(quality_gate, "_run", side_effect=_mock_run_factory(pytest_out)):
        # Katalog-Fallback: _KATALOG_SOLL in pipeline.py
        (tmp_path / "pipeline.py").write_text("_KATALOG_SOLL = 162\n")
        result = quality_gate.check_all(tmp_path)

    assert result["current"]["pytest"]["failed"] == 1
    assert result["delta"]["pytest"] == 1, f"delta.pytest={result['delta']['pytest']}"
    assert result["ok"] is False, "gate muss rot sein bei 1 failed"
    assert result["regression"] is True


def test_gate_all_green_ist_ok(tmp_path):
    """M-331b: 1361 passed, 0 failed -> delta.pytest=0 -> ok=True."""
    pytest_out = _pytest_out(_BASE)
    with patch.object(quality_gate, "_run", side_effect=_mock_run_factory(pytest_out)):
        (tmp_path / "pipeline.py").write_text("_KATALOG_SOLL = 162\n")
        result = quality_gate.check_all(tmp_path)

    assert result["current"]["pytest"]["failed"] == 0
    assert result["delta"]["pytest"] == 0
    assert result["ok"] is True


def test_gate_passed_unter_baseline_macht_rot(tmp_path):
    """M-331b: passed < baseline -> delta.pytest > 0 -> ok=False."""
    pytest_out = _pytest_out(_BASE - 1)  # passed < Baseline
    with patch.object(quality_gate, "_run", side_effect=_mock_run_factory(pytest_out)):
        (tmp_path / "pipeline.py").write_text("_KATALOG_SOLL = 162\n")
        result = quality_gate.check_all(tmp_path)

    assert result["delta"]["pytest"] == 1
    assert result["ok"] is False
