"""Zentrale RunState-Factory fuer Spec-Tests.

Ziel (OP-173): Tests bauen RunState ueber mk_state(**overrides).
Damit ist garantiert:
- alle Pflichtfelder gesetzt (kein AttributeError)
- neue RunState-Felder erben automatisch den Default
- Tests sagen was sie testen, nicht wie sie es bauen
- Tippfehler in Feldnamen failen sofort (fail-loud)

Spec-Vertrag: mk_state() liefert minimalen, aber vollstaendigen
RunState. Tests ueberschreiben nur, was sie explizit testen.
"""
from __future__ import annotations

from pathlib import Path

from werkstatt.state import RunState


def mk_state(**overrides) -> RunState:
    """Baut minimalen RunState mit allen Pflichtfeldern.

    Ueberschreibbar per kwargs. Alle nicht-ueberschriebenen Felder
    haben ihre RunState-Defaults (siehe werkstatt/state.py).

    Fail-loud: unbekannter kwargs-Name -> AttributeError.
    Damit ist ein Tippfehler im Test sofort sichtbar.
    """
    state = RunState(
        project_dir=overrides.pop("project_dir", Path("/tmp/test")),
        project_name=overrides.pop("project_name", "test"),
    )
    for k, v in overrides.items():
        if not hasattr(state, k):
            raise AttributeError(
                f"mk_state: unbekanntes Feld {k!r}. "
                f"Neue Felder muessen in RunState deklariert sein."
            )
        setattr(state, k, v)
    return state


def coordinator_decision_for_task(phase_state, state: RunState) -> dict:
    """Build the persisted action envelope used by the production dispatcher."""
    from werkstatt.checkpoint_coordinator import choose_task_checkpoint_action

    decision = choose_task_checkpoint_action(
        phase_state, phase_state.get_next_task(), state=state,
    )
    action_by_decision = {
        "execute_planned_task": "execute_task_checkpoint",
        "verify_task_checkpoint": "verify_task_checkpoint",
        "review_task_checkpoint": "review_task_checkpoint",
        "complete_task_checkpoint": "complete_task_checkpoint",
        "recover_verify_failure_checkpoint": "recover_verify_failure_checkpoint",
        "reject_stale_verify_failure_checkpoint": "reject_stale_verify_failure_checkpoint",
        "resolve_blocked_graph": "resolve_task_graph",
        "replan_unassigned_criteria": "replan_unassigned_criteria",
        "replan_failed_criteria": "replan_failed_criteria",
        "run_phase_end_verify": "phase_end_verify",
    }
    return {
        **decision,
        "coordinator_action": action_by_decision.get(
            str(decision.get("decision")), "reject_checkpoint",
        ),
    }
