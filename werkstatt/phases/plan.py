"""Phase: _phase_plan_and_preflight (OP-139 Phase 2b)."""
from __future__ import annotations

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
    run_planner,
)


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
    plan_ok = _plan_gate(state)
    if not plan_ok and phase_state.exists():
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
            plan_ok = _plan_gate(state)
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
            from werkstatt.planner import _preflight_scan
            _pf = _preflight_scan(state)
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
        if not run_planner(state):
            audit("loop_planner_failed", {}, pd, pn)
            return 1, False

        # OP-136a: Contract-Validierung planner->builder.
        # Nullfall "bereits erfuellt" erlaubt leere Tasks — kein Fail.
        if (not state.auftrag_bereits_erfuellt
                and getattr(state, "tasks", None)) and not _validate_contract_safe(
                "planner", "builder", state, pd, pn):
            return 1, False

        # GOLD 2026-10-30: Scout kann bereits_erfuellt melden.
        # Dann ist der Plan leer (Tasks = []), und der Plan-Gate
        # wuerde fail-closed abbrechen. Wir springen direkt zum
        # Human-Gate.
        if state.auftrag_bereits_erfuellt:
            audit("auftrag_bereits_erfuellt",
                  {"quelle": "scout", "aktion": "skip_plan_gate"},
                  pd, pn)
            # OP-062g: Merker setzen, damit _human_gate_body den
            # Nullfall-Block rendern kann. Das auftrag_bereits_erfuellt-
            # Flag wird wie bisher geleert, damit es nicht in spaetere
            # Phasen leakt.
            state.scout_bereits_erfuellt = True
            state.auftrag_bereits_erfuellt = False
            # GOLD 2026-10-30: tasks_ok auf 1 setzen, damit K13
            # (rc=0 nur wenn tasks_ok>0) den Lauf als Erfolg wertet.
            # Live-Beleg 2026-10-30 21:59: Commit 30decc63 durch,
            # aber Footer zeigte LOOP FEHLGESCHLAGEN (tasks_ok=0).
            tasks_ok = 1
            state.tasks_ok_counter = tasks_ok
            _task_ende(state, phase_state, "scout_skip", ok=True,
                       name="Auftrag bereits erfuellt")
            # Direkt zum Human-Gate (Phase 5), Plan-Gate ueberspringen.
            group_end()  # Phase 2: Planner
            group_start("Phase 5: Human-Gate")
            audit("loop_phase", {"phase": "human_gate",
                                 "status": "start",
                                 "reason": "auftrag_bereits_erfuellt"},
                  pd, pn)
            rc = _human_gate(state)
            group_end()
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
        plan_ok = _plan_gate(state)
        # M-349c/d: Plan-Reflection. Max 3 Runden.
        # GOLD 2026-10-30: Strukturelle Fehler NICHT wiederholen.
        # Live-Beleg 2026-10-30 22:17-22:24: 3x Scout + Architect +
        # Planner-Split, weil der Hook DOKU_TASK/TASK_FILE ablehnte.
        # Ein neuer Plan hilft nicht — der Hook prueft deterministisch.
        _STRUKTURELLE_REGELN = frozenset({
            "DOKU_TASK", "TASK_FILE", "MIGRATIONS_KOLLISION",
            "ACTION", "PHASE_ID", "DATEINAME_AEHNLICH", "PAYLOAD",
        })
        for _runde in range(3):
            if plan_ok:
                break
            _info = getattr(state, "last_planner_info", None)
            if not _info:
                break
            _regel = (
                _info.get("regel", "") if isinstance(_info, dict) else ""
            )
            if _regel in _STRUKTURELLE_REGELN:
                audit("loop_plan_reflection_abgebrochen",
                      {"runde": _runde + 1,
                       "regel": _regel,
                       "grund": "struktureller_fehler",
                       "fakt": (_info.get("fakt", "")
                                if isinstance(_info, dict) else "")},
                      pd, pn)
                break
            audit("loop_plan_reflection",
                  {"runde": _runde + 1, "info": _info}, pd, pn)
            if not run_planner(state):
                break
            plan_ok = _plan_gate(state)
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
        _rc_plan = _human_gate_plan(
            state,
            auto_approve=state.auto_approve,
        )
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
                _plan2_ok = _plan_gate(state)
                if _plan2_ok:
                    # Welle H v2: nach Reflection nochmal human_gate_plan
                    _rc_plan2 = _human_gate_plan(
                        state,
                        auto_approve=state.auto_approve,
                        kontext="revidierter_plan",
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
        if (not phase_state.exists()
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
