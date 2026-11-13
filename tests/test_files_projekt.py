"""Spec-Tests fuer OP-391: /files + /diff respektieren den Projektnamen.

Verhalten, das dieser Test verbietet:
- /api/projects/{name}/files zeigt Dateien aus dem falschen Projekt
  (hardcoded /opt/werkstatt statt _PROJECTS_BASE/name).
- /api/projects/{name}/diff ruft git diff mit cwd=Werkstatt statt mit
  cwd=<PROJECTS_BASE>/name.
- Pfad-Traversal (?pfad=../anderes-projekt/x) umgeht den Root-Check.

Isolation: _PROJECTS_BASE via monkeypatch auf tmp_path, subprocess.run
wird fuer /diff gemockt — der Test haengt nicht vom echten Working
Tree oder von /opt/werkstatt ab.
"""
from __future__ import annotations

import subprocess as real_subprocess
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from werkstatt.web import app as app_module
from werkstatt.web import auth


@pytest.fixture
def client_multi(monkeypatch, tmp_path):
    """Zwei Mini-Projekte in tmp_path, auth aus, _PROJECTS_BASE gepatcht."""
    (tmp_path / "test-a").mkdir()
    (tmp_path / "test-b").mkdir()
    (tmp_path / "test-a" / "a-datei.txt").write_text("INHALT-A", encoding="utf-8")
    (tmp_path / "test-b" / "b-datei.txt").write_text("INHALT-B", encoding="utf-8")
    monkeypatch.setattr(app_module, "_PROJECTS_BASE", tmp_path)
    monkeypatch.setattr(auth, "_AUTH_DISABLED", True)
    from werkstatt.web.app import create_app
    return TestClient(create_app()), tmp_path


def test_files_projektname_beruecksichtigt(client_multi) -> None:
    """GET /files fuer test-a zeigt nur test-a-Dateien."""
    client, tmp_path = client_multi
    r = client.get("/api/projects/test-a/files")
    assert r.status_code == 200, r.text
    body = r.json()
    namen = {e["name"] for e in body["eintraege"]}
    assert "a-datei.txt" in namen, (
        f"erwartet a-datei.txt aus {tmp_path / 'test-a'}, "
        f"bekommen: {sorted(namen)}"
    )
    assert "b-datei.txt" not in namen, (
        "b-datei.txt aus anderem Projekt darf NICHT erscheinen"
    )


def test_files_pfad_traversal_blockiert(client_multi) -> None:
    """Pfad ausserhalb des Projekt-Roots bleibt 400."""
    client, _ = client_multi
    r = client.get("/api/projects/test-a/files?pfad=../test-b/b-datei.txt")
    assert r.status_code == 400, r.text


def test_files_unbekanntes_projekt_404(client_multi) -> None:
    """Projekt existiert nicht im Dateisystem -> 404."""
    client, _ = client_multi
    r = client.get("/api/projects/gibtsnicht/files")
    assert r.status_code == 404, r.text


def test_diff_ruft_subprocess_mit_projekt_cwd(client_multi) -> None:
    """/diff fuer test-a ruft git diff mit cwd=<PROJECTS_BASE>/test-a.

    Deterministisch: subprocess.run wird gepatcht, cwd geprueft.
    """
    client, tmp_path = client_multi

    fake = MagicMock()
    fake.stdout = "diff --git a/x b/x\n"

    with patch.object(real_subprocess, "run", return_value=fake) as mock_run:
        r = client.get("/api/projects/test-a/diff?ref=HEAD")

    assert r.status_code == 200, r.text
    assert mock_run.call_count >= 1
    erwartet = str(tmp_path / "test-a")
    for call in mock_run.call_args_list:
        cwd = call.kwargs.get("cwd")
        assert cwd == erwartet, (
            f"git-diff-cwd muss {erwartet!r} sein (projekt-spezifisch), "
            f"war {cwd!r}"
        )


def test_github_run_diff_uses_validated_worktree_and_pinned_base(
    monkeypatch, tmp_path,
) -> None:
    """GitHub-Diff zeigt den Run-Worktree gegen die gepinnte Startrevision."""
    from werkstatt.project_sources import _managed_worktrees_root
    from werkstatt.web.app import create_app

    project = tmp_path / "demo"
    project.mkdir()

    def git(path, *args):
        result = real_subprocess.run(
            ["git", "-C", str(path), *args],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    git(project, "init", "-b", "main")
    git(project, "config", "user.email", "test@example.invalid")
    git(project, "config", "user.name", "Test")
    git(project, "remote", "add", "origin", "https://github.com/example/demo.git")
    (project / "tracked.txt").write_text("base\n", encoding="utf-8")
    git(project, "add", "tracked.txt")
    git(project, "commit", "-m", "base")
    pinned_sha = git(project, "rev-parse", "HEAD")

    run_id = "demo-20261113-abc12345"
    monkeypatch.setenv("WERKSTATT_RUN_WORKTREE_DIR", str(tmp_path / "run-state"))
    worktree = _managed_worktrees_root(project) / run_id
    worktree.parent.mkdir(parents=True)
    git(
        project, "worktree", "add", "-b", f"werkstatt/run/{run_id}",
        str(worktree), pinned_sha,
    )
    (worktree / "tracked.txt").write_text("changed by the loop\n", encoding="utf-8")

    record = {
        "run_id": run_id,
        "state": "running",
        "context": {
            "source": {
                "kind": "github",
                "repository": "example/demo",
                "branch": "main",
                "pinned_sha": pinned_sha,
                "run_branch": f"werkstatt/run/{run_id}",
                "worktree": str(worktree),
            },
        },
    }

    class Registry:
        def read(self, _project):
            return record


    monkeypatch.setattr(app_module, "_PROJECTS_BASE", tmp_path)
    monkeypatch.setattr(app_module, "_loop_registry", lambda: Registry())
    monkeypatch.setattr(auth, "_AUTH_DISABLED", True)
    client = TestClient(create_app())

    response = client.get("/api/projects/demo/diff")

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["run_id"] == run_id
    assert data["ref"] == pinned_sha
    assert "changed by the loop" in data["diff"]
    git(project, "worktree", "remove", "--force", str(worktree))
