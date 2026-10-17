"""Tests fuer werkstatt_aggregate.py (A1 projekt_stand)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "/opt/werkstatt")

import werkstatt_aggregate as wa


def _git_repo_mit_commits(
    pfad: Path,
    commits: list[tuple[str, str]],
) -> None:
    """W17-A1: baut ein deterministisches Fixture-Repo.

    commits: Liste von (message, inhalt). Jeder Commit
    legt eine Datei <i:03d>.txt an.
    Env: GIT_AUTHOR_*, GIT_COMMITTER_*, GIT_CONFIG_*
    (W17-A10, A14). Zusaetzlich -c user.name/-c user.email
    (W17-A14, doppelte Absicherung gegen
    GIT_CONFIG_GLOBAL=/dev/null).
    """
    import os
    import subprocess

    env = {
        "GIT_AUTHOR_NAME": "test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
        "GIT_AUTHOR_DATE": "2026-01-01T00:00:00 +0000",
        "GIT_COMMITTER_DATE": "2026-01-01T00:00:00 +0000",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", "/root"),
    }
    subprocess.run(
        ("git", "init", "-q", "-b", "main"),
        cwd=str(pfad), env=env, check=True,
    )
    for i, (message, inhalt_txt) in enumerate(commits):
        datei = pfad / f"{i:03d}.txt"
        datei.write_text(inhalt_txt, encoding="utf-8")
        subprocess.run(
            ("git", "add", datei.name),
            cwd=str(pfad), env=env, check=True,
        )
        subprocess.run(
            ("git",
             "-c", "user.name=test",
             "-c", "user.email=test@example.com",
             "commit", "-q", "-m", message),
            cwd=str(pfad), env=env, check=True,
        )


class TestIstWerkstattCommit:
    def test_test_workbench(self) -> None:
        assert wa._ist_werkstatt_commit(
            "test(workbench): notify_ntfy") is True

    def test_fix_workbench(self) -> None:
        assert wa._ist_werkstatt_commit(
            "fix(workbench): whois") is True

    def test_docs_workbench(self) -> None:
        assert wa._ist_werkstatt_commit(
            "docs(workbench): Handoff") is True

    def test_menschlicher_commit(self) -> None:
        assert wa._ist_werkstatt_commit(
            "feat: neues Feature") is False

    def test_workbench_im_body(self) -> None:
        # "workbench" ohne Scope-Klammer: menschlich.
        assert wa._ist_werkstatt_commit(
            "docs: workbench Handbuch") is False


class TestSammleProjektStand:
    def test_pfad_existiert_nicht(self, tmp_path: Path) -> None:
        fehlt = tmp_path / "gibtsnicht"
        stand = wa.sammle_projekt_stand(fehlt)
        assert stand["basis"] == "git-log"
        assert stand["letzte_commits"] == []

    def test_mit_commits(self) -> None:
        stand = wa.sammle_projekt_stand(Path("/opt/security-ai"),
                                        max_commits=3)
        assert stand["basis"] == "git-log"
        assert len(stand["letzte_commits"]) <= 3
        for c in stand["letzte_commits"]:
            assert "hash" in c
            assert "datum" in c
            assert "message" in c
            assert c["quelle"] in ("werkstatt", "mensch")
            assert isinstance(c["dateien"], list)

    def test_quelle_werkstatt(self, tmp_path: Path) -> None:
        """W17: prueft gemischte Historie deterministisch.

        Vorher (flaky): las aus /opt/security-ai live,
        wurde rot, sobald die letzten 5 Commits keinen
        workbench-Scope trugen.
        """
        _git_repo_mit_commits(tmp_path, [
            ("feat(workbench): a", "a"),
            ("fix(workbench): b", "b"),
            ("docs(workbench): c", "c"),
            ("feat: menschlich a", "d"),
            ("docs: menschlich b", "e"),
        ])
        stand = wa.sammle_projekt_stand(tmp_path, max_commits=5)
        quellen = [c["quelle"] for c in stand["letzte_commits"]]
        assert "werkstatt" in quellen, \
            f"quellen={sorted(quellen)}"
        assert "mensch" in quellen, \
            f"quellen={sorted(quellen)}"


class TestYamlQuote:
    def test_einfacher_string(self) -> None:
        assert wa._yaml_quote("hello") == "hello"

    def test_mit_doppelpunkt(self) -> None:
        assert wa._yaml_quote("test(workbench): x") == \
            '"test(workbench): x"'

    def test_mit_newline(self) -> None:
        ergebnis = wa._yaml_quote("a\nb")
        assert ergebnis.startswith('"')
        assert ergebnis.endswith('"')
        assert "\n" in ergebnis
