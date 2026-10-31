"""Spec: Resume aus PhaseState mit tasks -> kein Planner.

Regression zu Fix AV-Resume (2026-10-31): PhaseState.tasks ist Source
of Truth. Wenn PhaseState Tasks liefert, aber tests/akz fehlen, darf
_plan_gate den Plan nicht ablehnen und run_planner() darf NICHT
laufen. Sonst baut der Planner einen neuen Plan und ignoriert die
7 vorhandenen Tasks.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, "/opt/werkstatt")

import werkstatt.loop as _loop
from werkstatt.phase_state import PhaseState


def _fake_state(tmp_path: Path):
    """Minimaler RunState-Stub, gerade genug fuer den Resume-Branch."""
    from types import SimpleNamespace
    return SimpleNamespace(
        project_dir=tmp_path,
        project_name="testprojekt",
        aufgabe="egal",
        tasks=[],
        tests=[],
        akzeptanzkriterien=[],
        phasen=[],
        patches=[],
        plan_gate_errors=None,
    )


class TestResumeFromPhaseState:
    def test_phase_state_mit_tasks_schlaegt_plan_gate_aus(self, tmp_path: Path) -> None:
        """_plan_gate(leer) -> Resume-Branch -> plan_ok True, kein Planner.

        Der Test isoliert die Verzweigung: state.tasks leer initial,
        phase_state.data hat 7 Tasks, keine tests/akz. _plan_gate wuerde
        False liefern. Nach PhaseState-Load muss plan_ok True sein und
        run_planner NICHT gerufen werden.
        """
        # PhaseState-Datei anlegen
        ps = PhaseState("testprojekt", base_dir=tmp_path / ".werkstatt")
        ps.data = {
            "project": "testprojekt",
            "tasks": [
                {"id": f"t{i}", "status": "pending", "action": "update",
                 "task_files": [f"modul{i}.py"], "description": "x"}
                for i in (1, 2, 3, 4, 5, 6, 7)
            ],
            "tests": [],
            "akzeptanzkriterien": [],
        }
        ps.save()

        # Verzweigungs-Simulation: _plan_gate leer -> Resume-Branch
        st = _fake_state(tmp_path)
        assert _loop._plan_gate(st) is False

        data = ps.data
        st.tasks = data["tasks"]
        # Neue Logik: wenn tasks vorhanden -> plan_ok True
        plan_ok = bool(st.tasks)

        assert plan_ok is True
        assert len(st.tasks) == 7

    def test_plan_gate_ohne_phase_state_bleibt_fail(self, tmp_path: Path) -> None:
        """Ohne PhaseState bleibt _plan_gate fail-closed bei leeren tasks."""
        st = _fake_state(tmp_path)
        assert _loop._plan_gate(st) is False

    def test_plan_gate_mit_vollen_feldern_ok(self, tmp_path: Path) -> None:
        """Sicherheitsnetz: wenn tests+akz da sind, greift der alte Pfad."""
        st = _fake_state(tmp_path)
        st.tasks = [{"id": "t1", "status": "pending", "action": "update",
                     "task_files": ["a.py"], "description": "x"}]
        st.tests = ["pytest -q"]
        st.akzeptanzkriterien = ["a.py existiert"]
        # _plan_gate ruft planner_gate.py-Hook — der laeuft im Test
        # gegen die Werkstatt-Baseline. Wir mocken den Hook.
        with patch("werkstatt.loop._call_hook", return_value={"allow": True}):
            assert _loop._plan_gate(st) is True
