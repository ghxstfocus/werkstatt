# Phase 1 Plan — Loeschen (Stand nach Reviewer-Abnahme)

Stand: 2026-10-19
Status: ABGENOMMEN durch Reviewer-Chat (2026-10-19).
Basis: docs/BASELINE-2026-10-19.md, docs/UMBAU-FAHRPLAN.md 3.
Regel: Kein Symptom-Fix. Triage A/B/C (s. Charge 3).

## Chargen (nach Reviewer-Anpassung)

1. Audit-Kinds 166 -> 20. (unveraendert)
2a. Rollen: chaos, coverage, test_generator loeschen
    + Builder-Trio zusammenfuehren. (Gate 1a, jetzt)
2b. solver.md + reviewer.md loeschen. (Gate 1b, nach
    Phase-3-Judge)
3. Pipeline-Tests 1189 -> ~100. Triage A/B/C.
   (unveraendert)
4a. mypy-Runner einbauen, verify_code bleibt.
    (Gate 4, jetzt)
4b. verify_code + verify_code_kwargs loeschen.
    (Gate 4, nach Phase 3)
5. Symptom-Sonderfaelle. (unveraendert, nach Phase 2/3)

Branch: umbau/phase-1. Gruen an jeder Chargengrenze.

## Charge 1 — Audit-Kinds 166 -> 20

Ziel: 20 Kinds, die 80% der Laeufe abdecken.

Reihenfolge (Messen vor Loeschen):
- a) Frequenzmessung: audit.jsonl aus letzten Laeufen,
  Kinds nach Haeufigkeit. Read-only.
- b) Top-20 bestimmen, Ergebnis in docs/PHASE1-AUDIT-TOP20.md.
- c) Top-20 behalten, Rest loeschen.
- d) _KATALOG_SOLL auf 20 setzen.
- e) test_audit_kinds.py (6 Tests) auf 20 umstellen.

Kriterium: pytest gruen, _KATALOG_SOLL == 20.
Commit: "Phase 1a: Audit-Kinds 166 -> 20".

## Charge 2a — Rollen jetzt (Gate 1a)

Loeschen (3 Dateien):
- agents/chaos.md (10 Z.) — Measurement, keine Rolle.
- agents/coverage.md (10 Z.) — Measurement, keine Rolle.
- agents/test_generator.md (18 Z.) — Measurement, keine Rolle.

Konsolidieren (3 -> 1):
- agents/builder.md (552 Z.) + builder_commit.md (105 Z.)
  + builder_patch.md (486 Z.) -> builder.md (Phase 6 Kuerzung
  auf < 300).
- In Phase 1 nur Merge, keine Kuerzung.
- builder_patch.md loeschen nach Merge.

Ergebnis nach 2a: planner.md, builder.md, judge.md,
solver.md, reviewer.md (5 Dateien).
Ergebnis nach 2b: planner.md, builder.md, judge.md (3 Dateien).

Kriterium 2a: pytest gruen, 5 Rollen, builder.md enthaelt
builder_commit + builder_patch.
Commit: "Phase 1b: Rollen 10 -> 5 (Zwischenschritt)".

## Charge 2b — Rollen nach Phase 3 (Gate 1b)

Loeschen (2 Dateien):
- agents/solver.md (182 Z.) — Recovery, Judge ersetzt.
- agents/reviewer.md (56 Z.) — Review, Judge ersetzt.

Vorbedingung: Phase-3-Judge gebaut und getestet.
Grund (Reviewer): solver und reviewer sind keine Stubs.
Ohne Judge-Ersatz entsteht Grounding-Luecke zwischen
Phase 1 und 3.

Ergebnis: 3 Rollen (planner, builder, judge).
Commit: "Phase 1b-2: Rollen 5 -> 3 (nach Phase 3)".

## Charge 3 — Pipeline-Tests 1189 -> ~100

