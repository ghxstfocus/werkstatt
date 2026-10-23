"""PostToolUse-Hook (Phase 10).

Prueft die Baseline nach dem Anwenden eines Patches.
Ruft tools/quality_gate.py auf.

Output: {"allow": bool, "reason": str}
"""
from __future__ import annotations

import json
import subprocess
import sys


def check_baseline() -> dict:
    """Ruft quality_gate.py auf und prueft ok=true."""
    try:
        res = subprocess.run(
            ["python3", "/opt/werkstatt/tools/quality_gate.py", "--json"],
            cwd="/opt/werkstatt",
            capture_output=True, text=True, timeout=300, check=False,
        )
        output = res.stdout
        if '"ok": true' in output or '"ok":true' in output:
            return {"allow": True, "reason": "Baseline gruen"}
        # Fehler extrahieren
        return {
            "allow": False,
            "reason": f"Baseline rot: {output[:500]}",
        }
    except Exception as exc:  # noqa: BLE001
        return {"allow": False, "reason": f"Hook-Fehler: {exc}"}


def main() -> int:
    result = check_baseline()
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
