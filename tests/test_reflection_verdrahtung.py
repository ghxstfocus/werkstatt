"""Tests fuer die Verdrahtung der Reflection: letzter Test-Fehler im Prompt,
Skill-Body-Wiederverwendung und Doku der drei Reflection-Varianten.

Alle Tests sind deterministisch: kein LLM, kein echter Skill-Dateizugriff.
"""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import werkstatt.prompts as _p
import werkstatt.reflection as _refl
import werkstatt.skills as _skills

## test_letzter_test_fehler_landet_im_prompt


def test_letzter_test_fehler_landet_im_prompt() -> None:
    """Der letzte Test-Fehler landet im Prompt-Block, wird aber dedupliziert."""
    block = _p.format_letzter_test_fehler_block("AssertionError: 1 != 2", [])
    assert "LETZTER TEST-FEHLER" in block
    assert "AssertionError: 1 != 2" in block

    assert _p.format_letzter_test_fehler_block("Boom", ["Boom"]) == ""
    assert (
        _p.format_letzter_test_fehler_block(
            "Boom", [{"text": "Boom", "stage_id": "pytest_changed"}]
        )
        == ""
    )
    assert _p.format_letzter_test_fehler_block("", []) == ""

    quelle = Path(_refl.__file__).read_text(encoding="utf-8")
    baum = ast.parse(quelle)
    loop_body = None
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.FunctionDef) and knoten.name == "_reflection_loop":
            loop_body = ast.get_source_segment(quelle, knoten)
            break
    assert loop_body is not None, "_reflection_loop nicht gefunden"
    assert "format_letzter_test_fehler_block" in loop_body


## test_geladene_skills_wird_respektiert


def test_geladene_skills_wird_respektiert(monkeypatch) -> None:
    """Bereits geladene Skills werden nicht erneut geladen."""

    def _boom(*_a, **_kw):
        raise AssertionError("Skill erneut geladen")

    state_geladen = SimpleNamespace(
        geladene_skills=["systematic-debugging"],
        reflection_skill_body="BODY",
    )
    monkeypatch.setattr(_skills, "load_skill_by_name", _boom)
    assert _refl._skill_body_fuer_reflection(state_geladen) == "BODY"

    recorder: list[tuple[tuple, dict]] = []

    def _rec(*a, **kw):
        recorder.append((a, kw))

    state_leer = SimpleNamespace(geladene_skills=[], reflection_skill_body="")
    monkeypatch.setattr(_skills, "load_all_skills", list)
    monkeypatch.setattr(_skills, "load_skill_by_name", lambda *_a, **_kw: {"body": "SKILL-BODY"})
    monkeypatch.setattr(_skills, "_merke_geladene_skills", _rec)

    ergebnis = _refl._skill_body_fuer_reflection(state_leer)
    assert ergebnis == "SKILL-BODY"
    assert state_leer.reflection_skill_body == "SKILL-BODY"
    assert len(recorder) == 1
    args, kwargs = recorder[0]
    rolle = kwargs.get("rolle")
    if rolle is None and len(args) >= 3:
        rolle = args[2]
    assert rolle == "reflection"


## test_reflection_doku_listet_drei_varianten


def test_reflection_doku_listet_drei_varianten() -> None:
    """Die Modul-Doku von reflection.py nennt die drei Reflection-Varianten."""
    src = Path(_refl.__file__).read_text(encoding="utf-8")
    doc = ast.get_docstring(ast.parse(src)) or ""
    assert "post_build" in doc
    assert "phase_end" in doc
    assert "plan_reject" in doc
