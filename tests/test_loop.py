"""Tests fuer werkstatt/loop.py (Phase 1 Strangler-Fig)."""
from __future__ import annotations

from unittest.mock import patch

from werkstatt.loop import run_pipeline_loop
from werkstatt.state import RunState


def _state(tmp_path):
    st = RunState(
        block_id="t", aufgabe="a", start_ts="",
        docs={}, agents={}, always={}, optional={},
        file_whitelist=[], api_key="", budget={},
        agent_docs={}, project_dir=tmp_path, project_name="p"
    )
    return st


def test_loop_delegiert_an_pipeline(tmp_path):
    st = _state(tmp_path)
    with patch("pipeline.run_pipeline", return_value=42) as mock_rp, \
         patch("werkstatt.loop.audit") as mock_audit:
        rc = run_pipeline_loop("p", "a", [st])
        assert rc == 42
        mock_rp.assert_called_once()
        assert mock_audit.call_count == 2
        kinds = [c.args[0] for c in mock_audit.call_args_list]
        assert "loop_aktiv" in kinds
        assert "loop_fallback" in kinds


def test_loop_ohne_state(tmp_path):
    # Darf nicht crashen, auch wenn state_ref leer ist
    with patch("pipeline.run_pipeline", return_value=0) as mock_rp, \
         patch("werkstatt.loop.audit") as mock_audit:
        rc = run_pipeline_loop("p", "a", [])
        assert rc == 0
        mock_rp.assert_called_once()
        mock_audit.assert_not_called()  # Kein state -> kein audit
