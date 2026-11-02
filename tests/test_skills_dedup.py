"""Skill-Dedup + Audit-Event (nach 9362cc8).

Zwei Befunde aus der Messung 2026-11-02:
1. _reviewer_system wird 2x pro Task gerufen -> Skill-Namen wurden
   mehrfach in state.geladene_skills angehaengt.
2. geladene_skills wurde nirgends gelesen -> Trail wertlos.

Fix: zentrale _merke_geladene_skills (dedup + audit-on-change).
"""
from pathlib import Path

from werkstatt.skills import _merke_geladene_skills
from werkstatt.state import RunState


def _make_state():
    return RunState(
        block_id="t", aufgabe="a", start_ts="",
        docs={}, agents={}, always={}, optional={},
        file_whitelist=[], api_key="fake", budget={},
        agent_docs={}, project_dir=Path("/opt/werkstatt"),
        project_name="werkstatt",
    )


def test_kein_duplikat_bei_mehrfachem_merk():
    st = _make_state()
    st.geladene_skills = []
    r1 = _merke_geladene_skills(st, ["a", "b"], rolle="test")
    r2 = _merke_geladene_skills(st, ["a", "b"], rolle="test")
    r3 = _merke_geladene_skills(st, ["b", "c"], rolle="test")
    assert r1 == ["a", "b"]
    assert r2 == []  # alle schon da
    assert r3 == ["c"]  # nur c neu
    assert st.geladene_skills == ["a", "b", "c"]


def test_leere_names_kein_append():
    st = _make_state()
    st.geladene_skills = []
    r = _merke_geladene_skills(st, [], rolle="test")
    assert r == []
    assert st.geladene_skills == []


def test_state_ohne_geladene_skills_kein_crash():
    class FakeState:
        pass
    r = _merke_geladene_skills(FakeState(), ["a"], rolle="test")
    assert r == []


def test_geladene_skills_kein_list_kein_crash():
    class FakeState:
        geladene_skills = "kein list"
    r = _merke_geladene_skills(FakeState(), ["a"], rolle="test")
    assert r == []


def test_reviewer_2_aufrufe_kein_duplikat():
    """Regression: _reviewer_system 2x auf gleichem State."""
    from werkstatt.reviewer import _reviewer_system
    st = _make_state()
    st.geladene_skills = []
    _reviewer_system(st, ["tests/test_foo.py"])
    _reviewer_system(st, ["tests/test_foo.py"])
    counts = {}
    for n in st.geladene_skills:
        counts[n] = counts.get(n, 0) + 1
    dups = {n: c for n, c in counts.items() if c > 1}
    assert not dups, f"Duplikate: {dups} in {st.geladene_skills}"


def test_reviewer_wechselnde_task_files_kein_duplikat():
    """Regression: gleicher State, verschiedene task_files."""
    from werkstatt.reviewer import _reviewer_system
    st = _make_state()
    st.geladene_skills = []
    _reviewer_system(st, ["tests/test_foo.py"])
    _reviewer_system(st, ["core/auth/login.py"])
    _reviewer_system(st, ["werkstatt/verify.py"])
    counts = {}
    for n in st.geladene_skills:
        counts[n] = counts.get(n, 0) + 1
    dups = {n: c for n, c in counts.items() if c > 1}
    assert not dups, f"Duplikate: {dups} in {st.geladene_skills}"
    # Spezifitaets-Ranking: test-patterns UND security-review geladen
    assert "test-patterns" in st.geladene_skills
    assert "security-review" in st.geladene_skills
