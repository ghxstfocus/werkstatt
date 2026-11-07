"""Spec: planner_gate erlaubt Config-Example-Dateien (Fix Y)."""
from __future__ import annotations

import sys

sys.path.insert(0, "/opt/werkstatt")


class TestPlannerGateSuffixe:
    def test_env_example_erlaubt(self) -> None:
        from hooks.planner_gate import _VALID_SUFFIXES
        assert ".example" in _VALID_SUFFIXES

    def test_env_template_erlaubt(self) -> None:
        from hooks.planner_gate import _VALID_SUFFIXES
        assert ".template" in _VALID_SUFFIXES

    def test_env_sample_erlaubt(self) -> None:
        from hooks.planner_gate import _VALID_SUFFIXES
        assert ".sample" in _VALID_SUFFIXES

    def test_env_dist_erlaubt(self) -> None:
        from hooks.planner_gate import _VALID_SUFFIXES
        assert ".dist" in _VALID_SUFFIXES

    def test_bestehende_suffixe_nicht_entfernt(self) -> None:
        from hooks.planner_gate import _VALID_SUFFIXES
        for s in (".py", ".sql", ".md", ".yaml", ".json"):
            assert s in _VALID_SUFFIXES, f"{s} fehlt"


class TestPlannerGateDotfiles:
    def test_gitignore_erlaubt(self) -> None:
        from hooks.planner_gate import _DOTFILES
        assert ".gitignore" in _DOTFILES

    def test_gitattributes_erlaubt(self) -> None:
        from hooks.planner_gate import _DOTFILES
        assert ".gitattributes" in _DOTFILES

    def test_dockerignore_erlaubt(self) -> None:
        from hooks.planner_gate import _DOTFILES
        assert ".dockerignore" in _DOTFILES
