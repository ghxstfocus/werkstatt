"""Checkpoint-Verarbeitung bestaetigter Chat-Folgeauftraege."""
from __future__ import annotations

from pathlib import Path

from werkstatt import run_followups
from werkstatt.event_store import EventStore, RunInboxPendingError
from werkstatt.loop import _run_coordinator_action
from werkstatt.phase_state import PhaseState
from werkstatt.run_followups import retain_followup_history
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
    phase.run_id = "run-1"
    phase.data["run_id"] = "run-1"
    phase.bind_approved_plan()
    phase.save()
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


def _patch_gates(monkeypatch, *, approved: bool = True) -> None:
    monkeypatch.setattr("werkstatt.gates._plan_gate", lambda _state: True)

    def human_gate(candidate: RunState, *, kontext: str) -> int:
        assert kontext == "chat_followup"
        if not approved:
            candidate.last_reject_kind = "plan"
            return 1
        return 0

    monkeypatch.setattr("werkstatt.gates._human_gate_plan", human_gate)
    monkeypatch.setattr("werkstatt.audit.audit", lambda *_args, **_kwargs: True)


def test_followup_history_never_drops_unresolved_requests() -> None:
    history = [
        {"proposal_id": f"done-{index}", "status": "applied"}
        for index in range(65)
    ] + [
        {"proposal_id": f"open-{index}", "status": "received"}
        for index in range(60)
    ]
    history.append({"proposal_id": "unknown", "status": "new-state"})

    retained = retain_followup_history(history, resolved_limit=50)

    assert len([item for item in retained if item["status"] == "applied"]) == 50
    assert {
        item["proposal_id"] for item in retained
        if item["status"] == "received"
    } == {f"open-{index}" for index in range(60)}
    assert any(item["proposal_id"] == "unknown" for item in retained)


def test_checkpoint_status_update_keeps_all_pending_followups(tmp_path) -> None:
    _state, _phase, store = _setup(tmp_path)
    record = store.get_run_record("demo", "run-1")
    assert record is not None
    checkpoint = dict(record["checkpoint"])
    checkpoint["chat_followup_requests"] = [
        {"proposal_id": f"done-{index}", "status": "applied"}
        for index in range(65)
    ] + [
        {"proposal_id": f"open-{index}", "status": "received"}
        for index in range(60)
    ]
    store.update_run_checkpoint(
        "demo", "run-1", checkpoint,
        expected_version=record["checkpoint_version"],
    )

    run_followups._append_checkpoint_status(
        store, "demo", "run-1", "open-0", "applied",
    )

    latest = store.get_run_record("demo", "run-1")
    assert latest is not None
    requests = latest["checkpoint"]["chat_followup_requests"]
    assert {
        item["proposal_id"] for item in requests
        if item["status"] == "received"
    } == {f"open-{index}" for index in range(1, 60)}
    assert any(
        item["proposal_id"] == "open-0" and item["status"] == "applied"
        for item in requests
    )


def test_unknown_followup_status_fails_closed(tmp_path) -> None:
    _state, phase, store = _setup(tmp_path)
    record = store.get_run_record("demo", "run-1")
    assert record is not None
    checkpoint = dict(record["checkpoint"])
    checkpoint["chat_followup_requests"] = [{
        "proposal_id": "proposal-future",
        "session_id": "session-1",
        "request": "Do not discard this",
        "status": "future-state",
    }]
    store.update_run_checkpoint(
        "demo", "run-1", checkpoint,
        expected_version=record["checkpoint_version"],
    )

    try:
        run_followups.reconcile_chat_followups(
            _state, phase, store, "demo", "run-1",
        )
    except run_followups.FollowupReconciliationError as exc:
        assert "unbekannten Status" in str(exc)
    else:
        raise AssertionError("Unbekannter Follow-up-Status muss stoppen")


def test_malformed_followup_entry_fails_closed(tmp_path) -> None:
    state, phase, store = _setup(tmp_path)
    record = store.get_run_record("demo", "run-1")
    assert record is not None
    checkpoint = dict(record["checkpoint"])
    checkpoint["chat_followup_requests"] = [None]
    store.update_run_checkpoint(
        "demo", "run-1", checkpoint,
        expected_version=record["checkpoint_version"],
    )

    try:
        run_followups.reconcile_chat_followups(
            state, phase, store, "demo", "run-1",
        )
    except run_followups.FollowupReconciliationError as exc:
        assert "ungueltig" in str(exc)
    else:
        raise AssertionError("Ungueltiger Follow-up-Eintrag muss stoppen")


def _make_role_candidate(state, phase, store) -> str:
    assert run_followups.reconcile_chat_followups(
        state, phase, store, "demo", "run-1",
    ) is False
    record = run_followups.prepare_chat_followup_roles(state, phase)
    assert record is not None
    assert state.aufgabe == "Fuege einen unabhaengigen Dokumentationstest hinzu"
    state.tasks = [{
        "id": "t1", "name": "Folgeauftrag",
        "description": "Dokumentationstest ergaenzen",
        "task_files": ["docs/STATUS.md"],
        "dependencies": [], "criterion_refs": ["AC1"],
        "phase_id": "p1",
    }]
    state.tests = ["pytest -q tests/test_doc.py"]
    state.akzeptanzkriterien = ["Dokumentationstest ist vorhanden"]
    state.phasen = [{"id": "p1", "titel": "Pruefung", "tasks": ["t1"]}]
    return run_followups.store_chat_followup_candidate(
        state, phase, run_id="run-1",
    )


