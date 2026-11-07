"""OP-186: Planner-JSON-Fallback + Zieldatei-Cap.

Loop-Test 10 (2026-11-07 13:42): der JSON-Split-Output war
truncated (planner_split_json_fehler), der Fallback setzte
alle 30 Explorer-key_files als task_files eines Tasks. Der
Builder kann so einen 30-Dateien-Task nicht reviewen.

Drei Fixes, alle hier getestet:
1. _parse_json_robust toleriert truncation via Klammern-Repair.
2. _fallback_task_von_prosa nimmt nur 1 Zieldatei.
3. _cap_task_files als Defense-in-Depth: max 5 Files pro Task.
"""
from __future__ import annotations

from unittest.mock import MagicMock

from werkstatt import planner

# ============ Unit: _parse_json_robust ============

def test_parse_json_robust_vollstaendig() -> None:
    raw = '{"tasks": [{"id": "t1"}]}'
    assert planner._parse_json_robust(raw) == {"tasks": [{"id": "t1"}]}


def test_parse_json_robust_mit_prosa_prefix() -> None:
    raw = 'Vorwort\n{"tasks": [{"id": "t1"}]}\nNachwort'
    assert planner._parse_json_robust(raw) == {"tasks": [{"id": "t1"}]}


def test_parse_json_robust_truncated_wird_repariert() -> None:
    """Abgeschnittenes JSON: offene Klammern werden ergaenzt."""
    raw = '{"tasks": [{"id": "t1", "name": "X"}'
    parsed = planner._parse_json_robust(raw)
    assert parsed is not None, f"Truncated JSON nicht repariert: {raw!r}"
    assert isinstance(parsed.get("tasks"), list)
    assert parsed["tasks"][0]["id"] == "t1"


def test_parse_json_robust_lehnt_garbage_ab() -> None:
    assert planner._parse_json_robust("kein json") is None
    assert planner._parse_json_robust("") is None


# ============ Unit: _fallback_task_von_prosa ============

def test_fallback_task_ein_file() -> None:
    """OP-186: Fallback darf nur 1 Datei als task_files haben."""
    task = planner._fallback_task_von_prosa(
        "prosa", ["a.py", "b.py", "c.py"])
    assert task["task_files"] == ["a.py"]
    assert task["id"] == "t1"
    assert task["name"] == "Architect-Loesung umsetzen"


def test_fallback_task_leer() -> None:
    task = planner._fallback_task_von_prosa("prosa", [])
    assert task["task_files"] == []


# ============ Unit: _cap_task_files ============

def test_cap_task_files_fuenf() -> None:
    """Cap bei 5 Dateien pro Task, audit-Event."""
    tasks = [{"id": "t1", "task_files": [f"f{i}.py" for i in range(10)]}]
    capped = planner._cap_task_files(tasks, MagicMock(), "test", max_files=5)
    assert len(capped[0]["task_files"]) == 5
    assert capped[0]["task_files"] == [
        "f0.py", "f1.py", "f2.py", "f3.py", "f4.py"]


def test_cap_task_files_unveraendert() -> None:
    """Weniger als 5 Files: keine Aenderung."""
    tasks = [{"id": "t1", "task_files": ["a.py", "b.py"]}]
    capped = planner._cap_task_files(tasks, MagicMock(), "test")
    assert capped[0]["task_files"] == ["a.py", "b.py"]


def test_cap_task_files_leer() -> None:
    """Leere Task-Liste: keine Aenderung."""
    assert planner._cap_task_files([], MagicMock(), "test") == []
