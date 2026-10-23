"""Builder-Agent (Phase 6, 2026-10-23).

Eigenstaendiger Builder. Liest Plan + Code,
ruft ask_llm auf, generiert Patch (str_replace).
"""
from __future__ import annotations

import json

from werkstatt.agent import ask_llm
from werkstatt.audit import audit
from werkstatt.state import RunState

BUILDER_SYSTEM = """Du bist ein elite Software-Engineer.
Du bekommst eine Aufgabe und den aktuellen Code.
Schreibe einen Patch im exakten str_replace-Format:
{
  "patches": [
    {"file": "pfad/datei.py", "old_string": "exakter code", "new_string": "neuer code"}
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

    aufgabe = getattr(state, "aufgabe", "")
    tasks_ctx = json.dumps(tasks, ensure_ascii=False)

    # Aktuellen Code lesen (vereinfacht: aus state.docs oder direkt)
    # Fuer Phase 6 nehmen wir einen Platzhalter, spaeter wird das aus dem Repo gelesen.

    user_content = f"Aufgabe: {aufgabe}\n\nTasks:\n{tasks_ctx}"

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
