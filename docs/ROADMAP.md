# Roadmap — Werkstatt

Stand: 2026-11-10.
Diese Datei fasst die langfristige Entwicklung zusammen. Der verbindliche
Arbeitsfokus und offene Loop-OPs stehen in `STATUS.md`; erledigte Arbeit
steht in `PROGRESS.md`. Aeltere Baselines und Phasenberichte weiter unten
sind historische Snapshots, keine aktuelle Betriebsfreigabe.

## Aktueller Arbeitsfokus (2026-11-10)

**Ziel:** Eine belastbare Multi-Projekt-Agentenloop- und Entwicklungsumgebung,
deren Rollen, Gates, Audit und Projektgrenzen nachvollziehbar zusammenarbeiten.

### Bedien- und Autonomie-Fundament — ADR-0029

Chat wird zur zentralen Projekteingabe, Erklaerung und Steuerung. Jede
schreibende Chat-Aktion braucht eine konkrete vorherige Freigabe. Das
Plan-Gate bleibt immer verpflichtend. Runs bleiben ansprechbar und
transparent, waehrend Diagnose und Verify im Hintergrund laufen. Control
bietet Start, Pause, Fortsetzen und Stop mit sichtbarer Rueckmeldung.
STATUS liefert genehmigte Arbeitsauftraege; die Auswahl trifft ein
begruendeter, evidenzbasierter Selector statt einer blinden Zeilenfolge.

- **OP-396:** Chat als projektbezogene Hauptoberflaeche.
- **OP-397:** Persistente Hintergrundjobs mit Progress, Replay und Idempotenz.
- **OP-398:** Auswahl autonomer Arbeit mit Prioritaets-/Risiko-Begruendung,
  Verifikation und begrenzten Stop-Bedingungen.

1. **Phase 1 — UI bereitstellen:** OP-396, OP-397, OP-398, OP-381c,
   OP-381b, OP-306, OP-306b und Interfaces (Verify/CI-Status,
   Rollen-Details, Debug-Ansicht). Gate-Edit uebergibt den offenen
   Gate-Kontext an den Debug-Chat. Nach einmaliger Patch-Freigabe
   uebergibt der Chat den Patch-Inhalt direkt an den Coding-Loop;
   manueller Copy/Paste und Gate-Antwort als Codefreigabe sind ausgeschlossen.
2. **Phase 2 — Loop im UI-Betrieb stabilisieren:** OP-382 Dogfooding mit
   zehn vollständigen realen OPs, Debugger-Kette und konstante erfolgreiche
   Runs ohne Abbrüche.
3. **Phase 3 — Selbstverbesserung und Memory:** OP-376–379, OP-380 und
   OP-220 ff. bleiben gesperrt, bis Phase 2 mit zehn erfolgreichen Runs
   nachgewiesen ist.

Der Status der Phasen, Abhängigkeiten und Live-Belege wird ausschliesslich in
`STATUS.md` gepflegt. Die nachfolgenden Abschnitte dokumentieren frühere
Ausbaustufen und Messstände.

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
- pytest: 1164 passed, 5 skipped (2026-11-02).
- ruff: 180 errors (2026-11-02).
- mypy: 18 errors in 9 files (werkstatt/, nicht auf .).
- AST + Katalog: skip in quality_gate (Dateien entfernt, delta=0).
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

### Phase 20: ADaPT ~~✅~~ entfernt 2026-11-08 (zu selten, kein Audit-Trail)

- M-472: On-Demand-Zerlegung (`_split_task_on_demand`).
- M-473: `while`-Loop statt `for` (Sub-Tasks werden gebaut).
- M-474: ADaPT bei `reviewer_high_bug_fail_closed`.
- M-475: `get_next_task` liefert nur `pending`.

### Phase 21: Doku-Diataxis ✅ (2026-11-02)

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

### Phase 30: Web-Dashboard & Interactive UI ✅ (fertig 2026-11-03)

**Ziel:** Ein echtes Dashboard, das die Werkstatt visuell begreifbar macht.

