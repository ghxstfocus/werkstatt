"""Tests fuer hooks/pre_tool_use.py (M-334a)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_HOOK = Path("/opt/werkstatt/hooks/pre_tool_use.py")


def _run_hook(patch: str, project_dir: Path) -> dict:
    payload = json.dumps({
        "patch": patch,
        "action": "update",
        "project_dir": str(project_dir),
    })
    res = subprocess.run(
        [sys.executable, str(_HOOK)],
        input=payload, capture_output=True, text=True, timeout=10, check=False,
    )
    assert res.returncode == 0, f"Hook rc={res.returncode}, stderr={res.stderr}"
    return json.loads(res.stdout)


def test_pre_tool_use_blockt_erfundenen_import(tmp_path):
    """M-334a: Import, der nicht existiert, wird geblockt."""
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "__init__.py").write_text("")

    result = _run_hook(
        "from harness.tool_registry.errors import ToolArgumentValueError\n",
        tmp_path,
    )
    assert result["allow"] is False
    assert "harness" in result["reason"]


def test_pre_tool_use_erlaubt_existierenden_import(tmp_path):
    """M-334a: Import, der existiert, wird erlaubt."""
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "__init__.py").write_text("")
    (tmp_path / "core" / "checks").mkdir()
    (tmp_path / "core" / "checks" / "__init__.py").write_text("")

    result = _run_hook("from core.checks import check_port\n", tmp_path)
    assert result["allow"] is True


def test_pre_tool_use_erlaubt_standard_library(tmp_path):
    """M-334a: Standard-Library-Imports werden erlaubt."""
    result = _run_hook("import sys\nimport json\nfrom pathlib import Path\n", tmp_path)
    assert result["allow"] is True


def test_pre_tool_use_erlaubt_kein_import(tmp_path):
    """M-334a: Patch ohne Imports wird erlaubt."""
    result = _run_hook("def foo():\n    return 1\n", tmp_path)
    assert result["allow"] is True
