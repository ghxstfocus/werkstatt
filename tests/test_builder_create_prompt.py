"""Spec: Builder-Prompt fuer create-Task (Fix M)."""
from __future__ import annotations
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, "/opt/werkstatt")
import pytest
import werkstatt.builder as _b


class TestCreatePrompt:
    def test_create_task_ruft_llm_auch_wenn_datei_fehlt(self, tmp_path: Path) -> None:
        gesehener_prompt = {"user": ""}

        def _fake_ask(api_key, system, user, **kw):
            gesehener_prompt["user"] = user
            return SimpleNamespace(ok=True, content='{"patches": []}')

        state = SimpleNamespace(
            project_dir=tmp_path,
            project_name="test",
            aktuelle_task={
                "id": "t1", "name": "Neue Datei",
                "action": "create",
                "task_files": ["docs/NEU.md"],
                "description": "Datei anlegen",
            },
            architect_prosa="",
            builder_feedback={}, reviewer_bugs=[],
            last_verify_errors=[], reflection_history=[],
        )
        with patch.object(_b, "ask_llm", _fake_ask):
            _b._build_patches_fuer_datei(
                state, "docs/NEU.md", "## docs/NEU.md\nNeue Datei.", "key",
            )
        assert "DATEI IST NEU" in gesehener_prompt["user"], (
            f"Prompt enthaelt keinen CREATE-Hinweis: "
            f"{gesehener_prompt['user'][:500]}"
        )
        assert 'action="create"' in gesehener_prompt["user"]

    def test_update_task_fehler_datei_bleibt_fail_closed(self, tmp_path: Path) -> None:
        state = SimpleNamespace(
            project_dir=tmp_path,
            project_name="test",
            aktuelle_task={
                "id": "t1", "name": "Update",
                "action": "update",
                "task_files": ["docs/NICHT_DA.md"],
            },
        )
        r = _b._build_patches_fuer_datei(
            state, "docs/NICHT_DA.md", "## docs/NICHT_DA.md\nX.", "key",
        )
        assert r == []
