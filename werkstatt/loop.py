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
from werkstatt.pipeline_phases import (  # Fix AZ Stufe 11: Re-Export
    _normalize_tasks,
    _phase_explorer_and_setup,
    _phase_finalize,
    _phase_plan_and_preflight,
    _phase_tasks_loop,
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

    # Fix AZ Stufe 8-D: Phase-End-Review + Human-Gate + Verify + PROGRESS + Summary
    return _phase_finalize(state, tasks_ok, tasks, project_name, phase_state)


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
