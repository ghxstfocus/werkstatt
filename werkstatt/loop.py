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
from werkstatt.builder import run_builder
from werkstatt.explorer import run_explorer
from werkstatt.loop_renderer import group_end, group_start, header, step, task, task_ok
from werkstatt.phase_state import PhaseState
from werkstatt.planner import run_planner
from werkstatt.reviewer import run_reviewer
from werkstatt.state import RunState


def _plan_gate(state: RunState) -> bool:
    """B1: Plan-Gate (deterministisch).

    M-323c: Validiert Phasen-Struktur, wenn phasen existiert:
      - jeder Task mit phase_id hat eine gueltige phase_id
      - jede phase_id existiert in phasen
      - jede Phase hat mindestens 1 Task
    Flacher Plan (phasen leer) bleibt gueltig.
    """
    if not all((
        getattr(state, 'tasks', []),
        getattr(state, 'tests', []),
        getattr(state, 'akzeptanzkriterien', [])
    )):
        return False

    _phasen = getattr(state, "phasen", []) or []
    if not _phasen:
        return True  # flacher Plan

    _phasen_ids = {p.get("id") for p in _phasen if isinstance(p, dict)}
    _tasks = getattr(state, "tasks", []) or []

    # Jede Phase hat mindestens 1 Task
    for _phase in _phasen:
        _pid = _phase.get("id")
        _ptasks = [t for t in _tasks if isinstance(t, dict) and t.get("phase_id") == _pid]
        if not _ptasks:
            return False

    # Jeder Task mit phase_id hat eine gueltige phase_id
    for _t in _tasks:
        if not isinstance(_t, dict):
            continue
        _tid = _t.get("phase_id")
        if _tid is not None and _tid not in _phasen_ids:
            return False

    # M-349b: Doku-Tasks via Hook ablehnen (deterministisch).
    _hook_res = _call_hook("planner_gate.py", {
        "tasks": _tasks,
        "phasen": _phasen,
        "project_dir": str(getattr(state, "project_dir", "")),
    })
    if not _hook_res.get("allow", True):
        # Info fuer Planner-Reflection
        state.last_planner_info = _hook_res.get("info", {})  # type: ignore[attr-defined]
        return False

    return True


def _expand_cmd_placeholders(
    cmd: list, state: RunState, project_dir: Path,
) -> list[str] | None:
    """M-322: Ersetzt Platzhalter in Stage-Commands.

    Platzhalter:
      {changed_files}      — alle Dateien aus state.patches
      {changed_test_files} — nur test_*-Dateien aus state.patches

    Rueckgabe None: Stage ueberspringen (z.B. keine changed_test_files).
    """
    cmd_str = " ".join(str(c) for c in cmd)
    if ("{changed_files}" not in cmd_str
            and "{changed_test_files}" not in cmd_str
            and "{changed_py_files}" not in cmd_str):
        return [str(c) for c in cmd]

    patches = getattr(state, "patches", []) or []
    changed = [
        p["file"] for p in patches
        if isinstance(p, dict) and p.get("file")
        and (Path(project_dir) / p["file"]).exists()
    ]
    changed_tests = [
        f for f in changed
        if "test" in f.lower() and f.endswith(".py")
    ]

    changed_py = [f for f in changed if f.endswith(".py")]

    out: list[str] = []
    for c in cmd:
        s = str(c)
        if "{changed_py_files}" in s:
            if not changed_py:
                return None
            s = s.replace("{changed_py_files}", " ".join(changed_py))
        if "{changed_test_files}" in s:
            if not changed_tests:
                return None
            s = s.replace("{changed_test_files}", " ".join(changed_tests))
        if "{changed_files}" in s:
            if not changed:
                return None
            s = s.replace("{changed_files}", " ".join(changed))
        out.extend(s.split())
    return out


