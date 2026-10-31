"""Werkstatt-Orchestrator (M-299d, 2026-10-24).

Entkopplung von pipeline.py:
  - load_project_config
  - load_docs
  - build_run_state

Vorher lagen load_project_config/load_docs in pipeline.py
(6377 Zeilen Monolith). Die Funktionen sind 1:1 hierher
verschoben. pipeline.py behaelt Re-Exporte fuer
Backward-Compat (M-299d-Strangler-Fig).
"""
from __future__ import annotations

import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from werkstatt.state import RunState

PROJECTS_DIR = Path("/opt/werkstatt/projects")


def load_project_config(project_name: str) -> dict[str, Any]:
    """Laedt die Projekt-Konfiguration aus /opt/werkstatt/projects/.

    Kein CWD-Bezug. Fail closed, wenn Projekt oder Datei fehlt.

    M-299d: 1:1 aus pipeline.py:337-354.
    """
    if not project_name or "/" in project_name or ".." in project_name:
        print(f"[FAIL] Ungueltiger Projektname: {project_name!r}. Fail closed.")
        sys.exit(1)
    path = PROJECTS_DIR / f"{project_name}.yaml"
    if not path.exists():
        print(f"[FAIL] Projekt-Konfiguration fehlt: {path}. Fail closed.")
        sys.exit(1)
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        print(f"[FAIL] Projekt-Konfiguration ist kein dict: {path}. Fail closed.")
        sys.exit(1)
    return data



# DOC_CONVENTIONS.md §6 — Loop-Lese-Reihenfolge.
# entry > status > roadmap > architecture > conventions > adr_index > glossary.
# Unbekannte Keys landen alphabetisch am Ende.
_DOCS_PRIORITAET = [
    "entry", "status", "roadmap", "architecture",
    "conventions", "adr_index", "glossary",
]


def _sortiere_docs_nach_prioritaet(
    docs_config: dict[str, str],
) -> list[tuple[str, str]]:
    """Sortiert docs_config nach Loop-Lese-Reihenfolge (DOC_CONVENTIONS.md §6)."""
    prio = {k: i for i, k in enumerate(_DOCS_PRIORITAET)}
    return sorted(
        docs_config.items(),
        key=lambda kv: (prio.get(kv[0], len(_DOCS_PRIORITAET)), kv[0]),
    )

def load_docs(docs_config: dict[str, str], project_dir: Path) -> dict[str, str]:
    """Laedt die Pflichtdokumente aus dem Zielprojekt.

    M-299d: 1:1 aus pipeline.py:3035-3043.
    """
    docs: dict[str, str] = {}
    for key, rel in _sortiere_docs_nach_prioritaet(docs_config):
        path = project_dir / rel
        if not path.exists():
            print(f"[FAIL] Pflichtdokument fehlt: {rel}. Fail closed.")
            sys.exit(1)
        docs[key] = path.read_text(encoding="utf-8")
    return docs


def build_run_state(
    project_name: str,
    aufgabe: str,
    *,
    project_dir: Path | None = None,
) -> RunState:
    """Baut einen minimalen RunState (M-299d-Helper).

    Wird von main() genutzt, um RunState ohne pipeline-Import
    zu erzeugen.

    args:
      project_name: Projektname (aus projects/<name>.yaml).
      aufgabe: Aufgabentext.
      project_dir: Zielprojekt-Pfad (None -> aus Config).
    """
    import os as _os

    cfg = load_project_config(project_name)
    pd_str = cfg.get("project_dir")
    if not pd_str:
        raise ValueError(f"project_dir fehlt in projects/{project_name}.yaml")
    pd = Path(pd_str) if project_dir is None else project_dir

    api_key = _os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY fehlt")

    docs: dict[str, str] = {}
    try:
        docs = load_docs(cfg.get("docs", {}), pd)
    except SystemExit:
        # load_docs ruft sys.exit bei fehlenden Dateien.
        # In build_run_state tolerieren wir das (leerer Kontext).
        docs = {}
    except Exception:  # noqa: BLE001
        docs = {}

    state = RunState(
        block_id=project_name,
        aufgabe=aufgabe,
        start_ts=datetime.now(UTC).isoformat(timespec="seconds"),
        docs=docs,
        agents={},
        always={},
        optional={},
        file_whitelist=[],
        api_key=api_key,
        budget={},
        agent_docs={},
        project_dir=pd,
        project_name=project_name,
    )
    state.start_monotonic = time.monotonic()
    return state
