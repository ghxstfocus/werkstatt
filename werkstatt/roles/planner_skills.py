"""Load the shared skills context used by Planner capabilities."""
from __future__ import annotations

from typing import Any


def load_planner_skills(state: Any) -> str:
    """Load planner skills once through a single RunState write boundary."""
    try:
        from werkstatt.rollen import ROLLEN
        from werkstatt.skills import _merke_geladene_skills, load_all_skills

        loaded = ROLLEN["planner"].lade_skills(load_all_skills())
        if not loaded:
            return ""
        _merke_geladene_skills(
            state,
            [skill.get("name", "") for skill in loaded],
            rolle="planner",
        )
        lines = ["## SKILLS (planner)"]
        lines.extend(
            f"### {skill.get('name', '?')}\n{skill.get('body') or ''}"
            for skill in loaded if skill.get("body")
        )
        state.planner_skills_block = "\n\n".join(lines)
        return state.planner_skills_block
    except Exception:  # noqa: BLE001 - optional skills must not block planning
        state.planner_skills_block = ""
        return ""
