# Roadmap — Werkstatt

Stand: 2026-10-25 (nach M-472, ADaPT).
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

## Ist-Stand (2026-10-25)

**Werkstatt-HEAD:** efe4ffc (M-472 ADaPT).
**Zielprojekt-HEAD:** f436e42 + ChangeApplier-Code (RERUN-80).
**Baseline:** 1448 / 13 / 11 / 6 / 162.

**Loop-Status:** Ende-zu-Ende gruen nach ADaPT (RERUN-80).
ChangeApplier.apply/rollback implementiert (237 Zeilen),
6/6 Tasks approved, LOOP_RC=0.

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

- `docs/README.md` — Diátaxis-Map (angelegt).
- `AGENTS.md` — Routing (60 Zeilen).
- `README.md` — Einstieg (66 Zeilen).
- `docs/ARCHITEKTUR.md` — System-Map (93 Zeilen).
- `docs/ROADMAP.md` — diese Datei.
- `docs/ERLEDIGT.md` — M-441..M-476 ergaenzen.
- `docs/OFFENE-BLOECKE.md` — pruefen.

### Phase 22: pipeline.py loeschen 🟡 (M-345, OFFEN)

- `pipeline.py` (11.639 Zeilen) loeschen.
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

## Offene Bloecke (P1/P2)

| Block | Prio | Kurz |
|---|---|---|
| M-345 | 🟡 P2 | pipeline.py loeschen (11.639 Zeilen) |
| M-346 | 🟡 P2 | pipeline._approval_und_human_gate verschieben |
| M-347 | 🟢 P3 | CLI-Einstiegspunkt |
| M-341 | 🟢 P3 | Explorer ueberspringen bei task_files |
| M-344 | 🟢 P3 | PROGRESS.md mit Phasen-Header |
| M-323b | 🟡 P2 | phase_end-Checkpoint pro Phase |
| M-162 | 🟢 P3 | Recovery nach Loop messen |

## Verweise

- `ERLEDIGT.md` — erledigte Bloecke
- `OFFENE-BLOECKE.md` — offene Bloecke
- `MERKPOSTEN.md` — M-Nummern
- `ARCHITEKTUR.md` — System-Map
