# Status — Werkstatt

Format aus `DOC_CONVENTIONS.md` §5. Nur offene Punkte.
`—` in Feldern = noch nicht spezifiziert (Loop praezisiert bei Bearbeitung).
Letzte Aktualisierung: 2026-11-02.

Loop-faehige OPs sind alle, die NICHT `- **Typ:** roadmap-phase`
tragen. Roadmap-Phasen sind grobe Etappen aus der Vor-Session
(M-Nummern) und gehoeren nicht in die Loop-Queue.

## Offene Punkte


### OP-004: M-323b — `phase_end`-Checkpoint pro logischer Phase. Nach jeder Phase `_verify_patches(state, phase="phase_end")` + Reflection.
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** `phase_end`-Checkpoint pro logischer Phase. Nach jeder Phase `_verify_patches(state, phase="phase_end")` + Reflection.
- **Tests:** —
- **Blockiert von:** —

### OP-005: M-341 — Explorer ueberspringen, wenn `task_files` gesetzt.
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Explorer ueberspringen, wenn `task_files` gesetzt.
- **Tests:** —
- **Blockiert von:** —

### OP-006: M-344 — `PROGRESS.md` mit Phasen-Header (pro Phase, nicht pro Task).
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** `PROGRESS.md` mit Phasen-Header (pro Phase, nicht pro Task).
- **Tests:** —
- **Blockiert von:** —

### OP-008: M-346 — `pipeline._approval_und_human_gate` und `pipeline.load_project_config` in `werkstatt/` verschieben.
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** `pipeline._approval_und_human_gate` und `pipeline.load_project_config` in `werkstatt/` verschieben.
- **Tests:** —
- **Blockiert von:** —

### OP-009: M-347 — CLI-Einstiegspunkt fuer den Loop.
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** CLI-Einstiegspunkt fuer den Loop.
- **Tests:** —
- **Blockiert von:** —

### OP-010: Entkopplung — `werkstatt/verify.py` importiert `harness.*` und `core.changeapplier.*` (nur Introspektion). Ziel: null Fremd-Imports.
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** `werkstatt/verify.py` importiert `harness.*` und `core.changeapplier.*` (nur Introspektion). Ziel: null Fremd-Imports.
- **Tests:** —
- **Blockiert von:** —

### OP-011: mypy-Restfehler abbauen (Baseline 27, 2026-11-03)
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** `werkstatt/*.py` (9 Dateien)
- **Akzeptanzkriterien:** mypy werkstatt/ = 0 Fehler. Baseline 2026-11-03:
  27 Fehler. Verteilung: 3x name-defined (planner, verify), 9x attr-defined
  (RunState-Attribute: tasks, akzeptanzkriterien, architect_prosa,
  reviewer_stagnation_false_positive, patches, …), 4x var-annotated,
  2x union-attr, 1x list-item, 1x index, 1x assignment, 1x arg-type,
  4x shell.py (`object`-Typen). Prioritaet: RunState-Attribut-Definitionen
  in werkstatt/state.py nachziehen, dann die Kosmetik.
- **Tests:** `mypy werkstatt/` = 0
- **Blockiert von:** —

### OP-012: 3c — Alte Tests, die mit dem alten Code fallen, entfernen.
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Alte Tests, die mit dem alten Code fallen, entfernen.
- **Tests:** —
- **Blockiert von:** —

### OP-013: M-162 — „Recovery nach Loop" messen oder schliessen.
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** „Recovery nach Loop" messen oder schliessen.
- **Tests:** —
- **Blockiert von:** —

### OP-014: M-388 — UI-Testing via Chrome DevTools.
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** UI-Testing via Chrome DevTools.
- **Tests:** —
- **Blockiert von:** —

### OP-015: M-389 — Doku-Pflege im Loop.
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Doku-Pflege im Loop.
- **Tests:** —
- **Blockiert von:** —

### OP-016: M-479 — Modell-Routing pro Rolle. `ask_llm(role=...)` mit Env-Vars. Architect = `deepseek-reasoner`, Builder/Reviewer = `deepseek-chat`.
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Modell-Routing pro Rolle. `ask_llm(role=...)` mit Env-Vars. Architect = `deepseek-reasoner`, Builder/Reviewer = `deepseek-chat`.
- **Tests:** —
- **Blockiert von:** —

