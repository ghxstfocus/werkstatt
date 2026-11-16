"""Phase: _phase_plan_and_preflight (OP-139 Phase 2b)."""
from __future__ import annotations

import hashlib
import json
import time

from werkstatt.render import (
    group_end,
    group_start,
    step,
)
from werkstatt.state import RunState

from ._common import (
    _extract_files_from_tasks,
    _gate_failed_payload,
    _human_gate,
    _human_gate_plan,
    _normalize_tasks,
    _plan_gate,
    _task_ende,
    _validate_contract_safe,
    _verify_patches,
    audit,
    replan_task_graph_from_architect,
    run_planner,
)

_STRUCTURAL_PLAN_REJECTIONS = frozenset({
    "DOKU_TASK", "TASK_FILE", "MIGRATIONS_KOLLISION",
    "ACTION", "PHASE_ID", "DATEINAME_AEHNLICH", "PAYLOAD",
})
_REPLANNABLE_PLAN_REJECTIONS = frozenset({
    "TASK_GRAPH", "ACCEPTANCE_COVERAGE",
})


def _plan_reflection_feedback(
    state: RunState,
    seen_signatures: set[str],
) -> tuple[dict | None, str, str | None]:
    """Choose whether new, budgeted plan feedback warrants another attempt."""
    info = getattr(state, "last_planner_info", None)
    if not isinstance(info, dict) or not info:
        return None, "planner_feedback_missing", None
    rule = info.get("regel")
    if isinstance(rule, str) and rule in _STRUCTURAL_PLAN_REJECTIONS:
        return info, "structural_failure", None
    if rule not in _REPLANNABLE_PLAN_REJECTIONS:
        return info, "unsupported_gate_feedback", None

    signature_input = {
        key: str(info.get(key) or "")[:2_000]
        for key in ("regel", "fakt", "erklaerung", "details")
    }
    if not any(signature_input.values()):
        return info, "planner_feedback_missing", None
    signature = hashlib.sha256(json.dumps(
        signature_input, ensure_ascii=False, sort_keys=True,
    ).encode("utf-8")).hexdigest()
    if signature in seen_signatures:
        return info, "same_rejection_repeated", signature

    budget = state.budget if isinstance(state.budget, dict) else {}
    has_run_budget = any(
        isinstance(budget.get(key), int)
        and not isinstance(budget.get(key), bool)
        and budget[key] > 0
        for key in ("max_llm_calls", "max_minutes")
    )
    if not has_run_budget:
        return info, "run_budget_missing", signature
    from werkstatt.agent import _enforce_run_budget

    if _enforce_run_budget(state):
        return info, "run_budget_exhausted", signature
    seen_signatures.add(signature)
    return info, "new_budgeted_rejection", signature


def _check_plan_gate_current(state: RunState) -> bool:
    """Prevent stale gate feedback from authorizing a recovery attempt."""
    state.last_planner_info = {}
    return _plan_gate(state)


