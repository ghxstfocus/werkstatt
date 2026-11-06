"""Spec: RunState-Defaults + LLMReply-Defaults + kleine Dataclasses.

Nicht getestet (schon abgedeckt):
- PhaseState-Roundtrip/resume/failed -> tests/test_phase_state.py
- PhaseState-Atomaritaet/Persistenz   -> tests/test_loop_main_persistiert.py

Getestet hier nur, was sonst nichts testet: harte Defaults,
die der Handoff als "verifiziert" listet und die bei einer
Refaktorierung still brechen koennten.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from werkstatt.state import (
    BudgetExhausted,
    LLMReply,
    Measurement,
    RunState,
    SolverBefund,
    SolverDiagnose,
)

# ---------------------------------------------------------------------
# Pflicht-Felder (kein Default -> TypeError bei Weglassen)
# ---------------------------------------------------------------------

def _pflicht() -> dict:
    """Frische Pflichtfelder pro Aufruf.

    Wichtig: keine Modul-Konstante mit {} / [] teilen — sonst
    waeren alle RunState-Instanzen ueber dieselben Container
    verbunden (genau der Bug, den
    test_mutable_defaults_sind_isoliert sucht).
    """
    return {
        "block_id": "b",
        "aufgabe": "a",
        "start_ts": "2026-10-30T00:00:00Z",
        "docs": {},
        "agents": {},
        "always": {},
        "optional": {},
        "file_whitelist": [],
        "api_key": "sk-test",
        "budget": {},
        "agent_docs": {},
        "project_dir": Path("/tmp/x"),
    }


def _state(**overrides) -> RunState:
    kw = _pflicht()
    kw.update(overrides)
    return RunState(**kw)


def test_pflicht_felder_fehlen_wirft():
    with pytest.raises(TypeError):
        RunState(block_id="b")  # type: ignore[call-arg]


def test_pflicht_felder_gesetzt():
    s = _state()
    assert s.block_id == "b"
    assert s.project_dir == Path("/tmp/x")


# ---------------------------------------------------------------------
# Timeouts
# ---------------------------------------------------------------------

def test_max_total_llm_s_default():
    assert _state().max_total_llm_s == 240


# ---------------------------------------------------------------------
# Zaehler + Flag-Defaults
# ---------------------------------------------------------------------

@pytest.mark.parametrize("feld,erwartet", [
    ("llm_calls", 0),
    ("phase_aktueller_index", 0),
    ("phase_aktiv", False),
    ("mess_protokoll_veraltet", False),
    ("start_monotonic", 0.0),
])
def test_zaehler_und_flags(feld, erwartet):
    assert getattr(_state(), feld) == erwartet


# ---------------------------------------------------------------------
# default_factory-Listen/Dicts sind pro Instanz frisch
# (Klassiker: mutable default -> Shared State zwischen Runs)
# ---------------------------------------------------------------------

@pytest.mark.parametrize("feld", [
    # Nur Felder MIT default_factory. Pflichtfelder (docs,
    # agents, always, optional, file_whitelist, budget,
    # agent_docs) haben bewusst keinen Default — sie werden
    # vom Aufrufer gesetzt.
    "messungen",
    "code_patches",
    "reviewer_bugs", "reviewer_bugs_history",
    "reflection_history", "preflight_fehler",
    "basis_gate_test_results", "geladene_skills",
])
def test_mutable_defaults_sind_isoliert(feld):
    a = _state()
    b = _state()
    va = getattr(a, feld)
    vb = getattr(b, feld)
    assert va is not vb, f"{feld} teilt mutable default zwischen Instanzen"


# ---------------------------------------------------------------------
# LLMReply
# ---------------------------------------------------------------------

def test_llmreply_defaults():
    r = LLMReply(ok=True)
    assert r.content == ""
    assert r.error == ""
    assert r.system_len == 0
    assert r.user_len == 0


def test_llmreply_fehlerfall():
    r = LLMReply(ok=False, error="boom")
    assert r.ok is False
    assert r.error == "boom"
    assert r.content == ""


# ---------------------------------------------------------------------
# Measurement: frozen + timeout_s-Default
# ---------------------------------------------------------------------

def test_measurement_frozen():
    m = Measurement(mid="m", argv=("true",), beschreibung="x")
    with pytest.raises(Exception):  # FrozenInstanceError
        m.mid = "anders"  # type: ignore[misc]


def test_measurement_timeout_default():
    m = Measurement(mid="m", argv=("true",), beschreibung="x")
    assert m.timeout_s == 60


# ---------------------------------------------------------------------
# BudgetExhausted
# ---------------------------------------------------------------------

def test_budget_exhausted_ist_exception():
    assert issubclass(BudgetExhausted, Exception)
    with pytest.raises(BudgetExhausted):
        raise BudgetExhausted("leer")


# ---------------------------------------------------------------------
# SolverBefund.ist_vollstaendig — vier Diagnosen, je 1 Pflichtfeld
# ---------------------------------------------------------------------

def test_solverbefund_gleicher_fehler_braucht_kandidaten():
    assert not SolverBefund(art=SolverDiagnose.GLEICHER_FEHLER).ist_vollstaendig()
    assert SolverBefund(
        art=SolverDiagnose.GLEICHER_FEHLER,
        kandidaten=["a.py"],
    ).ist_vollstaendig()


def test_solverbefund_anderer_fehler_braucht_auftrag():
    assert not SolverBefund(art=SolverDiagnose.ANDERER_FEHLER).ist_vollstaendig()
    assert SolverBefund(
        art=SolverDiagnose.ANDERER_FEHLER,
        praezisierter_auftrag="mach x",
    ).ist_vollstaendig()


def test_solverbefund_widerspruch_braucht_hinweis():
    assert not SolverBefund(art=SolverDiagnose.WIDERSPRUCH).ist_vollstaendig()
    assert SolverBefund(
        art=SolverDiagnose.WIDERSPRUCH,
        rueckspiel_hinweis="anders",
    ).ist_vollstaendig()


def test_solverbefund_unklar_braucht_eskalation():
    assert not SolverBefund(art=SolverDiagnose.UNKLAR).ist_vollstaendig()
    assert SolverBefund(
        art=SolverDiagnose.UNKLAR,
        eskalation="mensch fragen",
    ).ist_vollstaendig()
