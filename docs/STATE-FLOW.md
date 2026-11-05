# State-Flow Report

Generiert von `tools/state_flow.py --markdown`. Nicht von Hand editieren.

## Zusammenfassung

- Felder gesamt: **86**
- Deklariert: **63**
- Ghost (nicht deklariert): **23**
- Tote Felder: **4**
- Multi-Writer: **23**
- Risiko HOCH: **20**, MITTEL: **26**, NIEDRIG: **40**

## Risiko HOCH

| Feld | Kategorie | Writer | Reader | Getattr | Contracts | Gruende |
|---|---|---|---|---|---|---|
| `aktuelle_task` | ghost | 2 | 0 | 4 | — | ghost (nicht in RunState deklariert); multi-writer(2) ohne Contract; getattr-onl |
| `applied_count` | ghost | 2 | 0 | 4 | — | ghost (nicht in RunState deklariert); multi-writer(2) ohne Contract; getattr-onl |
| `aufgabe` | aktiv | 2 | 1 | 7 | — | multi-writer(2) ohne Contract; getattr-only in 7 Datei(en) |
| `auftrag_bereits_erfuellt` | ghost | 4 | 0 | 5 | — | ghost (nicht in RunState deklariert); multi-writer(4) ohne Contract; getattr-onl |
| `auftrag_bereits_erfuellt_bestaetigt` | write_only | 2 | 0 | 1 | — | multi-writer(2) ohne Contract |
| `auftrag_bereits_erfuellt_quelle` | write_only | 2 | 0 | 0 | — | multi-writer(2) ohne Contract |
| `last_planner_info` | ghost | 1 | 0 | 2 | — | ghost (nicht in RunState deklariert) |
| `last_reject_kind` | write_only | 2 | 0 | 1 | — | multi-writer(2) ohne Contract |
| `last_reject_reason` | write_only | 2 | 0 | 1 | — | multi-writer(2) ohne Contract |
| `last_verify_errors` | ghost | 3 | 0 | 6 | — | ghost (nicht in RunState deklariert); multi-writer(3) ohne Contract; getattr-onl |
| `patches` | aktiv | 2 | 1 | 7 | — | multi-writer(2) ohne Contract; getattr-only in 7 Datei(en) |
| `phasen` | write_only | 2 | 0 | 2 | — | multi-writer(2) ohne Contract |
| `reviewer_bugs` | write_only | 3 | 0 | 6 | — | multi-writer(3) ohne Contract; getattr-only in 6 Datei(en) |
| `reviewer_bugs_history` | aktiv | 2 | 2 | 4 | — | multi-writer(2) ohne Contract; multi-reader(2) ohne Contract; getattr-only in 4  |
| `reviewer_deterministic_fail` | ghost | 2 | 0 | 1 | — | ghost (nicht in RunState deklariert); multi-writer(2) ohne Contract |
| `reviewer_stagnation_false_positive` | ghost | 2 | 0 | 1 | — | ghost (nicht in RunState deklariert); multi-writer(2) ohne Contract |
| `spec_widerspruch_erkannt` | ghost | 3 | 0 | 2 | — | ghost (nicht in RunState deklariert); multi-writer(3) ohne Contract |
| `split_failure_grund` | ghost | 2 | 0 | 1 | — | ghost (nicht in RunState deklariert); multi-writer(2) ohne Contract |
| `start_monotonic` | aktiv | 2 | 1 | 0 | — | multi-writer(2) ohne Contract |
| `tasks_ok_counter` | ghost | 2 | 0 | 2 | — | ghost (nicht in RunState deklariert); multi-writer(2) ohne Contract |

## Risiko MITTEL

