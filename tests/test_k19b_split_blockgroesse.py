"""Planner-Prosa bleibt vollständig; Task-Merges bleiben begrenzt."""
import inspect

from werkstatt import planner


def _source(func) -> str:
    return inspect.getsource(func)


def test_extrahiere_prosa_abschnitt_erhaelt_lange_architect_anweisung():
    start = "## werkstatt/demo.py"
    end = "## Ende"
    body = "vollstaendige Anweisung " * 180
    prose = f"{start}\n{body}\n{end}\nWeitere Phase"

    extracted = planner._extrahiere_prosa_abschnitt(prose, start, end)

    assert extracted == f"{start}\n{body}\n{end}"
    assert len(extracted) > 2500


def test_merge_grenze_ist_1800():
    """K41: max_merged_len von 2500 auf 1800 gesenkt.

    2500 erlaubte Mega-Tasks (>200 Zeilen Code), die der Builder
    nicht sauber baut. 1800 passt zu K15c (50-150 Zeilen pro Task).
    """
    sig = inspect.signature(planner._merge_mini_tasks)
    assert sig.parameters["max_merged_len"].default == 1800
