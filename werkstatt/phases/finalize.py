"""Phase: _phase_finalize (OP-139 Phase 2b)."""
from __future__ import annotations

from pathlib import Path


def _criterion_evidence_rows(
    criteria: object,
    tasks: object,
    phase_state: object,
    verify_results: object,
) -> tuple[list[dict[str, object]], list[str]]:
    """Bind each criterion to completed tasks and successful verify stages.

    Task completion alone is coverage, not proof. The final evidence record
    therefore includes the exact task IDs and executed, successful stage IDs.
    Any missing link is returned as an explicit gap instead of being guessed.
    """
    if not isinstance(criteria, list) or not criteria:
        return [], ["acceptance_criteria_missing"]
    if not isinstance(tasks, list):
        return [], ["task_graph_missing"]
    phase_end_stages = sorted({
        str(item.get("stage_id") or "").strip()
        for item in verify_results
        if isinstance(item, dict)
        and item.get("ok") is True
        and str(item.get("stage_id") or "").strip()
    }) if isinstance(verify_results, list) else []
    expected_run_id = getattr(phase_state, "run_id", None)
    if not isinstance(expected_run_id, str) or not expected_run_id:
        expected_run_id = ""

    rows: list[dict[str, object]] = []
    gaps: list[str] = []
    for index, criterion in enumerate(criteria, 1):
        criterion_id = f"AC{index}"
        if not isinstance(criterion, str) or not criterion.strip():
            gaps.append(f"{criterion_id}:invalid_text")
            continue
        assigned: list[str] = []
        incomplete: list[str] = []
        task_verify_stages: set[str] = set()
        for task in tasks:
            if isinstance(task, dict) and task.get("status") == "superseded":
                continue
            refs = task.get("criterion_refs") if isinstance(task, dict) else None
            if not isinstance(refs, list) or criterion_id not in refs:
                continue
            task_id = str(task.get("id") or "").strip()
            if not task_id:
                incomplete.append("task_id_missing")
                continue
            assigned.append(task_id)
            evidence = task.get("verify_evidence")
            current_evidence_check = getattr(
                phase_state, "task_verify_evidence_is_current", None,
            )
            evidence_matches_current_files = False
            if callable(current_evidence_check):
                try:
                    evidence_matches_current_files = (
                        current_evidence_check(task_id, evidence) is True
                    )
                except (OSError, RuntimeError, TypeError, ValueError):
                    evidence_matches_current_files = False
            if (
                isinstance(evidence, dict)
                and evidence_matches_current_files
                and evidence.get("schema_version") == 1
                and evidence.get("task_id") == task_id
                and evidence.get("phase") == "post_build"
                and (
                    bool(expected_run_id)
                    and evidence.get("run_id") == expected_run_id
                )
                and isinstance(evidence.get("criterion_refs"), list)
                and criterion_id in evidence["criterion_refs"]
                and isinstance(evidence.get("stages"), list)
            ):
                evidence_files = {
                    path.replace("\\", "/")
                    for path in evidence["task_files"]
                    if isinstance(path, str)
                }
                for stage in evidence["stages"]:
                    if not isinstance(stage, dict):
                        continue
                    stage_id = stage.get("stage_id")
                    scope_files = stage.get("scope_files")
                    if (
                        stage.get("ok") is True
                        and stage.get("exit_code") == 0
                        and isinstance(stage_id, str)
                        and stage_id.strip()
                        and isinstance(scope_files, list)
                        and any(
                            isinstance(path, str)
                            and path.replace("\\", "/") in evidence_files
                            for path in scope_files
                        )
                    ):
                        task_verify_stages.add(stage_id.strip())
            get_task = getattr(phase_state, "get_task", None)
            try:
                status_record = get_task(task_id) if callable(get_task) else task
            except Exception:
                status_record = None
                incomplete.append(f"{task_id}:state_read_failed")
            if (
                task_id not in incomplete
                and (
                    not isinstance(status_record, dict)
                    or status_record.get("status") != "done"
                )
            ):
                incomplete.append(task_id)
        if not assigned:
            gaps.append(f"{criterion_id}:task_mapping_missing")
        elif incomplete:
            gaps.append(f"{criterion_id}:tasks_not_done")
        if assigned and not task_verify_stages:
            gaps.append(f"{criterion_id}:task_verify_evidence_missing")
        if not phase_end_stages:
            gaps.append(f"{criterion_id}:successful_phase_end_verify_stage_missing")
        rows.append({
            "criterion_id": criterion_id,
            "criterion": criterion.strip(),
            "task_ids": sorted(set(assigned)),
            "task_status": (
                "done" if assigned and not incomplete else "incomplete"
            ),
            "verify_stage_ids": sorted(task_verify_stages),
            "phase_end_verify_stage_ids": phase_end_stages,
            "verification_status": (
                "passed"
                if task_verify_stages and phase_end_stages and not incomplete
                else "missing"
            ),
        })
    return rows, gaps


