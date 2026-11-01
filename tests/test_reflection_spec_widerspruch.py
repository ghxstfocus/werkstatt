"""OP-059c: Spec-Widerspruch-Erkennung via Bug-Text-Marker.

Der Loop soll nach 2 Runden Stagnation mit gleichem Bug-Text dann
human_review vorschlagen, wenn der Reviewer-Bug-Text auf einen
Widerspruch zwischen OP-Text und Diff hindeutet ("Task fordert X,
Diff macht Y"). Nicht bei generischen Bug-Texten ("fake bug").
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import werkstatt.builder as _builder_mod
from werkstatt import reflection as refl_mod


def _mk_state(tmp_path: Path, *, bug_text: str) -> SimpleNamespace:
    s = SimpleNamespace()
    s.project_dir = tmp_path
    s.project_name = "test"
    s.api_key = "dummy"
    s.last_verify_errors = []
    s.reviewer_bugs = [{"severity": "high", "description": bug_text}]
    s.patches = [{"file": "core/x.py", "old_string": "a", "new_string": "b"}]
    s.applied_count = 0
    s.reflection_history = []
    s.aktuelle_task = {"id": "t1", "task_files": ["core/x.py"]}
    return s


def _run_reflection(s, tmp_path, monkeypatch):
    """Helper: laesst reflection_loop 2 Runden stagnieren."""
    (tmp_path / "core").mkdir(exist_ok=True)
    (tmp_path / "core" / "x.py").write_text("b\n")

    monkeypatch.setattr(_builder_mod, "run_builder", lambda st: True)
    monkeypatch.setattr(
        refl_mod, "_apply_patches_with_diagnose",
        lambda st, p, **kw: (0, [{"file": "core/x.py",
                                  "old_string_len": 1,
                                  "grund": "kein_match",
                                  "vorkommen": 0}]),
    )
    # Verify ist ROT (Patch greift nicht UND Code ist falsch)
    monkeypatch.setattr(refl_mod, "_verify_patches",
                        lambda st, phase=None: False)
    monkeypatch.setattr(refl_mod, "_ruff_fix_changed", lambda st: None)
    monkeypatch.setattr(refl_mod, "_diff_hash_for_state", lambda st: "h")

    _audits: list[str] = []
    monkeypatch.setattr(
        refl_mod, "audit", lambda k, p, *a, **kw: _audits.append(k),
    )
    monkeypatch.setattr(refl_mod, "log_line", lambda *a, **kw: None)
    s._reflection_diff_hash = "h"  # type: ignore[attr-defined]
    rc = refl_mod._reflection_loop(
        s, max_runden=5, error_context="[]", phase="post_build",
    )
    return rc, _audits


def test_spec_widerspruch_bei_typischem_bug_text(
    tmp_path: Path, monkeypatch,
) -> None:
    """Bug-Text 'Task-Beschreibung fordert ... Diff ...' -> spec_widerspruch."""
    bug = (
        "Task-Beschreibung fordert explizit min_int = int(min_port). "
        "Der Diff macht stattdessen nur type: ignore. "
        "Die Narrowing-Loesung fehlt komplett."
    )
    s = _mk_state(tmp_path, bug_text=bug)
    rc, audits = _run_reflection(s, tmp_path, monkeypatch)
    assert getattr(s, "spec_widerspruch_erkannt", False) is True, (
        f"spec_widerspruch_erkannt fehlt; audits={audits}"
    )
    assert "loop_reflection_spec_widerspruch" in audits
    assert rc is True  # Signal fuer human_review


def test_kein_spec_widerspruch_bei_generischem_bug(
    tmp_path: Path, monkeypatch,
) -> None:
    """Bug-Text 'fake bug' (ohne Task-Diff-Marker) -> alter abort."""
    s = _mk_state(tmp_path, bug_text="fake bug")
    rc, audits = _run_reflection(s, tmp_path, monkeypatch)
    assert getattr(s, "spec_widerspruch_erkannt", False) is False, (
        f"spec_widerspruch faelschlich gesetzt; audits={audits}"
    )
    assert "loop_reflection_spec_widerspruch" not in audits
    assert rc is False  # alter abort
