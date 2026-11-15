"""Ask the originating project Chat for one bounded Builder recovery task."""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from typing import Any

_ALLOWED_CHAT_TOOLS = frozenset({
    "read_file", "grep", "git_log", "git_diff", "audit_query",
    "loop_status", "pytest_collect", "diagnose", "read_status", "next_op",
})
_SESSION_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
REFLECTION_EVIDENCE_MAX_CHARS = 18_000
REFLECTION_PROMPT_MAX_CHARS = 24_000


def originating_chat_session_id(run_record: Any) -> str | None:
    """Return only a validated Chat origin from the durable start context."""
    if not isinstance(run_record, dict):
        return None
    context = run_record.get("start_context")
    if not isinstance(context, dict) or context.get("origin") != "chat":
        return None
    session_id = context.get("origin_session_id")
    return session_id if isinstance(session_id, str) and _SESSION_ID.fullmatch(
        session_id,
    ) else None


def _scoped_files(task: dict[str, Any]) -> list[str]:
    if task.get("action", "update") not in {"create", "update"}:
        return []
    files = task.get("task_files")
    if not isinstance(files, list):
        return []
    result: list[str] = []
    for item in files:
        if not isinstance(item, str) or not item.strip():
            return []
        path = item.replace("\\", "/")
        if path.startswith("/") or re.match(r"^[A-Za-z]:", path):
            return []
        if any(part in {"", ".", ".."} for part in path.split("/")):
            return []
        if path not in result:
            result.append(path)
    return result


def _compact_items(value: Any, keys: tuple[str, ...]) -> list[Any]:
    if not isinstance(value, list):
        return []
    compacted: list[Any] = []
    for item in value:
        if isinstance(item, str):
            compacted.append(item)
        elif isinstance(item, dict):
            compacted.append({
                key: str(item[key])
                for key in keys
                if isinstance(item.get(key), (str, int, float, bool))
            })
    return compacted


def _readable_evidence(state: Any) -> dict[str, Any]:
    """Pack full required recovery evidence and whole optional sections."""
    task = state.aktuelle_task if isinstance(state.aktuelle_task, dict) else {}
    required = {
        "run_id": str(getattr(state, "run_id", "")),
        "phase": str(getattr(state, "phase_id", "") or "reflection"),
        "goal": str(getattr(state, "aufgabe", "")),
        "task": {
            "id": str(task.get("id", "")),
            "name": str(task.get("name", "")),
            "description": str(task.get("description", "")),
            "authorized_files": _scoped_files(task),
            "acceptance_criteria": _compact_items(
                task.get("acceptance_criteria")
                or task.get("akzeptanzkriterien")
                or getattr(state, "akzeptanzkriterien", []),
                ("id", "criterion_id", "text", "description", "status"),
            ),
        },
        "planned_tests": _compact_items(
            getattr(state, "tests", []),
            ("id", "name", "file", "command", "description", "criterion_id"),
        ),
        "verify_errors": [
            str(item)
            for item in (getattr(state, "last_verify_errors", None) or [])
            if isinstance(item, (str, int, float))
        ],
        "reviewer_bugs": [
            {
                key: str(item.get(key, ""))
                for key in ("file", "line", "severity", "description")
                if item.get(key) is not None
            }
            for item in (getattr(state, "reviewer_bugs", None) or [])
            if isinstance(item, dict)
        ],
    }
    optional = {
        "architect_constraints": str(
            getattr(state, "architect_prosa", "") or ""
        ),
        "reflection_history": [
            {
                key: item.get(key)
                for key in ("runde", "task_id", "patches_applied")
                if isinstance(item.get(key), (int, str))
            } | {
                "verify_errors": [
                    str(error)
                    for error in item.get("verify_errors", [])
                    if isinstance(error, str)
                ],
            }
            for item in (getattr(state, "reflection_history", None) or [])
            if isinstance(item, dict)
        ],
    }
    manifests = {
        key: {
            "chars": len(encoded := json.dumps(
                value, ensure_ascii=False, sort_keys=True, default=str,
            )),
            "sha256": hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
        }
        for key, value in {**required, **optional}.items()
    }
    required_chars = len(json.dumps(
        required, ensure_ascii=False, sort_keys=True, default=str,
    ))
    if required_chars > REFLECTION_EVIDENCE_MAX_CHARS:
        return {
            "context_status": "blocked_required_context_over_budget",
            "required_chars": required_chars,
            "max_chars": REFLECTION_EVIDENCE_MAX_CHARS,
            "sources": manifests,
            "omitted_optional": [],
        }

    evidence: dict[str, Any] = dict(required)
    omitted: list[str] = []
    for name, value in optional.items():
        candidate = {**evidence, name: value}
        size = len(json.dumps(
            candidate, ensure_ascii=False, sort_keys=True, default=str,
        ))
        if size <= REFLECTION_EVIDENCE_MAX_CHARS:
            evidence[name] = value
        else:
            omitted.append(name)
    evidence["context_status"] = "complete_required"
    context_budget: dict[str, Any] = {
        "max_chars": REFLECTION_EVIDENCE_MAX_CHARS,
        "sources": manifests,
        "omitted_optional": omitted,
        "omissions_are_not_negative_evidence": True,
    }
    evidence["context_budget"] = context_budget
    context_budget["used_chars"] = len(json.dumps(
        evidence, ensure_ascii=False, sort_keys=True, default=str,
    ))
    return evidence


