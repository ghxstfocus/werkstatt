"""Projektgebundene Tool-Registry fuer den Chat-Agent.

Repo-Tools bleiben read-only. request_loop_action speichert ausschliesslich
einen befristeten Vorschlag; die Ausfuehrung verlangt eine separate UI-Freigabe.
Kein write_file/apply_patch/git_commit/shell_exec.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import uuid
from collections.abc import Callable
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from werkstatt.validierung import pruefe_ref

__all__ = ["CHAT_TOOLS", "execute_tool", "openai_schemas"]

_PROJEKT_DIR = Path("/opt/werkstatt").resolve()
_PROJEKT_DIR_KONTEXT: ContextVar[Path | None] = ContextVar(
    "werkstatt_chat_project_dir", default=None,
)
_PROJEKTNAME_KONTEXT: ContextVar[str] = ContextVar(
    "werkstatt_chat_project_name", default="werkstatt",
)
_CHAT_SESSION_ID_KONTEXT: ContextVar[str] = ContextVar(
    "werkstatt_chat_session_id", default="",
)
_MAX_READ_BYTES = 50_000
_MAX_GREP_TREFFER = 30
_TIMEOUT_GREP_S = 10
_TIMEOUT_GIT_S = 30
_TIMEOUT_PYTEST_S = 60


def _aktives_projekt_dir() -> Path:
    return _PROJEKT_DIR_KONTEXT.get() or _PROJEKT_DIR


def _resolved_safe(pfad: str) -> Path | None:
    if not pfad:
        return None
    projekt_dir = _aktives_projekt_dir()
    try:
        p = (projekt_dir / pfad).resolve()
    except (OSError, RuntimeError):
        return None
    try:
        p.relative_to(projekt_dir)
    except ValueError:
        return None
    return p


def _read_file(args: dict[str, Any]) -> str:
    pfad = _resolved_safe(str(args.get("path", "")))
    if pfad is None or not pfad.is_file():
        return "Fehler: Datei nicht gefunden oder ausserhalb Projekt"
    try:
        start = int(args.get("start", 0))
        end_value = args.get("end")
        end = int(end_value) if end_value is not None else None
    except (TypeError, ValueError):
        return "Fehler: start/end muessen ganze Zahlen sein"
    if start < 0 or (end is not None and end < start):
        return "Fehler: ungueltiger start/end-Bereich"

    max_chars = end - start if end is not None else None
    # Keep room for an explicit continuation marker inside the output cap.
    content_byte_limit = _MAX_READ_BYTES - 1024
    try:
        teile: list[str] = []
        with pfad.open("r", encoding="utf-8", errors="replace") as datei:
            ueberspringen = start
            while ueberspringen:
                chunk = datei.read(min(ueberspringen, 8192))
                if not chunk:
                    return ""
                ueberspringen -= len(chunk)

            gelesen = 0
            bytezahl = 0
            truncated = False
            while max_chars is None or gelesen < max_chars:
                anfrage = 8192 if max_chars is None else min(
                    8192, max_chars - gelesen,
                )
                chunk = datei.read(anfrage)
                if not chunk:
                    break
                for zeichen in chunk:
                    zeichen_bytes = len(zeichen.encode("utf-8"))
                    if bytezahl + zeichen_bytes > content_byte_limit:
                        truncated = True
                        break
                    teile.append(zeichen)
                    bytezahl += zeichen_bytes
                    gelesen += 1
                if truncated:
                    break
        inhalt = "".join(teile)
        if truncated:
            fortsetzen = f"read_file(start={start + gelesen}"
            if end is not None:
                fortsetzen += f", end={end}"
            fortsetzen += ")"
            marker = (
                "\n[Ausgabe gekürzt: maximal 50 KB. start/end sind "
                "0-basierte Zeichen-Offsets, keine Zeilennummern. "
                f"Fortsetzen mit {fortsetzen}.]"
            )
            inhalt += marker
        return inhalt
    except OSError as exc:
        return f"Fehler beim Lesen: {exc}"


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
             "--", pattern, str(pfad)],
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
            cwd=_aktives_projekt_dir(),
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return f"git_log-Fehler: {exc}"
    return (r.stdout or r.stderr)[:10_000]


def _git_diff(args: dict[str, Any]) -> str:
    ref = str(args.get("ref", "HEAD"))
    try:
        ref = pruefe_ref(ref)
    except ValueError as exc:
        return f"git_diff: {exc}"
    try:
        r = subprocess.run(
            ["git", "diff", ref, "--"],
            capture_output=True, text=True, check=False, timeout=_TIMEOUT_GIT_S,
            cwd=_aktives_projekt_dir(),
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
    projekt = _PROJEKTNAME_KONTEXT.get()
    if not run_id.startswith(f"{projekt}-"):
        return "audit_query: run_id gehoert nicht zum aktiven Projekt"
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
            cwd=_aktives_projekt_dir(),
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return f"pytest_collect-Fehler: {exc}"
    return (r.stdout or r.stderr)[:20_000]


def _pytest_run(args: dict[str, Any]) -> str:
    """Fuehrt ausgewaehlte Projekt-Tests mit festem Timeout aus."""
    pfad = _resolved_safe(str(args.get("path", "")).strip())
    if pfad is None:
        return "Fehler: Testpfad fehlt oder liegt ausserhalb des Projekts"
    if not pfad.exists():
        return f"Fehler: Testpfad nicht gefunden: {pfad}"
    test = str(args.get("test") or "").strip()
    if len(test) > 200:
        return "Fehler: Testauswahl ist zu lang"
    command = [sys.executable, "-m", "pytest", "-q", str(pfad)]
    if test:
        command.extend(["-k", test])
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
            cwd=_aktives_projekt_dir(),
        )
    except subprocess.TimeoutExpired:
        return "pytest_run: Timeout nach 120 Sekunden"
    except OSError as exc:
        return f"pytest_run-Fehler: {exc}"
    output = (result.stdout or "") + (result.stderr or "")
    return json.dumps({
        "exit_code": result.returncode,
        "befehl": command[1:],
        "ausgabe": output[-20_000:],
    }, ensure_ascii=False)


def _write_temp_test(args: dict[str, Any]) -> str:
    """Schreibt einen isolierten Debug-Test nur in .werkstatt/temp_tests."""
    content = args.get("content")
    if not isinstance(content, str) or not content.strip():
        return "Fehler: Testinhalt fehlt"
    if len(content.encode("utf-8")) > 50_000:
        return "Fehler: Testinhalt ueberschreitet 50 KB"
    root = _aktives_projekt_dir()
    target_dir = root / ".werkstatt" / "temp_tests"
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        resolved_dir = target_dir.resolve()
        resolved_dir.relative_to(root)
        path = resolved_dir / f"test_chat_debug_{uuid.uuid4().hex}.py"
        with path.open("x", encoding="utf-8") as stream:
            stream.write(content)
    except (OSError, ValueError, RuntimeError) as exc:
        return f"write_temp_test-Fehler: {exc}"
    relative = path.relative_to(root).as_posix()
    session_id = _CHAT_SESSION_ID_KONTEXT.get()
    if session_id:
        from werkstatt.chat_session import ChatSession

        ChatSession(_PROJEKTNAME_KONTEXT.get(), session_id).append(
            "debug_temp_test_created", {"path": relative},
        )
    return json.dumps({
        "zustand": "created",
        "path": relative,
        "hinweis": "Temporärer Test; Produktionsdateien wurden nicht verändert.",
    }, ensure_ascii=False)


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
    """STATUS.md + PROGRESS.md plus strukturierte OP-Zusammenfassung."""
    teile: list[str] = []
    try:
        from werkstatt.web.inspector import parse_ops
        ops = parse_ops(_aktives_projekt_dir())
        counts: dict[str, int] = {}
        for o in ops:
            counts[o["status"]] = counts.get(o["status"], 0) + 1
        status_str = ", ".join(f"{n} {st}" for st, n in sorted(counts.items()))
        teile.append(
            "## OP-Zusammenfassung (parse_ops, authoritative)\n"
            f"Total {len(ops)} offene OPs ({status_str}).\n"
        )
    except Exception as exc:  # noqa: BLE001
        teile.append(f"## OP-Zusammenfassung: Fehler ({exc})\n")

    for name in ("docs/STATUS.md", "docs/PROGRESS.md"):
        pfad = _aktives_projekt_dir() / name
        if pfad.is_file():
            try:
                limit = 200_000 if "STATUS" in name else 20_000
                text = pfad.read_text(encoding="utf-8", errors="replace")[:limit]
            except OSError:
                continue
            teile.append(f"## {name}\n{text}\n")

    return "\n".join(teile) if teile else "(STATUS.md/PROGRESS.md nicht gefunden)"

def _next_op(_args: dict[str, Any]) -> str:
    """Liefert begruendete STATUS-OP-Auswahl ohne einen Run zu starten."""
    status_path = _aktives_projekt_dir() / "docs" / "STATUS.md"
    if not status_path.is_file():
        return json.dumps({
            "zustand": "no_status",
            "detail": "docs/STATUS.md fehlt im aktiven Projekt.",
        }, ensure_ascii=False)
    try:
        status_text = status_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return json.dumps({
            "zustand": "error",
            "detail": f"STATUS.md kann nicht gelesen werden: {exc}",
        }, ensure_ascii=False)

    from werkstatt.web.op_selector import (
        load_accepted_adr_ids,
        parse_completed_op_ids,
        select_next_op,
    )

    progress_path = _aktives_projekt_dir() / "PROGRESS.md"
    try:
        progress_text = progress_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        progress_text = ""
    result = select_next_op(
        status_text,
        completed_ids=parse_completed_op_ids(progress_text, status_text),
        accepted_adrs=load_accepted_adr_ids(
            _aktives_projekt_dir() / "docs" / "adr",
        ),
    )
    excluded = result.pop("ausgeschlossen", [])
    result["quelle"] = "docs/STATUS.md"
    result["ausgeschlossen_anzahl"] = len(excluded)
    result["ausgeschlossen"] = excluded[:20]
    result["ausgeschlossen_gekürzt"] = len(excluded) > 20
    return json.dumps(result, ensure_ascii=False)


def _request_loop_action(args: dict[str, Any]) -> str:
    """Persistiert einen befristeten Vorschlag; fuehrt keine Aktion aus."""
    action = str(args.get("action", "")).strip().lower()
    if action not in {"start", "pause", "resume", "stop"}:
        return json.dumps({
            "zustand": "invalid",
            "detail": "Aktion muss start, pause, resume oder stop sein.",
        }, ensure_ascii=False)

    session_id = _CHAT_SESSION_ID_KONTEXT.get()
    if not session_id:
        return json.dumps({
            "zustand": "error",
            "detail": "Chat-Session fehlt; kein Vorschlag gespeichert.",
        }, ensure_ascii=False)

    arguments: dict[str, Any] = {}
    preview = ""
    selection_reason: Any = None
    if action == "start":
        op_id = str(args.get("op_id") or "").strip()
        task = str(args.get("aufgabe") or "").strip()
        if op_id and task:
            return json.dumps({
                "zustand": "needs_input",
                "detail": "Bitte entweder eine OP-ID oder einen konkreten Auftrag angeben.",
            }, ensure_ascii=False)
        if op_id:
            if not re.fullmatch(r"OP-\d+[a-z]?", op_id):
                return json.dumps({"zustand": "invalid", "detail": "OP-ID ungueltig."}, ensure_ascii=False)
            status_path = _aktives_projekt_dir() / "docs" / "STATUS.md"
            try:
                status_text = status_path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                return json.dumps({"zustand": "error", "detail": f"STATUS kann nicht gelesen werden: {exc}"}, ensure_ascii=False)
            from werkstatt.web.op_selector import (
                load_accepted_adr_ids,
                parse_completed_op_ids,
                select_next_op,
            )

            progress_path = _aktives_projekt_dir() / "PROGRESS.md"
            try:
                progress_text = progress_path.read_text(
                    encoding="utf-8", errors="replace",
                )
            except OSError:
                progress_text = ""
            selection = select_next_op(
                status_text,
                completed_ids=parse_completed_op_ids(progress_text, status_text),
                accepted_adrs=load_accepted_adr_ids(
                    _aktives_projekt_dir() / "docs" / "adr",
                ),
            )
            candidate = next(
                (
                    item for item in selection.get("kandidaten", [])
                    if item.get("id") == op_id.upper()
                ),
                None,
            )
            if candidate is None:
                excluded = next(
                    (
                        item for item in selection.get("ausgeschlossen", [])
                        if item.get("id") == op_id.upper()
                    ),
                    None,
                )
                reasons = excluded.get("gruende", []) if excluded else []
                return json.dumps({
                    "zustand": "needs_input",
                    "detail": (
                        f"{op_id} ist nicht startfaehig."
                        + (" " + "; ".join(reasons) if reasons else
                           " STATUS.md markiert die OP nicht eindeutig als offen.")
                    ),
                    "auswahl": selection,
                }, ensure_ascii=False)
            match = re.search(
                rf"^### {re.escape(op_id)}:.*?(?=^### OP-|\Z)",
                status_text,
                re.MULTILINE | re.DOTALL,
            )
            if not match:
                return json.dumps({"zustand": "needs_input", "detail": f"{op_id} wurde nicht in docs/STATUS.md gefunden."}, ensure_ascii=False)
            preview = match.group(0).strip()
            arguments["op_id"] = op_id
            selection_reason = (
                candidate.get("gruende")
                or f"{op_id} wurde vom Nutzer explizit ausgewaehlt."
            )
        elif task:
            arguments["aufgabe"] = task
            preview = task
        else:
            selection = json.loads(_next_op({}))
            if selection.get("zustand") != "selected":
                return json.dumps({"zustand": "needs_input", "auswahl": selection}, ensure_ascii=False)
            op_id = str(selection["auswahl"]["id"])
            preview = str(selection["aufgabe"])
            arguments["op_id"] = op_id
            selection_reason = (
                selection["auswahl"].get("gruende")
                or selection.get("begruendung")
                or "Vom OP-Selector als naechster startbarer Auftrag gewaehlt."
            )

    if action == "start" and selection_reason is None:
        selection_reason = {
            "kind": "direct_task",
            "summary": "Konkreter Auftrag wurde direkt im Chat vorgegeben.",
        }

    from datetime import UTC, datetime, timedelta
    proposal_id = uuid.uuid4().hex
    now = datetime.now(UTC)
    proposal = {
        "proposal_id": proposal_id,
        "action": action,
        "arguments": arguments,
        "summary": f"Loop starten: {arguments.get('op_id') or 'Auftrag'}" if action == "start" else f"Loop {action}",
        "task_preview": preview,
        "selection_reason": selection_reason,
        "project": _PROJEKTNAME_KONTEXT.get(),
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(minutes=15)).isoformat(),
    }
    from werkstatt.chat_session import ChatSession
    ChatSession(_PROJEKTNAME_KONTEXT.get(), session_id).append(
        "loop_action_proposed", proposal,
    )
    return json.dumps({"zustand": "proposal", **proposal}, ensure_ascii=False)


def _propose_debugger_fix(args: dict[str, Any]) -> str:
    """Speichert einen hashgebundenen Patch-Vorschlag; schreibt keine Dateien."""
    project = _PROJEKTNAME_KONTEXT.get()
    session_id = _CHAT_SESSION_ID_KONTEXT.get()
    run_id = str(args.get("run_id") or "").strip()
    if not session_id:
        return json.dumps({"zustand": "error", "detail": "Chat-Session fehlt."})
    if not run_id.startswith(project + "-"):
        return json.dumps({
            "zustand": "invalid",
            "detail": "run_id gehoert nicht zum aktiven Projekt.",
        })
    from werkstatt.debugger_handoff import (
        DebuggerFixError,
        create_debugger_fix,
    )
    from werkstatt.event_store import EventStore
    from werkstatt.projection import Projector

    try:
        Projector().tail()
        event_store = EventStore()
    except (OSError, RuntimeError, ValueError) as exc:
        return json.dumps({"zustand": "error", "detail": f"Run-Audit konnte nicht aktualisiert werden: {type(exc).__name__}"}, ensure_ascii=False)
    evidence_kinds = (
        "loop_failed", "loop_verify_failed", "loop_task_failed",
        "loop_gate_failed", "loop_gate_timeout", "loop_reviewer_rejected",
        "gate_open", "gate_expired", "loop_gate_eof", "loop_human_gate_eof",
    )
    try:
        has_failure_evidence = any(
            event_store.query(
                run_id, project=project, kind=kind, limit=1,
            )
            for kind in evidence_kinds
        )
    except (OSError, RuntimeError, ValueError) as exc:
        return json.dumps({"zustand": "error", "detail": f"Run-Audit konnte nicht gelesen werden: {type(exc).__name__}"}, ensure_ascii=False)
    if not has_failure_evidence:
        return json.dumps({"zustand": "needs_input", "detail": "Fuer diesen Projekt-Run liegt kein Fehler- oder Gate-Nachweis vor."}, ensure_ascii=False)
    try:
        head = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=_aktives_projekt_dir(),
            capture_output=True,
            text=True,
            check=False,
            timeout=_TIMEOUT_GIT_S,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return json.dumps({
            "zustand": "error",
            "detail": f"Projekt-HEAD konnte nicht gelesen werden: {type(exc).__name__}",
        }, ensure_ascii=False)
    if head.returncode != 0:
        return json.dumps({
            "zustand": "error",
            "detail": "Aktives Projekt hat keinen lesbaren Git-HEAD.",
        }, ensure_ascii=False)
    raw_files = args.get("betroffene_dateien")
    if not isinstance(raw_files, list):
        return json.dumps({"zustand": "invalid", "detail": "betroffene_dateien muss eine Liste sein."}, ensure_ascii=False)
    files: list[str] = []
    for item in raw_files:
        if not isinstance(item, str):
            return json.dumps({"zustand": "invalid", "detail": "Dateipfade muessen Text sein."}, ensure_ascii=False)
        files.append(item)
    raw_confidence = args.get("confidence")
    if not isinstance(raw_confidence, (int, float)) or isinstance(raw_confidence, bool):
        return json.dumps({"zustand": "invalid", "detail": "confidence muss eine Zahl sein."}, ensure_ascii=False)
    try:
        fix = create_debugger_fix(
            signatur=str(args.get("signatur") or ""),
            ursache_tag=str(args.get("ursache_tag") or ""),
            diff=str(args.get("diff") or ""),
            betroffene_dateien=files,
            confidence=float(raw_confidence),
            project=project,
            run_id=run_id,
            base_head=head.stdout.strip(),
        )
    except (DebuggerFixError, TypeError) as exc:
        return json.dumps({
            "zustand": "invalid",
            "detail": str(exc),
        }, ensure_ascii=False)
    proposal_id = uuid.uuid4().hex
    from datetime import UTC, datetime, timedelta
    now = datetime.now(UTC)
    proposal = {
        "proposal_id": proposal_id,
        "action": "start",
        "arguments": {"debugger_fix": fix.to_payload()},
        "summary": f"Debugger-Fix freigeben: {fix.signatur}",
        "task_preview": (
            f"{fix.ursache_tag} · {len(fix.betroffene_dateien)} Datei(en) · "
            f"Confidence {fix.confidence:.0%}"
        ),
        "project": project,
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(minutes=15)).isoformat(),
    }
    from werkstatt.chat_session import ChatSession
    ChatSession(project, session_id).append("loop_action_proposed", proposal)
    return json.dumps({"zustand": "proposal", **proposal}, ensure_ascii=False)


CHAT_TOOLS: dict[str, dict[str, Any]] = {
    "read_file": {
        "description": (
            "Liest Datei-Inhalt mit 0-basierten Zeichen-Offsets (start/end, "
            "keine Zeilennummern; max 50 KB). Gekürzte Ausgaben nennen "
            "den nächsten start-Offset zur Fortsetzung."
        ),
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
    "pytest_run": {
        "description": "Fuehrt einen Projekt-Testpfad aus (nur Debug-Modus, max. 120 Sekunden).",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "test": {"type": "string"},
            },
            "required": ["path"],
        },
        "fn": _pytest_run,
        "mode": "debugger",
    },
    "write_temp_test": {
        "description": "Schreibt einen isolierten Test nach .werkstatt/temp_tests (nur Debug-Modus); niemals Produktionscode oder tests/.",
        "parameters": {
            "type": "object",
            "properties": {"content": {"type": "string"}},
            "required": ["content"],
        },
        "fn": _write_temp_test,
        "mode": "debugger",
    },
    "propose_debugger_fix": {
        "description": (
            "Legt im Debug-Modus einen hashgebundenen Patch-Vorschlag fuer "
            "einen belegten Run an. Schreibt keinen Produktionscode; die UI "
            "zeigt den exakten Diff und verlangt eine ausdrueckliche Freigabe."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "signatur": {"type": "string"},
                "ursache_tag": {"type": "string"},
                "diff": {"type": "string"},
                "betroffene_dateien": {
                    "type": "array", "items": {"type": "string"},
                },
                "confidence": {"type": "number"},
                "run_id": {"type": "string"},
            },
            "required": [
                "signatur", "ursache_tag", "diff",
                "betroffene_dateien", "confidence", "run_id",
            ],
        },
        "fn": _propose_debugger_fix,
        "mode": "debugger",
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
    "request_loop_action": {
        "description": (
            "Legt einen befristeten Vorschlag zum Starten, Pausieren, "
            "Fortsetzen oder Stoppen an. Fuehrt nichts aus; die UI verlangt "
            "anschliessend eine ausdrueckliche Bestaetigung."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["start", "pause", "resume", "stop"],
                },
                "op_id": {"type": "string"},
                "aufgabe": {"type": "string"},
            },
            "required": ["action"],
        },
        "fn": _request_loop_action,
        "mode": "read",
    },
    "next_op": {
        "description": (
            "Analysiert docs/STATUS.md des aktiven Projekts und liefert "
            "startfaehige OP-Kandidaten, Abhaengigkeiten und Ausschlussgruende. "
            "Startet oder aendert nichts."
        ),
        "parameters": {"type": "object", "properties": {}},
        "fn": _next_op,
        "mode": "read",
    },
}


def _mode_erlaubt(spec: dict[str, Any], mode: str) -> bool:
    want = spec.get("mode", "read")
    if want == "read":
        return True
    if want == "debugger":
        return mode == "debugger"
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
    *,
    project_dir: Path | str | None = None,
    project_name: str | None = None,
    session_id: str | None = None,
) -> str:
    src = tools if tools is not None else CHAT_TOOLS
    spec = src.get(name)
    if spec is None:
        return f"Fehler: Tool '{name}' nicht in Registry (read-only)"
    if not _mode_erlaubt(spec, mode):
        erforderlicher_modus = spec.get("mode", "read")
        return (
            f"Fehler: Tool '{name}' erfordert mode='{erforderlicher_modus}' "
            f"(aktuell '{mode}')"
        )
    fn: Callable[[dict[str, Any]], str] = spec["fn"]
    root = (
        Path(project_dir).expanduser().resolve()
        if project_dir is not None
        else _PROJEKT_DIR
    )
    if not root.is_dir():
        return f"Fehler: Aktives Projektverzeichnis fehlt: {root}"
    root_token = _PROJEKT_DIR_KONTEXT.set(root)
    name_token = _PROJEKTNAME_KONTEXT.set(project_name or "werkstatt")
    session_token = _CHAT_SESSION_ID_KONTEXT.set(session_id or "")
    try:
        return str(fn(args))
    except Exception as exc:
        return f"Tool-Fehler ({name}): {type(exc).__name__}: {exc}"
    finally:
        _CHAT_SESSION_ID_KONTEXT.reset(session_token)
        _PROJEKTNAME_KONTEXT.reset(name_token)
        _PROJEKT_DIR_KONTEXT.reset(root_token)
