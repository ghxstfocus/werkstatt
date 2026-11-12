"""Serverseitige Projektanlage scaffoldet Doku und registriert ein Loop-Manifest."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from werkstatt import project_creation


def test_create_local_project_scaffolds_and_registers_start_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    project_dir = tmp_path / "opt" / "loreipsum"
    config_dir = tmp_path / "werkstatt" / "projects"
    monkeypatch.setattr(
        project_creation,
        "project_config",
        lambda name: config_dir / f"{name}.yaml",
    )

    result = project_creation.create_local_project(
        "loreipsum", project_dir, allowed_root=tmp_path / "opt",
    )

    assert result.name == "loreipsum"
    assert result.manifest == config_dir / "loreipsum.yaml"
    assert (project_dir / "AGENTS.md").is_file()
    assert (project_dir / "docs" / "STATUS.md").is_file()
    assert (project_dir / "docs" / "ROADMAP.md").is_file()
    manifest = yaml.safe_load((config_dir / "loreipsum.yaml").read_text("utf-8"))
    assert manifest["project"] == "loreipsum"
    assert manifest["project_dir"] == str(project_dir.resolve())
    assert manifest["docs"]["status"] == "docs/STATUS.md"
    assert manifest["require_human_approval"] is True

    from werkstatt import orchestrator

    monkeypatch.setattr(orchestrator, "PROJECTS_DIR", config_dir)
    loaded = orchestrator.load_project_config("loreipsum")
    assert loaded["project_dir"] == str(project_dir.resolve())


@pytest.mark.parametrize("name", ["", "../outside", "BadName", "a" * 52])
def test_create_local_project_rejects_invalid_name(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, name: str,
) -> None:
    monkeypatch.setattr(
        project_creation, "project_config",
        lambda value: tmp_path / "projects" / f"{value}.yaml",
    )
    target = tmp_path / "target"

    with pytest.raises(ValueError, match="Projektname"):
        project_creation.create_local_project(
            name, target, allowed_root=tmp_path,
        )

    assert not target.exists()


def test_create_local_project_rejects_paths_outside_allowed_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        project_creation, "project_config",
        lambda name: tmp_path / "projects" / f"{name}.yaml",
    )

    with pytest.raises(ValueError, match="innerhalb"):
        project_creation.create_local_project(
            "loreipsum", tmp_path / "outside",
            allowed_root=tmp_path / "opt",
        )

    assert not (tmp_path / "outside").exists()


def test_create_local_project_never_overwrites_existing_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    target = tmp_path / "existing"
    target.mkdir()
    marker = target / "keep.txt"
    marker.write_text("preserve", encoding="utf-8")
    monkeypatch.setattr(
        project_creation, "project_config",
        lambda name: tmp_path / "projects" / f"{name}.yaml",
    )

    with pytest.raises(FileExistsError, match="existiert bereits"):
        project_creation.create_local_project(
            "loreipsum", target, allowed_root=tmp_path,
        )

    assert marker.read_text(encoding="utf-8") == "preserve"


def test_create_local_project_rejects_manifest_collision(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    target = tmp_path / "new-project"
    config = tmp_path / "projects" / "loreipsum.yaml"
    config.parent.mkdir()
    config.write_text("keep: true\n", encoding="utf-8")
    monkeypatch.setattr(project_creation, "project_config", lambda _name: config)

    with pytest.raises(FileExistsError, match="Manifest"):
        project_creation.create_local_project(
            "loreipsum", target, allowed_root=tmp_path,
        )

    assert not target.exists()
    assert config.read_text(encoding="utf-8") == "keep: true\n"


def test_create_local_project_cleans_new_directory_after_scaffold_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    target = tmp_path / "new-project"
    config = tmp_path / "projects" / "loreipsum.yaml"
    monkeypatch.setattr(project_creation, "project_config", lambda _name: config)

    def fail_after_partial_write(name: str, directory: Path) -> dict[str, str]:
        (directory / "partial.txt").write_text("partial", encoding="utf-8")
        raise ValueError("invalid scaffold")

    monkeypatch.setattr(project_creation, "scaffold", fail_after_partial_write)
    with pytest.raises(ValueError, match="invalid scaffold"):
        project_creation.create_local_project(
            "loreipsum", target, allowed_root=tmp_path,
        )

    assert not target.exists()
    assert not config.exists()
