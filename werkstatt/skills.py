"""Skill-Loader nach Agent-Skills-Standard.

Progressive Disclosure:
  Level 1: name + description (beim Start, ~100 Tokens/Skill)
  Level 2: SKILL.md-Body (nur bei Match)

allowed-tools im Frontmatter: pre-approved Tools fuer den Skill.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"


def _parse_frontmatter(text: str) -> dict[str, Any]:
    """Extrahiert YAML-Frontmatter aus SKILL.md."""
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    try:
        return yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return {}


def load_all_skills() -> list[dict[str, Any]]:
    """Level 1: name, description, allowed-tools. Body bleibt None."""
    if not SKILLS_DIR.is_dir():
        return []
    skills: list[dict[str, Any]] = []
    for d in sorted(SKILLS_DIR.iterdir()):
        if not d.is_dir():
            continue
        md = d / "SKILL.md"
        if not md.is_file():
            continue
        text = md.read_text(encoding="utf-8")
        fm = _parse_frontmatter(text)
        if not fm.get("name"):
            continue
        skills.append({
            "name": fm.get("name", d.name),
            "description": str(fm.get("description", "")).strip(),
            "allowed_tools": str(fm.get("allowed-tools", "")).strip(),
            "dir": d,
            "body": None,
        })
    return skills


def activate_skill(skill: dict[str, Any]) -> dict[str, Any]:
    """Level 2: laedt den SKILL.md-Body."""
    md = skill["dir"] / "SKILL.md"
    skill["body"] = md.read_text(encoding="utf-8")
    return skill


def load_skill_by_name(name: str, skills: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Laedt einen Skill per Name (Level 2)."""
    for s in skills:
        if s["name"] == name:
            return activate_skill(s)
    return None


def skills_summary(skills: list[dict[str, Any]]) -> str:
    """Level-1-Katalog fuer den System-Prompt (~100 Tokens/Skill)."""
    lines = []
    for s in skills:
        desc = s["description"].replace("\n", " ")[:120]
        lines.append(f"- {s['name']}: {desc}")
    return "\n".join(lines)
