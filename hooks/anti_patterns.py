"""Anti-Pattern-Hook (A8-3, 2026-10-23).

Liest Katalog, filtert nach Rolle + Trigger-Grund,
sortiert nach stufe(e), gibt JSON aus.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ANTI_PATTERN_KATALOG = Path("/opt/werkstatt/anti-patterns/katalog.yaml")
AP_BESCHREIBUNG_MAX = 500
AP_LIMIT = 3


def lade_anti_patterns(pfad: Path = ANTI_PATTERN_KATALOG) -> list[dict]:
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        raise RuntimeError("yaml fehlt")
    if not pfad.exists():
        raise FileNotFoundError(f"Anti-Pattern-Katalog fehlt: {pfad}")
    with pfad.open(encoding="utf-8") as fh:
        daten = yaml.safe_load(fh) or {}
    return daten.get("anti_patterns", []) or daten.get("eintraege", []) or []


def _stufe(e: dict, trigger_grund: str | None) -> int:
    if trigger_grund is None:
        return 2
    tgs = e.get("trigger_gruende")
    if tgs and trigger_grund in tgs:
        return 1
    return 2


def filtere_sortiert(
    alle: list[dict],
    rolle: str,
    trigger_grund: str | None,
    limit: int = AP_LIMIT,
) -> list[dict]:
    ausgewaehlt = []
    for e in alle:
        if rolle not in e.get("rollen", []):
            continue
        if trigger_grund is not None:
            tgs = e.get("trigger_gruende")
            if tgs and trigger_grund not in tgs:
                continue
        ausgewaehlt.append(e)
    ausgewaehlt.sort(key=lambda e: _stufe(e, trigger_grund))
    return ausgewaehlt[:limit]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rolle", required=True)
    parser.add_argument("--trigger-grund", default="")
    parser.add_argument("--limit", type=int, default=AP_LIMIT)
    args = parser.parse_args()
    try:
        alle = lade_anti_patterns()
        tg = args.trigger_grund or None
        treffer = filtere_sortiert(alle, args.rolle, tg, limit=args.limit)
        out = [
            {
                "id": e.get("id", ""),
                "titel": e.get("titel", ""),
                "beschreibung": (e.get("beschreibung") or "").strip()[:AP_BESCHREIBUNG_MAX],
                "loesung": (e.get("loesung") or "").strip()[:AP_BESCHREIBUNG_MAX],
            }
            for e in treffer
        ]
        json.dump(out, sys.stdout, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"[hook] Fehler: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
