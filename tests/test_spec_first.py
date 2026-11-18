from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from werkstatt.spec_first import (
    MAX_SPEC_FILES,
    _spec_test_schema_errors,
    _validate_test_source,
    run_spec_tests,
    spec_test_manifest_is_current,
)


def _manifest(root: Path, source: str) -> tuple[dict, str]:
    goal = "security-sensitive behavior"
    run_id = "spec-run-1"
    relative = Path(".werkstatt/spec-tests/spec-run-1/test_spec_1.py")
    target = root / relative
    target.parent.mkdir(parents=True)
    target.write_text(source, encoding="utf-8")
    raw = target.read_bytes()
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "goal_sha256": hashlib.sha256(goal.encode()).hexdigest(),
        "files": [{
            "path": relative.as_posix(),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "case_id": "AC1",
            "test_name": "test_ac1",
        }],
        "test_count": 1,
    }
    return manifest, goal


def test_high_risk_goal_selects_spec_first():
    from werkstatt.spec_first import requires_spec_first

    assert requires_spec_first("Change API authentication permissions")
    assert not requires_spec_first("Fix typo in README")


def test_spec_schema_allows_one_test_per_acceptance_criterion_up_to_limit():
    generated = {
        "tests": [
            {"id": f"AC{index}", "source": f"def test_ac{index}(): pass"}
            for index in range(1, 10)
        ],
    }
    assert MAX_SPEC_FILES >= 9
    assert _spec_test_schema_errors(generated) == []


def test_spec_schema_rejects_test_count_above_limit():
    generated = {
        "tests": [
            {"id": f"AC{index}", "source": f"def test_ac{index}(): pass"}
            for index in range(1, MAX_SPEC_FILES + 2)
        ],
    }
    assert _spec_test_schema_errors(generated) == [
        f"test_count_out_of_range:{MAX_SPEC_FILES + 1}",
    ]


def test_coordinator_selects_spec_builder_before_graph_split(tmp_path):
    from werkstatt.checkpoint_coordinator import choose_planner_checkpoint_action
    from werkstatt.planner_artifacts import make_role_artifact
    from werkstatt.state import RunState

    source = "def authenticate(token):\n    return token == 'ok'\n"
    target = tmp_path / "werkstatt" / "auth.py"
    target.parent.mkdir()
    target.write_text(source, encoding="utf-8")
    source_hash = hashlib.sha256(target.read_bytes()).hexdigest()
    goal = "Change authentication permissions in werkstatt/auth.py"
    state = RunState(
        project_dir=tmp_path,
        project_name="demo",
        run_id="run-1",
        aufgabe=goal,
        akzeptanzkriterien=["Unauthorized callers are rejected."],
        explorer_context={"key_files": [{
            "file": "werkstatt/auth.py",
            "source_complete": True,
            "source_sha256": source_hash,
        }]},
        preflight_checkpoint_ready=True,
    )
    state.planner_role_artifacts = {
        "scout": make_role_artifact(
            "scout", {"auftrag_prosa": "Current auth behavior inspected."},
            run_id="run-1", goal=goal, input_sha256="a" * 64,
        ),
        "architect": make_role_artifact(
            "architect",
            "Implement the approved authentication behavior and reject invalid permissions.",
            run_id="run-1", goal=goal, input_sha256="b" * 64,
        ),
    }
    decision = choose_planner_checkpoint_action(
        state,
        phase_data={"tasks": []},
        planner_role_stage="architect",
        plan_checkpoint_complete=False,
        plan_goal_matches=False,
        plan_run_matches=False,
        plan_project_matches=False,
        plan_fingerprint_matches=False,
        explicit_source_context_ready=True,
        preserve_failed_tasks_on_setup=False,
    )
    assert decision["coordinator_action"] == "planner_spec_builder"
    assert decision["next_executor"] == "planner_spec_builder"
    assert decision["reason"] == "high_risk_goal_requires_independent_frozen_spec"


