"""Builder-Agent (Phase 6, 2026-10-23).

Eigenstaendiger Builder. Liest Plan + Code,
ruft ask_llm auf, generiert Patch (str_replace).
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from werkstatt.agent import ask_llm
from werkstatt.audit import audit
from werkstatt.state import RunState

BUILDER_SYSTEM = """Du bist ein elite Software-Engineer.
Du bekommst EINE ZIELDATEI und EINE AKTION.

Bei AKTION=update (Datei aendern):
  - Aendere NUR die ZIELDATEI.
  - Verwende old_string/new_string.
  - old_string MUSS exakt im "Aktueller Datei-Inhalt" vorkommen.
  - KEINE neuen Dateien. KEINE anderen Dateien.

Bei AKTION=create (Datei anlegen):
  - Lege NUR die ZIELDATEI an.
  - Verwende content (kompletter Datei-Inhalt).
  - KEINE anderen Dateien.

Antworte NUR mit JSON. patches[].file MUSS die ZIELDATEI sein.
patches[].action MUSS der AKTION entsprechen.

Format:
{
  "patches": [
    {"action": "update", "file": "<ZIELDATEI>",
     "old_string": "exakter code", "new_string": "neuer code"}
    // ODER bei create:
    // {"action": "create", "file": "<ZIELDATEI>", "content": "..."}
  ]
}

WICHTIG — Imports (M-333):
  - Verwende AUSSCHLIESSLICH Imports, die im Abschnitt
    "Aktueller Datei-Kontext" sichtbar sind.
  - Erfinde KEINE Modulnamen.
  - Bei Unsicherheit: KEIN Import.

Keine Erklaerung, nur JSON."""


def run_builder(state: RunState) -> bool:
    """Erstellt Patches. Schreibt sie in state.patches (oder wendet sie an)."""
    pd = state.project_dir
    pn = state.project_name
    api_key = getattr(state, "api_key", "")

    if not api_key:
        audit("builder_kein_key", {}, pd, pn)
        return False

    tasks = getattr(state, "tasks", [])
    if not tasks:
        audit("builder_keine_tasks", {}, pd, pn)
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
        audit("builder_read_only", {"tasks": len(tasks)}, pd, pn)
        state.patches = []  # type: ignore[attr-defined]
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
                    audit("builder_zieldatei_inkorrekt",
                          {"file": str(_tf), "fehler": _res.stderr[:200]}, pd, pn)
                    break

        if _all_ok:
            # A2: Datei existiert UND ist korrekt -> task_ok.
            # Nur bei create-Tasks (M-317).
            audit("builder_nichts_zu_tun",
                  {"files": [str(f.name) for f in _target_files]}, pd, pn)
            state.patches = []  # type: ignore[attr-defined]
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
        _expl = getattr(state, "explorer_context", {}) or {}
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
        # Alle .py-Dateien im Projekt (max 30, um Token zu sparen)
        _py_files = sorted(pd.rglob("*.py"))[:30]
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
            audit("builder_import_context",
                  {"files": list(_imports_ctx.keys())[:15]}, pd, pn)

    if _file_context:
        audit("builder_file_context", {"files": list(_file_context.keys())}, pd, pn)

    # M-337: Zieldatei deterministisch bestimmen aus task_files.
    # Der Builder bekommt KEINE freie Wahl. Er MUSS diese Datei
    # aendern (update) oder anlegen (create).
    _aktuelle_task = getattr(state, "aktuelle_task", None)
    if not isinstance(_aktuelle_task, dict):
        audit("builder_keine_aktuelle_task", {}, pd, pn)
        return False
    _task_files = _aktuelle_task.get("task_files", []) or []
    _current_action2 = _aktuelle_task.get("action", "update")

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
        audit("builder_zieldatei_nicht_gefunden",
              {"task_files": _task_files}, pd, pn)
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
            "Wenn ein Import fehlt, ergaenze ihn in der Import-Zeile."
        )

    # M-298d: Datei-Kontext als zusaetzlicher Abschnitt (on-demand).
    # Nur Dateien, die der Task betrifft — verhindert Token-Ballern.
    if "_file_context" in dir() and _file_context:
        _ctx_parts = []
        for _f, _c in _file_context.items():
            _ctx_parts.append(f"--- {_f} (letzte 50 Zeilen) ---\n{_c}")
        user_content += "\n\nAktueller Datei-Kontext:\n" + "\n\n".join(_ctx_parts)

    reply = ask_llm(
        api_key, BUILDER_SYSTEM, user_content,
        model="deepseek-chat", temperature=0.2, max_tokens=8000,
    )

    if not reply.ok:
        audit("builder_llm_fehler", {"fehler": reply.error}, pd, pn)
        return False

    # JSON aus dem Reply extrahieren
    raw = reply.content.strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start < 0 or end <= start:
        audit("builder_json_fehler", {"raw": raw[:200]}, pd, pn)
        return False

    try:
        patch_data = json.loads(raw[start:end])
    except json.JSONDecodeError:
        audit("builder_json_fehler", {"raw": raw[:200]}, pd, pn)
        return False

    patches = patch_data.get("patches", [])
    if not patches:
        audit("builder_keine_patches", {}, pd, pn)
        return False

    # M-337: Jeder Patch MUSS die Zieldatei sein + die Aktion
    # respektieren. Der LLM darf NICHT frei entscheiden.
    for _p in patches:
        if not isinstance(_p, dict):
            continue
        _pfile = _p.get("file", "")
        if _pfile != _zieldatei:
            audit("builder_patch_invalid",
                  {"file": _pfile, "zieldatei": _zieldatei,
                   "grund": "falsche Datei"}, pd, pn)
            return False
        _paction = _p.get("action")
        if _current_action2 == "update" and _paction != "update":
            audit("builder_patch_invalid",
                  {"action": _paction, "expected": "update"}, pd, pn)
            return False
        if _current_action2 == "create" and _paction != "create":
            audit("builder_patch_invalid",
                  {"action": _paction, "expected": "create"}, pd, pn)
            return False

    # Patches in State schreiben (spaeter anwenden)
    # M-351: Patches mit identischem Inhalt (old == new) sind no_effect.
    _effective_patches = []
    for _p in patches:
        if not isinstance(_p, dict):
            continue
        if _p.get("action") == "update" and _p.get("old_string") == _p.get("new_string"):
            audit("builder_patch_no_effect",
                  {"file": _p.get("file", "?")}, pd, pn)
            continue
        _effective_patches.append(_p)
    if not _effective_patches:
        audit("builder_keine_wirksamen_patches", {}, pd, pn)
        return False
    state.patches = _effective_patches  # type: ignore[attr-defined]
    audit("builder_patches_erstellt", {"anzahl": len(_effective_patches)}, pd, pn)
    return True
