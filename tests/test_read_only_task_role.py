from __future__ import annotations

from hashlib import sha256

import pytest

from werkstatt.roles.read_only_task import read_task_scope_evidence


def test_read_task_scope_evidence_returns_current_hash_and_bounds(
    tmp_path,
) -> None:
    source = tmp_path / "src" / "module.py"
    source.parent.mkdir()
    content = b"first line\nlast line"
    source.write_bytes(content)

    evidence, error = read_task_scope_evidence(
        tmp_path, ["src/module.py"],
    )

    assert error == ""
    assert evidence == [{
        "file": "src/module.py",
        "sha256": sha256(content).hexdigest(),
        "bytes": len(content),
        "lines": 2,
    }]


@pytest.mark.parametrize(
    ("paths", "reason"),
    [
        ([], "read_task_scope_missing"),
        (["../outside.py"], "read_task_path_outside_project"),
        (["same.py", "same.py"], "read_task_duplicate_path"),
    ],
)
def test_read_task_scope_evidence_rejects_invalid_scopes(
    tmp_path, paths, reason: str,
) -> None:
    (tmp_path / "same.py").write_text("x = 1\n", encoding="utf-8")

    evidence, error = read_task_scope_evidence(tmp_path, paths)

    assert evidence == []
    assert error == reason


def test_read_task_scope_evidence_enforces_file_and_total_byte_limits(
    tmp_path,
) -> None:
    too_large = tmp_path / "large.py"
    too_large.write_bytes(b"x" * 1_000_001)

    evidence, error = read_task_scope_evidence(tmp_path, ["large.py"])

    assert evidence == []
    assert error == "read_task_source_over_budget"
