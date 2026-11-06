"""OP-061: builder_failed-Zustandsverwirrung (Task-Runner-Bug).

Live-Beleg OP-002b3-Loop (13:22):
- t1 baute die Aenderung (Patch angewendet). Reflection setzte
  auftrag_bereits_erfuellt (Datei im Zielzustand), aber der
  reviewer_rejected-Pfad prueft das Flag nicht -> t1 als failed.
- t2 lief gegen dieselbe Datei, sah keinen wirksamen Patch
  (builder_patch_invalid), wurde als builder_failed markiert —
  obwohl t1 die Datei bereits im Zielzustand hinterlassen hatte.

Drei Wurzeln (A/B/C):
- A: auftrag_bereits_erfuellt-Flag im reviewer_rejected-Pfad pruefen.
- B: Datei bereits durch prior done-Task geschrieben? -> done.
- C: loop_task_failed im builder_failed-Pfad mit Grund (kein {}).

Tests:
- test_builder_failed_mit_grund: Audit loop_task_failed enthaelt
  grund="builder_failed".
- test_builder_patch_bereits_erfuellt: t2 kein wirksamer Patch +
  prior done auf gleicher Datei + verify gruen -> t2 done + Audit.
- test_builder_patch_nicht_erfuellt_ohne_prior: t2 kein wirksamer
  Patch + KEIN prior done auf gleicher Datei -> t2 failed.
- test_auftrag_bereits_erfuellt_im_pre_reviewer_patch_fail: Reflection
  False + Flag True + Verify gruen -> done statt failed.
"""
from __future__ import annotations

from pathlib import Path

from werkstatt import loop as loop_mod
from werkstatt.state import RunState


def _mk_state(tmp_path: Path, *, tasks: list[dict]) -> RunState:
    (tmp_path / ".werkstatt").mkdir()
    (tmp_path / ".werkstatt" / "verify.json").write_text(
        '{"stages": [{"id": "pc", "command": ["python3", "-c", "pass"]}]}'
    )
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "x.py").write_text("b = 2\n")
    s = RunState(
        block_id="p", aufgabe="a", start_ts="", docs={}, agents={},
        always={}, optional={}, file_whitelist=[], api_key="dummy",
        budget={}, agent_docs={}, project_dir=tmp_path, project_name="p",
    )
    s.tasks = tasks
    s.phasen = []
    return s


def _common_mocks(monkeypatch, *, builder_fn, reviewer_fn, reflection_fn):
    """Gemeinsame Mocks fuer Phase-Tasks-Loop-Tests."""
    monkeypatch.setattr(loop_mod, "_plan_gate", lambda s: True)
    monkeypatch.setattr(
        loop_mod, "run_explorer",
        lambda s, a: {"key_files": [], "findings": "", "next_reads": []},
    )
    monkeypatch.setattr(loop_mod, "run_builder", builder_fn)
    monkeypatch.setattr(loop_mod, "_verify_patches", lambda s, phase=None: True)
    monkeypatch.setattr(loop_mod, "_call_hook", lambda n, p: {"allow": True})
    monkeypatch.setattr(loop_mod, "run_reviewer", reviewer_fn)
    monkeypatch.setattr(loop_mod, "_reflection_loop", reflection_fn)
    from werkstatt import reviewer as _rv_mod
    monkeypatch.setattr(_rv_mod, "run_phase_end_review", lambda s: True)
    for _fn in ("header", "step", "task", "task_ok", "task_failed",
                "group_start", "group_end", "footer"):
        if hasattr(loop_mod, _fn):
            monkeypatch.setattr(loop_mod, _fn, lambda *a, **kw: None)


def test_builder_failed_mit_grund(tmp_path: Path, monkeypatch) -> None:
    """C: Audit loop_task_failed enthaelt grund='builder_failed'."""
    st = _mk_state(tmp_path, tasks=[
        {"id": "t1", "name": "T1", "action": "update",
         "task_files": ["core/x.py"]},
    ])
    _audits: list[tuple] = []
    monkeypatch.setattr(loop_mod, "audit",
                        lambda k, p, *a, **kw: _audits.append((k, p)))

    def _builder_fail(_s):
        _s.patches = []
        return False

    def _no_rev(_s):
        return True

    def _no_refl(_s, **kw):
        return False

    _common_mocks(
        monkeypatch,
        builder_fn=_builder_fail,
        reviewer_fn=_no_rev,
        reflection_fn=_no_refl,
    )

    loop_mod.run_pipeline_loop("p", "a", [st])
    # Task ist failed — aber das Audit MUSS den Grund nennen.
    failed_kinds = [
        p for k, p in _audits if k == "loop_task_failed"
    ]
    assert failed_kinds, (
        f"kein loop_task_failed-Audit; kinds={[k for k, _ in _audits]}"
    )
    assert any(
        isinstance(p, dict) and p.get("grund") == "builder_failed"
        for p in failed_kinds
    ), f"loop_task_failed ohne grund=builder_failed: {failed_kinds}"


