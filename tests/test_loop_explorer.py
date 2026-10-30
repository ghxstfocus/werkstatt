"""Spec: Explorer — Helfer + run_explorer-Fail-closed-Pfade.

Nicht dupliziert:
- _extract_dateien          -> test_explorer_messung.py (3)
- _messen                   -> test_explorer_messung.py (3)
- _extrahiere_pfade         -> test_k12_explorer_md.py (5)
- run_explorer-Happy/kein-K -> test_explorer_agent.py (2)

Getestet hier (bisher 0 Tests):
- _datei_inhalt
- _format_findings
- _verwandte_dateien
- _explorer_system
- _list_py_files
- _migrations_stand  (nicht in planner.py, sondern explorer.py)
- run_explorer: explorer_llm_fehler + explorer_json_fehler
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from werkstatt import explorer
from werkstatt.state import LLMReply, RunState


# =====================================================================
# Fixtures
# =====================================================================

def _state(tmp_path: Path, **overrides) -> RunState:
    kw = dict(
        block_id="t", aufgabe="aufgabe", start_ts="2026-10-30T00:00:00Z",
        docs={}, agents={}, always={}, optional={}, file_whitelist=[],
        api_key="sk-test", budget={}, agent_docs={},
        project_dir=tmp_path, project_name="testproj",
    )
    kw.update(overrides)
    return RunState(**kw)


def _audit_events(tmp_path: Path) -> list[dict]:
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


def _kind(tmp_path: Path, kind: str) -> list[dict]:
    return [e for e in _audit_events(tmp_path) if e.get("kind") == kind]


# =====================================================================
# A. _datei_inhalt
# =====================================================================

def test_datei_inhalt_klein_komplett(tmp_path):
    (tmp_path / "klein.py").write_text("a\nb\nc\n")
    assert explorer._datei_inhalt(tmp_path, "klein.py") == "a\nb\nc\n"


def test_datei_inhalt_gross_truncated(tmp_path):
    (tmp_path / "gross.py").write_text("\n".join(
        f"zeile{i}" for i in range(300)))
    out = explorer._datei_inhalt(tmp_path, "gross.py")
    # Erste Zeile sichtbar, letzte Zeile sichtbar.
    assert "zeile0" in out
    assert "zeile299" in out
    # Truncation-Marker.
    assert "gekuerzt" in out
    # Mitte weg.
    assert "zeile150" not in out


def test_datei_inhalt_fehlt(tmp_path):
    assert explorer._datei_inhalt(tmp_path, "gibtsnicht.py") == ""


def test_datei_inhalt_ungueltige_utf8(tmp_path):
    """Binaere/ungueltige UTF-8 -> kein Crash (errors='replace')."""
    (tmp_path / "bin.py").write_bytes(b"def f():\n    return \xff\xfe\n")
    out = explorer._datei_inhalt(tmp_path, "bin.py")
    assert "def f():" in out


# =====================================================================
# B. _format_findings
# =====================================================================

def test_format_findings_leer():
    assert explorer._format_findings({}) == ""


def test_format_findings_migrations():
    m = {
        "migrations": {
            "hoechste": "0018", "naechste": "0019",
            "alle": ["0018"], "dateien": ["0018_x.sql"],
        },
    }
    out = explorer._format_findings(m)
    assert "migrations" in out
    assert "0018" in out
    assert "0019" in out


def test_format_findings_aufgabe_pfade():
    m = {"aufgabe_pfade": {"dateien": ["a.py", "b.py"]}}
    out = explorer._format_findings(m)
    assert "aufgabe_pfade" in out
    assert "2" in out


def test_format_findings_ruff_standard():
    m = {"ruff": {"dateien": ["x.py"]}}
    out = explorer._format_findings(m)
    assert "ruff" in out


# =====================================================================
# C. _verwandte_dateien
# =====================================================================

def test_verwandte_gleicher_ordner(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "a.py").write_text("")
    (tmp_path / "pkg" / "b.py").write_text("")
    out = explorer._verwandte_dateien(tmp_path, ["pkg/a.py"])
    assert "pkg/b.py" in out
    # Ausgangsdatei NICHT in Ausgabe.
    assert "pkg/a.py" not in out


def test_verwandte_keine_duplikate(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "a.py").write_text("")
    (tmp_path / "pkg" / "b.py").write_text("")
    out = explorer._verwandte_dateien(tmp_path, ["pkg/a.py", "pkg/b.py"])
    assert out.count("pkg/b.py") == 0  # b ist schon in dateien
    assert "pkg/a.py" not in out      # a ist schon in dateien


def test_verwandte_pfad_fehlt(tmp_path):
    assert explorer._verwandte_dateien(tmp_path, ["gibtsnicht.py"]) == []


# =====================================================================
# D. _explorer_system
# =====================================================================

def test_explorer_system_enthaelt_explorer_system():
    s = explorer._explorer_system("irgendeine frage")
    assert explorer.EXPLORER_SYSTEM in s


def test_explorer_system_trigger_debugging():
    s = explorer._explorer_system("ruff meckert im build")
    assert "## Skill: Systematic-Debugging" in s


def test_explorer_system_ohne_trigger():
    s = explorer._explorer_system("was ist die struktur")
    assert "## Skill: Systematic-Debugging" not in s


# =====================================================================
# E. _list_py_files
# =====================================================================

def test_list_py_files_ok(tmp_path):
    fake = type("R", (), {
        "stdout": "/a/x.py\n/a/y.py\n\n",
        "returncode": 0, "stderr": "",
    })()
    with patch("werkstatt.explorer.subprocess.run", return_value=fake):
        out = explorer._list_py_files(tmp_path)
    assert out == ["/a/x.py", "/a/y.py"]


def test_list_py_files_fehler(tmp_path):
    """Exception -> [] (fail-safe)."""
    with patch("werkstatt.explorer.subprocess.run",
               side_effect=RuntimeError("find weg")):
        assert explorer._list_py_files(tmp_path) == []


# =====================================================================
# F. _migrations_stand
# =====================================================================

def test_migrations_stand_leer(tmp_path):
    assert explorer._migrations_stand(tmp_path) == {}


def test_migrations_stand_mit_dateien(tmp_path):
    mdir = tmp_path / "data" / "migrations"
    mdir.mkdir(parents=True)
    (mdir / "0017_a.sql").write_text("")
    (mdir / "0018_b.sql").write_text("")
    out = explorer._migrations_stand(tmp_path)
    assert out["hoechste"] == "0018"
    assert out["naechste"] == "0019"
    assert "0017" in out["alle"]
    assert "0018" in out["alle"]


# =====================================================================
# G. run_explorer — Fail-closed-Pfade
# =====================================================================

def test_explorer_llm_fehler(tmp_path):
    """Fail-safe: leere, aber definierte Form (nicht None/{}).

    Der Aufrufer (run_planner) kann immer out["key_files"] lesen.
    """
    s = _state(tmp_path)
    with patch("werkstatt.explorer._messen", return_value={}), \
         patch("werkstatt.explorer.ask_llm",
               return_value=LLMReply(ok=False, error="kaputt")):
        out = explorer.run_explorer(s, "frage")
    assert out == {"findings": "", "key_files": [], "next_reads": []}
    ev = _kind(tmp_path, "explorer_llm_fehler")
    assert len(ev) == 1
    assert "kaputt" in ev[0]["fehler"]


def test_explorer_json_fehler(tmp_path):
    """Fail-safe: leere, aber definierte Form (nicht None/{})."""
    s = _state(tmp_path)
    with patch("werkstatt.explorer._messen", return_value={}), \
         patch("werkstatt.explorer.ask_llm",
               return_value=LLMReply(ok=True, content="kein json hier")):
        out = explorer.run_explorer(s, "frage")
    assert out == {"findings": "", "key_files": [], "next_reads": []}
    assert len(_kind(tmp_path, "explorer_json_fehler")) == 1


def test_explorer_result_audit(tmp_path):
    """Happy-Path: explorer_result-Audit-Event existiert."""
    s = _state(tmp_path)
    antwort = json.dumps({"key_files": [], "findings": "ok"})
    with patch("werkstatt.explorer._messen", return_value={}), \
         patch("werkstatt.explorer.ask_llm",
               return_value=LLMReply(ok=True, content=antwort)):
        out = explorer.run_explorer(s, "frage")
    assert isinstance(out, dict)
    assert len(_kind(tmp_path, "explorer_result")) == 1
