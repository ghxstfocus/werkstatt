"""K11: _zerlege_in_sub_tasks — tiefe + Metriken definiert."""
import inspect

from werkstatt.planner import _zerlege_in_sub_tasks


def test_keine_nackte_tiefe() -> None:
    src = inspect.getsource(_zerlege_in_sub_tasks)
    assert " or tiefe " not in src
    assert " tiefe >= " not in src
    assert " tiefe + " not in src
    assert '"tiefe": tiefe' not in src


def test_split_tiefe_gelesen() -> None:
    src = inspect.getsource(_zerlege_in_sub_tasks)
    assert "split_tiefe" in src
    assert "_tiefe" in src


def test_metriken_definiert() -> None:
    src = inspect.getsource(_zerlege_in_sub_tasks)
    assert "_schritte =" in src
    assert "_bullets =" in src
    assert "_komplexitaet =" in src


def test_import_ok() -> None:
    """Funktion laesst sich importieren (kein SyntaxError)."""
    assert callable(_zerlege_in_sub_tasks)
