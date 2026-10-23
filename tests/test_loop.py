"""Tests fuer werkstatt/loop.py (Phase 2: B1 + B2)."""
from __future__ import annotations

from unittest.mock import patch

from werkstatt.loop import _plan_gate, _verify_patches, run_pipeline_loop
from werkstatt.state import RunState


def _state(tmp_path, tasks=True, tests=True, akz=True):
    st = RunState(
        block_id="t", aufgabe="a", start_ts="",
        docs={}, agents={}, always={}, optional={},
        file_whitelist=[], api_key="", budget={},
        agent_docs={}, project_dir=tmp_path, project_name="p"
    )
    st.tasks = ["Task 1"] if tasks else []
    st.tests = ["Test 1"] if tests else []
    st.akzeptanzkriterien = ["Kriterium 1"] if akz else []
    return st


def test_plan_gate_ok(tmp_path):
    st = _state(tmp_path)
    assert _plan_gate(st) is True


def test_plan_gate_fails_ohne_tasks(tmp_path):
    st = _state(tmp_path, tasks=False)
    assert _plan_gate(st) is False


def test_plan_gate_fails_ohne_tests(tmp_path):
    st = _state(tmp_path, tests=False)
    assert _plan_gate(st) is False


def test_verify_patches_ok(tmp_path):
    st = _state(tmp_path)
    with patch("werkstatt.loop.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '{"ok": true}'
        assert _verify_patches(st) is True


def test_verify_patches_fails(tmp_path):
    st = _state(tmp_path)
    with patch("werkstatt.loop.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '{"ok": false}'
        assert _verify_patches(st) is False


def test_loop_stoppt_bei_plan_gate_fail(tmp_path):
    st = _state(tmp_path, tasks=False)
    with patch("pipeline.run_pipeline") as mock_rp, \
         patch("werkstatt.loop.audit") as mock_audit:
        rc = run_pipeline_loop("p", "a", [st])
        assert rc == 1
        mock_rp.assert_not_called()
        mock_audit.assert_called_with("loop_gate_failed", {"gate": "plan"}, st.project_dir, st.project_name)


def test_loop_stoppt_bei_verify_fail(tmp_path):
    st = _state(tmp_path)
    with patch("werkstatt.loop._verify_patches", return_value=False), \
         patch("pipeline.run_pipeline") as mock_rp, \
         patch("werkstatt.loop.audit") as mock_audit:
        rc = run_pipeline_loop("p", "a", [st])
        assert rc == 1
        mock_rp.assert_not_called()
        mock_audit.assert_called_with("loop_gate_failed", {"gate": "verify"}, st.project_dir, st.project_name)


def test_loop_delegiert_wenn_gates_gruen(tmp_path):
    st = _state(tmp_path)
    with patch("werkstatt.loop._verify_patches", return_value=True), \
         patch("pipeline.run_pipeline", return_value=42) as mock_rp, \
         patch("werkstatt.loop.audit"):
        rc = run_pipeline_loop("p", "a", [st])
        assert rc == 42
        mock_rp.assert_called_once()
