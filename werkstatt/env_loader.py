"""Laedt .env-Datei (KEY=VALUE) in os.environ."""
from __future__ import annotations

import os
from pathlib import Path


def load_env(path: Path | None = None) -> int:
    """Laedt .env in os.environ. Gibt Anzahl geladener Variablen zurueck."""
    if path is None:
        path = Path(__file__).parent.parent / ".env"
    if not path.exists():
        return 0
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value
            count += 1
    return count
