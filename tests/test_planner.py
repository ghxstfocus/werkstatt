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

from unittest import mock

from werkstatt.planner import _doku_post_check, _pruefe_zieldatei_existenz


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


def test_pruefe_zieldatei_existenz_create_bei_kopier_auftrag(tmp_path) -> None:
    """Kopier-Auftrag: Ziel fehlt -> aktion create, source_file gesetzt."""
    task = {
        "task_files": ["werkstatt/control/reflection.py"],
        "aktion": "update",
        "beschreibung": "kopiere reflection",
    }
    aufgabe = "kopiere werkstatt/reflection.py nach werkstatt/control/reflection.py"

    ergebnis = _pruefe_zieldatei_existenz([task], tmp_path, aufgabe)

    assert len(ergebnis) == 1
    assert ergebnis[0]["aktion"] == "create"
    assert ergebnis[0]["source_file"] == "werkstatt/reflection.py"


def test_pruefe_zieldatei_existenz_update_bei_existierender_datei(tmp_path) -> None:
    """Existierende Datei: aktion bleibt update, kein source_file."""
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/A.md").write_text("x", encoding="utf-8")
    task = {"task_files": ["docs/A.md"], "aktion": "update"}
    aufgabe = "docs/A.md ergaenzen"

    ergebnis = _pruefe_zieldatei_existenz([task], tmp_path, aufgabe)

    assert len(ergebnis) == 1
    assert ergebnis[0]["aktion"] == "update"
    assert "source_file" not in ergebnis[0]


def test_pruefe_zieldatei_existenz_fail_closed_ohne_quelle(tmp_path) -> None:
    """Ziel fehlt und keine Quelle ermittelbar: fail-closed + audit."""
    task = {"task_files": ["werkstatt/fehlt.py"], "aktion": "update"}
    aufgabe = "irgendwas ohne kopier-muster"

    with mock.patch("werkstatt.planner.audit") as mock_audit:
        ergebnis = _pruefe_zieldatei_existenz([task], tmp_path, aufgabe)

    assert ergebnis == []
    assert mock_audit.call_count == 1
    assert mock_audit.call_args.args[0] == "planner_update_ziel_fehlt"
    assert mock_audit.call_args.args[1]["ziel"] == "werkstatt/fehlt.py"


def test_pruefe_zieldatei_existenz_source_file_aus_task(tmp_path) -> None:
    """source_file direkt aus Task: aktion create, kein audit."""
    task = {
        "task_files": ["werkstatt/control/x.py"],
        "aktion": "update",
        "source_file": "werkstatt/x.py",
    }

    ergebnis = _pruefe_zieldatei_existenz([task], tmp_path, "")

    assert len(ergebnis) == 1
    assert ergebnis[0]["aktion"] == "create"
    assert ergebnis[0]["source_file"] == "werkstatt/x.py"


def test_pruefe_zieldatei_existenz_create_bei_existierender_datei_wird_update(
    tmp_path,
) -> None:
    """OP-110-Erweiterung: existierende Datei + aktion=create -> update.

    Live-Bug 2026-11-09 19:10: Planner gab OP-376 t1 (inspector.py
    ergaenzen) aktion=create, obwohl inspector.py existierte. Builder
    machte update (Datei-Realitaet), Check erwartete create ->
    builder_patch_invalid -> Reflection 5x gleicher Fehler -> loop_failed.

    Vorher korrigierte die Funktion nur update->create (Datei fehlt),
    nicht create->update (Datei existiert).
    """
    (tmp_path / "werkstatt").mkdir()
    (tmp_path / "werkstatt" / "inspector.py").write_text(
        "# existiert", encoding="utf-8"
    )
    task = {
        "task_files": ["werkstatt/inspector.py"],
        "aktion": "create",
    }

    with mock.patch("werkstatt.planner.audit") as mock_audit:
        ergebnis = _pruefe_zieldatei_existenz([task], tmp_path, "")

    assert len(ergebnis) == 1
    assert ergebnis[0]["aktion"] == "update", (
        f"Existierende Datei + create MUSS zu update werden, "
        f"war {ergebnis[0]['aktion']!r}"
    )
    assert mock_audit.call_count == 1
    assert mock_audit.call_args.args[0] == "planner_create_ziel_existiert"
    assert mock_audit.call_args.args[1]["ziel"] == "werkstatt/inspector.py"
