# State-Flow Report

Generiert von `tools/state_flow.py --markdown`. Nicht von Hand editieren.

## Zusammenfassung

- Felder gesamt: **86**
- Deklariert: **86**
- Ghost (nicht deklariert): **0**
- Tote Felder: **4**
- Multi-Writer: **23**
- Risiko HOCH: **19**, MITTEL: **13**, NIEDRIG: **54**

## Risiko HOCH

| Feld | Kategorie | Writer | Reader | Getattr | Contracts | Gruende |
|---|---|---|---|---|---|---|
| `aktuelle_task` | write_only | 2 | 0 | 4 | — | multi-writer(2) ohne Contract; getattr-only in 4 Datei(en) |
| `applied_count` | write_only | 2 | 0 | 4 | — | multi-writer(2) ohne Contract; getattr-only in 4 Datei(en) |
| `aufgabe` | aktiv | 2 | 1 | 7 | — | multi-writer(2) ohne Contract; getattr-only in 7 Datei(en) |
| `auftrag_bereits_erfuellt` | write_only | 4 | 0 | 5 | — | multi-writer(4) ohne Contract; getattr-only in 5 Datei(en) |
| `auftrag_bereits_erfuellt_bestaetigt` | write_only | 2 | 0 | 1 | — | multi-writer(2) ohne Contract |
| `auftrag_bereits_erfuellt_quelle` | write_only | 2 | 0 | 0 | — | multi-writer(2) ohne Contract |
| `last_reject_kind` | write_only | 2 | 0 | 1 | — | multi-writer(2) ohne Contract |
| `last_reject_reason` | write_only | 2 | 0 | 1 | — | multi-writer(2) ohne Contract |
| `last_verify_errors` | write_only | 3 | 0 | 6 | — | multi-writer(3) ohne Contract; getattr-only in 6 Datei(en) |
| `patches` | aktiv | 2 | 1 | 7 | — | multi-writer(2) ohne Contract; getattr-only in 7 Datei(en) |
| `phasen` | write_only | 2 | 0 | 2 | — | multi-writer(2) ohne Contract |
| `reviewer_bugs` | write_only | 3 | 0 | 6 | — | multi-writer(3) ohne Contract; getattr-only in 6 Datei(en) |
| `reviewer_bugs_history` | aktiv | 2 | 2 | 4 | — | multi-writer(2) ohne Contract; multi-reader(2) ohne Contract; getattr-only in 4  |
| `reviewer_deterministic_fail` | write_only | 2 | 0 | 1 | — | multi-writer(2) ohne Contract |
| `reviewer_stagnation_false_positive` | write_only | 2 | 0 | 1 | — | multi-writer(2) ohne Contract |
| `spec_widerspruch_erkannt` | write_only | 3 | 0 | 2 | — | multi-writer(3) ohne Contract |
| `split_failure_grund` | write_only | 2 | 0 | 1 | — | multi-writer(2) ohne Contract |
| `start_monotonic` | aktiv | 2 | 1 | 0 | — | multi-writer(2) ohne Contract |
| `tasks_ok_counter` | write_only | 2 | 0 | 2 | — | multi-writer(2) ohne Contract |

## Risiko MITTEL

| Feld | Kategorie | Writer | Reader | Getattr | Contracts | Gruende |
|---|---|---|---|---|---|---|
| `agent_docs` | tot | 0 | 0 | 0 | — | tot (weder Reader noch Writer) |
| `akzeptanzkriterien` | write_only | 3 | 0 | 4 | planner_output | multi-writer(3); getattr-only in 4 Datei(en) |
| `api_key` | getattr_only | 0 | 0 | 6 | — | getattr-only in 6 Datei(en) |
| `architect_prosa` | aktiv | 2 | 5 | 0 | architect_output | multi-writer(2) |
| `block_id` | tot | 0 | 0 | 0 | — | tot (weder Reader noch Writer) |
| `budget` | tot | 0 | 0 | 0 | — | tot (weder Reader noch Writer) |
| `docs` | read_only | 0 | 1 | 3 | — | getattr-only in 3 Datei(en) |
| `project_dir` | aktiv | 1 | 16 | 16 | — | multi-reader(16) ohne Contract; getattr-only in 16 Datei(en) |
| `project_name` | read_only | 0 | 15 | 11 | — | multi-reader(15) ohne Contract; getattr-only in 11 Datei(en) |
| `reflection_history` | aktiv | 1 | 1 | 3 | — | getattr-only in 3 Datei(en) |
| `start_ts` | tot | 0 | 0 | 0 | — | tot (weder Reader noch Writer) |
| `tasks` | aktiv | 4 | 1 | 11 | planner_output | multi-writer(4); getattr-only in 11 Datei(en) |
| `tests` | aktiv | 3 | 2 | 1 | planner_output | multi-writer(3) |

## Tote Felder (Delete-Kandidaten)

| Feld | Kategorie | Writer | Reader | Getattr | Contracts | Gruende |
|---|---|---|---|---|---|---|
| `agent_docs` | tot | 0 | 0 | 0 | — | tot (weder Reader noch Writer) |
| `block_id` | tot | 0 | 0 | 0 | — | tot (weder Reader noch Writer) |
| `budget` | tot | 0 | 0 | 0 | — | tot (weder Reader noch Writer) |
| `start_ts` | tot | 0 | 0 | 0 | — | tot (weder Reader noch Writer) |

## Ghost-Active (nicht deklariert, aber geschrieben)

(keine)

## Verweise

- `tools/state_inventory.py` — Kategorien (Basis)
- `tools/state_flow.py` — dieses Tool (Contract + Risiko)
- `werkstatt/state_contracts.py` — CONTRACTS, TRANSITIONS
- `docs/STATE-INVENTUR.md` — Detail-Inventur pro Kategorie
