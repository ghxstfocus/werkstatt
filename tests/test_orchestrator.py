"""Tests fuer werkstatt/orchestrator.py (M-299d)."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

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


def test_load_docs_fails_closed_on_read_error(tmp_path, monkeypatch):
    target = tmp_path / "broken.md"
    target.touch()
    original_read_text = Path.read_text

    def fail_target(path, *args, **kwargs):
        if path == target:
            raise OSError("simulierter Lesefehler")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fail_target)

    with pytest.raises(SystemExit):
        orchestrator.load_docs({"status": "broken.md"}, tmp_path)


def test_build_run_state_does_not_suppress_missing_docs(tmp_path, monkeypatch):
    monkeypatch.setattr(
        orchestrator,
        "load_project_config",
        lambda _name: {"project_dir": str(tmp_path), "docs": {"status": "missing.md"}},
    )
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

    with pytest.raises(SystemExit):
        orchestrator.build_run_state("demo", "Aufgabe", project_dir=tmp_path)


def test_werkstatt_manifest_loads_required_living_docs() -> None:
    config = yaml.safe_load(
        Path("projects/werkstatt.yaml").read_text(encoding="utf-8")
    )
    docs = config["docs"]

    assert docs["entry"] == "AGENTS.md"
    assert {
        "status", "roadmap", "architecture", "conventions", "adr_index",
    } <= docs.keys()


def test_load_project_config_rejects_missing_living_docs(tmp_path, monkeypatch):
    (tmp_path / "demo.yaml").write_text(
        "project: demo\nproject_dir: /tmp/demo\ndocs:\n  entry: AGENTS.md\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(orchestrator, "PROJECTS_DIR", tmp_path)

    with pytest.raises(SystemExit):
        orchestrator.load_project_config("demo")
