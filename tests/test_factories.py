"""Spec: mk_state liefert vollstaendigen RunState (OP-173 P1).

Drei Spec-Vertraege:
1. mk_state() ohne Argumente: RunState vollstaendig
2. mk_state(**overrides): gezielte Felder ueberschrieben
3. mk_state(unbekannt=x): fail-loud, nicht still ignorieren
"""
import sys
from pathlib import Path

_here = Path(__file__).parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

import pytest
from factories import mk_state

from werkstatt.state import RunState


def test_mk_state_ohne_argumente_vollstaendig():
    """Spec: mk_state() liefert RunState mit allen deklarierten Feldern.

    Vertrag: Jedes Feld in RunState.__dataclass_fields__ ist
    direkt per state.X erreichbar. Kein AttributeError.
    """
    state = mk_state()

    assert isinstance(state, RunState)
    assert state.project_dir == Path("/tmp/test")
    assert state.project_name == "test"
    assert state.block_id == ""
    assert state.aufgabe == ""
    assert state.api_key == ""
    assert state.docs == {}

    # Spec-Kern: jedes deklarierte Feld direkt erreichbar
    for feld in RunState.__dataclass_fields__:
        getattr(state, feld)  # wirft AttributeError wenn fehlt


def test_mk_state_overrides_gezielt():
    """Spec: mk_state(**kwargs) ueberschreibt genau die genannten Felder.

    Nicht-ueberschriebene Felder behalten ihre Defaults.
    """
    state = mk_state(aufgabe="Test-Aufgabe", api_key="sk-test")

    assert state.aufgabe == "Test-Aufgabe"
    assert state.api_key == "sk-test"
    # Unberuehrt:
    assert state.block_id == ""
    assert state.project_dir == Path("/tmp/test")


def test_mk_state_unbekanntes_feld_failt_sofort():
    """Spec: mk_state ist fail-loud bei Tippfehlern im Feldnamen.

    Vertrag: Tests koennen sich nicht versehentlich auf ein
    nicht-existentes Feld verlassen (z.B. "apikey" statt "api_key").
    """
    with pytest.raises(AttributeError, match="unbekanntes Feld"):
        mk_state(apikey="tippfehler")