### OP-017: M-480 — Kosten-Circuit-Breaker. `RunState.max_budget_usd`. `ask_llm` zaehlt Tokens, bei Ueberschreitung `BudgetExceededError`.
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Kosten-Circuit-Breaker. `RunState.max_budget_usd`. `ask_llm` zaehlt Tokens, bei Ueberschreitung `BudgetExceededError`.
- **Tests:** —
- **Blockiert von:** —

### OP-018: M-481 — Cache-aware Prompts. Stabiler Prefix (System, Architektur) vor variablem Suffix (Aufgabe). 98.6% Cache-Hit-Rate moeglich.
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Cache-aware Prompts. Stabiler Prefix (System, Architektur) vor variablem Suffix (Aufgabe). 98.6% Cache-Hit-Rate moeglich.
- **Tests:** —
- **Blockiert von:** —

### OP-019: M-482 — LiteLLM Adaptive Router (optional). Lernt, welches Modell fuer welchen Request-Typ am besten ist.
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** LiteLLM Adaptive Router (optional). Lernt, welches Modell fuer welchen Request-Typ am besten ist.
- **Tests:** —
- **Blockiert von:** —

### OP-020: M-478/M-489 — Test-Repair-Loop (TDFlow-Stil). 4 Sub-Agenten: Patch-Propose, Debug, Patch-Revise, Test-Generate. Tests FEST (kein Test-Hacking). Max 3 Runden, dann Eskalation.
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Test-Repair-Loop (TDFlow-Stil). 4 Sub-Agenten: Patch-Propose, Debug, Patch-Revise, Test-Generate. Tests FEST (kein Test-Hacking). Max 3 Runden, dann Eskalation.
- **Tests:** —
- **Blockiert von:** —

### OP-021: M-483 — Sandboxing (OS-Level). Filesystem-Isolation + Netzwerk-Isolation. Linux bubblewrap / macOS seatbelt. Reduziert Permission-Prompts um 84%.
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Sandboxing (OS-Level). Filesystem-Isolation + Netzwerk-Isolation. Linux bubblewrap / macOS seatbelt. Reduziert Permission-Prompts um 84%.
- **Tests:** —
- **Blockiert von:** —

### OP-022: M-484 — SWE-bench-Harness. 50-100 Tasks aus `princeton-nlp/SWE-bench_Verified`. Die einzige Zahl, die mit Aider/OpenHands/Devin vergleichbar ist.
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** SWE-bench-Harness. 50-100 Tasks aus `princeton-nlp/SWE-bench_Verified`. Die einzige Zahl, die mit Aider/OpenHands/Devin vergleichbar ist.
- **Tests:** —
- **Blockiert von:** —

### OP-023: M-485 — Event-Sourcing / Memory. Unveraenderliche Event-Logs statt YAML-Checkpoint. Loop-Spezifikation (Trigger, Goal, Verification, Stopping Rule, Memory).
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Event-Sourcing / Memory. Unveraenderliche Event-Logs statt YAML-Checkpoint. Loop-Spezifikation (Trigger, Goal, Verification, Stopping Rule, Memory).
- **Tests:** —
- **Blockiert von:** —

### OP-024: M-486 — Cache-aware Cost Model. 98.6% Input-Tokens aus Prefix-Cache. Flat-Pricing ueberschaetzt Kosten um 7.1x.
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Cache-aware Cost Model. 98.6% Input-Tokens aus Prefix-Cache. Flat-Pricing ueberschaetzt Kosten um 7.1x.
- **Tests:** —
- **Blockiert von:** —

### OP-025: M-488 — `phase_end` laeuft Vollsuite. `verify.json` + `loop.py` (M-476). Ohne das ist der Loop ein Builder.
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** `phase_end` laeuft Vollsuite. `verify.json` + `loop.py` (M-476). Ohne das ist der Loop ein Builder.
- **Tests:** —
- **Blockiert von:** —

### OP-027: M-490 — Doku-Staleness-Check (deterministisch, Documentledger). Nach jedem Task: Hash-Vergleich Code -> Doku. Kein LLM.
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Doku-Staleness-Check (deterministisch, Documentledger). Nach jedem Task: Hash-Vergleich Code -> Doku. Kein LLM.
- **Tests:** —
- **Blockiert von:** —

