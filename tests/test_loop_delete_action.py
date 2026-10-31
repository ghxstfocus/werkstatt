"""Spec: Fix AV — action="delete" im Loop.

Deckt zwei Schichten ab:
  - _delete_ziel_erlaubt: strukturelle Sicherheit (Whitelist, .git, migrations,
    Traversal, project_dir-Bounds).
  - _apply_patches_with_hooks: Delete-Anwendung (Reflection-Pfad ohne
    Task-Whitelist, da keine task_id gebunden).
Der Haupt-Build-Pfad in run_pipeline_loop nutzt dieselbe Helper-Funktion mit
der task-spezifischen Whitelist (task_files).
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, "/opt/werkstatt")

import werkstatt.loop as _loop


class TestDeleteZielErlaubt:
    def test_ok_in_whitelist(self, tmp_path: Path) -> None:
        ok, grund = _loop._delete_ziel_erlaubt(
            Path("harness/llm/client.py"),
            {"harness/llm/client.py", "harness/llm/ollama_client.py"},
            tmp_path,
        )
        assert ok is True and grund == ""

    def test_blocked_nicht_in_whitelist(self, tmp_path: Path) -> None:
        ok, grund = _loop._delete_ziel_erlaubt(
            Path("anderes.py"),
            {"harness/llm/client.py"},
            tmp_path,
        )
        assert ok is False and grund == "nicht_in_task_files"

    def test_blocked_git(self, tmp_path: Path) -> None:
        ok, grund = _loop._delete_ziel_erlaubt(
            Path(".git/config"), None, tmp_path,
        )
        assert ok is False and grund == ".git"

    def test_blocked_migrations(self, tmp_path: Path) -> None:
        ok, grund = _loop._delete_ziel_erlaubt(
            Path("data/migrations/0001_init.py"), None, tmp_path,
        )
        assert ok is False and grund == "migrations"

    def test_blocked_traversal(self, tmp_path: Path) -> None:
        ok, grund = _loop._delete_ziel_erlaubt(
            Path("../aussen.py"), None, tmp_path,
        )
        assert ok is False and grund == "pfad"

    def test_blocked_absolute(self, tmp_path: Path) -> None:
        ok, grund = _loop._delete_ziel_erlaubt(
            Path("/etc/passwd"), None, tmp_path,
        )
        assert ok is False and grund == "pfad"

    def test_blocked_symlink_ausserhalb(self, tmp_path: Path) -> None:
        # Ziel existiert, aber resolves ausserhalb project_dir.
        project = tmp_path / "proj"
        project.mkdir()
        aussen = tmp_path / "aussen.py"
        aussen.write_text("# x")
        link = project / "link.py"
        link.symlink_to(aussen)
        ok, grund = _loop._delete_ziel_erlaubt(
            Path("link.py"), None, project,
        )
        assert ok is False and grund == "ausserhalb_project_dir"


class TestApplyPatchesDelete:
    def _state(self, tmp_path: Path) -> SimpleNamespace:
        return SimpleNamespace(
            project_dir=tmp_path,
            project_name="testprojekt",
            patches=[],
        )

    def test_happy_path_datei_weg(self, tmp_path: Path) -> None:
        ziel = tmp_path / "harness" / "llm" / "client.py"
        ziel.parent.mkdir(parents=True)
        ziel.write_text("# leiche\n")
        st = self._state(tmp_path)
        with patch("werkstatt.loop._call_hook", return_value={"allow": True}), \
             patch("werkstatt.loop.audit"):
            n = _loop._apply_patches_with_hooks(
                st,
                [{"action": "delete", "file": "harness/llm/client.py"}],
                phase_label="test",
            )
        assert n == 1
        assert not ziel.exists()

    def test_missing_skip_kein_crash(self, tmp_path: Path) -> None:
        st = self._state(tmp_path)
        with patch("werkstatt.loop._call_hook", return_value={"allow": True}), \
             patch("werkstatt.loop.audit") as _aud:
            n = _loop._apply_patches_with_hooks(
                st,
                [{"action": "delete", "file": "fehlt.py"}],
                phase_label="test",
            )
        assert n == 0
        kinds = [c.args[0] for c in _aud.call_args_list]
        assert "loop_patch_delete_skip_missing" in kinds

    def test_git_blockiert(self, tmp_path: Path) -> None:
        st = self._state(tmp_path)
        with patch("werkstatt.loop._call_hook", return_value={"allow": True}), \
             patch("werkstatt.loop.audit") as _aud:
            n = _loop._apply_patches_with_hooks(
                st,
                [{"action": "delete", "file": ".git/config"}],
                phase_label="test",
            )
        assert n == 0
        kinds = [c.args[0] for c in _aud.call_args_list]
        assert "loop_patch_delete_blocked" in kinds
