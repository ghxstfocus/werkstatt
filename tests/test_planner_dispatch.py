from __future__ import annotations

import hashlib

import pytest

from werkstatt.roles.planner_dispatch import (
    architect_reasoning_route,
    architect_single_file_task_decision,
    choose_next_planner_role,
    direct_builder_route_decision,
)


@pytest.mark.parametrize(
    ("kwargs", "role", "reason"),
    [
        (
            {
                "scout_skip_path": None,
                "available_evidence": {
                    "user_goal", "project_inventory", "explorer_evidence",
                },
            },
            "scout", "scout_evidence_missing",
        ),
        (
            {
                "scout_skip_path": "src/module.py",
                "available_evidence": {"explorer_source_evidence"},
            },
            "architect",
            "scout_skipped_current_explorer_source_evidence",
        ),
        (
            {
                "scout_skip_path": None,
                "available_evidence": {
                    "user_goal", "scout_report", "current_source_evidence",
                },
            },
            "architect",
            "scout_report_needs_design_decision",
        ),
        (
            {
                "scout_skip_path": None,
                "available_evidence": {
                    "user_goal", "architect_plan", "architect_prose",
                    "acceptance_criteria", "current_source_manifest",
                },
            },
            "planner_split",
            "architect_output_needs_task_graph_compilation",
        ),
        (
            {
                "scout_skip_path": None,
                "available_evidence": {"validated_task_graph"},
            },
            None,
            "validated_task_graph_ready",
        ),
        (
            {
                "scout_skip_path": "src/module.py",
                "available_evidence": {
                    "scout_atomic_plan", "current_source_hashes",
                    "criteria_coverage", "validated_task_graph",
                },
            },
            None,
            "validated_deterministic_task_graph_ready",
        ),
        (
            {
                "scout_skip_path": "src/settings.py",
                "available_evidence": {
                    "explicit_user_edit", "unique_current_source",
                },
                "direct_builder_ready": True,
            },
            "builder_direct",
            "unique_source_bound_edit_ready",
        ),
        (
            {
                "scout_skip_path": None,
                "available_evidence": {
                    "scout_report", "current_source_evidence",
                    "goal_already_fulfilled",
                },
            },
            "architect",
            "scout_completion_claim_requires_independent_verification",
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


def test_planner_dispatch_rejects_unknown_evidence() -> None:
    with pytest.raises(ValueError, match="Unbekannte Planner-Belege"):
        choose_next_planner_role(
            scout_skip_path=None, available_evidence={"raw_model_prompt"},
        )


def test_planner_dispatch_declares_inputs_missing_and_available_evidence() -> None:
    scout = choose_next_planner_role(
        scout_skip_path=None,
        available_evidence={"user_goal"},
    )
    assert scout.role == "scout"
    assert scout.required_evidence == ("user_goal",)
    assert scout.missing_evidence == ("scout_report",)
    assert scout.missing_inputs == ()
    assert scout.available_evidence == ("user_goal",)

    architect = choose_next_planner_role(
        scout_skip_path=None,
        available_evidence={
            "user_goal", "scout_report", "current_source_evidence",
        },
    )
    assert architect.required_evidence == (
        "user_goal", "scout_report", "current_source_evidence",
    )
    assert architect.missing_evidence == ("architect_plan",)
    assert architect.missing_inputs == ()
    assert architect.available_evidence == (
        "current_source_evidence", "scout_report", "user_goal",
    )

    split = choose_next_planner_role(
        scout_skip_path=None,
        available_evidence={
            "user_goal", "architect_plan", "architect_prose",
            "acceptance_criteria", "current_source_manifest",
        },
    )
    assert split.role == "planner_split"
    assert split.required_evidence == (
        "user_goal", "architect_prose", "acceptance_criteria",
        "current_source_manifest",
    )
    assert split.missing_evidence == ("validated_task_graph",)

    direct = choose_next_planner_role(
        scout_skip_path="src/settings.py",
        available_evidence={
            "explicit_user_edit", "unique_current_source",
        },
        direct_builder_ready=True,
    )
    assert direct.role == "builder_direct"
    assert direct.missing_evidence == ()


def test_planner_dispatch_marks_missing_required_input() -> None:
    decision = choose_next_planner_role(
        scout_skip_path=None,
        available_evidence={"scout_report"},
    )

    assert decision.role == "architect"
    assert decision.missing_evidence == ("architect_plan",)
    assert decision.missing_inputs == ("user_goal", "current_source_evidence")
    assert decision.available_evidence == ("scout_report",)


def test_direct_builder_route_requires_current_unique_source_edit(tmp_path) -> None:
    source = tmp_path / "src" / "settings.py"
    source.parent.mkdir()
    source.write_text("TIMEOUT = 10\n", encoding="utf-8")
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    explorer_context = {"key_files": [{
        "file": "src/settings.py",
        "source_complete": True,
        "source_sha256": source_hash,
    }]}

    assert direct_builder_route_decision(
        "Setze TIMEOUT in src/settings.py auf 30",
        "src/settings.py",
        tmp_path,
        explorer_context=explorer_context,
    ) == (True, "eindeutige_ast_literalzuweisung")
    assert direct_builder_route_decision(
        "Pruefe src/settings.py und erklaere die Ursache",
        "src/settings.py",
        tmp_path,
        explorer_context=explorer_context,
    ) == (False, "kein_expliziter_literalersetzungsausdruck")


def test_direct_builder_selected_for_narrow_single_file_edit(tmp_path) -> None:
    from werkstatt.roles.planner_dispatch import (
        build_direct_single_file_task,
    )

    source = tmp_path / "src" / "settings.py"
    source.parent.mkdir()
    source.write_text("def timeout():\n    return 10\n", encoding="utf-8")
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    explorer_context = {"key_files": [{
        "file": "src/settings.py",
        "source_complete": True,
        "source_sha256": source_hash,
    }]}
    goal = "Korrigiere den Rückgabewert von timeout in src/settings.py"

    ready, reason = direct_builder_route_decision(
        goal, "src/settings.py", tmp_path,
        explorer_context=explorer_context,
    )
    task, task_reason, source_sha256 = build_direct_single_file_task(
        goal, "src/settings.py", tmp_path,
    )

    assert ready is True
    assert reason == "eindeutige_explorer_datei_niedriges_risiko"
    assert task_reason == reason
    assert source_sha256 is not None and len(source_sha256) == 64
    assert task == {
        "id": "t1",
        "name": "Builder direkt: src/settings.py",
        "description": (
            "Fuehre ausschliesslich diesen freizugebenden Nutzerauftrag aus: "
            + goal
        ),
        "action": "update",
        "task_files": ["src/settings.py"],
        "dependencies": [],
        "criterion_refs": ["AC1"],
    }


def test_direct_builder_rejects_missing_or_stale_explorer_hash(tmp_path) -> None:
    source = tmp_path / "settings.py"
    source.write_text("def timeout():\n    return 10\n", encoding="utf-8")
    goal = "Korrigiere den Rueckgabewert in settings.py"

    assert direct_builder_route_decision(
        goal, "settings.py", tmp_path, explorer_context={"key_files": []},
    ) == (False, "explorer_quellhash_fehlt_oder_unvollstaendig")

    stale_context = {"key_files": [{
        "file": "settings.py",
        "source_complete": True,
        "source_sha256": "0" * 64,
    }]}
    assert direct_builder_route_decision(
        goal, "settings.py", tmp_path, explorer_context=stale_context,
    ) == (False, "explorer_quellbeleg_veraltet")


@pytest.mark.parametrize(
    "goal",
    [
        "Korrigiere src/settings.py und fuege Tests hinzu",
        "Aendere das Berechtigungsverhalten in src/settings.py",
        "Refaktoriere src/settings.py",
    ],
)
def test_direct_builder_escalates_complex_single_file_edits(
    tmp_path, goal: str,
) -> None:
    source = tmp_path / "settings.py"
    source.write_text("def timeout():\n    return 10\n", encoding="utf-8")
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    explorer_context = {"key_files": [{
        "file": "settings.py",
        "source_complete": True,
        "source_sha256": source_hash,
    }]}

    ready, _reason = direct_builder_route_decision(
        goal, "settings.py", tmp_path,
        explorer_context=explorer_context,
    )

    assert ready is False


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


def test_architect_single_file_task_requires_complete_current_evidence(
    tmp_path,
) -> None:
    source = tmp_path / "src" / "module.py"
    source.parent.mkdir()
    content = "def update_value():\n    return 2\n"
    source.write_text(content, encoding="utf-8")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    prose = (
        "1. Problem\nDas Verhalten soll geaendert werden.\n"
        "2. Dateien\nEine Datei.\n"
        "3. Loesung\n## src/module.py\nAendere update_value so, dass 3 zurueckgegeben wird.\n"
        "4. Tests\nPruefe den neuen Rueckgabewert.\n"
        "5. Welche Dateien haengen voneinander ab? (PFLICHT)\n- (keine)\n"
    )
    manifest = {
        "sources": [{
            "path": "src/module.py",
            "complete": True,
            "source_sha256": digest,
        }],
    }

    task, reason = architect_single_file_task_decision(
        goal="Aendere das Verhalten in src/module.py",
        architect_prose=prose,
        key_files=["src/module.py"],
        source_manifest=manifest,
        project_dir=tmp_path,
    )

    assert reason == "einzelner_unabhaengiger_architect_dateiblock"
    assert task is not None
    assert task["task_files"] == ["src/module.py"]
    assert task["criterion_refs"] == ["AC1"]

    test_task, test_reason = architect_single_file_task_decision(
        goal="Aendere src/module.py und ergaenze einen Regressionstest",
        architect_prose=prose,
        key_files=["src/module.py"],
        source_manifest=manifest,
        project_dir=tmp_path,
    )
    assert test_task is None
    assert test_reason == "ziel_verlangt_weitere_testplanung"


def test_architect_independent_file_set_skips_split_only_with_fresh_proofs(
    tmp_path,
) -> None:
    from werkstatt.roles.planner_dispatch import (
        architect_independent_file_tasks_decision,
    )

    contents = {
        "src/one.py": "def one():\n    return 1\n",
        "src/two.py": "def two():\n    return 2\n",
    }
    sources = []
    for relative, content in contents.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        sources.append({
            "path": relative,
            "complete": True,
            "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    prose = (
        "3. Loesung\n"
        "## src/one.py\nAendere one wie beschrieben.\n"
        "## src/two.py\nAendere two wie beschrieben.\n"
        "5. Welche Dateien haengen voneinander ab? (PFLICHT)\n"
        "- src/one.py: (keine)\n- src/two.py: (keine)\n"
    )
    tasks, reason = architect_independent_file_tasks_decision(
        goal="Implementiere die beschriebenen Aenderungen in zwei Modulen",
        architect_prose=prose,
        key_files=list(contents),
        source_manifest={"sources": sources},
        project_dir=tmp_path,
    )

    assert reason == "kleiner_unabhaengiger_architect_dateisatz"
    assert tasks is not None
    assert [task["task_files"] for task in tasks] == [
        ["src/one.py"], ["src/two.py"],
    ]
    assert all(task["dependencies"] == [] for task in tasks)
    assert all(task["criterion_refs"] == ["AC1"] for task in tasks)


def test_architect_independent_file_set_escalates_dependency_and_test_work(
    tmp_path,
) -> None:
    from werkstatt.roles.planner_dispatch import (
        architect_independent_file_tasks_decision,
    )

    contents = {
        "src/one.py": "def one():\n    return 1\n",
        "src/two.py": "def two():\n    return 2\n",
    }
    sources = []
    for relative, content in contents.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        sources.append({
            "path": relative,
            "complete": True,
            "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    prose = (
        "3. Loesung\n"
        "## src/one.py\nAendere one.\n"
        "## src/two.py\nAendere two.\n"
        "5. Welche Dateien haengen voneinander ab?\n"
        "- src/one.py: (keine)\n- src/two.py: src/one.py\n"
    )
    kwargs = {
        "goal": "Implementiere die beschriebenen Aenderungen in zwei Modulen",
        "architect_prose": prose,
        "key_files": list(contents),
        "source_manifest": {"sources": sources},
        "project_dir": tmp_path,
    }

    tasks, reason = architect_independent_file_tasks_decision(**kwargs)
    assert tasks is None
    assert reason == "architect_abhaengigkeiten_nicht_eindeutig_unabhaengig"

    test_tasks, test_reason = architect_independent_file_tasks_decision(
        **{**kwargs, "goal": kwargs["goal"] + " und Regressionstest"},
    )
    assert test_tasks is None
    assert test_reason == "ziel_verlangt_weitere_testplanung"


@pytest.mark.parametrize(
    ("prose_suffix", "manifest_complete", "reason"),
    [
        (
            "## tests/test_module.py\nTest.\n",
            True,
            "architect_plan_hat_nicht_genau_einen_dateiblock",
        ),
        (
            "",
            False,
            "architect_quellbeleg_unvollstaendig",
        ),
    ],
)
def test_architect_single_file_task_escalates_without_sufficient_evidence(
    tmp_path, prose_suffix: str, manifest_complete: bool, reason: str,
) -> None:
    source = tmp_path / "module.py"
    content = "VALUE = 1\n"
    source.write_text(content, encoding="utf-8")
    prose = (
        "3. Loesung\n## module.py\nAendere VALUE.\n"
        "4. Tests\nPruefe das Verhalten.\n"
        "5. Welche Dateien haengen voneinander ab?\n- (keine)\n"
        + prose_suffix
    )
    manifest = {
        "sources": [{
            "path": "module.py",
            "complete": manifest_complete,
            "source_sha256": hashlib.sha256(content.encode()).hexdigest(),
        }],
    }

    task, actual_reason = architect_single_file_task_decision(
        goal="Aendere module.py",
        architect_prose=prose,
        key_files=["module.py"],
        source_manifest=manifest,
        project_dir=tmp_path,
    )

    assert task is None
    assert actual_reason == reason


def test_explicit_source_context_is_bounded_current_and_does_not_claim_inventory(
    tmp_path,
) -> None:
    from werkstatt.roles.planner_dispatch import (
        prepare_explicit_source_context,
    )

    for relative in ("src/one.py", "src/two.py"):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("value = 1\n", encoding="utf-8")

    context, reason = prepare_explicit_source_context(
        "Pruefe src/one.py zusammen mit src/two.py", tmp_path,
    )

    assert reason == "explicit_current_sources_ready_for_role_dispatch"
    assert context is not None
    assert context["dispatch"]["evidence_kind"] == "explicit_source_read"
    assert context["related_files_scan"]["status"] == "not_requested"
    assert len(context["key_files"]) == 2
    for item in context["key_files"]:
        source = (tmp_path / item["file"]).read_bytes()
        assert item["source_complete"] is True
        assert item["source_line_ranges"] == [[1, 1]]
        assert item["source_sha256"] == hashlib.sha256(source).hexdigest()

    (tmp_path / "src/two.py").write_text("changed = True\n", encoding="utf-8")
    stale_context, stale_reason = prepare_explicit_source_context(
        "Pruefe src/one.py zusammen mit src/two.py", tmp_path,
    )
    assert stale_reason == "explicit_current_sources_ready_for_role_dispatch"
    assert stale_context["key_files"][1]["source_sha256"] != (
        context["key_files"][1]["source_sha256"]
    )


def test_explicit_source_context_falls_back_for_long_or_unsafe_goals(
    tmp_path,
) -> None:
    from werkstatt.roles.planner_dispatch import (
        prepare_explicit_source_context,
    )

    long_context, long_reason = prepare_explicit_source_context(
        "Pruefe src/one.py src/two.py " + ("x" * 12_001), tmp_path,
    )
    assert long_context is None
    assert long_reason == "explicit_sources_goal_outside_limit"

    unsafe_context, unsafe_reason = prepare_explicit_source_context(
        "Pruefe ../outside.py und src/two.py", tmp_path,
    )
    assert unsafe_context is None
    assert unsafe_reason in {
        "explicit_sources_need_two_to_four_paths",
        "explicit_source_path_unsafe",
    }
