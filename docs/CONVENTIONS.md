# Konvention — Werkstatt

Stand: 2026-11-08
Zweck: Ordnerstruktur, Datei-Namen, Verantwortlichkeiten.

## 1. Ziel

Die Werkstatt ist ein Agenten-System, das Projekte baut.
Sie ist unabhaengig von jedem Ziel-Projekt. Ordner und
Datei-Namen folgen einer festen Konvention.

## 2. Ordner-Struktur (verbindlich, Stand 2026-11-08)

    /opt/werkstatt/
    |-- README.md                Einstieg, Ziel, Stand
    |-- PROGRESS.md              Historie (append-only)
    |-- AGENTS.md                Constitution, Lese-Reihenfolge
    |-- .werkstatt/              Laufzeit (nicht im git)
    |   |-- events.db            SQLite-Projektion (rebuildbar)
    |   |-- verify.json          Verify-Stage-Vertrag
    |   +-- auth-token           Web-UI-Auth
    |-- audit-logs/              Event-Log (JSONL)
    |   |-- semantic-*.jsonl     semantische Events (git)
    |   +-- stream-*.jsonl       Laufzeit-Events (gitignored)
    |-- projects/                Projekt-Registry (YAML pro Projekt)
    |-- werkstatt/               Python-Paket
    |   |-- loop.py              Orchestrierung, CLI
    |   |-- audit.py             JSONL-Writer (audit + stream)
    |   |-- projection.py        JSONL -> SQLite Projektor
    |   |-- event_store.py       SQLite-Reader fuer UI
    |   |-- scaffold.py          Projekt-Pflichtdateien
    |   |-- migrate.py           Doku-Konsistenz-Check
    |   |-- orchestrator.py      RunState + Config-Loader
    |   |-- explorer.py          Rolle Explorer
    |   |-- scout.py             Rolle Scout
    |   |-- planner.py           Architect + Planner-Split
    |   |-- reviewer.py          Rolle Reviewer
    |   |-- reflection.py        Rolle Reflection
    |   |-- rollen.py            Rollen-Registry (Single Source of Truth)
    |   |-- skills.py            Skill-Loader
    |   |-- chat_agent.py        Chat-Agent
    |   |-- chat_session.py      Session-Persistenz
    |   |-- chat_tools.py        Read-only Tool-Registry
    |   |-- roles/               Rollen-Module (builder/, etc.)
    |   |-- phases/              Loop-Phasen
    |   |-- render/              Terminal-Rendering
    |   |-- web/                 FastAPI-Backend
    |   |   |-- app.py           HTTP-Endpoints
    |   |   |-- inspector.py     Aggregatoren
    |   |   |-- auth.py          Login-Middleware
    |   |   +-- audit_panel.py   Audit-Endpoints
    |   +-- templates/           Scaffold-Templates
    |-- static/                  Web-UI (kein Build-Schritt)
    |   |-- layout.html          HTML-Grundgeruest
    |   |-- layout.css           Styles (sem-Farben aus OP-300)
    |   |-- ambient_status.js    Ambient-Bar (OP-301)
    |   |-- palette.js           Command Palette (OP-302)
    |   |-- runs.js              Runs-Liste + Start/Stop (OP-303)
    |   |-- shortcut_help.js     `?`-Overlay (OP-304)
    |   |-- utility_bar.js       ⌘K/?-Buttons (OP-305)
    |   |-- project_create.js    Projekt-Anlage-Modal (OP-305)
    |   |-- audit.js             Audit-Panel
    |   |-- timeline.js          Timeline
    |   |-- chat.js              Chat-Pane
    |   +-- tabs.js              Tab-Verwaltung
    |-- skills/                  On-Demand-Workflows (SKILL.md + tools/)
    |-- docs/                    Werkstatt-Doku
    |   |-- CONVENTIONS.md       Diese Datei
    |   |-- ARCHITECTURE.md      IST-Zustand
    |   |-- SOLL.md              Ziel-Architektur
    |   |-- STATUS.md            Offene Punkte (OP-NNN)
    |   |-- ROADMAP.md           Phasen
    |   |-- MERKPOSTEN.md        Prozess-Lehren (append-only)
    |   |-- DOC_CONVENTIONS.md   Meta-Regeln fuer Ziel-Projekte
    |   |-- glossary.md          Begriffe
    |   +-- adr/                 Architecture Decision Records
    +-- tests/                   pytest (1515 passed am 2026-11-08)

