"""_build_patches_fuer_datei run_builder (OP-140 Phase 2b)."""
from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from werkstatt.state import RunState

from . import _common as _bglob
from .ast import _sammle_projekt_py_files
from .patch import (
    _architect_abschnitt,
    _extrahiere_verbote,
    _korrigiere_builder_action,
    _korrigiere_doku_datum,
    _normalisiere_aider_patches,
    _pruefe_doku_patch_breite,
)
from .prompt import (
    BUILDER_SYSTEM,
    _format_explorer_findings_b,
    _format_scout_apis_for_builder,
)
from .validate import _validate_imports_in_patch


def _build_patches_fuer_datei(
    state: RunState,
    zieldatei: str,
    architect_beschreibung: str,
    api_key: str,
) -> list[dict]:
    """M-416b: Baut Patches fuer EINE Datei im Architect-Modus.

    Macht einen LLM-Aufruf, parst die Antwort, gibt Patches zurueck.
    Bei Fehler: leere Liste (Aufrufer entscheidet fail-closed).
    """
    import json as _json

    pd = state.project_dir
    pn = state.project_name
    _target = pd / zieldatei
    _ist_neu = False
    _akt_action_m = ""
    _task_m = getattr(state, "aktuelle_task", None)
    if isinstance(_task_m, dict):
        _akt_action_m = _task_m.get("action", "")
    if not _target.is_file():
        # FIX M 2026-10-31: create-Task — Datei existiert absichtlich
        # noch nicht. Leerer Inhalt, LLM baut action="create" mit content.
        if _akt_action_m == "create":
            _inhalt = ""
            _ist_neu = True
        else:
            return []
    else:
        try:
            _inhalt = _target.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return []

    _task_fuer_filter = getattr(state, "aktuelle_task", None) or {}
    if isinstance(_task_fuer_filter, dict):
        _filter_text = (
            (_task_fuer_filter.get("name") or "") + "\n"
            + (_task_fuer_filter.get("description") or "")
        )
    else:
        _filter_text = ""
    _abschnitt = _architect_abschnitt(
        architect_beschreibung, zieldatei, task_text=_filter_text,
    )
    # GOLD-Fallback: Task-Description enthaelt oft nicht die
    # "## <pfad>"-Ueberschrift. Dann auf die volle Architect-Prosa
    # zurueckfallen (state.architect_prosa).
    if not _abschnitt:
        _volle = state.architect_prosa or ""
        if _volle:
            _abschnitt = _architect_abschnitt(
            _volle, zieldatei, task_text=_filter_text,
        )
    # M-450: Leerer Abschnitt -> Datei ist nicht Teil der Aufgabe.
    # Kein LLM-Aufruf, kein Patch.
    if not _abschnitt:
        _bglob.audit("builder_architect_datei_nicht_beschrieben",
              {"datei": zieldatei}, pd, pn)
        return []
    # FIX AF 2026-10-31: Vorherige Fehlschlaege fuer diese Zieldatei
    # aus PhaseState laden. Bei --resume kennt der Builder sonst
    # nicht, warum der letzte Versuch gescheitert ist.
    _hist_fail = ""
    try:
        from werkstatt.phase_state import PhaseState as _PS_bf
        _ps_bf = _PS_bf(pn, base_dir=Path(pd) / ".werkstatt")
        if _ps_bf.exists() and _ps_bf.load():
            for _t_bf in (_ps_bf.data.get("tasks") or []):
                if not isinstance(_t_bf, dict):
                    continue
                if _t_bf.get("status") != "failed":
                    continue
                _tf_bf = _t_bf.get("task_files") or []
                if zieldatei in _tf_bf:
                    _fname_bf = (_t_bf.get("name") or "")[:60]
                    _fg_bf = _t_bf.get("failure") or "unbekannt"
                    _hist_fail += (
                        f"- Task {_t_bf.get('id','?')} "
                        f"({_fname_bf}): {_fg_bf}\n"
                    )
    except Exception:
        pass

    # M-444b: Feedback aus vorherigem Versuch einbauen.
    _feedback = (getattr(state, "builder_feedback", None) or {}).get(zieldatei, "")
    _feedback_block = ""
    if _hist_fail:
        _feedback_block = (
            "\n\n## VORHERIGE FEHLSCHLAEGE FUER DIESE DATEI:\n"
            + _hist_fail
            + "Behebe die Ursache, nicht nur die Symptome.\n"
        )
    if _feedback:
        _feedback_block = (
            f"\n\n## FEEDBACK AUS VORHERIGEM VERSUCH:\n"
            f"Der letzte Patch wurde verworfen. Grund:\n{_feedback}\n"
            f"Behebe das in dieser Antwort.\n"
        )
    # M-466: Reviewer-Bugs aus letzter Runde in den Prompt.
    _reviewer_bugs = getattr(state, "reviewer_bugs", None) or []
    if _reviewer_bugs:
        _bug_lines = []
        for _b in _reviewer_bugs:
            if not isinstance(_b, dict):
                continue
            _sev = _b.get("severity", "?")
            _desc = _b.get("description", "")
            if _desc:
                _bug_lines.append(f"- [{_sev}] {_desc}")
        if _bug_lines:
            _feedback_block += (
                "\n\n## REVIEWER-FEEDBACK (aus letzter Runde):\n"
                + "\n".join(_bug_lines)
                + "\nBehebe diese Bugs in dieser Antwort.\n"
            )
    # K33: Verify-Fehler (Ruff/Compile) aus letzter Runde als Feedback.
    _verify_errs = getattr(state, "last_verify_errors", None) or []
    if _verify_errs:
        _err_lines = [str(e)[:500] for e in _verify_errs[:5]]
        _feedback_block += (
            "\n\n## VERIFY-FEHLER (aus letzter Runde):\n"
            + "\n".join(f"- {e}" for e in _err_lines)
            + "\nBehebe diese Fehler in dieser Antwort.\n"
        )
    # K47: Reflection-Historie -- was in vorherigen Runden passiert ist.
    _refl_hist = getattr(state, "reflection_history", None) or []
    if _refl_hist:
        _refl_lines = ["\n\n## VORHERIGE REFLECTION-RUNDEN (was du bereits versucht hast):\n"]
        for _r in _refl_hist[-3:]:  # max 3 Runden
            _rn = _r.get("runde", "?")
            _pa = _r.get("patches_applied", 0)
            _ve = _r.get("verify_errors", [])[:2]
            _rb = _r.get("reviewer_bugs", [])[:2]
            _refl_lines.append(f"\n### Runde {_rn}:\n")
            _refl_lines.append(f"- Patches: {_pa} angewendet\n")
            if _ve:
                _refl_lines.append("- Verify-Fehler:\n")
                for _e in _ve:
                    _refl_lines.append(f"  * {str(_e)[:200]}\n")
            if _rb:
                _refl_lines.append("- Reviewer-Bugs:\n")
                for _b in _rb:
                    _sv = _b.get("severity", "?")
                    _ds = (_b.get("description") or _b.get("beschreibung") or "")[:150]
                    _refl_lines.append(f"  * [{_sv}] {_ds}\n")
        _refl_lines.append(
            "\nWiederhole NICHT die gleichen Versuche. Pruefe den aktuellen "
            "Dateiinhalt und waehle old_string zeichengenau.\n"
        )
        _feedback_block += "".join(_refl_lines)
    # M-466: Task-Name + Beschreibung fuer Kontext.
    _task = getattr(state, "aktuelle_task", None) or {}
    _task_name = _task.get("name", "") if isinstance(_task, dict) else ""
    _task_desc = _task.get("description", "") if isinstance(_task, dict) else ""
    # FIX AQ 2026-10-31: Verfuegbare Module im Zielverzeichnis als
    # Kontext. Live-Beleg 10:36 t1: Builder importierte
    # 'harness.llm.types' — existiert nicht. Der Hook blockte
    # korrekt, aber der Loop verlor den Task. Mit Modul-Liste im
    # Prompt kennt der LLM die echten Namen.
    _module_hint = ""
    try:
        _target_dir_aq = (pd / zieldatei).parent
        if _target_dir_aq.is_dir():
            _avail_aq = sorted(
                f.stem for f in _target_dir_aq.glob("*.py")
                if f.stem != "__init__"
            )
            if _avail_aq:
                _module_hint = (
                    "## VERFUEGBARE MODULE IM ZIELVERZEICHNIS\n"
                    f"{', '.join(_avail_aq)}\n\n"
                    "Nutze AUSSCHLIESSLICH diese Modulnamen. "
                    "Rate KEINE wie 'types', 'utils', 'helpers' oder "
                    "'client2', wenn sie nicht in der Liste stehen.\n\n"
                )
    except (OSError, TypeError):
        pass

    _verbote = _extrahiere_verbote(_abschnitt)
    _verbote_prefix = (_verbote + "\n\n") if _verbote else ""
    if _ist_neu:
        # FIX P 2026-10-31: ALLE Abschnitte aus der Architektur fordern.
        # Live-Beleg 2026-10-31 08:07: Datei mit 3/8 Abschnitten gebaut,
        # obwohl die Aufgabe 8 nannte.
        _datei_block = (
            "## DATEI IST NEU (action=\"create\")\n"
            "Die Zieldatei existiert noch nicht. Antworte mit:\n"
            "{\"patches\": [{\"action\": \"create\", "
            "\"file\": \"" + zieldatei + "\", "
            "\"content\": \"<kompletter Datei-Inhalt>\"}]}\n"
            "KEIN old_string, KEIN new_string. Nur content.\n\n"
            "PFLICHT-VOLLSTAENDIGKEIT: Der content MUSS ALLE in der "
            "ARCHITECT-BESCHREIBUNG genannten Abschnitte enthalten. "
            "Jeder Abschnitt bekommt seine eigene \"## <titel>\"-Zeile. "
            "Wenn die Aufgabe N Abschnitte nennt, hat der content N "
            "##-Ueberschriften. Kuerze NICHT. Fasse NICHT zusammen. "
            "Lasse KEINEN Abschnitt weg.\n"
        )
    else:
        _datei_block = (
            f"## AKTUELLER DATEI-INHALT:\n```\n{_inhalt}\n```\n"
        )
    # M-Wired-JD (2026-11-02): Measurement-Index fuer Builder
    try:
        from werkstatt.measurement import _messwerte_fuer_prompt
        _mess_builder = _messwerte_fuer_prompt(state)
    except Exception:
        _mess_builder = ""
    if _mess_builder and _mess_builder.strip() not in ("", "(keine)"):
        _messwerte_block_b = (
            f"## MESSWERTE-INDEX (deterministische Messungen):\n"
            f"{_mess_builder}\n\n"
        )
    else:
        _messwerte_block_b = ""

    # M-WelleF: Repair-Hint aus last_verify_errors
    try:
        from werkstatt.reflection import _format_repair_hint as _frh_b
        _refl_hint = _frh_b(getattr(state, 'last_verify_errors', []))
    except ImportError:
        _refl_hint = ''

    # M-Wired-B (2026-11-02): Baseline-Error-Details an _refl_hint anhaengen
    # Der Repair-Hint klassifiziert nur die Fehlerklasse. Der echte
    # Fehlertext mit Zeilenkontext (aus _get_baseline_error_details) gibt
    # dem Builder den Kontext fuer den konkreten Fix.
    try:
        from werkstatt.verify import _get_baseline_error_details
        _baseline_details = _get_baseline_error_details(state) or ""
        if _baseline_details.strip():
            _refl_hint = (
                _refl_hint.rstrip()
                + "\n\n## BASELINE-ERRORS (voller Fehlertext mit Zeilenkontext)\n"
                + _baseline_details[:3000]
                + "\n"
            )
    except Exception:
        pass
    # M-Skills-Builder: metadata + glob (Level 1+2)
    _skills_block = ""
    try:
        from werkstatt.skills import (
            load_all_skills,
            skills_aktivieren,
            skills_metadata_block,
        )
        _all_skills = load_all_skills()
        _meta = skills_metadata_block(_all_skills)
        _akt = skills_aktivieren(_all_skills, [zieldatei], rolle="builder")
        _akt_block = ""
        _akt_names = []
        for _s in _akt:
            _body = _s.get("body") or ""
            if _body:
                _akt_block += (
                    f"\n## Skill: {_s.get('name', '?')}\n" + _body + "\n"
                )
                _akt_names.append(_s.get("name", "?"))
        # M-Skills-Dedup: zentrale Merk-Funktion (dedup + audit)
        if _akt_names:
            try:
                from werkstatt.skills import _merke_geladene_skills
                _merke_geladene_skills(state, _akt_names, rolle="builder")
            except Exception:
                pass
        if _meta or _akt_block:
            _skills_block = (
                _meta + _akt_block + "\n"
            )
    except Exception:
        pass
    _user = (
        f"## ZIELDATEI: {zieldatei}\n\n"
        f"{_module_hint}"
        f"{_verbote_prefix}"
        f"{_skills_block}"
        f"## API-SIGNATUREN (Scout-Destillat):\n"
        f"{_format_scout_apis_for_builder(getattr(state, 'scout_api_auszug', {}))}\n\n"
        f"## EXPLORER-FINDINGS:\n"
        f"{_format_explorer_findings_b(getattr(state, 'explorer_findings', {}))}\n\n"
        f"{_messwerte_block_b}"
        f"{_refl_hint}"
        f"## TASK: {_task_name}\n"
        f"## TASK-BESCHREIBUNG: {_task_desc}\n\n"
        f"## ARCHITECT-BESCHREIBUNG (fuer Kontext):\n{_abschnitt}\n\n"
        f"{_datei_block}"
        f"{_feedback_block}"
    )
    reply = _bglob.ask_llm(
        api_key, BUILDER_SYSTEM, _user,
        model="deepseek-chat", temperature=0.2, max_tokens=8000,
        redact=False,  # OP-062a: Code-Pruefung braucht Rohdaten
        aufgabe="builder",
    )
    if not reply.ok:
        _bglob.audit("builder_architect_llm_fehler",
              {"datei": zieldatei, "fehler": reply.error}, pd, pn)
        return []
    raw = reply.content.strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start < 0 or end <= start:
        _bglob.audit("builder_architect_json_fehler",
              {"datei": zieldatei, "raw": raw[:200]}, pd, pn)
        return []
    try:
        parsed = _json.loads(raw[start:end])
    except _json.JSONDecodeError:
        return []
    patches = parsed.get("patches") or []
    if not isinstance(patches, list):
        return []
    if not patches:
        # GOLD 2026-10-30: LLM hat geantwortet, aber keine Patches
        # geliefert. Das ist der "Auftrag bereits erfuellt"-Fall —
        # die Zieldatei enthaelt den Zielzustand schon (z.B.
        # _RECENT_CHANGES_LIMIT aus f69f1b2).
        # Vorher: return [] -> run_builder False -> task_failed.
        # Jetzt: Flag setzen, run_builder entscheidet.
        if isinstance(state, object) and hasattr(state, "__dict__"):
            try:
                state.auftrag_bereits_erfuellt = True
                state.auftrag_bereits_erfuellt_bestaetigt = False
                state.auftrag_bereits_erfuellt_quelle = "builder:llm_keine_patches"
            except (AttributeError, TypeError):
                pass
        _bglob.audit("auftrag_bereits_erfuellt",
              {"zieldatei": zieldatei,
               "grund": "llm_keine_patches"}, pd, pn)
        _bglob.audit("builder_keine_patches_gold",
              {"zieldatei": zieldatei,
               "grund": "llm_keine_patches"}, pd, pn)
        return []
    for p in patches:
        if isinstance(p, dict):
            p["file"] = zieldatei
    # M-444: Import-Validierung. Patches mit unaufloesbaren Imports
    # werden verworfen — sonst bricht der Verify-Loop mit
    # ModuleNotFoundError (RERUN-54: core.changeapplier.errors).
    _gueltig: list[dict] = []
    _feedback_neu: list[str] = []
    for p in patches:
        if not isinstance(p, dict):
            continue
        # M-444c: Pruefe new_string UND old_string zusammen.
        # Sonst uebersehen wir Importe, die nur in old_string stehen
        # (und entfernt werden sollen). Verwirft den GANZEN Patch,
        # wenn ein Import ungueltig ist.
        _patch_text = (
            (p.get("old_string", "") or "")
            + "\n"
            + (p.get("new_string", "") or "")
            + "\n"
            + (p.get("context", "") or "")
            + "\n"
            + (p.get("old", "") or "")
            + "\n"
            + (p.get("new", "") or "")
        )
        _fehlend = _validate_imports_in_patch(
            _patch_text, pd,
            task_files=getattr(state, "tasks", [{}])[0].get("task_files", []) if getattr(state, "tasks", None) else None,
        )
        if _fehlend:
            _bglob.audit("builder_patch_import_fehler",
                  {"datei": zieldatei, "fehlend": _fehlend}, pd, pn)
            _feedback_neu.append(
                "Import nicht aufloesbar: " + ", ".join(_fehlend)
                + ". Verwende existierende Symbole oder definiere "
                "sie im selben Patch (class/def/var)."
            )
            continue
        _gueltig.append(p)

    # M-444b: Feedback speichern, damit der naechste Aufruf es sieht.
    if _feedback_neu:
        if not getattr(state, "builder_feedback", None):
            state.builder_feedback = {}
        state.builder_feedback[zieldatei] = "\n".join(_feedback_neu)
    else:
        if getattr(state, "builder_feedback", None):
            state.builder_feedback.pop(zieldatei, None)

    # K48: Aider-Format auf Legacy normalisieren (zentraler Helper).
    _gueltig = _normalisiere_aider_patches(_gueltig, pd=pd, pn=pn)

    # GOLD 2026-10-30: Patches filtern, deren old_string NICHT in
    # der Datei ist, aber deren new_string SCHON in der Datei ist.
    # Das bedeutet: Auftrag bereits erfuellt. Live-Beleg 2026-10-30
    # 21:37:34: alerts.html hatte schon class="table table-alerts",
    # der Builder baute old_string='class="table"'. Apply scheiterte
    # (old_string_not_found), reviewer_kein_diff_aber_patches ->
    # fail-closed.
    _erfuellt: list[dict] = []
    for _p in _gueltig:
        if not isinstance(_p, dict):
            continue
        if _p.get("action", "update") != "update":
            _erfuellt.append(_p)
            continue
        _old = _p.get("old_string", "") or ""
        _new = _p.get("new_string", "") or ""
        if not _old or not _new:
            _erfuellt.append(_p)
            continue
        _old_in_datei = _old in _inhalt
        _new_in_datei = _new in _inhalt
        if not _old_in_datei and _new_in_datei:
            _bglob.audit("auftrag_bereits_erfuellt",
                  {"zieldatei": zieldatei,
                   "grund": "old_nicht_da_aber_new_da",
                   "old_prefix": _old[:100],
                   "new_prefix": _new[:100]}, pd, pn)
            continue  # Patch verwerfen, Auftrag ist erfuellt
        _erfuellt.append(_p)

    if _gueltig and not _erfuellt:
        # Alle Patches waren "Auftrag bereits erfuellt".
        if isinstance(state, object) and hasattr(state, "__dict__"):
            try:
                state.auftrag_bereits_erfuellt = True
                state.auftrag_bereits_erfuellt_bestaetigt = True
                state.auftrag_bereits_erfuellt_quelle = "builder:old_nicht_da_aber_new_da"
            except (AttributeError, TypeError):
                pass
        return []

    _erfuellt = _pruefe_doku_patch_breite(
        _erfuellt, getattr(state, 'aufgabe', ''), zieldatei, pd, pn,
    )
    return _erfuellt


