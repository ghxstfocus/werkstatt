"""Vertragstests fuer den OP-240 DebuggerFix-Handoff."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from werkstatt.debugger_handoff import (
    DebuggerFixError,
    cleanup_debugger_workspace,
    debugger_fix_loop_patches,
    debugger_fix_loop_task,
    materialize_debugger_workspace,
    parse_debugger_fix,
    parse_debugger_loop_task,
    validate_debugger_fix_checkout,
)

_HEAD = "a" * 40
_DIFF = (
    "diff --git a/werkstatt/sample.py b/werkstatt/sample.py\n"
    "index 1111111..2222222 100644\n"
    "--- a/werkstatt/sample.py\n"
    "+++ b/werkstatt/sample.py\n"
    "@@ -1 +1 @@\n"
    "-value = 1\n"
    "+value = 2\n"
)


def _payload(**changes: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "signatur": "ruff_f821:werkstatt.sample",
        "ursache_tag": "undefined_name",
        "diff": _DIFF,
        "betroffene_dateien": ["werkstatt/sample.py"],
        "confidence": 0.91,
        "project": "demo",
        "run_id": "demo-20261111-ab12cd34",
        "base_head": _HEAD,
        "patch_hash": "",
    }
    values.update(changes)
    canonical = {
        key: values[key]
        for key in (
            "signatur", "ursache_tag", "diff", "betroffene_dateien",
            "confidence", "project", "run_id", "base_head",
        )
    }
    values["patch_hash"] = hashlib.sha256(json.dumps(
        canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()
    return values


def test_debugger_fix_hash_binds_exact_diff_and_context() -> None:
    payload = _payload()
    fix = parse_debugger_fix(payload)
    assert fix.to_payload()["patch_hash"] == payload["patch_hash"]
    assert parse_debugger_fix(fix.to_payload()) == fix

    changed = {**payload, "diff": _DIFF.replace("value = 2", "value = 3")}
    with pytest.raises(DebuggerFixError, match="Patch-Hash"):
        parse_debugger_fix(changed)


def test_chat_workspace_fix_uses_explicit_session_provenance() -> None:
    from werkstatt.debugger_handoff import create_debugger_fix

    fix = create_debugger_fix(
        signatur="chat-workspace-test",
        ursache_tag="chat_debug_workspace",
        diff=_DIFF,
        betroffene_dateien=["werkstatt/sample.py"],
        confidence=0.8,
        project="demo",
        run_id=None,
        base_head=_HEAD,
        source_chat_session_id="chat-session-123",
    )

    assert fix.source_kind == "chat_session"
    assert fix.source_chat_session_id == "chat-session-123"
    parsed = parse_debugger_loop_task(debugger_fix_loop_task(fix))
    assert parsed == fix
    assert parsed is not None and parsed.run_id.startswith("demo-chat-")

    forged = json.loads(debugger_fix_loop_task(fix))
    forged["source_chat_session_id"] = "other-session"
    with pytest.raises(DebuggerFixError):
        parse_debugger_loop_task(json.dumps(forged))


@pytest.mark.parametrize(
    ("diff", "files", "message"),
    [
        (_DIFF.replace("werkstatt/sample.py", "../outside.py"), ["../outside.py"], "Traversal"),
        (_DIFF.replace("werkstatt/sample.py", ".git/config"), [".git/config"], "Interne"),
        (_DIFF + "GIT binary patch\n", ["werkstatt/sample.py"], "Binaere"),
        (_DIFF, ["werkstatt/other.py"], "stimmen nicht"),
    ],
)
def test_debugger_fix_rejects_unsafe_or_mismatched_diffs(
    diff: str, files: list[str], message: str,
) -> None:
    with pytest.raises(DebuggerFixError, match=message):
        parse_debugger_fix(_payload(diff=diff, betroffene_dateien=files))


def test_debugger_fix_requires_project_scoped_run_id() -> None:
    with pytest.raises(DebuggerFixError, match="run_id"):
        parse_debugger_fix(_payload(run_id="other-20261111-ab12cd34"))


def test_checkout_validation_checks_head_then_patch(tmp_path: Path) -> None:
    fix = parse_debugger_fix(_payload())
    replies = [
        subprocess.CompletedProcess(args=["git"], returncode=0, stdout=_HEAD + "\n", stderr=""),
        subprocess.CompletedProcess(args=["git"], returncode=0, stdout="", stderr=""),
    ]
    with patch("werkstatt.debugger_handoff.subprocess.run", side_effect=replies) as run:
        ok, detail = validate_debugger_fix_checkout(
            fix, tmp_path, expected_project="demo",
        )
    assert ok, detail
    assert run.call_count == 2
    assert run.call_args_list[1].args[0][:3] == ["git", "apply", "--check"]
    assert run.call_args_list[1].kwargs["input"] == _DIFF.encode("utf-8")


def test_checkout_validation_fails_closed_on_changed_head(tmp_path: Path) -> None:
    reply = subprocess.CompletedProcess(
        args=["git"], returncode=0, stdout="b" * 40 + "\n", stderr="",
    )
    with patch("werkstatt.debugger_handoff.subprocess.run", return_value=reply) as run:
        ok, detail = validate_debugger_fix_checkout(
            parse_debugger_fix(_payload()), tmp_path, expected_project="demo",
        )
    assert not ok
    assert "HEAD" in detail
    assert run.call_count == 1


def test_checkout_validation_fails_on_cross_project_proposal(tmp_path: Path) -> None:
    with patch("werkstatt.debugger_handoff.subprocess.run") as run:
        ok, detail = validate_debugger_fix_checkout(
            parse_debugger_fix(_payload()), tmp_path, expected_project="other",
        )
    assert not ok
    assert "anderen Projekt" in detail
    run.assert_not_called()


def test_create_debugger_fix_builds_hash_and_loop_task() -> None:
    from werkstatt.debugger_handoff import (
        create_debugger_fix,
        debugger_fix_loop_task,
    )

    fix = create_debugger_fix(
        signatur="fixture-regression",
        ursache_tag="stale_fixture",
        diff=_DIFF,
        betroffene_dateien=["werkstatt/sample.py"],
        confidence=0.93,
        project="demo",
        run_id="demo-run-123",
        base_head="a" * 40,
    )
    payload = json.loads(debugger_fix_loop_task(fix))
    assert payload["patch_hash"] == fix.patch_hash
    assert payload["diff"] == _DIFF
    assert payload["approval"] == "exact_diff_hash"
    assert "Plan-/Human-Gate" in payload["instruction"]
    assert parse_debugger_loop_task(debugger_fix_loop_task(fix)) == fix


def test_debugger_loop_patch_records_are_derived_from_exact_diff(tmp_path: Path) -> None:
    from werkstatt.debugger_handoff import create_debugger_fix

    project = tmp_path / "project"
    project.mkdir()
    subprocess.run(["git", "init", str(project)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(project), "config", "user.email", "test@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(project), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "-C", str(project), "config", "core.autocrlf", "false"], check=True)
    target = project / "werkstatt" / "sample.py"
    target.parent.mkdir()
    target.write_bytes(b"value = 1\n")
    subprocess.run(["git", "-C", str(project), "add", "."], check=True)
    subprocess.run(["git", "-C", str(project), "commit", "-m", "base"], check=True, capture_output=True)
    head = subprocess.run(
        ["git", "-C", str(project), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    fix = create_debugger_fix(
        signatur="chat-loop-patch",
        ursache_tag="chat_debug_workspace",
        diff=_DIFF,
        betroffene_dateien=["werkstatt/sample.py"],
        confidence=0.9,
        project="demo",
        run_id=None,
        base_head=head,
        source_chat_session_id="debugger-session",
    )

    patches = debugger_fix_loop_patches(fix, project)

    assert patches == [{
        "action": "update",
        "file": "werkstatt/sample.py",
        "old_string": "value = 1\n",
        "new_string": "value = 2\n",
        "approved_debugger_exact": True,
    }]
    assert target.read_bytes() == b"value = 1\n"
    worktrees = subprocess.run(
        ["git", "-C", str(project), "worktree", "list", "--porcelain"],
        check=True, capture_output=True, text=True,
    ).stdout
    assert worktrees.count("worktree ") == 1


def test_chat_patch_is_written_only_to_detached_debug_worktree(tmp_path: Path) -> None:
    from werkstatt.debugger_handoff import create_debugger_fix

    project = tmp_path / "project"
    project.mkdir()
    subprocess.run(["git", "init", str(project)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(project), "config", "user.email", "test@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(project), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "-C", str(project), "config", "core.autocrlf", "false"], check=True)
    target = project / "werkstatt" / "sample.py"
    target.parent.mkdir()
    target.write_bytes(b"value = 1\n")
    subprocess.run(["git", "-C", str(project), "add", "."], check=True)
    subprocess.run(["git", "-C", str(project), "commit", "-m", "base"], check=True, capture_output=True)
    head = subprocess.run(
        ["git", "-C", str(project), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    fix = create_debugger_fix(
        signatur="chat-workspace-handoff",
        ursache_tag="chat_debug_workspace",
        diff=_DIFF,
        betroffene_dateien=["werkstatt/sample.py"],
        confidence=0.9,
        project="demo",
        run_id=None,
        base_head=head,
        source_chat_session_id="debug-session-1",
    )
    proposal_id = "b" * 32

    workspace = materialize_debugger_workspace(fix, project, proposal_id)

    assert (workspace / "werkstatt" / "sample.py").read_bytes() == b"value = 2\n"
    assert target.read_bytes() == b"value = 1\n"
    assert subprocess.run(
        ["git", "-C", str(workspace), "diff", "--check"], check=False,
    ).returncode == 0
    assert cleanup_debugger_workspace(fix, project, proposal_id)[0]
    assert not workspace.exists()
