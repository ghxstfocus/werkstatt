"""Vertrags-Tests fuer rollenbasiertes Modellrouting."""
from __future__ import annotations

import pytest

from werkstatt.model_routing import canonical_model_name, route_for_role


@pytest.mark.parametrize(
    "role",
    [
        "builder",
        "reviewer",
        "review",
        "planner",
        "planner-split",
        "scout",
        "explorer",
        "reflection",
        "validator",
        "test-spec-validator",
        "chat",
        "debugger",
        "project-coordinator",
    ],
)
def test_operational_roles_use_flash_without_thinking(
    role: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    route_label = (
        "chat" if role in {"debugger", "project-coordinator"} else role
    )
    monkeypatch.delenv(
        f"WERKSTATT_MODEL_{route_label.upper().replace('-', '_')}",
        raising=False,
    )
    route = route_for_role(role, requested_model="deepseek-v4-pro")

    assert route.model == "deepseek-flash"
    assert route.thinking == "disabled"
    assert route.reasoning_effort is None


def test_architect_uses_pro_thinking_for_legacy_reasoner_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("WERKSTATT_MODEL_ARCHITECT", raising=False)
    monkeypatch.delenv("WERKSTATT_ARCHITECT_MODEL", raising=False)
    route = route_for_role("architect", requested_model="deepseek-reasoner")

    assert route.model == "deepseek-v4-pro"
    assert route.thinking == "enabled"
    assert route.reasoning_effort == "high"


@pytest.mark.parametrize(
    ("reasoning", "thinking", "effort"),
    [(False, "disabled", None), (True, "enabled", "high")],
)
def test_role_can_override_thinking_from_checkpoint_decision(
    reasoning: bool,
    thinking: str,
    effort: str | None,
) -> None:
    route = route_for_role("architect", reasoning=reasoning)

    assert route.model == "deepseek-v4-pro"
    assert route.thinking == thinking
    assert route.reasoning_effort == effort


def test_role_override_is_scoped_and_keeps_role_thinking_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WERKSTATT_MODEL_BUILDER", "deepseek-v4-pro")
    monkeypatch.delenv("WERKSTATT_MODEL_REVIEWER", raising=False)

    builder = route_for_role("builder")
    reviewer = route_for_role("reviewer")

    assert builder.model == "deepseek-v4-pro"
    assert builder.thinking == "disabled"
    assert reviewer.model == "deepseek-flash"
    assert reviewer.thinking == "disabled"


def test_project_coordinator_shares_project_chat_model_and_reasoning_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WERKSTATT_MODEL_CHAT", "deepseek-v4-pro")
    monkeypatch.delenv("WERKSTATT_MODEL_PROJECT_COORDINATOR", raising=False)

    chat = route_for_role("chat", reasoning=True)
    coordinator = route_for_role("project-coordinator", reasoning=True)

    assert coordinator == chat
    assert coordinator.role == "chat"
    assert coordinator.model == "deepseek-v4-pro"
    assert coordinator.thinking == "enabled"
    assert coordinator.reasoning_effort == "high"


@pytest.mark.parametrize(
    ("legacy", "current"),
    [
        ("deepseek-chat", "deepseek-flash"),
        ("deepseek-reasoner", "deepseek-v4-pro"),
        ("deepseek-v4-flash", "deepseek-flash"),
        ("deepseek-v4-flash-vision-exp", "deepseek-flash"),
    ],
)
def test_legacy_model_names_are_canonicalized(
    legacy: str,
    current: str,
) -> None:
    assert canonical_model_name(legacy) == current


def test_unknown_agent_label_cannot_select_architect_model() -> None:
    route = route_for_role("future-agent", requested_model="deepseek-reasoner")

    assert route.model == "deepseek-flash"
    assert route.thinking == "disabled"
    assert route.reasoning_effort is None
