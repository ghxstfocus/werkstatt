"""Persisted, checkpoint-driven coordinator for goal-oriented project runs.

Each dispatch selects one permitted action from current goal, evidence,
progress, authorization, risk, and budget. Executor modules may retain their
historical names during migration, but they do not define a global run order.
"""
from __future__ import annotations

import hashlib
import json
import re
import signal
import subprocess  # noqa: F401  # re-export: Tests patchen werkstatt.loop.subprocess
import time  # noqa: F401  # re-export: Tests patchen werkstatt.loop.time
from pathlib import Path
from typing import Any, Literal

from werkstatt.apply_patches import (  # Fix AZ Stufe 4: Re-Export
    _apply_one_patch,
    _apply_patches_with_diagnose,
    _apply_patches_with_hooks,
    _delete_ziel_erlaubt,
    _diagnose_patch,
    _patches_wirklich_angewendet,
)
from werkstatt.audit import audit, get_run_id, set_run_id
from werkstatt.committer import (  # Fix AZ Stufe 5a: Re-Export
    _committe_zielprojekt,
    _task_fortschritt_block,
)
from werkstatt.env_loader import load_env
from werkstatt.event_store import (
    EventStore,
    RunInboxPendingError,
    RunLeaseBusy,
    RunLeaseLost,
)
from werkstatt.explorer import run_explorer
from werkstatt.gates import (  # Fix AZ Stufe 5b: Re-Export
    _human_gate,
    _human_gate_plan,
    _plan_gate,
)
from werkstatt.git_ops import (  # Fix AZ Stufe 1: Re-Export
    _get_git_diff_for_hook,
    _git_dirty,
    _git_head,
    _git_reset,
    _git_stash,
    _git_stash_owned,
    _git_stash_pop,
)
from werkstatt.hooks import _call_hook  # Fix AZ Stufe 2: Re-Export
from werkstatt.phase_state import PhaseState
from werkstatt.planner import run_planner
from werkstatt.reflection import (  # Fix AZ Stufe 6: Re-Export
    _phase_end_reflection,
    _reflection_loop,
)
from werkstatt.render import (
    _with_spinner,
    group_end,
    group_start,
    header,
    log_line,
    step,
    summary,
    task,
    task_done,
    task_ok,
    task_started,
)
from werkstatt.reviewer import run_reviewer
from werkstatt.roles.builder import run_builder
from werkstatt.roles.checkpoint_actions import (
    _phase_end_review_action,
    _phase_end_verify_action,
    _phase_human_gate_action,
)
from werkstatt.roles.project_context import collect_project_context
from werkstatt.roles.task_dispatch import run_task_checkpoint
from werkstatt.runtime_compat import (
    _gate_failed_payload,
    _hat_human_review_tasks,
    _normalize_tasks,
)
from werkstatt.state import RunState, check_run_lease
from werkstatt.task_runner import (  # Fix AZ Stufe 7: Re-Export
    _extract_files_from_tasks,
    _pruefe_prior_failed_dependency,
    _task_ende,
)
from werkstatt.verify import (  # Fix AZ Stufe 3: Re-Export
    _expand_cmd_placeholders,
    _get_baseline_error_details,
    _resolve_venv_cmd,
    _ruff_fix_changed,
    _stage_ist_hart,
    _verify_patches,
    _verify_patches_soft,
    _verify_stage_with_heartbeat,
)

_LIFECYCLE_PROJECT = ""
_STOP_SIGNAL: int | None = None
_STOP_SIGNAL_DEFERRED = False


class _LoopStopRequested(Exception):
    """Interner, kontrollierter Abbruch nach einem SIGTERM."""

    def __init__(self, signum: int):
        super().__init__(f"Loop gestoppt (Signal {signum})")
        self.signum = signum


def _handle_loop_sigterm(signum: int, _frame: object) -> None:
    """Unwindet den Loop kontrolliert; doppelte Signale stoeren Cleanup nicht."""
    global _STOP_SIGNAL
    if _STOP_SIGNAL is not None:
        return
    _STOP_SIGNAL = signum
    if not _STOP_SIGNAL_DEFERRED:
        raise _LoopStopRequested(signum)

# Oeffentliche API (Re-Exports + lokale Funktionen).
# ruff F401 entfernt sonst Re-Exports, die von Tests/Aufrufern
# importiert werden. __all__ ist die offizielle Python-Deklaration.
__all__ = [
    "Path",
    "PhaseState",
    "RunState",
    "_apply_one_patch",
    "_apply_patches_with_diagnose",
    "_apply_patches_with_hooks",
    "_call_hook",
    "_committe_zielprojekt",
    "_delete_ziel_erlaubt",
    "_diagnose_patch",
    "_expand_cmd_placeholders",
    "_extract_files_from_tasks",
    "_get_baseline_error_details",
    "_get_git_diff_for_hook",
    "_git_dirty",
    "_git_head",
    "_git_reset",
    "_git_stash",
    "_git_stash_owned",
    "_git_stash_pop",
    "_human_gate",
    "_human_gate_plan",
    "_normalize_tasks",
    "_patches_wirklich_angewendet",
    "_phase_end_reflection",
    "_plan_gate",
    "_pruefe_prior_failed_dependency",
    "_reflection_loop",
    "_resolve_venv_cmd",
    "_ruff_fix_changed",
    "_stage_ist_hart",
    "_task_ende",
    "_task_fortschritt_block",
    "_verify_patches",
    "_verify_patches_soft",
    "_verify_stage_with_heartbeat",
    "_with_spinner",
    "annotations",
    "audit",
    "collect_project_context",
    "group_end",
    "group_start",
    "header",
    "load_env",
    "log_line",
    "run_builder",
    "run_explorer",
    "run_planner",
    "run_reviewer",
    "run_task_checkpoint",
    "step",
    "summary",
    "task",
    "task_done",
    "task_ok",
    "task_started",
]


from werkstatt.paths import projects_dir as _projects_dir

PROJECTS_DIR = _projects_dir()




def _run_with_progress(
    fn,
    nr: int,
    total: int,
    name: str,
) -> object:
    """M-327: Ruft fn() auf, zeigt alle 2s eine Status-Zeile.

    Verhindert den Eindruck, der Loop haenge (Builder-LLM-Call
    dauert 20-40s, ask_llm timeout 120s).

    Nutzt loop_renderer.heartbeat (M-301), das im CI-Modus
    mit Zeitstempel schreibt. TTY-Modus: Carriage-Return.
    """
    import threading as _threading
    import time as _time

    from werkstatt import render as _r

    _result: list = [None]
    _exc: list = [None]
    _done = _threading.Event()

    def _worker():
        try:
            _result[0] = fn()
        except Exception as e:
            _exc[0] = e
        finally:
            _done.set()

    def _heartbeat_loop():
        """M-327c: Heartbeat in eigenem Thread.

        Der Worker-Thread (ask_llm, HTTP+JSON) blockiert den
        Main-Thread durch die GIL. Der Heartbeat-Thread laeuft
        trotzdem weiter, weil _done.wait() die GIL freigibt.

        M-371: Nutzt spinner_start/spinner_update, wenn der
        Renderer im live-Modus ist. In ci/pretty: heartbeat.
        """
        _start_hb = _time.monotonic()
        _last_hb = -1
        # M-377: KEIN spinner_start hier — task()/task_ok() steuert
        # den Live-Bereich. Nur heartbeat (No-Op in live, wenn
        # Heartbeat spinner_update ruft).
        while not _done.is_set():
            _elapsed_hb = int(_time.monotonic() - _start_hb)
            if _elapsed_hb // 2 > _last_hb // 2:
                try:
                    _r.heartbeat(f"[{nr}/{total}] {name}", _elapsed_hb)
                except Exception:
                    pass
                _last_hb = _elapsed_hb
            _done.wait(timeout=0.5)

    _t = _threading.Thread(target=_worker, daemon=True)
    _t_hb = _threading.Thread(target=_heartbeat_loop, daemon=True)
    _t.start()
    _t_hb.start()
    _t.join()
    _t_hb.join()

    if _exc[0] is not None:
        # M-357: Exception nicht re-raisen, sondern als False
        # zurueckgeben, damit der Aufrufer (Task-Loop) den
        # Fehlerpfad mit Audit + _task_ende durchlaeuft.
        import logging as _logging
        _logging.getLogger(__name__).exception(
            "run_with_progress exception: %s", _exc[0]
        )
        return False
    return _result[0]




def load_project_config(project_name: str) -> dict:
    """Laedt die Projekt-Konfiguration (Loop-eigene Variante).

    BEWUSST eigenstaendig, NICHT Alias auf pipeline.load_project_config.
    Grund: pipeline.load_project_config macht sys.exit(1) bei fehlender
    YAML (Fail-closed). Der Loop braucht Fallback-Verhalten
    (/opt/<name>), damit run_pipeline_loop auch ohne project-yaml
    startet. Die beiden Funktionen sind semantisch unterschiedlich.
    Aufloesung der Doppel-Definition nach Phase >20 (M-299+).

    Liefert ein dict mit 'project_dir' (Pfad zum Zielprojekt).
    Fallback: /opt/<project_name>, wenn keine YAML existiert.
    """
    import yaml
    cfg_path = PROJECTS_DIR / f"{project_name}.yaml"
    if cfg_path.exists():
        try:
            with cfg_path.open(encoding="utf-8") as fh:
                cfg = yaml.safe_load(fh) or {}
            if "project_dir" in cfg:
                return cfg
        except (yaml.YAMLError, OSError):
            pass
    # Fallback: /opt/<project_name>
    fallback_dir = Path(f"/opt/{project_name}")
    if fallback_dir.exists():
        return {"project_dir": str(fallback_dir)}
    return {"project_dir": None}










def _persist_run_result(
    store: EventStore,
    project_name: str,
    run_id: str,
    exit_code: int,
    *,
    run_state: RunState | None = None,
    phase_state: PhaseState | None = None,
) -> None:
    """Drain accepted chat input, then atomically mark the run terminal."""
    status: Literal["completed", "failed"] = (
        "completed" if exit_code == 0 else "failed"
    )
    current = store.get_run_record(project_name, run_id)
    if current is None:
        return
    if current["status"] in {"completed", "failed"}:
        if (
            current["status"] == status
            and current["checkpoint"].get("exit_code") == exit_code
        ):
            return
        # Terminal records are immutable. A duplicate/stale caller must not
        # overwrite them with a different exit code or status.
        return
    if run_state is not None:
        from werkstatt.run_checkpoint import persist_run_checkpoint

        if phase_state is None:
            phase_state = PhaseState(
                project_name,
                base_dir=Path(run_state.project_dir) / ".werkstatt",
            )
            phase_state.load()
        handled_kinds = {
            "job_notice", "job_result_notice", "chat_followup_request",
        }
        while True:
            check_run_lease(run_state)
            persist_run_checkpoint(
                store, project_name, run_id, phase_state, None,
                run_state=run_state,
            )
            record = store.get_run_record(project_name, run_id)
            if record is None:
                return
            checkpoint = dict(record["checkpoint"])
            if status == "completed":
                followups = checkpoint.get("chat_followup_requests", [])
                if not isinstance(followups, list) or any(
                    not isinstance(item, dict) for item in followups
                ):
                    raise RunInboxPendingError(
                        "Run kann nicht erfolgreich enden; Follow-up-Ledger "
                        "im Checkpoint ist ungueltig.",
                    )
                unresolved = [
                    item for item in followups
                    if item.get("status") not in {"applied", "rejected"}
                ]
                if unresolved:
                    raise RunInboxPendingError(
                        "Run kann nicht erfolgreich enden; bestaetigte Chat-"
                        "Folgeauftraege warten noch auf Plan und Freigabe.",
                    )
            checkpoint["exit_code"] = exit_code
            version = store.finish_run_checkpoint(
                project_name,
                run_id,
                checkpoint,
                expected_version=record["checkpoint_version"],
                status=status,
            )
            if version is not None:
                return
            pending_kinds = store.pending_run_message_kinds(project_name, run_id)
            unsupported = pending_kinds - handled_kinds
            if unsupported:
                raise RunInboxPendingError(
                    "Run-Inbox enthaelt nicht verarbeitbare Nachrichtentypen: "
                    + ", ".join(sorted(unsupported)),
                )

    record = store.get_run_record(project_name, run_id)
    if record is None:
        return
    checkpoint = dict(record["checkpoint"])
    checkpoint["exit_code"] = exit_code
    if store.finish_run_checkpoint(
        project_name,
        run_id,
        checkpoint,
        expected_version=record["checkpoint_version"],
        status=status,
    ) is None:
        pending_kinds = store.pending_run_message_kinds(project_name, run_id)
        raise RunInboxPendingError(
            "Run kann nicht terminal werden; offene Inbox-Nachricht(en): "
            + (", ".join(sorted(pending_kinds)) or "unbekannt"),
        )


def _run_phase_end_review_checkpoint(
    state: RunState,
    phase_state: PhaseState,
    project_name: str,
) -> int:
    """Run one review action and bind its result to the current worktree."""
    check_run_lease(state)
    tasks_ok = len([
        record for record in phase_state.data.get("tasks", [])
        if isinstance(record, dict) and record.get("status") == "done"
    ])
    review_rc = _phase_end_review_action(state, tasks_ok, phase_state)
    if review_rc != 0:
        return review_rc
    from werkstatt.failure_record import _worktree_fingerprint

    fingerprint = (
        _worktree_fingerprint(Path(state.project_dir))
        if state.project_dir else None
    )
    if fingerprint is None:
        audit(
            "loop_failed",
            {"reason": "phase_end_review_fingerprint_unavailable"},
            state.project_dir,
            project_name,
        )
        return 1
    try:
        phase_state.record_phase_end_review(worktree_fingerprint=fingerprint)
    except (AttributeError, ValueError) as exc:
        audit(
            "loop_failed",
            {
                "reason": "phase_end_review_checkpoint_invalid",
                "error": str(exc)[:300],
            },
            state.project_dir,
            project_name,
        )
        return 1
    audit(
        "loop_phase",
        {
            "phase": "phase_end_review",
            "status": "checkpointed",
            "worktree_sha256": fingerprint,
        },
        state.project_dir,
        project_name,
    )
    return 0


def _run_human_gate_checkpoint(
    state: RunState,
    phase_state: PhaseState,
    project_name: str,
) -> int:
    """Run the Human Gate only from a current phase-review checkpoint."""
    check_run_lease(state)
    from werkstatt.failure_record import _worktree_fingerprint

    before = (
        _worktree_fingerprint(Path(state.project_dir))
        if state.project_dir else None
    )
    if (
        before is None
        or not phase_state.phase_end_review_is_current(
            worktree_fingerprint=before,
        )
    ):
        audit(
            "loop_phase",
            {
                "phase": "human_gate",
                "status": "checkpoint_stale",
                "reason": "phase_end_review_missing_or_stale",
            },
            state.project_dir,
            project_name,
        )
        return 3

    gate_rc, commit_requested = _phase_human_gate_action(state)
    if gate_rc not in (0, 2):
        return gate_rc
    after = (
        _worktree_fingerprint(Path(state.project_dir))
        if state.project_dir else None
    )
    if (
        after != before
        or not phase_state.phase_end_review_is_current(
            worktree_fingerprint=after,
        )
    ):
        audit(
            "loop_phase",
            {
                "phase": "human_gate",
                "status": "checkpoint_stale",
                "reason": "worktree_changed_during_human_gate",
            },
            state.project_dir,
            project_name,
        )
        return 3
    if gate_rc == 0 and _hat_human_review_tasks(phase_state):
        audit(
            "loop_human_review_offen",
            {"phase": "human_gate"},
            state.project_dir,
            project_name,
        )
        return 2
    try:
        phase_state.record_human_gate(
            worktree_fingerprint=after,
            commit_requested=commit_requested,
        )
    except (AttributeError, ValueError) as exc:
        audit(
            "loop_failed",
            {
                "reason": "human_gate_checkpoint_invalid",
                "error": str(exc)[:300],
            },
            state.project_dir,
            project_name,
        )
        return 1
    audit(
        "loop_phase",
        {
            "phase": "human_gate",
            "status": "checkpointed",
            "worktree_sha256": after,
            "commit_requested": commit_requested,
        },
        state.project_dir,
        project_name,
    )
    return 0


def _run_phase_end_verify_checkpoint(
    state: RunState,
    phase_state: PhaseState,
    project_name: str,
) -> int:
    """Run final verification only after current review and human approval."""
    check_run_lease(state)
    from werkstatt.failure_record import _worktree_fingerprint
    from werkstatt.phase_state import phase_end_verify_evidence

    before = (
        _worktree_fingerprint(Path(state.project_dir))
        if state.project_dir else None
    )
    if (
        before is None
        or not phase_state.phase_end_review_is_current(
            worktree_fingerprint=before,
        )
        or not phase_state.human_gate_is_current(
            worktree_fingerprint=before,
        )
    ):
        audit(
            "loop_phase",
            {
                "phase": "phase_end_verify",
                "status": "checkpoint_stale",
                "reason": "review_or_human_gate_missing_or_stale",
            },
            state.project_dir,
            project_name,
        )
        return 3

    tasks_ok = len([
        record for record in phase_state.data.get("tasks", [])
        if isinstance(record, dict) and record.get("status") == "done"
    ])
    verify_rc = _phase_end_verify_action(
        state, tasks_ok, state.tasks, project_name, phase_state,
        checkpointed=True,
    )
    if verify_rc != 0:
        return verify_rc
    after = (
        _worktree_fingerprint(Path(state.project_dir))
        if state.project_dir else None
    )
    verify_results = getattr(state, "last_verify_results", None)
    verified_fingerprint = (
        verify_results[0].get("phase_end_tree_sha256")
        if isinstance(verify_results, list)
        and verify_results
        and isinstance(verify_results[0], dict)
        and verify_results[0].get("phase_end_tree_stable") is True
        else None
    )
    if (
        after is not None
        and verified_fingerprint is not None
        and after != verified_fingerprint
    ):
        audit(
            "loop_phase",
            {
                "phase": "phase_end_verify",
                "status": "checkpoint_stale",
                "reason": "worktree_changed_after_verify",
            },
            state.project_dir,
            project_name,
        )
        return 3
    evidence_sha256, stage_ids = phase_end_verify_evidence(
        getattr(state, "last_verify_results", None),
    )
    if (
        after is None
        or verified_fingerprint is None
        or evidence_sha256 is None
        or not stage_ids
    ):
        audit(
            "loop_failed",
            {
                "reason": "phase_end_verify_evidence_unavailable",
                "stage_count": len(stage_ids),
            },
            state.project_dir,
            project_name,
        )
        return 1
    try:
        phase_state.record_phase_end_verify(
            worktree_fingerprint=after,
            evidence_sha256=evidence_sha256,
            stage_ids=stage_ids,
        )
    except (AttributeError, ValueError) as exc:
        audit(
            "loop_failed",
            {
                "reason": "phase_end_verify_checkpoint_invalid",
                "error": str(exc)[:300],
            },
            state.project_dir,
            project_name,
        )
        return 1
    audit(
        "loop_phase",
        {
            "phase": "phase_end_verify",
            "status": "checkpointed",
            "worktree_sha256": after,
            "evidence_sha256": evidence_sha256,
            "stage_ids": stage_ids,
        },
        state.project_dir,
        project_name,
    )
    return 0


