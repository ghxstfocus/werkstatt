"""Reflection-Schleifen (Fix AZ Stufe 6, 2026-10-31).

Extrahiert aus loop.py. Re-Export in loop.py erhaelt API-
Kompatibilitaet (Tests patchen werkstatt.loop._apply_patches_with_hooks,
_verify_patches, run_builder, run_reviewer).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from werkstatt.state import RunState
from werkstatt.loop_renderer import log_line  # Fix BA


def audit(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop.audit."""
    from werkstatt.loop import audit as _orig
    return _orig(*args, **kwargs)


def _apply_patches_with_hooks(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop._apply_patches_with_hooks."""
    from werkstatt.loop import _apply_patches_with_hooks as _orig
    return _orig(*args, **kwargs)


def _task_ende(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop._task_ende."""
    from werkstatt.loop import _task_ende as _orig
    return _orig(*args, **kwargs)


def _verify_patches(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop._verify_patches."""
    from werkstatt.loop import _verify_patches as _orig
    return _orig(*args, **kwargs)


def _verify_patches_soft(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop._verify_patches_soft."""
    from werkstatt.loop import _verify_patches_soft as _orig
    return _orig(*args, **kwargs)


def run_builder(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop.run_builder."""
    from werkstatt.loop import run_builder as _orig
    return _orig(*args, **kwargs)


def run_reviewer(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop.run_reviewer."""
    from werkstatt.loop import run_reviewer as _orig
    return _orig(*args, **kwargs)


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
        log_line(f"[reflection] Runde {runde}/{max_runden} startet")
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
        # GOLD 2026-10-30: Stagnation auch bei Reviewer-Bugs zaehlen.
        # Vorher zaehlte nur _ruff_jetzt; bei Doku-Patches gibt es
        # keinen Ruff-Fehler, aber der Reviewer meldet denselben Bug
        # in jeder Runde. Live-Beleg 2026-10-30 22:28: 5 Reflection-
        # Runden, alle mit demselben Reviewer-Bug.
        _bugs_jetzt = getattr(state, "reviewer_bugs", None) or []
        _bug_sigs_jetzt = frozenset(
            (b.get("severity", ""), b.get("description", "")[:100])
            for b in _bugs_jetzt if isinstance(b, dict)
        )
        _bug_sigs_vorher = getattr(
            state, "_reflection_bug_sigs_vorher", frozenset())
        # FIX AJ 2026-10-31: bool() explizit — Pythons 'and'
        # gibt das erste falsy-Objekt zurueck (hier: frozenset()),
        # nicht False. Der Wert landet im Audit-Payload und killt
        # json.dumps mit TypeError (frozenset not serializable).
        # Live-Beleg 2026-10-31 10:03 in _reflection_loop.
        _hat_gleiche_bugs = bool(
            _bug_sigs_vorher and _bug_sigs_jetzt == _bug_sigs_vorher
        )
        _stagnation_grund = None
        if (_ruff_vorher is not None
                and _ruff_jetzt >= _ruff_vorher and _ruff_jetzt > 0):
            _stagnation_grund = "ruff"
        elif _hat_gleiche_bugs:
            _stagnation_grund = "reviewer_bugs"
        if _stagnation_grund:
            _stagnation += 1
            audit("loop_reflection_stagnation_runde",
                  {"runde": runde, "stagnation": _stagnation,
                   "grund": _stagnation_grund,
                   "ruff_vorher": _ruff_vorher,
                   "ruff_jetzt": _ruff_jetzt,
                   "gleiche_bugs": _hat_gleiche_bugs}, pd, pn)
            if _stagnation >= 2:
                audit("loop_reflection_stagnation_abort",
                      {"runde": runde, "stagnation": _stagnation,
                       "grund": _stagnation_grund}, pd, pn)
                return False
        else:
            _stagnation = 0
        _ruff_vorher = _ruff_jetzt
        state._reflection_bug_sigs_vorher = _bug_sigs_jetzt  # type: ignore[attr-defined]

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
            # GOLD 2026-10-30: patch_nicht_angewendet ZAEHLT als
            # Stagnation, wenn es mehrfach in Folge passiert.
            # Live-Beleg 2026-10-30 22:28: 5x patch_nicht_angewendet,
            # jedes Mal _stagnation=0 -> Loop drehte 5 Runden.
            _stagnation += 1
            audit("loop_reflection_stagnation_runde",
                  {"runde": runde, "stagnation": _stagnation,
                   "grund": "patch_nicht_angewendet"}, pd, pn)
            if _stagnation >= 2:
                audit("loop_reflection_stagnation_abort",
                      {"runde": runde, "stagnation": _stagnation,
                       "grund": "patch_nicht_angewendet"}, pd, pn)
                return False
            _ruff_vorher = None  # naechste Runde frisch zaehlen
            error_context = ""  # Verify in naechster Runde triggern
            continue

        audit("loop_reflection_patch_applied",
              {"runde": runde, "anzahl": _applied}, pd, pn)
        log_line(f"[reflection] {_applied} Patches angewendet (Runde {runde})")

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



def _ruff_fix_changed(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop._ruff_fix_changed."""
    from werkstatt.loop import _ruff_fix_changed as _orig
    return _orig(*args, **kwargs)


__all__ = ['_phase_end_reflection', '_reflection_loop']
