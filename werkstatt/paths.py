"""Zentrale Pfad-Aufloesung (OP-102).

Problem: vor diesem Modul gab es 6+ Stellen mit hardcoded
``/opt/werkstatt`` oder ``Path.cwd() / "projects"`` — jedes Modul hat
seine eigene cwd-Annahme. Das brach OP-091 (`_home_kontext`), das wuerde
brechen wenn der Loop von einem anderen cwd startet, und die Config
`projects/*.yaml` wird an manchen Stellen nicht gefunden.

Loesung: Alle Pfade ueber dieses Modul. Reihenfolge:
1. Env-Var ``WERKSTATT_HOME`` (explizit, fuer Tests/CI).
2. Modul-Datei ``werkstatt/__init__.py`` -> parent.parent (robust, cwd-unabhaengig).

Public API:
    werkstatt_home() -> Path
    projects_dir() -> Path
    project_config(project_name) -> Path
    audit_logs_dir(project_name=None) -> Path
    tools_dir() -> Path
"""
from __future__ import annotations

import os
from pathlib import Path


def werkstatt_home() -> Path:
    """Wurzel der Werkstatt-Installation (cwd-unabhaengig).

    Reihenfolge:
    1. ``WERKSTATT_HOME`` Env-Var (Tests/CI).
    2. Aus ``werkstatt/__init__.py`` abgeleitet.
    """
    env = os.environ.get("WERKSTATT_HOME")
    if env:
        return Path(env).expanduser().resolve()
    return Path(__file__).resolve().parent.parent


def projects_dir() -> Path:
    """Verzeichnis der Projekt-Configs (``projects/*.yaml``)."""
    return werkstatt_home() / "projects"


def project_config(project_name: str) -> Path:
    """Pfad zur Projekt-Config ``projects/<name>.yaml``."""
    return projects_dir() / f"{project_name}.yaml"


def audit_logs_dir(project_name: str | None = None) -> Path:
    """Audit-Log-Verzeichnis.

    Wenn ``project_name`` gesetzt: aus Projekt-Config ``home`` lesen,
    sonst ``werkstatt_home() / "audit-logs"``.
    """
    if project_name:
        try:
            import yaml
            with project_config(project_name).open(encoding="utf-8") as fh:
                cfg = yaml.safe_load(fh) or {}
            home = cfg.get("home")
            if home:
                return Path(home).expanduser() / "audit-logs"
        except (OSError, ValueError, TypeError):
            pass
    return werkstatt_home() / "audit-logs"


def tools_dir() -> Path:
    """Werkstatt-Tools-Verzeichnis (``tools/``)."""
    return werkstatt_home() / "tools"


__all__ = [
    "audit_logs_dir",
    "project_config",
    "projects_dir",
    "tools_dir",
    "werkstatt_home",
]
