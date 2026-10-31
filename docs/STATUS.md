# Status — Werkstatt

Format aus `DOC_CONVENTIONS.md` §5. Nur offene Punkte.
`—` in Feldern = noch nicht spezifiziert (Loop praezisiert bei Bearbeitung).
Letzte Aktualisierung: 2026-10-31.

## Offene Punkte

### OP-001: Block — Kurz
- **Status:** open
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Kurz
- **Tests:** —
- **Blockiert von:** —

### OP-002: K14 — `run_pipeline_loop` = 601 Zeilen. Refactoring in 7 `_phase_*`-Funktionen.
- **Status:** open
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** `run_pipeline_loop` = 601 Zeilen. Refactoring in 7 `_phase_*`-Funktionen.
- **Tests:** —
- **Blockiert von:** —

### OP-003: K17 — Architect prueft existierende Migrationsnummern nicht (Kollision 0017/0018 in security-ai). Fix: vor Migrations-Task `ls data/migrations/`.
- **Status:** open
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Architect prueft existierende Migrationsnummern nicht (Kollision 0017/0018 in security-ai). Fix: vor Migrations-Task `ls data/migrations/`.
- **Tests:** —
- **Blockiert von:** —

### OP-004: M-323b — `phase_end`-Checkpoint pro logischer Phase. Nach jeder Phase `_verify_patches(state, phase="phase_end")` + Reflection.
- **Status:** open
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** `phase_end`-Checkpoint pro logischer Phase. Nach jeder Phase `_verify_patches(state, phase="phase_end")` + Reflection.
- **Tests:** —
- **Blockiert von:** —

### OP-005: M-341 — Explorer ueberspringen, wenn `task_files` gesetzt.
- **Status:** open
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Explorer ueberspringen, wenn `task_files` gesetzt.
- **Tests:** —
- **Blockiert von:** —

### OP-006: M-344 — `PROGRESS.md` mit Phasen-Header (pro Phase, nicht pro Task).
- **Status:** open
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** `PROGRESS.md` mit Phasen-Header (pro Phase, nicht pro Task).
- **Tests:** —
- **Blockiert von:** —

### OP-007: M-345 — `pipeline.py` (11.118 Z., 172 Funktionen, 0 Klassen) ist **Loop-Code in Migration**, nicht toter Code. 146 Symbole werden noch von Tests referenziert (Stand 2026-10-30). Reihenfolge: (1) Symbole nach `werkstatt/*` verschieben, (2) `tests/test_pipeline.py` (11.377 Z., 182 Tests) aufteilen, (3) `tests/conftest.py` entkoppeln (3 Symbole), (4) `pipeline.py` + `tests/test_pipeline.py` + `tests/test_pipeline_integration.py` loeschen.
- **Status:** open
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** `pipeline.py` (11.118 Z., 172 Funktionen, 0 Klassen) ist **Loop-Code in Migration**, nicht toter Code. 146 Symbole werden noch von Tests referenziert (Stand 2026-10-30). Reihenfolge: (1) Symbole nach `werkstatt/*` verschieben, (2) `tests/test_pipeline.py` (11.377 Z., 182 Tests) aufteilen, (3) `tests/conftest.py` entkoppeln (3 Symbole), (4) `pipeline.py` + `tests/test_pipeline.py` + `tests/test_pipeline_integration.py` loeschen.
- **Tests:** —
- **Blockiert von:** —

### OP-008: M-346 — `pipeline._approval_und_human_gate` und `pipeline.load_project_config` in `werkstatt/` verschieben.
- **Status:** open
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** `pipeline._approval_und_human_gate` und `pipeline.load_project_config` in `werkstatt/` verschieben.
- **Tests:** —
- **Blockiert von:** —

### OP-009: M-347 — CLI-Einstiegspunkt fuer den Loop.
- **Status:** open
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** CLI-Einstiegspunkt fuer den Loop.
- **Tests:** —
- **Blockiert von:** —

### OP-010: Entkopplung — `werkstatt/verify.py` importiert `harness.*` und `core.changeapplier.*` (nur Introspektion). Ziel: null Fremd-Imports.
- **Status:** open
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** `werkstatt/verify.py` importiert `harness.*` und `core.changeapplier.*` (nur Introspektion). Ziel: null Fremd-Imports.
- **Tests:** —
- **Blockiert von:** —

### OP-011: 5-mypy — mypy 11 Fehler in 2 Dateien (Baseline 11).
- **Status:** open
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** mypy 11 Fehler in 2 Dateien (Baseline 11).
- **Tests:** —
- **Blockiert von:** —

### OP-012: 3c — Alte Tests, die mit dem alten Code fallen, entfernen.
- **Status:** open
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Alte Tests, die mit dem alten Code fallen, entfernen.
- **Tests:** —
- **Blockiert von:** —

