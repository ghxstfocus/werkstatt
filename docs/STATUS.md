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
### OP-063: Loop-PROGRESS-Einträge leer + Commit-Message abgeschnitten

- **Status:** open
- **Betroffene Dateien:** `werkstatt/task_runner.py`, `werkstatt/committer.py`, `werkstatt/progress.py`, `tests/test_progress_loop_quality.py`
- **Akzeptanzkriterien:** Drei zusammenhaengende Doku-Qualitaets-Defekte im Loop-Lauf.
  1. **Task-Ende-PROGRESS.append unterdruecken, wenn OP-NNN bekannt.**
     `_task_ende` (task_runner.py:83 ok, :112 fail) schreibt pro Task einen
     PROGRESS.md-Eintrag mit nur `name` + `status`. Bei einem 4-Task-Lauf
     ergibt das 4 leere Bloecke ohne OP-Bezug, ohne Commit, ohne Info.
     Wenn `state.aufgabe` ein `OP-NNN` enthaelt, soll `_task_ende` den
     PROGRESS.append unterlassen — der OP-Eintrag in `_committe_zielprojekt`
     ist die einzige Doku-Quelle (HARD-RULE 12: ein Fakt = eine Quelle).
     Wenn kein OP-NNN: Verhalten bleibt (Task-Eintrag als Fallback).
  2. **`_progress_op_done` auch bei Delete-Zone-only-OP.**
     `_status_md_op_entfernen` (committer.py) schlaegt fehl (`rm_ok=False`),
     wenn OP-NNN nicht mehr als `### OP-NNN:`-Block in STATUS.md steht,
     sondern nur in der Delete-Zone-Tabelle. Live-Beleg OP-002b3 17:25:
     STATUS.md hatte nur Delete-Zone-Zeile, `_rm_ok=False`, deshalb
     `_progress_op_done` nicht aufgerufen -> kein OP-Eintrag, stattdessen
     4 leere Task-Eintraege. Fix: `_committe_zielprojekt` prueft zusaetzlich,
     ob `op_nnn` schon in der Delete-Zone steht — dann ist der OP schon
     dokumentiert, aber ein sauberer `_progress_op_done`-Eintrag mit SHA
     fehlt noch und soll trotzdem geschrieben werden (mit Hinweis
     `already_in_delete_zone`).
  3. **Commit-Message-Subject bei langem OP-Text.**
     `_msg_kurz = _aufgabe_line[:60]` (committer.py:377) schneidet mitten
     im Wort. Live-Beleg 09cb89d: `fix(security-ai): OP-002b3: In
     core/inventory/repository.py die Metho...` — die Hälfte des Satzes,
     abgeschnitten. Fix: wenn `op_nnn` bekannt ist, Subject-Format
     `"<OP-NNN>: <Subject-Kurzform>"` mit Subject aus OP-Titel (STATUS.md)
     oder einem generischen "<OP-NNN>: Loop-Change". Kein Abschneiden
     mitten im Wort (Whitespace-Grenze).
- **Tests:** `tests/test_progress_loop_quality.py` (4 Faelle:
  * Task-Ende append suppressed wenn OP-NNN in Aufgabe;
  * Task-Ende append bleibt ohne OP-NNN;
  * `_committe_zielprojekt` schreibt `_progress_op_done`-Eintrag auch
    bei Delete-Zone-only (rm_ok=False, but in_delete_zone=True);
  * Commit-Message mit OP-NNN und sauberem Subject ohne Wortabschnitt).
- **Blockiert von:** —
- **Hinweis:** Live-Belege:
  * OP-002b3-Loop 17:25: PROGRESS.md bekam 4 leere Task-Eintraege
    (`## 2026-11-01T17:24:03 -- update_last_ip_if_changed commit-Parameter`,
    `- **Status:** done` — fertig, kein OP-NNN, kein SHA, keine Info).
    Der manuelle Doku-Commit 722bc77 hat sie durch einen sauberen
    OP-Eintrag ersetzt — der Loop selbst produziert diesen Muell aber
    bei jedem Lauf mit OP, der schon in der Delete-Zone steht.
  * Commit 09cb89d: Subject mitten im Wort abgeschnitten
    (`...die Metho...`). Der Loop-Text ist ein 3-Satz-Auftrag, kein
    Commit-Subject.
  Der Code selbst funktioniert — OP-002b3 4/4 Tasks, rc=0. Es geht
  ausschliesslich um Doku-Qualitaet. Nach OP-063 ist PROGRESS.md
  fuer den Menschen lesbar, ohne dass jede Loop-Doku manuell
  nachpoliert werden muss.

### OP-060b: human_review-Status + Duplikat-Anker-Regeneration (Design-OP)
- **Status:** open
- **Betroffene Dateien:** `werkstatt/phase_state.py`, `werkstatt/task_runner.py`, `werkstatt/gates.py`, `werkstatt/pipeline_phases.py`, `werkstatt/reflection.py`, `tests/test_human_review_status.py`
- **Akzeptanzkriterien:**
  1. `PhaseState.mark_human_review(task_id, grund)` setzt `status="human_review"`. Neuer Status neben `done`/`failed`/`split`/`pending`/`running`.
  2. `_task_ende` akzeptiert `human_review=True`: ruft `mark_human_review`, schreibt PROGRESS-Eintrag `Status: human_review`, ist idempotent (zweiter Aufruf mit gleichem task_id no-op via bestehendem Guard, erweitert um human_review).
  3. `_propagate_failed_to_parents` zaehlt `human_review`-Kinder NICHT als failed — Parent bleibt `split`, bis der Mensch entschieden hat.
  4. `_phase_finalize`: zaehlt `human_review` separat, rc=2 wenn nur human_review offen (nicht rc=1 wie bei failed).
  5. `_phase_tasks_loop`: bei 2 Reflexions-Runden `patch_nicht_angewendet` mit gleichen Reviewer-Bugs -> `_task_ende(..., human_review=True, grund="reflection_patch_unwirksam")` statt failed.
  6. Duplikat-Anker (Diagnose `mehrdeutig`): bei Human-Gate-Review-Hinweis Text "old_string kommt N-mal vor, Patch auf eindeutigeren Anker regenerieren". Optional LLM-Regeneration in einer Folg-OP.
  7. Am Human-Gate: Task-Zeile mit `[~]`-Prefix + Grund, sichtbar vom bestehenden Diff-Layout getrennt.
- **Tests:** `tests/test_human_review_status.py` (5 Faelle: mark_human_review setzt Status + Grund; _task_ende idempotent mit human_review; _propagate_failed ignoriert human_review-Kinder; _phase_finalize rc=2; Aufruf aus Reflexion bei 2x patch_nicht_angewendet).
- **Blockiert von:** —
- **Hinweis:** OP-060a (Commit ce5939f) liefert nur die Diagnose-Grundlage (`loop_reflection_patch_unwirksam` mit diagnosen-Liste, u.a. `grund=mehrdeutig` + `vorkommen>1`). human_review ist ein neuer Task-Status und braucht Design-Entscheid (Kollision mit Idempotenz-Guard, Human-Gate-Zaehlung, rc-Berechnung, Parent-Propagation). Aus OP-060 herausgesplittet, weil Code-Umfang deutlich groesser ist als OP-060a.
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

## Verweise

- [`ROADMAP.md`](ROADMAP.md) — Phasen-Uebersicht
- [`../PROGRESS.md`](../PROGRESS.md) — erledigte Punkte (append-only)
- [`MERKPOSTEN.md`](MERKPOSTEN.md) — M-Nummern
