"""Validierung des strukturierten Chat-Debugger-Patch-Vertrags.

Dieses Modul schreibt keine Produktionsdateien. Es prueft den Vorschlag,
bindet ihn an Projekt/Run/Basis-Commit und stellt eine stabile Hash-Identitaet
fuer die spaetere, einmalige Freigabe und Loop-Uebergabe bereit.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
import tempfile
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

__all__ = [
    "DebuggerFix",
    "DebuggerFixError",
    "cleanup_debugger_workspace",
    "create_debugger_fix",
    "debugger_fix_loop_task",
    "debugger_workspace_path",
    "materialize_debugger_workspace",
    "parse_debugger_fix",
    "parse_debugger_loop_task",
    "validate_debugger_fix_checkout",
]

_MAX_DIFF_BYTES = 20_000
_MAX_FILES = 20
_MAX_LOOP_PATCH_CONTENT_BYTES = 5_000_000
_HEX_HEAD = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_CAUSE_TAG = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_PROJECT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_RUN_SUFFIX = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_PROPOSAL_ID = re.compile(r"^[a-f0-9]{32}$")
_DIFF_HEADER = re.compile(r"^diff --git a/(.+) b/(.+)$")
_OLD_FILE = re.compile(r"^--- (?:a/(.+)|/dev/null)$")
_NEW_FILE = re.compile(r"^\+\+\+ (?:b/(.+)|/dev/null)$")


class DebuggerFixError(ValueError):
    """Ein Debugger-Patch erfuellt den Freigabe-Vertrag nicht."""


@dataclass(frozen=True)
class DebuggerFix:
    signatur: str
    ursache_tag: str
    diff: str
    betroffene_dateien: tuple[str, ...]
    confidence: float
    project: str
    run_id: str
    base_head: str
    source_kind: str = "loop_run"
    source_chat_session_id: str | None = None

    def _hash_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "signatur": self.signatur,
            "ursache_tag": self.ursache_tag,
            "diff": self.diff,
            "betroffene_dateien": list(self.betroffene_dateien),
            "confidence": self.confidence,
            "project": self.project,
            "run_id": self.run_id,
            "base_head": self.base_head,
        }
        if self.source_kind == "chat_session":
            payload["source_kind"] = self.source_kind
            payload["source_chat_session_id"] = self.source_chat_session_id
        return payload

    @property
    def patch_hash(self) -> str:
        encoded = json.dumps(
            self._hash_payload(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def to_payload(self) -> dict[str, Any]:
        return {**self._hash_payload(), "patch_hash": self.patch_hash}


def _safe_path(raw: Any) -> str:
    if not isinstance(raw, str) or not raw or "\\" in raw or "\x00" in raw:
        raise DebuggerFixError("Patch-Pfad ist ungueltig.")
    path = PurePosixPath(raw)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise DebuggerFixError("Patch-Pfad muss relativ und ohne Traversal sein.")
    lowered = [part.casefold() for part in path.parts]
    if ".git" in lowered or ".werkstatt" in lowered:
        raise DebuggerFixError("Interne Git-/Werkstatt-Pfade sind nicht zulaessig.")
    name = lowered[-1]
    if (
        name == ".env"
        or name.startswith(".env.")
        or name in {"id_rsa", "id_ed25519", "credentials.json"}
        or name.endswith((".pem", ".key", ".p12", ".pfx"))
    ):
        raise DebuggerFixError("Moeglicher Secret-Pfad ist nicht zulaessig.")
    return path.as_posix()


def _patch_files(diff: str) -> tuple[str, ...]:
    if not diff.startswith("diff --git "):
        raise DebuggerFixError("Diff muss ein vollstaendiger Unified Git-Diff sein.")
    if "GIT binary patch" in diff or "Binary files " in diff:
        raise DebuggerFixError("Binaere Patches sind nicht zulaessig.")
    forbidden_headers = (
        "old mode ",
        "new mode ",
        "deleted file mode ",
        "rename from ",
        "rename to ",
        "Subproject commit ",
    )
    lines = diff.splitlines()
    if any(line.startswith(forbidden_headers) for line in lines):
        raise DebuggerFixError("Dateimodus-, Rename- und Submodule-Patches sind gesperrt.")

    sections = re.split(r"(?m)(?=^diff --git )", diff)
    paths: list[str] = []
    for section in sections:
        if not section.strip():
            continue
        section_lines = section.splitlines()
        match = _DIFF_HEADER.fullmatch(section_lines[0])
        if match is None:
            raise DebuggerFixError("Git-Diff-Kopf ist ungueltig.")
        old_header, new_header = match.groups()
        old_path = _safe_path(old_header)
        new_path = _safe_path(new_header)
        if old_path != new_path:
            raise DebuggerFixError("Umbenennungen sind nicht zulaessig.")

        old_lines = [m for line in section_lines if (m := _OLD_FILE.fullmatch(line))]
        new_lines = [m for line in section_lines if (m := _NEW_FILE.fullmatch(line))]
        if len(old_lines) != 1 or len(new_lines) != 1:
            raise DebuggerFixError("Jeder Patch-Abschnitt braucht genau ein Datei-Paar.")
        from_path, to_path = old_lines[0].groups()[0], new_lines[0].groups()[0]
        if from_path is None and to_path is None:
            raise DebuggerFixError("Patch-Abschnitt enthaelt keine Zieldatei.")
        if from_path is not None and _safe_path(from_path) != old_path:
            raise DebuggerFixError("Alter Datei-Pfad stimmt nicht mit Diff-Kopf ueberein.")
        if to_path is not None and _safe_path(to_path) != new_path:
            raise DebuggerFixError("Neuer Datei-Pfad stimmt nicht mit Diff-Kopf ueberein.")
        new_file_modes = [
            line for line in section_lines
            if line.startswith("new file mode ")
        ]
        if new_file_modes and (
            new_file_modes != ["new file mode 100644"]
            or from_path is not None
            or to_path is None
        ):
            raise DebuggerFixError(
                "Nur einfache Neudateien mit Modus 100644 sind zulaessig."
            )
        if from_path is None and not new_file_modes:
            raise DebuggerFixError(
                "Neudatei-Patch braucht den expliziten Modus 100644."
            )
        if not any(line.startswith("@@ ") for line in section_lines):
            raise DebuggerFixError("Patch-Abschnitt enthaelt keinen Text-Hunk.")
        paths.append(new_path)

    if not paths or len(paths) > _MAX_FILES or len(set(paths)) != len(paths):
        raise DebuggerFixError("Dateianzahl im Patch ist leer, doppelt oder zu gross.")
    return tuple(sorted(paths))


def parse_debugger_fix(payload: Mapping[str, Any]) -> DebuggerFix:
    """Validiert Schema, Diff-Pfade und den vom UI freizugebenden SHA-256."""
    required = {
        "signatur",
        "ursache_tag",
        "diff",
        "betroffene_dateien",
        "confidence",
        "project",
        "run_id",
        "base_head",
        "patch_hash",
    }
    chat_source_fields = {"source_kind", "source_chat_session_id"}
    if frozenset(payload) not in {
        frozenset(required), frozenset(required | chat_source_fields),
    }:
        raise DebuggerFixError("DebuggerFix hat fehlende oder unerwartete Felder.")

    signatur = payload["signatur"]
    cause = payload["ursache_tag"]
    diff = payload["diff"]
    project = payload["project"]
    run_id = payload["run_id"]
    source_kind = payload.get("source_kind", "loop_run")
    source_chat_session_id = payload.get("source_chat_session_id")
    base_head = payload["base_head"]
    confidence = payload["confidence"]
    files = payload["betroffene_dateien"]

    if not isinstance(signatur, str) or not _IDENTIFIER.fullmatch(signatur):
        raise DebuggerFixError("signatur ist ungueltig.")
    if not isinstance(cause, str) or not _CAUSE_TAG.fullmatch(cause):
        raise DebuggerFixError("ursache_tag ist ungueltig.")
    if not isinstance(project, str) or not _PROJECT.fullmatch(project):
        raise DebuggerFixError("Projektname ist ungueltig.")
    if source_kind == "loop_run":
        if source_chat_session_id is not None:
            raise DebuggerFixError("Loop-Run-Debugger darf keine Chat-Session tragen.")
        if (
            not isinstance(run_id, str)
            or not run_id.startswith(project + "-")
            or not _RUN_SUFFIX.fullmatch(run_id[len(project) + 1 :])
        ):
            raise DebuggerFixError("run_id muss zum Projekt gehoeren.")
    elif source_kind == "chat_session":
        if (
            not isinstance(source_chat_session_id, str)
            or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", source_chat_session_id)
        ):
            raise DebuggerFixError("Chat-Session-Quelle ist ungueltig.")
        expected_internal_id = (
            f"{project}-chat-"
            f"{hashlib.sha256(source_chat_session_id.encode('utf-8')).hexdigest()[:32]}"
        )
        if run_id != expected_internal_id:
            raise DebuggerFixError("Interne Debug-Workspace-ID stimmt nicht mit Session ueberein.")
    else:
        raise DebuggerFixError("Debugger-Quelle ist unbekannt.")
    if not isinstance(base_head, str) or not _HEX_HEAD.fullmatch(base_head):
        raise DebuggerFixError("base_head muss ein voller Git-Commit-Hash sein.")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
        raise DebuggerFixError("confidence muss eine Zahl zwischen 0 und 1 sein.")
    confidence = float(confidence)
    if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
        raise DebuggerFixError("confidence muss eine endliche Zahl zwischen 0 und 1 sein.")
    if not isinstance(diff, str) or not diff.strip():
        raise DebuggerFixError("Diff fehlt.")
    if len(diff.encode("utf-8")) > _MAX_DIFF_BYTES:
        raise DebuggerFixError("Diff ueberschreitet das 20-KB-Limit.")
    if not isinstance(files, list) or not files or len(files) > _MAX_FILES:
        raise DebuggerFixError("betroffene_dateien muss 1 bis 20 Pfade enthalten.")
    declared_files = tuple(sorted(_safe_path(item) for item in files))
    if len(set(declared_files)) != len(declared_files):
        raise DebuggerFixError("betroffene_dateien enthaelt Duplikate.")
    actual_files = _patch_files(diff)
    if declared_files != actual_files:
        raise DebuggerFixError("Deklarierte Dateien stimmen nicht mit dem Diff ueberein.")

    fix = DebuggerFix(
        signatur=signatur,
        ursache_tag=cause,
        diff=diff,
        betroffene_dateien=actual_files,
        confidence=confidence,
        project=project,
        run_id=run_id,
        base_head=base_head,
        source_kind=source_kind,
        source_chat_session_id=source_chat_session_id,
    )
    if not isinstance(payload["patch_hash"], str) or payload["patch_hash"] != fix.patch_hash:
        raise DebuggerFixError("Patch-Hash stimmt nicht mit dem freizugebenden Inhalt ueberein.")
    return fix


def parse_debugger_loop_task(value: str) -> DebuggerFix | None:
    """Parse only the versioned exact-diff contract sent to the Loop."""
    try:
        payload = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(payload, dict) or payload.get("type") != "debugger_fix":
        return None
    version = payload.get("schema_version")
    if (
        payload.get("approval") != "exact_diff_hash"
        or isinstance(version, bool)
        or version not in {1, 2}
    ):
        raise DebuggerFixError("Debugger-Loop-Vertrag hat eine unbekannte Version.")
    try:
        fix_payload = {
            "signatur": payload["signatur"],
            "ursache_tag": payload["ursache_tag"],
            "diff": payload["diff"],
            "betroffene_dateien": payload["betroffene_dateien"],
            "confidence": payload["confidence"],
            "project": payload["project"],
            "base_head": payload["base_head"],
            "patch_hash": payload["patch_hash"],
        }
        if version == 1:
            fix_payload["run_id"] = payload["source_run_id"]
        else:
            if payload.get("source_kind") != "chat_session":
                raise DebuggerFixError("Debugger-Loop-Vertrag hat keine Chat-Quelle.")
            fix_payload["source_kind"] = "chat_session"
            fix_payload["source_chat_session_id"] = payload["source_chat_session_id"]
            fix_payload["run_id"] = (
                f"{payload['project']}-chat-"
                f"{hashlib.sha256(str(payload['source_chat_session_id']).encode('utf-8')).hexdigest()[:32]}"
            )
        return parse_debugger_fix(fix_payload)
    except KeyError as exc:
        raise DebuggerFixError(
            "Debugger-Loop-Vertrag enthaelt nicht alle Pflichtfelder."
        ) from exc



def create_debugger_fix(
    *,
    signatur: str,
    ursache_tag: str,
    diff: str,
    betroffene_dateien: list[str],
    confidence: float,
    project: str,
    run_id: str | None,
    base_head: str,
    source_chat_session_id: str | None = None,
) -> DebuggerFix:
    """Erzeugt einen geprueften Fix und berechnet dessen Freigabe-Hash."""
    source_kind = "chat_session" if source_chat_session_id is not None else "loop_run"
    if source_chat_session_id is not None:
        run_id = (
            f"{project}-chat-"
            f"{hashlib.sha256(source_chat_session_id.encode('utf-8')).hexdigest()[:32]}"
        )
    fix = DebuggerFix(
        signatur=signatur,
        ursache_tag=ursache_tag,
        diff=diff,
        betroffene_dateien=tuple(betroffene_dateien),
        confidence=confidence,
        project=project,
        run_id=str(run_id or ""),
        base_head=base_head,
        source_kind=source_kind,
        source_chat_session_id=source_chat_session_id,
    )
    return parse_debugger_fix(fix.to_payload())


def debugger_fix_loop_task(fix: DebuggerFix) -> str:
    """Formatiert den freigegebenen Fix als unveraenderlichen Loop-Auftrag."""
    payload: dict[str, Any] = {
        "type": "debugger_fix",
        "schema_version": 2 if fix.source_kind == "chat_session" else 1,
        "approval": "exact_diff_hash",
        "patch_hash": fix.patch_hash,
        "project": fix.project,
        "base_head": fix.base_head,
        "signatur": fix.signatur,
        "ursache_tag": fix.ursache_tag,
        "confidence": fix.confidence,
        "betroffene_dateien": list(fix.betroffene_dateien),
        "diff": fix.diff,
        "instruction": (
            "Dies ist der exakt freigegebene Debugger-Diff. Folge dem "
            "verpflichtenden Plan-/Human-Gate-Ablauf. Wende in der "
            "Implementierungsphase genau diesen Diff an; veraendere seinen "
            "Inhalt nur nach einer neuen ausdruecklichen Freigabe."
        ),
    }
    if fix.source_kind == "chat_session":
        payload["source_kind"] = fix.source_kind
        payload["source_chat_session_id"] = fix.source_chat_session_id
    else:
        payload["source_run_id"] = fix.run_id
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def debugger_workspace_path(
    fix: DebuggerFix,
    proposal_id: str,
) -> Path:
    """Deterministic private path for the Chat's isolated debug write."""
    if not _PROPOSAL_ID.fullmatch(proposal_id):
        raise DebuggerFixError("proposal_id fuer Debug-Arbeitsbaum ist ungueltig.")
    return (
        Path(tempfile.gettempdir())
        / "werkstatt-debugger-workspaces"
        / fix.project
        / fix.run_id
        / proposal_id
    )


