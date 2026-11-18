"""Tests fuer werkstatt/planner.py (Phase 5)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from werkstatt.planner import _preflight_scan
from werkstatt.state import RunState


def test_planner_explorer_findings_formatter_keeps_all_data() -> None:
    from werkstatt.planner import _format_explorer_findings

    findings = {
        f"finding_{index}": [f"detail_{index}_{item}" * 20 for item in range(7)]
        for index in range(12)
    }

    rendered = _format_explorer_findings(findings)

    assert "Untrusted Explorer-Daten" in rendered
    assert json.loads(rendered.split("\n", 1)[1]) == findings


def _state(tmp_path):
    return RunState(
        block_id="t", aufgabe="Baue Feature X", start_ts="",
        docs={"a": "doc a"}, agents={}, always={}, optional={},
        file_whitelist=[], api_key="fake", budget={},
        agent_docs={}, project_dir=tmp_path, project_name="p"
    )


def test_plan_gate_recovery_reuses_architect_evidence_and_preserves_criteria(
    tmp_path, monkeypatch,
) -> None:
    from werkstatt import planner

    state = _state(tmp_path)
    state.architect_prosa = "## Plan\nAenderung in a.py"
    state.explorer_context = {"key_files": [{"file": "a.py"}]}
    state.akzeptanzkriterien = ["AC1: Verhalten bleibt korrekt"]
    state.tasks = [{"id": "old", "action": "update", "task_files": ["a.py"]}]
    captured = {}

    def split(*args, **kwargs):
        captured["prose"] = args[0]
        captured["feedback"] = kwargs["gate_feedback"]
        captured["criteria"] = kwargs["preserve_criteria"]
        return [{
            "id": "new", "action": "update", "task_files": ["a.py"],
            "criterion_refs": ["AC1"],
        }]

    monkeypatch.setattr(planner, "_zerlege_in_sub_tasks", split)
    monkeypatch.setattr(
        planner, "_normalisiere_task_files", lambda tasks, *_args: tasks,
    )
    monkeypatch.setattr(planner, "audit", lambda *_args: None)

    assert planner.replan_task_graph_from_architect(state, {
        "regel": "ACCEPTANCE_COVERAGE", "fakt": "AC1 has no task",
    })
    assert captured == {
        "prose": state.architect_prosa,
        "feedback": {
            "regel": "ACCEPTANCE_COVERAGE", "fakt": "AC1 has no task",
        },
        "criteria": ["AC1: Verhalten bleibt korrekt"],
    }
    assert state.akzeptanzkriterien == ["AC1: Verhalten bleibt korrekt"]
    assert [task["id"] for task in state.tasks] == ["new"]


def test_plan_gate_recovery_rejects_other_gate_codes_before_split(
    tmp_path, monkeypatch,
) -> None:
    from werkstatt import planner

    state = _state(tmp_path)
    called = False

    def split(*_args, **_kwargs):
        nonlocal called
        called = True
        return []

    monkeypatch.setattr(planner, "_zerlege_in_sub_tasks", split)
    monkeypatch.setattr(planner, "audit", lambda *_args: None)

    assert not planner.replan_task_graph_from_architect(
        state, {"regel": "TASK_FILE", "fakt": "out of scope"},
    )
    assert not called


def test_scout_skip_requires_explicit_single_file_and_explorer_evidence(tmp_path):
    from werkstatt.roles.planner_dispatch import scout_route_decision

    target = tmp_path / "werkstatt" / "small.py"
    target.parent.mkdir()
    target.write_text("VALUE = 1\n", encoding="utf-8")
    context = {"key_files": [{"file": "werkstatt/small.py"}]}

    assert scout_route_decision(
        "Korrigiere werkstatt/small.py", context, tmp_path,
    )[0] == "werkstatt/small.py"
    assert scout_route_decision(
        "Prüfe den Fehler in werkstatt/small.py", context, tmp_path,
    )[0] is None
    assert scout_route_decision(
        "Korrigiere werkstatt/small.py und werkstatt/other.py",
        context, tmp_path,
    )[0] is None
    assert scout_route_decision(
        "Korrigiere werkstatt/small.py",
        {"key_files": []}, tmp_path,
    )[0] is None

    large = tmp_path / "werkstatt" / "large.py"
    large.write_text("VALUE = 'x'\n" + ("# extra context\n" * 500), encoding="utf-8")
    assert scout_route_decision(
        "Korrigiere werkstatt/large.py",
        {"key_files": [{"file": "werkstatt/large.py"}]}, tmp_path,
    )[0] is None
    oversized = tmp_path / "werkstatt" / "oversized.py"
    oversized.write_text("# context\n" * 3_000, encoding="utf-8")
    assert scout_route_decision(
        "Korrigiere werkstatt/oversized.py",
        {"key_files": [{"file": "werkstatt/oversized.py"}]}, tmp_path,
    )[0] is None

def test_literal_replacement_with_ambiguous_or_stale_text_falls_back(tmp_path):
    from werkstatt.roles.builder_direct import build_direct_edit_plan

    target = tmp_path / "module.py"
    target.write_text("VALUE = OLD\nCOPY = OLD\n", encoding="utf-8")
    assert build_direct_edit_plan(
        "Ersetze `OLD` durch `NEW` in module.py.", "module.py", tmp_path,
    ) == (None, "alter_text_nicht_eindeutig")
    assert build_direct_edit_plan(
        "Ersetze `MISSING` durch `NEW` in module.py.", "module.py", tmp_path,
    ) == (None, "alter_text_nicht_eindeutig")
    assert build_direct_edit_plan(
        "Aendere die Logik in module.py.", "module.py", tmp_path,
    ) == (None, "kein_expliziter_literalersetzungsausdruck")
    target.write_text("VALUE = OLD\n", encoding="utf-8")
    assert build_direct_edit_plan(
        "Ersetze `OLD` durch `NEW` und module.py.", "module.py", tmp_path,
    ) == (None, "zieldatei_nicht_an_ersetzung_gebunden")


def test_unique_literal_setting_can_dispatch_directly_to_builder(tmp_path):
    from werkstatt.roles.builder_direct import build_direct_edit_plan

    target = tmp_path / "settings.py"
    target.write_text("TIMEOUT = 15  # seconds\n", encoding="utf-8")
    plan, reason = build_direct_edit_plan(
        "Setze TIMEOUT in settings.py auf 30.", "settings.py", tmp_path,
    )

    assert reason == "eindeutige_ast_literalzuweisung"
    assert plan is not None
    change = plan["betroffene_stellen"][0]
    assert change["datei"] == "settings.py"
    assert change["zeile"] == 1
    assert change["alt"] == "TIMEOUT = 15  # seconds"
    assert change["neu"] == "TIMEOUT = 30  # seconds"


def test_literal_setting_with_duplicate_assignment_stays_on_role_path(tmp_path):
    from werkstatt.roles.builder_direct import build_direct_edit_plan

    target = tmp_path / "settings.py"
    target.write_text("TIMEOUT = 15\nTIMEOUT = 20\n", encoding="utf-8")

    assert build_direct_edit_plan(
        "Setze TIMEOUT in settings.py auf 30.", "settings.py", tmp_path,
    ) == (None, "zielvariable_nicht_eindeutig")


def test_atomic_scout_plan_requires_current_unique_evidence(tmp_path):
    from werkstatt.planner import _atomarer_scout_plan_freigabefaehig

    target = tmp_path / "module.py"
    target.write_text("VALUE = OLD\n", encoding="utf-8")
    report = {
        "atomarer_plan": True,
        "betroffene_stellen": [{
            "datei": "module.py",
            "zeile": 1,
            "alt": "OLD",
            "neu": "NEW",
            "grund": "Konsistente Umbenennung",
        }],
    }

    assert _atomarer_scout_plan_freigabefaehig(report, tmp_path) == (
        True, "exakte_einzeldatei_ersetzungen",
    )
    stale = {**report, "betroffene_stellen": [{
        **report["betroffene_stellen"][0], "zeile": 2,
    }]}
    assert _atomarer_scout_plan_freigabefaehig(stale, tmp_path) == (
        False, "stellenbeleg_veraltet_oder_mehrdeutig",
    )
    incomplete = {**report, "betroffene_stellen": [{
        **report["betroffene_stellen"][0], "neu": "",
    }]}
    assert _atomarer_scout_plan_freigabefaehig(incomplete, tmp_path) == (
        False, "ersetzung_unvollstaendig",
    )


def test_scout_route_decision_explains_escalation(tmp_path):
    from werkstatt.roles.planner_dispatch import scout_route_decision

    target = tmp_path / "werkstatt" / "small.py"
    target.parent.mkdir()
    target.write_text("VALUE = 1\n", encoding="utf-8")
    context = {"key_files": [{"file": "werkstatt/small.py"}]}

    assert scout_route_decision(
        "Pruefe den Fehler in werkstatt/small.py", context, tmp_path,
    ) == (None, "auftrag_enthaelt_breiten_marker:fehler")
    assert scout_route_decision(
        "Korrigiere werkstatt/small.py", context, tmp_path,
    ) == (
        "werkstatt/small.py",
        "explizite_einzeldatei_mit_explorer_beleg",
    )
    assert scout_route_decision(
        "Korrigiere checkpoint handling in werkstatt/small.py",
        context,
        tmp_path,
    ) == (
        "werkstatt/small.py",
        "explizite_einzeldatei_mit_explorer_beleg",
    )
    assert scout_route_decision(
        "Fix rapid status updates in werkstatt/small.py",
        context,
        tmp_path,
    ) == (
        "werkstatt/small.py",
        "explizite_einzeldatei_mit_explorer_beleg",
    )
    assert scout_route_decision(
        "Analysiere die Architektur in werkstatt/small.py",
        context,
        tmp_path,
    ) == (None, "auftrag_enthaelt_breiten_marker:architektur")
    assert scout_route_decision(
        "Analyze the architecture in werkstatt/small.py",
        context,
        tmp_path,
    ) == (None, "auftrag_enthaelt_breiten_marker:architecture")

    for filename in ("api.py", "debugger.py"):
        relative = f"werkstatt/{filename}"
        target = tmp_path / relative
        target.write_text("VALUE = 1\n", encoding="utf-8")
        assert scout_route_decision(
            f"Fix {relative}",
            {"key_files": [{"file": relative}]},
            tmp_path,
        ) == (
            relative,
            "explizite_einzeldatei_mit_explorer_beleg",
        )


def test_klassifiziert_env():
    """M-299a: ModuleNotFoundError wird als 'env' klassifiziert."""
    from werkstatt.planner import _klassifiziere_fehler
    assert _klassifiziere_fehler("pytest", "ModuleNotFoundError: No module named 'defusedxml'") == "env"


def test_klassifiziert_lint():
    """M-299a: ruff-Stage wird als 'lint' klassifiziert."""
    from werkstatt.planner import _klassifiziere_fehler
    assert _klassifiziere_fehler("ruff", "error: unused import") == "lint"


def test_klassifiziert_syntax():
    """M-299a: py_compile wird als 'syntax' klassifiziert."""
    from werkstatt.planner import _klassifiziere_fehler
    assert _klassifiziere_fehler("py_compile", "SyntaxError: invalid syntax") == "syntax"


@pytest.mark.skip(reason="GOLD: alter JSON-Plan-Pfad entfernt (blocker/follow_up/ignore nicht mehr im Gold-Flow)")


def test_preflight_scan_klassifiziert(tmp_path):
    """M-299e: _preflight_scan klassifiziert Stage-Fehler."""
    from subprocess import CompletedProcess

    st = _state(tmp_path)
    contract_dir = tmp_path / ".werkstatt"
    contract_dir.mkdir()
    (contract_dir / "verify.json").write_text(json.dumps({
        "stages": [
            {"id": "py_compile", "command": ["false"]},
            {"id": "ruff", "command": ["false"]},
        ]
    }))

    def _mock_run(cmd, **kwargs):
        if "py_compile" in str(cmd):
            return CompletedProcess(cmd, 1, "", "SyntaxError: invalid syntax")
        return CompletedProcess(cmd, 1, "", "ruff: unused import")

    with patch("subprocess.run", side_effect=_mock_run):
        fehler = _preflight_scan(st)

    assert len(fehler) == 2
    klassen = {f["klasse"] for f in fehler}
    assert "syntax" in klassen
    assert "lint" in klassen


@pytest.mark.skip(reason="GOLD: alter JSON-Plan-Pfad entfernt (action-Default kommt vom Planner-Split)")

@pytest.mark.skip(reason="GOLD: alter JSON-Plan-Pfad entfernt (phasen kommen vom Planner-Split, nicht direkt aus JSON)")


def test_planner_split_persistiert_abnahmekriterien_und_originalauftrag(tmp_path):
    """Der Split muss Kriterien aus dem Modell strukturiert in den Run uebernehmen."""
    from werkstatt.planner import _zerlege_in_sub_tasks

    st = _state(tmp_path)
    st.aufgabe = (
        "OP-900: Der API-Endpunkt muss Projektisolation erzwingen.\n"
        + "Vollstaendige Anforderung. " * 600
    )
    reply = MagicMock(
        ok=True,
        content=json.dumps({
            "akzeptanzkriterien": [
                "Fremde Projekte liefern keine Ereignisse.",
                "Fremde Projekte liefern keine Ereignisse.",
            ],
            "tasks": [{
                "id": "t1",
                "name": "Projektfilter",
                "task_files": ["werkstatt/web/app.py"],
                "dependencies": [],
            }],
        }),
    )
    captured = {}

    def _ask(_key, _system, user_content, **kwargs):
        captured["prompt"] = user_content
        captured["manifest"] = kwargs.get("context_manifest")
        return reply

    with patch("werkstatt.planner.ask_llm", side_effect=_ask), \
         patch("werkstatt.planner._with_spinner", side_effect=lambda _label, fn: fn()), \
         patch("werkstatt.planner.audit"):
        tasks = _zerlege_in_sub_tasks(
            "## werkstatt/web/app.py\nFiltere Projekt-Ereignisse.",
            ["werkstatt/web/app.py"],
            "fake",
            tmp_path,
            "demo",
            aufgabe=st.aufgabe,
            state=st,
        )

    assert tasks and tasks[0]["id"] == "t1"
    assert st.akzeptanzkriterien == [
        "Fremde Projekte liefern keine Ereignisse.",
    ]
    assert "ORIGINALAUFTRAG" in captured["prompt"]
    assert st.aufgabe.strip() in captured["prompt"]
    assert captured["manifest"]["budget_event"] == "planner_split_context_budget"
    assert captured["manifest"]["scope"] == "task_graph"
    assert captured["manifest"]["required_context_complete"] is True
    sections = captured["manifest"]["sections"]
    included = [
        item for item in sections
        if item["status"] in {"required_included", "optional_included"}
    ]
    section_status = {item["name"]: item["status"] for item in sections}
    assert section_status["original_request"] == "optional_included"
    assert section_status["architect_prose"] == "required_included"
    assert section_status["target_files"] == "required_included"
    assert any(item["name"] == "planner_skills"
               and item["status"] == "not_provided_optional" for item in sections)
    for item in included:
        start, end = item["prompt_start"], item["prompt_end"]
        excerpt = captured["prompt"][start:end]
        assert len(excerpt) == item["chars"]
        assert hashlib.sha256(excerpt.encode("utf-8")).hexdigest() == item["sha256"]
    assert included[0]["prompt_start"] == 0
    assert included[-1]["prompt_end"] == len(captured["prompt"])


def test_planner_split_prompt_binds_gate_feedback_and_frozen_criteria(tmp_path):
    from werkstatt.planner import _zerlege_in_sub_tasks

    state = _state(tmp_path)
    criteria = ["Der Handler liefert fuer fremde Projekte keine Daten."]
    feedback = {
        "regel": "ACCEPTANCE_COVERAGE",
        "fakt": "AC1 is not assigned to any task.",
        "details": "Untrusted gate diagnostic." + ("x" * 900),
    }
    response = MagicMock(
        ok=True,
        content=json.dumps({
            "akzeptanzkriterien": criteria,
            "tasks": [{
                "id": "t1", "name": "Projektfilter", "action": "update",
                "task_files": ["werkstatt/web/app.py"],
                "criterion_refs": ["AC1"],
            }],
        }),
    )
    captured = {}

    def ask(_key, _system, user_content, **kwargs):
        captured["prompt"] = user_content
        captured["manifest"] = kwargs["context_manifest"]
        return response

    with patch("werkstatt.planner.ask_llm", side_effect=ask), \
         patch("werkstatt.planner._with_spinner", side_effect=lambda _label, fn: fn()), \
         patch("werkstatt.planner.audit"):
        tasks = _zerlege_in_sub_tasks(
            "## werkstatt/web/app.py\nFiltere fremde Projekte.",
            ["werkstatt/web/app.py"], "fake", tmp_path, "demo",
            aufgabe="Begrenze API-Daten auf das aktive Projekt.",
            state=state,
            gate_feedback=feedback,
            preserve_criteria=criteria,
        )

    assert tasks and state.akzeptanzkriterien == criteria
    assert "PLAN-GATE-BEFUND (untrusted Diagnose" in captured["prompt"]
    assert "Untrusted gate diagnostic." in captured["prompt"]
    assert "truncated_fields" in captured["prompt"]
    assert json.dumps(criteria, ensure_ascii=False) in captured["prompt"]
    section_status = {
        item["name"]: item["status"]
        for item in captured["manifest"]["sections"]
    }
    assert section_status["plan_gate_feedback"] == "required_included"
    assert section_status["preserved_acceptance_criteria"] == "required_included"


def test_planner_split_rejects_changed_frozen_criteria(tmp_path):
    from werkstatt.planner import TaskGraphError, _zerlege_in_sub_tasks

    state = _state(tmp_path)
    original = ["Kriterium bleibt wortgleich."]
    response = MagicMock(
        ok=True,
        content=json.dumps({
            "akzeptanzkriterien": ["Aenderte Kriterien"],
            "tasks": [{"id": "t1", "name": "Task", "criterion_refs": ["AC1"]}],
        }),
    )

    with (
        patch("werkstatt.planner.ask_llm", return_value=response),
        patch("werkstatt.planner._with_spinner", side_effect=lambda _label, fn: fn()),
        patch("werkstatt.planner.audit"),
        pytest.raises(TaskGraphError, match="freigegebene Akzeptanzkriterien"),
    ):
        _zerlege_in_sub_tasks(
            "Plan", ["werkstatt/app.py"], "fake", tmp_path, "demo",
            state=state, gate_feedback={"regel": "TASK_GRAPH"},
            preserve_criteria=original,
        )
    assert state.akzeptanzkriterien == []


def test_planner_split_blockiert_uebergrossen_auftrag_statt_vorab_zu_schneiden(
    tmp_path,
):
    """Pflichtkontext muss vollstaendig ankommen oder vor dem LLM stoppen."""
    from werkstatt.planner import _zerlege_in_sub_tasks

    aufruf = "OP-999: " + ("vollstaendiger Auftrag. " * 3000)
    llm_calls = []
    audit_events = []
    with patch(
        "werkstatt.planner.ask_llm",
        side_effect=lambda *args, **kwargs: llm_calls.append((args, kwargs)),
    ), patch("werkstatt.planner._with_spinner", side_effect=lambda _label, fn: fn()), \
         patch("werkstatt.planner.audit", side_effect=lambda *args: audit_events.append(args)):
        tasks = _zerlege_in_sub_tasks(
            "## werkstatt/demo.py\nAendere die Funktion.",
            ["werkstatt/demo.py"], "fake", tmp_path, "demo",
            aufgabe=aufruf,
        )

    assert tasks == []
    assert llm_calls == []
    budget_events = [event for event in audit_events if event[0] == "planner_split_context_budget"]
    assert len(budget_events) == 1
    assert budget_events[0][1]["required_context_complete"] is False
    assert budget_events[0][1]["omitted"] == []


def test_planner_split_reloads_scout_source_with_hash_provenance(tmp_path):
    from werkstatt.architect import _format_scout_source_evidence
    from werkstatt.planner import _zerlege_in_sub_tasks

    source = tmp_path / "src.py"
    source.write_text("def current_handler():\n    return 'current'\n", encoding="utf-8")
    report = {
        "relevante_dateien": [{
            "pfad": "src.py",
            "zeilen": [1],
            "warum": "handler named by the task",
        }],
        "api_auszug": {},
    }
    _, architect_manifest = _format_scout_source_evidence(tmp_path, report)
    st = _state(tmp_path)
    st.scout_auftrag = report
    st.architect_scout_source_manifest = architect_manifest
    reply = MagicMock(
        ok=True,
        content=json.dumps({
            "akzeptanzkriterien": ["Current handler is retained."],
            "tasks": [{
                "id": "t1", "name": "Update handler",
                "task_files": ["src.py"], "criterion_refs": ["AC1"],
            }],
        }),
    )
    captured = {}

    def ask(_key, _system, content, **kwargs):
        captured["content"] = content
        captured["manifest"] = kwargs["context_manifest"]
        return reply

    with patch("werkstatt.planner.ask_llm", side_effect=ask), \
         patch("werkstatt.planner._with_spinner", side_effect=lambda _label, fn: fn()), \
         patch("werkstatt.planner.audit"):
        tasks = _zerlege_in_sub_tasks(
            "## src.py\nRetain current_handler.", ["src.py"], "fake",
            tmp_path, "demo", aufgabe="Update src.py", state=st,
        )

    assert tasks and "return 'current'" in captured["content"]
    source_manifest = captured["manifest"]["source_evidence"]
    assert source_manifest["sources"][0]["path"] == "src.py"
    assert source_manifest["sources"][0]["source_sha256"] == architect_manifest[
        "sources"
    ][0]["source_sha256"]
    source_record = source_manifest["sources"][0]
    start, end = source_record["prompt_start"], source_record["prompt_end"]
    excerpt = captured["content"][start:end]
    assert excerpt.startswith('<source datei="src.py"')
    assert excerpt.endswith("</source>")
    assert len(excerpt) == source_record["excerpt_chars"]
    assert hashlib.sha256(excerpt.encode("utf-8")).hexdigest() == (
        source_record["excerpt_sha256"]
    )
    assert captured["manifest"]["source_evidence_sha256"]


def test_planner_split_stops_if_source_changes_after_architect(tmp_path):
    from werkstatt.architect import _format_scout_source_evidence
    from werkstatt.planner import _zerlege_in_sub_tasks

    source = tmp_path / "src.py"
    source.write_text("def current_handler():\n    return 'architect-view'\n", encoding="utf-8")
    report = {
        "relevante_dateien": [{"pfad": "src.py", "zeilen": [1]}],
        "api_auszug": {},
    }
    _, architect_manifest = _format_scout_source_evidence(tmp_path, report)
    source.write_text("def current_handler():\n    return 'changed-after-architect'\n", encoding="utf-8")
    st = _state(tmp_path)
    st.scout_auftrag = report
    st.architect_scout_source_manifest = architect_manifest
    calls = []
    audit_events = []

    with patch(
        "werkstatt.planner.ask_llm",
        side_effect=lambda *args, **kwargs: calls.append((args, kwargs)),
    ), patch(
        "werkstatt.planner.audit",
        side_effect=lambda *args: audit_events.append(args),
    ):
        tasks = _zerlege_in_sub_tasks(
            "## src.py\nBased on architect-view.", ["src.py"], "fake",
            tmp_path, "demo", aufgabe="Update src.py", state=st,
        )

    assert tasks == []
    assert calls == []
    event = next(
        payload for name, payload, *_ in audit_events
        if name == "planner_split_context_budget"
    )
    assert event["reason"] == "source_changed_between_architect_and_planner"


def test_criteria_coverage_requires_known_references():
    from werkstatt.planner import (
        TaskGraphError,
        _validate_criteria_coverage,
    )

    tasks = [
        {"id": "t1", "criterion_refs": ["AC1"]},
        {"id": "t2", "criterion_refs": ["AC2"]},
    ]
    _validate_criteria_coverage(tasks, ["Kriterium eins", "Kriterium zwei"])

    with pytest.raises(TaskGraphError, match="Nicht alle Akzeptanzkriterien"):
        _validate_criteria_coverage(
            [{"id": "t1", "criterion_refs": ["AC1"]}],
            ["Kriterium eins", "Kriterium zwei"],
            infer_single_task=False,
        )

    with pytest.raises(TaskGraphError, match="unbekannte"):
        _validate_criteria_coverage(
            [{"id": "t1", "criterion_refs": ["AC3"]}],
            ["Kriterium eins", "Kriterium zwei"],
        )


def test_single_task_infers_all_acceptance_criteria():
    from werkstatt.planner import _validate_criteria_coverage

    tasks = [{"id": "t1"}]
    _validate_criteria_coverage(tasks, ["Kriterium eins", "Kriterium zwei"])
    assert tasks[0]["criterion_refs"] == ["AC1", "AC2"]



def test_oversized_task_split_rejects_malformed_criterion_refs():
    from werkstatt.planner import TaskGraphError, _llm_split_einzel_task

    reply = MagicMock(
        ok=True,
        content=json.dumps({"tasks": [{
            "id": "t1_a",
            "name": "Teil",
            "criterion_refs": [{"unexpected": "object"}],
        }]}),
    )
    with (
        patch("werkstatt.planner.ask_llm", return_value=reply),
        patch(
            "werkstatt.planner._with_spinner",
            side_effect=lambda _label, fn: fn(),
        ),
        pytest.raises(TaskGraphError, match="ungueltige criterion_refs"),
    ):
        _llm_split_einzel_task(
            "## werkstatt/demo.py\nAendere die Funktion.",
            {
                "id": "t1",
                "criterion_refs": ["AC1"],
                "task_files": ["werkstatt/demo.py"],
                "description": "x" * 2600,
            },
            "fake",
            Path("."),
            "demo",
        )


def test_oversized_task_split_preserves_full_architect_subsection():
    from werkstatt.planner import _llm_split_einzel_task

    start = "## werkstatt/demo.py"
    tail = "ARCHITECT_SECTION_TAIL_SENTINEL"
    prose = f"{start}\n" + "x" * 3_000 + f"\n{tail}"
    reply = MagicMock(ok=True, content=json.dumps({"tasks": [{
        "id": "t1_a",
        "name": "Repair the target file",
        "architect_start": start,
        "architect_ende": tail,
        "criterion_refs": ["AC1"],
        "task_files": ["werkstatt/demo.py"],
    }]}))

    with (
        patch("werkstatt.planner.ask_llm", return_value=reply),
        patch(
            "werkstatt.planner._with_spinner",
            side_effect=lambda _label, fn: fn(),
        ),
    ):
        tasks = _llm_split_einzel_task(
            prose,
            {
                "id": "t1", "criterion_refs": ["AC1"],
                "task_files": ["werkstatt/demo.py"],
                "description": "x" * 2_600,
            },
            "fake", Path("."), "demo",
        )

    assert len(tasks) == 1
    assert tasks[0]["description"].endswith(tail)
    assert "x" * 3_000 in tasks[0]["description"]
    assert len(tasks[0]["description"]) > 3_000


def test_planner_keeps_all_acceptance_criteria_without_length_caps(tmp_path):
    from werkstatt.planner import _zerlege_in_sub_tasks

    (tmp_path / "src.py").write_text("VALUE = 1\n", encoding="utf-8")
    criteria = [f"Criterion {index}" for index in range(1, 31)]
    criteria[-1] = "Long criterion " + "x" * 650
    reply = MagicMock(ok=True, content=json.dumps({
        "akzeptanzkriterien": criteria,
        "tasks": [{
            "id": "t1", "name": "Update source", "task_files": ["src.py"],
            "description": "Use the complete acceptance criteria.",
        }],
    }))
    state = _state(tmp_path)

    with (
        patch("werkstatt.planner.ask_llm", return_value=reply),
        patch(
            "werkstatt.planner._with_spinner",
            side_effect=lambda _label, fn: fn(),
        ),
        patch("werkstatt.planner.audit"),
    ):
        tasks = _zerlege_in_sub_tasks(
            "## src.py\nUpdate the source.", ["src.py"], "fake",
            tmp_path, "demo", state=state,
        )

    assert state.akzeptanzkriterien == criteria
    assert len(state.akzeptanzkriterien) == 30
    assert state.akzeptanzkriterien[-1].endswith("x" * 650)
    assert tasks[0]["criterion_refs"] == [f"AC{index}" for index in range(1, 31)]


def test_planner_split_blocks_missing_required_architect_prose(tmp_path):
    from werkstatt.planner import _zerlege_in_sub_tasks

    calls = []
    audits = []
    with patch(
        "werkstatt.planner.ask_llm",
        side_effect=lambda *args, **kwargs: calls.append((args, kwargs)),
    ), patch(
        "werkstatt.planner.audit",
        side_effect=lambda *args: audits.append(args),
    ):
        tasks = _zerlege_in_sub_tasks(
            "", ["src.py"], "fake", tmp_path, "demo", aufgabe="Update src.py",
        )

    assert tasks == []
    assert calls == []
    event = next(
        payload for name, payload, *_ in audits
        if name == "planner_split_context_budget"
    )
    assert event["required_context_complete"] is False
    assert event["reason"] == "missing_required_prompt_section"
    assert event["omitted"] == ["architect_prose"]


@pytest.mark.parametrize(
    ("files", "message"),
    [
        ([], "keinen konkreten task_files-Scope"),
        (["missing.py"], "keine gueltige Projektdatei"),
        (["../outside.py"], "ausserhalb des Projekt-Scopes"),
        (["src.py", "src.py"], "doppelt"),
    ],
)
def test_planner_rejects_unscoped_or_invalid_read_tasks(tmp_path, files, message):
    from werkstatt.planner import TaskGraphError, _validate_read_task_scopes

    (tmp_path / "src.py").write_text("VALUE = 1\n", encoding="utf-8")
    with pytest.raises(TaskGraphError, match=message):
        _validate_read_task_scopes(
            [{"id": "read-1", "action": "read", "task_files": files}],
            tmp_path,
        )


def test_planner_accepts_scoped_read_task_and_ignores_non_read(tmp_path):
    from werkstatt.planner import _validate_read_task_scopes

    (tmp_path / "src.py").write_text("VALUE = 1\n", encoding="utf-8")
    _validate_read_task_scopes(
        [
            {"id": "read-1", "action": "read", "task_files": ["src.py"]},
            {"id": "write-1", "action": "update", "task_files": []},
        ],
        tmp_path,
    )