Triage-Regel (verbindlich). Jeder Test faellt in genau eine
Kategorie:
- (A) testet geloeschten Code -> Test loeschen, Zeile in
  docs/PHASE1-TRIAGE.md.
- (B) testet erhaltenes Verhalten -> Test BLEIBT. Wenn rot:
  Bug, Verhalten reparieren — nicht Test loeschen.
- (C) testet Symptom eines entfernten Sonderfalls -> Test
  loeschen, mit Begruendung.

Reihenfolge:
1. test_pipeline.py (772). Ziel: 50-60 Integrationstests.
2. test_phase.py (184): private-Funktion-Tests (A), Verhalten (B).
3. test_planner.py (80), test_anti_patterns.py (54):
   je nach Charge-1-Ergebnis.
4. Rest: Verhaltenstests bleiben.

Ziel: ~50 Integration + 11 bestehende Produkt-Tests.
Wachstum auf 50 Produkt-Tests in Phase 7.

Kriterium: pytest gruen, Anzahl 90-110, Triage-Log vollstaendig.
Commit: "Phase 1c: Pipeline-Tests triagiert (1189 -> N)".

## Charge 4a — mypy einbauen (Gate 4, jetzt)

mypy-Runner als zusaetzliche Pruefung in den Verify-Pfad
einbauen. verify_code BLEIBT in Phase 1.

Kriterium: pytest gruen, mypy-Lauf im Log sichtbar.
Commit: "Phase 1d: mypy-Runner eingebaut (verify_code bleibt)".

## Charge 4b — verify_code loeschen (Gate 4, nach Phase 3)

Vorbedingung: Phase-3-Grounding gebaut (mypy tests/ +
Repo-Map + grep-Pflicht). Dann tragen mypy und Phase-3-
Grounding zusammen die Abdeckung.

Loeschen:
- verify_code (AST)
- verify_code_kwargs (inspect.signature)
- zugehoerige Tests + Audit-Kinds

Kriterium: pytest gruen, mypy-Lauf im Log sichtbar.
Commit: "Phase 1d-2: verify_code entfernt (nach Phase 3)".

## Charge 5 — Symptom-Sonderfaelle (nach Phase 2/3)

Zu loeschen (durch Phase 3/4 obsolet):
- _sim_mtime
- --allow-empty
- D2-Sonderfaelle (Duplikat-Schwelle)
- Planner-Resume (nur bei no_go, nicht bei failed)

Kriterium: pytest gruen.
Commit: "Phase 1e: Symptom-Sonderfaelle entfernt".

## Verbindlich

- Branch umbau/phase-1, nicht main.
- Nach jeder Charge: pytest + Commit.
- Triage-Log docs/PHASE1-TRIAGE.md: je geloeschtem Test
  eine Zeile (Kategorie, Begruendung).
- Keine neuen Tests in Phase 1. Nur loeschen.
- Kein Symptom-Fix.
- Chargen 2b, 4b erst nach Phase 3 (Reviewer-Bindung).

## Nicht Teil von Phase 1

- Modularisierung (Phase 2).
- Loop-Umbau (Phase 3).
- State-Migration (Phase 4).
- Prompt-Kuerzung (Phase 6).
- builder.md-Kuerzung auf < 300 (Phase 6, Gate 2 bestaetigt).

## Abnahme-Status

Reviewer-Chat 2026-10-19:
- Gate 1a: BESTAETIGT (10 -> 3, mit Reihenfolge-Bindung).
- Gate 1b: ALTERNATIVE (reviewer.md bis Phase 3 behalten,
  dann Charge 2b).
- Gate 2: BESTAETIGT (builder.md < 300, Phase 6).
- Gate 3: BESTAETIGT (Triage A/B/C).
- Gate 4: ALTERNATIVE (4a jetzt, 4b nach Phase 3).

Charge 1 (Audit-Kind-Frequenzmessung, read-only) freigegeben.
