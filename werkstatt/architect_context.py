"""Evidence and context helpers owned by the Architect role."""
from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path
from typing import Any

from werkstatt.state import RunState

ARCHITECT_EXECUTION_CONTEXT_MAX_CHARS = 12_000


def architect_input_fingerprint(
    state: RunState,
    goal: str,
    user_content: str,
    explorer_context: dict[str, Any] | None,
    scout_input_sha256: str | None,
) -> str | None:
    """Bind Architect replay to the rebuilt prompt and current source proofs."""
    from werkstatt.agent import DEEPSEEK_API_URL
    from werkstatt.architect import (
        _BUILDER_SCHNITTSTELLE,
        ARCHITECT_MAX_TOKENS,
        ARCHITECT_PROMPT_MAX_CHARS,
        _get_architect_model,
        _planner_system,
        _required_source_evidence_issue,
    )
    from werkstatt.planner_artifacts import value_sha256

    system_prompt = (
        _planner_system(goal, explorer_context, state)
        + "\n\n" + _BUILDER_SCHNITTSTELLE
    )
    source_manifest = getattr(
        state, "architect_scout_source_manifest", {},
    )
    source_issue = _required_source_evidence_issue(
        system_prompt,
        source_manifest,
        getattr(state, "architect_required_source_files", []),
    )
    if source_issue:
        return None
    scout_report = getattr(state, "scout_auftrag", None)
    architect_user_content = user_content
    if scout_report:
        execution_context = getattr(state, "architect_execution_context", "")
        if (
            not isinstance(execution_context, str)
            or len(execution_context) > ARCHITECT_EXECUTION_CONTEXT_MAX_CHARS
        ):
            return None
        architect_user_content = execution_context
    if len(system_prompt) + len(architect_user_content) > ARCHITECT_PROMPT_MAX_CHARS:
        return None
    return value_sha256({
        "context_builder": "architect_context_v1",
        "goal": goal,
        "system_prompt": system_prompt,
        "user_content": architect_user_content,
        "scout_report": scout_report,
        "upstream_scout_input_sha256": scout_input_sha256,
        "source_manifest": source_manifest,
        "project_docs_manifest": getattr(
            state, "architect_project_docs_manifest", {},
        ),
        "execution_context_manifest": getattr(
            state, "architect_execution_context_manifest", {},
        ),
        "model": _get_architect_model(),
        "thinking": getattr(state, "architect_reasoning_enabled", True),
        "endpoint": DEEPSEEK_API_URL,
        "temperature": 0.2,
        "max_tokens": ARCHITECT_MAX_TOKENS,
    })


