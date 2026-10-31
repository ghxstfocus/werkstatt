"""Spec: Reviewer prueft Abschnitt-Anzahl bei create-.md-Tasks (Fix Q)."""
from __future__ import annotations
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, "/opt/werkstatt")
import pytest
import werkstatt.reviewer as _r


class TestReviewerVollstaendigkeit:
    def test_zu_wenig_abschnitte_fail_closed(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "PLAN.md").write_text(
            "# Titel\n\n## A\n## B\n## C\n"
        )
        with patch.object(_r, "_get_git_diff", lambda pd, task_files=None: "diff"):
            state = SimpleNamespace(
                project_dir=tmp_path, project_name="test",
                api_key="fake", patches=[{"a": "b"}],
                aktuelle_task={
                    "id": "t1", "action": "create",
                    "task_files": ["docs/PLAN.md"],
                },
                aufgabe=("Lege docs/PLAN.md an. Abschnitte: A, B, C, D, E, "
                         "F, G, H."),
                baseline_gruen=True,
                reviewer_bugs=[], reviewer_bugs_history=[],
            )
            result = _r.run_reviewer(state)
            assert result is False

    def test_alle_abschnitte_kein_fail(self, tmp_path: Path) -> None:
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "PLAN.md").write_text(
            "# Titel\n\n" + "\n".join(f"## {l}" for l in "ABCDEFGH") + "\n"
        )
        with patch.object(_r, "_get_git_diff", lambda pd, task_files=None: ""):
            state = SimpleNamespace(
                project_dir=tmp_path, project_name="test",
                api_key="fake", patches=[],
                aktuelle_task={
                    "id": "t1", "action": "create",
                    "task_files": ["docs/PLAN.md"],
                },
                aufgabe="Abschnitte: A, B, C, D, E, F, G, H.",
                baseline_gruen=True,
                reviewer_bugs=[], reviewer_bugs_history=[],
            )
            result = _r.run_reviewer(state)
            assert result is True
