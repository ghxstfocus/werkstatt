"""Tests für werkstatt/state_contracts.py (OP-135a)."""
from pathlib import Path

import pytest

from werkstatt.state import RunState
from werkstatt.state_contracts import (
    CONTRACTS,
    ArchitectOutput,
    ExplorerDiagnostics,
    ExplorerOutput,
    KeyFile,
    PlannerOutput,
    ScoutOutput,
)


def _minimal_state(**kwargs):
    """RunState mit Minimal-Pflichtfeldern (siehe state.py RunState-Kopf)."""
    defaults = dict(
        block_id="test", aufgabe="test",
        start_ts="2026-11-05T00:00:00",
        docs={}, agents={}, always={}, optional={},
        file_whitelist=[], api_key="", budget={},
        agent_docs={}, project_dir=Path("/tmp"),
    )
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
