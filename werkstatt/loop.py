"""Strangler-Fig Loop (M-262 Option C, 2026-10-23).

Phase 7a: Happy Path.
Planner -> Builder -> Verify -> Reflection -> Human.

Hauptpfad: eigener Loop (run_pipeline_loop) ohne den Monolithen.
Fallback (Z.~305): pipeline.run_pipeline, wenn project_dir fehlt.
Das ist die Strangler-Fig-Zwischenphase (Phase 1-18) — kein
Endzustand; der Fallback wird nach Phase >20 entfernt (M-299+).
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

from werkstatt.audit import audit
from werkstatt.git_ops import (  # Fix AZ Stufe 1: Re-Export
    _get_git_diff_for_hook,
    _git_dirty,
    _git_head,
    _git_reset,
    _git_stash,
    _git_stash_drop,
    _git_stash_pop,
)
from werkstatt.hooks import _call_hook  # Fix AZ Stufe 2: Re-Export
from werkstatt.verify import (  # Fix AZ Stufe 3: Re-Export
    _expand_cmd_placeholders,
    _get_baseline_error_details,
    _resolve_venv_cmd,
    _ruff_fix_changed,
    _stage_ist_hart,
    _verify_patches,
    _verify_patches_soft,
    _verify_stage_with_heartbeat,
)
from werkstatt.apply_patches import (  # Fix AZ Stufe 4: Re-Export
    _apply_one_patch,
    _apply_patches_with_hooks,
    _delete_ziel_erlaubt,
    _patches_wirklich_angewendet,
)
from werkstatt.committer import (  # Fix AZ Stufe 5a: Re-Export
    _committe_zielprojekt,
    _task_fortschritt_block,
)
from werkstatt.gates import (  # Fix AZ Stufe 5b: Re-Export
    _human_gate,
    _human_gate_plan,
    _plan_gate,
)
from werkstatt.reflection import (  # Fix AZ Stufe 6: Re-Export
    _phase_end_reflection,
    _reflection_loop,
)
from werkstatt.task_runner import (  # Fix AZ Stufe 7: Re-Export
    _extract_files_from_tasks,
    _pruefe_prior_failed_dependency,
    _split_task_on_demand,
    _task_ende,
)
from werkstatt.loop_renderer import (
    _with_spinner, log_line, task_started, task_done, summary,
)
from werkstatt.builder import run_builder
from werkstatt.env_loader import load_env
from werkstatt.explorer import run_explorer
from werkstatt.loop_renderer import group_end, group_start, header, step, task, task_ok
from werkstatt.phase_state import PhaseState
from werkstatt.planner import run_planner
from werkstatt.reviewer import run_reviewer
from werkstatt.state import RunState




def _run_with_progress(
    fn,
    nr: int,
    total: int,
    name: str,
) -> object:
    """M-327: Ruft fn() auf, zeigt alle 2s eine Status-Zeile.

    Verhindert den Eindruck, der Loop haenge (Builder-LLM-Call
    dauert 20-40s, ask_llm timeout 120s).

    Nutzt loop_renderer.heartbeat (M-301), das im CI-Modus
    mit Zeitstempel schreibt. TTY-Modus: Carriage-Return.
    """
    import threading as _threading
    import time as _time

    from werkstatt import loop_renderer as _r

    _result: list = [None]
    _exc: list = [None]
    _done = _threading.Event()

    def _worker():
        try:
            _result[0] = fn()
        except Exception as e:  # noqa: BLE001
            _exc[0] = e
        finally:
            _done.set()

    def _heartbeat_loop():
        """M-327c: Heartbeat in eigenem Thread.

        Der Worker-Thread (ask_llm, HTTP+JSON) blockiert den
        Main-Thread durch die GIL. Der Heartbeat-Thread laeuft
        trotzdem weiter, weil _done.wait() die GIL freigibt.

        M-371: Nutzt spinner_start/spinner_update, wenn der
        Renderer im live-Modus ist. In ci/pretty: heartbeat.
        """
        _start_hb = _time.monotonic()
        _last_hb = -1
        # M-377: KEIN spinner_start hier — task()/task_ok() steuert
        # den Live-Bereich. Nur heartbeat (No-Op in live, wenn
        # Heartbeat spinner_update ruft).
        while not _done.is_set():
            _elapsed_hb = int(_time.monotonic() - _start_hb)
            if _elapsed_hb // 2 > _last_hb // 2:
                try:
                    _r.heartbeat(f"[{nr}/{total}] {name}", _elapsed_hb)
                except Exception:  # noqa: BLE001, S110
                    pass
                _last_hb = _elapsed_hb
            _done.wait(timeout=0.5)

    _t = _threading.Thread(target=_worker, daemon=True)
    _t_hb = _threading.Thread(target=_heartbeat_loop, daemon=True)
    _t.start()
    _t_hb.start()
    _t.join()
    _t_hb.join()

    if _exc[0] is not None:
        # M-357: Exception nicht re-raisen, sondern als False
        # zurueckgeben, damit der Aufrufer (Task-Loop) den
        # Fehlerpfad mit Audit + _task_ende durchlaeuft.
        import logging as _logging
        _logging.getLogger(__name__).exception(
            "run_with_progress exception: %s", _exc[0]
        )
        return False
    return _result[0]




def load_project_config(project_name: str) -> dict:
    """Laedt die Projekt-Konfiguration (Loop-eigene Variante).

    BEWUSST eigenstaendig, NICHT Alias auf pipeline.load_project_config.
    Grund: pipeline.load_project_config macht sys.exit(1) bei fehlender
    YAML (Fail-closed). Der Loop braucht Fallback-Verhalten
    (/opt/<name>), damit run_pipeline_loop auch ohne project-yaml
    startet. Die beiden Funktionen sind semantisch unterschiedlich.
    Aufloesung der Doppel-Definition nach Phase >20 (M-299+).

    Liefert ein dict mit 'project_dir' (Pfad zum Zielprojekt).
    Fallback: /opt/<project_name>, wenn keine YAML existiert.
    """
    import yaml  # type: ignore[import-untyped]
    cfg_path = PROJECTS_DIR / f"{project_name}.yaml"
    if cfg_path.exists():
        try:
            with cfg_path.open(encoding="utf-8") as fh:
                cfg = yaml.safe_load(fh) or {}
            if "project_dir" in cfg:
                return cfg
        except (yaml.YAMLError, OSError):
            pass
    # Fallback: /opt/<project_name>
    fallback_dir = Path(f"/opt/{project_name}")
    if fallback_dir.exists():
        return {"project_dir": str(fallback_dir)}
    return {"project_dir": None}





def _phase_explorer_and_setup(
    state: RunState,
    aufgabe: str,
    project_name: str,
    phase_state,
):
    """Phase 1 (Fix AZ Stufe 8-A, 2026-10-31): Explorer + Preflight +
    PhaseState-Init.

    Setzt state.explorer_context. Rueckgabe: (rc, phase_state).
    rc=0 -> weiter mit Plan-Gate. rc=1 -> Loop-Abbruch (Preflight).
    """
    pd = state.project_dir
    pn = state.project_name

    # 0b. Explorer (Phase 14, read-only). Einmal pro Loop-Lauf.
    # M-396: Ueberspringen, wenn die Aufgabe explizite Dateien nennt.
    import re as _re_explorer
    _explizite_dateien = _re_explorer.findall(
        r'\b([a-zA-Z_][a-zA-Z0-9_/]+\.(?:py|md|yaml|yml|json|toml|css|html|js))\b',
        aufgabe,
    )

    # GOLD 2026-10-30: Suchbegriffe aus der Aufgabe extrahieren.
    # Der Explorer nutzt sie, um bei grossen Dateien die relevanten
    # Zeilen zu finden statt stumpf erste 100 + letzte 50.
    _suchbegriffe: list[str] = []
    # Backticks: `foo_bar`, `nth-child(n+4)` — volle Kette in Backticks
    for _m in _re_explorer.finditer(r'`([^`]{2,120})`', aufgabe):
        _b = _m.group(1).strip()
        if _b:
            _suchbegriffe.append(_b)
    # CSS-Klassen mit table-Praefix: table-alerts, table-inventory
    for _m in _re_explorer.finditer(r'\b(table-[a-z][a-z0-9-]{1,40})\b', aufgabe):
        _b = _m.group(1)
        if _b not in _suchbegriffe:
            _suchbegriffe.append(_b)
    # CSS-Selektoren in Klammern: nth-child(...) vollstaendig
    for _m in _re_explorer.finditer(r'(nth-child\([^)]{1,40}\))', aufgabe):
        _b = _m.group(1)
        if _b not in _suchbegriffe:
            _suchbegriffe.append(_b)
    # Funktions-/Methoden-Namen mit Unterstrich (def foo_bar, foo_bar())
    for _m in _re_explorer.finditer(
            r'\b([a-z][a-z0-9]*_[a-z0-9_]{2,40})\b', aufgabe):
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
            aufgabe):
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
    _alle_genannten = list(_explizite_dateien)
    for _f in _ordner_dateien:
        if _f not in _alle_genannten:
            _alle_genannten.append(_f)
    _alle_genannten = _alle_genannten[:10]

    # M-396-Fix: Explorer laeuft IMMER, auch bei expliziten Dateien.
    # Genannte Dateien behalten Prioritaet, Explorer ergaenzt verwandte.
    group_start("Phase 1: Explorer")
    _t_exp = time.monotonic()
    _explorer_ergaenzung = run_explorer(state, aufgabe) or {}
    _explorer_key = _explorer_ergaenzung.get("key_files") or []

    # Verwandte Dateien fuer explizit genannte ergaenzen.
    try:
        from werkstatt.explorer import _verwandte_dateien as _vw
        _verwandte = _vw(Path(pd), _explizite_dateien) if _explizite_dateien else []
    except Exception:  # noqa: BLE001
        _verwandte = []

    _seen: set[str] = set()
    explorer_result = {
        "findings": _explorer_ergaenzung.get("findings", ""),
        "key_files": [],
        "next_reads": list(_explorer_ergaenzung.get("next_reads") or []),
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
            from werkstatt.explorer import _datei_inhalt as _di
            _preview = _di(Path(pd), f, suchbegriffe=_suchbegriffe)[:12000]
            explorer_result["key_files"].append(
                {"file": f, "why": "explizit in Aufgabe",
                 "confidence": "high", "preview": _preview}
            )
    for f in _verwandte:
        if f not in _seen:
            _seen.add(f)
            from werkstatt.explorer import _datei_inhalt as _di
            _preview = _di(Path(pd), f, suchbegriffe=_suchbegriffe)[:6000]
            explorer_result["key_files"].append(
                {"file": f, "why": "verwandt (M-396)",
                 "confidence": "medium", "preview": _preview}
            )
    for k in _explorer_key:
        if isinstance(k, dict) and k.get("file") and k["file"] not in _seen:
            _seen.add(k["file"])
            explorer_result["key_files"].append(k)
    audit("loop_explorer_ergaenzt",
          {"explizit": len(_explizite_dateien[:5]),
           "verwandt": len(_verwandte),
           "gesamt": len(explorer_result["key_files"])},
          pd, pn)
    _el_exp = time.monotonic() - _t_exp
    if explorer_result.get("key_files"):
        step(1, "Explorer", f"{len(explorer_result['key_files'])} files", elapsed_s=_el_exp)
        audit("loop_explorer_ok", {"files": len(explorer_result["key_files"])}, pd, pn)
        state.explorer_context = explorer_result  # type: ignore[attr-defined]
    else:
        step(1, "Explorer", "0 files", ok=False, elapsed_s=_el_exp)
        audit("loop_explorer_leer", {}, pd, pn)
    group_end()

    # FIX AN 2026-10-31: Schreibrechte-Preflight fuer Task-Dateien.
    # Live-Beleg 2026-10-31 10:31 t2: git restore als root machte
    # core/config.py root:root, Loop (security-ai) konnte nicht
    # schreiben -> patch_write_failed, Reflection-Stagnation, abort.
    # Preflight erkennt das VOR t1 und meldet mit klarer Aktion
    # (chown security-ai:security-ai ...).
    if state is not None:
        import os as _os_an
        _pd_an = getattr(state, "project_dir", None)
        _tasks_an = getattr(state, "tasks", None) or []
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
                if _p_an.exists() and _p_an.is_file():
                    if not _os_an.access(str(_p_an), _os_an.W_OK):
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
        _n_resume = phase_state.resume_failed()
        if _n_resume > 0:
            audit(
                "loop_resume_failed_tasks",
                {"anzahl": _n_resume},
                pd, pn,
            )

    return 0, phase_state


def _normalize_tasks(raw_tasks):
    """Normalisiert heterogene Task-Liste (dicts + strings) fuer PhaseState."""
    out = []
    for i, t in enumerate(raw_tasks, 1):
        if isinstance(t, dict):
            out.append(t)
        else:
            out.append({"id": f"t{i}", "name": str(t)})
    return out


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
            state.tasks = data["tasks"]  # type: ignore[attr-defined]
        if data.get("tests"):
            state.tests = data["tests"]  # type: ignore[attr-defined]
        if data.get("akzeptanzkriterien"):
            state.akzeptanzkriterien = data["akzeptanzkriterien"]  # type: ignore[attr-defined]
        # FIX (Fix AW-Resume) 2026-10-31: PhaseState mit tasks ist
        # Source of Truth. _plan_gate prueft Planner-Output-Vollstaendigkeit
        # (tasks+tests+akz). Bei Resume aus einer abgebrochenen PhaseState
        # sind tests/akz oft nicht mehr befuellt -> _plan_gate False ->
        # run_planner baut einen NEUEN Plan und ignoriert den PhaseState.
        # Live-Beleg 2026-10-31 11:18: RERUN gegen security-ai, 7 Tasks
        # in PhaseState, Resume geladen, aber Planner lieferte
        # 1-Task-Plan auf 17 SQL-Migrationen. Fix: wenn PhaseState Tasks
        # liefert, ist der Plan gueltig -- kein Planner.
        if getattr(state, "tasks", []):
            plan_ok = True
            audit("loop_resume", {"tasks": len(getattr(state, "tasks", [])),
                                  "quelle": "phase_state"}, pd, pn)
        else:
            plan_ok = _plan_gate(state)
            if plan_ok:
                audit("loop_resume",
                      {"tasks": len(getattr(state, "tasks", [])),
                       "quelle": "gate"}, pd, pn)

    if not plan_ok:
        audit("loop_plan_missing", {"aufgabe": aufgabe[:100]}, pd, pn)
        # M-299e: Preflight-Scan vor Planner. Klassifiziert
        # Baseline-Fehler, damit der Planner BLOCKER/FOLLOW_UP/
        # IGNORE entscheiden kann.
        if not getattr(state, "preflight_fehler", None):
            from werkstatt.planner import _preflight_scan
            _pf = _preflight_scan(state)
            state.preflight_fehler = _pf  # type: ignore[attr-defined]
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

        # GOLD 2026-10-30: Scout kann bereits_erfuellt melden.
        # Dann ist der Plan leer (Tasks = []), und der Plan-Gate
        # wuerde fail-closed abbrechen. Wir springen direkt zum
        # Human-Gate.
        if getattr(state, "auftrag_bereits_erfuellt", False):
            audit("auftrag_bereits_erfuellt",
                  {"quelle": "scout", "aktion": "skip_plan_gate"},
                  pd, pn)
            state.auftrag_bereits_erfuellt = False  # type: ignore[attr-defined]
            # GOLD 2026-10-30: tasks_ok auf 1 setzen, damit K13
            # (rc=0 nur wenn tasks_ok>0) den Lauf als Erfolg wertet.
            # Live-Beleg 2026-10-30 21:59: Commit 30decc63 durch,
            # aber Footer zeigte LOOP FEHLGESCHLAGEN (tasks_ok=0).
            tasks_ok = 1
            state.tasks_ok_counter = tasks_ok  # type: ignore[attr-defined]
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
        _arch_prosa = getattr(state, "architect_prosa", None)
        if _arch_prosa:
            from werkstatt import loop_renderer as _r_arch
            try:
                _r_arch.panel_diff(
                    _arch_prosa, title="ARCHITECT-BESCHREIBUNG"
                )
            except Exception:  # noqa: BLE001, S110
                pass
        else:
            _arch_tasks = [
                t for t in (getattr(state, "tasks", []) or [])
                if isinstance(t, dict) and t.get("action") == "architect"
            ]
            if _arch_tasks:
                _arch_desc = _arch_tasks[0].get("description", "")
                if _arch_desc:
                    from werkstatt import loop_renderer as _r_arch
                    try:
                        _r_arch.panel_diff(
                            _arch_desc, title="ARCHITECT-BESCHREIBUNG"
                        )
                    except Exception:  # noqa: BLE001, S110
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
            audit("loop_gate_failed", {"gate": "plan",
                                       "phase": "plan_reject"}, pd, pn)
            return 1, False

    # M-348c: Plan-Human-Gate (nach Plan-Erstellung, vor Builder).
    if plan_ok:
        audit("loop_phase", {"phase": "plan_gate", "status": "start"}, pd, pn)
        _rc_plan = _human_gate_plan(
            state,
            auto_approve=getattr(state, "auto_approve", False),
        )
        if _rc_plan != 0:
            audit("loop_phase", {"phase": "plan_gate", "status": "rejected"}, pd, pn)
            return 1, False
        audit("loop_phase", {"phase": "plan_gate", "status": "approved"}, pd, pn)
        # PhaseState mit vollstaendigem Plan-Checkpoint initialisieren.
        # K21: auch bei existierender aber leerer .phase.yaml ({})-Datei.
        if (not phase_state.exists()
                or not phase_state.data.get("tasks")):
            phase_state.init_new(
                aufgabe,
                _normalize_tasks(getattr(state, "tasks", [])),
                tests=list(getattr(state, "tests", []) or []),
                akzeptanzkriterien=list(getattr(state, "akzeptanzkriterien", []) or []),
                phasen=list(getattr(state, "phasen", []) or []),  # M-323d
            )

    # M-298d: init_new-Fallback. Wenn der Plan von Anfang an gruen
    # war (state.tasks vorbelegt, z.B. via Resume), wurde
    # init_new oben NICHT aufgerufen (nur im !plan_ok-Zweig).
    # Dann ist phase_state.data = {} und get_next_task() liefert
    # None -> Task-Loop bricht sofort ab (M-298b-Loop-Bug).
    # K21: auch bei leerer existierender Datei.
    if ((not phase_state.exists()
         or not phase_state.data.get("tasks"))
            and getattr(state, "tasks", [])):
        phase_state.init_new(
            aufgabe,
            _normalize_tasks(getattr(state, "tasks", [])),
            tests=list(getattr(state, "tests", []) or []),
            akzeptanzkriterien=list(getattr(state, "akzeptanzkriterien", []) or []),
        )

    _el_plan = time.monotonic() - _t_plan
    step(2, "Planner", f"{len(getattr(state, 'tasks', []))} tasks", elapsed_s=_el_plan)
    audit("loop_phase", {"phase": "plan", "status": "ok"}, pd, pn)
    group_end()

    # 2. Pre-Build Verify (M-299i: deterministische Baseline-Klassifikation).
    # Profi-Ansatz (dxkit, GitAuto): Baseline-Schuld blockiert nicht.
    # Nur Fehler, deren Datei in den Task-Dateien ist, sind BLOCKER.
    if not _verify_patches(state, phase="pre_build"):
        task_files = _extract_files_from_tasks(getattr(state, "tasks", []))
        preflight = getattr(state, "preflight_fehler", []) or []

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
                {"gate": "pre_build", "blocker": len(relevant),
                 "dateien": [f.get("datei") for f in relevant]},
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

    # 3. Autonomer Task-Loop (Claude-Code-Prinzip)
    #    Alle Tasks werden abgearbeitet ohne Unterbrechung.
    #    Human-Gate kommt nur am Ende der Phase.
    tasks = getattr(state, "tasks", [])
    tasks_ok = 0
    i = 0
    # M-473: while-Loop statt for. Nach ADaPT-Split wird die
    # Schleife neu gestartet, damit Sub-Tasks gebaut werden.
    while True:
        next_task = phase_state.get_next_task()
        if next_task is None:
            break
        task_obj = next_task  # Sub-Tasks werden direkt aus PhaseState geholt.
        i += 1
        task_id = next_task.get("id", f"t{i}")
        phase_state.mark_running(task_id)
        task_name = task_obj.get("name", f"Task {i}") if isinstance(task_obj, dict) else str(task_obj)
        group_start(f"Task {i}/?: {task_name}")
        try:
            task_started(i, len(tasks), task_name)
        except Exception:  # noqa: BLE001, S110
            pass
        _t_task = time.monotonic()
        task(i, len(tasks), task_name)
        audit("loop_task_start", {"task_id": i, "name": task_name}, pd, pn)

        # Builder fuer diesen Task
        state.aktuelle_task = task_obj  # type: ignore[attr-defined]

        # M-306d Fix 1: Pro-Task action-Check. read-only Tasks
        # erzeugen keinen Patch, markieren sich direkt als ok.
        _is_read = isinstance(task_obj, dict) and task_obj.get("action") == "read"
        if _is_read:
            audit("loop_task_read_only", {"task_id": i, "name": task_name}, pd, pn)
            _el_task = time.monotonic() - _t_task
            task_ok(i, len(tasks), elapsed_s=_el_task)
            group_end()
            tasks_ok += 1
            state.tasks_ok_counter = tasks_ok  # type: ignore[attr-defined]
            _task_ende(state, phase_state, task_id, ok=True, name=task_name)
            audit("loop_task_ok", {"task_id": i, "name": task_name}, pd, pn)
            continue

        if not _run_with_progress(
            lambda: _with_spinner(f"Builder t{i}", lambda: run_builder(state)),
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
            # M-355b: run_builder=False -> Task gescheitert, KEIN
            # Durchfallen in den Patch-Pfad mit leerem state.patches.
            audit("loop_builder_aufgerufen", {"task_id": i}, pd, pn)
            _task_ende(state, phase_state, task_id, ok=False,
                       name=task_name, failure="builder_failed")
            # M-472: On-Demand-Zerlegung (ADaPT).
            if _split_task_on_demand(state, task_id, phase_state):
                audit("loop_task_retry_nach_split",
                      {"task_id": task_id}, pd, pn)
                continue  # naechster Task (Sub-Task)
            # K38b: Grund aus split_max_tiefe uebernehmen.
            _split_failure = getattr(state, "split_failure_grund", None) or "builder_failed"
            state.split_failure_grund = None  # type: ignore[attr-defined]
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
        if getattr(state, "auftrag_bereits_erfuellt", False):
            audit("auftrag_bereits_erfuellt",
                  {"task_id": i,
                   "name": task_name,
                   "reason": "loop_flag_vor_hook"},
                  pd, pn)
            state.auftrag_bereits_erfuellt = False  # type: ignore[attr-defined]
            # GOLD 2026-10-30: tasks_ok auch bei auftrag_bereits_erfuellt
            # hochzaehlen. Sonst zeigt der Footer "1/5", obwohl alle 5
            # Tasks done sind (Live-Beleg 2026-10-30 21:41:45).
            tasks_ok += 1
            state.tasks_ok_counter = tasks_ok  # type: ignore[attr-defined]
            _task_ende(state, phase_state, task_id, ok=True,
                       name=task_name)
            audit("loop_task_ok", {"task_id": i, "name": task_name,
                                   "via": "auftrag_bereits_erfuellt_pre_hook"},
                  pd, pn)
            continue

        # PreToolUse-Hook (Phase 15): Patch pruefen, BEVOR er angewendet wird.
        # GOLD 2026-10-30: Wenn ein Patch blockiert wird, ueberspringen
        # wir den Apply-Loop komplett. Vorher rief "break" nur aus der
        # Hook-Schleife aus — der Apply-Loop darunter wendete dieselben
        # blockierten Patches trotzdem an (Audit loop_patch_updated).
        patches = getattr(state, "patches", [])
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
            if getattr(state, "auftrag_bereits_erfuellt", False):
                audit("auftrag_bereits_erfuellt",
                      {"task_id": i,
                       "name": task_name,
                       "reason": "hook_blocked_aber_erfuellt",
                       "blocked_reason": _blocked_reason},
                      pd, pn)
                state.auftrag_bereits_erfuellt = False  # type: ignore[attr-defined]
                tasks_ok += 1
                state.tasks_ok_counter = tasks_ok  # type: ignore[attr-defined]
                _task_ende(state, phase_state, task_id, ok=True,
                           name=task_name)
                audit("loop_task_ok", {"task_id": i, "name": task_name,
                                       "via": "auftrag_bereits_erfuellt"},
                      pd, pn)
                continue
            # Reflection versuchen. Sie ruft run_builder + _apply_patches_with_hooks
            # intern; bei True ist der neue Patch schon angewendet.
            # FIX AL 2026-10-31: Reflection-OK nur, wenn applied_count
            # tatsaechlich gestiegen ist. Vorher: _verify_patches gab
            # True bei "no changed files" (leere Stage), Task wurde
            # als done markiert, obwohl nichts geschrieben wurde.
            # Live-Beleg 2026-10-31 10:03 t1.
            _applied_vor_al = int(
                getattr(state, "applied_count", 0) or 0)
            _refl_ok_al = _reflection_loop(state)
            _applied_nach_al = int(
                getattr(state, "applied_count", 0) or 0)
            if _refl_ok_al and _applied_nach_al > _applied_vor_al:
                _task_ende(state, phase_state, task_id, ok=True,
                           name=task_name)
                audit("loop_task_ok", {"task_id": i, "name": task_name,
                                       "via": "reflection"},
                      pd, pn)
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
        state.applied_count = 0  # type: ignore[attr-defined]
        backup_dir = Path(pd) / ".werkstatt" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        _allowed_for_task: set[str] = set()
        for _t_av in (getattr(state, "tasks", []) or []):
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
                    target.write_text(content)
                except OSError as _e:
                    audit("loop_patch_write_failed",
                          {"file": file, "fehler": str(_e)[:200]}, pd, pn)
                    continue
                state.applied_count += 1  # type: ignore[attr-defined]
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
                    if not _reflection_loop(state):
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
                state.applied_count += 1  # type: ignore[attr-defined]
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
                    target.unlink()
                except OSError as _e:
                    audit("loop_patch_delete_failed",
                          {"file": file, "fehler": str(_e)[:200]}, pd, pn)
                    continue
                state.applied_count += 1  # type: ignore[attr-defined]
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
            audit("loop_gate_failed", {"gate": "post_build", "task_id": i}, pd, pn)
            if not _reflection_loop(state):
                audit("loop_reflection_gescheitert", {"task_id": i}, pd, pn)
                _task_ende(state, phase_state, task_id, ok=False, name=task_name, failure="post_build_verify_failed")
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
        state.reviewer_deterministic_fail = False  # type: ignore[attr-defined]
        _rev_ok = _with_spinner(f"Reviewer t{i}", lambda: run_reviewer(state))
        # K40: Historie pushen (unabhaengig vom Ergebnis).
        _cur_bugs = getattr(state, "reviewer_bugs", None) or []
        if _cur_bugs:
            _hist = getattr(state, "reviewer_bugs_history", None)
            if _hist is None:
                state.reviewer_bugs_history = []  # type: ignore[attr-defined]
                _hist = state.reviewer_bugs_history  # type: ignore[attr-defined]
            _hist.append(list(_cur_bugs))
            # Limit auf 5 Runden (RAM-Schutz).
            if len(_hist) > 5:
                state.reviewer_bugs_history = _hist[-5:]  # type: ignore[attr-defined]
        if not _rev_ok:
            # FIX R 2026-10-31: Deterministischer Fail = sofort
            # task_fail, kein Reflection, kein Ignore.
            if getattr(state, "reviewer_deterministic_fail", False):
                audit("loop_reviewer_deterministic_fail",
                      {"task_id": i}, pd, pn)
                _task_ende(state, phase_state, task_id, ok=False,
                           name=task_name,
                           failure="reviewer_unvollstaendig")
                # FIX AR 2026-10-31: continue statt return 1.
                continue
            audit("loop_reviewer_rejected", {"task_id": i}, pd, pn)
            # M-314: Reviewer-Bug-Text als Kontext an Reflection.
            _reviewer_bugs = getattr(state, "reviewer_bugs", []) or []
            # M-441: Bug-Anzahl Runde 1 merken (fuer Divergenz-Check).
            _bugs_runde1 = len(_reviewer_bugs)
            _bug_ctx = ""
            if _reviewer_bugs:
                import json as _json
                _bug_ctx = _json.dumps(_reviewer_bugs, ensure_ascii=False)
            if not _reflection_loop(state, error_context=_bug_ctx):
                audit("loop_reviewer_reflection_gescheitert", {"task_id": i}, pd, pn)
                # M-343c: pytest ist das letzte Wort. Wenn der letzte
                # _verify_patches-Lauf gruen war (last_verify_errors leer),
                # ist der Reviewer-Reject eine Halluzination.
                _last_errors = getattr(state, "last_verify_errors", None) or []
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
                    _task_ende(state, phase_state, task_id, ok=False, name=task_name, failure="reviewer_rejected")
                    continue
            # M-306d Fix 2: Nach erfolgreicher Reflection MUSS der
            # Reviewer erneut pruefen. Sonst fail-open (HR-R9).
            if not run_reviewer(state):
                audit("loop_reviewer_rejected_after_reflection", {"task_id": i}, pd, pn)
                # M-343c: pytest ist das letzte Wort.
                _last_errors = getattr(state, "last_verify_errors", None) or []
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
                _bugs_runde2 = len(getattr(state, "reviewer_bugs", []) or [])
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
                    b for b in (getattr(state, "reviewer_bugs", []) or [])
                    if isinstance(b, dict) and b.get("severity") == "high"
                ]
                if _high_bugs:
                    audit("loop_reviewer_high_bug_fail_closed",
                          {"task_id": i, "high_bugs": len(_high_bugs)}, pd, pn)
                    # M-474: ADaPT bei High-Bugs.
                    if _split_task_on_demand(state, task_id, phase_state):
                        audit("loop_task_retry_nach_split",
                              {"task_id": task_id}, pd, pn)
                        continue
                    # K38b: Grund aus split_max_tiefe uebernehmen.
                    _split_failure = getattr(state, "split_failure_grund", None) or "reviewer_high_bug"
                    state.split_failure_grund = None  # type: ignore[attr-defined]
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

        _el_task = time.monotonic() - _t_task
        task_ok(i, len(tasks), elapsed_s=_el_task)
        try:
            task_done(i, len(tasks), task_name, elapsed_s=_el_task, ok=True)
        except Exception:  # noqa: BLE001, S110
            pass
        group_end()
        tasks_ok += 1
        state.tasks_ok_counter = tasks_ok  # type: ignore[attr-defined]
        _task_ende(state, phase_state, task_id, ok=True, name=task_name)
        audit("loop_task_ok", {"task_id": i, "name": task_name}, pd, pn)

    return 0, tasks_ok, tasks


def run_pipeline_loop(
    project_name: str,
    aufgabe: str,
    state_ref: list[RunState],
    *,
    phasen_state: RunState | None = None,
    phase_state: PhaseState | None = None,
) -> int:
    """Echter Loop: Plan -> Planner -> Builder -> Verify -> Reflection -> Human.

    phase_state: wenn uebergeben, persistiert PhaseState den
    vollstaendigen Plan (tasks + tests + akz) und den
    Task-Fortschritt. Resume-faehig.
    """

    state = phasen_state or (state_ref[-1] if state_ref else None)

    header(f"{project_name} — {aufgabe[:50]}")

    # Projekt-Pfad aus Config aufloesen, falls nicht gesetzt
    if state is not None and getattr(state, "project_dir", None) is None:
        cfg = load_project_config(project_name)
        if cfg.get("project_dir"):
            state.project_dir = Path(cfg["project_dir"])  # type: ignore[attr-defined]

    if state is None or getattr(state, "project_dir", None) is None:
        # M-299b: Harter Abbruch statt Fallback auf pipeline.run_pipeline.
        # Ohne diese Pruefung faellt der Loop still auf den Monolithen
        # zurueck und "Loop funktioniert" ist nicht von "Loop delegiert
        # an pipeline" unterscheidbar (HR-R9).
        #
        # Wer den Loop aufruft, muss einen state mit project_dir
        # liefern. main() prueft das vorher (project_dir aus
        # projects/<name>.yaml), Tests setzen es im _state-Helper.
        _fb_pd = getattr(state, "project_dir", None) if state else None
        if not isinstance(_fb_pd, Path):
            _fb_pd = Path(".")
        _fb_pn = getattr(state, "project_name", project_name) if state else project_name
        audit(
            "loop_fallback_failed",
            {
                "project_name": project_name,
                "aufgabe": aufgabe[:100],
                "reason": "state_none_or_no_project_dir",
            },
            _fb_pd,
            _fb_pn,
        )
        return 1

    pd = state.project_dir
    pn = state.project_name

    # 0. Aufgabe in State setzen (fuer Planner)
    state.aufgabe = aufgabe  # type: ignore[attr-defined]

    # Fix AZ Stufe 8-A: Explorer + Preflight + PhaseState-Init
    _rc_exp, phase_state = _phase_explorer_and_setup(
        state, aufgabe, project_name, phase_state,
    )
    if _rc_exp != 0:
        return _rc_exp

    # 1. Plan-Gate (leer -> Planner muss erst laufen)
    #    Resume: wenn PhaseState vollstaendigen Plan-Checkpoint hat
    #    (tasks + tests + akz), Planner ueberspringen und
    #    state.* aus PhaseState befuellen.
    # Fix AZ Stufe 8-B: Plan-Gate + Planner + Plan-Human-Gate + Pre-Build
    _rc_plan, _done = _phase_plan_and_preflight(
        state, aufgabe, project_name, phase_state,
    )
    if _done or _rc_plan != 0:
        return _rc_plan

    # Fix AZ Stufe 8-C: Autonomer Task-Loop
    _rc_task, tasks_ok, tasks = _phase_tasks_loop(state, phase_state)
    if _rc_task != 0:
        return _rc_task

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
            if not _pt or _pt.get("status") != "done":
                _alle_done = False
                break
    # GOLD 2026-10-30: Nicht nur state.patches pruefen (die koennen
    # gefuellt sein, ohne dass etwas angewendet wurde). Sondern
    # applied_count: hat der Loop tatsaechlich Dateien geaendert?
    _applied = int(getattr(state, "applied_count", 0) or 0)
    _patches_leer = _applied == 0
    if _alle_done and _patches_leer:
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
                state.reviewer_bugs_history = []  # type: ignore[attr-defined]
                _hist = state.reviewer_bugs_history  # type: ignore[attr-defined]
            _hist.append(list(_pe_bugs))
            if len(_hist) > 5:
                state.reviewer_bugs_history = _hist[-5:]  # type: ignore[attr-defined]
        if not _pe_ok:
            audit("loop_phase", {"phase": "phase_end_review", "status": "rejected"}, pd, pn)
            group_end()
            # K23d: Phase-End-Reflection pro Datei.
            if not _phase_end_reflection(state):
                audit("loop_gate_failed",
                      {"gate": "phase_end_review"}, pd, pn)
                return 1
        audit("loop_phase", {"phase": "phase_end_review", "status": "approved"}, pd, pn)
        group_end()

    # 5. Human-Gate (eigenes, fail-closed)
    group_start("Phase 5: Human-Gate")
    audit("loop_phase", {"phase": "human_gate", "status": "start"}, pd, pn)
    rc = _human_gate(state)
    group_end()

    # M-476: Phase-End Verify (Vollsuite) nach human_gate.
    if rc == 0:
        if not _verify_patches(state, phase="phase_end"):
            audit("loop_gate_failed", {"gate": "phase_end"}, pd, pn)
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
    except Exception:  # noqa: BLE001, S110
        pass

    return rc


def _k13_rc(rc: int, tasks_ok: int) -> int:
    """K13: rc=0 nur wenn tasks_ok>0. Sonst ist der Lauf ein Fehlschlag."""
    if rc == 0 and tasks_ok <= 0:
        return 1
    return rc


def main(argv: list[str] | None = None) -> int:
    # M-391: .env laden (DEEPSEEK_API_KEY automatisch setzen)
    load_env()
    """CLI-Einstieg: python3 -m werkstatt.loop --project <name> --aufgabe <text> [--dry-run]."""
    import argparse

    from werkstatt import loop_renderer as _r

    parser = argparse.ArgumentParser(
        prog="werkstatt.loop",
        description="Werkstatt Strangler-Fig Loop (CLI-Einstieg).",
    )
    parser.add_argument("--project", required=True,
                        help="Projektname (z.B. security-ai)")
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Bei Fehler git reset --hard auf Start-HEAD (default: aus). "
             "Ohne Flag bleiben erfolgreiche Task-Aenderungen im Tree.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Aus .phase.yaml.fresh-bak laden (letzter abgebrochener Lauf). "
             "Ohne Flag: aktuelle .phase.yaml.",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="K24: .phase.yaml ignorieren, Phase neu starten.",
    )
    parser.add_argument("--aufgabe", default="",
                        help="Aufgabentext (leer = dry-run-aehnlich)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Nur Plan-Gate + Renderer, kein LLM, kein Patch")
    parser.add_argument("--auto-approve", action="store_true",
                        help="Plan-Gate + Human-Gate automatisch approven (Skript-Runs)")

    args = parser.parse_args(argv)

    _r.header(f"Loop: {args.project}")

    if args.dry_run:
        _r.step(0, "dry-run", "kein LLM, kein Patch")
        _r.footer(success=True, tasks_total=0, tasks_ok=0)
        return 0

    # M-298c: main() erzeugt echten RunState. Ohne das faellt der
    # Loop auf pipeline.run_pipeline zurueck (loop_fallback-Audit).
    # Merkposten: RunState-Bau ist hier inline; gemeinsame
    # Konstruktionsfunktion folgt in M-299+ (Altlasten).
    import os as _os
    import time as _time
    from datetime import UTC as _UTC
    from datetime import datetime as _dt
    from pathlib import Path as _Path

    _cfg = load_project_config(args.project)
    _pd_str = _cfg.get("project_dir")
    if not _pd_str:
        _r.step(0, "config",
                f"project_dir fehlt in projects/{args.project}.yaml",
                ok=False)
        _r.footer(success=False, tasks_total=0, tasks_ok=0)
        return 1
    _pd = _Path(_pd_str)

    _api_key = _os.environ.get("DEEPSEEK_API_KEY", "")
    if not _api_key:
        _r.step(0, "config", "DEEPSEEK_API_KEY fehlt", ok=False)
        _r.footer(success=False, tasks_total=0, tasks_ok=0)
        return 1

    # docs-Inhalte laden (Planner-Kontext). Fehler tolerieren.
    _docs: dict = {}
    try:
        from werkstatt.orchestrator import load_docs as _load_docs
        from werkstatt.orchestrator import load_project_config as _load_cfg
        _full_cfg = _load_cfg(args.project)
        _docs = _load_docs(_full_cfg.get("docs", {}), _pd)
    except SystemExit:
        # load_project_config killt bei Fehlern via sys.exit(1).
        # Das ist hier gewollt (fail-closed).
        raise
    except Exception:  # noqa: BLE001, S110
        # Doku-Ladefehler sind nicht fatal; Planner laeuft ohne Kontext.
        pass

    _state = RunState(
        block_id=args.project,
        aufgabe=args.aufgabe,
        start_ts=_dt.now(_UTC).isoformat(timespec="seconds"),
        docs=_docs,
        agents={},
        always={},
        optional={},
        file_whitelist=[],
        api_key=_api_key,
        budget={},
        agent_docs={},
        project_dir=_pd,
        project_name=args.project,
    )
    _state.start_monotonic = _time.monotonic()
    _state.auto_approve = bool(args.auto_approve)  # type: ignore[attr-defined]
    state_ref: list[RunState] = [_state]

    _ps = PhaseState(args.project, base_dir=_pd / ".werkstatt")
    _bak = _ps.path.with_suffix(".yaml.fresh-bak")
    # FIX AC 2026-10-31: --resume laedt aus .fresh-bak (letzter
    # abgebrochener Lauf). Ohne --resume/--fresh: aktuelle .phase.yaml.
    if getattr(args, "resume", False) and _bak.exists():
        try:
            _bak.replace(_ps.path)
        except OSError:
            pass
        _ps.load()
        audit("loop_resume_from_bak", {"bak": str(_bak)},
              _pd, args.project)
    elif getattr(args, "fresh", False) and _ps.exists():
        try:
            _ps.path.replace(_bak)
        except OSError:
            pass
        audit("loop_fresh_reset", {"bak": str(_bak)},
              _pd, args.project)
    elif _ps.exists():
        _ps.load()

    # M-356: Rollback immer auf start-HEAD. Merken, wo wir starten.
    _start_head = _git_head(_pd)
    _had_stash = False
    if _git_dirty(_pd):
        audit("loop_dirty_tree", {"aktion": "stash"}, _pd, args.project)
        _had_stash = _git_stash(_pd)

    rc = run_pipeline_loop(args.project, args.aufgabe, state_ref, phase_state=_ps)

    # K1b/Schritt1: PhaseState am Loop-Ende persistieren (K14-neutral).
    # Auch bei rc=1 schreiben -> Resume-Basis nach Abbruch.
    # K21: leeren State nicht persistieren (sonst ueberschreibt {} die Tasks).
    if _ps.data:
        try:
            _ps.save()
        except OSError:
            pass

    # FIX AA 2026-10-31: Rollback nur bei explizitem --rollback.
    # Vorher: bei rc!=0 wurde IMMER git reset --hard gemacht.
    # Bei Multi-Task-Aufgaben (DeepSeek 7 Tasks) hat das t1-t4
    # zerstoert, obwohl sie erfolgreich gebaut waren. Resume
    # war unmoeglich, weil die Datei-Aenderungen weg waren.
    _do_rollback = getattr(args, "rollback", False)
    if rc != 0:
        if _do_rollback:
            audit("loop_rollback",
                  {"rc": rc, "start_head": _start_head,
                   "grund": "explizit_angefordert"}, _pd, args.project)
            _git_reset(_pd, _start_head)
        else:
            audit("loop_rollback_skipped",
                  {"rc": rc, "start_head": _start_head,
                   "grund": "kein_rollback_flag"}, _pd, args.project)
        if _had_stash:
            _git_stash_pop(_pd)
    else:
        if _had_stash:
            audit("loop_stash_pop", {}, _pd, args.project)
            _git_stash_pop(_pd)
    # M-358: Footer mit echten Task-Zahlen (aus state).
    _tasks_total = len(getattr(_state, "tasks", []) or [])
    _tasks_ok = int(getattr(_state, "tasks_ok_counter", 0) or 0)
    # K13: rc=0 nur, wenn tatsaechlich Tasks erledigt wurden.
    _erfolg = (rc == 0) and (_tasks_ok > 0)
    _r.footer(success=_erfolg, tasks_total=_tasks_total, tasks_ok=_tasks_ok)
    return _k13_rc(rc, _tasks_ok)


if __name__ == "__main__":
    import sys as _sys
    _sys.exit(main())
