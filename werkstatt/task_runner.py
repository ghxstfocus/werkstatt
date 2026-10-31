"""Task-Runner-Helfer (Fix AZ Stufe 7, 2026-10-31).

Extrahiert aus loop.py. Re-Export in loop.py erhaelt API-
Kompatibilitaet (Tests patchen werkstatt.loop._task_ende,
_pruefe_prior_failed_dependency).
"""
from __future__ import annotations

import re
import subprocess
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


def _task_ende(
    state: RunState,
    phase_state,
    task_id: str,
    *,
    ok: bool,
    name: str = "",
    failure: str | None = None,
    dateien: list[str] | None = None,
) -> None:
    """M-307b (A1): zentrale Task-Ende-Behandlung.

    Kapselt mark_done/mark_failed + progress.append in EINEM
    Aufruf, damit nicht 9 Stellen einzeln gepflegt werden muessen.
    Fail-open bei progress.append (A2, Ereignis-Log, kein Gate).
    """
    from werkstatt import progress as _progress

    pd = getattr(state, "project_dir", None)
    if ok:
        phase_state.mark_done(task_id)
        if pd is not None:
            _progress.append(
                pd,
                name=name or task_id,
                status="done",
                dateien=dateien,
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
        if pd is not None:
            _progress.append(
                pd,
                name=name or task_id,
                status="failed",
                dateien=dateien,
                info=failure,
            )


def _split_task_on_demand(
    state: RunState, task_id: str,
    phase_state=None,
) -> bool:
    """M-472: Zerlegt eine fehlgeschlagene Task in Sub-Tasks (ADaPT).

    Nur wenn die Task noch nicht zu tief zerlegt ist (max 2 Ebenen).
    Abgeschlossene Tasks bleiben unveraendert.
    """
    from werkstatt.planner import _llm_split_einzel_task
    from werkstatt.phase_state import PhaseState

    pd = state.project_dir
    pn = state.project_name
    api_key = getattr(state, "api_key", "")

    # Task finden.
    _task = None
    for t in (getattr(state, "tasks", None) or []):
        if isinstance(t, dict) and t.get("id") == task_id:
            _task = t
            break
    if _task is None:
        return False

    # Tiefe pruefen (max 2).
    _tiefe = _task.get("split_tiefe", 0)
    if _tiefe >= 2:
        audit("loop_split_max_tiefe", {"task_id": task_id}, pd, pn)
        # K38b: Grund merken, damit Aufrufer korrektes failure setzt.
        state.split_failure_grund = "split_max_tiefe"  # type: ignore[attr-defined]
        return False

    # K43a/K44a: ADaPT nur bei WIRKLICH grossen Tasks (> 2500 Zeichen).
    # K43a-Schwelle 1500 war zu niedrig: t2 (Service-Methode + Validierung,
    # ~2000 Zeichen) wurde in 3 Subtasks gesplittet, t2_b nochmal in 3 --
    # mit Doppelung ("Route+Template" als Subtask, obwohl eigener Task).
    # K15c sagt: 50-150 Zeilen Code = ~1000-1800 Zeichen. Bei 2500 ist
    # der Task ~200+ Zeilen -- dann ist ADaPT sinnvoll.
    _desc_len = len(_task.get("description", ""))
    if _desc_len < 2500:
        audit("loop_split_skip_klein",
              {"task_id": task_id, "desc_len": _desc_len}, pd, pn)
        return False

    # Fehler-Kontext.
    _errors = getattr(state, "last_verify_errors", None) or []
    _bugs = getattr(state, "reviewer_bugs", None) or []
    _prosa = getattr(state, "architect_prosa", "") or ""

    # Sub-Tasks vom LLM.
    _sub = _llm_split_einzel_task(
        _prosa, _task, api_key, pd, pn,
    )
    if not _sub:
        audit("loop_split_fehler", {"task_id": task_id}, pd, pn)
        return False

    # K26: NUTZE die uebergebene phase_state (statt eigene Instanz).
    _ps = phase_state
    if _ps is None:
        _ps = PhaseState(pn, base_dir=Path(pd) / ".werkstatt")
        if _ps.exists():
            _ps.load()
    _existing = _ps.get_task(task_id)
    if _existing and _existing.get("status") == "split":
        audit("loop_split_bereits_erledigt", {"task_id": task_id}, pd, pn)
    else:
        _ps.split_task(task_id, _sub)

    # state.tasks: Sub-Tasks an Position von _task einfuegen.
    _tasks = list(getattr(state, "tasks", []) or [])
    _idx = -1
    for i, t in enumerate(_tasks):
        if isinstance(t, dict) and t.get("id") == task_id:
            _idx = i
            break
    if _idx >= 0:
        for j, st in enumerate(_sub):
            st["split_tiefe"] = _tiefe + 1
            _tasks.insert(_idx + 1 + j, st)
        state.tasks = _tasks  # type: ignore[attr-defined]

    audit("loop_task_split",
          {"task_id": task_id,
           "anzahl_sub": len(_sub),
           "sub_ids": [st.get("id") for st in _sub],
           "tiefe": _tiefe + 1}, pd, pn)
    return True


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
    _curr_files = set(
        f for f in (_curr.get("task_files") or [])
        if isinstance(f, str) and f
    )
    if not _curr_files:
        return False, []
    for _t in _tasks[:_idx_curr]:
        if not isinstance(_t, dict):
            continue
        if _t.get("status") != "failed":
            continue
        _prior_files = set(
            f for f in (_t.get("task_files") or [])
            if isinstance(f, str) and f
        )
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
    '_split_task_on_demand',
    '_task_ende',
]
