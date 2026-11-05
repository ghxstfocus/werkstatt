"""Rollen-Registry (2026-11-05): Strukturtests."""
from __future__ import annotations

import sys

sys.path.insert(0, "/opt/werkstatt")


def test_alle_rollen_registriert():
    from werkstatt.rollen import ROLLEN
    expected = {"architect", "planner", "builder", "reviewer",
                "explorer", "scout", "reflection"}
    assert set(ROLLEN.keys()) == expected


def test_architect_hat_keine_skills():
    from werkstatt.rollen import ROLLEN
    a = ROLLEN["architect"]
    assert a.skills == ()
    assert a.skill_filter_rolle is None
    assert a.tools == ()


def test_keine_rolle_laedt_plan_crafting_ausser_planner():
    from werkstatt.rollen import ROLLEN
    for name, rolle in ROLLEN.items():
        if "plan-crafting" in rolle.skills:
            assert name == "planner"


def test_prompt_module_existiert():
    import importlib

    from werkstatt.rollen import ROLLEN
    for rolle in ROLLEN.values():
        if not rolle.prompt_module:
            continue
        mod = importlib.import_module(rolle.prompt_module)
        if rolle.prompt_const:
            assert hasattr(mod, rolle.prompt_const)


def test_architect_system_prompt_laedbar():
    from werkstatt.rollen import ROLLEN
    prompt = ROLLEN["architect"].lade_system_prompt()
    assert "elite Software-Architekt" in prompt
    assert len(prompt) > 1000
