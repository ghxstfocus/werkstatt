# Offene Bloecke — Werkstatt

Stand: 2026-10-25 (nach M-476, RERUN-80).
Vorherige Liste: `OFFENE-BLOECKE-ARCHIV-2.md`.

Nur **offene** Bloecke. Erledigte stehen in `ERLEDIGT.md`.
Merkposten (M-Nummern) in `MERKPOSTEN.md`.

## Loop-Haertung

| Block | Aufwand | Kurz |
|---|---|---|
| M-323b | mittel | `phase_end`-Checkpoint pro logischer Phase. Nach jeder Phase `_verify_patches(state, phase="phase_end")` + Reflection. |
| M-341 | klein | Explorer ueberspringen, wenn `task_files` gesetzt. |
| M-344 | klein | `PROGRESS.md` mit Phasen-Header (pro Phase, nicht pro Task). |

## Pipeline-Abbau

| Block | Aufwand | Kurz |
|---|---|---|
| M-345 | mittel | `pipeline.py` (11.639 Z.) loeschen. Erst wenn `werkstatt/agent.py` keine Kopien mehr braucht. |
| M-346 | klein | `pipeline._approval_und_human_gate` und `pipeline.load_project_config` in `werkstatt/` verschieben. |

## CLI

| Block | Aufwand | Kurz |
|---|---|---|
| M-347 | klein | CLI-Einstiegspunkt fuer den Loop. |

## Werkstatt-Entkopplung

| Block | Aufwand | Kurz |
|---|---|---|
| Entkopplung | mittel | `werkstatt/verify.py` importiert `harness.*` und `core.changeapplier.*` (nur Introspektion). Ziel: null Fremd-Imports. |

## Baseline

| Block | Aufwand | Kurz |
|---|---|---|
| 5-mypy | klein | mypy 11 Fehler in 2 Dateien (Baseline 11). |

## Phase 3c — NEUBAU-Abloesung

| Block | Aufwand | Kurz |
|---|---|---|
| 3c | mittel | Alte Tests, die mit dem alten Code fallen, entfernen. |

## Merkposten

| Block | Aufwand | Kurz |
|---|---|---|
| M-162 | klein | „Recovery nach Loop" messen oder schliessen. |
| M-388 | klein | UI-Testing via Chrome DevTools. |
| M-389 | klein | Doku-Pflege im Loop. |

## Verweise

- `ROADMAP.md` — Phasen-Uebersicht.
- `ERLEDIGT.md` — erledigte Bloecke.
- `MERKPOSTEN.md` — M-Nummern.
