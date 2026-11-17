from __future__ import annotations

from pathlib import Path

from werkstatt.roles.builder_apply import (
    BuilderApplyServices,
    apply_builder_patch_set,
)
from werkstatt.state import RunState


def _services(*, hook_allow: bool = True) -> BuilderApplyServices:
    return BuilderApplyServices(
        audit_call=lambda *_args, **_kwargs: True,
        call_hook=lambda *_args, **_kwargs: {
            "allow": hook_allow,
            "reason": "blocked by test" if not hook_allow else "",
        },
        get_git_diff=lambda: "",
        apply_one_patch=lambda source, old, new: (
            (source.replace(old, new, 1), "exact")
            if old in source else (source, "fail")
        ),
        delete_allowed=lambda *_args: (True, "allowed"),
        ruff_fix_changed=lambda _state: None,
    )


def test_builder_apply_role_writes_only_a_task_scoped_file(tmp_path: Path) -> None:
    source = tmp_path / "src" / "settings.py"
    source.parent.mkdir()
    source.write_text("TIMEOUT = 10\n", encoding="utf-8")
    state = RunState(project_dir=tmp_path, project_name="demo")
    state.patches = [{
        "action": "update",
        "file": "src/settings.py",
        "old_string": "TIMEOUT = 10",
        "new_string": "TIMEOUT = 20",
    }]

    result = apply_builder_patch_set(
        state,
        {"task_files": ["src/settings.py"]},
        task_id="update-timeout",
        debugger_fix_bound=False,
        services=_services(),
    )

    assert result.status == "applied"
    assert result.applied_count == 1
    assert state.applied_count == 1
    assert source.read_text(encoding="utf-8") == "TIMEOUT = 20\n"


def test_builder_apply_validates_entire_patch_scope_before_any_write(
    tmp_path: Path,
) -> None:
    source = tmp_path / "src" / "settings.py"
    source.parent.mkdir()
    source.write_text("TIMEOUT = 10\n", encoding="utf-8")
    state = RunState(project_dir=tmp_path, project_name="demo")
    state.patches = [
        {
            "action": "update",
            "file": "src/settings.py",
            "old_string": "TIMEOUT = 10",
            "new_string": "TIMEOUT = 20",
        },
        {
            "action": "create",
            "file": "src/unapproved.py",
            "content": "VALUE = 1\n",
        },
    ]

    result = apply_builder_patch_set(
        state,
        {"task_files": ["src/settings.py"]},
        task_id="update-timeout",
        debugger_fix_bound=False,
        services=_services(),
    )

    assert result.status == "scope_rejected"
    assert result.reason == "builder_patch_outside_approved_scope"
    assert source.read_text(encoding="utf-8") == "TIMEOUT = 10\n"
    assert not (tmp_path / "src" / "unapproved.py").exists()


def test_builder_apply_hook_block_does_not_write(tmp_path: Path) -> None:
    source = tmp_path / "src" / "settings.py"
    source.parent.mkdir()
    source.write_text("TIMEOUT = 10\n", encoding="utf-8")
    state = RunState(project_dir=tmp_path, project_name="demo")
    state.patches = [{
        "action": "update",
        "file": "src/settings.py",
        "old_string": "TIMEOUT = 10",
        "new_string": "TIMEOUT = 20",
    }]

    result = apply_builder_patch_set(
        state,
        {"task_files": ["src/settings.py"]},
        task_id="update-timeout",
        debugger_fix_bound=False,
        services=_services(hook_allow=False),
    )

    assert result.status == "hook_blocked"
    assert source.read_text(encoding="utf-8") == "TIMEOUT = 10\n"
    assert state.applied_count == 0
