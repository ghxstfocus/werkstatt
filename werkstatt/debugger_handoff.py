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
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any

__all__ = [
    "DebuggerFix",
    "DebuggerFixError",
    "create_debugger_fix",
    "debugger_fix_loop_task",
    "parse_debugger_fix",
    "validate_debugger_fix_checkout",
]

_MAX_DIFF_BYTES = 20_000
_MAX_FILES = 20
_HEX_HEAD = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_CAUSE_TAG = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_PROJECT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_RUN_SUFFIX = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
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

    @property
    def patch_hash(self) -> str:
        encoded = json.dumps(
            asdict(self),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def to_payload(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "betroffene_dateien": list(self.betroffene_dateien),
            "patch_hash": self.patch_hash,
        }


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
        "new file mode ",
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
    if set(payload) != required:
        raise DebuggerFixError("DebuggerFix hat fehlende oder unerwartete Felder.")

    signatur = payload["signatur"]
    cause = payload["ursache_tag"]
    diff = payload["diff"]
    project = payload["project"]
    run_id = payload["run_id"]
    base_head = payload["base_head"]
    confidence = payload["confidence"]
    files = payload["betroffene_dateien"]

    if not isinstance(signatur, str) or not _IDENTIFIER.fullmatch(signatur):
        raise DebuggerFixError("signatur ist ungueltig.")
    if not isinstance(cause, str) or not _CAUSE_TAG.fullmatch(cause):
        raise DebuggerFixError("ursache_tag ist ungueltig.")
    if not isinstance(project, str) or not _PROJECT.fullmatch(project):
        raise DebuggerFixError("Projektname ist ungueltig.")
    if (
        not isinstance(run_id, str)
        or not run_id.startswith(project + "-")
        or not _RUN_SUFFIX.fullmatch(run_id[len(project) + 1 :])
    ):
        raise DebuggerFixError("run_id muss zum Projekt gehoeren.")
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
    )
    if not isinstance(payload["patch_hash"], str) or payload["patch_hash"] != fix.patch_hash:
        raise DebuggerFixError("Patch-Hash stimmt nicht mit dem freizugebenden Inhalt ueberein.")
    return fix



def create_debugger_fix(
    *,
    signatur: str,
    ursache_tag: str,
    diff: str,
    betroffene_dateien: list[str],
    confidence: float,
    project: str,
    run_id: str,
    base_head: str,
) -> DebuggerFix:
    """Erzeugt einen geprueften Fix und berechnet dessen Freigabe-Hash."""
    fix = DebuggerFix(
        signatur=signatur,
        ursache_tag=ursache_tag,
        diff=diff,
        betroffene_dateien=tuple(betroffene_dateien),
        confidence=confidence,
        project=project,
        run_id=run_id,
        base_head=base_head,
    )
    return parse_debugger_fix(fix.to_payload())


def debugger_fix_loop_task(fix: DebuggerFix) -> str:
    """Formatiert den freigegebenen Fix als unveraenderlichen Loop-Auftrag."""
    payload = {
        "type": "debugger_fix",
        "schema_version": 1,
        "approval": "exact_diff_hash",
        "patch_hash": fix.patch_hash,
        "project": fix.project,
        "source_run_id": fix.run_id,
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
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


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
            input=fix.diff,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_s,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"Patch-Pruefung fehlgeschlagen: {type(exc).__name__}"
    if check.returncode != 0:
        detail = (check.stderr or check.stdout or "Patch passt nicht zum Projektstand.")
        return False, detail[-2000:]
    return True, "Patch ist fuer Projekt und aktuellen HEAD anwendbar."
