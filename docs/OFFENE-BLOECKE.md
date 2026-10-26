# Offene Bloecke — Werkstatt

Stand: 2026-10-25 (nach M-476, RERUN-80).
Vorherige Liste: `OFFENE-BLOECKE-ARCHIV-2.md`.

Nur **offene** Bloecke. Erledigte stehen in `ERLEDIGT.md`.
Merkposten (M-Nummern) in `MERKPOSTEN.md`.

## Offene K-Fixes (Session 2026-10-26)

| Block | Aufwand | Kurz |
|---|---|---|
| K14 | gross | `run_pipeline_loop` = 601 Zeilen. Refactoring in 7 `_phase_*`-Funktionen. |
| K17 | mittel | Architect prueft existierende Migrationsnummern nicht (Kollision 0017/0018 in security-ai). Fix: vor Migrations-Task `ls data/migrations/`. |
| K19 | mittel | Builder setzt Task-Anforderungen nur teilweise um (Builder sinngemaess, Reviewer woertlich). Fix-Kandidaten: Builder-Prompt-Praezision / Checkliste. |

**K18 ist abgedeckt durch M-345/M-346** (Pipeline-Abbau, siehe unten).

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

## Grundsystem schliessen (M-487..M-489)

| Block | Aufwand | Kurz |
|---|---|---|
| M-487 | klein | Human-Gate committet selbst. `_human_gate` ruft `git commit` auf. Ohne das ist der Loop ein Vorschlagsgenerator. |
| M-488 | klein | `phase_end` laeuft Vollsuite. `verify.json` + `loop.py` (M-476). Ohne das ist der Loop ein Builder. |
| M-489 | gross | Test-Repair-Loop (TDFlow-Stil). 4 Sub-Agenten: Patch-Propose, Debug, Patch-Revise, Test-Generate. Tests FEST. Max 3 Runden. |

## Doku-Sync (M-490..M-492)

| Block | Aufwand | Kurz |
|---|---|---|
| M-490 | klein | Doku-Staleness-Check (deterministisch, Documentledger). Nach jedem Task: Hash-Vergleich Code -> Doku. Kein LLM. |
| M-491 | mittel | Doku-Update-Agent (DocWriter). Bekommt Git-Diff + betroffene Sektionen + Quellcode. Schreibt nur `<!-- AUTO:... -->`-Bloecke neu (docwright). |
| M-492 | klein | Doku-Critic (DocSync). Prueft DocWriter-Output gegen Code. Max 2 Runden. |

## Effizienz (M-479..M-482)

| Block | Aufwand | Kurz |
|---|---|---|
| M-479 | klein | Modell-Routing pro Rolle. `ask_llm(role=...)` mit Env-Vars. Architect = `deepseek-reasoner`, Builder/Reviewer = `deepseek-chat`. |
| M-480 | klein | Kosten-Circuit-Breaker. `RunState.max_budget_usd`. `ask_llm` zaehlt Tokens, bei Ueberschreitung `BudgetExceededError`. |
| M-481 | mittel | Cache-aware Prompts. Stabiler Prefix (System, Architektur) vor variablem Suffix (Aufgabe). 98.6% Cache-Hit-Rate moeglich. |
| M-482 | mittel | LiteLLM Adaptive Router (optional). Lernt, welches Modell fuer welchen Request-Typ am besten ist. |

## Robustheit (M-483..M-486)

| Block | Aufwand | Kurz |
|---|---|---|
| M-483 | mittel | Sandboxing (OS-Level). Filesystem-Isolation + Netzwerk-Isolation. Linux bubblewrap / macOS seatbelt. Reduziert Permission-Prompts um 84%. |
| M-484 | mittel | SWE-bench-Harness. 50-100 Tasks aus `princeton-nlp/SWE-bench_Verified`. Die einzige Zahl, die mit Aider/OpenHands/Devin vergleichbar ist. |
| M-485 | mittel | Event-Sourcing / Memory. Unveraenderliche Event-Logs statt YAML-Checkpoint. Loop-Spezifikation (Trigger, Goal, Verification, Stopping Rule, Memory). |
| M-486 | klein | Cache-aware Cost Model. 98.6% Input-Tokens aus Prefix-Cache. Flat-Pricing ueberschaetzt Kosten um 7.1x. |

## Web-Interface (M-494..M-497)

Das UI ist eine "IDE fuer Agenten": Chrome-Tabs oben (Projekte), CLI links (Live-Loop), Chat rechts (LLM-Interaktion), Reviewer unten (Diff/Audit).

| Block | Aufwand | Kurz |
|---|---|---|
| M-494 | mittel | Web-Backend (FastAPI). Startet den Loop als Subprozess, bietet Web-Sockets fuer Live-Logs und Chat. Zentraler State pro Projekt. |
| M-495 | klein | Terminal-Proxy. `loop_renderer`-Ausgaben (Spinner, `log_line`, `task_started`) live in den Browser streamen. xterm.js oder `<pre>` mit HTMX. |
| M-496 | mittel | Interactive Chat. Chat-Fenster rechts, Intent-Parsing (`plan`, `build`, `approve`, `chat_only`). Bestaetigung (j/n) per Chat oder CLI. |
| M-497 | mittel | UI-Layout. Chrome-Tabs oben (Projekte oeffnen/schliessen), CLI links, Chat rechts, Reviewer unten. Synchronisation: Tab-Wechsel wechselt beide Fenster. |

## Verweise

- `ROADMAP.md` — Phasen-Uebersicht.
- `ERLEDIGT.md` — erledigte Bloecke.
- `MERKPOSTEN.md` — M-Nummern.
