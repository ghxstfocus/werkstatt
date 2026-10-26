"""K13: _k13_rc — rc=0 nur wenn tasks_ok>0."""
from werkstatt.loop import _k13_rc


def test_rc_0_bei_tasks_ok_positiv() -> None:
    assert _k13_rc(0, 1) == 0


def test_rc_1_bei_null_tasks_ok() -> None:
    assert _k13_rc(0, 0) == 1


def test_rc_1_bei_negativem_tasks_ok() -> None:
    assert _k13_rc(0, -1) == 1


def test_rc_1_bleibt_1() -> None:
    assert _k13_rc(1, 5) == 1


def test_rc_1_bleibt_1_bei_null_tasks_ok() -> None:
    assert _k13_rc(1, 0) == 1


def test_rc_2_bleibt_2() -> None:
    assert _k13_rc(2, 5) == 2
