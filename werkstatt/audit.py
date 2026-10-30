"""Werkstatt-Audit-Modul (Neubau Phase 2, 2026-10-19).

Aus pipeline.py extrahiert (Gate 18, 18f: Modul-Grenze).
Enthaelt nur:
- audit(kind, payload, project_dir, project_name) — Kernfunktion.
- _AUDIT_KINDS_BEKANNT — Katalog der erlaubten Kinds.
- Hilfskonstanten (AUDIT_DIR_NAME, AUDIT_FILE_NAME,
  _AUDIT_RAW_MAX_LEN, _AUDIT_RAW_REDACTION_LIMIT).
- Modul-State _AKTUELLE_RUN_ID (Setter/Getter).
- Pfad-Helfer _werkstatt_home, _plan_audit_pfad.
- _ap_audit_haeufigkeit (Anti-Pattern-Haeufigkeit).

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
_AUDIT_KINDS_BEKANNT: frozenset[str] = frozenset({'aggregator_failed', 'anker_einrueckung_korrigiert', 'anti_patterns_injiziert', 'auftrag_bereits_erfuellt', 'auto_repair_ruff', 'basis_gate_rot', 'basis_gate_test_result', 'builder_anker_fehler', 'builder_call_failed', 'builder_command_deadlock', 'builder_command_executed', 'builder_commit_paket_failed', 'builder_commit_paket_failed_retry', 'builder_deadlock_anker_nicht_gemessen', 'builder_deadlock_leer', 'builder_deadlock_rueckfrage', 'builder_frage_reviewer', 'builder_prompt_gebaut', 'builder_recovery_nach_apply', 'builder_runden_ungueltig', 'builder_reply_erhalten', 'builder_wirkungsloser_patch', 'code_patches_apply', 'code_patches_leer', 'code_patches_new_file', 'command_block_bereinigt', 'command_block_in_plan', 'command_executed', 'command_rejected', 'commit_applied', 'commit_message_diskrepanz', 'commit_paket_gebaut', 'commit_paket_leer', 'commit_review', 'commit_review_diff_fehler', 'commit_review_diff_name_only', 'commit_review_new_file_skip', 'commit_review_ohne_messung', 'commit_scope_violation', 'git_add_intent', 'git_add_intent_failed', 'judge_call_failed', 'judge_uebersprungen_doku', 'llm_call', 'llm_timeout_gesamt', 'llm_timeout_read', 'loop_cap_erreicht', 'memory_yaml_korrupt', 'mess_dir_fehler', 'mess_nach_nahe_budget', 'mess_protokoll_limit_erreicht', 'patch_ambig', 'patch_anker_fehlt', 'patch_bereits_angewendet', 'patch_datei_geaendert_seit_messung', 'patch_ohne_messung', 'patch_ersatz_doppelte_zeilen', 'patch_konflikt_new_file', 'phase_abgebrochen', 'phase_abgeschlossen_keine_neuanlage', 'phase_basis_gate_failed', 'phase_budget_ende', 'phase_commit_dateien_deterministisch', 'phase_commit_paket_gesammelt', 'phase_commit_paket_leer', 'phase_finish', 'phase_finish_warnung', 'phase_gesamt_review', 'phase_gesamt_review_no_go', 'phase_judge_uebersprungen_doku', 'phase_neuanlage_mit_flag', 'phase_plan_editiert', 'phase_plan_erstellt', 'phase_plan_korrektur_failed', 'phase_plan_korrektur_start', 'phase_plan_parse_failed', 'phase_plan_unbeantwortet', 'phase_plan_verworfen', 'phase_resume_erkannt', 'phase_resume_force', 'phase_rollback', 'phase_start_head_gesetzt', 'phase_suite_rot_recovery', 'phase_unterblock_ende', 'phase_unterblock_start', 'phasen_basis_gate_untracked', 'pipeline_abgebrochen', 'pipeline_approved', 'pipeline_ende', 'pipeline_erfolg_ohne_commit', 'pipeline_escalated', 'pipeline_rejected', 'pipeline_start', 'planner_abgebrochen', 'planner_basis_gate_failed', 'planner_bestaetigt', 'planner_blockiert_aktive_phase', 'planner_blockiert_phase_abgeschlossen', 'planner_call_failed', 'planner_command_max_runden', 'planner_command_ohne_neue_messung', 'planner_new_file_auf_existierend', 'planner_pfad_ausserhalb_projekt', 'planner_phase_yaml_kaputt', 'planner_phase_zu_gross', 'planner_plan_praefix_format_verwendet', 'planner_plan_unvollstaendig', 'planner_resume_befund_ohne_trigger', 'planner_resume_cap_erreicht', 'planner_resume_coverage', 'planner_resume_failed', 'planner_resume_mehrfach_split_verboten', 'planner_resume_merge', 'planner_resume_messung', 'planner_resume_misch_zustand', 'planner_resume_order_verletzt', 'planner_resume_rename_verboten', 'planner_resume_solver_befund_kaputt', 'planner_resume_solver_nicht_gerufen', 'planner_resume_solver_ohne_befund', 'planner_resume_split_cap_erreicht', 'planner_resume_split_depth', 'planner_resume_split_done_verboten', 'planner_resume_split_ok', 'planner_resume_start', 'planner_rolle_fehlt', 'planner_start', 'planner_uebersprungen', 'planner_ungueltig', 'planner_verworfen', 'planner_vorschlag', 'quelle_invalid', 'recovery_basis_gate', 'recovery_basis_gate_nach_apply', 'recovery_budget', 'recovery_builder_command_deadlock', 'recovery_eskalation', 'recovery_no_go', 'explore_subagent', 'verify_code_befund', 'judge_frage_antwort', 'judge_round', 'judge_command', 'reviewer_call_failed', 'review_r15_verstoss', 'review_unklar_eskalation', 'review_unklar_widerspruch', 'reviewer_run_solver', 'reviewer_run_solver_phase2_ignoriert', 'rollback_fail_closed', 'run_phase_ende', 'run_phase_start', 'skill_geladen', 'solver_befund', 'solver_befund_verworfen', 'solver_budget_exhausted', 'solver_failed', 'solver_max_runden_erreicht', 'solver_run_duplicate', 'solver_trigger', 'solver_trigger_a', 'solver_trigger_b', 'solver_trigger_c'})


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


def _ap_audit_haeufigkeit() -> dict[str, int]:
    """Zaehlt bekannte audit_kinds in den Werkstatt-Audit-Logs.

    Wird nur fuer Sortierung genutzt (VV1: die drei mit den
    meisten Treffern). Fehlende Logs = alle Zaehler 0.
    """
    haeufig: dict[str, int] = {k: 0 for k in _AUDIT_KINDS_BEKANNT}
    logdir = Path('/opt/werkstatt/audit-logs')
    if not logdir.exists():
        return haeufig
    for jf in sorted(logdir.glob('agent-pipeline-*.jsonl')):
        try:
            for line in jf.read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                k = d.get('kind')
                if k in haeufig:
                    haeufig[k] += 1
        except OSError:
            continue
    return haeufig
