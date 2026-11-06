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
        _rollen = fm.get("rollen") or []
        if isinstance(_rollen, str):
            _rollen = [_rollen]
        skills.append({
            "name": fm.get("name", d.name),
            "description": str(fm.get("description", "")).strip(),
            "allowed_tools": str(fm.get("allowed-tools", "")).strip(),
            "globs": list(_globs),
            "always": bool(fm.get("always", False)),
            "rollen": [str(r) for r in _rollen],
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


def _glob_specificity(pattern: str) -> int:
    """Anzahl der Nicht-Wildcard-Zeichen im Glob-Pattern.

    Hoeher = spezifischer. Bei Test-Files soll ein Pattern wie
    'tests/**/*.py' (score 9) gegen die generischen '**/*.py' (score 3)
    gewinnen, damit test-patterns nicht durch Alphabet-Reihenfolge
    abgeschnitten wird.
    """
    if not isinstance(pattern, str):
        return 0
    return len(pattern.replace("*", "").replace("?", "").strip("/"))


def skills_fuer_task(
    skills: list[dict[str, Any]],
    task_files: list[str],
    rolle: str | None = None,
) -> list[dict[str, Any]]:
    """Progressive Disclosure Level 2, deterministischer Trigger.

    Laedt Skills deren `globs:` auf mindestens einen Task-File passt.
    Cursor-Stil: fs-path-matching, kein LLM-Call.

    rolle: filtert Skills nach `rollen:`-Feld. Skills ohne rollen-Liste
    gelten fuer alle Rollen (Backward-Compat).

    Reine Funktion, kein Side-Effect.
    """
    import fnmatch
    if not task_files:
        return []
    # Rolle filtern, wenn angegeben
    if rolle is not None:
        skills = [
            s for s in skills
            if not (s.get("rollen") or []) or rolle in (s.get("rollen") or [])
        ]
    # Pro Skill die hoechste Spezifitaet ueber alle matcht Glob-Patterns
    # ermitteln. Skills ohne Match fallen weg.
    matched: list[tuple[int, dict[str, Any]]] = []
    seen_names: set[str] = set()
    for s in skills:
        name = s.get("name") or ""
        if name in seen_names:
            continue
        globs = s.get("globs") or []
        if isinstance(globs, str):
            globs = [globs]
        best_spec = 0
        for g in globs:
            for f in task_files:
                if not isinstance(f, str):
                    continue
                _f = f.replace(chr(92), "/")
                if fnmatch.fnmatch(f, g) or fnmatch.fnmatch(_f, g):
                    spec = _glob_specificity(g)
                    best_spec = max(best_spec, spec)
        if best_spec > 0:
            matched.append((best_spec, s))
            seen_names.add(name)
    # Stabile Sortierung: hoechste Spezifitaet zuerst.
    # Bei Gleichstand bleibt die Eingabe-Reihenfolge (aus load_all_skills
    # alphabetisch sortiert) erhalten -> deterministisch.
    matched.sort(key=lambda pair: -pair[0])
    return [s for _, s in matched]


def skills_aktivieren(
    skills: list[dict[str, Any]],
    task_files: list[str],
    max_total: int = 3,
    rolle: str | None = None,
) -> list[dict[str, Any]]:
    """Glob-Trigger + Body laden, mit Limit.

    Laedt maximal max_total Skills. Verhindert Context-Overload,
    wenn mehrere Skills gleichzeitig matchen.

    rolle: filtert Skills nach `rollen:`-Feld (siehe skills_fuer_task).
    """
    matched = skills_fuer_task(skills, task_files, rolle=rolle)
    activated = []
    for s in matched[:max_total]:
        activated.append(activate_skill(s))
    return activated



def _merke_geladene_skills(
    state: Any,
    names: list[str],
    rolle: str = "?",
) -> list[str]:
    """Dedup + Audit: merkt neue Skill-Namen in state.geladene_skills.

    Rueckgabe: die tatsaechlich NEU gemerkten Namen. Wenn keine neu:
    leere Liste (dann loggt der Aufrufer auch nicht).

    Robust: wenn state.geladene_skills kein list ist oder fehlt,
    passiert nichts. Das deckt Test-Fixtures (SimpleNamespace) ab.

    Audit-Event nur bei tatsaechlicher Aenderung -> kein Spam bei
    mehrfachem Reviewer-Aufruf pro Task.
    """
    if state is None:
        return []
    _cur = getattr(state, "geladene_skills", None)
    if not isinstance(_cur, list):
        return []
    neu: list[str] = []
    for n in names:
        if isinstance(n, str) and n and n not in _cur:
            _cur.append(n)
            neu.append(n)
    if neu:
        try:
            from werkstatt.audit import audit
            audit(
                "loop_skills_geladen",
                {"rolle": rolle, "neu": list(neu)},
                getattr(state, "project_dir", None) or Path("."),
                getattr(state, "project_name", "?"),
            )
        except Exception:  # noqa: BLE001, S110
            pass
    return neu