## 3. Datei-Verantwortlichkeiten

### docs/

| Datei | Zweck | Stand |
|---|---|---|
| CONVENTIONS.md | Coding-Regeln | 2026-10-31 |
| ARCHITECTURE.md | Modul-Map | 2026-10-31 |
| ROADMAP.md | Uebersicht Phasen/W-Bloecke | offen |
| STATUS.md | Offene Punkte (OP-NNN) | 2026-10-31 |
| ERLEDIGT.md | Abgeschlossene Bloecke | offen |
| IDEEN.md | Wunschliste (2101-2106) | 2026-10-18 |
| ROLLEN-AUDIT.md | Rollen-Stand | 2026-10-18 |
| PROTOKOLL-*.md | Sitzungen | fortlaufend |

### agents/ — Frontmatter

    ---
    name: <rolle>
    description: |
      <was die Rolle tut>
    model: <deepseek-chat | deepseek-reasoner | none>
    temperature: <float>
    ---
    <Body: Rolle, Aufgaben, Grenzen, Adressat>

Groessen-Ziel:
- builder.md: < 300 (aktuell 647).
- planner.md: < 150 (aktuell 297).
- reviewer.md: < 250 (aktuell 56).
- solver.md: < 250 (aktuell 182).
- judge.md: < 200 (aktuell 90).

### projects/ — drei Dateien pro Ziel-Projekt

- `<name>.yaml` — Projekt-Config.
- `<name>.phase.yaml` — Phasen-State.
- `<name>.memory.yaml` — Agent-Memory.

Format: siehe `schemas/`.

### .werkstatt/ — Laufzeit-State

Nicht committen (W34-Ignore). Enthaelt:
- `plan.md` — aktueller Phasenplan.
- `contracts/` — Contract pro Unterblock.
- `messungen/<sha1>.txt` + `index.json` — On-Demand-
  Messungen (W52b). Statt String im Prompt: Index + Dateien.
- `planner/<runde>.reply` + `<runde>.plan` — Planner-
  Replies als Dateien (W52b).

## 4. Was wo hingehört

