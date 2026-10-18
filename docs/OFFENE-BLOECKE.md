# Offene Bloecke — Werkstatt

Stand: 2026-10-18 (nach W54-h)
Werkstatt-HEAD: 00483a1
security-ai-HEAD: 759b9e1 (Phase 20b-U1, manuell)

## Prioritaet 1 (akut, blockiert Phase 20b)

| Block | Kategorie | Beschreibung | Aufwand |
|---|---|---|---|
| W59 | 3 | Patch nur nach Messung (Read-Cache, mtime). Deadlock in Phase 20b. | mittel (25 Tests anpassen) |
| W61 | 3 | Rollen-Sanierung. builder.md 647, planner.md 297. Redundanz aufloesen. | gross (6+ Bloecke) |

## Prioritaet 2 (strukturell, aus Audit)

| Block | Kategorie | Beschreibung | Aufwand |
|---|---|---|---|
| W55 | 3 | Solver-Fehldiagnose. Prueft Ist-Zustand, nicht Aufgabe. | klein |
| W58 | 3 | Reviewer-Leer-Antwort bei Deadlock. | klein |
| W54-f | 3 | builder.md 647 Zeilen aufraeumen. | mittel |
| W57 | 3 | Prompt-Audit aller Rollen. | mittel |

## Prioritaet 3 (Refactor, nicht blockierend)

| Block | Kategorie | Beschreibung | Aufwand |
|---|---|---|---|
| W52a-1 | 2 | Planner-Funktionen nach planner.py (lazy imports). | mittel |
| W52b | 3 | Messungen/Replies in Dateien. | gross |
| W36-2b..6 | 3 | pipeline.py modularisieren: llm.py, audit.py, measurements.py, judge.py, apply.py, parser.py-Rest. | gross (6 Module) |
| W51b-2 | 3 | Resume-Pfad-Pruefungen. | klein |
| W54-e-b | 3 | patch_ambig pruefen (ueberlappt mit W54-g?). | klein |
| W56 | 3 | Phasen-Apply prueft alle Zieldatei-Tests pro Unterblock. | mittel |

## Merkposten

- W54-f: builder.md 647 Zeilen.
- W57: Prompt-Audit.
- W52a-c: pipeline.py-Modularisierung groesser als 500 Zeilen.
- W51h-b: W51h greift nur bei parsebarem Plan.
- W51g-b2: Check-Fehler (nicht Parse-Fehler) in
  letzter_plan_fehler.
- W59: 25 Tests rufen apply_code_patches direkt —
  muessen state.gelesene_dateien[pfad] = mtime
  vorher setzen.