def _parse_task(answer: str, allowed_files: list[str]) -> dict[str, Any] | None:
    start = answer.find("{")
    end = answer.rfind("}") + 1
    if start < 0 or end <= start:
        return None
    try:
        payload = json.loads(answer[start:end])
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict) or payload.get("decision") != "task":
        return None
    proposed = payload.get("task")
    if not isinstance(proposed, dict):
        return None
    name = proposed.get("name")
    description = proposed.get("description")
    files = proposed.get("task_files")
    if (
        not isinstance(name, str) or not name.strip() or len(name) > 240
        or not isinstance(description, str) or not description.strip()
        or len(description) > 3000
        or not isinstance(files, list) or not files
        or any(not isinstance(item, str) for item in files)
    ):
        return None
    normalized = [item.replace("\\", "/") for item in files]
    if len(set(normalized)) != len(normalized):
        return None
    if any(item not in allowed_files for item in normalized):
        return None
    return {
        "name": name.strip(),
        "description": description.strip(),
        "task_files": normalized,
    }


def ask_project_chat_for_builder_task(state: Any) -> dict[str, Any] | None:
    """Ask the run's originating Chat for a single in-scope repair task.

    The chat turn runs in a disposable snapshot with read-only project tools.
    Only a strict task proposal over already-authorized files is returned.
    """
    state.reflection_chat_error = ""
    project = str(getattr(state, "project_name", ""))
    session_id = getattr(state, "chat_origin_session_id", None)
    task = getattr(state, "aktuelle_task", None)
    if (
        not project or not isinstance(session_id, str)
        or not _SESSION_ID.fullmatch(session_id)
        or not isinstance(task, dict)
    ):
        return None
    allowed_files = _scoped_files(task)
    if not allowed_files:
        return None

    evidence = _readable_evidence(state)
    if evidence.get("context_status") != "complete_required":
        state.reflection_chat_error = "required_context_over_budget"
        return None
    evidence_json = json.dumps(evidence, ensure_ascii=False, sort_keys=True)
    evidence_hash = hashlib.sha256(evidence_json.encode("utf-8")).hexdigest()
    run_id = str(getattr(state, "run_id", "") or "run")
    job_id = "reflection-" + hashlib.sha256(
        f"{run_id}:{task.get('id')}:{evidence_hash}".encode(),
    ).hexdigest()[:32]
    prompt = (
        "Der Werkstatt-Loop ist bei der Reparatur des aktuellen freigegebenen "
        "Tasks an einem Stillstandspunkt angekommen. Analysiere die "
        "angegebenen Belege und lies bei Bedarf das Repo mit deinen "
        "Projektwerkzeugen. Formuliere genau eine verbesserte Aufgabe fuer "
        "den Builder oder lehne mit decision=\"cannot_solve\" ab. "
        "Aendere weder Akzeptanzkriterien noch den Auftragsscope. "
        "task_files muessen eine nichtleere Teilmenge der authorized_files "
        "bleiben. Behaupte keine Tests oder Ursachen ohne Beleg. Gib nur "
        "dieses JSON zurueck: {\"decision\":\"task\",\"task\":{"
        "\"name\":\"...\",\"description\":\"konkreter naechster "
        "Builder-Schritt mit Fehlerursache und Verify-Hinweis\","
        "\"task_files\":[\"...\"]}}. Bei fehlender belastbarer "
        "Reparaturaufgabe: {\"decision\":\"cannot_solve\","
        "\"reason\":\"...\"}. Fehlende optionale Belege oder ihre Hash-/"
        "Groessenmetadaten sind keine Negativbelege. Lies benoetigte, aber "
        "ausgelassene Informationen mit den Projektwerkzeugen gezielt nach; "
        "wenn das nicht belastbar gelingt, lehne ab.\n\nBELEGE:\n"
        + evidence_json
    )
    if len(prompt) > REFLECTION_PROMPT_MAX_CHARS:
        state.reflection_chat_error = "prompt_over_budget"
        return None

    parent = None
    worker = None
    parsed = None
    try:
        from werkstatt.chat_session import ChatSession

        parent = ChatSession(project, session_id)
        prior_turn = parent.get_job_turn(job_id)
        if prior_turn is not None:
            return _parse_task(prior_turn["assistant_text"], allowed_files)
        # A prior process may have died with only a partial branch snapshot.
        # Rebuild it from the same immutable parent transcript before retrying.
        parent.delete_snapshot(job_id)
        worker = parent.snapshot_to(job_id)
        from werkstatt.chat_agent import chat_loop
        from werkstatt.chat_tools import CHAT_TOOLS

        tools = {
            name: CHAT_TOOLS[name]
            for name in _ALLOWED_CHAT_TOOLS
            if name in CHAT_TOOLS
        }

        def count_chat_call() -> None:
            from werkstatt.agent import _enforce_run_budget

            if _enforce_run_budget(state):
                raise RuntimeError("Werkstatt-LLM-Budget vor Chat-Aufruf erreicht")
            state.llm_calls += 1

        answer = chat_loop(
            worker,
            prompt,
            tools=tools,
            mode="reflection",
            max_rounds=3,
            project_dir=state.project_dir,
            origin_session_id=session_id,
            on_llm_call=count_chat_call,
        )
        parsed = _parse_task(answer, allowed_files)
        parent.append_job_turn(job_id, prompt, answer)
    except Exception as exc:  # noqa: BLE001 — Chat/API failures fail closed.
        state.reflection_chat_error = type(exc).__name__
        parsed = None
    if parent is not None and worker is not None:
        try:
            parent.delete_snapshot(job_id)
        except (OSError, RuntimeError, ValueError, sqlite3.Error) as exc:
            state.reflection_chat_error = type(exc).__name__
            parsed = None
    return parsed
