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
