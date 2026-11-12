"""Tests fuer den strukturellen Living-Docs-Vertrag pro Projekt."""
from __future__ import annotations

from pathlib import Path

import pytest

from werkstatt.doc_contract import REQUIRED_DOC_KEYS, validate_project_docs

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


def _write_docs(root: Path) -> None:
    for key, rel in _DOCS.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        body = "## Dokument\nInhalt.\n"
        if key == "status":
            body = "## Offene Punkte\n\n(Noch keine.)\n"
        path.write_text(body, encoding="utf-8")


def test_empty_scaffold_status_is_valid(tmp_path: Path) -> None:
    _write_docs(tmp_path)
    assert validate_project_docs(tmp_path, _DOCS) == []


def test_status_requires_open_op_or_explicit_empty_marker(tmp_path: Path) -> None:
    _write_docs(tmp_path)
    (tmp_path / _DOCS["status"]).write_text(
        "# Status\n\nUnstrukturierter Zustand.\n", encoding="utf-8"
    )
    errors = validate_project_docs(tmp_path, _DOCS)
    assert any("STATUS.md" in error for error in errors)


@pytest.mark.parametrize("bad_path", ["../outside.md", r"..\outside.md", "/tmp/outside.md"])
def test_rejects_manifest_paths_outside_project(tmp_path: Path, bad_path: str) -> None:
    _write_docs(tmp_path)
    docs = dict(_DOCS, roadmap=bad_path)
    errors = validate_project_docs(tmp_path, docs)
    assert any("unsicherer Pfad" in error for error in errors)


def test_rejects_unresolved_template_placeholder(tmp_path: Path) -> None:
    _write_docs(tmp_path)
    (tmp_path / _DOCS["architecture"]).write_text(
        "# {{project_name}}\n", encoding="utf-8"
    )
    errors = validate_project_docs(tmp_path, _DOCS)
    assert any("Platzhalter" in error for error in errors)


def test_reports_missing_manifest_key(tmp_path: Path) -> None:
    _write_docs(tmp_path)
    docs = dict(_DOCS)
    del docs["glossary"]
    errors = validate_project_docs(tmp_path, docs)
    assert any("glossary" in error for error in errors)
    assert set(REQUIRED_DOC_KEYS) - docs.keys() == {"glossary"}


def test_build_run_state_fails_closed_on_structural_doc_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_docs(tmp_path)
    (tmp_path / _DOCS["status"]).write_text("# Status\n\nNo queue.\n", encoding="utf-8")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr(
        "werkstatt.orchestrator.load_project_config",
        lambda _name: {"project_dir": str(tmp_path), "docs": _DOCS},
    )
    from werkstatt import orchestrator

    with pytest.raises(SystemExit):
        orchestrator.build_run_state("demo", "Aufgabe", project_dir=tmp_path)
