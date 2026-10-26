"""K15a: _merge_mini_tasks merged benachbarte Tasks mit gleicher Datei."""
from werkstatt.planner import _merge_mini_tasks


def _t(id_, file, desc, action="update", deps=None):
    return {
        "id": id_, "name": f"task {id_}", "action": action,
        "task_files": [file], "description": desc,
        "dependencies": deps or [],
    }


def test_merge_gleiche_datei() -> None:
    tasks = [
        _t("t1", "a.py", "x" * 300),
        _t("t2", "a.py", "y" * 300),
    ]
    out = _merge_mini_tasks(tasks)
    assert len(out) == 1
    assert out[0]["id"] == "t1"


def test_nicht_merge_verschiedene_dateien() -> None:
    tasks = [
        _t("t1", "a.py", "x" * 300),
        _t("t2", "b.py", "y" * 300),
    ]
    out = _merge_mini_tasks(tasks)
    assert len(out) == 2


def test_nicht_merge_action_wechsel() -> None:
    tasks = [
        _t("t1", "a.py", "x" * 300, action="update"),
        _t("t2", "a.py", "y" * 300, action="create"),
    ]
    out = _merge_mini_tasks(tasks)
    assert len(out) == 2


def test_nicht_merge_zu_gross() -> None:
    tasks = [
        _t("t1", "a.py", "x" * 1500),
        _t("t2", "a.py", "y" * 1500),
    ]
    out = _merge_mini_tasks(tasks)
    assert len(out) == 2


def test_merge_3_tasks() -> None:
    tasks = [
        _t("t1", "a.py", "x" * 300),
        _t("t2", "a.py", "y" * 300),
        _t("t3", "a.py", "z" * 300),
    ]
    out = _merge_mini_tasks(tasks)
    assert len(out) == 1
    assert out[0]["description"].count("x") == 300
    assert out[0]["description"].count("z") == 300


def test_ids_neu_vergeben() -> None:
    tasks = [
        _t("t1", "a.py", "x" * 300),
        _t("t2", "b.py", "y" * 300),
        _t("t3", "c.py", "z" * 300),
    ]
    out = _merge_mini_tasks(tasks)
    assert [t["id"] for t in out] == ["t1", "t2", "t3"]


def test_leere_liste() -> None:
    assert _merge_mini_tasks([]) == []


def test_merge_dependencies_vereinigt() -> None:
    tasks = [
        _t("t1", "a.py", "x" * 300, deps=[]),
        _t("t2", "a.py", "y" * 300, deps=["t9"]),
    ]
    out = _merge_mini_tasks(tasks)
    assert len(out) == 1
    assert "t9" in out[0]["dependencies"]
