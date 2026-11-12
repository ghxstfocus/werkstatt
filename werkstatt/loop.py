"""Strangler-Fig Loop (M-262 Option C, 2026-10-23).

Phase 7a: Happy Path.
Planner -> Builder -> Verify -> Reflection -> Human.

Hauptpfad: eigener Loop (run_pipeline_loop) ohne den Monolithen.
Fallback (Z.~305): pipeline.run_pipeline, wenn project_dir fehlt.
Das ist die Strangler-Fig-Zwischenphase (Phase 1-18) — kein
Endzustand; der Fallback wird nach Phase >20 entfernt (M-299+).
"""
from __future__ import annotations

import signal
import subprocess  # noqa: F401  # re-export: Tests patchen werkstatt.loop.subprocess
import time  # noqa: F401  # re-export: Tests patchen werkstatt.loop.time
from pathlib import Path

from werkstatt.apply_patches import (  # Fix AZ Stufe 4: Re-Export
    _apply_one_patch,
    _apply_patches_with_diagnose,
    _apply_patches_with_hooks,
    _delete_ziel_erlaubt,
    _diagnose_patch,
    _patches_wirklich_angewendet,
)
from werkstatt.audit import audit, get_run_id, set_run_id
from werkstatt.committer import (  # Fix AZ Stufe 5a: Re-Export
    _committe_zielprojekt,
    _task_fortschritt_block,
)
from werkstatt.env_loader import load_env
from werkstatt.event_store import (
    EventStore,
    RunLeaseBusy,
    RunLeaseLost,
)
from werkstatt.explorer import run_explorer
from werkstatt.gates import (  # Fix AZ Stufe 5b: Re-Export
    _human_gate,
    _human_gate_plan,
    _plan_gate,
)
from werkstatt.git_ops import (  # Fix AZ Stufe 1: Re-Export
    _get_git_diff_for_hook,
    _git_dirty,
    _git_head,
    _git_reset,
    _git_stash,
    _git_stash_owned,
    _git_stash_pop,
)
from werkstatt.hooks import _call_hook  # Fix AZ Stufe 2: Re-Export
from werkstatt.phase_state import PhaseState
from werkstatt.phases import (  # Fix AZ Stufe 11: Re-Export
    _normalize_tasks,
    _phase_explorer_and_setup,
    _phase_finalize,
    _phase_plan_and_preflight,
    _phase_tasks_loop,
)
from werkstatt.planner import run_planner
from werkstatt.reflection import (  # Fix AZ Stufe 6: Re-Export
    _phase_end_reflection,
    _reflection_loop,
)
from werkstatt.render import (
    _with_spinner,
    group_end,
    group_start,
    header,
    log_line,
    step,
    summary,
    task,
    task_done,
    task_ok,
    task_started,
)
from werkstatt.reviewer import run_reviewer
from werkstatt.roles.builder import run_builder
from werkstatt.state import RunState, check_run_lease
from werkstatt.task_runner import (  # Fix AZ Stufe 7: Re-Export
    _extract_files_from_tasks,
    _pruefe_prior_failed_dependency,
    _task_ende,
)
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

_LIFECYCLE_PROJECT = ""
_STOP_SIGNAL: int | None = None
_STOP_SIGNAL_DEFERRED = False


class _LoopStopRequested(Exception):
    """Interner, kontrollierter Abbruch nach einem SIGTERM."""

    def __init__(self, signum: int):
        super().__init__(f"Loop gestoppt (Signal {signum})")
        self.signum = signum


def _handle_loop_sigterm(signum: int, _frame: object) -> None:
    """Unwindet den Loop kontrolliert; doppelte Signale stoeren Cleanup nicht."""
    global _STOP_SIGNAL
    if _STOP_SIGNAL is not None:
        return
    _STOP_SIGNAL = signum
    if not _STOP_SIGNAL_DEFERRED:
        raise _LoopStopRequested(signum)

