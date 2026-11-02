# Roadmap — Werkstatt

Stand: 2026-11-02 (nach Skills-Welle, UI-Vision, OP-Bereinigung).
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

**Baseline (gemessen 2026-11-02):** 1145 / 309 / 22 / - / -.
- pytest: 1145 passed, 5 skipped.
- ruff: 309 errors (tests/ nie durchgerufft).
- mypy: 22 errors in 9 files (werkstatt/, nicht auf .).
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

### Phase 22: pipeline.py loeschen ✅ (erledigt 2026-10-31)

- `pipeline.py` (11.639 Zeilen) wurde entfernt (M-345).
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

### Phase 29b: Skills-Welle ✅ (2026-11-02)

- 20 Skills in `skills/<name>/SKILL.md` mit Glob-Trigger und Rollen-Filter.
- `skills_aktivieren(skills, task_files, max_total=3, rolle=...)` in 4 Prompt-Bauern.
- `loop_skills_geladen`-Audit + `state.geladene_skills` (Dedup).
- BUILDER_SYSTEM von ~6210 auf ~3700 Zeichen reduziert (-40%).
- REVIEWER_SYSTEM von ~6806 auf ~2600 Zeichen reduziert (-62%).
- Ausnahme: `DATUM (STRIKT)` bleibt im Prompt (Output-Contract).

### Phase 29: Loop-Reife Code-Patches 🟠 (OFFEN)

Bugs aus Live-Test 3 (OP-034..OP-038) in `docs/STATUS.md`:
pytest-Regression, Datum aus UTC, Reflection-Deduplizierung,
Reviewer-Signal, Commit-Message-Builder.

### Phase 30: Web-Dashboard & Interactive UI 🟢 (VISION)

**Ziel:** Ein echtes Dashboard, das die Werkstatt visuell begreifbar macht.
Referenz: Screenshot vom 2026-11-02 (Web-Interface mit Chat und Terminal).

**Layout:**
- **Links:** CLI / Terminal-Proxy (Live-Output des Loops, farbig).
- **Rechts oben:** Zwei Chat-Fenster.
  - *Admin-KI:* Kann alle Projekte lesen, beantwortet Meta-Fragen (wie ein externer Berater).
  - *Bau-Chat:* Projektspezifischer Chat, um Aufgaben interaktiv zu steuern.
- **Unten:** Audit-Panel mit ein-/ausblendbarer History-Sidebar.
  - *Live-Stream:* Echtzeit-Ansicht der aktuellen Events (wie ein Terminal).
  - *History-Sidebar (DeepSeek-Style):* Links einblendbar. Zeigt die
    vergangenen Tage (z.B. `2026-11-01`, `2026-10-31`). Klick laedt die
    statischen Logs des jeweiligen Tages (`audit-logs/agent-pipeline-<datum>.jsonl`).

**Kopplungs-Mechanik (Kern des UI):**
- Chrome-Tabs = Projekte. Ein Tab pro Projekt (z.B. `werkstatt`, `security-ai`).
- Alle Panels (Terminal, Admin-Chat, Bau-Chat, Audit-Logs) sind an den
  aktiven Tab gekoppelt. Tab-Wechsel = Kontext-Wechsel fuer alle Panels.
- State-Isolation pro Tab: Terminal-Scrollback, Chat-History und Log-Puffer
  werden pro Projekt getrennt gehalten.
- Web-Socket-Namespace pro Tab (`/ws/{project}`), kein globaler Stream.
  `loop_renderer` muss multi-projekt-faehig werden.
- Admin-KI uebergreift Tabs (darf alle Projekte lesen, Meta-Fragen
  beantworten). Bau-Chat ist tab-gebunden.

**Technische Umsetzung (existierende OPs, erweitert):**
- OP-030: Web-Backend (FastAPI, Web-Sockets pro Projekt, Tab-Routing).
- OP-031: Terminal/Audit-Proxy.
  - Live-Modus: Web-Socket-Stream der aktuellen Events (`/ws/{project}`).
  - History-Modus: REST-Endpoint (`/api/audit/{project}/{date}`) liest statische
    JSONL-Logs vergangener Tage.
  - UI: DeepSeek-artige Sidebar (ein-/ausblendbar) zur Datums-Auswahl.
- OP-032: Interactive Chat (Admin-KI tab-uebergreifend, Bau-Chat tab-gebunden).
- OP-033: UI-Layout (Tabs = Projekte, Terminal links, Chat rechts, Audit-Panel unten mit Sidebar).

## Offene Bloecke (P1/P2)

| Block | Prio | Kurz |
|---|---|---|
| ~~M-345~~ | ✅ | pipeline.py geloescht (erledigt) |
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
