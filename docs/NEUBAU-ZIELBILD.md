# Neubau-Zielbild — Hybrid mit Funktions-Inventar

Stand: 2026-10-19
Branch: umbau/phase-2
Status: ABGENOMMEN durch Reviewer-Chat (Gate 20 + Rueckfrage 1).
Basis: docs/UMBAU-FAHRPLAN.md, docs/PHASE1-PLAN.md,
       docs/PHASE2-PLAN.md, Reviewer-Gates 19-21h.

## Entscheidung

Option 3 — Hybrid: Neubau mit Funktions-Inventar
und Baseline-Schutz. Nicht Greenfield, nicht
inkrementeller Umbau.

Drei Argumente tragen (unabhaengig von 40-%-Zahl
und unbelegten Kostenschaetzungen):

1. Befunde AG/AF/Q: Option 1 strukturell nicht
   tragfaehig (run_pipeline 1468 Z., 0 Klassen,
   dreifache Rollen-Definition).
2. Spolsky-Prinzip: Option 2 zerstoert Code-Memory
   (1189 Tests, 200+ W-Bloecke, 7-gliedrige
   Deadlock-Kette).
3. Option 3 erhaelt Code-Memory via
   Charakterisierungs-Tests (21b) und
   Baseline-Vergleich (21c).

Kosten-Relation Hybrid vs. inkrementell:
empirisch offen. Kein Entscheidungsgrund,
nur Risiko-Verteilung.

## Nutzer-Anforderungen (verbindlich)

1. Sammelcommit pro Phase (alle Unterbloecke in
   einem Commit/Push, inkl. Doku).
2. Pro Commit (Phasenende): Tests/ruff/mypy
   pruefen und korrigieren, bevor committet wird.
3. Unterbloecke werden vom Planner geplant, aber
   nicht einzeln committet. Waehrend der
   Unterbloecke weich pruefen, am Phasenende
   hart abnehmen.
4. Builder bearbeitet bei Rot automatisch alle
   Probleme (max 3 Versuche), dann Eskalation.
5. Abnahmen "wie die Profis": harte Gates, nicht
   nur Reviewer-Chat.

## Architektur

### 3 Rollen (Stationen im Loop, eigener State)

- Planner: Auftrag + Repo-Map -> Contract mit
  Ankern, Pfaden, Tests. Schreibt
  state.unterbloecke.
- Builder: Contract + Repo-Map + Zieldatei-
  Snippets -> Patch. Wendet Patches an (einziger
  Akteur mit Dateisystem-Schreibrecht).
  Schreibt state.pending_patches.
- Judge: Patch + voller Datei-Inhalt + ruff/mypy
  Exit-Codes -> GO / NO-GO / ESKALATION.
  Threshold 90/100, max 3 Iterationen.

### 4 Subagenten (Werkzeuge, isolierter Kontext)

- Explore: Codebase-Suche. Readonly.
- Debugger: Root-Cause bei rotem Test. Darf
  Patches VORSCHLAGEN (in
  .werkstatt/<run_id>/vorschlaege/), nicht
  anwenden.
- Test-Runner: fuehrt Tests aus. Readonly.
- Verifier: prueft Phasen-Abnahme. Readonly.

### Single-threaded writes (Cognition-Regel)

- Nur der Builder ruft apply_code_patches auf.
- Nur der Builder mutiert state.pending_patches.
- Subagenten schreiben nur in
  .werkstatt/<run_id>/vorschlaege/ (21h).
- Kein paralleles Schreiben in Projektdateien
  (CooperBench).

## Loop

### Unterblock-Ebene (weich, iterativ)

1. Builder liefert Patch.
2. apply_code_patches.
3. pytest auf betroffene Datei + ruff + mypy.
4. Bei Rot: Builder korrigiert (max 3 Versuche,
   VERSCHIEDENE Ansaetze, nicht derselbe Patch 3x).
5. Nach 3x rot: Eskalation an Menschen mit
   konkretem Befund (Test-Output, Patch-Diff,
   Fehlerkette).
6. Bei gruen: naechster Unterblock.

Kein Commit auf dieser Ebene.

### Phasen-Ebene (hart, einmalig)

1. Alle Unterbloecke done.
2. Voller pytest-Lauf.
3. ruff/mypy auf Zieldateien.
4. Deterministisches Gate: alle Unterbloecke
   done? Alle Patches in state.pending_patches?
   Tests gruen? ruff/mypy Exit 0?
5. Wenn rot: zurueck zum Builder (max 3 auf
   Phasen-Ebene), dann Eskalation.
6. Commit-Review-Judge: Commit-Message gegen
   tatsaechliche Aenderungen.
