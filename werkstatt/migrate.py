"""werkstatt.migrate — Projekt-Doku pruefen und minimal migrieren.

Aufruf:
    python3 -m werkstatt.migrate <name> --dir /opt/<name> [--dry-run|--apply]

Prueft gemaess DOC_CONVENTIONS.md:
    §2 — Pflichtdateien vorhanden?
    §3 — keine verbotenen Dateien?
    §5 — STATUS.md folgt Format (OP-NNN oder "leer"-Marker)?
    §6 — Manifest enthaelt alle Pflichtfelder?

Verhalten:
    --dry-run (Default): nur Bericht, nichts schreiben
    --apply:             fehlende §2-Pflichtdateien via scaffold anlegen.
                         Verbotene Dateien werden NUR gemeldet, NICHT
                         geloescht (Mensch entscheidet). Manifest wird
                         NUR gemeldet, NICHT automatisch erweitert.

Der echte §7-Migrations-Workflow (A-D) braucht menschliche Entscheidungen
und wird hier bewusst NICHT automatisiert.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

from werkstatt.scaffold import PFLICHTDATEIEN, scaffold

MANIFEST_PFLICHT = [
    "entry", "status", "roadmap", "architecture",
    "conventions", "adr_index", "glossary",
]

# §3 — Verbotene Dateien. `None` = Datei/Ordner-Pfad exakt.
VERBOTEN = {
    "docs/README.md": "docs/index.md",
    "docs/INDEX.md": "docs/index.md",
    "docs/DECISIONS.md": "docs/adr/",
    "docs/ERLEDIGT.md": "PROGRESS.md (root)",
    "docs/OFFENE-BLOECKE.md": "docs/STATUS.md",
    "docs/PROGRESS.md": "PROGRESS.md (root)",
    "Bau-Handoff-Archiv.md": "docs/archiv/",
}

VERBOTENE_ORDNER = [
    "docs/glossary",  # als Ordner verboten, Datei docs/glossary.md erlaubt
]


def _manifest_pfad(project_dir: Path) -> Path | None:
    """Sucht projects/<name>.yaml AUSSCHLIESSLICH im Zielprojekt.

    Kein Fallback auf /opt/werkstatt — sonst wuerde jedes fremde Projekt
    faelschlich das security-ai-Manifest angezeigt bekommen.
    """
    p = project_dir / "projects"
    if p.is_dir():
        for f in p.glob("*.yaml"):
            if f.name.startswith("_"):
                continue
            return f
    return None


def _find_adr_0001(project_dir: Path) -> Path | None:
    """ADR-0001.md ODER ADR-0001-<slug>.md (Slug-Variante akzeptiert)."""
    adr = project_dir / "docs/adr"
    if not adr.is_dir():
        return None
    exact = adr / "ADR-0001.md"
    if exact.is_file():
        return exact
    for f in adr.glob("ADR-0001-*.md"):
        return f
    return None


def check_pflicht(project_dir: Path) -> dict[str, str]:
    """§2 — Pflichtdateien. Rueckgabe: rel -> 'ok' | 'fehlt' | 'ok (slug: X)'.

    Sonderfall ADR-0001: Slug-Variante `ADR-0001-<slug>.md` ist aequivalent
    (gewachsene Projekte haben meist eine Slug-ADR als erste echte Entscheidung).
    """
    bericht = {}
    for rel in PFLICHTDATEIEN:
        if rel == "docs/adr/ADR-0001.md":
            found = _find_adr_0001(project_dir)
            if found is None:
                bericht[rel] = "fehlt"
            elif found.name == "ADR-0001.md":
                bericht[rel] = "ok"
            else:
                bericht[rel] = f"ok (slug: {found.name})"
            continue
        ok = (project_dir / rel).is_file()
        bericht[rel] = "ok" if ok else "fehlt"
    return bericht


def check_verbote(project_dir: Path) -> dict[str, str]:
    """§3 — Verbotene Dateien/Ordner. Rueckgabe: rel -> 'verboten' (nur Funde)."""
    funde = {}
    for rel, ersatz in VERBOTEN.items():
        if (project_dir / rel).is_file():
            funde[rel] = f"verboten — Ersatz: {ersatz}"
    for rel in VERBOTENE_ORDNER:
        p = project_dir / rel
        if p.is_dir() and (project_dir / f"{rel}.md").is_file():
            funde[rel + "/"] = f"verbotener Ordner — Ersatz: {rel}.md"
        elif p.is_dir():
            funde[rel + "/"] = "verbotener Ordner — kein .md-Ersatz gefunden"
    return funde


def check_manifest(project_dir: Path) -> dict[str, str]:
    """§6 — Manifest-Pflichtfelder. Rueckgabe: feld -> 'ok' | 'fehlt' | 'n/a'."""
    if yaml is None:
        return {feld: "n/a (yaml fehlt)" for feld in MANIFEST_PFLICHT}
    mp = _manifest_pfad(project_dir)
    if not mp or not mp.is_file():
        return {feld: "n/a (kein Manifest)" for feld in MANIFEST_PFLICHT}
    try:
        data = yaml.safe_load(mp.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return {feld: "n/a (Manifest unlesbar)" for feld in MANIFEST_PFLICHT}
    docs = data.get("docs") or {}
    return {
        feld: "ok" if feld in docs else "fehlt"
        for feld in MANIFEST_PFLICHT
    }


def check_status(project_dir: Path) -> tuple[str, int]:
    """§5 — STATUS.md: OP-NNN oder expliziter Leer-Marker."""
    p = project_dir / "docs/STATUS.md"
    if not p.is_file():
        return ("kein STATUS.md", 0)
    text = p.read_text(encoding="utf-8")
    anzahl_op = text.count("### OP-")
    hat_leer = "(Noch keine" in text or "Noch keine Punkte" in text or "## Offene Punkte\n\n(leer" in text
    if anzahl_op == 0 and not hat_leer:
        return ("FORMAT: keine OP-NNN und kein Leer-Marker", 0)
    return ("ok", anzahl_op)


def migriere(
    name: str,
    project_dir: Path,
    *,
    apply: bool = False,
) -> dict[str, object]:
    """Prueft + (optional) legt fehlende §2-Pflichtdateien an."""
    if not project_dir.is_dir():
        raise NotADirectoryError(f"Zielverzeichnis fehlt: {project_dir}")

    pflicht = check_pflicht(project_dir)
    verbote = check_verbote(project_dir)
    manifest = check_manifest(project_dir)
    status_info, op_anzahl = check_status(project_dir)

    bericht: dict[str, object] = {
        "project": name,
        "dir": str(project_dir),
        "pflicht": pflicht,
        "verbote": verbote,
        "manifest": manifest,
        "status": {"info": status_info, "op_anzahl": op_anzahl},
        "apply": apply,
    }

    fehlende = [rel for rel, st in pflicht.items() if st == "fehlt"]

    if apply and fehlende:
        scaf_bericht = scaffold(name, project_dir)
        bericht["scaffold_bericht"] = scaf_bericht
        bericht["pflicht"] = check_pflicht(project_dir)

    if verbote:
        bericht["warnung"] = (
            "Verbotene Dateien NUR gemeldet. Manuelle Migration noetig "
            "(siehe DOC_CONVENTIONS.md §3 fuer Ersatz)."
        )

    return bericht


def print_bericht(bericht: dict) -> None:
    print(f"\nMigrator: {bericht['project']} ({bericht['dir']})")
    print(f"  apply: {bericht['apply']}\n")

    pflicht = bericht["pflicht"]
    fehlend = [r for r, s in pflicht.items() if s == "fehlt"]
    print(f"§2 Pflichtdateien: {len(pflicht) - len(fehlend)}/{len(pflicht)} ok")
    for rel, st in pflicht.items():
        if st == "fehlt":
            print(f"    FEHLT: {rel}")
        elif st != "ok":
            print(f"    {rel}: {st}")

    verbote = bericht["verbote"]
    if verbote:
        print(f"\n§3 Verbotene Dateien ({len(verbote)}):")
        for rel, info in verbote.items():
            print(f"    {rel}: {info}")
    else:
        print("\n§3 Verbotene Dateien: keine")

    manifest = bericht["manifest"]
    ok = sum(1 for s in manifest.values() if s == "ok")
    mf = [f for f, s in manifest.items() if s == "fehlt"]
    na = [f for f, s in manifest.items() if s.startswith("n/a")]
    if na:
        print(f"\n§6 Manifest: n/a ({len(na)} Felder, kein Manifest gefunden)")
    else:
        print(f"\n§6 Manifest: {ok}/{len(manifest)} ok")
        for feld in mf:
            print(f"    FEHLT: docs.{feld}")

    st = bericht["status"]
    print(f"\n§5 STATUS.md: {st['info']} (OP-NNN: {st['op_anzahl']})")

    if bericht.get("warnung"):
        print(f"\nWARNUNG: {bericht['warnung']}")
    if bericht.get("scaffold_bericht"):
        neu = [r for r, s in bericht["scaffold_bericht"].items() if s == "angelegt"]
        print(f"\nScaffold hat angelegt: {len(neu)} Datei(en)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m werkstatt.migrate",
        description="Prueft und (mit --apply) migriert Projekt-Doku.",
    )
    parser.add_argument("name", help="Projektname (z.B. 'security-ai')")
    parser.add_argument("--dir", required=True, help="Zielverzeichnis (absolut)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Nur Bericht (Default).")
    parser.add_argument("--apply", action="store_true",
                        help="Fehlende §2-Pflichtdateien anlegen. Verbotene "
                             "Dateien NUR melden, nicht loeschen.")
    args = parser.parse_args(argv)

    if args.dry_run and args.apply:
        print("FEHLER: --dry-run und --apply schliessen sich aus.", file=sys.stderr)
        return 2

    project_dir = Path(args.dir)
    try:
        bericht = migriere(args.name, project_dir, apply=args.apply)
    except NotADirectoryError as e:
        print(f"FEHLER: {e}", file=sys.stderr)
        return 1

    print_bericht(bericht)

    # Exit-Code: 1 wenn §3-Verbote ODER §2-Fehler ODER §6-Fehler ODER §5-Format
    fehler = (
        bool(bericht["verbote"])
        or any(s == "fehlt" for s in bericht["pflicht"].values())
        or any(s == "fehlt" for s in bericht["manifest"].values())
        or bericht["status"]["info"].startswith("FORMAT")
    )
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main())
