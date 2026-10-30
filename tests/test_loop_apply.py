"""Spec: Apply-Pfad — deterministische Kernfunktionen.

Nicht in dieser Datei (gehoeren zu Phases/Integration):
- _verify_patches               (liest verify.json, ruft pytest/ruff)
- _verify_stage_with_heartbeat  (Threading + subprocess)

Getestet hier (bisher 0 Spec-Tests):
- _apply_one_patch        (4 Rueckgabemodi: exact/strip/context_only/fail)
- _patches_wirklich_angewendet (fail-closed)
- _expand_cmd_placeholders (Platzhalter-Expansion)
- _resolve_venv_cmd        (venv-Binary-Praeferenz)
- _apply_patches_with_hooks (Hook-blocked vs. erlaubt)

Hinweis: apply.py (apply_code_patches) wurde am 2026-10-30
entfernt (Dead Code seit Loop-Neubau, kein Aufrufer,
keine Audit-Treffer seit 2026-10-19).
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from werkstatt import loop
from werkstatt.state import RunState


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
# _apply_one_patch — 4 Rueckgabemodi
# =====================================================================

def test_apply_one_patch_exact():
    out, modus = loop._apply_one_patch("a\nb\nc\n", "b", "B")
    assert modus == "exact"
    assert out == "a\nB\nc\n"


def test_apply_one_patch_strip():
    """Woertlich nicht gefunden, aber old.lstrip() im content -> 'strip'.

    Wichtig: der Code macht new.lstrip() — fuehrende Leerzeichen
    von new gehen verloren (Design: Einrueckung kommt aus content).
    """
    content = "abc\ndef\n"
    old = "  def\n"
    new = "  XYZ\n"
    out, modus = loop._apply_one_patch(content, old, new)
    assert modus == "strip"
    assert out == "abc\nXYZ\n"


def test_apply_one_patch_context_only():
    content = "def f():\n    return 1\n"
    old = "irgendein kontext\n\ndef f():\n    return 1\n"
    new = "irgendein kontext\n\ndef f():\n    return 2\n"
    out, modus = loop._apply_one_patch(content, old, new)
    assert modus == "context_only"
    assert "return 2" in out


def test_apply_one_patch_context_only_mit_strip():
    content = "def f():\n    return 1\n"
    old = "  irgendein kontext\n\ndef f():\n    return 1\n"
    new = "  irgendein kontext\n\ndef f():\n    return 2\n"
    out, modus = loop._apply_one_patch(content, old, new)
    assert modus == "context_only"
    assert "return 2" in out


def test_apply_one_patch_fail():
    content = "abc\n"
    out, modus = loop._apply_one_patch(content, "xyz", "neu")
    assert modus == "fail"
    assert out == content


def test_apply_one_patch_leerer_old():
    """Leerer old-String -> exact, content.replace('', 'X', 1) = 'Xabc'."""
    out, modus = loop._apply_one_patch("abc", "", "X")
    assert modus == "exact"
    assert out == "Xabc"


def test_apply_one_patch_nur_erster_treffer():
    content = "a\na\na\n"
    out, modus = loop._apply_one_patch(content, "a", "X")
    assert modus == "exact"
    assert out == "X\na\na\n"


# =====================================================================
# _patches_wirklich_angewendet — fail-closed
# =====================================================================

def test_patches_angewendet_keine_patches(tmp_path):
    s = _state(tmp_path)
    s.patches = []
    s.applied_count = 0
    assert loop._patches_wirklich_angewendet(s) is False


def test_patches_angewendet_keine_applied_count(tmp_path):
    s = _state(tmp_path)
    s.patches = [{"file": "a.py"}]
    s.applied_count = 0
    assert loop._patches_wirklich_angewendet(s) is False


def test_patches_angewendet_mit_count(tmp_path):
    s = _state(tmp_path)
    s.patches = [{"file": "a.py"}]
    s.applied_count = 1
    assert loop._patches_wirklich_angewendet(s) is True


# =====================================================================
# _expand_cmd_placeholders
# =====================================================================

def test_placeholders_keine(tmp_path):
    s = _state(tmp_path)
    out = loop._expand_cmd_placeholders(["pytest", "-q"], s, tmp_path)
    assert out == ["pytest", "-q"]


def test_placeholders_changed_files(tmp_path):
    s = _state(tmp_path)
    (tmp_path / "a.py").write_text("")
    (tmp_path / "b.py").write_text("")
    s.patches = [{"file": "a.py"}, {"file": "b.py"},
                 {"file": "fehlt.py"}]
    out = loop._expand_cmd_placeholders(
        ["pytest", "{changed_files}"], s, tmp_path)
    assert "a.py" in out
    assert "b.py" in out
    assert "fehlt.py" not in out


def test_placeholders_changed_test_files(tmp_path):
    s = _state(tmp_path)
    (tmp_path / "test_a.py").write_text("")
    (tmp_path / "b.py").write_text("")
    s.patches = [{"file": "test_a.py"}, {"file": "b.py"}]
    out = loop._expand_cmd_placeholders(
        ["pytest", "{changed_test_files}"], s, tmp_path)
    assert out is None or "test_a.py" in out


def test_placeholders_changed_py_files(tmp_path):
    s = _state(tmp_path)
    (tmp_path / "a.py").write_text("")
    (tmp_path / "b.txt").write_text("")
    s.patches = [{"file": "a.py"}, {"file": "b.txt"}]
    out = loop._expand_cmd_placeholders(
        ["ruff", "{changed_py_files}"], s, tmp_path)
    assert out is None or "a.py" in out


def test_placeholders_skip_wenn_leer(tmp_path):
    s = _state(tmp_path)
    s.patches = []
    out = loop._expand_cmd_placeholders(
        ["pytest", "{changed_files}"], s, tmp_path)
    assert out is None


# =====================================================================
# _resolve_venv_cmd
# =====================================================================

def test_resolve_venv_cmd_kein_venv(tmp_path):
    assert loop._resolve_venv_cmd(["pytest", "-q"], tmp_path) == \
        ["pytest", "-q"]


def test_resolve_venv_cmd_mit_venv(tmp_path):
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    exe = tmp_path / ".venv" / "bin" / "pytest"
    exe.write_text("")
    exe.chmod(0o755)
    out = loop._resolve_venv_cmd(["pytest", "-q"], tmp_path)
    assert out[0] == str(exe)
    assert out[1:] == ["-q"]


def test_resolve_venv_cmd_leeres_cmd(tmp_path):
    assert loop._resolve_venv_cmd([], tmp_path) == []


def test_resolve_venv_cmd_kein_exec_bit(tmp_path):
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    exe = tmp_path / ".venv" / "bin" / "pytest"
    exe.write_text("")
    exe.chmod(0o644)
    assert loop._resolve_venv_cmd(["pytest"], tmp_path) == ["pytest"]


# =====================================================================
# _apply_patches_with_hooks
# =====================================================================

def test_apply_hooks_blocked(tmp_path):
    """pre_tool_use blockt -> 0 angewendet, Audit-Event."""
    s = _state(tmp_path)
    with patch("werkstatt.loop._call_hook",
               return_value={"allow": False, "reason": "test"}):
        n = loop._apply_patches_with_hooks(
            s, [{"file": "a.py", "old_string": "x", "new_string": "y"}],
            phase_label="test")
    assert n == 0
    assert len(_kind(tmp_path, "loop_hook_blocked")) >= 1


def test_apply_hooks_erlaubt_kein_patch(tmp_path):
    """Hooks erlauben, aber Patch passt nicht -> 0 angewendet."""
    s = _state(tmp_path)
    (tmp_path / "a.py").write_text("abc\n")
    with patch("werkstatt.loop._call_hook",
               return_value={"allow": True}):
        n = loop._apply_patches_with_hooks(
            s, [{"file": "a.py", "old_string": "xyz", "new_string": "y"}],
            phase_label="test")
    assert n == 0