**Status (2026-11-03):** Fertig. Auth-Middleware (Token+Cookie+WS-Check),
PTY-Terminal via xterm.js (echte bash im Browser), DeepSeek-Look, Audit-
Live + History farbcodiert nach Kategorie, Chat mit Intent-Klassifikation
(keine LLM-Antwort — siehe OP-084), Tab-Bindung mit WS-Lifecycle. Server-
Start: python -m werkstatt.web --host 0.0.0.0 --port 8000.
Referenz: Screenshot vom 2026-11-02 (Web-Interface mit Chat und Terminal).

**Layout:**
- **Links:** CLI / Terminal-Proxy (Live-Output des Loops, farbig).
- **Rechts oben:** Zwei Chat-Fenster.
  - *Admin-KI:* Kann alle Projekte lesen, beantwortet Meta-Fragen (wie ein externer Berater).
  - *Bau-Chat:* Projektspezifischer Chat, um Aufgaben interaktiv zu steuern.
  - *Maximize/Minimize:* Jedes der beiden Chat-Fenster hat einen Button, um es auf
    die volle rechte Breite/Höhe zu maximieren oder auf eine schmale Leiste
    zu minimieren. Der Nutzer kann so flexibel zwischen Übersicht (beide Chats)
    und Fokus (ein Chat) wechseln.
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

**Status 2026-11-02 abends:**
- Backend (OP-074): ✅ FastAPI mit WebSockets, 3 REST-Routen, 2 Tests
- Terminal-Proxy (OP-075): ✅ loop_renderer → WebSocket-Bridge
- Chat (OP-076): ✅ Chat-Fenster mit Maximize/Minimize
- Audit (OP-077): ✅ REST-History + WebSocket-Live
- Layout (OP-078): ✅ Tabs + Grid + History-Sidebar
- Offen: Verdrahtung (layout.html → Backend), FastAPI StaticFiles-Mount,
  uvicorn-Start-Anleitung. Naechster OP.

**Technische Umsetzung (existierende OPs, erweitert):**
- OP-030: Web-Backend (FastAPI, Web-Sockets pro Projekt, Tab-Routing).
- OP-031: Terminal/Audit-Proxy.
  - Live-Modus: Web-Socket-Stream der aktuellen Events (`/ws/{project}`).
  - History-Modus: REST-Endpoint (`/api/audit/{project}/{date}`) liest statische
    JSONL-Logs vergangener Tage.
  - UI: DeepSeek-artige Sidebar (ein-/ausblendbar) zur Datums-Auswahl.
- OP-032: Interactive Chat (Admin-KI tab-uebergreifend, Bau-Chat tab-gebunden).
- OP-033: UI-Layout (Tabs = Projekte, Terminal links, Chat rechts, Audit-Panel unten mit Sidebar).
  - *Split-Pane-System:* Die beiden Chat-Fenster auf der rechten Seite (Admin & Bau)
    koennen per Button maximiert/minimiert werden (Full-Height vs. schmale Leiste).
    Der Zustand wird im Frontend (React/Vue/htmx) gehalten, ohne das Backend zu belasten.

### Phase 31: Roadmap-to-OP Compiler (Meta-Loop) 🟢 (VISION)

**Ziel:** Die Luecke zwischen ROADMAP.md (Vision) und STATUS.md (Queue) schliessen.
Aktuell muessen wir Roadmap-Phasen manuell in OPs zerlegen. Das soll der Loop selbst lernen.

- Ein neues Werkzeug `werkstatt/roadmap_compiler.py`.
- Liest die naechste unfertige Phase aus `ROADMAP.md`.
- Ruft den Architect auf mit dem Prompt: *"Zerlege diese Phase in atomare OPs nach STATUS.md-Format."*
- Validiert das Ergebnis (OP-NNN, Akzeptanzkriterien, Tests vorhanden?).
- Haengt die validierten OPs an `docs/STATUS.md` an.

**Konsequenz:** Die Werkstatt kann autonom neue Phasen aus der Roadmap abarbeiten,
ohne dass ein Mensch die OPs manuell formulieren muss.


### Phase 32: Debugger-Agent — deterministisch messen, LLM-fixen 📋 (NEU 2026-11-02)

