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
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from werkstatt.state import RunState

# Konstanten (aus pipeline.py:131, 132, 3969, 3976).
AUDIT_DIR_NAME = "audit-logs"
AUDIT_FILE_NAME = "agent-pipeline.jsonl"
_AUDIT_RAW_MAX_LEN = 32768
_AUDIT_RAW_REDACTION_LIMIT = 1_000_000

# Modul-State: aktueller Run-Identifier (aus pipeline.py:3923).
_AKTUELLE_RUN_ID: str = ""

# Katalog (aus pipeline.py:1131-1300).
# Wird nach dem Copy aus pipeline.py eingefuegt. Platzhalter
# fuer den ersten Commit: leer, die Extraktion des Katalogs
# erfolgt in einem separaten Schritt.
_AUDIT_KINDS_BEKANNT: frozenset[str] = frozenset({'auftrag_bereits_erfuellt', 'builder_action_korrigiert', 'builder_aider_context_verworfen', 'builder_aider_patch_normalisiert', 'builder_architect_datei_fehlt', 'builder_architect_datei_nicht_beschrieben', 'builder_architect_json_fehler', 'builder_architect_keine_dateien', 'builder_architect_keine_patches', 'builder_architect_llm_fehler', 'builder_architect_patches', 'builder_file_context', 'builder_import_context', 'builder_kein_key', 'builder_keine_aktuelle_task', 'builder_keine_patches_gold', 'builder_keine_tasks', 'builder_keine_wirksamen_patches', 'builder_nichts_zu_tun', 'builder_patch_import_fehler', 'builder_patch_invalid', 'builder_patch_no_effect', 'builder_patches_erstellt', 'builder_read_only', 'builder_zieldatei_create_neu', 'builder_zieldatei_inkorrekt', 'builder_zieldatei_nicht_gefunden', 'command_executed', 'command_rejected', 'explorer_json_fehler', 'explorer_kein_key', 'explorer_llm_fehler', 'explorer_messung', 'explorer_messung_findings', 'explorer_result', 'llm_call', 'llm_timeout_gesamt', 'llm_timeout_read', 'loop_builder_aufgerufen', 'loop_builder_failed', 'loop_dirty_tree', 'loop_erfolg', 'loop_explorer_ergaenzt', 'loop_explorer_leer', 'loop_explorer_ok', 'loop_fallback_failed', 'loop_fresh_reset', 'loop_gate_failed', 'loop_hook_blocked', 'loop_human_gate_approved', 'loop_human_gate_auto', 'loop_human_gate_commit_abort', 'loop_human_gate_commit_fehler', 'loop_human_gate_commit_skip', 'loop_human_gate_committed', 'loop_human_gate_eof', 'loop_human_gate_rejected', 'loop_human_gate_test', 'loop_patch_applied', 'loop_patch_created', 'loop_patch_fallback_used', 'loop_patch_file_exists', 'loop_patch_file_missing', 'loop_patch_no_effect', 'loop_patch_not_applied', 'loop_patch_old_string_not_found', 'loop_patch_updated', 'loop_phase', 'loop_phase_reflection_approved', 'loop_phase_reflection_builder_failed', 'loop_phase_reflection_erschoepft', 'loop_phase_reflection_fallback_alle_task_files', 'loop_phase_reflection_kein_patch', 'loop_phase_reflection_keine_bugs', 'loop_phase_reflection_keine_dateien', 'loop_phase_reflection_patch_applied', 'loop_phase_reflection_runde', 'loop_phase_reflection_verify_failed', 'loop_plan_gate_approved', 'loop_plan_gate_auto', 'loop_plan_gate_eof', 'loop_plan_gate_leer', 'loop_plan_gate_rejected', 'loop_plan_gate_test', 'loop_plan_missing', 'loop_plan_reflection', 'loop_planner_failed', 'loop_pre_build_uebersprungen', 'loop_preflight_fehler', 'loop_reflection_builder_failed', 'loop_reflection_gescheitert', 'loop_reflection_kein_key', 'loop_reflection_kein_patch', 'loop_reflection_patch_applied', 'loop_reflection_patch_nicht_angewendet', 'loop_reflection_runde', 'loop_reflection_stagnation_abort', 'loop_reflection_stagnation_runde', 'loop_resume', 'loop_resume_failed_tasks', 'loop_reviewer_approved_after_reflection', 'loop_reviewer_divergenz', 'loop_reviewer_high_bug_fail_closed', 'loop_reviewer_reflection_gescheitert', 'loop_reviewer_reject_fail_closed', 'loop_reviewer_reject_ignoriert', 'loop_reviewer_rejected', 'loop_reviewer_rejected_after_reflection', 'loop_rollback', 'loop_split_bereits_erledigt', 'loop_split_fehler', 'loop_split_max_tiefe', 'loop_split_skip_klein', 'loop_stash_pop', 'loop_task_failed', 'loop_task_ok', 'loop_task_read_only', 'loop_task_retry_nach_split', 'loop_task_split', 'loop_task_start', 'loop_verify_failed', 'loop_verify_no_tests_stage', 'loop_verify_ok', 'loop_verify_stage_skipped', 'mess_protokoll_limit_erreicht', 'planner_action_korrigiert', 'planner_architect_llm_fehler', 'planner_architect_ok', 'planner_architect_prosa_zu_kurz', 'planner_kein_key', 'planner_plan_erstellt', 'planner_scout_api_widerspruch', 'planner_scout_json_fehler', 'planner_scout_llm_fehler', 'planner_scout_ok', 'planner_split', 'planner_split_json_fehler', 'planner_split_llm_fehler', 'planner_split_merged', 'planner_split_vor_merge', 'planner_task_files_korrigiert', 'planner_task_files_mehrdeutig', 'planner_task_zu_gross', 'progress_write_failed', 'quelle_invalid', 'reviewer_bug', 'reviewer_diff_fehler', 'reviewer_json_fehler', 'reviewer_kein_diff_aber_patches', 'reviewer_kein_diff_kein_patch', 'reviewer_kein_key', 'reviewer_llm_fehler', 'reviewer_phase_approved', 'reviewer_phase_call_failed', 'reviewer_phase_diff_fehler', 'reviewer_phase_json_fehler', 'reviewer_phase_kein_diff', 'reviewer_phase_kein_key', 'reviewer_phase_keine_task_files', 'reviewer_phase_rejected', 'reviewer_result'})


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


