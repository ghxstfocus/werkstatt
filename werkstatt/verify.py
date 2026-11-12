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


def _ist_test_datei(pfad: str) -> bool:
    """OP-034: strikte Test-Datei-Erkennung (Pfad-basiert)."""
    p = str(pfad).lower()
    name = p.rsplit("/", 1)[-1]
    if name == "conftest.py":
        return True
    if name.startswith("test_") and name.endswith(".py"):
        return True
    if name.endswith("_test.py"):
        return True
    if "/tests/" in ("/" + p) or p.startswith("tests/"):
        return True
    return bool("/test/" in "/" + p or p.startswith("test/"))


def _stage_anzahl(project_dir: Path) -> int:
    """Liest die Anzahl der Stages aus .werkstatt/verify.json.

    Fail-closed: fehlende/kaputte Datei oder falsches Format -> 0.
    """
    pfad = Path(project_dir) / ".werkstatt" / "verify.json"
    if not pfad.is_file():
        return 0
    try:
        text = pfad.read_text(encoding="utf-8")
        daten = json.loads(text)
    except (OSError, UnicodeError, json.JSONDecodeError):
        return 0
    if not isinstance(daten, dict):
        return 0
    stages = daten.get("stages")
    if not isinstance(stages, list):
        return 0
    return len(stages)


def _stage_ids(project_dir: Path) -> list[str]:
    """Liest die Stage-IDs aus .werkstatt/verify.json (sortiert).

    Fail-closed: fehlende/kaputte Datei oder falsches Format -> [].
    """
    pfad = Path(project_dir) / ".werkstatt" / "verify.json"
    if not pfad.is_file():
        return []
    try:
        text = pfad.read_text(encoding="utf-8")
        daten = json.loads(text)
    except (OSError, UnicodeError, json.JSONDecodeError):
        return []
    if not isinstance(daten, dict):
        return []
    stages = daten.get("stages")
    if not isinstance(stages, list):
        return []
    ids: list[str] = []
    for stage in stages:
        if isinstance(stage, dict) and isinstance(stage.get("id"), str):
            ids.append(stage["id"])
    return sorted(ids)


def _stage_count_by_phase(project_dir: Path, phase: str) -> int:
    """Zaehlt Stages mit exakt passendem phase-Feld in verify.json.

    Fail-closed: fehlende/kaputte Datei oder falsches Format -> 0.
    """
    pfad = Path(project_dir) / ".werkstatt" / "verify.json"
    if not pfad.is_file():
        return 0
    try:
        text = pfad.read_text(encoding="utf-8")
        daten = json.loads(text)
    except (OSError, UnicodeError, json.JSONDecodeError):
        return 0
    if not isinstance(daten, dict):
        return 0
    stages = daten.get("stages")
    if not isinstance(stages, list):
        return 0
    return sum(
        1 for stage in stages
        if isinstance(stage, dict) and stage.get("phase") == phase
    )


