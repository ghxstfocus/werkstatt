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
        project_dir=Path.cwd(),
        tasks=[],
        tests=[{"name": "t"}],
        akzeptanzkriterien=["criterion"],
        phasen=[],
        architect_prosa=None,
    )


def _run_local_planner_gate(monkeypatch) -> None:
    from hooks.planner_gate import check_plan

    monkeypatch.setattr(
        _loop,
        "_call_hook",
        lambda name, payload: (
            check_plan(payload)
            if name == "planner_gate.py"
            else {"allow": True, "reason": "unhandled test hook"}
        ),
    )


def test_k5_doku_task_ohne_phasen_wird_abgelehnt(monkeypatch) -> None:
    _run_local_planner_gate(monkeypatch)
    st = _State()
    st.tasks = [{
        "id": "t1", "task_files": ["docs/STATUS.md"], "action": "update",
        "criterion_refs": ["AC1"],
    }]
    assert _loop._plan_gate(st) is False, "Doku-Task muss abgelehnt werden"
    assert getattr(st, "last_planner_info", None) is not None


def test_k5_sauberer_task_ohne_phasen_ok(monkeypatch) -> None:
    _run_local_planner_gate(monkeypatch)
    st = _State()
    st.tasks = [{
        "id": "t1", "task_files": ["app/foo.py"], "action": "update",
        "criterion_refs": ["AC1"],
    }]
    assert _loop._plan_gate(st) is True


def test_k5_gueltige_phasen_ok(monkeypatch) -> None:
    _run_local_planner_gate(monkeypatch)
    st = _State()
    st.tasks = [{"id": "t1", "task_files": ["app/foo.py"], "action": "update",
                 "phase_id": "p1", "criterion_refs": ["AC1"]}]
    st.phasen = [{"id": "p1"}]
    assert _loop._plan_gate(st) is True


def test_k5_task_mit_falscher_phase_id_abgelehnt(monkeypatch) -> None:
    _run_local_planner_gate(monkeypatch)
    st = _State()
    st.tasks = [{"id": "t1", "task_files": ["app/foo.py"], "action": "update",
                 "phase_id": "p_falsch", "criterion_refs": ["AC1"]}]
    st.phasen = [{"id": "p1"}]
    assert _loop._plan_gate(st) is False
