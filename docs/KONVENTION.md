# Konvention — Werkstatt

Stand: 2026-10-18
Zweck: Ordnerstruktur, Datei-Namen, Verantwortlichkeiten.

## 1. Ziel

Die Werkstatt ist ein Agenten-System, das Projekte baut.
Sie ist unabhaengig von jedem Ziel-Projekt. Ordner und
Datei-Namen folgen einer festen Konvention.

## 2. Ordner-Struktur (verbindlich)

    /opt/werkstatt/
    |-- README.md                Einstieg, Ziel, Stand
    |-- Bau-Handoff.md           Aktueller Stand (kompakt, < 500 Z.)
    |-- Bau-Handoff-Archiv.md    Alte Handoffs (append-only)
    |-- pipeline.py              Orchestrierung
    |-- redaction.py             Redaction vor LLM-Calls
    |
    |-- docs/                    Werkstatt-Doku
    |   |-- KONVENTION.md        Diese Datei
    |   |-- ARCHITEKTUR.md       Ziel, Rollen, Luecken
    |   |-- ROADMAP.md           Phasen- und W-Block-Uebersicht
    |   |-- OFFENE-BLOECKE.md    Todo, priorisiert
    |   |-- ERLEDIGT.md          Abgeschlossene Bloecke
    |   |-- ROLLEN-AUDIT.md      Rollen-Stand
    |   |-- WORKFLOW.md          Pipeline-Ablauf
    |   +-- PROTOKOLL-*.md       Sitzungs-Protokolle
    |
    |-- agents/                  Rollen-Prompts
    |   |-- planner.md
    |   |-- builder.md
    |   |-- solver.md
    |   |-- judge.md
    |   |-- reviewer.md
    |   |-- test_generator.md
    |   |-- coverage.md
    |   +-- chaos.md
    |
    |-- skills/                  Workflows (W25)
    |-- anti-patterns/           Katalog (W37)
    |-- schemas/                 JSON-Schemas
    |-- werkstatt/               Modularisiert (W31-W47)
    |   |-- state.py
    |   |-- parser.py
    |   +-- (planner.py, audit.py,
    |        judge.py, apply.py, measurements.py
    |        -- W36/W52 offen)
    |
    |-- projects/                Projekt-Configs
    |   |-- <name>.yaml
    |   |-- <name>.phase.yaml
    |   |-- <name>.memory.yaml
    |   +-- _template.yaml
    |
    |-- audit-logs/              JSONL pro Tag
    |-- tests/                   Werkstatt-Tests
    +-- .werkstatt/              Laufzeit-State (W34-Ignore)

## 3. Datei-Verantwortlichkeiten

### docs/

| Datei | Zweck | Stand |
|---|---|---|
| KONVENTION.md | Ordner, Namen, Regeln | 2026-10-18 |
| ARCHITEKTUR.md | Ziel, Rollen, Luecken | 2026-10-18 |
| ROADMAP.md | Uebersicht Phasen/W-Bloecke | offen |
| OFFENE-BLOECKE.md | Todo, priorisiert | 2026-10-18 |
| ERLEDIGT.md | Abgeschlossene Bloecke | offen |
| ROLLEN-AUDIT.md | Rollen-Stand | 2026-10-18 |
| WORKFLOW.md | Pipeline-Ablauf | 2026-10-16 |
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

Nicht committen (W34-Ignore). Enthaelt plan.md,
contracts/, messungen/ (W52b offen), planner/ (W52b offen).

## 4. Was wo hingehört

| Information | Datei | Nicht in |
|---|---|---|
| Phasen-Uebersicht | docs/ROADMAP.md | Bau-Handoff.md |
| Offene Bloecke | docs/OFFENE-BLOECKE.md | docs/ROADMAP.md |
| Erledigte Bloecke | docs/ERLEDIGT.md | Bau-Handoff.md |
| Aktueller Stand | Bau-Handoff.md | README.md |
| Ziel des Systems | README.md, ARCHITEKTUR.md | ROADMAP.md |
| Rollen-Stand | docs/ROLLEN-AUDIT.md | agents/*.md |
| Rollen-Definition | agents/*.md | README.md |
| Pipeline-Ablauf | docs/WORKFLOW.md | README.md |
| Ordner-Konvention | docs/KONVENTION.md | README.md |

## 5. Trennung Roadmap / Todo / Erledigt

**docs/ROADMAP.md (Uebersicht):**
- Phasen: Phase 1-20b, Status done/offen/blockiert.
- W-Bloecke: W31-W61, Status done/offen/blockiert.
- Meilensteine. Keine Details.

**docs/OFFENE-BLOECKE.md (Todo):**
- Tabellarisch, priorisiert (P1/P2/P3).
- Spalten: Block, Kategorie, Beschreibung, Aufwand.
- Verweis auf ROADMAP.md.

**docs/ERLEDIGT.md (Erledigt):**
- Tabellarisch, append-only.
- Spalten: Block, Kategorie, Commit, Tests, Katalog.
- Bei > 200 Zeilen: aeltere ins Bau-Handoff-Archiv.md.

## 6. Bau-Handoff.md — kompakt

Ziel: < 500 Zeilen.

Inhalt:
- Kopf: Stand, HEAD (beide Repos), Tests (beide), Branch.
- Aktueller Bau-Block (naechster Schritt).
- Verweis auf docs/OFFENE-BLOECKE.md (Todo).
- Verweis auf docs/ERLEDIGT.md (Erledigt).
- Verweis auf docs/ROADMAP.md (Uebersicht).
- Wichtige Merkposten (W54-f, W57, W59, W61).

Nicht in Bau-Handoff.md:
- Details zu jedem W-Block (gehoert in ERLEDIGT.md).
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
| docs/OFFENE-BLOECKE.md | 150 Zeilen | Lesbarkeit |
| docs/ERLEDIGT.md | 200 Zeilen | danach Archiv |
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

- `docs/ARCHITEKTUR.md` — Ziel-Architektur, Rollen, Luecken.
- `docs/ROADMAP.md` — Phasen- und W-Block-Uebersicht.
- `docs/OFFENE-BLOECKE.md` — Todo, priorisiert.
- `docs/ERLEDIGT.md` — Abgeschlossene Bloecke.
- `docs/ROLLEN-AUDIT.md` — Rollen-Stand.
- `docs/WORKFLOW.md` — Pipeline-Ablauf.
