# Uebergabe an Phase-3a-Chat — 2026-10-19

## Lies zuerst (in dieser Reihenfolge)

1. docs/NEUBAU-ZIELBILD.md — Ziel-Architektur.
2. docs/NEUBAU-INVENTAR.md — 191 Funktionen klassifiziert
   + N1-N4 + R-3.
3. docs/NEUBAU-ENTFERNUNG.md — was im Zielsystem
   verschwindet (Phase 3b/3c/6).
4. Diese Uebergabe (Stand + Startschuss).

## Stand

Branch: umbau/phase-2, gepusht (origin/umbau/phase-2).
HEAD: ca56520 (3a-1c-2b-doc: Merkposten W2-Extraktion).
main: 3d71aad (43 Commits hinter umbau/phase-2, nicht
gepusht).

Baseline (2026-10-20, Ende Session):
- pytest: 1245 passed.
- ruff: 17 errors.
- mypy: 7 errors.
- AST-Test: 6 passed.
- Katalog: 167 (_KATALOG_SOLL).

Abgeschlossene Phase-3a-Bloecke:
- 3a-1a (8 Tests, 1ea4d15).
- 3a-1c-0 (be0cd3f).
- 3a-1c-1a (d89d0fa + 984f784 + 0b790e2).
- 3a-1c-1b (8110509 + 72e3459 + 9665140).
- 3a-1c-1-b (7cb8866 + 6cd545f + c57d1b1).
- 3a-1c-2-vorbereitung (4769dd9).
- 3a-1c-2a (88e3e5c + ecf35a4 + ae25e08).
- 3a-1c-2b-doc (ca56520, Merkposten).

Offen:
- 3a-1c-2b (W2-Extraktion, 14 Regressionen im 1. Versuch,
  Merkposten mit Fallstricken).
- 3a-1c-3 (C0+C1+C2+C6).
- 3a-1c-4 (C8+C9).
- 3a-2 (run_phase).
- 3a-3 (_phase_main_pfad, Deadlock).
- 3b (Loop-Umbau).
- 3c (NEUBAU-Abloesung).

## Was seit Phase 0 passiert ist

Phase 1 (Loeschen): Rollen 10 -> 8 (chaos, coverage weg).
Triage 1186 def / 1189 cases, keine Loeschung (Baseline
fuer Phase 3). Baseline-Doku, Phase-1-Abschluss.

Phase 2 (Modularisieren): pipeline.py 13.686 -> ~11.262.
9 Module in werkstatt/:
- audit.py (127): audit, Katalog.
- hard_rules.py (711): 10 HARD_RULES-Konstanten.
- prompts.py (278): 8 Prompt-Bauer.
- measurement.py (302): 8 Mess-Block-Funktionen.
- commit_input.py (400): 11 Commit/Judge-Input.
- subprocess_env.py (31): subprocess_env.
- apply.py (405): apply_code_patches + _shift_lines.
- verify.py (342): 5 verify-Funktionen.

Phase 2.5: Measurement.timeout -> timeout_s (BY).
P1-Fix: _post_apply_messung fail-closed bei mkdir-Fehler
(BR/P1-b). Katalog 166 -> 167.

Phase 3a-1a: 8 run_pipeline-Charakterisierungs-Tests.
Vorhanden: 3 echte run_pipeline-Tests (test_t1/t2/t3).
Gesamt: 11 run_pipeline-Testfunktionen.

## Phase-3-Plan (aktualisiert nach Befund CI/CG)

3a-1a: ✓ (8 Tests, 11 run_pipeline gesamt).
3a-1b: GESTRICHEN. Deadlock-Kette ist nicht in
  run_pipeline (Befund CI/CG). Sie lebt in
  _phase_main_pfad + _planner_lauf +
  builder_reply_mit_command_loop + apply + verify.
3a-1c-0: C-CN-3 (Verzweigungs-Klassifikation,
  dann B1b 2 Tests oder "0 kritisch").
3a-1c-1..4: Zerlegung Rest-Zerlegung run_pipeline
  (144 Verzweigungen, 1471 Z.).
3a-2: run_phase (528 Z.).
3a-3: _phase_main_pfad (641 Z., Deadlock-Test).
3b: Loop-Umbau (eigener Block).
3c: NEUBAU-Abloesung.

## Naechster konkreter Schritt: 3a-1c-0

Reviewer-Auflage C-CN-3:
1. Liste der nicht-getesteten Verzweigungen in
   run_pipeline (Z. 7607-9077).
2. Klassifikation pro Verzweigung:
   kritisch / unkritisch / Fail-Fast-Pfad.
3. B1b = 2 Tests fuer die kritischsten ODER
   "0 kritisch" mit Zitat.
4. C-CN-3 MUSS im 3a-1c-0-Commit-Body geliefert
   werden. Wenn fehlt: 3a-1c-1 startet nicht.

## Offene Reviewer-Auflagen

- C-CN-3 (siehe oben).
- B1b (2 Tests oder "0 kritisch").
- ruff/mypy-Rest (17 ruff, 7 mypy): Phase 5.
  Davon 3 import-not-found (MYPYPATH), 2 R-A
  (RunState.messungen_nach_apply fehlt), 2
  list/set (Annotation-only).

## Reviewer-Muster dieser Sitzung (Warnung)

Fuenf Messfehler des Reviewers, alle zum selben
Muster "Zahl aus Chat-Gedaechtnis":
- 192 -> 144 Verzweigungen (grep zaehlt if in
  Strings).
- "193" -> 191 Funktionen (Kategorie-Wechsel
  statt Fehlen).
- 4% -> 28,7% NEUBAU (falsche Kategorie-Annahme).
- "0 echte Tests" -> 3 (falsche Datei-Reichweite).
- "8 Tests" -> 5 -> 3 (Aufruf-Tiefe nicht gezaehlt).

Konsequenz fuer den neuen Chat: Jede Zahl, die in
einen Reviewer-Block geht, VORHER mit grep/ast/
pytest --collect-only messen. "Plausibel" ist kein
Beleg.

## Bau-Regeln (unveraendert)

- Ein Ausfuehrungsblock pro Nachricht, warten auf
  Ausgabe, dann naechster Block.
- Reviewer-Bloecke als Kopierblock, klar markiert.
- Kein Code-Touch bis Freigabe.
- Heredoc-Bloecke einzeln, nicht mit Prosa drumherum.
- ruff/mypy-Baseline pro Commit dokumentieren (18g).
- Signatur-Freeze bei Zerlegung (18c).
- Kein Misch-Commit (Test vs. Fix vs. Zerlegung).

## Doku-Dateien

- docs/NEUBAU-ZIELBILD.md (Ziel).
- docs/NEUBAU-INVENTAR.md (191 Fkt + N1-N4 + R-3).
- docs/NEUBAU-ENTFERNUNG.md (Register).
- docs/PHASE1-PLAN.md (Phase-1-Archiv).
- docs/PHASE2-PLAN.md (Phase-2-Archiv).
- docs/UEBERGABE-BAU-CHAT-2026-10-19.md (Phase-0/1).
- docs/UEBERGABE-3A-2026-10-19.md (diese Datei).

## Was NICHT zu tun ist

- Keine neuen Audit-Kinds (Ziel 20, aktuell 167).
- Keine neuen Rollen (Ziel 3, aktuell 8).
- Keine Symptom-Fixes.
- Kein 3b im selben Zug wie 3a.
- Keine Zerlegung ohne Charakterisierung (Befund AQ).
