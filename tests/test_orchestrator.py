"""Tests fuer werkstatt/orchestrator.py (M-299d)."""
from __future__ import annotations

import pytest

from werkstatt import orchestrator


def test_load_project_config_security_ai():
    """M-299d: load_project_config liest projects/security-ai.yaml."""
    cfg = orchestrator.load_project_config("security-ai")
    assert isinstance(cfg, dict)
    assert "project_dir" in cfg
    assert cfg["project_dir"] == "/opt/security-ai"


def test_load_project_config_fail_closed():
    """M-299d: load_project_config beendet bei fehlender Config."""
    with pytest.raises(SystemExit):
        orchestrator.load_project_config("nicht-existent-xyz")


def test_load_docs_liest_datei(tmp_path):
    """M-299d: load_docs liest konfigurierte Dateien."""
    (tmp_path / "a.md").write_text("# Doc A", encoding="utf-8")
    (tmp_path / "b.md").write_text("# Doc B", encoding="utf-8")
    docs = orchestrator.load_docs({"a": "a.md", "b": "b.md"}, tmp_path)
    assert docs == {"a": "# Doc A", "b": "# Doc B"}


def test_load_docs_fail_closed(tmp_path):
    """M-299d: load_docs beendet bei fehlender Datei."""
    with pytest.raises(SystemExit):
        orchestrator.load_docs({"missing": "nicht-da.md"}, tmp_path)
