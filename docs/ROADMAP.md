# Roadmap — Werkstatt

Stand: 2026-10-18
Uebersicht. Details in `OFFENE-BLOECKE.md` (Todo) und
`ERLEDIGT.md` (Erledigt).

## Symbole

| Symbol | Bedeutung |
|---|---|
| ✅ | abgeschlossen, verifiziert (Tests gruen, Commit) |
| 🔧 | abgeschlossen, nachgebessert (manuell oder A16) |
| ⚠️ | abgeschlossen, Symptom-Behandlung (nicht strukturell) |
| 🚫 | blockiert (Deadlock, Review offen) |
| 📋 | geplant, nicht begonnen |
| 🔴 | offen, Prioritaet P1 (akut, blockiert Phase) |
| 🟡 | offen, Prioritaet P2 (strukturell) |
| 🟢 | offen, Prioritaet P3 (Refactor) |

## Phasen

| Phase | Titel | Status | Commit | Tests |
|---|---|---|---|---|
| 1 | Projekt-Schema | ✅ | 406e3cc | — |
| 1b | Validator Fail-closed | ✅ | — | — |
| 2 | Scaffolder | 📋 | — | — |
| 3a-1 | Anti-Pattern-Bibliothek | ✅ | 1ed875a | — |
| 3a-2 | Anti-Pattern-Katalog | ✅ | 8ed6cd0 | — |
| 3b | Builder-Injektion | ✅ | 04012f6 | — |
| 3c-1 | Reviewer + Solver Injektion | ✅ | 4916b01 | — |
| 3c-1b | Reviewer/Solver-Praezisierung | ✅ | 045556e | — |
| 3c-2..17 | (weitere Phasen, im Archiv) | ✅ | — | — |
| 18 | Guardrails | ✅ | — | — |
| 19 | ChangeApplier + Sofort-Massnahmen | ✅ | 163f29b | 1102 |
| 20a | Change-Modell (Audit-Trail-Felder) | 🔧 | 560659a | 1452 |
| 20b | ChangeApplier (Audit-Log, Rollback) | 🚫 | — | — |

## W-Block-Serien

### W1–W35 (Basis, 2026-10-16/17)

Serie von 30 Bloecken. Details in `ERLEDIGT.md`.

| Serie | Inhalt | Status | Commits |
|---|---|---|---|
| W1–W11 | Planner-Messung, Unterblock-Isolation, Message-Check, read_file-Zeilenbereich | ✅ | 0e6c881..c3bd4db |
| W13–W13b | Anker-Zeilenbereich, Ersatz-Pruefung | ✅ | — |
| W23 | Kommunikationswege-Audit | ✅ | c3bd4db |
| W24a | Apply idempotent | ✅ | 4531451 |
| W25 | Skills-Infrastruktur | ✅ | 317b000 |
| W25a-e | Basis-Gate Testanzahl | ✅ | 784dd98..dcda015 |
| W26 | plan.md als Datei | ✅ | 05c817e |
| W27 | Sprint-Contracts | ✅ | 309aeef |
| W28a | Judge-Rolle + Reviewer reduziert | ✅ | f122c39 |
| W28b+c | Review-Loop auf Judge, Antwort-Limit | ✅ | — |
| W29 | Aggregated Phase-Review | ✅ | 0faa69f |
| W30 | Loop-Cap-Konsistenz | ✅ | — |
| W31–W34b | mypy-Fixes, phase_apply_vor_review, .werkstatt/Ignore | ✅ | 79027d8, 87a2fbe |
| W35a-1/2/2d | Planner-Resume + Merge + Suffix-Aufteilung | ✅ | — |

### W36–W47 (Modularisierung, 2026-10-17)

Serie von 12 Bloecken. Details in `ERLEDIGT.md`.

| Serie | Inhalt | Status | Commits |
|---|---|---|---|
| W36 | pipeline.py → state.py, parser.py | ✅ | 5f6e68f |
| W37–W41 | builder.md, alter_plan, Parser-Toleranz, judge.md/planner.md, classify_verdict | ✅ | 28b2ecb..6e4926a |
| W42–W45 | Planner-Resume-Messung, new_file-Idempotenz, Judge-Prompt-Groesse, fehlende Dateien | ✅ | 255191b..e621e24 |
| W47 | Idempotenz-Check vor Gesamt-Review | ✅ | 8aaa861 (1102) |

### W46–W50 (Judge/Planner-Bugs, 2026-10-18)

| Block | Titel | Status | Commit | Tests |
|---|---|---|---|---|
| W46 | Judge-Skip bei Doku-Patches/Phasen | ✅ | 38d3960 | 1113 |
| W48 | Planner-Start bei existierender phase.yaml sperren | 🔧 | 6ba89a6 | 1106 |
| W48-A16 | Katalog +2, Print-Statement | 🔧 | 7c46c7b | 1114 |
| W50 | Planner-Durchfall bei abgeschlossener Phase | 🔧 | 739397f | 1120 |

### W51a–h (Planner-Mess-Mechanik, 2026-10-18) — Symptom

Serie von 8 Bloecken. Symptom-Behandlung, nicht
strukturell. Details in `ERLEDIGT.md`.

| Block | Titel | Status | Commit | Tests |
|---|---|---|---|---|
| W51a–h | Planner-Prompt, Parser-Sperre, COMMAND-Bereinigung, Mess-Mechanik, Loop-Abbruch, Phasen-Groesse, Dedup, Plan+COMMANDs | ⚠️ | 23ce844..8205456 | 1158 |

### W54a/g/h (Builder-Fixes, 2026-10-18) — Symptom

Serie von 3 Bloecken. Symptom-Behandlung, nicht
strukturell.

| Block | Titel | Status | Commit | Tests |
|---|---|---|---|---|
| W54a | builder.md-Regeln doppelte Imports | ⚠️ | d291c37 | 1161 |
| W54g | apply_code_patches Ersatz-Duplikate | ⚠️ | 546bc22 | 1165 |
| W54h | builder.md-Regel Ziel-Klasse | ⚠️ | 00483a1 | 1166 |

### W60 (Doku-Struktur, 2026-10-18)

| Block | Titel | Status | Commit | Tests |
|---|---|---|---|---|
| W60 | Doku-Struktur (KONVENTION, ARCHITEKTUR, ROADMAP, OFFENE, ERLEDIGT) | 🔧 | a70a121.. | 1166 |

## Offene Bloecke

Detail in `OFFENE-BLOECKE.md`. Nur P1 (akut) hier:

| Block | Kategorie | Symbol | Kurz |
|---|---|---|---|
| W59 | 3 | 🔴 | Read-vor-Edit (Deadlock-Mechanismus) |
| W61 | 3 | 🔴 | Rollen-Sanierung (builder.md 647) |

## Ideen

Siehe `docs/IDEEN.md` (2101–2106, Wunschliste, nicht Plan).

## Verweise

- `OFFENE-BLOECKE.md` — Todo, priorisiert.
- `ERLEDIGT.md` — Erledigte Bloecke mit Commit/Tests.
- `ARCHITEKTUR.md` — Ziel, Rollen, Luecken.
- `KONVENTION.md` — Ordnerstruktur, Datei-Namen.