| Information | Datei | Nicht in |
|---|---|---|
| Phasen-Uebersicht | docs/ROADMAP.md | Bau-Handoff.md |
| Offene Bloecke | docs/STATUS.md | docs/ROADMAP.md |
| Erledigte Bloecke | PROGRESS.md | Bau-Handoff.md |
| Aktueller Stand | Bau-Handoff.md | README.md |
| Ziel des Systems | README.md, ARCHITEKTUR.md | ROADMAP.md |
| Rollen-Stand | docs/ROLLEN-AUDIT.md | agents/*.md |
| Rollen-Definition | agents/*.md | README.md |
| Ordner-Konvention | docs/CONVENTIONS.md | README.md |

## 5. Trennung Roadmap / Todo / Erledigt

**docs/ROADMAP.md (Uebersicht):**
- Phasen: Phase 1-20b, Status done/offen/blockiert.
- W-Bloecke: W31-W61, Status done/offen/blockiert.
- Meilensteine. Keine Details.

**docs/STATUS.md (Todo):**
- Tabellarisch, priorisiert (P1/P2/P3).
- Spalten: Block, Kategorie, Beschreibung, Aufwand.
- Verweis auf ROADMAP.md.

**PROGRESS.md (Erledigt):**
- Tabellarisch, append-only.
- Spalten: Block, Kategorie, Commit, Tests, Katalog.
- Bei > 200 Zeilen: aeltere ins archiv/bau-handoff-archiv.md.

## 6. Bau-Handoff.md — kompakt

Ziel: < 500 Zeilen.

Inhalt:
- Kopf: Stand, HEAD (beide Repos), Tests (beide), Branch.
- Aktueller Bau-Block (naechster Schritt).
- Verweis auf docs/STATUS.md (Todo).
- Verweis auf PROGRESS.md (Erledigt).
- Verweis auf docs/ROADMAP.md (Uebersicht).
- Wichtige Merkposten (W54-f, W57, W59, W61).

Nicht in Bau-Handoff.md:
- Details zu jedem W-Block (gehoert in PROGRESS.md).
- Phasen-Uebersicht (gehoert in ROADMAP.md).
- Rollen-Definitionen (gehoeren in agents/).

## 7. Regel: keine Duplikate

Ein Fakt, eine Datei. Wenn ein Fakt in zwei Dateien
steht:
- Die Quelle ist die kanonische Datei.
- Die andere Datei verweist.

Beispiel: "1166 Tests" steht im Bau-Handoff.md (Kopf).
README.md verweist: "Tests: siehe Bau-Handoff.md".

## 8. Regel: Aenderungen dokumentieren

Jeder Doku-Commit nennt im Body:
- Was geaendert.
- Warum.
- Rollback-Kriterium (falls relevant).

## 9. Regel: Groessen-Limits

| Datei | Limit | Grund |
|---|---|---|
| Bau-Handoff.md | 500 Zeilen | Lesbarkeit |
| docs/ROADMAP.md | 200 Zeilen | Uebersicht |
| docs/STATUS.md | 150 Zeilen | Lesbarkeit |
| PROGRESS.md | 200 Zeilen | danach Archiv |
| agents/builder.md | 300 Zeilen | LLM liest es sonst nicht |
| agents/planner.md | 150 Zeilen | dito |
| agents/reviewer.md | 250 Zeilen | dito |
| agents/solver.md | 250 Zeilen | dito |

Wenn ein Limit ueberschritten: eigener Block (z.B. W61
Rollen-Sanierung fuer builder.md).

## 10. Was NICHT in die Werkstatt gehoert

- Ziel-Projekt-Dateien (z.B. security-ai-spezifische
  Code-Dateien). Die Werkstatt baut sie, aber sie
  gehoeren dem Ziel-Projekt.
- Ziel-Projekt-Doku (STATUS.md, TODO.md der
  Ziel-Projekte). Die Werkstatt schreibt sie, aber sie
  liegen im Ziel-Projekt.
- Vertrauliche Daten (API-Keys, Passwoerter). Gehoeren
  in .env-Dateien (nicht committen).

## 11. Verweise

- `docs/ARCHITECTURE.md` — Ziel-Architektur, Rollen, Luecken.
- `docs/ROADMAP.md` — Phasen- und W-Block-Uebersicht.
- `docs/STATUS.md` — Todo, priorisiert.
- `PROGRESS.md` — Abgeschlossene Bloecke.
- `docs/ROLLEN-AUDIT.md` — Rollen-Stand.

## OP-Standard fuer loop-faehige Tasks (2026-11-02)

Jeder loop-faehige OP braucht vier Pflichtfelder. Scout parst Backticks
bei `Betroffene Dateien` -> Task-Zuordnung. Architect bekommt Akzeptanz
als Prompt-Kontext.

### Pflichtfelder

- **Status:** open
- **Betroffene Dateien:** Werkstatt-Pfade mit Backticks + Zweck
- **Akzeptanzkriterien:** Code-Verhalten (nicht "messen"/"entstauben")
- **Tests:** Konkreter Test-Name oder Test-Datei-Pfad
- **Blockiert von:** —

### Optionale Felder (bei Over-Engineering-Gefahr empfohlen)

- **Existiert bereits:** Symbole/Funktionen, die im Code schon da sind
- **Fehlt noch:** Was tatsaechlich fehlt, nicht vermuten
- **Nicht-Ziele:** Was NICHT gebaut werden soll (Wrapper, neue APIs)

### Loop-Faehigkeits-Kriterien

Ein OP ist loop-faehig wenn:
1. Betroffene Dateien unter `werkstatt/` oder `tests/`
2. Akzeptanz ist Code-Verhalten
3. 1-3 Dateien, kein Sammel-OP
4. Konkreter Test benennbar

NICHT loop-faehig: Mess-Aufgaben (OP-065, OP-070),
Doku-Entstauben (OP-045, OP-046), Baseline-Revision (OP-041),
Multi-Task-Umbauten (OP-064, OP-039).

Hintergrund: Live-Beleg OP-068 (2026-11-02). Ohne `Existiert bereits`
hat Architect `ask_llm_in_stage` erfunden, obwohl `ask_llm(aufgabe=)`
dasselbe leistet. Das Feld verhindert Fehldiagnosen.
