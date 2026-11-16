"""K4: Reviewer diffed nur task_files der aktuellen Task."""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from werkstatt import reviewer as _rv

_here = Path(__file__).parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))
from factories import mk_state  # noqa: E402


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
            stdout = "" if "ls-files" in cmd else "x\n"
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
    state = mk_state(
        project_dir=Path("/tmp"),
        project_name="k4",
        api_key="x",
        aufgabe="x",
        baseline_gruen=True,
        aktuelle_task={"name": "t", "description": "d",
                       "task_files": ["only_this.py"]},
    )

    captured = {}
    def _fake_diff(pd, task_files=None):
        captured["task_files"] = task_files
        return ""

    with patch.object(_rv, "_get_git_diff", side_effect=_fake_diff):
        _rv.run_reviewer(state)

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
                stdout = "a.py\0b.py\0"
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
                stdout = "a.py\0b.py\0"
            else:
                stdout = ""
            returncode = 0
        return _R()

    from unittest.mock import patch
    with patch("werkstatt.reviewer.subprocess.run", side_effect=_fake_run):
        diff = _rv._get_git_diff(str(tmp_path), task_files=None)

    assert "a.py" in diff
    assert "b.py" in diff


def test_reviewer_diff_uebergrosse_tracked_diffs_blockieren(tmp_path) -> None:
    fake = type("R", (), {
        "stdout": "x" * (_rv.REVIEWER_DIFF_MAX_CHARS + 1),
        "stderr": "",
        "returncode": 0,
    })()
    with patch("werkstatt.reviewer.subprocess.run", return_value=fake), \
            pytest.raises(RuntimeError, match="Vollstaendigkeitslimit"):
        _rv._get_git_diff(tmp_path)


def test_reviewer_diff_nimmt_versteckte_untracked_dateien_auf(tmp_path) -> None:
    import subprocess

    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=False)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "--allow-empty", "-m", "init"],
        cwd=tmp_path, capture_output=True, check=False,
    )
    (tmp_path / ".runtime-policy").write_text("deny unsafe action\n")

    diff = _rv._get_git_diff(tmp_path)

    assert "+++ b/.runtime-policy" in diff
    assert "+deny unsafe action" in diff


def test_reviewer_diff_ls_files_fehler_blockiert(tmp_path) -> None:
    results = [
        type("R", (), {"stdout": "", "stderr": "", "returncode": 0})(),
        type("R", (), {
            "stdout": "", "stderr": "fatal: index unavailable", "returncode": 128,
        })(),
    ]
    with patch("werkstatt.reviewer.subprocess.run", side_effect=results), \
            pytest.raises(RuntimeError, match="git ls-files fehlgeschlagen"):
        _rv._get_git_diff(tmp_path)


def test_reviewer_diff_nutzt_gesamten_untracked_inhalt_ohne_20k_kappung(
    tmp_path,
) -> None:
    import subprocess

    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, check=False)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "--allow-empty", "-m", "init"],
        cwd=tmp_path, capture_output=True, check=False,
    )
    payload = "z" * 25_000
    (tmp_path / "large_new.py").write_text(payload)

    diff = _rv._get_git_diff(tmp_path)

    assert len(diff) > 20_000
    assert f"+{payload}" in diff
