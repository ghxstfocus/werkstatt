from __future__ import annotations

import pytest

from werkstatt.roles.planner_dispatch import (
    architect_reasoning_route,
    choose_next_planner_role,
    direct_builder_route_decision,
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
            {
                "scout_skip_path": "src/settings.py",
                "direct_builder_ready": True,
            },
            "builder_direct",
            "unique_source_bound_edit_ready",
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


def test_direct_builder_route_requires_current_unique_source_edit(tmp_path) -> None:
    source = tmp_path / "src" / "settings.py"
    source.parent.mkdir()
    source.write_text("TIMEOUT = 10\n", encoding="utf-8")

    assert direct_builder_route_decision(
        "Setze TIMEOUT in src/settings.py auf 30",
        "src/settings.py",
        tmp_path,
    ) == (True, "eindeutige_ast_literalzuweisung")
    assert direct_builder_route_decision(
        "Pruefe src/settings.py und erklaere die Ursache",
        "src/settings.py",
        tmp_path,
    ) == (False, "kein_expliziter_literalersetzungsausdruck")


def test_direct_builder_compiles_multiple_explicit_literal_assignments(tmp_path) -> None:
    from werkstatt.roles.builder_direct import build_direct_edit_plan

    source = tmp_path / "src" / "settings.py"
    source.parent.mkdir()
    source.write_text(
        "TIMEOUT = 10  # seconds\nRETRIES = 2\nENABLED = True\n",
        encoding="utf-8",
    )
    task = (
        "Setze TIMEOUT in src/settings.py auf 30 und setze RETRIES "
        "in src/settings.py auf 5"
    )

    plan, reason = build_direct_edit_plan(task, "src/settings.py", tmp_path)

    assert reason == "eindeutige_ast_literalzuweisungen"
    assert plan is not None
    assert plan["atomarer_plan"] is True
    assert [item["zeile"] for item in plan["betroffene_stellen"]] == [1, 2]
    assert [item["neu"] for item in plan["betroffene_stellen"]] == [
        "TIMEOUT = 30  # seconds", "RETRIES = 5",
    ]


@pytest.mark.parametrize(
    ("source_text", "task", "reason"),
    [
        (
            "TIMEOUT = 10\nRETRIES = 2\nRETRIES = 3\n",
            (
                "Setze TIMEOUT in settings.py auf 30 und setze RETRIES "
                "in settings.py auf 5"
            ),
            "zielvariable_nicht_eindeutig",
        ),
        (
            "TIMEOUT = 10\nRETRIES = 2\n",
            (
                "Setze TIMEOUT in settings.py auf 30 und setze RETRIES "
                "in settings.py auf 2"
            ),
            "zielzuweisung_nicht_eindeutig_oder_unveraendert",
        ),
        (
            "TIMEOUT = 10\nRETRIES = 2\n",
            (
                "Setze TIMEOUT in settings.py auf 30 und setze RETRIES "
                "in settings.py auf 5 und dokumentiere die Änderung"
            ),
            "literal_batch_enthaelt_weitere_auftragsteile",
        ),
    ],
)
def test_direct_builder_escalates_ambiguous_or_noop_batch(
    tmp_path, source_text: str, task: str, reason: str,
) -> None:
    from werkstatt.roles.builder_direct import build_direct_edit_plan

    source = tmp_path / "settings.py"
    source.write_text(source_text, encoding="utf-8")

    assert build_direct_edit_plan(task, "settings.py", tmp_path) == (
        None, reason,
    )
