#!/usr/bin/env python3
"""State-Flow-Diagnose (read-only).

Fuer jedes RunState-Feld: Writer, Reader, Getattr-only, Contract-Bezug,
Risiko. Ergaenzt tools/state_inventory.py (dort: Kategorien) um die
Frage "was fliesst wann wohin".

CLI:
  (ohne Flag)      Tabelle aller Felder
  --field X        Detail-Steckbrief fuer Feld X
  --risk LEVEL     nur Felder mit Risiko (HOCH/MITTEL/NIEDRIG)
  --orphans        tote Felder + write_only ohne Contract
  --check          Exit 1 bei neuem Multi-Writer/Ghost-Active/Tot
  --write-baseline JSON nach tools/state_flow_baseline.json (stdout)
  --json           Maschinenlesbar
  --markdown       Markdown-Report nach docs/STATE-FLOW.md
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tools.state_inventory import kategorisiere
from werkstatt.state_contracts import TRANSITIONS

BASELINE_PATH = Path(__file__).resolve().parent / "state_flow_baseline.json"

# Property-View zu RunState-Feldern (aus state.py::RunState, OP-135a)
CONTRACT_FIELD_MAP: dict[str, list[str]] = {
    "explorer_output": ["explorer_context"],
    "explorer_diagnostics": ["explorer_findings"],
    "scout_output": ["scout_api_auszug"],
    "architect_output": ["architect_prosa"],
    "planner_output": ["tasks", "tests", "akzeptanzkriterien"],
}


def _feld_to_contracts() -> dict[str, list[str]]:
    """Rueckwaerts-Map: RunState-Feld -> [Contract-Name, ...]."""
    out: dict[str, list[str]] = defaultdict(list)
    for contract_name, fields in CONTRACT_FIELD_MAP.items():
        for f in fields:
            out[f].append(contract_name)
    return dict(out)


def _feld_to_transitions() -> dict[str, list[str]]:
    """Rueckwaerts-Map: RunState-Feld -> [Transition-Key, ...]."""
    out: dict[str, list[str]] = defaultdict(list)
    for trans_key, contract_list in TRANSITIONS.items():
        for contract_name, _regel in contract_list:
            for f in CONTRACT_FIELD_MAP.get(contract_name, []):
                out[f].append(trans_key)
    return dict(out)


def _risiko(info: dict, contracts: list[str]) -> tuple[str, list[str]]:
    """Bewertet das Debug-Risiko eines Felds. Rueckgabe: (level, gruende)."""
    gruende: list[str] = []
    kat = info["kategorie"]
    nw = len(info["schreiber"])
    nr = len(info["leser"])
    ng = len(info["getattr"])
    ghost = kat == "ghost"
    tot = kat == "tot"
    multi_writer = nw >= 2
    has_contract = bool(contracts)

    if ghost:
        gruende.append("ghost (nicht in RunState deklariert)")
    if tot:
        gruende.append("tot (weder Reader noch Writer)")
    if multi_writer and not has_contract:
        gruende.append(f"multi-writer({nw}) ohne Contract")
    elif multi_writer:
        gruende.append(f"multi-writer({nw})")
    if nr >= 2 and not has_contract:
        gruende.append(f"multi-reader({nr}) ohne Contract")
    if ng >= 3:
        gruende.append(f"getattr-only in {ng} Datei(en)")

    if multi_writer and not has_contract:
        return "HOCH", gruende
    if ghost and (multi_writer or ng >= 2):
        return "HOCH", gruende
    if multi_writer:
        return "MITTEL", gruende
    if ghost or tot:
        return "MITTEL", gruende
    if ng >= 3:
        return "MITTEL", gruende
    return "NIEDRIG", gruende


def baue_flow_index() -> dict[str, dict]:
    """Fuer jedes Feld: Kategorie, Writer, Reader, Getattr, Contracts, Transitions, Risiko."""
    idx = kategorisiere()
    f_to_c = _feld_to_contracts()
    f_to_t = _feld_to_transitions()

    ergebnis: dict[str, dict] = {}
    for name, info in idx.items():
        contracts = f_to_c.get(name, [])
        risiko, gruende = _risiko(info, contracts)
        ergebnis[name] = {
            "kategorie": info["kategorie"],
            "typ": info["typ"],
            "deklariert": info["typ"] != "?",
            "schreiber": info["schreiber"],
            "leser": info["leser"],
            "getattr": info["getattr"],
            "contracts": contracts,
            "transitions": f_to_t.get(name, []),
            "risiko": risiko,
            "gruende": gruende,
        }
    return ergebnis


def _aggregat(index: dict[str, dict]) -> dict[str, list[str]]:
    """Aggregat-Mengen fuer Baseline-Vergleich."""
    return {
        "multi_writer": sorted(
            n for n, i in index.items() if len(i["schreiber"]) >= 2
        ),
        "ghost_active": sorted(
            n for n, i in index.items()
            if i["kategorie"] == "ghost" and len(i["schreiber"]) >= 1
        ),
        "tote": sorted(
            n for n, i in index.items() if i["kategorie"] == "tot"
        ),
    }


def _write_baseline() -> int:
    """Schreibt JSON mit aktueller Baseline nach stdout."""
    index = baue_flow_index()
    agg = _aggregat(index)
    print(json.dumps({
        "generiert_von": "tools/state_flow.py --write-baseline",
        "hinweis": "Nicht von Hand editieren. Regenerieren bei "
                   "gewollter Baseline-Aenderung.",
        **agg,
    }, indent=2, sort_keys=True))
    return 0


def _read_baseline() -> dict[str, set[str]]:
    """Liest Baseline-JSON. Leer wenn Datei fehlt (fail-open)."""
    if not BASELINE_PATH.exists():
        return {"multi_writer": set(), "ghost_active": set(), "tote": set()}
    data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    return {
        "multi_writer": set(data.get("multi_writer", [])),
        "ghost_active": set(data.get("ghost_active", [])),
        "tote": set(data.get("tote", [])),
    }


def _tabelle(index: dict[str, dict]) -> None:
    header = (
        f"{'Feld':<32} {'Kategorie':<14} {'D':>2} {'W':>2} {'R':>2} "
        f"{'G':>2} {'C':>2} {'Risiko':<6}"
    )
    print(header)
    print("-" * len(header))
    for name in sorted(index):
        info = index[name]
        d = "J" if info["deklariert"] else "n"
        c = ",".join(info["contracts"]) or "-"
        print(
            f"{name:<32} {info['kategorie']:<14} {d:>2} "
            f"{len(info['schreiber']):>2} {len(info['leser']):>2} "
            f"{len(info['getattr']):>2} {c[:2]:>2} {info['risiko']:<6}"
        )
    print()
    print("Legende: D=deklariert, W=Writer, R=Reader, G=Getattr, C=Contract")


def _steckbrief(name: str, info: dict) -> None:
    print(f"Feld: {name}")
    print(f"  Kategorie:    {info['kategorie']}")
    print(f"  Deklariert:   {'JA' if info['deklariert'] else 'NEIN'}"
          f" (typ: {info['typ']})")
    print(f"  Writer ({len(info['schreiber'])}):")
    for f in info["schreiber"]:
        print(f"    - {f}")
    if not info["schreiber"]:
        print("    (keine)")
    print(f"  Reader ({len(info['leser'])}):")
    for f in info["leser"][:15]:
        print(f"    - {f}")
    if len(info["leser"]) > 15:
        print(f"    ... +{len(info['leser']) - 15} weitere")
    if not info["leser"]:
        print("    (keine)")
    print(f"  Getattr-only ({len(info['getattr'])}):")
    for f in info["getattr"]:
        print(f"    - {f}")
    if not info["getattr"]:
        print("    (keine)")
    print(f"  Contracts:    {info['contracts'] or '-'}")
    print(f"  Transitions:  {info['transitions'] or '-'}")
    print(f"  Risiko:       {info['risiko']}")
    if info["gruende"]:
        print("  Gruende:")
        for g in info["gruende"]:
            print(f"    - {g}")


def _check(index: dict[str, dict]) -> int:
    aktuell = _aggregat(index)
    baseline = _read_baseline()

    multi = set(aktuell["multi_writer"])
    ghost_active = set(aktuell["ghost_active"])
    tote = set(aktuell["tote"])

    neu_multi = multi - baseline["multi_writer"]
    neu_ghost = ghost_active - baseline["ghost_active"]
    neu_tot = tote - baseline["tote"]

    if not (neu_multi or neu_ghost or neu_tot):
        print("OK Kein State-Flow-Drift "
              f"({len(multi)} multi-writer, {len(ghost_active)} ghost-active, "
              f"{len(tote)} tot — alle in Baseline).")
        return 0

    print("FAIL State-Flow-Drift:")
    if neu_multi:
        print(f"  Neue Multi-Writer: {sorted(neu_multi)}")
    if neu_ghost:
        print(f"  Neue Ghost-Active: {sorted(neu_ghost)}")
    if neu_tot:
        print(f"  Neue Tote: {sorted(neu_tot)}")
    return 1


def _markdown(index: dict[str, dict], path: Path) -> None:
    lines = [
        "# State-Flow Report",
        "",
        "Generiert von `tools/state_flow.py --markdown`. Nicht von Hand editieren.",
        "",
        "## Zusammenfassung",
        "",
    ]
    total = len(index)
    deklariert = sum(1 for i in index.values() if i["deklariert"])
    ghost = sum(1 for i in index.values() if i["kategorie"] == "ghost")
    tot = sum(1 for i in index.values() if i["kategorie"] == "tot")
    multi = sum(1 for i in index.values() if len(i["schreiber"]) >= 2)
    hoch = sum(1 for i in index.values() if i["risiko"] == "HOCH")
    mittel = sum(1 for i in index.values() if i["risiko"] == "MITTEL")
    niedrig = sum(1 for i in index.values() if i["risiko"] == "NIEDRIG")
    lines.extend([
        f"- Felder gesamt: **{total}**",
        f"- Deklariert: **{deklariert}**",
        f"- Ghost (nicht deklariert): **{ghost}**",
        f"- Tote Felder: **{tot}**",
        f"- Multi-Writer: **{multi}**",
        f"- Risiko HOCH: **{hoch}**, MITTEL: **{mittel}**, NIEDRIG: **{niedrig}**",
        "",
    ])

    def _sektion(titel: str, felder: list) -> None:
        lines.append(f"## {titel}")
        lines.append("")
        if not felder:
            lines.append("(keine)")
            lines.append("")
            return
        lines.append("| Feld | Kategorie | Writer | Reader | Getattr | Contracts | Gruende |")
        lines.append("|---|---|---|---|---|---|---|")
        for name, info in felder:
            g = "; ".join(info["gruende"])[:80]
            lines.append(
                f"| `{name}` | {info['kategorie']} | {len(info['schreiber'])} "
                f"| {len(info['leser'])} | {len(info['getattr'])} "
                f"| {','.join(info['contracts']) or '—'} | {g} |"
            )
        lines.append("")

    _sektion("Risiko HOCH",
             sorted((n, i) for n, i in index.items() if i["risiko"] == "HOCH"))
    _sektion("Risiko MITTEL",
             sorted((n, i) for n, i in index.items() if i["risiko"] == "MITTEL"))
    _sektion("Tote Felder (Delete-Kandidaten)",
             sorted((n, i) for n, i in index.items() if i["kategorie"] == "tot"))
    _sektion("Ghost-Active (nicht deklariert, aber geschrieben)",
             sorted((n, i) for n, i in index.items()
                    if i["kategorie"] == "ghost" and i["schreiber"]))

    lines.extend([
        "## Verweise",
        "",
        "- `tools/state_inventory.py` — Kategorien (Basis)",
        "- `tools/state_flow.py` — dieses Tool (Contract + Risiko)",
        "- `werkstatt/state_contracts.py` — CONTRACTS, TRANSITIONS",
        "- `docs/STATE-INVENTUR.md` — Detail-Inventur pro Kategorie",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _json(index: dict[str, dict]) -> None:
    print(json.dumps(index, indent=2, sort_keys=True))


def main() -> int:
    p = argparse.ArgumentParser(
        description="State-Flow-Diagnose (read-only)."
    )
    p.add_argument("--field", metavar="NAME",
                   help="Detail-Steckbrief fuer ein Feld")
    p.add_argument("--risk", choices=["HOCH", "MITTEL", "NIEDRIG"])
    p.add_argument("--orphans", action="store_true",
                   help="Nur tote Felder + write_only ohne Contract")
    p.add_argument("--check", action="store_true",
                   help="Exit 1 bei Drift gegen tools/state_flow_baseline.json")
    p.add_argument("--write-baseline", action="store_true",
                   help="JSON mit aktueller Baseline nach stdout")
    p.add_argument("--json", action="store_true")
    p.add_argument("--markdown", action="store_true")
    args = p.parse_args()

    if args.write_baseline:
        return _write_baseline()

    index = baue_flow_index()

    if args.check:
        return _check(index)

    if args.json:
        _json(index)
        return 0

    if args.markdown:
        out = ROOT / "docs" / "STATE-FLOW.md"
        _markdown(index, out)
        print(f"Report geschrieben: {out}")
        return 0

    if args.field:
        if args.field not in index:
            print(f"Feld nicht gefunden: {args.field}")
            return 1
        _steckbrief(args.field, index[args.field])
        return 0

    if args.risk:
        gefiltert = {n: i for n, i in index.items() if i["risiko"] == args.risk}
        if not gefiltert:
            print(f"Keine Felder mit Risiko {args.risk}")
            return 0
        for name in sorted(gefiltert):
            _steckbrief(name, gefiltert[name])
            print()
        return 0

    if args.orphans:
        orph = {
            n: i for n, i in index.items()
            if i["kategorie"] == "tot"
            or (i["kategorie"] == "write_only" and not i["contracts"])
        }
        print(f"{len(orph)} Waisen-Felder:")
        for name in sorted(orph):
            print(f"  {name:<32} {orph[name]['kategorie']}")
        return 0

    _tabelle(index)
    return 0


if __name__ == "__main__":
    sys.exit(main())
