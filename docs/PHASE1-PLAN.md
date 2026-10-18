# Phase 1 Plan — Loeschen (Vorbereitung, nicht ausgefuehrt)

Stand: 2026-10-19
Status: PLAN — wartet auf Reviewer-Abnahme.
Basis: docs/BASELINE-2026-10-19.md, docs/UMBAU-FAHRPLAN.md 3.
Regel: Kein Symptom-Fix. Jede Loeschung muss die Ursache
adressieren. Nach jeder Charge pytest, Triage nach unten.

## Reihenfolge (kritischer Pfad)

1. Audit-Kinds 166 -> 20.
2. Rollen 10 -> 3.
3. Pipeline-Tests 1189 -> ~100.
4. verify_code entfernen (NACH mypy-Setup, s. Guard).
5. Symptom-Sonderfaelle (_sim_mtime, --allow-empty, D2).

Nach jeder Charge: Commit auf Branch umbau/phase-1.
Gruen an jeder Chargengrenze. Nicht alles in einem Commit.

## Charge 1 — Audit-Kinds 166 -> 20

Ziel: 20 Kinds, die 80% der Laeufe abdecken.

Vorgehen:
- a) Frequenz messen: audit.jsonl der letzten 5 Laeufe,
  Kinds nach Haeufigkeit.
- b) Top-20 behalten, Rest loeschen.
- c) _KATALOG_SOLL auf 20 setzen.
- d) test_audit_kinds.py (6 Tests) auf 20 umstellen.

Kriterium: pytest gruen, _KATALOG_SOLL == 20.
Commit: "Phase 1a: Audit-Kinds 166 -> 20".

## Charge 2 — Rollen 10 -> 3

Ziel: Plan, Act, Verify. planner.md, builder.md, judge.md.

Loeschen (4 Dateien):
- agents/chaos.md (10 Z.) — Measurement, keine Rolle.
- agents/coverage.md (10 Z.) — Measurement, keine Rolle.
- agents/solver.md (182 Z.) — Recovery, Phase 3 obsolet.
- agents/test_generator.md (18 Z.) — Measurement, keine Rolle.

Konsolidieren (3 -> 2):
- agents/builder.md (552 Z.) + builder_patch.md (486 Z.) +
  builder_commit.md (105 Z.) -> builder.md (< 300 Z., Phase 6).
- In Phase 1: builder_commit.md behalten, builder_patch.md-Inhalt
  nach builder.md mergen, builder_patch.md loeschen.

Ergebnis: agents/ = planner.md, builder.md, judge.md.
(Konsolidierung builder_commit.md -> builder.md in Phase 6.)

Kriterium: pytest gruen, ls agents/*.md | wc -l == 3.
Commit: "Phase 1b: Rollen 10 -> 3".

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
1. test_pipeline.py (772) zuerst. Ziel: 50-60 Integrationstests.
2. test_phase.py (184): private-Funktion-Tests fliegen,
   Verhaltens-Tests bleiben.
3. test_planner.py (80), test_anti_patterns.py (54): je nach
   Ergebnis von Charge 1 triagieren.
4. Rest (redaction, projekt_schema, aggregate,
   pipeline_integration, audit_kinds, conftest_subprocess,
   audit): bleibt bei Verhaltenstests.

Ziel: ~50 Integration + 11 bestehende Produkt-Tests.
Wachstum auf 50 Produkt-Tests in Phase 7.

Kriterium: pytest gruen, Anzahl 90-110, Triage-Log vollstaendig.
Commit: "Phase 1c: Pipeline-Tests triagiert (1189 -> N)".

## Charge 4 — verify_code entfernen (Guard: mypy zuerst)

Vorbedingung: mypy tests/ in always_run aktiv. Sonst entsteht
die Grounding-Luecke zwischen Phase 1 und Phase 5.

Reihenfolge:
1. mypy-Runner in den Verify-Pfad einbauen (Einzeiler).
2. verify_code, verify_code_kwargs aus pipeline.py loeschen.
3. Zugehoerige Tests + Audit-Kinds loeschen.

Kriterium: pytest gruen, mypy-Lauf im Log sichtbar.
Commit: "Phase 1d: verify_code -> mypy tests/".

## Charge 5 — Symptom-Sonderfaelle

Zu loeschen (durch Phase 3/4 obsolet):
- _sim_mtime
- --allow-empty
- D2-Sonderfaelle (Duplikat-Schwelle)
- Planner-Resume (nur bei no_go, nicht bei failed)

Vorbedingung: Phase 3 (Loop neu) muss vorher entworfen sein.
Deshalb Charge 5 optional NACH Phase 2.

Kriterium: pytest gruen.
Commit: "Phase 1e: Symptom-Sonderfaelle entfernt".

## Verbindlich

- Branch umbau/phase-1, nicht main.
- Nach jeder Charge: pytest + Commit.
- Triage-Log docs/PHASE1-TRIAGE.md: je geloeschtem Test
  eine Zeile (Kategorie, Begruendung).
- Keine neuen Tests in Phase 1. Nur loeschen.
- Kein Symptom-Fix. Wenn ein Test rot wird, Ursache finden,
  nicht Test loeschen.

## Nicht Teil von Phase 1

- Modularisierung (Phase 2).
- Loop-Umbau (Phase 3).
- State-Migration (Phase 4).
- mypy-Setup — ausser Charge 4, wo es Guard ist.
- Prompt-Kuerzung (Phase 6).

## Abnahme-Gate

Reviewer-Chat muss bestaetigen:
1. Rollen-Ziel: 3 statt 6+ (Befund B).
2. builder.md 552 -> < 300 (Befund C).
3. Triage-Regel (A/B/C) statt "rote Tests loeschen".
4. mypy-vor-verify_code (Charge 4 Guard).

Ohne 1-4: keine Ausfuehrung.