Ziel: Ein Agent, der Bugs/Lint/Typ-Fehler findet, per AST+ruff+mypy
deterministisch prueft ob ein Fix safe ist, und dann LLM-getrieben
iteriert. Bounded (max 3 Runden), dann Eskalation. Kein Endlos-Loop.

- M-500: `werkstatt/debugger.py` — Measure-Layer. Pro Datei: AST-Dump,
  Ruff-JSON, Mypy-JSON, betroffene Tests, Monkeypatch-Ziele (`patch("$modul.$name"`),
  Re-Export-Namen (`from $modul import $name` repo-weit).
- M-501: Guard-Layer. Verweigert Auto-Fix wenn (a) Name in `__all__` steht,
  (b) Monkeypatch-Ziel (grep-beweisbar), (c) Re-Export ohne lokalen Gebrauch.
  Alle drei deterministisch, kein LLM.
- M-502: Fix-Orchestrator. LLM (deepseek-chat) bekommt (a) Mess-Zustand aus
  M-500, (b) Guard-Verdikte aus M-501, (c) Gate-Historie. Liefert Patch.
  Max 3 Iterationen, dann Eskalation.
- M-503: Gate-Runner. Nach jedem Fix: py_compile, pytest --collect-only,
  pytest <betroffene>, mypy werkstatt/, ruff <geaenderte Datei>.
  Rot -> Rollback, naechste Iteration.
- M-504: Eskalation. Nach 3 Runden ohne gruene Gates: `PROGRESS.md`-Eintrag
  mit Status `manual-needed`, Diff-Vorschlag, Fehlerkategorien. Kein Commit.
- M-505: Tests. `tests/test_debugger.py` mit 3 Szenarien:
  (1) Re-Export-Schutz greift, (2) Monkeypatch-Schutz greift,
  (3) End-to-End-Fix mit Mock-LLM gruen.

Anlass (2026-11-02): Bei der F401-Welle (Commit 705ae81) sind zwei
Auto-Fix-Fallen aufgetreten, die der Agent deterministisch pruefen MUSS:
(a) ruff killt Re-Exports (`werkstatt/loop.py` 47 Namen, von Tests
importiert).
(b) ruff killt Monkeypatch-Ziele (`import time`/`subprocess` in loop.py,
von Tests als `werkstatt.loop.time`/`.subprocess` gepatcht).
Beide sind per grep/AST vor dem Fix erkennbar. Ein reiner LLM-Debugger
ohne deterministischen Guard haette beide Fallen reproduziert.


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

## Aus STATUS.md (Loop-Queue, roadmap-phase)

Die folgenden Punkte stammen aus `docs/STATUS.md` und sind **Roadmap-Phasen
(M-NNN)** — nicht loop-faehig. Sie stehen hier als Design-Notizen, bis sie
in konkrete loop-faehige OPs zerlegt werden (vgl. OP-073 Roadmap-Compiler).

Stand: 2026-11-03, migriert aus STATUS.md.

#### OP-004: M-323b — `phase_end`-Checkpoint pro logischer Phase. Nach jeder Phase `_verify_patches(state, phase="phase_end")` + Reflection.
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** `phase_end`-Checkpoint pro logischer Phase. Nach jeder Phase `_verify_patches(state, phase="phase_end")` + Reflection.
- **Tests:** —
- **Blockiert von:** —


#### OP-005: M-341 — Explorer ueberspringen, wenn `task_files` gesetzt.
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Explorer ueberspringen, wenn `task_files` gesetzt.
- **Tests:** —
- **Blockiert von:** —


#### OP-006: M-344 — `PROGRESS.md` mit Phasen-Header (pro Phase, nicht pro Task).
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** `PROGRESS.md` mit Phasen-Header (pro Phase, nicht pro Task).
- **Tests:** —
- **Blockiert von:** —


#### OP-010: Entkopplung — `werkstatt/verify.py` importiert `harness.*` und `core.changeapplier.*` (nur Introspektion). Ziel: null Fremd-Imports.
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** `werkstatt/verify.py` importiert `harness.*` und `core.changeapplier.*` (nur Introspektion). Ziel: null Fremd-Imports.
- **Tests:** —
- **Blockiert von:** —


