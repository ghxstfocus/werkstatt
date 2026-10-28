"""K20c: Plan-Gate bricht bei wiederholtem Leer-Input ab."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from werkstatt.loop import _human_gate_plan
from werkstatt.state import RunState


def _mk_state(tmp_path: Path) -> RunState:
    # minimale RunState mit project_dir
    s = RunState.__new__(RunState)
    s.project_dir = tmp_path  # type: ignore[attr-defined]
    s.project_name = "test"  # type: ignore[attr-defined]
    s.phasen = []  # type: ignore[attr-defined]
    s.tasks = []  # type: ignore[attr-defined]
    s.tests = []  # type: ignore[attr-defined]
    s.akzeptanzkriterien = []  # type: ignore[attr-defined]
    return s


def test_leerer_input_drei_mal_bricht_ab(monkeypatch, tmp_path: Path):
    """K20c: 3x '' -> return 1, kein endlos-Loop."""
    monkeypatch.delenv("WERKSTATT_IN_TEST", raising=False)
    s = _mk_state(tmp_path)
    with patch("builtins.input", side_effect=["", "", "", "", ""]) as m:
        rc = _human_gate_plan(s, auto_approve=False)
    assert rc == 1
    # Nach 3 leeren Versuchen Abbruch -- nicht alle 5 verbraucht.
    assert m.call_count == 3


def test_j_nach_zwei_leeren_geht_durch(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("WERKSTATT_IN_TEST", raising=False)
    s = _mk_state(tmp_path)
    with patch("builtins.input", side_effect=["", "", "j"]):
        rc = _human_gate_plan(s, auto_approve=False)
    assert rc == 0


def test_n_alleine_lehnt_ab(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("WERKSTATT_IN_TEST", raising=False)
    s = _mk_state(tmp_path)
    with patch("builtins.input", return_value="n"):
        rc = _human_gate_plan(s, auto_approve=False)
    assert rc == 1
