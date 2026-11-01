"""OP-059: Aufrufer wertet reviewer_stagnation_false_positive aus.

Wenn _reflection_loop die false_positive-Erkennung setzt und True
zurueckgibt, darf der Aufrufer NICHT erneut run_reviewer() aufrufen.
Der Task soll direkt als done in den Human-Gate-Pfad.
"""
from __future__ import annotations

from pathlib import Path

from werkstatt import loop as loop_mod
from werkstatt.state import RunState


def _mk_state(tmp_path: Path) -> RunState:
    (tmp_path / ".werkstatt").mkdir()
    (tmp_path / ".werkstatt" / "verify.json").write_text(
        '{"stages": [{"id": "pc", "command": ["python3", "-c", "pass"]}]}'
    )
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "x.py").write_text("b\n")
    s = RunState(
        block_id="p", aufgabe="a", start_ts="", docs={}, agents={},
        always={}, optional={}, file_whitelist=[], api_key="dummy",
        budget={}, agent_docs={}, project_dir=tmp_path, project_name="p",
    )
    s.tasks = [{"id": "t1", "name": "T1", "action": "update",
                "task_files": ["core/x.py"]}]
    s.phasen = []
    return s


def test_false_positive_task_wird_done_ohne_reviewer_call(
    tmp_path: Path, monkeypatch
) -> None:
    """_reflection_loop setzt false_positive -> run_reviewer nicht erneut."""
    st = _mk_state(tmp_path)
    _audits: list[str] = []
    _reviewer_calls = {"n": 0}

    monkeypatch.setattr(loop_mod, "audit",
                        lambda k, p, *a, **kw: _audits.append(k))
    monkeypatch.setattr(loop_mod, "_plan_gate", lambda s: True)
    monkeypatch.setattr(
        loop_mod, "run_explorer",
        lambda s, a: {"key_files": [], "findings": "", "next_reads": []},
    )

    def _fake_builder(_s):
        _s.patches = [{"action": "update", "file": "core/x.py",
                       "old_string": "b", "new_string": "c"}]
        _s.applied_count = 1
        return True

    monkeypatch.setattr(loop_mod, "run_builder", _fake_builder)
    monkeypatch.setattr(loop_mod, "_verify_patches", lambda s, phase=None: True)
    monkeypatch.setattr(loop_mod, "_call_hook", lambda n, p: {"allow": True})

    def _fake_reviewer_erster_call(_s):
        # 1. Reviewer lehnt ab (Halluzination).
        _s.reviewer_bugs = [{"severity": "high", "description": "fake"}]
        return False

    def _reflection_fp(_s, **kw):
        # Reflexion erkennt false_positive und setzt Flag.
        _s.reviewer_stagnation_false_positive = True
        return True

    monkeypatch.setattr(loop_mod, "run_reviewer", _fake_reviewer_erster_call)
    monkeypatch.setattr(loop_mod, "_reflection_loop", _reflection_fp)

    # Zaehle run_reviewer-Aufrufe (muss bei 1 bleiben, kein 2. Call).
    _orig_rev = _fake_reviewer_erster_call

    def _count_rev(_s):
        _reviewer_calls["n"] += 1
        return _orig_rev(_s)

    monkeypatch.setattr(loop_mod, "run_reviewer", _count_rev)

    from werkstatt import reviewer as _rv_mod
    monkeypatch.setattr(_rv_mod, "run_phase_end_review", lambda s: True)
    for _fn in ("header", "step", "task", "task_ok", "task_failed",
                "group_start", "group_end", "footer"):
        if hasattr(loop_mod, _fn):
            monkeypatch.setattr(loop_mod, _fn, lambda *a, **kw: None)

    rc = loop_mod.run_pipeline_loop("p", "a", [st])
    assert rc == 0, f"rc={rc}, audits={_audits}"
    assert "loop_reviewer_reject_false_positive" in _audits, \
        f"Aufrufer-Fix nicht aktiv; audits={_audits}"
    assert _reviewer_calls["n"] == 1, \
        f"run_reviewer {_reviewer_calls['n']}x aufgerufen (erwartet 1x)"


def test_kein_false_positive_normale_reviewer_ablehnung(
    tmp_path: Path, monkeypatch
) -> None:
    """Ohne false_positive-Flag: run_reviewer wird 2x aufgerufen (normal)."""
    st = _mk_state(tmp_path)
    _audits: list[str] = []
    _reviewer_calls = {"n": 0}

    monkeypatch.setattr(loop_mod, "audit",
                        lambda k, p, *a, **kw: _audits.append(k))
    monkeypatch.setattr(loop_mod, "_plan_gate", lambda s: True)
    monkeypatch.setattr(
        loop_mod, "run_explorer",
        lambda s, a: {"key_files": [], "findings": "", "next_reads": []},
    )

    def _fake_builder(_s):
        _s.patches = [{"action": "update", "file": "core/x.py",
                       "old_string": "b", "new_string": "c"}]
        _s.applied_count = 1
        return True

    monkeypatch.setattr(loop_mod, "run_builder", _fake_builder)
    monkeypatch.setattr(loop_mod, "_verify_patches", lambda s, phase=None: True)
    monkeypatch.setattr(loop_mod, "_call_hook", lambda n, p: {"allow": True})

    def _fake_reviewer(_s):
        _reviewer_calls["n"] += 1
        _s.reviewer_bugs = [{"severity": "high", "description": "fake"}]
        return False

    monkeypatch.setattr(loop_mod, "run_reviewer", _fake_reviewer)
    monkeypatch.setattr(loop_mod, "_reflection_loop", lambda s, **kw: False)

    from werkstatt import reviewer as _rv_mod
    monkeypatch.setattr(_rv_mod, "run_phase_end_review", lambda s: True)
    for _fn in ("header", "step", "task", "task_ok", "task_failed",
                "group_start", "group_end", "footer"):
        if hasattr(loop_mod, _fn):
            monkeypatch.setattr(loop_mod, _fn, lambda *a, **kw: None)

    rc = loop_mod.run_pipeline_loop("p", "a", [st])
    # Ohne false_positive: alter Pfad -> task failed, rc=1 (oder 0, je nach finalizer).
    assert "loop_reviewer_reject_false_positive" not in _audits