### OP-013: M-162 — „Recovery nach Loop" messen oder schliessen.
- **Status:** open
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** „Recovery nach Loop" messen oder schliessen.
- **Tests:** —
- **Blockiert von:** —

### OP-014: M-388 — UI-Testing via Chrome DevTools.
- **Status:** open
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** UI-Testing via Chrome DevTools.
- **Tests:** —
- **Blockiert von:** —

### OP-015: M-389 — Doku-Pflege im Loop.
- **Status:** open
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Doku-Pflege im Loop.
- **Tests:** —
- **Blockiert von:** —

### OP-016: M-479 — Modell-Routing pro Rolle. `ask_llm(role=...)` mit Env-Vars. Architect = `deepseek-reasoner`, Builder/Reviewer = `deepseek-chat`.
- **Status:** open
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Modell-Routing pro Rolle. `ask_llm(role=...)` mit Env-Vars. Architect = `deepseek-reasoner`, Builder/Reviewer = `deepseek-chat`.
- **Tests:** —
- **Blockiert von:** —

### OP-017: M-480 — Kosten-Circuit-Breaker. `RunState.max_budget_usd`. `ask_llm` zaehlt Tokens, bei Ueberschreitung `BudgetExceededError`.
- **Status:** open
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Kosten-Circuit-Breaker. `RunState.max_budget_usd`. `ask_llm` zaehlt Tokens, bei Ueberschreitung `BudgetExceededError`.
- **Tests:** —
- **Blockiert von:** —

### OP-018: M-481 — Cache-aware Prompts. Stabiler Prefix (System, Architektur) vor variablem Suffix (Aufgabe). 98.6% Cache-Hit-Rate moeglich.
- **Status:** open
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Cache-aware Prompts. Stabiler Prefix (System, Architektur) vor variablem Suffix (Aufgabe). 98.6% Cache-Hit-Rate moeglich.
- **Tests:** —
- **Blockiert von:** —

### OP-019: M-482 — LiteLLM Adaptive Router (optional). Lernt, welches Modell fuer welchen Request-Typ am besten ist.
- **Status:** open
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** LiteLLM Adaptive Router (optional). Lernt, welches Modell fuer welchen Request-Typ am besten ist.
- **Tests:** —
- **Blockiert von:** —

### OP-020: M-478/M-489 — Test-Repair-Loop (TDFlow-Stil). 4 Sub-Agenten: Patch-Propose, Debug, Patch-Revise, Test-Generate. Tests FEST (kein Test-Hacking). Max 3 Runden, dann Eskalation.
- **Status:** open
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Test-Repair-Loop (TDFlow-Stil). 4 Sub-Agenten: Patch-Propose, Debug, Patch-Revise, Test-Generate. Tests FEST (kein Test-Hacking). Max 3 Runden, dann Eskalation.
- **Tests:** —
- **Blockiert von:** —

### OP-021: M-483 — Sandboxing (OS-Level). Filesystem-Isolation + Netzwerk-Isolation. Linux bubblewrap / macOS seatbelt. Reduziert Permission-Prompts um 84%.
- **Status:** open
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Sandboxing (OS-Level). Filesystem-Isolation + Netzwerk-Isolation. Linux bubblewrap / macOS seatbelt. Reduziert Permission-Prompts um 84%.
- **Tests:** —
- **Blockiert von:** —

### OP-022: M-484 — SWE-bench-Harness. 50-100 Tasks aus `princeton-nlp/SWE-bench_Verified`. Die einzige Zahl, die mit Aider/OpenHands/Devin vergleichbar ist.
- **Status:** open
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** SWE-bench-Harness. 50-100 Tasks aus `princeton-nlp/SWE-bench_Verified`. Die einzige Zahl, die mit Aider/OpenHands/Devin vergleichbar ist.
- **Tests:** —
- **Blockiert von:** —

### OP-023: M-485 — Event-Sourcing / Memory. Unveraenderliche Event-Logs statt YAML-Checkpoint. Loop-Spezifikation (Trigger, Goal, Verification, Stopping Rule, Memory).
- **Status:** open
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Event-Sourcing / Memory. Unveraenderliche Event-Logs statt YAML-Checkpoint. Loop-Spezifikation (Trigger, Goal, Verification, Stopping Rule, Memory).
- **Tests:** —
- **Blockiert von:** —

### OP-024: M-486 — Cache-aware Cost Model. 98.6% Input-Tokens aus Prefix-Cache. Flat-Pricing ueberschaetzt Kosten um 7.1x.
- **Status:** open
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Cache-aware Cost Model. 98.6% Input-Tokens aus Prefix-Cache. Flat-Pricing ueberschaetzt Kosten um 7.1x.
- **Tests:** —
- **Blockiert von:** —

