"""K19b: Split- und Fallback-Cuts konsistent auf 2500 (K15c)."""
import inspect

from werkstatt import planner


def _source(func) -> str:
    return inspect.getsource(func)


def test_llm_split_einzel_task_cut_ist_2500():
    src = _source(planner._llm_split_einzel_task)
    assert "> 2500" in src
    # Alter 800-Cut darf nicht mehr vorkommen.
    assert "> 800" not in src
    assert "0, 800)" not in src


def test_zerlege_in_sub_tasks_fallback_ist_2500():
    src = _source(planner._zerlege_in_sub_tasks)
    # 800 darf nur noch im Nachbar-Kommentar (Legacy) vorkommen,
    # nicht als Cut mehr.
    assert "0, 800)" not in src
    assert "[:800]" not in src
    # 2500-Fallback muss vorhanden sein.
    assert "0, 2500)" in src or "[:2500]" in src


def test_extrahiere_prosa_abschnitt_ist_2500():
    src = _source(planner._extrahiere_prosa_abschnitt)
    assert "0, 2500)" in src or "[:2500]" in src


def test_merge_grenze_ist_1800():
    """K41: max_merged_len von 2500 auf 1800 gesenkt.

    2500 erlaubte Mega-Tasks (>200 Zeilen Code), die der Builder
    nicht sauber baut. 1800 passt zu K15c (50-150 Zeilen pro Task).
    """
    sig = inspect.signature(planner._merge_mini_tasks)
    assert sig.parameters["max_merged_len"].default == 1800
