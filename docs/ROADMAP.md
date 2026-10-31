# Roadmap — Werkstatt

Stand: 2026-10-31 (nach Doku-Migration, Scaffolder, Migrator, OP-NNN-Disziplin).
Uebersicht. Details in `STATUS.md` (Todo)
und `PROGRESS.md` (Erledigt).

## Symbole

| Symbol | Bedeutung |
|---|---|
| ✅ | abgeschlossen, verifiziert (Tests gruen, Commit, RERUN) |
| 🔧 | abgeschlossen, nachgebessert |
| ⚠️ | abgeschlossen, Symptom-Behandlung (nicht strukturell) |
| 🚫 | blockiert (Deadlock, Review offen) |
| 📋 | geplant, nicht begonnen |
| 🔴 | offen, Prioritaet P1 (akut, blockiert Phase) |
| 🟡 | offen, Prioritaet P2 (strukturell) |
| 🟢 | offen, Prioritaet P3 (Refactor) |

## Ist-Stand (2026-10-31)

**Baseline (gemessen 2026-10-31):** 945 / 248 / 16 / - / -.
- pytest: 945 passed, 5 skipped.
- ruff: 248 errors, 198 fixable (tests/ nie durchgerufft).
- mypy: 16 errors (werkstatt/, nicht auf .).
- AST + Katalog: Messung fehlt (AST-Tool entfernt, _KATALOG_SOLL fehlt).
- quality_gate: exit 1, regression true (Baseline aus 2026-10-25 ist
  veraltet, Re-Baseline als OP).

**Loop-Status:** liest `docs/STATUS.md` reproduzierbar (3 Live-Tests:
OP-005, OP-001, OP-002). OP-NNN-Disziplin greift: bei vager Aufgabe
waehlt der Scout genau einen Punkt.

**Bekannte Loop-Bugs (Live-Test 3):** OP-034..OP-038 in
`docs/STATUS.md`. Produktionscode-Aenderungen brauchen noch
pytest-Regression-Stage, hartes Reviewer-Signal, Datum aus UTC,
Reflection-Deduplizierung, Commit-Message-Builder.

## Phasen (aktuell)

### Phase 1-18: Strangler-Fig ✅

Loop aus `pipeline.py` herausgebaut.
Rollen: Explorer, Planner, Builder, Verify, Reviewer, Human-Gate.

### Phase 19: ChangeApplier ✅ (RERUN-80)

- `harness/versioning/applier.py` +237 Zeilen.
- `harness/versioning/__init__.py` +16 Zeilen.
- Fail-closed, Idempotenz, Backup/Restore.
- 6/6 Tasks approved, LOOP_RC=0.

### Phase 20: ADaPT ✅ (M-472..M-475)

- M-472: On-Demand-Zerlegung (`_split_task_on_demand`).
- M-473: `while`-Loop statt `for` (Sub-Tasks werden gebaut).
- M-474: ADaPT bei `reviewer_high_bug_fail_closed`.
- M-475: `get_next_task` liefert nur `pending`.

### Phase 21: Doku-Diataxis 🔧 (IN ARBEIT)

- `docs/index.md` — Diátaxis-Map (angelegt).
- `AGENTS.md` — Routing (60 Zeilen).
- `README.md` — Einstieg (66 Zeilen).
- `docs/ARCHITECTURE.md` — System-Map (93 Zeilen).
- `docs/ROADMAP.md` — diese Datei.
- `PROGRESS.md` — M-441..M-476 ergaenzen.
- `docs/STATUS.md` — pruefen.

### Phase 22: pipeline.py loeschen 🟡 (M-345, OFFEN)

- `pipeline.py` (11.639 Zeilen) loeschen.
- Voraussetzung: `werkstatt/agent.py` braucht keine Kopien mehr.

### Phase 23: Effizienz (M-479..M-482) 🔧

- M-479: Modell-Routing pro Rolle.
- M-480: Kosten-Circuit-Breaker.
- M-481: Cache-aware Prompts.
- M-482: LiteLLM Adaptive Router (optional).

### Phase 24: Robustheit (M-478, M-483..M-486) 🔴

- M-478: Test-Repair-Loop (TDFlow-Stil, 94.3% SWE-bench Verified).
- M-483: Sandboxing (OS-Level, 84% weniger Permission-Prompts).
- M-484: SWE-bench-Harness (die einzige vergleichbare Zahl).
- M-485: Event-Sourcing / Memory.
- M-486: Cache-aware Cost Model (7.1x Genauigkeit).

### Phase 22: Grundsystem schliessen (M-487..M-489) 🔴

- M-487: Human-Gate committet selbst.
- M-488: `phase_end` laeuft Vollsuite.
- M-489: Test-Repair-Loop (TDFlow-Stil, 94.3% SWE-bench Verified).

