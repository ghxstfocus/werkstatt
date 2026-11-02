"""OP-072: Skill-Relevanz-Ranking nach Glob-Spezifitaet.

Statt alphabetischer Reihenfolge werden Skills nach Spezifitaet
des matcht Glob-Patterns sortiert. Damit gewinnt test-patterns
bei Test-Files gegen die generischen **/*.py-Skills.
"""
from werkstatt.skills import (
    load_all_skills,
    skills_aktivieren,
    skills_fuer_task,
)


def test_spezifitaet_test_patterns_gewinnt():
    """Bei Test-Files: test-patterns vor generischen **/*.py-Skills."""
    skills = load_all_skills()
    matched = skills_fuer_task(skills, ["tests/test_foo.py"])
    names = [s["name"] for s in matched]
    assert "test-patterns" in names, f"nicht gematcht: {names}"
    # test-patterns spezifischer als anker-regeln (**/*.py)
    assert names.index("test-patterns") < names.index("anker-regeln"), names


def test_spezifitaet_security_gewinnt():
    """Bei auth/**-Pfaden: security-review vor generischen Python-Skills."""
    skills = load_all_skills()
    aktiviert = skills_aktivieren(skills, ["core/auth/login.py"], max_total=3)
    names = [s["name"] for s in aktiviert]
    assert "security-review" in names, f"nicht aktiviert: {names}"


def test_spezifitaet_reine_py_datei_ohne_test_patterns():
    """Bei reiner .py-Datei (nicht tests/) keine test-patterns."""
    skills = load_all_skills()
    matched = skills_fuer_task(skills, ["werkstatt/verify.py"])
    names = [s["name"] for s in matched]
    assert "anker-regeln" in names
    assert "patch-format" in names
    assert "simplify" in names
    assert "test-patterns" not in names


def test_gleichstand_alphabetisch_deterministisch():
    """Bei gleicher Spezifitaet bleibt die alphabetische Reihenfolge."""
    skills = load_all_skills()
    matched = skills_fuer_task(skills, ["werkstatt/verify.py"])
    names = [s["name"] for s in matched]
    # Alle drei haben **/*.py -> Spezifitaet 3 -> alphabetisch
    idx_anker = names.index("anker-regeln")
    idx_patch = names.index("patch-format")
    idx_simplify = names.index("simplify")
    assert idx_anker < idx_patch < idx_simplify, f"nicht alphabetisch: {names}"


def test_max_total_3_laedt_test_patterns_jetzt():
    """Regression-Schutz: mit dem Ranking landet test-patterns in top-3."""
    skills = load_all_skills()
    aktiviert = skills_aktivieren(skills, ["tests/test_foo.py"], max_total=3)
    names = [s["name"] for s in aktiviert]
    assert "test-patterns" in names, f"test-patterns fehlt: {names}"
