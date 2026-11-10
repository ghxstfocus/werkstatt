"""M-Arch-Reasoner: Architect nutzt deepseek-v4-pro."""
import importlib


def test_architect_model_default_ist_v4_pro(monkeypatch):
    monkeypatch.delenv("WERKSTATT_ARCHITECT_MODEL", raising=False)
    monkeypatch.delenv("WERKSTATT_MODEL_ARCHITECT", raising=False)
    import werkstatt.planner as p
    importlib.reload(p)
    assert p._ARCHITECT_MODEL == "deepseek-v4-pro"


def test_architect_model_env_override(monkeypatch):
    monkeypatch.setenv("WERKSTATT_MODEL_ARCHITECT", "deepseek-v4-pro")
    import werkstatt.planner as p
    importlib.reload(p)
    assert p._ARCHITECT_MODEL == "deepseek-v4-pro"
    # Cleanup: nach Test wieder reload ohne env
    monkeypatch.delenv("WERKSTATT_ARCHITECT_MODEL", raising=False)
    importlib.reload(p)


def test_get_architect_model_gibt_konstante_zurueck(monkeypatch):
    monkeypatch.delenv("WERKSTATT_ARCHITECT_MODEL", raising=False)
    import werkstatt.planner as p
    importlib.reload(p)
    from werkstatt.architect import _get_architect_model
    assert _get_architect_model() == p._ARCHITECT_MODEL
    assert _get_architect_model() == "deepseek-v4-pro"
