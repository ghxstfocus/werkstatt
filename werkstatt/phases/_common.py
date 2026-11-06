"""Gemeinsame Lazy-Stubs + Helper fuer phases/* (OP-139 Phase 2a).

Alle werkstatt.loop-Stubs importieren lazy (innerhalb der Funktion),
um Zirkularitaet beim Modul-Load zu vermeiden. Kein direkter
from-import von werkstatt.loop auf Modul-Ebene.

extract_audit_bug_summary + RunState werden direkt importiert:
- werkstatt.reviewer importiert nicht werkstatt.phases (kein Zirkel)
- werkstatt.state importiert nicht werkstatt.phases (kein Zirkel)
"""
from __future__ import annotations

from werkstatt.reviewer import extract_audit_bug_summary
from werkstatt.state import RunState


def audit(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop.audit."""
    from werkstatt.loop import audit as _orig
    return _orig(*args, **kwargs)


def _apply_one_patch(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop._apply_one_patch."""
    from werkstatt.loop import _apply_one_patch as _orig
    return _orig(*args, **kwargs)


def _call_hook(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop._call_hook."""
    from werkstatt.loop import _call_hook as _orig
    return _orig(*args, **kwargs)


def _delete_ziel_erlaubt(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop._delete_ziel_erlaubt."""
    from werkstatt.loop import _delete_ziel_erlaubt as _orig
    return _orig(*args, **kwargs)


def _extract_files_from_tasks(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop._extract_files_from_tasks."""
    from werkstatt.loop import _extract_files_from_tasks as _orig
    return _orig(*args, **kwargs)


def _get_git_diff_for_hook(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop._get_git_diff_for_hook."""
    from werkstatt.loop import _get_git_diff_for_hook as _orig
    return _orig(*args, **kwargs)


def _human_gate(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop._human_gate."""
    from werkstatt.loop import _human_gate as _orig
    return _orig(*args, **kwargs)


def _human_gate_plan(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop._human_gate_plan."""
    from werkstatt.loop import _human_gate_plan as _orig
    return _orig(*args, **kwargs)


def _patches_wirklich_angewendet(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop._patches_wirklich_angewendet."""
    from werkstatt.loop import _patches_wirklich_angewendet as _orig
    return _orig(*args, **kwargs)


def _phase_end_reflection(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop._phase_end_reflection."""
    from werkstatt.loop import _phase_end_reflection as _orig
    return _orig(*args, **kwargs)


def _plan_gate(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop._plan_gate."""
    from werkstatt.loop import _plan_gate as _orig
    return _orig(*args, **kwargs)


def _pruefe_prior_failed_dependency(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop._pruefe_prior_failed_dependency."""
    from werkstatt.loop import _pruefe_prior_failed_dependency as _orig
    return _orig(*args, **kwargs)


def _reflection_loop(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop._reflection_loop."""
    from werkstatt.loop import _reflection_loop as _orig
    return _orig(*args, **kwargs)


def _ruff_fix_changed(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop._ruff_fix_changed."""
    from werkstatt.loop import _ruff_fix_changed as _orig
    return _orig(*args, **kwargs)


def _run_with_progress(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop._run_with_progress."""
    from werkstatt.loop import _run_with_progress as _orig
    return _orig(*args, **kwargs)


def _split_task_on_demand(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop._split_task_on_demand."""
    from werkstatt.loop import _split_task_on_demand as _orig
    return _orig(*args, **kwargs)


def _task_ende(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop._task_ende."""
    from werkstatt.loop import _task_ende as _orig
    return _orig(*args, **kwargs)


def _verify_patches(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop._verify_patches."""
    from werkstatt.loop import _verify_patches as _orig
    return _orig(*args, **kwargs)


def _verify_patches_soft(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop._verify_patches_soft."""
    from werkstatt.loop import _verify_patches_soft as _orig
    return _orig(*args, **kwargs)


def _with_spinner(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop._with_spinner."""
    from werkstatt.loop import _with_spinner as _orig
    return _orig(*args, **kwargs)


def run_builder(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop.run_builder."""
    from werkstatt.loop import run_builder as _orig
    return _orig(*args, **kwargs)


def run_explorer(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop.run_explorer."""
    from werkstatt.loop import run_explorer as _orig
    return _orig(*args, **kwargs)


def _validate_contract_safe(
    von: str, zu: str, state, pd, pn,
) -> bool:
    """OP-136a: Contract-Validierung mit Audit-Fallback.

    Ruft state_contracts.validate_transition. Bei ContractViolation:
    schreibt audit("state_contract_violation") und liefert False
    (fail-loud, der Aufrufer entscheidet ueber den Loop-Abbruch).

    Unbekannte Uebergaenge (nicht in TRANSITIONS) sind Noop -> True.
    """
    from werkstatt.state_contracts import ContractViolation, validate_transition
    try:
        validate_transition(von, zu, state)
        return True
    except ContractViolation as _cv:
        _transition = getattr(_cv, "transition", f"{von}->{zu}")
        _felder = getattr(_cv, "felder", [str(_cv)[:200]])
        audit(
            "state_contract_violation",
            {"transition": _transition, "felder": list(_felder)},
            pd, pn,
        )
        return False


def run_planner(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop.run_planner."""
    from werkstatt.loop import run_planner as _orig
    return _orig(*args, **kwargs)


def run_reviewer(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop.run_reviewer."""
    from werkstatt.loop import run_reviewer as _orig
    return _orig(*args, **kwargs)


def _reviewer_rejected_payload(task_id: str, reviewer_result: dict) -> dict:
    """Baut das Payload fuer loop_reviewer_rejected (additiv)."""
    if not isinstance(reviewer_result, dict):
        reviewer_result = {}
    return {
        "task_id": task_id,
        "bugs": extract_audit_bug_summary(
            reviewer_result.get("bugs") or []
        ),
    }


def _gate_failed_payload(
    gate: str, fehler: list, phase: str | None = None,
) -> dict:
    """Baut das Payload fuer loop_gate_failed (additiv)."""
    payload = {
        "gate": str(gate),
        "fehler": [str(f) for f in (fehler or [])],
    }
    if phase is not None:
        payload["phase"] = phase
    return payload


def _normalize_tasks(raw_tasks):
    """Normalisiert heterogene Task-Liste (dicts + strings) fuer PhaseState."""
    out = []
    for i, t in enumerate(raw_tasks, 1):
        if isinstance(t, dict):
            out.append(t)
        else:
            out.append({"id": f"t{i}", "name": str(t)})
    return out


def _reset_task_state(state: RunState) -> None:
    """OP-166: Setzt per-Task-State zurueck vor jedem Task.

    Loop-Test-4 (2026-11-05): t7-Reflection sah 5 Runden die
    gleichen 2 Fehler (aus t2/gates.py), konnte sie aber nicht
    loesen — Zieldatei t7 war tests/test_gates.py. 0 Patches pro
    Runde, 5 Runden bis Erschoepfung.

    Reset nur bei Task-Start. Innerhalb einer Task bleiben
    Fehler kumulativ (K50-Bug-C in reflection.py:394-403),
    damit Reflection-Runden zusammenhaengen.

    Zusaetzlich `reviewer_bugs` (gleicher Leak-Pfad: builder.py:725
    liest reviewer_bugs vor dem ersten Reviewer-Call eines Tasks).
    """
    try:
        state.last_verify_errors = []
    except (AttributeError, TypeError):
        pass
    try:
        state.reviewer_bugs = []
    except (AttributeError, TypeError):
        pass


def _hat_human_review_tasks(phase_state) -> bool:
    """OP-060b: True, wenn mind. ein Task den Status human_review hat."""
    if phase_state is None:
        return False
    try:
        _tasks = phase_state.data.get("tasks") or []
    except Exception:  # noqa: BLE001
        return False
    return any(
        isinstance(t, dict) and (
            t.get("status") == "human_review"
            or t.get("verdict") == "vetoed"
        )
        for t in _tasks
    )
