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


def test_progress_append_schreibt_plattformunabhaengig_lf(tmp_path):
    progress_path = tmp_path / "PROGRESS.md"
    progress_path.write_bytes(b"# Fortschritt\r\n")

    assert progress.append(tmp_path, name="LF check", status="done") is True

    written = progress_path.read_bytes()
    assert b"\r" not in written
    assert written.endswith(b"- **Status:** done\n")


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

def test_progress_recent_context_is_bounded_and_keeps_newest_entries():
    content = "\n\n".join(
        f"## 2026-11-12T00:00:00 -- Task {i}\n- **Status:** done\n"
        + ("x" * 2400)
        for i in range(12)
    )

    recent = progress.recent_from_text(content, n=10, max_chars=5000)

    assert len(recent) <= 5000
    assert "Task 11" in recent
    assert "Task 10" in recent
    assert "Task 0" not in recent
    assert "gekuerzt" in recent


# =====================================================================
# GOLD 2026-10-30: progress.append schreibt Exception ins Audit
# =====================================================================

def test_progress_audit_enthaelt_exc_bei_oserror(tmp_path):
    """OSError -> audit-Event mit exc_type + exc_str.

    Regression fuer den 4-Tage-Rechte-Bug (2026-10-26 bis 2026-10-30):
    der alte Event hatte nur {file}, die Ursache war unsichtbar.
    """
    import json

    from werkstatt import progress

    # Schreibpfad unmoeglich machen (Verzeichnis statt Datei).
    (tmp_path / "PROGRESS.md").mkdir()

    ok = progress.append(
        tmp_path,
        name="t1",
        status="done",
        dateien=["a.py"],
    )
    assert ok is False

    logs = tmp_path / "audit-logs"
    assert logs.is_dir(), "kein audit-logs-Verzeichnis"
    events = []
    for f in logs.glob("agent-pipeline-*.jsonl"):
        for line in f.read_text().splitlines():
            if line.strip():
                events.append(json.loads(line))
    fehler = [e for e in events if e.get("kind") == "progress_write_failed"]
    assert len(fehler) == 1
    ev = fehler[0]
    assert "file" in ev
    assert ev["exc_type"] in ("IsADirectoryError", "NotADirectoryError",
                              "PermissionError", "OSError")
    assert ev["exc_str"], "exc_str darf nicht leer sein"
