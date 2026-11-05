"""Modul-Globals fuer Builder-Submodule (OP-140 Phase 2b).

Alias in patch.py / run.py: _bglob
Tests patchen _common.ask_llm / _common.audit direkt.
"""
from __future__ import annotations

from werkstatt.agent import ask_llm
from werkstatt.audit import audit

__all__ = ["ask_llm", "audit"]
