"""OP-060a: Diagnose-Grund im Audit statt {} bei Patch-nicht-angewendet.

Live-Beleg OP-002b2 12:51 t2 + OP-002b3 13:22 t2: Loop meldet
`loop_reflection_patch_nicht_angewendet` mit nur {"runde": N}. Ohne
Grund (kein_match / mehrdeutig / no_effect / write_failed / datei_fehlt)
war der Fehler nicht diagnostizierbar.

OP-060a baut:
- _diagnose_patch(content, old, new) -> dict mit {grund, old_string_len,
  vorkommen, match}.
- _apply_patches_with_diagnose(state, patches) -> (applied, diagnosen).
- _apply_patches_with_hooks bleibt Signatur-kompatibel (Rueckgabe int).
- reflection._reflection_loop auditiert bei applied==0 zusaetzlich
  'loop_reflection_patch_unwirksam' mit diagnosen.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import werkstatt.roles.builder as _builder_mod
from werkstatt import reflection as refl_mod
from werkstatt.apply_patches import (
    _apply_patches_with_diagnose,
    _diagnose_patch,
)

# ═══════════════════════════════════════════════════════════════
# A. _diagnose_patch — Unit-Tests (4 Faelle aus OP-060-Spec)
# ═══════════════════════════════════════════════════════════════


def test_diagnose_kein_match() -> None:
    d = _diagnose_patch("abc\ndef\n", "xyz", "neu")
    assert d["grund"] == "kein_match"
    assert d["old_string_len"] == 3
    assert d["vorkommen"] == 0


def test_diagnose_mehrdeutig() -> None:
    d = _diagnose_patch("foo\nfoo\nbar\n", "foo", "baz")
    assert d["grund"] == "mehrdeutig"
    assert d["old_string_len"] == 3
    assert d["vorkommen"] == 2


def test_diagnose_no_effect() -> None:
    d = _diagnose_patch("foo\n", "foo", "foo")
    assert d["grund"] == "no_effect"
    assert d["old_string_len"] == 3


def test_diagnose_ok() -> None:
    d = _diagnose_patch("abc\n", "abc", "xyz")
    assert d["grund"] == "ok"
    assert d["old_string_len"] == 3
    assert d["vorkommen"] == 1


def test_diagnose_leer() -> None:
    d = _diagnose_patch("abc\n", "", "xyz")
    assert d["grund"] == "leer"
    assert d["old_string_len"] == 0


# ═══════════════════════════════════════════════════════════════
# B. _apply_patches_with_diagnose — Datei-Faelle
# ═══════════════════════════════════════════════════════════════


def _mk_state(tmp_path: Path) -> SimpleNamespace:
    s = SimpleNamespace()
    s.project_dir = tmp_path
    s.project_name = "test"
    return s


def _mk_file(tmp_path: Path, rel: str, content: str) -> None:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def test_apply_diagnose_kein_match(tmp_path: Path, monkeypatch) -> None:
    _mk_file(tmp_path, "core/x.py", "abc\n")
    monkeypatch.setattr(
        "werkstatt.apply_patches._call_hook",
        lambda n, p: {"allow": True},
    )
    s = _mk_state(tmp_path)
    patches = [{"file": "core/x.py", "action": "update",
                "old_string": "xyz", "new_string": "neu"}]
    applied, diags = _apply_patches_with_diagnose(s, patches)
    assert applied == 0
    assert len(diags) == 1
    assert diags[0]["grund"] == "kein_match"
    assert diags[0]["file"] == "core/x.py"


def test_apply_diagnose_datei_fehlt(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "werkstatt.apply_patches._call_hook",
        lambda n, p: {"allow": True},
    )
    s = _mk_state(tmp_path)
    patches = [{"file": "core/missing.py", "action": "update",
                "old_string": "a", "new_string": "b"}]
    applied, diags = _apply_patches_with_diagnose(s, patches)
    assert applied == 0
    assert diags[0]["grund"] == "datei_fehlt"


def test_apply_diagnose_mehrdeutig_wird_angewendet_aber_gemeldet(
    tmp_path: Path, monkeypatch
) -> None:
    """Altes Verhalten bleibt: bei mehrdeutig wird blind ersetzt.

    OP-060a meldet nur, entscheidet aber nicht (Ablehnen waere OP-060b).
    """
    _mk_file(tmp_path, "core/x.py", "foo\nfoo\nbar\n")
    monkeypatch.setattr(
        "werkstatt.apply_patches._call_hook",
        lambda n, p: {"allow": True},
    )
    s = _mk_state(tmp_path)
    patches = [{"file": "core/x.py", "action": "update",
                "old_string": "foo", "new_string": "baz"}]
    applied, diags = _apply_patches_with_diagnose(s, patches)
    assert applied == 1
    assert diags[0]["grund"] == "mehrdeutig"
    assert diags[0]["vorkommen"] == 2


def test_apply_diagnose_ok(tmp_path: Path, monkeypatch) -> None:
    _mk_file(tmp_path, "core/x.py", "abc\n")
    monkeypatch.setattr(
        "werkstatt.apply_patches._call_hook",
        lambda n, p: {"allow": True},
    )
    s = _mk_state(tmp_path)
    patches = [{"file": "core/x.py", "action": "update",
                "old_string": "abc", "new_string": "xyz"}]
    applied, diags = _apply_patches_with_diagnose(s, patches)
    assert applied == 1
    assert diags[0]["grund"] == "ok"


# ═══════════════════════════════════════════════════════════════
# C. reflection._reflection_loop — audit mit diagnosen
# ═══════════════════════════════════════════════════════════════


def _mk_refl_state(tmp_path: Path) -> SimpleNamespace:
    s = SimpleNamespace()
    s.project_dir = tmp_path
    s.project_name = "test"
    s.api_key = "dummy"
    s.last_verify_errors = []
    s.reviewer_bugs = [{"severity": "high", "description": "fake"}]
    s.patches = [{"file": "core/x.py", "old_string": "a", "new_string": "b"}]
    s.applied_count = 0
    s.reflection_history = []
    s.aktuelle_task = {"task_files": ["core/x.py"]}
    return s


def test_reflection_audit_enthaelt_diagnosen(
    tmp_path: Path, monkeypatch
) -> None:
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "x.py").write_text("b\n")
    s = _mk_refl_state(tmp_path)

    monkeypatch.setattr(_builder_mod, "run_builder", lambda st: True)
    monkeypatch.setattr(
        refl_mod, "_apply_patches_with_diagnose",
        lambda st, p, **kw: (0, [{"file": "core/x.py",
                                  "old_string_len": 1,
                                  "grund": "kein_match",
                                  "vorkommen": 0}]),
    )
    monkeypatch.setattr(
        refl_mod, "_verify_patches", lambda st, phase=None: False
    )
    monkeypatch.setattr(refl_mod, "_ruff_fix_changed", lambda st: None)
    monkeypatch.setattr(refl_mod, "_diff_hash_for_state", lambda st: "h")

    _audits: list[tuple] = []
    monkeypatch.setattr(
        refl_mod, "audit",
        lambda k, p, *a, **kw: _audits.append((k, p)),
    )
    monkeypatch.setattr(refl_mod, "log_line", lambda *a, **kw: None)

    refl_mod._reflection_loop(
        s, max_runden=2, error_context="[]", phase="post_build"
    )

    kinds = [k for k, _ in _audits]
    assert "loop_reflection_patch_unwirksam" in kinds
    payloads = [p for k, p in _audits if k == "loop_reflection_patch_unwirksam"]
    assert payloads, "kein payload fuer loop_reflection_patch_unwirksam"
    assert "diagnosen" in payloads[0]
    assert payloads[0]["diagnosen"][0]["grund"] == "kein_match"
