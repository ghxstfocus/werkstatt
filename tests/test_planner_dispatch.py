from __future__ import annotations

import pytest

from werkstatt.roles.planner_dispatch import (
    architect_reasoning_route,
    choose_next_planner_role,
)


@pytest.mark.parametrize(
    ("kwargs", "role", "reason"),
    [
        ({"scout_skip_path": None}, "scout", "scout_evidence_missing"),
        (
            {"scout_skip_path": "src/module.py"},
            "architect",
            "scout_skipped_current_explorer_source_evidence",
        ),
        (
            {"scout_skip_path": None, "completed_role": "scout"},
            "architect",
            "scout_report_needs_design_decision",
        ),
        (
            {
                "scout_skip_path": None,
                "completed_role": "architect",
                "architect_output_ready": True,
            },
            "planner_split",
            "architect_output_needs_task_graph_compilation",
        ),
        (
            {"scout_skip_path": None, "task_graph_ready": True},
            None,
            "validated_task_graph_ready",
        ),
        (
            {
                "scout_skip_path": "src/module.py",
                "completed_role": "scout",
                "deterministic_task_graph_ready": True,
            },
            None,
            "validated_deterministic_task_graph_ready",
        ),
        (
            {"scout_skip_path": None, "scout_already_fulfilled": True},
            None,
            "scout_reports_goal_already_fulfilled",
        ),
    ],
)
def test_planner_dispatch_selects_only_the_next_missing_capability(
    kwargs: dict[str, object], role: str | None, reason: str,
) -> None:
    decision = choose_next_planner_role(**kwargs)

    assert decision.role == role
    assert decision.reason == reason


def test_architect_reasoning_is_independent_of_scout_skip() -> None:
    assert architect_reasoning_route(
        "Korrigiere src/module.py", "src/module.py",
    ) == (False, "explorer_belegte_routine_einzeldatei")
    assert architect_reasoning_route(
        "Korrigiere die Berechtigungsprüfung in src/module.py",
        "src/module.py",
    ) == (True, "komplexitaetsmarker:sicherheit")
    assert architect_reasoning_route(
        "Aendere und verifiziere src/module.py", "src/module.py",
    ) == (True, "mehrere_aktionsschritte")
    assert architect_reasoning_route("Korrigiere mehrere Dateien", None) == (
        True, "scout_oder_breitere_belegsuche_erforderlich",
    )


def test_planner_dispatch_rejects_unknown_completed_role() -> None:
    with pytest.raises(ValueError, match="Unbekannte abgeschlossene Planner-Rolle"):
        choose_next_planner_role(
            scout_skip_path=None, completed_role="builder",
        )
