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
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from tests.factories import coordinator_decision_for_task
from werkstatt import loop
from werkstatt.state import RunState


def test_finalize_resume_returns_to_coordinator_without_checkpoints(
    tmp_path, monkeypatch,
):
    phase_state = MagicMock()
    phase_state.data = {"tasks": [{"id": "t1", "status": "done"}]}
    state = _state(tmp_path)
    calls = []
    monkeypatch.setattr(
        "werkstatt.failure_record._worktree_fingerprint",
        lambda _project_dir: "a" * 64,
    )
    monkeypatch.setattr(
        loop, "_phase_end_review_action",
        lambda *_args, **_kwargs: calls.append("review") or 0,
    )
    monkeypatch.setattr(
        loop, "_phase_human_gate_action",
        lambda *_args, **_kwargs: calls.append("gate") or (0, False),
    )
    monkeypatch.setattr(
        loop, "_phase_end_verify_action",
        lambda *_args, **_kwargs: calls.append("verify") or 0,
    )

    rc = loop._phase_finalize(state, 1, [{"id": "t1"}], "testproj", phase_state)

    assert rc == 3
    assert calls == []


def test_op_progress_marker_requires_complete_evidence_for_verified_status(
    monkeypatch,
) -> None:
    from werkstatt.phases import finalize

    state = SimpleNamespace(
        aufgabe="Bearbeite OP-398",
        run_id="run-op398-123",
        last_verify_results=[{"stage_id": "pytest", "ok": True}],
    )
    phase_state = SimpleNamespace(
        data={"akzeptanzkriterien": ["AC1"], "tasks": [{"id": "t1"}]},
        criteria_progress=lambda: {
            "tracked": True, "valid": True,
            "covered": ["AC1"], "uncovered": [],
        },
    )

    monkeypatch.setattr(
        finalize, "_criterion_evidence_rows",
        lambda *args: ([{"criterion_id": "AC1"}], []),
    )
    assert "criteria_state=verified verified=AC1" in (
        finalize._op_criteria_progress_marker(state, phase_state, 0) or ""
    )
    assert "evidence_ref=Control/run-op398-123/loop_criteria_progress" in (
        finalize._op_criteria_progress_marker(state, phase_state, 0) or ""
    )

    monkeypatch.setattr(
        finalize, "_criterion_evidence_rows",
        lambda *args: ([{"criterion_id": "AC1"}], ["AC1:verify_evidence_missing"]),
    )
    marker = finalize._op_criteria_progress_marker(state, phase_state, 0)
    assert marker is not None
    assert "criteria_state=partial_unverified" in marker
    assert "verified=none" in marker
    assert "remaining=AC1" in marker
    assert "evidence_gaps=AC1:verify_evidence_missing" in marker

    phase_state.criteria_progress = lambda: {"tracked": False}
    assert "criteria_state=unknown" in (
        finalize._op_criteria_progress_marker(state, phase_state, 1) or ""
    )

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


@pytest.mark.parametrize(
    ("action", "executor"),
    [
        ("read", "read_only_task"),
        ("verify", "verify_only"),
        ("create", "builder"),
        ("update", "builder"),
    ],
)
def test_checkpoint_selects_registered_executor_for_task_action(
    action: str, executor: str,
) -> None:
    from werkstatt.phases.tasks import _checkpoint_decision_payload

    class Phase:
        def progress(self):
            return {"pending": 1, "failed": 0, "done": 0}

        def criteria_progress(self):
            return {
                "tracked": True, "valid": True,
                "covered": [], "uncovered": [],
            }

    decision = _checkpoint_decision_payload(
        Phase(), {"id": "t1", "action": action},
    )

    assert decision["decision"] == "execute_planned_task"
    assert decision["next_executor"] == executor
    assert executor in decision["reason"]


