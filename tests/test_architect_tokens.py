"""OP-172: Architect-Token-Budget und CoT-Trigger-Schutz.

Loop-Test-6 (2026-11-05): deepseek-reasoner produzierte 55706 Zeichen
Reasoning (~14000 Tokens). Bei max_tokens=16000 blieb kein Platz fuer
Content, Architect failte mit 'leerer content, reasoning_content
vorhanden'.
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/opt/werkstatt")

from werkstatt.architect import ARCHITECT_MAX_TOKENS, ARCHITECT_SYSTEM


def test_architect_max_tokens_mindestens_32000():
    """32000 = Default fuer deepseek-reasoner (Reasoning + Content)."""
    assert ARCHITECT_MAX_TOKENS >= 32000, (
        f"ARCHITECT_MAX_TOKENS={ARCHITECT_MAX_TOKENS} zu klein. "
        f"Reasoning-Modell braucht >= 32000, sonst sprengt CoT "
        f"das Budget (Loop-Test-6)."
    )


def test_prompt_keine_cot_trigger_konsequenz():
    """Aktive Konsequenz-Aussagen triggern CoT bei deepseek-reasoner.

    MERKPOSTEN 'Self-Check-Block auf Reasoning-Modellen = CoT-Trigger':
    'Pruefe vor dem Senden' und aehnliche Konsequenz-Aussagen sind
    CoT-Trigger. Passive Format-Vorgaben sind sicher.
    """
    verbotene = [
        "Falsche Abhaengigkeiten fuehren",
        "Pruefe vor dem Senden",
        "denke nochmal nach",
    ]
    for phrase in verbotene:
        assert phrase not in ARCHITECT_SYSTEM, (
            f"CoT-Trigger '{phrase}' im ARCHITECT_SYSTEM. "
            f"Entfernen oder passiv umformulieren."
        )


def test_prompt_hat_block_5_format():
    """Block 5 ist noch da (Passiv-Format, nicht entfernt)."""
    assert "5. Welche Dateien haengen voneinander ab?" in ARCHITECT_SYSTEM
    assert "(keine)" in ARCHITECT_SYSTEM
