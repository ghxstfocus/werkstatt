"""M-Arch-Reasoner (2026-11-02): Architect nutzt deepseek-reasoner."""
import importlib

import pytest


def test_architect_model_default_ist_reasoner(monkeypatch):
    monkeypatch.delenv("WERKSTATT_ARCHITECT_MODEL", raising=False)
    import werkstatt.planner as p
    importlib.reload(p)
    assert p._ARCHITECT_MODEL == "deepseek-reasoner"


def test_architect_model_env_override_auf_chat(monkeypatch):
    monkeypatch.setenv("WERKSTATT_ARCHITECT_MODEL", "deepseek-chat")
    import werkstatt.planner as p
    importlib.reload(p)
    assert p._ARCHITECT_MODEL == "deepseek-chat"
    # Cleanup: nach Test wieder reload ohne env
    monkeypatch.delenv("WERKSTATT_ARCHITECT_MODEL", raising=False)
    importlib.reload(p)


def test_get_architect_model_gibt_konstante_zurueck(monkeypatch):
    monkeypatch.delenv("WERKSTATT_ARCHITECT_MODEL", raising=False)
    import werkstatt.planner as p
    importlib.reload(p)
    from werkstatt.architect import _get_architect_model
    assert _get_architect_model() == p._ARCHITECT_MODEL
    assert _get_architect_model() == "deepseek-reasoner"