def test_reconcile_prepares_bounded_role_checkpoint_without_planning(tmp_path):
    state, phase, store = _setup(tmp_path)
    state.scout_auftrag = {"auftrag_prosa": "alter Scout-Bericht"}
    state.scout_api_auszug = {"old.py": ["old_symbol"]}
    state.explorer_context = {"key_files": ["old.py"]}
    state.explorer_findings = {"old": True}

    assert run_followups.reconcile_chat_followups(state, phase, store, "demo", "run-1") is False
    ledger = store.get_run_record("demo", "run-1")["checkpoint"]["chat_followup_requests"]
    assert ledger[0]["status"] == "planning"
    assert [task["id"] for task in phase.data["tasks"]] == ["t1"]
    assert state.aufgabe == "Hauptziel"
    record = run_followups.active_chat_followup(phase)
    assert record is not None and record["status"] == "roles_pending"
    state = RunState(project_dir=tmp_path, project_name="demo", aufgabe="Hauptziel")
    loaded = run_followups.prepare_chat_followup_roles(state, phase)
    assert loaded is not None
    assert state.aufgabe == record["planner_goal"]
    assert state.tasks == [] and state.scout_auftrag == {}
    assert phase.data["tasks"] == [{
        "id": "t1", "name": "Haupttask", "description": "", "action": None,
        "phase_id": None, "parent_id": None, "task_files": [], "dependencies": [],
        "criterion_refs": [], "status": "pending", "decision": None,
        "failure": None, "failure_detail": None, "verdict": "pending",
    }]


def test_role_candidate_is_separate_then_appended_once_after_gates(tmp_path, monkeypatch):
    state, phase, store = _setup(tmp_path)
    digest = _make_role_candidate(state, phase, store)
    assert run_followups.active_chat_followup(phase)["candidate_sha256"] == digest
    assert [task["id"] for task in phase.data["tasks"]] == ["t1"]
    _patch_gates(monkeypatch)
    monkeypatch.setattr("werkstatt.audit.audit", lambda *_args, **_kwargs: True)
    dispositions = []
    monkeypatch.setattr(run_followups, "_append_chat_disposition",
        lambda item, project, run_id, status, detail, **kwargs:
            dispositions.append((status, kwargs.get("task_ids", [])))
    )
    assert run_followups.apply_chat_followup_candidate(
        state, phase, store, "demo", "run-1",
    ) is True
    assert [task["id"] for task in phase.data["tasks"]] == ["t1", "fu_22e971ef18_t1"]
    assert phase.data["tasks"][1]["criterion_refs"] == ["AC2"]
    assert phase.data["tasks"][1]["phase_id"] == "fu_22e971ef18_phase_p1"
    assert phase.data["phasen"][0]["tasks"] == ["fu_22e971ef18_t1"]
    assert phase.data["phasen"][0]["id"] == "fu_22e971ef18_phase_p1"
    assert state.akzeptanzkriterien == ["Hauptkriterium", "Dokumentationstest ist vorhanden"]
    assert dispositions == [("applied", ["fu_22e971ef18_t1"])]
    assert store.get_run_record("demo", "run-1")["checkpoint"]["chat_followup_requests"][0]["status"] == "applied"
    assert run_followups.apply_chat_followup_candidate(state, phase, store, "demo", "run-1") is False


def test_reconcile_processes_only_one_followup_per_checkpoint(
    tmp_path, monkeypatch,
):
    state, phase, store = _setup(tmp_path)
    record = store.get_run_record("demo", "run-1")
    assert record is not None
    checkpoint = dict(record["checkpoint"])
    checkpoint["chat_followup_requests"] = [
        {
            "proposal_id": "proposal-1",
            "session_id": "session-1",
            "request": "Erster bestaetigter Auftrag",
            "status": "received",
        },
        {
            "proposal_id": "proposal-2",
            "session_id": "session-1",
            "request": "Zweiter bestaetigter Auftrag",
            "status": "received",
        },
    ]
    store.update_run_checkpoint(
        "demo", "run-1", checkpoint,
        expected_version=record["checkpoint_version"],
    )
    _patch_gates(monkeypatch)

    assert run_followups.reconcile_chat_followups(state, phase, store, "demo", "run-1") is False
    assert run_followups.prepare_chat_followup_roles(state, phase) is not None
    # Complete the first proposal, then ensure the next remains independently queued.
    state.tasks = [{"id": "t1", "name": "Followup"}]
    state.tests = ["pytest -q tests/test_doc.py"]
    state.akzeptanzkriterien = ["Dokumentationstest ist vorhanden"]
    state.phasen = []
    run_followups.store_chat_followup_candidate(state, phase, run_id="run-1")
    run_followups.apply_chat_followup_candidate(state, phase, store, "demo", "run-1")
    first = store.get_run_record("demo", "run-1")
    assert first is not None
    first_requests = first["checkpoint"]["chat_followup_requests"]
    assert [item["status"] for item in first_requests] == [
        "applied", "received",
    ]
    assert len([
        item for item in phase.data["tasks"]
        if item.get("source_followup_id")
    ]) == 1

    assert run_followups.reconcile_chat_followups(state, phase, store, "demo", "run-1") is False
    second_record = run_followups.prepare_chat_followup_roles(state, phase)
    assert second_record is not None
    assert second_record["proposal_id"] == "proposal-2"
    second = store.get_run_record("demo", "run-1")
    assert second is not None
    second_requests = second["checkpoint"]["chat_followup_requests"]
    assert [item["status"] for item in second_requests] == [
        "applied", "planning",
    ]
    assert len([
        item for item in phase.data["tasks"]
        if item.get("source_followup_id")
    ]) == 1


