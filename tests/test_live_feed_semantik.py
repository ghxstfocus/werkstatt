"""OP-394: Semantische Aktionen fuer Live-Feed (statt technischer Kinds).

Der User sieht im Live-Feed heute technische Event-Kinds
(`loop_phase`, `gate_open`). Nach OP-394 liefert `_tl_detail`
semantische Verben ("Architect denkt nach", "Antwort: j").
"""
from __future__ import annotations


def test_semantik_loop_phase_architect():
    from werkstatt.web.inspector import _tl_detail
    assert _tl_detail("loop_phase", {"phase": "architect"}) == "denkt nach"


def test_semantik_loop_phase_planner():
    from werkstatt.web.inspector import _tl_detail
    assert _tl_detail("loop_phase", {"phase": "planner"}) == "splittet Plan"


def test_semantik_loop_phase_builder():
    from werkstatt.web.inspector import _tl_detail
    assert _tl_detail("loop_phase", {"phase": "build"}) == "baut"
    assert _tl_detail("loop_phase", {"phase": "builder"}) == "baut"


def test_semantik_gate_open():
    from werkstatt.web.inspector import _tl_detail
    result = _tl_detail("gate_open", {"prompt": "Plan ausfuehren?"})
    assert "öffnet Gate" in result
    assert "Plan ausfuehren" in result


def test_semantik_gate_answered():
    from werkstatt.web.inspector import _tl_detail
    assert _tl_detail("gate_answered", {"answer": "j"}) == "Antwort: j"


def test_semantik_loop_plan_shown():
    from werkstatt.web.inspector import _tl_detail
    assert "Plan-Gate" in _tl_detail("loop_plan_shown", {})


def test_semantik_loop_started():
    from werkstatt.web.inspector import _tl_detail
    assert _tl_detail("loop_started", {}) == "Loop startet"


def test_project_coordinator_decision_is_visible_in_chat_activity():
    from datetime import UTC, datetime

    from werkstatt.web.inspector import _tl_aggregate_aktiv, _tl_detail

    event = {
        "kind": "loop_run_coordinator_decision",
        "timestamp": datetime.now(UTC).isoformat(),
        "payload": {
            "decision": "prepare_approved_work_graph",
            "action": "planner_scout",
            "reason": "project_coordinator_selected_scout",
            "coordinator_model_choice": {
                "role": "scout",
                "source": "project_chat_model",
            },
        },
    }

    detail = _tl_detail(event["kind"], event["payload"])
    activity = _tl_aggregate_aktiv([event])

    assert "Der Projektchat ruft Scout" in detail
    assert activity["rolle"] == "loop"
    assert "planner_scout" in activity["aktion"]


def test_semantik_loop_human_gate_eof():
    from werkstatt.web.inspector import _tl_detail
    result = _tl_detail("loop_human_gate_eof", {})
    assert "EOF" in result or "Human-Gate" in result
