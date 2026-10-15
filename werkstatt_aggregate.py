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


def _ist_werkstatt_commit(subject: str) -> bool:
    """A1 (UU3): erkennt Werkstatt-Commits streng.

    Muster: <typ>(workbench): <beschreibung>
    Typen: test, fix, feat, docs, refactor, chore.
    """
    import re as _re
    return bool(_re.match(
        r"^(test|fix|feat|docs|refactor|chore)\(workbench\):",
        subject,
    ))


def sammle_projekt_stand(project_dir: Path,
                        max_commits: int = 5) -> dict[str, Any]:
    """A1: liest die letzten Commits aus dem Ziel-Repo.

    Liefert dict mit berechnet_am, basis und
    letzte_commits. Bei Fehler (kein git, kein Repo,
    keine Commits): leeres dict (UU4).
    """
    import subprocess
    ergebnis: dict[str, Any] = {
        "berechnet_am": datetime.now(UTC).isoformat(
            timespec="seconds"),
        "basis": "git-log",
        "letzte_commits": [],
    }
    if not project_dir.exists():
        return ergebnis
    try:
        res = subprocess.run(
            ("git", "log", f"-{max_commits}",
             "--format=%h|%aI|%s"),
            cwd=str(project_dir),
            capture_output=True, text=True,
            timeout=10, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ergebnis
    if res.returncode != 0:
        return ergebnis
    for zeile in res.stdout.splitlines():
        teile = zeile.split("|", 2)
        if len(teile) != 3:
            continue
        h, datum, subject = teile
        dateien: list[str] = []
        try:
            res2 = subprocess.run(
                ("git", "show", "--name-only",
                 "--format=", h),
                cwd=str(project_dir),
                capture_output=True, text=True,
                timeout=10, check=False,
            )
            if res2.returncode == 0:
                dateien = [
                    z.strip() for z in res2.stdout.splitlines()
                    if z.strip()
                ]
        except (OSError, subprocess.SubprocessError):
            pass
        ergebnis["letzte_commits"].append({
            "hash": h,
            "datum": datum,
            "message": subject,
            "quelle": ("werkstatt"
                       if _ist_werkstatt_commit(subject)
                       else "mensch"),
            "dateien": dateien,
        })
    return ergebnis


def aggregiere(project: str, fenster_tage: int,
               project_dir: Path | None = None,
               ) -> dict[str, Any]:
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
        elif kind in ("review_round", "commit_review"):
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
        ende_event: dict[str, Any] | None = None
        if run_id:
            for x in enden:
                if x.get("run_id") == run_id:
                    ende_event = x
                    break
        letzte.append({
            "run_id": run_id,
            "start": start_ts,
            "ende": (ende_event.get("timestamp", "") if ende_event else ""),
            "rc": (ende_event.get("rc") if ende_event else None),
            "grund": (ende_event.get("grund", "") if ende_event else "kein_ende"),
            "llm_calls": (ende_event.get("llm_calls") if ende_event else None),
            "runden": (ende_event.get("runden") if ende_event else None),
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
        "projekt_stand": (
            sammle_projekt_stand(project_dir)
            if project_dir is not None else {}
        ),
    }


def _yaml_quote(text: str) -> str:
    """Zitiert einen String fuer YAML, wenn noetig."""
    if any(c in text for c in (":", "#", "\"", "'",
                                "\n")):
        esc = text.replace("\\", "\\\\").replace(
            "\"", "\\\"")
        return f'"{esc}"'
    return text


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

    ps = agg.get("projekt_stand", {})
    if ps:
        zeilen.append("")
        zeilen.append("projekt_stand:")
        zeilen.append(
            f"  berechnet_am: {ps.get('berechnet_am', '')}")
        zeilen.append(f"  basis: {ps.get('basis', '')}")
        zeilen.append("  letzte_commits:")
        for c in ps.get("letzte_commits", []):
            zeilen.append(f"    - hash: {c['hash']}")
            zeilen.append(f"      datum: {c['datum']}")
            zeilen.append(
                f"      message: {_yaml_quote(c['message'])}")
            zeilen.append(f"      quelle: {c['quelle']}")
            zeilen.append("      dateien:")
            for d in c.get("dateien", []):
                zeilen.append(f"        - {d}")

    ziel.write_text("\n".join(zeilen) + "\n", encoding="utf-8")
    return ziel


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("projekt")
    parser.add_argument("--fenster-tage", type=int, default=1)
    args = parser.parse_args()

    project_dir: Path | None = None
    yaml_pfad = PROJECTS_DIR / f"{args.projekt}.yaml"
    if yaml_pfad.exists():
        for zeile in yaml_pfad.read_text(
                encoding="utf-8").splitlines():
            if zeile.startswith("project_dir:"):
                project_dir = Path(
                    zeile.split(":", 1)[1].strip())
                break
    agg = aggregiere(args.projekt, args.fenster_tage,
                     project_dir=project_dir)
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