def _verify_patches(state: RunState, phase: str | None = None) -> bool:
    """B2: Verifier (multi-projekt-faehig via Projekt-Contract).

    Liest .werkstatt/verify.json aus dem Zielprojekt.
    Fallback: pytest + ruff im Zielprojekt, wenn keine Config.

    phase: wenn gesetzt ("pre_build" oder "post_build"),
    werden nur Stages mit passendem phase-Feld ausgefuehrt.
    Stages ohne phase-Feld laufen immer (Backward-Compat).
    """
    import json
    project_dir = getattr(state, "project_dir", None)
    if project_dir is None or not Path(project_dir).exists():
        return False

    project_dir = Path(project_dir)
    errors = []

    # M-306c: venv_python aus projects/<name>.yaml (verhindert,
    # dass Verify im Zielprojekt mit System-Python laeuft und
    # Dependencies nicht findet).
    _venv_python = "python3"  # Fallback
    _project_name = getattr(state, "project_name", "")
    if _project_name:
        try:
            from werkstatt.orchestrator import load_project_config
            _cfg = load_project_config(_project_name)
            if _cfg.get("venv_python"):
                _venv_python = _cfg["venv_python"]
        except (SystemExit, Exception):  # noqa: BLE001, S110
            pass  # Fallback auf python3

    # 1. Projekt-Contract lesen
    contract_file = project_dir / ".werkstatt" / "verify.json"
    stages = []

    if contract_file.exists():
        try:
            with contract_file.open(encoding="utf-8") as fh:
                contract = json.load(fh)
            stages = contract.get("stages", [])
        except (json.JSONDecodeError, OSError):
            pass

    # 1b. Phase-Filter (M-299a). Wenn phase gesetzt, nur passende
    # Stages behalten. Stages ohne phase-Feld laufen immer.
    if phase is not None:
        stages = [
            s for s in stages
            if s.get("phase") is None or s.get("phase") == phase
        ]

    # 2. Fallback (M-315): KEIN voller pytest/ruff, sondern nur
    # py_compile. Der alte Fallback (volle Suite) blockierte den Loop
    # bei fehlendem verify.json 10+ Minuten.
    # Fail-closed: ohne Contract pruefen wir nur Syntax.
    if not stages:
        # M-322: Fallback breiter — alle *.py in core/ und tests/.
        _fallback_targets: list[str] = []
        for _sub in ("core", "tests"):
            _d = project_dir / _sub
            if _d.exists():
                _fallback_targets.extend(
                    str(pp.relative_to(project_dir))
                    for pp in sorted(_d.rglob("*.py"))
                )
        if _fallback_targets:
            stages = [{
                "id": "py_compile_fallback",
                "command": ["python3", "-m", "py_compile", *_fallback_targets],
            }]
        else:
            stages = [{
                "id": "py_compile_fallback",
                "command": ["python3", "-m", "py_compile", "core/__init__.py"],
            }]

    # 3. Stages ausfuehren
    _executed_stages = []
    for stage in stages:
        cmd = stage.get("command")
        if not cmd:
            continue
        # M-322: Platzhalter ersetzen ({changed_files}, {changed_test_files}).
        _expanded = _expand_cmd_placeholders(list(cmd), state, project_dir)
        if _expanded is None:
            audit("loop_verify_stage_skipped",
                        {"stage": stage.get("id", "?"),
                         "reason": "no changed files"},
                        project_dir, getattr(state, "project_name", "?"))
            continue
        cmd = _expanded
        # M-306c: "python3" im Stage-Command durch venv_python ersetzen.
        if _venv_python != "python3":
            cmd = [_venv_python if c == "python3" else c for c in cmd]
        _executed_stages.append(stage.get("id", "?"))
        try:
            res = subprocess.run(
                cmd, cwd=str(project_dir),
                capture_output=True, text=True, timeout=300, check=False
            )
            if res.returncode != 0:
                errors.append(f"{stage.get('id', '?')}: {res.stdout[-500:]}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{stage.get('id', '?')}-Fehler: {exc}")

    if errors:
        audit("loop_verify_failed",
              {"errors": errors, "phase": phase,
               "stages": _executed_stages},
              project_dir, getattr(state, "project_name", "?"))
        # M-326a: Errors fuer Reflection verfuegbar machen.
        state.last_verify_errors = list(errors)  # type: ignore[attr-defined]
        return False

    # M-322: Erfolg sichtbar machen.
    audit("loop_verify_ok",
          {"stages": _executed_stages, "phase": phase},
          project_dir, getattr(state, "project_name", "?"))
    if not any("pytest" in (s.get("id", "") or "").lower()
               or any("pytest" in str(c) for c in (s.get("command") or []))
               for s in stages):
        audit("loop_verify_no_tests_stage",
              {"stages": [s.get("id", "?") for s in stages]},
              project_dir, getattr(state, "project_name", "?"))
    return True

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


