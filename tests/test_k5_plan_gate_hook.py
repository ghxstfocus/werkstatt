"""K5: _plan_gate ruft Doku-Hook auch bei flachem Plan."""
import sys
from pathlib import Path

from werkstatt import loop as _loop

_here = Path(__file__).parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))
from factories import mk_state  # noqa: E402


def _State():
    """Spec-State fuer _plan_gate-Hook-Tests (OP-174 P3-Nachtrag)."""
    return mk_state(
        project_dir=Path("/tmp/k5"),
        tasks=[],
        tests=[{"name": "t"}],
        akzeptanzkriterien=[{"name": "a"}],
        phasen=[],
        architect_prosa=None,
    )


def test_k5_doku_task_ohne_phasen_wird_abgelehnt() -> None:
    st = _State()
    st.tasks = [{"id": "t1", "task_files": ["docs/STATUS.md"], "action": "update"}]
    assert _loop._plan_gate(st) is False, "Doku-Task muss abgelehnt werden"
    assert getattr(st, "last_planner_info", None) is not None


def test_k5_sauberer_task_ohne_phasen_ok() -> None:
    st = _State()
    st.tasks = [{"id": "t1", "task_files": ["app/foo.py"], "action": "update"}]
    assert _loop._plan_gate(st) is True


def test_k5_gueltige_phasen_ok() -> None:
    st = _State()
    st.tasks = [{"id": "t1", "task_files": ["app/foo.py"], "action": "update",
                 "phase_id": "p1"}]
    st.phasen = [{"id": "p1"}]
    assert _loop._plan_gate(st) is True


def test_k5_task_mit_falscher_phase_id_abgelehnt() -> None:
    st = _State()
    st.tasks = [{"id": "t1", "task_files": ["app/foo.py"], "action": "update",
                 "phase_id": "p_falsch"}]
    st.phasen = [{"id": "p1"}]
    assert _loop._plan_gate(st) is False