def materialize_debugger_workspace(
    fix: DebuggerFix,
    project_dir: Path | str,
    proposal_id: str,
    *,
    timeout_s: int = 30,
) -> Path:
    """Write the exact Chat-authored patch into a detached Git worktree.

    The active project checkout is only read. The worktree is created at the
    fix's pinned base commit, and the patch must apply there before it is
    written. The caller keeps the hash-bound Loop proposal as the integration
    contract.
    """
    root = Path(project_dir).expanduser().resolve()
    workspace = debugger_workspace_path(fix, proposal_id)
    workspace_parent = workspace.parent.resolve()
    managed_root = (
        Path(tempfile.gettempdir()) / "werkstatt-debugger-workspaces"
    ).resolve()
    if not workspace_parent.is_relative_to(managed_root):
        raise DebuggerFixError("Debug-Arbeitsbaum liegt ausserhalb des Temp-Bereichs.")
    if workspace.exists():
        raise DebuggerFixError("Debug-Arbeitsbaum fuer diesen Vorschlag existiert bereits.")

    added = False
    try:
        add = subprocess.run(
            ["git", "worktree", "add", "--detach", str(workspace), fix.base_head],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_s,
        )
        if add.returncode != 0:
            detail = (add.stderr or add.stdout or "git worktree add fehlgeschlagen")
            raise DebuggerFixError(detail[-2_000:])
        added = True

        check = subprocess.run(
            ["git", "apply", "--check", "--whitespace=nowarn"],
            cwd=workspace,
            input=fix.diff.encode("utf-8"),
            capture_output=True,
            check=False,
            timeout=timeout_s,
        )
        if check.returncode != 0:
            detail = (check.stderr or check.stdout or b"Patch passt nicht auf die Basisrevision.").decode("utf-8", errors="replace")
            raise DebuggerFixError(detail[-2_000:])

        applied = subprocess.run(
            ["git", "apply", "--whitespace=nowarn"],
            cwd=workspace,
            input=fix.diff.encode("utf-8"),
            capture_output=True,
            check=False,
            timeout=timeout_s,
        )
        if applied.returncode != 0:
            detail = (applied.stderr or applied.stdout or b"Patch konnte nicht geschrieben werden.").decode("utf-8", errors="replace")
            raise DebuggerFixError(detail[-2_000:])

        whitespace = subprocess.run(
            ["git", "diff", "--check"],
            cwd=workspace,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_s,
        )
        if whitespace.returncode != 0:
            detail = whitespace.stderr or whitespace.stdout or "git diff --check fehlgeschlagen."
            raise DebuggerFixError(detail[-2_000:])
        return workspace
    except (OSError, subprocess.TimeoutExpired) as exc:
        if added:
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(workspace)],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout_s,
            )
        raise DebuggerFixError(
            f"Isolierter Debug-Schreibvorgang fehlgeschlagen: {type(exc).__name__}",
        ) from exc
    except DebuggerFixError:
        if added:
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(workspace)],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout_s,
            )
        raise


