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


# =====================================================================
# OP-176: setattr-Check im --changed-Pfad verdrahtet
# =====================================================================

def test_changed_pfad_findet_setattr_auf_unbekanntes_feld(tmp_path):
    """Spec: --changed ruft _pruefe_setattr_aufrufe und gibt rc=1.

    Anlass: OP-176-AK verlangt fail-closed. Ohne dieses Wiring
    laeuft die Pruefung nie — tools/contract_check.py wird dann
    von keiner verify.json-Stage gerufen.
    """
    import subprocess

    probe = tmp_path / "probe.py"
    probe.write_text(
        "def f(state):\n"
        "    setattr(state, \"gibt_es_nicht\", True)\n"
    )
    r = subprocess.run(
        ["python3", "tools/state_inventory.py", "--changed", str(probe)],
        capture_output=True, text=True, check=False,
    )
    assert r.returncode == 1, (
        f"rc={r.returncode}; stdout={r.stdout!r}; stderr={r.stderr!r}"
    )
    assert "gibt_es_nicht" in r.stdout


def test_changed_pfad_laesst_gueltiges_setattr_durch(tmp_path):
    """Spec: --changed gibt rc=0 bei deklariertem RunState-Feld."""
    import subprocess

    from werkstatt.state import RunState
    _feld = next(iter(RunState.__dataclass_fields__.keys()))

    probe = tmp_path / "probe.py"
    probe.write_text(
        "def f(state):\n"
        f"    setattr(state, \"{_feld}\", True)\n"
    )
    r = subprocess.run(
        ["python3", "tools/state_inventory.py", "--changed", str(probe)],
        capture_output=True, text=True, check=False,
    )
    assert r.returncode == 0, (
        f"rc={r.returncode}; stdout={r.stdout!r}; stderr={r.stderr!r}"
    )