def _phase_plan_and_preflight(
    state: RunState,
    aufgabe: str,
    project_name: str,
    phase_state,
) -> tuple[int, bool]:
    """Phase 2 (Fix AZ Stufe 8-B, 2026-10-31): Plan-Gate + Planner +
    Plan-Human-Gate + PhaseState-Init + Pre-Build-Verify.

    Rueckgabe: (rc, done).
    done=True  -> bereits_erfuellt-Pfad (rc zurueckgeben).
    done=False -> weiter mit Task-Loop (rc=0) oder Abbruch (rc=1).
    """
    pd = state.project_dir
    pn = state.project_name

    group_start("Phase 2: Planner")
    _t_plan = time.monotonic()
    debugger_fix = getattr(state, "debugger_fix_contract", None)
    if debugger_fix is not None:
        checkpoint_has_plan = bool(
            phase_state is not None
            and phase_state.exists()
            and phase_state.data.get("aufgabe") == aufgabe
            and phase_state.data.get("plan_complete") is True
            and isinstance(phase_state.data.get("tasks"), list)
        )
        if checkpoint_has_plan:
            state.tasks = list(phase_state.data["tasks"])
            state.tests = list(phase_state.data.get("tests") or [])
            state.akzeptanzkriterien = list(
                phase_state.data.get("akzeptanzkriterien") or []
            )
        else:
            from werkstatt.debugger_handoff import DebuggerFix

            if not isinstance(debugger_fix, DebuggerFix):
                audit(
                    "loop_debugger_fix_rejected",
                    {"reason": "invalid_in_memory_contract"},
                    pd,
                    pn,
                )
                return 1, False
            criterion = (
                "Der exakt freigegebene Patch "
                f"{debugger_fix.patch_hash} wird innerhalb seines Dateiscopes "
                "angewendet und von den normalen Verify-/Review-Gates geprueft."
            )
            state.tasks = [{
                "id": "debugger-fix",
                "name": f"Debugger-Fix: {debugger_fix.signatur}",
                "description": (
                    f"Ursache: {debugger_fix.ursache_tag}; "
                    f"freigegebener Diff SHA-256: {debugger_fix.patch_hash}; "
                    f"Dateien: {', '.join(debugger_fix.betroffene_dateien)}"
                ),
                "action": "update",
                "task_files": list(debugger_fix.betroffene_dateien),
                "criterion_refs": ["AC1"],
            }]
            state.tests = []
            state.akzeptanzkriterien = [criterion]
            state.phasen = []
            state.architect_prosa = (
                "Deterministischer Debugger-Handoff. Der Nutzer hat den "
                f"Diff {debugger_fix.patch_hash} fuer das Projekt "
                f"{debugger_fix.project} an Basis {debugger_fix.base_head} "
                "freigegeben. Der Loop wendet denselben Diff im genehmigten "
                "Dateiscope an und durchlaeuft die normalen Verify-, Review- "
                "und Ergebnis-Gates."
            )
            audit(
                "loop_debugger_fix_plan",
                {
                    "patch_hash": debugger_fix.patch_hash,
                    "source_kind": debugger_fix.source_kind,
                    "source_run_id": (
                        debugger_fix.run_id
                        if debugger_fix.source_kind == "loop_run" else None
                    ),
                    "source_chat_session_sha256": (
                        hashlib.sha256(
                            debugger_fix.source_chat_session_id.encode("utf-8"),
                        ).hexdigest()
                        if debugger_fix.source_chat_session_id else None
                    ),
                    "files": list(debugger_fix.betroffene_dateien),
                },
                pd,
                pn,
            )
    plan_ok = _check_plan_gate_current(state)
    # OP-381k (2026-11-09): Resume-Aufgabe-Check.
    # Ohne diesen Check wuerde ein Loop-Start mit anderer Aufgabe die
    # Tasks aus der alten PhaseState laden, Architect/Planner ueberspringen.
    _resume_erlaubt = True
    if phase_state.exists():
        try:
            _ps_aufgabe = str(phase_state.data.get("aufgabe") or "").strip()
            if _ps_aufgabe and _ps_aufgabe != (aufgabe or "").strip():
                _resume_erlaubt = False
                audit("loop_resume_verworfen",
                      {"phase_aufgabe": _ps_aufgabe[:100],
                       "aktuelle_aufgabe": (aufgabe or "")[:100],
                       "grund": "aufgabe_geaendert"}, pd, pn)
        except (AttributeError, TypeError):
            pass

    if not plan_ok and phase_state.exists() and _resume_erlaubt:
        data = phase_state.data
        if data.get("tasks"):
            state.tasks = data["tasks"]
        if data.get("tests"):
            state.tests = data["tests"]
        if data.get("akzeptanzkriterien"):
            state.akzeptanzkriterien = data["akzeptanzkriterien"]
        # FIX (Fix AW-Resume) 2026-10-31: PhaseState mit tasks ist
        # Source of Truth. _plan_gate prueft Planner-Output-Vollstaendigkeit
        # (tasks+tests+akz). Bei Resume aus einer abgebrochenen PhaseState
        # sind tests/akz oft nicht mehr befuellt -> _plan_gate False ->
        # run_planner baut einen NEUEN Plan und ignoriert den PhaseState.
        # Live-Beleg 2026-10-31 11:18: RERUN gegen security-ai, 7 Tasks
        # in PhaseState, Resume geladen, aber Planner lieferte
        # 1-Task-Plan auf 17 SQL-Migrationen. Fix: wenn PhaseState Tasks
        # liefert, ist der Plan gueltig -- kein Planner.
        if state.tasks:
            plan_ok = True
            audit("loop_resume", {"tasks": len(state.tasks),
                                  "quelle": "phase_state"}, pd, pn)
        else:
            plan_ok = _check_plan_gate_current(state)
            if plan_ok:
                audit("loop_resume",
                      {"tasks": len(state.tasks),
                       "quelle": "gate"}, pd, pn)

    if not plan_ok:
        audit("loop_plan_missing", {"aufgabe": aufgabe[:100]}, pd, pn)
        # M-299e: Preflight-Scan vor Planner. Klassifiziert
        # Baseline-Fehler, damit der Planner BLOCKER/FOLLOW_UP/
        # IGNORE entscheiden kann.
        if not getattr(state, "preflight_fehler", None):
            import time as _t_pf
            _pf_t0 = _t_pf.monotonic()
            audit("loop_preflight_start", {}, pd, pn)
            from werkstatt.planner import _preflight_scan
            _pf = _preflight_scan(state)
            audit("loop_preflight_done",
                  {"elapsed_s": round(_t_pf.monotonic() - _pf_t0, 2),
                   "befunde": len(_pf) if _pf else 0}, pd, pn)
            state.preflight_fehler = _pf
            if _pf:
                audit(
                    "loop_preflight_fehler",
                    {
                        "anzahl": len(_pf),
                        "klassen": sorted({f["klasse"] for f in _pf}),
                    },
                    pd, pn,
                )
        planner_stop_after_role = getattr(
            state, "planner_stop_after_role", None,
        )
        if planner_stop_after_role is not None:
            planner_ok = run_planner(
                state, stop_after_role=planner_stop_after_role,
            )
        else:
            planner_ok = run_planner(state)
        if not planner_ok:
            audit("loop_planner_failed", {}, pd, pn)
            return 1, False
        if getattr(state, "planner_step_yielded", False):
            audit(
                "loop_phase",
                {
                    "phase": f"planner_{state.planner_stop_after_role}",
                    "status": "checkpoint",
                },
                pd,
                pn,
            )
            group_end()
            return 0, False
        _plan_text = getattr(state, "architect_prosa", "") or ""
        audit("loop_plan_shown",
              {"plan_text": _plan_text[:80_000],
               "plan_laenge": len(_plan_text),
               "phasen": len(state.phasen or []),
               "tasks": len(state.tasks or []),
               "quelle": "planner_phase"},
              pd, pn)

        # OP-136a: Contract-Validierung planner->builder.
        # Nullfall "bereits erfuellt" erlaubt leere Tasks — kein Fail.
        if (not state.auftrag_bereits_erfuellt
                and getattr(state, "tasks", None)) and not _validate_contract_safe(
                "planner", "builder", state, pd, pn):
            return 1, False

        # Der Scout kann einen No-Op melden. Auch dieser Befund muss
        # vor der Ergebnispruefung durch das verpflichtende Plan-Gate.
        if state.auftrag_bereits_erfuellt:
            audit("auftrag_bereits_erfuellt",
                  {"quelle": "scout", "aktion": "no_op_plan_gate"},
                  pd, pn)
            # Merker fuer die No-Op-Plananzeige und das Human-Gate.
            state.scout_bereits_erfuellt = True
            state.auftrag_bereits_erfuellt = False
            audit("loop_phase",
                  {"phase": "plan_gate", "status": "start",
                   "reason": "auftrag_bereits_erfuellt"}, pd, pn)
            if _human_gate_plan(state) != 0:
                audit("loop_phase",
                      {"phase": "plan_gate", "status": "rejected",
                       "reason": "auftrag_bereits_erfuellt"}, pd, pn)
                group_end()
                return 1, True
            audit("loop_phase",
                  {"phase": "plan_gate", "status": "approved",
                   "reason": "auftrag_bereits_erfuellt"}, pd, pn)
            # Aufgabenzaehler erst nach Freigabe auf Erfolg setzen.
            tasks_ok = 1
            state.tasks_ok_counter = tasks_ok
            _task_ende(state, phase_state, "scout_skip", ok=True,
                       name="Auftrag bereits erfuellt")
            group_end()  # Phase 2: Planner
            group_start("Phase 5: Human-Gate")
            audit("loop_phase", {"phase": "human_gate",
                                 "status": "start",
                                 "reason": "auftrag_bereits_erfuellt"},
                  pd, pn)
            rc = _human_gate(state)
            group_end()
            # OP-398: Der Scout-No-Op muss dieselbe Abschluss-Verify
            # bestehen wie ein gebauter Auftrag. Sonst koennte ein
            # Modellurteil ohne technische Belege als Erfolg gelten.
            if rc == 0 and not _verify_patches(state, phase="phase_end"):
                audit("loop_gate_failed",
                      _gate_failed_payload(
                          "phase_end",
                          getattr(state, "last_verify_errors", []) or [],
                      ),
                      pd, pn)
                audit("loop_phase",
                      {"phase": "completion",
                       "status": "incomplete",
                       "reason": "scout_noop_verify_failed"},
                      pd, pn)
                rc = 1
            if rc == 0:
                audit("loop_erfolg",
                      {"project_name": project_name,
                       "via": "auftrag_bereits_erfuellt"}, pd, pn)
            return rc, True

        # M-458: Architect-Prosa anzeigen (Planner-Split).
        _arch_prosa = state.architect_prosa
        if _arch_prosa:
            from werkstatt import render as _r_arch
            try:
                _r_arch.panel_diff(
                    _arch_prosa, title="ARCHITECT-BESCHREIBUNG"
                )
            except Exception:
                pass
        else:
            _arch_tasks = [
                t for t in (state.tasks or [])
                if isinstance(t, dict) and t.get("action") == "architect"
            ]
            if _arch_tasks:
                _arch_desc = _arch_tasks[0].get("description", "")
                if _arch_desc:
                    from werkstatt import render as _r_arch
                    try:
                        _r_arch.panel_diff(
                            _arch_desc, title="ARCHITECT-BESCHREIBUNG"
                        )
                    except Exception:
                        pass
        plan_ok = _check_plan_gate_current(state)
        # Plan recovery is checkpoint-like: only a new, actionable rejection
        # can choose another attempt. Repeating a rejection or exhausting the
        # run budget stops; there is no fixed retry-count loop.
        _seen_plan_rejections: set[str] = set()
        _replan_attempt = 0
        while not plan_ok:
            _info, _feedback_decision, _signature = (
                _plan_reflection_feedback(state, _seen_plan_rejections)
            )
            if _feedback_decision != "new_budgeted_rejection":
                audit(
                    "loop_plan_reflection_abgebrochen",
                    {
                        "attempt": _replan_attempt + 1,
                        "rule": (
                            _info.get("regel")
                            if isinstance(_info, dict) else None
                        ),
                        "reason": _feedback_decision,
                        "evidence_signature": _signature,
                    },
                    pd,
                    pn,
                )
                break
            _replan_attempt += 1
            audit(
                "loop_plan_reflection",
                {
                    "attempt": _replan_attempt,
                    "info": _info,
                    "evidence_signature": _signature,
                    "route": "new_feedback_within_run_budget",
                },
                pd,
                pn,
            )
            if not isinstance(_info, dict) or not replan_task_graph_from_architect(
                state, _info,
            ):
                break
            plan_ok = _check_plan_gate_current(state)
        if not plan_ok:
            # FIX Z 2026-10-31: Bei Plan-Reject nicht "Tasks: 0/7"
            # melden (irrefuehrend — Tasks wurden geplant, aber
            # verworfen). Klarstellen.
            step(2, "Planner", "Plan verworfen", ok=False)
            audit("loop_gate_failed",
                  _gate_failed_payload("plan", [], "plan_reject"),
                  pd, pn)
            return 1, False

    # M-348c: Plan-Human-Gate (nach Plan-Erstellung, vor Builder).
    if plan_ok:
        audit("loop_phase", {"phase": "plan_gate", "status": "start"}, pd, pn)
        _rc_plan = _human_gate_plan(state)
        if _rc_plan != 0:
            audit("loop_phase", {"phase": "plan_gate", "status": "rejected"}, pd, pn)
            # Welle H (2026-11-02): Reflection-Runde bei Plan-Reject
            _rej_ok = False
            try:
                from werkstatt.reflection import _plan_reject_reflection
                _rej_ok = _plan_reject_reflection(state)
            except Exception as _rej_exc:
                audit("loop_plan_reject_fail_closed",
                      {"reason": "reflection_exception",
                       "error": str(_rej_exc)[:200]}, pd, pn)
                return 1, False

            if _rej_ok:
                # Revidierter Plan gebaut, nochmal pruefen
                _plan2_ok = _check_plan_gate_current(state)
                if _plan2_ok:
                    # Welle H v2: nach Reflection nochmal human_gate_plan
                    _rc_plan2 = _human_gate_plan(
                        state, kontext="revidierter_plan",
                    )
                    if _rc_plan2 != 0:
                        audit("loop_plan_reject_fail_closed",
                              {"reason": "human_gate_reflection_rejected"},
                              pd, pn)
                        return 1, False
                    audit("loop_plan_gate_approved",
                          {"via": "reflection_and_human"}, pd, pn)
                else:
                    audit("loop_plan_reject_fail_closed",
                          {"reason": "reflection_plan_unvollstaendig"}, pd, pn)
                    return 1, False
            else:
                audit("loop_plan_reject_fail_closed",
                      {"reason": "reflection_failed"}, pd, pn)
                return 1, False
        audit("loop_phase", {"phase": "plan_gate", "status": "approved"}, pd, pn)
        # PhaseState mit vollstaendigem Plan-Checkpoint initialisieren.
        # K21: auch bei existierender aber leerer .phase.yaml ({})-Datei.
        if (not _resume_erlaubt
                or not phase_state.exists()
                or not phase_state.data.get("tasks")):
            phase_state.init_new(
                aufgabe,
                _normalize_tasks(state.tasks),
                tests=list(state.tests or []),
                akzeptanzkriterien=list(state.akzeptanzkriterien or []),
                phasen=list(state.phasen or []),  # M-323d
            )

    # M-298d: init_new-Fallback. Wenn der Plan von Anfang an gruen
    # war (state.tasks vorbelegt, z.B. via Resume), wurde
    # init_new oben NICHT aufgerufen (nur im !plan_ok-Zweig).
    # Dann ist phase_state.data = {} und get_next_task() liefert
    # None -> Task-Loop bricht sofort ab (M-298b-Loop-Bug).
    # K21: auch bei leerer existierender Datei.
    if ((not phase_state.exists()
         or not phase_state.data.get("tasks"))
            and state.tasks):
        phase_state.init_new(
            aufgabe,
            _normalize_tasks(state.tasks),
            tests=list(state.tests or []),
            akzeptanzkriterien=list(state.akzeptanzkriterien or []),
        )

    _el_plan = time.monotonic() - _t_plan
    step(2, "Planner", f"{len(state.tasks)} tasks", elapsed_s=_el_plan)
    audit("loop_phase", {"phase": "plan", "status": "ok"}, pd, pn)
    group_end()

    # 2. Pre-Build Verify (M-299i: deterministische Baseline-Klassifikation).
    # Profi-Ansatz (dxkit, GitAuto): Baseline-Schuld blockiert nicht.
    # Nur Fehler, deren Datei in den Task-Dateien ist, sind BLOCKER.
    if not _verify_patches(state, phase="pre_build"):
        task_files = _extract_files_from_tasks(state.tasks)
        preflight = state.preflight_fehler or []

        relevant: list[dict] = []
        follow_up: list[dict] = []
        for fehler in preflight:
            _f = fehler.get("datei")
            if _f and any(_f in tf or tf in _f for tf in task_files):
                relevant.append(fehler)
            else:
                follow_up.append(fehler)

        if relevant:
            audit(
                "loop_gate_failed",
                _gate_failed_payload(
                    "pre_build",
                    [f.get("datei") for f in relevant],
                ),
                pd, pn,
            )
            return 1, False
        else:
            audit(
                "loop_pre_build_uebersprungen",
                {
                    "follow_up": len(follow_up),
                    "task_files": task_files,
                    "reason": "baseline_schuld",
                },
                pd, pn,
            )
            # Kein return 1 - Loop laeuft weiter.

    return 0, False
