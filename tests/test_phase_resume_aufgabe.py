"""OP-381k: Ein anderer Auftrag darf keinen alten PhaseState fortsetzen."""
from __future__ import annotations

from types import SimpleNamespace

from werkstatt.phase_state import PhaseState
from werkstatt.phases import plan as plan_phase


def test_neuer_freigegebener_plan_ersetzt_alte_tasks(
    monkeypatch, tmp_path,
) -> None:
    phase_state = PhaseState("demo", base_dir=tmp_path)
    phase_state.init_new(
        "alter Auftrag",
        [{"id": "old_task", "name": "Task des alten Auftrags"}],
    )
    state = SimpleNamespace(
        project_dir=tmp_path,
        project_name="demo",
        tasks=[],
        tests=[],
        akzeptanzkriterien=[],
        phasen=[],
        preflight_fehler=[{"klasse": "baseline"}],
        architect_prosa="",
        auftrag_bereits_erfuellt=False,
    )

    plan_gate_results = iter((False, True))
    monkeypatch.setattr(
        plan_phase, "_plan_gate", lambda _state: next(plan_gate_results),
    )

    def planner(neuer_state):
        neuer_state.tasks = [
            {"id": "new_task", "name": "Task des neuen Auftrags"},
        ]
        neuer_state.tests = ["pytest -q"]
        neuer_state.akzeptanzkriterien = ["Neuer Auftrag ist erfuellt"]
        neuer_state.phasen = []
        neuer_state.architect_prosa = ""
        neuer_state.auftrag_bereits_erfuellt = False
        return True

    monkeypatch.setattr(plan_phase, "run_planner", planner)
    monkeypatch.setattr(
        plan_phase, "_validate_contract_safe", lambda *_args: True,
    )
    monkeypatch.setattr(
        plan_phase, "_human_gate_plan", lambda *_args, **_kwargs: 0,
    )
    monkeypatch.setattr(
        plan_phase, "_verify_patches", lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(plan_phase, "audit", lambda *_args: None)
    monkeypatch.setattr(plan_phase, "group_start", lambda *_args: None)
    monkeypatch.setattr(plan_phase, "group_end", lambda *_args: None)
    monkeypatch.setattr(
        plan_phase, "step", lambda *_args, **_kwargs: None,
    )

    rc, done = plan_phase._phase_plan_and_preflight(
        state, "neuer Auftrag", "demo", phase_state,
    )

    assert (rc, done) == (0, False)
    assert phase_state.data["aufgabe"] == "neuer Auftrag"
    assert [task["id"] for task in phase_state.data["tasks"]] == ["new_task"]
    assert phase_state.get_next_task()["id"] == "new_task"
