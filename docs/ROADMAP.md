# Roadmap — Werkstatt

Stand: 2026-10-24 (nach M-360, RERUN-38).
Uebersicht. Details in `OFFENE-BLOECKE.md` (Todo)
und `ERLEDIGT.md` (Erledigt).

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

## Ist-Stand (2026-10-24)

**Werkstatt-HEAD:** 57e1472 (Doku nach M-360).
**Zielprojekt-HEAD:** 2a0a284 (RERUN-38, auf f1bd193).
**Baseline:** 1411 / 13 / 8 / 6 / 162.

**Loop-Status:** strukturell fertig nach M-352..M-360.
RERUN-38 ist der erste vollstaendige Durchlauf seit
RERUN-23 (8/8 Tasks, LOOP_RC=0, echte Aenderung im
Zielprojekt: `harness/audit/writer.py`, Owner-Check).

**Was seit dem letzten Roadmap-Stand passiert ist:**

- RERUN-33..37 zeigten fuenf strukturelle fail-opens
  (M-352, M-353, M-355, M-355b, M-356..M-360). Alle behoben.
- Der Loop wurde erst durch diese Fixes wirklich
  Ende-zu-Ende nutzbar.
- Der Zielbild-Loop (5 Rollen + 2 Hooks) ist verifiziert.

## Phasen (aktuell)

| Phase | Titel | Status | Beweis |
|---|---|---|---|
| 1 | Projekt-Schema | ✅ | 406e3cc |
| 1b | Validator Fail-closed | ✅ | — |
| 3a-1 | Anti-Pattern-Bibliothek | ✅ | 1ed875a |
| 3a-2 | Anti-Pattern-Katalog | ✅ | 8ed6cd0 |
| 3c-1 | Reviewer + Solver Injektion | ✅ | 4916b01 |
| 18 | Guardrails | ✅ | — |
| 19 | ChangeApplier + Sofort-Massnahmen | ✅ | 163f29b |
| 20a | Change-Modell (Audit-Trail-Felder) | ✅ | 560659a |
| 20b | ChangeApplier (Audit-Log, Rollback) | ✅ | 759b9e1..cba0ee3 |
| **Loop-Neubau** | **Strangler-Fig + 5 Rollen + 2 Hooks** | **✅** | **RERUN-38, 1411 Tests** |
| **M-352..M-360** | **5 fail-opens behoben** | **✅** | **RERUN-38, 8/8 Tasks** |

## Loop-Neubau — verifizierte Architektur

Der Loop hat **5 Rollen** und **2 Hooks** (Detail in
`NEUBAU-ZIELBILD.md`):

- **Explorer** (`werkstatt/explorer.py`) — read-only,
  `key_files`.
- **Planner** (`werkstatt/planner.py`) — JSON-Plan mit
  `phasen`-Pflicht (M-323c), `action` und `task_files`.
- **Builder** (`werkstatt/builder.py`) — search/replace,
  Zieldatei deterministisch aus `task_files` (M-337,
  M-352, M-360).
- **Reviewer** (`werkstatt/reviewer.py`) — Bug-Check,
  pytest ist das letzte Wort (M-343c, M-359).
- **Human-Gate** (`_human_gate` in `loop.py`) — fail-closed.

**Hooks:**
- `pre_tool_use` — AST-Import-Validierung (M-334a).
- `simplify` — Komplexitaets-Check.

**Rollback:** M-356, immer auf `start-HEAD` bei
`LOOP_RC != 0`.

## Offene Bloecke (P1/P2/P3)

Detail in `OFFENE-BLOECKE.md`. Aktuell offen:

| Block | Kategorie | Symbol | Kurz |
|---|---|---|---|
| M-361 | 3 (Tests) | 🟡 | Test fuer M-355b (run_builder=False -> return 1). |
| M-362 | 3 (Tests) | 🟡 | Test fuer M-360 (create + Datei fehlt -> anlegen). |
| M-363 | 3 (Doku) | 🟢 | Doku-Pflege Baseline/HISTORISCH. |

Aeltere offene Bloecke (M-162, M-231-Kontext, M-338,
M-345..M-351, M-354) sind in `OFFENE-BLOECKE.md`
dokumentiert und bleiben P2/P3.

## Naechste Schritte

1. **M-361/M-362:** Tests fuer die ungetesteten Fixes
   M-355b und M-360.
2. **RERUN-39** mit create-lastiger Aufgabe — M-360
   gezielt verifizieren (bisher hatte kein RERUN einen
   echten `create`-Task mit fehlender Datei).
3. **M-363:** Baseline-Doku aufraeumen, HISTORISCH-
   Markierungen konsolidieren.
4. **M-323b/M-344:** Phasen-Checkpoints und
   `PROGRESS.md`-Header (kosmetisch, P3).

## Archiv (abgeloest)

Die W-Block-Serien (W1..W62) und die alten Phasen
3b/3c sind **Archiv** — sie beschreiben die
Vor-Umbau-Architektur (Planner, Builder, Solver,
Judge, Reviewer, Human-Gate). Der Solver und Judge
existieren im Loop-Neubau nicht mehr. Details in
`ERLEDIGT.md` und `ARCHITEKTUR.md` (Abschnitt
"Ziel-Architektur — historisch").

## Verweise

- `NEUBAU-ZIELBILD.md` — aktueller Loop als Zielbild.
- `ARCHITEKTUR.md` — technische Architektur (teils historisch).
- `OFFENE-BLOECKE.md` — Todo, priorisiert.
- `ERLEDIGT.md` — erledigte Bloecke mit Commit/Tests.
- `KONVENTION.md` — Ordnerstruktur, Datei-Namen.
- `Bau-Handoff.md` — Zwischenstaende, RERUN-Ergebnisse.
