"""Spec: Reflection-OK nur bei applied_count-Anstieg (Fix AL)."""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, "/opt/werkstatt")
import pytest


class TestReflectionNoApply:
    def test_audit_kind_existiert(self) -> None:
        import werkstatt.audit as _a
        assert "loop_reflection_no_apply" in _a._AUDIT_KINDS_BEKANNT

    def test_pruefung_im_loop(self) -> None:
        """Code-Pruefung: nach _reflection_loop wird applied_count
        verglichen."""
        # Fix AZ Stufe 11: Logik liegt jetzt in pipeline_phases.py.
        # Alle relevanten Quellen pruefen (loop.py + pipeline_phases.py).
        import werkstatt.loop as _loop
        import werkstatt.pipeline_phases as _pp
        src = (
            Path(_loop.__file__).read_text(encoding="utf-8")
            + Path(_pp.__file__).read_text(encoding="utf-8")
        )
        assert "_applied_vor_al" in src
        assert "_applied_nach_al" in src
        assert "reflection_ohne_apply" in src
