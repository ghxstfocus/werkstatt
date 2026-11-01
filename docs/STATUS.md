# Status — Werkstatt

Format aus `DOC_CONVENTIONS.md` §5. Nur offene Punkte.
`—` in Feldern = noch nicht spezifiziert (Loop praezisiert bei Bearbeitung).
Letzte Aktualisierung: 2026-11-01.

## Offene Punkte

### OP-035: Doku-Task-Datum wird halluziniert
- **Status:** open
- **Betroffene Dateien:** `werkstatt/prompts.py` (BUILDER_SYSTEM), `werkstatt/builder.py`
- **Akzeptanzkriterien:** Builder bekommt das Datum deterministisch (z.B. als Platzhalter `{{date}}` aus `datetime.now(UTC).date()`) statt es aus dem Kontext zu raten. Patches mit falschem Datum (`2026-11-02`, `2026-11-03` beobachtet) werden deterministisch korrigiert oder abgelehnt.
- **Tests:** `tests/test_builder.py::test_datum_kommt_aus_utc`
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
  - **OP-064a** Sticky-Veto (Completion-Gate): einmal `vetoed` -> nur Mensch kann es zuruecksetzen. Ersetzt OP-062i.
  - **OP-064b** Deterministischer Antipattern-Scanner (`werkstatt/antipattern.py`): scannt Diff auf `# type: ignore`, `noqa`, `eslint-disable`, `|| true`, geloeschte Tests, geschwaechte Assertions. Bei Treffer in aktiver harter Verify-Zone: Veto. Kein LLM.
  - **OP-064c** StuckDetector (`werkstatt/stuck.py`): ein Modul analysiert `reflection_history` als Ganzes (gleicher Error-Kern, gleicher Patch-Hash, gleiche Bug-Signatur, Budget erschoepft). Ersetzt drei verstreute `_stagnation`-Pfade.
  - **OP-064d** Red-to-Green-Gate fuer "auftrag_bereits_erfuellt": ein Task gilt erst als verifiziert, wenn ein Test vorher rot war und jetzt gruen ist.
  - **OP-064e** Spec-Pre-Flight-Linter: vor dem Planner-Lauf OP-Text auf Widersprueche und nicht-existierende APIs pruefen.
  - **OP-064f** Structured Feature-List: `phase.yaml` bekommt pro Task `verdict: pending|verified|vetoed`. PROGRESS.md bleibt Menschen-Doku.
- **Tests:** Sub-OP-spezifisch.
- **Blockiert von:** —
- **Hinweis:** Design-Referenzen aus der Konkurrenz-Recherche 2026-11-01:
  - **Harn / Skyvern Completion Gate**: "A strict veto (a source write with a red or missing verifier) is never released by the veto budget."
  - **fakegreen**: deterministischer Diff-Scanner (kein LLM, unter 100 ms).
  - **OpenHands StuckDetector**: eigene Klasse analysiert die volle Agent-History.
  - **rulebridge / skillsaw**: ESLint fuer Agent-Instruktionen.
  - **GAN-style Red-to-Green**: "Ticks a task only when tests derived from your spec go from red to green."
  - **Anthropic Long-Running-Agents**: structured `feature_list.json` (JSON, nicht Markdown).
  - **Goodhart's Law auf Agent-Ebene**: "Mitigations rely on post-hoc review or prompt-based instructions, which are disciplinary rather than architectural and remain gameable."
  Kern-Erkenntnis: 4 Anlaeufe (OP-059c/d/e/062i) fuer dasselbe Problem. Das ist Symptom-Behandlung. Es braucht Architektur: deterministische Schichten, die nicht durch LLM-Approval ueberschreibbar sind.

### OP-064a: Sticky-Veto — einmal vetoed, nur Mensch setzt zurueck

- **Status:** open
- **Betroffene Dateien:** `werkstatt/phase_state.py`, `werkstatt/pipeline_phases.py`, `werkstatt/task_runner.py`, `tests/test_sticky_veto.py`
- **Akzeptanzkriterien:**
  1. **`PhaseState.mark_vetoed(task_id, grund)`** setzt zusaetzlich zu `status` ein Feld `verdict: "vetoed"` (parallel zu `pending|verified`). Einmal `vetoed`, nur durch `mark_done`/`mark_human_review`+Mensch zuruecksetzbar.
  2. **`PhaseState.ist_vetoed(task_id)`** gibt `True`/`False`.
  3. **`_task_ende`-Veto-Guard:** wenn `ist_vetoed(task_id)` und `ok=True`: kein `mark_done`, stattdessen `mark_human_review(grund="veto_nicht_aufgehoben")`. Audit `loop_task_veto_respected`.
  4. **Success-Pfad** in `_phase_tasks_loop`: bei `_refl_ok=True` pruefen, ob `state.spec_widerspruch_erkannt` gesetzt ist. Wenn ja: `mark_vetoed(task_id, grund="spec_widerspruch_vermutet")` + `_task_ende(human_review=True)` statt `task_ok`.
  5. **`state.spec_widerspruch_erkannt`** wird nur noch in `_phase_tasks_loop` zurueckgesetzt (nach `mark_vetoed`), nicht mehr verstreut in reflection.py/pipeline_phases.py. Veto muss sticky sein.
