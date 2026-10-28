"""K20b: create auf Datei, die frueherer Task anlegt -> update."""
from werkstatt.planner import _korrigiere_aktion_sequenziell


def test_zweiter_create_auf_selber_datei_wird_update():
    tasks = [
        {"action": "create", "task_files": ["a.py"]},
        {"action": "create", "task_files": ["a.py"]},
    ]
    _korrigiere_aktion_sequenziell(tasks, "/tmp", "p")
    assert tasks[0]["action"] == "create"
    assert tasks[1]["action"] == "update"


def test_dritter_create_auf_selber_datei_wird_update():
    tasks = [
        {"action": "create", "task_files": ["a.py"]},
        {"action": "create", "task_files": ["a.py"]},
        {"action": "create", "task_files": ["a.py"]},
    ]
    _korrigiere_aktion_sequenziell(tasks, "/tmp", "p")
    assert tasks[0]["action"] == "create"
    assert tasks[1]["action"] == "update"
    assert tasks[2]["action"] == "update"


def test_verschiedene_dateien_unveraendert():
    tasks = [
        {"action": "create", "task_files": ["a.py"]},
        {"action": "create", "task_files": ["b.py"]},
    ]
    _korrigiere_aktion_sequenziell(tasks, "/tmp", "p")
    assert tasks[0]["action"] == "create"
    assert tasks[1]["action"] == "create"


def test_update_bleibt_update():
    tasks = [
        {"action": "update", "task_files": ["a.py"]},
        {"action": "update", "task_files": ["a.py"]},
    ]
    _korrigiere_aktion_sequenziell(tasks, "/tmp", "p")
    assert tasks[0]["action"] == "update"
    assert tasks[1]["action"] == "update"


def test_create_nach_update_bleibt_create():
    tasks = [
        {"action": "update", "task_files": ["a.py"]},
        {"action": "create", "task_files": ["a.py"]},
    ]
    _korrigiere_aktion_sequenziell(tasks, "/tmp", "p")
    # update legt nicht an -> create bleibt create
    assert tasks[0]["action"] == "update"
    assert tasks[1]["action"] == "create"