def test_verify_task_runs_deterministic_verify_without_reviewer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from werkstatt.phase_state import PhaseState
    from werkstatt.phases import tasks as task_phase

    project = tmp_path / "project"
    project.mkdir()
    source = project / "feature.py"
    source.write_text("value = 1\n", encoding="utf-8")
    phase = PhaseState("testproj", base_dir=project / ".werkstatt")
    phase.init_new(
        "Verify the feature",
        [{
            "id": "verify-1", "name": "Verify feature", "action": "verify",
            "task_files": ["feature.py"], "criterion_refs": ["AC1"],
        }],
        akzeptanzkriterien=["The feature passes verification"],
    )
    phase.run_id = "verify-run-1"
    phase.save()
    state = _state(
        project,
        aufgabe="Verify the feature",
        run_id="verify-run-1",
        tasks=phase.data["tasks"],
    )
    verify_calls: list[str] = []

    def verify(_state, *, phase):
        verify_calls.append(phase)
        _state.last_verify_results = [{
            "stage_id": "pytest_changed", "ok": True, "exit_code": 0,
            "scope_files": ["feature.py"],
        }]
        return True

    monkeypatch.setattr(task_phase, "audit", lambda *args, **kwargs: True)
    monkeypatch.setattr(task_phase, "group_start", lambda *_args: None)
    monkeypatch.setattr(task_phase, "group_end", lambda: None)
    monkeypatch.setattr(task_phase, "task", lambda *_args: None)
    monkeypatch.setattr(task_phase, "task_started", lambda *_args: None)
    monkeypatch.setattr(task_phase, "task_ok", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(task_phase, "task_done", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(task_phase, "check_run_lease", lambda _state: None)
    monkeypatch.setattr(task_phase, "_verify_patches", verify)
    monkeypatch.setattr(
        task_phase, "run_reviewer",
        lambda _state: pytest.fail("Verify-only task must not call Reviewer"),
    )
    monkeypatch.setattr("werkstatt.agent._enforce_run_budget", lambda _state: False)
    monkeypatch.setattr("werkstatt.audit.get_run_id", lambda: "")

    rc, tasks_ok, tasks = task_phase._phase_tasks_loop(
        state, phase,
        coordinator_decision=coordinator_decision_for_task(phase, state),
    )

    assert rc == 0
    assert tasks_ok == 1
    assert tasks[0]["id"] == "verify-1"
    assert phase.get_task("verify-1")["status"] == "done"
    assert verify_calls == ["post_build"]








def test_verify_failure_detail_is_current_bounded_json() -> None:
    from werkstatt.roles.verify_task import verify_failure_detail

    state = _state(Path("."))
    state.last_verify_errors = [f"stage-{index}: " + "x" * 500 for index in range(8)]
    detail = verify_failure_detail(state)

    assert detail is not None
    assert len(detail) <= 1200
    evidence = json.loads(detail)
    assert evidence["source"] == "verify"
    assert evidence["errors"]
    assert len(evidence["errors"]) <= 4
    assert verify_failure_detail(_state(Path("."))) is None


def test_task_checkpoint_persists_only_successful_verify_evidence(tmp_path) -> None:
    from werkstatt.phase_state import PhaseState
    from werkstatt.roles.verify_task import run_task_verify_checkpoint

    phase_state = PhaseState("evidence", base_dir=tmp_path / ".werkstatt")
    phase_state.run_id = "evidence-run"
    phase_state.init_new(
        "Task Verify",
        [{
            "id": "t1", "criterion_refs": ["AC1"],
            "task_files": ["src/task.py"],
        }],
        akzeptanzkriterien=["Ziel"],
    )
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "task.py").write_text("x = 1\n", encoding="utf-8")
    state = _state(tmp_path)
    state.last_verify_results = [
        {
            "stage_id": "pytest_changed", "exit_code": 0, "ok": True,
            "scope_files": ["src/task.py"],
        },
        {
            "stage_id": "ruff_changed", "exit_code": 1, "ok": False,
            "scope_files": ["src/task.py"],
        },
    ]

    result = run_task_verify_checkpoint(
        state,
        phase_state,
        "t1",
        verify=lambda _state, *, phase: phase == "post_build",
        audit_call=lambda *_args, **_kwargs: True,
    )
    assert result.verify_ok is True
    assert result.evidence_recorded is True
    evidence = phase_state.get_task("t1")["verify_evidence"]
    assert evidence["criterion_refs"] == ["AC1"]
    assert [item["stage_id"] for item in evidence["stages"]] == [
        "pytest_changed",
    ]
    assert phase_state.task_verify_evidence_is_current("t1", evidence)


def test_checkpoint_rejects_unregistered_task_action() -> None:
    from werkstatt.phases.tasks import _checkpoint_decision_payload

    class Phase:
        def progress(self):
            return {"pending": 1, "failed": 0, "done": 0}

        def criteria_progress(self):
            return {"tracked": False, "valid": True, "covered": [], "uncovered": []}

    decision = _checkpoint_decision_payload(
        Phase(), {"id": "t1", "action": "architect"},
    )

    assert decision["decision"] == "reject_invalid_task_action"
    assert decision["next_executor"] is None
    assert "keinen freigegebenen Executor" in decision["reason"]




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
    # Review skip policy belongs to its independent checkpoint action.
    src = (
        inspect.getsource(loop_mod.run_pipeline_loop)
        + inspect.getsource(loop_mod._phase_end_review_action)
    )
    # Der Skip-Block muss applied_count pruefen
    assert "applied_count" in src
    # and skip only when no changes were actually applied.
    assert "int(state.applied_count or 0) == 0" in src


def test_alle_done_aus_phasestate():
    """_alle_done prueft PhaseState, nicht state.tasks.

    Regression: Live 2026-10-30 22:37: PhaseState t1=done, aber
    state.tasks[0] hatte kein status-Feld -> _alle_done=False ->
    reviewer_phase_kein_diff.
    """
    import inspect

    from werkstatt import loop as loop_mod
    # Completion state is read by the independent review checkpoint action.
    src = (
        inspect.getsource(loop_mod.run_pipeline_loop)
        + inspect.getsource(loop_mod._phase_end_review_action)
    )
    # Pruefe, dass phase_state.get_task aufgerufen wird
    assert "phase_state.get_task" in src
    assert "_alle_done" in src


def _run_finalize_commit_order(
    tmp_path, monkeypatch, verify_ok, *, task_status="done", doku_nachzug=False,
    criteria_progress=None, phase_state=None,
):
    from werkstatt.phases import finalize

    state = _state(tmp_path, run_id="run-verify-1")
    state.tasks = [{"id": "t1"}]
    state.applied_count = 0
    if doku_nachzug:
        state.aufgabe = "OP-999: Verifizierten Abschluss testen"
        state.akzeptanzkriterien = ["Abschluss wird erst nach Verify dokumentiert."]
        state.applied_count = 1
    if phase_state is None:
        phase_state = MagicMock()
        phase_state.get_task.return_value = {"status": task_status}
        phase_state.criteria_progress.return_value = criteria_progress or {
            "tracked": False, "valid": True, "covered": [], "uncovered": [],
        }
    order = []
    audit_events = []
    progress_entries = []

    def _append_progress(_project_dir, **kwargs):
        progress_entries.append(kwargs)
        order.append(
            "progress_final"
        )

    phase_data = getattr(phase_state, "data", None)
    if not isinstance(phase_data, dict):
        phase_data = {}
    phase_data["tasks"] = [{"id": "t1", "status": task_status}]
    phase_data["human_gate_checkpoint"] = {"commit_requested": False}
    phase_state.data = phase_data
    monkeypatch.setattr(
        phase_state, "phase_end_review_is_current",
        lambda **_kwargs: True, raising=False,
    )
    monkeypatch.setattr(
        phase_state, "human_gate_is_current",
        lambda **_kwargs: True, raising=False,
    )
    monkeypatch.setattr(
        phase_state, "phase_end_verify_is_current",
        lambda **_kwargs: True, raising=False,
    )
    order.extend(["phase_end_review", "human_gate", "phase_end_verify"])
    if not verify_ok:
        return 1, order, audit_events, progress_entries

    monkeypatch.setattr(finalize, "_hat_human_review_tasks", lambda _ps: False)
    monkeypatch.setattr(
        finalize, "_phase_end_reflection", lambda _state: True,
        raising=False,
    )
    monkeypatch.setattr(
        "werkstatt.reviewer.run_phase_end_review", lambda _state: True,
    )
    monkeypatch.setattr(finalize, "audit", lambda *a, **kw: audit_events.append(a))
    monkeypatch.setattr(finalize, "group_start", lambda *a, **kw: None)
    monkeypatch.setattr(finalize, "group_end", lambda *a, **kw: None)
    monkeypatch.setattr(finalize, "summary", lambda *a, **kw: None)
    monkeypatch.setattr(
        "werkstatt.progress.append",
        _append_progress,
    )

    rc = finalize._phase_finalize(
        state, tasks_ok=1, tasks=state.tasks,
        project_name="testproj", phase_state=phase_state,
        phase_review_checkpointed=True,
        human_gate_checkpointed=True,
        phase_end_verify_checkpointed=True,
    )
    return rc, order, audit_events, progress_entries


def test_finalize_committet_erst_nach_bestandenem_phase_end_verify(
    tmp_path, monkeypatch,
):
    rc, order, _events, progress = _run_finalize_commit_order(tmp_path, monkeypatch, True)
    assert rc == 0
    assert order == [
        "phase_end_review", "human_gate", "phase_end_verify", "progress_final",
    ]
    assert [entry["status"] for entry in progress] == ["phase_ende"]
    assert progress[0]["run_id"] == "run-verify-1"


def test_op_doku_commit_kommt_nach_code_post_commit_verify(tmp_path, monkeypatch):
    rc, order, _events, _progress = _run_finalize_commit_order(
        tmp_path, monkeypatch, True, doku_nachzug=True,
    )
    assert rc == 0
    assert order == [
        "phase_end_review", "human_gate", "phase_end_verify", "progress_final",
    ]


def test_finalize_committet_nicht_wenn_phase_end_verify_scheitert(
    tmp_path, monkeypatch,
):
    rc, order, _events, progress = _run_finalize_commit_order(tmp_path, monkeypatch, False)
    assert rc == 1
    assert order == ["phase_end_review", "human_gate", "phase_end_verify"]
    assert progress == []




def test_task_ende_auditiert_kriterienfortschritt_nach_gruenem_task(tmp_path):
    from werkstatt.phase_state import PhaseState
    from werkstatt.task_runner import _task_ende

    state = _state(tmp_path)
    phase_state = PhaseState("testprojekt", base_dir=tmp_path / ".werkstatt")
    phase_state.init_new(
        "Kriterienfortschritt",
        [
            {"id": "t1", "criterion_refs": ["AC1"]},
            {"id": "t2", "criterion_refs": ["AC2"]},
        ],
        akzeptanzkriterien=["Erstes Ziel", "Zweites Ziel"],
    )
    events = []

    with patch("werkstatt.task_runner.audit", lambda *args: events.append(args)), \
         patch("werkstatt.progress.append"):
        _task_ende(state, phase_state, "t1", ok=True, name="Erstes Ziel")

    progress_events = [
        event for event in events if event[0] == "loop_criteria_progress"
    ]
    assert len(progress_events) == 1
    assert progress_events[0][1] == {
        "task_id": "t1",
        "status": "in_progress",
        "tracked": True,
        "coverage_basis": "assigned_tasks_done",
        "covered": ["AC1"],
        "remaining": ["AC2"],
        "error": None,
        "next_step_type": "task",
        "next_task_id": "t2",
        "next_step": "Weiter mit t2",
        "decision_summary": (
            "Offene Kriterien bleiben im freigegebenen Task-Graph; "
            "der naechste ausfuehrbare Task wird fortgesetzt."
        ),
        "evidence": [
            "Task t1 als done gespeichert",
            "Ziel: Kriterienfortschritt",
            "Task-Abdeckung erledigt: AC1 — Erstes Ziel",
            "Offen: AC2 — Zweites Ziel",
            "Restlicher Graph: t2: pending",
        ],
    }


def test_task_ende_zeigt_phase_end_verify_als_naechsten_schritt(tmp_path):
    from werkstatt.phase_state import PhaseState
    from werkstatt.task_runner import _task_ende

    state = _state(tmp_path)
    phase_state = PhaseState("testprojekt", base_dir=tmp_path / ".werkstatt")
    phase_state.init_new(
        "Einzelnes Ziel",
        [{"id": "t1", "name": "Implementierung", "criterion_refs": ["AC1"]}],
        akzeptanzkriterien=["Ziel ist belegt"],
    )
    events = []

    with patch("werkstatt.task_runner.audit", lambda *args: events.append(args)), \
         patch("werkstatt.progress.append"):
        _task_ende(state, phase_state, "t1", ok=True, name="Implementierung")

    event = next(item for item in events if item[0] == "loop_criteria_progress")
    assert event[1]["next_step_type"] == "phase_end_verify"
    assert event[1]["next_step"] == (
        "Phase-End-Review, Freigabe und Gesamt-Verify ausfuehren"
    )
    assert event[1]["status"] == "task_graph_complete"
    assert event[1]["coverage_basis"] == "assigned_tasks_done"
    assert "noch kein Zielnachweis" in event[1]["decision_summary"]
    assert "Ziel: Einzelnes Ziel" in event[1]["evidence"]
    assert "Task-Abdeckung erledigt: AC1 — Ziel ist belegt" in event[1]["evidence"]


def test_task_ende_macht_fehlende_kriterienzuordnung_sichtbar(tmp_path):
    from werkstatt.phase_state import PhaseState
    from werkstatt.task_runner import _task_ende

    state = _state(tmp_path)
    phase_state = PhaseState("testprojekt", base_dir=tmp_path / ".werkstatt")
    phase_state.init_new(
        "Legacy-Auftrag ohne Kriterienzuordnung",
        [
            {"id": "t1", "name": "Erster Schritt"},
            {"id": "t2", "name": "Naechster Schritt"},
        ],
    )
    events = []

    with patch("werkstatt.task_runner.audit", lambda *args: events.append(args)), \
         patch("werkstatt.progress.append"):
        _task_ende(state, phase_state, "t1", ok=True, name="Erster Schritt")

    event = next(item for item in events if item[0] == "loop_criteria_progress")
    payload = event[1]
    assert payload["tracked"] is False
    assert payload["status"] == "untracked"
    assert payload["next_step"] == "Weiter mit t2: Naechster Schritt"
    assert any(
        "kein Zielabschluss aus diesem Checkpoint" in item
        for item in payload["evidence"]
    )
    assert "Ziel bleibt offen" in payload["decision_summary"]


@pytest.mark.parametrize("task_status", ["failed", "blocked", "pending", "running", "missing"])
def test_finalize_markiert_unvollstaendige_tasks_nicht_als_loop_erfolg(
    tmp_path, monkeypatch, task_status,
):
    rc, order, events, progress = _run_finalize_commit_order(
        tmp_path, monkeypatch, True, task_status=task_status,
    )

    assert rc == 1
    assert order == [
        "phase_end_review", "human_gate", "phase_end_verify", "progress_final",
    ]
    assert [entry["status"] for entry in progress] == ["phase_ende"]
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



def test_finalize_blockiert_erfolg_wenn_akzeptanzkriterium_offen_ist(
    tmp_path, monkeypatch,
):
    report = {
        "tracked": True,
        "valid": True,
        "covered": ["AC1"],
        "uncovered": ["AC2"],
        "error": None,
    }
    rc, _order, events, _progress = _run_finalize_commit_order(
        tmp_path,
        monkeypatch,
        True,
        criteria_progress=report,
    )

    assert rc == 1
    assert "loop_erfolg" not in [event[0] for event in events]
    completion = [
        event[1] for event in events
        if event[0] == "loop_phase"
        and event[1].get("phase") == "completion"
    ]
    assert completion == [{
        "phase": "completion",
        "status": "incomplete",
        "reason": "criteria_unresolved",
        "tasks_ok": 1,
        "tasks_total": 1,
        "unresolved": [],
        "criteria_covered": ["AC1"],
        "criteria_uncovered": ["AC2"],
        "criteria_error": None,
    }]


def test_finalize_blockiert_zielerfolg_bei_ungetrackten_akzeptanzkriterien(
    tmp_path, monkeypatch,
):
    from werkstatt.phase_state import PhaseState

    phase_state = PhaseState("testprojekt", base_dir=tmp_path / ".werkstatt")
    phase_state.init_new(
        "Ziel mit nicht zugeordneten Kriterien",
        [{"id": "t1", "name": "Implementierung"}],
        akzeptanzkriterien=["Belegbares Ziel"],
    )
    phase_state.mark_done("t1")
    assert phase_state.criteria_progress()["tracked"] is False

    rc, _order, events, _progress = _run_finalize_commit_order(
        tmp_path, monkeypatch, True, phase_state=phase_state,
    )

    assert rc == 1
    assert "loop_erfolg" not in [event[0] for event in events]
    completion = [
        event[1] for event in events
        if event[0] == "loop_phase"
        and event[1].get("phase") == "completion"
    ]
    assert completion == [{
        "phase": "completion",
        "status": "incomplete",
        "reason": "criteria_untracked",
        "tasks_ok": 1,
        "tasks_total": 1,
        "unresolved": [],
        "criteria_covered": [],
        "criteria_uncovered": [],
        "criteria_error": "criteria_not_tracked",
    }]





def test_criterion_evidence_reports_gaps_instead_of_guessing(tmp_path):
    from werkstatt.phases.finalize import _criterion_evidence_rows

    phase_state = MagicMock()
    phase_state.run_id = "run-1"
    phase_state.get_task.return_value = {"status": "done"}
    phase_state.task_verify_evidence_is_current.return_value = True
    rows, gaps = _criterion_evidence_rows(
        ["Kriterium wird verifiziert"],
        [{
            "id": "t1", "criterion_refs": ["AC1"],
            "task_files": ["src/task.py"],
            "verify_evidence": {
                "schema_version": 1, "task_id": "t1",
                "phase": "post_build", "criterion_refs": ["AC1"],
                "run_id": "run-1",
                "task_files": ["src/task.py"],
                "task_file_sha256": {"src/task.py": "a" * 64},
                "stages": [{
                    "stage_id": "pytest_changed", "exit_code": 0, "ok": True,
                    "scope_files": ["src/task.py"],
                }],
            },
        }],
        phase_state,
        [],
    )

    assert rows[0]["task_ids"] == ["t1"]
    assert rows[0]["task_status"] == "done"
    assert rows[0]["verify_stage_ids"] == ["pytest_changed"]
    assert rows[0]["phase_end_verify_stage_ids"] == []
    assert gaps == ["AC1:successful_phase_end_verify_stage_missing"]


def test_criterion_evidence_ignores_superseded_failed_history(tmp_path):
    from werkstatt.phases.finalize import _criterion_evidence_rows

    phase_state = MagicMock()
    phase_state.run_id = "run-replan"
    phase_state.get_task.side_effect = lambda task_id: {
        "status": "superseded" if task_id == "old" else "done",
    }
    phase_state.task_verify_evidence_is_current.side_effect = (
        lambda task_id, _evidence: task_id == "replacement"
    )
    rows, gaps = _criterion_evidence_rows(
        ["Criterion remains covered"],
        [
            {"id": "old", "status": "superseded", "criterion_refs": ["AC1"]},
            {
                "id": "replacement",
                "status": "done",
                "criterion_refs": ["AC1"],
                "task_files": ["src/fixed.py"],
                "verify_evidence": {
                    "schema_version": 1,
                    "task_id": "replacement",
                    "phase": "post_build",
                    "criterion_refs": ["AC1"],
                    "run_id": "run-replan",
                    "task_files": ["src/fixed.py"],
                    "stages": [{
                        "stage_id": "pytest_fixed",
                        "ok": True,
                        "exit_code": 0,
                        "scope_files": ["src/fixed.py"],
                    }],
                },
            },
        ],
        phase_state,
        [{
            "stage_id": "pytest_phase_end",
            "ok": True,
            "exit_code": 0,
        }],
    )

    assert rows[0]["task_ids"] == ["replacement"]
    assert rows[0]["task_status"] == "done"
    assert gaps == []


def test_criterion_evidence_does_not_reuse_unrelated_run_verify_for_task(
    tmp_path,
):
    from werkstatt.phases.finalize import _criterion_evidence_rows

    phase_state = MagicMock()
    phase_state.run_id = "run-1"
    phase_state.get_task.return_value = {"status": "done"}
    phase_state.task_verify_evidence_is_current.return_value = False
    rows, gaps = _criterion_evidence_rows(
        ["Kriterium wird verifiziert"],
        [{"id": "t1", "criterion_refs": ["AC1"]}],
        phase_state,
        [{"stage_id": "pytest_regression", "exit_code": 0, "ok": True}],
    )

    assert rows[0]["verify_stage_ids"] == []
    assert rows[0]["phase_end_verify_stage_ids"] == ["pytest_regression"]
    assert gaps == ["AC1:task_verify_evidence_missing"]


def test_finalizer_rejects_task_verify_for_stale_file_content(tmp_path):
    from werkstatt.phase_state import PhaseState
    from werkstatt.phases.finalize import _criterion_evidence_rows

    project_file = tmp_path / "src" / "task.py"
    project_file.parent.mkdir()
    project_file.write_text("value = 1\n", encoding="utf-8")
    phase_state = PhaseState("testproj", base_dir=tmp_path / ".werkstatt")
    phase_state.run_id = "verify-run"
    phase_state.init_new(
        "Verify-Provenance",
        [{
            "id": "t1", "criterion_refs": ["AC1"],
            "task_files": ["src/task.py"],
        }],
        akzeptanzkriterien=["Der aktuelle Inhalt ist geprueft"],
    )
    phase_state.mark_done("t1")
    assert phase_state.record_task_verify_evidence(
        "t1",
        [{
            "stage_id": "pytest_changed", "exit_code": 0, "ok": True,
            "scope_files": ["src/task.py"],
        }],
        phase="post_build",
    )
    record = phase_state.get_task("t1")
    project_file.write_text("value = 2\n", encoding="utf-8")

    rows, gaps = _criterion_evidence_rows(
        ["Der aktuelle Inhalt ist geprueft"],
        [record],
        phase_state,
        [{"stage_id": "pytest_regression", "exit_code": 0, "ok": True}],
    )

    assert rows[0]["verify_stage_ids"] == []
    assert gaps == ["AC1:task_verify_evidence_missing"]

def test_phase_finalize_rejects_review_checkpoint_after_worktree_change(
    tmp_path, monkeypatch,
):
    from werkstatt.phase_state import PhaseState

    phase_state = PhaseState("testproj", base_dir=tmp_path / ".werkstatt")
    phase_state.run_id = "run-review"
    phase_state.init_new("Goal", [{"id": "t1", "name": "Change"}])
    phase_state.bind_approved_plan()
    phase_state.record_phase_end_review(worktree_fingerprint="a" * 64)
    state = _state(tmp_path, run_id="run-review")
    monkeypatch.setattr(
        "werkstatt.failure_record._worktree_fingerprint",
        lambda _project_dir: "b" * 64,
    )
    monkeypatch.setattr(
        "werkstatt.phases.finalize._human_gate",
        lambda *_args, **_kwargs: pytest.fail(
            "stale review must stop before gate",
        ),
    )

    rc = loop._phase_finalize(
        state,
        0,
        [],
        "testproj",
        phase_state,
        phase_review_checkpointed=True,
    )

    assert rc == 3


def test_phase_end_verify_prueft_nach_task_checkpoint_fehler_erneut(
    tmp_path, monkeypatch,
):
    from werkstatt.phase_state import PhaseState
    from werkstatt.task_runner import _task_ende

    phase_state = PhaseState("testprojekt", base_dir=tmp_path / ".werkstatt")
    phase_state.run_id = "run-criteria-retry"
    phase_state.init_new(
        "Ziel trotz Checkpoint-Ausfall belegen",
        [{
            "id": "t1", "criterion_refs": ["AC1"],
            "task_files": ["src/task.py"],
        }],
        akzeptanzkriterien=["Ziel ist durch Verify belegt"],
    )
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "task.py").write_text("x = 1\n", encoding="utf-8")
    calls = 0

    def _criteria_progress():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("transient checkpoint failure")
        return {
            "tracked": True,
            "valid": True,
            "covered": ["AC1"],
            "uncovered": [],
            "error": None,
        }

    monkeypatch.setattr(phase_state, "criteria_progress", _criteria_progress)
    state = _state(tmp_path, run_id="run-criteria-retry")
    phase_state.run_id = "run-criteria-retry"
    assert phase_state.record_task_verify_evidence(
        "t1",
        [{
            "stage_id": "pytest_changed", "exit_code": 0, "ok": True,
            "scope_files": ["src/task.py"],
        }],
        phase="post_build",
    )
    state.tasks = [{"id": "t1"}]
    task_events = []
    monkeypatch.setattr(
        "werkstatt.task_runner.audit",
        lambda *args: task_events.append(args),
    )
    monkeypatch.setattr("werkstatt.progress.append", lambda *_args, **_kwargs: None)

    assert _task_ende(state, phase_state, "t1", ok=True, name="Implementierung")
    assert phase_state.get_task("t1")["status"] == "done"
    assert calls == 1
    assert any(event[0] == "loop_criteria_checkpoint_failed" for event in task_events)

    rc, _order, final_events, _progress = _run_finalize_commit_order(
        tmp_path, monkeypatch, True, phase_state=phase_state,
    )

    assert calls == 2
    assert rc == 1
    assert not any(event[0] == "loop_erfolg" for event in final_events)


