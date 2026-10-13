#!/usr/bin/env python3
"""2200: Audit-Aggregator.

Liest audit-logs/*.jsonl, filtert nach Projekt,
aggregiert Fail-Muster und schreibt
projects/<name>.memory.yaml.

Aufruf:
    python3 werkstatt_aggregate.py <projekt> [--fenster-tage N]

Default Fenster: 1 Tag.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

WERKSTATT_HOME = Path("/opt/werkstatt")
AUDIT_DIR = WERKSTATT_HOME / "audit-logs"
PROJECTS_DIR = WERKSTATT_HOME / "projects"


def lade_events(fenster_tage: int) -> list[dict[str, Any]]:
    """Liest alle Audit-Logs im Zeitfenster."""
    grenze = datetime.now(UTC) - timedelta(days=fenster_tage)
    events: list[dict[str, Any]] = []
    for datei in sorted(AUDIT_DIR.glob("agent-pipeline-*.jsonl")):
        with datei.open("r", encoding="utf-8") as fh:
            for zeile in fh:
                zeile = zeile.strip()
                if not zeile:
                    continue
                try:
                    eintrag = json.loads(zeile)
                except json.JSONDecodeError:
                    continue
                ts = eintrag.get("timestamp", "")
                try:
                    t = datetime.fromisoformat(ts)
                except ValueError:
                    continue
                if t >= grenze:
                    events.append(eintrag)
    return events


def aggregiere(project: str, fenster_tage: int) -> dict[str, Any]:
    """Aggregiert Events eines Projekts."""
    alle = lade_events(fenster_tage)
    meine = [e for e in alle if e.get("project") == project]

    kind_counter: Counter[str] = Counter()
    starts: list[dict[str, Any]] = []
    enden: list[dict[str, Any]] = []
    verdicts: Counter[str] = Counter()
    grund_counter: Counter[str] = Counter()
    llm_calls: list[int] = []

    for e in meine:
        kind = e.get("kind", "")
        kind_counter[kind] += 1

        if kind == "pipeline_start":
            starts.append(e)
        elif kind == "pipeline_ende":
            enden.append(e)
            g = e.get("grund", "")
            if g:
                grund_counter[g] += 1
            lc = e.get("llm_calls")
            if isinstance(lc, int):
                llm_calls.append(lc)
        elif kind == "review_round":
            v = e.get("verdict", "")
            if v:
                verdicts[v] += 1
        elif kind == "commit_review":
            v = e.get("verdict", "")
            if v:
                verdicts[v] += 1

    # Fail-Muster (Events, die auf ein Problem hindeuten).
    fail_kinds = [
        "anker_einrueckung_korrigiert",
        "recovery_basis_gate_nach_apply",
        "recovery_builder_command_deadlock",
        "recovery_no_go",
        "rollback_fail_closed",
        "code_patches_leer",
    ]
    fail_muster = {k: kind_counter.get(k, 0) for k in fail_kinds}

    # Letzte 10 Laeufe (per Zeitachse).
    starts_sorted = sorted(starts, key=lambda e: e.get("timestamp", ""))
    letzte = []
    for s in starts_sorted[-10:]:
        run_id = s.get("run_id", "")
        start_ts = s.get("timestamp", "")
        # Endlog mit gleicher run_id
        if run_id:
            e = next((x for x in enden
                      if x.get("run_id") == run_id), None)
        else:
            e = None
        letzte.append({
            "run_id": run_id,
            "start": start_ts,
            "ende": (e.get("timestamp", "") if e else ""),
            "rc": (e.get("rc") if e else None),
            "grund": (e.get("grund", "") if e else "kein_ende"),
            "llm_calls": (e.get("llm_calls") if e else None),
            "runden": (e.get("runden") if e else None),
        })

    lc_min = min(llm_calls) if llm_calls else None
    lc_max = max(llm_calls) if llm_calls else None
    lc_med = int(statistics.median(llm_calls)) if llm_calls else None

    return {
        "projekt": project,
        "aggregiert_am": datetime.now(UTC).isoformat(
            timespec="seconds"),
        "fenster_tage": fenster_tage,
        "laeufe": {
            "total": len(starts),
            "mit_ende": len(enden),
            "ohne_ende": len(starts) - len(enden),
        },
        "endstaende": dict(grund_counter),
        "review_verdicts": dict(verdicts),
        "llm_calls": {
            "min": lc_min,
            "max": lc_max,
            "median": lc_med,
            "samples": len(llm_calls),
        },
        "fail_muster": fail_muster,
        "letzte_laeufe": letzte,
    }


def schreibe_memory(agg: dict[str, Any]) -> Path:
    """Schreibt die Aggregation als YAML."""
    project = agg["projekt"]
    ziel = PROJECTS_DIR / f"{project}.memory.yaml"

    # Minimal-YAML, kein PyYAML noetig.
    zeilen: list[str] = []
    zeilen.append(f"projekt: {agg['projekt']}")
    zeilen.append(f"aggregiert_am: {agg['aggregiert_am']}")
    zeilen.append(f"fenster_tage: {agg['fenster_tage']}")
    zeilen.append("")
    zeilen.append("laeufe:")
    for k, v in agg["laeufe"].items():
        zeilen.append(f"  {k}: {v}")
    zeilen.append("")
    zeilen.append("endstaende:")
    for k, v in sorted(agg["endstaende"].items()):
        zeilen.append(f"  {k}: {v}")
    zeilen.append("")
    zeilen.append("review_verdicts:")
    for k, v in sorted(agg["review_verdicts"].items()):
        zeilen.append(f"  {k}: {v}")
    zeilen.append("")
    zeilen.append("llm_calls:")
    for k, v in agg["llm_calls"].items():
        zeilen.append(f"  {k}: {v}")
    zeilen.append("")
    zeilen.append("fail_muster:")
    for k, v in sorted(agg["fail_muster"].items()):
        zeilen.append(f"  {k}: {v}")
    zeilen.append("")
    zeilen.append("letzte_laeufe:")
    for lauf in agg["letzte_laeufe"]:
        zeilen.append(f"  - run_id: {lauf['run_id']}")
        zeilen.append(f"    start: {lauf['start']}")
        zeilen.append(f"    ende: {lauf['ende']}")
        zeilen.append(f"    rc: {lauf['rc']}")
        zeilen.append(f"    grund: {lauf['grund']}")
        zeilen.append(f"    llm_calls: {lauf['llm_calls']}")
        zeilen.append(f"    runden: {lauf['runden']}")

    ziel.write_text("\n".join(zeilen) + "\n", encoding="utf-8")
    return ziel


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("projekt")
    parser.add_argument("--fenster-tage", type=int, default=1)
    args = parser.parse_args()

    agg = aggregiere(args.projekt, args.fenster_tage)
    ziel = schreibe_memory(agg)
    print(f"[+] {ziel}")
    print(f"    Laeufe: {agg['laeufe']['total']} "
          f"(mit Ende: {agg['laeufe']['mit_ende']})")
    print(f"    llm_calls: min={agg['llm_calls']['min']} "
          f"max={agg['llm_calls']['max']} "
          f"median={agg['llm_calls']['median']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
