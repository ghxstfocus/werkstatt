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


def _plan_gate(state: RunState) -> bool:
    """B1: Plan-Gate (deterministisch).

    M-323c: Validiert Phasen-Struktur, wenn phasen existiert:
      - jeder Task mit phase_id hat eine gueltige phase_id
      - jede phase_id existiert in phasen
      - jede Phase hat mindestens 1 Task
    Flacher Plan (phasen leer) bleibt gueltig.
    """
    # M-408c: Architect-Modus braucht keine tests/akzeptanzkriterien
    _tasks_check = getattr(state, "tasks", []) or []
    _is_architect = any(
        isinstance(_t, dict) and _t.get("action") == "architect"
        for _t in _tasks_check
    )
    if _is_architect:
        # Architect-Modus: 1 Task mit action=architect -> Plan ok
        return bool(_tasks_check)

    # M-457: Planner-Split (Architect+Split) braucht keine
    # tests/akzeptanzkriterien. Tests sind out-of-scope (M-449).
    _is_split = bool(getattr(state, "architect_prosa", None))
    if _is_split:
        if not getattr(state, "tasks", []):
            return False
    elif not all((
        getattr(state, 'tasks', []),
        getattr(state, 'tests', []),
        getattr(state, 'akzeptanzkriterien', [])
    )):
        return False

    _phasen = getattr(state, "phasen", []) or []
    _tasks = getattr(state, "tasks", []) or []

    # K5: Phasen-Validierung nur wenn phasen existieren. Der
    # Doku-Filter-Hook unten laeuft IMMER — auch bei flachem Plan.
    if _phasen:
        _phasen_ids = {p.get("id") for p in _phasen if isinstance(p, dict)}

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
        # K17c: Architect-Prosa fuer Migrations-Kollisions-Check.
        "architect_prosa": getattr(state, "architect_prosa", "") or "",
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

    # GOLD 2026-10-30: Fallback via git diff --name-only, wenn
    # state.patches leer ist. Der Loop leert state.patches nach
    # dem Apply (z.B. _phase_end_reflection), dann finden die
    # Verify-Stages keine changed files und werden uebersprungen
    # (Live-Beleg 2026-10-30 20:52:28: alle Stages skipped, dann
    # loop_verify_ok — echte Verifikation fand nie statt).
    if not changed:
        try:
            import subprocess as _sp
            _res = _sp.run(
                ["git", "-C", str(project_dir), "diff", "--name-only",
                 "HEAD"],
                capture_output=True, text=True, timeout=10, check=False,
            )
            if _res.returncode == 0 and _res.stdout.strip():
                changed = [
                    f for f in _res.stdout.strip().splitlines()
                    if f and (Path(project_dir) / f).exists()
                ]
        except Exception:  # noqa: BLE001, S110
            pass

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


def _verify_stage_with_heartbeat(
    cmd: list[str], cwd: str, stage_id: str, timeout: int = 300
) -> subprocess.CompletedProcess:
    """M-390: Fuehrt subprocess.run aus, mit Heartbeat alle 2s.

    Bei langen pytest-Laeufen (11 Min) sieht der Nutzer sonst
    11 Minuten Stille — kein Lebenszeichen.
    """
    import threading as _threading
    import time as _time

    from werkstatt import loop_renderer

    _done = _threading.Event()
    _result: list = [None]
    _exc: list = [None]

    def _worker():
        try:
            _result[0] = subprocess.run(
                cmd, cwd=cwd, capture_output=True, text=True,
                timeout=timeout, check=False,
            )
        except Exception as e:  # noqa: BLE001
            _exc[0] = e
        finally:
            _done.set()

    def _heartbeat():
        _start = _time.monotonic()
        _last = -1
        while not _done.is_set():
            _el = int(_time.monotonic() - _start)
            if _el // 2 > _last // 2:
                try:
                    loop_renderer.heartbeat(f"[verify] {stage_id}", _el)
                except Exception:  # noqa: BLE001, S110
                    pass
                _last = _el
            _done.wait(timeout=0.5)

    _t = _threading.Thread(target=_worker, daemon=True)
    _th = _threading.Thread(target=_heartbeat, daemon=True)
    _t.start()
    _th.start()
    _t.join()
    _th.join()
    if _exc[0] is not None:
        raise _exc[0]
    return _result[0]