def _op_criteria_progress_marker(state, phase_state, run_rc: int) -> str | None:
    """Write a compact, evidence-backed OP marker for resumable progress."""
    progress_fn = getattr(phase_state, "criteria_progress", None)
    try:
        progress = progress_fn() if callable(progress_fn) else None
    except (OSError, RuntimeError, TypeError, ValueError):
        progress = None
    if not isinstance(progress, dict) or progress.get("tracked") is not True:
        return "criteria_state=unknown"
    if run_rc != 0:
        status = "partial_unverified"
        covered: list[str] = []
        remaining: list[str] = []
        gaps = ["run_not_completed"]
    else:
        raw_covered = progress.get("covered", [])
        raw_remaining = progress.get("uncovered", [])
        covered = [item for item in raw_covered if isinstance(item, str)] if isinstance(raw_covered, list) else []
        remaining = [item for item in raw_remaining if isinstance(item, str)] if isinstance(raw_remaining, list) else []
        data = getattr(phase_state, "data", {})
        criteria = data.get("akzeptanzkriterien", []) if isinstance(data, dict) else []
        rows, evidence_gaps = _criterion_evidence_rows(
            criteria, data.get("tasks", []) if isinstance(data, dict) else [],
            phase_state, getattr(state, "last_verify_results", None),
        )
        verified: list[str] = [
            str(row["criterion_id"]) for row in rows
            if isinstance(row, dict)
            and isinstance(row.get("criterion_id"), str)
            and row.get("verification_status") in {None, "passed"}
            and not any(
                isinstance(gap, str)
                and gap.startswith(f"{row['criterion_id']}:")
                for gap in evidence_gaps
            )
        ]
        gaps = evidence_gaps
        remaining = sorted(set(remaining + [
            gap.split(":", 1)[0] for gap in evidence_gaps
            if isinstance(gap, str) and ":" in gap
        ]))
        status = (
            "verified"
            if criteria and len(verified) == len(criteria) and not gaps
            else "partial_unverified"
        )
        covered = verified

    run_id = getattr(state, "run_id", None)
    evidence_ref = (
        f"Control/{run_id}/loop_criteria_progress"
        if isinstance(run_id, str) and run_id.strip()
        else "Control/loop_criteria_progress"
    )
    return (
        f"criteria_state={status} verified={','.join(covered) or 'none'} "
        f"remaining={','.join(remaining) or 'none'} "
        f"evidence_gaps={','.join(gaps) or 'none'} evidence_ref={evidence_ref}"
    )[:1800]


def _approved_commit(state: RunState) -> tuple[bool, str | None]:
    """Create the explicitly approved commit; post-commit Verify is separate."""
    import os

    from werkstatt.committer import (
        _committe_zielprojekt,
        _op_nnn_fuer_doku_nachzug,
    )

    project_dir = state.project_dir
    project_name = state.project_name
    doku_op, _reason = _op_nnn_fuer_doku_nachzug(
        getattr(state, "aufgabe", "") or "",
        getattr(state, "akzeptanzkriterien", []),
        bool(getattr(state, "phase_review_approved", False)),
    )
    state.doku_nachzug_deferred = (
        os.environ.get("WERKSTATT_DOKU_NACHZUG") == "1"
        and doku_op is not None
    )
    commit_ok, commit_info = _committe_zielprojekt(state)
    if not commit_ok:
        state.doku_nachzug_deferred = False
        audit("loop_human_gate_commit_abort", {"info": commit_info}, project_dir, project_name)
        return False, None

    if state.doku_nachzug_deferred:
        state.doku_nachzug_deferred = False
        state.doku_nachzug_commit_only = True
        try:
            docs_ok, docs_info = _committe_zielprojekt(
                state,
                verify_callback=lambda: _verify_patches(
                    state, phase="phase_end",
                ),
            )
        finally:
            state.doku_nachzug_commit_only = False
        if not docs_ok:
            audit(
                "loop_human_gate_commit_abort",
                {"reason": "verified_op_docs_commit_failed", "info": docs_info},
                project_dir,
                project_name,
            )
            return False, None

    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False, None
    final_sha = head.stdout.strip()
    if head.returncode != 0 or not final_sha:
        return False, None
    snapshot_ok, _snapshot = _post_commit_snapshot_check(project_dir, final_sha)
    if not snapshot_ok:
        return False, None
    return True, final_sha

