"""Ask the originating project Chat for one bounded Builder recovery task."""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
from pathlib import Path
from typing import Any

_ALLOWED_CHAT_TOOLS = frozenset({
    "read_file", "grep", "git_log", "git_diff", "audit_query",
    "loop_status", "pytest_collect", "diagnose", "read_status", "next_op",
})
_SESSION_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
REFLECTION_EVIDENCE_MAX_CHARS = 18_000
REFLECTION_PROMPT_MAX_CHARS = 24_000
REFLECTION_CHAT_MAX_CALLS = 3
REFLECTION_CHAT_MAX_ELAPSED_S = 90
REFLECTION_CHAT_BUILDER_MAX_CALLS = 1
REFLECTION_CHAT_REVIEWER_MAX_CALLS = 1
REFLECTION_CHAT_BUILDER_MAX_ELAPSED_S = 90


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
        return ([{"_context_notice": "source_not_a_list"}]
                if value is not None else [{"_context_notice": "source_missing"}])
    compacted: list[Any] = []
    omitted_items = 0
    omitted_fields = 0
    for item in value:
        if isinstance(item, str):
            compacted.append(item)
        elif isinstance(item, dict):
            represented = {
                key: str(item[key])
                for key in keys
                if isinstance(item.get(key), (str, int, float, bool))
            }
            omitted_fields += sum(
                1 for key, field_value in item.items()
                if key not in keys
                or not isinstance(field_value, (str, int, float, bool))
            )
            if represented:
                compacted.append(represented)
            else:
                omitted_items += 1
        else:
            omitted_items += 1
    if omitted_items or omitted_fields:
        compacted.append({
            "_context_notice": "representation_incomplete",
            "omitted_item_count": omitted_items,
            "omitted_field_count": omitted_fields,
            "instruction": (
                "These counts are not evidence of absence. Read relevant "
                "project sources with the available tools; if the missing "
                "details cannot be verified, do not propose a repair."
            ),
        })
    return compacted


def _readable_evidence(
    state: Any, *, failure_context: str | None = None,
) -> dict[str, Any]:
    """Pack full required recovery evidence and whole optional sections."""
    task = state.aktuelle_task if isinstance(state.aktuelle_task, dict) else {}
    required = {
        "run_id": str(getattr(state, "run_id", "")),
        "phase": str(getattr(state, "phase_id", "") or "reflection"),
        "goal": str(getattr(state, "aufgabe", "")),
        "recovery_failure": {
            "reflection_error_context": str(failure_context or ""),
            "builder_failure_reason": str(
                getattr(state, "builder_failure_reason", "") or ""
            ),
        },
        "task": {
            "id": str(task.get("id", "")),
            "name": str(task.get("name", "")),
            "description": str(task.get("description", "")),
            "authorized_files": _scoped_files(task),
            "acceptance_criteria": _compact_items(
                task.get("acceptance_criteria")
                or task.get("akzeptanzkriterien")
            or getattr(state, "akzeptanzkriterien", None),
                ("id", "criterion_id", "text", "description", "status"),
            ),
        },
        "planned_tests": _compact_items(
            getattr(state, "tests", None),
            ("id", "name", "file", "command", "description", "criterion_id"),
        ),
        "verify_errors": _compact_items(
            getattr(state, "last_verify_errors", None), ("error",),
        ),
        "reviewer_bugs": _compact_items(
            getattr(state, "reviewer_bugs", None),
            ("file", "line", "severity", "description"),
        ),
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
    context_budget: dict[str, Any] = {
        "max_chars": REFLECTION_EVIDENCE_MAX_CHARS,
        "sources": manifests,
        "omitted_optional": omitted,
        "omissions_are_not_negative_evidence": True,
        "used_chars": 0,
    }
    evidence["context_status"] = "complete_required"
    evidence["context_budget"] = context_budget
    for name, value in optional.items():
        candidate = {**evidence, name: value}
        candidate_budget = dict(context_budget)
        candidate_budget["omitted_optional"] = list(omitted)
        candidate["context_budget"] = candidate_budget
        size = len(json.dumps(
            candidate, ensure_ascii=False, sort_keys=True, default=str,
        ))
        if size <= REFLECTION_EVIDENCE_MAX_CHARS:
            evidence[name] = value
        else:
            omitted.append(name)

    context_budget["omitted_optional"] = omitted

    def measure_complete_evidence() -> int:
        """Measure the actual serialized object, including its own count."""
        for _ in range(4):
            measured = len(json.dumps(
                evidence, ensure_ascii=False, sort_keys=True, default=str,
            ))
            if context_budget["used_chars"] == measured:
                return measured
            context_budget["used_chars"] = measured
        return len(json.dumps(
            evidence, ensure_ascii=False, sort_keys=True, default=str,
        ))

    used_chars = measure_complete_evidence()
    if used_chars > REFLECTION_EVIDENCE_MAX_CHARS:
        # Budget accounting overhead can push a just-fitting optional section
        # over the cap. Remove optional sections whole, least recent/priority
        # last, and keep the omission explicit in the manifest.
        for name in reversed(tuple(optional)):
            if name not in evidence:
                continue
            del evidence[name]
            omitted.append(name)
            context_budget["omitted_optional"] = omitted
            used_chars = measure_complete_evidence()
            if used_chars <= REFLECTION_EVIDENCE_MAX_CHARS:
                break
    if used_chars > REFLECTION_EVIDENCE_MAX_CHARS:
        return {
            "context_status": "blocked_required_context_over_budget",
            "required_chars": used_chars,
            "max_chars": REFLECTION_EVIDENCE_MAX_CHARS,
            "sources": manifests,
            "omitted_optional": omitted,
        }
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
        "source_evidence": proposed.get("source_evidence"),
    }


