"""Gates: Plan- und Human-Gate (Fix AZ Stufe 5b, 2026-10-31).

Extrahiert aus loop.py. Re-Export in loop.py erhaelt API-
Kompatibilitaet (Tests patchen werkstatt.loop._human_gate_plan).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from werkstatt.state import RunState


def audit(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop.audit."""
    from werkstatt.loop import audit as _orig
    return _orig(*args, **kwargs)


def _call_hook(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop._call_hook."""
    from werkstatt.loop import _call_hook as _orig
    return _orig(*args, **kwargs)


def _committe_zielprojekt(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop._committe_zielprojekt."""
    from werkstatt.loop import _committe_zielprojekt as _orig
    return _orig(*args, **kwargs)


def _verify_patches(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop._verify_patches."""
    from werkstatt.loop import _verify_patches as _orig
    return _orig(*args, **kwargs)


def _verify_patches_soft(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop._verify_patches_soft."""
    from werkstatt.loop import _verify_patches_soft as _orig
    return _orig(*args, **kwargs)


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
        # GOLD 2026-10-30: Original-Aufgabe, damit der Hook
        # Doku-Aufgaben erkennen kann.
        "aufgabe": getattr(state, "aufgabe", "") or "",
    })
    if not _hook_res.get("allow", True):
        # Info fuer Planner-Reflection
        state.last_planner_info = _hook_res.get("info", {})  # type: ignore[attr-defined]
        return False

    return True


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
        # FIX O 2026-10-31: Untracked sichtbar machen via intent-to-add.
        # Sonst zeigt Human-Gate nur PROGRESS.md, nicht die neue Datei.
        subprocess.run(
            ["git", "-C", str(pd), "add", "-N", "."],
            capture_output=True, text=True, check=False, timeout=10,
        )
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

    # FIX AD 2026-10-31: Task-Fortschritt VOR dem Diff anzeigen.
    _fortschritt = _task_fortschritt_block(Path(pd), pn)
    _gate_body = ""
    if _fortschritt:
        _gate_body = _fortschritt + "\n"
    _gate_body += f"Aenderungen im Zielprojekt:\n{_stat_txt}"
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



def _task_fortschritt_block(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop._task_fortschritt_block."""
    from werkstatt.loop import _task_fortschritt_block as _orig
    return _orig(*args, **kwargs)


__all__ = ['_human_gate', '_human_gate_plan', '_plan_gate']
