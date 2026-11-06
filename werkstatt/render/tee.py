"""Tee-Stream fuer Log-Mitschnitt (OP-138 Phase 2a)."""
from __future__ import annotations

import re
import threading
from typing import TextIO

_TEE_STREAM: TextIO | None = None
_TEE_LOCK = threading.Lock()
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def set_tee_stream(stream: TextIO | None) -> None:
    """Setzt/loescht das Tee-Ziel. Schreibt jede Render-Zeile dort hin."""
    global _TEE_STREAM
    with _TEE_LOCK:
        _TEE_STREAM = stream


def _tee(text: str) -> None:
    """Schreibt text (ANSI-frei, GH-Actions-Prefixe entfernt) in Tee-Stream."""
    if _TEE_STREAM is None:
        return
    try:
        clean = _ANSI_RE.sub("", text)
        if clean.startswith("::log::"):
            clean = clean[len("::log::"):].lstrip()
        elif (clean.startswith(("::group::", "::endgroup::"))):
            return
        if not clean:
            return
        with _TEE_LOCK:
            _TEE_STREAM.write(clean + "\n")
            _TEE_STREAM.flush()
    except (OSError, ValueError):
        pass


class _TeeWriter:
    """File-Wrapper: schreibt an stdout + ruft _tee pro Zeile."""

    def __init__(self, base):
        self._base = base

    def write(self, text):
        try:
            n = self._base.write(text)
        except (ValueError, OSError):
            return 0
        try:
            for line in text.split("\n"):
                line = line.rstrip()
                if line:
                    _tee(line)
        except (ValueError, OSError):
            pass
        return n

    def flush(self):
        try:
            return self._base.flush()
        except (ValueError, OSError):
            return None

    def isatty(self):
        try:
            return self._base.isatty()
        except (ValueError, OSError):
            return False

    def fileno(self):
        return self._base.fileno()
