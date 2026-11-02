# Status — Werkstatt

Format aus `DOC_CONVENTIONS.md` §5. Nur offene Punkte.
`—` in Feldern = noch nicht spezifiziert (Loop praezisiert bei Bearbeitung).
Letzte Aktualisierung: 2026-11-01.

## Offene Punkte

### OP-039: security-ai Test-Suite 11 Min — messen und optimieren
- **Status:** open
- **Betroffene Dateien:** `tests/` in `/opt/security-ai`, ggf. `tests/conftest.py`
- **Akzeptanzkriterien:** `pytest -q` in security-ai laeuft in < 120s (statt ~660s). `pytest --durations=20` zeigt die 20 langsamsten Tests; mind. Top-10 auf < 5s reduziert. Kein `sleep() > 1s` in Tests. Keine echten Netzwerk-Calls ohne Mock.
- **Tests:** `.venv/bin/python -m pytest -q --durations=20 | tail -25`
- **Blockiert von:** —

Hinweis: Live-Test 4 (2026-10-31) zeigt 1334 Tests in ~660s (~500ms/Test).
Als `phase_end`-Stage (1x pro Loop) tragbar, aber teuer. Ursachen-Kandidaten:
DB-Reset zwischen Tests, Integration-Tests, Netzwerk ohne Mock.
### OP-041: Baseline-Revision (quality_gate rot)
- **Status:** open
- **Betroffene Dateien:** `tools/quality_gate.py`, `docs/HANDOFF-BASELINE.md`
- **Akzeptanzkriterien:** Neue Baseline (958 pytest, 0 ruff auf werkstatt/, 0 mypy auf werkstatt/ nach Cleanup — oder explizit als akzeptiert markiert). `quality_gate --json` gibt `exit 0` und `regression: false`.
- **Tests:** `python3 -m tools.quality_gate --json` -> exit 0.
- **Blockiert von:** security-ai OP-003 (ruff-Regelschaerfung), security-ai OP-004 (mypy)### OP-044: docs/CONVENTIONS.md entstauben (Selbstverweis + alte Namen)
- **Status:** open
- **Betroffene Dateien:** `docs/CONVENTIONS.md`
- **Akzeptanzkriterien:** (a) Selbstverweis `KONVENTION.md` -> `CONVENTIONS.md`. (b) Ordnerstruktur-Baum zeigt `CONVENTIONS.md`, `ARCHITECTURE.md`, `STATUS.md`, `PROGRESS.md` (nicht die alten Namen). (c) `pipeline.py`-Zeile entfernt oder durch `werkstatt/loop.py` + `werkstatt/pipeline_phases.py` ersetzt. (d) Referenztabelle (Zeilen ~67-71) auf aktuelle Namen aktualisiert oder entfernt.
- **Tests:** `grep -c "KONVENTION.md\|ARCHITEKTUR.md\|ERLEDIGT.md\|OFFENE-BLOECKE.md\|pipeline.py" docs/CONVENTIONS.md` = 0.
- **Blockiert von:** —

### OP-045: docs/WORKFLOW.md entstauben (pipeline.py + tote Links)
- **Status:** open
- **Betroffene Dateien:** `docs/WORKFLOW.md`
- **Akzeptanzkriterien:** (a) Alle `pipeline.py`-Referenzen entfernt oder auf `werkstatt/loop.py` + `werkstatt/pipeline_phases.py` umgebogen (10+ Stellen). (b) Tote Links `CONTEXT.md`, `CONTEXT_PROMPT.md`, `REVIEWER.md`, `REVIEWER_HANDOFF.md`, `INCONSISTENCIES_FOUND.md` entfernt oder korrigiert. (c) `pipeline.py --project ...`-CLI-Beispiele durch `python3 -m werkstatt.loop --project ...` ersetzt.
- **Tests:** `grep -c "pipeline.py\|CONTEXT.md\|REVIEWER.md" docs/WORKFLOW.md` = 0.
- **Blockiert von:** —

### OP-046: docs/PLANNER-KONZEPT.md + ROLLEN-AUDIT.md + MERKPOSTEN.md entstauben
- **Status:** open
- **Betroffene Dateien:** `docs/PLANNER-KONZEPT.md`, `docs/ROLLEN-AUDIT.md`, `docs/MERKPOSTEN.md`
- **Akzeptanzkriterien:** (a) `pipeline.py`-CLI-Beispiele in PLANNER-KONZEPT (5+ Stellen) auf `werkstatt.loop` umstellen. (b) `HARD_RULES_* in pipeline.py` -> `werkstatt/prompts.py` oder wo sie heute liegen. (c) ROLLEN-AUDIT: `ARCHITEKTUR.md` -> `ARCHITECTURE.md`. (d) MERKPOSTEN: tote Links `MESS-INFRASTRUKTUR.md`, `SESSION-BILANZ.md` (jetzt in `docs/archiv/`) korrigieren. (e) MERKPOSTEN: `OFFENE-BLOECKE.md`, `ERLEDIGT.md`-Referenzen durch `STATUS.md`, `PROGRESS.md` ersetzen.
- **Tests:** `grep -c "pipeline.py\|ARCHITEKTUR.md\|OFFENE-BLOECKE.md\|ERLEDIGT.md" docs/PLANNER-KONZEPT.md docs/ROLLEN-AUDIT.md docs/MERKPOSTEN.md` = 0 (pro Datei).
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

