from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

from werkstatt.roles.scout_execution import ScoutRoleServices, run_scout_checkpoint


def _state(**overrides):
    values = {
        "project_dir": "/repo",
        "project_name": "demo",
        "explorer_context": {"files": ["app.py"]},
        "planner_role_artifacts": {},
        "run_id": "run-1",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _services(*, direct_plan=(None, "not_applicable"),
              fingerprint="input-hash", artifact=None, scout_report=None):
    calls = {"index": Mock(return_value={"app.py": "symbols"}),
             "scout": Mock(return_value=scout_report),
             "validate": Mock(return_value=artifact),
             "checkpoint": Mock(), "audit": Mock()}
    services = ScoutRoleServices(
        direct_plan=Mock(return_value=direct_plan),
        build_index=calls["index"],
        input_fingerprint=Mock(return_value=fingerprint),
        validate_artifact=calls["validate"],
        run_scout=calls["scout"],
        publish_checkpoint=calls["checkpoint"],
        audit_call=calls["audit"],
    )
    return services, calls


def test_explicit_single_file_route_skips_scout():
    state = _state()
    report = {"ziel": "edit"}
    services, calls = _services(
        direct_plan=(report, "literal_replacement"),
    )

    result = run_scout_checkpoint(
        state, goal="edit", api_key="key", key_files=["app.py"],
        skip_path="app.py", route_reason="explorer_confirmed_single_file",
        services=services,
    )

    assert result.report == report
    assert result.source == "deterministische_literal_ersetzung"
    assert result.skip_path == "app.py"
    calls["index"].assert_not_called()
    calls["scout"].assert_not_called()
    calls["checkpoint"].assert_called_once()


def test_direct_builder_route_fails_closed_when_source_evidence_changed():
    state = _state(planner_action_role="builder_direct")
    services, calls = _services(
        direct_plan=(None, "target_changed"),
    )

    result = run_scout_checkpoint(
        state, goal="edit", api_key="key", key_files=["app.py"],
        skip_path="app.py", route_reason="explorer_confirmed_single_file",
        services=services,
    )

    assert result.failure_reason == "direct_builder_source_evidence_changed"
    calls["scout"].assert_not_called()
    calls["checkpoint"].assert_not_called()
    calls["audit"].assert_called_once()


def test_reuses_only_matching_scout_artifact():
    state = _state(planner_role_artifacts={"scout": {"some": "artifact"}})
    report = {"ziel": "edit", "relevante_dateien": []}
    artifact = {"output": report, "output_sha256": "output-hash"}
    services, calls = _services(artifact=artifact)

    result = run_scout_checkpoint(
        state, goal="edit", api_key="key", key_files=["app.py"],
        skip_path=None, route_reason="broad_goal",
        services=services,
    )

    assert result.report == report
    assert result.reused_artifact is True
    assert result.input_sha256 == "input-hash"
    calls["validate"].assert_called_once_with(
        {"some": "artifact"}, role="scout", run_id="run-1", goal="edit",
        input_sha256="input-hash",
    )
    calls["scout"].assert_not_called()


def test_calls_scout_for_current_inputs_and_rejects_missing_report():
    state = _state()
    services, calls = _services(scout_report=None)

    result = run_scout_checkpoint(
        state, goal="diagnose", api_key="key", key_files=["app.py"],
        skip_path=None, route_reason="broad_goal",
        services=services,
    )

    assert result.failure_reason == "structured_report_missing"
    calls["index"].assert_called_once_with("/repo")
    calls["scout"].assert_called_once_with(
        state, "diagnose", {"app.py": "symbols"}, ["app.py"], "key",
    )
    assert [call.args[2] for call in calls["checkpoint"].call_args_list] == [
        "running", "failed",
    ]
