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
from werkstatt.phase_state import PhaseState
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


def _approved_checkpoint(state: RunState) -> PhaseState:
    """Give task executor tests the current persisted plan contract."""
    state.run_id = "builder-failure-test-run"
    phase = PhaseState(
        state.project_name,
        base_dir=Path(state.project_dir) / ".werkstatt",
    )
    phase.run_id = state.run_id
    phase.init_new(
        state.aufgabe,
        state.tasks,
        tests=["python -c pass"],
        akzeptanzkriterien=["The checkpoint task outcome is recorded."],
    )
    phase.data["plan_complete"] = True
    phase.bind_approved_plan()
    phase.save()
    return phase


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


def _capture_audits(monkeypatch, audits: list[tuple]) -> None:
    from werkstatt.roles import task_dispatch as task_executor

    sink = lambda kind, payload, *args, **kwargs: audits.append((kind, payload))
    monkeypatch.setattr(loop_mod, "audit", sink)
    monkeypatch.setattr(task_executor, "audit", sink)


def test_builder_failed_mit_grund(tmp_path: Path, monkeypatch) -> None:
    """C: Audit loop_task_failed enthaelt grund='builder_failed'."""
    st = _mk_state(tmp_path, tasks=[
        {"id": "t1", "name": "T1", "action": "update",
         "task_files": ["core/x.py"]},
    ])
    _audits: list[tuple] = []
    _capture_audits(monkeypatch, _audits)

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

    loop_mod.run_pipeline_loop(
        "p", "a", [st], phase_state=_approved_checkpoint(st),
    )
    # Task ist failed — aber das Audit MUSS den Grund nennen.
    failed_kinds = [
        p for k, p in _audits if k == "loop_task_failed"
    ]
    assert failed_kinds, (
        f"kein loop_task_failed-Audit; kinds={[k for k, _ in _audits]}"
    )
    assert any(
        isinstance(p, dict)
        and p.get("reason") == "builder_failed_at_checkpoint"
        and p.get("coordinator_reentry") is True
        for p in failed_kinds
    ), f"Builder-Fehler wurde nicht am Checkpoint zurueckgegeben: {failed_kinds}"


def test_patch_apply_failure_returns_to_coordinator_without_reflection(
    tmp_path: Path, monkeypatch
) -> None:
    """A failed patch application is recorded without an inline role chain."""
    st = _mk_state(tmp_path, tasks=[
        {"id": "t1", "name": "T1", "action": "update",
         "task_files": ["core/x.py"]},
    ])
    _audits: list[tuple] = []
    _capture_audits(monkeypatch, _audits)

    def _builder(_s):
        _s.patches = [{"action": "update", "file": "core/x.py",
                       "old_string": "a = 1", "new_string": "b = 2"}]
        _s.applied_count = 1
        return True

    def _rev(_s):
        _s.reviewer_bugs = [{"severity": "high", "description": "fake"}]
        return False

    reflection_calls = []

    def _refl(_s, **kw):
        reflection_calls.append(True)
        return False

    _common_mocks(
        monkeypatch,
        builder_fn=_builder,
        reviewer_fn=_rev,
        reflection_fn=_refl,
    )

    rc = loop_mod.run_pipeline_loop(
        "p", "a", [st], phase_state=_approved_checkpoint(st),
    )
    assert reflection_calls == []
    assert not any(kind == "loop_task_ok" for kind, _ in _audits)
    assert any(kind == "loop_patch_old_string_not_found" for kind, _ in _audits)
    assert any(kind == "loop_task_failed" for kind, _ in _audits)
    assert rc != 0
