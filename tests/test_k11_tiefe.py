"""K11: Planner-Split-Compiler verwaltet Tiefe und Komplexitaetsmetriken."""
import inspect

from werkstatt.planner_task_compiler import run_planner_split_pipeline


def test_keine_nackte_tiefe() -> None:
    src = inspect.getsource(run_planner_split_pipeline)
    assert " or tiefe " not in src
    assert " tiefe >= " not in src
    assert " tiefe + " not in src
    assert '"tiefe": tiefe' not in src


def test_split_tiefe_gelesen() -> None:
    src = inspect.getsource(run_planner_split_pipeline)
    assert "split_tiefe" in src
    assert "_tiefe" in src


def test_metriken_definiert() -> None:
    src = inspect.getsource(run_planner_split_pipeline)
    assert "_schritte =" in src
    assert "_bullets =" in src
    assert "_komplexitaet =" in src


def test_import_ok() -> None:
    """Funktion laesst sich importieren (kein SyntaxError)."""
    assert callable(run_planner_split_pipeline)