# Oeffentliche API (Re-Exports + lokale Funktionen).
# ruff F401 entfernt sonst Re-Exports, die von Tests/Aufrufern
# importiert werden. __all__ ist die offizielle Python-Deklaration.
__all__ = [
    "Path",
    "PhaseState",
    "RunState",
    "_apply_one_patch",
    "_apply_patches_with_diagnose",
    "_apply_patches_with_hooks",
    "_call_hook",
    "_committe_zielprojekt",
    "_delete_ziel_erlaubt",
    "_diagnose_patch",
    "_expand_cmd_placeholders",
    "_extract_files_from_tasks",
    "_get_baseline_error_details",
    "_get_git_diff_for_hook",
    "_git_dirty",
    "_git_head",
    "_git_reset",
    "_git_stash",
    "_git_stash_owned",
    "_git_stash_pop",
    "_human_gate",
    "_human_gate_plan",
    "_normalize_tasks",
    "_patches_wirklich_angewendet",
    "_phase_end_reflection",
    "_phase_explorer_and_setup",
    "_phase_finalize",
    "_phase_plan_and_preflight",
    "_phase_tasks_loop",
    "_plan_gate",
    "_pruefe_prior_failed_dependency",
    "_reflection_loop",
    "_resolve_venv_cmd",
    "_ruff_fix_changed",
    "_stage_ist_hart",
    "_task_ende",
    "_task_fortschritt_block",
    "_verify_patches",
    "_verify_patches_soft",
    "_verify_stage_with_heartbeat",
    "_with_spinner",
    "annotations",
    "audit",
    "group_end",
    "group_start",
    "header",
    "load_env",
    "log_line",
    "run_builder",
    "run_explorer",
    "run_planner",
    "run_reviewer",
    "step",
    "summary",
    "task",
    "task_done",
    "task_ok",
    "task_started",
]


from werkstatt.paths import projects_dir as _projects_dir

PROJECTS_DIR = _projects_dir()




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

    from werkstatt import render as _r

    _result: list = [None]
    _exc: list = [None]
    _done = _threading.Event()

    def _worker():
        try:
            _result[0] = fn()
        except Exception as e:
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
                except Exception:
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
    import yaml
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










def _persist_run_result(
    store: EventStore,
    project_name: str,
    run_id: str,
    exit_code: int,
) -> None:
    """Mark the durable run terminal with a version-checked final checkpoint."""
    record = store.get_run_record(project_name, run_id)
    if record is None:
        return
    checkpoint = dict(record["checkpoint"])
    checkpoint["exit_code"] = exit_code
    store.update_run_checkpoint(
        project_name,
        run_id,
        checkpoint,
        expected_version=record["checkpoint_version"],
        status="completed" if exit_code == 0 else "failed",
    )


def run_pipeline_loop(
    project_name: str,
    aufgabe: str,
    state_ref: list[RunState],
    *,
    phasen_state: RunState | None = None,
    phase_state: PhaseState | None = None,
) -> int:
    """Run under an exclusive renewable lease, fencing stale writers."""
    state = phasen_state or (state_ref[-1] if state_ref else None)
    if state is None or not isinstance(getattr(state, "project_dir", None), Path):
        return _run_pipeline_loop_impl(
            project_name, aufgabe, state_ref,
            phasen_state=phasen_state, phase_state=phase_state,
        )
    if not get_run_id():
        set_run_id(f"{project_name}-{time.strftime('%Y%m%d-%H%M%S')}")
    run_id = get_run_id()
    store = EventStore()
    store.create_run_record(
        project_name, run_id, aufgabe, base_commit=_git_head(state.project_dir),
    )
    import os as _lease_os
    import uuid as _lease_uuid

    worker_id = f"{_lease_os.getpid()}:{_lease_uuid.uuid4().hex}"
    try:
        with store.run_lease(
            project_name, run_id, worker_id, lease_seconds=60,
        ) as lease:
            state.run_lease_check = lease.assert_owned
            state.run_id = run_id
            lease.assert_owned()
            return _run_pipeline_loop_impl(
                project_name, aufgabe, state_ref,
                phasen_state=phasen_state, phase_state=phase_state,
            )
    except RunLeaseBusy:
        step(0, "run-lease", "Ein anderer Worker besitzt diesen Run.", ok=False)
        return 1
    except RunLeaseLost as exc:
        audit(
            "loop_failed",
            {"reason": "run_lease_lost", "error": str(exc)[:300]},
            state.project_dir,
            project_name,
        )
        step(0, "run-lease", "Run-Lease verloren; Schreibarbeit gestoppt.", ok=False)
        return 1
    finally:
        state.run_lease_check = None