#### OP-011: mypy-Restfehler abbauen (Baseline 27, 2026-11-03)
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


#### OP-012: 3c — Alte Tests, die mit dem alten Code fallen, entfernen.
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Alte Tests, die mit dem alten Code fallen, entfernen.
- **Tests:** —
- **Blockiert von:** —


#### OP-013: M-162 — „Recovery nach Loop" messen oder schliessen.
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** „Recovery nach Loop" messen oder schliessen.
- **Tests:** —
- **Blockiert von:** —


#### OP-014: M-388 — UI-Testing via Chrome DevTools.
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** UI-Testing via Chrome DevTools.
- **Tests:** —
- **Blockiert von:** —


#### OP-015: M-389 — Doku-Pflege im Loop.
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Doku-Pflege im Loop.
- **Tests:** —
- **Blockiert von:** —


#### OP-016: M-479 — Modell-Routing pro Rolle. `ask_llm(role=...)` mit Env-Vars. Architect = `deepseek-reasoner`, Builder/Reviewer = `deepseek-chat`.
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Modell-Routing pro Rolle. `ask_llm(role=...)` mit Env-Vars. Architect = `deepseek-reasoner`, Builder/Reviewer = `deepseek-chat`.
- **Tests:** —
- **Blockiert von:** —


#### OP-017: M-480 — Kosten-Circuit-Breaker. `RunState.max_budget_usd`. `ask_llm` zaehlt Tokens, bei Ueberschreitung `BudgetExceededError`.
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Kosten-Circuit-Breaker. `RunState.max_budget_usd`. `ask_llm` zaehlt Tokens, bei Ueberschreitung `BudgetExceededError`.
- **Tests:** —
- **Blockiert von:** —


#### OP-018: M-481 — Cache-aware Prompts. Stabiler Prefix (System, Architektur) vor variablem Suffix (Aufgabe). 98.6% Cache-Hit-Rate moeglich.
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Cache-aware Prompts. Stabiler Prefix (System, Architektur) vor variablem Suffix (Aufgabe). 98.6% Cache-Hit-Rate moeglich.
- **Tests:** —
- **Blockiert von:** —


#### OP-019: M-482 — LiteLLM Adaptive Router (optional). Lernt, welches Modell fuer welchen Request-Typ am besten ist.
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** LiteLLM Adaptive Router (optional). Lernt, welches Modell fuer welchen Request-Typ am besten ist.
- **Tests:** —
- **Blockiert von:** —


#### OP-020: M-478/M-489 — Test-Repair-Loop (TDFlow-Stil). 4 Sub-Agenten: Patch-Propose, Debug, Patch-Revise, Test-Generate. Tests FEST (kein Test-Hacking). Max 3 Runden, dann Eskalation.
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Test-Repair-Loop (TDFlow-Stil). 4 Sub-Agenten: Patch-Propose, Debug, Patch-Revise, Test-Generate. Tests FEST (kein Test-Hacking). Max 3 Runden, dann Eskalation.
- **Tests:** —
- **Blockiert von:** —


#### OP-021: M-483 — Sandboxing (OS-Level). Filesystem-Isolation + Netzwerk-Isolation. Linux bubblewrap / macOS seatbelt. Reduziert Permission-Prompts um 84%.
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Sandboxing (OS-Level). Filesystem-Isolation + Netzwerk-Isolation. Linux bubblewrap / macOS seatbelt. Reduziert Permission-Prompts um 84%.
- **Tests:** —
- **Blockiert von:** —


#### OP-022: M-484 — SWE-bench-Harness. 50-100 Tasks aus `princeton-nlp/SWE-bench_Verified`. Die einzige Zahl, die mit Aider/OpenHands/Devin vergleichbar ist.
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** SWE-bench-Harness. 50-100 Tasks aus `princeton-nlp/SWE-bench_Verified`. Die einzige Zahl, die mit Aider/OpenHands/Devin vergleichbar ist.
- **Tests:** —
- **Blockiert von:** —


