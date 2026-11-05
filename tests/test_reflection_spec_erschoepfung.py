"""OP-059e: Erschoepfung mit Fortschritt = Spec-Widerspruch.

Testrunde 2 (18:49 OP-004) zeigte: Reflection dreht 5 Runden, jede
mit applied>0, verify bleibt rot (mypy: int(min_port) ungueltig).
_stagnation bleibt 0 (kein ruff, patches_applied>0, keine reviewer-
bugs), also greift weder OP-059c noch OP-059d. Loop endet via
Erschoepfung (return _verify_patches(False)), keine Spec-Erkennung.

Fix: am Ende von _reflection_loop pruefen, ob 2+ Runden mit
applied>0 und verify rot gelaufen sind. Dann spec_widerspruch.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import werkstatt.roles.builder as _builder_mod
from werkstatt import reflection as refl_mod


def _mk_state(tmp_path: Path) -> SimpleNamespace:
    s = SimpleNamespace()
    s.project_dir = tmp_path
    s.project_name = "test"
    s.api_key = "dummy"
    s.last_verify_errors = []
    s.reviewer_bugs = []
    s.patches = [{"file": "core/x.py", "old_string": "a", "new_string": "b"}]
    s.applied_count = 0
    s.reflection_history = []
    s.aktuelle_task = {"id": "t1", "task_files": ["core/x.py"]}
    return s


def test_erschoepfung_mit_fortschritt_setzt_spec_widerspruch(
    tmp_path: Path, monkeypatch,
) -> None:
    """3 Runden: jede applied>0, verify bleibt rot -> spec_widerspruch."""
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "x.py").write_text("b\n")
    s = _mk_state(tmp_path)

    monkeypatch.setattr(_builder_mod, "run_builder", lambda st: True)
    # Patch wird angewendet (applied=1)
    monkeypatch.setattr(
        refl_mod, "_apply_patches_with_diagnose",
        lambda st, p, **kw: (1, [{"file": "core/x.py",
                                  "old_string_len": 10,
                                  "grund": "ok", "vorkommen": 1}]),
    )
    # Verify immer rot
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
        s, max_runden=3, error_context="[]", phase="post_build",
    )
    assert getattr(s, "spec_widerspruch_erkannt", False) is True, (
        f"spec_widerspruch_erkannt fehlt; audits={_audits}"
    )
    assert "loop_reflection_spec_widerspruch_erschoepft" in _audits
    assert rc is True


def test_erschoepfung_ohne_fortschritt_kein_spec_widerspruch(
    tmp_path: Path, monkeypatch,
) -> None:
    """3 Runden, jede applied=0 -> kein spec_widerspruch (echter Fehler)."""
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "x.py").write_text("b\n")
    s = _mk_state(tmp_path)

    monkeypatch.setattr(_builder_mod, "run_builder", lambda st: True)
    monkeypatch.setattr(
        refl_mod, "_apply_patches_with_diagnose",
        lambda st, p, **kw: (0, [{"file": "core/x.py",
                                  "old_string_len": 10,
                                  "grund": "kein_match", "vorkommen": 0}]),
    )
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
        s, max_runden=3, error_context="[]", phase="post_build",
    )
    assert getattr(s, "spec_widerspruch_erkannt", False) is False, (
        f"spec_widerspruch faelschlich gesetzt; audits={_audits}"
    )


def test_erschoepfung_nach_einer_runde_kein_spec(
    tmp_path: Path, monkeypatch,
) -> None:
    """Nur 1 Runde gelaufen (max_runden=1) -> kein spec_widerspruch."""
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "x.py").write_text("b\n")
    s = _mk_state(tmp_path)

    monkeypatch.setattr(_builder_mod, "run_builder", lambda st: True)
    monkeypatch.setattr(
        refl_mod, "_apply_patches_with_diagnose",
        lambda st, p, **kw: (1, [{"file": "core/x.py",
                                  "old_string_len": 10,
                                  "grund": "ok", "vorkommen": 1}]),
    )
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
        s, max_runden=1, error_context="[]", phase="post_build",
    )
    # 1 Runde reicht nicht fuer Spec-Widerspruch
    assert getattr(s, "spec_widerspruch_erkannt", False) is False
