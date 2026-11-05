"""CONTROL_REGISTRY — Single Source of Truth aller Loop-Kontrollen.

Jede Kontrolle ist ein Eintrag. Bestehender Code wird NICHT umgestellt;
diese Datei dokumentiert nur, was wo existiert. Migration nach
werkstatt.control.* erfolgt schrittweise (Phase 2+).

Drift-Check: tools/control_drift.py --check
"""
from __future__ import annotations

from werkstatt import gates, planner, reflection, verify
from werkstatt.antipattern import scan_patches
from werkstatt.control.control import Control
from werkstatt.control.phases import Phase

CONTROL_REGISTRY: dict[str, Control] = {}


def _reg(ctrl: Control) -> None:
    if ctrl.name in CONTROL_REGISTRY:
        raise ValueError(f"Control-Name doppelt: {ctrl.name!r}")
    CONTROL_REGISTRY[ctrl.name] = ctrl


# ─── VERIFY (post_build, phase_end) ─────────────────────────
_reg(Control(
    name="verify_patches",
    phase=Phase.POST_BUILD,
    fn=verify._verify_patches,
    source="werkstatt.verify._verify_patches",
    description="Harte Verify-Stages (py_compile, ruff, mypy, pytest_changed)",
    hart=True, prioritaet=10,
))
_reg(Control(
    name="verify_patches_soft",
    phase=Phase.POST_BUILD,
    fn=verify._verify_patches_soft,
    source="werkstatt.verify._verify_patches_soft",
    description="Weiche Verify-Stages (Warnungen, kein Fail)",
    hart=False, prioritaet=20,
))

# ─── GATES (plan_gate, human_gate) ──────────────────────────
_reg(Control(
    name="plan_gate",
    phase=Phase.PLAN_GATE,
    fn=gates._plan_gate,
    source="werkstatt.gates._plan_gate",
    description="Deterministischer Plan-Validator (Phasen-Struktur, Hook)",
    hart=True, prioritaet=10,
))
_reg(Control(
    name="human_gate_plan",
    phase=Phase.PLAN_GATE,
    fn=gates._human_gate_plan,
    source="werkstatt.gates._human_gate_plan",
    description="Interaktives Plan-Gate (j/n/a + Reject-Reflection)",
    hart=True, prioritaet=20,
))
_reg(Control(
    name="human_gate",
    phase=Phase.HUMAN_GATE,
    fn=gates._human_gate,
    source="werkstatt.gates._human_gate",
    description="Human-Gate am Phase-Ende (j/n/e + Commit)",
    hart=True, prioritaet=10,
))

# ─── REFLECTION ─────────────────────────────────────────────
_reg(Control(
    name="reflection_loop",
    phase=Phase.REFLECTION,
    fn=reflection._reflection_loop,
    source="werkstatt.reflection._reflection_loop",
    description="Reflection-Runden mit Circuit-Breaker (OP-089)",
    hart=True, prioritaet=10,
))
_reg(Control(
    name="plan_reject_reflection",
    phase=Phase.PLAN_REJECT,
    fn=reflection._plan_reject_reflection,
    source="werkstatt.reflection._plan_reject_reflection",
    description="Planner-Reflection nach Plan-Reject",
    hart=True, prioritaet=10,
))
_reg(Control(
    name="phase_end_reflection",
    phase=Phase.PHASE_END,
    fn=reflection._phase_end_reflection,
    source="werkstatt.reflection._phase_end_reflection",
    description="Phase-End-Reflection (Reviewer-Findings)",
    hart=True, prioritaet=10,
))

# ─── PLANNER-GUARDS (pre_build) ─────────────────────────────
_reg(Control(
    name="preflight_scan",
    phase=Phase.PRE_BUILD,
    fn=planner._preflight_scan,
    source="werkstatt.planner._preflight_scan",
    description="Preflight: ruff/syntax/test/type-Vorfilter",
    hart=False, prioritaet=10,
))
_reg(Control(
    name="pruefe_migrations_kollision",
    phase=Phase.PRE_BUILD,
    fn=planner._pruefe_migrations_kollision,
    source="werkstatt.planner._pruefe_migrations_kollision",
    description="Migrations-Kollision im Plan verhindern",
    hart=True, prioritaet=20,
))

# ─── ANTIPATTERN (task_end, OP-064b) ────────────────────────
_reg(Control(
    name="scan_patches_antipattern",
    phase=Phase.TASK_END,
    fn=scan_patches,
    source="werkstatt.antipattern.scan_patches",
    description="Scanner: # type: ignore, noqa, geschwaechte Assertions",
    hart=True, prioritaet=10,
))


# ─── Helper (keine Loop-Kontrolle, aber registriert fuer Sichtbarkeit) ─
_reg(Control(
    name="stage_ids",
    phase=Phase.PHASE_END,
    fn=verify._stage_ids,
    source="werkstatt.verify._stage_ids",
    description="Liste aller verify.json-Stage-IDs",
    hart=False, prioritaet=1,
))
_reg(Control(
    name="stage_ist_hart",
    phase=Phase.PHASE_END,
    fn=verify._stage_ist_hart,
    source="werkstatt.verify._stage_ist_hart",
    description="Klassifiziert Stage als hart/weich (Prefix + hart-Flag)",
    hart=False, prioritaet=2,
))


def list_controls(phase: Phase | None = None) -> list[Control]:
    """Alle Kontrollen (optional nach Phase gefiltert)."""
    alle = list(CONTROL_REGISTRY.values())
    if phase is None:
        return sorted(alle, key=lambda c: (c.phase.value, c.prioritaet))
    return sorted(
        [c for c in alle if c.phase == phase],
        key=lambda c: c.prioritaet,
    )
