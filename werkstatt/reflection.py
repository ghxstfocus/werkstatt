"""Reflection-Schleifen (Fix AZ Stufe 6, 2026-10-31).

Extrahiert aus loop.py. Re-Export in loop.py erhaelt API-
Kompatibilitaet (Tests patchen werkstatt.loop._apply_patches_with_hooks,
_verify_patches, run_builder, run_reviewer).

Reflection-Varianten — welche State-Felder werden gelesen
----------------------------------------------------------
Variante                  | letzter_test_fehler | geladene_skills | last_verify_errors | reviewer_bugs
_reflection_loop          | ja                  | ja              | ja                 | ja
_phase_end_reflection     | nein                | nein            | ja                 | ja
_plan_reject_reflection   | nein                | nein            | nein               | nein

Die Tabelle ist reine Dokumentation (OP-147). Die Varianten werden
NICHT vereinheitlicht — das ist einer spaeteren OP vorbehalten.
Hinweis: `_reflection_loop` haengt den `letzter_test_fehler`-Block nur,
wenn er nicht schon in `last_verify_errors` steckt. Die Standard-Variante
`_reflection_loop` laeuft mit `phase='post_build'`.
"""
from __future__ import annotations

from werkstatt.prompts import format_letzter_test_fehler_block
from werkstatt.render import log_line  # Fix BA
from werkstatt.state import RunState


def _setze_runde_patches(state, patches: list) -> None:
    """OP-067: Spiegelt Runden-Patches in state.patches_aktuell_runde.

    Wird pro Reflection-Runde EINMAL aufgerufen, direkt nach
    _apply_patches_with_diagnose. Damit sieht _expand_cmd_placeholders
    die Runden-Patches als Fallback, wenn state.patches geleert ist.

    Schutz: state kann ein SimpleNamespace sein (Tests) — dann noop.
    Ein direkter state.patches_aktuell_runde.clear() wuerde in diesen
    Tests AttributeError werfen (Live-Beleg 2026-11-02: 11 Tests).
    """
    try:
        _cur = getattr(state, "patches_aktuell_runde", None)
        if isinstance(_cur, list):
            _cur.clear()
            _cur.extend(patches)
        else:
            state.patches_aktuell_runde = list(patches)  # type: ignore[attr-defined]
    except (AttributeError, TypeError):
        pass


def _klassifiziere_fehler(errors: list) -> str:
    """M-WelleF (2026-11-02): dominante Fehlerklasse + Repair-Hint."""
    if not errors:
        return ""
    joined = chr(10).join(str(e) for e in errors if e)[:4000]
    low = joined.lower()

    if "object" in low and ("int" in low or "no overload variant" in low):
        return (
            "HINT (mypy_cast): mypy beklagt object/int. Verwende "
            "typing.cast(int, x) NACH einem Runtime-Check (isinstance/"
            "check_port/etc). NIEMALS int(x) (aendert Wert), NIEMALS "
            "# type: ignore (OP-064b-Antipattern)."
        )
    if "error:" in low and "mypy" in low:
        return (
            "HINT (mypy_other): mypy-Fehler. Lies Zeile, Spalte, Klasse "
            "genau. Aendere nur die betroffene Stelle. Keine type: ignore."
        )
    if "f401" in low or "f811" in low or "imported but unused" in low:
        return (
            "HINT (ruff_import): Import-Fehler. Import entfernen oder "
            "Ziel benutzen. KEINE neue # noqa."
        )
    if "old_string_not_found" in low or "patch_not_applied" in low:
        return (
            "HINT (patch_not_applied): Patch passt nicht mehr. Lies den "
            "AKTUELLER DATEI-INHALT-Block neu und baue einen NEUEN Patch "
            "mit exaktem Anker. NICHT denselben Patch wiederholen."
        )
    if "assertionerror" in low or "assert " in low:
        return (
            "HINT (pytest_assert): Test schlaegt fehl. Pruefe: "
            "(a) Code falsch -> Code reparieren. (b) Test falsch -> "
            "Test reparieren NUR wenn Task das fordert. NIEMALS "
            "Assertion entfernen oder Test skippen."
        )
    if "sim103" in low or "c901" in low:
        return (
            "HINT (ruff_complex): Refactor-Hinweis. Nur aendern wenn "
            "im Scope der Task. Sonst: ignorieren."
        )
    return ""


