# Offene Bloecke — Werkstatt

Stand: 2026-10-24 (nach M-322..M-343c, RERUN-23/24).
Vorherige Liste: `OFFENE-BLOECKE-ARCHIV-2.md`.

Nur noch **offene** Bloecke. Erledigte stehen in
`ERLEDIGT.md`. Merkposten (M-Nummern) in `MERKPOSTEN.md`.

## Loop-Haertung (M-323b, M-341, M-344)

| Block | Aufwand | Kurz |
|---|---|---|
| M-323b | mittel | `phase_end`-Checkpoint pro logischer Phase. Aktuell: Phasen sind Gruppierung, kein Checkpoint. Nach jeder Phase `_verify_patches(state, phase="phase_end")` + Reflection. |
| M-341 | klein | Explorer ueberspringen, wenn `task_files` gesetzt. Aktuell: Explorer liefert 0 files (M-338 zu strikt), was kosmetisch ist. |
| M-344 | klein | `PROGRESS.md` mit Phasen-Header. Aktuell: pro Task, nicht pro Phase. |

## Pipeline-Abbau (M-345, M-346)

| Block | Aufwand | Kurz |
|---|---|---|
| M-345 | mittel | `pipeline.py` (11.639 Z.) loeschen. Erst wenn `werkstatt/agent.py` keine Kopien mehr braucht (M-231 Zwischenzustand). |
| M-346 | klein | `pipeline._approval_und_human_gate` und `pipeline.load_project_config` in `werkstatt/` verschieben. Letzte Abhaengigkeiten. |

## CLI (M-347)

| Block | Aufwand | Kurz |
|---|---|---|
| M-347 | klein | CLI-Einstiegspunkt fuer den Loop. Aktuell nur `python3 -m werkstatt.loop --project ... --aufgabe ...`. |

## Werkstatt-Entkopplung

| Block | Aufwand | Kurz |
|---|---|---|
| Entkopplung | mittel | `werkstatt/verify.py` importiert `harness.*` und `core.changeapplier.*` (nur Introspektion). Ziel: null Fremd-Imports. Empfohlen: AST-basierte Signatur-Extraktion aus `project_dir`. |

## Baseline

| Block | Aufwand | Kurz |
|---|---|---|
| 5-ruff | klein | ruff 13 Fehler. Kein Runtime-Bug. |
| 5-mypy | klein | mypy 8 Fehler in 2 Dateien. |

## Phase 3c — NEUBAU-Abloesung

| Block | Aufwand | Kurz |
|---|---|---|
| 3c | mittel | Alte Tests, die mit dem alten Code fallen, entfernen. Erkenntnisse in Inventar. |

## Merkposten (alte Session)

| Block | Aufwand | Kurz |
|---|---|---|
| M-162 | klein | „Recovery nach Loop" als eigenstaendigen Pfad messen oder als nicht-existent schliessen. |
| Werkstatt-Entkopplung | mittel | siehe oben. |
| Phase 3.0 | mittel | Rollen-Reduktion (10 -> 8 Rollen). Teils erledigt. |

## Verweise

- `ROADMAP.md` — Phasen-Uebersicht.
- `ERLEDIGT.md` — erledigte Bloecke.
- `MERKPOSTEN.md` — M-Nummern.
- `OFFENE-BLOECKE-ARCHIV-2.md` — archivierte Bloecke (vor 2026-10-24).
- `NEUBAU-ZIELBILD.md` — aktueller Loop als Ziel.
- `Bau-Handoff.md` — aktueller Stand.

## Hooks statt Prompts (M-349..M-352)

| Block | Aufwand | Kurz |
|---|---|---|
| **M-348-Fix** | klein | `plan_ok` nach `run_planner` neu berechnen. Sonst wird das Plan-Human-Gate uebersprungen. |
| **M-349** | klein | `hooks/planner_gate.py` neu: Doku-Tasks ablehnen. `_plan_gate` ruft Hook. Planner-Reflection mit `last_planner_info`. |
| **M-350** | mittel | `planner_gate.py` erweitern: action, task_files, phasen-Pflicht, phase_id. `PLANNER_SYSTEM` halbieren. |
| **M-351** | klein | `loop.py:1167`: toter `post_tool_use`-Aufruf entfernen. |
| **M-352** | klein | `anti_patterns.py`: tot oder aktivieren? Entscheidung offen. |

## Offene Merkposten (unveraendert)

- **M-323b:** Phasen-Checkpoints (`phase_end` pro Phase).
- **M-341:** Explorer ueberspringen bei `task_files`.
- **M-344:** PROGRESS.md mit Phasen-Header.
- **M-345:** pipeline.py loeschen (nach agent.py-Aufloesung).
- **M-346:** pipeline._approval_und_human_gate verschieben.
- **M-347:** CLI-Einstiegspunkt.

## M-350..M-353 (Hooks + Rollback)

| Block | Aufwand | Kurz |
|---|---|---|
| **M-350** | erledigt | planner_gate.py erweitert (5 Checks), PLANNER_SYSTEM gekuerzt. |
| **M-351** | erledigt | no_effect-Patches filtern (builder + loop). |
| **M-352** | offen | Idempotenz NUR bei create + Datei existiert. Tests anpassen. |
| **M-353** | offen | Rollback auf sauberen Tree (git reset --hard + clean). |
| **M-354** | offen | Checkpoint nach jedem Task (Aider-Muster, statt reset --hard). |
