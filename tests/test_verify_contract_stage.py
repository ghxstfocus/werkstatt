"""OP-165: contract_check-Stage + state_inventory --changed."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, "/opt/werkstatt")
sys.path.insert(0, "/opt/werkstatt/tools")
import state_inventory


def test_ghost_in_datei_failt(tmp_path):
    _feld = sorted(state_inventory.BASELINE_GEISTER)[0]
    py = tmp_path / "ghosty.py"
    py.write_text(
        "from werkstatt.state import RunState\n"
        "def f(state: RunState) -> None:\n"
        f"    _ = state.{_feld}\n",
        encoding="utf-8",
    )
    treffer = state_inventory.ghosts_in_files([str(py)])
    assert _feld in treffer


def test_datei_ohne_ghost_ok(tmp_path):
    py = tmp_path / "sauber.py"
    py.write_text(
        "from werkstatt.state import RunState\n"
        "def f(state: RunState) -> None:\n"
        "    _ = state.aufgabe\n",
        encoding="utf-8",
    )
    assert state_inventory.ghosts_in_files([str(py)]) == []