### OP-025: M-488 — `phase_end` laeuft Vollsuite. `verify.json` + `loop.py` (M-476). Ohne das ist der Loop ein Builder.
- **Status:** open
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** `phase_end` laeuft Vollsuite. `verify.json` + `loop.py` (M-476). Ohne das ist der Loop ein Builder.
- **Tests:** —
- **Blockiert von:** —

### OP-026: R-CHECK-1 — Reviewer prueft Task-Zahlen nicht. Live-Beleg 20:42: Task verlangt `limit=10`, Code nutzt `limit=5`, Phase-Review approved. In Runde 1 des vorigen RERUN (20:38) hatte der Reviewer denselben Bug als HIGH markiert — Regression. Fix: `## KONSTANTEN-CHECK` in `REVIEWER_SYSTEM` (Zahlen aus Task muessen im Diff als Literal auftauchen, sonst HIGH-Bug).
- **Status:** open
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Reviewer prueft Task-Zahlen nicht. Live-Beleg 20:42: Task verlangt `limit=10`, Code nutzt `limit=5`, Phase-Review approved. In Runde 1 des vorigen RERUN (20:38) hatte der Reviewer denselben Bug als HIGH markiert — Regression. Fix: `## KONSTANTEN-CHECK` in `REVIEWER_SYSTEM` (Zahlen aus Task muessen im Diff als Literal auftauchen, sonst HIGH-Bug).
- **Tests:** —
- **Blockiert von:** —

### OP-027: M-490 — Doku-Staleness-Check (deterministisch, Documentledger). Nach jedem Task: Hash-Vergleich Code -> Doku. Kein LLM.
- **Status:** open
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Doku-Staleness-Check (deterministisch, Documentledger). Nach jedem Task: Hash-Vergleich Code -> Doku. Kein LLM.
- **Tests:** —
- **Blockiert von:** —

### OP-028: M-491 — Doku-Update-Agent (DocWriter). Bekommt Git-Diff + betroffene Sektionen + Quellcode. Schreibt nur `<!-- AUTO:... -->`-Bloecke neu (docwright).
- **Status:** open
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Doku-Update-Agent (DocWriter). Bekommt Git-Diff + betroffene Sektionen + Quellcode. Schreibt nur `<!-- AUTO:... -->`-Bloecke neu (docwright).
- **Tests:** —
- **Blockiert von:** —

### OP-029: M-492 — Doku-Critic (DocSync). Prueft DocWriter-Output gegen Code. Max 2 Runden.
- **Status:** open
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Doku-Critic (DocSync). Prueft DocWriter-Output gegen Code. Max 2 Runden.
- **Tests:** —
- **Blockiert von:** —

### OP-030: M-494 — Web-Backend (FastAPI). Startet den Loop als Subprozess, bietet Web-Sockets fuer Live-Logs und Chat. Zentraler State pro Projekt.
- **Status:** open
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Web-Backend (FastAPI). Startet den Loop als Subprozess, bietet Web-Sockets fuer Live-Logs und Chat. Zentraler State pro Projekt.
- **Tests:** —
- **Blockiert von:** —

### OP-031: M-495 — Terminal-Proxy. `loop_renderer`-Ausgaben (Spinner, `log_line`, `task_started`) live in den Browser streamen. xterm.js oder `<pre>` mit HTMX.
- **Status:** open
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Terminal-Proxy. `loop_renderer`-Ausgaben (Spinner, `log_line`, `task_started`) live in den Browser streamen. xterm.js oder `<pre>` mit HTMX.
- **Tests:** —
- **Blockiert von:** —

### OP-032: M-496 — Interactive Chat. Chat-Fenster rechts, Intent-Parsing (`plan`, `build`, `approve`, `chat_only`). Bestaetigung (j/n) per Chat oder CLI.
- **Status:** open
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Interactive Chat. Chat-Fenster rechts, Intent-Parsing (`plan`, `build`, `approve`, `chat_only`). Bestaetigung (j/n) per Chat oder CLI.
- **Tests:** —
- **Blockiert von:** —

### OP-033: M-497 — UI-Layout. Chrome-Tabs oben (Projekte oeffnen/schliessen), CLI links, Chat rechts, Reviewer unten. Synchronisation: Tab-Wechsel wechselt beide Fenster.
- **Status:** open
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** UI-Layout. Chrome-Tabs oben (Projekte oeffnen/schliessen), CLI links, Chat rechts, Reviewer unten. Synchronisation: Tab-Wechsel wechselt beide Fenster.
- **Tests:** —
- **Blockiert von:** —


