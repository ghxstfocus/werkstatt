"""Erlaubte Umgebungsvariablen fuer Subprozesse.

Aus pipeline.py extrahiert (Phase 2 / Gate 18,
Befund BW). Selbststaendig (nur os.environ).

Konsumenten:
- pipeline.py (20x, Loop-Kontext).
- commit_input.py (in _git_diff_phase).
- Tests (3x).
"""

from __future__ import annotations

import os


def subprocess_env() -> dict[str, str]:
    """Erlaubt nur die Umgebungsvariablen, die Subprozesse brauchen.

    Auflage 2086: DEEPSEEK_API_KEY und andere Secrets werden
    NICHT durchgereicht. Allowlist statt Blacklist, damit neue
    Secrets nicht automatisch im Subprozess-Env landen.

    Erweiterung: Wenn ein Subprozess eine weitere Variable
    braucht, wird sie hier EXPLIZIT ergaenzt.
    """
    erlaubt = (
        "PATH", "HOME", "LANG", "LC_ALL", "LC_CTYPE",
        "TMPDIR", "USER", "SHELL",
    )
    return {k: os.environ[k] for k in erlaubt if k in os.environ}
