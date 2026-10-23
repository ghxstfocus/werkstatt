"""Tests fuer werkstatt/builder.py (Phase 6)."""
from __future__ import annotations

from unittest.mock import patch

from werkstatt.builder import run_builder
from werkstatt.state import RunState


def _state(tmp_path, tasks=None, api_key="fake"):
    return RunState(
        block_id="t", aufgabe="Baue Feature X", start_ts="",
        docs={}, agents={}, always={}, optional={},
        file_whitelist=[], api_key=api_key, budget={},
        agent_docs={}, project_dir=tmp_path, project_name="p"
    )


def test_builder_erstellt_patches(tmp_path):
    st = _state(tmp_path)
    st.tasks = [{"id": "t1", "name": "A", "description": "B"}]
    fake_json = '{"patches": [{"file": "a.py", "old_string": "x", "new_string": "y"}]}'

    class FakeReply:
        ok = True
        content = fake_json

    with patch("werkstatt.builder.ask_llm", return_value=FakeReply()):
        result = run_builder(st)
        assert result is True
        assert len(st.patches) == 1


def test_builder_ohne_key(tmp_path):
    st = _state(tmp_path, api_key="")
    st.tasks = [{"id": "t1"}]
    assert run_builder(st) is False


def test_builder_ohne_tasks(tmp_path):
    st = _state(tmp_path)
    st.tasks = []
    assert run_builder(st) is False