### OP-035: Doku-Task-Datum wird halluziniert
- **Status:** open
- **Betroffene Dateien:** `werkstatt/prompts.py` (BUILDER_SYSTEM), `werkstatt/builder.py`
- **Akzeptanzkriterien:** Builder bekommt das Datum deterministisch (z.B. als Platzhalter `{{date}}` aus `datetime.now(UTC).date()`) statt es aus dem Kontext zu raten. Patches mit falschem Datum (`2026-11-02`, `2026-11-03` beobachtet) werden deterministisch korrigiert oder abgelehnt.
- **Tests:** `tests/test_builder.py::test_datum_kommt_aus_utc`
- **Blockiert von:** —

### OP-038: Commit-Message-Builder nutzt rohe Aufgabe
- **Status:** open
- **Betroffene Dateien:** `werkstatt/committer.py`
- **Akzeptanzkriterien:** Auto-Commit-Message folgt Schema `docs(<project>): <Kurztitel>` bzw. `feat(<project>): <Kurztitel>` aus dem abgeschlossenen OP/Task, NICHT die abgeschnittene Roh-Aufgabe (`chore(werkstatt): Such im Projekt nach unerledigten...`). Laenge <= 72 Zeichen, ggf. mit Ellipse.
- **Tests:** `tests/test_committer.py::test_commit_message_format`
- **Blockiert von:** —


### OP-039: security-ai Test-Suite 11 Min — messen und optimieren
- **Status:** open
- **Betroffene Dateien:** `tests/` in `/opt/security-ai`, ggf. `tests/conftest.py`
- **Akzeptanzkriterien:** `pytest -q` in security-ai laeuft in < 120s (statt ~660s). `pytest --durations=20` zeigt die 20 langsamsten Tests; mind. Top-10 auf < 5s reduziert. Kein `sleep() > 1s` in Tests. Keine echten Netzwerk-Calls ohne Mock.
- **Tests:** `.venv/bin/python -m pytest -q --durations=20 | tail -25`
- **Blockiert von:** —

Hinweis: Live-Test 4 (2026-10-31) zeigt 1334 Tests in ~660s (~500ms/Test).
Als `phase_end`-Stage (1x pro Loop) tragbar, aber teuer. Ursachen-Kandidaten:
DB-Reset zwischen Tests, Integration-Tests, Netzwerk ohne Mock.

### OP-040: Mehrfache _task_ende-Aufrufe pro Task (Root-Cause OP-036)
- **Status:** open
- **Betroffene Dateien:** `werkstatt/pipeline_phases.py`
- **Akzeptanzkriterien:** In `_phase_tasks_loop` gibt es pro Task maximal EINEN `_task_ende`-Aufruf. Alle Fehlerpfade enden mit `continue`. Mitigation (Duplikat-Check in `progress.append`, OP-036) bleibt als Sicherheitsnetz. Grep-Check: in `pipeline_phases.py` sind die `_task_ende`-Aufrufe nach `continue` gruppiert; kein Fall wo derselbe Task zweimal `_task_ende` bekommt.
- **Tests:** `tests/test_pipeline_phases.py::test_ein_task_ende_pro_task` (pytest-Test mit gemocktem Fehlerpfad).
- **Blockiert von:** —

### OP-041: Baseline-Revision (quality_gate rot)
- **Status:** open
- **Betroffene Dateien:** `tools/quality_gate.py`, `docs/HANDOFF-BASELINE.md`
- **Akzeptanzkriterien:** Neue Baseline (945 pytest, 0 ruff auf werkstatt/, 0 mypy auf werkstatt/ nach Cleanup — oder explizit als akzeptiert markiert). `quality_gate --json` gibt `exit 0` und `regression: false`.
- **Tests:** `python3 -m tools.quality_gate --json` -> exit 0.
- **Blockiert von:** OP-003 (ruff-Regelschaerfung), OP-004 (mypy)

## Delete-Zone

| Pfad | Warum entfernt | Ersetzt durch | Wiedereinfuehrung |
|---|---|---|---|
| — | — | — | — |
| OP-034 | erledigt 2026-10-31 (f37d5ae/ee95412/7a4ba7a) | pytest_regression am phase_end | – |
| OP-036 | erledigt 2026-10-31 (a965810) | Duplikat-Check in progress.append | – |
| OP-037 | kein Bug — Reviewer-Verhalten korrekt (audit-log 183709-29980) | keine Aenderung | – |

## Verweise

- [`ROADMAP.md`](ROADMAP.md) — Phasen-Uebersicht
- [`../PROGRESS.md`](../PROGRESS.md) — erledigte Punkte (append-only)
- [`MERKPOSTEN.md`](MERKPOSTEN.md) — M-Nummern
