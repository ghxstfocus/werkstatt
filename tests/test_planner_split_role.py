from types import SimpleNamespace

from werkstatt.roles.planner_split import (
    PlannerSplitInput,
    build_context_manifest,
    run_planner_split_role,
)


def _request(*, scope="task_graph", task_id=None):
    system = "task graph role contract"
    user = "approved goal and architect handoff"
    manifest = build_context_manifest(
        system_prompt=system,
        user_prompt=user,
        key_files=["werkstatt/loop.py"],
        source_evidence={"sources": []},
        source_context="",
        sections=[{"name": "architect_prose", "status": "required_included"}],
        scope=scope,
        task_id=task_id,
    )
    return PlannerSplitInput(
        api_key="secret-for-provider",
        system_prompt=system,
        user_prompt=user,
        state=object(),
        context_manifest=manifest,
    )


def test_planner_split_role_sends_only_explicit_prompt_packet():
    request = _request()
    calls = []

    def ask_llm(*args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(ok=True, content='{"tasks": []}')

    result = run_planner_split_role(
        request,
        ask_llm_call=ask_llm,
        spinner_call=lambda _label, call: call(),
    )

    assert result.ok is True
    assert result.content == '{"tasks": []}'
    assert len(calls) == 1
    args, kwargs = calls[0]
    assert args == (
        "secret-for-provider",
        request.system_prompt,
        request.user_prompt,
    )
    assert kwargs["aufgabe"] == "planner-split"
    assert kwargs["max_tokens"] == 8000
    assert kwargs["context_manifest"] == request.context_manifest
    assert kwargs["state"] is request.state


def test_planner_split_role_rejects_stale_manifest_before_provider_call():
    request = _request()
    calls = []
    stale_manifest = dict(request.context_manifest)
    stale_manifest["user_sha256"] = "stale"
    stale_request = PlannerSplitInput(
        api_key=request.api_key,
        system_prompt=request.system_prompt,
        user_prompt=request.user_prompt,
        state=request.state,
        context_manifest=stale_manifest,
    )

    result = run_planner_split_role(
        stale_request,
        ask_llm_call=lambda *args, **kwargs: calls.append((args, kwargs)),
        spinner_call=lambda _label, call: call(),
    )

    assert result.ok is False
    assert result.error == "planner_split_input_manifest_mismatch"
    assert calls == []


def test_oversized_task_uses_the_same_worker_on_demand():
    request = _request(scope="single_task", task_id="t7")
    calls = []

    result = run_planner_split_role(
        request,
        ask_llm_call=lambda *args, **kwargs: (
            calls.append((args, kwargs))
            or SimpleNamespace(ok=True, content='{"tasks": []}')
        ),
        spinner_call=lambda _label, call: call(),
    )

    assert result.ok is True
    assert calls[0][1]["max_tokens"] == 4000
    assert calls[0][1]["context_manifest"]["scope"] == "single_task"
    assert calls[0][1]["context_manifest"]["task_id"] == "t7"