def test_rejected_followup_leaves_main_graph_unchanged(tmp_path, monkeypatch):
    state, phase, store = _setup(tmp_path)
    _make_role_candidate(state, phase, store)
    _patch_gates(monkeypatch, approved=False)
    dispositions = []
    monkeypatch.setattr(
        run_followups,
        "_append_chat_disposition",
        lambda item, project, run_id, status, detail, **kwargs: dispositions.append(status),
    )

    assert run_followups.apply_chat_followup_candidate(state, phase, store, "demo", "run-1") is True
    assert [task["id"] for task in phase.data["tasks"]] == ["t1"]
    record = store.get_run_record("demo", "run-1")
    assert record is not None
    request = record["checkpoint"]["chat_followup_requests"][0]
    assert request["status"] == "rejected"
    assert dispositions == ["rejected"]


def test_plan_gate_timeout_keeps_candidate_for_resume(tmp_path, monkeypatch):
    state, phase, store = _setup(tmp_path)
    _make_role_candidate(state, phase, store)
    monkeypatch.setattr("werkstatt.gates._plan_gate", lambda _state: True)

    def timed_out(candidate: RunState, *, kontext: str) -> int:
        assert kontext == "chat_followup"
        candidate.gate_timed_out = True
        return 2

    monkeypatch.setattr("werkstatt.gates._human_gate_plan", timed_out)
    try:
        run_followups.apply_chat_followup_candidate(state, phase, store, "demo", "run-1")
    except run_followups.FollowupReconciliationError:
        pass
    else:
        raise AssertionError("Plan-Gate-Timeout muss wiederaufnehmbar bleiben")
    record = store.get_run_record("demo", "run-1")
    assert record is not None
    assert record["checkpoint"]["chat_followup_requests"][0]["status"] == "planning"
    assert run_followups.active_chat_followup(phase)["status"] == "candidate_pending_approval"
    assert len(phase.data["tasks"]) == 1
    assert phase.data["tasks"][0]["id"] == "t1"


def test_coordinator_routes_prepared_followup_to_role_selection(tmp_path):
    state, phase, store = _setup(tmp_path)
    assert run_followups.reconcile_chat_followups(
        state, phase, store, "demo", "run-1",
    ) is False
    record = run_followups.prepare_chat_followup_roles(state, phase)
    assert record is not None

    decision = _run_coordinator_action(phase, state)

    assert state.aufgabe == record["planner_goal"]
    assert decision["coordinator_action"] not in {
        "reconcile_chat_followup", "apply_chat_followup_candidate",
    }
    assert decision["coordinator_action"].startswith("planner_")


def test_finalization_race_resumes_followup_through_coordinator(tmp_path, monkeypatch):
    from werkstatt import loop

    state, phase, store = _setup(tmp_path)
    calls = {"persist": 0, "resume": 0}

    def persist(*_args, **_kwargs):
        calls["persist"] += 1
        if calls["persist"] == 1:
            raise RunInboxPendingError("accepted work")

    monkeypatch.setattr(loop, "EventStore", lambda: store)
    monkeypatch.setattr(loop, "get_run_id", lambda: "run-1")
    monkeypatch.setattr(loop, "_persist_run_result", persist)
    monkeypatch.setattr(loop, "check_run_lease", lambda _state: None)
    monkeypatch.setattr(loop, "_run_coordinator_action", lambda *_args: {
        "coordinator_action": "reconcile_chat_followup",
        "decision": "reconcile_chat_followup",
        "reason": "test",
    })
    monkeypatch.setattr(loop, "_persist_run_coordinator_decision", lambda *_args, **_kwargs: None)

    def resume(*_args):
        calls["resume"] += 1
        return 0

    monkeypatch.setattr(loop, "_continue_followup_with_coordinator", resume)

    assert loop._finish_run_after_followups("demo", state, phase, 0) == 0
    assert calls == {"persist": 2, "resume": 1}
    assert run_followups.active_chat_followup(phase) is not None
