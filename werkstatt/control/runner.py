"""Runner: dispatcht Kontrollen ueber die Registry."""
from __future__ import annotations

from typing import Any

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