def test_missing_structured_criteria_dispatches_split_instead_of_architect_replay(
    tmp_path,
):
    from werkstatt.checkpoint_coordinator import choose_planner_checkpoint_action
    from werkstatt.planner_artifacts import make_role_artifact
    from werkstatt.state import RunState

    goal = "Change authentication permissions in werkstatt/auth.py"
    source = "def authenticate(token):\n    return token == 'ok'\n"
    target = tmp_path / "werkstatt" / "auth.py"
    target.parent.mkdir()
    target.write_text(source, encoding="utf-8")
    source_hash = hashlib.sha256(target.read_bytes()).hexdigest()
    state = RunState(
        project_dir=tmp_path,
        project_name="demo",
        run_id="run-1",
        aufgabe=goal,
        explorer_context={"key_files": [{
            "file": "werkstatt/auth.py",
            "source_complete": True,
            "source_sha256": source_hash,
        }]},
        preflight_checkpoint_ready=True,
    )
    state.planner_role_artifacts = {
        "architect": make_role_artifact(
            "architect",
            "Implement the approved authentication behavior and reject invalid permissions.",
            run_id="run-1", goal=goal, input_sha256="b" * 64,
        ),
    }

    decision = choose_planner_checkpoint_action(
        state,
        phase_data={"tasks": []},
        planner_role_stage="architect",
        plan_checkpoint_complete=False,
        plan_goal_matches=False,
        plan_run_matches=False,
        plan_project_matches=False,
        plan_fingerprint_matches=False,
        explicit_source_context_ready=True,
        preserve_failed_tasks_on_setup=False,
    )

    assert decision["coordinator_action"] == "planner_split"
    assert decision["decision_basis"]["planner_role_selected"] == "planner_split"
    assert decision["reason"] == "spec_first_requires_planner_split_criteria"


def _unapproved_high_risk_candidate(tmp_path):
    from werkstatt.phase_state import PhaseState
    from werkstatt.state import RunState

    goal = "Security-sensitive API migration behavior"
    phase_state = PhaseState("demo", base_dir=tmp_path / ".werkstatt")
    tasks = [{
        "id": "t1", "name": "Apply migration", "action": "update",
        "criterion_refs": ["AC1"], "task_files": ["src/api.py"],
    }]
    criteria = ["Invalid API permissions are rejected."]
    phase_state.init_new(
        goal, tasks, tests=["pytest -q"],
        akzeptanzkriterien=criteria, phasen=[],
    )
    phase_state.run_id = "run-1"
    phase_state.data["run_id"] = "run-1"
    phase_state.record_plan_candidate(
        goal=goal, run_id="run-1", tasks=tasks, tests=["pytest -q"],
        criteria=criteria, phases=[], architect_prose="Approved design.",
        preflight_findings=[],
    )
    source_path = tmp_path / "src" / "api.py"
    source_path.parent.mkdir()
    source_path.write_text(
        "def check_permission(token: str) -> bool:\n    return bool(token)\n",
        encoding="utf-8",
    )
    source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
    state = RunState(
        project_dir=tmp_path,
        project_name="demo",
        run_id="run-1",
        aufgabe=goal,
        explorer_context={"key_files": [{
            "file": "src/api.py",
            "source_complete": True,
            "source_sha256": source_hash,
        }]},
    )
    return phase_state, state


def test_high_risk_candidate_runs_spec_builder_before_plan_gate(tmp_path):
    from werkstatt.loop import _run_coordinator_action

    phase_state, state = _unapproved_high_risk_candidate(tmp_path)

    decision = _run_coordinator_action(phase_state, state)

    assert decision["coordinator_action"] == "planner_spec_builder"
    assert decision["next_executor"] == "planner_spec_builder"
    assert decision["decision_basis"]["criteria_count"] == 1


