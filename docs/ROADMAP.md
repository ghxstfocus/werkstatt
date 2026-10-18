# Roadmap — Werkstatt

Stand: 2026-10-18 (nach W52b C+D+E, W61, W58, Phase 20b)
Uebersicht. Details in `OFFENE-BLOECKE.md` (Todo)
und `ERLEDIGT.md` (Erledigt).

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

Phase 20b blockiert. U1 done (759b9e1),
U2 failed (Lauf 20261018-023047),
U3+U4 pending. Deadlock reproduziert
(Builder sendet falsche Anker). W52b C+D+E
+ W61 sind die Voraussetzung.

## W-Block-Serien

### W1–W35 (Basis, 2026-10-16/17)

Details in `ERLEDIGT.md`.

| Serie | Inhalt | Status | Commits |
|---|---|---|---|
| W1–W11 | Planner-Messung, Unterblock-Isolation, read_file-Zeilenbereich | ✅ | 0e6c881..c3bd4db |
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

Symptom-Behandlung, nicht strukturell.

| Block | Status | Commits | Tests |
|---|---|---|---|
| W51a–h | ⚠️ | 23ce844..8205456 | 1158 |

### W54a/g/h (Builder-Fixes, 2026-10-18) — Symptom

| Block | Status | Commit | Tests |
|---|---|---|---|
| W54a | ⚠️ | d291c37 | 1161 |
| W54g | ⚠️ | 546bc22 | 1165 |
| W54h | ⚠️ | 00483a1 | 1166 |

### Sanierungs-Welle (2026-10-18)

| Block | Titel | Status | Commit | Tests |
|---|---|---|---|---|
| B1-Schritt-1 | Audit-Werkzeug (statische Analyse) | ✅ | 15ce62a | 1169 |
| W51c-fix | Planner nutzt _parse_commands_planner | ✅ | 679251c | 1176 |
| A1b-fix | record_code_entwurf im Builder verdrahtet | ✅ | 800e924 | 1179 |
| T-2 | Integrationstest _post_apply | ✅ | aefecc7 | 1180 |
| B1 | 5 Leichen entfernt | ✅ | 3e1d804 | 1171 |
| W30-fix | Loop-Cap-Audit zentralisiert | ✅ | 5dbbb79 | 1174 |
| W48-A16-b | Katalog-Nutzungs-Test (AST) | ✅ | a074be1 | 1177 |
| W48-A16-b-2 | 36 Katalog-Luecken registriert | ✅ | bc69ffc | 1177 |
| W36-RP | run_pipeline-Integrationstests | ✅ | d0233c8 | 1180 |
| W30-fix-b | max_builder_runden < 1 fail-closed | ✅ | ab0f389 | 1181 |
| W48-A16-b-2-a | solver_max-Kinds zusammengelegt | ✅ | 70df288 | 1182 |
| W36-RP-b | subprocess-Schutz global | ✅ | 904c0de | 1186 |
| W25-planner-md | Skills im Planner-Prompt | ✅ | 041c9a3 | 1189 |

### W52b (On-Demand-Messung, 2026-10-18, in Arbeit)

| Schritt | Titel | Status | Commit | Tests |
|---|---|---|---|---|
| A+B | Messungen als Dateien (state.messungen, gelesene_dateien) | ✅ | 8ef403a | 1189 |
| C | Anker-Check gegen Datei-Inhalte | 🔴 | — | — |
| D | Prompt-Bauer auf Index | 🔴 | — | — |
| E | mess_protokoll deprecated | 🟡 | — | — |

## Offene Bloecke

Detail in `OFFENE-BLOECKE.md`. P1 (akut) hier:

| Block | Kategorie | Symbol | Kurz |
|---|---|---|---|
| W52b C | 3 | 🔴 | Anker-Check gegen Datei-Inhalte |
| W52b D | 3 | 🔴 | Prompt-Bauer auf Index |
| W61 | 3 | 🔴 | Rollen-Sanierung (5 Unterbloecke) |

P2/P3: W52b E, W-Resume-Fail-Kontext, W58,
W59-2, W36-RP-a, W36-RP-b-os, W48-A16-b-2-a-b,
W52a-1, W36-2b..6, W56, W62.

## Ideen

Siehe `docs/IDEEN.md` (2101–2106, Wunschliste,
nicht Plan).

## Verweise

- `OFFENE-BLOECKE.md` — Todo, priorisiert.
- `ERLEDIGT.md` — Erledigte Bloecke mit Commit/Tests.
- `ARCHITEKTUR.md` — Ziel, Rollen, Luecken.
- `KONVENTION.md` — Ordnerstruktur, Datei-Namen.

## Phase 20b — ChangeApplier-Audit-Trail (security-ai)  ✅

U1-U4 done. Commits in security-ai: 759b9e1, ada910a,
572d881, cba0ee3.

- U1: audit_writer-Parameter im ChangeApplier.
- U2: Audit-Log APPLIED nach erfolgreichem Apply.
- U3: Audit-Log FAILED + Auto-Rollback im Fehlerfall.
- U4: Audit-Log ROLLED_BACK in rollback().

## W61 — Rollen-Sanierung  🔨

- W61-Label-Fix (Judge-Loop): done (9ead335).
- W61c (solver_model): done (9ead335).
- W61a (Reviewer 3->1): offen.
- W61b (Judge 2->1): offen.
- W61d (builder.md <300, planner.md <150): offen.

## W52b — On-Demand-Messung  ✅

- A/B: Messungen als Dateien (8ef403a).
- C: Anker-Check gegen Datei-Inhalte (e768353).
- D+E: Prompt-Bauer auf Index, mess_protokoll deprecated
  (e2b3ab3, 3b907a9).

## W58 — Judge-Leer-Antwort  ✅

max_tokens_judge 2048 -> 8192 (e2e8b60). Reasoning-Modell
hatte kein Budget fuer sichtbare Antwort.

