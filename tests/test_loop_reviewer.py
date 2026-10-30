"""Spec: Reviewer — Wrapper + Fail-closed-Pfade.

Nicht dupliziert:
- run_reviewer-Happy       -> test_reviewer_agent.py, test_k4_reviewer_diff.py
- _get_git_diff-Happy      -> test_k4_reviewer_diff.py
- _reviewer_history_block  -> test_k40_reviewer_history.py
- run_phase_end_review     -> test_k16_reviewer_zieldatei.py (happy)

Getestet hier:
- _reviewer_system + SEMANTIK-CHECK (P0/P1 aa7881f, 0 bestehende Tests)
- _get_git_diff Fehlerverhalten (RuntimeError bei rc/dubious)
- ALLE Fail-closed-Pfade in run_reviewer/run_phase_end_review
  (bisher 0 Tests gegen Audit-Kinds)
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from werkstatt import reviewer
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
# A. _reviewer_system + SEMANTIK-CHECK
# =====================================================================

def test_reviewer_system_enthaelt_reviewer_system():
    s = reviewer._reviewer_system()
    assert reviewer.REVIEWER_SYSTEM in s


def test_reviewer_system_enthaelt_semantik_check():
    s = reviewer._reviewer_system()
    assert "## SEMANTIK-CHECK" in s


def test_reviewer_system_semantik_drei_faelle():
    """Alle drei HIGH-Bug-Faelle aus dem Prompt sind woertlich praesent."""
    s = reviewer._reviewer_system()
    # Fall 1: Task nennt Funktion X, Diff nutzt Y
    assert "der Diff aber eine andere" in s
    # Fall 2: bestehender Aufruf entfernt
    assert "bestehender Aufruf einer Funktion entfernt" in s
    # Fall 3: API erfunden
    assert "API erfunden" in s


def test_reviewer_system_stabil():
    assert reviewer._reviewer_system() == reviewer._reviewer_system()


# =====================================================================
# B. _get_git_diff — Fehlerverhalten
# =====================================================================

def test_git_diff_runtime_error_bei_rc_fehler(tmp_path):
    """rc != 0 -> RuntimeError (fail-closed, NICHT 'kein Diff')."""
    fake = type("R", (), {
        "returncode": 128,
        "stdout": "",
        "stderr": "fatal: not a git repository",
    })()
    with patch("werkstatt.reviewer.subprocess.run", return_value=fake):
        with pytest.raises(RuntimeError) as exc:
            reviewer._get_git_diff(tmp_path)
    assert "git diff fehlgeschlagen" in str(exc.value)


def test_git_diff_runtime_error_bei_dubious(tmp_path):
    """stderr enthaelt 'dubious' -> RuntimeError (auch bei rc==0)."""
    fake = type("R", (), {
        "returncode": 0,
        "stdout": "",
        "stderr": "fatal: detected dubious ownership in repository",
    })()
    with patch("werkstatt.reviewer.subprocess.run", return_value=fake):
        with pytest.raises(RuntimeError):
            reviewer._get_git_diff(tmp_path)


# =====================================================================
# C. run_reviewer — Fail-closed-Pfade
# =====================================================================

def test_reviewer_kein_key(tmp_path):
    s = _state(tmp_path, api_key="")
    assert reviewer.run_reviewer(s) is False
    assert len(_kind(tmp_path, "reviewer_kein_key")) == 1


def test_reviewer_diff_fehler(tmp_path):
    s = _state(tmp_path)
    with patch("werkstatt.reviewer._get_git_diff",
               side_effect=RuntimeError("boom")):
        assert reviewer.run_reviewer(s) is False
    ev = _kind(tmp_path, "reviewer_diff_fehler")
    assert len(ev) == 1
    assert "boom" in ev[0]["fehler"]


def test_reviewer_kein_diff_aber_patches(tmp_path):
    """Patches gesetzt, Diff leer -> False (fail-closed)."""
    s = _state(tmp_path)
    s.patches = [{"file": "a.py", "old_string": "x", "new_string": "y"}]
    with patch("werkstatt.reviewer._get_git_diff", return_value=""):
        assert reviewer.run_reviewer(s) is False
    ev = _kind(tmp_path, "reviewer_kein_diff_aber_patches")
    assert len(ev) == 1
    assert ev[0]["patches"] == 1


def test_reviewer_kein_diff_kein_patch(tmp_path):
    """Diff leer, keine Patches -> True (legitim)."""
    s = _state(tmp_path)
    with patch("werkstatt.reviewer._get_git_diff", return_value=""):
        assert reviewer.run_reviewer(s) is True
    assert len(_kind(tmp_path, "reviewer_kein_diff_kein_patch")) == 1


def test_reviewer_llm_fehler(tmp_path):
    s = _state(tmp_path)
    with patch("werkstatt.reviewer._get_git_diff",
               return_value="+ neue zeile\n"), \
         patch("werkstatt.reviewer.ask_llm",
               return_value=LLMReply(ok=False, error="kaputt")):
        assert reviewer.run_reviewer(s) is False
    ev = _kind(tmp_path, "reviewer_llm_fehler")
    assert len(ev) == 1
    assert "kaputt" in ev[0]["fehler"]


def test_reviewer_json_fehler(tmp_path):
    s = _state(tmp_path)
    with patch("werkstatt.reviewer._get_git_diff",
               return_value="+ neue zeile\n"), \
         patch("werkstatt.reviewer.ask_llm",
               return_value=LLMReply(ok=True, content="kein json hier")):
        assert reviewer.run_reviewer(s) is False
    assert len(_kind(tmp_path, "reviewer_json_fehler")) == 1


# =====================================================================
# D. run_phase_end_review — Fail-closed-Pfade
# =====================================================================

def test_phase_review_kein_key(tmp_path):
    s = _state(tmp_path, api_key="")
    assert reviewer.run_phase_end_review(s) is False
    assert len(_kind(tmp_path, "reviewer_phase_kein_key")) == 1


def test_phase_review_keine_task_files(tmp_path):
    s = _state(tmp_path)
    s.tasks = []
    assert reviewer.run_phase_end_review(s) is False
    assert len(_kind(tmp_path, "reviewer_phase_keine_task_files")) == 1


def test_phase_review_kein_diff(tmp_path):
    s = _state(tmp_path)
    s.tasks = [{"id": "t1", "task_files": ["a.py"]}]
    with patch("werkstatt.reviewer._get_git_diff", return_value=""):
        assert reviewer.run_phase_end_review(s) is False
    assert len(_kind(tmp_path, "reviewer_phase_kein_diff")) == 1


def test_phase_review_llm_fehler(tmp_path):
    s = _state(tmp_path)
    s.tasks = [{"id": "t1", "task_files": ["a.py"]}]
    with patch("werkstatt.reviewer._get_git_diff",
               return_value="+ zeile\n"), \
         patch("werkstatt.reviewer.ask_llm",
               return_value=LLMReply(ok=False, error="rate limit")):
        assert reviewer.run_phase_end_review(s) is False
    ev = _kind(tmp_path, "reviewer_phase_call_failed")
    assert len(ev) == 1


def test_phase_review_json_fehler(tmp_path):
    s = _state(tmp_path)
    s.tasks = [{"id": "t1", "task_files": ["a.py"]}]
    with patch("werkstatt.reviewer._get_git_diff",
               return_value="+ zeile\n"), \
         patch("werkstatt.reviewer.ask_llm",
               return_value=LLMReply(ok=True, content="nur prosa")):
        assert reviewer.run_phase_end_review(s) is False
    assert len(_kind(tmp_path, "reviewer_phase_json_fehler")) == 1