def test_valid_frozen_spec_is_bound_into_candidate_before_plan_gate(
    tmp_path, monkeypatch,
):
    from werkstatt import spec_first
    from werkstatt.loop import _run_coordinator_action

    phase_state, state = _unapproved_high_risk_candidate(tmp_path)
    original = phase_state.data["plan_candidate_checkpoint"]["candidate_sha256"]
    spec_checkpoint = {"schema_version": 1, "run_id": "run-1", "test_count": 1}
    phase_state.data["spec_test_checkpoint"] = spec_checkpoint
    monkeypatch.setattr(
        spec_first, "spec_test_manifest_is_current", lambda *_args, **_kwargs: True,
    )

    decision = _run_coordinator_action(phase_state, state)
    candidate = phase_state.load_plan_candidate(goal=state.aufgabe, run_id="run-1")
    record = phase_state.data["plan_candidate_checkpoint"]

    assert decision["coordinator_action"] == "plan_approval_gate"
    assert candidate is not None
    assert candidate["spec_test_checkpoint"] == spec_checkpoint
    assert record["candidate_sha256"] != original


def test_spec_builder_and_validator_create_run_bound_frozen_artifact(
    tmp_path, monkeypatch,
):
    from werkstatt import agent, spec_first
    from werkstatt.phase_state import PhaseState
    from werkstatt.state import LLMReply, RunState

    target = tmp_path / "werkstatt" / "auth.py"
    target.parent.mkdir()
    source = "def authenticate(token):\n    return token == 'ok'\n"
    target.write_text(source, encoding="utf-8")
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    goal = "Change authentication permissions across the API."
    state = RunState(
        api_key="test-key",
        project_dir=tmp_path,
        project_name="demo",
        run_id="run-spec",
        aufgabe=goal,
        akzeptanzkriterien=["Invalid credentials are rejected."],
        explorer_context={"key_files": [{
            "file": "werkstatt/auth.py",
            "source_complete": True,
            "source_sha256": digest,
        }]},
    )
    phase = PhaseState("demo", base_dir=tmp_path / "state")
    phase.data = {}
    replies = [
        LLMReply(
            ok=True,
            content=(
                '{"tests":[{"id":"AC1","source":'
                '"import os\\ndef test_ac1():\\n    assert True\\n"}]}'
            ),
        ),
        LLMReply(
            ok=True,
            content=(
                '{"tests":[{"id":"AC1","source":'
                '"from werkstatt.auth import authenticate\\n'
                'def test_ac1():\\n    assert authenticate(\\\"bad\\\") is False\\n"}]}'
            ),
        ),
        LLMReply(
            ok=True,
            content='{"complete":true,"uncovered":[],"invalid_tests":[]}',
        ),
    ]
    calls = []

    def fake_ask_llm(*args, **kwargs):
        calls.append((args, kwargs))
        return replies.pop(0)

    monkeypatch.setattr(agent, "ask_llm", fake_ask_llm)
    audit_events = []
    monkeypatch.setattr(
        spec_first, "audit",
        lambda kind, payload, *_args, **_kwargs: audit_events.append(
            (kind, payload),
        ) or True,
    )
    checkpoint = spec_first.build_spec_test_checkpoint(
        state, phase, goal=goal,
    )
    assert checkpoint is not None
    assert [call[1]["rolle"] for call in calls] == [
        "spec-builder", "spec-builder", "spec-validator",
    ]
    assert all(
        call[1]["context_manifest"]["required_context_complete"] is True
        for call in calls
    )
    retry_prompt = json.loads(calls[1][0][2])
    assert retry_prompt["previous_validation_feedback"]["reason_codes"] == [
        "acceptance_criteria_coverage_mismatch",
        "import_outside_current_source_evidence",
    ]
    assert any(
        kind == "loop_phase"
        and payload.get("phase") == "spec_builder_candidate"
        and payload.get("status") == "rejected"
        and payload.get("reason_codes") == [
            "acceptance_criteria_coverage_mismatch",
            "import_outside_current_source_evidence",
        ]
        for kind, payload in audit_events
    )
    spec_prompt = retry_prompt
    api_surface = spec_prompt["current_public_api_surfaces"][0]["source"]
    assert "def authenticate(token)" in api_surface
    assert "return token" not in api_surface
    assert spec_first.spec_test_manifest_is_current(
        tmp_path, checkpoint, run_id="run-spec", goal=goal,
    )
    assert phase.data["spec_test_checkpoint"] == checkpoint
    assert state.tests and "SHA-256" in state.tests[0]


