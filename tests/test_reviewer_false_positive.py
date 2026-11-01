"""OP-059: Reviewer-Stagnation-False-Positive.

Wenn der Reviewer einen HIGH-Bug meldet, die Reflection-Runde denselben
Bug erneut meldet UND der Diff sich zwischen den Runden nicht aendert,
ist das ein Reviewer-Fehlalarm (nicht: Task gescheitert).
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import werkstatt.builder as _builder_mod
from werkstatt import reflection as refl_mod


def _mk_state(
    tmp_path: Path,
    *,
    last_verify_errors: list | None = None,
    reviewer_bugs: list | None = None,
    task_files: list | None = None,
) -> SimpleNamespace:
    s = SimpleNamespace()
    s.project_dir = tmp_path
    s.project_name = "test"
    s.api_key = "dummy"
    s.last_verify_errors = list(last_verify_errors or [])
    s.reviewer_bugs = list(
        reviewer_bugs or [{"severity": "high", "description": "fake bug"}]
    )
    s.patches = [{"file": "core/x.py", "old_string": "a", "new_string": "b"}]
    s.applied_count = 1
    s.reflection_history = []
    s.aktuelle_task = {"task_files": task_files or ["core/x.py"]}
    return s


def _setup_common_mocks(monkeypatch, *, verify_ok: bool):
    monkeypatch.setattr(_builder_mod, "run_builder", lambda st: True)
    monkeypatch.setattr(
        refl_mod, "_apply_patches_with_diagnose",
        lambda st, p, **kw: (0, [{"file": "core/x.py",
                                  "old_string_len": 1,
                                  "grund": "kein_match",
                                  "vorkommen": 0}]),
    )
    monkeypatch.setattr(
        refl_mod, "_verify_patches", lambda st, phase=None: verify_ok
    )
    monkeypatch.setattr(refl_mod, "_ruff_fix_changed", lambda st: None)


def _collect_audits(monkeypatch) -> list[str]:
    _audits: list[str] = []
    monkeypatch.setattr(
        refl_mod, "audit", lambda k, p, *a, **kw: _audits.append(k)
    )
    monkeypatch.setattr(refl_mod, "log_line", lambda *a, **kw: None)
    return _audits


def test_false_positive_wenn_diff_unveraendert_und_verify_gruen(
    tmp_path: Path, monkeypatch
) -> None:
    """Idempotenter Patch + gleicher Diff + Verify gruen -> false_positive."""
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "x.py").write_text("b\n")
    s = _mk_state(tmp_path)

    monkeypatch.setattr(refl_mod, "_diff_hash_for_state", lambda st: "abc123")
    _setup_common_mocks(monkeypatch, verify_ok=True)
    _audits = _collect_audits(monkeypatch)

    s._reflection_diff_hash = "abc123"  # type: ignore[attr-defined]
    rc = refl_mod._reflection_loop(
        s, max_runden=2, error_context="[]", phase="post_build"
    )
    assert rc is True
    assert "reviewer_stagnation_false_positive" in _audits
    assert getattr(s, "reviewer_stagnation_false_positive", False) is True


def test_kein_false_positive_wenn_diff_sich_aendert(
    tmp_path: Path, monkeypatch
) -> None:
    """Diff zwischen Runden veraendert -> keine false_positive-Erkennung."""
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "x.py").write_text("b\n")
    s = _mk_state(tmp_path)

    _counter = {"n": 0}

    def _hash(st):
        _counter["n"] += 1
        return f"hash{_counter['n']}"

    monkeypatch.setattr(refl_mod, "_diff_hash_for_state", _hash)
    _setup_common_mocks(monkeypatch, verify_ok=False)
    _audits = _collect_audits(monkeypatch)

    s._reflection_diff_hash = "anderer-hash"  # type: ignore[attr-defined]
    rc = refl_mod._reflection_loop(
        s, max_runden=2, error_context="[]", phase="post_build"
    )
    assert rc is False
    assert "reviewer_stagnation_false_positive" not in _audits
    assert not getattr(s, "reviewer_stagnation_false_positive", False)


def test_kein_false_positive_wenn_verify_rot(
    tmp_path: Path, monkeypatch
) -> None:
    """Verify rot (echter Fehler) -> keine false_positive-Erkennung."""
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "x.py").write_text("b\n")
    s = _mk_state(tmp_path, last_verify_errors=["ruff F401: unused import"])

    monkeypatch.setattr(refl_mod, "_diff_hash_for_state", lambda st: "abc123")
    _setup_common_mocks(monkeypatch, verify_ok=False)
    _audits = _collect_audits(monkeypatch)

    s._reflection_diff_hash = "abc123"  # type: ignore[attr-defined]
    rc = refl_mod._reflection_loop(
        s, max_runden=2, error_context="[]", phase="post_build"
    )
    assert rc is False
    assert "reviewer_stagnation_false_positive" not in _audits
    assert not getattr(s, "reviewer_stagnation_false_positive", False)
