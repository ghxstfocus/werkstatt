"""Spec: Git + M-487 — Human-Gate committet selbst.

_committe_zielprojekt wird mit echtem Git-Repo in tmp_path getestet
(deterministisch, kein subprocess-Mock).

_git_*-Helfer und _get_git_diff_for_hook: subprocess.run gemockt —
die Logik ist returncode-basiert bzw. fail-safe.

(Tests fuer _human_gate selbst -> test_loop_human_gate.py)
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from werkstatt import loop
from werkstatt.state import RunState


# =====================================================================
# Fixtures
# =====================================================================

def _state(tmp_path: Path, **overrides) -> RunState:
    kw = dict(
        block_id="t", aufgabe="aufgabe", start_ts="2026-10-30T00:00:00Z",
        docs={}, agents={}, always={}, optional={}, file_whitelist=[],
        api_key="sk-test", budget={}, agent_docs={},
        project_dir=tmp_path, project_name="testproj",
    )
    kw.update(overrides)
    return RunState(**kw)


def _audit_events(tmp_path: Path) -> list[dict]:
    logs = tmp_path / "audit-logs"
    if not logs.is_dir():
        return []
    out: list[dict] = []
    for f in sorted(logs.glob("agent-pipeline-*.jsonl")):
        for line in f.read_text().splitlines():
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _kind(tmp_path: Path, kind: str) -> list[dict]:
    return [e for e in _audit_events(tmp_path) if e.get("kind") == kind]


def _init_repo(tmp_path: Path) -> None:
    """Legt ein echtes Git-Repo in tmp_path an, mit einem Initial-Commit."""
    env = {
        "GIT_AUTHOR_NAME": "init",
        "GIT_AUTHOR_EMAIL": "init@test",
        "GIT_COMMITTER_NAME": "init",
        "GIT_COMMITTER_EMAIL": "init@test",
    }
    import os
    e = {**os.environ, **env}
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True, env=e)
    subprocess.run(["git", "config", "user.name", "init"],
                   cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "init@test"],
                   cwd=tmp_path, check=True)
    (tmp_path / "seed.txt").write_text("seed\n")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True, env=e)
    subprocess.run(["git", "commit", "-qm", "init"],
                   cwd=tmp_path, check=True, env=e)


# =====================================================================
# A. _committe_zielprojekt — echtes Repo
# =====================================================================

def test_committe_kein_project_dir():
    """project_dir=None -> (False, "kein project_dir")."""
    from types import SimpleNamespace
    st = SimpleNamespace(project_dir=None, project_name="p")
    ok, info = loop._committe_zielprojekt(st)
    assert ok is False
    assert "kein project_dir" in info


def test_committe_working_tree_clean(tmp_path):
    """Repo ohne Aenderung -> (True, "") + skip-Audit."""
    _init_repo(tmp_path)
    s = _state(tmp_path)
    ok, info = loop._committe_zielprojekt(s)
    assert ok is True
    assert info == ""
    ev = _kind(tmp_path, "loop_human_gate_commit_skip")
    assert len(ev) == 1
    assert ev[0]["reason"] == "working_tree_clean"


def test_committe_erfolg(tmp_path):
    """Datei geaendert -> Commit angelegt, sha zurueck, Audit."""
    _init_repo(tmp_path)
    (tmp_path / "neu.py").write_text("def f(): pass\n")
    s = _state(tmp_path)
    ok, sha = loop._committe_zielprojekt(s)
    assert ok is True
    assert len(sha) == 12
    # SHA taucht im Log auf.
    log = subprocess.run(
        ["git", "-C", str(tmp_path), "log", "--oneline", "-1"],
        capture_output=True, text=True, check=True)
    assert sha[:7] in log.stdout
    ev = _kind(tmp_path, "loop_human_gate_committed")
    assert len(ev) == 1
    assert ev[0]["sha"] == sha


def test_committe_autor_aus_state(tmp_path):
    """git_author_name/email aus state werden im Commit verwendet."""
    _init_repo(tmp_path)
    (tmp_path / "neu.py").write_text("x\n")
    s = _state(tmp_path, git_author_name="Alice",
               git_author_email="alice@example.com")
    ok, _ = loop._committe_zielprojekt(s)
    assert ok is True
    log = subprocess.run(
        ["git", "-C", str(tmp_path), "log", "-1", "--format=%an <%ae>"],
        capture_output=True, text=True, check=True)
    assert "Alice" in log.stdout
    assert "alice@example.com" in log.stdout


def test_committe_git_add_fehler(tmp_path, monkeypatch):
    """git add rc!=0 -> (False, ...)."""
    _init_repo(tmp_path)
    (tmp_path / "x.py").write_text("x\n")
    s = _state(tmp_path)

    from werkstatt import loop as loop_mod
    original_run = loop_mod.subprocess.run

    class _R:
        def __init__(self, rc, stdout="", stderr=""):
            self.returncode = rc
            self.stdout = stdout
            self.stderr = stderr

    def _fake_run(argv, **kw):
        if "add" in argv:
            return _R(1, "", "add kaputt")
        return original_run(argv, **kw)

    monkeypatch.setattr(loop_mod.subprocess, "run", _fake_run)
    ok, info = loop._committe_zielprojekt(s)
    assert ok is False
    assert "git add" in info


def test_committe_git_commit_fehler(tmp_path, monkeypatch):
    """git commit rc!=0 -> (False, ...) + fehler-Audit."""
    _init_repo(tmp_path)
    (tmp_path / "x.py").write_text("x\n")
    s = _state(tmp_path)

    from werkstatt import loop as loop_mod
    original_run = loop_mod.subprocess.run

    class _R:
        def __init__(self, rc, stdout="", stderr=""):
            self.returncode = rc
            self.stdout = stdout
            self.stderr = stderr

    def _fake_run(argv, **kw):
        if "commit" in argv:
            return _R(1, "", "commit kaputt")
        return original_run(argv, **kw)

    monkeypatch.setattr(loop_mod.subprocess, "run", _fake_run)
    ok, info = loop._committe_zielprojekt(s)
    assert ok is False
    assert "git commit" in info
    ev = _kind(tmp_path, "loop_human_gate_commit_fehler")
    assert len(ev) == 1
    assert ev[0]["rc"] == 1


# =====================================================================
# B. _git_*-Helfer
# =====================================================================

def _fake_result(rc: int = 0, stdout: str = "", stderr: str = ""):
    r = type("R", (), {
        "returncode": rc, "stdout": stdout, "stderr": stderr,
    })()
    return r


def test_git_dirty_ja(tmp_path):
    with patch("werkstatt.loop.subprocess.run",
               return_value=_fake_result(0, "M  a.py\n")):
        assert loop._git_dirty(tmp_path) is True


def test_git_dirty_nein(tmp_path):
    with patch("werkstatt.loop.subprocess.run",
               return_value=_fake_result(0, "")):
        assert loop._git_dirty(tmp_path) is False


def test_git_dirty_exception(tmp_path):
    with patch("werkstatt.loop.subprocess.run",
               side_effect=RuntimeError("git weg")):
        assert loop._git_dirty(tmp_path) is False


def test_git_head(tmp_path):
    with patch("werkstatt.loop.subprocess.run",
               return_value=_fake_result(0, "abc123\n")):
        assert loop._git_head(tmp_path) == "abc123"


def test_git_stash_erfolg(tmp_path):
    with patch("werkstatt.loop.subprocess.run",
               return_value=_fake_result(0)):
        assert loop._git_stash(tmp_path) is True


def test_git_stash_fehler(tmp_path):
    with patch("werkstatt.loop.subprocess.run",
               return_value=_fake_result(1)):
        assert loop._git_stash(tmp_path) is False


def test_git_reset_ref(tmp_path):
    """_git_reset uebergibt ref als Argv-Argument."""
    captured: list = []

    def _fake_run(argv, **kw):
        captured.append(list(argv))
        return _fake_result(0)

    with patch("werkstatt.loop.subprocess.run", _fake_run):
        assert loop._git_reset(tmp_path, "abc123") is True
    argv = captured[0]
    assert argv[0] == "git"
    assert "reset" in argv
    assert "--hard" in argv
    assert "abc123" in argv


# =====================================================================
# C. _get_git_diff_for_hook
# =====================================================================

def test_git_diff_for_hook():
    with patch("werkstatt.loop.subprocess.run",
               return_value=_fake_result(0, "+ neue zeile\n")):
        out = loop._get_git_diff_for_hook()
    assert "neue zeile" in out


def test_git_diff_for_hook_exception():
    with patch("werkstatt.loop.subprocess.run",
               side_effect=RuntimeError("git weg")):
        assert loop._get_git_diff_for_hook() == ""



# =====================================================================
# GOLD 2026-10-30: _git_stash_pop mit drop-Fallback
# =====================================================================

def test_stash_pop_drop_fallback_bei_fehler(tmp_path):
    """_git_stash_pop droppt den Stash, wenn pop fehlschlaegt.

    Regression: Live 2026-10-30 — 8 offene Stashes nach 8 RERUNs.
    """
    from unittest.mock import patch

    calls: list = []
    def _fake_run(argv, **kw):
        calls.append(list(argv))
        rc = 0 if "pop" in argv else 1  # pop schlaegt fehl
        # Eigentlich: erster Call (pop) rc=1, zweiter (drop) rc=0
        if "pop" in argv:
            return type("R", (), {"returncode": 1, "stdout": "",
                                  "stderr": "conflict"})()
        return type("R", (), {"returncode": 0, "stdout": "",
                              "stderr": ""})()

    with patch("werkstatt.loop.subprocess.run", _fake_run):
        ok = loop._git_stash_pop(tmp_path)
    assert ok is False
    # Zwei Calls: pop, drop
    assert len(calls) == 2
    assert "pop" in calls[0]
    assert "drop" in calls[1]
    assert "stash@{0}" in calls[1]


def test_stash_pop_ohne_drop_bei_erfolg(tmp_path):
    """_git_stash_pop droppt NICHT, wenn pop klappt."""
    from unittest.mock import patch
    calls: list = []
    def _fake_run(argv, **kw):
        calls.append(list(argv))
        return type("R", (), {"returncode": 0, "stdout": "",
                              "stderr": ""})()
    with patch("werkstatt.loop.subprocess.run", _fake_run):
        ok = loop._git_stash_pop(tmp_path)
    assert ok is True
    assert len(calls) == 1
    assert "pop" in calls[0]
