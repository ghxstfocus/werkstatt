"""CONTROL_REGISTRY — Inventar und Drift-Pruefung der Loop-Kontrollen.

Die Registry dokumentiert Kontrollfunktionen und ihre Quellmodule. Sie
fuehrt keine Ablaufreihenfolge aus; der Checkpoint-Koordinator entscheidet,
welche Aktion im jeweiligen Run faellig ist.

Drift-Check: tools/control_drift.py --check
"""
from __future__ import annotations

from werkstatt import architect_context, gates, reflection, verify
from werkstatt.antipattern import scan_patches
from werkstatt.control.control import Control

CONTROL_REGISTRY: dict[str, Control] = {}


def _reg(ctrl: Control) -> None:
    if ctrl.name in CONTROL_REGISTRY:
        raise ValueError(f"Control-Name doppelt: {ctrl.name!r}")
    CONTROL_REGISTRY[ctrl.name] = ctrl


# ─── VERIFY ─────────────────────────────────────────────────
_reg(Control(
    name="verify_patches",
    fn=verify._verify_patches,
    source="werkstatt.verify._verify_patches",
    description="Harte Verify-Stages (py_compile, ruff, mypy, pytest_changed)",
    hart=True,
))
_reg(Control(
    name="verify_patches_soft",
    fn=verify._verify_patches_soft,
    source="werkstatt.verify._verify_patches_soft",
    description="Weiche Verify-Stages (Warnungen, kein Fail)",
    hart=False,
))

# ─── GATES ──────────────────────────────────────────────────
_reg(Control(
    name="plan_gate",
    fn=gates._plan_gate,
    source="werkstatt.gates._plan_gate",
    description="Deterministischer Plan-Validator und Hook",
    hart=True,
))
_reg(Control(
    name="human_gate_plan",
    fn=gates._human_gate_plan,
    source="werkstatt.gates._human_gate_plan",
    description="Interaktives Plan-Gate (j/n/a + Reject-Reflection)",
    hart=True,
))
_reg(Control(
    name="human_gate",
    fn=gates._human_gate,
    source="werkstatt.gates._human_gate",
    description="Human-Gate fuer Freigabe und Commit",
    hart=True,
))

# ─── REFLECTION ─────────────────────────────────────────────
_reg(Control(
    name="reflection_loop",
    fn=reflection._reflection_loop,
    source="werkstatt.reflection._reflection_loop",
    description="Reflection-Runden mit Circuit-Breaker (OP-089)",
    hart=True,
))
_reg(Control(
    name="phase_end_reflection",
    fn=reflection._phase_end_reflection,
    source="werkstatt.reflection._phase_end_reflection",
    description="Reflection-Recovery anhand von Reviewer-Findings",
    hart=True,
))

# ─── PLANNER-GUARDS ─────────────────────────────────────────
_reg(Control(
    name="preflight_scan",
    fn=verify.preflight_scan,
    source="werkstatt.verify.preflight_scan",
    description="Preflight: ruff/syntax/test/type-Vorfilter",
    hart=False,
))
_reg(Control(
    name="pruefe_migrations_kollision",
    fn=architect_context.migration_collisions,
    source="werkstatt.architect_context.migration_collisions",
    description="Migrations-Kollision im Plan verhindern",
    hart=True,
))

# ─── ANTIPATTERN ────────────────────────────────────────────
_reg(Control(
    name="scan_patches_antipattern",
    fn=scan_patches,
    source="werkstatt.antipattern.scan_patches",
    description="Scanner: # type: ignore, noqa, geschwaechte Assertions",
    hart=True,
))


# ─── Helper (keine Loop-Kontrolle, aber registriert fuer Sichtbarkeit) ─
_reg(Control(
    name="stage_ids",
    fn=verify._stage_ids,
    source="werkstatt.verify._stage_ids",
    description="Liste aller verify.json-Stage-IDs",
    hart=False,
))
_reg(Control(
    name="stage_ist_hart",
    fn=verify._stage_ist_hart,
    source="werkstatt.verify._stage_ist_hart",
    description="Klassifiziert Stage als hart/weich (Prefix + hart-Flag)",
    hart=False,
))


def list_controls() -> list[Control]:
    """Alle Kontrollen alphabetisch fuer Inventar und Drift-Checks."""
    return sorted(CONTROL_REGISTRY.values(), key=lambda control: control.name)
