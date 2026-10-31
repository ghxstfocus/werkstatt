"""Spec: verify-Soft-Fail trennt Style von echten Fehlern (Fix AT)."""
from __future__ import annotations
import sys

sys.path.insert(0, "/opt/werkstatt")
import pytest


class TestStageKlassifikation:
    def test_py_compile_ist_hart(self) -> None:
        from werkstatt.loop import _stage_ist_hart
        assert _stage_ist_hart("py_compile_changed") is True
        assert _stage_ist_hart("py_compile_core") is True
        assert _stage_ist_hart("py_compile_fallback") is True

    def test_pytest_ist_hart(self) -> None:
        from werkstatt.loop import _stage_ist_hart
        assert _stage_ist_hart("pytest_changed") is True
        assert _stage_ist_hart("pytest_full_checks") is True

    def test_ruff_ist_weich(self) -> None:
        from werkstatt.loop import _stage_ist_hart
        assert _stage_ist_hart("ruff_changed") is False
        assert _stage_ist_hart("ruff_full") is False

    def test_mypy_ist_weich(self) -> None:
        from werkstatt.loop import _stage_ist_hart
        assert _stage_ist_hart("mypy_tests") is False

    def test_unbekannt_ist_hart(self) -> None:
        from werkstatt.loop import _stage_ist_hart
        assert _stage_ist_hart("voellig_neu") is True
