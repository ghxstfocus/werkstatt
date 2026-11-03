"""OP-047: Tests fuer _doku_post_check.

Semantik (Nachbesserung 2026-11-03):
- Trigger "nur X.md" -> SINGLE-TARGET: nur Tasks die X.md anfassen.
- Trigger "keine python" + ".md"/"docs/"/"doku" -> MULTI-FILE:
  alle .md-Tasks bleiben, pro .md-Datei max 1 Task (Kollaps bei Duplikat).
- Kein Trigger (auch "keine python" ohne Doku-Ziel) -> Tasks unveraendert.

Wichtig: "keine python, alle docs aktualisieren" triggert NICHT, weil
weder ".md" noch "docs/" (kein Slash) noch "doku" vorkommt. Der Test
braucht ".md" in der Aufgabe.
"""
from __future__ import annotations

from werkstatt.planner import _doku_post_check


def test_doku_post_check_multi_file() -> None:
    """'keine python' + '.md': 3 verschiedene .md-Tasks bleiben 3."""
    tasks = [
        {"task_files": ["docs/A.md"], "aktion": "patch", "beschreibung": ""},
        {"task_files": ["docs/B.md"], "aktion": "patch", "beschreibung": ""},
        {"task_files": ["docs/C.md"], "aktion": "patch", "beschreibung": ""},
    ]

    ergebnis = _doku_post_check(tasks, aufgabe="keine python, alle .md aktualisieren")

    assert len(ergebnis) == 3
    assert [t["task_files"][0] for t in ergebnis] == ["docs/A.md", "docs/B.md", "docs/C.md"]


def test_doku_post_check_same_file_reduziert() -> None:
    """'keine python' + '.md': 3 Tasks auf dieselbe .md-Datei -> 1 (Kollaps)."""
    tasks = [
        {"task_files": ["docs/A.md"], "aktion": "patch", "beschreibung": ""},
        {"task_files": ["docs/A.md"], "aktion": "patch", "beschreibung": ""},
        {"task_files": ["docs/A.md"], "aktion": "patch", "beschreibung": ""},
    ]

    ergebnis = _doku_post_check(tasks, aufgabe="keine python, alle .md aktualisieren")

    assert len(ergebnis) == 1
    assert ergebnis[0]["task_files"][0] == "docs/A.md"
    assert ergebnis[0] is tasks[0]


def test_doku_post_check_single_target_grossbuchstabe() -> None:
    """'nur docs/A.md': case-insensitiver Vergleich (Task-Files gross)."""
    tasks = [
        {"task_files": ["docs/A.md"], "aktion": "patch", "beschreibung": ""},
        {"task_files": ["docs/B.md"], "aktion": "patch", "beschreibung": ""},
    ]

    ergebnis = _doku_post_check(tasks, aufgabe="nur docs/A.md aendern")

    assert len(ergebnis) == 1
    assert ergebnis[0]["task_files"][0] == "docs/A.md"
