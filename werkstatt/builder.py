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
Du bekommst eine Aufgabe und den aktuellen Code.
Entscheide, ob du eine Datei AENDERN oder ERSTELLEN musst.

Fuer AENDERUNGEN (Datei existiert):
{
  "patches": [
    {"action": "update", "file": "pfad/datei.py", "old_string": "exakter code", "new_string": "neuer code"}
  ]
}

Fuer NEUE DATEIEN (Datei existiert nicht):
{
  "patches": [
    {"action": "create", "file": "pfad/datei.py", "content": "kompletter dateiinhalt"}
  ]
}

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

    # M-316 (A1/A2): Idempotenz-Check (Variante iii: verify.py).
    # Wenn die Zieldatei(en) existieren UND via py_compile
    # (schnell) syntaktisch ok sind, ist nichts zu tun.
    # Verhindert fail-open (falscher Code bleibt) und
    # fail-closed (Reflection auf Phantom).
    _target_files: list[Path] = []
    import re as _re2
    _file_pattern2 = _re2.compile(r'\b([a-zA-Z_][a-zA-Z0-9_/]+\.(?:md|py|yaml|yml|json|txt|toml|cfg|ini))\b')
    for _task_obj in tasks:
        _text2 = _task_obj if isinstance(_task_obj, str) else str(_task_obj)
        for _m2 in _file_pattern2.findall(_text2):
            _tf = pd / _m2
            if _tf.exists() and _tf.is_file() and _tf not in _target_files:
                _target_files.append(_tf)

    if _target_files:
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
    # Explorer-Report (key_files) als Wegweiser ergaenzen.
    # key_files kann dicts enthalten (z.B. {"file": "...", ...})
    # oder strings. Wir normalisieren auf strings.
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
    for _rel in _relevant_files[:5]:  # max 5, kein Kontext-Ballern
        # Sicherheits-Check: _rel muss str sein (M-298d-Bugfix).
        if not isinstance(_rel, str):
            continue
        _target = pd / _rel
        if _target.exists() and _target.is_file():
            try:
                _content = _target.read_text()
                # Nur letzte 50 Zeilen (On-Demand, nicht volle Datei)
                _tail = "\n".join(_content.splitlines()[-50:])
                _file_context[_rel] = _tail
            except OSError:
                continue

    if _file_context:
        audit("builder_file_context", {"files": list(_file_context.keys())}, pd, pn)

    aufgabe = getattr(state, "aufgabe", "")
    tasks_ctx = json.dumps(tasks, ensure_ascii=False)

    # Aktuellen Code lesen (vereinfacht: aus state.docs oder direkt)
    # Fuer Phase 6 nehmen wir einen Platzhalter, spaeter wird das aus dem Repo gelesen.

    user_content = f"Aufgabe: {aufgabe}\n\nTasks:\n{tasks_ctx}"

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

    # Patches in State schreiben (spaeter anwenden)
    state.patches = patches  # type: ignore[attr-defined]
    audit("builder_patches_erstellt", {"anzahl": len(patches)}, pd, pn)
    return True
