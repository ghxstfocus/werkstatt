"""Task-Runner-Helfer (Fix AZ Stufe 7, 2026-10-31).

Extrahiert aus loop.py. Re-Export in loop.py erhaelt API-
Kompatibilitaet (Tests patchen werkstatt.loop._task_ende,
_pruefe_prior_failed_dependency).
"""
from __future__ import annotations

from pathlib import Path

from werkstatt.state import RunState


def audit(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop.audit."""
    from werkstatt.loop import audit as _orig
    return _orig(*args, **kwargs)


def _verify_patches(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop._verify_patches."""
    from werkstatt.loop import _verify_patches as _orig
    return _orig(*args, **kwargs)


def run_planner(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop.run_planner."""
    from werkstatt.loop import run_planner as _orig
    return _orig(*args, **kwargs)


def _hat_op_nnn(state) -> bool:
    """OP-063: True, wenn state.aufgabe ein OP-NNN nennt.

    Dann uebernimmt _committe_zielprojekt die PROGRESS-Doku als
    einzige Quelle (HARD-RULE 12). _task_ende schreibt dann keinen
    eigenen Eintrag, sonst entstehen pro Task leere Bloecke.
    """
    import re as _re
    _auf = state.aufgabe or ""
    return bool(_re.search(r"\bOP-\d{3}[a-z]?\d*\b", _auf))


def _task_ende(
    state: RunState,
    phase_state,
    task_id: str,
    *,
    ok: bool,
    name: str = "",
    failure: str | None = None,
    dateien: list[str] | None = None,
    human_review: bool = False,
) -> bool:
    """M-307b (A1): zentrale Task-Ende-Behandlung.

    Kapselt mark_done/mark_failed + progress.append in EINEM
    Aufruf, damit nicht 9 Stellen einzeln gepflegt werden muessen.
    Fail-open bei progress.append (A2, Ereignis-Log, kein Gate).
    """
    from werkstatt import progress as _progress

    # OP-040: Idempotenz-Guard. Schutz vor mehrfachen Aufrufen im
    # selben Task-Durchlauf (Live-Beleg 2026-10-31: patch_write_failed
    # + reviewer_rejected_no_patch in derselben Sekunde, derselbe Task,
    # weil zwischen zwei Fehlerpfaden ein `continue` fehlte).
    #
    # Wenn der Task schon done/failed ist, wird der zweite Aufruf
    # uebersprungen und ein Audit-Event geschrieben. `split` ist
    # KEIN Endstatus (Parent wird durch Kinder abgeschlossen),
    # `pending`/`running` sind Zwischenzustaende.
    _existing = None
    try:
        if phase_state is not None:
            _existing = phase_state.get_task(task_id)
    except Exception:
        _existing = None
    if _existing and _existing.get("status") in (
            "done", "failed", "human_review"):
        audit(
            "loop_task_ende_skip",
            {"task_id": task_id,
             "status": _existing.get("status"),
             "new_ok": ok,
             "new_failure": failure or "unknown"},
            getattr(state, "project_dir", None),
            getattr(state, "project_name", "?"),
        )
        return False

    pd = getattr(state, "project_dir", None)
    # OP-064a-Live-Fix (2026-11-01): Spec-Widerspruch aus reflection.py
    # in Sticky-Veto uebersetzen. Der Haupt-Fix sitzt im Caller
    # (pipeline_phases._phase_tasks_loop, vor _task_ende(ok=True)) —
    # damit loop_task_ok nicht auditiert wird. Dieser Guard ist die
    # defensive Schicht: jeder direkte _task_ende(ok=True)-Aufruf
    # landet hier und wird zum human_review statt mark_done.
    # Live-Beleg Testrunde #4 (19:10): _refl_ok=True, _rev_ok=True,
    # spec_widerspruch=True, aber loop_task_ok + status=done.
    if state.spec_widerspruch_erkannt:
        audit("loop_task_spec_widerspruch_veto",
              {"task_id": task_id, "ok": ok, "schicht": "task_ende"},
              getattr(state, "project_dir", None),
              getattr(state, "project_name", "?"))
        state.spec_widerspruch_erkannt = False
        if hasattr(phase_state, "mark_vetoed"):
            phase_state.mark_vetoed(
                task_id, grund="spec_widerspruch_vermutet",
            )
        if hasattr(phase_state, "mark_human_review"):
            phase_state.mark_human_review(
                task_id, grund="spec_widerspruch_vermutet",
            )
        return False
    # OP-064a: Sticky-Veto respektieren. Wenn vetoed und ok=True:
    # kein mark_done, stattdessen human_review.
    # Defensiv: nur echte PhaseState-Instanzen fragen (MagicMock in
    # Tests wuerde sonst truthy zurueckgeben).
    _vetoed = False
    if phase_state is not None and hasattr(phase_state, "ist_vetoed"):
        try:
            _res = phase_state.ist_vetoed(task_id)
            # `is True` schuetzt gegen MagicMock (truthy Return ohne bool)
            _vetoed = _res is True
        except Exception:
            _vetoed = False
    if _vetoed and ok:
        audit("loop_task_veto_respected",
              {"task_id": task_id},
              getattr(state, "project_dir", None),
              getattr(state, "project_name", "?"))
        phase_state.mark_human_review(
            task_id, grund="veto_nicht_aufgehoben",
        )
        return False
    if human_review:
        # OP-060b: human_review ist Endstatus, kein done/failed.
        phase_state.mark_human_review(
            task_id, grund=failure or "unknown",
        )
        return False
    if ok:
        phase_state.mark_done(task_id)
        if hasattr(phase_state, "criteria_progress"):
            try:
                _criterion_progress = phase_state.criteria_progress()
                if (
                    isinstance(_criterion_progress, dict)
                    and _criterion_progress.get("tracked") is True
                ):
                    _next_task = None
                    try:
                        _candidate = phase_state.get_next_task()
                        if isinstance(_candidate, dict):
                            _next_task = _candidate
                    except Exception:
                        _next_task = None
                    _next_task_id = (
                        str(_next_task.get("id") or "").strip()
                        if _next_task else ""
                    )
                    _next_task_name = (
                        str(_next_task.get("name") or "").strip()
                        if _next_task else ""
                    )
                    if _next_task_id:
                        _next_step_type = "task"
                        _next_step = (
                            f"Weiter mit {_next_task_id}"
                            + (f": {_next_task_name}" if _next_task_name else "")
                        )
                        _decision = (
                            "Offene Kriterien bleiben im freigegebenen Task-Graph; "
                            "der naechste ausfuehrbare Task wird fortgesetzt."
                        )
                    else:
                        try:
                            _all_tasks_done = phase_state.is_complete() is True
                        except Exception:
                            _all_tasks_done = False
                        if _all_tasks_done:
                            _next_step_type = "phase_end_verify"
                            _next_step = "Phase-End-Verify ausfuehren"
                            _decision = (
                                "Der Task-Graph ist abgeschlossen; jetzt wird "
                                "das Gesamtziel mit der Abschlusspruefung belegt."
                            )
                        else:
                            _next_step_type = "resolve_open_tasks"
                            _next_step = (
                                "Offene oder blockierte Tasks und Abhaengigkeiten klaeren"
                            )
                            _decision = (
                                "Kein weiterer Task ist ausfuehrbar; offene "
                                "Abhaengigkeiten muessen vor dem Abschluss geklaert werden."
                            )
                    _goal = str(
                        getattr(phase_state, "data", {}).get("aufgabe")
                        or getattr(state, "aufgabe", "")
                    ).strip()
                    _criteria_text = getattr(phase_state, "data", {}).get(
                        "akzeptanzkriterien", [],
                    )
                    _criteria_by_id = {
                        f"AC{index}": str(text).strip()
                        for index, text in enumerate(_criteria_text, 1)
                        if isinstance(text, str) and text.strip()
                    } if isinstance(_criteria_text, list) else {}
                    _checkpoint_evidence = [
                        f"Task {task_id} als done gespeichert",
                    ]
                    if _goal:
                        _checkpoint_evidence.append(f"Ziel: {_goal[:160]}")
                    for _criterion_id in _criterion_progress.get("covered", []):
                        if len(_checkpoint_evidence) >= 5:
                            break
                        _criterion_text = _criteria_by_id.get(
                            str(_criterion_id), "",
                        )
                        _checkpoint_evidence.append(
                            f"Erfuellt: {_criterion_id}"
                            + (f" — {_criterion_text[:120]}" if _criterion_text else "")
                        )
                    for _criterion_id in _criterion_progress.get("uncovered", []):
                        if len(_checkpoint_evidence) >= 5:
                            break
                        _criterion_text = _criteria_by_id.get(
                            str(_criterion_id), "",
                        )
                        _checkpoint_evidence.append(
                            f"Offen: {_criterion_id}"
                            + (f" — {_criterion_text[:120]}" if _criterion_text else "")
                        )
                    _task_rows = getattr(phase_state, "data", {}).get("tasks", [])
                    _open_tasks = [
                        item for item in _task_rows
                        if isinstance(item, dict)
                        and item.get("status") not in ("done", "split")
                    ] if isinstance(_task_rows, list) else []
                    if _open_tasks and len(_checkpoint_evidence) < 5:
                        _open_labels = [
                            f"{(item.get('id') or '?')!s}: "
                            f"{(item.get('status') or '?')!s}"
                            for item in _open_tasks[:3]
                        ]
                        _checkpoint_evidence.append(
                            "Restlicher Graph: " + ", ".join(_open_labels)
                            + (f" (+{len(_open_tasks) - 3})" if len(_open_tasks) > 3 else "")
                        )
                    audit(
                        "loop_criteria_progress",
                        {
                            "task_id": task_id,
                            "status": (
                                "complete"
                                if _criterion_progress.get("valid") is True
                                and not _criterion_progress.get("uncovered")
                                else "in_progress"
                            ),
                            "covered": _criterion_progress.get("covered", []),
                            "remaining": _criterion_progress.get("uncovered", []),
                            "error": _criterion_progress.get("error"),
                            "next_step_type": _next_step_type,
                            "next_task_id": _next_task_id or None,
                            "next_step": _next_step,
                            "decision_summary": _decision,
                            "evidence": _checkpoint_evidence,
                        },
                        pd,
                        getattr(state, "project_name", "?"),
                    )
            except Exception as exc:
                # Der Task bleibt done, aber ein fehlender Zielabgleich darf
                # nicht unsichtbar bleiben. Keine Exception-Texte persistieren.
                try:
                    audit(
                        "loop_criteria_checkpoint_failed",
                        {
                            "task_id": task_id,
                            "error_type": type(exc).__name__,
                            "next_step": (
                                "Kriterienfortschritt am naechsten sicheren "
                                "Checkpoint erneut pruefen"
                            ),
                        },
                        pd,
                        getattr(state, "project_name", "?"),
                    )
                except Exception:
                    # Der Taskabschluss bleibt unangetastet, auch wenn der
                    # Audit-Store selbst nicht verfuegbar ist.
                    pass
        if pd is not None and not _hat_op_nnn(state):
            _progress.append(
                pd,
                name=name or task_id,
                status="done",
                dateien=dateien,
                run_id=getattr(state, "run_id", None),
            )
    else:
        phase_state.mark_failed(task_id, failure=failure or "unknown")
        # FIX AE 2026-10-31: Eigene Spur in .werkstatt/abbrueche.jsonl.
        # Ueberlebt Rollback (untracked), strukturiert durchsuchbar.
        if pd is not None:
            try:
                import json as _json_ae
                from datetime import UTC as _UTC_ae
                from datetime import datetime as _dt_ae
                _abr = Path(pd) / ".werkstatt" / "abbrueche.jsonl"
                _abr.parent.mkdir(parents=True, exist_ok=True)
                with _abr.open("a", encoding="utf-8") as _fh_ae:
                    _fh_ae.write(_json_ae.dumps({
                        "ts": _dt_ae.now(_UTC_ae).isoformat(
                            timespec="seconds"),
                        "task_id": task_id,
                        "name": name or "",
                        "failure": failure or "unknown",
                        "dateien": list(dateien or []),
                    }, ensure_ascii=True) + "\n")
            except (OSError, TypeError):
                pass
        if pd is not None and not _hat_op_nnn(state):
            _progress.append(
                pd,
                name=name or task_id,
                status="failed",
                dateien=dateien,
                info=failure,
                run_id=getattr(state, "run_id", None),
            )
    return bool(ok)


def _pruefe_prior_failed_dependency(
    phase_state, task_id: str,
) -> tuple[bool, list[str]]:
    """FIX AP 2026-10-31: Prueft, ob ein frueherer Task auf derselben
    Datei failed ist.

    Live-Beleg 2026-10-31 10:36: t1 (create deepseek_client.py) failte
    am PreToolUse-Hook. t2-t4 sind update auf derselben Datei —
    der Builder findet die Datei nicht (builder_zieldatei_nicht_gefunden),
    Loop bricht bei t2 mit return 1 ab. t5-t14 (unabhaengig) werden
    nie versucht.

    Rueckgabe: (ist_dependency_failure, task_files)
    """
    if phase_state is None:
        return False, []
    try:
        _tasks = phase_state.data.get("tasks") or []
    except (AttributeError, TypeError):
        return False, []
    _curr = None
    _idx_curr = -1
    for _i, _t in enumerate(_tasks):
        if isinstance(_t, dict) and _t.get("id") == task_id:
            _curr = _t
            _idx_curr = _i
            break
    if _curr is None or _idx_curr <= 0:
        return False, []
    _curr_files = {
        f for f in (_curr.get("task_files") or [])
        if isinstance(f, str) and f
    }
    if not _curr_files:
        return False, []
    for _t in _tasks[:_idx_curr]:
        if not isinstance(_t, dict):
            continue
        if _t.get("status") != "failed":
            continue
        _prior_files = {
            f for f in (_t.get("task_files") or [])
            if isinstance(f, str) and f
        }
        if _curr_files & _prior_files:
            return True, sorted(_curr_files)
    return False, []


def _extract_files_from_tasks(tasks: list) -> list[str]:
    """M-299i + M-306b: Datei-Pfade aus Task-Beschreibungen extrahieren.

    Bevorzugt das task_files-Feld (deterministisch). Fallback:
    Regex auf Task-Text (Backward-Compat fuer alte Plaene).
    """
    import re as _re
    pattern = _re.compile(
        r'([a-zA-Z_][a-zA-Z0-9_/.-]*\.(?:md|py|yaml|yml|json|txt|toml|cfg|ini))'
    )
    files: list[str] = []
    for task_obj in tasks or []:
        # M-306b: task_files-Feld bevorzugen (deterministisch).
        if isinstance(task_obj, dict):
            tf = task_obj.get("task_files")
            if isinstance(tf, list):
                for f in tf:
                    if isinstance(f, str) and f not in files:
                        files.append(f)
                continue  # task_files da -> kein Regex-Fallback
        # Fallback: Regex auf Task-Text (Backward-Compat).
        text = task_obj if isinstance(task_obj, str) else str(task_obj)
        for f in pattern.findall(text):
            if f not in files:
                files.append(f)
    return files


__all__ = [
    '_extract_files_from_tasks',
    '_pruefe_prior_failed_dependency',
    '_task_ende',
]
