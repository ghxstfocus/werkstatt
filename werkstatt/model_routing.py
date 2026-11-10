"""Rollenbasiertes Routing fuer die aktuellen DeepSeek-API-Modelle.

DeepSeek hat die Modellnamen deepseek-chat/deepseek-reasoner abgeschaltet.
Legacy-Konfigurationen werden an der Grenze auf die aktuellen IDs abgebildet.
"""
from __future__ import annotations

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
    "reflection": "deepseek-flash",
    "debugger": "deepseek-flash",
    "solver": "deepseek-flash",
    "planner": "deepseek-flash",
    "planner-split": "deepseek-flash",
    "explorer": "deepseek-flash",
    "scout": "deepseek-flash",
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
    """Mappt alte oder retired IDs auf die aktuelle API-Modell-ID."""
    clean = model.strip()
    return _LEGACY_MODELS.get(clean, clean)


def route_for_role(role: str, requested_model: str | None = None) -> ModelRoute:
    """Liefert das Rollenmodell; nur Architect bekommt Pro-Thinking."""
    label = role.strip().lower().replace("_", "-")
    model = canonical_model_name(
        requested_model or _ROLE_MODELS.get(label, "deepseek-flash")
    )
    if label == "architect":
        return ModelRoute(label, model, "enabled", "high")
    return ModelRoute(label, model, "disabled", None)
