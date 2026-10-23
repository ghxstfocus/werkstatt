"""PreToolUse-Hook (Phase 10).

Prueft, ob ein Patch sicher ist, bevor er angewendet wird.
Blockiert bei .env-Dateien, destruktiven Git-Kommandos
oder leerem Diff.

Output: {"allow": bool, "reason": str}
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Verbotene Muster im Patch
DESTRUCTIVE_PATTERNS = [
    r"git\s+reset\s+--hard",
    r"git\s+clean\s+-[fd]",
    r"rm\s+-rf\s+/",
]

FORBIDDEN_FILES = [
    r"\.env$",
    r"\.env\.",
    r"secrets\.yaml$",
    r"id_rsa$",
]


def check_patch(patch_text: str, *, project_dir: str | None = None, action: str = "update") -> dict:
    """Prueft einen Patch auf Sicherheitsverletzungen.
    
    NEU: Bei action="create" wird geprueft, ob die Datei
    bereits existiert. Wenn ja -> blockieren.
    """
    if not patch_text.strip():
        return {"allow": False, "reason": "Patch ist leer."}

    # Verbotene Dateien
    for pattern in FORBIDDEN_FILES:
        if re.search(pattern, patch_text, re.MULTILINE):
            return {
                "allow": False,
                "reason": f"Patch beruehrt verbotene Datei ({pattern}). "
                          f"Entferne diese Datei aus dem Patch.",
            }

    # Destruktive Kommandos
    for pattern in DESTRUCTIVE_PATTERNS:
        if re.search(pattern, patch_text, re.MULTILINE):
            return {
                "allow": False,
                "reason": f"Patch enthaelt destruktives Kommando ({pattern}). "
                          f"Verwende eine sichere Alternative.",
            }

    # NEU: Bei create pruefen, ob Datei existiert
    if action == "create" and project_dir:
        # Datei aus dem Patch extrahieren (erste Zeile, die mit "+++ b/" beginnt)
        match = re.search(r'^\+\+\+ b/(.+)$', patch_text, re.MULTILINE)
        if match:
            file_path = Path(project_dir) / match.group(1)
            if file_path.exists():
                return {
                    "allow": False,
                    "reason": f"Datei existiert bereits: {match.group(1)}. "
                              f"Verwende action='update' statt 'create'.",
                }

    return {"allow": True, "reason": "OK"}


def main() -> int:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print(json.dumps({"allow": False, "reason": "Hook-Input ist kein JSON."}))
        return 0

    patch = data.get("patch", "")
    result = check_patch(patch)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
