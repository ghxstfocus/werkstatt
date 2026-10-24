"""Tests fuer werkstatt/progress.py (M-307b)."""
from __future__ import annotations

from werkstatt import progress


def test_progress_append_und_read(tmp_path):
    """M-307b: append + read_recent."""
    ok = progress.append(tmp_path, name="Task 1", status="done",
                        dateien=["README.md"], patch="+1 Zeile")
    assert ok is True

    ok = progress.append(tmp_path, name="Task 2", status="failed",
                        info="builder_failed")
    assert ok is True

    recent = progress.read_recent(tmp_path, n=10)
    assert "Task 1" in recent
    assert "Task 2" in recent
    assert "builder_failed" in recent


def test_progress_read_recent_format_drift(tmp_path):
    """M-307b: kaputter Block wird uebersprungen, nicht gecrasht."""
    progress_path = tmp_path / "PROGRESS.md"
    progress_path.write_text(
        "# Fortschritt: test\n\n"
        "## 2026-10-24T10:00:00 -- Task 1\n"
        "- **Status:** done\n\n"
        "kaputter Block ohne Header\n"
        "kein Parser-Anker\n\n"
        "## 2026-10-24T10:05:00 -- Task 2\n"
        "- **Status:** failed\n",
        encoding="utf-8",
    )

    recent = progress.read_recent(tmp_path, n=10)
    # Beide "## "-Bloecke werden gefunden
    assert "Task 1" in recent
    assert "Task 2" in recent
    # Kein Crash
    assert isinstance(recent, str)


def test_progress_read_recent_limit(tmp_path):
    """M-307b: n-Limit respektiert."""
    for i in range(15):
        progress.append(tmp_path, name=f"Task {i}", status="done")
    recent = progress.read_recent(tmp_path, n=5)
    assert "Task 14" in recent
    assert "Task 10" in recent
    assert "Task 9" not in recent

def test_loop_schreibt_progress(tmp_path):
    """M-307b-3 (N1): Loop schreibt PROGRESS.md bei mark_done."""
    from unittest.mock import patch

    from werkstatt.loop import run_pipeline_loop
    from werkstatt.state import RunState

    st = RunState(
        block_id="t", aufgabe="a", start_ts="",
        docs={}, agents={}, always={}, optional={},
        file_whitelist=[], api_key="fake", budget={},
        agent_docs={}, project_dir=tmp_path, project_name="p"
    )
    st.tasks = [{"id": "t1", "name": "Test-Task", "action": "write"}]
    st.tests = ["Test 1"]
    st.akzeptanzkriterien = ["Kriterium 1"]

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
    progress_path = tmp_path / "PROGRESS.md"
    assert progress_path.exists(), "PROGRESS.md muss angelegt werden"
    content = progress_path.read_text()
    assert "Test-Task" in content
    assert "Status:** done" in content
    # Phase-Ende-Block
    assert "Phase abgeschlossen" in content
