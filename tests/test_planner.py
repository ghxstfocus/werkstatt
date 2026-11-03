from __future__ import annotations

from werkstatt.planner import _doku_post_check


def test_doku_post_check_multi_file() -> None:
    tasks = [
        {"task_files": ["docs/A.md"], "aktion": "patch", "beschreibung": ""},
        {"task_files": ["docs/B.md"], "aktion": "patch", "beschreibung": ""},
        {"task_files": ["docs/C.md"], "aktion": "patch", "beschreibung": ""},
    ]

    ergebnis = _doku_post_check(tasks, aufgabe="nur docs/A.md aendern")

    assert len(ergebnis) == 3
    assert [t["task_files"][0] for t in ergebnis] == ["docs/A.md", "docs/B.md", "docs/C.md"]


def test_doku_post_check_same_file_reduziert() -> None:
    tasks = [
        {"task_files": ["docs/A.md"], "aktion": "patch", "beschreibung": ""},
        {"task_files": ["docs/A.md"], "aktion": "patch", "beschreibung": ""},
        {"task_files": ["docs/A.md"], "aktion": "patch", "beschreibung": ""},
    ]

    ergebnis = _doku_post_check(tasks, aufgabe="nur docs/A.md aendern")

    assert len(ergebnis) == 1
    assert ergebnis[0]["task_files"][0] == "docs/A.md"
    assert ergebnis[0] is tasks[0]
