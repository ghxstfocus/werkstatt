"""Werkstatt: Dataclasses und Enums.

W36 (2026-10-17): Extrahiert aus pipeline.py.
"""
from __future__ import annotations

from dataclasses import dataclass

SUBPROCESS_TIMEOUT = 60


class BudgetExhausted(Exception):
    """Wird geworfen, wenn das LLM-Budget erschoepft ist."""




@dataclass(frozen=True)
class Measurement:
    mid: str
    argv: tuple[str, ...]
    beschreibung: str
    timeout_s: int = SUBPROCESS_TIMEOUT




@dataclass
class LLMReply:
    ok: bool
    content: str = ""
    error: str = ""




