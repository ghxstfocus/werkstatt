"""Klassifikation von Verify-Fehlern (hart vs. weich).

Hart (blockiert Reviewer):
- py_compile: Syntax-Fehler, Code laeuft nicht
- pytest: Tests fehlgeschlagen
- ruff mit F-Klasse (F401, F811, F821, F822): undefined names,
  unused imports -> Code laeuft oft nicht korrekt

Weich (blockiert Reviewer NICHT):
- ruff E/C/W (Style, Complexity)
- mypy (Baseline-Drift im Repo bekannt)
"""
from __future__ import annotations

import re

# ruff F-Klasse: "ruff_changed: F822 ..."
_RUFF_F_KLASSE = re.compile(r"\bF[0-9]{3}\b")
_HART_PREFIXE = ("py_compile", "pytest", "test", "test_")


def ist_harter_verify_fehler(error: str) -> bool:
    """Klassifiziert einen Verify-Fehler-String als hart."""
    s = str(error)
    for prefix in _HART_PREFIXE:
        if s.startswith(prefix) or f"{prefix}_" in s or f"{prefix}:" in s:
            return True
    return bool(_RUFF_F_KLASSE.search(s))


def filtere_harte_verify_fehler(errors: list) -> list:
    """Gibt nur die harten Fehler zurueck."""
    if not errors:
        return []
    return [e for e in errors if ist_harter_verify_fehler(e)]