def _run_phase_end_verify_recovery_checkpoint(
    state: RunState,
    phase_state: PhaseState,
    project_name: str,
) -> int:
    """Run one coordinator-selected repair from current final-verify evidence."""
    check_run_lease(state)
    claim = phase_state.claim_phase_end_verify_recovery(
        project_dir=Path(state.project_dir),
    )
    if claim is None:
        audit(
            "loop_verify_recovery_checkpoint_rejected",
            {"reason": "stale_or_already_attempted"},
            state.project_dir,
            project_name,
        )
        return 3
    from werkstatt.roles.verify_recovery import (
        run_phase_end_verify_recovery,
    )

    try:
        result = run_phase_end_verify_recovery(state, claim)
    except Exception as exc:  # noqa: BLE001 - persist failure at coordinator boundary
        result = {
            "status": "failed",
            "reason": f"recovery_error:{type(exc).__name__}",
            "stage_ids": [],
        }
    audit(
        "loop_verify_recovery_result",
        {
            "failure_id": claim.get("failure_id"),
            "status": result.get("status"),
            "reason": result.get("reason"),
            "stage_ids": result.get("stage_ids", []),
            "dispatch": "coordinator_checkpoint",
        },
        state.project_dir,
        project_name,
    )
    if result.get("status") == "repair_handoff":
        return 3
    return 1


def _run_commit_checkpoint(
    state: RunState,
    phase_state: PhaseState,
    project_name: str,
) -> int:
    """Commit from current approval, then yield for a separate Verify action."""
    check_run_lease(state)
    from werkstatt.failure_record import _worktree_fingerprint
    from werkstatt.phase_state import phase_end_verify_evidence
    from werkstatt.roles.checkpoint_actions import _approved_commit

    before = (
        _worktree_fingerprint(Path(state.project_dir))
        if state.project_dir else None
    )
    verify = phase_state.data.get("phase_end_verify_checkpoint")
    verify = verify if isinstance(verify, dict) else {}
    evidence_sha256 = verify.get("evidence_sha256")
    if (
        before is None
        or not phase_state.phase_end_review_is_current(
            worktree_fingerprint=before,
        )
        or not phase_state.human_gate_is_current(
            worktree_fingerprint=before,
        )
        or not phase_state.phase_end_verify_is_current(
            worktree_fingerprint=before,
            evidence_sha256=evidence_sha256,
        )
        or not isinstance(evidence_sha256, str)
        or phase_state.data.get("human_gate_checkpoint", {}).get(
            "commit_requested",
        ) is not True
    ):
        audit(
            "loop_phase",
            {
                "phase": "commit",
                "status": "checkpoint_stale",
                "reason": "review_gate_or_verify_missing_or_stale",
            },
            state.project_dir,
            project_name,
        )
        return 3

    committed, commit_sha = _approved_commit(state)
    if not committed or not commit_sha:
        audit(
            "loop_phase",
            {
                "phase": "commit",
                "status": "failed",
                "reason": "approved_commit_failed",
            },
            state.project_dir,
            project_name,
        )
        return 1
    from werkstatt.roles.checkpoint_actions import _post_commit_snapshot_check

    snapshot_ok, snapshot = _post_commit_snapshot_check(
        Path(state.project_dir), commit_sha,
    )
    if not snapshot_ok:
        audit(
            "loop_human_gate_commit_post_verify_abort",
            {"sha": commit_sha, **snapshot},
            state.project_dir,
            project_name,
        )
        return 1
    try:
        phase_state.record_commit_pending_post_verify(
            commit_sha=commit_sha,
            verify_evidence_sha256=evidence_sha256,
        )
    except (AttributeError, ValueError) as exc:
        audit(
            "loop_failed",
            {"reason": "commit_pending_checkpoint_invalid",
             "error": str(exc)[:300]},
            state.project_dir,
            project_name,
        )
        return 1
    _pre_evidence_sha256, pre_stage_ids = phase_end_verify_evidence(
        getattr(state, "last_verify_results", None),
    )
    audit(
        "loop_phase",
        {
            "phase": "commit",
            "status": "committed_pending_post_verify",
            "commit_sha": commit_sha,
            "verify_evidence_sha256": evidence_sha256,
            "stage_ids": pre_stage_ids or verify.get("stage_ids", []),
        },
        state.project_dir,
        project_name,
    )
    return 3


def _run_post_commit_verify_checkpoint(
    state: RunState,
    phase_state: PhaseState,
    project_name: str,
) -> int:
    """Verify exactly one committed HEAD; failures return to checkpoint choice."""
    check_run_lease(state)
    from werkstatt.failure_record import (
        _worktree_fingerprint,
        create_failure_record,
    )
    from werkstatt.phase_state import phase_end_verify_evidence
    from werkstatt.roles.checkpoint_actions import _post_commit_snapshot_check

    commit_sha = _git_head(Path(state.project_dir)) if state.project_dir else ""
    pending = phase_state.data.get("commit_pending_post_verify_checkpoint")
    before = (
        _worktree_fingerprint(Path(state.project_dir))
        if state.project_dir else None
    )
    snapshot_ok, snapshot = (
        _post_commit_snapshot_check(Path(state.project_dir), commit_sha)
        if state.project_dir and commit_sha else (False, {"reason": "head_missing"})
    )
    if (
        before is None
        or not snapshot_ok
        or not phase_state.commit_pending_post_verify_is_current(
            commit_sha=commit_sha,
        )
    ):
        audit(
            "loop_phase",
            {"phase": "post_commit_verify", "status": "checkpoint_stale",
             "reason": snapshot.get("reason", "commit_pending_stale")},
            state.project_dir,
            project_name,
        )
        return 3

    verify_ok = bool(_verify_patches(state, phase="phase_end"))
    check_run_lease(state)
    after = (
        _worktree_fingerprint(Path(state.project_dir))
        if state.project_dir else None
    )
    final_snapshot_ok, final_snapshot = _post_commit_snapshot_check(
        Path(state.project_dir), commit_sha,
    ) if state.project_dir else (False, {"reason": "project_dir_missing"})
    if not verify_ok:
        failure_record = create_failure_record(state, stage="post_commit")
        recorder = getattr(
            phase_state, "record_phase_end_verify_failure", None,
        )
        persisted = bool(
            callable(recorder)
            and recorder(failure_record, project_dir=Path(state.project_dir))
        )
        audit(
            "loop_post_commit_verify_failed",
            {
                "sha": commit_sha,
                "failure_id": failure_record.get("failure_id"),
                "artifact_ref": failure_record.get("artifact_ref"),
                "stage_ids": [
                    str(item.get("stage_id") or "?")
                    for item in failure_record.get("failed_stages", [])
                    if isinstance(item, dict)
                ][:12],
                "dispatch": "coordinator_checkpoint" if persisted else "failed_closed",
            },
            state.project_dir,
            project_name,
        )
        return 3 if persisted else 1
    if (
        not final_snapshot_ok
        or after is None
        or before != after
    ):
        audit(
            "loop_human_gate_commit_post_verify_abort",
            {"sha": commit_sha, **final_snapshot,
             "reason": "worktree_changed_during_post_commit_verify"},
            state.project_dir,
            project_name,
        )
        return 3

    post_evidence_sha256, post_stage_ids = phase_end_verify_evidence(
        getattr(state, "last_verify_results", None),
    )
    verify_evidence_sha256 = (
        pending.get("verify_evidence_sha256")
        if isinstance(pending, dict) else None
    )
    if (
        post_evidence_sha256 is None
        or verify_evidence_sha256 is None
        or not post_stage_ids
    ):
        audit(
            "loop_failed",
            {"reason": "commit_post_verify_evidence_missing"},
            state.project_dir,
            project_name,
        )
        return 1
    try:
        phase_state.record_commit_checkpoint(
            commit_sha=commit_sha,
            verify_evidence_sha256=verify_evidence_sha256,
            post_commit_evidence_sha256=post_evidence_sha256,
        )
    except (AttributeError, ValueError) as exc:
        audit(
            "loop_failed",
            {"reason": "commit_checkpoint_invalid", "error": str(exc)[:300]},
            state.project_dir,
            project_name,
        )
        return 1
    phase_state.data.pop("phase_end_verify_failure_checkpoint", None)
    phase_state.save()
    audit(
        "loop_post_commit_verify_passed",
        {"sha": commit_sha, **final_snapshot,
         "stage_ids": post_stage_ids},
        state.project_dir,
        project_name,
    )
    audit(
        "loop_phase",
        {"phase": "commit", "status": "checkpointed",
         "commit_sha": commit_sha,
         "verify_evidence_sha256": verify_evidence_sha256,
         "post_commit_evidence_sha256": post_evidence_sha256,
         "post_commit_stage_ids": post_stage_ids},
        state.project_dir,
        project_name,
    )
    return 0


def _reconcile_chat_followup_checkpoint(
    project_name: str,
    state: RunState,
    phase_state: PhaseState,
) -> bool:
    """Plan at most one received chat follow-up at a coordinator checkpoint."""
    from werkstatt.run_followups import (
        FollowupReconciliationError,
        reconcile_chat_followups,
    )

    run_id = get_run_id()
    store = EventStore()
    changed = reconcile_chat_followups(
        state, phase_state, store, project_name, run_id,
    )
    if changed:
        return True
    latest = store.get_run_record(project_name, run_id)
    checkpoint = latest.get("checkpoint") if isinstance(latest, dict) else None
    requests = (
        checkpoint.get("chat_followup_requests")
        if isinstance(checkpoint, dict) else None
    )
    if isinstance(requests, list) and any(
        isinstance(item, dict) and item.get("status") == "received"
        for item in requests
    ):
        raise FollowupReconciliationError(
            "Chat-Folgeauftrag blieb nach einer Koordinatoraktion unveraendert.",
        )
    return False


def _continue_followup_with_coordinator(
    project_name: str,
    state: RunState,
    phase_state: PhaseState,
) -> int:
    """Resume accepted follow-up work through the single run coordinator."""
    parent_goal = phase_state.data.get("aufgabe")
    if not isinstance(parent_goal, str) or not parent_goal.strip():
        audit(
            "loop_failed",
            {"reason": "followup_parent_goal_missing", "recoverable": False},
            state.project_dir,
            project_name,
            run_id=get_run_id(),
        )
        return 1
    return _run_pipeline_loop_impl(
        project_name,
        parent_goal,
        [state],
        phasen_state=state,
        phase_state=phase_state,
        continuation=True,
        finish_followups=False,
    )


def _run_selected_planner_role_action(state: RunState, action: str) -> bool:
    """Execute only the role selected at the current Planner checkpoint."""
    if action == "planner_scout":
        from werkstatt.roles.scout_execution import run_scout_role_checkpoint

        return bool(run_scout_role_checkpoint(
            state,
            goal=state.aufgabe,
            mark_plan_candidate=lambda: setattr(
                state, "planner_plan_candidate_ready", True,
            ),
        ))
    if action not in {"planner_architect", "planner_split"}:
        return False
    from werkstatt.planner import run_planner

    stop_after_role = (
        "architect" if action == "planner_architect" else "planner_split"
    )
    return bool(run_planner(state, stop_after_role=stop_after_role))