def _resolve_venv_cmd(
    cmd: list[str] | None, project_dir: Path,
) -> list[str] | None:
    """M-443: Wenn .venv/bin/<cmd[0]> existiert, nutze es statt System-Binary.

    Zielprojekte haben ein eigenes venv. Ohne diesen Fix ruft der
    Verify-Loop System-pytest auf, das z.B. defusedxml nicht kennt.
    """
    import os as _os
    if not cmd:
        return cmd
    venv_bin = project_dir / ".venv" / "bin"
    if not venv_bin.is_dir():
        return cmd
    exe = venv_bin / cmd[0]
    if exe.is_file() and _os.access(exe, _os.X_OK):
        return [str(exe)] + cmd[1:]
    return cmd


def _ruff_fix_changed(state: RunState) -> None:
    """GOLD 2026-10-30: ruff --fix auf geaenderte Dateien.

    Vor jedem _verify_patches aufrufen, damit der Fehler-Report
    den aktuellen (nach --fix) Zustand sieht. Bisher lief --fix
    nur im Haupt-Pfad, nicht in der Reflection-Schleife — der
    Builder sah dadurch veraltete Ruff-Fehler.
    """
    try:
        import subprocess as _sp
        pd = getattr(state, "project_dir", None)
        if pd is None:
            return
        _changed = [
            p.get("file") for p in (getattr(state, "patches", None) or [])
            if isinstance(p, dict) and p.get("file")
        ]
        _py_files = [f for f in _changed if f.endswith(".py")]
        if not _py_files:
            return
        _sp.run(
            ["ruff", "check", "--fix", "--no-cache", *_py_files],
            cwd=pd, capture_output=True, text=True, timeout=30,
        )
    except Exception:  # noqa: BLE001, S110
        pass


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
        # M-443: venv-Binary nutzen, falls vorhanden.
        _expanded = _resolve_venv_cmd(_expanded, project_dir)
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
            # M-390: Heartbeat alle 2s waehrend der Stage
            res = _verify_stage_with_heartbeat(
                cmd, str(project_dir), stage.get("id", "?"),
            )
            if res.returncode != 0:
                # K22a: stderr einbeziehen -- ruff schreibt auf stderr.
                _out = (res.stdout or "") + (res.stderr or "")
                errors.append(f"{stage.get('id', '?')}: {_out[-500:]}")
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

    # K20c: Leere-Antworten-Zaehler (EOF-aehnlicher Zustand via script-Wrapper).
    _leer_count = 0
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

        # K20c: Leere Antwort -- script/su-Wrapper liefert '' statt EOFError.
        # Nach 3 leeren Versuchen abbrechen, sonst endlos-Schleife.
        if not _antwort:
            _leer_count += 1
            if _leer_count >= 3:
                audit("loop_plan_gate_leer",
                      {"anzahl": _leer_count}, pd, pn)
                return 1
            continue
        _leer_count = 0

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


def _apply_one_patch(
    content: str, old: str, new: str,
) -> tuple[str, str]:
    """K49: Mehrstufiger old_string-Fallback fuer Aider/Search-Replace."""
    if old in content:
        return content.replace(old, new, 1), "exact"
    _old_s = old.lstrip()
    if _old_s and _old_s in content:
        return content.replace(_old_s, new.lstrip(), 1), "strip"
    _SEP = chr(10) + chr(10)  # "\n\n"
    if _SEP in old:
        _parts = old.rsplit(_SEP, 1)
        _just_old = _parts[-1]
        if _just_old and _just_old in content:
            _new_tail = new.rsplit(_SEP, 1)[-1]
            return (
                content.replace(_just_old, _new_tail, 1),
                "context_only",
            )
    if _SEP in _old_s:
        _parts = _old_s.rsplit(_SEP, 1)
        _just_old = _parts[-1]
        if _just_old and _just_old in content:
            _new_tail = new.rsplit(_SEP, 1)[-1]
            return (
                content.replace(_just_old, _new_tail, 1),
                "context_only",
            )
    return content, "fail"


