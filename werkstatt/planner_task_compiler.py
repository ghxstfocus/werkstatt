"""Compile Planner-Split output into a validated task graph."""
from __future__ import annotations

from typing import Any, cast

from werkstatt.task_graph import TaskGraphError


def run_planner_split_pipeline(
    prosa: str, key_files: list[str], api_key: str, pd, pn,
    aufgabe: str = "",
    state=None,
    gate_feedback: dict | None = None,
    preserve_criteria: list[str] | None = None,
    *,
    services: object,
) -> list[dict]:
    """Compile a role response into a verified, ordered task graph."""
    service = cast(Any, services)
    audit = service.audit
    _compose_planner_prompt_sections = service._compose_planner_prompt_sections
    _planner_split_context_fits = service._planner_split_context_fits
    PLANNER_SPLIT_SYSTEM = service.PLANNER_SPLIT_SYSTEM
    ask_llm = service.ask_llm
    _with_spinner = service._with_spinner
    _parse_json_robust = service._parse_json_robust
    _extrahiere_prosa_abschnitt = service._extrahiere_prosa_abschnitt
    _segmentiere_nach_pfad = service._segmentiere_nach_pfad
    _validate_criteria_coverage = service._validate_criteria_coverage
    _llm_split_einzel_task = service._llm_split_einzel_task
    _normalisiere_task_files = service._normalisiere_task_files
    _cap_task_files = service._cap_task_files
    _korrigiere_aktion = service._korrigiere_aktion
    _korrigiere_aktion_sequenziell = service._korrigiere_aktion_sequenziell
    _merge_mini_tasks = service._merge_mini_tasks
    _leite_deps_deterministisch = service._leite_deps_deterministisch
    _topo_sort_tasks = service._topo_sort_tasks
    _doku_post_check = service._doku_post_check
    _validate_read_task_scopes = service._validate_read_task_scopes
    from werkstatt.roles.planner_split import build_planner_split_prompt

    _split_prompt = build_planner_split_prompt(
        goal=aufgabe,
        architect_prose=prosa,
        key_files=key_files,
        skills_block=(
            state.planner_skills_block or "" if state is not None else ""
        ),
        scout_report=(
            getattr(state, "scout_auftrag", None)
            if state is not None else None
        ),
        architect_source_manifest=(
            getattr(state, "architect_scout_source_manifest", {})
            if state is not None else {}
        ),
        project_dir=pd,
        project_name=pn,
        gate_feedback=gate_feedback,
        preserve_criteria=preserve_criteria,
        compose_sections=_compose_planner_prompt_sections,
        fits_check=_planner_split_context_fits,
        audit_call=audit,
    )
    if _split_prompt is None:
        return []
    _user = _split_prompt.user_prompt
    section_manifest = _split_prompt.sections
    source_context = _split_prompt.source_context
    source_manifest = _split_prompt.source_evidence
    from werkstatt.roles.planner_split import (
        PlannerSplitInput,
        build_context_manifest,
        run_planner_split_role,
    )

    _split_manifest = build_context_manifest(
        system_prompt=PLANNER_SPLIT_SYSTEM,
        user_prompt=_user,
        key_files=key_files,
        source_evidence=source_manifest,
        source_context=source_context,
        sections=section_manifest,
    )
    _split_result = run_planner_split_role(
        PlannerSplitInput(
            api_key=api_key,
            system_prompt=PLANNER_SPLIT_SYSTEM,
            user_prompt=_user,
            state=state,
            context_manifest=_split_manifest,
        ),
        # Keep the compatibility seams used by run replay and existing tests;
        # the role runner itself owns call parameters and payload validation.
        ask_llm_call=ask_llm,
        spinner_call=_with_spinner,
    )
    if not _split_result.ok:
        audit("planner_split_llm_fehler", {"fehler": _split_result.error}, pd, pn)
        return []
    raw = _split_result.content
    parsed = _parse_json_robust(raw)
    if parsed is None:
        audit("planner_split_json_fehler", {"raw": raw[:200]}, pd, pn)
        return []
    criteria_raw = parsed.get("akzeptanzkriterien", [])
    if not isinstance(criteria_raw, list):
        raise TaskGraphError("Akzeptanzkriterien muessen eine Liste sein.")
    if any(not isinstance(item, str) or not item.strip() for item in criteria_raw):
        raise TaskGraphError(
            "Akzeptanzkriterien muessen nichtleere Texte sein; "
            "ungueltige Kriterien werden nicht verworfen."
        )
    criteria = list(dict.fromkeys(item.strip() for item in criteria_raw))
    if not criteria:
        raise TaskGraphError("Der Planner-Split lieferte keine Akzeptanzkriterien.")
    if preserve_criteria is not None and criteria != preserve_criteria:
        raise TaskGraphError(
            "Der Recovery-Split hat freigegebene Akzeptanzkriterien veraendert."
        )
    if state is not None:
        state.akzeptanzkriterien = criteria
    tasks_raw = parsed.get("tasks", [])
    if not isinstance(tasks_raw, list):
        return []
    tasks: list[dict] = []
    for i, t in enumerate(tasks_raw, 1):
        if not isinstance(t, dict):
            continue
        _start = t.get("architect_start") or ""
        _ende = t.get("architect_ende") or ""
        # M-461: Woertlichen Prosa-Abschnitt extrahieren.
        _abschnitt = _extrahiere_prosa_abschnitt(prosa, _start, _ende)
        # GOLD: Wenn architect_start fehlt (Gold-Architect liefert
        # "## <pfad>"-Ueberschriften), deterministisch segmentieren.
        if not _abschnitt and not _start:
            _tf = t.get("task_files") or []
            _ziel = _tf[0] if _tf else ""
            if _ziel:
                for _seg in _segmentiere_nach_pfad(prosa):
                    if _seg["datei"] == _ziel or _seg["datei"].endswith("/" + _ziel) or _ziel.endswith(_seg["datei"]):
                        _abschnitt = _seg["prosa"]
                        break
        if not _abschnitt:
            # M-463: Fallback: Task-Name + Description, NICHT ganze Prosa.
            _name = t.get("name") or ""
            _desc = t.get("description") or ""
            _abschnitt = f"## TASK: {_name}\n{_desc}" if _desc else _name
        tasks.append({
            "id": t.get("id") or f"t{i}",
            "name": t.get("name") or f"Sub-Task {i}",
            "action": t.get("action", "update"),
            "task_files": t.get("task_files") or [],
            "dependencies": t.get("dependencies") or [],
            "criterion_refs": t.get("criterion_refs") or [],
            "description": _abschnitt,
        })
    _validate_criteria_coverage(tasks, criteria)
    # M-469: Rekursive Zerlegung (ADaPT). Tasks > 2500 Zeichen (K19b).
    # werden neu zerlegt (max 2 Ebenen tief).
    _final: list[dict] = []
    import re as _re_470
    for t in tasks:
        _desc = t.get("description", "")
        # K11: Tiefe und Komplexitaetsmetriken fuer den Haupt-Task.
        # Vorher waren die Tiefe, Schritte und Bullets
        # '_komplexitaet' undefiniert -> NameError >2000 Zeichen.
        _tiefe = int(t.get("split_tiefe", 0) or 0)
        _schritte = len(_re_470.findall(
            r"^\s*\d+\.", _desc, _re_470.MULTILINE
        ))
        _bullets = len(_re_470.findall(
            r"^\s+-\s", _desc, _re_470.MULTILINE
        ))
        _komplexitaet = _schritte + _bullets
        # M-472: On-Demand-Zerlegung (ADaPT). Keine praeventive
        # Komplexitaetspruefung mehr. Nur Sicherheitsnetz: > 2000 Zeichen.
        _zu_gross = len(_desc) > 2500
        if not _zu_gross or _tiefe >= 2:
            _final.append(t)
        else:
            audit("planner_task_zu_gross",
                  {"id": t.get("id"),
                   "desc_len": len(_desc),
                   "schritte": _schritte,
                   "bullets": _bullets,
                   "komplexitaet": _komplexitaet,
                   "tiefe": _tiefe}, pd, pn)
            _sub = _llm_split_einzel_task(prosa, t, api_key, pd, pn, state=state)
            if _sub:
                for _st in _sub:
                    _st_desc = _st.get("description", "")
                    _st_schritte = len(_re_470.findall(
                        r"^\s*\d+\.", _st_desc, _re_470.MULTILINE
                    ))
                    _st_bullets = len(_re_470.findall(
                        r"^\s+-\s", _st_desc, _re_470.MULTILINE
                    ))
                    _st_komplex = _st_schritte + _st_bullets
                    # K19b: 2500 statt 800 -- konsistent mit K15c.
                    _st_gross = len(_st_desc) > 2500 or _st_komplex > 4
                    if not _st_gross or _tiefe + 1 >= 2:
                        _final.append(_st)
                    else:
                        _sub2 = _llm_split_einzel_task(prosa, _st, api_key, pd, pn, state=state)
                        _final.extend(_sub2 or [_st])
            else:
                _final.append(t)

    # Recursive on-demand splits may remove IDs still referenced downstream.
    from werkstatt.task_graph import remap_dependencies_to_split_leaves
    _final = remap_dependencies_to_split_leaves(_final)

    # K61a: task_files normalisieren (Dateiname -> voller Pfad).
    # Vor K20, damit _korrigiere_aktion auf korrekten Pfaden arbeitet.
    _final = _normalisiere_task_files(
        _final, {"key_files": key_files}, pd, pn,
    )
    # OP-186: Defense-in-Depth gegen Zieldatei-Explosion.
    _final = _cap_task_files(_final, pd, pn)
    # K20: Action anhand Datei-Existenz korrigieren (vor Merge).
    for _t_korr in _final:
        if isinstance(_t_korr, dict):
            _korrigiere_aktion(_t_korr, pd, pn)
    # K20b: Sequentiell -- create auf Datei, die ein frueherer
    # Task bereits anlegt -> update.
    _korrigiere_aktion_sequenziell(_final, pd, pn)

    # K36: Vor-Merge-State loggen.
    audit("planner_split_vor_merge", {
        "anzahl": len(_final),
        "tasks": [
            {"id": t.get("id"), "name": t.get("name"),
             "files": t.get("task_files"), "action": t.get("action"),
             "desc_len": len(t.get("description", ""))}
            for t in _final if isinstance(t, dict)
        ],
    }, pd, pn)

    # K15a: deterministischer Merge benachbarter Mini-Tasks.
    _vor_merge = len(_final)
    _final = _merge_mini_tasks(_final)
    if len(_final) != _vor_merge:
        audit("planner_split_merged",
              {"vorher": _vor_merge, "nachher": len(_final)},
              pd, pn)

    # OP-163b: Dep-Extraktion aus Architect-Block 5 (Vorrang)
    # oder task_files-Heuristik (Fallback).
    _final = _leite_deps_deterministisch(_final, prosa, pd, pn)
    # OP-175 A: Topo-Sort, damit Task-Reihenfolge zu deps passt.
    _final = _topo_sort_tasks(_final, pd, pn)

    audit("planner_split", {"anzahl": len(_final), "tasks": [
        {"id": t["id"], "files": t["task_files"],
         "deps": t.get("dependencies") or [],
         "desc_len": len(t.get("description", ""))} for t in _final
    ]}, pd, pn)
    _checked = _doku_post_check(_final, prosa, pd, pn, aufgabe)
    _validate_criteria_coverage(_checked, criteria)
    _validate_read_task_scopes(_checked, pd)
    return _checked
