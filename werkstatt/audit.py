"""Werkstatt-Audit-Modul (Neubau Phase 2, 2026-10-19).

Aus pipeline.py extrahiert (Gate 18, 18f: Modul-Grenze).
Enthaelt nur:
- audit(kind, payload, project_dir, project_name) — Kernfunktion.
- _AUDIT_KINDS_BEKANNT — Katalog der erlaubten Kinds.
- Hilfskonstanten (AUDIT_DIR_NAME, AUDIT_FILE_NAME,
  _AUDIT_RAW_MAX_LEN, _AUDIT_RAW_REDACTION_LIMIT).
- Modul-State _AKTUELLE_RUN_ID (Setter/Getter).
- Pfad-Helfer _werkstatt_home, _plan_audit_pfad.

Keine Auslagerung weiterer Funktionen (18f: kein W52a-
Fehler, kein "und noch schnell X mitnehmen").
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from werkstatt.state import RunState

# Konstanten (aus pipeline.py:131, 132, 3969, 3976).
import uuid

AUDIT_DIR_NAME = "audit-logs"
AUDIT_FILE_NAME = "agent-pipeline.jsonl"

# OP-321: Stream-Kinds (hochfrequent, gitignore). Alle anderen Kinds -> Semantic.
_STREAM_KINDS: frozenset[str] = frozenset({
    "log_line", "progress", "spinner",
    "heartbeat", "task_started", "task_done",
})


# OP-323: Flush-Hook. Nach 100 Events wird Projector.tail() gerufen.
_EVENT_COUNTER = 0
_FLUSH_INTERVAL = 100
_FLUSH_LOCK = __import__("threading").Lock()


def _maybe_flush() -> None:
    """Zaehlt Events, ruft bei 100 Projector.tail(). Fehler still."""
    global _EVENT_COUNTER
    with _FLUSH_LOCK:
        _EVENT_COUNTER += 1
        if _EVENT_COUNTER < _FLUSH_INTERVAL:
            return
        _EVENT_COUNTER = 0
    try:
        from werkstatt.projection import Projector
        Projector().tail()
    except Exception:
        pass


def _event_id(run_id: str, audit_id: str) -> str:
    """Deterministische event_id fuer Replay-Idempotenz (OP-321)."""
    import hashlib
    return hashlib.sha256(f"{run_id}|{audit_id}".encode()).hexdigest()[:16]
_AUDIT_RAW_MAX_LEN = 32768
_AUDIT_RAW_REDACTION_LIMIT = 1_000_000

# Modul-State: aktueller Run-Identifier (aus pipeline.py:3923).
_AKTUELLE_RUN_ID: str = ""

# Katalog (aus pipeline.py:1131-1300).
# Wird nach dem Copy aus pipeline.py eingefuegt. Platzhalter
# fuer den ersten Commit: leer, die Extraktion des Katalogs
# erfolgt in einem separaten Schritt.
_AUDIT_KINDS_BEKANNT: frozenset[str] = frozenset({'state_contract_violation', 'builder_patch_datum_korrigiert', 'adr_mini_created', 'adr_mini_fehler', 'adr_mini_skip', 'auftrag_bereits_erfuellt', 'builder_action_korrigiert', 'builder_aider_context_verworfen', 'builder_aider_patch_normalisiert', 'builder_architect_datei_fehlt', 'builder_architect_datei_nicht_beschrieben', 'builder_architect_json_fehler', 'builder_architect_keine_dateien', 'builder_architect_keine_patches', 'builder_architect_llm_fehler', 'builder_architect_patches', 'builder_file_context', 'builder_import_context', 'builder_kein_key', 'builder_keine_aktuelle_task', 'builder_keine_patches_gold', 'builder_keine_tasks', 'builder_keine_wirksamen_patches', 'builder_patch_bereits_erfuellt', 'builder_nichts_zu_tun', 'builder_patch_duplicate_anchor', 'builder_patch_import_fehler', 'builder_patch_invalid', 'builder_patch_no_effect', 'builder_patch_zu_breit', 'builder_patches_erstellt', 'builder_read_only', 'builder_zieldatei_create_neu', 'builder_zieldatei_inkorrekt', 'builder_zieldatei_nicht_gefunden', 'command_executed', 'command_rejected', 'committer_architecture_drift', 'doku_nachzug_skip', 'doku_nachzug_delete_zone_retry', 'explorer_json_fehler', 'explorer_kein_key', 'explorer_llm_fehler', 'explorer_messung', 'explorer_messung_findings', 'explorer_result', 'llm_call', 'llm_call_start', 'llm_call_end', 'llm_timeout_gesamt', 'llm_timeout_read', 'llm_usage', 'loop_builder_aufgerufen', 'loop_builder_failed', 'loop_dirty_tree', 'loop_erfolg', 'loop_failed', 'loop_ended', 'loop_explorer_ergaenzt', 'loop_explorer_grep_fallback', 'loop_explorer_leer', 'loop_explorer_ok', 'loop_explorer_suchbegriffe', 'loop_fallback_failed', 'loop_docs_load_failed', 'loop_started', 'loop_stopped', 'loop_fresh_reset', 'gate_expired', 'gate_open', 'gate_answered', 'loop_gate_failed', 'loop_gate_timeout', 'loop_hook_blocked', 'loop_human_gate_approved', 'loop_human_review_offen',  'loop_human_gate_commit_abort', 'loop_human_gate_commit_fehler', 'loop_human_gate_commit_skip', 'loop_human_gate_committed', 'loop_human_gate_eof', 'loop_human_gate_task_files_missing', 'loop_human_gate_rejected', 'loop_human_gate_test', 'loop_patch_applied', 'loop_patch_created', 'loop_patch_delete_blocked', 'loop_patch_delete_failed', 'loop_patch_delete_skip_missing', 'loop_patch_deleted', 'loop_patch_fallback_used', 'loop_patch_file_exists', 'loop_patch_file_missing', 'loop_patch_no_effect', 'loop_patch_not_applied', 'loop_patch_not_applied_vor_schreiben', 'loop_patch_old_string_not_found', 'loop_patch_updated', 'loop_patch_write_failed', 'loop_verify_recovery_started', 'loop_verify_recovery_error', 'loop_verify_recovered', 'loop_verify_recovery_stalled', 'loop_phase', 'loop_phase_reflection_approved', 'loop_phase_reflection_builder_failed', 'loop_phase_reflection_erschoepft', 'loop_phase_reflection_fallback_alle_task_files', 'loop_phase_reflection_kein_patch', 'loop_phase_reflection_keine_bugs', 'loop_phase_reflection_keine_dateien', 'loop_phase_reflection_patch_applied', 'loop_phase_reflection_runde', 'loop_phase_reflection_verify_failed', 'loop_plan_shown', 'loop_plan_gate_approved', 'loop_plan_gate_eof', 'loop_plan_gate_leer', 'loop_plan_gate_rejected', 'loop_plan_reject_ohne_grund', 'web_login_ok', 'verify_stage_ohne_hart_flag',
    'web_login_fail', 'web_logout', 'loop_plan_reject_grund', 'loop_plan_reject_fail_closed', 'loop_plan_reject_reflection_start', 'loop_plan_reject_reflection_done', 'loop_plan_gate_test', 'loop_plan_missing', 'loop_plan_reflection', 'loop_plan_reflection_abgebrochen', 'loop_planner_failed', 'loop_pre_build_uebersprungen', 'loop_preflight_fehler', 'loop_preflight_done', 'loop_preflight_start', 'loop_preflight_rechte', 'loop_reflection_builder_failed', 'loop_reflection_det_diagnose', 'loop_reflection_gescheitert', 'loop_reflection_kein_key', 'loop_reflection_kein_patch', 'loop_reflection_patch_applied', 'loop_reflection_patch_nicht_angewendet', 'loop_reflection_patch_unwirksam', 'loop_reflection_no_apply', 'reflection_no_progress', 'loop_reflection_runde', 'loop_reflection_stagnation_abort', 'loop_reflection_spec_widerspruch', 'loop_reflection_spec_widerspruch_erschoepft', 'loop_reflection_stagnation_runde', 'loop_resume', 'loop_resume_verworfen', 'loop_resume_failed_tasks', 'loop_reviewer_approved_after_reflection', 'loop_reviewer_deterministic_fail', 'loop_reviewer_divergenz', 'loop_reviewer_high_bug_fail_closed', 'loop_reviewer_reflection_gescheitert', 'loop_reviewer_reject_fail_closed', 'loop_reviewer_reject_ignoriert', 'loop_reviewer_rejected', 'loop_reviewer_rejected_after_reflection', 'loop_rollback', 'loop_resume_from_bak', 'loop_rollback_skipped', 'loop_skills_geladen', 'loop_stash_pop', 'loop_stash_failed', 'loop_stash_restore_failed', 'loop_task_ende_skip', 'loop_task_veto_respected', 'loop_task_antipattern_veto', 'loop_task_spec_widerspruch_veto', 'loop_task_blocked', 'loop_task_failed', 'loop_task_failed_dependency', 'loop_task_ok', 'loop_task_partial_ok', 'loop_task_read_only', 'loop_task_start', 'loop_verify_failed', 'loop_verify_failed_human_review', 'loop_verify_no_tests_stage', 'loop_verify_ok', 'loop_task_soft_fail', 'loop_verify_soft_fail', 'loop_verify_stage_skipped', 'mess_protokoll_limit_erreicht', 'planner_action_korrigiert', 'planner_architect_llm_fehler', 'planner_deps_abgeleitet', 'planner_deps_zyklus', 'planner_architect_ok', 'planner_doku_post_check_leer', 'planner_doku_post_check_reduziert', 'planner_architect_prosa_zu_kurz', 'planner_atomarer_plan', 'planner_atomarer_plan_verworfen', 'planner_kein_key', 'planner_plan_erstellt', 'planner_precheck_bereits_erfuellt', 'planner_scout_api_widerspruch', 'planner_scout_grep', 'planner_scout_json_fehler', 'planner_scout_llm_fehler', 'planner_scout_ok', 'planner_scout_skipped', 'planner_scout_required', 'planner_split', 'planner_split_json_fehler', 'planner_split_llm_fehler', 'planner_split_merged', 'planner_split_vor_merge', 'planner_task_files_korrigiert', 'planner_task_files_mehrdeutig', 'planner_task_zu_gross', 'progress_write_failed', 'quelle_invalid', 'reviewer_bug', 'reviewer_bug_widerlegt', 'reviewer_dead_code_parse_fehler', 'reviewer_diff_fehler', 'reviewer_json_fehler', 'reviewer_kein_diff_aber_patches', 'reviewer_kein_diff_kein_patch', 'reviewer_kein_diff_update_task', 'reviewer_kein_key', 'reviewer_llm_fehler', 'reviewer_phase_approved', 'reviewer_phase_call_failed', 'reviewer_phase_diff_fehler', 'reviewer_phase_json_fehler', 'reviewer_phase_kein_diff', 'reviewer_phase_kein_key', 'reviewer_phase_keine_task_files', 'reviewer_phase_rejected', 'reviewer_result', 'reviewer_unvollstaendig', 'reviewer_pre_gate_hart', 'reviewer_stagnation_false_positive', 'loop_reviewer_reject_false_positive', 'loop_reviewer_reject_human_review', 'loop_human_gate_reflection_erschoepft_approved', 'loop_human_gate_reflection_erschoepft_rejected', 'loop_plan_gate_ungueltig', 'explorer_findings_fehler', 'planner_update_ziel_fehlt', 'planner_create_ziel_existiert', 'planner_zieldatei_check_ohne_project_dir', 'planner_task_files_cap', 'web_op_selected', 'web_loop_paused', 'web_loop_resumed', 'web_loop_stopped', 'chat_job_queued', 'chat_job_started', 'chat_job_chunk', 'chat_job_tool_call', 'chat_job_tool_result', 'chat_job_succeeded', 'chat_job_failed', 'chat_job_cancelled', 'chat_job_cancel_requested', 'chat_job_branch_cleanup_failed', 'loop_budget_exhausted'})


def _werkstatt_home() -> Path:
    """Liefert das Werkstatt-Heimverzeichnis (aus pipeline.py:3906)."""
    return Path(__file__).resolve().parent.parent


def set_run_id(run_id: str) -> None:
    """Setzt die aktuelle Run-ID (aus pipeline.py:10130 ff.)."""
    global _AKTUELLE_RUN_ID
    _AKTUELLE_RUN_ID = run_id


def get_run_id() -> str:
    """Liefert die aktuelle Run-ID (leer, wenn nicht gesetzt)."""
    return _AKTUELLE_RUN_ID


def _plan_audit_pfad(state: "RunState") -> Path:  # noqa: UP037
    """W26: Pfad zu audit-logs/<run_id>/01-plan.md.

    Aus pipeline.py:6382-6387. Signatur bleibt
    (state: RunState) -> Path (18c Signatur-Freeze).
    """
    if state.run_id:
        return (_werkstatt_home() / "audit-logs"
                / state.run_id / "01-plan.md")
    return _werkstatt_home() / "audit-logs" / "01-plan.md"


def audit(
    kind: str,
    payload: dict[str, Any],
    project_dir: Path,
    project_name: str,
    *,
    run_id: str | None = None,
    audit_id: str | None = None,
    event_id: str | None = None,
) -> bool:
    """Write a durable JSONL audit event with optional explicit IDs."""
    import sys as _sys

    if kind not in _AUDIT_KINDS_BEKANNT:
        print(
            f"[WARN] audit(): unbekannter kind={kind!r}. "
            "Bitte in _AUDIT_KINDS_BEKANNT eintragen.",
            file=_sys.stderr,
        )

    effektive_run_id = _AKTUELLE_RUN_ID if run_id is None else run_id
    try:
        audit_dir = _werkstatt_home() / AUDIT_DIR_NAME
        audit_dir.mkdir(parents=True, exist_ok=True)
        jetzt = datetime.now(UTC)
        datei = audit_dir / f"agent-pipeline-{jetzt:%Y-%m-%d}.jsonl"
        aid = audit_id or f"PIPE-{jetzt:%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}"
        entry = {
            "audit_id": aid,
            "event_id": event_id or _event_id(effektive_run_id, aid),
            "timestamp": jetzt.isoformat(timespec="milliseconds"),
            "agent": "agent_pipeline",
            **payload,
            "project": project_name,
            "kind": kind,
        }
        if effektive_run_id:
            entry["run_id"] = effektive_run_id
        with datei.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=True, default=str) + "\n")
    except (OSError, TypeError, ValueError) as exc:
        print(f"[WARN] Audit-Schreibfehler: {exc}", file=_sys.stderr)
        return False
    _maybe_flush()
    return True


def stream(kind: str, payload: dict[str, Any], project_dir: Path,
           project_name: str) -> None:
    """Stream-Event nach audit-logs/stream-YYYY-MM-DD.jsonl (OP-321).

    Fail-closed: unbekannter Kind geht via audit() nach Semantic.
    """
    if kind not in _STREAM_KINDS:
        audit(kind, payload, project_dir, project_name)
        return
    audit_dir = _werkstatt_home() / AUDIT_DIR_NAME
    audit_dir.mkdir(parents=True, exist_ok=True)
    tag = datetime.now(UTC).strftime("%Y-%m-%d")
    datei = audit_dir / f"stream-{tag}.jsonl"
    _aid = f"STREAM-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    entry = {
        "audit_id": _aid,
        "event_id": _event_id(_AKTUELLE_RUN_ID, _aid),
        "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds"),
        "agent": "agent_pipeline",
        "project": project_name,
        "kind": kind,
        **payload,
    }
    if _AKTUELLE_RUN_ID:
        entry["run_id"] = _AKTUELLE_RUN_ID
    try:
        with datei.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=True, default=str) + "\n")
    except (OSError, TypeError, ValueError) as exc:
        print(f"[WARN] Stream-Schreibfehler: {exc}")
    _maybe_flush()

def audit_safe(
    kind: str,
    payload: dict | None = None,
    project_dir: Path | str | None = None,
    project_name: str = "?",
) -> None:
    """Wie audit(), crasht aber NIE.

    Fuer Audit-Calls in kritischen Pfaden: Contract-Violations,
    Gate-Fehler, Verify-Stage-Audit. Wenn der Audit-Logger selbst
    kaputt ist (z.B. PermissionError auf audit-logs/), darf der
    Loop nicht deswegen abbrechen — aber der Fehler soll sichtbar
    sein, nicht still verschluckt.
    """
    import sys as _sys
    try:
        audit(
            kind,
            payload or {},
            Path(project_dir) if project_dir else Path("."),
            project_name,
        )
    except Exception as _e:  # bewusst: logger darf nicht crashen
        print(
            f"[WARN] audit({kind!r}) fehlgeschlagen: "
            f"{type(_e).__name__}: {_e}",
            file=_sys.stderr,
        )

