"""Checkpoint-Verarbeitung bestaetigter Chat-Folgeauftraege."""
from __future__ import annotations

from pathlib import Path

from werkstatt import planner, run_followups
from werkstatt.event_store import EventStore
from werkstatt.phase_state import PhaseState
from werkstatt.state import RunState


def _setup(tmp_path: Path) -> tuple[RunState, PhaseState, EventStore]:
    state = RunState(
        project_dir=tmp_path,
        project_name="demo",
        aufgabe="Hauptziel",
        tasks=[{"id": "t1", "name": "Haupttask", "dependencies": []}],
        tests=[],
        akzeptanzkriterien=["Hauptkriterium"],
    )
    phase = PhaseState("demo", base_dir=tmp_path / "phase")
    phase.init_new(
        "Hauptziel",
        state.tasks,
        akzeptanzkriterien=state.akzeptanzkriterien,
    )
    store = EventStore(tmp_path / "events.db")
    store.create_run_record("demo", "run-1", "Hauptziel")
    record = store.get_run_record("demo", "run-1")
    assert record is not None
    checkpoint = dict(record["checkpoint"])
    checkpoint["chat_followup_requests"] = [{
        "proposal_id": "proposal-1",
        "session_id": "session-1",
        "request": "Fuege einen unabhaengigen Dokumentationstest hinzu",
        "status": "received",
    }]
    store.update_run_checkpoint(
        "demo", "run-1", checkpoint,
        expected_version=record["checkpoint_version"],
    )
    return state, phase, store


def _patch_planning(monkeypatch, *, approved: bool = True) -> None:
    def plan(addition: RunState) -> bool:
        addition.tasks = [{
            "id": "t1",
            "name": "Folgeauftrag",
            "description": "Dokumentationstest ergaenzen",
            "task_files": ["docs/STATUS.md"],
            "dependencies": [],
            "criterion_refs": ["AC1"],
        }]
        addition.tests = ["pytest -q tests/test_doc.py"]
        addition.akzeptanzkriterien = ["Dokumentationstest ist vorhanden"]
        return True

    monkeypatch.setattr(planner, "run_planner", plan)
    monkeypatch.setattr("werkstatt.gates._plan_gate", lambda _state: True)

    def human_gate(candidate: RunState, *, kontext: str) -> int:
        assert kontext == "chat_followup"
        if not approved:
            candidate.last_reject_kind = "plan"
            return 1
        return 0

    monkeypatch.setattr("werkstatt.gates._human_gate_plan", human_gate)
    monkeypatch.setattr("werkstatt.audit.audit", lambda *_args, **_kwargs: True)


def test_reconcile_approved_followup_appends_once_and_reports_chat(tmp_path, monkeypatch):
    state, phase, store = _setup(tmp_path)
    state.scout_auftrag = {"auftrag_prosa": "alter Scout-Bericht"}
    state.scout_api_auszug = {"old.py": ["old_symbol"]}
    state.explorer_context = {"key_files": ["old.py"]}
    state.explorer_findings = {"old": True}

    def plan(addition: RunState) -> bool:
        assert addition.scout_auftrag == {}
        assert addition.scout_api_auszug == {}
        assert addition.explorer_context == {}
        assert addition.explorer_findings == {}
        addition.tasks = [{
            "id": "t1", "name": "Folgeauftrag",
            "description": "Dokumentationstest ergaenzen",
            "task_files": ["docs/STATUS.md"],
            "dependencies": [], "criterion_refs": ["AC1"],
            "phase_id": "p1",
        }]
        addition.tests = ["pytest -q tests/test_doc.py"]
        addition.akzeptanzkriterien = ["Dokumentationstest ist vorhanden"]
        addition.phasen = [{"id": "p1", "titel": "Pruefung", "tasks": ["t1"]}]
        return True

    monkeypatch.setattr(planner, "run_planner", plan)
    monkeypatch.setattr("werkstatt.gates._plan_gate", lambda _state: True)
    monkeypatch.setattr("werkstatt.gates._human_gate_plan", lambda *_a, **_kw: 0)
    monkeypatch.setattr("werkstatt.audit.audit", lambda *_args, **_kwargs: True)
    dispositions = []
    monkeypatch.setattr(
        run_followups,
        "_append_chat_disposition",
        lambda item, project, run_id, status, detail, **kwargs: dispositions.append(
            (status, kwargs.get("task_ids", [])),
        ),
    )

    assert run_followups.reconcile_chat_followups(
        state, phase, store, "demo", "run-1",
    ) is True
    assert [task["id"] for task in phase.data["tasks"]] == [
        "t1", "fu_22e971ef18_t1",
    ]
    assert phase.data["tasks"][1]["criterion_refs"] == ["AC2"]
    assert phase.data["tasks"][1]["phase_id"] == "fu_22e971ef18_phase_p1"
    assert state.phasen[0]["tasks"] == ["fu_22e971ef18_t1"]
    assert state.phasen[0]["id"] == "fu_22e971ef18_phase_p1"
    assert state.akzeptanzkriterien == [
        "Hauptkriterium", "Dokumentationstest ist vorhanden",
    ]
    assert phase.data["phasen"] == state.phasen
    assert dispositions == [("applied", ["fu_22e971ef18_t1"])]

    # A replay sees the durable applied status and does not invoke planning again.
    state.tasks = [{"id": "t1", "name": "Haupttask"}]
    state.akzeptanzkriterien = ["Hauptkriterium"]
    state.phasen = []
    monkeypatch.setattr(
        planner, "run_planner",
        lambda _state: (_ for _ in ()).throw(AssertionError("replanned")),
    )
    assert run_followups.reconcile_chat_followups(
        state, phase, store, "demo", "run-1",
    ) is False
    assert len(phase.data["tasks"]) == 2
    assert [task["id"] for task in state.tasks] == [
        "t1", "fu_22e971ef18_t1",
    ]
    assert state.akzeptanzkriterien == [
        "Hauptkriterium", "Dokumentationstest ist vorhanden",
    ]
    assert state.phasen == phase.data["phasen"]
    assert dispositions[-1][0] == "applied"


