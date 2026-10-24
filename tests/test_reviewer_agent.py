"""Tests fuer werkstatt/reviewer.py (Phase 8)."""
from __future__ import annotations

from unittest.mock import patch

from werkstatt.reviewer import run_reviewer
from werkstatt.state import RunState


def _state(tmp_path):
    return RunState(
        block_id="t", aufgabe="Baue Feature X", start_ts="",
        docs={}, agents={}, always={}, optional={},
        file_whitelist=[], api_key="fake", budget={},
        agent_docs={}, project_dir=tmp_path, project_name="p"
    )


def test_reviewer_approves_clean_diff(tmp_path):
    st = _state(tmp_path)
    fake_json = '{"approved": true, "bugs": [], "summary": "LGTM"}'

    class FakeReply:
        ok = True
        content = fake_json

    with patch("werkstatt.reviewer._get_git_diff", return_value="diff --git a/x b/x"), \
         patch("werkstatt.reviewer.ask_llm", return_value=FakeReply()):
        assert run_reviewer(st) is True


def test_reviewer_rejects_buggy_diff(tmp_path):
    st = _state(tmp_path)
    fake_json = '{"approved": false, "bugs": [{"file": "a.py", "line": 1, "description": "Bug", "severity": "high"}], "summary": "Fix needed"}'

    class FakeReply:
        ok = True
        content = fake_json

    with patch("werkstatt.reviewer._get_git_diff", return_value="diff --git a/x b/x"), \
         patch("werkstatt.reviewer.ask_llm", return_value=FakeReply()):
        assert run_reviewer(st) is False


def test_reviewer_ohne_diff(tmp_path):
    st = _state(tmp_path)
    with patch("werkstatt.reviewer._get_git_diff", return_value=""):
        assert run_reviewer(st) is True


def test_reviewer_sieht_untracked_dateien(tmp_path):
    """M-314: _get_git_diff umfasst untracked-Dateien."""
    import subprocess as _sp

    from werkstatt.reviewer import _get_git_diff

    # Repo initialisieren
    _sp.run(["git", "init"], cwd=str(tmp_path), capture_output=True, check=False)
    _sp.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
             "commit", "--allow-empty", "-m", "init"],
            cwd=str(tmp_path), capture_output=True, check=False)

    # Neue (untracked) Datei
    (tmp_path / "new_file.py").write_text("def foo():\n    return 1\n")

    diff = _get_git_diff(tmp_path)
    assert "new_file.py" in diff
    assert "NEUE DATEI" in diff
    assert "def foo" in diff