- **Tests:** `tests/test_sticky_veto.py` (4 Faelle: mark_vetoed setzt verdict; ist_vetoed erkennt; _task_ende respektiert veto und macht human_review statt done; spec_widerspruch_erkannt im Erfolgs-Pfad -> vetoed+human_review).
- **Blockiert von:** —
- **Hinweis:** Live-Beleg Testrunde 3 (18:54 OP-004). Loop-Reflexion setzte `spec_widerspruch_erkannt=True`, `_reflection_loop` gab `return True`. `_phase_tasks_loop` sah `_refl_ok=True`, lief in den Erfolgs-Pfad, 2. Reviewer-Call approved (Reviewer-Inkonsistenz: Runde 1 HIGH, Runde 2 ok), `task_ok`. Am Human-Gate: `Tasks: 1/1 done`, aber Diff enthielt `# type: ignore[operator]`. Veto haette das verhindert. Ersetzt OP-062i.


## Delete-Zone

| Pfad | Warum entfernt | Ersetzt durch | Wiedereinfuehrung |
|---|---|---|---|
| OP-001 | Platzhalter ohne Inhalt | – | – |
| OP-002 (K14) | stale: run_pipeline_loop nutzt 4 Phasen (nicht 7), nicht 601 Z. | – | – |
| OP-007 (M-345) | pipeline.py geloescht (11.118 Z. -> 0) | erledigt 2026-10-31 | – |
| OP-040 | erledigt 2026-10-31 (ca9c010) | Idempotenz-Guard in _task_ende | – |
| OP-038 | erledigt 2026-11-01 | Conventional-Commits | – |
| OP-042 | erledigt 2026-11-01 | glossary.md | – |
| OP-043 | erledigt 2026-11-01 | HANDOFF-BASELINE | – |
| OP-044 | erledigt 2026-11-01 | CONVENTIONS.md | – |
| OP-047 | erledigt 2026-11-01 | tote Links | – |
| OP-053 | erledigt 2026-11-01 | git_author | – |
| OP-048 | erledigt 2026-11-01 (73f3156) | Doku-Selbstpflege Ebene 1 | – |
| OP-055 | erledigt 2026-11-01 (73f3156) | HEAD-Kennzahl (partial: Tests = Follow-up, blockiert OP-039) | – |
| OP-056 | erledigt 2026-11-01 (73f3156) | CHANGELOG-Append | – |
| OP-057 | erledigt 2026-11-01 (73f3156) | Architecture-Drift-Audit | – |
| OP-058 | erledigt 2026-11-01 (73f3156) | ADR-Mini-Phase (partial: Template statt LLM) | – |
| OP-034 | erledigt 2026-10-31 (f37d5ae/ee95412/7a4ba7a) | pytest_regression am phase_end | – |
| OP-036 | erledigt 2026-10-31 (a965810) | Duplikat-Check in progress.append | – |
| OP-037 | kein Bug — Reviewer-Verhalten korrekt (audit-log 183709-29980) | keine Aenderung | – |
| OP-059 | erledigt 2026-11-01 (05162e7) | reflection false_positive (partial: human_review-Zweig nicht gebaut, nur done bei verify gruen) | – |
| OP-060a | erledigt 2026-11-01 (ce5939f) | Patch-Diagnose bei Nicht-Anwendung (partial: human_review + Duplikat-Anker-Regeneration in OP-060b) | – |
| OP-061 | erledigt 2026-11-01 (05bb2b2) | builder_failed-Klarheit (A: pre-reviewer flag, B: prior-done gleiche Datei) | – |
| OP-062a | erledigt 2026-11-01 (HEAD) | redact=False fuer Builder + Reviewer (Code-Pruefung) | – |
| OP-062b | erledigt 2026-11-01 (HEAD) | Human-Gate zeigt Architect-Plan + Reviewer-Bugs + Reflexionen | – |
| OP-062c | erledigt 2026-11-01 (83a0407) | Human-Gate Bug-Sync + task_id + Hunk-Summary (partial: Verdrahtung in OP-062d) | – |
| OP-062d | erledigt 2026-11-01 (HEAD) | Hunk-Summary im Human-Gate verdrahtet | – |
| OP-063 | erledigt 2026-11-01 (HEAD) | Loop-PROGRESS/Commit-Qualitaet (3 Defekte) | – |
| OP-062e | erledigt 2026-11-01 (HEAD) | Human-Gate zeigt Nullfall (Erfuellt ohne Aenderung) | – |

## Verweise

- [`ROADMAP.md`](ROADMAP.md) — Phasen-Uebersicht
- [`../PROGRESS.md`](../PROGRESS.md) — erledigte Punkte (append-only)
- [`MERKPOSTEN.md`](MERKPOSTEN.md) — M-Nummern