def _extrahiere_fehlerkern(text: str, max_chars: int = 3000) -> str:
    """OP-172: Extrahiert Fehler-Zeilen aus Tool-Output.

    Live-Beleg Loop-Test 7 (18:29:11): mypy-Output enthielt
    "error: Source file found twice..." + 5 "note:"-Zeilen. Der
    alte Code `_out[-500:]` schnitt den error-Kopf ab, sodass der
    Builder nur "(also at ...)" + Notes sah und nicht reparieren
    konnte.

    Verwirft:
    - "note:"-Zeilen (mypy-Erklaerungen)
    - "help:"-Zeilen (ruff-Erklaerungen)
    - Statistik-Zeilen ("Found N errors", "X passed", "X failed")

    Behaelt:
    - Zeilen mit " error: " (mypy)
    - Zeilen mit Code-Praefix wie E501/BLE001/F401 (ruff)
    - Zeilen mit "FAILED " oder "AssertionError" oder "assert " (pytest)
    - Je 1 Kontextzeile davor (der Aufhaenger wie "(also at ...)")
    - Je 1 Kontextzeile danach (z.B. "assert False")

    Fallback: letzte max_chars Zeichen (wenn nichts erkannt wurde).
    """
    import re as _re
    if not text:
        return ""

    lines = text.splitlines()
    kerne: list[str] = []
    seen: set[str] = set()

    def _add(s: str) -> None:
        if s and s not in seen:
            kerne.append(s)
            seen.add(s)

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        # Verwirf explizit
        if stripped.startswith(("note:", "help:")):
            continue
        if _re.match(r"^\[?\d+\s+(passed|failed|errors?|warnings?|skipped)",
                     stripped, _re.IGNORECASE):
            continue
        if stripped.lower().startswith("found ") and " error" in stripped.lower():
            continue

        is_err = (
            " error: " in line
            or line.startswith("FAILED ")
            or "AssertionError" in line
            or _re.match(r"^[A-Z]\d{3,4}\b", stripped)
        )
        if not is_err:
            continue

        # 1 Kontextzeile davor (Aufhaenger wie "(also at ...)")
        if i > 0:
            prev = lines[i - 1].rstrip()
            if (prev and not prev.strip().startswith(("note:", "help:"))
                    and " error: " not in prev):
                _add(prev)
        _add(line.rstrip())
        # 1 Kontextzeile danach (assert-Body bei pytest)
        if i + 1 < len(lines):
            nxt = lines[i + 1]
            if ("assert" in nxt.lower()
                    and not nxt.strip().startswith(("note:", "help:"))):
                _add(nxt.rstrip())

    if not kerne:
        return text[-max_chars:]

    # Join mit echtem Newline (Zeichen-Code 10).
    result = chr(10).join(kerne)
    if len(result) > max_chars:
        result = result[:max_chars] + chr(10) + "[...]"
    return result


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
            and "{changed_py_files}" not in cmd_str
            and "{changed_non_test_py_files}" not in cmd_str
            and "{task_files}" not in cmd_str):
        return [str(c) for c in cmd]

    patches = state.patches or []
    if not patches:
        _fallback = getattr(state, "patches_aktuell_runde", None)
        if _fallback:
            patches = _fallback
    # 2026-11-07: Dedupe. Nach mehreren Reflection-Runden hat
    # state.patches denselben File-Pfad mehrfach. Ohne Dedupe bekommt
    # z.B. `mypy {changed_py_files}` denselben Pfad 5x und meldet
    # "Duplicate module named ..." — kuenstlicher Fehler, der nie
    # verschwindet. dict.fromkeys dedupliziert und bewahrt Reihenfolge.
    changed = list(dict.fromkeys(
        p["file"] for p in patches
        if isinstance(p, dict) and p.get("file")
        and (Path(project_dir) / p["file"]).exists()
    ))

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
                # 2026-11-07: Dedupe wie bei `changed`.
                changed = list(dict.fromkeys(_new_changed))
        except Exception:
            pass

    changed_tests = [
        f for f in changed
        if "test" in f.lower() and f.endswith(".py")
    ]

    changed_py = [f for f in changed if f.endswith(".py")]
    changed_non_test_py = [f for f in changed_py if not _ist_test_datei(f)]

    # FIX M-P1 (2026-11-01): Testdateien aus Konvention ableiten, wenn
    # keine Testdatei geaendert wurde. Verhindert 94%-Skip-Quote von
    # pytest_changed (Live-Beleg: 93 Skips bei 95 Laeufen heute).
    # Konvention: core/X/Y.py -> tests/unit/test_Y.py
    #             core/X/__init__.py -> tests/unit/test_X.py
    if not changed_tests and changed_non_test_py:
        _derived: list[str] = []
        for _f in changed_non_test_py:
            _parts = _f.replace("\\", "/").split("/")
            _bn = _parts[-1]
            if _bn == "__init__.py" and len(_parts) >= 2:
                _dir = _parts[-2]
                _cands = [f"tests/unit/test_{_dir}.py",
                          f"tests/test_{_dir}.py"]
            else:
                _stem = _bn.removesuffix(".py")
                _cands = [f"tests/unit/test_{_stem}.py",
                          f"tests/test_{_stem}.py"]
                if len(_parts) >= 2:
                    _cands.insert(
                        0, f"tests/unit/test_{_parts[-2]}_{_stem}.py")
            for _cand in _cands:
                if (Path(project_dir) / _cand).exists():
                    _derived.append(_cand)
                    break
        if _derived:
            changed_tests = _derived


    # OP-165: {task_files} aus aktuelle_task (pro Task, nicht kumulativ).
    _tf_task = None
    _akt_task = getattr(state, "aktuelle_task", None)
    if isinstance(_akt_task, dict):
        _tf_task = [f for f in (_akt_task.get("task_files") or []) if f]

    out: list[str] = []
    for c in cmd:
        s = str(c)
        if "{task_files}" in s:
            if not _tf_task:
                return None
            s = s.replace("{task_files}", " ".join(_tf_task))
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
        if "{changed_non_test_py_files}" in s:
            if not changed_non_test_py:
                return None
            s = s.replace("{changed_non_test_py_files}",
                          " ".join(changed_non_test_py))
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

    from werkstatt import render as loop_renderer

    _done = _threading.Event()
    _result: list = [None]
    _exc: list = [None]

    def _worker():
        try:
            _result[0] = subprocess.run(
                cmd, cwd=cwd, capture_output=True, text=True,
                timeout=timeout, check=False,
            )
        except Exception as e:
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
                except Exception:
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
        _changed: list[str] = []
        for _p_c in (state.patches or []):
            if not isinstance(_p_c, dict):
                continue
            _f_c = _p_c.get("file")
            if isinstance(_f_c, str) and _f_c:
                _changed.append(_f_c)
        _py_files = [f for f in _changed if f.endswith(".py")]
        if not _py_files:
            return
        _sp.run(
            ["ruff", "check", "--fix", "--no-cache", *_py_files],
            cwd=pd, capture_output=True, text=True, timeout=30, check=False,
        )
    except Exception:
        pass


