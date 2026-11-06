"""Runner: dispatcht Kontrollen ueber die Registry."""
from __future__ import annotations

from typing import Any

from werkstatt.control.phases import Phase
from werkstatt.control.registry import CONTROL_REGISTRY


def run_control(name: str, ctx: Any) -> Any:
    """Fuehrt eine Kontrolle aus.

    Args:
        name: Registry-Name der Kontrolle.
        ctx: Kontext (typischerweise RunState).

    Returns:
        Rueckgabewert der Control.fn.

    Raises:
        KeyError: wenn name nicht in Registry.
    """
    if name not in CONTROL_REGISTRY:
        raise KeyError(
            f"Kontrolle {name!r} nicht in Registry. "
            f"Verfuegbar: {sorted(CONTROL_REGISTRY)[:5]}…"
        )
    return CONTROL_REGISTRY[name].fn(ctx)


def run_phase(
    phase: Phase,
    ctx: Any,
    *,
    stop_on_hard: bool = True,
) -> dict[str, Any]:
    """Fuehrt alle Kontrollen einer Phase aus, sortiert nach prioritaet.

    Args:
        phase: Loop-Phase.
        ctx: Kontext.
        stop_on_hard: True = erste harte Fail beendet Phase.
            False = alle laufen, Ergebnis sammelt alle Fails.

    Returns:
        dict mit:
            "ok": bool — alle hart-Kontrollen bestanden.
            "ergebnisse": {name: rueckgabe}.
            "fehler": [name, ...] — Kontrollen mit falsy Rueckgabe.
    """
    ergebnisse: dict[str, Any] = {}
    fehler: list[str] = []
    for ctrl in sorted(CONTROL_REGISTRY.values(), key=lambda c: c.prioritaet):
        if ctrl.phase != phase:
            continue
        try:
            res = ctrl.fn(ctx)
        except Exception as exc:
            ergebnisse[ctrl.name] = f"EXCEPTION: {exc!r}"
            fehler.append(ctrl.name)
            if ctrl.hart and stop_on_hard:
                return {"ok": False, "ergebnisse": ergebnisse, "fehler": fehler}
            continue
        ergebnisse[ctrl.name] = res
        if not res:
            fehler.append(ctrl.name)
            if ctrl.hart and stop_on_hard:
                return {"ok": False, "ergebnisse": ergebnisse, "fehler": fehler}
    return {"ok": not fehler, "ergebnisse": ergebnisse, "fehler": fehler}
