# Roadmap — Werkstatt

Stand: 2026-10-19 (nach W61-Pro, Phase 21)
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

Phase 20b done. U1-U4 abgeschlossen in Sitzung
2026-10-18: 759b9e1 (U1), ada910a (U2),
572d881 (U3), cba0ee3 (U4). Der Deadlock
(Builder sendet falsche Anker) wurde durch
W52b C+D+E + W61 + W58 gebrochen.

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

## W61-Pro — Grounding  ✅

verify_code (AST), verify_code_kwargs (inspect),
verify_values (Enums), Test-Bezug-Check.
Feedback-Loop (letzter_test_fehler persistiert).

## Phase 21 — ChangeApplier-Audit-Trail-Tests  🔨

U1 (Tests APPLIED): 13 Tests gruen, im Feedback-Loop
gebaut. Commit-Review-Judge eskaliert (Messlage
unvollstaendig, ruff/mypy fehlen).
U2/U3/U4 offen.

## Offene Deadlock-Kette (dokumentiert)

Siehe OFFENE-BLOECKE.md. Sieben Glieder:
Parser-Einrueckung, max_tokens_judge, D2-Duplikate,
Planner-Resume, Contract im Prompt, Feedback-Loop,
verify_code.

## Phase 3a — run_pipeline zerlegen (laufend, 2026-10-20)

Baseline: pytest 1245 / ruff 17 / mypy 9 / AST 6 / Katalog 167.
(mypy 7->9: M-34, mypy 1.x->2.4.0 strenger bei attr-defined,
keine Verhaltensaenderung, Baseline-NeuMessung 2026-10-21.)

| Block | Status | Inhalt |
|---|---|---|
| 3a-1a | done (1ea4d15) | 8 run_pipeline-Tests. |
| 3a-1c-0 | done (be0cd3f) | 169 Verzweigungen klassifiziert, 2 B1b-Tests. |
| 3a-1c-1a | done (d89d0fa/984f784/0b790e2) | 2 AQ-Tests C4. |
| 3a-1c-1b | done (8110509/72e3459/9665140) | V2 extrahiert, 4 AQ-Tests. |
| 3a-1c-1-b | done (7cb8866/6cd545f/c57d1b1) | 3 UNKLAR-Tests. |
| 3a-1c-2-vorb | done (4769dd9) | Struktur-Tests reduziert. |
| 3a-1c-2a | done (88e3e5c/ecf35a4/ae25e08) | W0a-1/2/3 extrahiert, 7390 geloescht, 9 AQ-Tests. |
| 3a-1c-2b | done (277029f/74ff77d/ac4956f) | W2-Extraktion, _commit_review_w25_loop, 10 Parameter. |
| 3a-1c-3 | done (da67198/bb919d1/d06cf23/fafc5b5) | C0+C1+C2 extrahiert; C6 gestrichen (-> 3b). |
| 3a-1c-4 | done (5762d8e) | _approval_und_human_gate (Variante A, 8 Returns). C8=8819-8854, C9=8855-8898. Return-Bilanz 27/3/2/7/8=47. |
| 3a-2a | done (20f0e7d) | Vorlauf _phase_vorlauf, PhaseVorlaufErgebnis. run_phase 17, _phase_vorlauf 7, Summe 24. |
| 3a-2b | done (8e46062) | _phase_unterblock_loop. |
| 3a-2c | done (3f98364) | _phase_nachlauf. |
| 3a-2d | done (00ffb5e) | _phase_wiederaufnahme. |
| 3a-3 | done (6e440e6) | _phase_main_pfad (641 Z.) in 5 Funktionen zerlegt. Return-Bilanz global 123. |
| 3b | offen | Loop-Umbau (C6, Quality-Gate, Reviewer-Modus). NACH 3.0 + Werkstatt-Entkopplung. |
| 3c | offen | NEUBAU-Abloesung. |

