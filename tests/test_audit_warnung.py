"""Spec: audit() warnt bei unbekanntem Kind, bricht aber nicht."""
from __future__ import annotations

import json
from pathlib import Path

from werkstatt import audit as audit_mod


def _events(tmp_path: Path) -> list[dict]:
    logs = tmp_path / "audit-logs"
    if not logs.is_dir():
        return []
    out: list[dict] = []
    for f in sorted(logs.glob("agent-pipeline-*.jsonl")):
        for line in f.read_text().splitlines():
            if line.strip():
                out.append(json.loads(line))
    return out


def test_audit_unbekannter_kind_warnt(tmp_path, capsys):
    """Unbekannter Kind wird geschrieben UND warnt auf stderr."""
    audit_mod.audit("voellig_neuer_kind", {"x": 1},
                    tmp_path, "testproj")
    ev = [e for e in _events(tmp_path)
          if e.get("kind") == "voellig_neuer_kind"]
    assert len(ev) == 1
    cap = capsys.readouterr()
    assert "voellig_neuer_kind" in cap.err
    assert "unbekannter kind" in cap.err


def test_audit_bekannter_kind_keine_warnung(tmp_path, capsys):
    """Bekannter Kind: keine Warnung."""
    audit_mod.audit("llm_call", {"x": 1}, tmp_path, "testproj")
    cap = capsys.readouterr()
    assert "unbekannter kind" not in cap.err


def test_audit_unbekannter_kind_schreibt_trotzdem(tmp_path):
    """Fail-safe: Audit bricht nie, schreibt immer."""
    audit_mod.audit("ganz_neuer_kind", {"y": 2},
                    tmp_path, "testproj")
    ev = [e for e in _events(tmp_path)
          if e.get("kind") == "ganz_neuer_kind"]
    assert len(ev) == 1
    assert ev[0]["y"] == 2