def test_reconcile_rejected_followup_leaves_main_graph_unchanged(tmp_path, monkeypatch):
    state, phase, store = _setup(tmp_path)
    _patch_planning(monkeypatch, approved=False)
    dispositions = []
    monkeypatch.setattr(
        run_followups,
        "_append_chat_disposition",
        lambda item, project, run_id, status, detail, **kwargs: dispositions.append(status),
    )

    assert run_followups.reconcile_chat_followups(
        state, phase, store, "demo", "run-1",
    ) is False
    assert [task["id"] for task in phase.data["tasks"]] == ["t1"]
    record = store.get_run_record("demo", "run-1")
    assert record is not None
    request = record["checkpoint"]["chat_followup_requests"][0]
    assert request["status"] == "rejected"
    assert dispositions == ["rejected"]


def test_plan_gate_timeout_keeps_followup_pending(tmp_path, monkeypatch):
    state, phase, store = _setup(tmp_path)
    _patch_planning(monkeypatch)
    dispositions = []

    def timed_out(candidate: RunState, *, kontext: str) -> int:
        assert kontext == "chat_followup"
        candidate.gate_timed_out = True
        return 2

    monkeypatch.setattr("werkstatt.gates._human_gate_plan", timed_out)
    monkeypatch.setattr(
        run_followups,
        "_append_chat_disposition",
        lambda _item, _project, _run, status, _detail, **_kwargs: dispositions.append(status),
    )

    assert run_followups.reconcile_chat_followups(
        state, phase, store, "demo", "run-1",
    ) is False
    record = store.get_run_record("demo", "run-1")
    assert record is not None
    assert record["checkpoint"]["chat_followup_requests"][0]["status"] == "received"
    assert len(phase.data["tasks"]) == 1
    assert phase.data["tasks"][0]["id"] == "t1"
    assert dispositions == ["pending"]


def test_planner_failure_keeps_confirmed_followup_pending_for_resume(tmp_path, monkeypatch):
    state, phase, store = _setup(tmp_path)
    monkeypatch.setattr(planner, "run_planner", lambda _state: False)
    monkeypatch.setattr("werkstatt.audit.audit", lambda *_args, **_kwargs: True)

    try:
        run_followups.reconcile_chat_followups(
            state, phase, store, "demo", "run-1",
        )
    except run_followups.FollowupReconciliationError:
        pass
    else:
        raise AssertionError("Planner-Ausfall muss als Retry-Fehler behandelt werden")

    record = store.get_run_record("demo", "run-1")
    assert record is not None
    assert record["checkpoint"]["chat_followup_requests"][0]["status"] == "received"
    assert [task["id"] for task in phase.data["tasks"]] == ["t1"]
