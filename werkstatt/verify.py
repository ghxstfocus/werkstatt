"""Verify-Stages (Fix AZ Stufe 3, 2026-10-31).

Extrahiert aus loop.py. Re-Export in loop.py erhaelt
Test-Patches auf werkstatt.loop._verify_patches etc.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

def audit(*args, **kwargs):
    """Late-Binding-Audit-Proxy (Fix AZ Stufe 3, 2026-10-31).

    Tests patchen werkstatt.loop.audit. Nach der Extraktion nach
    verify.py wuerde ein direkter Import den Patch nicht sehen.
    Der Proxy loest den Namen bei jedem Aufruf in werkstatt.loop
    auf. Damit bleiben alle Test-Patches wirksam
    (test_loop, test_loop_main, test_status_porcelain_parser,
    test_progress, test_k3_reflection).
    """
    from werkstatt.loop import audit as _loop_audit
    return _loop_audit(*args, **kwargs)
from werkstatt.state import RunState


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
            # FIX V 2026-10-31: status --porcelain -uall erfasst auch
            # untracked (create-Tasks). diff --name-only verschweigt
            # sie. Live-Beleg 2026-10-31 08:15: py_compile_changed +
            # ruff_changed wurden uebersprungen, obwohl
            # docs/PLAN_CHAT_ACTIONS.md neu war.
            _res = _sp.run(
                ["git", "-C", str(project_dir), "status", "--porcelain",
                 "-uall"],
                capture_output=True, text=True, timeout=10, check=False,
            )
            if _res.returncode == 0 and _res.stdout.strip():
                # FIX X 2026-10-31: splitlines() OHNE strip() — sonst
                # geht das fuehrende Leerzeichen von " M path"
                # verloren (live: ' M a.py' wurde zu '.py').
                _new_changed = []
                for _ln in _res.stdout.splitlines():
                    if not _ln or not _ln.strip():
                        continue
                    _p = _ln[3:].strip() if len(_ln) > 3 else ""
                    if " -> " in _p:
                        _p = _p.split(" -> ", 1)[1]
                    if _p and (Path(project_dir) / _p).exists():
                        _new_changed.append(_p)
                changed = _new_changed
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
        _t_stage = _time.monotonic() if "_time" in dir() else None
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



# FIX AT 2026-10-31: Stage-Klassifikation nach Schwere.
# Harte Stages: Code crasht, Tests brechen, DB-Schema kaputt.
# Weiche Stages: Style/Lint, blockieren den Commit nicht.


_HARTE_STAGE_PREFIXES = (
    "py_compile", "pytest", "test", "test_",
    "migrations_check", "schema", "import_check",
)
_WEICHE_STAGE_PREFIXES = (
    "ruff", "lint", "mypy", "style", "format", "flake8",
    "bandit", "pip_audit",
)


def _stage_ist_hart(stage_id: str) -> bool:
    """FIX AT: Klassifiziert eine Verify-Stage als hart/weich."""
    _sid = (stage_id or "").lower()
    for _p in _HARTE_STAGE_PREFIXES:
        if _sid.startswith(_p):
            return True
    for _p in _WEICHE_STAGE_PREFIXES:
        if _sid.startswith(_p):
            return False
    # Unbekannt -> hart (fail-closed). Verhindert, dass
    # unbekannte Stages stillschweigend ignoriert werden.
    return True


def _verify_patches_soft(
    state: RunState, phase: str | None = None,
) -> tuple[bool, list[str]]:
    """FIX AT: Wie _verify_patches, aber liefert (hart_ok, weiche_errors).

    hart_ok=True, weiche_errors=[...] -> Task war erfolgreich,
    nur Style-Fehler. Loop markiert task mit Warnung, kein
    task_failed.

    hart_ok=False -> echter Fehler wie zuvor.
    """
    # Rufe _verify_patches auf (setzt last_verify_errors)
    _ok = _verify_patches(state, phase=phase)
    if _ok:
        return True, []
    _all_errors = list(getattr(state, "last_verify_errors", None) or [])
    _hart = []
    _weich = []
    for _e in _all_errors:
        _e_str = str(_e)
        # Format: "stage_id: <message>"
        _stage = _e_str.split(":", 1)[0].strip()
        if _stage_ist_hart(_stage):
            _hart.append(_e_str)
        else:
            _weich.append(_e_str)
    if _hart:
        # Echter Fehler. Nur harte Errors als last_verify_errors
        # behalten (Reflection sieht sie).
        state.last_verify_errors = _hart  # type: ignore[attr-defined]
        return False, _weich
    # Nur weiche Errors. Als "hart_ok" markieren.
    audit("loop_verify_soft_fail",
          {"errors": _weich, "phase": phase},
          getattr(state, "project_dir", None) or Path("."),
          getattr(state, "project_name", "?"))
    return True, _weich


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


__all__ = [
    '_expand_cmd_placeholders',
    '_get_baseline_error_details',
    '_resolve_venv_cmd',
    '_ruff_fix_changed',
    '_stage_ist_hart',
    '_verify_patches',
    '_verify_patches_soft',
    '_verify_stage_with_heartbeat',
]
