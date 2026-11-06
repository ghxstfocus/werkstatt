"""Phase: _phase_finalize (OP-139 Phase 2b)."""
from __future__ import annotations

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
    _phase_end_reflection,
    _verify_patches,
    _with_spinner,
    audit,
)
from .review import _phase_review_gate


def _phase_finalize(
    state: RunState,
    tasks_ok: int,
    tasks: list,
    project_name: str,
    phase_state,
) -> int:
    """Phase 4+5 (Fix AZ Stufe 8-D, 2026-10-31): Phase-End-Review +
    Human-Gate + Phase-End-Verify + PROGRESS + Summary.

    Rueckgabe: rc (0 = Erfolg, 1 = Abbruch).
    """
    pd = state.project_dir
    pn = state.project_name

    # 4. (M-476) Phase-End Verify NACH human_gate.

    # FIX AS 2026-10-31: Partielle Bilanz auditieren, wenn Loop
    # mit 0 < tasks_ok < total zum Human-Gate geht (Fix AR).
    _total_tasks_as = len(getattr(state, "tasks", None) or [])
    if 0 < tasks_ok < _total_tasks_as:
        audit("loop_task_partial_ok",
              {"done": tasks_ok, "total": _total_tasks_as,
               "failed": _total_tasks_as - tasks_ok}, pd, pn)

    # K23c: Phase-End-Review VOR Human-Gate.
    group_start("Phase 4: Phase-End-Review")
    audit("loop_phase", {"phase": "phase_end_review", "status": "start"}, pd, pn)
    # GOLD 2026-10-30: Wenn state.patches leer ist (alle Tasks waren
    # auftrag_bereits_erfuellt) und kein Task fehlgeschlagen ist,
    # ueberspringen wir den Phase-Review. Der Reviewer braucht einen
    # Diff — bei leerem patches gibt es keinen, und der Reviewer
    # wuerde mit 'reviewer_phase_kein_diff' fail-closed abbrechen.
    # Live-Beleg 2026-10-30 21:28:25: alle 5 Tasks done, aber
    # reviewer_phase_kein_diff -> Loop-Rollback.
    # GOLD 2026-10-30: _alle_done aus PhaseState, nicht aus
    # state.tasks (dort fehlt das status-Feld).
    # Live-Beleg 2026-10-30 22:37: PhaseState t1=done, aber
    # state.tasks[0] hatte kein status -> _alle_done=False ->
    # reviewer_phase_kein_diff -> Loop-Rollback.
    _tasks = getattr(state, "tasks", None) or []
    _alle_done = bool(_tasks)
    if _alle_done and phase_state is not None:
        # Pruefe PhaseState pro Task.
        for _t in _tasks:
            if not isinstance(_t, dict):
                _alle_done = False
                break
            _tid = _t.get("id")
            if not _tid:
                _alle_done = False
                break
            _pt = phase_state.get_task(_tid)
            _pt_status = (_pt or {}).get("status")
            # OP-060b: human_review zaehlt als bearbeitet.
            if _pt_status not in ("done", "human_review"):
                _alle_done = False
                break
    # GOLD 2026-10-30: Nicht nur state.patches pruefen (die koennen
    # gefuellt sein, ohne dass etwas angewendet wurde). Sondern
    # applied_count: hat der Loop tatsaechlich Dateien geaendert?
    _applied = int(state.applied_count or 0)
    _patches_leer = _applied == 0
    if _alle_done and _patches_leer:
        # OP-062e: Nullfall-Flag fuer Human-Gate.
        state.phase_review_uebersprungen = "keine Aenderungen"
        audit("loop_phase",
              {"phase": "phase_end_review",
               "status": "skipped",
               "reason": "keine_patches_alle_done"}, pd, pn)
    else:
        from werkstatt.reviewer import run_phase_end_review as _phase_review
        _pe_ok = _with_spinner("Phase-Review", lambda: _phase_review(state))
        # K40: Historie pushen.
        _pe_bugs = getattr(state, "reviewer_bugs", None) or []
        if _pe_bugs:
            _hist = getattr(state, "reviewer_bugs_history", None)
            if _hist is None:
                state.reviewer_bugs_history = []
                _hist = state.reviewer_bugs_history
            _hist.append(list(_pe_bugs))
            if len(_hist) > 5:
                state.reviewer_bugs_history = _hist[-5:]
        if not _pe_ok:
            audit("loop_phase", {"phase": "phase_end_review", "status": "rejected"}, pd, pn)
            group_end()
            # K23d: Phase-End-Reflection pro Datei.
            if not _phase_end_reflection(state):
                audit("loop_gate_failed",
                      _gate_failed_payload("phase_end_review", []),
                      pd, pn)
                # OP-168: Human-Gate vor Loop-Abbruch.
                # Loop-Test-4: 3 Runden ohne Gate -> LOOP FEHLGESCHLAGEN
                # mit 8 Files dirty. User bekam keine Wahl.
                _gate_rc_168 = _phase_review_gate(state)
                if _gate_rc_168 != 0:
                    return 1
                audit("loop_phase",
                      {"phase": "phase_end_review",
                       "status": "approved_after_gate"}, pd, pn)
        audit("loop_phase", {"phase": "phase_end_review", "status": "approved"}, pd, pn)
        group_end()

    # 5. Human-Gate (eigenes, fail-closed)
    group_start("Phase 5: Human-Gate")
    audit("loop_phase", {"phase": "human_gate", "status": "start"}, pd, pn)
    rc = _human_gate(state)
    group_end()

    # OP-060b: human_review-Tasks offen + Mensch approved -> rc=2.
    if rc == 0 and _hat_human_review_tasks(phase_state):
        audit("loop_human_review_offen",
              {"phase": "human_gate"}, pd, pn)
        rc = 2

    # M-476: Phase-End Verify (Vollsuite) nach human_gate.
    if rc == 0 and not _verify_patches(state, phase="phase_end"):
        audit("loop_gate_failed",
              _gate_failed_payload("phase_end", []), pd, pn)
        rc = 1

    if rc == 0:
        audit("loop_erfolg", {"project_name": project_name}, pd, pn)

    # M-307b: Phasen-Ende in PROGRESS.md
    # FIX AH 2026-10-31: Wurde bei jedem Loop-Ende geschrieben,
    # ausser wenn _committe_zielprojekt den Eintrag VOR git add
    # geschrieben hat (Flag progress_written_at_commit).
    if not getattr(state, "progress_written_at_commit", False):
        from werkstatt import progress as _progress
        _progress.append(
            pd,
            name=f"Phase abgeschlossen: {project_name}",
            status="phase_ende",
            info=f"rc={rc} tasks_ok={tasks_ok}/{len(tasks)}",
        )

    # M-456: Zusammenfassung.
    try:
        _total = len(tasks)
        _failed = _total - tasks_ok
        summary(tasks_ok, _failed, 0)
    except Exception:
        pass

    return rc
