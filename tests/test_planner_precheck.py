"""Spec: Deterministischer Pre-Check fuer Entfernen-Aufgaben (Fix S)."""
from __future__ import annotations
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, "/opt/werkstatt")
import pytest
from werkstatt.planner import _deterministic_entfernen_precheck


class TestEntfernenPrecheck:
    def test_punkt_fehlt_skip(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "STATUS.md").write_text(
            "# Status\n\n## Offene Punkte\n\n2. systemd\n3. Rollen\n"
        )
        state = SimpleNamespace(
            project_dir=tmp_path, project_name="test",
            aufgabe="In docs/STATUS.md den Punkt 1 entfernen.",
        )
        assert _deterministic_entfernen_precheck(state) is True
        assert state.auftrag_bereits_erfuellt is True

    def test_punkt_existiert_kein_skip(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "STATUS.md").write_text(
            "# Status\n\n## Offene Punkte\n\n1. AuditReaderError\n2. systemd\n"
        )
        state = SimpleNamespace(
            project_dir=tmp_path, project_name="test",
            aufgabe="In docs/STATUS.md den Punkt 1 entfernen.",
        )
        assert _deterministic_entfernen_precheck(state) is False

    def test_marker_fehlt_skip(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "STATUS.md").write_text(
            "# Status\n\nNur noch Cleanup.\n"
        )
        state = SimpleNamespace(
            project_dir=tmp_path, project_name="test",
            aufgabe="Entferne (AuditReaderError) aus docs/STATUS.md.",
        )
        assert _deterministic_entfernen_precheck(state) is True

    def test_marker_existiert_kein_skip(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "STATUS.md").write_text(
            "# Status\n\nAuditReaderError wird noch genutzt.\n"
        )
        state = SimpleNamespace(
            project_dir=tmp_path, project_name="test",
            aufgabe="Entferne (AuditReaderError) aus docs/STATUS.md.",
        )
        assert _deterministic_entfernen_precheck(state) is False

    def test_keine_entfernen_aufgabe_kein_check(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "STATUS.md").write_text("# Status\n")
        state = SimpleNamespace(
            project_dir=tmp_path, project_name="test",
            aufgabe="Baue eine neue Funktion in core/foo.py.",
        )
        assert _deterministic_entfernen_precheck(state) is False

    def test_keine_datei_kein_check(self, tmp_path: Path) -> None:
        state = SimpleNamespace(
            project_dir=tmp_path, project_name="test",
            aufgabe="Entferne Punkt 1.",
        )
        assert _deterministic_entfernen_precheck(state) is False