7. Sammelcommit + Push + Doku.

Reihenfolge: erst Code-Gates (deterministisch),
dann LLM-Review (Judge). Nicht umgekehrt.

## Grounding

- Repo-Map: tree-sitter + PageRank, 1024 Tokens
  Default. Im Planner- und Builder-Prompt.
  Neues Modul werkstatt/repo_map.py.
- grep-Pflicht im Builder-Prompt: "Bevor du eine
  Funktion aufrufst, grep sie."
- mypy auf tests/ und pipeline.py als Gate
  (nicht als Measurement).
- verify_values behalten (Enum-Checks, die mypy
  nicht kann).
- verify_code_kwargs behalten (API-Signaturen,
  die mypy wegen **kwargs nicht faengt).
- verify_code (Symbol-Existenz): pruefen, ob
  mypy + AST-Fallback das abdecken. Wenn ja:
  faellt.

## State

state.json mit JSON-Schema, ein Format, ein Parser:

{
  "run_id": "...",
  "phase": {"id": "21", "status": "in_progress"},
  "unterbloecke": [...],       // Planner schreibt
  "pending_patches": [...],    // Builder schreibt
  "pruefung": {...},           // Verifier/Judge schreibt
  "phasen_abnahme": null       // Judge schreibt
}

Single-writer pro Feld, multi-reader. Das ist die
strukturelle Konsequenz aus Befund Q (drei Quellen,
keine Gewinner-Regel).

## Datei-Struktur

werkstatt/
  orchestrator.py      # run_phase, run_pipeline (< 400 Z.)
  apply.py             # apply_code_patches (< 300 Z.)
  verify.py            # verify_values, mypy-Runner (< 200 Z.)
  prompts.py           # _build_commit_input, _build_judge_input (< 300 Z.)
  audit.py             # audit(), JSONL-Writer, 20 Kinds (< 200 Z.)
  phase.py             # state.json, JSON-Schema (< 300 Z.)
  repo_map.py          # tree-sitter + PageRank (NEU, < 200 Z.)
  hooks.py             # PreToolUse-Gates (NEU, < 150 Z.)
  pipeline.py          # Facade, main() (< 100 Z.)

agents/
  planner.md           # < 150 Z.
  builder.md           # < 300 Z.
  judge.md             # < 150 Z.
  subagents/
    explore.md         # < 80 Z.
    debugger.md        # < 80 Z.
    test_runner.md     # < 60 Z.
    verifier.md        # < 80 Z.

skills/ (10 bestehende SKILL.md bleiben)

## Tests

50 Integration + 50 Produkt, von Anfang an.
Die 1189 alten Tests bleiben bis zum Ende des
Neubaus gruen (Baseline). Dann: alte Tests fallen
mit dem alten Code.

Jeder alte Test, der einen Bug dokumentiert, wird
zu einem neuen Integration-Test oder einer Regel
im Neubau (Charakterisierung, 21b).

## Gates (Reviewer, 21a-21h)

21a Funktions-Inventar VOR Neubau.
21b Charakterisierungs-Tests VOR Neubau.
21c Sammel-Commit + Baseline-Vergleich.
21d Builder-Korrektur max 3 (verschiedene Ansaetze).
21e Subagenten-Isolation (Vorschlag ja, Anwendung nein).
21f Rollen-Trennung (Planner, Builder, Judge).
21g State-Schema vor Neubau festgelegt.
21h Subagenten-Vorschlags-Kanal
    (.werkstatt/<run_id>/vorschlaege/).

## Reihenfolge

Phase A — Inventar (21a + 21b, 2-3 Tage, read-only).
Phase B — Ziel-Struktur fein (1 Tag, Abnahme).
Phase C — Neubau (2-3 Wochen).
Phase D — Baseline-Abloesung (alte Tests + alter
          Code fallen).

## Nicht Teil des Neubaus

- Commit-Review-Messlage (P1): strukturell durch
  neuen Judge geloest.
- Phase 21 U2-U4, U1-Smoke: nach Neubau erneut
  messen.
- Alte 1189 Tests: fallen mit dem alten Code,
  Erkenntnisse wandern ins Inventar.

## Was Phase 1+2 geliefert haben (bleibt gueltig)

- Phase 1: Rollen 10 -> 8, Triage 1186/1189,
  Audit-Kinds 166 unveraendert (Phase-3-Material).
- Phase 2 (Plan): Reihenfolge audit -> prompts ->
  apply -> verify (wird im Neubau anders geloest,
  aber die Modul-Grenzen bleiben).

Die Phase-1/2-Artefakte sind Grundlage fuer 21a
(Inventar).
