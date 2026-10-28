"""K22: _korrigiere_builder_action testet Action-Live-Korrektur."""
from pathlib import Path

from werkstatt.builder import _korrigiere_builder_action


def _mk(tmp_path: Path, rel: str, exists: bool) -> Path:
    if exists:
        f = tmp_path / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("alt\n")
    return tmp_path


def test_create_auf_existierend_wird_update(tmp_path):
    _mk(tmp_path, "x.py", exists=True)
    t = {"action": "create", "task_files": ["x.py"]}
    act = _korrigiere_builder_action(t, tmp_path, "test")
    assert act == "update"
    assert t["action"] == "update"


def test_update_auf_fehlend_bleibt_update_fail_closed(tmp_path):
    """K22b: update + fehlt -> NICHT korrigiert (fail-closed)."""
    _mk(tmp_path, "y.py", exists=False)
    t = {"action": "update", "task_files": ["y.py"]}
    act = _korrigiere_builder_action(t, tmp_path, "test")
    assert act == "update"
    assert t["action"] == "update"


def test_create_auf_fehlend_bleibt_create(tmp_path):
    _mk(tmp_path, "z.py", exists=False)
    t = {"action": "create", "task_files": ["z.py"]}
    act = _korrigiere_builder_action(t, tmp_path, "test")
    assert act == "create"


def test_update_auf_existierend_bleibt_update(tmp_path):
    _mk(tmp_path, "w.py", exists=True)
    t = {"action": "update", "task_files": ["w.py"]}
    act = _korrigiere_builder_action(t, tmp_path, "test")
    assert act == "update"


def test_architect_wird_ignoriert(tmp_path):
    _mk(tmp_path, "a.py", exists=True)
    t = {"action": "architect", "task_files": ["a.py"]}
    act = _korrigiere_builder_action(t, tmp_path, "test")
    assert act == "architect"
    assert t["action"] == "architect"


def test_ohne_task_files_unveraendert(tmp_path):
    t = {"action": "create", "task_files": []}
    act = _korrigiere_builder_action(t, tmp_path, "test")
    assert act == "create"
