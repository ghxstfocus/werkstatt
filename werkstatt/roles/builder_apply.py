"""Apply one Builder patch set within its approved task scope."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Literal

from werkstatt.antipattern import scan_patches
from werkstatt.state import RunState, check_run_lease

ApplyStatus = Literal[
    "applied",
    "already_fulfilled",
    "antipattern_veto",
    "scope_rejected",
    "hook_blocked",
    "patch_failed",
    "simplify_blocked",
]


@dataclass(frozen=True)
class BuilderApplyResult:
    """Bounded outcome of one Builder write action."""

    status: ApplyStatus
    applied_count: int = 0
    reason: str = ""
    finding_count: int = 0
    finding_kinds: tuple[str, ...] = ()
    finding_files: tuple[str, ...] = ()


@dataclass(frozen=True)
class BuilderApplyServices:
    """Phase adapters required by the Builder's bounded apply worker."""

    audit_call: Callable[..., Any]
    call_hook: Callable[..., dict[str, Any]]
    get_git_diff: Callable[..., str]
    apply_one_patch: Callable[..., tuple[str, str]]
    delete_allowed: Callable[..., tuple[bool, str]]
    ruff_fix_changed: Callable[[RunState], Any]


def _scoped_target(
    project_root: Path,
    task_files: set[str],
    raw_file: object,
) -> tuple[Path | None, str | None]:
    """Resolve only a normalized task file contained by the project root."""
    if not isinstance(raw_file, str) or not raw_file or "\x00" in raw_file:
        return None, None
    normalized = raw_file.replace("\\", "/")
    relative = PurePosixPath(normalized)
    windows_relative = PureWindowsPath(raw_file)
    if (
        relative.is_absolute()
        or windows_relative.is_absolute()
        or windows_relative.drive
        or ".." in relative.parts
    ):
        return None, None
    relative_text = relative.as_posix()
    if relative_text in {"", "."} or relative_text not in task_files:
        return None, None
    try:
        root = project_root.resolve(strict=True)
        target = (root / Path(*relative.parts)).resolve()
        target.relative_to(root)
    except (OSError, RuntimeError, ValueError):
        return None, None
    return target, relative_text


