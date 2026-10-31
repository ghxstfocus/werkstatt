"""Spec: audit() ueberlebt nicht-JSON-serialisierbare Payloads (Fix AK)."""
from __future__ import annotations
import json
import sys
from pathlib import Path

sys.path.insert(0, "/opt/werkstatt")
import pytest


class TestAuditDefensive:
    def test_frozenset_im_payload(self, tmp_path: Path) -> None:
        from werkstatt import audit as _a
        _a.audit("loop_reflection_stagnation_runde",
                 {"payload": frozenset({"a", "b"})},
                 tmp_path, "test")
        _files = list((tmp_path / "audit-logs").glob("*.jsonl"))
        assert _files, "kein audit-log geschrieben"
        _line = _files[0].read_text().strip().splitlines()[-1]
        _rec = json.loads(_line)
        assert _rec["kind"] == "loop_reflection_stagnation_runde"
        assert "payload" in _rec

    def test_set_im_payload(self, tmp_path: Path) -> None:
        from werkstatt import audit as _a
        _a.audit("loop_reflection_stagnation_runde",
                 {"s": {1, 2, 3}}, tmp_path, "test")
        _files = list((tmp_path / "audit-logs").glob("*.jsonl"))
        assert _files
        _line = _files[0].read_text().strip().splitlines()[-1]
        json.loads(_line)

    def test_bytes_im_payload(self, tmp_path: Path) -> None:
        from werkstatt import audit as _a
        _a.audit("loop_reflection_stagnation_runde",
                 {"b": b"raw"}, tmp_path, "test")
        _files = list((tmp_path / "audit-logs").glob("*.jsonl"))
        assert _files
        _line = _files[0].read_text().strip().splitlines()[-1]
        json.loads(_line)