| Feld | Kategorie | Writer | Reader | Getattr | Contracts | Gruende |
|---|---|---|---|---|---|---|
| `_reflection_bug_sigs_vorher` | ghost | 1 | 0 | 1 | — | ghost (nicht in RunState deklariert) |
| `_reflection_diff_hash` | ghost | 1 | 0 | 0 | — | ghost (nicht in RunState deklariert) |
| `agent_docs` | tot | 0 | 0 | 0 | — | tot (weder Reader noch Writer) |
| `akzeptanzkriterien` | write_only | 3 | 0 | 4 | planner_output | multi-writer(3); getattr-only in 4 Datei(en) |
| `api_key` | getattr_only | 0 | 0 | 6 | — | getattr-only in 6 Datei(en) |
| `architect_prosa` | aktiv | 2 | 5 | 0 | architect_output | multi-writer(2) |
| `auto_approve` | ghost | 1 | 0 | 1 | — | ghost (nicht in RunState deklariert) |
| `baseline_gruen` | ghost | 0 | 0 | 1 | — | ghost (nicht in RunState deklariert) |
| `block_id` | tot | 0 | 0 | 0 | — | tot (weder Reader noch Writer) |
| `budget` | tot | 0 | 0 | 0 | — | tot (weder Reader noch Writer) |
| `docs` | read_only | 0 | 1 | 3 | — | getattr-only in 3 Datei(en) |
| `explorer_pytest_laufzeit_s` | ghost | 0 | 0 | 1 | — | ghost (nicht in RunState deklariert) |
| `explorer_ruff_befunde` | ghost | 0 | 0 | 1 | — | ghost (nicht in RunState deklariert) |
| `last_verify_hart_stages` | ghost | 1 | 0 | 1 | — | ghost (nicht in RunState deklariert) |
| `messungen_nach_apply` | ghost | 0 | 0 | 1 | — | ghost (nicht in RunState deklariert) |
| `phase_review_uebersprungen` | ghost | 1 | 0 | 1 | — | ghost (nicht in RunState deklariert) |
| `progress_written_at_commit` | ghost | 1 | 0 | 1 | — | ghost (nicht in RunState deklariert) |
| `project_dir` | aktiv | 1 | 16 | 16 | — | multi-reader(16) ohne Contract; getattr-only in 16 Datei(en) |
| `project_name` | read_only | 0 | 15 | 11 | — | multi-reader(15) ohne Contract; getattr-only in 11 Datei(en) |
| `reflection_erschoepft` | ghost | 1 | 0 | 1 | — | ghost (nicht in RunState deklariert) |
| `reflection_history` | aktiv | 1 | 1 | 3 | — | getattr-only in 3 Datei(en) |
| `reflection_phase` | ghost | 1 | 0 | 1 | — | ghost (nicht in RunState deklariert) |
| `scout_bereits_erfuellt` | ghost | 1 | 0 | 1 | — | ghost (nicht in RunState deklariert) |
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

| Feld | Kategorie | Writer | Reader | Getattr | Contracts | Gruende |
|---|---|---|---|---|---|---|
| `_reflection_bug_sigs_vorher` | ghost | 1 | 0 | 1 | — | ghost (nicht in RunState deklariert) |
| `_reflection_diff_hash` | ghost | 1 | 0 | 0 | — | ghost (nicht in RunState deklariert) |
| `aktuelle_task` | ghost | 2 | 0 | 4 | — | ghost (nicht in RunState deklariert); multi-writer(2) ohne Contract; getattr-onl |
| `applied_count` | ghost | 2 | 0 | 4 | — | ghost (nicht in RunState deklariert); multi-writer(2) ohne Contract; getattr-onl |
| `auftrag_bereits_erfuellt` | ghost | 4 | 0 | 5 | — | ghost (nicht in RunState deklariert); multi-writer(4) ohne Contract; getattr-onl |
| `auto_approve` | ghost | 1 | 0 | 1 | — | ghost (nicht in RunState deklariert) |
| `last_planner_info` | ghost | 1 | 0 | 2 | — | ghost (nicht in RunState deklariert) |
| `last_verify_errors` | ghost | 3 | 0 | 6 | — | ghost (nicht in RunState deklariert); multi-writer(3) ohne Contract; getattr-onl |
| `last_verify_hart_stages` | ghost | 1 | 0 | 1 | — | ghost (nicht in RunState deklariert) |
| `phase_review_uebersprungen` | ghost | 1 | 0 | 1 | — | ghost (nicht in RunState deklariert) |
| `progress_written_at_commit` | ghost | 1 | 0 | 1 | — | ghost (nicht in RunState deklariert) |
| `reflection_erschoepft` | ghost | 1 | 0 | 1 | — | ghost (nicht in RunState deklariert) |
| `reflection_phase` | ghost | 1 | 0 | 1 | — | ghost (nicht in RunState deklariert) |
| `reviewer_deterministic_fail` | ghost | 2 | 0 | 1 | — | ghost (nicht in RunState deklariert); multi-writer(2) ohne Contract |
| `reviewer_stagnation_false_positive` | ghost | 2 | 0 | 1 | — | ghost (nicht in RunState deklariert); multi-writer(2) ohne Contract |
| `scout_bereits_erfuellt` | ghost | 1 | 0 | 1 | — | ghost (nicht in RunState deklariert) |
| `spec_widerspruch_erkannt` | ghost | 3 | 0 | 2 | — | ghost (nicht in RunState deklariert); multi-writer(3) ohne Contract |
| `split_failure_grund` | ghost | 2 | 0 | 1 | — | ghost (nicht in RunState deklariert); multi-writer(2) ohne Contract |
| `tasks_ok_counter` | ghost | 2 | 0 | 2 | — | ghost (nicht in RunState deklariert); multi-writer(2) ohne Contract |

## Verweise

- `tools/state_inventory.py` — Kategorien (Basis)
- `tools/state_flow.py` — dieses Tool (Contract + Risiko)
- `werkstatt/state_contracts.py` — CONTRACTS, TRANSITIONS
- `docs/STATE-INVENTUR.md` — Detail-Inventur pro Kategorie
