"""Checkpoint action that validates goal completion evidence."""
from __future__ import annotations

import subprocess
from pathlib import Path

from werkstatt.audit import audit
from werkstatt.failure_record import _worktree_fingerprint
from werkstatt.phase_state import phase_end_verify_evidence
from werkstatt.phases._common import _hat_human_review_tasks
from werkstatt.phases.finalize import (
    _criterion_evidence_rows,
    _post_commit_snapshot_check,
)
from werkstatt.render import summary
from werkstatt.state import RunState


def run_completion_checkpoint(
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
    """Validate completed goal evidence and persist the run outcome."""
    pd = state.project_dir
    pn = state.project_name
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