def audit(kind: str, payload: dict[str, Any], project_dir: Path,
          project_name: str) -> None:
    """Schreibt einen Audit-Eintrag (aus pipeline.py:3978-4009).

    Auflage 2043: project_name wird explizit uebergeben.
    Auflage 2110: Audit schreibt in die Werkstatt, nicht
    ins Ziel-Projekt. project_dir wird nicht mehr fuer die
    Lokation genutzt, bleibt aber Parameter.
    """
    # GOLD 2026-10-30: Warnung bei unbekanntem Kind.
    # Kein Abbruch: Audit darf nie einen Lauf killen.
    # Signal fuer Katalog-Drift.
    import sys as _sys
    if kind not in _AUDIT_KINDS_BEKANNT:
        print(
            f"[WARN] audit(): unbekannter kind={kind!r}. "
            f"Bitte in _AUDIT_KINDS_BEKANNT eintragen.",
            file=_sys.stderr,
        )

    audit_dir = _werkstatt_home() / AUDIT_DIR_NAME
    audit_dir.mkdir(parents=True, exist_ok=True)
    tag = datetime.now(UTC).strftime("%Y-%m-%d")
    datei = audit_dir / f"agent-pipeline-{tag}.jsonl"
    entry = {
        "audit_id": f"PIPE-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{int(time.time()*1000)%100000}",
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
            fh.write(json.dumps(entry, ensure_ascii=True) + "\n")
    except OSError as exc:
        print(f"[WARN] Audit-Schreibfehler: {exc}")