### Phase 22b: Doku-Sync (M-490..M-492) 🔴

- M-490: Doku-Staleness-Check (deterministisch, Documentledger).
- M-491: Doku-Update-Agent (DocWriter, AUTO-Sections).
- M-492: Doku-Critic (DocSync).

### Phase 23: Effizienz (M-479..M-482) 🔧

- M-479: Modell-Routing pro Rolle.
- M-480: Kosten-Circuit-Breaker.
- M-481: Cache-aware Prompts.
- M-482: LiteLLM Adaptive Router (optional).

### Phase 24: Robustheit (M-483..M-486) 🔴

- M-483: Sandboxing (OS-Level, 84% weniger Permission-Prompts).
- M-484: SWE-bench-Harness (die einzige vergleichbare Zahl).
- M-485: Event-Sourcing / Memory.
- M-486: Cache-aware Cost Model (7.1x Genauigkeit).

### Phase 25: Web-Interface (M-494..M-497) 📋

- M-494: Web-Backend (FastAPI, Web-Sockets, State pro Projekt).
- M-495: Terminal-Proxy (Live-Logs im Browser).
- M-496: Interactive Chat (Intent-Parsing, Bestaetigung per Chat).
- M-497: UI-Layout (Chrome-Tabs, CLI links, Chat rechts, Reviewer unten).

### Phase 26: Doku-Migration ✅ (2026-10-31)

- Beide Projekte auf DOC_CONVENTIONS.md §2/§3/§5/§6.
- 24 Werkstatt-Renames, 27 ADRs in security-ai.
- `PROGRESS.md` (root) als append-only-Historie.
- Delete-Zone in beiden STATUS.md.

### Phase 27: Loop liest Doku ✅ (2026-10-31)

- `load_docs` sortiert nach §6-Prioritaet.
- Scout bekommt `## PROJEKT-DOKU`-Sektion (max 4000 Z. je Doc).
- Planner erkennt vage Aufgaben -> STATUS.md primaer.
- Scout `## OP-NNN-DISZIPLIN`: bei vager Aufgabe GENAU EINEN OP.
- Live-Belege: OP-005, OP-001, OP-002.

### Phase 28: Doku-Werkzeuge ✅ (2026-10-31)

- `werkstatt/scaffold.py` + `werkstatt/templates/` (14 Vorlagen).
- `werkstatt/migrate.py` (§2/§3/§5/§6-Pruefung).
- Tests: `test_scaffold.py` (9), `test_migrate.py` (16),
  `test_scout_op_disziplin.py` (5), `test_planner_docs_reihenfolge.py`,
  `test_planner_vage_aufgabe.py`, `test_manifest_pflichtfelder.py`,
  `test_scout_liest_doku.py`.

### Phase 29: Loop-Reife Code-Patches 🟠 (OFFEN)

Bugs aus Live-Test 3 (OP-034..OP-038) in `docs/STATUS.md`:
pytest-Regression, Datum aus UTC, Reflection-Deduplizierung,
Reviewer-Signal, Commit-Message-Builder.

## Offene Bloecke (P1/P2)

| Block | Prio | Kurz |
|---|---|---|
| M-345 | 🟡 P2 | pipeline.py loeschen (11.639 Zeilen) |
| M-346 | 🟡 P2 | pipeline._approval_und_human_gate verschieben |
| M-347 | 🟢 P3 | CLI-Einstiegspunkt |
| M-341 | 🟢 P3 | Explorer ueberspringen bei task_files |
| M-344 | 🟢 P3 | PROGRESS.md mit Phasen-Header |
| M-323b | 🟡 P2 | phase_end-Checkpoint pro Phase |
| M-162 | 🟢 P3 | Recovery nach Loop messen |

## Loop-Bugs aus Live-Test 3 (OP-034..OP-038)

Akzeptanzkriterien und Test-Namen in `docs/STATUS.md`.

| OP | Titel | Prio |
|---|---|---|
| OP-034 | pytest-Stage deckt bestehende Tests nicht ab | 🔴 P1 |
| OP-037 | Reviewer-Signal invertiert | 🔴 P1 |
| OP-038 | Commit-Message-Builder nutzt rohe Aufgabe | 🟡 P2 |
| OP-035 | Doku-Task-Datum wird halluziniert | 🟡 P2 |
| OP-036 | Reflection dupliziert PROGRESS-Eintraege | 🟢 P3 |

## Verweise

- `PROGRESS.md` — erledigte Bloecke
- `STATUS.md` — offene Bloecke
- `MERKPOSTEN.md` — M-Nummern
- `ARCHITECTURE.md` — System-Map
