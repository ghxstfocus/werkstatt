"""Strangler-Fig Loop (M-262 Option C, 2026-10-23).

Neuer Orchestrator-Einstiegspunkt.
Ruft in Phase 1 den alten pipeline.run_pipeline als Fallback auf.
Schreibt Audit-Events (loop_aktiv, loop_fallback).
"""
from __future__ import annotations

import pipeline
from werkstatt.audit import audit
from werkstatt.state import RunState


def run_pipeline_loop(
    project_name: str,
    aufgabe: str,
    state_ref: list[RunState],
    *,
    phasen_state: RunState | None = None,
) -> int:
    """Neuer Orchestrator. Delegiert an pipeline.run_pipeline (Strangler-Fig)."""
    # State fuer Audit ermitteln
    state = phasen_state or (state_ref[-1] if state_ref else None)
    
    if state is not None and getattr(state, "project_dir", None) is not None:
        audit(
            "loop_aktiv",
            {"project_name": project_name, "aufgabe": aufgabe[:100]},
            state.project_dir,
            state.project_name,
        )
        audit(
            "loop_fallback",
            {"reason": "phase1_delegation_to_pipeline"},
            state.project_dir,
            state.project_name,
        )

    # Phase 1: Delegation an den alten Motor
    return pipeline.run_pipeline(
        project_name, aufgabe, state_ref, phasen_state=phasen_state
    )
