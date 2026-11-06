"""Spec: Write-Fehler im Patch-Apply fail-closed (Fix N)."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, "/opt/werkstatt")
import werkstatt.loop as _loop

_here = Path(__file__).parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))
from factories import mk_state  # noqa: E402


class TestPatchWriteFailed:
    def test_write_error_bricht_sauber_ab(self, tmp_path: Path) -> None:
        (tmp_path / "x.md").write_text("alt\n")
        state = mk_state(
            project_dir=tmp_path,
            project_name="test",
            patches=[],
        )
        patches = [{
            "action": "update", "file": "x.md",
            "old_string": "alt\n", "new_string": "neu\n",
        }]

        def _bad_write(self, *a, **kw):
            raise OSError("test: keine Schreibrechte")

        with patch.object(Path, "write_text", _bad_write):
            result = _loop._apply_patches_with_hooks(state, patches)
        assert result == 0
