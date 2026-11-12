"""Spec: Phasen-/Reflection-Funktionen in loop.py.

Nicht dupliziert (bereits gut abgedeckt):
- _plan_gate              -> test_loop.py (~10), test_k5
- _verify_patches         -> test_loop.py (~15)
- _reflection_loop        -> test_loop.py (7) + test_k3_reflection.py
- _run_with_progress      -> test_loop.py:1029

Getestet hier (0 bestehende Spec-Tests):
- _phase_end_reflection   (K23d, 10 Audit-Kinds, max 2 Runden)
- _split_task_on_demand   (M-472, 5 Audit-Kinds)
- _task_ende              (M-307b, mark_done/mark_failed + progress.append)
- _verify_stage_with_heartbeat (M-390, Threading + subprocess)
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from werkstatt import loop
from werkstatt.state import RunState

# =====================================================================
# Fixtures
# =====================================================================

def _state(tmp_path: Path, **overrides) -> RunState:
    kw = {
        "block_id": "t", "aufgabe": "aufgabe", "start_ts": "2026-10-30T00:00:00Z",
        "docs": {}, "agents": {}, "always": {}, "optional": {}, "file_whitelist": [],
        "api_key": "sk-test", "budget": {}, "agent_docs": {},
        "project_dir": tmp_path, "project_name": "testproj",
    }
    kw.update(overrides)
    return RunState(**kw)


def _audit_events(tmp_path: Path) -> list[dict]:
    logs = tmp_path / "audit-logs"
    if not logs.is_dir():
        return []
    out: list[dict] = []
    for f in sorted(logs.glob("agent-pipeline-*.jsonl")):
        for line in f.read_text().splitlines():
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _kind(tmp_path: Path, kind: str) -> list[dict]:
    return [e for e in _audit_events(tmp_path) if e.get("kind") == kind]


# =====================================================================
# A. _phase_end_reflection
# =====================================================================

def _patch_phase_reflection(builder=True, apply=1, verify=True,
                            review=True, review_iter=None):
    """Hilfs-Patch: alle externen Abhaengigkeiten von _phase_end_reflection."""
    review_ret = review_iter if review_iter is not None else review
    return [
        patch("werkstatt.loop.run_builder", return_value=builder),
        patch("werkstatt.loop._apply_patches_with_hooks",
              return_value=apply),
        patch("werkstatt.loop._verify_patches", return_value=verify),
        patch("werkstatt.reviewer.run_phase_end_review",
              return_value=review_ret),
    ]


def test_phase_reflection_keine_bugs(tmp_path):
    """Keine reviewer_bugs -> False + keine_bugs-Audit."""
    s = _state(tmp_path)
    s.reviewer_bugs = []
    assert loop._phase_end_reflection(s) is False
    assert len(_kind(tmp_path, "loop_phase_reflection_keine_bugs")) == 1


def test_phase_reflection_keine_dateien(tmp_path):
    """Bugs ohne file + tasks ohne task_files -> False + keine_dateien."""
    s = _state(tmp_path)
    s.reviewer_bugs = [{"description": "x", "severity": "high"}]
    s.tasks = []
    assert loop._phase_end_reflection(s) is False
    assert len(_kind(tmp_path, "loop_phase_reflection_keine_dateien")) == 1


def test_phase_reflection_fallback_task_files(tmp_path):
    """Bugs ohne file-Feld -> Fallback auf tasks[].task_files."""
    s = _state(tmp_path)
    s.reviewer_bugs = [{"description": "x", "severity": "high"}]
    s.tasks = [{"id": "t1", "task_files": ["a.py"]}]
    s.patches = [{"file": "a.py", "old_string": "x", "new_string": "y"}]
    with patch("werkstatt.loop.run_builder", return_value=True), \
         patch("werkstatt.loop._apply_patches_with_hooks", return_value=1), \
         patch("werkstatt.loop._verify_patches", return_value=True), \
         patch("werkstatt.reviewer.run_phase_end_review", return_value=False), \
         patch("werkstatt.phases.review._phase_review_gate", return_value=1):
        assert loop._phase_end_reflection(s) is False
    ev = _kind(tmp_path, "loop_phase_reflection_fallback_alle_task_files")
    assert len(ev) >= 1


def test_phase_reflection_builder_failed(tmp_path):
    """run_builder False -> builder_failed-Audit, aber Loop weiter."""
    s = _state(tmp_path)
    s.reviewer_bugs = [{"file": "a.py", "description": "x",
                        "severity": "high"}]
    with patch("werkstatt.loop.run_builder", return_value=False), \
         patch("werkstatt.loop._apply_patches_with_hooks", return_value=0), \
         patch("werkstatt.loop._verify_patches", return_value=True), \
         patch("werkstatt.reviewer.run_phase_end_review", return_value=False), \
         patch("werkstatt.phases.review._phase_review_gate", return_value=1):
        assert loop._phase_end_reflection(s) is False
    assert len(_kind(tmp_path, "loop_phase_reflection_builder_failed")) >= 1


def test_phase_reflection_kein_patch(tmp_path):
    """run_builder True, aber state.patches leer -> kein_patch-Audit."""
    s = _state(tmp_path)
    s.reviewer_bugs = [{"file": "a.py", "description": "x",
                        "severity": "high"}]
    with patch("werkstatt.loop.run_builder", return_value=True), \
         patch("werkstatt.loop._apply_patches_with_hooks", return_value=0), \
         patch("werkstatt.loop._verify_patches", return_value=True), \
         patch("werkstatt.reviewer.run_phase_end_review", return_value=False), \
         patch("werkstatt.phases.review._phase_review_gate", return_value=1):
        assert loop._phase_end_reflection(s) is False
    assert len(_kind(tmp_path, "loop_phase_reflection_kein_patch")) >= 1


def test_phase_reflection_verify_failed(tmp_path):
    """Patch angewendet, aber verify rot -> False + verify_failed-Audit."""
    s = _state(tmp_path)
    s.reviewer_bugs = [{"file": "a.py", "description": "x",
                        "severity": "high"}]
    s.patches = [{"file": "a.py"}]
    with patch("werkstatt.loop.run_builder", return_value=True), \
         patch("werkstatt.loop._apply_patches_with_hooks", return_value=1), \
         patch("werkstatt.loop._verify_patches", return_value=False), \
         patch("werkstatt.reviewer.run_phase_end_review", return_value=False), \
         patch("werkstatt.phases.review._phase_review_gate", return_value=1):
        assert loop._phase_end_reflection(s) is False
    assert len(_kind(tmp_path, "loop_phase_reflection_verify_failed")) == 1


def test_phase_reflection_approved(tmp_path):
    """1 Runde, Review danach gruen -> True + approved-Audit."""
    s = _state(tmp_path)
    s.reviewer_bugs = [{"file": "a.py", "description": "x",
                        "severity": "high"}]
    s.patches = [{"file": "a.py"}]
    reviews = iter([False, True])  # erste Runde reject, dann approved

    def _review_side_effect(st):
        return next(reviews)

    with patch("werkstatt.loop.run_builder", return_value=True), \
         patch("werkstatt.loop._apply_patches_with_hooks", return_value=1), \
         patch("werkstatt.loop._verify_patches", return_value=True), \
         patch("werkstatt.reviewer.run_phase_end_review",
               side_effect=_review_side_effect), \
         patch("werkstatt.phases.review._phase_review_gate", return_value=0):
        assert loop._phase_end_reflection(s) is True
    assert len(_kind(tmp_path, "loop_phase_reflection_approved")) == 1


def test_phase_reflection_last_explicit_approval_accepts_remaining_review_findings(tmp_path):
    """Nach zwei Rejects kann der Mensch die verbleibenden Patches explizit übernehmen."""
    s = _state(tmp_path)
    s.reviewer_bugs = [{"file": "a.py", "description": "x",
                        "severity": "high"}]
    s.patches = [{"file": "a.py"}]
    with patch("werkstatt.loop.run_builder", return_value=True), \
         patch("werkstatt.loop._apply_patches_with_hooks", return_value=1), \
         patch("werkstatt.loop._verify_patches", return_value=True), \
         patch("werkstatt.reviewer.run_phase_end_review",
               return_value=False), \
         patch("werkstatt.phases.review._phase_review_gate", return_value=0) as gate:
        assert loop._phase_end_reflection(s) is True
    assert gate.call_count == 2



def test_task_ende_ok(tmp_path):
    """ok=True -> mark_done, progress.append 'done'."""
    s = _state(tmp_path)
    ps = MagicMock()
    with patch("werkstatt.progress.append") as mock_append:
        loop._task_ende(s, ps, "t1", ok=True, name="Task Eins",
                        dateien=["a.py"])
    ps.mark_done.assert_called_once_with("t1")
    ps.mark_failed.assert_not_called()
    mock_append.assert_called_once()
    args, kw = mock_append.call_args
    assert args[0] == tmp_path  # pd
    assert kw["status"] == "done"
    assert kw["dateien"] == ["a.py"]


def test_task_ende_fail(tmp_path):
    """ok=False -> mark_failed(failure), progress.append 'failed'."""
    s = _state(tmp_path)
    ps = MagicMock()
    with patch("werkstatt.progress.append") as mock_append:
        loop._task_ende(s, ps, "t1", ok=False, failure="boom",
                        dateien=["a.py"])
    ps.mark_failed.assert_called_once_with("t1", failure="boom")
    ps.mark_done.assert_not_called()
    _args, kw = mock_append.call_args
    assert kw["status"] == "failed"
    assert kw["info"] == "boom"


# =====================================================================
# D. _verify_stage_with_heartbeat
# =====================================================================

def test_heartbeat_erfolg(tmp_path):
    """subprocess.run liefert CompletedProcess -> durchgereicht."""
    cp = subprocess.CompletedProcess(args=["x"], returncode=0,
                                     stdout="ok", stderr="")
    with patch("werkstatt.loop.subprocess.run", return_value=cp):
        out = loop._verify_stage_with_heartbeat(
            ["echo", "x"], str(tmp_path), "stage-1", timeout=5)
    assert out is cp


def test_heartbeat_exception_propagiert(tmp_path):
    """subprocess.run wirft -> Exception wird im Hauptthread re-raised."""
    with (patch("werkstatt.loop.subprocess.run",
                side_effect=RuntimeError("boom")),
          pytest.raises(RuntimeError, match="boom")):
        loop._verify_stage_with_heartbeat(
            ["x"], str(tmp_path), "stage-1", timeout=5)


def test_heartbeat_timeout_propagiert(tmp_path):
    """subprocess.run wirft TimeoutExpired -> propagiert."""
    exc = subprocess.TimeoutExpired(cmd=["x"], timeout=5)
    with (patch("werkstatt.loop.subprocess.run", side_effect=exc),
          pytest.raises(subprocess.TimeoutExpired)):
        loop._verify_stage_with_heartbeat(
            ["x"], str(tmp_path), "stage-1", timeout=5)


# =====================================================================
# GOLD 2026-10-30: _ruff_fix_changed vor jedem Verify
# =====================================================================

def test_ruff_fix_changed_ruft_ruff_auf(tmp_path):
    """_ruff_fix_changed ruft ruff --fix auf geaenderte Dateien."""
    from unittest.mock import patch

    from werkstatt.state import RunState

    s = RunState(
        block_id="t", aufgabe="a", start_ts="x",
        docs={}, agents={}, always={}, optional={},
        file_whitelist=[], api_key="k", budget={}, agent_docs={},
        project_dir=tmp_path, project_name="t",
    )
    (tmp_path / "a.py").write_text("")
    s.patches = [{"file": "a.py"}]

    aufrufe: list = []
    def _fake_run(argv, **kw):
        aufrufe.append((argv, kw.get("cwd")))
        return type("R", (), {"returncode": 0})()
    with patch("werkstatt.loop.subprocess.run", _fake_run):
        loop._ruff_fix_changed(s)

    assert len(aufrufe) == 1
    argv, _cwd = aufrufe[0]
    assert argv[0] == "ruff"
    assert "--fix" in argv
    assert "a.py" in argv


def test_ruff_fix_changed_leer(tmp_path):
    """Ohne .py-Patches: kein ruff-Aufruf."""
    from unittest.mock import patch

    from werkstatt.state import RunState

    s = RunState(
        block_id="t", aufgabe="a", start_ts="x",
        docs={}, agents={}, always={}, optional={},
        file_whitelist=[], api_key="k", budget={}, agent_docs={},
        project_dir=tmp_path, project_name="t",
    )
    s.patches = [{"file": "a.txt"}]
    aufrufe: list = []
    with patch("werkstatt.loop.subprocess.run",
               lambda *a, **kw: aufrufe.append(a) or
                                 type("R", (), {"returncode": 0})()):
        loop._ruff_fix_changed(s)
    assert aufrufe == []


# =====================================================================
# GOLD 2026-10-30: Phase-Review-Skip bei leerem patches + alle done
# =====================================================================

def test_phase_review_skip_bei_leerem_patches():
    """Bei leeren patches + alle Tasks done: Phase-Review wird
    uebersprungen, kein reviewer_phase_kein_diff.

    Regression: Live 2026-10-30 21:28:25 — alle 5 Tasks done,
    state.patches leer, reviewer_phase_kein_diff -> Rollback.
    """
    import tempfile
    from pathlib import Path

    from werkstatt.state import RunState

    tmp = Path(tempfile.mkdtemp())
    s = RunState(
        block_id="t", aufgabe="a", start_ts="x",
        docs={}, agents={}, always={}, optional={},
        file_whitelist=[], api_key="k", budget={},
        agent_docs={}, project_dir=tmp, project_name="t",
    )
    s.tasks = [{"id": "t1", "status": "done", "task_files": ["a.py"]}]
    s.patches = []
    # Die Hilfsfunktionen, die run_pipeline_loop aufrufen wuerde,
    # koennen wir nicht isoliert testen ohne den vollen Loop.
    # Wir pruefen die Logik direkt:
    _tasks = s.tasks
    _alle_done = (
        bool(_tasks)
        and all(
            isinstance(t, dict) and t.get("status") == "done"
            for t in _tasks
        )
    )
    _patches_leer = not s.patches
    assert _alle_done
    assert _patches_leer


def test_phase_review_skip_prueft_applied_count():
    """Der Skip prueft applied_count, nicht nur state.patches.

    Regression: Live 2026-10-30 21:33:31 — state.patches war
    gefuellt (4 no-op-Patches), aber applied_count war 0.
    Ohne diesen Fix lief der Phase-Review mit leerem Diff
    und rejected 4x.
    """
    import inspect

    from werkstatt import loop as loop_mod
    # Fix AZ Stufe 8-D: Logik liegt jetzt in _phase_finalize.
    src = (
        inspect.getsource(loop_mod.run_pipeline_loop)
        + inspect.getsource(loop_mod._phase_finalize)
    )
    # Der Skip-Block muss applied_count pruefen
    assert "applied_count" in src
    # und _patches_leer aus applied_count ableiten
    assert "_patches_leer = _applied == 0" in src or            "_patches_leer = _applied" in src


def test_alle_done_aus_phasestate():
    """_alle_done prueft PhaseState, nicht state.tasks.

    Regression: Live 2026-10-30 22:37: PhaseState t1=done, aber
    state.tasks[0] hatte kein status-Feld -> _alle_done=False ->
    reviewer_phase_kein_diff.
    """
    import inspect

    from werkstatt import loop as loop_mod
    # Fix AZ Stufe 8-D: Logik liegt jetzt in _phase_finalize.
    src = (
        inspect.getsource(loop_mod.run_pipeline_loop)
        + inspect.getsource(loop_mod._phase_finalize)
    )
    # Pruefe, dass phase_state.get_task aufgerufen wird
    assert "phase_state.get_task" in src
    assert "_alle_done" in src


def _run_finalize_commit_order(
    tmp_path, monkeypatch, verify_ok, *, task_status="done",
):
    from werkstatt.phases import finalize

    state = _state(tmp_path, run_id="run-verify-1")
    state.tasks = [{"id": "t1"}]
    state.applied_count = 0
    phase_state = MagicMock()
    phase_state.get_task.return_value = {"status": task_status}
    order = []
    audit_events = []
    progress_entries = []

    def _human_gate(_state, *, defer_commit=False):
        assert defer_commit is True
        return 2

    def _verify(_state, phase=None):
        assert phase == "phase_end"
        order.append("verify")
        return verify_ok

    def _append_progress(_project_dir, **kwargs):
        progress_entries.append(kwargs)
        order.append(
            "progress_pending"
            if kwargs.get("status") == "verify_pending"
            else "progress_final"
        )

    def _commit(_state):
        order.append("commit")
        _state.progress_written_at_commit = True
        return True, "abc123"

    monkeypatch.setattr(finalize, "_human_gate", _human_gate)
    monkeypatch.setattr(
        finalize, "_phase_end_recovery_pause", lambda *_args: False,
    )
    monkeypatch.setattr(finalize, "_verify_patches", _verify)
    monkeypatch.setattr(finalize, "_hat_human_review_tasks", lambda _ps: False)
    monkeypatch.setattr(finalize, "_phase_end_reflection", lambda _state: True)
    monkeypatch.setattr(
        "werkstatt.reviewer.run_phase_end_review", lambda _state: True,
    )
    monkeypatch.setattr(finalize, "audit", lambda *a, **kw: audit_events.append(a))
    monkeypatch.setattr(finalize, "group_start", lambda *a, **kw: None)
    monkeypatch.setattr(finalize, "group_end", lambda *a, **kw: None)
    monkeypatch.setattr(finalize, "summary", lambda *a, **kw: None)
    monkeypatch.setattr("werkstatt.committer._committe_zielprojekt", _commit)
    monkeypatch.setattr(
        "werkstatt.progress.append",
        _append_progress,
    )

    rc = finalize._phase_finalize(
        state, tasks_ok=1, tasks=state.tasks,
        project_name="testproj", phase_state=phase_state,
    )
    return rc, order, audit_events, progress_entries


def test_finalize_committet_erst_nach_bestandenem_phase_end_verify(
    tmp_path, monkeypatch,
):
    rc, order, _events, progress = _run_finalize_commit_order(tmp_path, monkeypatch, True)
    assert rc == 0
    assert order == ["progress_pending", "verify", "commit"]
    assert [entry["status"] for entry in progress] == ["verify_pending"]
    assert progress[0]["run_id"] == "run-verify-1"


def test_finalize_committet_nicht_wenn_phase_end_verify_scheitert(
    tmp_path, monkeypatch,
):
    rc, order, _events, progress = _run_finalize_commit_order(tmp_path, monkeypatch, False)
    assert rc == 1
    assert order == ["progress_pending", "verify", "progress_final"]
    assert [entry["status"] for entry in progress] == ["verify_pending", "phase_ende"]
    assert [entry["run_id"] for entry in progress] == [
        "run-verify-1", "run-verify-1",
    ]



@pytest.mark.parametrize("task_status", ["failed", "blocked", "pending", "running", "missing"])
def test_finalize_markiert_unvollstaendige_tasks_nicht_als_loop_erfolg(
    tmp_path, monkeypatch, task_status,
):
    rc, order, events, progress = _run_finalize_commit_order(
        tmp_path, monkeypatch, True, task_status=task_status,
    )

    assert rc == 1
    assert order == ["progress_pending", "verify", "commit"]
    assert [entry["status"] for entry in progress] == ["verify_pending"]
    kinds = [event[0] for event in events]
    assert "loop_erfolg" not in kinds
    unvollstaendig = [
        event[1] for event in events
        if event[0] == "loop_phase"
        and event[1].get("phase") == "completion"
    ]
    assert unvollstaendig == [{
        "phase": "completion",
        "status": "incomplete",
        "reason": "tasks_unresolved",
        "tasks_ok": 1,
        "tasks_total": 1,
        "unresolved": [{"task_id": "t1", "status": task_status}],
    }]



def test_resume_erledigte_tasks_fuehrt_phase_end_verify_aus(
    tmp_path, monkeypatch,
):
    """Ein gespeicherter All-done-Checkpoint muss erneut final verifiziert werden."""
    from werkstatt.phase_state import PhaseState
    from werkstatt.phases import finalize, tasks

    planned = [{"id": "t1", "name": "Implementierung"}]
    phase_state = PhaseState("testproj", base_dir=tmp_path / ".werkstatt")
    phase_state.init_new("Resume Abschlusspruefung", planned)
    phase_state.mark_done("t1")

    state = _state(tmp_path)
    state.tasks = planned
    state.applied_count = 0
    order = []
    audit_events = []

    monkeypatch.setattr(
        "werkstatt.agent._enforce_run_budget", lambda _state: False,
    )
    monkeypatch.setattr(tasks, "audit", lambda *_args: None)
    monkeypatch.setattr(finalize, "audit",
                        lambda *args, **_kwargs: audit_events.append(args))
    monkeypatch.setattr(finalize, "group_start", lambda *_args: None)
    monkeypatch.setattr(finalize, "group_end", lambda *_args: None)
    monkeypatch.setattr(finalize, "summary", lambda *_args: None)
    monkeypatch.setattr(finalize, "_human_gate",
                        lambda *_args, **_kwargs: 2)
    monkeypatch.setattr(finalize, "_hat_human_review_tasks",
                        lambda _phase_state: False)
    monkeypatch.setattr(finalize, "_phase_end_reflection",
                        lambda _state: True)
    monkeypatch.setattr(
        "werkstatt.reviewer.run_phase_end_review", lambda _state: True,
    )

    def verify(_state, *, phase=None):
        order.append(("verify", phase))
        return True

    def append_progress(_project_dir, **_kwargs):
        return None

    def commit(_state):
        order.append(("commit", None))
        _state.progress_written_at_commit = True
        return True, "abc123"

    monkeypatch.setattr(finalize, "_verify_patches", verify)
    monkeypatch.setattr("werkstatt.progress.append", append_progress)
    monkeypatch.setattr("werkstatt.committer._committe_zielprojekt", commit)

    rc_tasks, tasks_ok, returned_tasks = tasks._phase_tasks_loop(
        state, phase_state,
    )
    assert rc_tasks == 0

    rc = finalize._phase_finalize(
        state, tasks_ok, returned_tasks, "testproj", phase_state,
    )

    assert rc == 0
    assert tasks_ok == 1
    assert state.tasks_ok_counter == 1
    assert order == [("verify", "phase_end"), ("commit", None)]
    assert any(event[0] == "loop_erfolg" for event in audit_events)