#### OP-023: M-485 — Event-Sourcing / Memory. Unveraenderliche Event-Logs statt YAML-Checkpoint. Loop-Spezifikation (Trigger, Goal, Verification, Stopping Rule, Memory).
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Event-Sourcing / Memory. Unveraenderliche Event-Logs statt YAML-Checkpoint. Loop-Spezifikation (Trigger, Goal, Verification, Stopping Rule, Memory).
- **Tests:** —
- **Blockiert von:** —


#### OP-024: M-486 — Cache-aware Cost Model. 98.6% Input-Tokens aus Prefix-Cache. Flat-Pricing ueberschaetzt Kosten um 7.1x.
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Cache-aware Cost Model. 98.6% Input-Tokens aus Prefix-Cache. Flat-Pricing ueberschaetzt Kosten um 7.1x.
- **Tests:** —
- **Blockiert von:** —


#### OP-025: M-488 — `phase_end` laeuft Vollsuite. `verify.json` + `loop.py` (M-476). Ohne das ist der Loop ein Builder.
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** `phase_end` laeuft Vollsuite. `verify.json` + `loop.py` (M-476). Ohne das ist der Loop ein Builder.
- **Tests:** —
- **Blockiert von:** —


#### OP-027: M-490 — Doku-Staleness-Check (deterministisch, Documentledger). Nach jedem Task: Hash-Vergleich Code -> Doku. Kein LLM.
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Doku-Staleness-Check (deterministisch, Documentledger). Nach jedem Task: Hash-Vergleich Code -> Doku. Kein LLM.
- **Tests:** —
- **Blockiert von:** —


#### OP-028: M-491 — Doku-Update-Agent (DocWriter). Bekommt Git-Diff + betroffene Sektionen + Quellcode. Schreibt nur `<!-- AUTO:... -->`-Bloecke neu (docwright).
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Doku-Update-Agent (DocWriter). Bekommt Git-Diff + betroffene Sektionen + Quellcode. Schreibt nur `<!-- AUTO:... -->`-Bloecke neu (docwright).
- **Tests:** —
- **Blockiert von:** —


#### OP-029: M-492 — Doku-Critic (DocSync). Prueft DocWriter-Output gegen Code. Max 2 Runden.
- **Status:** open
- **Typ:** roadmap-phase (nicht loop-fähig — gehört in ROADMAP.md, nicht in die Loop-Queue)
- **Betroffene Dateien:** —
- **Akzeptanzkriterien:** Doku-Critic (DocSync). Prueft DocWriter-Output gegen Code. Max 2 Runden.
- **Tests:** —
- **Blockiert von:** —


#### OP-064: Architektur-Umbau — Completion-Gate mit Vetorecht (Sammel-OP)

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



## Phase 33: Kontroll-Zentralisierung (werkstatt/control/)

Stand: 2026-11-03, gestartet.

Motivation: 32 Kontrollfunktionen ueber 14 Dateien verstreut, 21
Phase-Hooks ueber 10 Dateien. Debugging erforderte Grep ueber den
halben Code. Nach dem pipeline.py-Monolithen die naechste Schicht.

Ziel: `werkstatt/control/` als einzige Stelle fuer Gates,
Verify-Stages, Reflections und Guards.

| Phase | Inhalt | Status |
|---|---|---|
| 33.1 | control/-Skelett + Registry (13 Kontrollen) + Drift-Check | erledigt 2026-11-03 |
| 33.2 | verify.py nach control/, 5 Proxies weg, verify.json hart-Feld | OP-095 |
| 33.3 | gates.py nach control/ | OP-096 |
| 33.4 | reflection.py nach control/ | OP-097 |
| 33.5 | pipeline_phases.py 1600 auf <400 Zeilen | OP-098 |
| 33.6 | control_drift als Pre-Commit-Gate | OP-099 |

Guardrail pro Phase: `pytest -q --ignore=tests/test_shell.py` gruen UND
`python3 tools/control_drift.py --check` Exit 0. Kein Big-Bang.
