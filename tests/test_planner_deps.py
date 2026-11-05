"""OP-163b: Deterministische Dep-Extraktion.

Zwei Pfade:
  1. Architect-Block 5 (strukturiert, Vorrang)
  2. task_files-Heuristik (Fallback, wenn Block fehlt)

Live-Beleg Loop-Test-4 (2026-11-05): alle 8 Tasks deps=[],
t6/t7/t8 liefen parallel zu t1-t5.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/opt/werkstatt")

from werkstatt.planner import (
    _leite_deps_deterministisch,
    _parse_architect_deps_block,
)


def _tasks_loop4():
    return [
        {"id": "t1", "task_files": ["werkstatt/state.py"]},
        {"id": "t2", "task_files": ["werkstatt/gates.py"]},
        {"id": "t3", "task_files": ["werkstatt/builder.py"]},
        {"id": "t4", "task_files": ["werkstatt/planner.py"]},
        {"id": "t5", "task_files": ["werkstatt/pipeline_phases.py"]},
        {"id": "t6", "task_files": ["tools/state_inventory.py"]},
        {"id": "t7", "task_files": ["tests/test_gates.py"]},
        {"id": "t8", "task_files": ["docs/STATE-INVENTUR.md"]},
    ]


# ============ Architect-Block-Parser ============

def test_parse_block_mit_deps():
    prosa = (
        "## 3. Wie sieht die Loesung aus?\n"
        "## werkstatt/state.py\nDocstring.\n\n"
        "## 5. Welche Dateien haengen voneinander ab?\n"
        "- werkstatt/state.py: (keine)\n"
        "- tests/test_gates.py: werkstatt/state.py, werkstatt/gates.py\n"
        "\n"
        "DEINE ROLLE IM LOOP\n"
    )
    found, deps = _parse_architect_deps_block(prosa)
    assert found is True
    assert deps["werkstatt/state.py"] == []
    assert deps["tests/test_gates.py"] == [
        "werkstatt/state.py", "werkstatt/gates.py",
    ]


def test_parse_block_nicht_vorhanden():
    prosa = "## 3. Wie sieht die Loesung aus?\n## a.py\nFoo.\n"
    found, deps = _parse_architect_deps_block(prosa)
    assert found is False
    assert deps == {}


# ============ Pfad 1: Architect-Block hat Vorrang ============

def test_architect_block_hat_vorrang():
    """Strukturierter Block ueberschreibt Fallback-Heuristik."""
    prosa = (
        "## 5. Welche Dateien haengen voneinander ab?\n"
        "- werkstatt/state.py: (keine)\n"
        "- werkstatt/gates.py: (keine)\n"
        "- werkstatt/builder.py: (keine)\n"
        "- werkstatt/planner.py: (keine)\n"
        "- werkstatt/pipeline_phases.py: (keine)\n"
        "- tools/state_inventory.py: werkstatt/state.py\n"
        "- tests/test_gates.py: werkstatt/state.py, werkstatt/gates.py\n"
        "- docs/STATE-INVENTUR.md: werkstatt/state.py, tests/test_gates.py\n"
        "\n"
        "DEINE ROLLE IM LOOP\n"
    )
    out = _leite_deps_deterministisch(_tasks_loop4(), prosa)
    by_id = {t["id"]: t for t in out}
    assert by_id["t1"].get("dependencies") in (None, [])
    assert by_id["t6"]["dependencies"] == ["t1"]
    assert set(by_id["t7"]["dependencies"]) == {"t1", "t2"}
    assert set(by_id["t8"]["dependencies"]) == {"t1", "t7"}


def test_architect_block_leer_keine_deps():
    """Wenn der Architect explizit '(keine)' schreibt, keine Fallback-Heuristik."""
    prosa = (
        "## 5. Welche Dateien haengen voneinander ab?\n"
        "- (keine)\n"
        "\n"
        "DEINE ROLLE IM LOOP\n"
    )
    out = _leite_deps_deterministisch(_tasks_loop4(), prosa)
    for t in out:
        assert t.get("dependencies") in (None, [])


# ============ Pfad 2: Fallback-Heuristik ============

def test_fallback_loop4_muster():
    """Ohne Architect-Block: task_files-Heuristik greift."""
    out = _leite_deps_deterministisch(_tasks_loop4(), prosa="")
    by_id = {t["id"]: t for t in out}
    _codes = {"t1", "t2", "t3", "t4", "t5"}
    for tid in _codes:
        assert by_id[tid].get("dependencies") in (None, [])
    assert set(by_id["t6"]["dependencies"]) == _codes
    assert set(by_id["t7"]["dependencies"]) == _codes
    assert set(by_id["t8"]["dependencies"]) == _codes | {"t6", "t7"}


def test_bestehende_deps_werden_gemerged():
    """Manuell gesetzte deps bleiben, auch im Fallback."""
    tasks = [
        {"id": "t1", "task_files": ["werkstatt/a.py"]},
        {"id": "t2", "task_files": ["werkstatt/b.py"]},
        {"id": "t3", "task_files": ["tests/test_x.py"],
         "dependencies": ["t2"]},
    ]
    out = _leite_deps_deterministisch(tasks, prosa="")
    by_id = {t["id"]: t for t in out}
    assert set(by_id["t3"]["dependencies"]) == {"t1", "t2"}
