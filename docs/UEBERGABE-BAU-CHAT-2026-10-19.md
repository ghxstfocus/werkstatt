# Uebergabe an den Bau-Chat — 2026-10-19

## Lies zuerst

1. docs/UMBAU-FAHRPLAN.md (der Plan — 7 Phasen)
2. docs/BASELINE-2026-10-19.md (Phase 0, gemessene Zahlen)
3. docs/PHASE1-PLAN.md (Loesch-Liste, wartet auf Abnahme)
4. docs/OFFENE-BLOECKE.md (was offen ist)
5. docs/ERLEDIGT.md (was gebaut wurde)
6. Diese Uebergabe (Stand + Startschuss)

## Stand

Werkstatt-HEAD: 102e433 (Phase 0 + Phase 1 Plan).
Davor: f007bfb (Umbau-Fahrplan), 8c75729 (W61-Pro).
security-ai-HEAD: 5874691 (Phase 21 U1, 13 Tests gruen).
Tests Werkstatt: 1189 (davon 772 in test_pipeline.py).
Katalog: 166 Audit-Kinds.
Rollen: 10 (nicht 6+).
W1-Anker: dd95ed4. Commits seit W1: 194.

Phase 20b (security-ai) ist durch: U1-U4 done,
Sammel-Commit e9c5daa.
Phase 21 (security-ai) U1 ist im Feedback-Loop gebaut,
13 Tests gruen. Der Commit-Review-Judge eskaliert noch:
"Messlage unvollstaendig: Dateiende nicht im Ausschnitt;
ruff/mypy Exit-Codes fehlen."

## Was diese Sitzung geliefert hat

- W61-Pro: Grounding (verify_code, verify_code_kwargs,
  verify_values, Test-Bezug-Check).
- Feedback-Loop: letzter_test_fehler persistiert,
  im Builder-Prompt.
- Parser-Fixes: min 2/4 Einrueckung, Block-Ende per
  Feld-Token, Duplikat-Schwelle 50.
- failed -> pending, Planner-Resume nur bei no_go.
- _post_apply_messung befuellt messungen_nach_apply.
- max_tokens_judge 32768, --allow-empty, D2 pro Paket.
- builder_commit.md (105 Z.) / builder_patch.md (486 Z.).
- Doku: ERLEDIGT, OFFENE-BLOECKE, ARCHITEKTUR, ROADMAP,
  UMBAU-FAHRPLAN.
- Phase 0 (Baseline) + Phase 1 Plan (Loesch-Liste).

## Die zentrale Erkenntnis

Der Phase-21-Deadlock war sieben Glieder, nicht eins:
Parser-Einrueckung, max_tokens_judge, D2-Duplikate,
Planner-Resume, Contract im Prompt, Feedback-Loop,
verify_code.

Das ist im OFFENE-BLOECKE.md dokumentiert. Der naechste
Chat soll NICHT bei einem einzelnen Symptom ansetzen,
sondern beim Umbau.

## Drei Befunde aus Phase 0

A) test_pipeline.py hat 772 von 1189 Tests (65%),
   10.858 Zeilen. Phase 7 betrifft primaer diese Datei.
B) Rollen: 10 statt 6+. Ziel 3 heisst 7 entfernen,
   nicht 3.
C) builder.md: 552 Zeilen. Fehlt im Fahrplan §2/§6.
   Ziel < 300.

Details in docs/BASELINE-2026-10-19.md.

## Was jetzt startet

Phase 1 nach docs/PHASE1-PLAN.md, 5 Charges:

1. Audit-Kinds 166 -> 20.
2. Rollen 10 -> 3.
3. Pipeline-Tests 1189 -> ~100 (Triage A/B/C).
4. verify_code entfernen (Guard: mypy zuerst).
5. Symptom-Sonderfaelle (nach Phase 2/3).

Auf Branch umbau/phase-1, nicht main. Gruen an jeder
Chargengrenze.

## Abnahme-Gate (offen)

Reviewer-Chat muss bestaetigen:
1. Rollen-Ziel 10 -> 3 (statt 6+ -> 3).
2. builder.md 552 -> < 300.
3. Triage-Regel A/B/C statt "rote Tests loeschen".
4. mypy vor verify_code-Loeschung (Charge 4 Guard).

Ohne 1-4: keine Ausfuehrung.

## Was NICHT zu tun ist

- Keine neuen W-Bloecke. Die W-Block-Kultur ist Teil
  des Problems (21 Bloecke in zwei Sitzungen).
- Keine Symptom-Fixes. Jeder Fix muss die Ursache
  adressieren, nicht das Symptom.
- Keine neuen Audit-Kinds. Ziel ist 20, nicht 166.
- Keine neuen Rollen. Ziel ist 3, nicht 10.
- Keine neuen Pipeline-Tests. Ziel ist ~100, nicht 1189.

## Die eine Regel

"Is this needed on >=80% of turns?
 Yes -> pre-load. No -> identifier plus a tool to fetch it."

Jede Datei, jede Funktion, jeder Prompt-Block, jeder
Test, jeder Audit-Kind muss diese Frage beantworten.

## Offene Blocker (P1, nicht Teil des Umbaus)

- Commit-Review-Judge: _build_commit_input liefert
  579 statt 6854 Zeichen, ruff/mypy Exit-Codes fehlen.
  Vollstaendigkeits-Problem, kein Groessen-Problem
  (max_tokens_judge ist 32768).
- Phase 21 U2/U3/U4 (Tests FAILED, ROLLED_BACK, Doku).

Diese Blocker werden durch den Umbau (Phase 2/3)
strukturell geloest — nicht durch weitere Symptom-Fixes.

## Freigabe

Fahrplan braucht Abnahme durch:
1. Bau-Chat (macht die Umsetzung).
2. Reviewer-Chat (prueft die Architektur).

Erste Aktion war Phase 0 (Baseline, erledigt, 102e433).
Naechste Aktion ist Phase 1 Charge 1 — aber erst nach
Reviewer-Antwort zu den vier Gates.