import subprocess

from werkstatt.failure_record import create_failure_record
from werkstatt.render import (
    group_end,
    group_start,
    summary,
)
from werkstatt.state import RunState

from ._common import (
    _gate_failed_payload,
    _hat_human_review_tasks,
    _human_gate,
    _verify_patches,
    _with_spinner,
    audit,
)


def _post_commit_snapshot_check(
    project_dir: Path, expected_sha: str,
) -> tuple[bool, dict[str, object]]:
    """Ensure Verify observed the exact committed HEAD and left no dirty files."""
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        if head.returncode != 0:
            return False, {"reason": "head_read_failed"}
        actual_sha = head.stdout.strip()
        if not expected_sha or not actual_sha.startswith(expected_sha):
            return False, {
                "reason": "head_changed_during_post_commit_verify",
                "expected_sha": expected_sha,
                "actual_sha": actual_sha,
            }

        status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
        if status.returncode != 0:
            return False, {"reason": "worktree_status_failed"}
        dirty_paths = [
            line[3:].strip()
            for line in status.stdout.splitlines()
            if line.strip()
        ]
        if dirty_paths:
            return False, {
                "reason": "worktree_changed_during_post_commit_verify",
                "dirty_paths": dirty_paths[:50],
                "omitted_paths": max(0, len(dirty_paths) - 50),
            }
        return True, {"head_sha": actual_sha, "worktree_clean": True}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, {
            "reason": "post_commit_snapshot_check_failed",
            "error_type": type(exc).__name__,
        }


def _phase_end_review_action(
    state: RunState,
    tasks_ok: int,
    phase_state,
) -> int:
    """Run and record the phase-end review as one coordinator action."""
    pd = state.project_dir
    pn = state.project_name
    _total_tasks = len(state.tasks or [])
    if 0 < tasks_ok < _total_tasks:
        audit(
            "loop_task_partial_ok",
            {
                "done": tasks_ok,
                "total": _total_tasks,
                "failed": _total_tasks - tasks_ok,
            },
            pd,
            pn,
        )

    group_start("Phase 4: Phase-End-Review")
    audit(
        "loop_phase",
        {"phase": "phase_end_review", "status": "start"},
        pd,
        pn,
    )
    tasks = state.tasks or []
    all_done = bool(tasks)
    if all_done and phase_state is not None:
        for task in tasks:
            if not isinstance(task, dict) or not task.get("id"):
                all_done = False
                break
            record = phase_state.get_task(task["id"])
            if (record or {}).get("status") not in ("done", "human_review"):
                all_done = False
                break

    if all_done and int(state.applied_count or 0) == 0:
        state.phase_review_uebersprungen = "keine Aenderungen"
        audit(
            "loop_phase",
            {
                "phase": "phase_end_review",
                "status": "skipped",
                "reason": "keine_patches_alle_done",
            },
            pd,
            pn,
        )
    else:
        from werkstatt.reviewer import run_phase_end_review

        review_ok = _with_spinner(
            "Phase-Review", lambda: run_phase_end_review(state),
        )
        bugs = state.reviewer_bugs or []
        if bugs:
            history = getattr(state, "reviewer_bugs_history", None)
            if history is None:
                state.reviewer_bugs_history = []
                history = state.reviewer_bugs_history
            history.append(list(bugs))
            if len(history) > 5:
                state.reviewer_bugs_history = history[-5:]
        if not review_ok:
            audit(
                "loop_phase",
                {"phase": "phase_end_review", "status": "rejected"},
                pd,
                pn,
            )
            group_end()
            # A review checkpoint is one role invocation. Recovery or a
            # human decision must be selected by the run coordinator from
            # this rejection evidence, never chained here.
            return 1
    state.phase_review_approved = True
    audit(
        "loop_phase",
        {"phase": "phase_end_review", "status": "approved"},
        pd,
        pn,
    )
    group_end()
    return 0


