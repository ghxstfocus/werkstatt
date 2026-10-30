"""Spec: Scout + Architect — deterministische Kernfunktionen + LLM-Pfad.

Goldstandard-Anspruch:
- Deterministische Funktionen werden deterministisch getestet
  (echter AST-Parse, echtes rglob, 2x gleicher Output).
- Jeder Audit-Pfad von _run_scout wird gegen die echte
  Audit-JSONL geprueft (kein vakuum-gruen).
- Die Uebergabe an ask_llm (System + User) wird explizit
  asserted, nicht nur "return war ok".
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from werkstatt import planner
from werkstatt.state import LLMReply, RunState


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------

def _state(tmp_path: Path) -> RunState:
    return RunState(
        block_id="t",
        aufgabe="Aufgabe X",
        start_ts="2026-10-30T00:00:00Z",
        docs={},
        agents={},
        always={},
        optional={},
        file_whitelist=[],
        api_key="sk-test",
        budget={},
        agent_docs={},
        project_dir=tmp_path,
        project_name="testproj",
    )


def _audit_events(tmp_path: Path) -> list[dict]:
    """Echte Audit-JSONL (conftest._isolate_audit -> tmp_path/audit-logs)."""
    logs = tmp_path / "audit-logs"
    if not logs.is_dir():
        return []
    out: list[dict] = []
    for f in sorted(logs.glob("agent-pipeline-*.jsonl")):
        for line in f.read_text().splitlines():
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _schreibe(pfad: Path, inhalt: str) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(inhalt, encoding="utf-8")


def _reply(ok: bool, content: str = "", error: str = "") -> LLMReply:
    return LLMReply(ok=ok, content=content, error=error)


# =====================================================================
# A. _baue_api_index
# =====================================================================

def test_index_leere_datei(tmp_path):
    _schreibe(tmp_path / "leer.py", "")
    idx = planner._baue_api_index(tmp_path)
    assert "leer.py" in idx
    assert idx["leer.py"] == {
        "all": [], "classes": [], "functions": [], "imports": [],
    }


def test_index_top_level_funktionen(tmp_path):
    _schreibe(tmp_path / "mod.py",
              "def f(a, b) -> int:\n    return a + b\n")
    idx = planner._baue_api_index(tmp_path)
    fns = idx["mod.py"]["functions"]
    assert len(fns) == 1
    assert fns[0]["name"] == "f"
    assert fns[0]["args"] == ["a", "b"]
    assert fns[0]["return"] == "int"


def test_index_funktion_ohne_return_annot(tmp_path):
    _schreibe(tmp_path / "mod.py", "def g(x):\n    return x\n")
    idx = planner._baue_api_index(tmp_path)
    assert idx["mod.py"]["functions"][0]["return"] == ""


def test_index_klasse_mit_methoden(tmp_path):
    _schreibe(tmp_path / "mod.py",
              "class C:\n"
              "    def a(self, x) -> None: pass\n"
              "    def b(self) -> str: return ''\n")
    idx = planner._baue_api_index(tmp_path)
    klassen = idx["mod.py"]["classes"]
    assert len(klassen) == 1
    assert klassen[0]["name"] == "C"
    methoden = {m["name"]: m for m in klassen[0]["methods"]}
    assert set(methoden) == {"a", "b"}
    assert methoden["a"]["args"] == ["self", "x"]
    assert methoden["b"]["return"] == "str"


def test_index_all(tmp_path):
    _schreibe(tmp_path / "mod.py",
              '__all__ = ["x", "y"]\ndef x(): pass\ndef y(): pass\n')
    idx = planner._baue_api_index(tmp_path)
    assert idx["mod.py"]["all"] == ["x", "y"]


def test_index_all_kaputt_kein_crash(tmp_path):
    _schreibe(tmp_path / "mod.py",
              "__all__ = some_name  # kein literal\ndef x(): pass\n")
    idx = planner._baue_api_index(tmp_path)
    assert idx["mod.py"]["all"] == []
    assert len(idx["mod.py"]["functions"]) == 1


def test_index_imports_from_form(tmp_path):
    """from X import Y,Z -> {"from": X, "names": [Y, Z]}."""
    _schreibe(tmp_path / "mod.py",
              "from werkstatt.state import RunState, LLMReply\n")
    idx = planner._baue_api_index(tmp_path)
    imports = idx["mod.py"]["imports"]
    assert imports == [
        {"from": "werkstatt.state",
         "names": ["RunState", "LLMReply"]},
    ]


def test_index_imports_plain_form(tmp_path):
    """import X -> {"import": X}."""
    _schreibe(tmp_path / "mod.py", "import sys\n")
    idx = planner._baue_api_index(tmp_path)
    assert idx["mod.py"]["imports"] == [{"import": "sys"}]


def test_index_imports_alias_geht_verloren(tmp_path):
    """import json as j -> {"import": "json"}.

    Der Alias (j) wird bewusst nicht erfasst: der Scout
    braucht das Ziel-Modul, nicht den lokalen Namen.
    Dieser Test haelt das Design fest, damit es nicht
    spaeter als "Bug" repariert wird.
    """
    _schreibe(tmp_path / "mod.py", "import json as j\n")
    idx = planner._baue_api_index(tmp_path)
    assert idx["mod.py"]["imports"] == [{"import": "json"}]


def test_index_imports_from_leerer_modul(tmp_path):
    """from . import x -> module None -> "" als Schluessel."""
    _schreibe(tmp_path / "mod.py", "from . import x\n")
    idx = planner._baue_api_index(tmp_path)
    imports = idx["mod.py"]["imports"]
    assert len(imports) == 1
    assert imports[0]["from"] == ""
    assert imports[0]["names"] == ["x"]


def test_index_imports_mehrere_in_einer_datei(tmp_path):
    """Reihenfolge der Imports = Quellreihenfolge."""
    _schreibe(tmp_path / "mod.py",
              "from os import path\n"
              "import sys\n"
              "import json as j\n"
              "from werkstatt.state import RunState, LLMReply\n")
    idx = planner._baue_api_index(tmp_path)
    imports = idx["mod.py"]["imports"]
    assert imports == [
        {"from": "os", "names": ["path"]},
        {"import": "sys"},
        {"import": "json"},
        {"from": "werkstatt.state",
         "names": ["RunState", "LLMReply"]},
    ]


def test_index_syntax_error_uebersprungen(tmp_path):
    _schreibe(tmp_path / "gut.py", "def f(): pass\n")
    _schreibe(tmp_path / "kaputt.py", "def f(:\n    pass\n")
    idx = planner._baue_api_index(tmp_path)
    assert "gut.py" in idx
    assert "kaputt.py" not in idx


def test_index_ignoriert_venv_und_pycache(tmp_path):
    _schreibe(tmp_path / ".venv/x.py", "def a(): pass\n")
    _schreibe(tmp_path / "__pycache__/y.py", "def b(): pass\n")
    _schreibe(tmp_path / "echt.py", "def c(): pass\n")
    idx = planner._baue_api_index(tmp_path)
    assert "echt.py" in idx
    assert not any(".venv" in k for k in idx)
    assert not any("__pycache__" in k for k in idx)


def test_index_relpfade(tmp_path):
    _schreibe(tmp_path / "pkg" / "mod.py", "def f(): pass\n")
    idx = planner._baue_api_index(tmp_path)
    assert "pkg/mod.py" in idx


def test_index_deterministisch(tmp_path):
    _schreibe(tmp_path / "a.py", "def f(): pass\n")
    _schreibe(tmp_path / "b.py", "def g(): pass\n")
    a = planner._baue_api_index(tmp_path)
    b = planner._baue_api_index(tmp_path)
    assert a == b


# =====================================================================
# B. _format_api_index_for_prompt
# =====================================================================

def test_format_leerer_index():
    assert planner._format_api_index_for_prompt({}) == ""


def test_format_mit_funktion():
    idx = {"a.py": {"all": [], "classes": [],
                    "functions": [{"name": "f",
                                   "args": ["x"],
                                   "return": "int"}],
                    "imports": []}}
    s = planner._format_api_index_for_prompt(idx)
    assert "a.py" in s
    assert "def f(x) -> int" in s


def test_format_max_files():
    idx = {f"m{i}.py": {"all": [], "classes": [],
                        "functions": [], "imports": []}
           for i in range(50)}
    s = planner._format_api_index_for_prompt(idx, max_files=40)
    assert "und 10 weitere Dateien" in s


def test_format_ohne_api():
    idx = {"leer.py": {"all": [], "classes": [],
                       "functions": [], "imports": []}}
    s = planner._format_api_index_for_prompt(idx)
    assert "(kein oeffentliches API)" in s


# =====================================================================
# C. _finde_api
# =====================================================================

def _idx_mit_api() -> dict:
    return {
        "mod.py": {
            "all": [],
            "classes": [{
                "name": "C",
                "methods": [
                    {"name": "m1", "args": ["self"], "return": ""},
                ],
            }],
            "functions": [
                {"name": "fn", "args": ["a"], "return": "int"},
            ],
            "imports": [],
        },
        "zwei.py": {
            "all": [],
            "classes": [],
            "functions": [
                {"name": "fn", "args": [], "return": ""},
            ],
            "imports": [],
        },
    }


def test_finde_api_funktion():
    treffer = planner._finde_api(_idx_mit_api(), "fn")
    assert len(treffer) == 2  # in 2 Dateien
    assert all(t["kind"] == "function" for t in treffer)
    assert {t["pfad"] for t in treffer} == {"mod.py", "zwei.py"}


def test_finde_api_klasse():
    treffer = planner._finde_api(_idx_mit_api(), "C")
    assert len(treffer) == 1
    assert treffer[0]["kind"] == "class"
    assert treffer[0]["name"] == "C"
    assert "m1" in treffer[0]["methods"]


def test_finde_api_methode():
    treffer = planner._finde_api(_idx_mit_api(), "m1")
    assert len(treffer) == 1
    assert treffer[0]["kind"] == "method"
    assert treffer[0]["class"] == "C"


def test_finde_api_nicht_gefunden():
    assert planner._finde_api(_idx_mit_api(), "gibtsnicht") == []


# =====================================================================
# D. _segmentiere_nach_pfad
# =====================================================================

def test_segment_leer():
    assert planner._segmentiere_nach_pfad("") == []


def test_segment_ein_pfad():
    s = "## a.py\nCode hier"
    segs = planner._segmentiere_nach_pfad(s)
    assert len(segs) == 1
    assert segs[0]["datei"] == "a.py"
    assert "Code hier" in segs[0]["prosa"]


def test_segment_zwei_pfade():
    s = "## a.py\nA\n## b.py\nB"
    segs = planner._segmentiere_nach_pfad(s)
    assert [x["datei"] for x in segs] == ["a.py", "b.py"]
    assert "A" in segs[0]["prosa"]
    assert "B" in segs[1]["prosa"]


def test_segment_ohne_pfad_ueberschrift():
    assert planner._segmentiere_nach_pfad("nur Prosa ohne Header") == []


# =====================================================================
# E. System-Wrapper
# =====================================================================

def test_architect_system_enthaelt_builder_schnittstelle():
    s = planner._architect_system_with_builder()
    assert planner.ARCHITECT_SYSTEM in s
    assert planner._BUILDER_SCHNITTSTELLE in s


def test_scout_system_enthaelt_nachfolger():
    s = planner._scout_system_with_nachfolger()
    assert planner.SCOUT_SYSTEM in s
    assert planner._SCOUT_NACHFOLGER_BLOCK in s


def test_wrapper_stabil():
    assert planner._architect_system_with_builder() == \
        planner._architect_system_with_builder()
    assert planner._scout_system_with_nachfolger() == \
        planner._scout_system_with_nachfolger()


# =====================================================================
# F. _run_scout
# =====================================================================

def _patch_scout(reply: LLMReply):
    """Patcht ask_llm + _with_spinner im planner-Modul."""
    return patch.multiple(
        "werkstatt.planner",
        ask_llm=lambda *a, **kw: reply,
        _with_spinner=lambda _label, fn: fn(),
    )


def test_scout_ok(tmp_path):
    s = _state(tmp_path)
    antwort = _reply(True, json.dumps({
        "relevante_dateien": ["a.py", "b.py"],
        "risiken": ["r1"],
        "ziel": "x",
    }))
    with _patch_scout(antwort):
        res = planner._run_scout(s, "Aufgabe", {}, [], "sk-test")
    assert res is not None
    assert res["relevante_dateien"] == ["a.py", "b.py"]
    evs = [e for e in _audit_events(tmp_path) if e["kind"] == "planner_scout_ok"]
    assert len(evs) == 1
    assert evs[0]["dateien"] == 2
    assert evs[0]["risiken"] == 1


def test_scout_llm_fehler(tmp_path):
    s = _state(tmp_path)
    with _patch_scout(_reply(False, error="boom")):
        res = planner._run_scout(s, "A", {}, [], "sk")
    assert res is None
    evs = [e for e in _audit_events(tmp_path)
           if e["kind"] == "planner_scout_llm_fehler"]
    assert len(evs) == 1
    assert evs[0]["fehler"] == "boom"


def test_scout_kein_json(tmp_path):
    s = _state(tmp_path)
    with _patch_scout(_reply(True, "nur Prosa, kein JSON")):
        res = planner._run_scout(s, "A", {}, [], "sk")
    assert res is None
    evs = [e for e in _audit_events(tmp_path)
           if e["kind"] == "planner_scout_json_fehler"]
    assert len(evs) == 1


def test_scout_json_kaputt(tmp_path):
    s = _state(tmp_path)
    with _patch_scout(_reply(True, "{ das ist kein json")):
        res = planner._run_scout(s, "A", {}, [], "sk")
    assert res is None
    evs = [e for e in _audit_events(tmp_path)
           if e["kind"] == "planner_scout_json_fehler"]
    assert len(evs) == 1


def test_scout_json_nicht_dict(tmp_path):
    s = _state(tmp_path)
    with _patch_scout(_reply(True, "[1, 2, 3]")):
        res = planner._run_scout(s, "A", {}, [], "sk")
    assert res is None


def test_scout_uebergabe_an_llm(tmp_path):
    """User-Prompt enthaelt Aufgabe + formatierten Index.

    System-Prompt == _scout_system_with_nachfolger().
    """
    s = _state(tmp_path)
    aufrufe: list[dict] = []

    def _fake_ask(api_key, system, user, **kw):
        aufrufe.append({
            "api_key": api_key,
            "system": system,
            "user": user,
            "model": kw.get("model"),
            "temperature": kw.get("temperature"),
            "max_tokens": kw.get("max_tokens"),
        })
        return _reply(True, json.dumps({"relevante_dateien": [],
                                        "risiken": []}))

    idx = {"a.py": {"all": [], "classes": [],
                    "functions": [{"name": "fn",
                                   "args": ["x"],
                                   "return": "int"}],
                    "imports": []}}
    with patch.multiple("werkstatt.planner",
                        ask_llm=_fake_ask,
                        _with_spinner=lambda _l, fn: fn()):
        planner._run_scout(s, "AUFGABE-XY", idx, ["a.py"], "sk-test")

    assert len(aufrufe) == 1
    a = aufrufe[0]
    assert a["api_key"] == "sk-test"
    assert a["system"] == planner._scout_system_with_nachfolger()
    assert "AUFGABE-XY" in a["user"]
    assert "a.py" in a["user"]
    assert "def fn(x) -> int" in a["user"]
    assert a["model"] == "deepseek-chat"
    assert a["temperature"] == 0.2
    assert a["max_tokens"] == 4000
