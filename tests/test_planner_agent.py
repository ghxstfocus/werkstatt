"""Tests fuer werkstatt/planner.py (Phase 5)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from werkstatt.planner import _preflight_scan, run_planner
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


def test_planner_erstellt_plan(tmp_path):
    """GOLD: Scout + Architect (Prosa) + Planner (JSON). Drei Calls."""
    st = _state(tmp_path)

    _scout_json = json.dumps({
        "ziel": "Test",
        "relevante_dateien": [{"pfad": "a.py", "zeilen": [1], "warum": "test"}],
        "api_auszug": {},
        "vorgeschlagene_aenderungen": ["neue Funktion fix()"],
        "risiken": [],
        "auftrag_prosa": "Baue fix() in a.py",
    })
    _arch_prosa = (
        "## Interface\n"
        "Neue Funktion fix() in a.py.\n\n"
        "## Logik\n"
        "Validiert x > 0, ruft helper().\n\n"
        "## Integration\n"
        "In main() einbauen.\n\n"
        "## Tests\n"
        "test_fix() in tests/test_a.py."
    )
    _planner_json = json.dumps({
        "tasks": [{"id": "t1", "name": "A", "description": "B",
                   "action": "update", "task_files": ["a.py"]}],
        "tests": ["test_a"],
        "akzeptanzkriterien": ["done"],
    })

    class FakeReply:
        def __init__(self, content):
            self.ok = True
            self.content = content

    _responses = iter([
        FakeReply(_scout_json),
        FakeReply(_arch_prosa),
        FakeReply(_planner_json),
    ])

    def _fake_ask_llm(*args, **kwargs):
        return next(_responses)

    with patch("werkstatt.planner.ask_llm", side_effect=_fake_ask_llm):
        result = run_planner(st)
        assert result is True
        assert len(st.tasks) == 1
        assert st.architect_reasoning_enabled is True


def test_planner_can_yield_after_each_required_role(tmp_path, monkeypatch):
    from werkstatt import planner

    state = _state(tmp_path)
    state.run_id = "run-1"
    state.planner_action_role = "scout"
    state.planner_role_artifacts = {}
    state.planner_role_artifact_callback = lambda artifact: (
        state.planner_role_artifacts.__setitem__(artifact["role"], artifact)
    )
    scout_fingerprints = []
    original_scout_fingerprint = planner._scout_input_fingerprint
    monkeypatch.setattr(
        planner,
        "_scout_input_fingerprint",
        lambda *args: scout_fingerprints.append(
            original_scout_fingerprint(*args),
        ) or scout_fingerprints[-1],
    )
    report = {
        "ziel": "Baue Feature X",
        "relevante_dateien": [{"pfad": "feature.py", "warum": "Ziel"}],
        "api_auszug": {},
        "vorgeschlagene_aenderungen": ["Implementiere Feature X"],
        "risiken": [],
        "auftrag_prosa": "Implementiere Feature X in feature.py.",
        "bereits_erfuellt": False,
        "atomarer_plan": False,
    }
    calls = {"scout": 0, "architect": 0, "split": 0}

    monkeypatch.setattr(
        planner, "_deterministic_entfernen_precheck", lambda _state: False,
    )
    monkeypatch.setattr(
        planner, "_scout_route_decision", lambda *_args: (None, "needs_scout"),
    )
    monkeypatch.setattr(planner, "_baue_api_index", lambda _path: {})
    monkeypatch.setattr(
        planner, "_run_scout",
        lambda *_args: calls.__setitem__("scout", calls["scout"] + 1) or report,
    )
    monkeypatch.setattr(
        planner, "_scout_report_hat_architect_auftrag", lambda _report: True,
    )
    monkeypatch.setattr(planner, "_pruefe_api_widerspruch", lambda *_args: [])
    monkeypatch.setattr(
        planner, "_validate_contract_or_audit", lambda *_args: True,
    )

    def architect(*_args):
        calls["architect"] += 1
        state.architect_prosa = (
            "## Plan\nImplementiere Feature X in feature.py mit Tests "
            "und dokumentiere die aktuelle Schnittstelle."
        )
        return True

    def split(*_args, **_kwargs):
        calls["split"] += 1
        state.akzeptanzkriterien = ["Feature X ist implementiert"]
        return [{
            "id": "t1", "name": "Feature X",
            "action": "update", "task_files": ["feature.py"],
            "criterion_refs": ["AC1"],
        }]

    monkeypatch.setattr(planner, "run_architect", architect)
    monkeypatch.setattr(planner, "_zerlege_in_sub_tasks", split)
    monkeypatch.setattr(planner, "audit", lambda *_args, **_kwargs: None)

    assert planner.run_planner(state, stop_after_role="scout") is True
    assert state.planner_step_yielded is True
    assert calls == {"scout": 1, "architect": 0, "split": 0}

    state.planner_action_role = "architect"
    assert planner.run_planner(state, stop_after_role="architect") is True
    assert state.planner_step_yielded is True
    assert calls == {"scout": 1, "architect": 1, "split": 0}

    state.planner_action_role = "planner_split"
    assert planner.run_planner(state) is True
    assert state.planner_step_yielded is False
    assert len(set(scout_fingerprints[:3])) == 1
    assert calls == {"scout": 1, "architect": 1, "split": 1}

    from werkstatt import architect as architect_module

    monkeypatch.setattr(
        architect_module, "_get_architect_model", lambda: "changed-model",
    )
    assert planner.run_planner(state) is True
    assert state.planner_yielded_after_role == "architect"
    assert calls == {"scout": 1, "architect": 2, "split": 1}

    # A changed candidate source invalidates the cached role output and
    # re-runs Scout before Architect can consume it.
    state.docs["a"] = "changed project evidence"
    assert planner.run_planner(state) is True
    assert state.planner_step_yielded is True
    assert state.planner_yielded_after_role == "scout"
    assert calls == {"scout": 2, "architect": 2, "split": 1}

    state.planner_action_role = "architect"
    assert planner.run_planner(state, stop_after_role="architect") is True
    assert state.planner_yielded_after_role == "architect"
    assert calls == {"scout": 2, "architect": 3, "split": 1}

    state.planner_role_artifact_callback = None
    state.docs["a"] = "a further changed source"
    state.planner_action_role = "planner_split"
    assert planner.run_planner(state) is False
    assert calls == {"scout": 3, "architect": 3, "split": 1}


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
    from werkstatt.planner import _scout_skip_target

    target = tmp_path / "werkstatt" / "small.py"
    target.parent.mkdir()
    target.write_text("VALUE = 1\n", encoding="utf-8")
    context = {"key_files": [{"file": "werkstatt/small.py"}]}

    assert _scout_skip_target(
        "Korrigiere werkstatt/small.py", context, tmp_path,
    ) == "werkstatt/small.py"
    assert _scout_skip_target(
        "Prüfe den Fehler in werkstatt/small.py", context, tmp_path,
    ) is None
    assert _scout_skip_target(
        "Korrigiere werkstatt/small.py und werkstatt/other.py",
        context, tmp_path,
    ) is None
    assert _scout_skip_target(
        "Korrigiere werkstatt/small.py",
        {"key_files": []}, tmp_path,
    ) is None

    large = tmp_path / "werkstatt" / "large.py"
    large.write_text("VALUE = 'x'\n" + ("# extra context\n" * 500), encoding="utf-8")
    assert _scout_skip_target(
        "Korrigiere werkstatt/large.py",
        {"key_files": [{"file": "werkstatt/large.py"}]}, tmp_path,
    ) is None
    oversized = tmp_path / "werkstatt" / "oversized.py"
    oversized.write_text("# context\n" * 3_000, encoding="utf-8")
    assert _scout_skip_target(
        "Korrigiere werkstatt/oversized.py",
        {"key_files": [{"file": "werkstatt/oversized.py"}]}, tmp_path,
    ) is None


def test_planner_skips_scout_but_keeps_architect_and_plan_path(tmp_path):
    from werkstatt.planner import run_planner

    target = tmp_path / "werkstatt" / "small.py"
    target.parent.mkdir()
    target.write_text("VALUE = 1\n", encoding="utf-8")
    st = _state(tmp_path)
    st.aufgabe = "Korrigiere werkstatt/small.py"
    st.explorer_context = {
        "key_files": [{"file": "werkstatt/small.py"}],
        "findings": "Datei vorhanden",
    }
    role_checkpoints = []
    st.planner_checkpoint_callback = role_checkpoints.append

    def architect(_state, _aufgabe, _content, _key, _explorer):
        _state.architect_prosa = "## Aenderung\nAendere VALUE in small.py."
        return True

    split_tasks = [{
        "id": "t1",
        "name": "Kleine Korrektur",
        "action": "update",
        "task_files": ["werkstatt/small.py"],
        "dependencies": [],
        "description": "Korrigiere die angegebene Stelle.",
    }]
    with patch("werkstatt.planner._run_scout", side_effect=AssertionError("Scout unnötig")), \
         patch("werkstatt.planner.run_architect", side_effect=architect) as mock_architect, \
         patch("werkstatt.planner._zerlege_in_sub_tasks", return_value=split_tasks), \
         patch("werkstatt.planner.audit") as mock_audit:
        assert run_planner(st) is True

    mock_architect.assert_called_once()
    assert st.architect_reasoning_enabled is False
    assert st.tasks == split_tasks
    assert any(
        call.args[0] == "planner_scout_skipped"
        for call in mock_audit.call_args_list
    )
    assert [(item["role"], item["status"]) for item in role_checkpoints] == [
        ("scout", "skipped"),
        ("architect", "running"),
        ("architect", "completed"),
        ("planner_split", "running"),
        ("planner_split", "completed"),
    ]
    assert role_checkpoints[2]["output_sha256"]
    assert role_checkpoints[4]["output_sha256"]


def test_literal_single_file_replacement_skips_scout_and_architect(tmp_path):
    target = tmp_path / "module.py"
    target.write_text("VALUE = OLD\n", encoding="utf-8")
    st = _state(tmp_path)
    st.aufgabe = "Ersetze `OLD` durch `NEW` in module.py."
    st.explorer_context = {"key_files": [{"file": "module.py"}]}
    role_checkpoints = []
    st.planner_checkpoint_callback = role_checkpoints.append

    with patch(
        "werkstatt.planner._run_scout",
        side_effect=AssertionError("Scout fuer explizite Ersetzung unnoetig"),
    ), patch(
        "werkstatt.planner.run_architect",
        side_effect=AssertionError("Architect fuer belegte Ersetzung unnoetig"),
    ), patch("werkstatt.planner.audit") as mock_audit:
        assert run_planner(st) is True

    assert len(st.tasks) == 1
    assert st.tasks[0]["task_files"] == ["module.py"]
    assert "`OLD` durch `NEW`" in st.tasks[0]["description"]
    assert st.architect_prosa == "[atomarer Plan: deterministische_literal_ersetzung]"
    assert any(
        call.args[0] == "planner_atomarer_plan"
        and call.args[1].get("architect") == "uebersprungen"
        for call in mock_audit.call_args_list
    )
    assert [(item["role"], item["status"]) for item in role_checkpoints] == [
        ("scout", "skipped"),
        ("architect", "skipped"),
        ("planner_split", "skipped"),
    ]


def test_unique_literal_setting_skips_scout_architect_and_split(tmp_path):
    target = tmp_path / "settings.py"
    target.write_text("TIMEOUT = 15  # seconds\n", encoding="utf-8")
    st = _state(tmp_path)
    st.aufgabe = "Setze TIMEOUT in settings.py auf 30."
    st.explorer_context = {"key_files": [{"file": "settings.py"}]}
    role_checkpoints = []
    st.planner_checkpoint_callback = role_checkpoints.append

    with patch(
        "werkstatt.planner._run_scout",
        side_effect=AssertionError("Scout fuer belegte Einzelwertaenderung unnoetig"),
    ), patch(
        "werkstatt.planner.run_architect",
        side_effect=AssertionError("Architect fuer belegte Einzelwertaenderung unnoetig"),
    ), patch("werkstatt.planner.audit"):
        assert run_planner(st) is True

    assert len(st.tasks) == 1
    assert st.tasks[0]["task_files"] == ["settings.py"]
    assert "TIMEOUT = 15  # seconds` durch `TIMEOUT = 30  # seconds" in (
        st.tasks[0]["description"]
    )
    assert [(item["role"], item["status"]) for item in role_checkpoints] == [
        ("scout", "skipped"),
        ("architect", "skipped"),
        ("planner_split", "skipped"),
    ]


def test_explicit_same_file_literal_batch_skips_all_planning_roles(tmp_path):
    target = tmp_path / "settings.py"
    target.write_text("TIMEOUT = 15\nRETRIES = 2\n", encoding="utf-8")
    st = _state(tmp_path)
    st.aufgabe = (
        "Setze TIMEOUT in settings.py auf 30 und setze RETRIES "
        "in settings.py auf 5"
    )
    st.explorer_context = {"key_files": [{"file": "settings.py"}]}
    role_checkpoints = []
    st.planner_checkpoint_callback = role_checkpoints.append

    with patch(
        "werkstatt.planner._run_scout",
        side_effect=AssertionError("Scout fuer belegten Literal-Batch unnoetig"),
    ), patch(
        "werkstatt.planner.run_architect",
        side_effect=AssertionError("Architect fuer belegten Literal-Batch unnoetig"),
    ), patch("werkstatt.planner._zerlege_in_sub_tasks") as split:
        assert run_planner(st) is True

    split.assert_not_called()
    assert len(st.tasks) == 1
    assert st.tasks[0]["task_files"] == ["settings.py"]
    assert "TIMEOUT = 15` durch `TIMEOUT = 30" in st.tasks[0]["description"]
    assert "RETRIES = 2` durch `RETRIES = 5" in st.tasks[0]["description"]
    assert [(item["role"], item["status"]) for item in role_checkpoints] == [
        ("scout", "skipped"),
        ("architect", "skipped"),
        ("planner_split", "skipped"),
    ]


def test_complex_single_file_request_keeps_architect_reasoning_enabled(tmp_path):
    target = tmp_path / "src" / "auth.py"
    target.parent.mkdir()
    target.write_text("def allowed(user):\n    return True\n", encoding="utf-8")
    st = _state(tmp_path)
    st.aufgabe = "Korrigiere die Berechtigungsprüfung in src/auth.py"
    st.explorer_context = {"key_files": [{"file": "src/auth.py"}]}
    split_tasks = [{
        "id": "t1", "name": "Update authorization", "action": "update",
        "task_files": ["src/auth.py"], "criterion_refs": ["AC1"],
        "dependencies": [], "description": "Implement the approved fix.",
    }]

    def architect(state, *_args):
        assert state.architect_reasoning_enabled is True
        state.architect_prosa = "## src/auth.py\nKorrigiere die Berechtigungsprüfung."
        return True

    with patch(
        "werkstatt.planner._run_scout",
        side_effect=AssertionError("Scout ist fuer den belegten Einzeldateipfad unnoetig"),
    ), patch("werkstatt.planner.run_architect", side_effect=architect), patch(
        "werkstatt.planner._zerlege_in_sub_tasks", return_value=split_tasks,
    ), patch("werkstatt.planner.audit"):
        assert run_planner(st) is True

    assert st.tasks == split_tasks


def test_literal_replacement_with_ambiguous_or_stale_text_falls_back(tmp_path):
    from werkstatt.planner import _deterministic_literal_replace_plan

    target = tmp_path / "module.py"
    target.write_text("VALUE = OLD\nCOPY = OLD\n", encoding="utf-8")
    assert _deterministic_literal_replace_plan(
        "Ersetze `OLD` durch `NEW` in module.py.", "module.py", tmp_path,
    ) == (None, "alter_text_nicht_eindeutig")
    assert _deterministic_literal_replace_plan(
        "Ersetze `MISSING` durch `NEW` in module.py.", "module.py", tmp_path,
    ) == (None, "alter_text_nicht_eindeutig")
    assert _deterministic_literal_replace_plan(
        "Aendere die Logik in module.py.", "module.py", tmp_path,
    ) == (None, "kein_expliziter_literalersetzungsausdruck")
    target.write_text("VALUE = OLD\n", encoding="utf-8")
    assert _deterministic_literal_replace_plan(
        "Ersetze `OLD` durch `NEW` und module.py.", "module.py", tmp_path,
    ) == (None, "zieldatei_nicht_an_ersetzung_gebunden")


def test_unique_literal_setting_can_dispatch_directly_to_builder(tmp_path):
    from werkstatt.planner import _deterministic_literal_replace_plan

    target = tmp_path / "settings.py"
    target.write_text("TIMEOUT = 15  # seconds\n", encoding="utf-8")
    plan, reason = _deterministic_literal_replace_plan(
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
    from werkstatt.planner import _deterministic_literal_replace_plan

    target = tmp_path / "settings.py"
    target.write_text("TIMEOUT = 15\nTIMEOUT = 20\n", encoding="utf-8")

    assert _deterministic_literal_replace_plan(
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


def test_valid_atomic_scout_plan_skips_architect(tmp_path):
    from werkstatt.planner import run_planner

    target = tmp_path / "module.py"
    target.write_text("VALUE = OLD\n", encoding="utf-8")
    st = _state(tmp_path)
    st.aufgabe = "Ersetze OLD durch NEW in module.py."
    scout_report = {
        "auftrag_prosa": "Ersetze OLD durch NEW.",
        "api_auszug": {},
        "risiken": [],
        "atomarer_plan": True,
        "betroffene_stellen": [{
            "datei": "module.py",
            "zeile": 1,
            "alt": "OLD",
            "neu": "NEW",
            "grund": "Konsistente Umbenennung",
        }],
    }

    with patch("werkstatt.planner._run_scout", return_value=scout_report), \
         patch("werkstatt.planner.run_architect",
               side_effect=AssertionError("Architect unnoetig")):
        assert run_planner(st) is True

    assert len(st.tasks) == 1
    assert st.tasks[0]["task_files"] == ["module.py"]
    assert st.architect_prosa == "[atomarer Plan: Scout]"


def test_invalid_atomic_scout_plan_escalates_to_architect(tmp_path):
    from werkstatt.planner import run_planner

    target = tmp_path / "module.py"
    target.write_text("VALUE = OLD\n", encoding="utf-8")
    st = _state(tmp_path)
    scout_report = {
        "auftrag_prosa": "Ersetze OLD durch NEW.",
        "api_auszug": {},
        "risiken": [],
        "atomarer_plan": True,
        "betroffene_stellen": [{
            "datei": "module.py",
            "zeile": 2,
            "alt": "OLD",
            "neu": "NEW",
            "grund": "Konsistente Umbenennung",
        }],
    }

    def architect(_state, _aufgabe, _content, _key, _explorer):
        _state.architect_prosa = "## Plan\nAendere module.py."
        return True

    tasks = [{
        "id": "t1",
        "name": "Aenderung",
        "action": "update",
        "task_files": ["module.py"],
        "dependencies": [],
        "description": "Ersetze OLD durch NEW.",
    }]
    with patch("werkstatt.planner._run_scout", return_value=scout_report), \
         patch("werkstatt.planner.run_architect", side_effect=architect) as mock_architect, \
         patch("werkstatt.planner._zerlege_in_sub_tasks", return_value=tasks):
        assert run_planner(st) is True

    mock_architect.assert_called_once()
    assert st.tasks == tasks


def test_scout_route_decision_explains_escalation(tmp_path):
    from werkstatt.planner import _scout_route_decision

    target = tmp_path / "werkstatt" / "small.py"
    target.parent.mkdir()
    target.write_text("VALUE = 1\n", encoding="utf-8")
    context = {"key_files": [{"file": "werkstatt/small.py"}]}

    assert _scout_route_decision(
        "Pruefe den Fehler in werkstatt/small.py", context, tmp_path,
    ) == (None, "auftrag_enthaelt_breiten_marker:fehler")
    assert _scout_route_decision(
        "Korrigiere werkstatt/small.py", context, tmp_path,
    ) == (
        "werkstatt/small.py",
        "explizite_einzeldatei_mit_explorer_beleg",
    )
    assert _scout_route_decision(
        "Korrigiere checkpoint handling in werkstatt/small.py",
        context,
        tmp_path,
    ) == (
        "werkstatt/small.py",
        "explizite_einzeldatei_mit_explorer_beleg",
    )
    assert _scout_route_decision(
        "Fix rapid status updates in werkstatt/small.py",
        context,
        tmp_path,
    ) == (
        "werkstatt/small.py",
        "explizite_einzeldatei_mit_explorer_beleg",
    )
    assert _scout_route_decision(
        "Analysiere die Architektur in werkstatt/small.py",
        context,
        tmp_path,
    ) == (None, "auftrag_enthaelt_breiten_marker:architektur")
    assert _scout_route_decision(
        "Analyze the architecture in werkstatt/small.py",
        context,
        tmp_path,
    ) == (None, "auftrag_enthaelt_breiten_marker:architecture")

    for filename in ("api.py", "debugger.py"):
        relative = f"werkstatt/{filename}"
        target = tmp_path / relative
        target.write_text("VALUE = 1\n", encoding="utf-8")
        assert _scout_route_decision(
            f"Fix {relative}",
            {"key_files": [{"file": relative}]},
            tmp_path,
        ) == (
            relative,
            "explizite_einzeldatei_mit_explorer_beleg",
        )


def test_planner_ohne_key(tmp_path):
    st = _state(tmp_path)
    st.api_key = ""
    assert run_planner(st) is False


def test_planner_llm_fehler(tmp_path):
    st = _state(tmp_path)
    
    class FakeReply:
        ok = False
        error = "timeout"
    
    with patch("werkstatt.planner.ask_llm", return_value=FakeReply()):
        assert run_planner(st) is False


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
def test_planner_blocker_follow_up_ignore(tmp_path):
    """M-299e: Planner klassifiziert Preflight-Fehler."""
    st = _state(tmp_path)
    st.aufgabe = "Test-Aufgabe"
    st.docs = {}
    st.preflight_fehler = [
        {"klasse": "syntax", "stage_id": "py_compile", "datei": None, "text": "SyntaxError"},
    ]
    st.follow_up_fehler = [
        {"klasse": "type", "stage_id": "mypy", "datei": None, "text": "unused-ignore"},
    ]

    mock_reply = MagicMock()
    mock_reply.ok = True
    mock_reply.content = json.dumps({
        "tasks": [{"id": "t1", "name": "Fix", "description": "Fix syntax", "akzeptanzkriterien": ["ok"]}],
        "tests": ["test_fix"],
        "akzeptanzkriterien": ["fix laeuft"],
        "blocker": [{"klasse": "syntax", "text": "SyntaxError"}],
        "follow_up": [{"klasse": "type", "text": "unused-ignore"}],
        "ignore": [],
    })

    with patch("werkstatt.planner._run_scout", return_value={
    "auftrag_prosa": "Arbeite die angeforderte Aufgabe in den betroffenen Dateien um.",
    "api_auszug": {},
    "risiken": [],
    "bereits_erfuellt": False,
}), \
         patch("werkstatt.planner.ask_llm", return_value=mock_reply):
        rc = run_planner(st)

    assert rc is True
    assert len(st.blocker_fehler) == 1
    assert st.blocker_fehler[0]["klasse"] == "syntax"
    assert len(st.follow_up_fehler) == 1
    assert st.follow_up_fehler[0]["klasse"] == "type"
    assert st.ignore_fehler == []


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


def test_planner_deklariert_task_files(tmp_path):
    """M-306b: Planner speichert task_files aus Plan."""
    import json
    from unittest.mock import MagicMock, patch

    from werkstatt.planner import run_planner

    st = _state(tmp_path)
    st.aufgabe = "Repariere"
    st.docs = {}
    st.preflight_fehler = [
        {"klasse": "type", "stage_id": "mypy", "datei": "core/a.py", "text": "err"},
    ]

    mock_reply = MagicMock()
    mock_reply.ok = True
    mock_reply.content = json.dumps({
        "tasks": [{
            "id": "t1", "name": "Fix a.py", "description": "...",
            "action": "write",
            "task_files": ["core/a.py"],
            "akzeptanzkriterien": ["ok"],
        }],
        "tests": ["t1"],
        "akzeptanzkriterien": ["akz"],
        "blocker": [{"klasse": "type", "text": "err"}],
        "follow_up": [],
        "ignore": [],
    })

    with patch("werkstatt.planner._run_scout", return_value={
            "auftrag_prosa": "Arbeite die angeforderte Aufgabe in den betroffenen Dateien um.",
            "api_auszug": {},
            "risiken": [],
            "bereits_erfuellt": False,
        }), \
         patch("werkstatt.planner.ask_llm", return_value=mock_reply):
        rc = run_planner(st)

    assert rc is True
    assert len(st.tasks) == 1
    assert st.tasks[0]["task_files"] == ["core/a.py"]


@pytest.mark.skip(reason="GOLD: alter JSON-Plan-Pfad entfernt (action-Default kommt vom Planner-Split)")
def test_planner_action_missing(tmp_path):
    """M-306d: Planner-Task ohne action-Feld -> Default write + Audit."""
    import json
    from unittest.mock import MagicMock, patch

    from werkstatt.planner import run_planner

    st = _state(tmp_path)
    st.aufgabe = "Test"
    st.docs = {}

    mock_reply = MagicMock()
    mock_reply.ok = True
    mock_reply.content = json.dumps({
        "tasks": [{"id": "t1", "name": "Task ohne action"}],
        "tests": ["test"],
        "akzeptanzkriterien": ["akz"],
        "blocker": [], "follow_up": [], "ignore": [],
    })

    with patch("werkstatt.planner.ask_llm", return_value=mock_reply), \
         patch("werkstatt.planner.audit") as mock_audit:
        rc = run_planner(st)

    assert rc is True
    # M-317: action-Default ist "update" (nicht "write")
    assert st.tasks[0]["action"] == "update"
    # Audit wurde aufgerufen
    assert any(
        c[0][0] == "planner_action_missing"
        for c in mock_audit.call_args_list
    )

def test_planner_liest_progress(tmp_path):
    """M-307b-3 (N2): Planner-Prompt enthaelt PROGRESS.md-Inhalt."""
    import json
    from unittest.mock import MagicMock, patch

    from werkstatt.planner import run_planner

    # PROGRESS.md mit 2 Bloecken anlegen
    (tmp_path / "PROGRESS.md").write_text(
        "# Fortschritt: test\n\n"
        "## 2026-10-24T10:00:00 -- Vorheriger Task 1\n"
        "- **Status:** done\n"
        "- **Dateien:** a.py\n\n"
        "## 2026-10-24T10:05:00 -- Vorheriger Task 2\n"
        "- **Status:** failed\n"
        "- **Info:** builder_failed\n",
        encoding="utf-8",
    )

    st = _state(tmp_path)
    st.aufgabe = "Test-Aufgabe"
    st.docs = {}

    captured = {"calls": []}

    def _mock_ask_llm(api_key, system, user_content, **kwargs):
        captured["calls"].append(user_content)
        reply = MagicMock()
        reply.ok = True
        reply.content = json.dumps({
            "tasks": [{"id": "t1", "name": "Task 1"}],
            "tests": ["test"],
            "akzeptanzkriterien": ["akz"],
            "blocker": [], "follow_up": [], "ignore": [],
        })
        return reply

    with patch("werkstatt.planner._run_scout", return_value={
        "auftrag_prosa": "Arbeite die angeforderte Aufgabe in den betroffenen Dateien um.",
        "api_auszug": {},
        "risiken": [],
        "bereits_erfuellt": False,
    }), \
         patch("werkstatt.planner.ask_llm", side_effect=_mock_ask_llm):
        rc = run_planner(st)

    assert rc is True
    # Der Scout ist gemockt; Architect und Planner-Split folgen.
    # PROGRESS.md-Inhalt geht an den Architect als Ausfuehrungskontext.
    _alle = "\n".join(captured["calls"])
    assert "PROJEKT-FORTSCHRITT" in _alle
    assert "Vorheriger Task 1" in _alle
    assert "Vorheriger Task 2" in _alle
    assert "builder_failed" in _alle


@pytest.mark.skip(reason="GOLD: alter JSON-Plan-Pfad entfernt (phasen kommen vom Planner-Split, nicht direkt aus JSON)")
def test_planner_speichert_phasen(tmp_path):
    """M-310: Planner speichert phasen in state."""
    import json
    from unittest.mock import MagicMock, patch

    from werkstatt.planner import run_planner

    st = _state(tmp_path)
    st.aufgabe = "Test"
    st.docs = {}

    mock_reply = MagicMock()
    mock_reply.ok = True
    mock_reply.content = json.dumps({
        "phasen": [
            {"id": "p1", "titel": "Vorbereitung", "parent_id": None,
             "tasks": ["t1"]},
        ],
        "tasks": [{"id": "t1", "name": "Task 1", "action": "write"}],
        "tests": ["test"],
        "akzeptanzkriterien": ["akz"],
        "blocker": [], "follow_up": [], "ignore": [],
    })

    with patch("werkstatt.planner.ask_llm", return_value=mock_reply):
        rc = run_planner(st)

    assert rc is True
    assert len(st.phasen) == 1
    assert st.phasen[0]["id"] == "p1"
    assert st.phasen[0]["titel"] == "Vorbereitung"


def test_planner_action_create_update(tmp_path):
    """M-317: Planner akzeptiert action=create und action=update."""
    import json
    from unittest.mock import MagicMock, patch

    from werkstatt.planner import run_planner

    st = _state(tmp_path)
    st.aufgabe = "Test"
    st.docs = {}

    mock_reply = MagicMock()
    mock_reply.ok = True
    mock_reply.content = json.dumps({
        "tasks": [
            {
                "id": "t1", "name": "Neu", "action": "create",
                "criterion_refs": ["AC1"],
            },
            {
                "id": "t2", "name": "Update", "action": "update",
                "criterion_refs": ["AC1"],
            },
        ],
        "tests": ["t"],
        "akzeptanzkriterien": ["a"],
        "blocker": [], "follow_up": [], "ignore": [],
    })

    with patch("werkstatt.planner._run_scout", return_value={
            "auftrag_prosa": "Arbeite die angeforderte Aufgabe in den betroffenen Dateien um.",
            "api_auszug": {},
            "risiken": [],
            "bereits_erfuellt": False,
        }), \
         patch("werkstatt.planner.ask_llm", return_value=mock_reply):
        rc = run_planner(st)

    assert rc is True
    assert st.tasks[0]["action"] == "create"
    assert st.tasks[1]["action"] == "update"



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


def test_run_planner_behaelt_kriterien_des_planner_splits(tmp_path):
    """Ein nachgelagerter Planner-Schritt darf Kriterien nicht wieder loeschen."""
    st = _state(tmp_path)
    st.explorer_context = {"key_files": [{"file": "werkstatt/demo.py"}]}

    def _architect(_state, _aufgabe, _content, _key, _explorer):
        _state.architect_prosa = "## werkstatt/demo.py\nAendere den Handler."
        return True

    def _split(*_args, state=None, **_kwargs):
        state.akzeptanzkriterien = ["Handler gibt 404 bei unbekanntem Projekt."]
        return [{
            "id": "t1",
            "name": "Handler anpassen",
            "action": "update",
            "task_files": ["werkstatt/demo.py"],
            "dependencies": [],
            "description": "Aendere den Handler.",
        }]

    with patch("werkstatt.planner._run_scout", return_value={
        "auftrag_prosa": "Aendere den Handler.", "api_auszug": {},
        "risiken": [], "bereits_erfuellt": False,
    }), \
         patch("werkstatt.planner.run_architect", side_effect=_architect), \
         patch("werkstatt.planner._zerlege_in_sub_tasks", side_effect=_split):
        assert run_planner(st) is True

    assert st.akzeptanzkriterien == [
        "Handler gibt 404 bei unbekanntem Projekt.",
    ]


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
