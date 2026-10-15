# Bau-Handoff — Archiv

Historische Eintraege, die nicht mehr in den aktiven
Bau-Handoff gehoeren. Aufbewahrt fuer Nachvollziehbarkeit.

Letzte Aktualisierung: 2026-10-15 (Konsolidierung).

## Warum dieses Archiv

Der aktive Bau-Handoff (Bau-Handoff.md) soll kurz und
aktuell sein. Alles, was laenger als zwei Sessions alt
ist oder aus der Zwei-Webchat-Aera stammt, liegt hier.

Bei Bedarf: dieses Archiv lesen, Eintraege suchen,
Kontext verstehen. Kein Neuschreiben.

================================================================
A. PROBEBETRIEB-CHRONIK (29 bis 83)
================================================================

Ausfuehrliches Beobachtungs-Protokoll 29-40 siehe
docs/PROTOKOLL-29-40.md. Nachfolgend die Kurzfassung
aller Probebetriebe, die in der Zwei-Webchat-Aera
und der Werkstatt-Aera gelaufen sind.

## 2026-10-12 bis 2026-10-13 (Probebetriebe 29-83)

  PB-29: Fail (Anker 0x). Ausschnitt-Bug entdeckt.
  PB-30: Fail (Livelock, 5x NO-GO). COMMAND-Loop fehlt.
  PB-31: Fail (Anker 0x). Prompt einmal gebaut.
  PB-32: Fail (builder_command_deadlock).
  PB-33: Fail (Anker 0x). read_file ignoriert.
  PB-34: Fail (Anker 0x). GEMESSENER INHALT fehlt.
  PB-35: Fail (Anker 0x). GEMESSENER INHALT ignoriert.
  PB-36: Fail (Anker 0x). Automatik + GEMESSENER INHALT
         greifen nicht.
  PB-37: Fail (Anker 0x). Audit-Debug zeigt: IP-Redaction
         zerstoert Anker. WURZEL GEFUNDEN.
  PB-38: Fail (Commit-NO-GO). Anker trifft! Testzahl fehlt.
  PB-39: Fail (Commit-NO-GO). Rechte-Problem + Testzahl.
  PB-40: ERFOLG. Commit 3ccb883 in security-ai.
  PB-41: Doku. Handoff + Protokoll 29-40 neu.
  PB-42: Chore. .gitignore um *.alt ergaenzt.
  PB-43: ERFOLG. Auflage 2191-R. HEAD 87092f8.
  PB-44: Doku. Handoff auf PB-43-Stand.
  PB-45: Style. ruff I001 in tests/ behoben.
         KORREKTUR (PB-75): War unvollstaendig.
  PB-46: Doku. Handoff Abschluss-Update PB-45.
  PB-47: Fix. reviewer.md Verweis HR4 -> B5.
  PB-48: Refactor. Audit-Debug-Felder reduziert (2194-M).
  PB-49: Feature. GEMESSENER INHALT + CODE-PATCHES
         in commit_input (2191-R2).
  PB-50: Feature. Fail-closed bei leerem mess_protokoll
         in Phase 2 (2191-R2b).
  PB-51: Doku. Handoff auf PB-50.
  PB-52: Fix. reviewer.md Body an R7 angeglichen
         (2191-R3).
  PB-53: Doku. Handoff-Update 2199-Zwischenstand.
  PB-54: Doku. Handoff-Update 2199a als Auflage.
  PB-55: Doku. Handoff 2199 abgeschlossen, 2183 vor.
  PB-56: Feature. pipeline_ende mit llm_calls
         (2183-P4-Log).
  PB-57: Feature. pipeline_ende im Deadlock-Pfad.
  PB-58: Doku. Handoff 2199 R7 bestaetigt.
  PB-59: Feature. pipeline_ende im basis_gate_
         nach_apply-Pfad (2183-P4-Log2).
  PB-60: Doku. Handoff P4-Log2 + Worst-Case.
  PB-61: Refactor. Zentraler pipeline_ende-Wrapper
         (2183-P4-Log2, endgueltig).

  HINWEIS (2026-10-14): Die Tags probebetrieb-62
  bis probebetrieb-83 wurden fuer manuelle Bau-Sessions
  vergeben. Das war semantisch falsch und wurde
  entfernt. Die Commits bleiben (Arbeit ist real).

  M-62: Feature. run_id im Audit (2200a).
  M-63: Feature. Audit-Aggregator (2200).
  PB-64: Chore. projects/*.memory.yaml ignorieren.
  PB-66: Fix. R7-Phase-2-Toleranz + Aggregator
         mypy/ruff (2199-R7-P2).
  PB-67: Doku. Handoff auf PB-66.
  PB-68: Feature. Recovery-Zustand + Prompt-Block
         (2183 A1a).
  PB-69: Doku. Handoff auf PB-68.
  PB-70: Feature. code_entwurf_historie (2183 A1b).
  PB-71: Feature. rollback_vor_recovery +
         max_llm_calls 30 (2183 A1c).
  PB-72: Doku. Handoff auf PB-71.
  PB-73: Feature. SolverBefund-Klasse + run_id
         (2183 A2).
  PB-74: Doku. Handoff auf PB-73.
  PB-75: Feature. Trigger-Erkennung (2183 A3).
         +8 Tests, 301 passed.
  PB-76: Doku. Handoff auf PB-75.
  PB-77: Doku. Handoff-Korrektur nach PB-75.
  PB-78: Feature. P1 Gegenstandsvergleich
         (2183 A4/A5). +10 Tests, 311 passed.
  PB-79: Doku. Handoff auf PB-78.
  PB-80: Feature. Solver-Code (2183 B).
         +14 Tests, 325 passed.
  PB-81: Doku. Handoff auf PB-80.
  PB-82: Feature. COMMAND: RUN solver (2183 C).
         +8 Tests, 333 passed.

## 2026-10-14 (echter PB-62 nach Neudefinition)

  PB-62: ERFOLG. Commit 3bb5917. Erster echter
         security-ai-Durchlauf nach der
         Probebetrieb-Neudefinition.
         rc=0, Runden 1, llm_calls 5.

## 2026-10-15 (Probebetriebe 63-66)

  PB-63: ERFOLG. notify_ntfy auf Konvention
         umgestellt. Commit 8db36f7, Tag
         probebetrieb-63. Runden 2, llm_calls 7, rc 0.

  Feldtest PB-64 (Feld): Auftrag bereits erfuellt.
         Drei Laeufe. Loesung: Block Auftrag-erfuellt
         (B1-B5) + Solver-Prompt-Auftrag (Commit 3cf7404).

  PB-65: notify_ntfy — acht Tests fuer
         ToolArgumentValueError. Commit 2aa2b0b,
         Tag probebetrieb-64.

  PB-66: nmap_scan — ToolArgumentValueError.
         Erster Lauf mit PROJEKT-STAND-Block im Prompt.
         Commit d135fd4, Tag probebetrieb-65.

  PB-67: nmap_scan — Unit-Tests fuer Argument-
         Validierung. Commit c9142a7, Tag probebetrieb-66.

================================================================
B. ERLEDIGTE AUFLAGEN (DETAILS)
================================================================

Alle Auflagen, die in frueheren Sessions erledigt wurden.
Aufgelistet mit Status und Commit, wo bekannt.

## Auflagen 2026-10-12 bis 2026-10-13

  2186: KUERZUNGS-MARKER.
  2187: Builder-COMMAND-Loop.
  2188: builder.md KUERZUNGS-MARKER respektieren.
  2189: Pfad-Woertlichkeit + Fehler-Marker.
  2190: GEMESSENER INHALT als primaere Quelle.
  2191: Prompt pro Runde frisch.
  2192: Werkstatt messt automatisch.
  2193: zurueckgezogen (Modellwechsel).
  2194: Audit-Debug (Diagnose).
  2195: Private IPs nicht mehr redigieren (WURZEL).
  2196: collect_messwerte bevorzugt nach-apply.
  2197: Fail-closed-Rollback.
  2198: collect_messwerte-Regex an Kuerzung.
  2185: README komplett, 6 Rollen inkl. Solver
        (nachgezogen 2026-10-15, Commit da50145).

## 2183-Blöcke (Solver-Agent)

  2183-B3: Solver-Wissensbasis (Solver sieht
        Projekt-Doku wie Reviewer). Kategorie 3,
        Reviewer-Block GO mit FF1-FF8.
        Commit d706e66. +4 Tests, 350 passed.

  2183-B5: Solver-Loop + Fail-Pfade. Variante X
        mit GG1-GG5. max_solver_runden=3, Zaehler
        solver_aufrufe, Historie im Solver-Prompt.
        Commit 0b19bcb. +5 Tests, 355 passed.

  2183 A1a (Recovery-Zustand): ERLEDIGT (PB-68).
        Marker recovery an review_runden.
        formatiere_runden(), recovery_hinweis_block().

  2183 A1b (code_entwurf_historie): ERLEDIGT (PB-70).
        Feld + record_code_entwurf(). Kuerzung auf
        10 Eintraege.

  2183 A1c (rollback_vor_recovery + 2184):
        ERLEDIGT (PB-71). max_llm_calls-Defaults
        20 -> 30.

  2183 A2 (SolverBefund-Klasse): ERLEDIGT (PB-73).
        Enum SolverDiagnose, @dataclass
        SolverBefund, format_solver_befund.
        RunState.run_id und RunState.solver_befunde.
        10 neue Tests, 293 passed.

  2183 A3 (Trigger-Erkennung): ERLEDIGT (PB-75).
        zaehle_no_go_in_folge(), recovery-Marker
        ab 2. NO-GO in Folge.

  2183 A4/A5 (P1 Gegenstandsvergleich): ERLEDIGT
        (PB-78). jaccard_aehnlichkeit,
        gegenstand_gleich, solver_config im YAML
        (p1_schwellwert=0.5, p1_min_tokens=10).
        +10 Tests, 311 passed.

  2183 B (Solver-Code): ERLEDIGT (manual,
        Commit 47a9a8b). agents/solver.md,
        HARD_RULES_SOLVER S1-S7, Parser
        parse_solver_diagnose, rufe_solver,
        _letzte_zwei_entwuerfe, _solver_prompt_bauen.
        +14 Tests, 325 passed.

  2183 C (COMMAND: RUN solver): ERLEDIGT (manual,
        Commit 9a5a17f). ERLAUBTE_QUELLEN um
        reviewer_command. SOLVER_ARG_MAX_LEN=200.
        +8 Tests, 333 passed.

  2183-P4-Log2: Zentraler pipeline_ende-Wrapper.
        ERLEDIGT (PB-61). run_pipeline nimmt
        state_ref: list[RunState].

## Weitere Erledigte

  Agent-Memory Ebene 1: ERLEDIGT 2026-10-15.
        Aggregator sammelt projekt_stand aus git log.
        PROJEKT-STAND-Block in Builder, Reviewer,
        Solver. Commits 4e23aba, 52cd658.
        +16 Tests, 423 passed.

  Stufe 0 (Selbstheilung): ERLEDIGT 2026-10-15.
        pruefe_anker_gegen_messung + pruefe_
        ersatz_gegen_messung. Solver-Trigger A+B.
        Commits b5f3073 bis 737afe9. +28 Tests.

  Auftrag bereits erfuellt: ERLEDIGT 2026-10-15.
        Commits a0d436b, 183f560, 0f6442d,
        7fdaffa, 3cf7404. +24 Tests, 407 passed.

  Block Auftrag-erfuellt: ERLEDIGT 2026-10-15.
        Commits a0d436b, 183f560, 0f6442d,
        7fdaffa, 3cf7404.

  2200 (Audit-Aggregator): ERLEDIGT (PB-63).
  2200a (run_id im Audit): ERLEDIGT (PB-62).
  2200c (Pipeline ruft Aggregator): ERLEDIGT.
        pipeline.py:4784.
  2200-T (Test fuer Aggregator): ERLEDIGT.
        tests/test_aggregate.py existiert.

  2199-R7-P2: ERLEDIGT (PB-66).

  Phase 1 Projekt-Schema: ERLEDIGT 2026-10-15.
        Commit 406e3cc. schemas/projekt.yaml,
        projects/_template.yaml,
        tests/test_projekt_schema.py.
        pruefe_projekt_yaml (Warn-Modus),
        _lade_und_pruefe_projekt.
        441 passed.

  Phase 3a-1 Anti-Pattern-Bibliothek: ERLEDIGT
        2026-10-15. Commit 1ed875a.
        anti-patterns/katalog.yaml (7 Eintraege),
        anti-patterns/README.md,
        tests/test_anti_patterns.py (28 Tests).

  Phase 3a-2 Anti-Pattern-Katalog: ERLEDIGT
        2026-10-15. Commit 8ed6cd0.
        Katalog auf 26 Eintraege.

  Phase 3b Builder-Injektion: ERLEDIGT 2026-10-15.
        Commit 04012f6. _anti_pattern_block,
        Zwei-Stufen-Sortierung, trigger_gruende.
        485 passed.

  Phase 3c-1 Solver-Rolle zu 6 Anti-Patterns:
        ERLEDIGT. Commit 4916b01.
  Phase 3c-1b Test-Anpassung: ERLEDIGT.
        Commit 045556e.
  Phase 3c-2 Reviewer-Injektion: ERLEDIGT.
        Commit b84ee8e.
  Phase 3c-3 Solver-Injektion: ERLEDIGT.
        Commit d0a9bad.

  Doku-Migration: ERLEDIGT 2026-10-15.
        Werkstatt: 254b3fb. security-ai: 220c6be.
        PHASES -> ROADMAP, DESIGN_DECISIONS ->
        DECISIONS, SECURITY_REVIEW_LOG -> SECURITY_LOG,
        WORKFLOW -> CONVENTIONS. CONTEXT_PROMPT und
        REVIEWER_HANDOFF entfernt. STATUS.md und
        CHANGELOG.md neu.

================================================================
C. HARD RULES FUER DEN REVIEWER-CHAT (HR-R1 bis HR-R10)
================================================================

Zwei-Webchat-Artefakt. Die Regeln gelten weiter
implizit, sind aber in der Werkstatt durch
HARD_RULES_REVIEWER (pipeline.py) und die
Werkstatt-WORKFLOW abgedeckt.

HR-R1. Faktenlage vor Meinung.
HR-R2. Bestandsaufnahme vor Reviewer-Block.
HR-R3. Auflagen-Nummern global fortlaufend.
HR-R4. Reviewer-Blocks immer in einen Codeblock.
HR-R5. Kategorie 3 nur mit vorherigem Reviewer-Block.
HR-R6. Wenn unsicher: ESKALATION.
HR-R7. Fehler anerkennen, korrigieren, dokumentieren.
HR-R8. Kein Scope-Creep.
HR-R9. Fail-closed.
HR-R10. Kein "das haben wir schon immer so gemacht".

================================================================
D. ANTWORTFORMATE DES REVIEWERS (alt)
================================================================

Zwei-Webchat-Artefakt. Die Werkstatt parst Verdicts
ueber classify_verdict (pipeline.py). Die Formate
sind dort kodifiziert.

GO:
    GO
    Grund: <kurz>
    Bemerkung: <optional>

NO-GO:
    NO-GO
    Grund: <konkreter Punkt>
    Empfehlung: <wie richtig>
    Verweis: <Design-Entscheidung / Doc>

ESKALATION:
    ESKALATION
    Frage: <was>
    Warum: <warum unsicher>
    Vorschlag: <was du empfiehlst>

================================================================
ENDE DES ARCHIVS
================================================================
