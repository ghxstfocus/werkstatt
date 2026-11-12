"""Serverseitige, gemeinsame Anlage lokaler Werkstatt-Projekte.

UI und Metaorchestrator verwenden denselben typisierten Einstiegspunkt:
Name/Pfad pruefen, Projektdokumente scaffolden und anschliessend ein
startbares Loop-Manifest ohne Ueberschreiben registrieren.
"""
from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import yaml

from werkstatt.paths import project_config
from werkstatt.scaffold import scaffold

_PROJEKTNAME = re.compile(r"^[a-z][a-z0-9_-]{0,50}$")
_DOCS = {
    "entry": "AGENTS.md",
    "status": "docs/STATUS.md",
    "roadmap": "docs/ROADMAP.md",
    "architecture": "docs/ARCHITECTURE.md",
    "progress": "PROGRESS.md",
    "conventions": "docs/CONVENTIONS.md",
    "adr_index": "docs/adr/README.md",
    "glossary": "docs/glossary.md",
}


@dataclass(frozen=True, slots=True)
class LocalProjectResult:
    """Ergebnis der Anlage, unabhaengig von UI- oder Chat-Aufrufern."""

    name: str
    project_dir: Path
    manifest: Path
    bericht: dict[str, str]

    def as_dict(self) -> dict[str, Any]:
        """Serialisiert das Ergebnis fuer den Web-API-Vertrag."""
        return {
            "name": self.name,
            "project_dir": str(self.project_dir),
            "manifest": str(self.manifest),
            "bericht": dict(self.bericht),
        }


def _write_manifest_exclusive(manifest: Path, daten: dict[str, Any]) -> None:
    """Schreibt erst vollstaendig in Tempdatei, danach atomar ohne Replace."""
    temp_path: Path | None = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=manifest.parent,
            prefix=f".{manifest.name}.",
            suffix=".tmp",
            delete=False,
        ) as fh:
            temp_path = Path(fh.name)
            yaml.safe_dump(
                daten,
                fh,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
            )
            fh.flush()
            os.fsync(fh.fileno())
        # Hard-link creation is atomic and fails if another request registered
        # the same project name first. Both paths are in the same filesystem.
        os.link(temp_path, manifest)
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass


def create_local_project(
    name: str,
    project_dir: Path,
    *,
    allowed_root: Path = Path("/opt"),
) -> LocalProjectResult:
    """Scaffoldet ein neues Serverprojekt und registriert sein Loop-Manifest.

    Bestehende Verzeichnisse und Manifeste werden fail-closed abgewiesen.
    Bei einem Fehler nach dem Anlegen des Zielverzeichnisses wird nur dieses
    neu von diesem Aufruf angelegte Verzeichnis entfernt.
    """
    if not isinstance(name, str) or not _PROJEKTNAME.fullmatch(name):
        raise ValueError("ungueltiger Projektname")
    basis = allowed_root.expanduser().resolve()
    ziel = project_dir.expanduser().resolve()
    try:
        ziel.relative_to(basis)
    except ValueError as exc:
        raise ValueError(f"Projektpfad muss innerhalb {basis} liegen") from exc
    if ziel == basis:
        raise ValueError("Projektpfad darf nicht die Projektbasis sein")
    manifest = project_config(name)
    if ziel.exists():
        raise FileExistsError(f"Projektpfad existiert bereits: {ziel}")
    if manifest.exists():
        raise FileExistsError(f"Projekt-Manifest existiert bereits: {manifest}")

    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.mkdir(exist_ok=False)
    manifest_angelegt = False
    try:
        bericht = scaffold(name, ziel)
        manifest.parent.mkdir(parents=True, exist_ok=True)
        daten = {
            "project": name,
            "project_dir": str(ziel),
            "home": str(ziel),
            "docs": dict(_DOCS),
            "venv_python": "python3",
            "require_human_approval": True,
            "review_commit_package": True,
        }
        _write_manifest_exclusive(manifest, daten)
        manifest_angelegt = True
    except Exception:
        if manifest_angelegt:
            manifest.unlink(missing_ok=True)
        shutil.rmtree(ziel, ignore_errors=True)
        raise

    return LocalProjectResult(name, ziel, manifest, bericht)