def apply_builder_patch_set(
    state: RunState,
    task: dict[str, Any],
    *,
    task_id: str,
    debugger_fix_bound: bool,
    services: BuilderApplyServices,
) -> BuilderApplyResult:
    """Validate hooks/scope and apply exactly one selected Builder patch set.

    This worker does not run Verify or Reviewer. The caller persists the build
    checkpoint and yields to the coordinator after this single write action.
    """
    project_dir = Path(state.project_dir)
    project_name = state.project_name
    raw_patches = getattr(state, "patches", None)
    patches = raw_patches if isinstance(raw_patches, list) else []

    findings = scan_patches(list(patches))
    if findings:
        return BuilderApplyResult(
            "antipattern_veto",
            finding_count=len(findings),
            finding_kinds=tuple(item.kind for item in findings[:5]),
            finding_files=tuple(item.file for item in findings[:5]),
            reason=str(findings[0].kind)[:120],
        )

    if (
        getattr(state, "auftrag_bereits_erfuellt", False)
        and getattr(state, "auftrag_bereits_erfuellt_bestaetigt", False)
    ):
        return BuilderApplyResult("already_fulfilled")

    raw_scope = task.get("task_files")
    task_files = {
        item.replace("\\", "/")
        for item in raw_scope
        if isinstance(item, str) and item
    } if isinstance(raw_scope, list) else set()
    if patches and not task_files:
        return BuilderApplyResult(
            "scope_rejected", reason="approved_task_file_scope_missing",
        )

    resolved: list[tuple[dict[str, Any], Path, str]] = []
    for patch in patches:
        if not isinstance(patch, dict):
            return BuilderApplyResult(
                "scope_rejected", reason="builder_patch_not_an_object",
            )
        target, relative = _scoped_target(
            project_dir, task_files, patch.get("file"),
        )
        if target is None or relative is None:
            return BuilderApplyResult(
                "scope_rejected", reason="builder_patch_outside_approved_scope",
            )
        if patch.get("approved_debugger_exact") is True and not debugger_fix_bound:
            return BuilderApplyResult(
                "scope_rejected", reason="unbound_approved_debugger_patch",
            )
        action = patch.get("action", "update")
        if action not in {"create", "update", "delete"}:
            return BuilderApplyResult(
                "patch_failed", reason="builder_patch_action_invalid",
            )
        resolved.append((patch, target, relative))

    for patch, _target, _relative in resolved:
        action = patch.get("action", "update")
        patch_text = patch.get("new_string", "") or patch.get("content", "")
        if patch_text is None:
            patch_text = ""
        if not isinstance(patch_text, str):
            return BuilderApplyResult(
                "patch_failed", reason="builder_patch_content_invalid",
            )
        hook_result = services.call_hook("pre_tool_use.py", {
            "patch": patch_text,
            "action": action,
            "project_dir": str(project_dir),
        })
        if not hook_result.get("allow", False):
            reason = str(hook_result.get("reason", ""))[:300]
            services.audit_call(
                "loop_hook_blocked",
                {"hook": "pre_tool_use", "reason": reason, "task_id": task_id},
                project_dir,
                project_name,
            )
            return BuilderApplyResult("hook_blocked", reason=reason)

    state.applied_count = 0
    for patch, target, relative in resolved:
        action = patch.get("action", "update")
        if action == "create":
            content = patch.get("content", "")
            if not isinstance(content, str) or not content:
                continue
            if target.exists():
                services.audit_call(
                    "loop_patch_file_exists",
                    {"file": relative, "task_id": task_id},
                    project_dir, project_name,
                )
                continue
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                check_run_lease(state)
                if patch.get("approved_debugger_exact") is True:
                    with target.open("w", encoding="utf-8", newline="") as handle:
                        handle.write(content)
                else:
                    target.write_text(content)
            except OSError as exc:
                services.audit_call(
                    "loop_patch_write_failed",
                    {"file": relative, "fehler": str(exc)[:200], "task_id": task_id},
                    project_dir, project_name,
                )
                return BuilderApplyResult("patch_failed", reason="patch_write_failed")
            state.applied_count += 1
            services.audit_call(
                "loop_patch_created", {"file": relative, "task_id": task_id},
                project_dir, project_name,
            )
            continue

        if action == "update":
            old_text, new_text = patch.get("old_string", ""), patch.get("new_string", "")
            if not isinstance(old_text, str) or not old_text or not isinstance(new_text, str) or not new_text:
                return BuilderApplyResult("patch_failed", reason="builder_patch_content_missing")
            if not target.exists():
                services.audit_call(
                    "loop_patch_file_missing",
                    {"file": relative, "task_id": task_id},
                    project_dir, project_name,
                )
                return BuilderApplyResult("patch_failed", reason=f"patch_file_missing:{relative}")
            try:
                exact_debugger_patch = patch.get("approved_debugger_exact") is True
                before = (
                    target.read_bytes().decode("utf-8")
                    if exact_debugger_patch else target.read_text()
                )
                after, match = services.apply_one_patch(before, old_text, new_text)
            except (OSError, UnicodeDecodeError, RuntimeError, ValueError):
                return BuilderApplyResult("patch_failed", reason=f"patch_source_unreadable:{relative}")
            if match == "fail":
                services.audit_call(
                    "loop_patch_old_string_not_found",
                    {"file": relative, "old": old_text[:50], "task_id": task_id},
                    project_dir, project_name,
                )
                return BuilderApplyResult("patch_failed", reason=f"old_string_not_found:{relative}")
            if old_text == new_text and match == "exact":
                services.audit_call(
                    "loop_patch_no_effect",
                    {"file": relative, "task_id": task_id},
                    project_dir, project_name,
                )
                continue
            if match != "exact":
                services.audit_call(
                    "loop_patch_fallback_used",
                    {"file": relative, "match": match, "task_id": task_id},
                    project_dir, project_name,
                )
            if new_text not in after:
                services.audit_call(
                    "loop_patch_not_applied_vor_schreiben",
                    {"file": relative, "task_id": task_id},
                    project_dir, project_name,
                )
                return BuilderApplyResult("patch_failed", reason=f"patch_not_applied:{relative}")
            try:
                check_run_lease(state)
                if exact_debugger_patch:
                    with target.open("w", encoding="utf-8", newline="") as handle:
                        handle.write(after)
                else:
                    target.write_text(after)
                written = (
                    target.read_bytes().decode("utf-8")
                    if exact_debugger_patch else target.read_text()
                )
            except (OSError, UnicodeDecodeError) as exc:
                services.audit_call(
                    "loop_patch_write_failed",
                    {"file": relative, "fehler": str(exc)[:200], "task_id": task_id},
                    project_dir, project_name,
                )
                return BuilderApplyResult("patch_failed", reason="patch_write_failed")
            if new_text not in written:
                services.audit_call(
                    "loop_patch_not_applied",
                    {"file": relative, "task_id": task_id},
                    project_dir, project_name,
                )
                return BuilderApplyResult(
                    "patch_failed", reason=f"post_write_patch_check_failed:{relative}",
                )
            state.applied_count += 1
            services.audit_call(
                "loop_patch_updated", {"file": relative, "task_id": task_id},
                project_dir, project_name,
            )
            continue

        allowed, reason = services.delete_allowed(
            Path(relative), task_files, project_dir,
        )
        if not allowed:
            services.audit_call(
                "loop_patch_delete_blocked",
                {"file": relative, "grund": str(reason)[:200], "task_id": task_id},
                project_dir, project_name,
            )
            return BuilderApplyResult("scope_rejected", reason="delete_scope_rejected")
        if not target.exists():
            services.audit_call(
                "loop_patch_delete_skip_missing",
                {"file": relative, "task_id": task_id},
                project_dir, project_name,
            )
            continue
        try:
            check_run_lease(state)
            target.unlink()
        except OSError as exc:
            services.audit_call(
                "loop_patch_delete_failed",
                {"file": relative, "fehler": str(exc)[:200], "task_id": task_id},
                project_dir, project_name,
            )
            return BuilderApplyResult("patch_failed", reason="patch_delete_failed")
        state.applied_count += 1
        services.audit_call(
            "loop_patch_deleted", {"file": relative, "task_id": task_id},
            project_dir, project_name,
        )

    hook_result = services.call_hook(
        "simplify.py", {"diff": services.get_git_diff()},
    )
    if not hook_result.get("allow", False):
        reason = str(hook_result.get("reason", ""))[:1200]
        services.audit_call(
            "loop_hook_blocked",
            {"hook": "simplify", "reason": reason, "task_id": task_id},
            project_dir, project_name,
        )
        return BuilderApplyResult("simplify_blocked", reason=reason)

    services.ruff_fix_changed(state)
    return BuilderApplyResult("applied", applied_count=state.applied_count)


__all__ = [
    "ApplyStatus",
    "BuilderApplyResult",
    "BuilderApplyServices",
    "apply_builder_patch_set",
]
