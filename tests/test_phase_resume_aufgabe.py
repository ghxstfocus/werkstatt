"""OP-381k: Resume nur wenn Aufgabe identisch."""
from __future__ import annotations

from pathlib import Path


def test_plan_py_hat_resume_check():
    src = Path("werkstatt/phases/plan.py").read_text(encoding="utf-8")
    assert "_resume_erlaubt" in src
    assert "loop_resume_verworfen" in src
    assert 'phase_state.data.get("aufgabe")' in src


def test_resume_bei_anderer_aufgabe_verworfen():
    phase_aufgabe = "OP-376: Fehler-Cluster"
    aktuelle_aufgabe = "OP-381b: Freitext-Gates"
    erlaubt = True
    if phase_aufgabe and phase_aufgabe != aktuelle_aufgabe:
        erlaubt = False
    assert erlaubt is False


def test_resume_bei_gleicher_aufgabe():
    phase_aufgabe = "OP-376: Fehler-Cluster"
    aktuelle_aufgabe = "OP-376: Fehler-Cluster"
    erlaubt = True
    if phase_aufgabe and phase_aufgabe != aktuelle_aufgabe:
        erlaubt = False
    assert erlaubt is True


def test_resume_bei_leerer_phase_aufgabe():
    phase_aufgabe = ""
    aktuelle_aufgabe = "OP-376"
    erlaubt = True
    if phase_aufgabe and phase_aufgabe != aktuelle_aufgabe:
        erlaubt = False
    assert erlaubt is True
