"""Read-only Tool-Registry fuer den Chat-Agent (OP-231, ADR-0008).

Acht Tools (SOLL §5.3). Kein write_file/apply_patch/git_commit/shell_exec.
Alle Tools haben Timeouts und Groessenlimits. ``mode``-Feld pro Tool
bereitet opt-in write-Tools vor (heute alle read).
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

__all__ = ["CHAT_TOOLS", "execute_tool", "openai_schemas"]

_PROJEKT_DIR = Path("/opt/werkstatt").resolve()
_MAX_READ_BYTES = 50_000
_MAX_GREP_TREFFER = 30
_TIMEOUT_GREP_S = 10
_TIMEOUT_GIT_S = 30
_TIMEOUT_PYTEST_S = 60


def _resolved_safe(pfad: str) -> Path | None:
    if not pfad:
        return None
    try:
        p = (_PROJEKT_DIR / pfad).resolve()
    except (OSError, RuntimeError):
        return None
    try:
        p.relative_to(_PROJEKT_DIR)
    except ValueError:
        return None
    return p


def _read_file(args: dict[str, Any]) -> str:
    pfad = _resolved_safe(str(args.get("path", "")))
    if pfad is None or not pfad.is_file():
        return "Fehler: Datei nicht gefunden oder ausserhalb Projekt"
    try:
        data = pfad.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"Fehler beim Lesen: {exc}"
    start = int(args.get("start", 0))
    end = args.get("end")
    if end is not None:
        return data[start : int(end)]
    return data[start : start + _MAX_READ_BYTES]


def _grep(args: dict[str, Any]) -> str:
    pattern = str(args.get("pattern", "")).strip()
    if not pattern:
        return "Fehler: pattern fehlt"
    pfad = _resolved_safe(str(args.get("path", ".")))
    if pfad is None:
        return "Fehler: path ausserhalb Projekt"
    try:
        r = subprocess.run(
            ["grep", "-rn", f"--max-count={_MAX_GREP_TREFFER}",
             pattern, str(pfad)],
            capture_output=True, text=True, check=False,
            timeout=_TIMEOUT_GREP_S,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return f"grep-Fehler: {exc}"
    return (r.stdout or r.stderr or "(kein Treffer)")[:20_000]


def _git_log(args: dict[str, Any]) -> str:
    n = max(1, min(int(args.get("n", 10)), 100))
    try:
        r = subprocess.run(
            ["git", "log", "--oneline", f"-n{n}"],
            capture_output=True, text=True, check=False, timeout=_TIMEOUT_GIT_S,
            cwd=_PROJEKT_DIR,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return f"git_log-Fehler: {exc}"
    return (r.stdout or r.stderr)[:10_000]


def _git_diff(args: dict[str, Any]) -> str:
    ref = str(args.get("ref", "HEAD"))
    try:
        r = subprocess.run(
            ["git", "diff", ref],
            capture_output=True, text=True, check=False, timeout=_TIMEOUT_GIT_S,
            cwd=_PROJEKT_DIR,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return f"git_diff-Fehler: {exc}"
    return (r.stdout or "(kein Diff)")[:50_000]


def _audit_query(args: dict[str, Any]) -> str:
    from werkstatt.audit import get_run_id
    from werkstatt.event_store import EventStore

    run_id = str(args.get("run_id") or get_run_id() or "")
    if not run_id:
        return "audit_query: keine run_id (weder Argument noch set_run_id())"
    kind = args.get("kind")
    since = args.get("since")
    try:
        evs = EventStore().query(
            run_id,
            kind=str(kind) if kind else None,
            since_seq=int(since) if since is not None else None,
        )
    except Exception as exc:
        return f"audit_query-Fehler: {exc}"
    return json.dumps(evs[:50], ensure_ascii=False)[:30_000]


def _pytest_collect(args: dict[str, Any]) -> str:
    pfad = _resolved_safe(str(args.get("path", ".")))
    if pfad is None:
        return "Fehler: path ausserhalb Projekt"
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q", str(pfad)],
            capture_output=True, text=True, check=False, timeout=_TIMEOUT_PYTEST_S,
            cwd=_PROJEKT_DIR,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return f"pytest_collect-Fehler: {exc}"
    return (r.stdout or r.stderr)[:20_000]


def _diagnose(_args: dict[str, Any]) -> str:
    return json.dumps({
        "bekannte_fehlerklassen": [
            "ruff_rot", "mypy_rot", "pytest_rot", "drift_rot",
            "quality_gate_baseline_drift", "gate_timeout",
            "headless_ohne_run_id",
        ],
        "hinweis": (
            "diagnose() ist statisch. Fuer konkrete Zahlen "
            "read_status + grep nutzen."
        ),
    }, ensure_ascii=False)


def _read_status(_args: dict[str, Any]) -> str:
    aus: list[str] = []
    for name in ("docs/STATUS.md", "docs/PROGRESS.md"):
        p = _PROJEKT_DIR / name
        if p.is_file():
            try:
                text = p.read_text(encoding="utf-8", errors="replace")[:10_000]
            except OSError:
                continue
            aus.append(f"## {name}\n{text}\n")
    return "\n".join(aus) or "(STATUS.md/PROGRESS.md nicht gefunden)"


CHAT_TOOLS: dict[str, dict[str, Any]] = {
    "read_file": {
        "description": "Liest Datei-Inhalt (max 50 KB).",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "start": {"type": "integer"},
                "end": {"type": "integer"},
            },
            "required": ["path"],
        },
        "fn": _read_file,
        "mode": "read",
    },
    "grep": {
        "description": f"Sucht Pattern in Datei/Verzeichnis (max {_MAX_GREP_TREFFER} Treffer).",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "path": {"type": "string"},
            },
            "required": ["pattern"],
        },
        "fn": _grep,
        "mode": "read",
    },
    "git_log": {
        "description": "Letzte Commits (oneline).",
        "parameters": {
            "type": "object",
            "properties": {"n": {"type": "integer"}},
        },
        "fn": _git_log,
        "mode": "read",
    },
    "git_diff": {
        "description": "Diff gegen Ref (default HEAD).",
        "parameters": {
            "type": "object",
            "properties": {"ref": {"type": "string"}},
        },
        "fn": _git_diff,
        "mode": "read",
    },
    "audit_query": {
        "description": "Audit-Events einer run_id filtern (kind, since).",
        "parameters": {
            "type": "object",
            "properties": {
                "kind": {"type": "string"},
                "since": {"type": "integer"},
                "run_id": {"type": "string"},
            },
        },
        "fn": _audit_query,
        "mode": "read",
    },
    "pytest_collect": {
        "description": "Tests sammeln (collect-only, kein Run).",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
        },
        "fn": _pytest_collect,
        "mode": "read",
    },
    "diagnose": {
        "description": "Liste bekannter Fehlerklassen.",
        "parameters": {"type": "object", "properties": {}},
        "fn": _diagnose,
        "mode": "read",
    },
    "read_status": {
        "description": "STATUS.md + PROGRESS.md (Kopf).",
        "parameters": {"type": "object", "properties": {}},
        "fn": _read_status,
        "mode": "read",
    },
}


def _mode_erlaubt(spec: dict[str, Any], mode: str) -> bool:
    want = spec.get("mode", "read")
    if want == "read":
        return True
    return mode == "write"


def openai_schemas(
    tools: dict[str, dict[str, Any]] | None = None,
    mode: str = "read",
) -> list[dict[str, Any]]:
    src = tools if tools is not None else CHAT_TOOLS
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": spec.get("description", ""),
                "parameters": spec.get(
                    "parameters",
                    {"type": "object", "properties": {}},
                ),
            },
        }
        for name, spec in src.items()
        if _mode_erlaubt(spec, mode)
    ]


def execute_tool(
    name: str,
    args: dict[str, Any],
    tools: dict[str, dict[str, Any]] | None = None,
    mode: str = "read",
) -> str:
    src = tools if tools is not None else CHAT_TOOLS
    spec = src.get(name)
    if spec is None:
        return f"Fehler: Tool '{name}' nicht in Registry (read-only)"
    if not _mode_erlaubt(spec, mode):
        return f"Fehler: Tool '{name}' erfordert mode='write' (aktuell '{mode}')"
    fn: Callable[[dict[str, Any]], str] = spec["fn"]
    try:
        return str(fn(args))
    except Exception as exc:
        return f"Tool-Fehler ({name}): {type(exc).__name__}: {exc}"
