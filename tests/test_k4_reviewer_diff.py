"""K4: Reviewer diffed nur task_files der aktuellen Task."""
from pathlib import Path
from unittest.mock import patch

from werkstatt import reviewer as _rv


def test_k4_git_diff_mit_task_files() -> None:
    """Mit task_files: Pathspec enthaelt nur die Task-Dateien."""
    calls = []

    def _fake_run(cmd, *args, **kwargs):
        calls.append(cmd)
        class _R:
            stdout = "diff --git a/x b/x\n"
            returncode = 0
        return _R()

    with patch("werkstatt.reviewer.subprocess.run", side_effect=_fake_run):
        _rv._get_git_diff("/tmp", task_files=["foo.py", "bar.py"])

    diff_calls = [c for c in calls if "diff" in c and "HEAD" in c]
    assert diff_calls, "kein git-diff-Aufruf"
    cmd = diff_calls[0]
    assert "foo.py" in cmd and "bar.py" in cmd, f"task_files fehlen: {cmd}"
    assert "." not in cmd[cmd.index("--") + 1:cmd.index(":!PROGRESS.md")], \
        f"'.' darf nicht im Pathspec sein: {cmd}"


def test_k4_ohne_task_files_nutzt_dot() -> None:
    """Ohne task_files: altes Verhalten ('.')."""
    calls = []

    def _fake_run(cmd, *args, **kwargs):
        calls.append(cmd)
        class _R:
            stdout = "x\n"
            returncode = 0
        return _R()

    with patch("werkstatt.reviewer.subprocess.run", side_effect=_fake_run):
        _rv._get_git_diff("/tmp", task_files=None)

    diff_calls = [c for c in calls if "diff" in c and "HEAD" in c]
    assert diff_calls
    cmd = diff_calls[0]
    assert "." in cmd[cmd.index("--"):cmd.index(":!PROGRESS.md")]


def test_k4_run_reviewer_reicht_task_files_durch() -> None:
    """run_reviewer mit aktuelle_task.task_files -> _get_git_diff bekommt sie."""
    class _State:
        def __init__(self):
            self.project_dir = Path("/tmp")
            self.project_name = "k4"
            self.api_key = "x"
            self.aufgabe = "x"
            self.baseline_gruen = True
            self.aktuelle_task = {"name": "t", "description": "d",
                                  "task_files": ["only_this.py"]}

    captured = {}
    def _fake_diff(pd, task_files=None):
        captured["task_files"] = task_files
        return ""

    with patch.object(_rv, "_get_git_diff", side_effect=_fake_diff):
        _rv.run_reviewer(_State())

    assert captured["task_files"] == ["only_this.py"], captured


def test_k4b_untracked_nur_task_files(tmp_path) -> None:
    """K4b: untracked-Dateien werden nach task_files gefiltert."""
    (tmp_path / "a.py").write_text("x")
    (tmp_path / "b.py").write_text("x")

    calls = []

    def _fake_run(cmd, *args, **kwargs):
        calls.append(cmd)
        class _R:
            if "ls-files" in cmd:
                stdout = "a.py\nb.py\n"
            else:
                stdout = "diff --git a/a.py b/a.py\n"
            returncode = 0
        return _R()

    from unittest.mock import patch
    with patch("werkstatt.reviewer.subprocess.run", side_effect=_fake_run):
        diff = _rv._get_git_diff(str(tmp_path), task_files=["a.py"])

    assert "a.py" in diff
    assert "b.py" not in diff, f"b.py darf nicht im Diff sein: {diff}"


def test_k4b_ohne_task_files_alle_untracked(tmp_path) -> None:
    """Ohne task_files: altes Verhalten (alle untracked)."""
    (tmp_path / "a.py").write_text("x")
    (tmp_path / "b.py").write_text("x")

    calls = []

    def _fake_run(cmd, *args, **kwargs):
        calls.append(cmd)
        class _R:
            if "ls-files" in cmd:
                stdout = "a.py\nb.py\n"
            else:
                stdout = ""
            returncode = 0
        return _R()

    from unittest.mock import patch
    with patch("werkstatt.reviewer.subprocess.run", side_effect=_fake_run):
        diff = _rv._get_git_diff(str(tmp_path), task_files=None)

    assert "a.py" in diff
    assert "b.py" in diff
