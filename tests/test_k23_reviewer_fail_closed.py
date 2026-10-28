"""K23: Reviewer fail-closed bei Diff-Fehler oder Patch-ohne-Diff."""
from pathlib import Path
from unittest.mock import patch

from werkstatt.reviewer import _get_git_diff, run_reviewer
from werkstatt.state import RunState


def _mk_state(tmp_path: Path, patches: list | None = None) -> RunState:
    s = RunState.__new__(RunState)
    s.project_dir = tmp_path  # type: ignore[attr-defined]
    s.project_name = "test"  # type: ignore[attr-defined]
    s.api_key = "dummy"  # type: ignore[attr-defined]
    s.aktuelle_task = {}  # type: ignore[attr-defined]
    s.patches = patches or []  # type: ignore[attr-defined]
    return s


def test_git_diff_fail_closed_bei_fehler(tmp_path: Path):
    """K23a: git-Fehler -> RuntimeError, nicht ''."""
    with patch("werkstatt.reviewer.subprocess.run") as m:
        class R:
            returncode = 128
            stdout = ""
            stderr = "fatal: not a git repository"
        m.return_value = R()
        try:
            _get_git_diff(tmp_path)
            assert False, "RuntimeError erwartet"
        except RuntimeError:
            pass


def test_git_diff_fail_closed_bei_dubious(tmp_path: Path):
    """K23a: 'dubious' im stderr -> RuntimeError."""
    with patch("werkstatt.reviewer.subprocess.run") as m:
        class R:
            returncode = 0
            stdout = ""
            stderr = "Schwerwiegend: dubiose Besitzverhaeltnisse"
        m.return_value = R()
        try:
            _get_git_diff(tmp_path)
            assert False, "RuntimeError erwartet"
        except RuntimeError:
            pass


def test_run_reviewer_fail_closed_wenn_patches_aber_kein_diff(tmp_path: Path):
    """K23b: patches da, aber diff leer -> False (fail-closed)."""
    s = _mk_state(tmp_path, patches=[{"file": "x.py", "action": "create"}])
    with patch("werkstatt.reviewer._get_git_diff", return_value=""):
        with patch("werkstatt.reviewer.audit"):
            rc = run_reviewer(s)
    assert rc is False


def test_run_reviewer_fail_closed_wenn_diff_fehler(tmp_path: Path):
    """K23b: _get_git_diff wirft RuntimeError -> False."""
    s = _mk_state(tmp_path, patches=[{"file": "x.py"}])
    with patch("werkstatt.reviewer._get_git_diff",
               side_effect=RuntimeError("git fail")):
        with patch("werkstatt.reviewer.audit"):
            rc = run_reviewer(s)
    assert rc is False


def test_run_reviewer_kein_patch_kein_diff_ist_legitim(tmp_path: Path):
    """K23b: weder Patch noch Diff -> True (nichts zu reviewen)."""
    s = _mk_state(tmp_path, patches=[])
    with patch("werkstatt.reviewer._get_git_diff", return_value=""):
        with patch("werkstatt.reviewer.audit"):
            rc = run_reviewer(s)
    assert rc is True
