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
    ],
)
def test_operational_roles_use_flash_without_thinking(
    role: str,
) -> None:
    route = route_for_role(role, requested_model="deepseek-v4-pro")

    assert route.model == "deepseek-flash"
    assert route.thinking == "disabled"
    assert route.reasoning_effort is None


def test_architect_uses_pro_thinking_for_legacy_reasoner_alias() -> None:
    route = route_for_role("architect", requested_model="deepseek-reasoner")

    assert route.model == "deepseek-v4-pro"
    assert route.thinking == "enabled"
    assert route.reasoning_effort == "high"


def test_role_override_is_scoped_and_keeps_role_thinking_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WERKSTATT_MODEL_BUILDER", "deepseek-v4-pro")

    builder = route_for_role("builder")
    reviewer = route_for_role("reviewer")

    assert builder.model == "deepseek-v4-pro"
    assert builder.thinking == "disabled"
    assert reviewer.model == "deepseek-flash"
    assert reviewer.thinking == "disabled"


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