def test_spec_builder_reports_and_retries_exact_schema_shape_error(
    tmp_path, monkeypatch,
):
    from werkstatt import agent, spec_first
    from werkstatt.phase_state import PhaseState
    from werkstatt.state import LLMReply, RunState

    source_path = tmp_path / "src" / "api.py"
    source_path.parent.mkdir()
    source_path.write_text("def check():\n    return True\n", encoding="utf-8")
    digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
    goal = "Security-sensitive API behavior"
    state = RunState(
        api_key="test-key", project_dir=tmp_path, project_name="demo",
        run_id="run-schema", aufgabe=goal,
        akzeptanzkriterien=["The API rejects invalid credentials."],
        explorer_context={"key_files": [{
            "file": "src/api.py", "source_complete": True,
            "source_sha256": digest,
        }]},
    )
    phase = PhaseState("demo", base_dir=tmp_path / "state")
    phase.data = {}
    replies = [
        LLMReply(ok=True, content=(
            '{"tests":[{"id":7,"source":"def test_ac1():\\n    assert True\\n"}]}'
        )),
        LLMReply(ok=True, content=(
            '{"tests":[{"id":"AC1","source":"def test_ac1():\\n    assert True\\n"}]}'
        )),
        LLMReply(ok=True, content='{"complete":true,"uncovered":[],"invalid_tests":[]}'),
    ]
    calls = []

    def fake_ask_llm(*args, **kwargs):
        calls.append((args, kwargs))
        return replies.pop(0)

    monkeypatch.setattr(agent, "ask_llm", fake_ask_llm)
    audit_events = []
    monkeypatch.setattr(
        spec_first, "audit",
        lambda kind, payload, *_args, **_kwargs: audit_events.append(
            (kind, payload),
        ) or True,
    )

    checkpoint = spec_first.build_spec_test_checkpoint(state, phase, goal=goal)

    assert checkpoint is not None
    retry = json.loads(calls[1][0][2])["previous_validation_feedback"]
    assert retry["schema_errors"] == ["entry_1_id_missing_or_not_string"]
    rejected = next(
        payload for kind, payload in audit_events
        if kind == "loop_phase" and payload.get("phase") == "spec_builder_candidate"
    )
    assert rejected["schema_errors"] == retry["schema_errors"]


def test_spec_test_source_is_constrained_to_one_behavior_test():
    valid, reason, name = _validate_test_source(
        "def test_ac1():\n    assert 1 == 2\n",
    )
    assert (valid, reason, name) == (True, "ok", "test_ac1")

    valid, reason, _ = _validate_test_source(
        "def test_ac1():\n    open('secret.txt').read()\n",
    )
    assert not valid
    assert reason == "forbidden_test_operation"


def test_frozen_test_manifest_rejects_changed_bytes(tmp_path):
    source = "def test_ac1():\n    assert 1 == 2\n"
    manifest, goal = _manifest(tmp_path, source)
    assert spec_test_manifest_is_current(
        tmp_path, manifest, run_id="spec-run-1", goal=goal,
    )
    path = tmp_path / manifest["files"][0]["path"]
    path.write_text(source + "# changed\n", encoding="utf-8")
    assert not spec_test_manifest_is_current(
        tmp_path, manifest, run_id="spec-run-1", goal=goal,
    )


def test_baseline_qualification_requires_expected_assertion_failures(tmp_path):
    manifest, goal = _manifest(
        tmp_path, "def test_ac1():\n    assert 1 == 2\n",
    )
    result = run_spec_tests(
        tmp_path, manifest, python_executable=sys.executable,
        run_id="spec-run-1", goal=goal, must_fail=True,
    )
    assert result["ok"] is True, result
    assert result["error"] == "baseline_assertions_failed_as_expected"
    assert result["cases"] == [{
        "test_id": "AC1", "error_class": "AssertionError",
    }]


