"""Spec: _human_gate — alle 8 Rueckgabepfade.

Config: /opt/werkstatt/projects/<pn>.yaml (nicht Zielprojekt).
Tests legen projects/testproj.yaml fuer die Dauer des Tests an
und raeumen sie im finally auf. Test-Projektname "testproj"
kollidiert nicht mit echten Projekten (nur security-ai).
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from werkstatt import loop
from werkstatt.state import RunState


PROJECTS_DIR = Path("/opt/werkstatt/projects")
CONFIG_NAME = "testproj.yaml"
CONFIG_PATH = PROJECTS_DIR / CONFIG_NAME


# =====================================================================
# Fixtures
# =====================================================================

def _state(tmp_path: Path, **overrides) -> RunState:
    kw = dict(
        block_id="t", aufgabe="aufgabe", start_ts="2026-10-30T00:00:00Z",
        docs={}, agents={}, always={}, optional={}, file_whitelist=[],
        api_key="sk-test", budget={}, agent_docs={},
        project_dir=tmp_path, project_name="testproj",
    )
    kw.update(overrides)
    return RunState(**kw)


def _audit_events(tmp_path: Path) -> list[dict]:
    logs = tmp_path / "audit-logs"
    if not logs.is_dir():
        return []
    out: list[dict] = []
    for f in sorted(logs.glob("agent-pipeline-*.jsonl")):
        for line in f.read_text().splitlines():
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _kind(tmp_path: Path, kind: str) -> list[dict]:
    return [e for e in _audit_events(tmp_path) if e.get("kind") == kind]


@pytest.fixture
def cfg_file():
    """Legt projects/testproj.yaml an, raeumt im finally wieder auf.

    Existiert die Datei bereits (sollte nicht), wird sie gesichert
    und wiederhergestellt.
    """
    vorher = None
    if CONFIG_PATH.exists():
        vorher = CONFIG_PATH.read_text(encoding="utf-8")
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        yield CONFIG_PATH
    finally:
        if vorher is not None:
            CONFIG_PATH.write_text(vorher, encoding="utf-8")
        elif CONFIG_PATH.exists():
            CONFIG_PATH.unlink()


# =====================================================================
# Pfad 1: project_dir fehlt
# =====================================================================

def test_gate_kein_project_dir():
    from types import SimpleNamespace
    st = SimpleNamespace(project_dir=None, project_name="testproj")
    assert loop._human_gate(st) == 1


# =====================================================================
# Pfad 2: require_human_approval=false -> auto approve
# =====================================================================

def test_gate_auto_approve(tmp_path, cfg_file):
    cfg_file.write_text("require_human_approval: false\n",
                        encoding="utf-8")
    s = _state(tmp_path)
    assert loop._human_gate(s) == 0
    ev = _kind(tmp_path, "loop_human_gate_auto")
    assert len(ev) == 1
    assert ev[0]["reason"] == "require_human_approval=false"


# =====================================================================
# Pfad 3: WERKSTATT_IN_TEST=1 -> auto approve
# =====================================================================

def test_gate_test_modus(tmp_path, monkeypatch, cfg_file):
    # Config explizit auf true, damit der Test-Modus greift.
    cfg_file.write_text("require_human_approval: true\n",
                        encoding="utf-8")
    monkeypatch.setenv("WERKSTATT_IN_TEST", "1")
    s = _state(tmp_path)
    assert loop._human_gate(s) == 0
    ev = _kind(tmp_path, "loop_human_gate_test")
    assert len(ev) == 1
    assert ev[0]["reason"] == "WERKSTATT_IN_TEST=1"


# =====================================================================
# Pfad 4: EOF/KeyboardInterrupt -> rc=1
# =====================================================================

def test_gate_eof(tmp_path, monkeypatch, cfg_file):
    cfg_file.write_text("require_human_approval: true\n",
                        encoding="utf-8")
    monkeypatch.delenv("WERKSTATT_IN_TEST", raising=False)

    def _raise(*a, **kw):
        raise EOFError()

    monkeypatch.setattr("builtins.input", _raise)
    s = _state(tmp_path)
    assert loop._human_gate(s) == 1
    ev = _kind(tmp_path, "loop_human_gate_eof")
    assert len(ev) == 1


# =====================================================================
# Pfad 5: 'j' + Commit ok -> rc=0 + approved + committed
# =====================================================================

def test_gate_approved_j(tmp_path, monkeypatch, cfg_file):
    cfg_file.write_text("require_human_approval: true\n",
                        encoding="utf-8")
    monkeypatch.delenv("WERKSTATT_IN_TEST", raising=False)
    monkeypatch.setattr("builtins.input", lambda *a, **kw: "j")
    with patch("werkstatt.loop._committe_zielprojekt",
               return_value=(True, "abc123")):
        s = _state(tmp_path)
        assert loop._human_gate(s) == 0
    assert len(_kind(tmp_path, "loop_human_gate_approved")) == 1


# =====================================================================
# Pfad 6: 'ja' (Alias) -> rc=0
# =====================================================================

def test_gate_approved_ja_alias(tmp_path, monkeypatch, cfg_file):
    cfg_file.write_text("require_human_approval: true\n",
                        encoding="utf-8")
    monkeypatch.delenv("WERKSTATT_IN_TEST", raising=False)
    monkeypatch.setattr("builtins.input", lambda *a, **kw: "ja")
    with patch("werkstatt.loop._committe_zielprojekt",
               return_value=(True, "")):
        s = _state(tmp_path)
        assert loop._human_gate(s) == 0
    assert len(_kind(tmp_path, "loop_human_gate_approved")) == 1


# =====================================================================
# Pfad 7: 'j' + Commit fail -> rc=1 + commit_abort
# =====================================================================

def test_gate_approved_commit_fail(tmp_path, monkeypatch, cfg_file):
    cfg_file.write_text("require_human_approval: true\n",
                        encoding="utf-8")
    monkeypatch.delenv("WERKSTATT_IN_TEST", raising=False)
    monkeypatch.setattr("builtins.input", lambda *a, **kw: "j")
    with patch("werkstatt.loop._committe_zielprojekt",
               return_value=(False, "git boom")):
        s = _state(tmp_path)
        assert loop._human_gate(s) == 1
    ev = _kind(tmp_path, "loop_human_gate_commit_abort")
    assert len(ev) == 1
    assert ev[0]["info"] == "git boom"


# =====================================================================
# Pfad 8: 'n' -> rc=1 + rejected
# =====================================================================

def test_gate_rejected(tmp_path, monkeypatch, cfg_file):
    cfg_file.write_text("require_human_approval: true\n",
                        encoding="utf-8")
    monkeypatch.delenv("WERKSTATT_IN_TEST", raising=False)
    monkeypatch.setattr("builtins.input", lambda *a, **kw: "n")
    s = _state(tmp_path)
    assert loop._human_gate(s) == 1
    ev = _kind(tmp_path, "loop_human_gate_rejected")
    assert len(ev) == 1
    assert ev[0]["antwort"] == "n"


# =====================================================================
# Pfad 9: 'e' (edit) -> rekursiv, dann 'j' -> rc=0
# =====================================================================

def test_gate_edit_rekursiv(tmp_path, monkeypatch, cfg_file):
    """Zwei input()-Aufrufe: erst 'e' (Edit), dann 'j'."""
    cfg_file.write_text("require_human_approval: true\n",
                        encoding="utf-8")
    monkeypatch.delenv("WERKSTATT_IN_TEST", raising=False)
    antworten = iter(["e", "", "j"])

    def _fake_input(*a, **kw):
        return next(antworten)

    monkeypatch.setattr("builtins.input", _fake_input)
    with patch("werkstatt.loop._committe_zielprojekt",
               return_value=(True, "abc123")):
        s = _state(tmp_path)
        assert loop._human_gate(s) == 0
    # approved-Audit genau einmal (aus der zweiten Runde).
    assert len(_kind(tmp_path, "loop_human_gate_approved")) == 1
