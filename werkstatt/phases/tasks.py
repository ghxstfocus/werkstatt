"""Phase: _phase_tasks_loop (OP-139 Phase 2b)."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from werkstatt.antipattern import scan_patches
from werkstatt.event_store import EventStore
from werkstatt.render import (
    group_end,
    group_start,
    task,
    task_done,
    task_ok,
    task_started,
)
from werkstatt.state import RunState, check_run_lease
from werkstatt.verify_classify import filtere_harte_verify_fehler

from ._common import (
    _apply_one_patch,
    _call_hook,
    _delete_ziel_erlaubt,
    _gate_failed_payload,
    _get_git_diff_for_hook,
    _human_gate,
    _patches_wirklich_angewendet,
    _pruefe_prior_failed_dependency,
    _reflection_loop,
    _reset_task_state,
    _reviewer_rejected_payload,
    _ruff_fix_changed,
    _run_with_progress,
    _task_ende,
    _verify_patches,
    _verify_patches_soft,
    _with_spinner,
    audit,
    run_builder,
    run_reviewer,
)


def _audit_task_ok(
    transitioned: bool,
    task_id: str,
    task_name: str,
    project_dir: Path,
    project_name: str,
    *,
    via: str | None = None,
) -> None:
    """Emit a timeline success only after a new done transition."""
    if not transitioned:
        return
    payload = {
        "task_id": task_id,
        "name": task_name,
        "status": "done",
        "result_summary": "Task abgeschlossen und im Phase-State als erledigt markiert.",
        "evidence": ["Phase-State: done"],
    }
    if via:
        payload["via"] = via
    audit("loop_task_ok", payload, project_dir, project_name)



def _persist_run_checkpoint(
    store: EventStore,
    project_name: str,
    run_id: str,
    phase_state: Any,
    next_task: dict[str, Any] | None,
    *,
    run_state: RunState | None = None,
) -> None:
    """Persist task-boundary state and acknowledge only observed chat notices."""
    if run_state is not None:
        check_run_lease(run_state)
    record = store.get_run_record(project_name, run_id)
    if record is None:
        return

    worker_id = f"loop:{run_id}"
    notices: list[dict[str, object]] = []
    claimed: list[dict[str, Any]] = []
    for _ in range(20):
        message = store.claim_run_message(
            project_name, run_id, worker_id, lease_seconds=120,
        )
        if message is None:
            break
        if message["kind"] != "job_notice":
            break
        claimed.append(message)
        payload = message["payload"]
        notices.append({
            "seq": message["seq"],
            "job_id": payload.get("job_id"),
            "mode": payload.get("mode"),
            "session_id": payload.get("session_id"),
        })

    checkpoint = dict(record["checkpoint"])
    prior_notices = checkpoint.get("job_notices", [])
    if not isinstance(prior_notices, list):
        prior_notices = []
    checkpoint["job_notices"] = (prior_notices + notices)[-50:]
    checkpoint["safe_point"] = {
        "phase": "build",
        "next_task_id": next_task.get("id") if next_task else None,
        "completed_task_ids": [
            task_record.get("id")
            for task_record in phase_state.data.get("tasks", [])
            if isinstance(task_record, dict)
            and task_record.get("status") == "done"
        ],
    }
    if claimed:
        checkpoint["inbox_offset"] = max(
            int(checkpoint.get("inbox_offset", 0)),
            max(int(message["seq"]) for message in claimed),
        )
    if run_state is not None:
        check_run_lease(run_state)
    store.update_run_checkpoint(
        project_name,
        run_id,
        checkpoint,
        expected_version=record["checkpoint_version"],
    )
    for message in claimed:
        if run_state is not None:
            check_run_lease(run_state)
        if not store.acknowledge_run_message(
            message["seq"], worker_id, message["fencing_token"],
        ):
            raise RuntimeError(
                f"Run-Inbox-Lease verloren: {message['message_id']}",
            )


def _phase_tasks_loop(
    state: RunState,
    phase_state,
) -> tuple[int, int, list]:
    """Phase 3 (Fix AZ Stufe 8-C, 2026-10-31): Autonomer Task-Loop.

    Extrahiert aus run_pipeline_loop. Enthaelt den while-True-Loop
    mit Task-Build, Reviewer, Reflection, Task-Fail-Continue.

    Rueckgabe: (rc, tasks_ok, tasks).
    rc=1 -> Caller gibt direkt zurueck (Abbruch).
    rc=0 -> weiter mit Phase-End + Human-Gate.
    """
    pd = state.project_dir
    pn = state.project_name

    # OP-381g: loop_phase-Marker fuer Timeline-Gruppierung.
    # Ohne diesen Marker landen alle Builder/Verify/Reflection/Reviewer-
    # Events unter dem letzten loop_phase-Knoten (Plan) statt in einem
    # eigenen "Build"-Knoten. Live-Bug 2026-11-09: 104 children unter
    # "Plan", Timeline-Gruppierung kaputt (aggregate_timeline schliesst
    # Knoten nur bei naechstem loop_phase-Event, siehe inspector.py Z.965).
    audit("loop_phase", {"phase": "build", "status": "start"}, pd, pn)

    # 3. Autonomer Task-Loop (Claude-Code-Prinzip)
    #    Alle Tasks werden abgearbeitet ohne Unterbrechung.
    #    Human-Gate kommt nur am Ende der Phase.
    tasks = state.tasks
    # Resume after a final-verify failure may find every planned task already
    # done. Count persisted work so finalization can re-run verification instead
    # of misclassifying the resumed run as having done no work.
    tasks_ok = sum(
        1 for task_record in phase_state.data.get("tasks", [])
        if isinstance(task_record, dict) and task_record.get("status") == "done"
    )
    state.tasks_ok_counter = tasks_ok
    i = 0
    from werkstatt.agent import _enforce_run_budget
    # M-473: while-Loop statt for. Nach ADaPT-Split wird die
    # Schleife neu gestartet, damit Sub-Tasks gebaut werden.
    while True:
        check_run_lease(state)
        if _enforce_run_budget(state):
            phase_state.save()
            return 1, tasks_ok, tasks
        next_task = phase_state.get_next_task()
        from werkstatt.audit import get_run_id
        run_id = get_run_id()
        if run_id:
            _persist_run_checkpoint(
                EventStore(), pn, run_id, phase_state, next_task,
                run_state=state,
            )
        if next_task is None:
            # OP-163: unerfuellte Deps -> als blocked markieren.
            _pending_after = [
                _t_b for _t_b in phase_state.data.get("tasks", [])
                if isinstance(_t_b, dict)
                and _t_b.get("status") == "pending"
            ]
            for _t_b in _pending_after:
                _unmet = phase_state._unmet_dependencies(_t_b)
                _tid_b = _t_b.get("id", "?")
                phase_state.mark_blocked(
                    _tid_b, grund="deps:" + ",".join(_unmet),
                )
                audit("loop_task_blocked",
                      {"task_id": _tid_b, "unmet_deps": _unmet},
                      pd, pn)
            if _pending_after:
                phase_state.save()
            break
        task_obj = next_task  # Sub-Tasks werden direkt aus PhaseState geholt.
        i += 1
        task_id = next_task.get("id", f"t{i}")
        phase_state.mark_running(task_id)
        task_name = task_obj.get("name", f"Task {i}") if isinstance(task_obj, dict) else str(task_obj)
        group_start(f"Task {i}/?: {task_name}")
        try:
            task_started(i, len(tasks), task_name)
        except Exception:
            pass
        _t_task = time.monotonic()
        task(i, len(tasks), task_name)
        audit("loop_task_start", {"task_id": task_id, "name": task_name}, pd, pn)

        # Builder fuer diesen Task
        state.aktuelle_task = task_obj
        # OP-166: per-Task-State reset, sonst leaken Fehler aus
        # vorherigen Tasks in Reflection (Loop-Test-4 t7-Bug).
        _reset_task_state(state)

        # M-306d Fix 1: Pro-Task action-Check. read-only Tasks
        # erzeugen keinen Patch, markieren sich direkt als ok.
        _is_read = isinstance(task_obj, dict) and task_obj.get("action") == "read"
        if _is_read:
            audit("loop_task_read_only", {"task_id": task_id, "name": task_name}, pd, pn)
            _el_task = time.monotonic() - _t_task
            task_ok(i, len(tasks), elapsed_s=_el_task)
            group_end()
            tasks_ok += 1
            state.tasks_ok_counter = tasks_ok
            _audit_task_ok(
                _task_ende(state, phase_state, task_id, ok=True, name=task_name),
                task_id, task_name, pd, pn,
            )
            continue

        # Verify-Task: kein Builder, direkt Verify + Reviewer.
        _is_verify = isinstance(task_obj, dict) and task_obj.get("action") == "verify"
        if _is_verify:
            _v_ok = bool(_verify_patches(state, phase="post_build"))
            if _v_ok:
                _r_ok = bool(run_reviewer(state))
            else:
                _r_ok = False
            _el_task = time.monotonic() - _t_task
            if _v_ok and _r_ok:
                task_ok(i, len(tasks), elapsed_s=_el_task)
                group_end()
                tasks_ok += 1
                state.tasks_ok_counter = tasks_ok
                _audit_task_ok(
                    _task_ende(state, phase_state, task_id, ok=True, name=task_name),
                    task_id, task_name, pd, pn,
                    via="verify_and_review",
                )
            else:
                group_end()
                _task_ende(state, phase_state, task_id, ok=False, name=task_name, failure="verify_failed")
            continue

        if not _run_with_progress(
            lambda i=i: _with_spinner(f"Builder t{i}", lambda: run_builder(state)),
            i, len(tasks), task_name,
        ):
            # M-316 + M-317: Idempotenz-Erkennung NUR bei
            # action="create". Bei update: fail-closed (return 1).
            _loop_action = None
            if isinstance(task_obj, dict):
                _loop_action = task_obj.get("action")
            if _loop_action not in ("create", "update", "read"):
                # read-Task mit leerem Patch: echter Fehler (Builder
                # sollte hier nie laufen). Bei create/update: Idempotenz-
                # Pfad unten pruefen (M-318).
                # FIX AR 2026-10-31: continue statt return 1.
                audit("loop_builder_failed", {"task_id": i, "action": _loop_action}, pd, pn)
                _task_ende(state, phase_state, task_id, ok=False, name=task_name, failure="builder_failed")
                continue

            # Idempotenz-Erkennung (nur create).
            # M-355: Loop-Idempotenz-Check entfernt. Der Builder
            # (M-352) entscheidet ueber Idempotenz. Der Loop prueft
            # nur noch, ob der Builder erfolgreich war.
            # OP-061 B: Hat ein prior done-Task die gleiche Datei
            # bereits geschrieben? Dann ist der Task erfuellt.
            _task_files_b = (task_obj.get("task_files", [])
                             if isinstance(task_obj, dict) else [])
            if _task_files_b and phase_state is not None:
                _primary = _task_files_b[0]
                _prior_done = False
                for _pt in phase_state.data.get("tasks", []):
                    if _pt.get("id") == task_id:
                        continue
                    if _pt.get("status") != "done":
                        continue
                    if _primary in (_pt.get("task_files") or []):
                        _prior_done = True
                        break
                if _prior_done:
                    _v_gruen_b = False
                    try:
                        _v_gruen_b = bool(
                            _verify_patches(state, phase="post_build"))
                    except Exception:
                        _v_gruen_b = False
                    if _v_gruen_b:
                        audit("builder_patch_bereits_erfuellt",
                              {"task_id": i, "file": _primary}, pd, pn)
                        tasks_ok += 1
                        state.tasks_ok_counter = tasks_ok
                        _audit_task_ok(
                            _task_ende(state, phase_state, task_id, ok=True,
                                       name=task_name),
                            task_id, task_name, pd, pn,
                            via="builder_patch_bereits_erfuellt",
                        )
                        continue
            # M-355b: run_builder=False -> Task gescheitert, KEIN
            # Durchfallen in den Patch-Pfad mit leerem state.patches.
            audit("loop_builder_aufgerufen", {"task_id": i}, pd, pn)
            _task_ende(state, phase_state, task_id, ok=False,
                       name=task_name, failure="builder_failed")
            _split_failure = "builder_failed"
            # FIX AP 2026-10-31: Dependency-Failure -> continue statt
            # return 1. Live-Beleg 10:36: t1 (create) failte, t2-t4
            # (update) fanden Datei nicht, Loop brach bei t2 ab,
            # t5-t14 (unabhaengig) wurden nie versucht.
            _is_dep_fail, _dep_files = _pruefe_prior_failed_dependency(
                phase_state, task_id)
            if _is_dep_fail:
                audit("loop_task_failed_dependency",
                      {"task_id": i, "files": _dep_files}, pd, pn)
                _task_ende(state, phase_state, task_id, ok=False,
                           name=task_name, failure="depends_on_failed")
                continue
            audit("loop_task_failed", {"task_id": i, "grund": _split_failure}, pd, pn)
            _task_ende(state, phase_state, task_id, ok=False,
                       name=task_name, failure=_split_failure)
            # K43b / FIX AR 2026-10-31: Task-Fail -> continue statt
            # return 1. Spaetere Tasks koennen unabhaengig sein.
            # Live-Beleg v6: t2 failte, t3-t7 nie versucht.
            continue

        # GOLD 2026-10-30: Wenn der Builder das auftrag_bereits_erfuellt-
        # Flag gesetzt hat (weil die Zieldatei den Zielzustand schon
        # enthaelt), ist der Task erfuellt. Kein Hook, kein Apply, kein
        # Reviewer. Live-Beleg 21:18:37: Builder setzte Flag, Hook liess
        # durch, Apply-Loop lief mit leerem state.patches,
        # reviewer_kein_diff_aber_patches -> fail-closed.
        if (state.auftrag_bereits_erfuellt
            and state.auftrag_bereits_erfuellt_bestaetigt):
            audit("auftrag_bereits_erfuellt",
                  {"task_id": i,
                   "name": task_name,
                   "reason": "loop_flag_vor_hook"},
                  pd, pn)
            state.auftrag_bereits_erfuellt = False
            # GOLD 2026-10-30: tasks_ok auch bei auftrag_bereits_erfuellt
            # hochzaehlen. Sonst zeigt der Footer "1/5", obwohl alle 5
            # Tasks done sind (Live-Beleg 2026-10-30 21:41:45).
            tasks_ok += 1
            state.tasks_ok_counter = tasks_ok
            _audit_task_ok(
                _task_ende(state, phase_state, task_id, ok=True,
                           name=task_name),
                task_id, task_name, pd, pn,
                via="auftrag_bereits_erfuellt_pre_hook",
            )
            continue

        # PreToolUse-Hook (Phase 15): Patch pruefen, BEVOR er angewendet wird.
        # GOLD 2026-10-30: Wenn ein Patch blockiert wird, ueberspringen
        # wir den Apply-Loop komplett. Vorher rief "break" nur aus der
        # Hook-Schleife aus — der Apply-Loop darunter wendete dieselben
        # blockierten Patches trotzdem an (Audit loop_patch_updated).
        patches = state.patches
        _hook_blocked = False
        _blocked_reason = ""
        for patch in patches:
            if not isinstance(patch, dict):
                continue
            action = patch.get("action", "update")
            patch_text = patch.get("new_string", "") or patch.get("content", "")
            hook_res = _call_hook("pre_tool_use.py", {
                "patch": patch_text,
                "action": action,
                "project_dir": str(pd),
            })
            if not hook_res.get("allow", False):
                audit("loop_hook_blocked",
                      {"hook": "pre_tool_use",
                       "reason": hook_res.get("reason", "")}, pd, pn)
                _hook_blocked = True
                _blocked_reason = hook_res.get("reason", "")
                break
        if _hook_blocked:
            # GOLD 2026-10-30: ZUERST pruefen, ob der Builder das
            # auftrag_bereits_erfuellt-Flag gesetzt hat (weil die
            # Zieldatei den Zielzustand schon enthaelt). Dann ist der
            # Hook-Block irrelevant — der Task ist erfuellt.
            # Live-Beleg 2026-10-30 20:52:18: Hook blockte import math,
            # _reflection_loop gab True (weil Verify wegen leerer
            # Stage-Skipping gruen war), Task wurde als ok markiert,
            # ohne dass etwas geprueft wurde.
            if (state.auftrag_bereits_erfuellt
                and state.auftrag_bereits_erfuellt_bestaetigt):
                audit("auftrag_bereits_erfuellt",
                      {"task_id": i,
                       "name": task_name,
                       "reason": "hook_blocked_aber_erfuellt",
                       "blocked_reason": _blocked_reason},
                      pd, pn)
                state.auftrag_bereits_erfuellt = False
                tasks_ok += 1
                state.tasks_ok_counter = tasks_ok
                _audit_task_ok(
                    _task_ende(state, phase_state, task_id, ok=True,
                               name=task_name),
                    task_id, task_name, pd, pn,
                    via="auftrag_bereits_erfuellt",
                )
                continue
            # Reflection versuchen. Sie ruft run_builder + _apply_patches_with_hooks
            # intern; bei True ist der neue Patch schon angewendet.
            # FIX AL 2026-10-31: Reflection-OK nur, wenn applied_count
            # tatsaechlich gestiegen ist. Vorher: _verify_patches gab
            # True bei "no changed files" (leere Stage), Task wurde
            # als done markiert, obwohl nichts geschrieben wurde.
            # Live-Beleg 2026-10-31 10:03 t1.
            _applied_vor_al = int(
                state.applied_count or 0)
            _refl_ok_al = _reflection_loop(state)
            _applied_nach_al = int(
                state.applied_count or 0)
            if _refl_ok_al and _applied_nach_al > _applied_vor_al:
                # OP-167: Counter auch im Reflection-OK-Pfad hochzaehlen.
                # Loop-Test-8 (2026-11-05): t3/t4 über Reflection
                # done, aber tasks_ok_counter blieb 0 -> Footer
                # meldete '8 failed'.
                tasks_ok += 1
                state.tasks_ok_counter = tasks_ok
                _audit_task_ok(
                    _task_ende(state, phase_state, task_id, ok=True,
                               name=task_name),
                    task_id, task_name, pd, pn, via="reflection",
                )
            elif _refl_ok_al and _applied_nach_al <= _applied_vor_al:
                # Reflection sagte "ok", aber nichts angewendet
                audit("loop_reflection_no_apply",
                      {"task_id": i,
                       "applied_vorher": _applied_vor_al,
                       "applied_nachher": _applied_nach_al}, pd, pn)
                _task_ende(state, phase_state, task_id, ok=False,
                           name=task_name,
                           failure="reflection_ohne_apply")
                audit("loop_task_failed",
                      {"task_id": i,
                       "grund": "reflection_ohne_apply"}, pd, pn)
            else:
                _task_ende(state, phase_state, task_id, ok=False,
                           name=task_name,
                           failure=f"hook_blocked: {_blocked_reason}")
                audit("loop_task_failed",
                      {"task_id": i, "grund": f"hook_blocked: {_blocked_reason}"},
                      pd, pn)
            continue

        # Patches anwenden (create + update) — NACH dem Hook.
        # K50b: applied_count zaehlen.
        state.applied_count = 0
        backup_dir = Path(pd) / ".werkstatt" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        _allowed_for_task: set[str] = set()
        for _t_av in (state.tasks or []):
            if isinstance(_t_av, dict) and _t_av.get("id") == task_id:
                _allowed_for_task = set(_t_av.get("task_files") or [])
                break
        for patch in patches:
            if not isinstance(patch, dict):
                continue
            action = patch.get("action", "update")
            file = patch.get("file", "")
            if not file:
                continue
            target = Path(pd) / file

            if action == "create":
                content = patch.get("content", "")
                if not content:
                    continue
                if target.exists():
                    audit("loop_patch_file_exists", {"file": file}, pd, pn)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                # FIX N 2026-10-31: Write-Fehler fail-closed.
                try:
                    check_run_lease(state)
                    target.write_text(content)
                except OSError as _e:
                    audit("loop_patch_write_failed",
                          {"file": file, "fehler": str(_e)[:200]}, pd, pn)
                    continue
                state.applied_count += 1
                audit("loop_patch_created", {"file": file}, pd, pn)
            elif action == "update":
                old_str = patch.get("old_string", "")
                new_str = patch.get("new_string", "")
                if not old_str or not new_str:
                    continue
                if not target.exists():
                    audit("loop_patch_file_missing", {"file": file}, pd, pn)
                    continue
                file_content = target.read_text()
                _neu_content2, _match2 = _apply_one_patch(
                    file_content, old_str, new_str,
                )
                # FIX W 2026-10-31: Doppel-Schreiben entfernt. Der
                # alte write_text+applied_count++ stand hier VOR
                # dem "erst pruefen, dann schreiben"-Check. Live-
                # Beleg: applied_count doppelt gezaehlt, und
                # Schreibfehler beim ersten write_text unbehandelt.
                # Der korrekte Pfad ist weiter unten (try/except).
                if _match2 == "fail":
                    audit("loop_patch_old_string_not_found",
                          {"file": file, "old": old_str[:50]}, pd, pn)
                    # M-298d: Reflection statt stumm weiterlaufen.
                    # OP-061 A: Flag-Check vor fail-Pfad.
                    _refl_ok = _reflection_loop(state)
                    if not _refl_ok:
                        if (state.auftrag_bereits_erfuellt
                                and _verify_patches(state, phase="post_build")):
                            audit("auftrag_bereits_erfuellt",
                                  {"task_id": i,
                                   "reason": "pre_reviewer_patch_fail"},
                                  pd, pn)
                            state.auftrag_bereits_erfuellt = False
                            tasks_ok += 1
                            state.tasks_ok_counter = tasks_ok
                            _audit_task_ok(
                                _task_ende(state, phase_state, task_id, ok=True,
                                           name=task_name),
                                task_id, task_name, pd, pn,
                                via="auftrag_bereits_erfuellt_pre_reviewer",
                            )
                            break
                        _task_ende(state, phase_state, task_id, ok=False, name=task_name, failure="old_string_not_found")
                        return 1, tasks_ok, tasks
                    break  # Retry mit korrigiertem Patch
                # M-351a: Patch mit identischem Inhalt = no_effect.
                if old_str == new_str and _match2 == "exact":
                    audit("loop_patch_no_effect", {"file": file}, pd, pn)
                    continue
                if _match2 != "exact":
                    audit("loop_patch_fallback_used",
                          {"file": file, "match": _match2}, pd, pn)
                # GOLD 2026-10-30: Erst pruefen, ob new_str im neuen
                # Inhalt steht, DANN schreiben. Vorher wurde
                # geschrieben, applied_count++, dann geprueft. Bei
                # loop_patch_not_applied war applied_count trotzdem
                # >0 -> _patches_wirklich_angewendet True ->
                # reviewer_reject_ignoriert -> task_ok obwohl Patch
                # nicht angewendet. Live-Beleg 2026-10-30 22:35.
                if new_str not in _neu_content2:
                    audit("loop_patch_not_applied_vor_schreiben",
                          {"file": file}, pd, pn)
                    if not _reflection_loop(state):
                        _task_ende(state, phase_state, task_id,
                                   ok=False, name=task_name,
                                   failure="patch_not_applied")
                        return 1, tasks_ok, tasks
                    _task_ende(state, phase_state, task_id,
                               ok=False, name=task_name,
                               failure="patch_not_applied_nach_reflection")
                    break
                # FIX N 2026-10-31: Write-Fehler fail-closed.
                try:
                    check_run_lease(state)
                    target.write_text(_neu_content2)
                except OSError as _e:
                    audit("loop_patch_write_failed",
                          {"file": file, "fehler": str(_e)[:200]}, pd, pn)
                    _task_ende(state, phase_state, task_id,
                               ok=False, name=task_name,
                               failure="patch_write_failed")
                    break
                # M-298d: Post-Apply-Verifikation (Profi-Ansatz
                # Overwatcher/Claude-Code edit-verifier).
                _after = target.read_text()
                if new_str not in _after:
                    audit("loop_patch_not_applied", {"file": file}, pd, pn)
                    # GOLD 2026-10-30: Auch nach erfolgreicher Reflection
                    # ist der Patch NICHT angewendet. Der Task ist nicht
                    # erledigt. Live-Beleg 2026-10-30 22:35:
                    # loop_patch_not_applied, _reflection_loop True,
                    # break, reviewer_kein_diff_aber_patches,
                    # loop_task_ok trotzdem -> Phase-Review fail.
                    if not _reflection_loop(state):
                        _task_ende(state, phase_state, task_id,
                                   ok=False, name=task_name,
                                   failure="patch_not_applied")
                        return 1, tasks_ok, tasks
                    # Reflection war "erfolgreich", aber der Patch
                    # wurde trotzdem nicht angewendet. Task fail.
                    _task_ende(state, phase_state, task_id,
                               ok=False, name=task_name,
                               failure="patch_not_applied_nach_reflection")
                    break
                # FIX AI 2026-10-31: applied_count++ erst NACH
                # erfolgreichem Post-Verify. Vorher (Fix W) wurde
                # der alte applied_count++ entfernt, aber nirgends
                # neu hinzugefuegt. Folge: _patches_wirklich_angewendet
                # war False, auch bei sauber angewendetem Patch.
                # Position: nach write_text + nach _after-Check.
                state.applied_count += 1
                audit("loop_patch_updated", {"file": file}, pd, pn)
            elif action == "delete":
                # Fix AV: Datei loeschen. Whitelist = task_files der aktuellen Task.
                _ok_del, _grund_del = _delete_ziel_erlaubt(
                    Path(file), _allowed_for_task, Path(pd),
                )
                if not _ok_del:
                    audit("loop_patch_delete_blocked",
                          {"file": file, "grund": _grund_del}, pd, pn)
                    continue
                if not target.exists():
                    audit("loop_patch_delete_skip_missing",
                          {"file": file}, pd, pn)
                    continue
                try:
                    check_run_lease(state)
                    target.unlink()
                except OSError as _e:
                    audit("loop_patch_delete_failed",
                          {"file": file, "fehler": str(_e)[:200]}, pd, pn)
                    continue
                state.applied_count += 1
                audit("loop_patch_deleted", {"file": file}, pd, pn)

        # M-334b/M-351: post_tool_use entfernt (prueft Werkstatt statt
        # Zielprojekt). _verify_patches prueft das Zielprojekt.

        # Simplify-Hook (Phase 11)
        hook_res = _call_hook("simplify.py", {"diff": _get_git_diff_for_hook()})
        if not hook_res.get("allow", False):
            audit("loop_hook_blocked", {"hook": "simplify", "reason": hook_res.get("reason", "")}, pd, pn)
            if not _reflection_loop(state):
                return 1, tasks_ok, tasks

        # M-467: ruff --fix auf geaenderte Dateien (deterministisch).
        # GOLD 2026-10-30: ausgelagert nach _ruff_fix_changed, damit
        # dieselbe Logik auch in der Reflection-Schleife laeuft.
        _ruff_fix_changed(state)

        # Post-Build Verify + Reflection (automatisch)
        # FIX AT/AU 2026-10-31: Weiche Verify-Fehler (ruff, mypy)
        # markieren Task als done mit Warnung, nicht als failed.
        # Live-Beleg v7: t1 ok bis auf 2 ruff TRY004, als failed
        # markiert trotz funktionalem Code.
        _v_hart_ok, _v_weich = _verify_patches_soft(state, phase="post_build")
        if not _v_hart_ok:
            audit(
                "loop_gate_failed",
                _gate_failed_payload("post_build", []),
                pd, pn,
            )
            if not _reflection_loop(state):
                audit("loop_reflection_gescheitert", {"task_id": i}, pd, pn)
                # OP-059d: bei Spec-Widerspruch-Verdacht human_review
                # statt post_build_verify_failed.
                if state.spec_widerspruch_erkannt:
                    audit("loop_verify_failed_human_review",
                          {"task_id": i,
                           "grund": "spec_widerspruch_vermutet"}, pd, pn)
                    state.spec_widerspruch_erkannt = False
                    _task_ende(state, phase_state, task_id,
                               ok=False, name=task_name,
                               human_review=True,
                               failure="spec_widerspruch_vermutet")
                    continue
                # OP-090: Human-Gate statt sofortigem Fail.
                # Der User soll den Diff sehen und entscheiden:
                # j = Patches behalten + committen (Task ok)
                # n = Patches verwerfen (Task fail, Loop laeuft weiter)
                state.reflection_erschoepft = True
                _gate_rc = _human_gate(state)
                state.reflection_erschoepft = False
                if _gate_rc == 0:
                    audit("loop_human_gate_reflection_erschoepft_approved",
                          {"task_id": i}, pd, pn)
                    # OP-167: Counter auch hier hochzaehlen.
                    # Reflection-Erschoepft-Gate-approve (User 'j').
                    tasks_ok += 1
                    state.tasks_ok_counter = tasks_ok
                    _task_ende(state, phase_state, task_id,
                               ok=True, name=task_name,
                               failure="reflection_erschoepft_approved")
                    continue
                audit("loop_human_gate_reflection_erschoepft_rejected",
                      {"task_id": i}, pd, pn)
                _task_ende(state, phase_state, task_id,
                           ok=False, name=task_name,
                           failure="reflection_erschoepft_rejected")
                continue
        elif _v_weich:
            # Weiche Fehler: Warnung auditieren, aber Task laeuft weiter
            # zum Reviewer (der prueft Code-Substanz).
            audit("loop_task_soft_fail",
                  {"task_id": i, "warnungen": len(_v_weich),
                   "errors": _v_weich[:3]}, pd, pn)

        # Reviewer (Phase 9)
        # FIX R 2026-10-31: Deterministischen Reviewer-Fail nicht
        # durch "pytest gruen" ignorieren. Flag wird in run_reviewer
        # gesetzt (z.B. reviewer_unvollstaendig).
        state.reviewer_deterministic_fail = False

        # Pre-Reviewer-Gate: harte Verify-Fehler verhindern LLM-Review.
        # Live-Beleg 2026-11-02 (OP-077): Builder hat __all__=["create_app"]
        # ohne create_app gebaut. ruff F822 (undefined name) hat es gemeldet
        # (in _v_weich), aber _v_hart_ok war True (ruff ist weiche Stage).
        # Der Reviewer hat approved -> t1 = done. Test scheitert 5 Runden.
        #
        # WICHTIG: Nur _v_weich pruefen (frischer Rueckgabewert von
        # _verify_patches_soft). NICHT last_verify_errors — das ist global
        # und enthaelt Reste vom ersten Reviewer-Call.
        _harte = filtere_harte_verify_fehler(list(_v_weich or []))
        if _harte:
            audit(
                "reviewer_pre_gate_hart",
                {
                    "task_id": i,
                    "anzahl": len(_harte),
                    "beispiele": [str(e)[:120] for e in _harte[:3]],
                },
                pd, pn,
            )
            state.reviewer_bugs = [
                {
                    "severity": "high",
                    "description": (
                        f"Pre-Reviewer-Gate: {len(_harte)} harte Verify-Fehler "
                        f"vor LLM-Review (nicht uebergangen): "
                        + "; ".join(str(e)[:80] for e in _harte[:3])
                    ),
                }
            ]
            # Reviewer ueberspringen, Reflection soll greifen (nicht
            # deterministic_fail, sonst wird Task sofort gefailt).
            _rev_ok = False
        else:
            _rev_ok = _with_spinner(f"Reviewer t{i}", lambda: run_reviewer(state))
        # K40: Historie pushen (unabhaengig vom Ergebnis).
        _cur_bugs = state.reviewer_bugs or []
        if _cur_bugs:
            _hist = getattr(state, "reviewer_bugs_history", None)
            if _hist is None:
                state.reviewer_bugs_history = []
                _hist = state.reviewer_bugs_history
            _hist.append(list(_cur_bugs))
            # Limit auf 5 Runden (RAM-Schutz).
            if len(_hist) > 5:
                state.reviewer_bugs_history = _hist[-5:]
        if not _rev_ok:
            # FIX R 2026-10-31: Deterministischer Fail = sofort
            # task_fail, kein Reflection, kein Ignore.
            if state.reviewer_deterministic_fail:
                audit("loop_reviewer_deterministic_fail",
                      {"task_id": i}, pd, pn)
                _task_ende(state, phase_state, task_id, ok=False,
                           name=task_name,
                           failure="reviewer_unvollstaendig")
                # FIX AR 2026-10-31: continue statt return 1.
                continue
            audit(
                "loop_reviewer_rejected",
                _reviewer_rejected_payload(
                    task_id,
                    {"bugs": state.reviewer_bugs or []},
                ),
                pd, pn,
            )
            # M-314: Reviewer-Bug-Text als Kontext an Reflection.
            _reviewer_bugs = state.reviewer_bugs or []
            # M-441: Bug-Anzahl Runde 1 merken (fuer Divergenz-Check).
            _bugs_runde1 = len(_reviewer_bugs)
            _bug_ctx = ""
            if _reviewer_bugs:
                import json as _json
                _bug_ctx = _json.dumps(_reviewer_bugs, ensure_ascii=False)
            # OP-059: Diff-Hash VOR Reflexion als Referenz fuer
            # die false_positive-Erkennung (idempotenter Patch).
            try:
                from werkstatt.reflection import _diff_hash_for_state as _dh
                state._reflection_diff_hash = _dh(state)
            except Exception:
                state._reflection_diff_hash = None
            state.reviewer_stagnation_false_positive = False
            if not _reflection_loop(state, error_context=_bug_ctx):
                audit("loop_reviewer_reflection_gescheitert", {"task_id": i}, pd, pn)
                # M-343c: pytest ist das letzte Wort. Wenn der letzte
                # _verify_patches-Lauf gruen war (last_verify_errors leer),
                # ist der Reviewer-Reject eine Halluzination.
                _last_errors = state.last_verify_errors or []
                # K50-Bug-A: wie BUG-B, gleicher semantischer
                # _hat_patch-Check. Ohne diesen Zweig war der
                # erste Reject-Pfad fail-open, der zweite fail-
                # closed -- asymmetrisch und reproduzierbar falsch.
                _hat_patch_a = _patches_wirklich_angewendet(state)
                if not _last_errors and _hat_patch_a:
                    audit("loop_reviewer_reject_ignoriert",
                          {"task_id": i, "grund": "pytest gruen"}, pd, pn)
                    # Fall durch zum task_ok
                elif not _last_errors and not _hat_patch_a:
                    audit("loop_reviewer_reject_fail_closed",
                          {"task_id": i, "grund": "kein_patch_angewendet_runde1"},
                          pd, pn)
                    _task_ende(state, phase_state, task_id, ok=False,
                               name=task_name,
                               failure="reviewer_rejected_no_patch")
                    # FIX AR 2026-10-31: continue statt return 1.
                    continue
                else:
                    # OP-060b-Rest: bei Spec-Widerspruch-Verdacht
                    # human_review statt failed.
                    if state.spec_widerspruch_erkannt:
                        audit("loop_reviewer_reject_human_review",
                              {"task_id": i,
                               "grund": "spec_widerspruch_vermutet"}, pd, pn)
                        state.spec_widerspruch_erkannt = False
                        _task_ende(state, phase_state, task_id,
                                   ok=False, name=task_name,
                                   human_review=True,
                                   failure="spec_widerspruch_vermutet")
                        continue
                    _task_ende(state, phase_state, task_id, ok=False, name=task_name, failure="reviewer_rejected")
                    continue
            # OP-064a: Sticky-Veto. Wenn die Reflection spec_widerspruch
            # erkannt hat, ist der Task NICHT fertig — auch wenn die
            # Reflection return True lieferte. Veto + human_review.
            if state.spec_widerspruch_erkannt:
                audit("loop_task_spec_widerspruch_veto",
                      {"task_id": i,
                       "grund": "spec_widerspruch_vermutet"}, pd, pn)
                state.spec_widerspruch_erkannt = False
                phase_state.mark_vetoed(
                    task_id, grund="spec_widerspruch_vermutet",
                )
                _task_ende(state, phase_state, task_id,
                           ok=False, name=task_name,
                           human_review=True,
                           failure="spec_widerspruch_vermutet")
                continue
            # OP-059: False-Positive erkannt -> erneuten Reviewer-
            # Call sparen (Reviewer-Bug, nicht Task-Problem).
            _is_fp = bool(state.reviewer_stagnation_false_positive)
            if _is_fp:
                audit("loop_reviewer_reject_false_positive",
                      {"task_id": i, "grund": "stagnation_idempotent"}, pd, pn)
                # Fall durch zum task_ok (kein _task_ende im Else-Zweig)
            # M-306d Fix 2: Nach erfolgreicher Reflection MUSS der
            # Reviewer erneut pruefen. Sonst fail-open (HR-R9).
            elif not run_reviewer(state):
                audit("loop_reviewer_rejected_after_reflection", {"task_id": i}, pd, pn)
                # M-343c: pytest ist das letzte Wort.
                _last_errors = state.last_verify_errors or []
                # M-359: pytest gruen reicht NICHT, wenn der Patch
                # gar nicht angewendet wurde (old_string_not_found).
                # Dann ist der Task fail-closed.
                # K50-Bug-B: state.patches ist nur Builder-Output.
                # Es sagt NICHTS darueber, ob der Patch angewandt
                # wurde (loop_patch_old_string_not_found setzt
                # state.patches NICHT zurueck). Fail-closed nur,
                # wenn nachweislich kein Patch angewandt wurde:
                _hat_patch = _patches_wirklich_angewendet(state)
                # M-441: Divergenz-Check. Wenn der Reviewer in Runde 2
                # MEHR Bugs findet als in Runde 1, hat die Reflection
                # nichts geholfen — fail-closed, keine dritte Runde.
                _bugs_runde2 = len(state.reviewer_bugs or [])
                if _bugs_runde2 > _bugs_runde1:
                    audit("loop_reviewer_divergenz",
                          {"task_id": i,
                           "bugs_runde1": _bugs_runde1,
                           "bugs_runde2": _bugs_runde2}, pd, pn)
                    _task_ende(state, phase_state, task_id, ok=False,
                               name=task_name,
                               failure="reviewer_divergenz")
                    # FIX AR 2026-10-31: continue statt return 1.
                    continue
                # M-399b: High-severity Bugs NIE ignorieren.
                _high_bugs = [
                    b for b in (state.reviewer_bugs or [])
                    if isinstance(b, dict) and b.get("severity") == "high"
                ]
                if _high_bugs:
                    audit("loop_reviewer_high_bug_fail_closed",
                          {"task_id": i, "high_bugs": len(_high_bugs)}, pd, pn)
                    _split_failure = "reviewer_high_bug"
                    _task_ende(state, phase_state, task_id, ok=False,
                               name=task_name, failure=_split_failure)
                    # FIX AR 2026-10-31: continue statt return 1.
                    continue
                elif not _last_errors and _hat_patch:
                    audit("loop_reviewer_reject_ignoriert",
                          {"task_id": i, "grund": "pytest gruen nach Reflection"}, pd, pn)
                elif not _last_errors and not _hat_patch:
                    audit("loop_reviewer_reject_fail_closed",
                          {"task_id": i, "grund": "kein_patch_angewendet"}, pd, pn)
                    _task_ende(state, phase_state, task_id, ok=False, name=task_name, failure="reviewer_rejected_no_patch")
                    # FIX AR 2026-10-31: continue statt return 1.
                    continue
                else:
                    _task_ende(state, phase_state, task_id, ok=False, name=task_name, failure="reviewer_rejected_after_reflection")
                    continue
            audit("loop_reviewer_approved_after_reflection", {"task_id": i}, pd, pn)

        # OP-064a-Live-Fix (2026-11-01, HR-24): Spec-Widerspruch aus
        # reflection.py ist ein deterministisches Signal und darf NICHT
        # zu task_ok fuehren — egal welcher Pfad (reviewer-approved
        # oder reflection-durch). Der Erfolgs-Pfad ist die einzige
        # Stelle, an der _task_ende(ok=True) gerufen wird; dieser
        # Guard sitzt genau davor. Live-Beleg Testrunde #4 (19:10):
        # _refl_ok=True, _rev_ok=True, spec_widerspruch=True, aber
        # loop_task_ok + status=done.
        if state.spec_widerspruch_erkannt:
            audit("loop_task_spec_widerspruch_veto",
                  {"task_id": i,
                   "grund": "spec_widerspruch_vermutet",
                   "schicht": "pipeline"}, pd, pn)
            state.spec_widerspruch_erkannt = False
            phase_state.mark_vetoed(
                task_id, grund="spec_widerspruch_vermutet",
            )
            _task_ende(state, phase_state, task_id,
                       ok=False, name=task_name,
                       human_review=True,
                       failure="spec_widerspruch_vermutet")
            continue

        # OP-064b: Antipattern-Scanner (deterministisch, kein LLM).
        # Greift im Erfolgs-Pfad nach OP-064a. Ein Patch mit
        # # type: ignore / noqa / eslint-disable / || true / geloeschtem
        # Test wuerde das Verify-Gate umgehen — auch wenn Verify
        # (durch das Muster selbst) gruen meldet. Veto statt
        # task_ok. Referenz: fakegreen, Harn Completion-Gate.
        _ap_treffer = scan_patches(
            list(state.patches or [])
        )
        if _ap_treffer:
            audit("loop_task_antipattern_veto",
                  {"task_id": i,
                   "anzahl": len(_ap_treffer),
                   "kinds": [a.kind for a in _ap_treffer[:5]],
                   "files": [a.file for a in _ap_treffer[:5]]},
                  pd, pn)
            _ap_grund = f"antipattern:{_ap_treffer[0].kind}"
            phase_state.mark_vetoed(task_id, grund=_ap_grund)
            _task_ende(state, phase_state, task_id,
                       ok=False, name=task_name,
                       human_review=True,
                       failure=_ap_grund)
            continue

        _el_task = time.monotonic() - _t_task
        task_ok(i, len(tasks), elapsed_s=_el_task)
        try:
            task_done(i, len(tasks), task_name, elapsed_s=_el_task, ok=True)
        except Exception:
            pass
        group_end()
        tasks_ok += 1
        state.tasks_ok_counter = tasks_ok
        _audit_task_ok(
            _task_ende(state, phase_state, task_id, ok=True, name=task_name),
            task_id, task_name, pd, pn,
        )

    return 0, tasks_ok, tasks
