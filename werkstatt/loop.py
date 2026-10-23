"""Strangler-Fig Loop (M-262 Option C, 2026-10-23).

Phase 3: Echter Ablauf mit harten Gates.
Der Loop ruft die Bausteine des alten Motors auf,
prueft aber nach jeder Phase die Baseline.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pipeline
from werkstatt.audit import audit
from werkstatt.state import RunState


def _plan_gate(state: RunState) -> bool:
    """B1: Plan-Gate (deterministisch)."""
    return all((
        getattr(state, 'tasks', []),
        getattr(state, 'tests', []),
        getattr(state, 'akzeptanzkriterien', [])
    ))


def _verify_patches(state: RunState) -> bool:
    """B2: Verifier (deterministisch). Ruft quality_gate.py auf."""
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
    """Echter Loop: Plan -> Build -> Verify -> Review -> Verify -> Human."""
    state = phasen_state or (state_ref[-1] if state_ref else None)

    if state is None or getattr(state, "project_dir", None) is None:
        # Ohne State koennen wir keine Gates ausfuehren.
        return pipeline.run_pipeline(
            project_name, aufgabe, state_ref, phasen_state=phasen_state
        )

    pd = state.project_dir
    pn = state.project_name

    # 1. Plan-Gate
    if not _plan_gate(state):
        audit("loop_gate_failed", {"gate": "plan"}, pd, pn)
        return 1
    audit("loop_phase", {"phase": "plan", "status": "ok"}, pd, pn)

    # 2. Start-Check (Baseline vor dem Bauen)
    if not _verify_patches(state):
        audit("loop_gate_failed", {"gate": "pre_build"}, pd, pn)
        return 1
    audit("loop_phase", {"phase": "pre_build", "status": "ok"}, pd, pn)

    # 3. Delegation an den alten Motor (Build + Review)
    #    Hinweis: Hier wird noch der Monolith aufgerufen, aber
    #    die Vor- und Nach-Gates sind jetzt im neuen Loop.
    audit("loop_aktiv", {"project_name": project_name, "aufgabe": aufgabe[:100]}, pd, pn)
    audit("loop_fallback", {"reason": "phase3_monolith_delegation"}, pd, pn)
    
    rc = pipeline.run_pipeline(
        project_name, aufgabe, state_ref, phasen_state=phasen_state
    )

    # 4. Post-Build / Post-Review Check (Baseline nach dem Bauen)
    if not _verify_patches(state):
        audit("loop_gate_failed", {"gate": "post_build"}, pd, pn)
        return rc or 1  # rc vom Motor weitergeben, aber Fehler markieren
    
    audit("loop_phase", {"phase": "post_build", "status": "ok"}, pd, pn)
    audit("loop_erfolg", {"project_name": project_name}, pd, pn)

    return rc