def _run_pipeline_loop_impl(
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

    # OP-122: Run-ID fuer Event-Store und audit-Logs setzen.
    # Muss VOR dem ersten _publish (header) passieren, sonst bleibt
    # der Event-Store leer.
    if not get_run_id():
        set_run_id(f"{project_name}-{time.strftime('%Y%m%d-%H%M%S')}")

    header(f"{project_name} — {aufgabe[:50]}")

    # OP-303: Loop-Start-Marker fuer Run-Status pro OP.
    import re as _re_loop
    _op_m = _re_loop.search(r"\bOP-(\d+[a-z]?)\b", aufgabe or "")
    _op_id_start = ("OP-" + _op_m.group(1)) if _op_m else ""
    audit("loop_started", {
        "op_id": _op_id_start,
        "aufgabe_kurz": (aufgabe or "")[:200],
    }, Path("."), project_name)

    # Projekt-Pfad aus Config aufloesen, falls nicht gesetzt
    if state is not None and getattr(state, "project_dir", None) is None:
        cfg = load_project_config(project_name)
        if cfg.get("project_dir"):
            state.project_dir = Path(cfg["project_dir"])

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


    # ADR-0032 M1: create the durable run identity before work starts.
    # Existing records are reused on resume; their original base commit stays pinned.
    run_store = EventStore()
    run_record = run_store.create_run_record(
        project_name,
        get_run_id(),
        aufgabe,
        base_commit=_git_head(state.project_dir),
    )
    # A process can die after its filesystem checkpoint was saved. On an
    # explicit, validated resume, re-open the same durable record for work.
    # Keep the checkpoint payload and CAS version intact.
    if run_record["status"] == "failed":
        run_store.update_run_checkpoint(
            project_name,
            get_run_id(),
            run_record["checkpoint"],
            expected_version=run_record["checkpoint_version"],
            status="running",
        )

    # 0. Aufgabe in State setzen (fuer Planner)
    state.aufgabe = aufgabe

    # Fix AZ Stufe 8-A: Explorer + Preflight + PhaseState-Init
    check_run_lease(state)
    _rc_exp, phase_state = _phase_explorer_and_setup(
        state, aufgabe, project_name, phase_state,
    )
    if _rc_exp != 0:
        check_run_lease(state)
        _persist_run_result(EventStore(), project_name, get_run_id(), _rc_exp)
        return _rc_exp

    # 1. Plan-Gate (leer -> Planner muss erst laufen)
    #    Resume: wenn PhaseState vollstaendigen Plan-Checkpoint hat
    #    (tasks + tests + akz), Planner ueberspringen und
    #    state.* aus PhaseState befuellen.
    # Fix AZ Stufe 8-B: Plan-Gate + Planner + Plan-Human-Gate + Pre-Build
    check_run_lease(state)
    _rc_plan, _done = _phase_plan_and_preflight(
        state, aufgabe, project_name, phase_state,
    )
    if _done or _rc_plan != 0:
        check_run_lease(state)
        _persist_run_result(EventStore(), project_name, get_run_id(), _rc_plan)
        return _rc_plan
    from werkstatt.agent import _enforce_run_budget
    if _enforce_run_budget(state):
        check_run_lease(state)
        _persist_run_result(EventStore(), project_name, get_run_id(), 1)
        return 1

    # Fix AZ Stufe 8-C: Autonomer Task-Loop
    check_run_lease(state)
    _rc_task, tasks_ok, tasks = _phase_tasks_loop(state, phase_state)
    if _rc_task != 0:
        check_run_lease(state)
        _persist_run_result(EventStore(), project_name, get_run_id(), _rc_task)
        return _rc_task

    # Fix AZ Stufe 8-D: Phase-End-Review + Human-Gate + Verify + PROGRESS + Summary
    check_run_lease(state)
    rc = _phase_finalize(state, tasks_ok, tasks, project_name, phase_state)
    check_run_lease(state)
    _persist_run_result(EventStore(), project_name, get_run_id(), rc)
    return rc


def _k13_rc(rc: int, tasks_ok: int) -> int:
    """K13: rc=0 nur wenn tasks_ok>0. Sonst ist der Lauf ein Fehlschlag."""
    if rc == 0 and tasks_ok <= 0:
        return 1
    return rc


def _git_stash_head(project_dir: Path) -> str | None:
    """Return the current stash ref, or None when the repository has no stash."""
    try:
        result = subprocess.run(
            ["git", "-C", str(project_dir), "rev-parse", "--verify", "refs/stash"],
            capture_output=True, text=True, timeout=5, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None

def _rotate_fresh_checkpoint(checkpoint: Path, backup: Path) -> Path | None:
    """Preserve the previous backup before moving the active checkpoint.

    Repeated fresh starts must not overwrite the only recovery copy. The
    active checkpoint becomes the resumable backup; older backups are kept
    under numbered archive names in the same directory.
    """
    archived: Path | None = None
    if backup.exists():
        index = 1
        while True:
            candidate = backup.with_name(f"{backup.name}.archive-{index:04d}")
            if not candidate.exists():
                archived = candidate
                break
            index += 1
        backup.replace(archived)
    try:
        checkpoint.replace(backup)
    except OSError:
        if archived is not None and archived.exists() and not backup.exists():
            archived.replace(backup)
        raise
    return archived


def _promote_resume_checkpoint(checkpoint: Path, backup: Path) -> Path | None:
    """Activate a validated backup while preserving the current checkpoint."""
    archived: Path | None = None
    if checkpoint.exists():
        index = 1
        while True:
            candidate = checkpoint.with_name(
                f"{checkpoint.name}.resume-archive-{index:04d}"
            )
            if not candidate.exists():
                archived = candidate
                break
            index += 1
        checkpoint.replace(archived)
    try:
        backup.replace(checkpoint)
    except OSError:
        if archived is not None and archived.exists() and not checkpoint.exists():
            archived.replace(checkpoint)
        raise
    return archived


def _main_inner(argv: list[str] | None = None) -> int:
    global _LIFECYCLE_PROJECT
    # M-391: .env laden (DEEPSEEK_API_KEY automatisch setzen)
    load_env()
    # Tee-Stream fuer Browser-Terminal: alle Render-Zeilen in
    # logs/loop-render-YYYY-MM-DD.log mitschreiben. Wird beim
    # Beenden geschlossen.
    _tee_handle = None
    try:
        from datetime import UTC as _TEE_UTC
        from datetime import datetime as _TEE_DT
        from pathlib import Path as _TEE_P

        from werkstatt import render as _TEE_R
        _tee_now = _TEE_DT.now(_TEE_UTC)
        _tee_p = _TEE_P("logs") / (
            "loop-render-"
            + _tee_now.date().isoformat()
            + "-" + _tee_now.strftime("%H%M%S")
            + ".log"
        )
        _tee_p.parent.mkdir(parents=True, exist_ok=True)
        _tee_handle = _tee_p.open("a", encoding="utf-8")
        _TEE_R.set_tee_stream(_tee_handle)
    except Exception:
        _tee_handle = None

    # Sicherheitsnetz: Tee bei Prozess-Ende schliessen
    import atexit as _atexit
    if _tee_handle is not None:
        _atexit.register(_tee_handle.close)
    """CLI-Einstieg: python3 -m werkstatt.loop --project <name> --aufgabe <text> [--dry-run]."""
    import argparse

    from werkstatt import render as _r

    parser = argparse.ArgumentParser(
        prog="werkstatt.loop",
        description="Werkstatt Strangler-Fig Loop (CLI-Einstieg).",
    )
    parser.add_argument("--project", required=True,
                        help="Projektname (z.B. security-ai)")
    parser.add_argument(
        "--project-dir",
        default="",
        help="Explizites Arbeitsverzeichnis, z.B. ein gepinnter GitHub-Run-Worktree.",
    )
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Bei Fehler git reset --hard auf Start-HEAD (default: aus). "
             "Ohne Flag bleiben erfolgreiche Task-Aenderungen im Tree.",
    )
    checkpoint_group = parser.add_mutually_exclusive_group()
    checkpoint_group.add_argument(
        "--resume",
        action="store_true",
        help="Mit Run-ID passenden aktiven Checkpoint bevorzugen; sonst Backup zuerst.",
    )
    checkpoint_group.add_argument(
        "--fresh",
        action="store_true",
        help="K24: .phase.yaml ignorieren, Phase neu starten.",
    )
    parser.add_argument("--aufgabe", default="",
                        help="Aufgabentext (leer = dry-run-aehnlich)")
    parser.add_argument("--headless", action="store_true",
                        help="Gates per Event-Store statt stdin (ADR-0007).")
    parser.add_argument("--run-id", default="",
                        help="Externe run_id vom Web (Pflicht bei --headless).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Nur Plan-Gate + Renderer, kein LLM, kein Patch")
    args = parser.parse_args(argv)
    _LIFECYCLE_PROJECT = args.project
    if args.headless and not args.run_id:
        parser.error("--headless erfordert --run-id")
    if args.run_id and not args.headless:
        parser.error("--run-id nur mit --headless")
    from werkstatt.gates import set_headless as _set_headless
    _set_headless(bool(args.headless))
    if args.run_id:
        set_run_id(args.run_id)

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
    import uuid as _uuid
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
    _pd = _Path(args.project_dir or _pd_str).expanduser().resolve()
    if not _pd.is_dir():
        _r.step(0, "config", f"project_dir ist kein Verzeichnis: {_pd}", ok=False)
        _r.footer(success=False, tasks_total=0, tasks_ok=0)
        return 1

    _api_key = _os.environ.get("DEEPSEEK_API_KEY", "")
    if not _api_key:
        _r.step(0, "config", "DEEPSEEK_API_KEY fehlt", ok=False)
        _r.footer(success=False, tasks_total=0, tasks_ok=0)
        return 1

    # docs-Inhalte laden (Planner-Kontext). Fehler tolerieren.
    _docs: dict = {}
    _full_cfg: dict = {}  # Bug A (OP-392): vor try, sonst UnboundLocalError
    try:
        from werkstatt.orchestrator import load_docs as _load_docs
        from werkstatt.orchestrator import load_project_config as _load_cfg
        _full_cfg = _load_cfg(args.project)
        if args.project_dir:
            _full_cfg["project_dir"] = str(_pd)
        _docs = _load_docs(_full_cfg.get("docs", {}), _pd)
    except SystemExit:
        # load_project_config/load_docs signalisieren Pflichtfehler per sys.exit.
        raise
    except (OSError, UnicodeError, ValueError, TypeError, AttributeError) as exc:
        _fehler = f"{type(exc).__name__}: {exc}"[:500]
        audit(
            "loop_docs_load_failed",
            {"error": _fehler},
            _pd,
            args.project,
        )
        _r.step(
            0, "docs", f"Pflichtdokumente nicht lesbar: {_fehler}", ok=False,
        )
        _r.footer(success=False, tasks_total=0, tasks_ok=0)
        return 1

    _git_author_cfg = (_full_cfg.get("git_author", {}) if _full_cfg else {}) or {}
    _state = RunState(
        git_author_name=_git_author_cfg.get("name", ""),
        git_author_email=_git_author_cfg.get("email", ""),
        block_id=args.project,
        aufgabe=args.aufgabe,
        start_ts=_dt.now(_UTC).isoformat(timespec="seconds"),
        docs=_docs,
        agents={},
        always={},
        optional={},
        file_whitelist=[],
        api_key=_api_key,
        budget=dict(_full_cfg.get("budget", {}) or {}),
        agent_docs={},
        project_dir=_pd,
        project_name=args.project,
    )
    _state.start_monotonic = _time.monotonic()
    state_ref: list[RunState] = [_state]

    _ps = PhaseState(args.project, base_dir=_pd / ".werkstatt")
    _bak = _ps.path.with_suffix(".yaml.fresh-bak")
    resume_requested = bool(getattr(args, "resume", False))
    fresh_requested = bool(getattr(args, "fresh", False))
    checkpoint_source: Path | None = None

    if resume_requested:
        checkpoint_source = _bak if _bak.exists() else (
            _ps.path if _ps.exists() else None
        )
        if (
            args.run_id and checkpoint_source == _bak
            and _ps.load() and _ps.run_id == args.run_id
        ):
            checkpoint_source = _ps.path
        if checkpoint_source is None:
            audit(
                "loop_resume_verworfen",
                {"reason": "checkpoint_missing"},
                _pd,
                args.project,
            )
            _r.step(0, "checkpoint", "Resume abgelehnt: Checkpoint fehlt", ok=False)
            _r.footer(success=False, tasks_total=0, tasks_ok=0)
            return 1
    elif fresh_requested and _ps.exists():
        archived_backup = _rotate_fresh_checkpoint(_ps.path, _bak)
        audit(
            "loop_fresh_reset",
            {
                "bak": str(_bak),
                "archived_backup": str(archived_backup) if archived_backup else None,
            },
            _pd,
            args.project,
        )
    elif _ps.exists():
        checkpoint_source = _ps.path

    if checkpoint_source is not None:
        active_path = _ps.path
        _ps.path = checkpoint_source
        try:
            checkpoint_valid = _ps.load()
        finally:
            _ps.path = active_path
        if not checkpoint_valid:
            audit(
                "loop_resume_verworfen",
                {
                    "reason": "checkpoint_invalid",
                    "checkpoint": str(checkpoint_source),
                },
                _pd,
                args.project,
            )
            _r.step(
                0, "checkpoint", "Resume abgelehnt: Checkpoint ist ungueltig",
                ok=False,
            )
            _r.footer(success=False, tasks_total=0, tasks_ok=0)
            return 1

        if checkpoint_source is not None and not _ps.run_id:
            audit(
                "loop_resume_verworfen",
                {
                    "reason": "checkpoint_run_id_missing",
                    "checkpoint": str(checkpoint_source),
                },
                _pd,
                args.project,
            )
            _r.step(
                0,
                "checkpoint",
                "Resume abgelehnt: Run-ID im Checkpoint fehlt",
                ok=False,
            )
            _r.footer(success=False, tasks_total=0, tasks_ok=0)
            return 1

        if args.run_id and _ps.run_id != args.run_id:
            audit(
                "loop_checkpoint_run_mismatch",
                {
                    "checkpoint_run_id": _ps.run_id,
                    "requested_run_id": args.run_id,
                    "resume_requested": resume_requested,
                },
                _pd,
                args.project,
            )
            audit(
                "loop_resume_verworfen",
                {
                    "reason": "run_id_mismatch",
                    "checkpoint_run_id": _ps.run_id,
                    "requested_run_id": args.run_id,
                },
                _pd,
                args.project,
            )
            _r.step(
                0,
                "checkpoint",
                "Checkpoint gehoert nicht zu diesem Run; Resume fail-closed gestoppt",
                ok=False,
            )
            _r.footer(success=False, tasks_total=0, tasks_ok=0)
            return 1

        if resume_requested and checkpoint_source == _bak:
            try:
                archived_active = _promote_resume_checkpoint(_ps.path, _bak)
            except OSError as exc:
                audit(
                    "loop_resume_verworfen",
                    {
                        "reason": "checkpoint_promotion_failed",
                        "error": f"{type(exc).__name__}: {exc}"[:300],
                    },
                    _pd,
                    args.project,
                )
                _r.step(
                    0, "checkpoint",
                    "Resume abgelehnt: Backup konnte nicht aktiviert werden",
                    ok=False,
                )
                _r.footer(success=False, tasks_total=0, tasks_ok=0)
                return 1
            audit(
                "loop_resume_from_bak",
                {
                    "bak": str(_bak),
                    "archived_active": str(archived_active) if archived_active else None,
                },
                _pd,
                args.project,
            )
    if args.run_id:
        _ps.run_id = args.run_id
    else:
        # Lokale Starts und Wiederaufnahmen teilen ihre ID mit dem Checkpoint.
        if not _ps.run_id:
            _ps.run_id = f"{args.project}-{_uuid.uuid4().hex}"
        set_run_id(_ps.run_id)

    # K14: Stop muss auch bei SIGTERM den Checkpoint persistieren und
    # einen eventuell angelegten User-Stash wiederherstellen.
    _start_head = ""
    _had_stash = False
    rc = 1
    _hat_exception = False
    try:
        _start_head = _git_head(_pd)
        if _git_dirty(_pd):
            audit("loop_dirty_tree", {"aktion": "stash"}, _pd, args.project)
            # Git-Stash ist ein kurzer, aber mutierender Schritt. Ein
            # SIGTERM wird bis zum Abschluss aufgeschoben; der Stash-Ref
            # erkennt auch einen Stash, dessen Git-Prozess gerade beendet
            # wurde, nachdem der Ref bereits aktualisiert war.
            global _STOP_SIGNAL_DEFERRED
            _STOP_SIGNAL_DEFERRED = True
            try:
                _stash_ref = _git_stash_owned(_pd)
                _stash_after = _stash_ref
                _had_stash = _stash_ref is not None
                _dirty_after_stash = _git_dirty(_pd)
                if not _had_stash or _dirty_after_stash:
                    audit(
                        "loop_stash_failed",
                        {
                            "reason": (
                                "dirty_tree_remains"
                                if _dirty_after_stash
                                else "stash_ref_missing"
                            ),
                            "stash_owned": _had_stash,
                        },
                        _pd, args.project,
                    )
                    raise RuntimeError(
                        "Lokale Aenderungen konnten nicht eindeutig diesem Run "
                        "zugeordnet gesichert werden; der Loop startet nicht."
                    )
            finally:
                _STOP_SIGNAL_DEFERRED = False
            if _STOP_SIGNAL is not None:
                raise _LoopStopRequested(_STOP_SIGNAL)
        rc = run_pipeline_loop(args.project, args.aufgabe, state_ref, phase_state=_ps)
    except BaseException:
        _hat_exception = True
        raise
    finally:
        # Cleanup ist nicht erneut durch ein doppeltes SIGTERM abbrechbar.
        _STOP_SIGNAL_DEFERRED = True
        try:
            if _ps.data:
                try:
                    _ps.save()
                except OSError:
                    pass

            # Kein Rollback bei Ausnahme oder explizitem Stop.
            _do_rollback = getattr(args, "rollback", False)
            if rc != 0 and not _hat_exception:
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
                _stash_restored = _git_stash_pop(_pd, _stash_after)
                if _stash_restored:
                    audit(
                        "loop_stash_pop",
                        {"stash_ref": _stash_after, "stash_retained": True},
                        _pd, args.project,
                    )
                else:
                    audit(
                        "loop_stash_restore_failed",
                        {
                            "stash_ref": _stash_after,
                            "recovery": (
                                f"git stash apply --index {_stash_after}"
                            ),
                        },
                        _pd, args.project,
                    )
        finally:
            _STOP_SIGNAL_DEFERRED = False

    # M-358: Footer mit echten Task-Zahlen (aus state).
    _tasks_total = len(getattr(_state, "tasks", []) or [])
    _tasks_ok = int(getattr(_state, "tasks_ok_counter", 0) or 0)
    # K13: rc=0 nur, wenn tatsaechlich Tasks erledigt wurden.
    _erfolg = (rc == 0) and (_tasks_ok > 0)
    _r.footer(success=_erfolg, tasks_total=_tasks_total, tasks_ok=_tasks_ok)
    return _k13_rc(rc, _tasks_ok)


def _emit_lifecycle_end(
    erfolg: bool, project_name: str | None = None, *, stopped: bool = False,
) -> None:
    """Emit the terminal lifecycle event and close gates for this run."""
    try:
        from pathlib import Path as _P

        from werkstatt.audit import audit, get_run_id
        from werkstatt.gate_bridge import expire_for_run
    except Exception:  # noqa: BLE001
        return
    run_id = get_run_id()
    effektives_projekt = project_name or _LIFECYCLE_PROJECT
    if (
        not run_id
        or not effektives_projekt
        or not run_id.startswith(f"{effektives_projekt}-")
    ):
        return
    if stopped:
        kind = "loop_stopped"
        payload = {"erfolg": False, "abgebrochen": True, "run_id": run_id}
        try:
            audit("loop_stopped", payload, _P.cwd(), effektives_projekt)
        except Exception:  # noqa: BLE001
            pass
    elif erfolg:
        kind = "loop_ended"
        payload = {"erfolg": True, "run_id": run_id}
        try:
            audit("loop_ended", payload, _P.cwd(), effektives_projekt)
        except Exception:  # noqa: BLE001
            pass
    else:
        kind = "loop_failed"
        payload = {"erfolg": False, "run_id": run_id}
        try:
            audit("loop_failed", payload, _P.cwd(), effektives_projekt)
        except Exception:  # noqa: BLE001
            pass
    try:
        expire_for_run(run_id, grund=kind)
    except Exception:  # noqa: BLE001
        pass


def main(argv: list[str] | None = None) -> int:
    """CLI lifecycle wrapper with cleanup-safe SIGTERM handling."""
    global _LIFECYCLE_PROJECT, _STOP_SIGNAL, _STOP_SIGNAL_DEFERRED
    _LIFECYCLE_PROJECT = ""
    _STOP_SIGNAL = None
    _STOP_SIGNAL_DEFERRED = False
    erfolg = False
    gestoppt = False
    previous_sigterm = None
    try:
        previous_sigterm = signal.getsignal(signal.SIGTERM)
        signal.signal(signal.SIGTERM, _handle_loop_sigterm)
    except ValueError:
        # Main() may be invoked in a worker thread by an embedding host.
        previous_sigterm = None
    try:
        try:
            rc = _main_inner(argv)
            if _STOP_SIGNAL is not None:
                gestoppt = True
                return 128 + _STOP_SIGNAL
            erfolg = rc == 0
            return rc
        except _LoopStopRequested as stop:
            gestoppt = True
            return 128 + stop.signum
        except BaseException:
            erfolg = False
            raise
    finally:
        if previous_sigterm is not None:
            signal.signal(signal.SIGTERM, previous_sigterm)
        _emit_lifecycle_end(erfolg, _LIFECYCLE_PROJECT, stopped=gestoppt)
        _LIFECYCLE_PROJECT = ""

if __name__ == "__main__":
    import sys as _sys
    _sys.exit(main())
