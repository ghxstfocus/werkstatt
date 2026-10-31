"""Spec: Loop bricht bei reviewer_deterministic_fail sofort ab (Fix R)."""
from __future__ import annotations
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, "/opt/werkstatt")
import pytest


class TestLoopReviewerDeterministicFail:
    def test_loop_setzt_flag_vor_reviewer(self) -> None:
        """Loop muss reviewer_deterministic_fail=False vor run_reviewer
        initialisieren, damit ein stale Flag nicht triggert."""
        # Fix AZ Stufe 11: Logik liegt jetzt in pipeline_phases.py.
        import werkstatt.loop as _loop
        import werkstatt.pipeline_phases as _pp
        src = (
            Path(_loop.__file__).read_text(encoding="utf-8")
            + Path(_pp.__file__).read_text(encoding="utf-8")
        )
        # Nach _with_spinner("Reviewer ...
        assert "state.reviewer_deterministic_fail = False" in src, (
            "Loop initialisiert reviewer_deterministic_fail nicht"
        )
        # Und prueft es nach not _rev_ok
        idx = src.find("if not _rev_ok:")
        assert idx > 0
        block = src[idx:idx + 2000]
        assert "reviewer_deterministic_fail" in block, (
            "Loop prueft reviewer_deterministic_fail nicht nach Reviewer-Fail"
        )
        assert "reviewer_unvollstaendig" in block, (
            "Loop setzt failure='reviewer_unvollstaendig' nicht"
        )

    def test_reviewer_setzt_flag_bei_unvollstaendig(self) -> None:
        """run_reviewer muss bei fehlenden Konzepten Flag setzen."""
        import werkstatt.reviewer as _r
        src = Path(_r.__file__).read_text(encoding="utf-8")
        assert "state.reviewer_deterministic_fail = True" in src