### OP-028: M-491 — Doku-Update-Agent (DocWriter). Bekommt Git-Diff + betroffene Sektionen + Quellcode. Schreibt nur `<!-- AUTO:... -->`-Bloecke neu (docwright).
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Doku-Update-Agent (DocWriter). Bekommt Git-Diff + betroffene Sektionen + Quellcode. Schreibt nur `<!-- AUTO:... -->`-Bloecke neu (docwright).
- **Tests:** —
- **Blockiert von:** —

### OP-029: M-492 — Doku-Critic (DocSync). Prueft DocWriter-Output gegen Code. Max 2 Runden.
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Doku-Critic (DocSync). Prueft DocWriter-Output gegen Code. Max 2 Runden.
- **Tests:** —
- **Blockiert von:** —

### OP-064: Architektur-Umbau — Completion-Gate mit Vetorecht (Sammel-OP)

- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** `werkstatt/state.py`, `werkstatt/phase_state.py`, `werkstatt/pipeline_phases.py`, `werkstatt/antipattern.py` (neu), `werkstatt/stuck.py` (nicht existent — pruefen) (neu), `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`
- **Akzeptanzkriterien:** Umbau des Loops von "drei konkurrierenden Wahrheiten" (Reflection-Return / Reviewer-Approval / Verify-Gate) auf "eine Hierarchie mit deterministischem Vetorecht". Sechs Bausteine, jeder ein eigener Sub-OP:
  - **OP-064a** Sticky-Veto (Completion-Gate): einmal `vetoed` -> nur Mensch kann es zuruecksetzen. Ersetzt OP-062i. **Live verifiziert 2026-11-01 19:22** (Testrunde #5, Commit `09fb4e7`): `_reflection_loop`=True + `_rev_ok`=True + `spec_widerspruch=True` -> `loop_task_spec_widerspruch_veto`, `status=human_review`, `verdict=vetoed`, **kein** `loop_task_ok`. Guard primaer in `pipeline_phases._phase_tasks_loop` vor `_task_ende(ok=True)`; defensiv in `task_runner._task_ende`.
  - **OP-064b** Deterministischer Antipattern-Scanner (`werkstatt/antipattern.py`): scannt `state.patches` auf `# type: ignore`, `noqa`, `eslint-disable`, `|| true` (Shell-Kontext), geloeschte Tests, geschwaechte Assertions. Kein LLM, kein subprocess, unter 100 ms. **Live verifiziert 2026-11-01 19:31** (Testrunde #6, Commit `a7a8e4d`): LLM baute unter Prompt-Anweisung tatsaechlich `# type: ignore[operator]`, Verify gruen (weil type:ignore mypy still macht), Reviewer approved — Guard feuerte vor `_task_ende(ok=True)`: `loop_task_antipattern_veto`, `status=human_review`, `failure=antipattern:type_ignore`, **kein** `loop_task_ok`. Guard sitzt im selben Konvergenz-Punkt wie OP-064a (`pipeline_phases._phase_tasks_loop`).
  - **OP-064c** StuckDetector (`werkstatt/stuck.py` (nicht existent — pruefen)): ein Modul analysiert `reflection_history` als Ganzes (gleicher Error-Kern, gleicher Patch-Hash, gleiche Bug-Signatur, Budget erschoepft). Ersetzt drei verstreute `_stagnation`-Pfade.
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


### OP-070: Scout-Redundanz messen vor Umbau
- **Status:** open
- **Betroffene Dateien:** `werkstatt/scout.py`, `werkstatt/planner.py` (`_run_scout`, `_baue_api_index`)
- **Akzeptanzkriterien:** Auswertung der letzten 10 Loop-Läufe: (a) Wie oft setzt `_run_scout` `bereits_erfuellt == True`? (b) Wie oft liefert `_pruefe_api_widerspruch` einen Befund, den der Architect ohne Scout-Auszug nicht gefunden hätte? (c) Wie oft weicht `api_auszug` von einem reinen Token-Match ab? Entscheidung: Scout-LLM behalten (Wahrscheinlichkeit hoch nach Rollen-Analyse) oder deterministisch ersetzen. Kein Umbau vor Messung.
- **Tests:** Keine — Mess-Aufgabe.
- **Blockiert von:** —

### Notiz 2026-11-02: `explorer_result` fehlt in aktuellen Logs

- **Beobachtung:** `audit("explorer_result", ...)` existiert in
  `werkstatt/explorer.py`. In Logs vom 23.-25.10. taucht er auf (10-58x),
  in Logs ab 26.10. **nicht mehr**. Stattdessen gibt es heute 15x
  `explorer_messung_findings`.
- **Verdacht:** Der Event wurde bei einer Explorer-Refactor-Welle
  umbenannt oder der Pfad, der ihn schreibt, wird nicht mehr erreicht.
- **Konsequenz:** `explorer_context` (den der Scout fuer Datei-Previews
  braucht) ist moeglicherweise leer -> Scout-Redundanz-Analyse (OP-070)
  hat keine Basis.
- **Naechster Schritt:** Pruefen ob `explorer_result` noch erreicht wird;
  falls nicht, Event wieder aktivieren oder durch `explorer_messung_findings`
  ersetzen (semantisch gleich?). Kein sofortiger Fix.

### OP-073: Werkzeug fuer Roadmap-to-OP Compiler

- **Status:** open
- **Beschreibung:** Baut das Werkzeug `werkstatt/roadmap_compiler.py`, das wie in Phase 31
  beschrieben, die naechste ROADMAP-Phase liest und automatisch in STATUS.md-OPs uebersetzt.
- **Betroffene Dateien:** `werkstatt/roadmap_compiler.py` (neu), `tests/test_roadmap_compiler.py` (neu)
- **Akzeptanzkriterien:** CLI-Tool, das den Architect aufruft, die Ausgabe validiert
  (OP-NNN, Akzeptanzkriterien vorhanden) und die OPs formatiert in STATUS.md einfuegt.
- **Tests:** Unit-Tests fuer die Validierungs-Logik und den Parser der Roadmap.
- **Blockiert von:** —




### OP-086: Doku-Drift als Verify-Gate (deterministisch)

- **Status:** open
- **Beschreibung:** `tools/doku_check.py` ist gebaut, aber noch nicht
  im Loop-Gate. Commits mit Subject `feat/fix/chore/...` und Code-
  Aenderung ohne Doku-Aenderung sollen als eigene verify-Stage laufen.
  Wenn Verdacht: Gate rot, Commit blockiert. Ausnahmen (docs(, test(,
  ci(, [skip-doku]) bereits implementiert.

  Ziel: Doku-Pflege ist strukturell erzwungen, nicht Erinnerung des
  Menschen. Begruendung: der Loop liest seine Queue aus docs/STATUS.md.
  Wenn dort stale OPs stehen (Beispiel 2026-11-03: Chat-Agent
  empfahl OP-084/085, obwohl beide bereits durch 82502f0..98a53d3
  erledigt waren), arbeitet der Loop gegen Phantom-Eintraege.
- **Betroffene Dateien:** `.werkstatt/verify.json` (neue Stage
  `doku_drift`), `tools/doku_check.py` (nutzen), `tests/test_doku_check.py`
  (neu), `AGENTS.md` (Pflicht-Befehl dokumentieren)
- **Akzeptanzkriterien:** (a) `verify.json` enthaelt Stage
  `doku_drift` mit Command `python3 tools/doku_check.py --strict
  --limit 5`. (b) Stage ist `hart=True`, blockiert Commit. (c) Tests
  `tests/test_doku_check.py` mit 4 Szenarien: Verdacht erkannt,
  Doku-Aenderung da, `[skip-doku]` greift, `docs(`-Scope greift.
  (d) `python3 tools/doku_check.py --strict` im Repo aktuell
  exit 0 (kein Verdacht in letzten 5 Commits) — sonst Commit
  sowieso blockiert.
- **Tests:** `pytest tests/test_doku_check.py -v`
- **Blockiert von:** —

### OP-047: Doku-Filter `doku_post_check_reduziert` killt Multi-File-Tasks

- **Status:** open
- **Betroffen:** `werkstatt/planner.py`, Funktion `_doku_post_check`
  (Zeile 1015–1100; Log-Tag: `planner_doku_post_check_reduziert` in Zeile 1097)
- **Problem:** Bei Doku-Ops über mehrere `.md`-Dateien (z.B. OP-046 mit
  `docs/PLANNER-KONZEPT.md`, `docs/ROLLEN-AUDIT.md`, `docs/MERKPOSTEN.md`)
  reduziert `_doku_post_check` den Plan auf die Tasks EINER Datei. Log-Beleg
  aus OP-046: `planner_doku_post_check_reduziert original_task_count=3
  md_task_count=3 behalten=["docs/PLANNER-KONZEPT.md"]` — die beiden Tasks
  für `ROLLEN-AUDIT.md` und `MERKPOSTEN.md` fallen weg, der Loop committet
  nur 1 Datei. **Wichtig:** die Merge-Logik in `_reduce_tasks` (Zeile ~734,
  `if same_file and same_act`) ist NICHT schuld, sie greift korrekt nur bei
  identischer Datei. Der Bug sitzt ausschließlich im `_doku_post_check`-Filter.
- **Fix:** `_doku_post_check` darf Tasks nur reduzieren, wenn `same_file=True`
  ist; unterschiedliche `.md`-Dateien müssen stehen bleiben. Wenn der Filter
  tatsächlich nur pro Datei eine Task-Auswahl treffen soll (z.B. um doppelte
  `docs_offen`-Tasks zu einer Datei zu kollabieren), dann NUR bei identischer
  Datei reduzieren, nie datei-übergreifend.
- **Test:** Datei `tests/test_planner.py` NEU anlegen (existiert nicht), Test
  `test_doku_post_check_multi_file` mit 3 Tasks auf 3 verschiedene `.md`-
  Dateien → erwartet: 3 Tasks bleiben stehen. Plus `test_doku_post_check_
  same_file_reduziert` mit 3 Tasks auf DIESELBE `.md`-Datei → erwartet:
  Reduktion auf 1 Task (Regressionsschutz für das eigentliche Ziel des Filters).
- **Akzeptanz:** Bei einem Doku-OP mit N verschiedenen Dateien liefert der
  Planner N Tasks, nicht 1. Verifikation: erneuter Loop-Lauf mit der OP-046-
  Aufgabenbeschreibung liefert `PLAN — 0 Phasen, 3 Tasks` in der PLAN-Anzeige.
- **Blockiert von:** —

## Erledigt (Auto-Log)

- 2026-11-02 | OP-076 | done | Chat-Fenster (f0e6d50)
- 2026-11-02 | OP-077 | done | Audit-Panel (92b3b69)
- 2026-11-02 | OP-078 | done | UI-Layout (0f916f9..e75bc7d)
- 2026-10-30 | OP-071 | `c1e8377`: revertiert
- 2026-11-02 | OP-003 | wontfix (security-ai-Drift)
- 2026-11-02 | OP-030 | wontfix (Duplikat zu OP-074)
- 2026-11-02 | OP-031 | wontfix (Duplikat zu OP-075)
- 2026-11-02 | OP-032 | wontfix (Duplikat zu OP-076)
- 2026-11-02 | OP-033 | wontfix (Duplikat zu OP-078)
- 2026-11-02 | OP-039 | wontfix (security-ai)
- 2026-11-02 | OP-041 | wontfix (security-ai)
- 2026-11-02 | OP-066 | done | Reviewer prueft Zwischenstand (bereits implementiert)
- 2026-11-02 | OP-065 | wontfix | Phase-2-Kette (Modell-Latenz, nicht Code)
- 2026-11-02 | OP-026 | wontfix | R-CHECK-1 Prompt-Block ist Skill
- 2026-11-02 | OP-067 | done | pytest_changed feuert in Reflection (69889b7)
- 2026-11-02 | OP-072 | done | UI-Phase 30 in OPs zerlegt (88ab237)
- 2026-11-02 | OP-074 | done | FastAPI-Backend (624fb5e + c82f537)
- 2026-11-02 | OP-075 | done | Terminal-Proxy (b8dce51)
- 2026-11-02 | OP-079 | done | review-work-Skill: Markdown-Hunk-Header (d023535)
- 2026-11-02 | OP-080 | done | review-work-Skill: Python-PATCHES (3d7fd1f)

## Delete-Zone

Nach Delete-Zone-Muster: erledigte OPs werden hier protokolliert.

- 2026-11-02 | OP-035 | Doku-Task-Datum wird halluziniert — deterministisch geloest (BUILDER_SYSTEM + {date}-Ersetzung + _korrigiere_doku_datum Sicherheitsnetz)
- 2026-11-02 | OP-068 | Heartbeat-Stage-Name (Builder/Reviewer) — Commit 2c099da
- 2026-11-02 | OP-069 | Delete-Zone-Sektion anlegen — Commit 6fa1d74 + Fix ebe8049
- 2026-11-03 | OP-045 | docs/WORKFLOW.md geloescht (nicht mehr gepflegt, nicht in DOC_CONVENTIONS §2 Pflicht)
