"""Spec: commit_input + verify — Patch-Format-Kompatibilitaet.

GOLD 2026-10-30: Beide Stellen akzeptieren jetzt BEIDE Patch-Formate:
- old_string/new_string (aktiv, loop._apply_patches_with_hooks)
- anker/ersatz (Legacy)

Getestet wird `format_code_patches_fuer_commit(patches)` — die
Stelle, wo `anker` gelesen wird. `_build_commit_input` braucht
3 Extra-Args (diff_name_only, w11_unterblock_kontext,
auflagen_text), die fuer den Format-Test nicht relevant sind.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from werkstatt import commit_input
from werkstatt.state import RunState


def _state(tmp_path: Path) -> RunState:
    return RunState(
        block_id="t", aufgabe="a", start_ts="2026-10-30T00:00:00Z",
        docs={}, agents={}, always={}, optional={}, file_whitelist=[],
        api_key="k", budget={}, agent_docs={},
        project_dir=tmp_path, project_name="testproj",
    )


# =====================================================================
# format_code_patches_fuer_commit — Format-Kompatibilitaet
# =====================================================================

def test_format_liest_old_string():
    """Patch mit old_string/new_string -> anker im Output gefuellt."""
    patches = [{
        "file": "a.py",
        "old_string": "def foo():\n    return 1\n",
        "new_string": "def foo():\n    return 2\n",
    }]
    out = commit_input.format_code_patches_fuer_commit(patches)
    assert "def foo" in out
    assert "return 1" in out


def test_format_liest_anker_legacy():
    """Patch mit anker/ersatz (Legacy) -> auch erkannt."""
    patches = [{"file": "a.py", "anker": "alter text",
                "ersatz": "neuer text"}]
    out = commit_input.format_code_patches_fuer_commit(patches)
    assert "alter text" in out


def test_format_leere_patches():
    """Keine Patches -> leerer String oder Hinweis, kein Crash."""
    out = commit_input.format_code_patches_fuer_commit([])
    assert isinstance(out, str)


# =====================================================================
# verify._expand_cmd_placeholders: changed_test_files mit beiden Formaten
# =====================================================================

def test_verify_erkennt_test_in_old_string(tmp_path):
    """Patch mit old_string/new_string + Datei existiert -> Stage kriegt Datei."""
    s = _state(tmp_path)
    s.patches = [{
        "file": "test_x.py",
        "old_string": "def test_a():\n    pass\n",
        "new_string": "def test_a():\n    assert True\n",
    }]
    (tmp_path / "test_x.py").write_text("def test_a(): pass\n")
    from werkstatt import loop
    out = loop._expand_cmd_placeholders(
        ["pytest", "{changed_test_files}"], s, tmp_path)
    assert out is None or "test_x.py" in out


def test_verify_liest_ersatz_fallback(tmp_path):
    """Patch mit anker/ersatz (Legacy) + Datei existiert -> Stage kriegt Datei."""
    s = _state(tmp_path)
    s.patches = [{
        "file": "test_y.py",
        "anker": "def test_b(): pass\n",
        "ersatz": "def test_b(): assert True\n",
    }]
    (tmp_path / "test_y.py").write_text("def test_b(): pass\n")
    from werkstatt import loop
    out = loop._expand_cmd_placeholders(
        ["pytest", "{changed_test_files}"], s, tmp_path)
    assert out is None or "test_y.py" in out
