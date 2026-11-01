"""OP-064a: Sticky-Veto — einmal vetoed, nur Mensch setzt zurueck.

Live-Beleg Testrunde 3 (18:54 OP-004): spec_widerspruch_erkannt wurde
gesetzt, aber _phase_tasks_loop's Erfolgs-Pfad (_refl_ok=True) hat es
ignoriert. Reviewer Runde 2 approved, task_ok, obwohl Diff # type: ignore
enthielt.

Sticky-Veto: deterministische Signale setzen vetoed, LLM-Approval kann
es nicht aufheben. Nur mark_human_review/mark_done durch Mensch.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from werkstatt.phase_state import PhaseState
from werkstatt.task_runner import _task_ende


def _mk_ps(tmp_path: Path) -> PhaseState:
    (tmp_path / ".werkstatt").mkdir(exist_ok=True)
    ps = PhaseState("p", base_dir=tmp_path / ".werkstatt")
    ps.data["tasks"] = [
        {"id": "t1", "name": "T1", "status": "running"},
    ]
    ps.save()
    return ps


def test_mark_vetoed_setzt_verdict(tmp_path: Path) -> None:
    ps = _mk_ps(tmp_path)
    ps.mark_vetoed("t1", grund="spec_widerspruch_vermutet")
    t = ps.get_task("t1")
    assert t.get("verdict") == "vetoed"
    assert t.get("failure") == "spec_widerspruch_vermutet"


def test_ist_vetoed(tmp_path: Path) -> None:
    ps = _mk_ps(tmp_path)
    assert ps.ist_vetoed("t1") is False
    ps.mark_vetoed("t1", grund="x")
    assert ps.ist_vetoed("t1") is True


def test_task_ende_respektiert_veto(tmp_path: Path) -> None:
    """ok=True, aber vetoed -> mark_human_review statt mark_done."""
    (tmp_path / ".werkstatt").mkdir(exist_ok=True)
    (tmp_path / "PROGRESS.md").write_text("# Fortschritt\n", encoding="utf-8")

    s = SimpleNamespace()
    s.project_dir = tmp_path
    s.project_name = "p"
    s.aufgabe = "ohne OP"
    s.tasks_ok_counter = 0

    ps = _mk_ps(tmp_path)
    ps.mark_vetoed("t1", grund="spec_widerspruch_vermutet")

    _audits: list[str] = []
    import werkstatt.task_runner as tr
    _orig_audit = tr.audit
    tr.audit = lambda k, p, *a, **kw: _audits.append(k)
    try:
        _task_ende(s, ps, "t1", ok=True, name="T1")
    finally:
        tr.audit = _orig_audit

    t = ps.get_task("t1")
    assert t.get("status") == "human_review", (
        f"Veto ignoriert, status={t.get('status')}"
    )
    assert "loop_task_veto_respected" in _audits


def test_success_pfad_bei_spec_widerspruch_setzt_veto(
    tmp_path: Path, monkeypatch,
) -> None:
    """_refl_ok=True + spec_widerspruch_erkannt -> vetoed + human_review.

    Live-Beleg Testrunde 3 (18:54 OP-004): _reflection_loop gab True
    zurueck, weil spec_widerspruch erkannt. _phase_tasks_loop lief in
    den Erfolgs-Pfad, Reviewer approved, task_ok. Mit Sticky-Veto:
    phase_state.mark_vetoed + human_review.
    """
    from werkstatt import loop as loop_mod
    from werkstatt.state import RunState

    (tmp_path / ".werkstatt").mkdir(exist_ok=True)
    (tmp_path / ".werkstatt" / "verify.json").write_text(
        '{"stages": [{"id": "pc", "command": ["python3", "-c", "pass"]}]}'
    )
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "x.py").write_text("b = 2\n")

    st = RunState(
        block_id="p", aufgabe="a", start_ts="", docs={}, agents={},
        always={}, optional={}, file_whitelist=[], api_key="dummy",
        budget={}, agent_docs={}, project_dir=tmp_path, project_name="p",
    )
    st.tasks = [{"id": "t1", "name": "T1", "action": "update",
                 "task_files": ["core/x.py"]}]
    st.phasen = []

    _audits: list[tuple] = []
    monkeypatch.setattr(loop_mod, "audit",
                        lambda k, p, *a, **kw: _audits.append((k, p)))
    monkeypatch.setattr(loop_mod, "_plan_gate", lambda s: True)
    monkeypatch.setattr(
        loop_mod, "run_explorer",
        lambda s, a: {"key_files": [], "findings": "", "next_reads": []},
    )

    def _fake_builder(_s):
        _s.patches = [{"action": "update", "file": "core/x.py",
                       "old_string": "a = 1", "new_string": "b = 2"}]
        _s.applied_count = 1
        return True

    monkeypatch.setattr(loop_mod, "run_builder", _fake_builder)
    monkeypatch.setattr(loop_mod, "_verify_patches", lambda s, phase=None: True)
    monkeypatch.setattr(loop_mod, "_call_hook", lambda n, p: {"allow": True})

    _reviewer_calls = {"n": 0}

    def _fake_reviewer(_s):
        _reviewer_calls["n"] += 1
        _s.reviewer_bugs = [{"severity": "high",
                             "description": "Task fordert X, Diff macht Y"}]
        return False

    def _fake_reflection(_s, **kw):
        # OP-059e: Erschoepfung mit Fortschritt -> spec_widerspruch
        _s.spec_widerspruch_erkannt = True
        return True

    monkeypatch.setattr(loop_mod, "run_reviewer", _fake_reviewer)
    monkeypatch.setattr(loop_mod, "_reflection_loop", _fake_reflection)

    from werkstatt import reviewer as _rv_mod
    monkeypatch.setattr(_rv_mod, "run_phase_end_review", lambda s: True)
    for _fn in ("header", "step", "task", "task_ok", "task_failed",
                "group_start", "group_end", "footer"):
        if hasattr(loop_mod, _fn):
            monkeypatch.setattr(loop_mod, _fn, lambda *a, **kw: None)

    rc = loop_mod.run_pipeline_loop("p", "a", [st])

    # Veto-Event muss im Audit stehen
    kinds = [k for k, _ in _audits]
    assert "loop_task_spec_widerspruch_veto" in kinds, (
        f"kein Veto-Audit; kinds={kinds}"
    )

    # Task-Status in phase_state muss human_review sein
    from werkstatt.phase_state import PhaseState
    ps = PhaseState("p", base_dir=tmp_path / ".werkstatt")
    ps.load()
    _t = ps.get_task("t1")
    assert _t is not None
    assert _t.get("status") == "human_review", (
        f"Status nicht human_review: {_t.get('status')}"
    )
    assert _t.get("verdict") == "vetoed", (
        f"Verdict nicht vetoed: {_t.get('verdict')}"
    )
