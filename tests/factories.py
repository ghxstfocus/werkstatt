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