def _format_repair_hint(errors: list) -> str:
    """M-WelleF: formatierter Repair-Block fuer Prompt."""
    hint = _klassifiziere_fehler(errors)
    if not hint:
        return ""
    return f"## REPAIR-HINT:{chr(10)}{hint}{chr(10)}"


def audit(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop.audit."""
    from werkstatt.loop import audit as _orig
    return _orig(*args, **kwargs)


def _apply_patches_with_hooks(*args, **kwargs):
    """Late-Binding-Proxy fuer werkstatt.loop._apply_patches_with_hooks."""
    from werkstatt.loop import _apply_patches_with_hooks as _orig
    return _orig(*args, **kwargs)


def _apply_patches_with_diagnose(*args, **kwargs):
    """OP-060a: Late-Binding-Proxy."""
    from werkstatt.loop import _apply_patches_with_diagnose as _orig
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


def _verify_fehler_wiederholt_sich(errors: list) -> bool:
    """OP-059d: True, wenn verify_errors den gleichen Kern-Fehler 2x hat.

    Erkennt Wiederholungs-Muster: 'mypy_changed: ... : error: ...'
    mit identischer Error-Signatur (ohne Zeilennummer-Praefix).
    Dient als Signal fuer Spec-Widerspruch im Verify-Pfad, wo kein
    Reviewer-Bug-Text vorliegt.
    """
    if not errors or len(errors) < 2:
        return False
    _sigs: list[str] = []
    for _e in errors:
        if not isinstance(_e, str):
            continue
        # Nimm den ersten 'error:'-Satz als Signatur
        _idx = _e.find("error:")
        if _idx < 0:
            continue
        _sig = _e[_idx:_idx + 120].strip()
        _sigs.append(_sig)
    if len(_sigs) < 2:
        return False
    return _sigs[0] == _sigs[1]


def _test_fehler_signatur(state) -> str | None:
    """Signatur der pytest-Fehler aus state.last_verify_errors."""
    _errs = getattr(state, "last_verify_errors", None) or []
    _sigs: list[str] = []
    for _e in _errs:
        try:
            if isinstance(_e, dict):
                _stage = _e.get("stage_id") or ""
                if not (isinstance(_stage, str) and (
                        _stage == "pytest_changed" or "pytest" in _stage)):
                    continue
                _text = _e.get("text") or ""
                _datei = _e.get("datei") or ""
            elif isinstance(_e, str):
                if "pytest" not in _e:
                    continue
                _text = _e
                _datei = ""
            else:
                continue
            if not isinstance(_text, str):
                continue
            _test_name = ""
            _assertion = ""
            _rest = _text
            if "::" in _text:
                _vor, _rest = _text.split("::", 1)
                if not _datei:
                    _datei = _vor.strip()
                _cut = len(_rest)
                for _sep in (" ", " - "):
                    _i = _rest.find(_sep)
                    if 0 <= _i < _cut:
                        _cut = _i
                _test_name = _rest[:_cut].strip()
            if " - " in _text:
                _assertion = _text.split(" - ", 1)[1].strip()
            else:
                for _line in _text.splitlines():
                    if _line.strip():
                        _assertion = _line.strip()
                        break
            _sigs.append(
                f"{_datei or ''}::{_test_name or ''}::{_assertion or ''}"
            )
        except (KeyError, TypeError, AttributeError):
            continue
    if not _sigs:
        return None
    return "|".join(sorted(_sigs))


def _bug_text_deutet_spec_widerspruch(bugs: list) -> bool:
    """OP-059c: Erkennt Spec-Widerspruch-Muster in Reviewer-Bug-Texten.

    Heuristik: Bug-Text nennt explizit eine Task-Anforderung UND
    einen Diff-Gegensatz. Typische Marker aus dem Live-Beleg:
    'Task-Beschreibung fordert', 'Task fordert', 'Die Aufgabe verlangt'
    in Kombination mit 'Der Diff' / 'Der Patch' / 'Diff fuegt'.
    """
    if not bugs:
        return False
    _text = " ".join(
        (b.get("description") or "") for b in bugs if isinstance(b, dict)
    ).lower()
    _forder_marker = (
        "task-beschreibung fordert",
        "task fordert",
        "task verlangt",
        "die aufgabe fordert",
        "die aufgabe verlangt",
        "task-spez fordert",
    )
    _diff_marker = ("der diff", "der patch", "diff fuegt", "diff macht")
    has_forder = any(m in _text for m in _forder_marker)
    has_diff = any(m in _text for m in _diff_marker)
    return has_forder and has_diff


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

    # Stellschrauben 2026-11-03: reflection-Skill.
    _skill_body_fuer_reflection(state)

    if not api_key:
        audit("loop_reflection_kein_key", {}, pd, pn)
        return False

    # M-329: Builder importieren (vermeidet Zirkularitaet).
    from werkstatt.roles.builder import run_builder

    _ruff_vorher: int | None = None
    _hash_vorher: str | None = None
    _test_sig_vorher: str | None = None
    _stagnation = 0
    # K39a: merken, ob wir wegen Reviewer-Reject gestartet sind.
    _had_error_context = bool(error_context)
    # OP-062c: task_id fuer Reflexions-Runden (Render task-spezifisch).
    _akt_task = getattr(state, "aktuelle_task", None)
    _refl_task_id = (
        _akt_task.get("id") if isinstance(_akt_task, dict) else None
    )
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
        _hash_jetzt = _diff_hash_for_state(state)
        _test_sig = _test_fehler_signatur(state)
        if (_hash_vorher is not None and _hash_vorher == _hash_jetzt
                and _test_sig_vorher is not None
                and _test_sig_vorher == _test_sig):
            audit("reflection_no_progress",
                  {"runde": runde, "hash": _hash_jetzt,
                   "test_sig": _test_sig}, pd, pn)
            return False
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
                # OP-059c + OP-059d: Spec-Widerspruch pruefen.
                # Zwei Pfade: (a) Reviewer-Bug-Marker, (b) verify-
                # Fehler wiederholt sich (mypy, patch_apply).
                _bugs_fuer_check = getattr(state, "reviewer_bugs", None) or []
                _verify_fuer_check = (
                    getattr(state, "last_verify_errors", None) or []
                )
                _is_spec = (
                    _bug_text_deutet_spec_widerspruch(_bugs_fuer_check)
                    or _verify_fehler_wiederholt_sich(_verify_fuer_check)
                )
                if _is_spec:
                    audit("loop_reflection_spec_widerspruch",
                          {"runde": runde,
                           "bug_text_preview": [
                               (b.get("description") or "")[:150]
                               for b in _bugs_fuer_check[:2]
                               if isinstance(b, dict)
                           ]}, pd, pn)
                    state.spec_widerspruch_erkannt = True  # type: ignore[attr-defined]
                    audit("loop_reflection_stagnation_abort",
                          {"runde": runde, "stagnation": _stagnation,
                           "grund": _stagnation_grund,
                           "folge": "spec_widerspruch_vermutet"}, pd, pn)
                    return True
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

        # OP-081: Deterministische Diagnose VOR LLM-Builder.
        # Bekannte Fehlerklassen (NameError, Directory-not-found)
        # werden deterministisch gepatcht. Kein LLM-Call in dieser
        # Runde. Bei Erfolg: continue, naechste Runde verifiziert.
        try:
            from werkstatt.diagnose import (
                _deterministische_diagnose,
            )
            _det = _deterministische_diagnose(state)
        except Exception:  # noqa: BLE001
            _det = None
        if _det is not None:
            _a_det, _d_det = _apply_patches_with_diagnose(
                state, [_det],
                phase_label=f"reflection-det-{runde}",
            )
            state.applied_count = (  # type: ignore[attr-defined]
                getattr(state, "applied_count", 0) + _a_det
            )
            _setze_runde_patches(state, [_det])
            audit(
                "loop_reflection_det_diagnose",
                {"runde": runde, "applied": _a_det,
                 "klasse": _det.get("klasse", ""),
                 "grund": _det.get("grund", "")},
                pd, pn,
            )
            if _a_det > 0:
                continue

        # M-329: Builder erneut rufen. Er nutzt search/replace.
        # K34: reflection_phase -> _korrigiere_builder_action skip.
        # OP-059: Diff-Hash VOR Builder. Vergleich nachher
        # zeigt, ob der Patch wirksam war oder idempotent
        # (Datei bereits im Zielzustand, Hash unveraendert).
        _hash_vorher = _hash_jetzt
        _test_sig_vorher = _test_sig
        # OP-147: letzter_test_fehler-Block an den Prompt haengen,
        # bevor der Builder gerufen wird. Dedup: nur wenn nicht
        # schon in last_verify_errors enthalten.
        _ltf_block = format_letzter_test_fehler_block(
            getattr(state, "letzter_test_fehler", ""),
            list(getattr(state, "last_verify_errors", None) or []),
        )
        if _ltf_block:
            # Builder liest state.last_verify_errors als Prompt-Kontext.
            # Den Block dort anhaengen (dedupliziert).
            _cur_errs = list(getattr(state, "last_verify_errors", None) or [])
            if _ltf_block not in _cur_errs:
                _cur_errs.append(_ltf_block)
                state.last_verify_errors = _cur_errs
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
        # OP-060a: diagnose-Variante liefert (applied, diagnosen).
        _applied, _diagnosen = _apply_patches_with_diagnose(
            state, _patches,
            phase_label=f"reflection-runde-{runde}",
        )
        state.applied_count = getattr(state, "applied_count", 0) + _applied  # type: ignore[attr-defined]
        # OP-067: Runden-Patches fuer Verify sichtbar machen
        _setze_runde_patches(state, list(_patches))

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
                  {"runde": runde, "diagnosen": _diagnosen}, pd, pn)
            audit("loop_reflection_patch_unwirksam",
                  {"runde": runde, "diagnosen": _diagnosen}, pd, pn)
            # K47: auch hier History-Eintrag (Patches=0).
            _refl_hist = getattr(state, "reflection_history", None)
            if _refl_hist is None:
                state.reflection_history = []  # type: ignore[attr-defined]
                _refl_hist = state.reflection_history  # type: ignore[attr-defined]
            _refl_hist.append({
                "runde": runde,
                "task_id": _refl_task_id,
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
            # OP-059: False-Positive-Erkennung. Wenn der Patch
            # idempotent war (Diff unveraendert vor/nach Builder),
            # zuvor bereits ein Patch wirksam wurde, die Datei
            # keinen echten Verify-Fehler hat und der Hash dem
            # Ausgangszustand entspricht, ist der Reviewer-Reject
            # ein Fehlalarm (nicht: Task gescheitert).
            _hash_nachher = _diff_hash_for_state(state)
            _applied_vorher = int(
                getattr(state, "applied_count", 0) or 0)
            # OP-059: Fehler-Filter. Patch-nicht-angewendet-Marker
            # und der aktuelle error_context (Reviewer-Bugs) sind
            # KEINE echten Verify-Fehler — sie werden vom Loop
            # selbst gesetzt und wuerden die false_positive-
            # Erkennung immer blockieren.
            _echte_errors = [
                _e for _e in (
                    getattr(state, "last_verify_errors", None) or [])
                if not (isinstance(_e, str) and (
                    _e.startswith("reflection: patch_nicht_angewendet")
                    or (error_context and _e == error_context)
                ))
            ]
            # OP-059-Nachtrag (15:16 Live-Beleg OP-002b3):
            # _hash_ref-Bedingung entfernt. Sie war zu strikt:
            # Wenn Runde 1 wirksam war (Hash geaendert) und
            # Runde 2 idempotent ist (_hash_vorher == _hash_nachher),
            # dann ist der Reviewer-Reject ein Fehlalarm — auch wenn
            # _hash_nachher != _hash_ref (Runde 1 hatte ihn geaendert).
            # Die Idempotenz-Pruefung _hash_vorher == _hash_nachher
            # + applied_vorher > 0 + leere echte errors + Verify gruen
            # decken den Fall vollstaendig ab.
            _is_false_positive = (
                _had_error_context
                and _applied_vorher > 0
                and bool(_hash_vorher)
                and bool(_hash_nachher)
                and _hash_vorher == _hash_nachher
                and not _echte_errors
            )
            if _is_false_positive:
                _verify_gruen = False
                try:
                    _verify_gruen = bool(
                        _verify_patches(state, phase=phase))
                except Exception:  # noqa: BLE001
                    _verify_gruen = False
                if _verify_gruen:
                    audit("reviewer_stagnation_false_positive",
                          {"runde": runde,
                           "diff_hash": _hash_nachher,
                           "applied_vorher": _applied_vorher},
                          pd, pn)
                    state.reviewer_stagnation_false_positive = True  # type: ignore[attr-defined]
                    return True
            _stagnation += 1
            audit("loop_reflection_stagnation_runde",
                  {"runde": runde, "stagnation": _stagnation,
                   "grund": "patch_nicht_angewendet"}, pd, pn)
            if _stagnation >= 2:
                _bugs_fuer_check2 = getattr(state, "reviewer_bugs", None) or []
                _verify_fuer_check2 = (
                    getattr(state, "last_verify_errors", None) or []
                )
                _is_spec2 = (
                    _bug_text_deutet_spec_widerspruch(_bugs_fuer_check2)
                    or _verify_fehler_wiederholt_sich(_verify_fuer_check2)
                )
                if _is_spec2:
                    audit("loop_reflection_spec_widerspruch",
                          {"runde": runde,
                           "grund": "patch_nicht_angewendet"}, pd, pn)
                    state.spec_widerspruch_erkannt = True  # type: ignore[attr-defined]
                    audit("loop_reflection_stagnation_abort",
                          {"runde": runde, "stagnation": _stagnation,
                           "grund": "patch_nicht_angewendet",
                           "folge": "spec_widerspruch_vermutet"}, pd, pn)
                    return True
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
            "task_id": _refl_task_id,
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

    # OP-059e: Erschoepfung mit Fortschritt = Spec-Widerspruch-Verdacht.
    # Wenn 2+ Runden mit patches_applied>0 gelaufen sind und verify
    # IMMER NOCH rot ist, kann der Builder die Spec nicht erfuellen —
    # kein echter Fortschritt, sondern Spec-Fehler. Live-Beleg 18:49
    # OP-004: 5 Runden, jede applied=1, mypy blieb rot mit int(min_port).
    _final_verify_ok = _verify_patches(state, phase=phase)
    if not _final_verify_ok:
        _hist_e = getattr(state, "reflection_history", None) or []
        _letzte_e = _hist_e[-2:] if len(_hist_e) >= 2 else []
        if len(_letzte_e) >= 2:
            _alle_applied = all(
                isinstance(r, dict)
                and int(r.get("patches_applied", 0) or 0) > 0
                for r in _letzte_e
            )
            if _alle_applied:
                audit("loop_reflection_spec_widerspruch_erschoepft",
                      {"runden": len(_hist_e),
                       "letzte_applied": [
                           int(r.get("patches_applied", 0) or 0)
                           for r in _letzte_e if isinstance(r, dict)
                       ],
                       "letzte_verify_errors": [
                           (r.get("verify_errors") or [])[:1]
                           for r in _letzte_e if isinstance(r, dict)
                       ]}, pd, pn)
                state.spec_widerspruch_erkannt = True  # type: ignore[attr-defined]
                return True
    return _final_verify_ok


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
            _applied, _diag_phase = _apply_patches_with_diagnose(
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


def _diff_hash_for_state(state) -> str:
    """OP-059: SHA256 über den aktuellen Task-Diff im Zielprojekt.

    Wird von _reflection_loop genutzt, um idempotente Patches
    (Datei bereits im Zielzustand) von kaputten Patches zu
    unterscheiden. Leerer String bei Fehler/kein Diff.
    """
    import hashlib

    from werkstatt.reviewer import _get_git_diff

    pd = getattr(state, "project_dir", None)
    if pd is None:
        return ""
    task = getattr(state, "aktuelle_task", None) or {}
    task_files = task.get("task_files") if isinstance(task, dict) else None
    try:
        diff = _get_git_diff(pd, task_files=task_files)
    except Exception:
        return ""
    if not diff:
        return ""
    return hashlib.sha256(
        diff.encode("utf-8", errors="replace")
    ).hexdigest()


__all__ = [
    '_apply_patches_with_diagnose',
    '_diff_hash_for_state',
    '_phase_end_reflection',
    '_reflection_loop',
]


def _skill_body_fuer_reflection(state) -> str:
    """Laedt den systematic-debugging-Body hoechstens einmal pro Run."""
    namen = ["systematic-debugging"]
    geladen = getattr(state, "geladene_skills", None) or []
    if any(n in geladen for n in namen):
        return getattr(state, "reflection_skill_body", "") or ""

    from werkstatt.skills import (
        _merke_geladene_skills,
        load_all_skills,
        load_skill_by_name,
    )

    _all = load_all_skills()
    skill = load_skill_by_name("systematic-debugging", _all)
    if not skill:
        return ""
    body = skill.get("body") or ""
    if not isinstance(body, str):
        body = ""
    try:
        state.reflection_skill_body = body
    except (AttributeError, TypeError):
        pass
    _merke_geladene_skills(state, namen, rolle="reflection")
    return body


def _plan_reject_reflection(state) -> bool:
    """Welle H (2026-11-02): Reject-Grund → Reflection → neuer Plan.

    Wenn der User im Plan-Gate `n` sagt, wird der Grund in
    state.last_reject_reason gespeichert. Diese Funktion gibt ihn
    an den Planner weiter, damit er einen revidierten Plan baut.

    Max 1 Runde (nicht 5 wie bei Verify-Reflection). Wenn der zweite
    Plan auch rejected wird -> fail-closed im Aufrufer.

    Rueckgabe True -> Planner hat einen neuen Plan gebaut.
    Rueckgabe False -> Planner-Reflection gescheitert.
    """
    reason = (getattr(state, "last_reject_reason", "") or "").strip()
    kind = getattr(state, "last_reject_kind", "") or ""
    if kind != "plan":
        return False
    if not reason:
        # Leerer Grund = User will hart abbrechen, kein Reflection-Zyklus.
        # Frueher wurde ein Placeholder eingesetzt und der Planner erneut
        # gerufen — das widersprach dem Gate-Prompt "n = ablehnen".
        audit("loop_plan_reject_ohne_grund",
              {"folge": "hart_abbrechen"},
              getattr(state, "project_dir", None),
              getattr(state, "project_name", "?"))
        return False

    pd = getattr(state, "project_dir", None)
    pn = getattr(state, "project_name", "?")
    try:
        audit("loop_plan_reject_reflection_start",
              {"reason": reason[:200]}, pd, pn)
    except Exception:  # noqa: BLE001, S110
        pass

    # Prompt-Variante: urspruengliche Aufgabe + Reject-Grund
    _orig_aufgabe = getattr(state, "aufgabe", "") or ""
    _aufgabe_mit_feedback = (
        f"{_orig_aufgabe}\n\n"
        f"## REJECT-FEEDBACK (voriger Plan wurde abgelehnt)\n"
        f"Der Mensch hat den vorigen Plan abgelehnt.\n"
        f"Reject-Grund: {reason}\n\n"
        f"Baue einen REVIDIERTEN Plan, der diesen Grund adressiert.\n"
        f"Behalte die urspruengliche Aufgabe im Scope.\n"
    )

    # Aufruf des Planner mit Feedback. run_planner liest state.aufgabe.
    _saved_aufgabe = _orig_aufgabe
    try:
        state.aufgabe = _aufgabe_mit_feedback  # type: ignore[attr-defined]
        from werkstatt.planner import run_planner
        ok = run_planner(state)
    finally:
        state.aufgabe = _saved_aufgabe  # type: ignore[attr-defined]

    # Reject-Felder leeren, damit naechster Lauf sauber startet
    state.last_reject_kind = ""  # type: ignore[attr-defined]
    state.last_reject_reason = ""  # type: ignore[attr-defined]

    try:
        audit("loop_plan_reject_reflection_done",
              {"ok": bool(ok)}, pd, pn)
    except Exception:  # noqa: BLE001, S110
        pass

    return bool(ok)
