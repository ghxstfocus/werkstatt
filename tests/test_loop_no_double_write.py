"""Spec: apply_patches schreibt nur einmal (Fix W)."""
from __future__ import annotations
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, "/opt/werkstatt")
import pytest


class TestNoDoubleWrite:
    def test_applied_count_einmal_pro_patch(self, tmp_path: Path) -> None:
        import werkstatt.loop as _loop
        (tmp_path / "x.md").write_text("alt\n")
        state = SimpleNamespace(
            project_dir=tmp_path,
            project_name="test",
            patches=[],
            applied_count=0,
        )
        patches = [{
            "action": "update", "file": "x.md",
            "old_string": "alt\n", "new_string": "neu\n",
        }]
        result = _loop._apply_patches_with_hooks(state, patches)
        assert result == 1, f"Erwartet 1, war {result}"
        assert (tmp_path / "x.md").read_text() == "neu\n"
