"""Tests fuer werkstatt/loop.py (Phase 7a: Happy Path)."""
from __future__ import annotations

import subprocess
import sys
from unittest.mock import patch

from werkstatt.loop import _plan_gate, _verify_patches, run_pipeline_loop
from werkstatt.state import RunState


def _state(tmp_path, tasks=True, tests=True, akz=True):
    st = RunState(
        block_id="t", aufgabe="a", start_ts="",
        docs={}, agents={}, always={}, optional={},
        file_whitelist=[], api_key="fake", budget={},
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
    """Neue Version: Contract mit erfolgreichem Check -> True."""
    st = _state(tmp_path)
    contract_dir = tmp_path / ".werkstatt"
    contract_dir.mkdir()
    (contract_dir / "verify.json").write_text(
        '{"stages": [{"id": "ok", "command": ["python3", "-c", "import sys; sys.exit(0)"]}]}'
    )
    assert _verify_patches(st) is True


def test_verify_patches_fails(tmp_path):
    """Neue Version: Contract mit fehlschlagendem Check -> False."""
    st = _state(tmp_path)
    contract_dir = tmp_path / ".werkstatt"
    contract_dir.mkdir()
    (contract_dir / "verify.json").write_text(
        '{"stages": [{"id": "fail", "command": ["python3", "-c", "import sys; sys.exit(1)"]}]}'
    )
    assert _verify_patches(st) is False


def test_loop_planner_fail(tmp_path):
    # Plan-Gate fail -> Planner wird aufgerufen -> schlaegt fehl
    st = _state(tmp_path, tasks=False)
    with patch("werkstatt.loop.run_planner", return_value=False), \
         patch("werkstatt.loop.audit") as mock_audit:
        rc = run_pipeline_loop("p", "a", [st])
        assert rc == 1
        mock_audit.assert_called_with("loop_planner_failed", {}, st.project_dir, st.project_name)


def test_loop_stoppt_bei_verify_fail(tmp_path):
    st = _state(tmp_path)
    with patch("werkstatt.loop._verify_patches", return_value=False), \
         patch("werkstatt.loop.audit") as mock_audit:
        rc = run_pipeline_loop("p", "a", [st])
        assert rc == 1
        mock_audit.assert_called_with("loop_gate_failed", {"gate": "pre_build"}, st.project_dir, st.project_name)


def test_loop_happy_path(tmp_path):
    st = _state(tmp_path)
    # _verify_patches mocken (verhindert subprocess.run(pytest))
    with patch("werkstatt.loop._verify_patches", return_value=True), \
         patch("werkstatt.loop.run_planner", return_value=True), \
         patch("werkstatt.loop.run_builder", return_value=True), \
         patch("werkstatt.loop.run_explorer", return_value={"key_files": [], "findings": "", "next_reads": []}), \
         patch("werkstatt.loop.run_reviewer", return_value=True), \
         patch("pipeline._approval_und_human_gate", return_value=0), \
         patch("pipeline.load_project_config", return_value={}), \
         patch("werkstatt.loop.audit"):
        rc = run_pipeline_loop("p", "a", [st])
        assert rc == 0


def test_loop_cli_help_zeigt_usage():
    """CLI --help: argparse-usage + Exit 0."""
    result = subprocess.run(
        [sys.executable, "-m", "werkstatt.loop", "--help"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()
    assert "--project" in result.stdout


def test_loop_cli_requires_project():
    """CLI ohne --project: argparse-Fehler rc=2."""
    result = subprocess.run(
        [sys.executable, "-m", "werkstatt.loop"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode != 0
    assert "project" in (result.stderr + result.stdout).lower()


def test_loop_cli_dry_run_uses_renderer():
    """CLI --dry-run ruft Renderer header + footer auf, kein LLM."""
    from werkstatt import loop_renderer
    with patch.object(loop_renderer, "header") as m_h, \
         patch.object(loop_renderer, "footer") as m_f:
        from werkstatt.loop import main
        rc = main(["--project", "test-x", "--dry-run"])
    assert rc == 0
    assert m_h.called, "renderer.header muss aufgerufen werden"
    assert m_f.called, "renderer.footer muss aufgerufen werden"
