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
    parse_debugger_fix,
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

    changed = _payload(diff=_DIFF.replace("value = 2", "value = 3"))
    with pytest.raises(DebuggerFixError, match="Patch-Hash"):
        parse_debugger_fix(changed)


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
    assert run.call_args_list[1].kwargs["input"] == _DIFF


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
