"""K20: _korrigiere_aktion korrigiert action anhand Datei-Existenz."""
from pathlib import Path

from werkstatt.planner import _korrigiere_aktion


def _mk(tmp_path: Path, rel: str, exists: bool) -> Path:
    ziel = tmp_path / rel
    if exists:
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text("")
    return tmp_path


def test_update_auf_fehlend_wird_create(tmp_path: Path):
    _mk(tmp_path, "fehlt.py", exists=False)
    t = {"action": "update", "task_files": ["fehlt.py"]}
    _korrigiere_aktion(t, tmp_path, "p")
    assert t["action"] == "create"


def test_create_auf_existierend_wird_update(tmp_path: Path):
    _mk(tmp_path, "da.py", exists=True)
    t = {"action": "create", "task_files": ["da.py"]}
    _korrigiere_aktion(t, tmp_path, "p")
    assert t["action"] == "update"


def test_update_auf_existierend_bleibt_update(tmp_path: Path):
    _mk(tmp_path, "da.py", exists=True)
    t = {"action": "update", "task_files": ["da.py"]}
    _korrigiere_aktion(t, tmp_path, "p")
    assert t["action"] == "update"


def test_create_auf_fehlend_bleibt_create(tmp_path: Path):
    _mk(tmp_path, "fehlt.py", exists=False)
    t = {"action": "create", "task_files": ["fehlt.py"]}
    _korrigiere_aktion(t, tmp_path, "p")
    assert t["action"] == "create"


def test_architect_wird_ignoriert(tmp_path: Path):
    _mk(tmp_path, "fehlt.py", exists=False)
    t = {"action": "architect", "task_files": ["fehlt.py"]}
    _korrigiere_aktion(t, tmp_path, "p")
    assert t["action"] == "architect"


def test_mehrere_dateien_gemischt_unveraendert(tmp_path: Path):
    _mk(tmp_path, "a.py", exists=True)
    _mk(tmp_path, "b.py", exists=False)
    t = {"action": "update", "task_files": ["a.py", "b.py"]}
    _korrigiere_aktion(t, tmp_path, "p")
    assert t["action"] == "update"  # unsicher, nicht anfassen


def test_mehrere_dateien_alle_fehlend_wird_create(tmp_path: Path):
    _mk(tmp_path, "a.py", exists=False)
    _mk(tmp_path, "b.py", exists=False)
    t = {"action": "update", "task_files": ["a.py", "b.py"]}
    _korrigiere_aktion(t, tmp_path, "p")
    assert t["action"] == "create"


def test_leere_task_files_unveraendert(tmp_path: Path):
    t = {"action": "update", "task_files": []}
    _korrigiere_aktion(t, tmp_path, "p")
    assert t["action"] == "update"