def cleanup_debugger_workspace(
    fix: DebuggerFix,
    project_dir: Path | str,
    proposal_id: str,
    *,
    timeout_s: int = 30,
) -> tuple[bool, str]:
    """Remove only the deterministic managed worktree for this proposal."""
    root = Path(project_dir).expanduser().resolve()
    try:
        workspace = debugger_workspace_path(fix, proposal_id)
    except DebuggerFixError as exc:
        return False, str(exc)
    managed_root = (
        Path(tempfile.gettempdir()) / "werkstatt-debugger-workspaces"
    ).resolve()
    resolved_workspace = workspace.resolve()
    if not resolved_workspace.is_relative_to(managed_root):
        return False, "Debug-Arbeitsbaum liegt ausserhalb des Temp-Bereichs."
    if not workspace.exists():
        return True, "Debug-Arbeitsbaum ist bereits entfernt."
    try:
        result = subprocess.run(
            ["git", "worktree", "remove", "--force", str(workspace)],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_s,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"Debug-Arbeitsbaum konnte nicht entfernt werden: {type(exc).__name__}"
    if result.returncode != 0:
        detail = result.stderr or result.stdout or "git worktree remove fehlgeschlagen"
        return False, detail[-2_000:]
    return True, "Debug-Arbeitsbaum entfernt."


def debugger_fix_loop_patches(
    fix: DebuggerFix,
    project_dir: Path | str,
    *,
    timeout_s: int = 30,
) -> list[dict[str, Any]]:
    """Convert the approved Git diff into exact normal-Loop patch records.

    The project checkout is read only here. A temporary detached worktree
    applies the approved diff at its pinned base; the ordinary Loop patch
    applier then writes those exact resulting file contents after its hooks.
    """
    root = Path(project_dir).expanduser().resolve()
    ok, detail = validate_debugger_fix_checkout(
        fix, root, expected_project=fix.project, timeout_s=timeout_s,
    )
    if not ok:
        raise DebuggerFixError(detail)

    before: dict[str, bytes | None] = {}
    content_bytes = 0
    for relative in fix.betroffene_dateien:
        target = root / relative
        if target.is_symlink():
            raise DebuggerFixError("Debugger-Zieldatei ist ein Symlink.")
        try:
            target.resolve(strict=False).relative_to(root)
        except ValueError as exc:
            raise DebuggerFixError("Debugger-Zieldatei liegt ausserhalb des Projekts.") from exc
        source = subprocess.run(
            ["git", "show", f"{fix.base_head}:{relative}"],
            cwd=root,
            capture_output=True,
            check=False,
            timeout=timeout_s,
        )
        if source.returncode == 0:
            if not target.is_file():
                raise DebuggerFixError("Debugger-Zieldatei fehlt am gepinnten Basisstand.")
            current = target.read_bytes()
            if current != source.stdout:
                raise DebuggerFixError("Debugger-Zieldatei weicht vom gepinnten Basisstand ab.")
            before[relative] = current
            content_bytes += len(current)
        else:
            if target.exists():
                raise DebuggerFixError("Debugger-Neudatei existiert bereits im Checkout.")
            before[relative] = None

    worktree = materialize_debugger_workspace(
        fix, root, uuid.uuid4().hex, timeout_s=timeout_s,
    )
    try:
        patches: list[dict[str, Any]] = []
        for relative in fix.betroffene_dateien:
            target = worktree / relative
            if target.is_symlink():
                raise DebuggerFixError("Debugger-Zieldatei ist ein Symlink.")
            after = target.read_bytes() if target.is_file() else None
            previous = before[relative]
            content_bytes += len(after or b"")
            if content_bytes > _MAX_LOOP_PATCH_CONTENT_BYTES:
                raise DebuggerFixError(
                    "Debugger-Patch ueberschreitet das 5-MB-Loop-Limit."
                )
            if previous is None and after is not None:
                patches.append({
                    "action": "create",
                    "file": relative,
                    "content": after.decode("utf-8"),
                    "approved_debugger_exact": True,
                })
            elif previous is not None and after is None:
                patches.append({
                    "action": "delete",
                    "file": relative,
                    "approved_debugger_exact": True,
                })
            elif previous is not None and after is not None:
                patches.append({
                    "action": "update",
                    "file": relative,
                    "old_string": previous.decode("utf-8"),
                    "new_string": after.decode("utf-8"),
                    "approved_debugger_exact": True,
                })
            else:
                raise DebuggerFixError("Debugger-Patch enthaelt keine Dateiaenderung.")
        return patches
    except UnicodeDecodeError as exc:
        raise DebuggerFixError(
            "Debugger-Diff kann nicht als UTF-8-Text verarbeitet werden."
        ) from exc
    finally:
        cleaned, cleanup_detail = cleanup_debugger_workspace(
            fix, root, worktree.name, timeout_s=timeout_s,
        )
        if not cleaned:
            raise DebuggerFixError(cleanup_detail)


def validate_debugger_fix_checkout(
    fix: DebuggerFix,
    project_dir: Path | str,
    *,
    expected_project: str,
    timeout_s: int = 10,
) -> tuple[bool, str]:
    """Bindet den Fix an das Projekt/HEAD und prueft git apply ohne Dateien zu schreiben."""
    if fix.project != expected_project:
        return False, "DebuggerFix gehoert zu einem anderen Projekt."
    root = Path(project_dir).expanduser().resolve()
    if not root.is_dir():
        return False, "Projektverzeichnis fehlt."
    try:
        head = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_s,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"Git-HEAD konnte nicht geprueft werden: {type(exc).__name__}"
    if head.returncode != 0 or head.stdout.strip() != fix.base_head:
        return False, "Projekt-HEAD hat sich seit der Debugger-Diagnose geaendert."
    try:
        check = subprocess.run(
            ["git", "apply", "--check", "--whitespace=nowarn"],
            cwd=root,
            input=fix.diff.encode("utf-8"),
            capture_output=True,
            check=False,
            timeout=timeout_s,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"Patch-Pruefung fehlgeschlagen: {type(exc).__name__}"
    if check.returncode != 0:
        detail = (check.stderr or check.stdout or b"Patch passt nicht zum Projektstand.").decode("utf-8", errors="replace")
        return False, detail[-2000:]
    return True, "Patch ist fuer Projekt und aktuellen HEAD anwendbar."
