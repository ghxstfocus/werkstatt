"""Spec: Task-Fail -> continue statt return 1 (Fix AR)."""
from __future__ import annotations
import re
import sys
from pathlib import Path

sys.path.insert(0, "/opt/werkstatt")
import pytest


class TestTaskFailContinue:
    def test_kein_return_1_in_task_fail_pfaden(self) -> None:
        """Prueft fuer jeden Task-Fail-Pfad: nach `_task_ende(ok=False, ...)
        folgt `continue`, NICHT `return 1`. Zwischen beiden darf etwas
        Code stehen (z.B. Reflection), aber kein `return 1`."""
        import werkstatt.loop as _loop
        src = Path(_loop.__file__).read_text(encoding="utf-8")
        for marker in (
            'failure="reviewer_unvollstaendig")',
            'failure="reviewer_rejected_no_patch")',
            'failure="reviewer_rejected")',
            'failure="reviewer_divergenz")',
            'failure="reviewer_rejected_after_reflection")',
        ):
            idx = src.find(marker)
            assert idx > 0, f"Marker nicht gefunden: {marker}"
            # Suche das naechste Vorkommen von continue und return 1
            next_continue = src.find("continue", idx)
            next_return1 = src.find("return 1", idx)
            assert next_continue > 0, (
                f"Kein continue nach {marker}"
            )
            assert (next_return1 < 0 or next_continue < next_return1), (
                f"Nach {marker} folgt return 1 (pos {next_return1}) vor "
                f"continue (pos {next_continue})"
            )

    def test_pre_build_gate_bleibt_return_1(self) -> None:
        """pre_build_gate ist echter Abbruch, kein Task-Fail."""
        import werkstatt.loop as _loop
        src = Path(_loop.__file__).read_text(encoding="utf-8")
        assert '"gate": "pre_build"' in src
        idx = src.find('"gate": "pre_build"')
        assert idx > 0
        tail = src[idx:idx+400]
        assert "return 1" in tail