def test_builder_patch_bereits_erfuellt(
    tmp_path: Path, monkeypatch
) -> None:
    """B: t2 kein wirksamer Patch, prior done auf gleicher Datei -> done."""
    st = _mk_state(tmp_path, tasks=[
        {"id": "t1", "name": "T1", "action": "update",
         "task_files": ["core/x.py"]},
        {"id": "t2", "name": "T2", "action": "update",
         "task_files": ["core/x.py"]},
    ])
    _audits: list[tuple] = []
    _builder_calls = {"n": 0}
    # t1-Patch old="a = 1", new="b = 2" muss auf Datei passen.
    (tmp_path / "core" / "x.py").write_text("a = 1\n")

    monkeypatch.setattr(loop_mod, "audit",
                        lambda k, p, *a, **kw: _audits.append((k, p)))

    def _builder(_s):
        _builder_calls["n"] += 1
        if _builder_calls["n"] == 1:
            _s.patches = [{"action": "update", "file": "core/x.py",
                           "old_string": "a = 1", "new_string": "b = 2"}]
            _s.applied_count = 1
            return True
        # t2: kein wirksamer Patch (Datei bereits im Zielzustand).
        _s.patches = []
        _s.applied_count = 0
        return False

    def _rev(_s):
        return True

    def _refl(_s, **kw):
        return False

    _common_mocks(
        monkeypatch,
        builder_fn=_builder,
        reviewer_fn=_rev,
        reflection_fn=_refl,
    )

    rc = loop_mod.run_pipeline_loop("p", "a", [st])
    via = [p for k, p in _audits
           if k == "loop_task_ok" and isinstance(p, dict)
           and p.get("via") == "builder_patch_bereits_erfuellt"]
    assert via, (
        "t2 nicht done via builder_patch_bereits_erfuellt; "
        f"kinds={[k for k, _ in _audits]}"
    )
    assert rc == 0, f"erwartet rc=0, war {rc}; kinds={[k for k, _ in _audits]}"


def test_builder_patch_nicht_erfuellt_ohne_prior(
    tmp_path: Path, monkeypatch
) -> None:
    """B: t2 kein wirksamer Patch, KEIN prior done auf gleicher Datei -> failed."""
    st = _mk_state(tmp_path, tasks=[
        {"id": "t2", "name": "T2", "action": "update",
         "task_files": ["core/y.py"]},
    ])
    (tmp_path / "core" / "y.py").write_text("z = 1\n")
    _audits: list[tuple] = []
    monkeypatch.setattr(loop_mod, "audit",
                        lambda k, p, *a, **kw: _audits.append((k, p)))

    def _builder(_s):
        _s.patches = []
        return False

    def _rev(_s):
        return True

    def _refl(_s, **kw):
        return False

    _common_mocks(
        monkeypatch,
        builder_fn=_builder,
        reviewer_fn=_rev,
        reflection_fn=_refl,
    )

    loop_mod.run_pipeline_loop("p", "a", [st])
    via = [p for k, p in _audits
           if k == "loop_task_ok" and isinstance(p, dict)
           and p.get("via") == "builder_patch_bereits_erfuellt"]
    assert not via, (
        "t2 faelschlich done via builder_patch_bereits_erfuellt ohne prior done"
    )
    failed = [p for k, p in _audits if k == "loop_task_failed"]
    assert failed, (
        f"t2 nicht als failed markiert; kinds={[k for k, _ in _audits]}"
    )


def test_auftrag_bereits_erfuellt_im_pre_reviewer_patch_fail(
    tmp_path: Path, monkeypatch
) -> None:
    """A: Reflection False + auftrag_bereits_erfuellt + Verify gruen -> done.

    Szenario Pre-Reviewer-Patch-Fail: der Patch passt nicht mehr zur
    Datei (old_string weg), Reflection scheitert mit gesetztem Flag.
    """
    st = _mk_state(tmp_path, tasks=[
        {"id": "t1", "name": "T1", "action": "update",
         "task_files": ["core/x.py"]},
    ])
    _audits: list[tuple] = []
    monkeypatch.setattr(loop_mod, "audit",
                        lambda k, p, *a, **kw: _audits.append((k, p)))

    def _builder(_s):
        _s.patches = [{"action": "update", "file": "core/x.py",
                       "old_string": "a = 1", "new_string": "b = 2"}]
        _s.applied_count = 1
        return True

    def _rev(_s):
        _s.reviewer_bugs = [{"severity": "high", "description": "fake"}]
        return False

    def _refl(_s, **kw):
        # Reflection setzt Flag (Datei bereits im Zielzustand), gibt
        # aber False zurueck (Stagnation).
        _s.auftrag_bereits_erfuellt = True
        return False

    _common_mocks(
        monkeypatch,
        builder_fn=_builder,
        reviewer_fn=_rev,
        reflection_fn=_refl,
    )

    rc = loop_mod.run_pipeline_loop("p", "a", [st])
    done_audits = [
        p for k, p in _audits
        if k == "loop_task_ok" and isinstance(p, dict)
    ]
    via = [p for p in done_audits
           if "auftrag_bereits_erfuellt" in str(p.get("via", ""))]
    assert via, (
        "t1 nicht done via auftrag_bereits_erfuellt nach Reflection; "
        f"kinds={[k for k, _ in _audits]}"
    )
    assert rc == 0, f"erwartet rc=0, war {rc}"