def _get_baseline_error_details(
    state: RunState | None = None,
) -> str:
    """Holt den echten Fehlertext fuer die Reflexion.

    M-326b: Wenn state uebergeben ist UND last_verify_errors
    vorhanden sind, nutze diese (Zielprojekt-Fehler). Sonst
    Fallback auf Werkstatt-Baseline (Backward-Compat fuer
    Reflection-Aufrufe ohne state).
    """
    if state is not None:
        _errors = getattr(state, "last_verify_errors", None)
        if _errors:
            return "\n".join(str(e) for e in _errors)[:4000]
    try:
        res = subprocess.run(
            ["python3", "/opt/werkstatt/tools/quality_gate.py", "--json"],
            cwd="/opt/werkstatt",
            capture_output=True, text=True, timeout=300, check=False
        )
        return res.stdout[:4000]
    except Exception:  # noqa: BLE001
        return "Baseline-Check fehlgeschlagen (Timeout/OSError)"


def _human_gate_plan(state, auto_approve=False):
    """M-348b: Plan-Human-Gate (nach Plan-Erstellung, vor Builder)."""
    pd = getattr(state, "project_dir", None)
    pn = getattr(state, "project_name", "?")
    if pd is None:
        return 1

    if auto_approve:
        audit("loop_plan_gate_auto", {"reason": "auto_approve"}, pd, pn)
        return 0

    import os as _os
    if _os.environ.get("WERKSTATT_IN_TEST") == "1":
        audit("loop_plan_gate_test", {"reason": "WERKSTATT_IN_TEST=1"}, pd, pn)
        return 0

    require = True
    for cfg_name in (f"/opt/werkstatt/projects/{pn}.yaml",):
        cfg_path = Path(cfg_name)
        if cfg_path.exists():
            try:
                import yaml  # type: ignore[import-untyped]
                with cfg_path.open() as fh:
                    cfg = yaml.safe_load(fh) or {}
                require = bool(cfg.get("require_plan_approval", True))
            except Exception:  # noqa: BLE001, S110
                pass
    if not require:
        audit("loop_plan_gate_auto", {"reason": "require_plan_approval=false"}, pd, pn)
        return 0

    from werkstatt import loop_renderer as _r
    _r.plan(
        getattr(state, "phasen", []) or [],
        getattr(state, "tasks", []) or [],
        getattr(state, "tests", []) or [],
        getattr(state, "akzeptanzkriterien", []) or [],
    )

    while True:
        try:
            _antwort = input(
                "\nPlan ausfuehren? [j/n/a]\n"
                "  j = bauen\n"
                "  n = ablehnen (Loop bricht ab)\n"
                "  a = Plan anpassen\n"
                "Deine Wahl: "
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            audit("loop_plan_gate_eof", {}, pd, pn)
            return 1

        if _antwort == "j":
            audit("loop_plan_gate_approved", {}, pd, pn)
            return 0
        if _antwort == "n":
            audit("loop_plan_gate_rejected", {}, pd, pn)
            return 1
        if _antwort == "a":
            _plan_file = Path(pd) / ".werkstatt" / f"{pn}.phase.yaml"
            print(f"\nPlan-Datei: {_plan_file}")
            input("Enter zum Fortfahren...")
            if _plan_file.exists():
                try:
                    import yaml  # type: ignore[import-untyped]
                    with _plan_file.open() as fh:
                        _d = yaml.safe_load(fh) or {}
                    if _d.get("tasks"):
                        state.tasks = _d["tasks"]
                    if _d.get("phasen"):
                        state.phasen = _d["phasen"]
                    if _d.get("tests"):
                        state.tests = _d["tests"]
                    if _d.get("akzeptanzkriterien"):
                        state.akzeptanzkriterien = _d["akzeptanzkriterien"]
                except Exception:  # noqa: BLE001, S110
                    pass
            _r.plan(
                getattr(state, "phasen", []) or [],
                getattr(state, "tasks", []) or [],
                getattr(state, "tests", []) or [],
                getattr(state, "akzeptanzkriterien", []) or [],
            )
            continue
        print("Antworte mit j, n oder a.")

    return 1


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
        if pd is not None:
            _progress.append(
                pd,
                name=name or task_id,
                status="failed",
                dateien=dateien,
                info=failure,
            )


def _apply_patches_with_hooks(
    state: RunState,
    patches: list,
    *,
    phase_label: str = "",
) -> int:
    """Wendet search/replace-Patches an, MIT Hooks (M-330).

    Wird vom Haupt-Pfad UND von der Reflection genutzt.
    Hooks:
      - pre_tool_use pro Patch (allow-Check)
      - post_tool_use nach Apply
      - simplify nach Apply

    Rueckgabe: Anzahl angewendeter Patches (0 = keiner).
    """
    pd = state.project_dir
    pn = state.project_name

    # 1. PreToolUse pro Patch
    for _pat in patches:
        if not isinstance(_pat, dict):
            continue
        _hook_res = _call_hook("pre_tool_use.py", {
            "patch": _pat.get("new_string", "") or _pat.get("content", ""),
            "action": _pat.get("action", "update"),
            "project_dir": str(pd),
        })
        if not _hook_res.get("allow", False):
            audit("loop_hook_blocked",
                  {"hook": "pre_tool_use", "phase": phase_label,
                   "reason": _hook_res.get("reason", "")},
                  pd, pn)
            return 0

    # 2. Apply (search/replace)
    _applied = 0
    for _pat in patches:
        if not isinstance(_pat, dict):
            continue
        _f = _pat.get("file", "")
        _old = _pat.get("old_string", "")
        _new = _pat.get("new_string", "")
        if not _f or not _old or not _new:
            continue
        _target = Path(pd) / _f
        if not _target.exists():
            audit("loop_patch_file_missing",
                  {"file": _f, "phase": phase_label}, pd, pn)
            continue
        _content = _target.read_text(encoding="utf-8")
        if _old not in _content:
            audit("loop_patch_old_string_not_found",
                  {"file": _f, "phase": phase_label}, pd, pn)
            continue
        _target.write_text(
            _content.replace(_old, _new, 1), encoding="utf-8",
        )
        audit("loop_patch_applied",
              {"file": _f, "phase": phase_label}, pd, pn)
        _applied += 1

    if _applied == 0:
        return 0

    # M-334b: post_tool_use entfernt. Der Hook prueft die
    # Werkstatt-Baseline (cwd=/opt/werkstatt), nicht das
    # Zielprojekt. _verify_patches prueft das Zielprojekt
    # (via verify.json). post_tool_use war redundant und blind.

    # 4. Simplify
    _hook_res = _call_hook("simplify.py", {
        "diff": _get_git_diff_for_hook() if "_get_git_diff_for_hook" in globals() else "",
    })
    if not _hook_res.get("allow", False):
        audit("loop_hook_blocked",
              {"hook": "simplify", "phase": phase_label,
               "reason": _hook_res.get("reason", "")},
              pd, pn)

    return _applied


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
        """
        _start_hb = _time.monotonic()
        _last_hb = -1
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
        raise _exc[0]
    return _result[0]


def _reflection_loop(
    state: RunState,
    max_runden: int = 3,
    error_context: str | None = None,
) -> bool:
    """Echter Reflection-Loop (Aider-Prinzip, M-329).

    Statt LLM-Patch + git apply (fragil: LLM schreibt oft
    ungueltige Hunk-Header) ruft die Reflection den Builder
    erneut. Der Builder nutzt sein bewaehrtes search/replace-
    System (old_string/new_string), das deterministisch prueft.

    error_context: zusaetzlicher Kontext (z.B. Reviewer-Befund),
    wird dem Builder-Prompt angehaengt (M-314).
    """
    pd = state.project_dir
    pn = state.project_name
    api_key = getattr(state, "api_key", "")

    if not api_key:
        audit("loop_reflection_kein_key", {}, pd, pn)
        return False

    # M-329: Builder importieren (vermeidet Zirkularitaet).
    from werkstatt.builder import run_builder

    for runde in range(1, max_runden + 1):
        if _verify_patches(state, phase=None):
            return True

        audit("loop_reflection_runde", {"runde": runde}, pd, pn)

        # Fehler-Kontext anreichern (aus _verify_patches).
        _errors = getattr(state, "last_verify_errors", None) or []
        if error_context:
            _errors = list(_errors) + [error_context]
        state.last_verify_errors = _errors  # type: ignore[attr-defined]

        # M-329: Builder erneut rufen. Er nutzt search/replace.
        if not run_builder(state):
            audit("loop_reflection_builder_failed", {"runde": runde}, pd, pn)
            continue

        # Wenn der Builder neue Patches erzeugt hat: anwenden.
        _patches = getattr(state, "patches", []) or []
        if not _patches:
            audit("loop_reflection_kein_patch", {"runde": runde}, pd, pn)
            continue

        # M-330: gemeinsame Apply-Funktion MIT Hooks.
        _applied = _apply_patches_with_hooks(
            state, _patches,
            phase_label=f"reflection-runde-{runde}",
        )

        if _applied == 0:
            audit("loop_reflection_patch_nicht_angewendet",
                  {"runde": runde}, pd, pn)
            continue

        audit("loop_reflection_patch_applied",
              {"runde": runde, "anzahl": _applied}, pd, pn)

    return _verify_patches(state, phase=None)


def _call_hook(hook_name: str, payload: dict) -> dict:
    """Ruft einen Hook auf und gibt das JSON-Ergebnis zurueck."""
    import json as _json
    hook_path = Path(f"/opt/werkstatt/hooks/{hook_name}")
    if not hook_path.exists():
        return {"allow": True, "reason": "Hook nicht gefunden (fail-open)"}
    try:
        res = subprocess.run(
            ["python3", str(hook_path)],
            input=_json.dumps(payload),
            cwd="/opt/werkstatt",
            capture_output=True, text=True, timeout=30, check=False,
        )
        if res.returncode != 0:
            return {"allow": False, "reason": f"Hook rc={res.returncode}"}
        return _json.loads(res.stdout)
    except Exception as exc:  # noqa: BLE001
        return {"allow": False, "reason": f"Hook-Fehler: {exc}"}




def _get_git_diff_for_hook() -> str:
    """Holt den aktuellen Git-Diff fuer Hooks."""
    try:
        res = subprocess.run(
            ["git", "diff", "HEAD"],
            cwd="/opt/werkstatt", capture_output=True, text=True, timeout=30, check=False
        )
        return res.stdout[:10000]
    except Exception:  # noqa: BLE001
        return ""



PROJECTS_DIR = Path("/opt/werkstatt/projects")


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



def _human_gate(state: RunState) -> int:
    """Eigenes Human-Gate im Loop (fail-closed).

    Liest require_human_approval aus der Zielprojekt-Config.
    - false: automatisch approve (rc=0).
    - true: interaktiv input() aufrufen, bei EOFError -> reject (rc=1).
    """
    pd = getattr(state, "project_dir", None)
    pn = getattr(state, "project_name", "?")
    if pd is None:
        return 1

    # Config aus dem Zielprojekt lesen
    require = True
    for cfg_name in (f"/opt/werkstatt/projects/{pn}.yaml",):
        cfg_path = Path(cfg_name)
        if cfg_path.exists():
            try:
                import yaml
                with cfg_path.open() as fh:
                    cfg = yaml.safe_load(fh) or {}
                require = bool(cfg.get("require_human_approval", True))
            except Exception:  # noqa: BLE001, S110
                pass

    if not require:
        audit("loop_human_gate_auto", {"reason": "require_human_approval=false"}, pd, pn)
        return 0

    # Im Test-Kontext: automatisch approven (kein input())
    import os as _os
    if _os.environ.get("WERKSTATT_IN_TEST") == "1":
        audit("loop_human_gate_test", {"reason": "WERKSTATT_IN_TEST=1"}, pd, pn)
        return 0

    # Interaktiv: fail-closed bei EOFError
    # M-303: Impact-Preview vor dem Gate (Agent-Polis/pi-show-diffs-Muster).
    print("\n=== HUMAN GATE ===")
    print("Aenderungen im Zielprojekt:")
    try:
        _stat = subprocess.run(
            ["git", "-C", str(pd), "diff", "--stat"],
            capture_output=True, text=True, check=False, timeout=10,
        ).stdout
        if _stat.strip():
            print(_stat)
        else:
            print("  (keine Aenderungen)")

        # Voller Diff nur bei kleiner Aenderung (max 2000 Zeichen)
        _full = subprocess.run(
            ["git", "-C", str(pd), "diff"],
            capture_output=True, text=True, check=False, timeout=10,
        ).stdout
        if _full.strip() and len(_full) <= 2000:
            print("--- Diff ---")
            print(_full)
        elif _full.strip():
            print(f"  (Diff zu gross: {len(_full)} Zeichen, siehe git diff)")
    except Exception:  # noqa: BLE001
        print("  (Diff nicht verfuegbar)")

    print()
    print("Approve? [j/n/e]")
    print("  j = approve")
    print("  n = reject (Loop bricht ab)")
    print("  e = Datei manuell bearbeiten (dann erneut fragen)")
    try:
        antwort = input("Deine Wahl: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        audit("loop_human_gate_eof", {"reason": "EOFError/KeyboardInterrupt"}, pd, pn)
        return 1

    if antwort in ("j", "ja", "y", "yes"):
        audit("loop_human_gate_approved", {}, pd, pn)
        return 0
    if antwort == "e":
        # Manueller Edit-Modus: Nutzer oeffnet Editor, dann erneut fragen
        print("  Bitte Datei(en) manuell bearbeiten. Enter druecken zum Fortfahren.")
        input()
        # Rekursiv erneut fragen (Diff neu anzeigen)
        return _human_gate(state)
    audit("loop_human_gate_rejected", {"antwort": antwort}, pd, pn)
    return 1


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
    def _normalize_tasks(raw_tasks):
        """Normalisiert heterogene Task-Liste (dicts + strings) fuer PhaseState."""
        out = []
        for i, t in enumerate(raw_tasks, 1):
            if isinstance(t, dict):
                out.append(t)
            else:
                out.append({"id": f"t{i}", "name": str(t)})
        return out

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

    # 0b. Explorer (Phase 14, read-only). Einmal pro Loop-Lauf.
    group_start("Phase 1: Explorer")
    _t_exp = time.monotonic()
    explorer_result = run_explorer(state, aufgabe)
    _el_exp = time.monotonic() - _t_exp
    if explorer_result.get("key_files"):
        step(1, "Explorer", f"{len(explorer_result['key_files'])} files", elapsed_s=_el_exp)
        audit("loop_explorer_ok", {"files": len(explorer_result["key_files"])}, pd, pn)
        state.explorer_context = explorer_result  # type: ignore[attr-defined]
    else:
        step(1, "Explorer", "0 files", ok=False, elapsed_s=_el_exp)
        audit("loop_explorer_leer", {}, pd, pn)
    group_end()

    # PhaseState automatisch anlegen (fuer Resume-Pfad).
    if phase_state is None:
        phase_state = PhaseState(project_name, base_dir=Path(pd) / ".werkstatt")
        if phase_state.exists():
            phase_state.load()
        # M-310c: failed-Tasks reaktivieren (Resume nach Abbruch).
        _n_resume = phase_state.resume_failed()
        if _n_resume > 0:
            audit(
                "loop_resume_failed_tasks",
                {"anzahl": _n_resume},
                pd, pn,
            )

    # 1. Plan-Gate (leer -> Planner muss erst laufen)
    #    Resume: wenn PhaseState vollstaendigen Plan-Checkpoint hat
    #    (tasks + tests + akz), Planner ueberspringen und
    #    state.* aus PhaseState befuellen.
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
        plan_ok = _plan_gate(state)
        if plan_ok:
            audit("loop_resume", {"tasks": len(getattr(state, "tasks", []))}, pd, pn)

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
            return 1
        plan_ok = _plan_gate(state)
        # M-349c: Plan-Reflection. Wenn der Hook den Plan abgelehnt
        # hat (last_planner_info gesetzt), Planner erneut rufen.
        if not plan_ok and getattr(state, "last_planner_info", None):
            audit("loop_plan_reflection",
                  {"info": state.last_planner_info},  # type: ignore[attr-defined]
                  pd, pn)
            if run_planner(state):
                plan_ok = _plan_gate(state)
        if not plan_ok:
            step(2, "Planner", "kein Plan", ok=False)
            audit("loop_gate_failed", {"gate": "plan"}, pd, pn)
            return 1

    # M-348c: Plan-Human-Gate (nach Plan-Erstellung, vor Builder).
    if plan_ok:
        audit("loop_phase", {"phase": "plan_gate", "status": "start"}, pd, pn)
        _rc_plan = _human_gate_plan(
            state,
            auto_approve=getattr(state, "auto_approve", False),
        )
        if _rc_plan != 0:
            audit("loop_phase", {"phase": "plan_gate", "status": "rejected"}, pd, pn)
            return 1
        audit("loop_phase", {"phase": "plan_gate", "status": "approved"}, pd, pn)
        # PhaseState mit vollstaendigem Plan-Checkpoint initialisieren.
        if not phase_state.exists():
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
    if not phase_state.exists() and getattr(state, "tasks", []):
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
            return 1
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

    # 3. Autonomer Task-Loop (Claude-Code-Prinzip)
    #    Alle Tasks werden abgearbeitet ohne Unterbrechung.
    #    Human-Gate kommt nur am Ende der Phase.
    tasks = getattr(state, "tasks", [])
    tasks_ok = 0
    i = 0
    for task_obj in tasks:
        next_task = phase_state.get_next_task()
        if next_task is None:
            break
        i += 1
        task_id = next_task.get("id", f"t{i}")
        phase_state.mark_running(task_id)
        task_name = task_obj.get("name", f"Task {i}") if isinstance(task_obj, dict) else str(task_obj)
        group_start(f"Task {i}/{len(tasks)}: {task_name}")
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
            _task_ende(state, phase_state, task_id, ok=True, name=task_name)
            audit("loop_task_ok", {"task_id": i, "name": task_name}, pd, pn)
            continue

        if not _run_with_progress(
            lambda: run_builder(state),
            i, len(tasks), task_name,
        ):
            # M-316 + M-317: Idempotenz-Erkennung NUR bei
            # action="create". Bei update: fail-closed (return 1).
            _loop_action = None
            if isinstance(task_obj, dict):
                _loop_action = task_obj.get("action")
            if _loop_action not in ("create", "update"):
                # read-Task mit leerem Patch: echter Fehler (Builder
                # sollte hier nie laufen). Bei create/update: Idempotenz-
                # Pfad unten pruefen (M-318).
                audit("loop_builder_failed", {"task_id": i, "action": _loop_action}, pd, pn)
                _task_ende(state, phase_state, task_id, ok=False, name=task_name, failure="builder_failed")
                return 1

            # Idempotenz-Erkennung (nur create).
            _targets_exist = True
            import re as _re3
            _file_pattern3 = _re3.compile(r'\b([a-zA-Z_][a-zA-Z0-9_/]+\.(?:md|py|yaml|yml|json|txt|toml|cfg|ini))\b')
            _found_any = False
            for _task3 in tasks:
                _text3 = _task3 if isinstance(_task3, str) else str(_task3)
                for _m3 in _file_pattern3.findall(_text3):
                    _tf3 = Path(pd) / _m3
                    if _tf3.exists():
                        _found_any = True
                        if _tf3.suffix == ".py":
                            _r3 = subprocess.run(
                                ["python3", "-m", "py_compile", str(_tf3)],
                                capture_output=True, text=True, timeout=30, check=False,
                            )
                            if _r3.returncode != 0:
                                _targets_exist = False
                                break
            if _found_any and _targets_exist:
                audit("loop_task_idempotent", {"task_id": i}, pd, pn)
                _el_task = time.monotonic() - _t_task
                task_ok(i, len(tasks), elapsed_s=_el_task)
                group_end()
                tasks_ok += 1
                _task_ende(state, phase_state, task_id, ok=True, name=task_name)
                audit("loop_task_ok", {"task_id": i, "name": task_name, "idempotent": True}, pd, pn)
                continue
            audit("loop_builder_failed", {"task_id": i}, pd, pn)
            _task_ende(state, phase_state, task_id, ok=False, name=task_name, failure="builder_failed")
            return 1

        # PreToolUse-Hook (Phase 15): Patch pruefen, BEVOR er angewendet wird.
        patches = getattr(state, "patches", [])
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
                audit("loop_hook_blocked", {"hook": "pre_tool_use", "reason": hook_res.get("reason", "")}, pd, pn)
                if not _reflection_loop(state):
                    return 1
                break

        # Patches anwenden (create + update) — NACH dem Hook.
        backup_dir = Path(pd) / ".werkstatt" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
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
                target.write_text(content)
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
                if old_str not in file_content:
                    audit("loop_patch_old_string_not_found", {"file": file, "old": old_str[:50]}, pd, pn)
                    # M-298d: Reflection statt stumm weiterlaufen.
                    if not _reflection_loop(state):
                        _task_ende(state, phase_state, task_id, ok=False, name=task_name, failure="old_string_not_found")
                        return 1
                    break  # Retry mit korrigiertem Patch
                file_content = file_content.replace(old_str, new_str, 1)
                target.write_text(file_content)
                # M-298d: Post-Apply-Verifikation (Profi-Ansatz
                # Overwatcher/Claude-Code edit-verifier).
                _after = target.read_text()
                if new_str not in _after:
                    audit("loop_patch_not_applied", {"file": file}, pd, pn)
                    if not _reflection_loop(state):
                        _task_ende(state, phase_state, task_id, ok=False, name=task_name, failure="patch_not_applied")
                        return 1
                    break
                audit("loop_patch_updated", {"file": file}, pd, pn)

        # M-334b/M-351: post_tool_use entfernt (prueft Werkstatt statt
        # Zielprojekt). _verify_patches prueft das Zielprojekt.

        # Simplify-Hook (Phase 11)
        hook_res = _call_hook("simplify.py", {"diff": _get_git_diff_for_hook()})
        if not hook_res.get("allow", False):
            audit("loop_hook_blocked", {"hook": "simplify", "reason": hook_res.get("reason", "")}, pd, pn)
            if not _reflection_loop(state):
                return 1

        # Post-Build Verify + Reflection (automatisch)
        if not _verify_patches(state, phase="post_build"):
            audit("loop_gate_failed", {"gate": "post_build", "task_id": i}, pd, pn)
            if not _reflection_loop(state):
                audit("loop_reflection_gescheitert", {"task_id": i}, pd, pn)
                _task_ende(state, phase_state, task_id, ok=False, name=task_name, failure="post_build_verify_failed")
                return 1

        # Reviewer (Phase 9)
        if not run_reviewer(state):
            audit("loop_reviewer_rejected", {"task_id": i}, pd, pn)
            # M-314: Reviewer-Bug-Text als Kontext an Reflection.
            _reviewer_bugs = getattr(state, "reviewer_bugs", []) or []
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
                if not _last_errors:
                    audit("loop_reviewer_reject_ignoriert",
                          {"task_id": i, "grund": "pytest gruen"}, pd, pn)
                    # Fall durch zum task_ok
                else:
                    _task_ende(state, phase_state, task_id, ok=False, name=task_name, failure="reviewer_rejected")
                    return 1
            # M-306d Fix 2: Nach erfolgreicher Reflection MUSS der
            # Reviewer erneut pruefen. Sonst fail-open (HR-R9).
            if not run_reviewer(state):
                audit("loop_reviewer_rejected_after_reflection", {"task_id": i}, pd, pn)
                # M-343c: pytest ist das letzte Wort.
                _last_errors = getattr(state, "last_verify_errors", None) or []
                if not _last_errors:
                    audit("loop_reviewer_reject_ignoriert",
                          {"task_id": i, "grund": "pytest gruen nach Reflection"}, pd, pn)
                else:
                    _task_ende(state, phase_state, task_id, ok=False, name=task_name, failure="reviewer_rejected_after_reflection")
                    return 1
            audit("loop_reviewer_approved_after_reflection", {"task_id": i}, pd, pn)

        _el_task = time.monotonic() - _t_task
        task_ok(i, len(tasks), elapsed_s=_el_task)
        group_end()
        tasks_ok += 1
        _task_ende(state, phase_state, task_id, ok=True, name=task_name)
        audit("loop_task_ok", {"task_id": i, "name": task_name}, pd, pn)

    # 4. Phase-End Verify + Reflection (nach allen Tasks).
    # M-322: Bei vorhandener Phasen-Hierarchie laeuft hier die
    # Vollsuite (verify.json: phase="phase_end"). Bei flachem Plan
    # (nur Einzelauftraege) ist phase="phase_end" ein No-Op, weil
    # keine Stage diese Phase deklariert — der Aufruf ist dann
    # billig (nur py_compile-Fallback oder leer).
    if not _verify_patches(state, phase="phase_end"):
        audit("loop_gate_failed", {"gate": "post_build"}, pd, pn)
        if _reflection_loop(state):
            audit("loop_reflection_erfolg", {"project_name": project_name}, pd, pn)
        else:
            audit("loop_reflection_gescheitert", {"project_name": project_name}, pd, pn)
            return 1

    # 5. Human-Gate (eigenes, fail-closed)
    group_start("Phase 5: Human-Gate")
    audit("loop_phase", {"phase": "human_gate", "status": "start"}, pd, pn)
    rc = _human_gate(state)
    group_end()

    if rc == 0:
        audit("loop_erfolg", {"project_name": project_name}, pd, pn)

    # M-307b: Phasen-Ende in PROGRESS.md
    from werkstatt import progress as _progress
    _progress.append(
        pd,
        name=f"Phase abgeschlossen: {project_name}",
        status="phase_ende",
        info=f"rc={rc} tasks_ok={tasks_ok}/{len(tasks)}",
    )

    return rc


def main(argv: list[str] | None = None) -> int:
    """CLI-Einstieg: python3 -m werkstatt.loop --project <name> --aufgabe <text> [--dry-run]."""
    import argparse

    from werkstatt import loop_renderer as _r

    parser = argparse.ArgumentParser(
        prog="werkstatt.loop",
        description="Werkstatt Strangler-Fig Loop (CLI-Einstieg).",
    )
    parser.add_argument("--project", required=True,
                        help="Projektname (z.B. security-ai)")
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
    if _ps.exists():
        _ps.load()

    rc = run_pipeline_loop(args.project, args.aufgabe, state_ref, phase_state=_ps)
    _r.footer(success=(rc == 0), tasks_total=0, tasks_ok=0)
    return rc


if __name__ == "__main__":
    import sys as _sys
    _sys.exit(main())
