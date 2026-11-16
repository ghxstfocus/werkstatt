"""Evidence-based Reviewer dispatch after deterministic task verification."""
from __future__ import annotations

import hashlib
import re
from pathlib import PurePosixPath
from typing import Any

_HIGH_RISK_MARKERS = re.compile(
    r"\b(?:auth\w*|sicher\w*|security|credential\w*|secret\w*|token\w*|"
    r"permission\w*|berechtig\w*|crypto\w*|encrypt\w*|password\w*|"
    r"database|\bdb\b|schema\w*|migration\w*|transaction\w*|"
    r"concurr\w*|async\w*|parallel\w*|race\w*|thread\w*|lease\w*|"
    r"workflow\w*|deploy\w*|release\w*|network\w*|payment\w*|"
    r"billing\w*|privacy\w*|safety\w*|schnittstell\w*|\bapi\b|"
    r"refactor\w*|migration\w*|kompatib\w*|compatib\w*)\b",
    re.IGNORECASE,
)
_HIGH_RISK_PATH_PARTS = frozenset({
    "auth", "security", "permissions", "migrations", "schema", "db",
    "database", "crypto", "payments", "billing", "workflows", ".github",
})
_DIFF_PATH = re.compile(r"^\+\+\+ b/(.+)$", re.MULTILINE)


def reviewer_dispatch_decision(
    task: object,
    diff: object,
    *,
    verify_warnings: object = None,
    recovery: bool = False,
) -> dict[str, Any]:
    """Skip semantic review only for a tiny, single-file low-risk patch.

    Unknown or incomplete diff evidence always selects Reviewer. Deterministic
    Verify remains mandatory for every route; chat recovery is always reviewed
    independently, even when its resulting patch looks small.
    """
    reasons: list[str] = []
    task_record = task if isinstance(task, dict) else {}
    raw_files = task_record.get("task_files")
    task_files = [
        item.replace("\\", "/")
        for item in raw_files
        if isinstance(item, str) and item.strip()
    ] if isinstance(raw_files, list) else []
    if recovery:
        reasons.append("chat_recovery_requires_independent_review")
    if not isinstance(diff, str) or not diff.strip():
        reasons.append("diff_evidence_missing")
        rendered_diff = ""
    else:
        rendered_diff = diff
    if len(rendered_diff) > 5_000:
        reasons.append("diff_exceeds_low_risk_limit")
    if not task_files or len(task_files) != 1:
        reasons.append("task_scope_not_single_file")
    changed_files = sorted(set(_DIFF_PATH.findall(rendered_diff)))
    if not changed_files or set(changed_files) != set(task_files):
        reasons.append("diff_scope_not_exactly_bound_to_task")
    if len(changed_files) != 1:
        reasons.append("diff_changes_multiple_files")
    if any(not path.endswith(".py") for path in changed_files):
        reasons.append("non_python_change_requires_review")

    for path in changed_files:
        normalized = path.replace("\\", "/")
        parts = {
            name.casefold()
            for part in PurePosixPath(normalized).parts
            for name in (part, PurePosixPath(part).stem)
        }
        if parts & _HIGH_RISK_PATH_PARTS:
            reasons.append("high_risk_path")
            break
    task_text = " ".join(
        str(task_record.get(key) or "")
        for key in ("name", "description", "action")
    )
    if _HIGH_RISK_MARKERS.search(task_text):
        reasons.append("high_risk_task_intent")
    if task_record.get("action") != "update":
        reasons.append("non_update_action_requires_review")
    if verify_warnings:
        reasons.append("verify_warning_present")

    additions = sum(
        line.startswith("+") and not line.startswith("+++")
        for line in rendered_diff.splitlines()
    )
    deletions = sum(
        line.startswith("-") and not line.startswith("---")
        for line in rendered_diff.splitlines()
    )
    if additions + deletions > 40:
        reasons.append("diff_change_volume_exceeds_low_risk_limit")

    unique_reasons = list(dict.fromkeys(reasons))
    return {
        "invoke_reviewer": bool(unique_reasons),
        "reason": unique_reasons[0] if unique_reasons else "small_verified_low_risk_patch",
        "evidence": {
            "task_files": task_files[:10],
            "changed_files": changed_files[:10],
            "diff_chars": len(rendered_diff),
            "diff_sha256": hashlib.sha256(
                rendered_diff.encode("utf-8"),
            ).hexdigest(),
            "added_lines": additions,
            "removed_lines": deletions,
            "verify_warning_count": (
                len(verify_warnings)
                if isinstance(verify_warnings, (list, tuple, set, dict))
                else int(bool(verify_warnings))
            ),
            "recovery": bool(recovery),
            "risk_reasons": unique_reasons,
        },
    }