def run_builder(state: RunState) -> bool:
    """Erstellt Patches. Schreibt sie in state.patches (oder wendet sie an)."""
    pd = state.project_dir
    pn = state.project_name
    api_key = getattr(state, "api_key", "")

    if not api_key:
        _bglob.audit("builder_kein_key", {}, pd, pn)
        return False

    tasks = getattr(state, "tasks", [])
    if not tasks:
        _bglob.audit("builder_keine_tasks", {}, pd, pn)
        return False

    # M-306a: Read-only-Tasks. Wenn ALLE Tasks action="read" haben,
    # ist der Task eine Bestandsaufnahme. Builder ruft keinen LLM,
    # erzeugt keinen Patch. Gibt True (Task erfolgreich = Info
    # gesammelt).
    def _is_read_only(task_obj) -> bool:
        if not isinstance(task_obj, dict):
            return False
        return task_obj.get("action") == "read"

    if all(_is_read_only(t) for t in tasks):
        _bglob.audit("builder_read_only", {"tasks": len(tasks)}, pd, pn)
        state.patches = []
        return True

    # M-317: Idempotenz-Check NUR bei action="create".
    # Bei "update" (Datei existiert + soll erweitert werden)
    # ist py_compile immer ok -> fail-open (M-317-Befund).
    # Also: bei update IMMER durch den LLM-Patch-Pfad.
    _current_action = None
    for _t_check in tasks:
        if isinstance(_t_check, dict):
            _current_action = _t_check.get("action")
            break
    # M-318: Idempotenz auch bei "update" pruefen. Wenn die Zieldatei
    # existiert und syntaktisch korrekt ist, ist "nichts zu tun" ein
    # legitimer Erfolg. M-317 hatte "nur create" — das war zu strikt:
    # ein update-Task, dessen Ziel durch einen vorherigen Task bereits
    # erfuellt wurde, wurde als Fehler gewertet.
    # Profi-Muster (Aider, Claude Code, SWE-agent): Erfuellung ist
    # Repo-Zustand nach Task, nicht "Patch nicht leer".
    # M-352: Idempotenz NUR bei create, wenn Zieldatei existiert.
    # Sonst: fail-closed (Builder muss Datei anlegen).
    if _current_action == "create":
        _task_obj = getattr(state, "aktuelle_task", None)
        if not isinstance(_task_obj, dict) or not _task_obj:
            _task_obj = next(
                (t for t in tasks if isinstance(t, dict)), {}
            )
        _files = (
            _task_obj.get("task_files", [])
            if isinstance(_task_obj, dict) else []
        )
        _any_exists = any(
            (pd / f).exists() for f in _files if isinstance(f, str)
        )
        # M-352-Fallback: task_files leer -> Dateiname aus name (M-317).
        if not _any_exists and not _files:
            import re as _re_fb
            _name_fb = (
                _task_obj.get("name", "") if isinstance(_task_obj, dict) else ""
            )
            for _m_fb in _re_fb.findall(
                r'\b([a-zA-Z_][a-zA-Z0-9_/]+\.'
                r'(?:md|py|yaml|yml|json|txt|toml|cfg|ini))\b',
                _name_fb,
            ):
                if (pd / _m_fb).exists():
                    _any_exists = True
                    break
        _allow_idempotent = _any_exists
    else:
        _allow_idempotent = False

    # M-316 (A1/A2): Idempotenz-Check (Variante iii: verify.py).
    # Wird nur bei create-Tasks verwendet (M-317).
    _target_files: list[Path] = []
    import re as _re2
    _file_pattern2 = _re2.compile(r'\b([a-zA-Z_][a-zA-Z0-9_/]+\.(?:md|py|yaml|yml|json|txt|toml|cfg|ini))\b')
    for _task_obj in tasks:
        _text2 = _task_obj if isinstance(_task_obj, str) else str(_task_obj)
        for _m2 in _file_pattern2.findall(_text2):
            _tf = pd / _m2
            if _tf.exists() and _tf.is_file() and _tf not in _target_files:
                _target_files.append(_tf)

    # M-337-c: Idempotenz-Check NUR wenn task_files leer ist.
    # Wenn task_files gesetzt: Der Planner will die Datei explizit
    # aendern. Idempotenz (M-318) wuerde den Patch ueberspringen.
    _aktuelle_task_early = getattr(state, "aktuelle_task", None)
    _hat_task_files = (
        isinstance(_aktuelle_task_early, dict)
        and bool(_aktuelle_task_early.get("task_files"))
    )

    if _target_files and _allow_idempotent and not _hat_task_files:
        _all_ok = True
        for _tf in _target_files:
            if _tf.suffix == ".py":
                _res = subprocess.run(
                    ["python3", "-m", "py_compile", str(_tf)],
                    capture_output=True, text=True, timeout=30, check=False,
                )
                if _res.returncode != 0:
                    _all_ok = False
                    _bglob.audit("builder_zieldatei_inkorrekt",
                          {"file": str(_tf), "fehler": _res.stderr[:200]}, pd, pn)
                    break

        if _all_ok:
            # A2: Datei existiert UND ist korrekt -> task_ok.
            # Nur bei create-Tasks (M-317).
            _bglob.audit("builder_nichts_zu_tun",
                  {"files": [str(f.name) for f in _target_files]}, pd, pn)
            state.patches = []
            return True

    # M-298d: On-demand Zieldatei lesen.
    # Profi-Ansatz (Aider Repo-Map, Cline read_file): Der Builder
    # liest nur die Dateien, die der Task betrifft — nicht die
    # ganze Codebase. Explorer-Report (key_files) zeigt WELCHE
    # Datei relevant ist; der Builder liest sie DANN selbst.
    #
    # Wir scannen den Task-Text nach Datei-Pfaden (typisch:
    # "README.md", "core/x.py"). Der erste Treffer wird gelesen.
    import re as _re
    _file_pattern = _re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_/]+\.(?:md|py|yaml|yml|json|txt|toml|cfg|ini))\b')
    _relevant_files: list[str] = []
    for _task in tasks:
        _text = _task if isinstance(_task, str) else str(_task)
        for _m in _file_pattern.findall(_text):
            if _m not in _relevant_files:
                _relevant_files.append(_m)
    # M-335: task_files aus aktuellem Task (M-317) PRIORISIEREN.
    # Der Planner setzt explizite Datei-Pfade pro Task. Der Builder
    # hat sie bisher ignoriert — deshalb sah er oft die falsche
    # Datei (z.B. tools/port_check.py statt core/checks/).
    _aktuelle_task = getattr(state, "aktuelle_task", None)
    if isinstance(_aktuelle_task, dict):
        _task_files = _aktuelle_task.get("task_files", []) or []
        if _task_files:
            _task_files_str = [f for f in _task_files if isinstance(f, str)]
            if _task_files_str:
                # M-337-b: NUR task_files. Kein Regex, kein Explorer.
                # Der Builder soll nur die vom Planner genannten
                # Dateien sehen — nicht 6 andere.
                _relevant_files = list(_task_files_str)

    # M-337-b: Explorer-key_files NUR als Fallback, wenn
    # task_files leer war.
    _hat_task_files = (
        isinstance(_aktuelle_task, dict)
        and bool(_aktuelle_task.get("task_files"))
    )
    if not _hat_task_files:
        _expl = state.explorer_context or {}
        for _f in _expl.get("key_files", []) or []:
            _f_str = None
            if isinstance(_f, str):
                _f_str = _f
            elif isinstance(_f, dict):
                _f_str = _f.get("file") or _f.get("path") or _f.get("name")
            if _f_str and _f_str not in _relevant_files:
                _relevant_files.append(_f_str)

    _file_context: dict[str, str] = {}
    # M-336: Ordner in _relevant_files aufloesen. Der Planner
    # setzt task_files manchmal als Ordner (z.B. "core/checks/")
    # statt als Datei ("core/checks/__init__.py"). is_file()
    # schlaegt dann fehl — der Builder sieht die Datei nicht.
    _aufgeloest: list[Path] = []
    for _rel in _relevant_files:
        if not isinstance(_rel, str):
            continue
        _target = pd / _rel
        if _target.is_dir():
            # Ordner: alle .py-Dateien darin (max 5)
            _aufgeloest.extend(sorted(_target.glob("*.py"))[:5])
        elif _target.is_file():
            _aufgeloest.append(_target)

    for _target in _aufgeloest[:5]:  # max 5, kein Kontext-Ballern
        try:
            _content = _target.read_text()
            # Nur letzte 50 Zeilen (On-Demand, nicht volle Datei)
            _tail = "\n".join(_content.splitlines()[-50:])
            _rel_str = str(_target.relative_to(pd))
            _file_context[_rel_str] = _tail
        except OSError:
            continue

    # M-333b: Bei create-Tasks (neue Dateien) gibt es keinen
    # _file_context (Datei existiert nicht). Wir sammeln die
    # Imports benachbarter .py-Dateien, damit der Builder weiss,
    # welche Module im Projekt existieren.
    _create_tasks = [
        t for t in tasks
        if isinstance(t, dict) and t.get("action") == "create"
    ]
    if _create_tasks:
        _imports_ctx: dict[str, str] = {}
        # Alle .py-Dateien im Projekt (max 30). K10: Ignorier-Pfade
        # (.venv, __pycache__, site-packages, node_modules) werden
        # in _sammle_projekt_py_files gefiltert.
        _py_files = _sammle_projekt_py_files(pd, limit=30)
        for _f in _py_files:
            if _f.is_file():
                try:
                    _lines = _f.read_text(encoding="utf-8").splitlines()
                except (OSError, UnicodeDecodeError):
                    continue
                _imports = [
                    ln for ln in _lines[:30]
                    if ln.startswith(("import ", "from "))
                ]
                if _imports:
                    _rel = str(_f.relative_to(pd))
                    _imports_ctx[_rel] = "\n".join(_imports)
        if _imports_ctx:
            _file_context["__projekt_imports__"] = (
                "\n\n".join(
                    f"--- {f} ---\n{imp}"
                    for f, imp in list(_imports_ctx.items())[:15]
                )
            )
            _bglob.audit("builder_import_context",
                  {"files": list(_imports_ctx.keys())[:15]}, pd, pn)

    if _file_context:
        _bglob.audit("builder_file_context", {"files": list(_file_context.keys())}, pd, pn)

    # M-337: Zieldatei deterministisch bestimmen aus task_files.
    # Der Builder bekommt KEINE freie Wahl. Er MUSS diese Datei
    # aendern (update) oder anlegen (create).
    _aktuelle_task = getattr(state, "aktuelle_task", None)
    if not isinstance(_aktuelle_task, dict):
        _bglob.audit("builder_keine_aktuelle_task", {}, pd, pn)
        return False
    _task_files = _aktuelle_task.get("task_files", []) or []
    _current_action2 = _aktuelle_task.get("action", "update")
    _is_architect = _current_action2 == "architect"
    # K22b/c: Action live gegen Dateisystem korrigieren.
    # K34: NICHT in Reflection-Runde (Task-Action bleibt wie im Plan).
    if not _is_architect and not getattr(state, "reflection_phase", False):
        _current_action2 = _korrigiere_builder_action(
            _aktuelle_task, pd, pn,
        )
    _architect_beschreibung = _aktuelle_task.get("description", "") if _is_architect else ""

    # M-416b: Architect-Modus -> Editor pro Datei.
    # Wird VOR der normalen Zieldatei-Wahl ausgefuehrt.
    if _is_architect:
        _alle_dateien = [f for f in _task_files if isinstance(f, str) and f]
        if not _alle_dateien:
            _bglob.audit("builder_architect_keine_dateien", {}, pd, pn)
            return False
        _alle_patches: list[dict] = []
        _dateien_ok: list[str] = []
        for _zd in _alle_dateien:
            _target = pd / _zd
            if not _target.is_file():
                _bglob.audit("builder_architect_datei_fehlt",
                      {"datei": _zd}, pd, pn)
                continue
            _patches = _build_patches_fuer_datei(
                state, _zd, _architect_beschreibung, api_key,
            )
            if _patches:
                _alle_patches.extend(_patches)
                _dateien_ok.append(_zd)
        if not _alle_patches:
            _bglob.audit("builder_architect_keine_patches",
                  {"dateien": _alle_dateien}, pd, pn)
            return False
        state.patches = _alle_patches
        _bglob.audit("builder_architect_patches",
              {"anzahl_patches": len(_alle_patches),
               "dateien": _dateien_ok}, pd, pn)
        return True

    _zieldatei = None
    for _tf in _task_files:
        if not isinstance(_tf, str):
            continue
        _target = pd / _tf
        if _target.is_dir():
            _init = _target / "__init__.py"
            if _init.exists():
                _zieldatei = str(_init.relative_to(pd))
                break
            _py = sorted(_target.glob("*.py"))
            if _py:
                _zieldatei = str(_py[0].relative_to(pd))
                break
        elif _target.is_file():
            _zieldatei = _tf
            break

    if _zieldatei is None:
        # M-360: Bei create-Tasks ist das Fehlen der Zieldatei
        # ERWARTET (die Datei soll angelegt werden). Statt
        # fail-closed nehmen wir die erste task_file als Ziel
        # und lassen das LLM sie anlegen.
        # Bei update/read: Datei MUSS existieren -> fail-closed.
        if _current_action2 == "create":
            _erste = next(
                (f for f in _task_files if isinstance(f, str) and f),
                None,
            )
            if _erste:
                _zieldatei = _erste
                _bglob.audit("builder_zieldatei_create_neu",
                      {"task_files": _task_files, "zieldatei": _zieldatei},
                      pd, pn)
            else:
                _bglob.audit("builder_zieldatei_nicht_gefunden",
                      {"task_files": _task_files, "action": _current_action2},
                      pd, pn)
                return False
        else:
            _bglob.audit("builder_zieldatei_nicht_gefunden",
                  {"task_files": _task_files, "action": _current_action2},
                  pd, pn)
            return False

    # Volle Zieldatei in den Prompt (nicht letzte 50 Zeilen),
    # damit old_string exakt passt.
    _zieldatei_path = pd / _zieldatei
    if _zieldatei_path.exists() and _zieldatei_path.is_file():
        try:
            _file_context[_zieldatei] = _zieldatei_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            pass

    aufgabe = getattr(state, "aufgabe", "")

    # Aktuellen Code lesen (vereinfacht: aus state.docs oder direkt)
    # Fuer Phase 6 nehmen wir einen Platzhalter, spaeter wird das aus dem Repo gelesen.

    # M-337: user_content mit Zieldatei + Aktion. KEINE Task-Liste
    # (der LLM soll nicht frei entscheiden).
    user_content = (
        f"ZIELDATEI: {_zieldatei}\n"
        f"AKTION: {_current_action2}\n\n"
        f"AUFGABE: {aufgabe}\n\n"
        f"AKTUELLER TASK: {json.dumps(_aktuelle_task, ensure_ascii=False)}"
    )

    # M-329a: Fehler-Kontext aus Reflection (_verify_patches).
    _verify_errors = getattr(state, "last_verify_errors", None)
    if _verify_errors:
        _err_text = "\n".join(str(e) for e in _verify_errors)[:3000]
        user_content += (
            f"\n\nDer letzte Patch hat die Tests zerstoert. "
            f"Hier ist der Fehler-Output:\n\n{_err_text}\n\n"
            "Behebe NUR diesen Fehler. Nutze old_string/new_string. "
            "M-383: Wenn der Fehler RUF100 (unused noqa) ist: Entferne den # noqa NICHT, wenn der Code absichtlich so ist (Negativtest, naive datetime). Behalte den # noqa. " 
            "Wenn ein Import fehlt, ergaenze ihn in der Import-Zeile."
        )

    # M-298d: Datei-Kontext als zusaetzlicher Abschnitt (on-demand).
    # Nur Dateien, die der Task betrifft — verhindert Token-Ballern.
    if "_file_context" in dir() and _file_context:
        _ctx_parts = []
        for _f, _c in _file_context.items():
            _ctx_parts.append(f"--- {_f} (letzte 50 Zeilen) ---\n{_c}")
        user_content += "\n\nAktueller Datei-Kontext:\n" + "\n\n".join(_ctx_parts)

    # GOLD: Klassischer Pfad nutzt _build_patches_fuer_datei.
    # Vorteile: voller Datei-Inhalt, relevanter Architect-Abschnitt,
    # Feedback, Reviewer-Bugs, Verify-Fehler, Reflection-History,
    # Import-Validierung.
    _arch_beschreibung = (
        _aktuelle_task.get("description", "")
        if isinstance(_aktuelle_task, dict) else ""
    )
    patches = _build_patches_fuer_datei(
        state, _zieldatei, _arch_beschreibung, api_key,
    )
    patches = _korrigiere_doku_datum(
        patches,
        datetime.now(UTC).date().isoformat(),
        pd=getattr(state, "project_dir", None),
        pn=getattr(state, "project_name", "?"),
    )
    if not patches:
        # GOLD 2026-10-30: pruefen, ob der LLM-Pfad bereits das
        # auftrag_bereits_erfuellt-Flag gesetzt hat.
        if getattr(state, "auftrag_bereits_erfuellt", False):
            return True
        _bglob.audit("builder_keine_patches_gold",
              {"zieldatei": _zieldatei}, pd, pn)
        return False

    # GOLD 2026-10-30: no_effect-Patches filtern (old == new).
    # Der Haupt-Pfad filtert schon, der Architect-Pfad bisher nicht.
    # Live 2026-10-30 20:46:55: builder_patch_no_effect +
    # builder_patches_erstellt + loop_patch_updated -> Patch ohne
    # Aenderung wurde angewendet.
    _effektiv: list = []
    for _p in patches:
        if not isinstance(_p, dict):
            continue
        if (_p.get("action") == "update"
                and _p.get("old_string") == _p.get("new_string")):
            _bglob.audit("builder_patch_no_effect",
                  {"file": _p.get("file", "?"),
                   "grund": "old_eq_new"}, pd, pn)
            continue
        _effektiv.append(_p)
    if not _effektiv:
        # OP-054: no_effect hat zwei Bedeutungen.
        # (a) Datei enthaelt old_string genau einmal -> Auftrag
        #     tatsaechlich bereits erfuellt (Builder hat nichts
        #     geaendert, weil nichts zu aendern war).
        # (b) Datei enthaelt old_string MEHRFACH -> Duplikat-Anker.
        #     Builder hat denselben Text zweimal im Ist-Zustand
        #     gesehen und "ich aendere nichts" geantwortet. Das
        #     ist ein Fehler, KEIN "bereits erfuellt".
        # Live-Beleg 2026-11-01: t2 (OP-002b) wurde als "done via
        # auftrag_bereits_erfuellt_pre_hook" markiert, obwohl t1
        # eine doppelte Methodendefinition in repository.py
        # hinterlassen hatte.
        _ist_zustand_054 = ""
        try:
            _ist_zustand_054 = (
                Path(pd) / _zieldatei
            ).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            pass

        _duplikat_anker: list[str] = []
        for _p in patches:
            if not isinstance(_p, dict):
                continue
            _old_anker = _p.get("old_string", "")
            if not _old_anker:
                continue
            if _ist_zustand_054.count(_old_anker) > 1:
                _duplikat_anker.append(_p.get("file", _zieldatei))

        if _duplikat_anker:
            _bglob.audit("builder_patch_duplicate_anchor",
                  {"zieldatei": _zieldatei,
                   "anzahl": len(_duplikat_anker),
                   "files": list(set(_duplikat_anker))[:5]},
                  pd, pn)
            # NICHT als "bereits erfuellt" markieren.
            # Loop muss das als Fehler sehen (task_failed).
            return False

        # Ansonsten: bisheriges Verhalten — Auftrag ist bereits erfuellt.
        state.auftrag_bereits_erfuellt = True
        state.auftrag_bereits_erfuellt_bestaetigt = False
        state.auftrag_bereits_erfuellt_quelle = "builder:alle_patches_no_effect"
        _bglob.audit("auftrag_bereits_erfuellt",
              {"zieldatei": _zieldatei,
               "grund": "alle_patches_no_effect"}, pd, pn)
        return True
    patches = _effektiv

    # M-337: Jeder Patch MUSS die Zieldatei sein + die Aktion
    # respektieren. Der LLM darf NICHT frei entscheiden.
    for _p in patches:
        if not isinstance(_p, dict):
            continue
        _pfile = _p.get("file", "")
        if _pfile != _zieldatei:
            _bglob.audit("builder_patch_invalid",
                  {"file": _pfile, "zieldatei": _zieldatei,
                   "grund": "falsche Datei"}, pd, pn)
            return False
        _paction = _p.get("action")
        # Fix AV-3 2026-10-31: delete als Alternative zu update akzeptieren.
        # Planner setzt bei "Datei entfernen"-Tasks action="update" (kennt
        # delete nicht). Builder erkennt die Intention, liefert action=
        # "delete". Vorher: builder_patch_invalid expected update -> Patch
        # verworfen -> builder_failed. Live-Beleg 2026-10-31 11:22 t5/t6.
        if _current_action2 == "update" and _paction not in ("update", "delete"):
            _bglob.audit("builder_patch_invalid",
                  {"action": _paction, "expected": "update|delete"}, pd, pn)
            return False
        if _current_action2 == "create" and _paction != "create":
            _bglob.audit("builder_patch_invalid",
                  {"action": _paction, "expected": "create"}, pd, pn)
            return False

    # Patches in State schreiben (spaeter anwenden)
    # M-351: Patches mit identischem Inhalt (old == new) sind no_effect.
    _effective_patches = []
    for _p in patches:
        if not isinstance(_p, dict):
            continue
        if _p.get("action") == "update" and _p.get("old_string") == _p.get("new_string"):
            _bglob.audit("builder_patch_no_effect",
                  {"file": _p.get("file", "?")}, pd, pn)
            continue
        _effective_patches.append(_p)
    if not _effective_patches:
        _bglob.audit("builder_keine_wirksamen_patches", {}, pd, pn)
        return False
    state.patches = _effective_patches
    _bglob.audit("builder_patches_erstellt", {"anzahl": len(_effective_patches)}, pd, pn)
    return True
