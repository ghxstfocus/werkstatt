"""Doku-Drift-Pruefung fuer Commit-Historie und Working Tree."""
from __future__ import annotations

from pathlib import Path

import pytest

from tools import doku_check


def test_ist_verdaechtig_erkennt_code_ohne_doku() -> None:
    assert doku_check.ist_verdaechtig(
        "fix(web): validate gate answers",
        ["werkstatt/web/app.py", "tests/test_web.py"],
    )


def test_ist_verdaechtig_akzeptiert_doku_aenderung() -> None:
    assert not doku_check.ist_verdaechtig(
        "fix(web): validate gate answers",
        ["werkstatt/web/app.py", "PROGRESS.md"],
    )


@pytest.mark.parametrize("subject", [
    "docs(status): describe gate behavior",
    "test(web): cover gate response",
    "ci(test): update runner",
    "fix(web): narrow a documented exception [skip-doku]",
])
def test_ist_verdaechtig_beachtet_subject_ausnahmen(
    subject: str,
) -> None:
    assert not doku_check.ist_verdaechtig(
        subject,
        ["werkstatt/web/app.py"],
    )


def test_ist_verdaechtig_erkennt_roadmap_als_doku() -> None:
    assert not doku_check.ist_verdaechtig(
        "feat(loop): rank ready operations",
        ["werkstatt/selector.py", "ROADMAP.md"],
    )


def _fake_worktree(
    monkeypatch: pytest.MonkeyPatch,
    diff: str,
    untracked: str = "",
) -> None:
    def fake_git(*args: str, cwd: Path | None = None) -> str:
        if args[:3] == ("diff", "--name-status", "HEAD"):
            return diff
        if args[:1] == ("ls-files",):
            return untracked
        raise AssertionError(f"unerwarteter git-Aufruf: {args}")

    monkeypatch.setattr(doku_check, "_git", fake_git)


def test_worktree_blockt_code_ohne_doku(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_worktree(monkeypatch, "M\twerkstatt/web/app.py\n")

    result = doku_check.pruefe_worktree(Path("."))

    assert result is not None
    assert result["sha"] == "WORKTREE"
    assert result["code_files"] == ["werkstatt/web/app.py"]


def test_worktree_erkennt_untracked_code(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_worktree(monkeypatch, "", "tools/new_check.py\n")

    result = doku_check.pruefe_worktree(Path("."))

    assert result is not None
    assert result["code_files"] == ["tools/new_check.py"]


def test_worktree_akzeptiert_code_mit_neuer_doku(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_worktree(
        monkeypatch,
        "M\twerkstatt/web/app.py\nA\tPROGRESS.md\n",
    )

    assert doku_check.pruefe_worktree(Path(".")) is None


def test_worktree_geloeschte_doku_zaehlt_nicht_als_update(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_worktree(
        monkeypatch,
        "M\twerkstatt/web/app.py\nD\tPROGRESS.md\n",
    )

    assert doku_check.pruefe_worktree(Path(".")) is not None


def test_main_strict_blockiert_worktree_drift(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(doku_check, "pruefe_commits", lambda **_kwargs: [])
    monkeypatch.setattr(
        doku_check,
        "pruefe_worktree",
        lambda: {
            "sha": "WORKTREE",
            "subject": "uncommitted code changes",
            "code_files": ["werkstatt/web/app.py"],
        },
    )

    assert doku_check.main(["--strict", "--worktree"]) == 1
    assert "Working Tree" in capsys.readouterr().out


def test_worktree_only_ueberspringt_commit_historie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _history_must_not_run(**_kwargs: object) -> list[dict]:
        raise AssertionError("Historie geprueft")

    monkeypatch.setattr(
        doku_check, "pruefe_commits", _history_must_not_run,
    )
    monkeypatch.setattr(doku_check, "pruefe_worktree", lambda: None)

    assert doku_check.main(["--strict", "--worktree-only"]) == 0


def test_pruefe_commits_akzeptiert_explizite_progress_hash_referenz(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sha = "1234567890abcdef" * 2 + "12345678"
    (tmp_path / "PROGRESS.md").write_text(
        f"- **Commit:** `{sha[:12]}` — dokumentierter OP-Fix.\n",
        encoding="utf-8",
    )

    def fake_git(*args: str, cwd: Path | None = None) -> str:
        if args[:1] == ("log",):
            return f"{sha}|feat(chat): add selected work tool\n"
        if args[:1] == ("show",):
            return "werkstatt/chat_tools.py\n"
        raise AssertionError(f"unerwarteter git-Aufruf: {args}")

    monkeypatch.setattr(doku_check, "_git", fake_git)

    assert doku_check.pruefe_commits(limit=5, cwd=tmp_path) == []

