"""Tests fuer werkstatt/planner.py (Phase 5)."""
from __future__ import annotations

from unittest.mock import patch

from werkstatt.planner import run_planner
from werkstatt.state import RunState


def _state(tmp_path):
    return RunState(
        block_id="t", aufgabe="Baue Feature X", start_ts="",
        docs={"a": "doc a"}, agents={}, always={}, optional={},
        file_whitelist=[], api_key="fake", budget={},
        agent_docs={}, project_dir=tmp_path, project_name="p"
    )


def test_planner_erstellt_plan(tmp_path):
    st = _state(tmp_path)
    fake_json = '{"tasks": [{"id": "t1", "name": "A", "description": "B", "akzeptanzkriterien": ["c"]}], "tests": ["test_a"], "akzeptanzkriterien": ["done"]}'
    
    class FakeReply:
        ok = True
        content = fake_json
    
    with patch("werkstatt.planner.ask_llm", return_value=FakeReply()):
        result = run_planner(st)
        assert result is True
        assert len(st.tasks) == 1
        assert st.tests == ["test_a"]
        assert st.akzeptanzkriterien == ["done"]


def test_planner_ohne_key(tmp_path):
    st = _state(tmp_path)
    st.api_key = ""
    assert run_planner(st) is False


def test_planner_llm_fehler(tmp_path):
    st = _state(tmp_path)
    
    class FakeReply:
        ok = False
        error = "timeout"
    
    with patch("werkstatt.planner.ask_llm", return_value=FakeReply()):
        assert run_planner(st) is False
