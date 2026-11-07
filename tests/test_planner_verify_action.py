from unittest.mock import MagicMock

from tests.factories import mk_state
from werkstatt.planner import PLANNER_SPLIT_SYSTEM, _ist_verify_task
from werkstatt.reviewer import _filter_auftrag_treue_false_positives


def test_ist_verify_task_klassifiziert_verifikation():
    assert _ist_verify_task("pruefe X", "") is True
    assert _ist_verify_task("", "verifiziere Y") is True
    assert _ist_verify_task("stelle sicher Z", "") is True
    assert _ist_verify_task("check W", "") is True
    assert _ist_verify_task("Pruefe Grossbuchstaben", "") is True
    assert _ist_verify_task("baue V", "") is False
    assert _ist_verify_task(None, None) is False
    assert "verify" in PLANNER_SPLIT_SYSTEM
    assert "Task prueft einen Zustand" in PLANNER_SPLIT_SYSTEM


def test_phase_tasks_verify_ruft_run_builder_nicht(monkeypatch):
    import werkstatt.phases.tasks as tasks_mod

    state = mk_state()
    state.tasks = [
        {"id": "t1", "name": "pruefe X", "action": "verify", "task_files": ["a.py"]}
    ]
    state.aktuelle_task = None
    state.auftrag_bereits_erfuellt = False

    phase_state = MagicMock()
    phase_state.get_next_task.side_effect = [state.tasks[0], None]
    phase_state.data = {"tasks": state.tasks}
    phase_state._unmet_dependencies.return_value = []

    builder_calls = []
    verify_calls = []
    reviewer_calls = []

    def fake_run_builder(*args, **kwargs):
        builder_calls.append((args, kwargs))
        return True

    def fake_verify_patches(*args, **kwargs):
        verify_calls.append((args, kwargs))
        return True

    def fake_run_reviewer(*args, **kwargs):
        reviewer_calls.append((args, kwargs))
        return True

    monkeypatch.setattr(tasks_mod, "run_builder", fake_run_builder)
    monkeypatch.setattr(tasks_mod, "_verify_patches", fake_verify_patches)
    monkeypatch.setattr(tasks_mod, "run_reviewer", fake_run_reviewer)
    monkeypatch.setattr(tasks_mod, "_task_ende", lambda *a, **k: None)
    monkeypatch.setattr(tasks_mod, "audit", lambda *a, **k: None)
    monkeypatch.setattr(tasks_mod, "_reset_task_state", lambda *a, **k: None)
    monkeypatch.setattr(tasks_mod, "_split_task_on_demand", lambda *a, **k: None)
    monkeypatch.setattr(tasks_mod, "group_start", lambda *a, **k: None)
    monkeypatch.setattr(tasks_mod, "group_end", lambda *a, **k: None)
    monkeypatch.setattr(tasks_mod, "task", lambda *a, **k: None)
    monkeypatch.setattr(tasks_mod, "task_started", lambda *a, **k: None)
    monkeypatch.setattr(tasks_mod, "task_ok", lambda *a, **k: None)
    monkeypatch.setattr(tasks_mod, "task_done", lambda *a, **k: None)

    tasks_mod._phase_tasks_loop(state, phase_state)

    assert builder_calls == []
    assert len(verify_calls) == 1
    assert len(reviewer_calls) == 1


def test_reviewer_filtert_diff_erwartung_bei_verify():
    bugs = [
        {"severity": "high", "description": "Diff fehlt Datei a.py"},
        {"severity": "high", "description": "Task verlangt Funktion run_x, Diff hat sie nicht"},
        {"severity": "high", "description": "Neues Modul nicht genutzt"},
        {"severity": "high", "description": "Echter Syntaxfehler in Zeile 5"},
    ]

    result = _filter_auftrag_treue_false_positives(
        bugs,
        diff="",
        task_desc="pruefe X",
        task_files=["a.py"],
        action="verify",
    )

    assert len(result) == 1
    assert "Syntaxfehler" in result[0]["description"]
