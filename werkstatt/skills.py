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
        _globs = fm.get("globs") or []
        if isinstance(_globs, str):
            _globs = [_globs]
        skills.append({
            "name": fm.get("name", d.name),
            "description": str(fm.get("description", "")).strip(),
            "allowed_tools": str(fm.get("allowed-tools", "")).strip(),
            "globs": list(_globs),
            "always": bool(fm.get("always", False)),
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


def skills_metadata_block(skills: list[dict[str, Any]]) -> str:
    """Progressive Disclosure Level 1: Name + Description.

    Wird IMMER in den System-Prompt gehaengt. Damit weiss das LLM,
    welche Skills existieren. Bei Bedarf laedt es einen per Name
    (Level 2) oder ein Glob-Trigger feuert.
    """
    if not skills:
        return ""
    lines = ["## VERFUEGBARE SKILLS (Name — Description)"]
    for s in skills:
        name = s.get("name") or "?"
        desc = (s.get("description") or "").strip().replace(chr(10), " ")
        if len(desc) > 100:
            desc = desc[:97] + "..."
        lines.append(f"- **{name}** — {desc}")
    return chr(10).join(lines) + chr(10) + chr(10)


def skills_fuer_task(
    skills: list[dict[str, Any]],
    task_files: list[str],
) -> list[dict[str, Any]]:
    """Progressive Disclosure Level 2, deterministischer Trigger.

    Laedt Skills deren `globs:` auf mindestens einen Task-File passt.
    Cursor-Stil: fs-path-matching, kein LLM-Call.

    Reine Funktion, kein Side-Effect.
    """
    import fnmatch
    if not task_files:
        return []
    result = []
    seen = set()
    for s in skills:
        name = s.get("name") or ""
        if name in seen:
            continue
        globs = s.get("globs") or []
        if isinstance(globs, str):
            globs = [globs]
        for g in globs:
            for f in task_files:
                if not isinstance(f, str):
                    continue
                _f = f.replace(chr(92), "/")
                if fnmatch.fnmatch(f, g) or fnmatch.fnmatch(_f, g):
                    seen.add(name)
                    result.append(s)
                    break
            if name in seen:
                break
    return result


def skills_aktivieren(
    skills: list[dict[str, Any]],
    task_files: list[str],
    max_total: int = 3,
) -> list[dict[str, Any]]:
    """Glob-Trigger + Body laden, mit Limit.

    Laedt maximal max_total Skills. Verhindert Context-Overload,
    wenn mehrere Skills gleichzeitig matchen.
    """
    matched = skills_fuer_task(skills, task_files)
    activated = []
    for s in matched[:max_total]:
        activated.append(activate_skill(s))
    return activated

