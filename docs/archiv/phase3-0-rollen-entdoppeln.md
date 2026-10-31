# Phase 3.0 — Rollen-Definitionen entdoppeln (Vorbedingung Phase 3)

Stand: 2026-10-19
Status: ABGENOMMEN durch Reviewer-Chat (Gate 14, 5 Auflagen).
Basis: Befund Q (Body + HARD_RULES + Code dreifach),
       docs/UMBAU-FAHRPLAN.md Phase 3.
Vorbedingung: Charge 2a abgeschlossen (Rollen 10 -> 6).

## Warum

Befund Q: Verhalten einer Rolle wird an drei Stellen
definiert (Body, HARD_RULES, Code-Checker). Woertliche
Doppelung (Beispiel: builder.md "MESSWERTE IM PROMPT"
vs. HARD_RULES_BUILDER B1-B3). Symptom: Modell kann
nicht erkennen, welche Regel gewinnt, wenn drei
Versionen derselben Aussage existieren. W51-Serie,
drei Integrations-Luecken (W51c, A1b, W30) sind
Symptome dieser Ursache.

## Ziel (Gate 13 C, bestaetigt)

Pro Rolle eine Aussage = eine Quelle:

1. Body (agents/<rolle>.md): Rollenbeschreibung,
   Format-Beispiele, Prozess. Keine Regelnummern.
   Keine Wiederholung von HARD_RULES-Aussagen.
2. HARD_RULES: zwei Sorten, klar getrennt.
   (i) pruefbare Regeln -> Code-Checker im
       Verify-Pfad, HARD_RULES-Eintrag verweist
       auf den Checker (z.B. "B1: siehe
       check_messwerte_einzige_quelle").
       NICHT den Wortlaut doppeln.
   (ii) nicht pruefbare Regeln -> docs/ROLLEN-DOKU.md,
        NICHT im Prompt. Prompt-Entscheidung faellt
        Modell-Instinkt oder Integrationstest.
3. Code: prueft deterministisch, was in (i) als
   Regel formuliert ist.

## Scope (3 Rollen, Phase 3.0)

- planner
- builder
- judge

solver, reviewer, test_generator: 3.0-Lite in Phase 3b,
wenn sie sterben (Befund J: load_agents-Pflicht fuer
reviewer + test_generator bis Phase 3).

Aufwand: 1-2 Tage fuer 3 Rollen. Wenn es fuer 6 Rollen
in 1-2 Tagen nicht geht: Scope auf 3 Rollen reduzieren.

## Auflagen (Reviewer Gate 14)

### 14a — Messbares Ergebnis

Pro Rolle ein Test `test_<rolle>_keine_doppelten_aussagen`:
- AST- oder String-Vergleich: Body-Aussage vs.
  HARD_RULES-Aussage (gleiches Subjekt + Objekt)
  -> schlaegt an.
- Erlaubte Ausnahme: expliziter Verweis
  ("siehe HARD_RULES B1").
Ohne diesen Test ist "entdoppelt" eine Behauptung.

### 14b — Pruefbare Regeln -> Code-Checker IM SELBEN BLOCK

"Wo pruefbar: Code-Checker" heisst: der Checker wird
in Phase 3.0 gebaut und getestet, nicht in einer
spaeteren Phase. Kein "Code-Checker folgt in Phase 5".

### 14c — Nicht pruefbare Regeln -> Integrationstest ODER Doku

Wenn eine Regel aus dem Prompt entfernt wird, MUSS:
- ein Integrationstest existiert bereits, der das
  Verhalten absichert;
- ODER die Regel wird als Merkposten "Verhaltens-
  Risiko" gefuehrt und in Phase 3 (Loop-Umbau)
  gemessen.

### 14d — Reihenfolge zu Gate 12 (Builder-Trio-Merge)

Builder-Trio-Merge (Gate 12, Option 3) kommt NACH
Phase 3.0, nicht davor. Erst entdoppeln, dann
mergen. Dann ist der gemergte builder.md per
Konstruktion dreifach-frei.

### 14e — Rollback-Kriterium

Revert Phase 3.0, wenn:
- in Phase 20 nach 3.0 die no_go-Loops gegenueber
  Baseline zunehmen, ODER
- ein pruefbarer Checker einen bisher gruenen
  Patch rot macht (False-Positive).

Rollen-Definitionen bleiben dann wie heute,
Neubewertung.

## Reihenfolge

1. Charge 2a (Phase 1): chaos.md + coverage.md loeschen.
   Rollen 10 -> 8 (Uebergang).
2. Charge 3 (Phase 1): Tests triagieren 1189 -> ~100.
3. Charge 4a (Phase 1): mypy einbauen, verify_code bleibt.
4. Phase 2 (Modularisieren): pipeline.py -> 6 Module.
5. Phase 3.0: Rollen-Definitionen entdoppeln (3 Rollen).
   Mit 14a-14e.
6. Phase 3: Loop neu. Erst danach Builder-Trio-Merge,
   solver/reviewer/test_generator sterben.

## Phase-1-Metrik (bestaetigt)

- Rollen 10 -> 8 (nach Charge 2a).
- Keine Audit-Kinds geloescht.
- mypy eingebaut, verify_code bleibt.
- Tests 1189 -> ~100.
- Katalog 166 unveraendert.

"Rollen-Definitionen entdoppelt" ist Phase-3-Ziel,
nicht Phase-1.