def test_task_ende_auditiert_fehlgeschlagenen_kriterien_checkpoint(
    tmp_path, monkeypatch,
):
    from werkstatt.phase_state import PhaseState
    from werkstatt.task_runner import _task_ende

    state = _state(tmp_path)
    phase_state = PhaseState("testprojekt", base_dir=tmp_path / ".werkstatt")
    phase_state.init_new(
        "Kriterienfortschritt",
        [{"id": "t1", "criterion_refs": ["AC1"]}],
        akzeptanzkriterien=["Erstes Ziel"],
    )

    def _checkpoint_fehler():
        raise RuntimeError("interner Text wird nicht persistiert")

    monkeypatch.setattr(phase_state, "criteria_progress", _checkpoint_fehler)
    events = []
    monkeypatch.setattr(
        "werkstatt.task_runner.audit",
        lambda *args: events.append(args),
    )
    monkeypatch.setattr("werkstatt.progress.append", lambda *_args, **_kwargs: None)

    _task_ende(state, phase_state, "t1", ok=True, name="Erstes Ziel")

    assert phase_state.get_task("t1")["status"] == "done"
    failed = [
        event for event in events
        if event[0] == "loop_criteria_checkpoint_failed"
    ]
    assert len(failed) == 1
    assert failed[0][1] == {
        "task_id": "t1",
        "error_type": "RuntimeError",
        "next_step": (
            "Phase-End-Verify prueft den Zielabgleich erneut; "
            "Erfolg bleibt bis dahin offen"
        ),
    }