def _prepare_direct_builder_candidate(
    state: RunState,
    goal: str,
) -> bool | None:
    """Create a gated one-file task without entering the Planner executor.

    ``None`` means this route is not applicable (for example, a deterministic
    literal-replacement plan still belongs to the plan compiler). ``False`` is
    a rejected or stale direct handoff and must fail closed.
    """
    context = state.explorer_context
    if not isinstance(context, dict):
        return False
    dispatch = context.get("dispatch")
    key_files = context.get("key_files")
    if (
        not isinstance(dispatch, dict)
        or dispatch.get("selected") != "direct_builder"
        or not isinstance(key_files, list)
        or len(key_files) != 1
        or not isinstance(key_files[0], dict)
    ):
        return False
    target = key_files[0].get("file")
    expected_sha256 = key_files[0].get("source_sha256")
    if (
        not isinstance(target, str)
        or not isinstance(expected_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None
    ):
        return False

    from werkstatt.roles.builder_direct import build_direct_edit_plan
    from werkstatt.roles.planner_dispatch import (
        build_direct_single_file_task,
        current_direct_source_sha256,
        explorer_source_sha256,
        scout_route_decision,
    )

    selected_target, route_reason = scout_route_decision(
        goal, context, state.project_dir,
    )
    context_sha256 = explorer_source_sha256(context, target)
    current_sha256 = current_direct_source_sha256(
        target, state.project_dir,
    )
    if (
        selected_target != target
        or context_sha256 != expected_sha256
        or current_sha256 != expected_sha256
    ):
        audit(
            "planner_role_dispatch_decision",
            {
                "next_role": None,
                "reason": "direct_builder_source_evidence_changed",
                "basis": "direct_checkpoint_revalidated_source_hash",
                "target": target,
            },
            state.project_dir,
            state.project_name,
        )
        return False

    literal_plan, _literal_reason = build_direct_edit_plan(
        goal, target, state.project_dir,
    )
    if literal_plan is not None:
        return None
    task, reason, source_sha256 = build_direct_single_file_task(
        goal,
        target,
        state.project_dir,
        expected_source_sha256=expected_sha256,
    )
    if (
        task is None
        or source_sha256 != expected_sha256
        or not reason
    ):
        audit(
            "planner_role_dispatch_decision",
            {
                "next_role": None,
                "reason": reason or "direct_builder_task_rejected",
                "basis": "direct_checkpoint_task_validation",
                "target": target,
            },
            state.project_dir,
            state.project_name,
        )
        return False

    state.tasks = [task]
    state.tests = [
        "Die fuer geaenderte Dateien konfigurierte Verify-Suite muss erfolgreich sein.",
    ]
    state.akzeptanzkriterien = [goal]
    state.phasen = []
    state.architect_prosa = ""
    state.architect_reasoning_enabled = False
    state.architect_required_source_files = [target]
    if not _plan_gate(state):
        audit(
            "loop_gate_failed",
            _gate_failed_payload("plan", state.tasks, "direct_builder_plan_rejected"),
            state.project_dir,
            state.project_name,
        )
        return False

    input_sha256 = hashlib.sha256(
        f"{goal}\0{source_sha256}".encode(),
    ).hexdigest()
    output_sha256 = hashlib.sha256(json.dumps(
        task, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()
    checkpoint_callback = getattr(
        state, "planner_checkpoint_callback", None,
    )
    if callable(checkpoint_callback):
        for role, role_reason in (
            ("scout", "direct_builder_current_source"),
            ("architect", "single_file_low_risk_goal_needs_no_design_plan"),
            ("planner_split", "single_builder_task_needs_no_graph_split"),
        ):
            checkpoint_callback({
                "role": role,
                "status": "skipped",
                "reason": role_reason,
                "input_sha256": input_sha256,
                "output_sha256": output_sha256,
            })
    audit(
        "planner_role_dispatch_decision",
        {
            "next_role": "builder_direct",
            "reason": route_reason,
            "basis": "direct_checkpoint_current_source_and_plan_gate",
            "target": target,
            "source_sha256": source_sha256,
            "skipped_roles": ["scout", "architect", "planner_split"],
        },
        state.project_dir,
        state.project_name,
    )
    state.planner_plan_candidate_ready = True
    return True


def _dispatch_planner_checkpoint_action(
    state: RunState,
    action: str,
    aufgabe: str,
    project_name: str,
    phase_state: PhaseState,
) -> tuple[int, bool]:
    """Route one coordinator action to its role or taskgraph executor."""
    if action in {"planner_scout", "planner_architect"}:
        success = _run_selected_planner_role_action(state, action)
        return (0 if success else 1), False
    if action == "planner_split":
        from werkstatt.roles.planner_split import (
            run_planner_split_checkpoint,
        )

        direct_success = run_planner_split_checkpoint(state, goal=aufgabe)
        if direct_success is None:
            # Missing or stale handoffs re-enter the compatibility planner,
            # which refreshes only the missing upstream role and yields back.
            split_success = _run_selected_planner_role_action(state, action)
        else:
            split_success = direct_success
        if not split_success:
            return 1, False
        if (
            state.planner_step_yielded
            and state.planner_yielded_after_role != "planner_split"
        ):
            # The selected split cannot proceed until its Architect artifact
            # has been refreshed. Return that dependency checkpoint to the
            # coordinator, which will decide again after the role boundary.
            return 0, False
        if not _plan_gate(state):
            audit(
                "loop_gate_failed",
                _gate_failed_payload(
                    "plan", state.tasks, "planner_split_candidate_rejected",
                ),
                state.project_dir,
                state.project_name,
            )
            return 1, False
        state.planner_plan_candidate_ready = True
        return 0, False
    if action == "planner_direct":
        direct_result = _prepare_direct_builder_candidate(state, aufgabe)
        if direct_result is not None:
            return (0 if direct_result else 1), False
    audit(
        "loop_planner_failed",
        {
            "reason": "unsupported_planner_checkpoint_action",
            "action": str(action or "")[:120],
        },
        state.project_dir,
        project_name,
    )
    return 1, False


def _finish_run_after_followups(
    project_name: str,
    state: RunState,
    phase_state: PhaseState,
    exit_code: int,
) -> int:
    """Drain follow-ups that race with finalization before ending the run.

    A follow-up can arrive after the last task checkpoint but before the
    terminal compare-and-swap. In that case, return to the safe coordinator
    boundary, reconcile and execute the approved work, then verify/finalize
    again. If planning or its approval gate cannot complete, leave a durable
    failed/recoverable RunRecord instead of a dead worker marked running.
    """
    store = EventStore()
    run_id = get_run_id()
    rc = exit_code
    while True:
        check_run_lease(state)
        try:
            _persist_run_result(
                store, project_name, run_id, rc,
                run_state=state, phase_state=phase_state,
            )
            return rc
        except RunInboxPendingError:
            if rc != 0:
                raise

        record = store.get_run_record(project_name, run_id)
        if record is None:
            return rc
        requests = record["checkpoint"].get("chat_followup_requests", [])
        if not isinstance(requests, list) or any(
            not isinstance(item, dict) for item in requests
        ):
            raise RunInboxPendingError(
                "Run-Abschluss blockiert; Follow-up-Ledger ist ungueltig.",
            )
        unresolved = [
            item for item in requests
            if item.get("status") not in {"applied", "rejected"}
        ]
        if not unresolved:
            # Do not spin on an inbox message this coordinator cannot handle.
            # Preserve the existing fail-closed diagnostic for that condition.
            raise RunInboxPendingError(
                "Run-Abschluss blockiert; keine verarbeitbare Follow-up-"
                "Anfrage liegt im Checkpoint.",
            )

        decision = _run_coordinator_action(phase_state, state)
        audit(
            "loop_run_coordinator_decision",
            _coordinator_decision_audit_payload(run_id, decision),
            state.project_dir,
            project_name,
        )
        if decision.get("coordinator_action") != "reconcile_chat_followup":
            raise RunInboxPendingError(
                "Run-Abschluss blockiert; der Koordinator hat keine sichere "
                "Follow-up-Reconciliation ausgewaehlt.",
            )
        try:
            _persist_run_coordinator_decision(
                store, project_name, run_id, decision, run_state=state,
            )
        except RuntimeError as exc:
            audit(
                "loop_failed",
                {
                    "reason": "coordinator_decision_persist_failed",
                    "error": str(exc)[:300],
                    "finalization_inbox": True,
                },
                state.project_dir,
                project_name,
                run_id=run_id,
            )
            _persist_run_result(
                store, project_name, run_id, 1,
                run_state=state, phase_state=phase_state,
            )
            return 1

        from werkstatt.run_followups import FollowupReconciliationError

        try:
            changed = _reconcile_chat_followup_checkpoint(
                project_name, state, phase_state,
            )
        except FollowupReconciliationError as exc:
            audit(
                "loop_failed",
                {
                    "reason": "chat_followup_finalization",
                    "error": str(exc)[:500],
                    "recoverable": True,
                    "next_step": (
                        "Run nach Behebung des Planungs- oder Gate-Problems "
                        "mit dem gespeicherten Checkpoint fortsetzen."
                    ),
                },
                state.project_dir,
                project_name,
                run_id=run_id,
            )
            _persist_run_result(
                store, project_name, run_id, 1,
                run_state=state, phase_state=phase_state,
            )
            return 1

        from werkstatt.run_followups import active_chat_followup

        if active_chat_followup(phase_state) is not None:
            check_run_lease(state)
            rc = _continue_followup_with_coordinator(
                project_name, state, phase_state,
            )
            if rc != 0:
                _persist_run_result(
                    store, project_name, run_id, rc,
                    run_state=state, phase_state=phase_state,
                )
                return rc
            continue

        if not changed:
            latest = store.get_run_record(project_name, run_id)
            latest_requests = (
                latest["checkpoint"].get("chat_followup_requests", [])
                if latest is not None else []
            )
            if not isinstance(latest_requests, list) or any(
                not isinstance(item, dict) for item in latest_requests
            ):
                raise RunInboxPendingError(
                    "Run-Abschluss blockiert; Follow-up-Ledger ist ungueltig.",
                )
            still_unresolved = [
                item for item in latest_requests
                if item.get("status") not in {"applied", "rejected"}
            ]
            if still_unresolved:
                # A timed-out human gate is a resumable wait, not success. The
                # schema has no waiting status yet, so persist the run as
                # failed/recoverable and preserve the pending request.
                audit(
                    "loop_failed",
                    {
                        "reason": "chat_followup_waiting_for_gate",
                        "proposal_ids": [
                            item.get("proposal_id") for item in still_unresolved
                        ],
                        "recoverable": True,
                        "next_step": (
                            "Gate beantworten und den Run aus seinem "
                            "gespeicherten Checkpoint fortsetzen."
                        ),
                    },
                    state.project_dir,
                    project_name,
                    run_id=run_id,
                )
                _persist_run_result(
                    store, project_name, run_id, 1,
                    run_state=state, phase_state=phase_state,
                )
                return 1
            continue

        check_run_lease(state)
        rc = _continue_followup_with_coordinator(
            project_name, state, phase_state,
        )
        if rc != 0:
            _persist_run_result(
                store, project_name, run_id, rc,
                run_state=state, phase_state=phase_state,
            )
            return rc


_SETUP_CONTEXT_CHECKPOINT_VERSION = 1
_SETUP_CONTEXT_CHECKPOINT_MAX_CHARS = 80_000


def _is_checkpointable_deterministic_explorer_context(
    context: object,
) -> bool:
    if not isinstance(context, dict):
        return False
    dispatch = context.get("dispatch")
    scan = context.get("related_files_scan")
    direct_builder_context = bool(
        isinstance(dispatch, dict)
        and dispatch.get("role") == "builder"
        and dispatch.get("selected") == "direct_builder"
        and dispatch.get("reason") == "direct_builder_current_source_evidence"
        and dispatch.get("evidence_kind") == "deterministic"
        and isinstance(scan, dict)
        and scan.get("status") == "not_requested"
        and scan.get("reason") == "bounded_single_file_low_risk_route"
    )
    return bool(
        (
            direct_builder_context
            or (
                isinstance(dispatch, dict)
                and dispatch.get("role") == "explorer"
                and dispatch.get("selected") == "skip"
                and dispatch.get("evidence_kind") == "deterministic"
                and dispatch.get("reason")
                == "explizite_einzeldatei_mit_explorer_beleg"
                and context.get("findings")
                == (
                    "Explizites Einzeldatei-Ziel ist durch den deterministischen "
                    "Planner-Router bestaetigt; kein Explorer-LLM-Aufruf."
                )
            )
        )
        and (
            direct_builder_context
            or isinstance(scan, dict) and scan.get("status") == "complete"
        )
        and isinstance(scan, dict)
        and context.get("content_retrieval") in ({}, None)
        and context.get("next_reads") == []
    )


def _deterministic_setup_context_checkpoint(
    state: RunState,
) -> dict[str, Any] | None:
    """Persist only deterministic Explorer skips with current source hashes."""
    context = state.explorer_context
    if not _is_checkpointable_deterministic_explorer_context(context):
        return None
    try:
        encoded_context = json.dumps(
            context, ensure_ascii=False, sort_keys=True,
        )
    except (TypeError, ValueError):
        return None
    if len(encoded_context) > _SETUP_CONTEXT_CHECKPOINT_MAX_CHARS:
        return None
    files = context.get("key_files")
    if not isinstance(files, list) or not files or len(files) > 8:
        return None
    source_manifest: list[dict[str, str]] = []
    for item in files:
        if not isinstance(item, dict):
            return None
        relative = item.get("file")
        digest = item.get("source_sha256")
        if not isinstance(relative, str) or not isinstance(digest, str):
            return None
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts:
            return None
        source_manifest.append({"file": path.as_posix(), "sha256": digest})
    return {
        "version": _SETUP_CONTEXT_CHECKPOINT_VERSION,
        "run_id": state.run_id,
        "goal_sha256": hashlib.sha256(
            state.aufgabe.strip().encode("utf-8"),
        ).hexdigest(),
        "context_sha256": hashlib.sha256(
            encoded_context.encode("utf-8"),
        ).hexdigest(),
        "source_manifest": source_manifest,
        "context": context,
    }


def _restore_deterministic_setup_context(
    phase_state: PhaseState | None,
    state: RunState,
) -> bool:
    """Restore the narrow cached context only when every bound fact is fresh."""
    if phase_state is None or not isinstance(phase_state.data, dict):
        return False
    cached = phase_state.data.get("setup_context_checkpoint")
    if not isinstance(cached, dict):
        return False
    if (
        cached.get("version") != _SETUP_CONTEXT_CHECKPOINT_VERSION
        or cached.get("run_id") != state.run_id
        or cached.get("run_id") != phase_state.run_id
        or cached.get("goal_sha256") != hashlib.sha256(
            state.aufgabe.strip().encode("utf-8"),
        ).hexdigest()
    ):
        return False
    context = cached.get("context")
    manifest = cached.get("source_manifest")
    if not isinstance(context, dict) or not isinstance(manifest, list):
        return False
    try:
        encoded_context = json.dumps(
            context, ensure_ascii=False, sort_keys=True,
        )
    except (TypeError, ValueError):
        return False
    if (
        len(encoded_context) > _SETUP_CONTEXT_CHECKPOINT_MAX_CHARS
        or hashlib.sha256(encoded_context.encode("utf-8")).hexdigest()
        != cached.get("context_sha256")
    ):
        return False
    if not manifest or len(manifest) > 8:
        return False
    root = Path(state.project_dir).resolve()
    for item in manifest:
        if not isinstance(item, dict):
            return False
        relative = item.get("file")
        expected = item.get("sha256")
        if not isinstance(relative, str) or not isinstance(expected, str):
            return False
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts:
            return False
        try:
            source = (root / path).resolve(strict=True)
            source.relative_to(root)
            actual = hashlib.sha256(source.read_bytes()).hexdigest()
        except (OSError, RuntimeError, ValueError):
            return False
        if actual != expected:
            return False
    if not _is_checkpointable_deterministic_explorer_context(context):
        return False
    files = context.get("key_files")
    if not isinstance(files, list) or len(files) != len(manifest):
        return False
    expected_sources = [
        {"file": item.get("file"), "sha256": item.get("source_sha256")}
        for item in files if isinstance(item, dict)
    ]
    if expected_sources != manifest:
        return False
    state.explorer_context = context
    state.coordinator_setup_context_ready = True
    return True


def _hydrate_plan_candidate(state: RunState, payload: dict) -> bool:
    """Load only the persisted, hash-validated plan fields into this run."""
    tasks = payload.get("tasks")
    tests = payload.get("tests")
    criteria = payload.get("akzeptanzkriterien")
    phases = payload.get("phasen")
    prose = payload.get("architect_prosa")
    if (
        not isinstance(tasks, list) or not tasks
        or any(not isinstance(item, dict) for item in tasks)
        or not isinstance(tests, list)
        or not isinstance(criteria, list)
        or not isinstance(phases, list)
        or any(not isinstance(item, dict) for item in phases)
        or not isinstance(prose, str)
    ):
        return False
    state.tasks = tasks
    state.tests = tests
    state.akzeptanzkriterien = criteria
    state.phasen = phases
    state.architect_prosa = prose
    preflight = payload.get("preflight_findings", [])
    if not isinstance(preflight, list) or any(
        not isinstance(item, dict) for item in preflight
    ):
        return False
    state.preflight_fehler = preflight
    return True


def _run_plan_candidate_approval(
    state: RunState, phase_state: PhaseState, project_name: str,
) -> int:
    """Ask the existing human gate to approve the exact persisted proposal."""
    candidate = phase_state.load_plan_candidate(
        goal=state.aufgabe, run_id=get_run_id(),
    )
    record = phase_state.data.get("plan_candidate_checkpoint")
    digest = record.get("candidate_sha256") if isinstance(record, dict) else None
    if (
        candidate is None or not isinstance(digest, str)
        or not _hydrate_plan_candidate(state, candidate)
    ):
        audit(
            "loop_plan_candidate_stale",
            {"reason": "candidate_identity_or_digest_invalid"},
            state.project_dir, project_name,
        )
        return 1
    check_run_lease(state)
    audit(
        "loop_phase",
        {"phase": "plan_approval_gate", "status": "start",
         "candidate_sha256": digest},
        state.project_dir, project_name,
    )
    gate_rc = _human_gate_plan(state)
    if gate_rc != 0:
        audit(
            "loop_phase",
            {"phase": "plan_approval_gate", "status": "rejected",
             "candidate_sha256": digest},
            state.project_dir, project_name,
        )
        return gate_rc
    if not phase_state.approve_plan_candidate(
        goal=state.aufgabe, run_id=get_run_id(), candidate_sha256=digest,
    ):
        audit(
            "loop_plan_candidate_stale",
            {"reason": "approval_binding_failed", "candidate_sha256": digest},
            state.project_dir, project_name,
        )
        return 1
    audit(
        "loop_phase",
        {"phase": "plan_approval_gate", "status": "approved",
         "candidate_sha256": digest},
        state.project_dir, project_name,
    )
    return 0


def _run_plan_candidate_prebuild_verify(
    state: RunState, phase_state: PhaseState, project_name: str,
) -> int:
    """Verify the approved candidate before binding it as the task graph."""
    candidate = phase_state.load_plan_candidate(
        goal=state.aufgabe, run_id=get_run_id(),
    )
    if (
        candidate is None
        or not phase_state.plan_candidate_is_approved(
            goal=state.aufgabe, run_id=get_run_id(),
        )
        or not _hydrate_plan_candidate(state, candidate)
    ):
        audit(
            "loop_plan_candidate_stale",
            {"reason": "approved_candidate_invalid"},
            state.project_dir, project_name,
        )
        return 1
    candidate_checkpoint = phase_state.data.get("plan_candidate_checkpoint")
    candidate_digest = (
        candidate_checkpoint.get("candidate_sha256")
        if isinstance(candidate_checkpoint, dict) else None
    )
    if not _plan_gate(state):
        audit(
            "loop_gate_failed",
            _gate_failed_payload("plan_candidate_revalidation", []),
            state.project_dir, project_name,
        )
        return 1
    check_run_lease(state)
    verify_ok = _verify_patches(state, phase="pre_build")
    relevant: list[dict[str, Any]] = []
    if not verify_ok:
        findings = state.preflight_fehler
        if not isinstance(findings, list) or not findings or any(
            not isinstance(item, dict)
            or not isinstance(item.get("klasse"), str)
            or not item.get("klasse", "").strip()
            or not isinstance(item.get("stage_id"), str)
            or not item.get("stage_id", "").strip()
            for item in findings
        ):
            audit(
                "loop_gate_failed",
                _gate_failed_payload(
                    "pre_build",
                    ["fehlende oder unvollstaendige Preflight-Klassifikation"],
                ),
                state.project_dir,
                project_name,
            )
            return 1
        task_files = _extract_files_from_tasks(state.tasks)
        relevant = [
            item for item in findings
            if not item.get("datei")
            or any(
                str(item["datei"]) in target
                or target in str(item["datei"])
                for target in task_files
            )
        ]
        if relevant:
            audit(
                "loop_gate_failed",
                _gate_failed_payload(
                    "pre_build", [item.get("datei") for item in relevant],
                ),
                state.project_dir, project_name,
            )
            return 1
        audit(
            "loop_pre_build_uebersprungen",
            {"follow_up": len(state.preflight_fehler or []) - len(relevant),
             "task_files": task_files, "reason": "baseline_schuld"},
            state.project_dir, project_name,
        )
    phase_state.init_new(
        state.aufgabe,
        _normalize_tasks(state.tasks),
        tests=list(state.tests),
        akzeptanzkriterien=list(state.akzeptanzkriterien),
        phasen=list(state.phasen),
    )
    phase_state.run_id = get_run_id()
    phase_state.data["setup_complete"] = True
    phase_state.data["plan_complete"] = True
    setup_checkpoint = _deterministic_setup_context_checkpoint(state)
    if setup_checkpoint is not None:
        phase_state.data["setup_context_checkpoint"] = setup_checkpoint
    try:
        fingerprint = phase_state.bind_approved_plan()
    except (AttributeError, ValueError) as exc:
        audit(
            "loop_failed",
            {"reason": "approved_plan_fingerprint_failed",
             "error": str(exc)[:300]},
            state.project_dir, project_name,
        )
        return 1
    preflight_bytes = json.dumps(
        state.preflight_fehler or [],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    phase_state.data["plan_prebuild_verify_checkpoint"] = {
        "schema_version": 1,
        "run_id": get_run_id(),
        "goal_sha256": hashlib.sha256(
            state.aufgabe.encode("utf-8"),
        ).hexdigest(),
        "candidate_sha256": candidate_digest,
        "approved_plan_sha256": fingerprint,
        "status": "passed" if verify_ok else "baseline_debt_only",
        "relevant_failure_count": len(relevant),
        "preflight_findings_sha256": hashlib.sha256(preflight_bytes).hexdigest(),
    }
    phase_state.save()
    audit(
        "loop_phase",
        {"phase": "plan_prebuild_verify", "status": "approved_plan_bound",
         "approved_plan_sha256": fingerprint},
        state.project_dir, project_name,
    )
    return 0


def _run_plan_preflight_checkpoint(
    state: RunState, phase_state: PhaseState, project_name: str,
) -> int:
    """Run and persist preflight as an independently resumable action."""
    check_run_lease(state)
    from werkstatt.planner import _preflight_scan

    started = time.monotonic()
    audit("loop_preflight_start", {"checkpoint_action": True},
          state.project_dir, project_name)
    try:
        findings = _preflight_scan(state)
        if not isinstance(findings, list) or any(
            not isinstance(item, dict) for item in findings
        ):
            raise ValueError("Preflight lieferte kein strukturiertes Ergebnis")
        digest = phase_state.record_preflight_checkpoint(
            goal=state.aufgabe,
            run_id=get_run_id(),
            findings=findings,
        )
    except Exception as exc:  # noqa: BLE001 - evidence failure stops planning
        audit(
            "loop_failed",
            {"reason": "preflight_checkpoint_failed",
             "error": str(exc)[:300]},
            state.project_dir, project_name,
        )
        return 1
    phase_state.run_id = get_run_id()
    phase_state.save()
    state.preflight_fehler = findings
    state.preflight_checkpoint_ready = True
    audit(
        "loop_preflight_done",
        {"elapsed_s": round(time.monotonic() - started, 2),
         "befunde": len(findings), "checkpoint_action": True,
         "evidence_sha256": digest},
        state.project_dir, project_name,
    )
    if findings:
        audit(
            "loop_preflight_fehler",
            {"anzahl": len(findings),
             "klassen": sorted({str(item.get("klasse", "unknown"))
                                for item in findings})},
            state.project_dir, project_name,
        )
    return 0


def _run_coordinator_action(phase_state, state: RunState) -> dict:
    """Choose one resumable run action from persisted checkpoint evidence."""
    # A direct-route skip applies to exactly the upcoming planner action. Do
    # not let that transient decision leak into a later follow-up or new goal.
    state.preflight_checkpoint_skipped = False
    state.preflight_checkpoint_ready = False
    state.preflight_fehler = []
    phase_data = getattr(phase_state, "data", {})
    phase_data = phase_data if isinstance(phase_data, dict) else {}
    planner_phase_data = phase_data
    task_records = phase_data.get("tasks")
    task_count = len(task_records) if isinstance(task_records, list) else 0
    from werkstatt.criteria_replan import active_criteria_replan

    active_replan = (
        active_criteria_replan(phase_state)
        if phase_state is not None else None
    )
    from werkstatt.run_followups import (
        FollowupReconciliationError,
        active_chat_followup,
        prepare_chat_followup_roles,
        restore_chat_followup_parent,
    )
    active_followup = active_chat_followup(phase_state) if phase_state is not None else None
    if active_followup is not None and active_replan is None:
        followup_status = active_followup.get("status")
        if followup_status == "candidate_pending_approval":
            restore_chat_followup_parent(state, phase_state)
            return {
                "decision": "apply_chat_followup_candidate",
                "coordinator_action": "apply_chat_followup_candidate",
                "reason": "chat_followup_candidate_requires_plan_and_human_gates",
                "next_executor": "plan_and_human_gates",
                "decision_basis": {
                    "proposal_id": active_followup.get("proposal_id"),
                    "candidate_sha256": active_followup.get("candidate_sha256"),
                    "parent_plan_sha256": active_followup.get("parent_plan_sha256"),
                },
            }
        if followup_status == "roles_pending":
            try:
                active_followup = prepare_chat_followup_roles(state, phase_state)
            except (FollowupReconciliationError, TypeError, ValueError) as exc:
                return {
                    "decision": "stop_missing_evidence",
                    "coordinator_action": "stop_missing_evidence",
                    "reason": "chat_followup_checkpoint_invalid",
                    "decision_basis": {"error": str(exc)[:300]},
                }
            if active_followup is not None:
                planner_phase_data = {**phase_data, "tasks": []}
                from werkstatt.planner_artifacts import load_role_artifacts
                from werkstatt.planner_replay import load_response_cache
                state.planner_role_artifacts = load_role_artifacts(
                    phase_data.get("planner_role_artifacts"),
                    run_id=state.run_id, goal=state.aufgabe,
                )
                state.planning_response_cache = load_response_cache(
                    phase_data.get("planner_response_cache"),
                    run_id=state.run_id, goal=state.aufgabe,
                )
    setup_checkpoint_complete = phase_data.get("setup_complete") is True
    plan_checkpoint_complete = phase_data.get("plan_complete") is True
    plan_goal_matches = phase_data.get("aufgabe") == state.aufgabe
    checkpoint_run_id = (
        getattr(phase_state, "run_id", None)
        or phase_data.get("run_id")
    )
    active_run_id = get_run_id() or getattr(state, "run_id", None)
    if phase_state is not None and active_run_id and state.project_name:
        run_record = EventStore().get_run_record(
            state.project_name, str(active_run_id),
        )
        checkpoint = (
            run_record.get("checkpoint")
            if isinstance(run_record, dict) else None
        )
        followups = (
            checkpoint.get("chat_followup_requests")
            if isinstance(checkpoint, dict) else None
        )
        received_followups = [
            item for item in followups
            if isinstance(item, dict) and item.get("status") == "received"
        ] if isinstance(followups, list) else []
        if received_followups and active_replan is None and active_followup is None:
            item = received_followups[0]
            return {
                "decision": "reconcile_chat_followup",
                "coordinator_action": "reconcile_chat_followup",
                "reason": "accepted_chat_followup_waiting_at_checkpoint",
                "next_executor": "followup_planner_and_plan_gate",
                "decision_basis": {
                    "followup_count_waiting": len(received_followups),
                    "proposal_id": str(item.get("proposal_id") or "")[:160],
                    "message_seq": item.get("seq"),
                    "main_goal_preserved": True,
                    "current_task_graph_count": task_count,
                    "setup_checkpoint_complete": setup_checkpoint_complete,
                    "plan_checkpoint_complete": plan_checkpoint_complete,
                },
            }
    if active_replan is not None:
        replan_status = active_replan.get("status")
        if replan_status in {"candidate_pending_approval", "pending"}:
            from werkstatt.criteria_replan import (
                restore_criteria_replan_parent,
            )

            restore_criteria_replan_parent(state, phase_state)
            return {
                "decision": "approve_criteria_replan_candidate",
                "coordinator_action": "apply_criteria_replan_candidate",
                "reason": "criteria_replan_candidate_requires_plan_and_human_gates",
                "next_executor": "plan_and_human_gates",
                "decision_basis": {
                    "replan_id": active_replan["replan_id"],
                    "criteria_refs": active_replan.get("criteria_refs", [])[:20],
                    "candidate_sha256": active_replan.get("candidate_sha256"),
                },
            }
        if replan_status == "roles_pending":
            state.aufgabe = active_replan["planner_goal"]
            state.criteria_replan_id = active_replan["replan_id"]
            state.tasks = []
            state.tests = []
            state.akzeptanzkriterien = []
            state.phasen = []
            state.architect_prosa = ""
            state.explorer_context = {}
            state.explorer_findings = {}
            state.coordinator_setup_context_ready = False
            planner_phase_data = {**phase_data, "tasks": []}
            from werkstatt.planner_artifacts import load_role_artifacts
            from werkstatt.planner_replay import load_response_cache

            state.planner_role_artifacts = load_role_artifacts(
                phase_data.get("planner_role_artifacts"),
                run_id=state.run_id,
                goal=state.aufgabe,
            )
            state.planning_response_cache = load_response_cache(
                phase_data.get("planner_response_cache"),
                run_id=state.run_id,
                goal=state.aufgabe,
            )
    plan_run_matches = (
        not state.run_id or checkpoint_run_id == state.run_id
    )
    plan_project_matches = (
        not state.project_name
        or getattr(phase_state, "project_name", None) == state.project_name
    )
    plan_fingerprint_matches = (
        not state.run_id
        or (
            phase_state is not None
            and callable(getattr(phase_state, "approved_plan_is_current", None))
            and phase_state.approved_plan_is_current()
        )
    )
    # setup_complete is a legacy preparation marker. A current, approved plan
    # is sufficient to resume its own next checkpoint; requiring both markers
    # would reintroduce Setup as a mandatory runtime predecessor.
    plan_checkpoint_current = bool(
        phase_state is not None
        and plan_checkpoint_complete
        and plan_goal_matches
        and plan_run_matches
        and plan_project_matches
        and plan_fingerprint_matches
    )
    candidate_payload = None
    candidate_record = phase_data.get("plan_candidate_checkpoint")
    if phase_state is not None and state.run_id:
        candidate_payload = phase_state.load_plan_candidate(
            goal=state.aufgabe, run_id=state.run_id,
        )
    if candidate_payload is not None and isinstance(candidate_record, dict):
        candidate_digest = candidate_record.get("candidate_sha256")
        candidate_approved = phase_state.plan_candidate_is_approved(
            goal=state.aufgabe, run_id=state.run_id,
        )
        return {
            "decision": "plan_candidate_approved" if candidate_approved
                else "plan_candidate_pending_approval",
            "coordinator_action": "plan_prebuild_verify" if candidate_approved
                else "plan_approval_gate",
            "reason": "approved_candidate_requires_prebuild_verify"
                if candidate_approved else "validated_plan_requires_human_approval",
            "next_executor": "verify" if candidate_approved else "human_gate",
            "decision_basis": {
                "plan_candidate_current": True,
                "plan_candidate_approved": candidate_approved,
                "candidate_task_count": len(candidate_payload["tasks"]),
                "candidate_sha256": candidate_digest,
                "setup_checkpoint_complete": setup_checkpoint_complete,
            },
        }
    if plan_checkpoint_current and phase_state is not None:
        # A persisted plan survives process restarts; hydrate the current
        # RunState before allowing the dispatcher to skip planner/preflight.
        if not state.tasks:
            tasks = phase_state.data.get("tasks")
            state.tasks = tasks if isinstance(tasks, list) else []
        if not state.tests:
            tests = phase_state.data.get("tests")
            state.tests = tests if isinstance(tests, list) else []
        if not state.akzeptanzkriterien:
            criteria = phase_state.data.get("akzeptanzkriterien")
            state.akzeptanzkriterien = (
                criteria if isinstance(criteria, list) else []
            )
        if not state.phasen:
            phases = phase_state.data.get("phasen")
            state.phasen = phases if isinstance(phases, list) else []

    reuse_checkpoint_context = False
    preserve_failed_tasks_on_setup = False
    if (
        not state.coordinator_setup_context_ready
        and plan_checkpoint_current
        and phase_state is not None
    ):
        # A goal-matched, approved task graph carries its own scoped task
        # descriptions. Builder rereads each target file before its call;
        # final verification uses the persisted tests/criteria. Explorer is
        # needed again only if the checkpoint chooses new planning work.
        from werkstatt.checkpoint_coordinator import (
            choose_task_checkpoint_action as _checkpoint_decision_payload,
        )

        checkpoint_action = _checkpoint_decision_payload(
            phase_state, phase_state.get_next_task(), state=state,
        )
        preserve_failed_tasks_on_setup = (
            checkpoint_action.get("decision") == "replan_failed_criteria"
        )
        reuse_checkpoint_context = checkpoint_action.get("decision") in {
            "execute_planned_task",
            "run_phase_end_verify",
            "recover_verify_failure_checkpoint",
            "reject_stale_verify_failure_checkpoint",
        }
    if not state.coordinator_setup_context_ready:
        restored_context = _restore_deterministic_setup_context(
            phase_state, state,
        )
        if restored_context:
            restored_dispatch = state.explorer_context.get("dispatch")
            if (
                isinstance(restored_dispatch, dict)
                and restored_dispatch.get("selected") == "direct_builder"
                and restored_dispatch.get("reason")
                == "direct_builder_current_source_evidence"
            ):
                state.preflight_checkpoint_skipped = True
    if (
        not state.coordinator_setup_context_ready
        and not plan_checkpoint_current
        and getattr(state, "debugger_fix_contract", None) is None
    ):
        from werkstatt.roles.planner_dispatch import (
            prepare_direct_builder_context,
        )

        direct_context, direct_reason = prepare_direct_builder_context(
            state.aufgabe, state.project_dir,
        )
        if direct_context is not None:
            state.explorer_context = direct_context
            state.coordinator_setup_context_ready = True
            state.preflight_checkpoint_skipped = False
            if phase_state is not None and state.run_id:
                direct_preflight = phase_state.load_preflight_checkpoint(
                    goal=state.aufgabe, run_id=state.run_id,
                )
                if direct_preflight is not None:
                    state.preflight_fehler = direct_preflight
                    state.preflight_checkpoint_ready = True
                else:
                    # This route is admitted only for one explicit, current,
                    # small Python source and a single low-risk edit intent.
                    # Planner baseline triage is not used by this route; the
                    # exact plan gate and normal post-build Verify still run.
                    state.preflight_checkpoint_skipped = True
            else:
                state.preflight_checkpoint_skipped = True
            key_file = direct_context["key_files"][0]
            return {
                "decision": "prepare_approved_work_graph",
                "coordinator_action": "planner_direct",
                "reason": direct_reason,
                "next_executor": "builder_direct",
                "decision_basis": {
                    "setup_context_ready": True,
                    "setup_checkpoint_complete": False,
                    "setup_context_source": "direct_current_source_tool",
                    "plan_checkpoint_complete": False,
                    "preflight_checkpoint_current": state.preflight_checkpoint_ready,
                    "preflight_policy": (
                        "current_checkpoint"
                        if state.preflight_checkpoint_ready
                        else "skip_low_risk_direct_builder"
                    ),
                    "plan_goal_matches": plan_goal_matches,
                    "plan_run_matches": plan_run_matches,
                    "plan_project_matches": plan_project_matches,
                    "plan_fingerprint_matches": plan_fingerprint_matches,
                    "task_count": task_count,
                    "planner_role_decision": "builder_direct",
                    "planner_role_decision_reason": (
                        "unique_source_bound_edit_ready"
                    ),
                    "planner_role_available_evidence": [
                        "user_goal", "explicit_user_edit",
                        "unique_current_source",
                    ] + (
                        ["preflight_findings"]
                        if state.preflight_checkpoint_ready else []
                    ),
                    "planner_role_required_evidence": [
                        "explicit_user_edit", "unique_current_source",
                    ],
                    "planner_role_missing_evidence": [],
                    "planner_role_missing_inputs": [],
                    "direct_target": key_file["file"],
                    "direct_source_sha256": key_file["source_sha256"],
                },
            }
    explicit_source_context_ready = False
    if (
        not state.coordinator_setup_context_ready
        and not plan_checkpoint_current
        and getattr(state, "debugger_fix_contract", None) is None
    ):
        from werkstatt.roles.planner_dispatch import (
            prepare_explicit_source_context,
        )

        source_context, _ = (
            prepare_explicit_source_context(state.aufgabe, state.project_dir)
        )
        if source_context is not None:
            state.explorer_context = source_context
            state.coordinator_setup_context_ready = True
            explicit_source_context_ready = True
    # Missing repository context is not a mandatory Setup predecessor.
    # The role chooser below may dispatch Scout directly; Scout owns its
    # bounded Graphify/source investigation. A separate context refresh is
    # selected only when a later role checkpoint proves it is still needed.
    if not plan_checkpoint_current and phase_state is not None and state.run_id:
        # Existing current measurements are useful evidence, but a missing
        # preflight is not itself a fixed phase transition. The role decision
        # below determines whether those measurements are needed now.
        preflight_findings = phase_state.load_preflight_checkpoint(
            goal=state.aufgabe, run_id=state.run_id,
        )
        if preflight_findings is not None:
            state.preflight_fehler = preflight_findings
            state.preflight_checkpoint_ready = True
    if not plan_checkpoint_current:
        planner_role_stage = None
        if (
            phase_state is not None
            and phase_state.run_id == state.run_id
            and phase_data.get("planner_role_goal_sha256")
            == hashlib.sha256(state.aufgabe.encode("utf-8")).hexdigest()
        ):
            candidate_stage = phase_data.get("planner_role_stage")
            if candidate_stage in {"scout", "architect"}:
                planner_role_stage = candidate_stage
        from werkstatt.checkpoint_coordinator import (
            choose_planner_checkpoint_action,
        )

        return choose_planner_checkpoint_action(
            state,
            phase_data=planner_phase_data,
            planner_role_stage=planner_role_stage,
            plan_checkpoint_complete=plan_checkpoint_complete,
            plan_goal_matches=plan_goal_matches,
            plan_run_matches=plan_run_matches,
            plan_project_matches=plan_project_matches,
            plan_fingerprint_matches=plan_fingerprint_matches,
            explicit_source_context_ready=explicit_source_context_ready,
            preserve_failed_tasks_on_setup=preserve_failed_tasks_on_setup,
        )
    from werkstatt.checkpoint_coordinator import (
        choose_task_checkpoint_action as _checkpoint_decision_payload,
    )

    next_task = phase_state.get_next_task()
    stale_tasks_queued: list[str] = []
    if isinstance(next_task, dict):
        queue_stale_dependencies = getattr(
            phase_state, "queue_stale_read_dependencies", None,
        )
        if callable(queue_stale_dependencies):
            queued = queue_stale_dependencies(str(next_task.get("id", "")))
            if isinstance(queued, list):
                stale_tasks_queued = [
                    task_id for task_id in queued
                    if isinstance(task_id, str)
                ]
            if stale_tasks_queued:
                next_task = phase_state.get_next_task()
    task_progress = phase_state.progress()
    if next_task is None and task_progress.get("pending", 0) == 0:
        queue_stale = getattr(
            phase_state, "queue_stale_task_reverification", None,
        )
        if callable(queue_stale):
            queued = queue_stale()
            if isinstance(queued, list):
                stale_tasks_queued.extend(
                    task_id for task_id in queued
                    if isinstance(task_id, str)
                )
            if stale_tasks_queued:
                next_task = phase_state.get_next_task()
    decision = _checkpoint_decision_payload(
        phase_state, next_task, state=state,
    )
    if reuse_checkpoint_context:
        decision_basis = decision.get("decision_basis")
        if not isinstance(decision_basis, dict):
            decision_basis = {}
            decision["decision_basis"] = decision_basis
        decision_basis.update({
            "setup_context_ready": False,
            "setup_checkpoint_complete": setup_checkpoint_complete,
            "plan_checkpoint_complete": True,
            "plan_goal_matches": True,
            "plan_run_matches": plan_run_matches,
            "plan_project_matches": plan_project_matches,
            "plan_fingerprint_matches": plan_fingerprint_matches,
            "setup_context_source": "checkpointed_plan",
            "task_count": task_count,
        })
        decision["reason"] = (
            str(decision.get("reason") or "")
            + " Aktueller Taskgraph und Task-Kontext werden aus dem "
            "zielgleichen Plan-Checkpoint wiederverwendet."
        ).strip()
    if decision.get("decision") == "execute_planned_task":
        action = "execute_task_checkpoint"
    elif decision.get("decision") == "verify_task_checkpoint":
        action = "verify_task_checkpoint"
    elif decision.get("decision") in {
        "review_task_checkpoint", "complete_task_checkpoint",
        "recover_verify_failure_checkpoint",
        "reject_stale_verify_failure_checkpoint",
        "recover_phase_end_verify_checkpoint",
        "reject_stalled_phase_end_verify_recovery",
    }:
        action = decision["decision"]
    elif decision.get("decision") == "resolve_blocked_graph":
        action = "resolve_task_graph"
    elif decision.get("decision") == "replan_unassigned_criteria":
        action = "replan_unassigned_criteria"
    elif decision.get("decision") == "replan_failed_criteria":
        action = "replan_failed_criteria"
    elif decision.get("next_executor") == "phase_end_verify":
        from werkstatt.failure_record import _worktree_fingerprint

        worktree_fingerprint = (
            _worktree_fingerprint(Path(state.project_dir))
            if state.project_dir else None
        )
        verify_record_raw = phase_data.get("phase_end_verify_checkpoint")
        verify_record = (
            verify_record_raw if isinstance(verify_record_raw, dict) else {}
        )
        commit_sha = _git_head(Path(state.project_dir)) if state.project_dir else ""
        commit_checkpoint_current = bool(
            phase_state is not None
            and phase_state.commit_checkpoint_is_current(
                commit_sha=commit_sha,
            )
            and not _git_dirty(Path(state.project_dir))
        )
        commit_pending_post_verify_current = bool(
            phase_state is not None
            and phase_state.commit_pending_post_verify_is_current(
                commit_sha=commit_sha,
            )
            and not _git_dirty(Path(state.project_dir))
        )
        evidence_sha256 = verify_record.get("evidence_sha256")
        human_gate_record = phase_data.get("human_gate_checkpoint")
        if not isinstance(human_gate_record, dict):
            human_gate_record = {}
        evidence_worktree_fingerprint = (
            verify_record.get("worktree_sha256")
            if commit_checkpoint_current or commit_pending_post_verify_current
            else worktree_fingerprint
        )
        review_current = bool(
            phase_state is not None
            and callable(getattr(
                phase_state, "phase_end_review_is_current", None,
            ))
            and phase_state.phase_end_review_is_current(
                worktree_fingerprint=evidence_worktree_fingerprint,
            )
        )
        if review_current:
            gate_current = bool(
                phase_state is not None
                and callable(getattr(
                    phase_state, "human_gate_is_current", None,
                ))
                and phase_state.human_gate_is_current(
                    worktree_fingerprint=evidence_worktree_fingerprint,
                )
            )
            if not gate_current:
                action = "human_gate"
            else:
                verify_current = bool(
                    phase_state is not None
                    and callable(getattr(
                        phase_state, "phase_end_verify_is_current", None,
                    ))
                    and phase_state.phase_end_verify_is_current(
                        worktree_fingerprint=evidence_worktree_fingerprint,
                        evidence_sha256=evidence_sha256,
                    )
                )
                if not verify_current:
                    action = "phase_end_verify"
                elif (
                    human_gate_record.get("commit_requested") is True
                    and phase_state is not None
                    and commit_pending_post_verify_current
                    and not _git_dirty(Path(state.project_dir))
                ):
                    action = "post_commit_verify"
                elif (
                    human_gate_record.get("commit_requested") is True
                    and not commit_checkpoint_current
                    and not _hat_human_review_tasks(phase_state)
                ):
                    action = "commit_run"
                else:
                    action = "finalize_run"
        else:
            action = "phase_end_review"
            decision = {
                **decision,
                "decision": "run_phase_end_review",
                "next_executor": "reviewer",
                "reason": "phase_end_review_checkpoint_missing_or_stale",
            }
    else:
        action = "reject_checkpoint"
    return {
        **decision,
        "coordinator_action": action,
        "stale_tasks_queued": stale_tasks_queued,
    }


def _recoverable_task_error_decision(
    phase_state: PhaseState,
    state: RunState,
    *,
    progress_changed: bool,
) -> dict[str, Any] | None:
    """Re-enter the coordinator only for checkpoint-proven safe task failures.

    A task worker may return an error after recording a recoverable failure.
    The outer coordinator must not turn that into an unconditional run abort:
    it may route an independent approved task or a gated criteria replan.
    Unknown failures, stale/no-progress results, and failures without current
    uncovered criterion references remain terminal.
    """
    if not progress_changed:
        return None
    tasks = phase_state.data.get("tasks")
    if not isinstance(tasks, list):
        return None
    failed_ids: list[str] = []
    for task_record in tasks:
        if (
            not isinstance(task_record, dict)
            or task_record.get("status") != "failed"
        ):
            continue
        task_id = task_record.get("id")
        if isinstance(task_id, str):
            failed_ids.append(task_id)
    failed_ids.sort()
    if not failed_ids:
        return None
    criteria = phase_state.criteria_progress()
    from werkstatt.criteria_replan import eligible_failed_task_ids

    eligible_ids = eligible_failed_task_ids(
        phase_state, criteria.get("uncovered"),
    )
    if failed_ids != eligible_ids:
        return None
    decision = _run_coordinator_action(phase_state, state)
    if decision.get("coordinator_action") not in {
        "execute_task_checkpoint", "verify_task_checkpoint",
        "replan_failed_criteria",
    }:
        return None
    return decision


def _safe_coordinator_decision_basis(raw: Any) -> dict[str, Any] | None:
    """Keep only primitive checkpoint facts safe for Control and RunRecord."""
    if not isinstance(raw, dict):
        return None
    from werkstatt.roles.planner_dispatch import (
        PLANNER_ROLE_DECISION_REASONS,
        PLANNER_ROLE_EVIDENCE_NAMES,
        PLANNER_ROLE_NAMES,
    )

    safe: dict[str, Any] = {}
    for key in (
        "setup_context_ready", "setup_checkpoint_complete",
        "plan_checkpoint_complete", "plan_goal_matches",
        "plan_run_matches", "plan_project_matches",
        "plan_fingerprint_matches",
        "plan_candidate_current", "plan_candidate_approved",
        "preflight_checkpoint_current",
    ):
        if isinstance(raw.get(key), bool):
            safe[key] = raw[key]
    preflight_policy = raw.get("preflight_policy")
    if preflight_policy in {
        "current_checkpoint", "skip_low_risk_direct_builder",
    }:
        safe["preflight_policy"] = preflight_policy
    context_source = raw.get("setup_context_source")
    if (
        isinstance(context_source, str)
        and context_source in {
            "checkpointed_plan", "fresh_explorer",
            "direct_current_source_tool",
            "explicit_current_sources",
        }
    ):
        safe["setup_context_source"] = context_source
    task_count = raw.get("task_count")
    if (
        isinstance(task_count, int)
        and not isinstance(task_count, bool)
        and task_count >= 0
    ):
        safe["task_count"] = task_count
    candidate_count = raw.get("candidate_task_count")
    if (
        isinstance(candidate_count, int)
        and not isinstance(candidate_count, bool)
        and 0 <= candidate_count <= 10_000
    ):
        safe["candidate_task_count"] = candidate_count
    candidate_hash = raw.get("candidate_sha256")
    if (
        isinstance(candidate_hash, str)
        and len(candidate_hash) == 64
        and all(char in "0123456789abcdef" for char in candidate_hash)
    ):
        safe["candidate_sha256"] = candidate_hash
    role_stage = raw.get("planner_role_stage")
    if role_stage in {"scout", "architect"}:
        safe["planner_role_stage"] = role_stage
    role = raw.get("planner_role_decision")
    if role in PLANNER_ROLE_NAMES:
        safe["planner_role_decision"] = role
    role_reason = raw.get("planner_role_decision_reason")
    if isinstance(role_reason, str) and role_reason in PLANNER_ROLE_DECISION_REASONS:
        safe["planner_role_decision_reason"] = role_reason
    for key in (
        "planner_role_available_evidence",
        "planner_role_required_evidence", "planner_role_missing_evidence",
        "planner_role_missing_inputs",
    ):
        items = raw.get(key)
        if (
            isinstance(items, list)
            and len(items) <= 12
            and all(isinstance(item, str) and item in PLANNER_ROLE_EVIDENCE_NAMES
                    for item in items)
        ):
            safe[key] = list(dict.fromkeys(items))
    direct_target = raw.get("direct_target")
    if (
        isinstance(direct_target, str)
        and len(direct_target) <= 300
        and not Path(direct_target).is_absolute()
        and ".." not in Path(direct_target).parts
    ):
        safe["direct_target"] = direct_target
    direct_hash = raw.get("direct_source_sha256")
    if (
        isinstance(direct_hash, str)
        and len(direct_hash) == 64
        and all(char in "0123456789abcdef" for char in direct_hash)
    ):
        safe["direct_source_sha256"] = direct_hash
    return safe or None


def _coordinator_decision_audit_payload(
    run_id: str, decision: dict[str, Any],
) -> dict[str, Any]:
    """Project bounded coordinator evidence into the Control audit event."""
    payload: dict[str, Any] = {
        "run_id": run_id,
        "decision": decision.get("decision"),
        "action": decision.get("coordinator_action"),
        "reason": decision.get("reason"),
        "next_task_id": decision.get("next_task_id"),
        "next_executor": decision.get("next_executor"),
        "verification_only": decision.get("verification_only"),
        "stale_tasks_queued": decision.get("stale_tasks_queued"),
        "task_progress": decision.get("task_progress"),
        "criteria_task_coverage": decision.get("criteria_task_coverage"),
    }
    raw_choice = decision.get("coordinator_model_choice")
    if isinstance(raw_choice, dict):
        role = raw_choice.get("role")
        source = raw_choice.get("source")
        reason_code = raw_choice.get("reason_code")
        allowed = raw_choice.get("allowed_roles")
        if (
            role in {"scout", "architect"}
            and source in {"project_chat_model", "deterministic_fallback"}
            and isinstance(reason_code, str)
            and len(reason_code) <= 80
            and isinstance(allowed, list)
            and len(allowed) <= 4
            and all(item in {"scout", "architect"} for item in allowed)
        ):
            payload["coordinator_model_choice"] = {
                "role": role,
                "source": source,
                "reason_code": reason_code,
                "allowed_roles": list(dict.fromkeys(allowed)),
            }
    raw_review = decision.get("review_dispatch")
    if isinstance(raw_review, dict):
        evidence = raw_review.get("evidence")
        if isinstance(evidence, dict):
            diff_hash = evidence.get("diff_sha256")
            diff_chars = evidence.get("diff_chars")
            reasons = evidence.get("risk_reasons")
            safe_evidence: dict[str, Any] = {}
            if (
                isinstance(diff_hash, str)
                and len(diff_hash) == 64
                and all(char in "0123456789abcdef" for char in diff_hash)
            ):
                safe_evidence["diff_sha256"] = diff_hash
            if (
                isinstance(diff_chars, int)
                and not isinstance(diff_chars, bool)
                and 0 <= diff_chars <= 1_000_000
            ):
                safe_evidence["diff_chars"] = diff_chars
            if (
                isinstance(reasons, list)
                and len(reasons) <= 12
                and all(
                    isinstance(item, str)
                    and re.fullmatch(r"[a-z0-9_]{1,80}", item)
                    for item in reasons
                )
            ):
                safe_evidence["risk_reasons"] = list(dict.fromkeys(reasons))
            invoke_reviewer = raw_review.get("invoke_reviewer")
            reason = raw_review.get("reason")
            if (
                isinstance(invoke_reviewer, bool)
                and isinstance(reason, str)
                and re.fullmatch(r"[a-z0-9_]{1,80}", reason)
                and safe_evidence
            ):
                payload["review_dispatch"] = {
                    "invoke_reviewer": invoke_reviewer,
                    "reason": reason,
                    "evidence": safe_evidence,
                }
    preserve_failed = decision.get("preserve_failed_tasks_on_setup")
    if isinstance(preserve_failed, bool):
        payload["preserve_failed_tasks_on_setup"] = preserve_failed
    decision_basis = _safe_coordinator_decision_basis(
        decision.get("decision_basis"),
    )
    if decision_basis is not None:
        payload["decision_basis"] = decision_basis
    verification = decision.get("criteria_task_verification")
    if isinstance(verification, dict):
        payload["criteria_task_verification"] = verification
    recovery = decision.get("verify_recovery_evidence")
    if isinstance(recovery, dict):
        digest = recovery.get("sha256")
        error_count = recovery.get("error_count")
        current = recovery.get("current")
        if (
            isinstance(digest, str)
            and len(digest) == 64
            and all(char in "0123456789abcdef" for char in digest)
            and isinstance(error_count, int)
            and not isinstance(error_count, bool)
            and 0 <= error_count <= 8
            and isinstance(current, bool)
        ):
            payload["verify_recovery_evidence"] = {
                "current": current,
                "sha256": digest,
                "error_count": error_count,
            }
    return payload


def _persist_run_coordinator_decision(
    store: EventStore,
    project_name: str,
    run_id: str,
    decision: dict,
    *,
    run_state: RunState | None = None,
) -> None:
    """Publish the current bounded dispatch decision in the durable RunRecord."""
    for _attempt in range(5):
        if run_state is not None:
            check_run_lease(run_state)
        record = store.get_run_record(project_name, run_id)
        if record is None or record.get("status") not in {"starting", "running"}:
            raise RuntimeError("Aktiver RunCheckpoint fuer Dispatch fehlt")
        checkpoint = dict(record.get("checkpoint") or {})
        persisted_decision: dict[str, Any] = {
            "decision": str(decision.get("decision") or "")[:120],
            "action": str(decision.get("coordinator_action") or "")[:120],
            "reason": str(decision.get("reason") or "")[:500],
            "executor": str(decision.get("next_executor") or "")[:120],
            "task_id": str(decision.get("next_task_id") or "")[:120],
            "checkpoint_version": int(record["checkpoint_version"]) + 1,
        }
        raw_choice = decision.get("coordinator_model_choice")
        if isinstance(raw_choice, dict):
            role = raw_choice.get("role")
            source = raw_choice.get("source")
            reason_code = raw_choice.get("reason_code")
            allowed_roles = raw_choice.get("allowed_roles")
            if (
                role in {"scout", "architect"}
                and source in {"project_chat_model", "deterministic_fallback"}
                and isinstance(reason_code, str)
                and re.fullmatch(r"[a-z0-9_:-]{1,80}", reason_code)
                and isinstance(allowed_roles, list)
                and len(allowed_roles) <= 4
                and all(item in {"scout", "architect"} for item in allowed_roles)
            ):
                persisted_decision["coordinator_model_choice"] = {
                    "role": role,
                    "source": source,
                    "reason_code": reason_code,
                    "allowed_roles": list(dict.fromkeys(allowed_roles)),
                }
        preserve_failed = decision.get("preserve_failed_tasks_on_setup")
        if isinstance(preserve_failed, bool):
            persisted_decision["preserve_failed_tasks_on_setup"] = preserve_failed
        raw_progress = decision.get("task_progress")
        if isinstance(raw_progress, dict):
            progress = {
                key: raw_progress[key]
                for key in (
                    "total", "pending", "running", "done", "failed",
                    "blocked",
                )
                if isinstance(raw_progress.get(key), int)
                and not isinstance(raw_progress.get(key), bool)
            }
        else:
            progress = {}
        raw_coverage = decision.get("criteria_task_coverage")
        coverage: dict[str, Any] = {}
        if isinstance(raw_coverage, dict):
            for key in ("tracked", "valid"):
                if isinstance(raw_coverage.get(key), bool):
                    coverage[key] = raw_coverage[key]
            for key in ("covered", "uncovered"):
                value = raw_coverage.get(key)
                if isinstance(value, list) and all(
                    isinstance(item, str) for item in value
                ):
                    coverage[f"{key}_count"] = len(value)
                    coverage[key] = value[:20]
                    coverage[f"{key}_omitted_count"] = max(
                        0, len(value) - 20,
                    )
            error = raw_coverage.get("error")
            if isinstance(error, str):
                if error in {
                    "criteria_not_assigned",
                    "invalid_acceptance_criteria",
                    "invalid_task_record",
                }:
                    coverage["error"] = error
                elif error.startswith("invalid_criterion_refs:"):
                    coverage["error"] = "invalid_criterion_refs"
        if progress or coverage:
            persisted_decision["evidence"] = {
                "task_progress": progress,
                "criteria_task_coverage": coverage,
            }
        raw_basis = decision.get("decision_basis")
        safe_basis = _safe_coordinator_decision_basis(raw_basis)
        if safe_basis is not None:
            persisted_decision.setdefault("evidence", {})[
                "decision_basis"
            ] = safe_basis
        raw_verification = decision.get("criteria_task_verification")
        if isinstance(raw_verification, dict):
            verification: dict[str, Any] = {}
            for key in (
                "required_task_count", "current_count",
                "reverify_possible_count", "unverifiable_count",
            ):
                value = raw_verification.get(key)
                if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                    verification[key] = value
            for key in ("current", "reverify_possible", "unverifiable"):
                values = raw_verification.get(key)
                if isinstance(values, list) and all(
                    isinstance(value, str) for value in values
                ):
                    verification[key] = values[:20]
                    omitted = raw_verification.get(f"{key}_omitted_count")
                    if (
                        isinstance(omitted, int)
                        and not isinstance(omitted, bool)
                        and omitted >= 0
                    ):
                        verification[f"{key}_omitted_count"] = omitted
            if verification:
                evidence = persisted_decision.get("evidence")
                if not isinstance(evidence, dict):
                    evidence = {}
                evidence["criteria_task_verification"] = verification
                persisted_decision["evidence"] = evidence
        checkpoint["coordinator_decision"] = persisted_decision
        try:
            store.update_run_checkpoint(
                project_name,
                run_id,
                checkpoint,
                expected_version=int(record["checkpoint_version"]),
            )
            return
        except RuntimeError:
            # Inbox/Chat may update the same checkpoint concurrently. Reload
            # and merge our bounded status into the latest durable snapshot.
            continue
    raise RuntimeError("Dispatch-Entscheidung konnte nicht CAS-persistiert werden")


def _persist_run_planner_role_checkpoint(
    project_name: str,
    run_id: str,
    role_checkpoint: dict[str, Any],
    *,
    run_state: RunState,
) -> None:
    """Persist a bounded planning-role boundary for live status and recovery."""
    role = role_checkpoint.get("role")
    status = role_checkpoint.get("status")
    if role not in {"scout", "architect", "planner_split"}:
        raise ValueError("Unbekannte Planner-Rolle im Checkpoint")
    if status not in {"running", "completed", "skipped", "failed"}:
        raise ValueError("Ungueltiger Planner-Rollenstatus")
    safe = {
        "role": role,
        "status": status,
        "reason": str(role_checkpoint.get("reason") or "")[:300],
        "input_sha256": role_checkpoint.get("input_sha256"),
        "output_sha256": role_checkpoint.get("output_sha256"),
        "updated_at": time.time(),
    }
    for key in ("input_sha256", "output_sha256"):
        digest = safe[key]
        if digest is not None and (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(char not in "0123456789abcdef" for char in digest)
        ):
            raise ValueError("Ungueltiger Rollenbeleg-Hash")

    store = EventStore()
    for _attempt in range(5):
        check_run_lease(run_state)
        record = store.get_run_record(project_name, run_id)
        if record is None or record.get("status") not in {"starting", "running"}:
            raise RuntimeError("Aktiver RunCheckpoint fuer Planner-Rolle fehlt")
        checkpoint = dict(record.get("checkpoint") or {})
        history = checkpoint.get("planner_role_history")
        history = list(history) if isinstance(history, list) else []
        history.append(safe)
        checkpoint["planner_role_history"] = history[-12:]
        checkpoint["planner_role_checkpoint"] = safe
        try:
            store.update_run_checkpoint(
                project_name, run_id, checkpoint,
                expected_version=int(record["checkpoint_version"]),
            )
            audit(
                "loop_run_coordinator_decision",
                {
                    "run_id": run_id,
                    "decision": "planner_role_checkpoint",
                    "action": role,
                    "reason": safe["reason"],
                    "role_checkpoint": safe,
                },
                run_state.project_dir,
                project_name,
            )
            return
        except RuntimeError:
            continue
    raise RuntimeError("Planner-Rollencheckpoint konnte nicht CAS-persistiert werden")


def _persist_planning_response_cache(
    phase_state: PhaseState,
    entry: dict[str, Any],
    *,
    run_id: str,
    goal: str,
) -> None:
    """Persist one bounded successful planning response in its phase file."""
    if (
        phase_state.run_id != run_id
        or phase_state.data.get("aufgabe") != goal
    ):
        raise RuntimeError(
            "Planner-Antwortcache ist nicht an diesen Run gebunden",
        )
    from werkstatt.planner_replay import add_response_entry

    phase_state.data["planner_response_cache"] = add_response_entry(
        phase_state.data.get("planner_response_cache"),
        entry,
        run_id=run_id,
        goal=goal,
    )
    phase_state.save()


def _persist_planner_role_artifact(
    phase_state: PhaseState,
    artifact: dict[str, Any],
    *,
    run_id: str,
    goal: str,
) -> None:
    """Persist a bounded, exact-input-bound role output in PhaseState."""
    if phase_state.run_id != run_id:
        raise RuntimeError(
            "Planner-Rollenartefakt ist nicht an diesen Run gebunden",
        )
    from werkstatt.planner_artifacts import add_role_artifact

    phase_state.data["planner_role_artifacts"] = add_role_artifact(
        phase_state.data.get("planner_role_artifacts"),
        artifact,
        run_id=run_id,
        goal=goal,
    )
    phase_state.save()


def _persist_planner_role_stage(
    phase_state: PhaseState,
    role: str,
    *,
    run_id: str,
    goal: str,
) -> None:
    """Persist one completed role boundary for same-run coordinator resume."""
    if role not in {"scout", "architect"}:
        raise ValueError("Ungueltiger Planner-Rollenstage")
    if not run_id or not goal:
        raise ValueError("Planner-Rollenstage braucht Run-ID und Ziel")
    if phase_state.run_id not in (None, run_id):
        raise RuntimeError("Planner-Rollenstage gehoert zu einem anderen Run")
    phase_state.run_id = run_id
    phase_state.data["planner_role_stage"] = role
    phase_state.data["planner_role_goal_sha256"] = hashlib.sha256(
        goal.encode("utf-8"),
    ).hexdigest()
    phase_state.save()


def _select_loop_run_id(
    project_name: str,
    state: RunState,
    phase_state: PhaseState | None,
    store: EventStore,
) -> str:
    """Keep explicit resume IDs; rotate stale process-global IDs for new runs."""
    requested = state.run_id or (
        phase_state.run_id if phase_state is not None else None
    )
    if requested:
        if get_run_id() != requested:
            set_run_id(requested)
        return requested

    current = get_run_id()
    existing = store.get_run_record(project_name, current) if current else None
    if current and (
        existing is None or existing.get("status") in {"starting", "running"}
    ):
        return current

    import uuid

    new_run_id = f"{project_name}-{uuid.uuid4().hex}"
    set_run_id(new_run_id)
    return new_run_id


def _run_scoped_phase_state(
    project_name: str,
    project_dir: Path,
    run_id: str,
) -> PhaseState:
    """Create or resume an isolated durable checkpoint for direct API calls.

    The CLI supplies its explicitly selected project checkpoint. Callers of
    ``run_pipeline_loop`` that omit it still need durable coordinator state;
    keep those runs under a run-specific directory so they cannot overwrite a
    different run's project-level resume checkpoint.
    """
    if not isinstance(run_id, str) or not run_id or len(run_id) > 240:
        raise ValueError("Ungueltige Run-ID fuer den Phase-State")
    run_key = hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:32]
    phase_state = PhaseState(
        project_name,
        base_dir=project_dir / ".werkstatt" / "runs" / run_key,
    )
    if phase_state.exists():
        if not phase_state.load():
            raise ValueError("Vorhandener Run-Checkpoint ist ungueltig")
        if phase_state.run_id != run_id:
            raise ValueError("Run-Checkpoint gehoert zu einer anderen Run-ID")
    else:
        phase_state.run_id = run_id
    return phase_state


def run_pipeline_loop(
    project_name: str,
    aufgabe: str,
    state_ref: list[RunState],
    *,
    phasen_state: RunState | None = None,
    phase_state: PhaseState | None = None,
) -> int:
    """Run under an exclusive renewable lease, fencing stale writers."""
    state = phasen_state or (state_ref[-1] if state_ref else None)
    if state is None or not isinstance(getattr(state, "project_dir", None), Path):
        return _run_pipeline_loop_impl(
            project_name, aufgabe, state_ref,
            phasen_state=phasen_state, phase_state=phase_state,
        )
    store = EventStore()
    run_id = _select_loop_run_id(project_name, state, phase_state, store)
    state.run_id = run_id
    if phase_state is None:
        try:
            phase_state = _run_scoped_phase_state(
                project_name, state.project_dir, run_id,
            )
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            audit(
                "loop_failed",
                {
                    "reason": "run_checkpoint_initialization_failed",
                    "error": str(exc)[:300],
                },
                state.project_dir,
                project_name,
            )
            return 1
    store.create_run_record(
        project_name, run_id, aufgabe, base_commit=_git_head(state.project_dir),
    )
    import os as _lease_os
    import uuid as _lease_uuid

    worker_id = f"{_lease_os.getpid()}:{_lease_uuid.uuid4().hex}"
    try:
        with store.run_lease(
            project_name, run_id, worker_id, lease_seconds=60,
        ) as lease:
            state.run_lease_check = lease.assert_owned
            state.run_id = run_id
            lease.assert_owned()
            return _run_pipeline_loop_impl(
                project_name, aufgabe, state_ref,
                phasen_state=phasen_state, phase_state=phase_state,
            )
    except RunLeaseBusy:
        step(0, "run-lease", "Ein anderer Worker besitzt diesen Run.", ok=False)
        return 1
    except RunLeaseLost as exc:
        audit(
            "loop_failed",
            {"reason": "run_lease_lost", "error": str(exc)[:300]},
            state.project_dir,
            project_name,
        )
        step(0, "run-lease", "Run-Lease verloren; Schreibarbeit gestoppt.", ok=False)
        return 1
    finally:
        state.run_lease_check = None
    return 1


_TERMINAL_CHECKPOINT_ACTIONS = frozenset({
    "phase_end_review", "human_gate", "phase_end_verify",
    "commit_run", "post_commit_verify", "finalize_run",
})


def _checkpoint_action_key(action: object, phase_state: PhaseState | None) -> tuple[str, str] | None:
    """Fingerprint terminal action input so an unchanged stale retry stops."""
    if action not in _TERMINAL_CHECKPOINT_ACTIONS:
        return None
    checkpoint_data = phase_state.data if phase_state is not None else {}
    try:
        checkpoint_bytes = json.dumps(
            checkpoint_data,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError):
        checkpoint_bytes = repr(checkpoint_data).encode(
            "utf-8", errors="replace",
        )
    return (
        str(action), hashlib.sha256(checkpoint_bytes).hexdigest(),
    )


def _run_pipeline_loop_impl(
    project_name: str,
    aufgabe: str,
    state_ref: list[RunState],
    *,
    phasen_state: RunState | None = None,
    phase_state: PhaseState | None = None,
    continuation: bool = False,
    finish_followups: bool = True,
) -> int:
    """Execute coordinator-selected actions and persist each safe checkpoint."""

    state = phasen_state or (state_ref[-1] if state_ref else None)

    # OP-122: Run-ID fuer Event-Store und audit-Logs setzen.
    # Muss VOR dem ersten _publish (header) passieren, sonst bleibt
    # der Event-Store leer.
    if not get_run_id():
        set_run_id(f"{project_name}-{time.strftime('%Y%m%d-%H%M%S')}")

    if not continuation:
        header(f"{project_name} — {aufgabe[:50]}")

        # OP-303: Loop-Start-Marker fuer Run-Status pro OP.
        import re as _re_loop
        _op_m = _re_loop.search(r"\bOP-(\d+[a-z]?)\b", aufgabe or "")
        _op_id_start = ("OP-" + _op_m.group(1)) if _op_m else ""
        audit("loop_started", {
            "op_id": _op_id_start,
            "aufgabe_kurz": (aufgabe or "")[:200],
        }, Path("."), project_name)

    # Projekt-Pfad aus Config aufloesen, falls nicht gesetzt
    if state is not None and getattr(state, "project_dir", None) is None:
        cfg = load_project_config(project_name)
        if cfg.get("project_dir"):
            state.project_dir = Path(cfg["project_dir"])

    if state is None or getattr(state, "project_dir", None) is None:
        # M-299b: Harter Abbruch statt Fallback auf pipeline.run_pipeline.
        # Ohne diese Pruefung faellt der Loop still auf den Monolithen
        # zurueck und "Loop funktioniert" ist nicht von "Loop delegiert
        # an pipeline" unterscheidbar (HR-R9).
        #
        # Wer den Loop aufruft, muss einen state mit project_dir
        # liefern. main() prueft das vorher (project_dir aus
        # projects/<name>.yaml), Tests setzen es im _state-Helper.
        _fb_pd = getattr(state, "project_dir", None) if state else None
        if not isinstance(_fb_pd, Path):
            _fb_pd = Path(".")
        _fb_pn = getattr(state, "project_name", project_name) if state else project_name
        audit(
            "loop_fallback_failed",
            {
                "project_name": project_name,
                "aufgabe": aufgabe[:100],
                "reason": "state_none_or_no_project_dir",
            },
            _fb_pd,
            _fb_pn,
        )
        return 1


    # ADR-0032 M1: create the durable run identity before work starts.
    # Existing records are reused on resume; their original base commit stays pinned.
    run_store = EventStore()
    run_record = run_store.create_run_record(
        project_name,
        get_run_id(),
        aufgabe,
        base_commit=_git_head(state.project_dir),
    )
    from werkstatt.reflection_chat import originating_chat_session_id

    state.chat_origin_session_id = originating_chat_session_id(run_record)
    start_context = run_record.get("start_context")
    if (
        isinstance(start_context, dict)
        and start_context.get("origin") == "chat"
        and state.chat_origin_session_id is None
    ):
        audit(
            "loop_reflection_chat_skipped",
            {"reason": "invalid_origin_session_id"},
            state.project_dir,
            project_name,
        )
    # A process can die after its filesystem checkpoint was saved. On an
    # explicit, validated resume, re-open the same durable record for work.
    # Keep the checkpoint payload and CAS version intact.
    if run_record["status"] == "failed":
        run_store.update_run_checkpoint(
            project_name,
            get_run_id(),
            run_record["checkpoint"],
            expected_version=run_record["checkpoint_version"],
            status="running",
        )

    # 0. Aufgabe in State setzen (fuer Planner)
    state.aufgabe = aufgabe
    if phase_state is not None:
        from werkstatt.planner_artifacts import load_role_artifacts
        from werkstatt.planner_replay import load_response_cache

        phase_run_id = (
            phase_state.run_id or phase_state.data.get("run_id")
        )
        if phase_run_id == get_run_id():
            state.planner_role_artifacts = load_role_artifacts(
                phase_state.data.get("planner_role_artifacts"),
                run_id=get_run_id(),
                goal=aufgabe,
            )
        else:
            state.planner_role_artifacts = {}
        if (
            phase_run_id == get_run_id()
            and phase_state.data.get("aufgabe") == aufgabe
        ):
            state.planning_response_cache = load_response_cache(
                phase_state.data.get("planner_response_cache"),
                run_id=get_run_id(),
                goal=aufgabe,
            )
        else:
            state.planning_response_cache = {}

    # ADR-0032 M2: Setup, Plan, Task und Verify sind einzelne Checkpoint-
    # Aktionen. Der Persistenzmarker entscheidet nach Resume erneut, was fehlt.
    tasks_ok = 0
    tasks = state.tasks
    finalize_rc: int | None = None
    last_checkpoint_action: tuple[str, str] | None = None
    while True:
        check_run_lease(state)
        if phase_state is not None:
            from werkstatt.run_checkpoint import persist_run_checkpoint

            try:
                persist_run_checkpoint(
                    EventStore(), project_name, get_run_id(), phase_state,
                    phase_state.get_next_task(), run_state=state,
                )
            except (RuntimeError, ValueError, TypeError) as exc:
                audit(
                    "loop_failed",
                    {
                        "reason": "checkpoint_inbox_reconciliation_failed",
                        "error": str(exc)[:300],
                    },
                    state.project_dir,
                    project_name,
                )
                _persist_run_result(
                    EventStore(), project_name, get_run_id(), 1,
                    run_state=state, phase_state=phase_state,
                )
                return 1
        decision = _run_coordinator_action(phase_state, state)
        audit(
            "loop_run_coordinator_decision",
            _coordinator_decision_audit_payload(get_run_id(), decision),
            state.project_dir,
            project_name,
        )
        try:
            _persist_run_coordinator_decision(
                EventStore(), project_name, get_run_id(), decision,
                run_state=state,
            )
        except RuntimeError as exc:
            audit(
                "loop_failed",
                {
                    "reason": "coordinator_decision_persist_failed",
                    "error": str(exc)[:300],
                },
                state.project_dir,
                project_name,
            )
            _persist_run_result(
                EventStore(), project_name, get_run_id(), 1,
                run_state=state, phase_state=phase_state,
            )
            return 1
        action = decision.get("coordinator_action")
        current_checkpoint = _checkpoint_action_key(action, phase_state)
        if current_checkpoint is not None:
            if current_checkpoint == last_checkpoint_action:
                audit(
                    "loop_failed",
                    {
                        "reason": "coordinator_checkpoint_repeated_without_progress",
                        "action": action,
                        "checkpoint_sha256": current_checkpoint[1],
                        "recoverable": True,
                        "next_step": (
                            "Die Ursache des stale/rejected Checkpoints beheben "
                            "und den Run aus dem gespeicherten Stand fortsetzen."
                        ),
                    },
                    state.project_dir,
                    project_name,
                )
                if phase_state is not None:
                    phase_state.save()
                _persist_run_result(
                    EventStore(), project_name, get_run_id(), 1,
                    run_state=state, phase_state=phase_state,
                )
                return 1
            last_checkpoint_action = current_checkpoint
        else:
            last_checkpoint_action = None
        if action == "stop_missing_evidence":
            decision_basis = decision.get("decision_basis")
            missing_inputs = (
                decision_basis.get("planner_role_missing_inputs", [])
                if isinstance(decision_basis, dict) else []
            )
            audit(
                "loop_planner_required_evidence_unavailable",
                {
                    "missing_inputs": missing_inputs,
                    "reason": decision.get("reason"),
                },
                state.project_dir,
                project_name,
            )
            if phase_state is not None:
                phase_state.save()
            _persist_run_result(
                EventStore(), project_name, get_run_id(), 1,
                run_state=state, phase_state=phase_state,
            )
            return 1
        if action == "reconcile_chat_followup":
            from werkstatt.run_followups import FollowupReconciliationError

            if phase_state is None:
                audit(
                    "loop_failed",
                    {"reason": "chat_followup_without_phase_checkpoint"},
                    state.project_dir,
                    project_name,
                )
                _persist_run_result(
                    EventStore(), project_name, get_run_id(), 1,
                    run_state=state, phase_state=None,
                )
                return 1
            try:
                _reconcile_chat_followup_checkpoint(
                    project_name, state, phase_state,
                )
            except FollowupReconciliationError as exc:
                audit(
                    "loop_failed",
                    {
                        "reason": "chat_followup_reconciliation",
                        "error": str(exc)[:500],
                    },
                    state.project_dir,
                    project_name,
                )
                phase_state.save()
                _persist_run_result(
                    EventStore(), project_name, get_run_id(), 1,
                    run_state=state, phase_state=phase_state,
                )
                return 1
            continue
        if action == "apply_chat_followup_candidate":
            if phase_state is None:
                _persist_run_result(
                    EventStore(), project_name, get_run_id(), 1,
                    run_state=state, phase_state=None,
                )
                return 1
            from werkstatt.run_followups import (
                FollowupReconciliationError,
                apply_chat_followup_candidate,
            )
            try:
                applied = apply_chat_followup_candidate(
                    state, phase_state, EventStore(), project_name, get_run_id(),
                )
            except FollowupReconciliationError as exc:
                audit("loop_failed", {
                    "reason": "chat_followup_gate_pending",
                    "error": str(exc)[:400], "recoverable": True,
                }, state.project_dir, project_name)
                _persist_run_result(
                    EventStore(), project_name, get_run_id(), 1,
                    run_state=state, phase_state=phase_state,
                )
                return 1
            if not applied:
                audit("loop_failed", {
                    "reason": "chat_followup_candidate_invalid",
                    "recoverable": False,
                }, state.project_dir, project_name)
                _persist_run_result(
                    EventStore(), project_name, get_run_id(), 1,
                    run_state=state, phase_state=phase_state,
                )
                return 1
            continue
        if action == "apply_criteria_replan_candidate":
            if phase_state is None:
                _persist_run_result(
                    EventStore(), project_name, get_run_id(), 1,
                    run_state=state, phase_state=None,
                )
                return 1
            from werkstatt.criteria_replan import (
                active_criteria_replan,
                apply_criteria_replan_candidate,
            )

            replan = active_criteria_replan(phase_state)
            applied = bool(
                replan
                and apply_criteria_replan_candidate(
                    state, phase_state, str(replan.get("replan_id", "")),
                )
            )
            if not applied:
                audit(
                    "loop_failed",
                    {
                        "reason": "criteria_replan_candidate_gate_or_evidence_failed",
                        "replan_id": (
                            replan.get("replan_id") if replan else None
                        ),
                    },
                    state.project_dir,
                    project_name,
                )
                phase_state.save()
                _persist_run_result(
                    EventStore(), project_name, get_run_id(), 1,
                    run_state=state, phase_state=phase_state,
                )
                return 1
            continue
        if action == "plan_preflight":
            if phase_state is None:
                _persist_run_result(
                    EventStore(), project_name, get_run_id(), 1,
                    run_state=state, phase_state=None,
                )
                return 1
            preflight_rc = _run_plan_preflight_checkpoint(
                state, phase_state, project_name,
            )
            if preflight_rc != 0:
                _persist_run_result(
                    EventStore(), project_name, get_run_id(), preflight_rc,
                    run_state=state, phase_state=phase_state,
                )
                return preflight_rc
            continue
        if action == "refresh_project_evidence":
            check_run_lease(state)
            if decision.get("preserve_failed_tasks_on_setup") is True:
                _rc_exp, phase_state = collect_project_context(
                    state, aufgabe, project_name, phase_state,
                    preserve_failed_tasks=True,
                )
            else:
                _rc_exp, phase_state = collect_project_context(
                    state, aufgabe, project_name, phase_state,
                )
            if _rc_exp != 0 or phase_state is None:
                rc = _rc_exp or 1
                _persist_run_result(
                    EventStore(), project_name, get_run_id(), rc,
                    run_state=state, phase_state=phase_state,
                )
                return rc
            if phase_state.run_id not in (None, get_run_id()):
                audit(
                    "loop_checkpoint_run_mismatch",
                    {
                        "checkpoint_run_id": phase_state.run_id,
                        "requested_run_id": get_run_id(),
                    },
                    state.project_dir,
                    project_name,
                )
                _persist_run_result(
                    EventStore(), project_name, get_run_id(), 1,
                    run_state=state, phase_state=phase_state,
                )
                return 1
            phase_state.run_id = get_run_id()
            phase_state.data["setup_complete"] = True
            if decision.get("reason") == "planner_role_required_evidence_missing":
                refresh_goal_sha256 = hashlib.sha256(
                    state.aufgabe.encode("utf-8"),
                ).hexdigest()
                previous_goal = phase_state.data.get(
                    "planner_evidence_refresh_goal_sha256",
                )
                previous_count = phase_state.data.get(
                    "planner_evidence_refresh_count", 0,
                )
                phase_state.data["planner_evidence_refresh_goal_sha256"] = (
                    refresh_goal_sha256
                )
                phase_state.data["planner_evidence_refresh_count"] = (
                    previous_count + 1
                    if previous_goal == refresh_goal_sha256
                    and isinstance(previous_count, int)
                    and not isinstance(previous_count, bool)
                    else 1
                )
            setup_context_checkpoint = _deterministic_setup_context_checkpoint(
                state,
            )
            if setup_context_checkpoint is None:
                phase_state.data.pop("setup_context_checkpoint", None)
            else:
                phase_state.data[
                    "setup_context_checkpoint"
                ] = setup_context_checkpoint
            phase_state.save()
            state.coordinator_setup_context_ready = True
            continue
        if action in {
            "planner_scout", "planner_architect",
            "planner_split", "planner_dispatch", "planner_direct",
        }:
            if phase_state is None:
                _persist_run_result(
                    EventStore(), project_name, get_run_id(), 1,
                    run_state=state, phase_state=None,
                )
                return 1
            check_run_lease(state)
            planner_goal = state.aufgabe
            state.planner_checkpoint_callback = (
                lambda role_checkpoint: _persist_run_planner_role_checkpoint(
                    project_name, get_run_id(), role_checkpoint,
                    run_state=state,
                )
            )
            def persist_planning_response_cache(
                entry: dict[str, Any],
                _phase_state: PhaseState = phase_state,
                _run_id: str = get_run_id(),
                _goal: str = planner_goal,
            ) -> None:
                _persist_planning_response_cache(
                    _phase_state, entry, run_id=_run_id, goal=_goal,
                )

            state.planning_response_cache_callback = (
                persist_planning_response_cache
            )
            def persist_planner_role_artifact(
                artifact: dict[str, Any],
                _phase_state: PhaseState = phase_state,
                _run_id: str = get_run_id(),
                _goal: str = planner_goal,
            ) -> None:
                _persist_planner_role_artifact(
                    _phase_state, artifact, run_id=_run_id, goal=_goal,
                )

            state.planner_role_artifact_callback = (
                persist_planner_role_artifact
            )
            stop_after_role = {
                "planner_scout": "scout",
                "planner_architect": "architect",
            }.get(action)
            state.planner_stop_after_role = stop_after_role
            state.planner_action_role = {
                "planner_scout": "scout",
                "planner_architect": "architect",
                "planner_split": "planner_split",
                "planner_direct": "builder_direct",
            }.get(action)
            coordinator_choice = decision.get("coordinator_model_choice")
            if isinstance(coordinator_choice, dict):
                selected_role = coordinator_choice.get("role")
                state.planner_coordinator_role = (
                    selected_role
                    if selected_role in {"scout", "architect"}
                    else None
                )
                source_evidence = coordinator_choice.get("source_evidence")
                state.planner_coordinator_source_evidence = tuple(
                    item for item in source_evidence
                    if isinstance(item, dict)
                ) if isinstance(source_evidence, list) else ()
            state.planner_yielded_after_role = None
            state.planner_step_yielded = False
            state.planner_defer_plan_approval = True
            state.planner_plan_candidate_ready = False
            try:
                # Keep routing policy in one place: information-only role
                # checkpoints run directly, while plan/taskgraph actions use
                # the candidate-producing executor.
                _rc_plan, _done = _dispatch_planner_checkpoint_action(
                    state, action, planner_goal, project_name, phase_state,
                )
            finally:
                yielded_after_role = state.planner_yielded_after_role
                candidate_ready = state.planner_plan_candidate_ready
                state.planner_defer_plan_approval = False
                state.planner_plan_candidate_ready = False
                state.planner_checkpoint_callback = None
                state.planning_response_cache_callback = None
                state.planner_role_artifact_callback = None
                state.planner_stop_after_role = None
                state.planner_action_role = None
                state.planner_coordinator_role = None
                state.planner_coordinator_source_evidence = ()
                state.planner_yielded_after_role = None
            if candidate_ready:
                try:
                    from werkstatt.run_followups import active_chat_followup
                    followup_checkpoint = active_chat_followup(phase_state)
                    if (
                        followup_checkpoint is not None
                        and followup_checkpoint.get("status") == "roles_pending"
                        and followup_checkpoint.get("planner_goal") == planner_goal
                    ):
                        from werkstatt.run_followups import (
                            restore_chat_followup_parent,
                            store_chat_followup_candidate,
                        )

                        candidate_digest = store_chat_followup_candidate(
                            state, phase_state, run_id=get_run_id(),
                        )
                        restore_chat_followup_parent(state, phase_state)
                    elif state.criteria_replan_id:
                        from werkstatt.criteria_replan import (
                            restore_criteria_replan_parent,
                            store_criteria_replan_candidate,
                        )

                        candidate_digest = store_criteria_replan_candidate(
                            state, phase_state, run_id=get_run_id(),
                        )
                        restore_criteria_replan_parent(state, phase_state)
                    else:
                        candidate_digest = phase_state.record_plan_candidate(
                            goal=planner_goal,
                            run_id=get_run_id(),
                            tasks=state.tasks,
                            tests=list(state.tests or []),
                            criteria=list(state.akzeptanzkriterien or []),
                            phases=list(state.phasen or []),
                            architect_prose=state.architect_prosa or "",
                            preflight_findings=list(state.preflight_fehler or []),
                        )
                    phase_state.run_id = get_run_id()
                    phase_state.save()
                except (AttributeError, TypeError, ValueError) as exc:
                    audit(
                        "loop_failed",
                        {"reason": "plan_candidate_persist_failed",
                         "error": str(exc)[:300]},
                        state.project_dir, project_name,
                    )
                    _persist_run_result(
                        EventStore(), project_name, get_run_id(), 1,
                        run_state=state, phase_state=phase_state,
                    )
                    return 1
                audit(
                    "loop_phase",
                    {"phase": "plan_candidate", "status": "persisted",
                     "candidate_sha256": candidate_digest,
                     "task_count": len(state.tasks)},
                    state.project_dir, project_name,
                )
                continue
            if state.planner_step_yielded:
                completed_role = yielded_after_role or stop_after_role
                if completed_role not in {"scout", "architect"}:
                    _persist_run_result(
                        EventStore(), project_name, get_run_id(), 1,
                        run_state=state, phase_state=phase_state,
                    )
                    return 1
                try:
                    _persist_planner_role_stage(
                        phase_state,
                        completed_role,
                        run_id=get_run_id(),
                        goal=planner_goal,
                    )
                except Exception as exc:
                    audit(
                        "loop_failed",
                        {
                            "reason": "planner_role_stage_persist_failed",
                            "role": completed_role,
                            "error": str(exc)[:300],
                        },
                        state.project_dir,
                        project_name,
                    )
                    _persist_run_result(
                        EventStore(), project_name, get_run_id(), 1,
                        run_state=state, phase_state=phase_state,
                    )
                    return 1
                audit(
                    "loop_phase",
                    {
                        "phase": f"planner_{completed_role}",
                        "status": "checkpoint",
                        "role": completed_role,
                    },
                    state.project_dir,
                    project_name,
                )
                check_run_lease(state)
                continue
            if _done or _rc_plan != 0:
                check_run_lease(state)
                _persist_run_result(
                    EventStore(), project_name, get_run_id(), _rc_plan,
                    run_state=state, phase_state=phase_state,
                )
                return _rc_plan
            from werkstatt.agent import _enforce_run_budget
            if _enforce_run_budget(state):
                check_run_lease(state)
                _persist_run_result(
                    EventStore(), project_name, get_run_id(), 1,
                    run_state=state, phase_state=phase_state,
                )
                return 1
            phase_state.data["setup_complete"] = True
            phase_state.data["plan_complete"] = True
            try:
                phase_state.bind_approved_plan()
            except (AttributeError, ValueError) as exc:
                audit(
                    "loop_failed",
                    {
                        "reason": "approved_plan_fingerprint_failed",
                        "error": str(exc)[:300],
                    },
                    state.project_dir,
                    project_name,
                )
                _persist_run_result(
                    EventStore(), project_name, get_run_id(), 1,
                    run_state=state, phase_state=phase_state,
                )
                return 1
            phase_state.save()
            tasks = state.tasks
            tasks_ok = len([
                record for record in phase_state.data.get("tasks", [])
                if isinstance(record, dict) and record.get("status") == "done"
            ])
            continue
        if phase_state is None:
            _persist_run_result(
                EventStore(), project_name, get_run_id(), 1,
                run_state=state, phase_state=None,
            )
            return 1
        if action == "plan_approval_gate":
            gate_rc = _run_plan_candidate_approval(
                state, phase_state, project_name,
            )
            if gate_rc != 0:
                _persist_run_result(
                    EventStore(), project_name, get_run_id(), gate_rc,
                    run_state=state, phase_state=phase_state,
                )
                return gate_rc
            continue
        if action == "plan_prebuild_verify":
            verify_rc = _run_plan_candidate_prebuild_verify(
                state, phase_state, project_name,
            )
            if verify_rc != 0:
                _persist_run_result(
                    EventStore(), project_name, get_run_id(), verify_rc,
                    run_state=state, phase_state=phase_state,
                )
                return verify_rc
            continue
        if action == "phase_end_review":
            review_rc = _run_phase_end_review_checkpoint(
                state, phase_state, project_name,
            )
            if review_rc != 0:
                _persist_run_result(
                    EventStore(), project_name, get_run_id(), review_rc,
                    run_state=state, phase_state=phase_state,
                )
                return review_rc
            continue
        if action == "human_gate":
            gate_rc = _run_human_gate_checkpoint(
                state, phase_state, project_name,
            )
            if gate_rc == 3:
                continue
            if gate_rc != 0:
                _persist_run_result(
                    EventStore(), project_name, get_run_id(), gate_rc,
                    run_state=state, phase_state=phase_state,
                )
                return gate_rc
            continue
        if action == "recover_phase_end_verify_checkpoint":
            recovery_rc = _run_phase_end_verify_recovery_checkpoint(
                state, phase_state, project_name,
            )
            if recovery_rc == 3:
                continue
            _persist_run_result(
                EventStore(), project_name, get_run_id(), recovery_rc,
                run_state=state, phase_state=phase_state,
            )
            return recovery_rc
        if action == "reject_stalled_phase_end_verify_recovery":
            audit(
                "loop_verify_recovery_stalled",
                {
                    "reason": "same_worktree_after_coordinator_recovery",
                    "decision_summary": (
                        "Der Koordinator wiederholt keine Recovery ohne "
                        "veraenderten Arbeitsstand."
                    ),
                },
                state.project_dir,
                project_name,
            )
            _persist_run_result(
                EventStore(), project_name, get_run_id(), 1,
                run_state=state, phase_state=phase_state,
            )
            return 1
        if action == "phase_end_verify":
            verify_rc = _run_phase_end_verify_checkpoint(
                state, phase_state, project_name,
            )
            if verify_rc == 3:
                continue
            if verify_rc != 0:
                _persist_run_result(
                    EventStore(), project_name, get_run_id(), verify_rc,
                    run_state=state, phase_state=phase_state,
                )
                return verify_rc
            continue
        if action == "post_commit_verify":
            post_verify_rc = _run_post_commit_verify_checkpoint(
                state, phase_state, project_name,
            )
            if post_verify_rc == 3:
                continue
            if post_verify_rc != 0:
                _persist_run_result(
                    EventStore(), project_name, get_run_id(), post_verify_rc,
                    run_state=state, phase_state=phase_state,
                )
                return post_verify_rc
            continue
        if action == "commit_run":
            commit_rc = _run_commit_checkpoint(
                state, phase_state, project_name,
            )
            if commit_rc == 3:
                continue
            if commit_rc != 0:
                _persist_run_result(
                    EventStore(), project_name, get_run_id(), commit_rc,
                    run_state=state, phase_state=phase_state,
                )
                return commit_rc
            continue
        if action == "finalize_run":
            from werkstatt.roles.complete_run import run_completion_checkpoint

            tasks = state.tasks
            tasks_ok = len([
                record for record in phase_state.data.get("tasks", [])
                if isinstance(record, dict) and record.get("status") == "done"
            ])
            check_run_lease(state)
            finalize_rc = run_completion_checkpoint(
                state, tasks_ok, tasks, project_name, phase_state,
                phase_review_checkpointed=True,
                human_gate_checkpointed=True,
                phase_end_verify_checkpointed=True,
                commit_checkpointed=(
                    phase_state.data.get("human_gate_checkpoint", {}).get(
                        "commit_requested",
                    ) is True
                ),
            )
            if finalize_rc == 3:
                finalize_rc = None
                continue
            break
        if action not in {
            "execute_task_checkpoint",
            "verify_task_checkpoint",
            "review_task_checkpoint",
            "complete_task_checkpoint",
            "recover_verify_failure_checkpoint",
            "reject_stale_verify_failure_checkpoint",
            "resolve_task_graph",
            "replan_unassigned_criteria",
            "replan_failed_criteria",
            "human_gate",
        }:
            phase_state.save()
            _persist_run_result(
                EventStore(), project_name, get_run_id(), 1,
                run_state=state, phase_state=phase_state,
            )
            return 1

        def _task_progress_snapshot(current_phase_state) -> tuple[tuple, ...]:
            snapshot: list[tuple[Any, ...]] = []
            replan_records = current_phase_state.data.get("criteria_replans")
            if isinstance(replan_records, list):
                for record in replan_records:
                    if not isinstance(record, dict):
                        continue
                    snapshot.append((
                        "criteria_replan",
                        record.get("replan_id"),
                        record.get("status"),
                        record.get("candidate_sha256"),
                    ))
            for record in current_phase_state.data.get("tasks", []):
                if not isinstance(record, dict):
                    continue
                evidence = record.get("verify_evidence")
                evidence = evidence if isinstance(evidence, dict) else {}
                raw_hashes = evidence.get("task_file_sha256")
                hashes = raw_hashes if isinstance(raw_hashes, dict) else {}
                snapshot.append((
                    record.get("id"),
                    record.get("status"),
                    record.get("failure"),
                    record.get("verification_pending"),
                    (
                        record.get("verify_failure_checkpoint", {}).get("evidence_sha256")
                        if isinstance(record.get("verify_failure_checkpoint"), dict)
                        else None
                    ),
                    evidence.get("verified_at"),
                    tuple(sorted(
                        (str(path), str(digest))
                        for path, digest in hashes.items()
                    )),
                ))
            return tuple(snapshot)

        before = _task_progress_snapshot(phase_state)
        task_index_offset = len([
            record for record in phase_state.data.get("tasks", [])
            if isinstance(record, dict)
            and record.get("status") in {
                "done", "failed", "blocked", "vetoed", "split",
            }
        ])
        state.coordinator_dispatch_stale = False
        _rc_task, tasks_ok, tasks = run_task_checkpoint(
            state,
            phase_state,
            task_index_offset,
            coordinator_decision=decision,
        )
        check_run_lease(state)
        if state.coordinator_dispatch_stale:
            # Follow-up reconciliation changed the work graph after the
            # coordinator chose an action. Re-evaluate from the new checkpoint.
            continue
        if _rc_task != 0:
            after_failure = _task_progress_snapshot(phase_state)
            recovery_decision = _recoverable_task_error_decision(
                phase_state,
                state,
                progress_changed=before != after_failure,
            )
            if recovery_decision is not None:
                recovery_payload = _coordinator_decision_audit_payload(
                    get_run_id(), recovery_decision,
                )
                recovery_payload["failure_checkpoint"] = True
                audit(
                    "loop_run_coordinator_decision",
                    recovery_payload,
                    state.project_dir,
                    project_name,
                )
                continue
            _persist_run_result(
                EventStore(), project_name, get_run_id(), _rc_task,
                run_state=state, phase_state=phase_state,
            )
            return _rc_task
        after = _task_progress_snapshot(phase_state)
        if before == after:
            audit(
                "loop_failed",
                {
                    "reason": "coordinator_checkpoint_no_progress",
                    "action": action,
                    "next_task_id": decision.get("next_task_id"),
                },
                state.project_dir,
                project_name,
            )
            phase_state.save()
            _persist_run_result(
                EventStore(), project_name, get_run_id(), 1,
                run_state=state, phase_state=phase_state,
            )
            return 1

    # Finalize only after the current checkpoint explicitly requests it.
    check_run_lease(state)
    rc = finalize_rc if finalize_rc is not None else 1
    if finish_followups:
        return _finish_run_after_followups(
            project_name, state, phase_state, rc,
        )
    return rc


def _k13_rc(rc: int, tasks_ok: int) -> int:
    """K13: rc=0 nur wenn tasks_ok>0. Sonst ist der Lauf ein Fehlschlag."""
    if rc == 0 and tasks_ok <= 0:
        return 1
    return rc


def _git_stash_head(project_dir: Path) -> str | None:
    """Return the current stash ref, or None when the repository has no stash."""
    try:
        result = subprocess.run(
            ["git", "-C", str(project_dir), "rev-parse", "--verify", "refs/stash"],
            capture_output=True, text=True, timeout=5, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None

def _rotate_fresh_checkpoint(checkpoint: Path, backup: Path) -> Path | None:
    """Preserve the previous backup before moving the active checkpoint.

    Repeated fresh starts must not overwrite the only recovery copy. The
    active checkpoint becomes the resumable backup; older backups are kept
    under numbered archive names in the same directory.
    """
    archived: Path | None = None
    if backup.exists():
        index = 1
        while True:
            candidate = backup.with_name(f"{backup.name}.archive-{index:04d}")
            if not candidate.exists():
                archived = candidate
                break
            index += 1
        backup.replace(archived)
    try:
        checkpoint.replace(backup)
    except OSError:
        if archived is not None and archived.exists() and not backup.exists():
            archived.replace(backup)
        raise
    return archived


def _promote_resume_checkpoint(checkpoint: Path, backup: Path) -> Path | None:
    """Activate a validated backup while preserving the current checkpoint."""
    archived: Path | None = None
    if checkpoint.exists():
        index = 1
        while True:
            candidate = checkpoint.with_name(
                f"{checkpoint.name}.resume-archive-{index:04d}"
            )
            if not candidate.exists():
                archived = candidate
                break
            index += 1
        checkpoint.replace(archived)
    try:
        backup.replace(checkpoint)
    except OSError:
        if archived is not None and archived.exists() and not checkpoint.exists():
            archived.replace(checkpoint)
        raise
    return archived


def _main_inner(argv: list[str] | None = None) -> int:
    global _LIFECYCLE_PROJECT
    # M-391: .env laden (DEEPSEEK_API_KEY automatisch setzen)
    load_env()
    # Tee-Stream fuer Browser-Terminal: alle Render-Zeilen in
    # logs/loop-render-YYYY-MM-DD.log mitschreiben. Wird beim
    # Beenden geschlossen.
    _tee_handle = None
    try:
        from datetime import UTC as _TEE_UTC
        from datetime import datetime as _TEE_DT
        from pathlib import Path as _TEE_P

        from werkstatt import render as _TEE_R
        _tee_now = _TEE_DT.now(_TEE_UTC)
        _tee_p = _TEE_P("logs") / (
            "loop-render-"
            + _tee_now.date().isoformat()
            + "-" + _tee_now.strftime("%H%M%S")
            + ".log"
        )
        _tee_p.parent.mkdir(parents=True, exist_ok=True)
        _tee_handle = _tee_p.open("a", encoding="utf-8")
        _TEE_R.set_tee_stream(_tee_handle)
    except Exception:
        _tee_handle = None

    # Sicherheitsnetz: Tee bei Prozess-Ende schliessen
    import atexit as _atexit
    if _tee_handle is not None:
        _atexit.register(_tee_handle.close)
    """CLI-Einstieg: python3 -m werkstatt.loop --project <name> --aufgabe <text> [--dry-run]."""
    import argparse

    from werkstatt import render as _r

    parser = argparse.ArgumentParser(
        prog="werkstatt.loop",
        description="Werkstatt Strangler-Fig Loop (CLI-Einstieg).",
    )
    parser.add_argument("--project", required=True,
                        help="Projektname (z.B. security-ai)")
    parser.add_argument(
        "--project-dir",
        default="",
        help="Explizites Arbeitsverzeichnis, z.B. ein gepinnter GitHub-Run-Worktree.",
    )
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Bei Fehler git reset --hard auf Start-HEAD (default: aus). "
             "Ohne Flag bleiben erfolgreiche Task-Aenderungen im Tree.",
    )
    checkpoint_group = parser.add_mutually_exclusive_group()
    checkpoint_group.add_argument(
        "--resume",
        action="store_true",
        help="Mit Run-ID passenden aktiven Checkpoint bevorzugen; sonst Backup zuerst.",
    )
    checkpoint_group.add_argument(
        "--fresh",
        action="store_true",
        help="K24: .phase.yaml ignorieren, Phase neu starten.",
    )
    parser.add_argument("--aufgabe", default="",
                        help="Aufgabentext (leer = dry-run-aehnlich)")
    parser.add_argument("--headless", action="store_true",
                        help="Gates per Event-Store statt stdin (ADR-0007).")
    parser.add_argument("--run-id", default="",
                        help="Externe run_id vom Web (Pflicht bei --headless).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Nur Plan-Gate + Renderer, kein LLM, kein Patch")
    args = parser.parse_args(argv)
    _LIFECYCLE_PROJECT = args.project
    if args.headless and not args.run_id:
        parser.error("--headless erfordert --run-id")
    if args.run_id and not args.headless:
        parser.error("--run-id nur mit --headless")
    from werkstatt.gates import set_headless as _set_headless
    _set_headless(bool(args.headless))
    if args.run_id:
        set_run_id(args.run_id)

    _r.header(f"Loop: {args.project}")

    if args.dry_run:
        _r.step(0, "dry-run", "kein LLM, kein Patch")
        _r.footer(success=True, tasks_total=0, tasks_ok=0)
        return 0

    # M-298c: main() erzeugt echten RunState. Ohne das faellt der
    # Loop auf pipeline.run_pipeline zurueck (loop_fallback-Audit).
    # Merkposten: RunState-Bau ist hier inline; gemeinsame
    # Konstruktionsfunktion folgt in M-299+ (Altlasten).
    import os as _os
    import time as _time
    import uuid as _uuid
    from datetime import UTC as _UTC
    from datetime import datetime as _dt
    from pathlib import Path as _Path

    _cfg = load_project_config(args.project)
    _pd_str = _cfg.get("project_dir")
    if not _pd_str:
        _r.step(0, "config",
                f"project_dir fehlt in projects/{args.project}.yaml",
                ok=False)
        _r.footer(success=False, tasks_total=0, tasks_ok=0)
        return 1
    _pd = _Path(args.project_dir or _pd_str).expanduser().resolve()
    if not _pd.is_dir():
        _r.step(0, "config", f"project_dir ist kein Verzeichnis: {_pd}", ok=False)
        _r.footer(success=False, tasks_total=0, tasks_ok=0)
        return 1

    _api_key = _os.environ.get("DEEPSEEK_API_KEY", "")
    if not _api_key:
        _r.step(0, "config", "DEEPSEEK_API_KEY fehlt", ok=False)
        _r.footer(success=False, tasks_total=0, tasks_ok=0)
        return 1

    # docs-Inhalte laden (Planner-Kontext). Fehler tolerieren.
    _docs: dict = {}
    _full_cfg: dict = {}  # Bug A (OP-392): vor try, sonst UnboundLocalError
    try:
        from werkstatt.orchestrator import load_docs as _load_docs
        from werkstatt.orchestrator import load_project_config as _load_cfg
        _full_cfg = _load_cfg(args.project)
        if args.project_dir:
            _full_cfg["project_dir"] = str(_pd)
        _docs = _load_docs(_full_cfg.get("docs", {}), _pd)
    except SystemExit:
        # load_project_config/load_docs signalisieren Pflichtfehler per sys.exit.
        raise
    except (OSError, UnicodeError, ValueError, TypeError, AttributeError) as exc:
        _fehler = f"{type(exc).__name__}: {exc}"[:500]
        audit(
            "loop_docs_load_failed",
            {"error": _fehler},
            _pd,
            args.project,
        )
        _r.step(
            0, "docs", f"Pflichtdokumente nicht lesbar: {_fehler}", ok=False,
        )
        _r.footer(success=False, tasks_total=0, tasks_ok=0)
        return 1

    _git_author_cfg = (_full_cfg.get("git_author", {}) if _full_cfg else {}) or {}
    _state = RunState(
        git_author_name=_git_author_cfg.get("name", ""),
        git_author_email=_git_author_cfg.get("email", ""),
        block_id=args.project,
        aufgabe=args.aufgabe,
        start_ts=_dt.now(_UTC).isoformat(timespec="seconds"),
        docs=_docs,
        agents={},
        always={},
        optional={},
        file_whitelist=[],
        api_key=_api_key,
        budget=dict(_full_cfg.get("budget", {}) or {}),
        agent_docs={},
        project_dir=_pd,
        project_name=args.project,
    )
    try:
        from werkstatt.debugger_handoff import (
            DebuggerFixError,
            parse_debugger_loop_task,
            validate_debugger_fix_checkout,
        )

        debugger_fix = parse_debugger_loop_task(args.aufgabe)
        if debugger_fix is not None:
            if debugger_fix.project != args.project:
                raise DebuggerFixError(
                    "Debugger-Fix gehoert nicht zum aktiven Projekt."
                )
            valid, reason = validate_debugger_fix_checkout(
                debugger_fix, _pd, expected_project=args.project,
            )
            if not valid:
                raise DebuggerFixError(reason)
            _state.debugger_fix_contract = debugger_fix
    except (DebuggerFixError, TypeError, ValueError) as exc:
        audit(
            "loop_debugger_fix_rejected",
            {"reason": type(exc).__name__},
            _pd,
            args.project,
        )
        _r.step(0, "Debugger", "Freigegebener Diff ist nicht mehr gueltig", ok=False)
        _r.footer(success=False, tasks_total=0, tasks_ok=0)
        return 1
    _state.start_monotonic = _time.monotonic()
    state_ref: list[RunState] = [_state]

    _ps = PhaseState(args.project, base_dir=_pd / ".werkstatt")
    _bak = _ps.path.with_suffix(".yaml.fresh-bak")
    resume_requested = bool(getattr(args, "resume", False))
    fresh_requested = bool(getattr(args, "fresh", False))
    checkpoint_source: Path | None = None

    if resume_requested:
        checkpoint_source = _bak if _bak.exists() else (
            _ps.path if _ps.exists() else None
        )
        if (
            args.run_id and checkpoint_source == _bak
            and _ps.load() and _ps.run_id == args.run_id
        ):
            checkpoint_source = _ps.path
        if checkpoint_source is None:
            audit(
                "loop_resume_verworfen",
                {"reason": "checkpoint_missing"},
                _pd,
                args.project,
            )
            _r.step(0, "checkpoint", "Resume abgelehnt: Checkpoint fehlt", ok=False)
            _r.footer(success=False, tasks_total=0, tasks_ok=0)
            return 1
    elif fresh_requested and _ps.exists():
        archived_backup = _rotate_fresh_checkpoint(_ps.path, _bak)
        audit(
            "loop_fresh_reset",
            {
                "bak": str(_bak),
                "archived_backup": str(archived_backup) if archived_backup else None,
            },
            _pd,
            args.project,
        )
    elif _ps.exists():
        checkpoint_source = _ps.path

    if checkpoint_source is not None:
        active_path = _ps.path
        _ps.path = checkpoint_source
        try:
            checkpoint_valid = _ps.load()
        finally:
            _ps.path = active_path
        if not checkpoint_valid:
            audit(
                "loop_resume_verworfen",
                {
                    "reason": "checkpoint_invalid",
                    "checkpoint": str(checkpoint_source),
                },
                _pd,
                args.project,
            )
            _r.step(
                0, "checkpoint", "Resume abgelehnt: Checkpoint ist ungueltig",
                ok=False,
            )
            _r.footer(success=False, tasks_total=0, tasks_ok=0)
            return 1

        if checkpoint_source is not None and not _ps.run_id:
            audit(
                "loop_resume_verworfen",
                {
                    "reason": "checkpoint_run_id_missing",
                    "checkpoint": str(checkpoint_source),
                },
                _pd,
                args.project,
            )
            _r.step(
                0,
                "checkpoint",
                "Resume abgelehnt: Run-ID im Checkpoint fehlt",
                ok=False,
            )
            _r.footer(success=False, tasks_total=0, tasks_ok=0)
            return 1

        if args.run_id and _ps.run_id != args.run_id:
            audit(
                "loop_checkpoint_run_mismatch",
                {
                    "checkpoint_run_id": _ps.run_id,
                    "requested_run_id": args.run_id,
                    "resume_requested": resume_requested,
                },
                _pd,
                args.project,
            )
            audit(
                "loop_resume_verworfen",
                {
                    "reason": "run_id_mismatch",
                    "checkpoint_run_id": _ps.run_id,
                    "requested_run_id": args.run_id,
                },
                _pd,
                args.project,
            )
            _r.step(
                0,
                "checkpoint",
                "Checkpoint gehoert nicht zu diesem Run; Resume fail-closed gestoppt",
                ok=False,
            )
            _r.footer(success=False, tasks_total=0, tasks_ok=0)
            return 1

        if resume_requested and checkpoint_source == _bak:
            try:
                archived_active = _promote_resume_checkpoint(_ps.path, _bak)
            except OSError as exc:
                audit(
                    "loop_resume_verworfen",
                    {
                        "reason": "checkpoint_promotion_failed",
                        "error": f"{type(exc).__name__}: {exc}"[:300],
                    },
                    _pd,
                    args.project,
                )
                _r.step(
                    0, "checkpoint",
                    "Resume abgelehnt: Backup konnte nicht aktiviert werden",
                    ok=False,
                )
                _r.footer(success=False, tasks_total=0, tasks_ok=0)
                return 1
            audit(
                "loop_resume_from_bak",
                {
                    "bak": str(_bak),
                    "archived_active": str(archived_active) if archived_active else None,
                },
                _pd,
                args.project,
            )
    if args.run_id:
        _ps.run_id = args.run_id
    else:
        # Lokale Starts und Wiederaufnahmen teilen ihre ID mit dem Checkpoint.
        if not _ps.run_id:
            _ps.run_id = f"{args.project}-{_uuid.uuid4().hex}"
        set_run_id(_ps.run_id)
    _state.run_id = _ps.run_id or args.run_id

    # K14: Stop muss auch bei SIGTERM den Checkpoint persistieren und
    # einen eventuell angelegten User-Stash wiederherstellen.
    _start_head = ""
    _had_stash = False
    rc = 1
    _hat_exception = False
    try:
        _start_head = _git_head(_pd)
        if _git_dirty(_pd):
            audit("loop_dirty_tree", {"aktion": "stash"}, _pd, args.project)
            # Git-Stash ist ein kurzer, aber mutierender Schritt. Ein
            # SIGTERM wird bis zum Abschluss aufgeschoben; der Stash-Ref
            # erkennt auch einen Stash, dessen Git-Prozess gerade beendet
            # wurde, nachdem der Ref bereits aktualisiert war.
            global _STOP_SIGNAL_DEFERRED
            _STOP_SIGNAL_DEFERRED = True
            try:
                _stash_ref = _git_stash_owned(_pd)
                _stash_after = _stash_ref
                _had_stash = _stash_ref is not None
                _dirty_after_stash = _git_dirty(_pd)
                if not _had_stash or _dirty_after_stash:
                    audit(
                        "loop_stash_failed",
                        {
                            "reason": (
                                "dirty_tree_remains"
                                if _dirty_after_stash
                                else "stash_ref_missing"
                            ),
                            "stash_owned": _had_stash,
                        },
                        _pd, args.project,
                    )
                    raise RuntimeError(
                        "Lokale Aenderungen konnten nicht eindeutig diesem Run "
                        "zugeordnet gesichert werden; der Loop startet nicht."
                    )
            finally:
                _STOP_SIGNAL_DEFERRED = False
            if _STOP_SIGNAL is not None:
                raise _LoopStopRequested(_STOP_SIGNAL)
        rc = run_pipeline_loop(args.project, args.aufgabe, state_ref, phase_state=_ps)
    except BaseException:
        _hat_exception = True
        raise
    finally:
        # Cleanup ist nicht erneut durch ein doppeltes SIGTERM abbrechbar.
        _STOP_SIGNAL_DEFERRED = True
        try:
            if _ps.data:
                try:
                    _ps.save()
                except OSError:
                    pass

            # Kein Rollback bei Ausnahme oder explizitem Stop.
            _do_rollback = getattr(args, "rollback", False)
            if rc != 0 and not _hat_exception:
                if _do_rollback:
                    audit("loop_rollback",
                          {"rc": rc, "start_head": _start_head,
                           "grund": "explizit_angefordert"}, _pd, args.project)
                    _git_reset(_pd, _start_head)
                else:
                    audit("loop_rollback_skipped",
                          {"rc": rc, "start_head": _start_head,
                           "grund": "kein_rollback_flag"}, _pd, args.project)

            if _had_stash:
                _stash_restored = _git_stash_pop(_pd, _stash_after)
                if _stash_restored:
                    audit(
                        "loop_stash_pop",
                        {"stash_ref": _stash_after, "stash_retained": True},
                        _pd, args.project,
                    )
                else:
                    audit(
                        "loop_stash_restore_failed",
                        {
                            "stash_ref": _stash_after,
                            "recovery": (
                                f"git stash apply --index {_stash_after}"
                            ),
                        },
                        _pd, args.project,
                    )
        finally:
            _STOP_SIGNAL_DEFERRED = False

    # M-358: Footer mit echten Task-Zahlen (aus state).
    _tasks_total = len(getattr(_state, "tasks", []) or [])
    _tasks_ok = int(getattr(_state, "tasks_ok_counter", 0) or 0)
    # A successful resume may only finalize tasks already marked done in the
    # durable checkpoint, so this process executes zero tasks. Count those
    # persisted completions for the CLI success guard as well.
    try:
        _checkpoint_done = _ps.progress().get("done", 0) if _ps.data else 0
        if isinstance(_checkpoint_done, int) and not isinstance(
            _checkpoint_done, bool,
        ):
            _tasks_ok = max(_tasks_ok, _checkpoint_done)
    except (AttributeError, TypeError, ValueError):
        pass
    # K13: rc=0 nur, wenn tatsaechlich Tasks erledigt wurden.
    _erfolg = (rc == 0) and (_tasks_ok > 0)
    _r.footer(success=_erfolg, tasks_total=_tasks_total, tasks_ok=_tasks_ok)
    return _k13_rc(rc, _tasks_ok)


def _emit_lifecycle_end(
    erfolg: bool, project_name: str | None = None, *, stopped: bool = False,
) -> None:
    """Emit the terminal lifecycle event and close gates for this run."""
    try:
        from pathlib import Path as _P

        from werkstatt.audit import audit, get_run_id
        from werkstatt.gate_bridge import expire_for_run
    except Exception:  # noqa: BLE001
        return
    run_id = get_run_id()
    effektives_projekt = project_name or _LIFECYCLE_PROJECT
    if (
        not run_id
        or not effektives_projekt
        or not run_id.startswith(f"{effektives_projekt}-")
    ):
        return
    if stopped:
        kind = "loop_stopped"
        payload = {"erfolg": False, "abgebrochen": True, "run_id": run_id}
        try:
            audit("loop_stopped", payload, _P.cwd(), effektives_projekt)
        except Exception:  # noqa: BLE001
            pass
    elif erfolg:
        kind = "loop_ended"
        payload = {"erfolg": True, "run_id": run_id}
        try:
            audit("loop_ended", payload, _P.cwd(), effektives_projekt)
        except Exception:  # noqa: BLE001
            pass
    else:
        kind = "loop_failed"
        payload = {"erfolg": False, "run_id": run_id}
        try:
            audit("loop_failed", payload, _P.cwd(), effektives_projekt)
        except Exception:  # noqa: BLE001
            pass
    try:
        expire_for_run(run_id, grund=kind, project=effektives_projekt)
    except Exception:  # noqa: BLE001
        pass


def main(argv: list[str] | None = None) -> int:
    """CLI lifecycle wrapper with cleanup-safe SIGTERM handling."""
    global _LIFECYCLE_PROJECT, _STOP_SIGNAL, _STOP_SIGNAL_DEFERRED
    _LIFECYCLE_PROJECT = ""
    _STOP_SIGNAL = None
    _STOP_SIGNAL_DEFERRED = False
    erfolg = False
    gestoppt = False
    previous_sigterm = None
    try:
        previous_sigterm = signal.getsignal(signal.SIGTERM)
        signal.signal(signal.SIGTERM, _handle_loop_sigterm)
    except ValueError:
        # Main() may be invoked in a worker thread by an embedding host.
        previous_sigterm = None
    try:
        try:
            rc = _main_inner(argv)
            if _STOP_SIGNAL is not None:
                gestoppt = True
                return 128 + _STOP_SIGNAL
            erfolg = rc == 0
            return rc
        except _LoopStopRequested as stop:
            gestoppt = True
            return 128 + stop.signum
        except BaseException:
            erfolg = False
            raise
    finally:
        if previous_sigterm is not None:
            signal.signal(signal.SIGTERM, previous_sigterm)
        _emit_lifecycle_end(erfolg, _LIFECYCLE_PROJECT, stopped=gestoppt)
        _LIFECYCLE_PROJECT = ""

if __name__ == "__main__":
    import sys as _sys
    _sys.exit(main())
