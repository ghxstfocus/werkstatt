"""K15: Split-Prompt enthaelt Interface-Grenze-Regel."""
from werkstatt.planner import (
    PLANNER_SPLIT_SINGLE_SYSTEM,
    PLANNER_SPLIT_SYSTEM,
)


def test_interface_grenze_im_split_prompt() -> None:
    assert "INTERFACE-GRENZE" in PLANNER_SPLIT_SYSTEM


def test_groesse_50_bis_150_im_split_prompt() -> None:
    assert "50-150 Zeilen" in PLANNER_SPLIT_SYSTEM


def test_keine_50_zeilen_regel_mehr() -> None:
    assert "Jeder Sub-Task < 50 Zeilen" not in PLANNER_SPLIT_SYSTEM


def test_interface_grenze_im_single_prompt() -> None:
    assert "vollstaendiges, reviewbares" in PLANNER_SPLIT_SINGLE_SYSTEM


def test_groesse_auch_im_single_prompt() -> None:
    assert "50-150 Zeilen" in PLANNER_SPLIT_SINGLE_SYSTEM


def test_keine_800_zeichen_regel_mehr() -> None:
    assert "< 800 Zeichen" not in PLANNER_SPLIT_SINGLE_SYSTEM