def _verify_patches(
    state: RunState,
    phase: str | None = None,
    stage_ids: set[str] | None = None,
) -> bool:
    """B2: Verifier (multi-projekt-faehig via Projekt-Contract).

    Liest .werkstatt/verify.json aus dem Zielprojekt.
    Fallback: pytest + ruff im Zielprojekt, wenn keine Config.

    phase: wenn gesetzt ("pre_build" oder "post_build"),
    werden nur Stages mit passendem phase-Feld ausgefuehrt.
    Stages ohne phase-Feld laufen immer (Backward-Compat).
    stage_ids: wenn gesetzt, wird ausschliesslich diese Teilmenge
    verifiziert. Fehlende oder nicht ausfuehrbare Ziel-Stages sind rot.

    Returns: True wenn alle harten Stages gruen sind, sonst False.
    """
    import json
    project_dir = getattr(state, "project_dir", None)
    if project_dir is None or not Path(project_dir).exists():
        return False

    project_dir = Path(project_dir)
    errors = []
    _stage_results: list[dict] = []
    state.last_verify_results = []
    state.last_verify_hart_stages = set()

    # M-306c: venv_python aus projects/<name>.yaml (verhindert,
    # dass Verify im Zielprojekt mit System-Python laeuft und
    # Dependencies nicht findet).
    _venv_python = "python3"  # Fallback
    _project_name = state.project_name
    if _project_name:
        try:
            from werkstatt.orchestrator import load_project_config
            _cfg = load_project_config(_project_name)
            if _cfg.get("venv_python"):
                _venv_python = _cfg["venv_python"]
        except (SystemExit, Exception):
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

    # Fuer Recovery muessen die angeforderten Stage-IDs exakt existieren.
    # Sonst darf eine leere/veraenderte Config nicht als gruene Pruefung gelten.
    _selected_stage_ids = (
        {str(stage_id) for stage_id in stage_ids}
        if stage_ids is not None else None
    )
    if _selected_stage_ids is not None:
        if not _selected_stage_ids:
            errors.append("verify recovery requested no stage IDs")
        else:
            _known_stage_ids = {
                str(stage.get("id") or "?")
                for stage in stages
                if isinstance(stage, dict)
            }
            _missing_stage_ids = sorted(_selected_stage_ids - _known_stage_ids)
            errors.extend(
                f"{stage_id}: requested recovery stage is missing from verify contract"
                for stage_id in _missing_stage_ids
            )
            stages = [
                stage for stage in stages
                if isinstance(stage, dict)
                and str(stage.get("id") or "?") in _selected_stage_ids
            ]
        if errors:
            state.last_verify_errors = list(errors)
            state.last_verify_results = [
                {
                    "stage_id": stage_id,
                    "exit_code": None,
                    "ok": False,
                    "error_excerpt": (
                        "Requested recovery stage is absent from the active "
                        "verify contract."
                    ),
                }
                for stage_id in sorted(_selected_stage_ids)
            ]
            audit(
                "loop_verify_failed",
                {
                    "errors": errors,
                    "phase": phase,
                    "stages": sorted(_selected_stage_ids),
                },
                project_dir,
                getattr(state, "project_name", "?"),
            )
            return False

    # 3. Stages ausfuehren
    _executed_stages = []
    _hart_stage_ids: set[str] = set()
    for stage in stages:
        if (
            _selected_stage_ids is not None
            and str(stage.get("id") or "?") not in _selected_stage_ids
        ):
            continue
        # OP-034: requires-Gate
        _req = stage.get("requires")
        if _req:
            _req_expanded = _expand_cmd_placeholders(
                [_req], state, project_dir)
            if _req_expanded is None:
                audit("loop_verify_stage_skipped",
                      {"stage": stage.get("id", "?"),
                       "reason": "requires not met"},
                      project_dir,
                      getattr(state, "project_name", "?"))
                continue
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
        _sid = stage.get("id", "?")
        _executed_stages.append(_sid)
        if _stage_ist_hart(stage):
            _hart_stage_ids.add(_sid)
        _t_stage = None  # F821: _time war nie im Scope (lokaler Import in anderer Funktion)
        try:
            # M-390: Heartbeat alle 2s waehrend der Stage
            # OP-034b: Per-Stage-Timeout aus verify.json (default 300).
            _stage_timeout = int(stage.get("timeout") or 300)
            res = _verify_stage_with_heartbeat(
                cmd, str(project_dir), stage.get("id", "?"),
                timeout=_stage_timeout,
            )
            _record = {
                "stage_id": str(stage.get("id", "?"))[:120],
                "exit_code": int(res.returncode),
                "ok": res.returncode == 0,
                "error_excerpt": "",
            }
            if res.returncode != 0:
                # K22a: stderr einbeziehen -- ruff schreibt auf stderr.
                _out = (res.stdout or "") + (res.stderr or "")
                _kern = _extrahiere_fehlerkern(_out)
                _record["error_excerpt"] = _kern[:1200]
                errors.append(f"{stage.get('id', '?')}: {_kern}")
            _stage_results.append(_record)
        except Exception as exc:
            _error = _extrahiere_fehlerkern(str(exc), max_chars=1200)
            _stage_results.append({
                "stage_id": str(stage.get("id", "?"))[:120],
                "exit_code": None,
                "ok": False,
                "error_excerpt": _error,
            })
            errors.append(f"{stage.get('id', '?')}-Fehler: {_error}")

    if _selected_stage_ids is not None:
        _executed_set = set(_executed_stages)
        for _stage_id in sorted(_selected_stage_ids - _executed_set):
            _reason = (
                "requested recovery stage was not executed "
                "(requires gate, missing command, or no runnable files)"
            )
            errors.append(f"{_stage_id}: {_reason}")
            _stage_results.append({
                "stage_id": _stage_id[:120],
                "exit_code": None,
                "ok": False,
                "error_excerpt": _reason[:1200],
            })

    # OP-062f: Hart-Info fuer _verify_patches_soft (Prefix-Match reicht
    # nicht, wenn stage_dict 'hart': true setzt, aber Aufrufer nur
    # den Stage-ID-String sieht).
    if state is not None:
        state.last_verify_hart_stages = set(_hart_stage_ids)
        state.last_verify_results = _stage_results
        # Immer den aktuellen Laufstand spiegeln. Sonst bleiben Fehler
        # eines vorherigen Verify-Aufrufs nach einem gruenen Lauf im State.
        state.last_verify_errors = list(errors)
    if errors:
        audit("loop_verify_failed",
              {"errors": errors, "phase": phase,
               "stages": _executed_stages},
              project_dir, getattr(state, "project_name", "?"))
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


