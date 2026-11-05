"""OP-165: contract_check-Stage + state_inventory --changed."""
from __future__ import annotations

import sys

sys.path.insert(0, "/opt/werkstatt")
sys.path.insert(0, "/opt/werkstatt/tools")

import state_inventory


def test_ghost_in_datei_failt(tmp_path, monkeypatch):
    """Prueft, dass ghosts_in_files Ghost-Zugriffe erkennt.

    Nach OP-141-Vorarbeit (2026-11-05) ist BASELINE_GEISTER leer
    (alle ehemaligen Ghosts deklariert). Wir setzen temporaer ein
    Fake-Ghost-Feld per monkeypatch, um den Mechanismus zu testen.
    """
    monkeypatch.setattr(
        state_inventory, "BASELINE_GEISTER",
        frozenset({"fake_ghost_feld"}),
    )
    py = tmp_path / "ghosty.py"
    py.write_text(
        "from werkstatt.state import RunState\n"
        "def f(state: RunState) -> None:\n"
        "    _ = state.fake_ghost_feld\n",
        encoding="utf-8",
    )
    treffer = state_inventory.ghosts_in_files([str(py)])
    assert "fake_ghost_feld" in treffer


def test_datei_ohne_ghost_ok(tmp_path):
    py = tmp_path / "sauber.py"
    py.write_text(
        "from werkstatt.state import RunState\n"
        "def f(state: RunState) -> None:\n"
        "    _ = state.aufgabe\n",
        encoding="utf-8",
    )
    assert state_inventory.ghosts_in_files([str(py)]) == []