def _patches_wirklich_angewendet(state) -> bool:
    """K50: True nur, wenn Patches geliefert UND angewandt wurden.

    Wird von beiden Reviewer-Reject-Pfaden genutzt (BUG-A + BUG-B),
    damit die Logik an einer Stelle lebt und testbar ist.
    fail-closed: state.patches truthy, aber applied_count 0/None
    -> False -> Reviewer-Reject wird NICHT ignoriert.
    """
    _applied = int(getattr(state, "applied_count", 0) or 0)
    return bool(getattr(state, "patches", [])) and _applied > 0


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
        _neu_content, _match = _apply_one_patch(_content, _old, _new)
        if _match == "fail":
            audit("loop_patch_old_string_not_found",
                  {"file": _f, "phase": phase_label}, pd, pn)
            continue
        _target.write_text(_neu_content, encoding="utf-8")
        audit("loop_patch_applied",
              {"file": _f, "phase": phase_label, "match": _match}, pd, pn)
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


def _reflection_loop(
    state: RunState,
    max_runden: int = 5,
    error_context: str | None = None,
    phase: str | None = "post_build",
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

    _ruff_vorher: int | None = None
    _stagnation = 0
    # K39a: merken, ob wir wegen Reviewer-Reject gestartet sind.
    _had_error_context = bool(error_context)
    for runde in range(1, max_runden + 1):
        # K3: Wenn error_context gesetzt ist (Reviewer hat abgelehnt),
        # ist ein "Verify gruen" kein Grund zum Abbrechen — der Patch
        # ist semantisch falsch, auch wenn er kompiliert. Dann direkt
        # in den Builder.
        if not error_context:
            # M-402: phase statt None (sonst laeuft pytest_full_checks
            # bei jeder Reflection-Runde mit).
            # GOLD 2026-10-30: ruff --fix vor jedem Verify, damit der
            # Fehler-Report den aktuellen (nach --fix) Zustand sieht.
            _ruff_fix_changed(state)
            if _verify_patches(state, phase=phase):
                return True
        # K28: Circuit Breaker praezisiert. Zaehlt nur echte Stagnation
        # (gleiche Fehler-Anzahl UND keine Verbesserung in 2 Runden).
        # Vorher: abort bei 1 Runde ohne Rueckgang -> verhinderte
        # Reparatur, wenn Fehler sich aendern (F841 statt RUF-Serie).
        _errs = getattr(state, "last_verify_errors", None) or []
        _ruff_jetzt = sum(1 for e in _errs if isinstance(e, str) and "ruff" in e.lower())
        if _ruff_vorher is not None and _ruff_jetzt >= _ruff_vorher and _ruff_jetzt > 0:
            _stagnation += 1
            audit("loop_reflection_stagnation_runde",
                  {"runde": runde, "stagnation": _stagnation,
                   "ruff_vorher": _ruff_vorher,
                   "ruff_jetzt": _ruff_jetzt}, pd, pn)
            if _stagnation >= 2:
                audit("loop_reflection_stagnation_abort",
                      {"runde": runde, "stagnation": _stagnation}, pd, pn)
                return False
        else:
            _stagnation = 0
        _ruff_vorher = _ruff_jetzt

        audit("loop_reflection_runde", {"runde": runde}, pd, pn)

        # K50-Bug-C: last_verify_errors KUMULATIV halten.
        # Vorher wurde die Liste bei jedem Reflection-Eintritt mit
        # error_context ueberschrieben, was dazu fuehrte, dass ein
        # spaeterer reject-Pfad (Z. ~1933) ein leeres _last_errors
        # sah und den Task trotz gescheitertem Patch als task_ok
        # markierte.
        _errors = list(getattr(state, "last_verify_errors", None) or [])
        if error_context and error_context not in _errors:
            _errors = _errors + [error_context]
        state.last_verify_errors = _errors  # type: ignore[attr-defined]

        # M-329: Builder erneut rufen. Er nutzt search/replace.
        # K34: reflection_phase -> _korrigiere_builder_action skip.
        state.reflection_phase = True  # type: ignore[attr-defined]
        try:
            _builder_ok = run_builder(state)
        finally:
            state.reflection_phase = False  # type: ignore[attr-defined]
        if not _builder_ok:
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
        state.applied_count = getattr(state, "applied_count", 0) + _applied  # type: ignore[attr-defined]

        if _applied == 0:
            # K30: Konkreten Patch-Fehler in verify_errors anhaengen,
            # damit naechste Runde weiss warum.
            _patch_err = (
                "reflection: patch_nicht_angewendet "
                "(old_string not found oder apply_skip). "
                "Pruefe den aktuellen Dateiinhalt exakt -- old_string "
                "MUSS zeichengenau aus dem aktuellen Inhalt kopiert sein."
            )
            _cur = getattr(state, "last_verify_errors", None) or []
            state.last_verify_errors = list(_cur) + [_patch_err]  # type: ignore[attr-defined]
            audit("loop_reflection_patch_nicht_angewendet",
                  {"runde": runde}, pd, pn)
            # K47: auch hier History-Eintrag (Patches=0).
            _refl_hist = getattr(state, "reflection_history", None)
            if _refl_hist is None:
                state.reflection_history = []  # type: ignore[attr-defined]
                _refl_hist = state.reflection_history  # type: ignore[attr-defined]
            _refl_hist.append({
                "runde": runde,
                "patches_applied": 0,
                "verify_errors": list(getattr(state, "last_verify_errors", None) or [])[:3],
                "reviewer_bugs": list(getattr(state, "reviewer_bugs", None) or [])[:3],
            })
            if len(_refl_hist) > 5:
                state.reflection_history = _refl_hist[-5:]  # type: ignore[attr-defined]
            # K45: patch_nicht_angewendet ist KEINE Stagnation --
            # der Builder hat etwas versucht. Stagnation-Zaehler
            # zurücksetzen, damit der naechste echte Stagnations-Fall
            # erkannt wird (2x in Folge ohne Versuch).
            _stagnation = 0
            _ruff_vorher = None  # naechste Runde frisch zaehlen
            error_context = ""  # Verify in naechster Runde triggern
            continue

        audit("loop_reflection_patch_applied",
              {"runde": runde, "anzahl": _applied}, pd, pn)

        # K47: Reflection-History Eintrag.
        _refl_hist = getattr(state, "reflection_history", None)
        if _refl_hist is None:
            state.reflection_history = []  # type: ignore[attr-defined]
            _refl_hist = state.reflection_history  # type: ignore[attr-defined]
        _refl_hist.append({
            "runde": runde,
            "patches_applied": _applied,
            "verify_errors": list(getattr(state, "last_verify_errors", None) or [])[:3],
            "reviewer_bugs": list(getattr(state, "reviewer_bugs", None) or [])[:3],
        })
        if len(_refl_hist) > 5:
            state.reflection_history = _refl_hist[-5:]  # type: ignore[attr-defined]

        # K39a: Verify NACH jeder Runde pruefen (nicht nur am Ende).
        # Sonst reparieren die Runden 1-3 nur Reviewer-Bugs und bauen
        # dabei neue Verify-Fehler ein, ohne dass die nächste Runde
        # davon erfährt.
        # GOLD 2026-10-30: ruff --fix vor jedem Verify.
        _ruff_fix_changed(state)
        if not _verify_patches(state, phase=phase):
            # Verify-Fehler -> naechste Runde triggert Verify erneut.
            error_context = ""  # type: ignore[assignment]
            continue
        # Verify gruen -- wenn wir Reflection wegen Reviewer-Reject
        # gestartet haben, jetzt pruefen ob Reviewer jetzt approved.
        if _had_error_context and not error_context:
            from werkstatt.reviewer import run_reviewer as _run_rev
            if _run_rev(state):
                return True
            # sonst: neue Reviewer-Bugs -> naechste Runde
            _new_bugs = getattr(state, "reviewer_bugs", None) or []
            if _new_bugs:
                import json as _j
                error_context = _j.dumps(_new_bugs, ensure_ascii=False)
            continue

    return _verify_patches(state, phase=phase)


def _phase_end_reflection(state: RunState) -> bool:
    """K23d: Phase-End-Reflection. Repariert Phase-Review-Bugs pro Datei.

    Anders als _reflection_loop: kein aktueller Task im State.
    Stattdessen synthetischer Task pro Bug-Datei.

    Max 2 Runden. Rueckgabe: True wenn Phase-Review danach approved.
    """
    from werkstatt.reviewer import run_phase_end_review

    pd = state.project_dir
    pn = state.project_name
    bugs = getattr(state, "reviewer_bugs", []) or []

    for _runde in range(2):
        if not bugs:
            # Nichts zu reparieren, aber Phase-Review war reject.
            # Fail-closed.
            audit("loop_phase_reflection_keine_bugs",
                  {"runde": _runde + 1}, pd, pn)
            return False

        # Eindeutige Dateien aus bugs.
        _bug_files: list[str] = []
        for _b in bugs:
            if not isinstance(_b, dict):
                continue
            _f = _b.get("file")
            if _f and _f not in _bug_files:
                _bug_files.append(_f)
        # K37b: Wenn keine file-Felder in bugs (LLM hat Schema verletzt),
        # Fallback auf alle Task-Dateien.
        if not _bug_files:
            for _t in (getattr(state, "tasks", []) or []):
                if not isinstance(_t, dict):
                    continue
                for _f in (_t.get("task_files") or []):
                    if isinstance(_f, str) and _f not in _bug_files:
                        _bug_files.append(_f)
            if _bug_files:
                audit("loop_phase_reflection_fallback_alle_task_files",
                      {"runde": _runde + 1, "dateien": _bug_files}, pd, pn)
        if not _bug_files:
            audit("loop_phase_reflection_keine_dateien",
                  {"runde": _runde + 1}, pd, pn)
            return False

        audit("loop_phase_reflection_runde",
              {"runde": _runde + 1, "dateien": _bug_files}, pd, pn)

        _repaired = 0
        for _datei in _bug_files:
            # Bugs dieser Datei als Fehler-Kontext.
            _datei_bugs = [
                b for b in bugs
                if isinstance(b, dict) and b.get("file") == _datei
            ]
            _bug_text = "; ".join(
                f"[{b.get('severity')}] {b.get('description', '')}"
                for b in _datei_bugs
            )
            # Synthetischer Task.
            state.aktuelle_task = {  # type: ignore[attr-defined]
                "id": f"phase-fix-{_datei}",
                "name": f"Phase-Fix: {_datei}",
                "action": "update",
                "task_files": [_datei],
                "description": (
                    f"Behebe die vom Phase-Review gemeldeten Bugs in "
                    f"{_datei}: {_bug_text[:1000]}"
                ),
            }
            # Builder rufen.
            state.patches = []  # type: ignore[attr-defined]
            if not run_builder(state):
                audit("loop_phase_reflection_builder_failed",
                      {"datei": _datei, "runde": _runde + 1}, pd, pn)
                continue
            _patches = getattr(state, "patches", None) or []
            if not _patches:
                audit("loop_phase_reflection_kein_patch",
                      {"datei": _datei, "runde": _runde + 1}, pd, pn)
                continue
            _applied = _apply_patches_with_hooks(
                state, _patches,
                phase_label=f"phase-fix-{_datei}-r{_runde + 1}",
            )
            state.applied_count = getattr(state, "applied_count", 0) + _applied  # type: ignore[attr-defined]
            if _applied > 0:
                _repaired += 1
                audit("loop_phase_reflection_patch_applied",
                      {"datei": _datei, "anzahl": _applied,
                       "runde": _runde + 1}, pd, pn)

        # Verify nach Repair.
        if not _verify_patches(state, phase="post_build"):
            audit("loop_phase_reflection_verify_failed",
                  {"runde": _runde + 1}, pd, pn)
            return False

        # Phase-Review erneut.
        if run_phase_end_review(state):
            audit("loop_phase_reflection_approved",
                  {"runde": _runde + 1, "repaired": _repaired}, pd, pn)
            return True
        bugs = getattr(state, "reviewer_bugs", []) or []

    audit("loop_phase_reflection_erschoepft", {"runden": 2}, pd, pn)
    return False


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
            ["git", "diff", "HEAD", "--", ".", ":!PROGRESS.md"],
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



def _committe_zielprojekt(state: RunState) -> tuple[bool, str]:
    """M-487: Committet uncommittete Aenderungen im Zielprojekt.

    Wird vom Human-Gate nach 'j' aufgerufen. Fail-closed bei Git-Fehler.
    Rueckgabe: (True, sha) bei Erfolg, (True, "") wenn nichts zu tun,
    (False, fehlertext) bei Fehler.
    """
    pd = getattr(state, "project_dir", None)
    pn = getattr(state, "project_name", "?")
    if pd is None:
        return False, "kein project_dir"

    try:
        status = subprocess.run(
            ["git", "-C", str(pd), "status", "--porcelain"],
            capture_output=True, text=True, check=False, timeout=10,
        )
    except Exception as _e:  # noqa: BLE001
        return False, f"git status fehlgeschlagen: {_e}"
    if not status.stdout.strip():
        audit("loop_human_gate_commit_skip",
              {"reason": "working_tree_clean"}, pd, pn)
        return True, ""

    try:
        add = subprocess.run(
            ["git", "-C", str(pd), "add", "-A"],
            capture_output=True, text=True, check=False, timeout=30,
        )
    except Exception as _e:  # noqa: BLE001
        return False, f"git add fehlgeschlagen: {_e}"
    if add.returncode != 0:
        return False, f"git add rc={add.returncode}: {add.stderr.strip()[:200]}"

    _name = getattr(state, "git_author_name", "") or "builder"
    _email = getattr(state, "git_author_email", "") or "builder@security-ai.local"
    _aufgabe = (getattr(state, "aufgabe", "") or "").strip()
    _msg_kurz = _aufgabe.split("\n")[0][:80] if _aufgabe else "Werkstatt-RERUN"
    _msg = f"chore(werkstatt): {_msg_kurz}\n\nRERUN (M-487, human_gate committet selbst)."

    _commit_argv = [
        "git", "-C", str(pd),
        "-c", f"user.name={_name}",
        "-c", f"user.email={_email}",
        "commit", "-m", _msg,
    ]
    try:
        commit = subprocess.run(
            _commit_argv,
            capture_output=True, text=True, check=False, timeout=30,
        )
    except Exception as _e:  # noqa: BLE001
        return False, f"git commit fehlgeschlagen: {_e}"
    if commit.returncode != 0:
        audit("loop_human_gate_commit_fehler",
              {"rc": commit.returncode, "stderr": commit.stderr[:300]}, pd, pn)
        return False, f"git commit rc={commit.returncode}: {commit.stderr.strip()[:200]}"

    try:
        _rev = subprocess.run(
            ["git", "-C", str(pd), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=False, timeout=10,
        )
        _sha = _rev.stdout.strip()[:12]
    except Exception:  # noqa: BLE001
        _sha = ""

    audit("loop_human_gate_committed",
          {"sha": _sha, "msg": _msg_kurz}, pd, pn)
    return True, _sha


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
    # M-372: panel_diff statt Plain-Text (rich im pretty/live-Modus).
    from werkstatt import loop_renderer as _rh
    _stat_txt = ""
    _diff_txt = ""
    try:
        _stat = subprocess.run(
            ["git", "-C", str(pd), "diff", "--stat"],
            capture_output=True, text=True, check=False, timeout=10,
        ).stdout
        _stat_txt = _stat.strip() if _stat.strip() else "  (keine Aenderungen)"

        # Voller Diff nur bei kleiner Aenderung (max 2000 Zeichen)
        _full = subprocess.run(
            ["git", "-C", str(pd), "diff"],
            capture_output=True, text=True, check=False, timeout=10,
        ).stdout
        if _full.strip() and len(_full) <= 2000:
            _diff_txt = _full
        elif _full.strip():
            _diff_txt = f"  (Diff zu gross: {len(_full)} Zeichen, siehe git diff)"
    except Exception:  # noqa: BLE001
        _stat_txt = "  (Diff nicht verfuegbar)"

    _gate_body = f"Aenderungen im Zielprojekt:\n{_stat_txt}"
    if _diff_txt:
        _gate_body += f"\n\n{_diff_txt}"
    try:
        _rh.panel_diff(_gate_body, title="HUMAN GATE")
    except Exception:  # noqa: BLE001
        # Fallback: Plain
        print("\n=== HUMAN GATE ===")
        print(_gate_body)

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
        # M-487: Human-Gate committet selbst (nur bei explizitem j).
        _ok, _info = _committe_zielprojekt(state)
        if not _ok:
            audit("loop_human_gate_commit_abort", {"info": _info}, pd, pn)
            print(f"  FEHLER beim Commit: {_info}")
            return 1
        if _info:
            print(f"  Commit: {_info}")
        return 0
    if antwort == "e":
        # Manueller Edit-Modus: Nutzer oeffnet Editor, dann erneut fragen
        print("  Bitte Datei(en) manuell bearbeiten. Enter druecken zum Fortfahren.")
        input()
        # Rekursiv erneut fragen (Diff neu anzeigen)
        return _human_gate(state)
    audit("loop_human_gate_rejected", {"antwort": antwort}, pd, pn)
    return 1


def _git_dirty(pd: Path) -> bool:
    """M-353a: Prueft, ob das Zielprojekt uncommittete Aenderungen hat."""
    import subprocess as _sp
    try:
        res = _sp.run(
            ["git", "-C", str(pd), "status", "--porcelain"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        return bool(res.stdout.strip())
    except Exception:  # noqa: BLE001
        return False


def _git_head(pd: Path) -> str:
    """M-353a: Liefert den aktuellen HEAD-Commit."""
    import subprocess as _sp
    try:
        res = _sp.run(
            ["git", "-C", str(pd), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        return res.stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def _git_stash(pd: Path) -> bool:
    """M-353b: Sichert dirty tree via git stash."""
    import subprocess as _sp
    try:
        res = _sp.run(
            ["git", "-C", str(pd), "stash", "push", "-u", "-m", "werkstatt-loop"],
            capture_output=True, text=True, timeout=30, check=False,
        )
        return res.returncode == 0
    except Exception:  # noqa: BLE001
        return False


def _git_stash_pop(pd: Path) -> bool:
    """M-353b: Holt dirty tree zurueck (bei Erfolg).

    GOLD 2026-10-30: Wenn pop fehlschlaegt (Konflikt), drop den
    Stash. Sonst sammeln sich Stashes an — Live-Beleg 2026-10-30:
    8 offene Stashes nach 8 RERUNs, alle 'werkstatt-loop'.
    """
    import subprocess as _sp
    try:
        res = _sp.run(
            ["git", "-C", str(pd), "stash", "pop"],
            capture_output=True, text=True, timeout=30, check=False,
        )
        if res.returncode == 0:
            return True
        # Pop fehlgeschlagen -> drop den obersten Stash, damit
        # er nicht ewig liegen bleibt.
        _sp.run(
            ["git", "-C", str(pd), "stash", "drop", "stash@{0}"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        return False
    except Exception:  # noqa: BLE001
        return False


def _git_stash_drop(pd: Path) -> bool:
    """M-353b: Verwirft dirty tree (bei Fehler)."""
    import subprocess as _sp
    try:
        res = _sp.run(
            ["git", "-C", str(pd), "stash", "drop"],
            capture_output=True, text=True, timeout=30, check=False,
        )
        return res.returncode == 0
    except Exception:  # noqa: BLE001
        return False


def _git_reset(pd: Path, ref: str) -> bool:
    """M-353c: Setzt Arbeitsbaum auf ref zurueck."""
    import subprocess as _sp
    try:
        res = _sp.run(
            ["git", "-C", str(pd), "reset", "--hard", ref],
            capture_output=True, text=True, timeout=30, check=False,
        )
        return res.returncode == 0
    except Exception:  # noqa: BLE001
        return False


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
    # Backticks: `foo_bar`, `class="x"`, `nth-child(n+4)`
    for _m in _re_explorer.finditer(r'`([^`]{2,80})`', aufgabe):
        _b = _m.group(1).strip()
        if _b:
            _suchbegriffe.append(_b)
    # CSS-Klassen und Selektoren: nth-child(...), table-xyz
    for _m in _re_explorer.finditer(
            r'\b((?:nth-child|table-[a-z]+|class=)[^\s,)\]]{0,40})', aufgabe):
        _b = _m.group(1).strip()
        if _b and _b not in _suchbegriffe:
            _suchbegriffe.append(_b)
    # Funktions-/Methoden-Namen (def foo, foo_bar())
    for _m in _re_explorer.finditer(r'\b([a-z_][a-z0-9_]{3,40})\s*\(', aufgabe):
        _b = _m.group(1)
        if _b not in _suchbegriffe:
            _suchbegriffe.append(_b)
    _suchbegriffe = _suchbegriffe[:20]
    audit("loop_explorer_suchbegriffe",
          {"anzahl": len(_suchbegriffe),
           "begriffe": _suchbegriffe[:10]}, pd, pn)
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
    for f in _explizite_dateien[:5]:
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
        for _runde in range(3):
            if plan_ok:
                break
            _info = getattr(state, "last_planner_info", None)
            if not _info:
                break
            audit("loop_plan_reflection",
                  {"runde": _runde + 1, "info": _info}, pd, pn)
            if not run_planner(state):
                break
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
                audit("loop_builder_failed", {"task_id": i, "action": _loop_action}, pd, pn)
                _task_ende(state, phase_state, task_id, ok=False, name=task_name, failure="builder_failed")
                return 1

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
            audit("loop_task_failed", {"task_id": i, "grund": _split_failure}, pd, pn)
            _task_ende(state, phase_state, task_id, ok=False,
                       name=task_name, failure=_split_failure)
            # K43b: bei split_max_tiefe NICHT den ganzen Loop abbrechen.
            # Der Task ist failed, aber spaetere Tasks koennen weiterlaufen
            # (die Phase ist dann inkonsistent, aber Loop-Erfolg zeigt es
            # im footer korrekt als X/N).
            if _split_failure == "split_max_tiefe":
                continue
            return 1
            return 1

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
            if _reflection_loop(state):
                _task_ende(state, phase_state, task_id, ok=True,
                           name=task_name)
                audit("loop_task_ok", {"task_id": i, "name": task_name,
                                       "via": "reflection"},
                      pd, pn)
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
                if _match2 != "fail":
                    target.write_text(_neu_content2)
                    state.applied_count += 1  # type: ignore[attr-defined]
                if _match2 == "fail":
                    audit("loop_patch_old_string_not_found",
                          {"file": file, "old": old_str[:50]}, pd, pn)
                    # M-298d: Reflection statt stumm weiterlaufen.
                    if not _reflection_loop(state):
                        _task_ende(state, phase_state, task_id, ok=False, name=task_name, failure="old_string_not_found")
                        return 1
                    break  # Retry mit korrigiertem Patch
                # M-351a: Patch mit identischem Inhalt = no_effect.
                if old_str == new_str and _match2 == "exact":
                    audit("loop_patch_no_effect", {"file": file}, pd, pn)
                    continue
                if _match2 != "exact":
                    audit("loop_patch_fallback_used",
                          {"file": file, "match": _match2}, pd, pn)
                target.write_text(_neu_content2)
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

        # M-467: ruff --fix auf geaenderte Dateien (deterministisch).
        # GOLD 2026-10-30: ausgelagert nach _ruff_fix_changed, damit
        # dieselbe Logik auch in der Reflection-Schleife laeuft.
        _ruff_fix_changed(state)

        # Post-Build Verify + Reflection (automatisch)
        if not _verify_patches(state, phase="post_build"):
            audit("loop_gate_failed", {"gate": "post_build", "task_id": i}, pd, pn)
            if not _reflection_loop(state):
                audit("loop_reflection_gescheitert", {"task_id": i}, pd, pn)
                _task_ende(state, phase_state, task_id, ok=False, name=task_name, failure="post_build_verify_failed")
                # K44b: Loop laeuft weiter, andere Tasks koennen noch
                # gebaut werden. Phase ist inkonsistent (footer zeigt X/N),
                # aber ein einzelner gescheiterter Task soll nicht den
                # ganzen Lauf stoppen (vgl. K43b fuer split_max_tiefe).
                continue

        # Reviewer (Phase 9)
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
                    return 1
                else:
                    _task_ende(state, phase_state, task_id, ok=False, name=task_name, failure="reviewer_rejected")
                    return 1
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
                    return 1
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
                    # K43b: bei split_max_tiefe NICHT abbrechen.
                    if _split_failure == "split_max_tiefe":
                        continue
                    return 1
                elif not _last_errors and _hat_patch:
                    audit("loop_reviewer_reject_ignoriert",
                          {"task_id": i, "grund": "pytest gruen nach Reflection"}, pd, pn)
                elif not _last_errors and not _hat_patch:
                    audit("loop_reviewer_reject_fail_closed",
                          {"task_id": i, "grund": "kein_patch_angewendet"}, pd, pn)
                    _task_ende(state, phase_state, task_id, ok=False, name=task_name, failure="reviewer_rejected_no_patch")
                    return 1
                else:
                    _task_ende(state, phase_state, task_id, ok=False, name=task_name, failure="reviewer_rejected_after_reflection")
                    return 1
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

    # 4. (M-476) Phase-End Verify NACH human_gate.

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
    _tasks = getattr(state, "tasks", None) or []
    _alle_done = (
        bool(_tasks)
        and all(
            isinstance(t, dict) and t.get("status") == "done"
            for t in _tasks
        )
    )
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
    # K24: --fresh -> alte .phase.yaml verwerfen, Phase neu.
    if getattr(args, "fresh", False) and _ps.exists():
        _bak = _ps.path.with_suffix(".yaml.fresh-bak")
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

    if rc != 0:
        # M-356: Fehler -> Tree auf start-HEAD zuruecksetzen.
        audit("loop_rollback", {"rc": rc, "start_head": _start_head}, _pd, args.project)
        _git_reset(_pd, _start_head)
        if _had_stash:
            _git_stash_pop(_pd)  # Nutzer-Aenderungen zurueckholen
    else:
        # Erfolg: Loop-Aenderungen behalten.
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
