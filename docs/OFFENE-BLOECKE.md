# Offene Bloecke — Werkstatt

Stand: 2026-10-18
Todo, priorisiert. Append-only.
Uebersicht in `ROADMAP.md`. Erledigt in `ERLEDIGT.md`.

## Prioritaet 1 (akut, blockiert Phase 20b)

| Block | Kategorie | Beschreibung | Aufwand |
|---|---|---|---|
| W59 | 3 | Patch nur nach Messung (Read-Cache, mtime, Deadlock-Mechanismus). Blockiert Phase 20b. | mittel (25 Tests anpassen) |
| W61 | 3 | Rollen-Sanierung. builder.md 647 -> < 300, planner.md 297 -> < 150. Redundanz aufloesen. Aus docs/ROLLEN-AUDIT.md Sektion 8. | gross (6+ Bloecke) |

## Prioritaet 2 (strukturell, aus Audit)

| Block | Kategorie | Beschreibung | Aufwand |
|---|---|---|---|
| W55 | 3 | Solver-Fehldiagnose. Prueft Ist-Zustand statt Aufgabe (Phase-20b: "Auftrag erfuellt" obwohl .log() fehlt). | klein |
| W58 | 3 | Reviewer-Leer-Antwort bei Deadlock. Reviewer antwortet leer statt Fail-closed. | klein |
| W54f | 3 | builder.md 647 Zeilen kuerzen. Audit-Ziel < 300. | mittel |
| W57 | 3 | Prompt-Audit aller Rollen-Dateien. Was liest das LLM tatsaechlich? Was wird ignoriert? | mittel |

## Prioritaet 3 (Refactor, nicht blockierend)

| Block | Kategorie | Beschreibung | Aufwand |
|---|---|---|---|
| W52a-1 | 2 | Planner-Funktionen nach `werkstatt/planner.py` (lazy imports, ~900 Zeilen). | mittel |
| W52b | 3 | Messungen/Replies als Dateien (statt Strings). `_planner_lauf` schreibt `.werkstatt/<phase>/messungen/` + `planner/`. | gross |
| W36-2b..6 | 3 | pipeline.py modularisieren: llm.py, audit.py, measurements.py, judge.py, apply.py, parser.py-Rest. | gross (6 Module) |
| W51b-2 | 3 | Resume-Pfad-Pruefungen (`_phase_planner_resume` ruft `_plan_ist_*` nicht). | klein |
| W54e-b | 3 | `patch_ambig` pruefen: ueberlappt es mit W54-g? Wenn ja, entfernen. | klein |
| W56 | 3 | Phasen-Apply prueft alle Zieldatei-Tests pro Unterblock. Pruefen, ob pro Unterblock nur zugehoerige Tests. | mittel |
| W62 | 3 | README und KONVENTION: README-Diagramm ist schematisch, KONVENTION-Diagramm ist textuell. KONSISTENZ pruefen. | klein |

## Merkposten

- W54-f: builder.md 647 Zeilen.
- W57: Prompt-Audit.
- W52a-c: pipeline.py-Modularisierung groesser als 500 Zeilen (ask_llm, audit, execute_commands sind Kern-Infrastruktur).
- W51h-b: W51h greift nur bei parsebarem Plan.
- W51g-b2: Check-Fehler (nicht Parse-Fehler) in letzter_plan_fehler.
- W59-Nachlieferung: 25 Tests rufen apply_code_patches direkt.
- W59-e: `patch_ambig` pruefen (ueberlappt mit W54-g?).
- W59-f: `_phase_main_pfad` -> W50 bug (planner_resume statt neuanlage bei phase_aktiv=false).
- W60b: `docs/ROADMAP.md` bei > 200 Zeilen kuerzen (aktuell 125).
- W60c: `docs/ERLEDIGT.md` bei > 200 Zeilen ins Archiv (aktuell 116).
- W60d: `Bau-Handoff.md` neu (kompakt, < 500 Zeilen).

## Verweise

- `ROADMAP.md` — Uebersicht Phasen/W-Bloecke.
- `ERLEDIGT.md` — Erledigte Bloecke mit Commit/Tests.
- `ARCHITEKTUR.md` — Ziel, Rollen, Luecken.
- `KONVENTION.md` — Ordnerstruktur, Datei-Namen.
- `ROLLEN-AUDIT.md` — Rollen-Stand (Sektion 8, Update 2026-10-18).
