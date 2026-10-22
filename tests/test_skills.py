"""A3: Skills-Format-Test (read-only, kein Produktions-Code)."""
from pathlib import Path

import pytest

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"


def _skill_dirs() -> list[Path]:
    return sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir())


def _parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    fm: dict[str, str] = {}
    key = None
    for line in parts[1].splitlines():
        if ":" in line and not line.startswith(" "):
            key, _, val = line.partition(":")
            key = key.strip()
            fm[key] = val.strip()
        elif key and line.startswith(" "):
            fm[key] = (fm[key] + " " + line.strip()).strip()
    return fm


def test_skills_dir_existiert() -> None:
    assert SKILLS_DIR.is_dir(), f"skills/ fehlt: {SKILLS_DIR}"


def test_12_skills() -> None:
    dirs = _skill_dirs()
    assert len(dirs) == 12, f"erwartet 12, gefunden {len(dirs)}: {[d.name for d in dirs]}"


@pytest.mark.parametrize("skill_dir", _skill_dirs(), ids=lambda p: p.name)
def test_skill_format(skill_dir: Path) -> None:
    skill_md = skill_dir / "SKILL.md"
    assert skill_md.is_file(), f"{skill_dir.name}: SKILL.md fehlt"
    text = skill_md.read_text(encoding="utf-8")
    assert text.startswith("---"), f"{skill_dir.name}: Frontmatter fehlt"
    fm = _parse_frontmatter(text)
    assert fm.get("name") == skill_dir.name, (
        f"{skill_dir.name}: name={fm.get('name')!r} != Ordnername"
    )
    assert fm.get("description"), f"{skill_dir.name}: description fehlt/leer"
