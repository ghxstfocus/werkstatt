from __future__ import annotations

from pathlib import Path

from werkstatt.roles.complete_task import (
    TaskCompletionServices,
    complete_task_checkpoint,
)
from werkstatt.state import RunState


class _PhaseState:
    def __init__(self) -> None:
        self.record = {"review_checkpoint": {"verify_warnings": []}}
        self.saved = 0

    def get_task(self, _task_id: str) -> dict[str, object]:
        return self.record

    def task_review_checkpoint_is_current(self, _task_id: str) -> bool:
        return True

    def save(self) -> None:
        self.saved += 1


def _services(
    *, should_review: bool = False,
    current_sha: str = "a" * 64,
    review_ok: bool = True,
    review_calls: list[int] | None = None,
    task_end_calls: list[dict[str, object]] | None = None,
) -> TaskCompletionServices:
    return TaskCompletionServices(
        audit_call=lambda *_args, **_kwargs: True,
        get_git_diff=lambda **_kwargs: "diff",
        reviewer_dispatch_decision=lambda *_args, **_kwargs: {
            "invoke_reviewer": should_review,
            "evidence": {"diff_sha256": current_sha},
        },
        review=lambda _state, index: (
            review_calls.append(index) if review_calls is not None else None
        ) is None and review_ok,
        task_end=lambda *_args, **kwargs: (
            task_end_calls.append(kwargs) if task_end_calls is not None else None
        ) is None or True,
        audit_task_ok=lambda *_args, **_kwargs: True,
        reviewer_rejected_payload=lambda *_args, **_kwargs: {},
        check_lease=lambda _state: None,
    )


def _decision(*, review: bool, sha: str = "a" * 64) -> dict[str, object]:
    return {
        "next_executor": "reviewer" if review else "task_completion",
        "review_dispatch": {"evidence": {"diff_sha256": sha}},
    }


def test_task_completion_records_done_after_current_non_reviewer_dispatch(
    tmp_path: Path,
) -> None:
    state = RunState(project_dir=tmp_path, project_name="demo")
    phase = _PhaseState()
    ends: list[dict[str, object]] = []
    result = complete_task_checkpoint(
        state,
        phase,
        {"task_files": ["src/app.py"]},
        task_id="t1",
        task_name="Update app",
        task_index=1,
        decision="complete_task_checkpoint",
        decision_payload=_decision(review=False),
        services=_services(task_end_calls=ends),
    )

    assert result.status == "completed"
    assert result.tasks_ok_delta == 1
    assert ends == [{"ok": True, "name": "Update app"}]
    assert phase.saved == 1


def test_task_completion_rechecks_review_hash_before_reviewer_call(
    tmp_path: Path,
) -> None:
    state = RunState(project_dir=tmp_path, project_name="demo")
    phase = _PhaseState()
    review_calls: list[int] = []
    result = complete_task_checkpoint(
        state,
        phase,
        {"task_files": ["src/app.py"]},
        task_id="t1",
        task_name="Review app",
        task_index=2,
        decision="review_task_checkpoint",
        decision_payload=_decision(review=True, sha="b" * 64),
        services=_services(
            should_review=True,
            current_sha="c" * 64,
            review_calls=review_calls,
        ),
    )

    assert result.status == "stale"
    assert review_calls == []
    assert phase.saved == 0


def test_task_completion_invokes_reviewer_only_when_checkpoint_requires_it(
    tmp_path: Path,
) -> None:
    state = RunState(project_dir=tmp_path, project_name="demo")
    phase = _PhaseState()
    review_calls: list[int] = []
    result = complete_task_checkpoint(
        state,
        phase,
        {"task_files": ["src/app.py"]},
        task_id="t1",
        task_name="Review app",
        task_index=3,
        decision="review_task_checkpoint",
        decision_payload=_decision(review=True),
        services=_services(
            should_review=True,
            review_calls=review_calls,
        ),
    )

    assert result.status == "completed"
    assert review_calls == [3]
    assert result.tasks_ok_delta == 1


def test_task_reviewer_rejection_returns_to_coordinator_as_failed_checkpoint(
    tmp_path: Path,
) -> None:
    state = RunState(project_dir=tmp_path, project_name="demo")
    phase = _PhaseState()
    review_calls: list[int] = []
    task_ends: list[dict[str, object]] = []
    result = complete_task_checkpoint(
        state,
        phase,
        {"task_files": ["src/auth.py"]},
        task_id="t1",
        task_name="Repair auth",
        task_index=1,
        decision="review_task_checkpoint",
        decision_payload=_decision(review=True),
        services=_services(
            should_review=True,
            review_ok=False,
            review_calls=review_calls,
            task_end_calls=task_ends,
        ),
    )

    assert result.status == "review_rejected"
    assert result.reason == "reviewer_rejected_at_checkpoint"
    assert review_calls == [1]
    assert task_ends == [{
        "ok": False,
        "name": "Repair auth",
        "failure": "reviewer_rejected_at_checkpoint",
        "failure_detail": "[]",
    }]
    assert phase.saved == 1
