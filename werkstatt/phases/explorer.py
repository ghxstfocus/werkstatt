"""Tool-oriented project-context collection for checkpoint dispatch."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from werkstatt.phase_state import PhaseState
from werkstatt.render import (
    group_end,
    group_start,
    step,
)
from werkstatt.state import RunState

from ._common import (
    _validate_contract_safe,
    audit,
)


def _append_graphify_candidates(
    explorer_result: dict[str, Any],
    seen: set[str],
    candidates: object,
    search_terms: list[str],
    evidence_factory,
) -> int:
    """Use Graphify only for remaining source slots after direct retrieval."""
    key_files = explorer_result.get("key_files")
    if not isinstance(key_files, list) or not isinstance(candidates, list):
        return 0
    added = 0
    for candidate in candidates:
        if len(key_files) >= 5:
            break
        if not isinstance(candidate, dict):
            continue
        relative = candidate.get("file")
        if not isinstance(relative, str) or not relative or relative in seen:
            continue
        evidence = evidence_factory(
            relative,
            str(candidate.get("why") or "Graphify candidate"),
            "medium",
            6000,
            search_terms=search_terms,
        )
        seen.add(relative)
        key_files.append(evidence)
        added += 1
    return added


def _phase_project_context_tools(
    state: RunState,
    aufgabe: str,
    project_name: str,
    phase_state,
    *,
    preserve_failed_tasks: bool = False,
):
    """Collect deterministic project evidence before role selection.

    Setzt state.explorer_context. Rueckgabe: (rc, phase_state).
    rc=0 -> weiter mit Plan-Gate. rc=1 -> Loop-Abbruch (Preflight).
    """
    pd = state.project_dir
    pn = state.project_name
    debugger_fix = getattr(state, "debugger_fix_contract", None)
    if debugger_fix is not None:
        from werkstatt.debugger_handoff import DebuggerFix

        if not isinstance(debugger_fix, DebuggerFix):
            audit(
                "loop_debugger_fix_rejected",
                {"reason": "invalid_in_memory_contract"},
                pd,
                pn,
            )
            return 1, phase_state
        _explorer_request = " ".join((
            debugger_fix.signatur,
            *debugger_fix.betroffene_dateien,
        ))
        _explizite_dateien = list(debugger_fix.betroffene_dateien)
    else:
        _explorer_request = aufgabe

    # Read-only request path discovery. Explicit user paths stay pinned.
    import re as _re_explorer
    if debugger_fix is None:
        _explizite_dateien = _re_explorer.findall(
            r'\b([a-zA-Z_][a-zA-Z0-9_/]+\.(?:py|md|yaml|yml|json|toml|css|html|js))\b',
            _explorer_request,
        )

    # GOLD 2026-10-30: Suchbegriffe aus der Aufgabe extrahieren.
    # Excerpts use these terms to select relevant lines in large files.
    _suchbegriffe: list[str] = []
    # Backticks: `foo_bar`, `nth-child(n+4)` — volle Kette in Backticks
    for _m in _re_explorer.finditer(r'`([^`]{2,120})`', _explorer_request):
        _b = _m.group(1).strip()
        if _b:
            _suchbegriffe.append(_b)
    # CSS-Klassen mit table-Praefix: table-alerts, table-inventory
    for _m in _re_explorer.finditer(r'\b(table-[a-z][a-z0-9-]{1,40})\b', _explorer_request):
        _b = _m.group(1)
        if _b not in _suchbegriffe:
            _suchbegriffe.append(_b)
    # CSS-Selektoren in Klammern: nth-child(...) vollstaendig
    for _m in _re_explorer.finditer(r'(nth-child\([^)]{1,40}\))', _explorer_request):
        _b = _m.group(1)
        if _b not in _suchbegriffe:
            _suchbegriffe.append(_b)
    # Funktions-/Methoden-Namen mit Unterstrich (def foo_bar, foo_bar())
    for _m in _re_explorer.finditer(
            r'\b([a-z][a-z0-9]*_[a-z0-9_]{2,40})\b', _explorer_request):
        _b = _m.group(1)
        if _b not in _suchbegriffe:
            _suchbegriffe.append(_b)
    _suchbegriffe = _suchbegriffe[:20]
    audit("loop_explorer_suchbegriffe",
          {"anzahl": len(_suchbegriffe),
           "begriffe": _suchbegriffe[:10]}, pd, pn)
    # GOLD 2026-10-30: Wenn die Aufgabe nur einen Ordner nennt
    # (z.B. "apps/dashboard/static/css/"), finde die konkreten
    # Dateien im Ordner, die zu den Suchbegriffen passen.
    # Live-Beleg 2026-10-30 21:53: Aufgabe nannte "apps/dashboard/
    # static/css/" (Ordner), aber nicht "components.css". Der
    # Architect bekam deshalb keinen components.css-Inhalt.
    _ordner_dateien: list[str] = []
    for _m in _re_explorer.finditer(
            r'\b((?:[a-zA-Z_][a-zA-Z0-9_-]*/){2,}[a-zA-Z0-9_-]*/)\b',
            _explorer_request):
        _ordner = _m.group(1).rstrip("/")
        _dir = Path(pd) / _ordner
        if not _dir.is_dir():
            continue
        for _f in sorted(_dir.glob("*")):
            if not _f.is_file():
                continue
            _rel = str(_f.relative_to(pd))
            if _rel in _explizite_dateien or _rel in _ordner_dateien:
                continue
            # Nur Dateien, die einen Suchbegriff enthalten?
            # Wir fuegen alle hinzu — der Architect entscheidet.
            _ordner_dateien.append(_rel)
            if len(_ordner_dateien) >= 10:
                break
    # Ordner-Dateien an explizite Dateien anhaengen (max 10 gesamt)
    _alle_genannten: list[str] = [str(_p_g) for _p_g in _explizite_dateien]
    for _ord_f in _ordner_dateien:
        if _ord_f not in _alle_genannten:
            _alle_genannten.append(_ord_f)
    _alle_genannten = _alle_genannten[:10]

    # Adaptive role routing (OP-398 / ADR-0032): einen Explorer-LLM-Aufruf
    # einsparen, wenn der gleiche fail-closed Scout-Router ein enges,
    # explizites Einzeldatei-Aenderungsziel bestaetigt. Deterministische
    # Datei-/Verwandtschaftsbelege werden unten trotzdem aufgebaut. Breite,
    # diagnostische und mehrdeutige Auftraege bleiben im Explorer-Pfad.
    group_start("Kontext: Graphify und Quellen")
    _t_exp = time.monotonic()
    _skip_reason = "kein_deterministischer_literalplan"
    _skip_explorer = debugger_fix is not None
    if debugger_fix is not None:
        _skip_reason = "approved_debugger_diff_has_pinned_scope"
    elif len(_explizite_dateien) == 1:
        try:
            from werkstatt.planner import _scout_route_decision

            _candidate = _explizite_dateien[0]
            _scout_target, _skip_reason = _scout_route_decision(
                _explorer_request,
                {"key_files": [{"file": _candidate}]},
                pd,
            )
            _skip_explorer = _scout_target is not None
        except (ImportError, AttributeError, TypeError, ValueError):
            # Routing-Ausfall darf niemals einen Rollenaufruf unterdruecken.
            _skip_explorer = False
            _skip_reason = "routing_pruefung_nicht_verfuegbar"

    # Resolve related-file evidence before deciding whether the Explorer role
    # can be skipped. A failed scan is unknown context, never an empty result.
    _related_scan_status = "not_requested"
    _related_scan_error = ""
    _verwandte: list[str] = []
    if _explizite_dateien:
        try:
            from werkstatt.explorer import _verwandte_dateien as _vw

            _verwandte = _vw(Path(pd), _explizite_dateien)
            _related_scan_status = "complete"
        except Exception as exc:  # noqa: BLE001 - context loss must be recorded
            _related_scan_status = "failed"
            _related_scan_error = type(exc).__name__
            audit(
                "loop_explorer_related_files_failed",
                {
                    "reason": "related_file_scan_failed",
                    "exception_type": _related_scan_error,
                    "explicit_file_count": len(_explizite_dateien),
                },
                pd,
                pn,
            )
            if _skip_explorer:
                _skip_explorer = False
                _skip_reason = "related_file_scan_failed"

    # Project context is assembled with tools, not an Explorer model role.
    # Graphify and the source reader below provide navigation and current
    # hash-bound excerpts; deterministic measurements remain available as
    # evidence without paying for a separate exploratory LLM call.
    from werkstatt.explorer import _format_findings, _messen

    _measurements = _messen(_explorer_request, Path(pd))
    _measurement_files: list[dict[str, Any]] = []
    for _measurement_name, _measurement in _measurements.items():
        if _measurement_name == "migrations":
            continue
        for _measurement_path in _measurement.get("dateien", []):
            if (
                not isinstance(_measurement_path, str)
                or _measurement_path.endswith(".md")
                or _measurement_path.startswith("docs/")
            ):
                continue
            _measurement_files.append({
                "file": _measurement_path,
                "why": f"{_measurement_name}-Messung",
                "confidence": "high",
            })
    _explorer_ergaenzung = {
        "findings": _format_findings(_measurements) if _measurements else "",
        "key_files": _measurement_files,
        "next_reads": [item["file"] for item in _measurement_files],
    }
    audit("loop_explorer_ergaenzt", {
        "method": "deterministic_measurements_and_graphify",
        "measurement_count": len(_measurements),
        "measurement_file_count": len(_measurement_files),
        "explorer_model_calls": 0,
    }, pd, pn)
    _explorer_key = _explorer_ergaenzung.get("key_files") or []
    if not isinstance(_explorer_key, list):
        _explorer_key = []
    _explorer_retrieval = _explorer_ergaenzung.get("content_retrieval")
    if isinstance(_explorer_retrieval, dict):
        _retrieved_sources = _explorer_retrieval.get("selected_sources") or []
        for _source in _retrieved_sources:
            if not isinstance(_source, dict):
                continue
            _source_path = _source.get("file")
            if not isinstance(_source_path, str):
                continue
            _existing = next((
                item for item in _explorer_key
                if isinstance(item, dict) and item.get("file") == _source_path
            ), None)
            if _existing is None:
                _explorer_key.append({
                    "file": _source_path,
                    "why": _source.get("why") or "Inhaltstreffer",
                    "confidence": _source.get("confidence") or "medium",
                    "matched_terms": _source.get("matched_terms", []),
                    "retrieval_source_sha256": _source.get("source_sha256"),
                })
            elif isinstance(_existing, dict):
                _existing["retrieval_source_sha256"] = _source.get(
                    "source_sha256",
                )

    _seen: set[str] = set()
    _explorer_findings = _explorer_ergaenzung.get("findings", "")
    if _related_scan_status == "failed":
        _explorer_findings = (
            f"{_explorer_findings}\n\n" if _explorer_findings else ""
        ) + (
            "BELEG-LUECKE: Der Scan verwandter Dateien ist fehlgeschlagen "
            f"({_related_scan_error}). Nicht gefundene verwandte Quellen "
            "gelten als unbekannt und duerfen nicht als nicht vorhanden "
            "behandelt werden."
        )
    explorer_result: dict[str, Any] = {
        "findings": _explorer_findings,
        "key_files": [],
        "next_reads": list(_explorer_ergaenzung.get("next_reads") or []),
        "content_retrieval": _explorer_retrieval or {},
        "dispatch": {
            "role": "project_context_tools",
            "selected": "deterministic",
            "reason": "graphify_and_current_source_retrieval",
            "evidence_kind": (
                "explicit_source_read"
                if _explizite_dateien else "graph_navigation"
            ),
        },
        "related_files_scan": {
            "status": _related_scan_status,
            "explicit_file_count": len(_explizite_dateien),
            **({"error_type": _related_scan_error}
               if _related_scan_error else {}),
        },
    }
    def _file_evidence(
        file_path: str,
        why: str,
        confidence: str,
        char_limit: int,
        search_terms: list[str] | None = None,
    ) -> dict[str, Any]:
        from werkstatt.explorer import _datei_inhalt_mit_fundstellen

        evidence = _datei_inhalt_mit_fundstellen(
            Path(pd), file_path,
            suchbegriffe=(
                search_terms if search_terms is not None else _suchbegriffe
            ),
        )
        excerpt = str(evidence.get("text") or "")
        preview = excerpt[:char_limit]
        char_limited = len(excerpt) > char_limit
        return {
            "file": file_path,
            "why": why,
            "confidence": confidence,
            "preview": preview,
            "source_line_ranges": evidence.get("line_ranges", []),
            "source_total_lines": evidence.get("total_lines", 0),
            "source_complete": evidence.get("complete") is True
            and not char_limited,
            "preview_source_chars": len(excerpt),
            "source_sha256": evidence.get("source_sha256"),
        }

    for f in _alle_genannten[:8]:
        if f not in _seen:
            _seen.add(f)
            # GOLD 2026-10-30: Datei-Inhalt fuer den Architect.
            # Vorher hatte der Architect nur die API-Signaturen
            # (aus _baue_api_index), nicht den Ist-Zustand. Deshalb
            # plante er Aenderungen, die schon erledigt waren.
            # Live-Beleg 2026-10-30 21:44: alerts.html hatte schon
            # class="table table-alerts", der Architect plante
            # trotzdem einen Patch.
            explorer_result["key_files"].append(_file_evidence(
                f, "explizit in Aufgabe", "high", 12000,
            ))
    for f in _verwandte:
        if f not in _seen:
            _seen.add(f)
            explorer_result["key_files"].append(_file_evidence(
                f, "verwandt (M-396)", "medium", 6000,
            ))
    for k in _explorer_key:
        if isinstance(k, dict) and k.get("file") and k["file"] not in _seen:
            _explorer_path = str(k["file"]).replace("\\", "/")
            _retrieval_source_hash = k.get("retrieval_source_sha256")
            _evidence = _file_evidence(
                _explorer_path,
                str(k.get("why") or "Explorer-Vorschlag"),
                str(k.get("confidence") or "low"),
                6000,
                search_terms=(
                    k.get("matched_terms")
                    if isinstance(k.get("matched_terms"), list) else None
                ),
            )
            if (
                isinstance(_retrieval_source_hash, str)
                and _evidence.get("source_sha256") != _retrieval_source_hash
            ):
                audit(
                    "loop_explorer_grep_fallback",
                    {"file": _explorer_path, "result": "stale_source_rejected"},
                    pd, pn,
                )
                continue
            _seen.add(_explorer_path)
            explorer_result["key_files"].append(_evidence)
    # Retrieve matching source by content as a bounded supplement to path-only
    # Explorer results. Missing files/index entries remain unknown, not negative.
    from werkstatt.graphify_index import (
        graphify_candidates,
        refresh_graphify_index,
    )

    _graph_seeds = [
        str(item["file"])
        for item in explorer_result["key_files"]
        if isinstance(item, dict)
        and isinstance(item.get("file"), str)
        and item.get("source_complete") is True
        and isinstance(item.get("source_sha256"), str)
    ][:3]
    _graph_seed_sha256 = {
        str(item["file"]): str(item["source_sha256"])
        for item in explorer_result["key_files"]
        if isinstance(item, dict)
        and isinstance(item.get("file"), str)
        and item.get("source_complete") is True
        and isinstance(item.get("source_sha256"), str)
    }
    _graph_retrieval = graphify_candidates(
        Path(pd), _explorer_request + " " + " ".join(_suchbegriffe),
        limit=8,
        seed_paths=_graph_seeds,
        seed_sha256=_graph_seed_sha256,
    )
    _graph_refresh: dict[str, Any] | None = None
    if _graph_retrieval.get("status") in {
        "unavailable", "stale", "partial_stale", "invalid_index",
    }:
        _graph_refresh = refresh_graphify_index(Path(pd))
        if _graph_refresh.get("status") == "refreshed":
            _graph_retrieval = graphify_candidates(
                Path(pd), _explorer_request + " " + " ".join(_suchbegriffe),
                limit=8,
                seed_paths=_graph_seeds,
                seed_sha256=_graph_seed_sha256,
            )
    _graph_retrieval["refresh_attempted"] = _graph_refresh is not None
    explorer_result["graphify_retrieval"] = _graph_retrieval
    audit("loop_explorer_graphify", {
        "status": _graph_retrieval.get("status"),
        "retrieval_method": _graph_retrieval.get("retrieval_method"),
        "native_query_status": _graph_retrieval.get("native_query_status"),
        "native_node_count": _graph_retrieval.get("native_node_count", 0),
        "native_relationship_count": _graph_retrieval.get(
            "native_relationship_count", 0,
        ),
        "ignored_source_count": _graph_retrieval.get("ignored_source_count", 0),
        "refresh_status": _graph_refresh.get("status") if _graph_refresh else "not_needed",
        "candidate_count": len(_graph_retrieval.get("candidates") or []),
        "ast_symbol_count": sum(
            len(item.get("symbols") or [])
            for item in _graph_retrieval.get("candidates") or []
            if isinstance(item, dict)
        ),
        "relationship_count": sum(
            len(item.get("relationships") or [])
            for item in _graph_retrieval.get("candidates") or []
            if isinstance(item, dict)
        ),
        "stale_source_count": _graph_retrieval.get("stale_source_count", 0),
        "stale_relationship_count": _graph_retrieval.get(
            "stale_relationship_count", 0,
        ),
        "index_sha256": _graph_retrieval.get("index_sha256"),
        "seed_paths": _graph_retrieval.get("seed_paths", []),
    }, pd, pn)
    _graphify_primary = (
        _graph_retrieval.get("retrieval_method") == "graphify_cli_query"
        and _graph_retrieval.get("status") == "ok"
        and _graph_retrieval.get("stale_source_count", 0) == 0
    )

    def _add_graphify_candidates(selection_order: str) -> None:
        added = _append_graphify_candidates(
            explorer_result,
            _seen,
            _graph_retrieval.get("candidates") if _graph_retrieval else [],
            _suchbegriffe,
            _file_evidence,
        )
        if not added:
            return
        audit(
            "loop_explorer_graphify",
            {"status": _graph_retrieval.get("status"),
             "selection_order": selection_order,
             "selected_count": added,
             "candidate_count": len(
                 _graph_retrieval.get("candidates") or [],
             ),
             "ast_symbol_count": sum(
                 len(item.get("symbols") or [])
                 for item in _graph_retrieval.get("candidates") or []
                 if isinstance(item, dict)
             ),
             "relationship_count": sum(
                 len(item.get("relationships") or [])
                 for item in _graph_retrieval.get("candidates") or []
                 if isinstance(item, dict)
             ),
             "stale_relationship_count": _graph_retrieval.get(
                 "stale_relationship_count", 0,
             ),
             "index_sha256": _graph_retrieval.get("index_sha256")},
            pd, pn,
        )

    # Prefer Graphify only when its native query is available and the index
    # is fully current. The Werkstatt ranking fallback is weaker in the
    # checked-in retrieval evaluation, so direct content matches stay first.
    if _graphify_primary:
        _add_graphify_candidates("fresh_native_graphify_before_content_fallback")
    from werkstatt.explorer import _rank_source_files

    _source_matches: list[dict[str, Any]] = []
    _retrieval_manifest: dict[str, Any] = {}
    _retrieval_reused = (
        isinstance(_explorer_retrieval, dict)
        and _explorer_retrieval.get("index_scan_succeeded") is True
    )
    if len(explorer_result["key_files"]) < 5 and not _retrieval_reused:
        _source_matches, _retrieval_manifest = _rank_source_files(
            Path(pd), _explorer_request + " " + " ".join(_suchbegriffe),
            exclude=set(_seen),
            limit=5 - len(explorer_result["key_files"]),
        )
    if _retrieval_manifest:
        explorer_result["content_retrieval"] = _retrieval_manifest
    if not _source_matches and not _retrieval_reused:
        audit(
            "loop_explorer_grep_fallback",
            {"result": "no_specific_content_match",
             "retrieval": _retrieval_manifest},
            pd, pn,
        )
    for _match in _source_matches:
        _rel = str(_match["file"])
        _matched_terms = list(dict.fromkeys([
            *_suchbegriffe,
            *[
                str(term) for term in _match.get("matched_terms", [])
                if isinstance(term, str)
            ],
        ]))
        _seen.add(_rel)
        explorer_result["key_files"].append(_file_evidence(
            _rel,
            str(_match.get("why") or "Inhaltstreffer"),
            str(_match.get("confidence") or "medium"),
            6000,
            search_terms=_matched_terms,
        ))
        audit(
            "loop_explorer_grep_fallback",
            {"file": _rel,
             "begriffe": _match.get("matched_terms", []),
             "retrieval": _retrieval_manifest},
            pd, pn,
        )
    if not _graphify_primary:
        _add_graphify_candidates("after_current_content_fallback")

    audit("loop_explorer_ergaenzt",
          {"explizit": len(_explizite_dateien[:5]),
           "verwandt": len(_verwandte),
           "gesamt": len(explorer_result["key_files"]),
           "source_evidence": [
               {
                   "file": item.get("file"),
                   "line_ranges": item.get("source_line_ranges"),
                   "total_lines": item.get("source_total_lines"),
                   "complete": item.get("source_complete"),
                   "preview_chars": len(item.get("preview", "")),
                   "source_chars": item.get("preview_source_chars"),
                   "source_sha256": item.get("source_sha256"),
               }
               for item in explorer_result["key_files"]
               if isinstance(item, dict)
           ]},
          pd, pn)
    _el_exp = time.monotonic() - _t_exp
    if explorer_result.get("key_files"):
        step(1, "Projektkontext", f"{len(explorer_result['key_files'])} Dateien", elapsed_s=_el_exp)
        audit("loop_explorer_ok", {"files": len(explorer_result["key_files"])}, pd, pn)
    else:
        step(1, "Projektkontext", "0 Dateien", ok=False, elapsed_s=_el_exp)
        audit("loop_explorer_leer", {}, pd, pn)
    # Preserve the retrieval coverage even when it found no source file so
    # Scout can distinguish a bounded no-match from complete negative evidence.
    state.explorer_context = explorer_result
    group_end()

    # Required context contract before the planner can choose its next role.
    # Skip it only for resume and already-satisfied runs with existing tasks.
    _skip_explorer_check = (
        bool(getattr(state, "tasks", None))
        or state.auftrag_bereits_erfuellt
    )
    if (not _skip_explorer_check
            and not _validate_contract_safe(
                "project_context", "planner", state, pd, pn,
            )):
        return 1, phase_state

    # FIX AN 2026-10-31: Schreibrechte-Preflight fuer Task-Dateien.
    # Live-Beleg 2026-10-31 10:31 t2: git restore als root machte
    # core/config.py root:root, Loop (security-ai) konnte nicht
    # schreiben -> patch_write_failed, Reflection-Stagnation, abort.
    # Preflight erkennt das VOR t1 und meldet mit klarer Aktion
    # (chown security-ai:security-ai ...).
    if state is not None:
        import os as _os_an
        _pd_an = getattr(state, "project_dir", None)
        _tasks_an = state.tasks or []
        _rechte_fehler: list[str] = []
        for _t_an in _tasks_an:
            if not isinstance(_t_an, dict):
                continue
            for _f_an in (_t_an.get("task_files") or []):
                if not isinstance(_f_an, str) or not _f_an:
                    continue
                _p_an = Path(_pd_an) / _f_an if _pd_an else None
                if _p_an is None:
                    continue
                if (_p_an.exists() and _p_an.is_file()
                        and not _os_an.access(str(_p_an), _os_an.W_OK)):
                    _rechte_fehler.append(_f_an)
        if _rechte_fehler:
            audit("loop_preflight_rechte",
                  {"dateien": _rechte_fehler[:10],
                   "anzahl": len(_rechte_fehler)},
                  pd, pn)
            print(
                f"[FEHLER] Keine Schreibrechte fuer {len(_rechte_fehler)} "
                f"Task-Datei(en):"
            )
            for _f_an in _rechte_fehler[:10]:
                print(f"  {_f_an}")
            print("  Fix: chown security-ai:security-ai <datei>")
            return 1, phase_state

    # PhaseState automatisch anlegen (fuer Resume-Pfad).
    if phase_state is None:
        phase_state = PhaseState(project_name, base_dir=Path(pd) / ".werkstatt")
        if phase_state.exists():
            phase_state.load()
    # FIX AB 2026-10-31: resume_failed IMMER aufrufen, nicht nur
    # wenn phase_state neu angelegt wurde. Vorher: main() uebergibt
    # phase_state=_ps, also lief resume_failed im CLI-Pfad nie.
    # Bei Resume eines abgebrochenen Multi-Task-Laufs (t5+failed)
    # wurden die failed-Tasks nie wieder pending.
    if phase_state is not None and phase_state.exists():
        if not phase_state.data:
            phase_state.load()
        _n_resume = phase_state.resume_failed(
            preserve_failed=preserve_failed_tasks,
        )
        if _n_resume > 0:
            audit(
                "loop_resume_failed_tasks",
                {"anzahl": _n_resume},
                pd, pn,
            )

    return 0, phase_state


# Compatibility export for older CLI/test integrations. The loop dispatcher
# uses the tool-oriented name and does not invoke the Explorer model role.
_phase_explorer_and_setup = _phase_project_context_tools
