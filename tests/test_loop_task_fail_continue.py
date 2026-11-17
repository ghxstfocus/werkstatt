"""Spec: Task-Fail -> continue statt return 1 (Fix AR)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "/opt/werkstatt")


class TestTaskFailContinue:
    def test_builder_hands_off_to_checkpoint_coordinator(self) -> None:
        """Builder must return before inline Verify/Reflection/Reviewer paths."""
        import werkstatt.roles.task_dispatch as _tasks

        src = Path(_tasks.__file__).read_text(encoding="utf-8")
        assert "task_checkpoint_requires_coordinator_decision" in src
        assert "record_task_build_checkpoint(task_id)" in src
        assert '"reason": "build_evidence_could_not_be_bound"' in src
        assert "Post-Build Verify + Reflection (automatisch)" not in src
        assert "Reviewer (Phase 9)" not in src

    def test_pre_build_gate_bleibt_return_1(self) -> None:
        """pre_build_gate ist echter Abbruch, kein Task-Fail."""
        # Laufzeitcode liegt im Koordinator und seinen aktiven Checkpoint-Executoren.
        import werkstatt.loop as _loop
        import werkstatt.phases as _pp
        import werkstatt.roles.project_context as _ctx
        import werkstatt.roles.task_dispatch as _task_dispatch
        src = (
            Path(_loop.__file__).read_text(encoding="utf-8")
            + ("\n".join(Path(m.__file__).read_text(encoding="utf-8") for m in [_ctx, _task_dispatch, _pp._review_mod, _pp._finalize_mod]))
        )
        # OP-114 (2026-11-04): Payload wird jetzt via _gate_failed_payload
        # gebaut. Struktur-Anker ist der _verify_patches-Aufruf mit
        # phase="pre_build"; danach muss ein return 1 folgen (echter Abbruch).
        idx = src.find('_verify_patches(state, phase="pre_build")')
        assert idx > 0, "pre_build-verify-Pfad nicht gefunden"
        tail = src[idx:idx+2000]
        assert "return 1" in tail, "pre_build-Pfad endet nicht mit return 1"