### OP-064: Architektur-Umbau — Completion-Gate mit Vetorecht (Sammel-OP)

- **Status:** open
- **Betroffene Dateien:** `werkstatt/state.py`, `werkstatt/phase_state.py`, `werkstatt/pipeline_phases.py`, `werkstatt/antipattern.py` (neu), `werkstatt/stuck.py` (neu), `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`
- **Akzeptanzkriterien:** Umbau des Loops von "drei konkurrierenden Wahrheiten" (Reflection-Return / Reviewer-Approval / Verify-Gate) auf "eine Hierarchie mit deterministischem Vetorecht". Sechs Bausteine, jeder ein eigener Sub-OP:
  - **OP-064a** Sticky-Veto (Completion-Gate): einmal `vetoed` -> nur Mensch kann es zuruecksetzen. Ersetzt OP-062i. **Live verifiziert 2026-11-01 19:22** (Testrunde #5, Commit `09fb4e7`): `_reflection_loop`=True + `_rev_ok`=True + `spec_widerspruch=True` -> `loop_task_spec_widerspruch_veto`, `status=human_review`, `verdict=vetoed`, **kein** `loop_task_ok`. Guard primaer in `pipeline_phases._phase_tasks_loop` vor `_task_ende(ok=True)`; defensiv in `task_runner._task_ende`.
  - **OP-064b** Deterministischer Antipattern-Scanner (`werkstatt/antipattern.py`): scannt `state.patches` auf `# type: ignore`, `noqa`, `eslint-disable`, `|| true` (Shell-Kontext), geloeschte Tests, geschwaechte Assertions. Kein LLM, kein subprocess, unter 100 ms. **Live verifiziert 2026-11-01 19:31** (Testrunde #6, Commit `a7a8e4d`): LLM baute unter Prompt-Anweisung tatsaechlich `# type: ignore[operator]`, Verify gruen (weil type:ignore mypy still macht), Reviewer approved — Guard feuerte vor `_task_ende(ok=True)`: `loop_task_antipattern_veto`, `status=human_review`, `failure=antipattern:type_ignore`, **kein** `loop_task_ok`. Guard sitzt im selben Konvergenz-Punkt wie OP-064a (`pipeline_phases._phase_tasks_loop`).
  - **OP-064c** StuckDetector (`werkstatt/stuck.py`): ein Modul analysiert `reflection_history` als Ganzes (gleicher Error-Kern, gleicher Patch-Hash, gleiche Bug-Signatur, Budget erschoepft). Ersetzt drei verstreute `_stagnation`-Pfade.
  - **OP-064d** Red-to-Green-Gate fuer "auftrag_bereits_erfuellt": ein Task gilt erst als verifiziert, wenn ein Test vorher rot war und jetzt gruen ist.
  - **OP-064e** Spec-Pre-Flight-Linter: vor dem Planner-Lauf OP-Text auf Widersprueche und nicht-existierende APIs pruefen.
  - **OP-064f** Structured Feature-List: `phase.yaml` bekommt pro Task `verdict: pending|verified|vetoed`. PROGRESS.md bleibt Menschen-Doku.
- **Tests:** Sub-OP-spezifisch.
- **Blockiert von:** —
- **Baustein-Status (2026-11-01 19:10):** 064a done. 064b-f offen.
- **Hinweis:** Design-Referenzen aus der Konkurrenz-Recherche 2026-11-01:
  - **Harn / Skyvern Completion Gate**: "A strict veto (a source write with a red or missing verifier) is never released by the veto budget."
  - **fakegreen**: deterministischer Diff-Scanner (kein LLM, unter 100 ms).
  - **OpenHands StuckDetector**: eigene Klasse analysiert die volle Agent-History.
  - **rulebridge / skillsaw**: ESLint fuer Agent-Instruktionen.
  - **GAN-style Red-to-Green**: "Ticks a task only when tests derived from your spec go from red to green."
  - **Anthropic Long-Running-Agents**: structured `feature_list.json` (JSON, nicht Markdown).
  - **Goodhart's Law auf Agent-Ebene**: "Mitigations rely on post-hoc review or prompt-based instructions, which are disciplinary rather than architectural and remain gameable."
  Kern-Erkenntnis: 4 Anlaeufe (OP-059c/d/e/062i) fuer dasselbe Problem. Das ist Symptom-Behandlung. Es braucht Architektur: deterministische Schichten, die nicht durch LLM-Approval ueberschreibbar sind.


## Erledigt (Auto-Log)

Nach Delete-Zone-Muster: erledigte OPs werden hier protokolliert.

- 2026-11-02 | OP-035 | Doku-Task-Datum wird halluziniert — deterministisch geloest (BUILDER_SYSTEM + {date}-Ersetzung + _korrigiere_doku_datum Sicherheitsnetz)
