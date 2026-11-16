from __future__ import annotations

from werkstatt.review_dispatch import reviewer_dispatch_decision


def _diff(path: str, *lines: str) -> str:
    return "\n".join((
        f"diff --git a/{path} b/{path}",
        f"+++ b/{path}",
        *lines,
    ))


def test_small_verified_single_file_update_can_skip_semantic_reviewer() -> None:
    decision = reviewer_dispatch_decision(
        {
            "name": "Update helper",
            "description": "Return the normalized display label.",
            "action": "update",
            "task_files": ["src/labels.py"],
        },
        _diff("src/labels.py", "+    return label.strip()"),
    )

    assert decision["invoke_reviewer"] is False
    assert decision["reason"] == "small_verified_low_risk_patch"


def test_reviewer_is_required_for_uncertainty_risk_and_findings() -> None:
    task = {
        "name": "Update auth check",
        "description": "Change authentication behavior.",
        "action": "update",
        "task_files": ["src/auth.py"],
    }
    diff = _diff("src/auth.py", "+    return check_credentials(user)")

    decision = reviewer_dispatch_decision(task, diff)
    assert decision["invoke_reviewer"] is True
    assert decision["reason"] == "high_risk_path"

    warning = reviewer_dispatch_decision(
        {
            **task,
            "name": "Update display helper",
            "description": "Return the display label.",
            "task_files": ["src/labels.py"],
        },
        _diff("src/labels.py", "+    return label.strip()"),
        verify_warnings=["ruff warning"],
    )
    assert warning["invoke_reviewer"] is True
    assert warning["reason"] == "verify_warning_present"


def test_reviewer_fails_closed_for_scope_mismatch_or_chat_recovery() -> None:
    task = {
        "name": "Update helper",
        "description": "Return the normalized display label.",
        "action": "update",
        "task_files": ["src/labels.py"],
    }
    mismatch = reviewer_dispatch_decision(
        task,
        _diff("src/other.py", "+    return label.strip()"),
    )
    assert mismatch["invoke_reviewer"] is True
    assert mismatch["reason"] == "diff_scope_not_exactly_bound_to_task"

    recovery = reviewer_dispatch_decision(
        task,
        _diff("src/labels.py", "+    return label.strip()"),
        recovery=True,
    )
    assert recovery["invoke_reviewer"] is True
    assert recovery["reason"] == "chat_recovery_requires_independent_review"

