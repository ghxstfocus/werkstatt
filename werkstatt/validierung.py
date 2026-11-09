"""Eingabe-Validierung fuer git-ref-Argumente.

Zentrale Stelle, damit HTTP-Endpoints (werkstatt/web/app.py) und
Chat-Tools (werkstatt/chat_tools.py) dieselbe Muster-Semantik
nutzen (OP-390, Defense-in-depth gegen git-Argument-Injection wie
``--output=...`` oder ``--ext-diff``).

Der Kern (werkstatt/) darf werkstatt/web/ nicht importieren; darum
liegt der Helper hier und nicht in app.py.
"""
from __future__ import annotations

import re

__all__ = ["REF_MUSTER", "pruefe_ref"]

# Git-Ref-Muster: erlaubt Branch-Namen, Tags, SHAs, HEAD~N, HEAD^,
# origin/main, refs/heads/x. Verbietet fuehrendes ``-``
# (Option-Interpretation: --output=, -p, --ext-diff) sowie
# Leerzeichen und Shell-Metazeichen. Max 128 Zeichen.
REF_MUSTER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-/~^@{}]{0,127}$")


def pruefe_ref(ref: str) -> str:
    """Validiert einen git-ref gegen das erlaubte Muster.

    Rueckgabe: der unveraenderte ref-String.

    Raises:
        ValueError: bei Verstoss gegen das Muster (leer, fuehrendes
            ``-``, Leerzeichen, Shell-Metazeichen, ueberlang).
    """
    if not isinstance(ref, str) or not REF_MUSTER.fullmatch(ref):
        raise ValueError(f"ungueltiger ref {ref!r}")
    return ref
