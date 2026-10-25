# Offene Bloecke — Werkstatt

Stand: 2026-10-25 (nach M-476, RERUN-80).
Vorherige Liste: `OFFENE-BLOECKE-ARCHIV-2.md`.

Nur **offene** Bloecke. Erledigte stehen in `ERLEDIGT.md`.
Merkposten (M-Nummern) in `MERKPOSTEN.md`.

## Loop-Haertung

| Block | Aufwand | Kurz |
|---|---|---|
| M-323b | mittel | `phase_end`-Checkpoint pro logischer Phase. Nach jeder Phase `_verify_patches(state, phase="phase_end")` + Reflection. |
| M-341 | klein | Explorer ueberspringen, wenn `task_files` gesetzt. |
| M-344 | klein | `PROGRESS.md` mit Phasen-Header (pro Phase, nicht pro Task). |

## Pipeline-Abbau

| Block | Aufwand | Kurz |
|---|---|---|
| M-345 | mittel | `pipeline.py` (11.639 Z.) loeschen. Erst wenn `werkstatt/agent.py` keine Kopien mehr braucht. |
| M-346 | klein | `pipeline._approval_und_human_gate` und `pipeline.load_project_config` in `werkstatt/` verschieben. |

## CLI

| Block | Aufwand | Kurz |
|---|---|---|
| M-347 | klein | CLI-Einstiegspunkt fuer den Loop. |

## Werkstatt-Entkopplung

| Block | Aufwand | Kurz |
|---|---|---|
| Entkopplung | mittel | `werkstatt/verify.py` importiert `harness.*` und `core.changeapplier.*` (nur Introspektion). Ziel: null Fremd-Imports. |

## Baseline

| Block | Aufwand | Kurz |
|---|---|---|
| 5-mypy | klein | mypy 11 Fehler in 2 Dateien (Baseline 11). |

## Phase 3c — NEUBAU-Abloesung

| Block | Aufwand | Kurz |
|---|---|---|
| 3c | mittel | Alte Tests, die mit dem alten Code fallen, entfernen. |

## Merkposten

| Block | Aufwand | Kurz |
|---|---|---|
| M-162 | klein | „Recovery nach Loop" messen oder schliessen. |
| M-388 | klein | UI-Testing via Chrome DevTools. |
| M-389 | klein | Doku-Pflege im Loop. |

## Effizienz (M-479..M-482)

| Block | Aufwand | Kurz |
|---|---|---|
| M-479 | klein | Modell-Routing pro Rolle. `ask_llm(role=...)` mit Env-Vars. Architect = `deepseek-reasoner`, Builder/Reviewer = `deepseek-chat`. |
| M-480 | klein | Kosten-Circuit-Breaker. `RunState.max_budget_usd`. `ask_llm` zaehlt Tokens, bei Ueberschreitung `BudgetExceededError`. |
| M-481 | mittel | Cache-aware Prompts. Stabiler Prefix (System, Architektur) vor variablem Suffix (Aufgabe). 98.6% Cache-Hit-Rate moeglich. |
| M-482 | mittel | LiteLLM Adaptive Router (optional). Lernt, welches Modell fuer welchen Request-Typ am besten ist. |

## Robustheit (M-478, M-483..M-486)

| Block | Aufwand | Kurz |
|---|---|---|
| M-478 | gross | Test-Repair-Loop (TDFlow-Stil). 4 Sub-Agenten: Patch-Propose, Debug, Patch-Revise, Test-Generate. Tests FEST (kein Test-Hacking). Max 3 Runden, dann Eskalation. |
| M-483 | mittel | Sandboxing (OS-Level). Filesystem-Isolation + Netzwerk-Isolation. Linux bubblewrap / macOS seatbelt. Reduziert Permission-Prompts um 84%. |
| M-484 | mittel | SWE-bench-Harness. 50-100 Tasks aus `princeton-nlp/SWE-bench_Verified`. Die einzige Zahl, die mit Aider/OpenHands/Devin vergleichbar ist. |
| M-485 | mittel | Event-Sourcing / Memory. Unveraenderliche Event-Logs statt YAML-Checkpoint. Loop-Spezifikation (Trigger, Goal, Verification, Stopping Rule, Memory). |
| M-486 | klein | Cache-aware Cost Model. 98.6% Input-Tokens aus Prefix-Cache. Flat-Pricing ueberschaetzt Kosten um 7.1x. |

## Verweise

- `ROADMAP.md` — Phasen-Uebersicht.
- `ERLEDIGT.md` — erledigte Bloecke.
- `MERKPOSTEN.md` — M-Nummern.
