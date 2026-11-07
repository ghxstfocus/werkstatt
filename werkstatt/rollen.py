"""Rollen-Registry (2026-11-05).

Single Source of Truth fuer:
- System-Prompt pro Rolle (LAZY — Zirkel-Import vermeiden)
- Skills pro Rolle (explizit oder via rollen-Marker)
- Tool-Verfuegbarkeit pro Rolle

Hintergrund: Regress 2026-11-03 (architect.py lud 'plan-crafting'
mit '## Tools', deepseek-reasoner lieferte DSML). Siehe M-446.

Zentrale Regel: Rolle ohne explizite skills + ohne skill_filter_rolle
bekommt KEINE Skills. Fail-closed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Rolle:
    """Eine Rolle im Loop."""
    name: str
    skills: tuple[str, ...] = ()
    skill_filter_rolle: str | None = None
    tools: tuple[str, ...] = ()
    prompt_module: str = ""
    prompt_const: str | None = None
    prompt_builder: str | None = None
    beschreibung: str = ""

    def lade_system_prompt(self, *args, **kwargs) -> str:
        """Laedt System-Prompt LAZY (vermeidet Zirkel-Importe)."""
        if not self.prompt_module:
            return ""
        import importlib
        mod = importlib.import_module(self.prompt_module)
        if self.prompt_builder:
            builder = getattr(mod, self.prompt_builder, None)
            if builder is not None:
                return builder(*args, **kwargs) or ""
        if self.prompt_const:
            return getattr(mod, self.prompt_const, "") or ""
        return ""

    def lade_skills(
        self,
        alle_skills: list[dict[str, Any]],
        task_files: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Laedt Skills dieser Rolle. Fail-closed."""
        from werkstatt.skills import load_skill_by_name, skills_aktivieren

        result: list[dict[str, Any]] = []
        seen: set[str] = set()
        for skill_name in self.skills:
            s = load_skill_by_name(skill_name, alle_skills)
            if s and s.get("name") not in seen:
                result.append(s)
                seen.add(s.get("name", ""))
        if self.skill_filter_rolle and task_files:
            akt = skills_aktivieren(
                alle_skills, list(task_files),
                rolle=self.skill_filter_rolle,
            )
            for s in akt:
                n = s.get("name")
                if n and n not in seen:
                    result.append(s)
                    seen.add(n)
        return result


ROLLEN: dict[str, Rolle] = {}


def _reg(rolle: Rolle) -> None:
    if rolle.name in ROLLEN:
        raise ValueError(f"Rolle doppelt: {rolle.name!r}")
    ROLLEN[rolle.name] = rolle


_reg(Rolle(
    name="architect",
    skills=(),
    skill_filter_rolle=None,
    tools=(),
    prompt_module="werkstatt.architect",
    prompt_const="ARCHITECT_SYSTEM",
    beschreibung="Prosa-Planer. M-446: KEINE Skills, KEINE Tools.",
))

_reg(Rolle(
    name="planner",
    skills=("using-werkstatt", "milestone-planning", "plan-crafting"),
    tools=("run_readonly",),
    prompt_module="werkstatt.planner",
    prompt_const="PLANNER_SPLIT_SYSTEM",
    beschreibung="Task-Zerleger. plan-crafting mit Tools — OK.",
))

_reg(Rolle(
    name="builder",
    skill_filter_rolle="builder",
    prompt_module="werkstatt.roles.builder",
    prompt_const="BUILDER_SYSTEM",
    beschreibung="Patch-Editor. Skills dynamisch nach Zieldatei.",
))

_reg(Rolle(
    name="reviewer",
    skills=("review-work",),
    skill_filter_rolle="reviewer",
    prompt_module="werkstatt.reviewer",
    prompt_const="REVIEWER_SYSTEM",
    beschreibung="Code-Review.",
))

_reg(Rolle(
    name="explorer",
    skills=("using-werkstatt",),
    prompt_module="werkstatt.explorer",
    prompt_const="EXPLORER_SYSTEM",
    beschreibung="Read-only Explorer.",
))

_reg(Rolle(
    name="scout",
    prompt_module="werkstatt.scout",
    prompt_const="SCOUT_SYSTEM",
    beschreibung="Auftrag-Formulierer.",
))

_reg(Rolle(
    name="reflection",
    skills=("systematic-debugging",),
    beschreibung="Debugger bei Reject.",
))

__all__ = ["ROLLEN", "Rolle"]
