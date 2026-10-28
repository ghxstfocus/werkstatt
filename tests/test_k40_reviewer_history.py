"""K40: Reviewer-Historie in user_content."""
from werkstatt.reviewer import _reviewer_history_block
from werkstatt.state import RunState


def _mk_state() -> RunState:
    s = RunState.__new__(RunState)
    s.reviewer_bugs_history = []  # type: ignore[attr-defined]
    return s


def test_leere_historie_kein_block():
    s = _mk_state()
    assert _reviewer_history_block(s) == ""


def test_historie_mit_bugs():
    s = _mk_state()
    s.reviewer_bugs_history = [  # type: ignore[attr-defined]
        [{"severity": "high", "file": "a.py", "description": "Bug A"}],
        [{"severity": "medium", "file": "b.py", "description": "Bug B"}],
    ]
    block = _reviewer_history_block(s)
    assert "REVIEWER-HISTORIE" in block
    assert "Runde 1" in block
    assert "Runde 2" in block
    assert "Bug A" in block
    assert "Bug B" in block
    assert "NICHT erneut melden" in block


def test_max_3_runden():
    s = _mk_state()
    s.reviewer_bugs_history = [  # type: ignore[attr-defined]
        [{"severity": "low", "file": f"f{i}.py", "description": f"B{i}"}]
        for i in range(5)
    ]
    block = _reviewer_history_block(s)
    assert "B4" in block
    assert "B0" not in block
