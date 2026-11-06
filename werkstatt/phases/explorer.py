"""Phase: _phase_explorer_and_setup (OP-139 Phase 2b)."""
from __future__ import annotations

import time
from pathlib import Path

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
    run_explorer,
)


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

    # OP-136a: Contract-Validierung explorer->scout.
    # Nur wenn der Loop tatsaechlich plant (kein Resume, kein
    # "bereits erfuellt"). Sonst laeuft er mit vorbelegten Tasks
    # (Test-Mocks, Resume) weiter.
    _skip_explorer_check = (
        bool(getattr(state, "tasks", None))
        or getattr(state, "auftrag_bereits_erfuellt", False)
    )
    if (not _skip_explorer_check
            and not _validate_contract_safe("explorer", "scout", state, pd, pn)):
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
        _n_resume = phase_state.resume_failed()
        if _n_resume > 0:
            audit(
                "loop_resume_failed_tasks",
                {"anzahl": _n_resume},
                pd, pn,
            )

    return 0, phase_state
