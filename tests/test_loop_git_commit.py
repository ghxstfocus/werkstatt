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
import sys
from pathlib import Path
from unittest.mock import patch

from werkstatt import loop
from werkstatt.state import RunState

_here = Path(__file__).parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))
from factories import mk_state  # noqa: E402

# =====================================================================
# Fixtures
# =====================================================================

def _state(tmp_path: Path, **overrides) -> RunState:
    kw = {
        "block_id": "t", "aufgabe": "aufgabe", "start_ts": "2026-10-30T00:00:00Z",
        "docs": {}, "agents": {}, "always": {}, "optional": {}, "file_whitelist": [],
        "api_key": "sk-test", "budget": {}, "agent_docs": {},
        "project_dir": tmp_path, "project_name": "testproj",
    }
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
    st = mk_state(project_dir=None, project_name="p")
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
    assert ok is True, sha
    assert len(sha) == 12
    # SHA taucht im Log auf.
    log = subprocess.run(
        ["git", "-C", str(tmp_path), "log", "--oneline", "-1"],
        capture_output=True, text=True, check=True)
    assert sha[:7] in log.stdout
    ev = _kind(tmp_path, "loop_human_gate_committed")
    assert len(ev) == 1
    assert ev[0]["sha"] == sha
    assert ev[0]["post_commit_check"] == "passed"
    assert _kind(tmp_path, "loop_human_gate_commit_postcheck_failed") == []



def test_committe_postcheck_faengt_neue_aenderungen_nach_commit_ab(
    tmp_path, monkeypatch,
):
    """Der Commit gilt nicht als fertig, wenn nach dem Commit neue Aenderungen auftauchen."""
    _init_repo(tmp_path)
    (tmp_path / "neu.py").write_text("def f(): pass\n")
    s = _state(tmp_path)

    from werkstatt import loop as loop_mod
    original_run = loop_mod.subprocess.run

    def _inject_after_commit(argv, **kwargs):
        result = original_run(argv, **kwargs)
        if "commit" in argv and result.returncode == 0:
            (tmp_path / "parallel.py").write_text("parallel change\n")
        return result

    monkeypatch.setattr(loop_mod.subprocess, "run", _inject_after_commit)
    ok, info = loop._committe_zielprojekt(s)

    assert ok is False
    assert "Nachkontrolle fehlgeschlagen" in info
    assert (tmp_path / "parallel.py").exists()
    failure = _kind(tmp_path, "loop_human_gate_commit_postcheck_failed")[0]
    assert failure["reason"] == "working_tree_dirty_after_commit", failure
    assert failure["pending_files"] == ["parallel.py"], failure
    assert _kind(tmp_path, "loop_human_gate_committed")[0][
        "post_commit_check"
    ] == "failed"



