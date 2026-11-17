"""Spec: Loop bricht bei reviewer_deterministic_fail sofort ab (Fix R)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "/opt/werkstatt")


class TestLoopReviewerDeterministicFail:
    def test_loop_setzt_flag_vor_reviewer(self) -> None:
        """Loop muss reviewer_deterministic_fail=False vor run_reviewer
        initialisieren, damit ein stale Flag nicht triggert."""
        # Fix AZ Stufe 11: Logik liegt jetzt in pipeline_phases.py.
        import werkstatt.loop as _loop
        import werkstatt.phases as _pp
        import werkstatt.roles.complete_task as _ctx
        import werkstatt.roles.task_dispatch as _task_dispatch
        src = (
            Path(_loop.__file__).read_text(encoding="utf-8")
            + ("\n".join(Path(m.__file__).read_text(encoding="utf-8") for m in [_ctx, _task_dispatch, _pp._review_mod, _pp._finalize_mod]))
        )
        # Nach _with_spinner("Reviewer ...
        assert "state.reviewer_deterministic_fail = False" in src, (
            "Loop initialisiert reviewer_deterministic_fail nicht"
        )
        # Reviewer-Ablehnung wird aus dem Task-Abschlussworker gemeldet.
        idx = src.find("if not services.review(state, task_index):")
        assert idx > 0
        block = src[idx:idx + 2000]
        assert "reviewer_rejected_at_checkpoint" in block, (
            "Task role does not persist the reviewer rejection outcome"
        )

    def test_reviewer_setzt_flag_bei_unvollstaendig(self) -> None:
        """run_reviewer muss bei fehlenden Konzepten Flag setzen."""
        import werkstatt.reviewer as _r
        src = Path(_r.__file__).read_text(encoding="utf-8")
        assert "state.reviewer_deterministic_fail = True" in src
