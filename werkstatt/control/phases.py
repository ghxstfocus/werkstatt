"""Phase-Enum: alle Stadien im Loop, in denen Kontrollen laufen."""
from __future__ import annotations

from enum import Enum


class Phase(str, Enum):
    """Chronologische Loop-Phasen.

    Reihenfolge entspricht dem Loop-Ablauf (nicht alphabetisch).
    """
    # Vor dem Builder
    PRE_BUILD = "pre_build"
    SCOUT = "scout"
    PLAN_GATE = "plan_gate"
    PLAN_REJECT = "plan_reject"

    # Pro Task
    TASK_START = "task_start"
    TASK_END = "task_end"

    # Nach dem Builder
    POST_BUILD = "post_build"
    REFLECTION = "reflection"

    # Pro Phase
    PHASE_START = "phase_start"
    PHASE_END = "phase_end"

    # Human
    HUMAN_GATE = "human_gate"

    # Opt-in
    ADR_MINI = "adr_mini"

    def __str__(self) -> str:  # noqa: D401
        return self.value
