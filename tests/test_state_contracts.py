"""Tests für werkstatt/state_contracts.py (OP-135a + OP-136)."""
from pathlib import Path

from werkstatt.state import RunState
from werkstatt.state_contracts import (
    CONTRACTS,
    ArchitectOutput,
    ContractViolation,
    ExplorerDiagnostics,
    ExplorerOutput,
    KeyFile,
    PlannerOutput,
    ScoutOutput,
    validate_transition,
)


def _minimal_state(**kwargs):
    """RunState mit Minimal-Pflichtfeldern (siehe state.py RunState-Kopf)."""
    defaults = {
        "block_id": "test", "aufgabe": "test",
        "start_ts": "2026-11-05T00:00:00",
        "docs": {}, "agents": {}, "always": {}, "optional": {},
        "file_whitelist": [], "api_key": "", "budget": {},
        "agent_docs": {}, "project_dir": Path("/tmp"),
    }
    defaults.update(kwargs)
    return RunState(**defaults)


def test_registry_vollstaendig():
    """Alle 5 Contracts registriert, Typen importierbar."""
    assert set(CONTRACTS.keys()) == {
        "explorer_output", "explorer_diagnostics",
        "scout_output", "architect_output", "planner_output",
    }
    for c in CONTRACTS.values():
        assert c.schreiber, f"{c.typ}: keine Schreiber"
        assert c.leser, f"{c.typ}: keine Leser"


def test_contract_dict_roundtrip():
    """from_dict(to_dict(x)) == x für alle Dataclasses."""
    cases = [
        ExplorerOutput(findings="f", next_reads=["a"]),
        ExplorerDiagnostics(git_dirty=True, pytest_laufzeit_s=5,
                            ruff_befunde=["x"]),
        ScoutOutput(api_auszug={"a.py": ["f"]}, bereits_erfuellt=True),
        ArchitectOutput(prosa="text"),
        PlannerOutput(tasks=[{"id": "t1"}], tests=["pytest"],
                      akzeptanzkriterien=["x"]),
    ]
    for obj in cases:
        rt = type(obj).from_dict(obj.to_dict())
        assert rt == obj, f"{type(obj).__name__}: roundtrip mismatch"


def test_explorer_output_aus_dict_normalisiert_key_files():
    """ExplorerOutput.from_dict({key_files: [{...}]}) → list[KeyFile]."""
    d = {
        "findings": "text",
        "key_files": [
            {"file": "a.py", "why": "x", "confidence": "high"},
        ],
        "next_reads": ["a.py"],
    }
    eo = ExplorerOutput.from_dict(d)
    assert len(eo.key_files) == 1
    assert isinstance(eo.key_files[0], KeyFile)
    assert eo.key_files[0].file == "a.py"
    assert eo.key_files[0].confidence == "high"


def test_leere_dicts_sind_defaults():
    """from_dict({}) == from_dict(None) == Default-Instanz."""
    for cls in [ExplorerOutput, ExplorerDiagnostics, ScoutOutput,
                ArchitectOutput, PlannerOutput]:
        assert cls.from_dict({}) == cls()
        assert cls.from_dict(None) == cls()


def test_property_views_auf_runstate():
    """state.explorer_output spiegelt state.explorer_context (Ghost)."""
    st = _minimal_state()
    st.explorer_context = {
        "findings": "gefunden",
        "key_files": [{"file": "x.py", "why": "y"}],
        "next_reads": ["x.py"],
    }
    eo = st.explorer_output
    assert isinstance(eo, ExplorerOutput)
    assert eo.findings == "gefunden"
    assert eo.key_files[0].file == "x.py"
    # dict-Zugriff für Rückwärts-Kompatibilität
    assert eo["findings"] == "gefunden"
    assert eo.get("nicht_da", "default") == "default"


def test_planner_output_reflektiert_tasks():
    """state.planner_output.tasks liest state.tasks (kein doppelter Zustand)."""
    st = _minimal_state()
    st.tasks = [{"id": "t1", "name": "X"}]
    st.tests = ["pytest tests/x"]
    st.akzeptanzkriterien = ["x laeuft"]
    po = st.planner_output
    assert po.tasks == [{"id": "t1", "name": "X"}]
    assert po.tests == ["pytest tests/x"]
    assert po.akzeptanzkriterien == ["x laeuft"]


def test_explorer_diagnostics_default():
    """Frischer RunState → explorer_diagnostics alle Defaults."""
    st = _minimal_state()
    ed = st.explorer_diagnostics
    assert ed.git_dirty is False
    assert ed.pytest_laufzeit_s == 0
    assert ed.ruff_befunde == []


# ============================================================
# OP-136: validate_transition
# ============================================================


def _state_mit_contracts(
    *, explorer_output=None, architect_output=None, planner_output=None,
):
    st = _minimal_state()
    if explorer_output is not None:
        st.explorer_context = explorer_output
    if architect_output is not None:
        st.architect_prosa = architect_output
    if planner_output is not None:
        st.tasks = planner_output.get("tasks", [])
        st.tests = planner_output.get("tests", [])
        st.akzeptanzkriterien = planner_output.get("akzeptanzkriterien", [])
    return st


def test_validate_transition_leer_failt():
    st = _minimal_state()
    try:
        validate_transition("explorer", "scout", st,
                            audit_fn=lambda *a, **k: None)
    except ContractViolation as e:
        assert e.transition == "explorer->scout"
        assert "explorer_output" in e.felder
    else:
        raise AssertionError("ContractViolation erwartet")


def test_validate_transition_befuellt_passiert():
    st = _state_mit_contracts(
        explorer_output={"findings": "x",
                         "key_files": [{"file": "a.py"}]},
    )
    validate_transition("explorer", "scout", st,
                        audit_fn=lambda *a, **k: None)


def test_validate_transition_architect_to_planner():
    st = _state_mit_contracts(architect_output="")
    try:
        validate_transition("architect", "planner", st,
                            audit_fn=lambda *a, **k: None)
    except ContractViolation as e:
        assert "architect_output" in e.felder
    else:
        raise AssertionError("ContractViolation erwartet")

    st2 = _state_mit_contracts(architect_output="plan text")
    validate_transition("architect", "planner", st2,
                        audit_fn=lambda *a, **k: None)


def test_validate_transition_planner_to_builder():
    st = _minimal_state()
    try:
        validate_transition("planner", "builder", st,
                            audit_fn=lambda *a, **k: None)
    except ContractViolation:
        pass
    else:
        raise AssertionError("ContractViolation erwartet")

    st2 = _state_mit_contracts(
        planner_output={"tasks": [{"id": "t1"}],
                        "tests": ["pytest"],
                        "akzeptanzkriterien": ["x"]},
    )
    validate_transition("planner", "builder", st2,
                        audit_fn=lambda *a, **k: None)


def test_validate_transition_auto_skip_scout():
    """scout->architect: leerer scout_output ist OK (auto-Regel)."""
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
    assert "explorer_output" in args[1]["felder"]
