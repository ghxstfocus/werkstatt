"""Rollenbasiertes Routing fuer die DeepSeek-API.

Legacy-Modellnamen werden auf aktuelle IDs abgebildet. Fuer bekannte Rollen
hat die Rollen-Policy Vorrang vor alten Call-Sites; individuelle Abweichungen
sind ueber WERKSTATT_MODEL_<ROLLE> konfigurierbar.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

__all__ = ["ModelRoute", "canonical_model_name", "route_for_role"]

_LEGACY_MODELS = {
    "deepseek-chat": "deepseek-flash",
    "deepseek-reasoner": "deepseek-v4-pro",
    "deepseek-v4-flash": "deepseek-flash",
    "deepseek-v4-flash-vision-exp": "deepseek-flash",
}

_ROLE_MODELS = {
    "architect": "deepseek-v4-pro",
    "builder": "deepseek-flash",
    "reviewer": "deepseek-flash",
    "review": "deepseek-flash",
    "reflection": "deepseek-flash",
    "planner": "deepseek-flash",
    "planner-split": "deepseek-flash",
    "explorer": "deepseek-flash",
    "scout": "deepseek-flash",
    "validator": "deepseek-flash",
    "test-spec-validator": "deepseek-flash",
    "chat": "deepseek-flash",
}


@dataclass(frozen=True)
class ModelRoute:
    """Model, Thinking-Schalter und Effort fuer eine Rolle."""

    role: str
    model: str
    thinking: str
    reasoning_effort: str | None


def canonical_model_name(model: str) -> str:
    """Mappt alte Modellnamen auf aktuelle API-IDs."""
    clean = model.strip()
    return _LEGACY_MODELS.get(clean, clean)


def _role_label(role: str) -> str:
    label = role.strip().lower().replace("_", "-")
    if label == "debugger":
        return "chat"
    if label.startswith("planner-") and label not in _ROLE_MODELS:
        return "planner"
    if label.startswith("reflection-") and label not in _ROLE_MODELS:
        return "reflection"
    return label


def route_for_role(role: str, requested_model: str | None = None) -> ModelRoute:
    """Waehlt Modell und Thinking passend zur Rolle.

    Bekannte Rollen koennen nur durch ihre eigene WERKSTATT_MODEL_<ROLLE>
    Variable ueberschrieben werden. Veraltete Modellargumente aus Call-Sites
    koennen die Rollen-Policy nicht versehentlich aushebeln.
    """
    label = _role_label(role)
    env_name = f"WERKSTATT_MODEL_{label.upper().replace('-', '_')}"
    configured = os.environ.get(env_name)
    if label == "architect":
        # Alte Konfiguration bleibt kompatibel, wird aber kanonisiert.
        configured = (
            configured
            or os.environ.get("WERKSTATT_ARCHITECT_MODEL")
            or requested_model
        )
    if configured:
        model = canonical_model_name(configured)
    elif label in _ROLE_MODELS:
        model = _ROLE_MODELS[label]
    else:
        model = canonical_model_name(requested_model or "deepseek-flash")

    if label == "architect":
        return ModelRoute(label, model, "enabled", "high")
    return ModelRoute(label, model, "disabled", None)
