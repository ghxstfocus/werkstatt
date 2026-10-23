"""Simplify-Hook (Phase 11).

Prueft einen Diff auf Komplexitaet, Duplikate und
Over-Engineering. Gibt einen Simplify-Vorschlag zurueck.

Inspiriert von Claude Codes /simplify (3 parallele Sub-Agenten).

Output: {"allow": bool, "reason": str, "patch": str | None}
"""
from __future__ import annotations

import json
import sys


def check_simplify(diff_text: str) -> dict:
    """Prueft den Diff auf Komplexitaet."""
    if not diff_text.strip():
        return {"allow": True, "reason": "Diff ist leer, nichts zu vereinfachen.", "patch": None}

    # Einfache Heuristiken (spaeter durch LLM ersetzen):
    # 1. Sehr lange Funktionen (> 100 Zeilen) -> zu komplex
    # 2. Sehr tiefe Verschachtelung (> 4 Ebenen) -> zu komplex
    lines = diff_text.split("\n")
    added_lines = [line for line in lines if line.startswith("+") and not line.startswith("+++")]
    
    if len(added_lines) > 200:
        return {
            "allow": False,
            "reason": f"Diff ist zu gross ({len(added_lines)} Zeilen). Aufteilen empfohlen.",
            "patch": None,
        }

    # 3. Duplikate: gleiche Zeile mehr als 5x
    from collections import Counter
    counts = Counter(added_lines)
    for line, count in counts.items():
        if count > 5 and len(line.strip()) > 20:
            return {
                "allow": False,
                "reason": f"Zeile wiederholt sich {count}x: {line[:80]}. "
                          f"Extrahiere in eine Hilfsfunktion.",
                "patch": None,
            }

    return {"allow": True, "reason": "Diff ist angemessen.", "patch": None}


def main() -> int:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print(json.dumps({"allow": False, "reason": "Hook-Input ist kein JSON.", "patch": None}))
        return 0

    diff = data.get("diff", "")
    result = check_simplify(diff)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
