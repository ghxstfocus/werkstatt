# Phase 2 — Modularisieren (B-Form, Reviewer-Gate 18)

Stand: 2026-10-19
Branch: umbau/phase-2 (wird aus umbau/phase-1 erzeugt).
Status: ABGENOMMEN durch Reviewer-Chat (Gate 18, B).
Basis: docs/UMBAU-FAHRPLAN.md Phase 2, Befunde AF/AG.

## Ziel

pipeline.py 13.686 Z. -> ~11.500 Z.
Vier Module < 500 Z. etabliert.
orchestrator.py (run_pipeline, run_phase,
_phase_main_pfad, ~2.600 Z.) bleibt bis Phase 3.

"Alle Dateien < 500 Z." erst nach Phase 3
(run_pipeline-Zerlegung).

## Reihenfolge (Gate 18a: Risiko, nicht Groesse)

1. audit.py (audit + Katalog, klein, breit genutzt,
   stabile Schnittstelle).
2. prompts.py (_build_commit_input P1-Blocker ->
   Fix wird im kleinen Modul zur Ein-Zeilen-Sache).
3. apply.py (apply_code_patches in Deadlock-Kette,
   aber Signatur-Freeze macht Extraktion neutral).
4. verify.py (Gate 4-neu C: Funktionen bleiben
   funktional bis Phase 3, Extraktion unabhaengig).

Jedes Modul ein eigener Commit. pytest gruen vor
Commit. Kein Refactor im selben Zug (18c).

## Auflage 18b — "Safe" messen, nicht behaupten

Pro Modul VOR Extraktion (Messung ins Charge-
Posting, nicht in den Commit-Body):
- Aufrufer-Zahl in pipeline.py + tests/.
- Zirkulaere Abhaengigkeiten mit pipeline.py
  (state, RunState, _AUDIT_KINDS_BEKANNT,
  verify_*-Aufrufe).
- Phase-3-Beruehrung: welche Funktionen werden in
  Phase 3 geloescht/umgebaut?
- Wenn zirkulaer: Import in Funktionen (lazy) ODER
  gezielte gemeinsame Hilfsdatei. Kein globales
  Helfer-Modul (W52a-Abbruch ist die Warnung).

## Auflage 18c — Signatur-Freeze

Extraktion aendert Signaturen NICHT. Kein Refactor
"im selben Zug" (Kategorie 2, Verhalten identisch).
Wenn eine Signatur waehrend der Extraktion als
falsch auffaellt: Merkposten, eigener Block.

Grund: 1189 Tests sind der Regressions-Beweis fuer
"Code verschoben, nicht geaendert".

## Auflage 18d — Phase-3-Vorbedingung (nicht Gate-18-Scope)

In Phase 3 wird:
- Schritt 3a: run_pipeline in 15-20 Funktionen
  zerlegen (Verhalten identisch, 1189 Tests gruen).
- Schritt 3b: Loop-Umbau (Phase-21-Deadlock-Kette
  strukturell beheben).

Nicht gleichzeitig. 3a ist purer Refactor,
3b ist Verhaltensaenderung.

## Phase-2-Metrik

- pipeline.py 13.686 -> ~11.500 (ehrlich).
- Vier Module < 500 Z.
- 1189 Tests unveraendert gruen nach jedem Commit.
- Keine Signatur-Aenderung.
- Kein Audit-Kinds-Touch.
