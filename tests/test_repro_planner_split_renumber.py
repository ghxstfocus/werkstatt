"""Regression tests for task IDs and dependencies after planner splitting."""
from __future__ import annotations

from pathlib import Path

import werkstatt
from werkstatt.planner import _merge_mini_tasks
from werkstatt.task_graph import _topo_sort_tasks, remap_dependencies_to_split_leaves

_ROOT = Path(__file__).resolve().parents[1]


def _task(task_id: str, dependencies: list[str], *, size: int = 1_000,
          file: str = "docs/STATUS.md") -> dict:
    return {
        "id": task_id,
        "name": task_id,
        "action": "update",
        "task_files": [file],
        "description": "x" * size,
        "dependencies": dependencies,
        "criterion_refs": ["AC1"],
    }


def test_importpfad_ist_der_checkout_der_tests() -> None:
    module_path = Path(werkstatt.__file__).resolve()
    assert module_path.is_relative_to(_ROOT), module_path


def test_renumbering_schreibt_dependencies_mit_um() -> None:
    tasks = [
        _task("t1_a", []),
        _task("t1_b", ["t1_a"]),
        _task("t1_c", ["t1_b"]),
        _task("t2", ["t1_a"]),
        _task("t3", ["t2"]),
        _task("t4", ["t3"]),
    ]

    result = _merge_mini_tasks(tasks)

    assert [task["id"] for task in result] == [f"t{i}" for i in range(1, 7)]
    assert result[1]["dependencies"] == ["t1"]
    assert result[2]["dependencies"] == ["t2"]
    assert result[3]["dependencies"] == ["t1"]
    assert [task["id"] for task in _topo_sort_tasks(result)] == [
        f"t{i}" for i in range(1, 7)
    ]


def test_gemergte_id_wird_auf_ueberlebenden_task_abgebildet() -> None:
    tasks = [
        _task("t1_a", [], size=300),
        _task("t1_b", ["t1_a", "t1_b"], size=300),
        _task("t2", ["t1_a", "t1_b", "t9"], size=300,
              file="werkstatt/planner.py"),
    ]

    result = _merge_mini_tasks(tasks)

    assert [task["id"] for task in result] == ["t1", "t2"]
    assert result[0]["dependencies"] == []
    assert result[1]["dependencies"] == ["t1", "t9"]


def test_unbekannte_dependency_bleibt_unveraendert() -> None:
    result = _merge_mini_tasks([
        _task("t1_a", [], file="a.py"),
        _task("t2", ["t9"], file="b.py"),
    ])

    assert result[1]["id"] == "t2"
    assert result[1]["dependencies"] == ["t9"]


def test_dependency_on_recursively_split_task_maps_to_surviving_leaves() -> None:
    tasks = [
        _task("t4_b_a_x", [], file="a.py"),
        _task("t4_b_a_y", ["t4_b_a_x"], file="b.py"),
        _task("t4_b_b", ["t4_b_a_y"], file="c.py"),
        _task("t8", ["t4_b"], file="d.py"),
    ]
    remap_dependencies_to_split_leaves(tasks)
    assert tasks[-1]["dependencies"] == ["t4_b_a_y", "t4_b_b"]
    assert _topo_sort_tasks(tasks)[-1]["id"] == "t8"