def test_post_build_spec_verify_requires_green_tests(tmp_path):
    manifest, goal = _manifest(
        tmp_path, "def test_ac1():\n    assert 1 == 2\n",
    )
    result = run_spec_tests(
        tmp_path, manifest, python_executable=sys.executable,
        run_id="spec-run-1", goal=goal, must_fail=False,
    )
    assert result["ok"] is False
    assert result["error"] == "spec_acceptance_tests_failed"
    assert result["cases"][0]["test_id"] == "AC1"


def test_phase_end_verify_runs_frozen_suite_and_sanitizes_failure(
    tmp_path, monkeypatch,
):
    from types import SimpleNamespace

    from werkstatt.roles import checkpoint_actions
    from werkstatt.state import RunState

    state = RunState(
        project_dir=tmp_path,
        project_name="demo",
        run_id="spec-run-1",
        aufgabe="security-sensitive behavior",
        progress_written_at_commit=True,
    )
    state.last_verify_results = [{
        "stage_id": "pytest", "exit_code": 0, "ok": True,
        "error_excerpt": "",
    }]
    state.last_verify_errors = []
    phase = SimpleNamespace(
        data={"spec_test_checkpoint": {"schema_version": 1}},
        run_id="spec-run-1",
    )
    monkeypatch.setattr(
        checkpoint_actions, "_verify_patches", lambda *_a, **_k: True,
    )
    monkeypatch.setattr(
        "werkstatt.spec_first.run_spec_tests",
        lambda *_a, **_k: {
            "ok": False,
            "error": "spec_acceptance_tests_failed",
            "cases": [{
                "test_id": "AC1",
                "error_class": "AssertionError",
                "private_assertion_text": "do not expose me",
            }],
        },
    )
    monkeypatch.setattr(
        "werkstatt.verify._projekt_venv_python",
        lambda *_a, **_k: sys.executable,
    )
    monkeypatch.setattr(
        "werkstatt.failure_record._worktree_fingerprint",
        lambda *_a: "a" * 64,
    )
    monkeypatch.setattr(
        checkpoint_actions, "create_failure_record",
        lambda *_a, **_k: {"failed_stages": []},
    )
    monkeypatch.setattr(
        checkpoint_actions, "audit", lambda *_a, **_k: True,
    )
    result = checkpoint_actions._phase_end_verify_action(
        state, 1, [], "demo", phase, checkpointed=False,
    )
    assert result == 1
    assert state.last_verify_results[-1]["stage_id"] == "spec_acceptance_tests"
    assert state.last_verify_results[-1]["error_excerpt"] == (
        "Frozen acceptance tests failed: AC1"
    )
    assert "private_assertion_text" not in str(state.last_verify_results)
    assert all("do not expose me" not in item for item in state.last_verify_errors)


def test_spec_only_recovery_returns_to_full_coordinator_verify(
    tmp_path, monkeypatch,
):
    from werkstatt import failure_record, reflection
    from werkstatt.roles.verify_recovery import run_phase_end_verify_recovery
    from werkstatt.state import RunState

    state = RunState(
        project_dir=tmp_path,
        project_name="demo",
        run_id="spec-run-1",
        budget={"max_llm_calls": 2},
    )
    checkpoint = {"failed_stages": [{
        "stage_id": "spec_acceptance_tests",
        "error_excerpt": "AC1: AssertionError",
    }]}
    seen = {}
    monkeypatch.setattr(
        failure_record, "_worktree_fingerprint", lambda _path: "a" * 64,
    )
    monkeypatch.setattr(
        reflection, "_reflection_loop_core",
        lambda *_a, **kwargs: seen.update(kwargs) or True,
    )
    result = run_phase_end_verify_recovery(state, checkpoint)
    assert result["status"] == "repair_handoff"
    assert seen["verify_stage_ids"] is None

