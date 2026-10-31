"""werkstatt.scaffold — DOC_CONVENTIONS.md §2 Pflichtdateien anlegen.

Aufruf:
    python3 -m werkstatt.scaffold <name> --dir /opt/<name> [--dry-run] [--force]

Legt alle §2-Pflichtdateien im Zielprojekt an. Idempotent: existierende
Dateien bleiben ohne --force unangetastet.

Platzhalter in Templates:
    {{project_name}} — Projektname (CLI-Argument)
    {{project_dir}}  — Ziel-Verzeichnis (absolut)
    {{date}}         — Datum UTC (YYYY-MM-DD)
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent / "templates"

# DOC_CONVENTIONS.md §2 — Pflichtdateien, relativ zum Zielprojekt.
PFLICHTDATEIEN = [
    "AGENTS.md",
    "README.md",
    "PROGRESS.md",
    "CHANGELOG.md",
    "docs/index.md",
    "docs/STATUS.md",
    "docs/ROADMAP.md",
    "docs/ARCHITECTURE.md",
    "docs/CONVENTIONS.md",
    "docs/glossary.md",
    "docs/adr/README.md",
    "docs/adr/ADR-0001.md",
    ".werkstatt/verify.json",
]


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def substitute(content: str, name: str, project_dir: Path) -> str:
    """Ersetzt die drei Platzhalter im Template."""
    return (
        content
        .replace("{{project_name}}", name)
        .replace("{{project_dir}}", str(project_dir))
        .replace("{{date}}", _today())
    )


def _load_template(rel: str) -> str:
    p = TEMPLATES_DIR / rel
    if not p.exists():
        raise FileNotFoundError(f"Template fehlt: {p}")
    return p.read_text(encoding="utf-8")


def scaffold(
    name: str,
    project_dir: Path,
    *,
    dry_run: bool = False,
    force: bool = False,
) -> dict[str, str]:
    """Legt Pflichtdateien an. Rueckgabe: dict rel -> status."""
    if not project_dir.exists():
        raise FileNotFoundError(f"Zielverzeichnis existiert nicht: {project_dir}")
    if not project_dir.is_dir():
        raise NotADirectoryError(f"Zielpfad ist kein Verzeichnis: {project_dir}")

    bericht: dict[str, str] = {}
    for rel in PFLICHTDATEIEN:
        ziel = project_dir / rel
        exists = ziel.exists()
        if exists and not force:
            bericht[rel] = "uebersprungen"
            continue
        if dry_run:
            bericht[rel] = "waere-ueberschrieben" if exists else "waere-angelegt"
            continue
        content = substitute(_load_template(rel), name, project_dir)
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(content, encoding="utf-8")
        bericht[rel] = "ueberschrieben" if exists else "angelegt"
    return bericht


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m werkstatt.scaffold",
        description="Legt DOC_CONVENTIONS.md §2 Pflichtdateien an.",
    )
    parser.add_argument("name", help="Projektname (z.B. 'mein-projekt')")
    parser.add_argument("--dir", required=True, help="Zielverzeichnis (absolut)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Nur Bericht, nichts schreiben")
    parser.add_argument("--force", action="store_true",
                        help="Existierende Dateien ueberschreiben")
    args = parser.parse_args(argv)

    project_dir = Path(args.dir)
    print(f"Scaffold: '{args.name}' unter {project_dir}")
    if args.dry_run:
        print("  (dry-run — nichts wird geschrieben)")

    try:
        bericht = scaffold(
            args.name, project_dir,
            dry_run=args.dry_run, force=args.force,
        )
    except (FileNotFoundError, NotADirectoryError) as e:
        print(f"FEHLER: {e}", file=sys.stderr)
        return 1

    for rel, status in bericht.items():
        print(f"  [{status}] {rel}")

    anzahl = sum(
        1 for s in bericht.values()
        if s.startswith(("angelegt", "ueberschrieben", "waere"))
    )
    print(f"Fertig. {anzahl}/{len(PFLICHTDATEIEN)} betroffen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
