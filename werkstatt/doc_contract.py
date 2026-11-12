"""Struktureller Mindestvertrag fuer projektbezogene Living Docs.

Der Check laeuft beim Scaffolding und vor jedem Run. Er bewertet keine
fachliche Wahrheit; leere, ausdruecklich markierte Startdokumente sind gueltig.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path, PureWindowsPath

REQUIRED_DOC_KEYS = (
    "entry",
    "status",
    "roadmap",
    "architecture",
    "progress",
    "conventions",
    "adr_index",
    "glossary",
)
_UNRESOLVED = re.compile(r"\{\{[^{}]+\}\}")
_OP_HEADING = re.compile(r"^###\s+OP-\d+\b", re.MULTILINE)
_EMPTY_STATUS = re.compile(
    r"\(\s*noch keine(?:\s+punkte)?\s*[.)]|\(leer\)|noch keine punkte",
    re.IGNORECASE,
)


def validate_project_docs(
    project_dir: Path,
    docs_config: Mapping[str, object],
) -> list[str]:
    """Liefert strukturelle Vertragsfehler mit betroffener Doku/Feld."""
    root = project_dir.resolve()
    errors: list[str] = []
    missing = sorted(set(REQUIRED_DOC_KEYS) - docs_config.keys())
    if missing:
        errors.append(f"Manifest: Pflicht-Keys fehlen: {', '.join(missing)}")

    contents: dict[str, str] = {}
    for key in REQUIRED_DOC_KEYS:
        raw_path = docs_config.get(key)
        if not isinstance(raw_path, str) or not raw_path.strip():
            if key not in missing:
                errors.append(f"Manifest: Pfad fuer '{key}' ist leer oder ungueltig")
            continue
        windows_path = PureWindowsPath(raw_path)
        relative = Path(raw_path)
        if (
            relative.is_absolute()
            or windows_path.is_absolute()
            or windows_path.drive
            or "\\" in raw_path
            or ".." in relative.parts
            or ".." in windows_path.parts
        ):
            errors.append(f"Manifest: unsicherer Pfad fuer '{key}': {raw_path}")
            continue
        path = (root / relative).resolve()
        if not path.is_relative_to(root):
            errors.append(f"Manifest: Pfad fuer '{key}' verlaesst das Projekt")
            continue
        try:
            if not path.is_file():
                errors.append(f"Pflichtdokument fehlt: {raw_path}")
                continue
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"Pflichtdokument nicht lesbar ({raw_path}): {exc}")
            continue
        if not content.strip():
            errors.append(f"Pflichtdokument ist leer: {raw_path}")
            continue
        if _UNRESOLVED.search(content):
            errors.append(f"Unaufgeloester Template-Platzhalter in {raw_path}")
        contents[key] = content

    status = contents.get("status", "")
    if status and not _OP_HEADING.search(status) and not _EMPTY_STATUS.search(status):
        errors.append(
            "STATUS.md: erwartet mindestens einen '### OP-NNN'-Eintrag "
            "oder einen expliziten Leer-Marker"
        )
    return errors
