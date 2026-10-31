# AGENTS.md — {{project_name}}

Verbindliche Constitution. Lese-Reihenfolge (Loop und Mensch):

1. `docs/STATUS.md` — offene Punkte (einziger Ort fuer "was ist zu tun")
2. `docs/ROADMAP.md` — Phasen, Milestones
3. `docs/ARCHITECTURE.md` — Modul-Map
4. `docs/CONVENTIONS.md` — Coding-Regeln
5. `docs/adr/` — Entscheidungen
6. `docs/glossary.md` — Begriffe
7. `docs/index.md` — Einstieg

Stand: {{date}}. Projekt: `{{project_dir}}`.

## Zweck

TODO: Kurzbeschreibung des Projekts (2-3 Saetze).

## Hard-Rules

- Ein Fakt = eine Quelle.
- Erledigte STATUS-Punkte wandern nach `PROGRESS.md`.
- Keine Behauptung ohne Code-Beleg (grep / Test / ast.parse).

## Loop

Der Loop liest die Dateien in obiger Reihenfolge. `docs/STATUS.md`
ist primaere Aufgabenquelle bei vagen Auftraegen.