def budget_architect_execution_context(
    sections: list[tuple[str, str]],
    *,
    max_chars: int = ARCHITECT_EXECUTION_CONTEXT_MAX_CHARS,
) -> tuple[str, dict[str, object]]:
    """Admit whole Architect evidence sections and report omissions."""
    normalized_input = [
        (title, content)
        for title, content in sections
        if isinstance(title, str) and isinstance(content, str) and content
    ]

    def priority(item: tuple[str, str]) -> int:
        title = item[0].casefold()
        if title.startswith("preflight-fehler"):
            return 0
        if title.startswith("bereits erledigt"):
            return 1
        if title.startswith("vorherige fehlschlaege"):
            return 2
        if title.startswith("phase-state"):
            return 3
        return 4

    normalized = sorted(normalized_input, key=priority)
    full = "\n\n".join(
        f"## {title}\n{content}" for title, content in normalized
    )

    def section_manifest(
        text: str, included_indices: set[int],
    ) -> list[dict[str, object]]:
        records: list[dict[str, object]] = []
        cursor = 0
        for index, (title, content) in enumerate(normalized):
            section = f"## {title}\n{content}"
            included = index in included_indices
            record: dict[str, object] = {
                "name": title,
                "status": "included" if included else "omitted_optional",
                "chars": len(section),
                "content_chars": len(content),
                "sha256": hashlib.sha256(section.encode("utf-8")).hexdigest(),
            }
            if included:
                start = text.find(section, cursor)
                if start < 0:
                    raise ValueError(
                        f"Architect-Kontextabschnitt {title!r} fehlt im finalen Text.",
                    )
                end = start + len(section)
                record["prompt_start"] = start
                record["prompt_end"] = end
                cursor = end + 2
            records.append(record)
        return records

    if len(full) <= max_chars:
        return full, {
            "max_chars": max_chars,
            "chars": len(full),
            "included": [title for title, _ in normalized],
            "truncated": [],
            "omitted": [],
            "section_manifest": section_manifest(
                full, set(range(len(normalized))),
            ),
        }

    report_reserve = min(700, max(40, max_chars // 12))
    content_budget = max(0, max_chars - report_reserve)
    output: list[str] = []
    included: list[str] = []
    omitted: list[str] = []
    used = 0
    for index, (title, content) in enumerate(normalized):
        heading = f"## {title}\n"
        separator = 2 if output else 0
        section = heading + content
        if used + separator + len(section) > content_budget:
            omitted.extend(name for name, _ in normalized[index:])
            break
        output.append(section)
        included.append(title)
        used += separator + len(section)

    report = (
        "KONTEXT AUSGELASSEN (kein Negativbeleg): "
        + ", ".join(omitted)
        + ". Bei Bedarf gezielt nachladen."
    )
    used_text = "\n\n".join(output)
    report_room = max(0, max_chars - len(used_text) - (2 if output else 0))
    if len(report) > report_room:
        marker = "…"
        report = (report[:max(0, report_room - len(marker))] + marker)[:report_room]
    text = "\n\n".join(output + [report])
    metadata: dict[str, object] = {
        "max_chars": max_chars,
        "chars": len(text),
        "included": included,
        "truncated": [],
        "omitted": omitted,
        "section_manifest": section_manifest(text, set(range(len(included)))),
    }
    return text, metadata


def scout_report_has_architect_assignment(report: object) -> bool:
    """Return whether Scout supplied a usable Architect assignment."""
    if not isinstance(report, dict):
        return False
    assignment = report.get("auftrag_prosa")
    return isinstance(assignment, str) and bool(assignment.strip())


def completed_project_points(project_dir: Path | str | None) -> str:
    """Gather completed items from git history and current living docs."""
    parts: list[str] = []
    root = Path(project_dir) if project_dir else Path(".")
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "log", "--grep=✅", "--oneline", "-20"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        if result.stdout.strip():
            parts.append("Commits mit ✅:\n" + result.stdout.strip())
    except Exception:
        pass

    for name, candidates in (
        ("ROADMAP", ("docs/ROADMAP.md", "ROADMAP.md")),
        ("STATUS", ("docs/STATUS.md", "STATUS.md")),
    ):
        source = next((root / relative for relative in candidates if (root / relative).is_file()), None)
        if source is None:
            continue
        try:
            text = source.read_text(encoding="utf-8")
        except OSError:
            continue
        matches = re.findall(r"^.*✅.*$", text, flags=re.MULTILINE)
        if matches:
            parts.append(f"{name} ✅-Zeilen:\n" + "\n".join(matches[:30]))
    return "\n\n".join(parts)


def migration_status(project_dir: Path | str) -> str:
    """Return the current numbered SQL migrations and next free number."""
    try:
        directory = Path(project_dir) / "data" / "migrations"
        if not directory.is_dir():
            return ""
        files = sorted(
            path.name for path in directory.glob("*.sql") if path.is_file()
        )
        numbers = [name.split("_", 1)[0] for name in files]
        numbers = [number for number in numbers if number.isdigit()]
        if not numbers:
            return ""
        highest = max(numbers)
        next_number = f"{int(highest) + 1:04d}"
        blocked = ", ".join(
            f"{number}_*" for number in sorted(set(numbers))[-5:]
        )
        lines = [
            '<migrationsstand pflicht="true">',
            f"Hoechste vorhandene Nummer: {highest}",
            f"Naechste freie Nummer: {next_number}",
            f"VERBOTEN (bereits belegt): {blocked}",
            "Waehle fuer neue Migrationen NUR die naechste freie Nummer.",
            "Eine andere Nummer fuehrt zu einem Review-Fail und Loop-Abbruch.",
            "</migrationsstand>",
        ]
        return "\n".join(lines)
    except Exception:
        return ""


def migration_collisions(prose: str, project_dir: Path | str) -> list[dict[str, Any]]:
    """Report migration numbers already present in the project."""
    try:
        directory = Path(project_dir) / "data" / "migrations"
        if not directory.is_dir():
            return []
        existing = {
            path.name.split("_", 1)[0]
            for path in directory.glob("*.sql")
            if path.is_file() and path.name.split("_", 1)[0].isdigit()
        }
        planned = re.findall(r"data/migrations/(\d+)_", prose)
        return [
            {"nummer": number, "existiert": True}
            for number in sorted(set(planned) & existing)
        ]
    except Exception:
        return []
