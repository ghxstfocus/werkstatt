"""Regression: Selbst-Check-Block + CoT-Fallback duerfen nicht wieder
in den Architect-Prompt kommen (siehe 2026-11-05)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "/opt/werkstatt")


def test_selbst_check_nicht_im_prompt():
    """_build_selbst_check_block darf nicht im user_content landen."""
    src = Path("werkstatt/planner.py").read_text()
    # Die Konstante darf referenziert, aber nicht per += eingebaut werden.
    assert "_build_selbst_check_block()" not in src, (
        "Selbst-Check-Block triggert CoT bei deepseek-reasoner. "
        "Regress 2026-11-05: reasoning_content landete als Prosa "
        "im Planner-Split."
    )


def test_fallback_fail_loud():
    """_ask_llm_impl darf reasoning_content NICHT als content akzeptieren."""
    src = Path("werkstatt/agent.py").read_text()
    # Der fail-loud-Pfad muss da sein
    assert "leerer content, reasoning_content vorhanden" in src, (
        "Fallback muss fail-loud sein (ok=False). Regress: leerer "
        "content = CoT-Budget erschoepft, kein Prosa-Substitut."
    )