def _parse_refusal_reason(answer: str) -> str:
    """Extract a short refusal explanation for audit/display, never execution."""
    start = answer.find("{")
    end = answer.rfind("}") + 1
    if start < 0 or end <= start:
        return ""
    try:
        payload = json.loads(answer[start:end])
    except json.JSONDecodeError:
        return ""
    if not isinstance(payload, dict) or payload.get("decision") != "cannot_solve":
        return ""
    reason = payload.get("reason")
    if not isinstance(reason, str):
        return ""
    return " ".join(re.sub(r"[\x00-\x1f\x7f]", " ", reason).split())[:300]


def _verify_source_evidence(
    task: dict[str, Any],
    allowed_files: list[str],
    project_dir: Any,
) -> list[dict[str, Any]] | None:
    """Bind the recovery diagnosis to exact excerpts from current source.

    Offsets follow ``read_file``'s zero-based character offsets. The worker
    re-reads each allowed file and verifies the quote before the Builder gets
    the proposal, then attaches a current whole-file hash.
    """
    raw = task.get("source_evidence")
    if not isinstance(raw, list) or not 1 <= len(raw) <= 4:
        return None
    root = Path(project_dir).resolve()
    verified: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            return None
        path = item.get("file")
        start = item.get("start")
        end = item.get("end")
        quote = item.get("quote")
        if (
            not isinstance(path, str)
            or path.replace("\\", "/") not in allowed_files
            or not isinstance(start, int) or isinstance(start, bool)
            or not isinstance(end, int) or isinstance(end, bool)
            or start < 0 or end <= start
            or not isinstance(quote, str) or not quote or len(quote) > 600
        ):
            return None
        normalized = path.replace("\\", "/")
        try:
            resolved = (root / normalized).resolve(strict=True)
            resolved.relative_to(root)
            if not resolved.is_file() or resolved.stat().st_size > 2_000_000:
                return None
            source_bytes = resolved.read_bytes()
            source = source_bytes.decode("utf-8")
        except (OSError, UnicodeError, RuntimeError, ValueError):
            return None
        if end > len(source) or source[start:end] != quote:
            return None
        verified.append({
            "file": normalized,
            "start": start,
            "end": end,
            "quote": quote,
            "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        })
    return verified


def _build_recovery_prompt(evidence: dict[str, Any]) -> tuple[str, str]:
    """Serialize the exact evidence and return the complete recovery prompt."""
    evidence_json = json.dumps(evidence, ensure_ascii=False, sort_keys=True)
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
        "\"task_files\":[\"...\"],\"source_evidence\":[{"
        "\"file\":\"...\",\"start\":0,\"end\":24,"
        "\"quote\":\"exakter read_file-Auszug\"}]}}. Jeder Beleg muss "
        "eine tatsaechlich gelesene Fundstelle in task_files sein; start/end "
        "sind 0-basierte Zeichen-Offsets in der vollstaendigen Datei. Bei "
        "fehlender belastbarer "
        "Reparaturaufgabe: {\"decision\":\"cannot_solve\","
        "\"reason\":\"...\"}. Fehlende optionale Belege oder ihre Hash-/"
        "Groessenmetadaten sind keine Negativbelege. Kontextmarker zu nicht "
        "darstellbaren Pflichtdaten sind ebenfalls keine Negativbelege. Lies "
        "benoetigte, aber "
        "ausgelassene Informationen mit den Projektwerkzeugen gezielt nach; "
        "wenn das nicht belastbar gelingt, lehne ab.\n\nBELEGE:\n"
        + evidence_json
    )
    return prompt, evidence_json


def _claim_recovery_chat_call(state: Any) -> int:
    """Durably reserve one of the run's bounded Reflection-Chat calls."""
    project = getattr(state, "project_name", None)
    run_id = getattr(state, "run_id", None)
    if not isinstance(project, str) or not project.strip() or not isinstance(
        run_id, str,
    ) or not run_id.strip():
        raise RuntimeError("reflection_chat_run_identity_missing")

    from werkstatt.event_store import EventStore

    store = EventStore()
    for _ in range(5):
        record = store.get_run_record(project, run_id)
        if record is None:
            raise RuntimeError("reflection_chat_run_checkpoint_missing")
        checkpoint = record.get("checkpoint")
        if not isinstance(checkpoint, dict):
            raise TypeError("reflection_chat_checkpoint_invalid")
        used = checkpoint.get("reflection_chat_recovery_calls", 0)
        if (
            isinstance(used, bool) or not isinstance(used, int) or used < 0
        ):
            raise RuntimeError("reflection_chat_recovery_counter_invalid")
        if used >= REFLECTION_CHAT_MAX_CALLS:
            raise RuntimeError("reflection_chat_recovery_budget_exhausted")
        updated = dict(checkpoint)
        updated["reflection_chat_recovery_calls"] = used + 1
        try:
            store.update_run_checkpoint(
                project,
                run_id,
                updated,
                expected_version=record["checkpoint_version"],
            )
        except RuntimeError:
            continue
        state.reflection_chat_calls = used + 1
        return used + 1
    raise RuntimeError("reflection_chat_checkpoint_conflict")


def claim_recovery_worker_call(state: Any, role: str) -> int:
    """Durably allow one Builder and then one Reviewer recovery call.

    Both calls share the same expiring reserve. Reviewer cannot run until the
    reserved Builder call has been claimed, and neither role can claim a
    second provider request after resume.
    """
    from datetime import UTC, datetime, timedelta

    limits = {
        "builder": REFLECTION_CHAT_BUILDER_MAX_CALLS,
        "reviewer": REFLECTION_CHAT_REVIEWER_MAX_CALLS,
    }
    checkpoint_keys = {
        "builder": "reflection_chat_builder_calls",
        "reviewer": "reflection_chat_reviewer_calls",
    }
    if role not in limits:
        raise RuntimeError("reflection_recovery_role_invalid")

    project = getattr(state, "project_name", None)
    run_id = getattr(state, "run_id", None)
    if not isinstance(project, str) or not project.strip() or not isinstance(
        run_id, str,
    ) or not run_id.strip():
        raise RuntimeError("reflection_recovery_run_identity_missing")

    from werkstatt.event_store import EventStore

    now = datetime.now(UTC)
    store = EventStore()
    for _ in range(5):
        record = store.get_run_record(project, run_id)
        if record is None:
            raise RuntimeError("reflection_recovery_checkpoint_missing")
        checkpoint = record.get("checkpoint")
        if not isinstance(checkpoint, dict):
            raise TypeError("reflection_recovery_checkpoint_invalid")
        checkpoint_key = checkpoint_keys[role]
        used = checkpoint.get(checkpoint_key, 0)
        if isinstance(used, bool) or not isinstance(used, int) or used < 0:
            raise RuntimeError("reflection_recovery_counter_invalid")
        if used >= limits[role]:
            raise RuntimeError(f"reflection_{role}_reserve_exhausted")
        if role == "reviewer":
            builder_calls = checkpoint.get("reflection_chat_builder_calls", 0)
            if (
                isinstance(builder_calls, bool)
                or not isinstance(builder_calls, int)
                or builder_calls < 1
            ):
                raise RuntimeError("reflection_reviewer_before_builder")
        expiry = checkpoint.get("reflection_chat_builder_expires_at")
        if expiry is None:
            expiry = (now + timedelta(
                seconds=REFLECTION_CHAT_BUILDER_MAX_ELAPSED_S,
            )).isoformat()
        if not isinstance(expiry, str):
            raise TypeError("reflection_recovery_expiry_invalid")
        try:
            expires_at = datetime.fromisoformat(expiry)
        except ValueError as exc:
            raise RuntimeError("reflection_recovery_expiry_invalid") from exc
        if expires_at.tzinfo is None or now >= expires_at:
            raise RuntimeError("reflection_recovery_reserve_expired")
        updated = dict(checkpoint)
        updated[checkpoint_key] = used + 1
        updated["reflection_chat_builder_expires_at"] = expiry
        try:
            store.update_run_checkpoint(
                project,
                run_id,
                updated,
                expected_version=record["checkpoint_version"],
            )
        except RuntimeError:
            continue
        if role == "builder":
            state.reflection_chat_builder_calls = used + 1
        else:
            state.reflection_chat_reviewer_calls = used + 1
        state.reflection_chat_builder_deadline_monotonic = (
            time.monotonic() + (expires_at - now).total_seconds()
        )
        return used + 1
    raise RuntimeError("reflection_recovery_checkpoint_conflict")


def claim_recovery_builder_call(state: Any) -> int:
    """Compatibility wrapper for the single scoped Builder call."""
    return claim_recovery_worker_call(state, "builder")


def claim_recovery_reviewer_call(state: Any) -> int:
    """Claim the one scoped independent review after the Builder attempt."""
    return claim_recovery_worker_call(state, "reviewer")


def ask_project_chat_for_builder_task(
    state: Any, *, failure_context: str | None = None,
) -> dict[str, Any] | None:
    """Ask the run's originating Chat for a single in-scope repair task.

    The chat turn runs in a disposable snapshot with read-only project tools.
    Only a strict task proposal over already-authorized files is returned.
    """
    state.reflection_chat_error = ""
    state.reflection_chat_refusal_reason = ""
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

    evidence = _readable_evidence(state, failure_context=failure_context)
    if evidence.get("context_status") != "complete_required":
        state.reflection_chat_error = "required_context_over_budget"
        return None
    prompt, evidence_json = _build_recovery_prompt(evidence)
    evidence_hash = hashlib.sha256(evidence_json.encode("utf-8")).hexdigest()
    run_id = str(getattr(state, "run_id", "") or "run")
    if len(prompt) > REFLECTION_PROMPT_MAX_CHARS:
        state.reflection_chat_error = "prompt_over_budget"
        return None
    evidence_prompt_start = len(prompt) - len(evidence_json)
    if prompt[evidence_prompt_start:] != evidence_json:
        state.reflection_chat_error = "evidence_prompt_span_mismatch"
        return None
    prompt_sha256 = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    job_id = "reflection-" + hashlib.sha256(
        f"{run_id}:{task.get('id')}:{prompt_sha256}".encode(),
    ).hexdigest()[:32]

    parent = None
    worker = None
    parsed = None
    try:
        from werkstatt.chat_session import ChatSession

        parent = ChatSession(project, session_id)
        prior_turn = parent.get_job_turn(job_id)
        if prior_turn is not None:
            if prior_turn.get("user_text") != prompt:
                state.reflection_chat_error = "replay_prompt_mismatch"
                return None
            parsed_prior = _parse_task(
                prior_turn["assistant_text"], allowed_files,
            )
            if parsed_prior is None:
                refusal = _parse_refusal_reason(prior_turn["assistant_text"])
                if refusal:
                    state.reflection_chat_error = "chat_cannot_solve"
                    state.reflection_chat_refusal_reason = refusal
                return None
            verified_prior = _verify_source_evidence(
                parsed_prior, parsed_prior["task_files"], state.project_dir,
            )
            if verified_prior is None:
                state.reflection_chat_error = "source_evidence_unverified"
                return None
            parsed_prior["source_evidence"] = verified_prior
            return parsed_prior
        # A prior process may have died with only a partial branch snapshot.
        # Rebuild an empty, isolated branch before retrying: the recovery Chat
        # gets the explicit run evidence below, and can fetch additional
        # project facts through its read-only tools. Copying the user's recent
        # conversation here would mix unrelated turns into a role handoff.
        parent.delete_snapshot(job_id)
        worker = parent.snapshot_to(job_id, at_seq=0)
        from werkstatt.audit import audit
        from werkstatt.chat_agent import chat_loop
        from werkstatt.chat_tools import CHAT_TOOLS

        tools = {
            name: CHAT_TOOLS[name]
            for name in _ALLOWED_CHAT_TOOLS
            if name in CHAT_TOOLS
        }

        recovery_calls = 0

        def count_chat_call() -> None:
            nonlocal recovery_calls
            if recovery_calls >= REFLECTION_CHAT_MAX_CALLS:
                raise RuntimeError("reflection_chat_recovery_call_limit")
            # This evidence-bound consultation has a separate, small reserve:
            # it is specifically requested after ordinary run work stalls or
            # exhausts its budget. Count calls truthfully, but do not let the
            # exhausted work budget prevent the coordinator from asking Chat.
            recovery_calls += 1
            _claim_recovery_chat_call(state)
            state.llm_calls += 1

        def audit_chat_model_request(manifest: dict[str, Any]) -> None:
            written = audit(
                "loop_reflection_chat_model_request",
                {
                    **manifest,
                    "project": project,
                    "session_id": session_id,
                    "task_id": str(task.get("id", "")),
                    "job_id": job_id,
                    "origin_history_snapshot_seq": 0,
                    "evidence_sha256": evidence_hash,
                    "evidence_prompt_span": {
                        "unit": "unicode_codepoints",
                        "start": evidence_prompt_start,
                        "end": len(prompt),
                        "sha256": evidence_hash,
                    },
                    "chat_prompt_chars": len(prompt),
                    "chat_prompt_sha256": prompt_sha256,
                },
                state.project_dir,
                project,
                run_id=run_id,
            )
            if not written:
                raise RuntimeError("reflection_chat_model_request_audit_failed")

        answer = chat_loop(
            worker,
            prompt,
            tools=tools,
            mode="reflection",
            project_dir=state.project_dir,
            origin_session_id=session_id,
            on_llm_call=count_chat_call,
            on_model_request=audit_chat_model_request,
            max_rounds=REFLECTION_CHAT_MAX_CALLS - 1,
            max_elapsed_s=REFLECTION_CHAT_MAX_ELAPSED_S,
            allow_time_budget_finalize=False,
        )
        raw_task = _parse_task(answer, allowed_files)
        parsed = None
        if raw_task is None:
            refusal = _parse_refusal_reason(answer)
            if refusal:
                state.reflection_chat_error = "chat_cannot_solve"
                state.reflection_chat_refusal_reason = refusal
        if raw_task is not None:
            verified_evidence = _verify_source_evidence(
                raw_task, raw_task["task_files"], state.project_dir,
            )
            if verified_evidence is None:
                state.reflection_chat_error = "source_evidence_unverified"
            else:
                raw_task["source_evidence"] = verified_evidence
                parsed = raw_task
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
