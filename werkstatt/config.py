"""Projekt-Config-Wrapper (A4-a).

Kapselt das dict, das `_lade_und_pruefe_projekt` heute
zurueckgibt. Defaults zentral, Bestandsaufrufe bleiben
via `.get()` funktional.

Neue Aufrufe sollen Properties nutzen (typisiert), alte
`.get()`-Aufrufe werden schrittweise migriert.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

_DEFAULT_VENV = ".venv/bin/python3"
_DEFAULT_AGENTS_DIR = "/opt/werkstatt/agents"


class Config:
    """Projekt-Config mit zentralen Defaults."""

    def __init__(self, raw: dict[str, Any]) -> None:
        self._raw = raw

    # --- dict-Kompatibilitaet ---
    def get(self, key: str, default: Any = None) -> Any:
        return self._raw.get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self._raw[key]

    def __contains__(self, key: str) -> bool:
        return key in self._raw

    def __iter__(self):
        return iter(self._raw)

    def items(self):
        return self._raw.items()

    def keys(self):
        return self._raw.keys()

    def values(self):
        return self._raw.values()

    def raw(self) -> dict[str, Any]:
        """Original-dict (fuer load_docs etc., die dict erwarten)."""
        return self._raw

    # --- typisierte Properties ---
    @property
    def project(self) -> str:
        return str(self._raw.get("project", "unknown"))

    @property
    def project_dir(self) -> Path:
        return Path(
            self._raw.get("project_dir", str(Path.cwd()))
        ).expanduser()

    @property
    def project_agents_dir(self) -> str:
        return str(self._raw.get("project_agents_dir", _DEFAULT_AGENTS_DIR))

    @property
    def venv_python(self) -> str:
        return str(
            self._raw.get(
                "venv_python",
                str(self.project_dir / _DEFAULT_VENV),
            )
        )

    @property
    def docs(self) -> dict[str, str]:
        return dict(self._raw.get("docs", {}) or {})

    @property
    def file_whitelist(self) -> list[str]:
        return list(self._raw.get("file_whitelist", []) or [])

    @property
    def budget(self) -> dict[str, int]:
        return dict(self._raw.get("budget", {}) or {})

    @property
    def agent_docs(self) -> dict[str, list[str]]:
        return dict(self._raw.get("agent_docs", {}) or {})

    @property
    def planner(self) -> dict[str, Any]:
        return dict(self._raw.get("planner", {}) or {})

    @property
    def solver(self) -> dict[str, Any]:
        return dict(self._raw.get("solver", {}) or {})

    @property
    def git_author(self) -> dict[str, Any]:
        return dict(self._raw.get("git_author", {}) or {})

    @property
    def always_run(self) -> list[str]:
        return list(self._raw.get("always_run", []) or [])

    @property
    def optional_catalog(self) -> list[str]:
        return list(self._raw.get("optional_catalog", []) or [])

    @property
    def require_human_approval(self) -> bool:
        return bool(self._raw.get("require_human_approval", True))

    @property
    def review_commit_package(self) -> bool:
        return bool(self._raw.get("review_commit_package", True))
