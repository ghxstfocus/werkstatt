"""OP-059: Reviewer-Stagnation-False-Positive.

Wenn der Reviewer einen HIGH-Bug meldet, die Reflection-Runde denselben
Bug erneut meldet UND der Diff sich zwischen den Runden nicht aendert,
ist das ein Reviewer-Fehlalarm (nicht: Task gescheitert).
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path

import werkstatt.roles.builder as _builder_mod
from werkstatt import reflection as refl_mod
from werkstatt.state import RunState

_here = Path(__file__).parent
if str(_here) not in _sys.path:
    _sys.path.insert(0, str(_here))
from factories import mk_state  # noqa: E402


def _mk_state(
    tmp_path: Path,
    *,
    last_verify_errors: list | None = None,
    reviewer_bugs: list | None = None,
    task_files: list | None = None,
) -> RunState:
    """Spec-State fuer Reviewer-False-Positive (OP-174 P3).

    Alle Felder in RunState deklariert. mk_state fail-loud bei
    Tippfehler in Feldnamen. Kein Sub-State.
    """
    return mk_state(
        project_dir=tmp_path,
        project_name="test",
        api_key="dummy",
        last_verify_errors=list(last_verify_errors or []),
        reviewer_bugs=list(
            reviewer_bugs or [{"severity": "high", "description": "fake bug"}]
        ),
        patches=[{"file": "core/x.py", "old_string": "a", "new_string": "b"}],
        applied_count=1,
        reflection_history=[],
        aktuelle_task={"task_files": task_files or ["core/x.py"]},
    )


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


def test_false_positive_nach_wirksamer_erster_runde(
    tmp_path: Path, monkeypatch
) -> None:
    """Live-Beleg 15:16 OP-002b3: Runde 1 wirksam, Runde 2 idempotent.

    Der Hash aendert sich zwischen _reflection_diff_hash (vor Reflexion)
    und Runde 2, weil Runde 1 tatsaechlich 2 Patches angewendet hat.
    Aber Runde 2 selbst ist idempotent (_hash_vorher == _hash_nachher)
    und Verify gruen + keine echten errors. Das ist ein
    Reviewer-Fehlalarm, kein Task-Fail.

    Vor Fix: _hash_ref-Bedingung blockierte das, weil
    _hash_nachher != _hash_ref (Runde 1 hatte den Hash geaendert).
    Nach Fix: _hash_ref-Bedingung entfernt; _hash_vorher == _hash_nachher
    reicht als Idempotenz-Beweis.
    """
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "x.py").write_text("b\n")
    s = _mk_state(tmp_path)

    # Simuliert: Hash hat sich in Runde 1 geaendert (echte Anwendung),
    # in Runde 2 idempotent (gleicher Hash vor/nach).
    _hash_werte = iter(["hash-nach-runde1", "hash-nach-runde1"])
    monkeypatch.setattr(
        refl_mod, "_diff_hash_for_state", lambda st: next(_hash_werte),
    )
    _setup_common_mocks(monkeypatch, verify_ok=True)
    _audits = _collect_audits(monkeypatch)

    # _hash_ref ist der Hash VOR Reflexion (nach t1, aber vor R1).
    # Runde 1 hat ihn geaendert -> _hash_ref != _hash_nachher.
    s._reflection_diff_hash = "hash-nach-t1"  # type: ignore[attr-defined]
    rc = refl_mod._reflection_loop(
        s, max_runden=2, error_context="[]", phase="post_build"
    )
    assert rc is True, (
        "Runde 1 wirksam + Runde 2 idempotent + Verify gruen "
        "-> false_positive erwartet"
    )
    assert "reviewer_stagnation_false_positive" in _audits
    assert getattr(s, "reviewer_stagnation_false_positive", False) is True
