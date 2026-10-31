"""Spec: Hook blockt keine stdlib-Imports (Fix AM)."""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "/opt/werkstatt")
import pytest


class TestHookStdlibImports:
    def _call_hook(self, patch: str, project_dir: Path) -> dict:
        p = subprocess.run(
            [sys.executable, "/opt/werkstatt/hooks/pre_tool_use.py"],
            input=json.dumps({"patch": patch,
                              "project_dir": str(project_dir),
                              "action": "create"}),
            capture_output=True, text=True,
        )
        return json.loads(p.stdout)

    def test_urllib_error_erlaubt(self, tmp_path: Path) -> None:
        out = self._call_hook(
            "import urllib.error\nimport urllib.request\n", tmp_path)
        assert out["allow"] is True, out["reason"]

    def test_socket_erlaubt(self, tmp_path: Path) -> None:
        out = self._call_hook("import socket\n", tmp_path)
        assert out["allow"] is True

    def test_ssl_erlaubt(self, tmp_path: Path) -> None:
        out = self._call_hook("import ssl\n", tmp_path)
        assert out["allow"] is True

    def test_erfundenes_modul_blockt_weiter(self, tmp_path: Path) -> None:
        out = self._call_hook("import nicht_existentes_modul_xyz\n", tmp_path)
        assert out["allow"] is False