def _stage_ist_hart(stage_id) -> bool:
    """FIX AT + OP-062f: Klassifiziert eine Verify-Stage als hart/weich.

    Akzeptiert str (Rueckwaerts-Kompatibilitaet) ODER dict mit
    optionalem Feld 'hart': true. hart=true verschaerft, aber
    hart=false entschaerft NICHT (Prefix-Klassifikation gilt dann).
    """
    _flag = None
    if isinstance(stage_id, dict):
        _flag = stage_id.get("hart")
        _sid = (stage_id.get("id") or "").lower()
        # OP-095: hart-Feld fehlt -> warnen + Prefix-Fallback
        if _flag is None:
            from werkstatt.audit import audit_safe
            audit_safe("verify_stage_ohne_hart_flag", {"id": _sid})
    else:
        _sid = (stage_id or "").lower()
    if _flag is True:
        return True
    # hart=false entschaerft NICHT (Docstring): Prefix-Klassifikation gilt.
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
    _all_errors = list(state.last_verify_errors or [])
    _hart = []
    _weich = []
    for _e in _all_errors:
        _e_str = str(_e)
        # Format: "stage_id: <message>"
        _stage = _e_str.split(":", 1)[0].strip()
        # OP-062f: State-Hinweis hat Vorrang vor Prefix-Match.
        _hart_stages: set[str] = set(getattr(state, "last_verify_hart_stages", set()))
        if _stage in _hart_stages or _stage_ist_hart(_stage):
            _hart.append(_e_str)
        else:
            _weich.append(_e_str)
    if _hart:
        # Echter Fehler. Nur harte Errors als last_verify_errors
        # behalten (Reflection sieht sie).
        state.last_verify_errors = _hart
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
            ["python3",
             str(__import__("werkstatt.paths", fromlist=["tools_dir"]).tools_dir() / "quality_gate.py"),
             "--json"],
            cwd=str(__import__("werkstatt.paths", fromlist=["werkstatt_home"]).werkstatt_home()),
            capture_output=True, text=True, timeout=300, check=False
        )
        return res.stdout[:4000]
    except Exception:
        return "Baseline-Check fehlgeschlagen (Timeout/OSError)"


__all__ = [
    "_expand_cmd_placeholders",
    "_get_baseline_error_details",
    "_resolve_venv_cmd",
    "_ruff_fix_changed",
    "_stage_anzahl",
    "_stage_count_by_phase",
    "_stage_ids",
    "_stage_ist_hart",
    "_verify_patches",
    "_verify_patches_soft",
    "_verify_stage_with_heartbeat",
]
