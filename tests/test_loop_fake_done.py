"""Spec: Fake-Done ist fail-closed (Fix 2026-10-31).

Regression: 669a7de behauptet "docs/STATUS.md entfernt",
aendert aber nur PROGRESS.md. Der Loop hat das nicht erkannt,
weil
  - reviewer_kein_diff_kein_patch -> True (jetzt: fail-closed
    bei update-Task)
  - _committe_zielprojekt -> committet blind (jetzt: task_files
    gegen git diff --name-only pruefen)

Diese Specs sind Verhaltenstests, keine Bugfix-Historie.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, "/opt/werkstatt")

import pytest


def _mk_state(tmp_path: Path, tasks: list, aufgabe: str = ""):
    return SimpleNamespace(
        project_dir=tmp_path,
        project_name="test",
        aufgabe=aufgabe,
        tasks=tasks,
        git_author_name="tester",
        git_author_email="tester@example.com",
    )


def _git(tmp_path: Path, *args: str) -> None:
    import subprocess
    subprocess.run(["git", "-C", str(tmp_path), *args],
                   check=True, capture_output=True)


def _init_repo(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@t")
    _git(tmp_path, "config", "user.name", "t")
    # Initial-Commit damit HEAD existiert
    (tmp_path / "README.md").write_text("init\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "init")


class TestCommitTaskFilesGuard:
    """Fix 3: _committe_zielprojekt prueft task_files im Diff."""

    def test_task_done_aber_datei_nicht_im_diff_abort(
        self, tmp_path: Path, monkeypatch,
    ) -> None:
        """Fake-Done: Task done + task_files, aber Datei unveraendert."""
        _init_repo(tmp_path)
        # Nur PROGRESS.md geaendert (das passiert beim echten 669a7de)
        (tmp_path / "PROGRESS.md").write_text("done\n")
        from werkstatt import loop as _loop
        state = _mk_state(tmp_path, [{
            "id": "t1", "status": "done",
            "task_files": ["docs/STATUS.md"],
        }])
        ok, info = _loop._committe_zielprojekt(state)
        assert ok is False
        assert "docs/STATUS.md" in info
        assert "nicht im git-Diff" in info

    def test_task_done_datei_im_diff_commit(
        self, tmp_path: Path, monkeypatch,
    ) -> None:
        """Echter Done: task_files im Diff -> Commit."""
        _init_repo(tmp_path)
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "STATUS.md").write_text("# Status\n")
        from werkstatt import loop as _loop
        state = _mk_state(tmp_path, [{
            "id": "t1", "status": "done",
            "task_files": ["docs/STATUS.md"],
        }])
        ok, info = _loop._committe_zielprojekt(state)
        assert ok is True
        assert info != ""

    def test_task_read_only_kein_task_files_commit_erlaubt(
        self, tmp_path: Path,
    ) -> None:
        """Read-only-Task ohne task_files: Commit ohne Datei-Erwartung."""
        _init_repo(tmp_path)
        (tmp_path / "PROGRESS.md").write_text("done\n")
        from werkstatt import loop as _loop
        state = _mk_state(tmp_path, [{
            "id": "t1", "status": "done",
            "task_files": [],
        }])
        ok, info = _loop._committe_zielprojekt(state)
        assert ok is True


class TestReviewerUpdateTaskFailClosed:
    """Fix 2: Reviewer fail-closed bei update-Task ohne Diff."""

    def _audit_collector(self, tmp_path: Path):
        """Liefert (audit_fn, gesammelte_kinds)."""
        import werkstatt.reviewer as _rev
        seen: list[str] = []
        def _fake_audit(kind, payload, pd, pn):
            seen.append(kind)
        return _rev, seen

    def test_update_task_ohne_diff_fail_closed(
        self, tmp_path: Path, monkeypatch,
    ) -> None:
        import werkstatt.reviewer as _rev
        seen: list[str] = []
        monkeypatch.setattr(_rev, "audit",
                            lambda k, p, pd, pn: seen.append(k))
        monkeypatch.setattr(_rev, "_get_git_diff",
                            lambda pd, task_files=None: "")
        state = SimpleNamespace(
            project_dir=tmp_path,
            project_name="t",
            api_key="fake",
            patches=[],
            aktuelle_task={
                "id": "t1", "action": "update",
                "task_files": ["docs/STATUS.md"],
            },
            aufgabe="x", baseline_gruen=True,
            reviewer_bugs=[], reviewer_bugs_history=[],
        )
        result = _rev.run_reviewer(state)
        assert result is False
        assert "reviewer_kein_diff_update_task" in seen

    def test_read_task_ohne_diff_legitim(
        self, tmp_path: Path, monkeypatch,
    ) -> None:
        import werkstatt.reviewer as _rev
        seen: list[str] = []
        monkeypatch.setattr(_rev, "audit",
                            lambda k, p, pd, pn: seen.append(k))
        monkeypatch.setattr(_rev, "_get_git_diff",
                            lambda pd, task_files=None: "")
        state = SimpleNamespace(
            project_dir=tmp_path,
            project_name="t",
            api_key="fake",
            patches=[],
            aktuelle_task={
                "id": "t1", "action": "read",
                "task_files": [],
            },
            aufgabe="x", baseline_gruen=True,
            reviewer_bugs=[], reviewer_bugs_history=[],
        )
        result = _rev.run_reviewer(state)
        assert result is True
        assert "reviewer_kein_diff_kein_patch" in seen

    def test_update_task_ohne_task_files_legitim(
        self, tmp_path: Path, monkeypatch,
    ) -> None:
        """update ohne task_files: fail-open (kein Fake-Done moeglich)."""
        import werkstatt.reviewer as _rev
        seen: list[str] = []
        monkeypatch.setattr(_rev, "audit",
                            lambda k, p, pd, pn: seen.append(k))
        monkeypatch.setattr(_rev, "_get_git_diff",
                            lambda pd, task_files=None: "")
        state = SimpleNamespace(
            project_dir=tmp_path,
            project_name="t",
            api_key="fake",
            patches=[],
            aktuelle_task={"id": "t1", "action": "update"},
            aufgabe="x", baseline_gruen=True,
            reviewer_bugs=[], reviewer_bugs_history=[],
        )
        result = _rev.run_reviewer(state)
        assert result is True
