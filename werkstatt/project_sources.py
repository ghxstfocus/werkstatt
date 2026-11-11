"""Sichere, serverseitige GitHub-Run-Worktrees fuer registrierte Projekte."""
from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


class GitHubSyncError(RuntimeError):
    """Remote-Run kann nicht sicher vorbereitet werden."""


@dataclass(frozen=True)
class PreparedGitHubRun:
    repository: str
    branch: str
    base_sha: str
    remote_sha: str
    run_branch: str
    worktree_path: Path


def _git(cwd: Path, *args: str, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    try:
        return subprocess.run(
            ["git", "-C", str(cwd), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GitHubSyncError(
            "Git-Befehl fehlgeschlagen oder Zeitlimit ueberschritten.",
        ) from exc


def _github_slug(remote: str) -> str | None:
    """Validiert HTTPS-/SSH-Remotes und liefert owner/repo ohne Credentials."""
    if remote.startswith("git@github.com:"):
        path = remote.removeprefix("git@github.com:")
    else:
        try:
            parsed = urlsplit(remote)
        except ValueError as exc:
            raise GitHubSyncError("GitHub-Remote ist ungueltig.") from exc
        try:
            hostname = parsed.hostname
            port = parsed.port
        except ValueError as exc:
            raise GitHubSyncError("GitHub-Remote ist ungueltig.") from exc
        if hostname is None or hostname.casefold() != "github.com":
            return None
        if parsed.scheme not in {"https", "ssh"}:
            raise GitHubSyncError("GitHub-Remote muss HTTPS oder SSH verwenden.")
        if parsed.username not in {None, "", "git"} or parsed.password:
            raise GitHubSyncError("Credentials im Git-Remote sind nicht erlaubt.")
        if port is not None or parsed.query or parsed.fragment:
            raise GitHubSyncError(
                "GitHub-Remote enthaelt unzulaessige URL-Bestandteile.",
            )
        path = parsed.path.lstrip("/")
    path = path.removesuffix(".git")
    parts = path.split("/")
    if len(parts) != 2 or any(
        not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", part)
        or part in {".", ".."}
        for part in parts
    ):
        raise GitHubSyncError("GitHub-Remote muss genau owner/repo bezeichnen.")
    return f"{parts[0]}/{parts[1]}"


def _looks_like_git_checkout(project_dir: Path) -> bool:
    try:
        (project_dir / ".git").lstat()
    except FileNotFoundError:
        return False
    except OSError:
        return True
    return True


def _origin_repository(project_dir: Path) -> str | None:
    if not _looks_like_git_checkout(project_dir):
        return None
    root = _git(project_dir, "rev-parse", "--show-toplevel")
    if root.returncode != 0:
        if _looks_like_git_checkout(project_dir):
            raise GitHubSyncError("Git-Repository kann nicht sicher geprueft werden.")
        return None
    remotes = _git(project_dir, "remote")
    if remotes.returncode != 0:
        raise GitHubSyncError("Git-Remotes koennen nicht sicher gelesen werden.")
    if "origin" not in remotes.stdout.split():
        return None
    remote = _git(project_dir, "remote", "get-url", "origin")
    if remote.returncode != 0:
        raise GitHubSyncError("Konfiguriertes origin-Remote ist nicht lesbar.")
    return _github_slug(remote.stdout.strip())


def _upstream_branch(project_dir: Path) -> str:
    upstream = _git(
        project_dir, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}",
    )
    if upstream.returncode != 0:
        raise GitHubSyncError(
            "GitHub-Projekt hat keinen konfigurierten Upstream-Branch.",
        )
    value = upstream.stdout.strip()
    prefix = "origin/"
    if not value.startswith(prefix) or len(value) == len(prefix):
        raise GitHubSyncError("Der konfigurierte Upstream muss auf origin zeigen.")
    branch = value.removeprefix(prefix)
    check = _git(project_dir, "check-ref-format", "--branch", branch)
    if check.returncode != 0:
        raise GitHubSyncError("Der konfigurierte Remote-Branch ist ungueltig.")
    return branch


def prepare_github_run_worktree(
    project_dir: Path,
    run_id: str,
) -> PreparedGitHubRun | None:
    """Fetch + pinnt GitHub-HEAD und erzeugt einen eigenen Run-Branch/Worktree.

    Gibt None fuer Nicht-Git- oder Nicht-GitHub-Projekte zurueck. Der
    bestehende Server-Checkout wird niemals gemergt, zurueckgesetzt oder
    anderweitig durch den Fetch veraendert.
    """
    project_dir = Path(project_dir).resolve()
    repository = _origin_repository(project_dir)
    if repository is None:
        return None
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", run_id):
        raise GitHubSyncError("Run-ID ist fuer einen Worktree ungueltig.")

    status = _git(project_dir, "status", "--porcelain", "--untracked-files=all")
    if status.returncode != 0:
        raise GitHubSyncError("Git-Status kann nicht sicher bestimmt werden.")
    if status.stdout.strip():
        raise GitHubSyncError(
            "Server-Checkout hat lokale Aenderungen; Remote-Run gestoppt.",
        )

    head = _git(project_dir, "rev-parse", "--verify", "HEAD^{commit}")
    if head.returncode != 0:
        raise GitHubSyncError("Server-Checkout hat keinen aufloesbaren HEAD.")
    base_sha = head.stdout.strip()
    branch = _upstream_branch(project_dir)
    remote_ref = f"refs/remotes/werkstatt-sync/{branch}"
    ref_check = _git(project_dir, "check-ref-format", remote_ref)
    if ref_check.returncode != 0:
        raise GitHubSyncError("GitHub-Branch ist ungueltig.")

    fetched = _git(
        project_dir,
        "fetch",
        "--no-tags",
        "--no-recurse-submodules",
        "origin",
        f"+refs/heads/{branch}:{remote_ref}",
        timeout=120,
    )
    if fetched.returncode != 0:
        raise GitHubSyncError(
            "GitHub-Fetch fehlgeschlagen; der Loop wurde nicht gestartet.",
        )
    remote = _git(project_dir, "rev-parse", "--verify", f"{remote_ref}^{{commit}}")
    if remote.returncode != 0:
        raise GitHubSyncError("Gefetchter GitHub-Commit ist nicht aufloesbar.")
    remote_sha = remote.stdout.strip()

    ancestor = _git(project_dir, "merge-base", "--is-ancestor", base_sha, remote_sha)
    if ancestor.returncode != 0:
        raise GitHubSyncError(
            "Server-Branch ist voraus oder divergiert; "
            "automatische Synchronisierung gestoppt.",
        )

    run_branch = f"werkstatt/run/{run_id}"
    branch_check = _git(project_dir, "check-ref-format", "--branch", run_branch)
    if branch_check.returncode != 0:
        raise GitHubSyncError("Run-Branch ist ungueltig.")

    worktrees_root = (project_dir / ".werkstatt" / "worktrees").resolve()
    try:
        worktrees_root.relative_to(project_dir)
    except ValueError as exc:
        raise GitHubSyncError(
            "Worktree-Verzeichnis liegt ausserhalb des Projekts.",
        ) from exc
    worktree_path = worktrees_root / run_id
    if worktree_path.exists():
        raise GitHubSyncError("Run-Worktree existiert bereits.")
    if worktree_path.resolve().parent != worktrees_root:
        raise GitHubSyncError("Run-Worktree-Pfad ist nicht sicher.")
    final_status = _git(project_dir, "status", "--porcelain", "--untracked-files=all")
    final_head = _git(project_dir, "rev-parse", "--verify", "HEAD^{commit}")
    if (
        final_status.returncode != 0
        or final_status.stdout.strip()
        or final_head.returncode != 0
        or final_head.stdout.strip() != base_sha
    ):
        raise GitHubSyncError(
            "Server-Checkout hat sich waehrend des Fetchs geaendert; Run gestoppt.",
        )
    try:
        worktrees_root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise GitHubSyncError(
            "Verwaltetes Worktree-Verzeichnis kann nicht angelegt werden.",
        ) from exc
    created = _git(
        project_dir, "worktree", "add", "--quiet", "-b", run_branch,
        str(worktree_path), remote_sha,
        timeout=60,
    )
    if created.returncode != 0:
        raise GitHubSyncError(
            "Isolierter GitHub-Worktree konnte nicht erstellt werden.",
        )
    return PreparedGitHubRun(
        repository=repository,
        branch=branch,
        base_sha=base_sha,
        remote_sha=remote_sha,
        run_branch=run_branch,
        worktree_path=worktree_path,
    )


def remove_prepared_worktree(project_dir: Path, prepared: PreparedGitHubRun) -> None:
    """Entfernt nur einen frisch angelegten Run-Worktree nach Startfehler."""
    project_dir = Path(project_dir).resolve()
    expected_root = (project_dir / ".werkstatt" / "worktrees").resolve()
    path = prepared.worktree_path.resolve()
    if (
        path.parent != expected_root
        or prepared.run_branch != f"werkstatt/run/{path.name}"
    ):
        raise GitHubSyncError(
            "Run-Worktree oder Branch entspricht nicht der Run-Identitaet.",
        )
    removed = _git(project_dir, "worktree", "remove", "--force", str(path), timeout=30)
    if removed.returncode != 0:
        raise GitHubSyncError(
            "Run-Worktree konnte nach Startfehler nicht entfernt werden.",
        )
    deleted = _git(project_dir, "branch", "-D", prepared.run_branch)
    if deleted.returncode != 0:
        raise GitHubSyncError("Temporärer Run-Branch konnte nicht entfernt werden.")