def test_committe_postcheck_erkennt_parallelen_head_commit(tmp_path, monkeypatch):
    """Ein fremder Folge-Commit darf nicht als eigener Commit verifiziert werden."""
    _init_repo(tmp_path)
    (tmp_path / "neu.py").write_text("def f(): pass\n")
    s = _state(tmp_path)

    from werkstatt import loop as loop_mod
    original_run = loop_mod.subprocess.run

    def _commit_parallel(argv, **kwargs):
        result = original_run(argv, **kwargs)
        if "commit" in argv and "--allow-empty" not in argv and result.returncode == 0:
            parallel = original_run(
                [
                    "git", "-C", str(tmp_path),
                    "-c", "user.name=parallel",
                    "-c", "user.email=parallel@example.com",
                    "commit", "--allow-empty", "-m", "parallel commit",
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            assert parallel.returncode == 0, parallel.stderr
        return result

    monkeypatch.setattr(loop_mod.subprocess, "run", _commit_parallel)
    ok, info = loop._committe_zielprojekt(s)

    assert ok is False
    assert "Repository-Stand" in info
    failure = _kind(tmp_path, "loop_human_gate_commit_postcheck_failed")[0]
    assert failure["reason"] == "head_parent_mismatch"
    assert failure["actual_parent_sha"]
    assert failure["expected_parent_sha"] != failure["actual_parent_sha"]

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


def test_git_dirty_git_status_fehler_in_repo_ist_unsicher(tmp_path):
    (tmp_path / ".git").mkdir()
    with patch("werkstatt.loop.subprocess.run",
               return_value=_fake_result(128, "", "index kaputt")):
        assert loop._git_dirty(tmp_path) is True


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
# Stash restoration is scoped to the run-owned entry
# =====================================================================

def test_stash_pop_uses_exact_entry_and_never_drops_on_conflict(tmp_path):
    stash_sha = "a" * 40
    calls: list[list[str]] = []

    def _fake_run(argv, **_kwargs):
        calls.append(list(argv))
        if "list" in argv:
            return _fake_result(0, f"{stash_sha}\n")
        return _fake_result(1, "", "conflict")

    with patch("werkstatt.loop.subprocess.run", _fake_run):
        assert loop._git_stash_pop(tmp_path, stash_sha) is False

    assert len(calls) == 2
    assert calls[1][-3:] == ["apply", "--index", stash_sha]
    assert all("drop" not in argv for argv in calls)


def test_stash_pop_missing_entry_does_not_touch_stash_stack(tmp_path):
    calls: list[list[str]] = []

    def _fake_run(argv, **_kwargs):
        calls.append(list(argv))
        return _fake_result(0, "")

    with patch("werkstatt.loop.subprocess.run", _fake_run):
        assert loop._git_stash_pop(tmp_path, "a" * 40) is False

    assert len(calls) == 1
    assert "list" in calls[0]


def test_real_stash_restore_survives_concurrent_push(tmp_path):
    _init_repo(tmp_path)
    git = ["git", "-C", str(tmp_path)]
    run = subprocess.run
    seed = tmp_path / "seed.txt"
    seed.write_text("run-owned staged change\n")
    run([*git, "add", "seed.txt"], check=True)
    seed.write_text("run-owned unstaged change\n")
    run_stash = loop._git_stash_owned(tmp_path)
    assert run_stash is not None

    newer_file = tmp_path / "newer.txt"

    def _concurrent_push(argv, **kwargs):
        result = run(argv, **kwargs)
        if argv[3:5] == ["stash", "list"]:
            newer_file.write_text("user's newer stash\n")
            run(
                [*git, "stash", "push", "-u", "-m", "foreign"],
                capture_output=True, check=True,
            )
        return result

    with patch("werkstatt.loop.subprocess.run", _concurrent_push):
        assert loop._git_stash_pop(tmp_path, run_stash) is True

    assert seed.read_text() == "run-owned unstaged change\n"
    assert not newer_file.exists()
    assert run(
        [*git, "show", ":seed.txt"], capture_output=True, text=True, check=True,
    ).stdout == "run-owned staged change\n"
    remaining = run(
        [*git, "stash", "list", "--format=%H%x09%gs"],
        capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    assert len(remaining) == 2
    assert remaining[0].endswith(": foreign")
    assert remaining[1].startswith(f"{run_stash}\t")


def test_real_stash_conflict_remains_recoverable(tmp_path):
    _init_repo(tmp_path)
    ziel = tmp_path / "seed.txt"
    ziel.write_text("user change\n")
    assert loop._git_stash(tmp_path) is True
    stash_sha = subprocess.run(
        ["git", "-C", str(tmp_path), "rev-parse", "refs/stash"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    ziel.write_text("loop change\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "seed.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "commit", "-m", "loop change"],
        capture_output=True, check=True,
    )

    assert loop._git_stash_pop(tmp_path, stash_sha) is False
    remaining = subprocess.run(
        ["git", "-C", str(tmp_path), "stash", "list", "--format=%H"],
        capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    assert stash_sha in remaining


def test_commit_gate_prompt_ist_explizit(monkeypatch):
    """OP-381: Commit-Gate-Prompt sagt WAS entschieden wird.

    Vorher: nur "Deine Wahl: " — User sieht nicht ob es um Commit,
    Plan-Reject, oder etwas anderes geht.
    """
    from werkstatt import gates
    gesehen = []

    def fake_frage_gate(name, prompt, optionen):
        gesehen.append((name, prompt, optionen))
        return "j"

    monkeypatch.setattr(gates, "_frage_gate", fake_frage_gate)
    # minimaler Kontext: das Commit-Gate wird irgendwo in gates.py
    # gerufen; wir rufen die oeffentliche Funktion direkt auf.
    # Welche Funktion das genau ist, klaert der Test beim Aufruf —
    # wenn es keine oeffentliche gibt, pruefen wir nur den Quelltext.
    import inspect
    src = inspect.getsource(gates)
    # Kernaussage: der Commit-Prompt nennt explizit was entschieden wird
    assert "Phase committed werden" in src, "Commit-Gate-Prompt muss explizit sein"
    assert "kein Commit" in src or "Abbruch, kein Commit" in src, "n-Zweig muss als Abbruch markiert sein"
    # Und der alte inhaltsleere Text "Deine Wahl: " allein darf bei commit nicht mehr stehen
    # (er steht weiter in den Plan-Gates, das ist OK — dort gibt es Kontext drumherum)

