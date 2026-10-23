"""Strangler-Fig Loop (M-262 Option C, 2026-10-23).

Phase 2: Harte Gates (B1 Plan-Gate, B2 Verifier).
Der Loop prueft deterministisch, bevor er den alten Motor startet.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pipeline
from werkstatt.audit import audit
from werkstatt.state import RunState


def _plan_gate(state: RunState) -> bool:
    """B1: Plan-Gate (deterministisch).
    
    Prueft, ob tasks, tests und akzeptanzkriterien vorhanden sind.
    Kein LLM.
    """
    return all((getattr(state, 'tasks', []), getattr(state, 'tests', []), getattr(state, 'akzeptanzkriterien', [])))


def _verify_patches(state: RunState) -> bool:
    """B2: Verifier (deterministisch).
    
    Ruft tools/quality_gate.py auf dem aktuellen Stand auf.
    Kein LLM.
    """
    qg_path = Path("/opt/werkstatt/tools/quality_gate.py")
    if not qg_path.exists():
        return False
    
    try:
        res = subprocess.run(
            ["python3", str(qg_path), "--json"],
            cwd="/opt/werkstatt",
            capture_output=True, text=True, timeout=300, check=False
        )
        return res.returncode == 0 and (
            '"ok": true' in res.stdout or '"ok":true' in res.stdout
        )
    except Exception:  # noqa: BLE001
        return False


def run_pipeline_loop(
    project_name: str,
    aufgabe: str,
    state_ref: list[RunState],
    *,
    phasen_state: RunState | None = None,
) -> int:
    """Neuer Orchestrator. Prueft Gates, bevor er an pipeline.run_pipeline delegiert."""
    state = phasen_state or (state_ref[-1] if state_ref else None)

    if state is not None and getattr(state, "project_dir", None) is not None:
        # B1: Plan-Gate
        if not _plan_gate(state):
            audit("loop_gate_failed", {"gate": "plan"}, state.project_dir, state.project_name)
            return 1
        
        # B2: Verifier
        if not _verify_patches(state):
            audit("loop_gate_failed", {"gate": "verify"}, state.project_dir, state.project_name)
            return 1

        # Gates gruen -> Delegation an den alten Motor
        audit("loop_aktiv", {"project_name": project_name, "aufgabe": aufgabe[:100]}, state.project_dir, state.project_name)
        audit("loop_fallback", {"reason": "phase2_delegation_to_pipeline"}, state.project_dir, state.project_name)

    # Delegation
    rc = pipeline.run_pipeline(
        project_name, aufgabe, state_ref, phasen_state=phasen_state
    )
    return rc
