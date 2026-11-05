"""Tests fuer werkstatt/state_contracts.py (OP-136, OP-141-Vorarbeit)."""
from pathlib import Path

from werkstatt.state import RunState
from werkstatt.state_contracts import (
    TRANSITIONS,
    ContractViolation,
    validate_transition,
)


def _minimal_state(**kwargs):
    defaults = {
        "block_id": "test", "aufgabe": "test",
        "start_ts": "2026-11-05T00:00:00",
        "docs": {}, "agents": {}, "always": {}, "optional": {},
        "file_whitelist": [], "api_key": "", "budget": {},
        "agent_docs": {}, "project_dir": Path("/tmp"),
    }
    defaults.update(kwargs)
    return RunState(**defaults)


def test_transitions_vollstaendig():
    """Alle 5 erwarteten Uebergaenge sind definiert."""
    assert set(TRANSITIONS.keys()) == {
        "explorer->scout", "scout->architect", "architect->planner",
        "planner->builder", "builder->reviewer",
    }


def test_transitions_felder_sind_runstate_felder():
    """Jedes TRANSITIONS-Feld ist in RunState deklariert."""
    deklariert = set(RunState.__dataclass_fields__.keys())
    for key, felder in TRANSITIONS.items():
        for feld_name, _regel in felder:
            assert feld_name in deklariert, (
                f"TRANSITIONS[{key!r}] referenziert unbekanntes Feld "
                f"{feld_name!r}"
            )


# ============================================================
# validate_transition
# ============================================================


def test_validate_transition_leer_failt():
    st = _minimal_state()  # explorer_context = {}
    try:
        validate_transition("explorer", "scout", st,
                            audit_fn=lambda *a, **k: None)
    except ContractViolation as e:
        assert e.transition == "explorer->scout"
        assert "explorer_context" in e.felder
    else:
        raise AssertionError("ContractViolation erwartet")


def test_validate_transition_befuellt_passiert():
    st = _minimal_state()
    st.explorer_context = {"findings": "x", "key_files": [{"file": "a.py"}]}
    validate_transition("explorer", "scout", st,
                        audit_fn=lambda *a, **k: None)


def test_validate_transition_architect_to_planner():
    st = _minimal_state()  # architect_prosa = ""
    try:
        validate_transition("architect", "planner", st,
                            audit_fn=lambda *a, **k: None)
    except ContractViolation as e:
        assert "architect_prosa" in e.felder
    else:
        raise AssertionError("ContractViolation erwartet")

    st2 = _minimal_state()
    st2.architect_prosa = "plan text"
    validate_transition("architect", "planner", st2,
                        audit_fn=lambda *a, **k: None)


def test_validate_transition_planner_to_builder():
    st = _minimal_state()  # tasks = []
    try:
        validate_transition("planner", "builder", st,
                            audit_fn=lambda *a, **k: None)
    except ContractViolation:
        pass
    else:
        raise AssertionError("ContractViolation erwartet")

    st2 = _minimal_state()
    st2.tasks = [{"id": "t1"}]
    validate_transition("planner", "builder", st2,
                        audit_fn=lambda *a, **k: None)


def test_validate_transition_auto_skip_scout():
    """scout->architect: auto-Regeln greifen, leere Felder OK."""
    st = _minimal_state()
    validate_transition("scout", "architect", st,
                        audit_fn=lambda *a, **k: None)


def test_validate_transition_unbekannter_uebergang_ist_noop():
    st = _minimal_state()
    validate_transition("foo", "bar", st)


def test_validate_transition_ruft_audit():
    calls = []

    def _fake_audit(*args, **kwargs):
        calls.append((args, kwargs))

    st = _minimal_state()
    try:
        validate_transition("explorer", "scout", st, audit_fn=_fake_audit)
    except ContractViolation:
        pass
    assert len(calls) == 1
    args, _ = calls[0]
    assert args[0] == "state_contract_violation"
    assert args[1]["transition"] == "explorer->scout"
    assert "explorer_context" in args[1]["felder"]
