"""OP-381g: _phase_tasks_loop emittiert loop_phase:build:start.

Live-Bug 2026-11-09 19:10: Builder/Verify/Reflection/Reviewer-Events
hatten keinen loop_phase-Marker -> aggregate_timeline haengte sie alle
unter den letzten Knoten (Plan), 104 children.

Der Test ist ein Source-Scan (kein voller Integrationstest — 
_phase_tasks_loop braucht State + PhaseState + Task-Fortschritt).
Regress-Barriere: Test verhindert, dass der Marker entfernt wird.

Echte Verhaltens-Verifikation: Live-Loop-Start, Timeline muss
"Build" als eigenen Knoten zeigen.
"""
from __future__ import annotations

from pathlib import Path


def test_tasks_py_emittiert_loop_phase_build():
    """Source-Scan: audit('loop_phase', {'phase': 'build'}) muss in
    _phase_tasks_loop VOR dem while-True-Task-Loop stehen."""
    src = Path("werkstatt/phases/tasks.py").read_text(encoding="utf-8")

    marker = 'audit("loop_phase", {"phase": "build"'
    marker_pos = src.find(marker)
    assert marker_pos > 0, (
        "tasks.py muss loop_phase:build emittieren, sonst landen alle "
        "Builder/Verify/Reflection-Events unter dem letzten Knoten"
    )

    # while True NACH dem Marker suchen (ab marker_pos, nicht rueckwaerts)
    while_pos = src.find("while True:", marker_pos)
    assert while_pos > 0, (
        "_phase_tasks_loop hat keinen while-True-Loop nach dem Marker?"
    )
    assert while_pos > marker_pos, (
        f"loop_phase:build muss VOR dem while-True-Loop stehen "
        f"(marker@{marker_pos}, while@{while_pos})"
    )



def test_task_outcome_event_has_stable_id_and_state_evidence(
    monkeypatch, tmp_path,
):
    from werkstatt.phases import tasks

    events = []
    monkeypatch.setattr(tasks, "audit", lambda *args: events.append(args))

    tasks._audit_task_ok(
        True, "t-build-api", "API bauen", tmp_path, "demo",
        via="reflection",
    )

    assert len(events) == 1
    kind, payload = events[0][:2]
    assert kind == "loop_task_ok"
    assert payload["task_id"] == "t-build-api"
    assert payload["status"] == "done"
    assert payload["result_summary"]
    assert payload["evidence"] == ["Phase-State: done"]
    assert payload["via"] == "reflection"


def test_task_outcome_event_omitted_without_done_transition(
    monkeypatch, tmp_path,
):
    from werkstatt.phases import tasks

    events = []
    monkeypatch.setattr(tasks, "audit", lambda *args: events.append(args))

    tasks._audit_task_ok(
        False, "t-review", "Review", tmp_path, "demo",
    )

    assert events == []