def _phase_human_gate_action(state: RunState) -> tuple[int, bool]:
    """Run the human gate independently; return rc and commit consent."""
    pd = state.project_dir
    pn = state.project_name
    group_start("Phase 5: Human-Gate")
    audit("loop_phase", {"phase": "human_gate", "status": "start"}, pd, pn)
    gate_rc = _human_gate(state, defer_commit=True)
    group_end()
    return gate_rc, gate_rc == 2


def _phase_end_verify_action(
    state: RunState,
    tasks_ok: int,
    tasks: list,
    project_name: str,
    phase_state,
    *,
    checkpointed: bool = False,
) -> int:
    """Run full phase-end verification and bounded evidence-based recovery."""
    pd = state.project_dir
    pn = state.project_name
    rc = 0
    # M-476: Phase-End Verify (Vollsuite) nach human_gate.
    # Die harte Doku-Pruefung laeuft auf dem aktuellen Worktree. Schreibe
    # deshalb vor ihr einen wahrheitsgetreuen Eintrag: die Arbeit ist
    # abgeschlossen und wartet auf Endpruefung. Das Endergebnis folgt danach.
    pending_for_run = phase_state.data.get(
        "phase_end_verify_pending_run_id",
    )
    if (
        rc == 0
        and not state.progress_written_at_commit
        and (
            not phase_state.run_id
            or pending_for_run != phase_state.run_id
        )
    ):
        from werkstatt import progress as _progress
        _progress.append(
            pd,
            name=f"Endpruefung: {project_name}",
            status="verify_pending",
            info=f"tasks_ok={tasks_ok}/{len(tasks)}",
            run_id=getattr(state, "run_id", None),
        )
        if phase_state.run_id:
            phase_state.data["phase_end_verify_pending_run_id"] = phase_state.run_id
            phase_state.save()
        if checkpointed:
            from werkstatt.failure_record import _worktree_fingerprint

            pending_fingerprint = (
                _worktree_fingerprint(Path(pd)) if pd else None
            )
            if pending_fingerprint != phase_state.data.get(
                "human_gate_checkpoint", {},
            ).get("worktree_sha256"):
                audit(
                    "loop_phase",
                    {
                        "phase": "phase_end_verify",
                        "status": "checkpoint_stale",
                        "reason": "verify_pending_progress_changed_worktree",
                    },
                    pd,
                    pn,
                )
                return 3

    def _verify_phase_end_tree() -> bool:
        from werkstatt.failure_record import _worktree_fingerprint

        before = _worktree_fingerprint(Path(pd)) if pd else None
        verify_ok = _verify_patches(state, phase="phase_end")
        after = _worktree_fingerprint(Path(pd)) if pd else None
        stable = before is not None and before == after
        results = getattr(state, "last_verify_results", None)
        if (
            verify_ok
            and isinstance(results, list)
            and results
            and isinstance(results[0], dict)
        ):
            results[0]["phase_end_tree_sha256"] = before
            results[0]["phase_end_tree_stable"] = stable
        return bool(verify_ok and stable)

    if rc == 0 and not _verify_phase_end_tree():
        failure_record = create_failure_record(state, stage="phase_end")
        if checkpointed:
            recorder = getattr(
                phase_state, "record_phase_end_verify_failure", None,
            )
            persisted = bool(
                callable(recorder)
                and recorder(
                    failure_record,
                    project_dir=Path(pd),
                )
            )
            if persisted:
                audit(
                    "loop_verify_recovery_started",
                    {
                        "failure_id": failure_record.get("failure_id"),
                        "artifact_ref": failure_record.get("artifact_ref"),
                        "stage_ids": [
                            str(item.get("stage_id") or "?")
                            for item in failure_record.get("failed_stages", [])
                            if isinstance(item, dict)
                        ][:12],
                        "dispatch": "coordinator_checkpoint",
                        "result_summary": (
                            "Die Abschlusspruefung ist fehlgeschlagen; der "
                            "Beleg wurde fuer eine separate Recovery-Entscheidung gespeichert."
                        ),
                        "decision_summary": (
                            "Der Koordinator entscheidet nach diesem Verify-Schritt "
                            "ueber einen gezielten Recovery-Aufruf."
                        ),
                    },
                    pd,
                    pn,
                )
                return 3
            audit(
                "loop_verify_recovery_stalled",
                {
                    "failure_id": failure_record.get("failure_id"),
                    "artifact_ref": failure_record.get("artifact_ref"),
                    "reason": "failure_checkpoint_missing_or_repeated_worktree",
                    "result_summary": (
                        "Die Verify-Fehlerbelege konnten nicht als neuer "
                        "Recovery-Checkpoint gespeichert werden."
                    ),
                    "decision_summary": (
                        "Der Run stoppt fail-closed; derselbe Worktree wird "
                        "nicht erneut automatisch repariert."
                    ),
                },
                pd,
                pn,
            )
            return 1
        audit(
            "loop_gate_failed",
            _gate_failed_payload(
                "phase_end", getattr(state, "last_verify_errors", []) or [],
            ),
            pd,
            pn,
        )
        return 1

    verify_results = getattr(state, "last_verify_results", None)
    verify_tree_changed = bool(
        isinstance(verify_results, list)
        and verify_results
        and isinstance(verify_results[0], dict)
        and verify_results[0].get("phase_end_tree_stable") is False
    )
    if checkpointed and verify_tree_changed:
        audit(
            "loop_phase",
            {
                "phase": "phase_end_verify",
                "status": "checkpoint_stale",
                "reason": "worktree_changed_during_verify",
            },
            pd,
            pn,
        )
        return 3

    return rc


