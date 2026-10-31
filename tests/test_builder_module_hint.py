"""Spec: Builder-Prompt erdet Modulnamen (Fix AQ)."""
from __future__ import annotations
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch as _p

sys.path.insert(0, "/opt/werkstatt")
import pytest


class TestModuleHint:
    def test_verfuegbare_module_im_prompt(self, tmp_path: Path) -> None:
        from werkstatt import builder as _b
        (tmp_path / "harness" / "llm").mkdir(parents=True)
        (tmp_path / "harness" / "llm" / "errors.py").write_text("class LLMError: pass\n")
        (tmp_path / "harness" / "llm" / "models.py").write_text("class LLMRequest: pass\n")
        (tmp_path / "harness" / "llm" / "client.py").write_text("x = 1\n")
        gesehener_prompt = {"user": ""}

        def _fake_ask(api_key, system, user, **kw):
            gesehener_prompt["user"] = user
            return SimpleNamespace(ok=True, content='{"patches": []}')

        state = SimpleNamespace(
            project_dir=tmp_path, project_name="t",
            aktuelle_task={
                "id": "t1", "action": "create",
                "task_files": ["harness/llm/deepseek_client.py"],
                "name": "DeepSeekClient", "description": "x",
            },
            architect_prosa="", builder_feedback={},
            reviewer_bugs=[], last_verify_errors=[],
            reflection_history=[],
        )
        with _p.object(_b, "ask_llm", _fake_ask):
            _b._build_patches_fuer_datei(
                state, "harness/llm/deepseek_client.py",
                "## harness/llm/deepseek_client.py\nNeu.", "key",
            )
        _user = gesehener_prompt["user"]
        assert "VERFUEGBARE MODULE" in _user
        assert "errors" in _user
        assert "models" in _user