def _phase_finalize(
    state: RunState,
    tasks_ok: int,
    tasks: list,
    project_name: str,
    phase_state,
    *,
    phase_review_checkpointed: bool = False,
    human_gate_checkpointed: bool = False,
    phase_end_verify_checkpointed: bool = False,
    commit_checkpointed: bool = False,
) -> int:
    """Persist completion only after independent checkpoint actions pass."""
    pd = state.project_dir
    pn = state.project_name
    from werkstatt.failure_record import _worktree_fingerprint

    checkpoint_fingerprint = _worktree_fingerprint(Path(pd))
    if commit_checkpointed:
        head_result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=pd,
            capture_output=True, text=True, check=False, timeout=15,
        )
        head_sha = head_result.stdout.strip()
        snapshot_ok, _snapshot = (
            _post_commit_snapshot_check(Path(pd), head_sha)
            if head_result.returncode == 0 and head_sha
            else (False, {"reason": "head_read_failed"})
        )
        verify_checkpoint = phase_state.data.get(
            "phase_end_verify_checkpoint", {},
        )
        if (
            not snapshot_ok
            or not phase_state.commit_checkpoint_is_current(commit_sha=head_sha)
            or not isinstance(verify_checkpoint, dict)
        ):
            audit(
                "loop_phase",
                {"phase": "commit", "status": "checkpoint_stale",
                 "reason": "commit_checkpoint_missing_or_head_changed"},
                pd, pn,
            )
            return 3
        checkpoint_fingerprint = verify_checkpoint.get("worktree_sha256")

    # Review, approval and Verify are independent coordinator actions. The
    # finalizer never recreates the old fixed chain when a checkpoint is absent.
    if not (
        phase_review_checkpointed
        and human_gate_checkpointed
        and phase_end_verify_checkpointed
    ):
        audit(
            "loop_phase",
            {"phase": "finalize_run", "status": "checkpoint_missing",
             "reason": "review_gate_verify_must_be_coordinator_actions"},
            pd, pn,
        )
        return 3
    if not phase_state.phase_end_review_is_current(
        worktree_fingerprint=checkpoint_fingerprint,
    ):
        audit(
            "loop_phase",
            {"phase": "phase_end_review", "status": "checkpoint_stale",
             "reason": "worktree_or_plan_changed_before_finalize"},
            pd, pn,
        )
        return 3
    if not phase_state.human_gate_is_current(
        worktree_fingerprint=checkpoint_fingerprint,
    ):
        audit(
            "loop_phase",
            {"phase": "human_gate", "status": "checkpoint_stale",
             "reason": "worktree_or_plan_changed_before_finalize"},
            pd, pn,
        )
        return 3
    gate_checkpoint = phase_state.data.get("human_gate_checkpoint", {})
    _commit_requested = bool(
        isinstance(gate_checkpoint, dict)
        and gate_checkpoint.get("commit_requested") is True
    )
    rc = 0
    from werkstatt.phase_state import phase_end_verify_evidence
    verify_checkpoint = phase_state.data.get("phase_end_verify_checkpoint", {})
    if commit_checkpointed and isinstance(verify_checkpoint, dict):
        verify_fingerprint = verify_checkpoint.get("worktree_sha256")
        evidence_sha256 = verify_checkpoint.get("evidence_sha256")
    else:
        verify_fingerprint = checkpoint_fingerprint
        evidence_sha256, _stage_ids = phase_end_verify_evidence(
            getattr(state, "last_verify_results", None),
        )
    if not phase_state.phase_end_verify_is_current(
        worktree_fingerprint=verify_fingerprint,
        evidence_sha256=evidence_sha256,
    ):
        audit(
            "loop_phase",
            {"phase": "phase_end_verify", "status": "checkpoint_stale",
             "reason": "worktree_plan_or_evidence_changed_before_finalize"},
            pd, pn,
        )
        return 3

    # OP-060b: human_review-Tasks offen + Mensch approved -> rc=2.
    if rc == 0 and _hat_human_review_tasks(phase_state):
        audit("loop_human_review_offen",
              {"phase": "human_gate"}, pd, pn)
        rc = 2

    if rc == 0 and _commit_requested and not commit_checkpointed:
        audit(
            "loop_phase",
            {"phase": "finalize_run", "status": "commit_checkpoint_missing",
             "reason": "commit_must_be_coordinator_action"},
            pd, pn,
        )
        return 3

    if rc == 0:
        # OP-398: Ein gruenes Verify reicht nicht fuer einen gruenen Run,
        # wenn geplante Tasks fehlgeschlagen, blockiert oder offen sind.
        _records = None
        _phase_data = getattr(phase_state, "data", None)
        if isinstance(_phase_data, dict):
            _candidate = _phase_data.get("tasks")
            if isinstance(_candidate, list):
                _records = [
                    record for record in _candidate
                    if not (
                        isinstance(record, dict)
                        and record.get("status") == "superseded"
                    )
                ]
        if not _records:
            _records = tasks or []

        _unresolved = []
        for _index, _task_record in enumerate(_records, 1):
            if not isinstance(_task_record, dict):
                _unresolved.append({"task_id": f"task-{_index}", "status": "invalid"})
                continue
            _task_id = _task_record.get("id")
            _status_record = (
                phase_state.get_task(_task_id)
                if _task_id and phase_state is not None
                else _task_record
            )
            _task_status = (
                _status_record.get("status")
                if isinstance(_status_record, dict)
                else None
            )
            if _task_status != "done":
                _unresolved.append({
                    "task_id": _task_id or f"task-{_index}",
                    "status": _task_status or "missing",
                })

        _criterion_progress = (
            phase_state.criteria_progress()
            if phase_state is not None
            and callable(getattr(phase_state, "criteria_progress", None))
            else {"tracked": False, "valid": True, "covered": [], "uncovered": []}
        )
        _phase_data = getattr(phase_state, "data", {})
        _explicit_criteria = (
            _phase_data.get("akzeptanzkriterien")
            if isinstance(_phase_data, dict)
            else None
        )
        _has_explicit_criteria = bool(_explicit_criteria)
        _criteria_untracked = bool(
            _has_explicit_criteria
            and (
                not isinstance(_criterion_progress, dict)
                or _criterion_progress.get("tracked") is not True
            )
        )
        _criteria_unresolved = bool(
            isinstance(_criterion_progress, dict)
            and _criterion_progress.get("tracked") is True
            and (
                _criterion_progress.get("valid") is not True
                or _criterion_progress.get("uncovered")
            )
        )
        if (
            tasks_ok <= 0 or _unresolved or _criteria_unresolved
            or _criteria_untracked
        ):
            _reason = (
                "no_successful_tasks"
                if tasks_ok <= 0
                else "tasks_unresolved"
                if _unresolved
                else "criteria_untracked"
                if _criteria_untracked
                else "criteria_unresolved"
            )
            _completion = {
                "phase": "completion",
                "status": "incomplete",
                "reason": _reason,
                "tasks_ok": tasks_ok,
                "tasks_total": len(_records),
                "unresolved": _unresolved[:50],
            }
            if _criteria_unresolved or _criteria_untracked:
                _completion["criteria_covered"] = _criterion_progress.get(
                    "covered", [],
                ) if isinstance(_criterion_progress, dict) else []
                _completion["criteria_uncovered"] = _criterion_progress.get(
                    "uncovered", [],
                ) if isinstance(_criterion_progress, dict) else []
                _completion["criteria_error"] = (
                    _criterion_progress.get("error")
                    if isinstance(_criterion_progress, dict)
                    else "invalid_criteria_progress"
                ) or ("criteria_not_tracked" if _criteria_untracked else None)
            audit("loop_phase", _completion, pd, pn)
            rc = 1
        else:
            _goal_evidence_complete = not _has_explicit_criteria
            _criteria_evidence_gaps: list[str] = []
            if (
                isinstance(_criterion_progress, dict)
                and _criterion_progress.get("tracked") is True
                and _criterion_progress.get("valid") is True
                and not _criterion_progress.get("uncovered")
            ):
                _criteria_evidence, _criteria_evidence_gaps = (
                    _criterion_evidence_rows(
                        _phase_data.get("akzeptanzkriterien")
                        if isinstance(_phase_data, dict) else None,
                        _records,
                        phase_state,
                        getattr(state, "last_verify_results", None),
                    )
                )
                _criteria_verified = not _criteria_evidence_gaps
                _goal_evidence_complete = _criteria_verified
                audit(
                    "loop_criteria_progress",
                    {
                        "status": (
                            "verified"
                            if _criteria_verified
                            else "checks_passed_unverified"
                        ),
                        "tracked": True,
                        "coverage_basis": (
                            "criterion_task_mapping_task_verify_and_phase_end"
                            if _criteria_verified
                            else "task_graph_and_phase_checks_only"
                        ),
                        "covered": _criterion_progress.get("covered", []),
                        "remaining": [],
                        "verification": "phase_end",
                        "criteria_evidence": _criteria_evidence,
                        "evidence_gaps": _criteria_evidence_gaps,
                        "decision_summary": (
                            "Jedes Akzeptanzkriterium ist auf erledigte Tasks "
                            "mit taskgebundenen Verify-Belegen sowie die "
                            "Phase-End-Verify zurueckgefuehrt."
                            if _criteria_verified else
                            "Tasks und Abschlusspruefung sind gruen, aber die "
                            "kriterienspezifische Belegkette ist unvollstaendig."
                        ),
                        "evidence": [
                            "Alle zugeordneten Tasks sind erledigt.",
                            "Phase-End-Review, Human Gate und Abschluss-Verify bestanden.",
                            *(
                                ["Kriterien, erledigte Tasks, deren Verify-Belege und die Phase-End-Verify sind verknuepft."]
                                if _criteria_verified else
                                ["Kein Zielnachweis: Belegluecken "
                                 + ", ".join(_criteria_evidence_gaps[:8])]
                            ),
                        ],
                    },
                    pd,
                    pn,
                )
            if _goal_evidence_complete:
                audit("loop_erfolg", {"project_name": project_name}, pd, pn)
            elif _has_explicit_criteria:
                audit(
                    "loop_phase",
                    {
                        "phase": "completion",
                        "status": "incomplete",
                        "reason": "criteria_evidence_incomplete",
                        "criteria_evidence_gaps": (
                            _criteria_evidence_gaps[:20]
                            if isinstance(_criteria_evidence_gaps, list)
                            else ["criteria_evidence_missing"]
                        ),
                        "next_step": (
                            "Belegluecken schliessen und die Abschluss-Verify "
                            "erneut ausfuehren; der Run wird nicht als Erfolg markiert."
                        ),
                    },
                    pd,
                    pn,
                )
                rc = 1

    # M-307b: Phasen-Ende in PROGRESS.md
    # FIX AH 2026-10-31: Wurde bei jedem Loop-Ende geschrieben,
    # ausser wenn _committe_zielprojekt den Eintrag VOR git add
    # geschrieben hat (Flag progress_written_at_commit).
    if not state.progress_written_at_commit:
        from werkstatt import progress as _progress
        _progress.append(
            pd,
            name=f"Phase abgeschlossen: {project_name}",
            status="phase_ende",
            info=f"rc={rc} tasks_ok={tasks_ok}/{len(tasks)}",
            run_id=getattr(state, "run_id", None),
        )

    # M-456: Zusammenfassung.
    try:
        _total = len(tasks)
        _failed = _total - tasks_ok
        summary(tasks_ok, _failed, 0)
    except Exception:
        pass

    return rc

