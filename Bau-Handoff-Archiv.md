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

================================================================
ARCHIVIERT 2026-10-18 (Bau-Handoff vor W60-Kuerzung)
================================================================

================================================================
WICHTIG — PROBEBETRIEB-DEFINITION
================================================================

Ein Probebetrieb ist NUR ein echter Pipeline-
Durchlauf (pipeline_start + pipeline_ende im
Audit-Log, Projekt security-ai).

Manual-Sessions werden NICHT getaggt.
Die Tags probebetrieb-62 bis -83 (alte Vergabe)
wurden am 2026-10-14 entfernt.

Letzter echter Lauf:
  2026-10-15T16:11-16:11  rc=0  PB-67
  Commit 0d0fe2c (Docstring orchestrator.py).
  Erster echter Lauf nach Phase 1 (Projekt-Schema).
  Runden 1, llm_calls 5, kein Solver-Trigger.

Vorheriger echter Lauf:
  2026-10-14T21:00-21:02  rc=0  PB-62
  Commit 3bb5917 (whois).

Naechster echter Probebetrieb: probebetrieb-68.

================================================================
1. WAS DIE WERKSTATT IST
================================================================

Die Werkstatt ist ein Agenten-System. Sie baut
Projekte, ist aber selbst kein Teil eines Projekts.

Verzeichnis: /opt/werkstatt/
Projekt-Konfigurationen: projects/<name>.yaml
Projekt-Schema: schemas/projekt.yaml
Rollen: agents/
Anti-Pattern-Katalog: anti-patterns/katalog.yaml
Tests: tests/
Doku: docs/

Rollen (6):
  - reviewer (LLM, deepseek-reasoner): prueft Patches
    und Commit-Paket, entscheidet GO/NO-GO/ESKALATION.
  - builder (LLM, deepseek-chat): liefert strukturierte
    Code-Patches (PATCH-BEGINN/ENDE) und das Commit-Paket.
  - solver (LLM): unterstuetzt den Builder bei
    wiederholten NO-GOs.
  - test_generator (LLM): liefert Test-Vorschlaege.
  - coverage (No-LLM): misst Coverage.
  - chaos (No-LLM): fuzzt Extremwerte.

================================================================
WICHTIG FUER DEN NEUEN CHAT (Uebergabe 2026-10-16):
================================================================

Dieser Handoff ist am Ende einer sehr langen
Sitzung (2026-10-16) entstanden. Zwoelf PB-68-
Laeufe, kein erfolgreicher Sammel-Commit, aber
viele fundamentale Werkstatt-Fixes.

Bevor der neue Chat arbeitet:
  1. Werkstatt-HEAD pruefen:
       git -C /opt/werkstatt log -1 --oneline
  2. Tests laufen lassen:
       /opt/security-ai/.venv/bin/python3 -m
       pytest /opt/werkstatt/tests/ -q
     Erwartung: 707 passed.
  3. security-ai pruefen:
       git -C /opt/security-ai log -1 --oneline
       git -C /opt/security-ai status --porcelain
     Erwartung: 0d0fe2c, clean.
  4. phase.yaml pruefen:
       head -6 /opt/werkstatt/projects/
       security-ai.phase.yaml
     Erwartung: phase_aktiv=true, U1=no_go.

Der naechste Bau-Block:
  Plan-Konkretisierung. Reviewer-Block wird in
  dieser Sitzung formuliert, im neuen Chat
  eingereicht. Kategorie 3, Reviewer-Freigabe
  einholen.

Der Reviewer-Chat wechselt mit:
  Der neue Chat muss dem Reviewer mitteilen:
  'Neuer Bau-Chat, Uebergabe 2026-10-16. Stand:
   siehe Bau-Handoff, HEAD 707f964+.'
  Der Reviewer fuehrt seinen eigenen Kontext
  (alle getroffenen Entscheidungen); er braucht
  nur den Uebergabe-Hinweis.

Naechster echter Probebetrieb: PB-68 (nicht
  PB-67 nochmal). Erst nach erfolgreichem
  Sammel-Commit taggen.

================================================================
2. AKTUELLER ZUSTAND
================================================================

Werkstatt-Repo (/opt/werkstatt):
  HEAD 26a9911 (Doku: Handoff — P2a-Smoke-Test).
  P2a-Commit: e700e4b.
  Tests: 542 passed.
  ruff --no-cache: 0.
  mypy pipeline.py: 0.
  git status: clean.
  Remote: github.com/ghxstfocus/werkstatt.git (privat).

Ziel-Projekt security-ai (/opt/security-ai):
  HEAD 0d0fe2c (PB-67).
  Doku-Migration: 220c6be (siehe Abschnitt 3).
  Tests: 1334 collected.
  ruff: 0.
  mypy: 1353 Fehler (Altlast, no-untyped-def).
  git status: sauber.
  Remote: github.com/ghxstfocus/security-ai.git.

Dateien (Werkstatt):
  - pipeline.py (~6162 Zeilen)
  - redaction.py
  - werkstatt_aggregate.py
  - schemas/projekt.yaml
  - projects/security-ai.yaml
  - agents/*.md (7 Rollen: reviewer, builder, solver,
    test_generator, coverage, chaos, planner)
  - anti-patterns/katalog.yaml (26 Eintraege)
  - tests/test_pipeline.py
  - tests/test_projekt_schema.py
  - tests/test_anti_patterns.py
  - tests/test_aggregate.py
  - tests/test_redaction.py
  - tests/test_planner.py (27 Tests)
  - tests/test_phase.py (17 Tests)
  - docs/WORKFLOW.md (~583 Zeilen)
  - docs/ROADMAP.md
  - docs/PROTOKOLL-29-40.md
  - docs/PLANNER-KONZEPT.md (v4 final)

Ziel-Projekt-Doku (nach Doku-Migration):
  Top-Level: README.md, CHANGELOG.md,
             PROJECT_VISION.md, LICENSE
  docs/: STATUS.md, ROADMAP.md, DECISIONS.md,
         SECURITY_LOG.md, CONVENTIONS.md,
         WORKFLOW (entfernt), ARCHITECTURE.md,
         SECURITY.md, PERMISSIONS.md, PROTOCOL.md,
         DEPLOYMENT.md, WEB_SECURITY_CHECKLIST.md,
         ADMIN_AI_SCOPE.md, INCONSISTENCIES_FOUND.md,
         WERKZEUGE.md, ICONS.md, NTFY.md, README.md

Struktur-Konvention (gilt fuer alle Projekte):
  - README.md (Top-Level) — 30-Sekunden-Ueberblick.
  - CHANGELOG.md (Top-Level) — chronologisch.
  - PROJECT_VISION.md (Top-Level) — Vision.
  - docs/STATUS.md — aktueller Stand.
  - docs/ROADMAP.md — Phasen und Ausblick.
  - docs/DECISIONS.md — Design-Entscheidungen.
  - docs/SECURITY_LOG.md — Sicherheits-Entscheidungen.
  - docs/CONVENTIONS.md — projektspezifische Konventionen.

Status-Icons:
  ✅ abgeschlossen, 🔨 in Arbeit, 💡 geplant,
  ❌ abgebrochen, ⏸ pausiert.

================================================================
3. LETZTE SESSION (2026-10-15)
================================================================

Phase 1 Projekt-Schema (Commit 406e3cc):
  schemas/projekt.yaml (K/O/P/W+O, Defaults,
  Alias-Mechanik), projects/_template.yaml,
  tests/test_projekt_schema.py.
  pipeline.py: pruefe_projekt_yaml (Warn-Modus,
  Fail-Modus via WERKSTATT_SCHEMA_MODUS),
  _lade_und_pruefe_projekt.

Phase 3a-1 Anti-Pattern-Bibliothek (Commit 1ed875a):
  anti-patterns/katalog.yaml (7 Eintraege),
  anti-patterns/README.md, pipeline.lade_anti_patterns
  + anti_patterns_fuer, _AUDIT_KINDS_BEKANNT.

Phase 3a-2 Anti-Pattern-Katalog (Commit 8ed6cd0):
  Katalog auf 26 Eintraege erweitert.

Phase 3b Builder-Injektion (Commit 04012f6):
  _anti_pattern_block, _ap_trigger_grund_aus_state,
  Zwei-Stufen-Sortierung (spezifisch vor Fallback).

Phase 3c-1/2/3 Reviewer + Solver Injektion
(Commits 4916b01, 045556e, b84ee8e, d0a9bad):
  - 3c-1: Solver-Rolle zu 6 Anti-Patterns.
  - 3c-2: Reviewer-Injektion in build_system_prompt.
  - 3c-3: Solver-Injektion in rufe_solver
    (trigger_grund, aufrufer).

Erster echter Pipeline-Lauf PB-67:
  Commit 0d0fe2c in security-ai, Tag probebetrieb-67.
  Commit-Message: "docs: Docstring in
  _build_default_registry entkoppelt".
  Inhalt: Docstring orchestrator.py korrigiert
  (Punkt 94).
  Runden 1, llm_calls 5, kein Solver-Trigger.
  Tag probebetrieb-67 gesetzt.
  Damit ist die Bedingung fuer Phase 1b erfuellt.

Block P1 (Planner-Rolle + _planner_lauf):
  ERLEDIGT 2026-10-15. Commit 9544c7e.
  agents/planner.md (73 Zeilen).
  HARD_RULES_PLANNER (P1-P9),
  PLANNER_BLOCK_PRAEFIXE,
  HARD_RULES_BY_ROLE["planner"].
  RunState: planner_model, planner_vorschlag,
  planner_modus, planner_runden.
  parse_planner_reply, _planner_lauf,
  _planner_main_pfad.
  main() --planner-Pfad.
  Minimales Basis-Gate (Projekt + git clean).
  Rueckfrage-Loop, Bestaetigung [j]/[n]/[e].
  projects/security-ai.yaml: agent_docs.planner
  + planner-Block.
  schemas/projekt.yaml: planner-Schema.
  tests/test_planner.py (19 Tests).
  514 passed.

Planner-Konzept v4 (final):
  Commit da80b1f. docs/PLANNER-KONZEPT.md.
  Alle 40 Praezisierungen aus 3 Reviewer-
  Durchlaeufen eingearbeitet.

P1-Live-Test (2026-10-15, nach Commit 9544c7e):
  Erster echter --planner-Lauf.
  Rohauftrag: "Schau dir den aktuellen
  Projektstand an und plane den naechsten
  sinnvollen Bau-Auftrag."

  Ergebnis:
    - Planner-Runde 1: Auftrag formuliert
      (Punkt 26 aus SECURITY_LOG: security_ai-
      Startpfad, __main__.py + systemd-Unit).
    - Bestaetigung [j]: Lauf startet.
    - Basis-Gate: gruen.
    - Builder-Runde 1-3: kein Patch, nur
      COMMAND-Zeilen (Rueckfragen zur Messung).
    - Deadlock: builder_command_deadlock.
    - Recovery: Reviewer diagnostiziert
      "Zuschnitt-Fehler".
    - Kein Commit in security-ai.
    - security-ai unveraendert 0d0fe2c.

  Erkenntnis:
    - P1 funktioniert im Live-Betrieb.
    - Der Planner hat den Ist-Zustand korrekt
      gelesen und einen sinnvollen Auftrag
      formuliert.
    - ABER: Der Auftrag war zu gross (6 Schritte,
      7-9 Dateien, Betriebsakt in einem Block).
    - Der Builder misst korrekt und endlos,
      kommt aber nie zum Bauen.
    - Das ist genau der Zuschnitt-Fehler, den
      P2 (Phasen-Modus) loesen soll.
    - Bestaetigt: P2 ist dringender als gedacht.

  Reviewer-Recovery-Vorschlag (im Audit):
    Vier Bloecke:
      1. Bestandsaufnahme (Kategorie 1, nur lesen).
      2. __main__.py + Tests (Kategorie 3).
      3. systemd-Unit + Doku (Kategorie 1/2).
      4. Betriebsakt systemctl (Kategorie 3,
         eigener GO, eigener Rollback).
    Faustregel: hoechstens EIN neuer Code-Pfad
    pro Block; systemd-Start nie im selben Block
    wie der Code; Erkundung nie im selben Block
    wie Bau.

Doku-Migration (Werkstatt 254b3fb,
security-ai 220c6be):
  - Profi-Konvention: PHASES -> ROADMAP,
    DESIGN_DECISIONS -> DECISIONS,
    SECURITY_REVIEW_LOG -> SECURITY_LOG,
    WORKFLOW -> CONVENTIONS.
  - Neue Dateien: docs/STATUS.md, CHANGELOG.md.
  - Entfernt: docs/CONTEXT_PROMPT.md,
    docs/REVIEWER_HANDOFF.md.
  - Werkstatt-WORKFLOW um 9 Abschnitte erweitert.
  - Alias-Mechanik datengetrieben (Schema als
    einzige Quelle).

Block P2a (Phasen-Modus Fundament):
  ERLEDIGT 2026-10-15. Sieben Teilschritte.
  Basis: HEAD e8a01a4 (P1-Live-Test-Doku).
  Commit: e700e4b ("P2a: Phasen-Modus Fundament —
  Datenmodell, Parser, Persistenz, CLI").
  Folge-Commits: 7186363 (Werkstatt-Regel projects/-
  Owner), 26a9911 (Handoff P2a-Smoke-Test).

Block P2b-1 (run_phase-Geruest + Status-Helfer):
  ERLEDIGT 2026-10-16. Commit 770fbea.
  Reviewer: GO-mit-Auflagen (P2b-Zuschnitt).
  Reihenfolge (Reviewer F3): Rollback VOR
  Phasen-Modus. Daher P2b-2 = Rollback.

  Aenderungen:
    - _AUDIT_KINDS_BEKANNT +8 (phase_abgebrochen,
      phase_commit_paket_gesammelt,
      phase_gesamt_review, phase_rollback,
      phase_unterblock_ende, phase_unterblock_start,
      run_phase_ende, run_phase_start).
    - _phase_yaml_status_update neu (liest via
      _phase_plan_laden, patcht status, ruft
      _phase_plan_speichern; Fail-closed ValueError).
    - run_phase neu (Loop ueber phase_unterbloecke,
      pending->running->done, phase_aktueller_index,
      Audit-Kette, Idempotenz-Schutz, Stub statt
      run_pipeline mit TODO(P2b-3)).
    - _phase_main_pfad: Andock an run_phase
      (Z. ~5821).
  Tests: 542 -> 555. test_phase.py +13.
  Kein Probebetrieb-Tag (F7: PB-68 erst nach P2b-4).

Block P2b-2 (Rollback + phase_start_head):
  ERLEDIGT 2026-10-16. Commit 95b2671.
  Reviewer: GO-mit-Auflagen (P2b-2-Zuschnitt).

  Aenderungen:
    - _AUDIT_KINDS_BEKANNT +1
      (phase_start_head_gesetzt).
    - _git_rev_parse_head (neu): git rev-parse HEAD,
      "" bei Fehler.
    - _git_status_porcelain (neu): git status
      --porcelain, "!FEHLER!" bei Fehler.
    - _phase_rollback (neu): RR-K1/K2/K3.
      Best-Effort (F6): faengt Exception, gibt False.
      Rueckgabe bool (F4), kein rc.
      state.phase_commit_pakete wird geleert (F5).
    - run_phase: phase_start_head-Synchronisation
      vor run_phase_start (YAML gewinnt, wenn != "").
  Tests: 555 -> 570. test_phase.py 30 -> 45.
  Kein Probebetrieb-Tag.
  Rollback-Aufruf folgt P2b-3 (Exception-Pfad) und
  P2b-4 (Phase-NO-GO).

Block P2b-2-A7 (Fail-closed phase_start_head):
  ERLEDIGT 2026-10-16. Commit fd34f5d.
  Reviewer-Nachtrag zu P2b-2 (K2 aus P2b-3).
  run_phase prueft jetzt vor dem phase_start_head-
  Setzen: yaml_head == "" UND state != "" ->
  ValueError. Plus mypy-Fix (_state-Rueckgabetyp
  in test_phase.py).
  Tests: 570 -> 571.

Block P2b-3 (run_pipeline-Phasen-Modus):
  ERLEDIGT 2026-10-16. Commit 85e0572.
  Reviewer: GO-mit-Auflagen (P2b-3-Zuschnitt).

  Aenderungen:
    - _AUDIT_KINDS_BEKANNT +1
      (phase_commit_paket_leer).
    - run_pipeline-Signatur: *, phasen_state=None
      (keyword-only).
    - Docstring fuer phasen_state.
    - phasen_state-Guard beim RunState-Bau:
      state_ref muss leer sein, sonst ValueError.
    - Phasen-Modus vor Schritt 6:
      state.phase_aktiv True -> Paket sammeln
      (Audit phase_commit_paket_gesammelt) +
      return 0.
      Leeres Paket -> rc=21 (Audit
      phase_commit_paket_leer).
    - apply_commit_and_doku unveraendert.
  Tests: 571 -> 575. test_phase.py 46 -> 50.
  Loop-Aufruf folgt in P2b-3b.

Block P2b-3b (Loop-Aufruf in run_phase):
  ERLEDIGT 2026-10-16. Commit af45157.
  Reviewer: GO-mit-Auflagen (P2b-3b-Zuschnitt).

  Aenderungen:
    - run_phase-Signatur:
      (project_name, state, state_ref) -> int.
    - state_ref-Guard (ValueError wenn nicht leer).
    - Loop-Koerper: Stub ersetzt durch
      run_pipeline(phasen_state=state),
      lokaler sr_intern pro Aufruf,
      Vertragspruefung sr_intern[0] is state.
    - Vier rc-Klassen (L3):
        Klasse 1: rc=0 + Paket -> done, weiter.
        Klasse 2: rc=0 ohne Paket -> B2,
                  done, weiter.
        Klasse 3: rc=15 -> no_go, Loop-Abbruch,
                  KEIN Rollback.
        Klasse 4: sonst -> failed + Rollback,
                  rc zurueck.
    - Exception im Loop -> Rollback, rc=22.
    - state_ref.append(state) am Ende
      (nur im Erfolgspfad).
    - _phase_main_pfad-Aufruf angepasst.
  Tests: 575 -> 583. test_phase.py +8.
  Merkposten NA3: run_pipeline B2-Signal im
  state (siehe Abschnitt 4).

Block P2b-4 (Phasen-Gesamt-Review + Sammel-Commit):
  ERLEDIGT 2026-10-16. Commit 16eec88.
  Reviewer: GO-mit-Auflagen (P2b-4-Zuschnitt).

  Aenderungen:
    - _phase_gesamt_review (deterministisch).
    - _phase_sammel_message (Commit-Message-Format).
    - _phase_sammel_paket (Union aller Pakete).
    - _print_phase_approval_dokument.
    - run_phase: Gesamt-Review + Approval [j]/[n]
      + Sammel-Commit via apply_commit_and_doku.
    - _phase_main_pfad: phase_aktiv=False nach
      erfolgreichem run_phase.
  Tests: 583 -> 592.
  Kein Probebetrieb-Tag (F7: PB-68 erst nach
  P2b-5).

Block P2b-5 (Budget-Layer-1 + Plan-Korrektur):
  ERLEDIGT 2026-10-16. Commit 6e8b791.
  Reviewer: GO-mit-Auflagen (P2b-5-Zuschnitt).

  Aenderungen:
    - _AUDIT_KINDS_BEKANNT +3 (phase_budget_ende,
      phase_plan_korrektur_failed,
      phase_plan_korrektur_start).
    - _planner_user_content + korrektur_kontext.
    - _planner_lauf + korrektur_kontext.
    - _phase_rr_k8 (neu): RR-K8-Menue [1]/[2]/[3].
    - _phase_plan_korrektur (neu): Planner-Korrektur.
    - run_phase: korrektur_zyklus (keyword-only),
      Budget-Check vor jedem Unterblock (rc=13),
      Plan-Korrektur im [n]-Zweig (max 1 Zyklus).
    - conftest.py: autouse DEEPSEEK_API_KEY-Fixture.
  Tests: 592 -> 602.
  P2b ist damit FERTIG.

Sitzung 2026-10-16 (nach P2b):
  Ziel: erster echter Phasen-Lauf (PB-68).
  Ergebnis: elf Laeufe, kein erfolgreicher
  Sammel-Commit. Aber: viele fundamentale
  Bugs gefunden und gefixt.

  PB-68-Laeufe und ihre Befunde:
    1-5: Resume-Pfad, state_ref, build_catalog,
         NEW_FILE-Format, Solver-Trigger.
    6:   Builder-Rueckfrage als Fliesstext
         statt COMMAND: frage_reviewer.
    7:   Planner lieferte Roadmap-Themen
         statt baubare Bloecke.
    8:   state.aufgabe im Phasen-Modus
         zeigte Phasen-Gesamttext.
    9:   builder.md nannte nur typ: patch,
         nicht typ: new_file im Kopf.
    10:  Anker-Pruefung lehnte korrekte
         typ: new_file-Patches ab.
    11:  Erste Code-GO + Apply. Post-Apply-
         Basis-Gate rot (ruff). Lauf endete
         terminal, Recovery-Plan erreichte
         den Builder nicht.

  Wichtige Werkstatt-Fixes in dieser Sitzung:
    - P2b-Frage-A/B: Rueckfrage-Kanal
      (COMMAND: frage_reviewer, ANTWORT-Modus).
    - P2b-Korrektur: Plan-Korrektur bei
      Unterblock-NO-GO.
    - Rollen-Audit-A/B: reviewer.md, builder.md,
      solver.md korrigiert.
    - Planner-Rolle: P15/P16 (Blockgroessen).
    - builder-format: typ: new_file im
      WICHTIG-Block.
    - V3-Fix: Anker-Pruefung ueberspringt
      typ: new_file.
    - Post-Apply-Fix: rc=19-Signal +
      _post_apply_korrektur_loop.

  Aktueller Zustand:
    - Phase 18 (Guardrails) in phase.yaml.
    - U1 (Guardrail-Modell) status=no_go nach
      Lauf 12 (rc=15, unterblock_no_go).
    - Working Tree clean (nach git clean -fd
      vor Lauf 12).

  Lauf 12 (2026-10-16, Post-Apply-Fix):
    - typ: new_file funktioniert weiter.
    - Zwei NO-GO-Zyklen in U1 (5 Runden +
      Plan-Korrektur + 5 Runden).
    - Reviewer-Diagnose (Zitat):
        'Der Loop haengt nicht an einem
         fehlerhaften Builder, sondern an
         wechselnden Review-Kriterien.'
        'Der Kern-Befund — Auftrag unterbestimmt
         — kann nur der Planner aufloesen,
         nicht der Builder.'
    - Reviewer verlangt: feste Spezifikation
      (frozen ja/nein, Defaults, Feldreihen-
      folge, str-Enum vs. Enum, Bedeutung
      von 'Roundtrip').
    - Plan-Korrektur ERSETZT den Plan, sie
      KONKRETISIERT ihn nicht. Der Builder
      sieht denselben Auftrag, liefert den
      denselben Code, der Reviewer gibt
      dieselbe Bewertung.

  Struktureller Befund (offen):
    - Es fehlt ein Kanal 'Reviewer-Befund ->
      Planner-Konkretisierung -> neue
      Plan-Version'. Plan-Korrektur muss
      konkretisieren, nicht ersetzen.
    - Naechster Reviewer-Block: Plan-Konkre-
      tisierung (in dieser Session formuliert,
      noch nicht gebaut).

  Teilschritte:
    1. RunState + 7 phase_*-Felder.
    2. _parse_phase_plan (P10-P14-Format).
    3. _phase_plan_laden/_speichern (atomar, 0600).
       .gitignore: projects/*.phase.yaml +
       projects/.*.tmp.*
    4. HARD_RULES_PLANNER_STUFE1/STUFE2.
       P1-P9 wortgleich in STUFE1. STUFE2:
       P1', P2, P3', P4', P5, P6, P8, P9',
       P10-P14. Alias HARD_RULES_PLANNER auf
       STUFE1.
    5a. _parse_phase_kopf + build_system_prompt
        stufe-Parameter (keyword-only) +
        _planner_lauf stufe-Parameter +
        _planner_user_content.
    5b. _phase_main_pfad + main() --phase +
        Audit-Kinds phase_plan_erstellt,
        phase_plan_parse_failed,
        phase_plan_verworfen.
    5c. Konflikt-Check --phase/--planner (rc=65)
        + _phase_plan_als_text (Roundtrip)
        + _phase_edit_modus (nur Titel/Runden)
        + Audit-Kind phase_plan_editiert
        + letzter_vorschlag-Mechanik.
    6. agents/planner.md: Stufe-1/Stufe-2-Sektionen.
    7. projects/security-ai.yaml +
       schemas/projekt.yaml: planner.phasen_modus,
       budget.max_llm_calls_phase (Deklaration).

  Tests: 514 -> 542 (+28).
  Reviewer-Auflagen: P2a-A1..A14, P2a-S1..P2a-S6-7
  (alle eingearbeitet).
  Kein Probebetrieb-Tag (kein echter Pipeline-
  Durchlauf; der Phasen-Loop ist erst in P2b
  funktional).

  Smoke-Test (2026-10-15, kein Tag):
    Aufruf: pipeline.py --project security-ai
            --phase "Baue eine kleine Testphase ..."
    Ergebnis: erfolgreich.
      - Planner Stufe 2 liefert korrektes P10-P14-
        Format.
      - Anzeige korrekt (Phase-Titel, U1 mit 5
        Unterpunkten, U2 mit 4 Unterpunkten,
        (Runde 1/3)).
      - [j] schreibt projects/security-ai.phase.yaml
        atomar, mode 0600, owner builder:builder.
      - Audit-Kette vollstaendig: pipeline_start
        -> planner_start (stufe=2) ->
        planner_vorschlag -> phase_plan_erstellt
        -> pipeline_ende (rc=0).
      - .gitignore-Schutz greift (git status leer).
      - Kein tmp-Zombie.
    Deployment-Regression entdeckt:
      projects/ war faelschlich root:root (Phase-1-
      Commit 406e3cc hatte den Owner versehentlich
      ueberschrieben). Reparatur: chown
      builder:builder + chmod 750. Werkstatt-Regel
      im Handoff ergaenzt.
    Qualitaets-Beobachtung (wichtig fuer P2b):
      Der Planner liefert praezise Unterpunkte mit
      Datei, Testpfad, Verifikationskommandos und
      Doku-Nachzug. Der Loop in P2b kann sich auf
      'unterpunkte' als Bau-Auftrag verlassen.

================================================================
4. OFFENE MERKPOSTEN
================================================================

KRITISCH: keine.

AUS SITZUNG 2026-10-16 (neu):

  P8 — Builder-Rueckfrage als Fliesstext:
        Der Builder liefert die Rueckfrage als
        Fliesstext mit '?' am Ende, nicht als
        'COMMAND: frage_reviewer <text>'.
        R8 greift deshalb nicht.
        Fix: Builder-Prompt expliziter.
        Kategorie 3.

  V1 — baue_anker_rueckmeldung Option (c):
        Der Anker-Block sollte typ: new_file
        als Option (c) mit Diagnose-Satz
        'Existiert die Zieldatei?' nennen.
        Nur relevant fuer den Fall 'Builder
        liefert typ: patch mit leerem Anker
        auf neue Datei'. Eigener Block.

  V4 — statischer new_file-Hinweis in
        _builder_user_prompt: Position pruefen.
        Kosmetisch, eigener Block.

  V6 — dynamische vs. statische Prompt-Bloecke:
        Dynamische Bloecke (baue_anker_rueckmeldung,
        baue_budget_rueckmeldung) sind maechtiger
        als statische Doku. Gemeinsamer Katalog
        'Patch-Format-Optionen' als Quelle.
        Eigener Block.

  Solver-Entlastung — bereits implementiert:
        solver_trigger_b (builder_rueckfrage)
        laeuft parallel zum Reviewer. Rollenbild
        in Rollen-Audit-B nachgezogen.
        Kein offener Fix.

  Phase-18-Plan (10 Unterbloecke) — Review:
        Nach Lauf 12 pruefen, ob 10 Bloecke
        pro Phase sinnvoll sind. Evtl. P17
        (Phasen-Obergrenze) einfuehren.

WICHTIG:

  Block P2a (Phasen-Modus Fundament):
        ERLEDIGT 2026-10-15. Siehe Abschnitt 3.
        Commit: "P2a: Phasen-Modus Fundament".

  Block P2b-1 (run_phase-Geruest): ERLEDIGT.
        Commit 770fbea. Siehe Abschnitt 3.

  Block P2b-2 (Rollback + phase_start_head):
        ERLEDIGT. Commit 95b2671. Siehe Abschnitt 3.

  Block P2b-3 (run_pipeline-Phasen-Modus):
        ERLEDIGT. Commit 85e0572. Siehe Abschnitt 3.

  Block P2b-3b (Loop-Aufruf in run_phase):
        ERLEDIGT. Commit af45157. Siehe Abschnitt 3.

  Merkposten (P2b-3b-A4-NA3): run_pipeline B2-Fall
        B2 ist heute nur per Audit
        (auftrag_bereits_erfuellt) und rc=0
        erkennbar. run_phase nutzt die strukturelle
        Heuristik rc=0 ohne Paket = B2
        (P2b-3b-A4). Wenn run_pipeline weitere
        rc=0-Pfade ohne Paket bekommt, MUSS die
        Heuristik durch ein state-Feld (z.B.
        state.b2_erreicht: bool) ersetzt werden.
        Eigener Block, nicht in P2b.

  Block P2b-4: ERLEDIGT. Commit 16eec88.

  Block P2b-5: ERLEDIGT. Commit 6e8b791.

  P2b ist FERTIG. Naechster Meilenstein:
        PB-68 (erster echter Phasen-Lauf).
        Kategorie 3 (echter Lauf, Commit in
        security-ai).
        Bedingung F7 erfuellt.
        Vorsicht: der Lauf committet in
        security-ai. Auftrag klein halten.

  Planner-Portionierung (Zwischenloesung):
        OFFEN. Falls P2 zu gross ist, reicht
        evtl. eine Zwischenloesung: der Planner
        liefert bei grossen Auftraegen eine Liste
        von Unterauftraegen, und der main-Pfad
        ruft run_pipeline mehrfach auf. Das waere
        eine vereinfachte Form des Phasen-Modus
        ohne Persistenz, Gesamt-Review, atomaren
        Rollback. Diskussion in naechster Session.

  Block P3 (ASK_HUMAN + Persistenz):
        OFFEN. Nach P2. Kategorie 3.
        Datei-basiert (ask-human/<run_id>).
        Timeout 60 min.

  Rollen-Modell aus Frontmatter lesen:
        OFFEN. Bestehende Inkonsistenz:
        agents/*.md Frontmatter liefert
        model/temperature, wird aber nicht
        vom Code gelesen. Alle *_model-Felder
        in pipeline.py sind hartcodiert.
        Eigener Block, Kategorie 2.
        Anlass: P1, SS7-(C).

  Phase 1b (Validator Fail-closed): BEREIT.
        WERKSTATT_SCHEMA_MODUS Default ist warn
        (pipeline.py:478). PB-67 (2026-10-15) ist
        der erste echte Lauf nach Phase 1, Warn-
        Modus ohne Warnung durchgelaufen. Bedingung
        erfuellt.
        Naechster Schritt: Kategorie-3-Reviewer-Block,
        dann Default auf fail umstellen. Kategorie 3
        (bestaetigt vom Reviewer-Chat 2026-10-15).

  Solver-Kurskorrektur Block 6 (Smoke-Test): OFFEN.
        Echter Solver-Lauf im Deadlock- und
        Phase-1-Trigger-Pfad. Nach PB-67 oder
        spaeter. Kategorie 3.

  2183-AQ (Auftragsqualitaet vor Werkstatt-Lauf):
        Auftraege gegen Zielcode pruefen, bevor
        ein Lauf startet. Auftraege, die Verhalten
        annehmen, das im Zielcode nicht existiert,
        enden in Livelock oder Deadlock.
        Kategorie 3.

  2199a (Recovery-Pfad post-apply-Basis-Gate):
        Zustandsmaschine klaeren:
          - Recovery-Lauf vs. normaler Builder-Lauf.
          - Zaehlung in state.review_runden?
          - Reviewer sieht Recovery als neue Runde?
          - max_llm_calls-Zaehlung.
        Dann Recovery-Zweig bauen. Max 1 Zyklus.
        Kategorie 3.

  Werkstatt-Vertrag (2183). Kategorie 3.
        Fuenf Vertraege zusammenfuehren:
          1. Anker-Vertrag.
          2. Auftrags-Vertrag.
          3. Patch-Vertrag.
          4. Fail-Vertrag.
          5. Rollen-Vertrag.
        Format: docs/WERKSTATT-VERTRAG.md + .yaml.
        Offene Design-Fragen W1-W4 im Archiv.

  B2 — Builder-Kanal fuer Solver-Befund.
        praezisierter_auftrag landet heute nur in
        state.solver_befunde und im Reviewer-Prompt.
        Der Builder sieht ihn nicht. Kategorie 3.

  _WERKSTATT_PROJECTS_DIR (aus P2a-S3-A8):
        Path("/opt/werkstatt/projects") inline in
        memory.yaml-Pfad + _PHASE_YAML_DIR in P2a
        sind zwei Stellen. Zusammenfuehren in eine
        Konstante. Kategorie 2.

  ruff TRY004 vs. Auflage ValueError (P2a-S3-NA-A5):
        In _phase_plan_laden bewusst # noqa: TRY004,
        weil P2a-A7 explizit ValueError fordert.
        Bei haeufigerem TRY004 in spaeteren Bloecken:
        Werkstatt-Konvention statt 4x # noqa.

  Resume/Schutz alter phase.yaml (aus P2a-S5b-3):
        5b/5c pruefen NICHT, ob eine alte phase.yaml
        existiert, und loeschen nichts. Resume
        gehoert in einen eigenen Block (Konzept 9.2).

  Gemeinsame Basis _planner_main_pfad +
  _phase_main_pfad (aus P2a-S5b-F4):
        Bewusste Duplikation in P2a. Spaeter pruefen,
        wenn weitere Pfade dazukommen (P3,
        Scaffolder). Kategorie 2.

MITTEL:

  _AUDIT_KINDS_BEKANNT: manuell pflegen.
        Neue kind-Werte im Audit-Log muessen in
        pipeline.py ergaenzt werden, sonst
        schlaegt die Katalog-Validierung fehl.
        Merkposten: automatische Ableitung pruefen.

  ap-string-literal-statt-konstante:
        Bau-Chat-Befund. Bei der naechsten
        Katalog-Durchsicht pruefen, ob weitere
        Bau-Chat-Befunde in Eintraege umgewandelt
        werden.

  tests-mypy: 15 Fehler (nicht mehr 151).
        In tests/test_pipeline.py, Zeilen
        3583-3608 (code_entwurf_historie) und
        4147 (append return value). Vorbestehend.
        Eigener Block. Kategorie 2.

  II2b (Substring-Kollision): Ersatz-Pruefung
        nutzt Substring-Match. Bei erster realer
        Kollision: Wortgrenzen oder exakter Match.

  II5b (Audit-Fuss-Kuerzung): _audit_builder_
        reply kuerzt Fuss auf 200 Zeichen.
        Vorschlag: auf redigiert[-1000:] erweitern.

  II6b (Inhaltswort-Kalibrierung): Liste
        INHALTSWOERTER_TRIGGER_B nach 5-10
        PB-Laeufen kalibrieren.

  F2 (Fail-closed bei rufe_solver-Fehler):
        max_rufe_solver_fehler = 2 nach
        5-10 PB-Laeufen mit Solver kalibrieren.

  F3 (Fail-closed bei unvollstaendigem Befund):
        Bleibt (a): leerer Block + Audit.
        Fail-closed nur bei Quote >20%.

  F4 (_bauer_auflagen_prompt): DD5 bleibt.
        Ueberdenken, wenn Auflagen-Pfad haeufiger
        failt.

  B5-M1 (Historie-Block Umfang): Solver-Prompt
        zeigt nur DIAGNOSE, nicht Volltext.
        Nach ersten PB-Laeufen pruefen.

  B5-M2 (Trigger-Pfad-Test): voller Test
        ausstehend.

  Solver-Kurskorrektur Merkposten:
        W10 (Befund-Historie), W12 (Rollen-Vertrag),
        P4-nach-Solver (max_llm_calls neu messen),
        max_solver_runden-Kalibrierung (3 ist
        Setzung), solver_befunde-Eingrenzung,
        Audit-Kanal Solver-UNKLAR.

  U4-Kalibrierung (P1): Schwellwert 0.5 und
        min_tokens 10 sind Setzungen. Nach ersten
        PB-Laeufen labeln und neu setzen.

  P4-nach-P1-B (llm_calls): P1 reduziert den
        Trigger. Wirkung nicht gemessen. Nach
        Solver-Nutzung neu messen.

  docs-Migration Rollen-Prompt-Generator
        (Phase 3.5): mittelfristig docs/*.md
        durch generierte Rollen-Prompts ersetzen.

NIEDRIG:

  2187b: read_file Zeilenbereich.
  2188a: agents/*.md konsolidieren.
  2188c, 2189c, 2190b-M, 2191-M2, 2192-M2,
  2198-M, 2198-M2: Feature + Prompt + Aktualisierung
        konsolidieren.
  2190-M: Reviewer-Auswahl-Logik pruefen.
  2192-M1: execute_commands prueft, ob Pfad schon
        vollstaendig gemessen.
  2195-M2: MAC-Redaction rechtfertigen oder entfernen.
  2195-M3: Anker mit gemischten privaten/oeffentlichen IPs.
  2191-R2b-T: Test fuer commit_review_ohne_messung.
        Test-Harness bauen. Kategorie 2.
  2191-R4: Builder-Prompt vs. Reviewer-Prompt
        (GEMESSENER INHALT Position). Kategorie 2.
  Phase-2-COMMAND-Schleichpfad: classify_verdict
        erkennt COMMAND in Phase 2, Loop bricht
        ab. Kein Fail, kein Log. Merkposten.
  Audit-Log-Ausbau dauerhaft.
  Tag-Verwirrung vereinheitlichen.

================================================================
5. ERLEDIGTE MERKPOSTEN (KURZREFERENZ)
================================================================

Detaillierte Beschreibungen in Bau-Handoff-Archiv.md,
Abschnitt B.

  2183 A1a, A1b, A1c, A2, A3, A4/A5, B, C
       (Solver-Kurskorrektur, alle erledigt).
  2183-B3, 2183-B5 (Solver-Wissensbasis, -Loop).
  2183-P4-Log2 (pipeline_ende-Wrapper).
  2184 (max_llm_calls 30).
  2185 (README komplett).
  2186-2198 (Auflagen 2026-10-12 bis -13).
  2199, 2199-R7-P2 (ABGESCHLOSSEN).
  2200, 2200a, 2200c, 2200-T.
  Agent-Memory Ebene 1 (Commits 4e23aba, 52cd658).
  Stufe 0 (Commits b5f3073 bis 737afe9).
  Auftrag bereits erfuellt (Commits a0d436b bis 3cf7404).
  Phase 1 Projekt-Schema (Commit 406e3cc).
  Phase 3a-1 (1ed875a), 3a-2 (8ed6cd0), 3b (04012f6).
  Phase 3c-1 (4916b01), 3c-1b (045556e),
    3c-2 (b84ee8e), 3c-3 (d0a9bad).
  Doku-Migration (Werkstatt 254b3fb,
    security-ai 220c6be).
  Block P1 (Planner-Rolle + _planner_lauf,
    Commit 9544c7e).
  Block P2a (Phasen-Modus Fundament,
    Commit "P2a: Phasen-Modus Fundament").
  Block P2b-1 (run_phase-Geruest + Status-Helfer,
    Commit 770fbea).
  Block P2b-2 (Rollback + phase_start_head,
    Commit 95b2671).
  Block P2b-2-A7 (Fail-closed phase_start_head,
    Commit fd34f5d).
  Block P2b-3 (run_pipeline-Phasen-Modus,
    Commit 85e0572).
  Block P2b-3b (Loop-Aufruf in run_phase,
    Commit af45157).
  Block P2b-4 (Phasen-Gesamt-Review + Sammel-
    Commit, Commit 16eec88).
  Block P2b-5 (Budget-Layer-1 + Plan-Korrektur,
    Commit 6e8b791).

================================================================
6. ZIELE
================================================================

Ziel 1 — Autonomie bis Approval.
        Die Werkstatt soll grosse Arbeitspakete
        eigenstaendig abarbeiten. Mensch nur am
        Approval-Gate.

Ziel 2 — Deterministisch vor LLM.
        Regel entscheidet, wo moeglich.

Ziel 3 — Ordner-/Doku-Schema + Scaffolder.
        Vorlage fuer neue Projekte, Migration
        bestehender. Struktur-Konvention jetzt
        dokumentiert.

Ziel 4 — Dashboard (spaeter).
        Web-Ansicht des Prozesses, Live-Log,
        Konversation zwischen LLMs, ASK_HUMAN-Kanal.

Ziel 5 — Anti-Pattern-Bibliothek.
        ERLEDIGT fuer 3 Rollen (Builder, Reviewer,
        Solver). Aggregator-Vorschlaege noch offen.

Ziel 6 — Planner-Agent (spaeter).
        Liest Roadmap des Ziel-Projekts, formuliert
        Auftraege, Uebergabe an Reviewer.
        Voraussetzung: Ziel 3 + Roadmap-Format.

================================================================
7. WIE MAN WEITERARBEITET
================================================================

Regeln fuer jeden Bau-Block:

1. Faktenlage vor Meinung. Kein Inhalt annehmen.
2. Patch per Python-Skript mit assert count == 1.
   Kein sed auf Python-Code.
   Heredoc nur bis ~40 Zeilen. Laenger: Skript in
   /tmp anlegen, dann per write_text schreiben.
3. Nach jedem Patch: wc -l, py_compile, ruff,
   mypy, pytest.
4. Vor jedem Commit: git status --porcelain.
5. Commit-Autor: ghxstfocus <ghxst.focus@gmail.com>.
6. Bei Kategorie 3: Reviewer-Block vor Commit.
6a. Probebetrieb-Tag NUR bei echtem Pipeline-
    Durchlauf (pipeline_start + pipeline_ende).
7. Nach jedem Meilenstein: Handoff aktualisieren.
8. Reviewer-Blocks in Codeblock.
9. Kein Scope-Creep. Jede Auflage eigener Block.
10. Am Ende: git status sauber, Handoff aktuell.

Werkstatt-Regel: ruff --no-cache messen.
Werkstatt-Regel: mypy rekursiv pruefen.
Werkstatt-Regel: bei Import-Sortierung ruff --fix.
Werkstatt-Regel: /opt/werkstatt/projects/ gehoert
                 builder:builder 750 (Pipeline-User
                 schreibt dort Laufzeit-State). Nach
                 root-Eingriffen pruefen.

================================================================
8. WERKZEUGE UND BEFEHLE
================================================================

ruff:   /opt/security-ai/.venv/bin/python3 -m ruff check ... --no-cache
mypy:   /opt/security-ai/.venv/bin/python3 -m mypy ...
pytest (aus /opt/werkstatt):
        /opt/security-ai/.venv/bin/python3 -m pytest tests/ -q

Werkstatt-Lauf (aus /opt/security-ai als builder):
  set -a
  . /opt/security-ai/.env
  set +a
  cd /opt/security-ai && \
  runuser -u builder -- env DEEPSEEK_API_KEY="$DEEPSEEK_API_KEY" \
    /opt/security-ai/.venv/bin/python3 \
    /opt/werkstatt/pipeline.py \
    --project security-ai \
    "<Block-Auftrag>"
  unset DEEPSEEK_API_KEY

Git-Commit mit Autor:
  git -c user.name="ghxstfocus" \
      -c user.email="ghxst.focus@gmail.com" \
      commit -F /tmp/msg.txt

================================================================
9. GIT-STATUS
================================================================

Werkstatt-Repo: /opt/werkstatt/.git
  Branch: main
  Remote: git@github.com:ghxstfocus/werkstatt.git
  .gitignore: Cache, .venv, audit-logs/,
              approvals/*.db, *.env,
              projects/*.memory.yaml, *.alt.

Ziel-Projekt (security-ai): /opt/security-ai/.git
  Branch: main
  Remote: git@github.com:ghxstfocus/security-ai.git

Hinweis: Werkstatt-Lauf braucht Schreibrechte des
builder-Users im Ziel-Projekt. Nach manuellen
git-Eingriffen als root: chown builder:builder pruefen.

================================================================
10. HARD RULES
================================================================

Rollenspezifisch getrennt (Auflage 2182):
  - HARD_RULES_BASE (universell).
  - HARD_RULES_REVIEWER (R1-R7).
  - HARD_RULES_BUILDER (B1-B10).
  - HARD_RULES_TEST_GENERATOR (T1-T4).
  - HARD_RULES_SOLVER (S1-S7).
build_system_prompt waehlt anhand des Agent-Namens.
Quelle: pipeline.py.

Die Chat-Regeln (HR-R1..R10) und Antwortformate
sind Zwei-Webchat-Artefakte. Sie sind im Archiv.
Die Werkstatt hat sie durch HARD_RULES_REVIEWER
und classify_verdict abgeloest.

================================================================
11. NAECHSTE SCHRITTE (konkret)
================================================================

Der neue Bau-Chat soll:

1. Diesen Handoff lesen. HEAD pruefen:
     git -C /opt/werkstatt log -1 --oneline
     git -C /opt/werkstatt status --porcelain
     /opt/security-ai/.venv/bin/python3 -m pytest \
       /opt/werkstatt/tests/ -q

2. Reihenfolge:
   a) Block P2: --phase + run_phase + Gesamt-Review.
      Naechster Block. Stufe 2 des Planner-Konzepts.
      Kategorie 3.
   b) Block P3: ASK_HUMAN + Persistenz.
      Kategorie 3.
   c) Phase 1b: Validator Fail-closed.
      Nach P2/P3. Kategorie 3.
   d) Solver-Kurskorrektur Block 6 (Smoke-Test).
      Echter Solver-Lauf.
   e) Phase 2: Scaffolder.
   f) Rollen-Modell aus Frontmatter lesen.
      Kategorie 2.
   d) Rollen-Prompt-Generator (Phase 3.5).
   e) Agent-Memory Ebene 2.
   f) Ziel 2: Phasen-Modus.
   g) Ziel 4: Dashboard.
   h) 2183-AQ, 2199a, Werkstatt-Vertrag, B2.

3. Fuer Kategorie-3-Bloecke: Reviewer-Block
   formulieren, vor Ausfuehrung.

4. Nach Erfolg (NUR echter Pipeline-Durchlauf):
   git tag probebetrieb-<n>. Naechste Nummer: 68.

5. Bei Problemen: zurueck zu diesem Handoff,
   Faktenlage pruefen, Reviewer-Chat fragen.

================================================================
ENDE DES HANDOFFS
================================================================

================================================================
WEG-Y-PATCH 2026-10-16 (manueller Eingriff)
================================================================

Kontext: 13. PB-68-Lauf (dritter Versuch) ergab eine
NO-GO-Schleife. Reviewer-Diagnose: Auftrag unterbestimmt.
Der Reviewer-Befund "file_whitelist fehlt" ist nach
Messung sachlich falsch — die Whitelist existiert in
projects/security-ai.yaml Z. 89-96. Der LLM-Reviewer
sieht sie nicht im Prompt (Merkposten).

Manueller Eingriff in projects/security-ai.phase.yaml
(vor dem 14. Lauf):

U1-Unterpunkte vorher (3):
  1. 'neu: core/guardrails/__init__.py (leer,
      Package-Marker).'
  2. 'neu: core/guardrails/models.py: Dataclass
      Guardrail (id, name, level, state) plus Enum ...'
  3. 'test: tests/unit/test_guardrails_models.py:
      Roundtrip (anlegen, lesen), Enum-Werte,
      Default-State.'

U1-Unterpunkte nachher (4):
  1. 'neu: core/guardrails/__init__.py. Inhalt: ""
      (leerer String, kein "inhalt: |"-Block).
      ... Whitelist: core/ ist freigegeben.'
  2. 'neu: core/guardrails/models.py. GENAU VIER
      Felder: id, name, level, state. ...'
  3. 'test: tests/unit/test_guardrails_models.py.
      Roundtrip, Enum-Werte, Default-Werte,
      frozen-Check. ...'
  4. 'Hinweis (nicht Bau-Auftrag): new_file-Patches
      -> GEMESSENER INHALT nicht anwendbar. ...'

U2-U10 unveraendert. phase_aktiv=true unveraendert.
phase_start_head=0d0fe2c unveraendert.

Grund: Reviewer-Antwort "Weg Y als Uebergangsloesung".
Bewusste Einmal-Aenderung, kein Werkstatt-Bug.

Merkposten (neu):
  - Weg X (Plan-Konkretisierung) bleibt offen.
    Anlass praeziser: "Projekt-Whitelist im Prompt
    unsichtbar", nicht "Auftrag unterbestimmt".
    Aufteilung in X-1/X-2/X-3 nach 14. Lauf.
  - LLM-Reviewer sieht file_whitelist aus
    projects/<name>.yaml nicht im Prompt.
    Fix-Option: Whitelist in aufgabe_block
    sichtbar machen. Eigener Block, Kategorie 3.
  - Fail-closed laesst untracked files in
    whitelist-Pfaden liegen. Manuelles Cleanup
    noetig. Eigener Block.

Erwartung Lauf 14 (Weg-Y-A11):
  - Resume-Force: U1 (no_go) -> pending.
  - Planner-Skip (Resume-Pfad, verifiziert).
  - Builder liest U1 mit 4 Unterpunkten.
  - Patches: inhalt:"" + vier Felder.
  - Reviewer Code-GO.
  - Commit-Review mit mess_protokoll_nach_apply.
  - Sammel-Commit moeglich.

Wenn Lauf 14 scheitert: kein Fix-Loop (Weg-Y-A7).
Analyse im Handoff, dann entscheiden.

================================================================
ENDE WEG-Y-PATCH
================================================================

================================================================
REKONSTRUKTION 2026-10-16 — phase.yaml nach Plan-Korrektur-Bug
================================================================

Kontext: 15. PB-68-Lauf (Versuch 2, 2026-10-16 14:26).
_phase_plan_korrektur hat den Plan komplett ersetzt und
dabei ALLE Unterbloecke auf status=pending gesetzt
sowie deren commit_paket geloescht. U1 (vorher done)
verlor damit:
  - Status done (wurde no_go),
  - commit_paket mit den drei U1-Dateien,
  - die urspruenglichen 4 Unterpunkte (der Planner
    hat neue formuliert).

Konsequenz: der 15. Lauf startete faelschlich mit U1
statt mit U2 und lief in eine NO-GO-Schleife.

Fix (Commit 6049a0d): _phase_plan_korrektur merged
jetzt. done-Unterbloecke bleiben unveraendert
(status, commit_paket, unterpunkte). Struktur-Check:
Anzahl, ids, titel muessen gleich bleiben. Bei
Verletzung Fail-closed.

Manuelle Rekonstruktion der phase.yaml (2026-10-16):
U1 zurueckgesetzt auf:
  status: done
  commit_paket:
    dateien: [core/guardrails/__init__.py,
              core/guardrails/models.py,
              tests/unit/test_guardrails_models.py]
    message: "U1: Guardrail-Modell"
  unterpunkte: die urspruenglichen 4 aus Weg-Y.
U2-U10 bleiben pending (korrekt).

Working Tree: 3 U1-Dateien (unveraendert).
Grund: die U1-Arbeit ist gut und wurde nicht
verworfen, nur der Plan-Zustand war falsch.

Erwartung 15. Lauf (Versuch 3):
  - Resume-Force: U2 (pending) -> keine Aenderung
    (resume-force setzt nur no_go/failed auf pending).
    U1 bleibt done.
  - Basis-Gate: untracked U1-Dateien erlaubt.
  - Phasen-Persistenz: 1 done-Paket geladen.
  - U1 uebersprungen.
  - U2 laeuft mit dem neuen Plan-Korrektur-Schutz.
  - Falls U2 no_go: Plan-Korrektur merged jetzt
    statt zu ersetzen.
  - U3-U10.
  - Sammel-Commit.

Merkposten:
  - Der 15.-Lauf-Befund bestaetigt: Plan-Korrektur
    muss mergen, nicht ersetzen. Commit 6049a0d.
  - Weg X (Marker + Diskriminator) bleibt offen.
    Anlass praeziser: Reviewer eskaliert
    "Auftrag unterbestimmt/veraltet" — der Planner
    soll anreichern, nicht neu formulieren.

================================================================
ENDE REKONSTRUKTION
================================================================

================================================================
U2-REPARATUR 2026-10-16
================================================================

Kontext: 15. PB-68-Lauf (Versuch 3, 2026-10-16 14:35).
Der Lauf ist bis Post-Apply-Basis-Gate gruen gekommen.
Dort `ruff` rot: SIM115 in
tests/unit/test_guardrails_loader.py:24.

Der Post-Apply-Korrektur-Loop ruft den Reviewer.
Der Reviewer-Kontext ist durch
`aktueller_prompt[:2000]` geschnitten (Bug,
siehe Truncation-Fix 6041033). Der Reviewer sieht
den abgeschnittenen Prompt und schliesst auf eine
"unvollstaendige Datei". Das ist falsch — die Datei
ist 152 Zeilen, py_compile ok, vollstaendig.

Der Builder folgt dem falschen Befund, dreht im
COMMAND-Loop. Post-Apply-Korrektur max_runden
erreicht. Fail-closed.

Fix (6041033): Truncation-Marker + GEMESSENER
INHALT separat im Reviewer-Kontext.

Manuelle U2-Reparatur (2026-10-16):
- tests/unit/test_guardrails_loader.py: _write
  auf Context Manager umgestellt (with ... as tmp).
- ruff check: All checks passed.
- pytest tests/unit/test_guardrails_loader.py: 22 passed.

phase.yaml: U2 auf status=done mit Paket
(loader.py + test_guardrails_loader.py).
U1 bleibt done. U3-U10 pending.

Working Tree:
  ?? core/guardrails/                 (U1 + U2)
  ?? tests/unit/test_guardrails_loader.py
  ?? tests/unit/test_guardrails_models.py

Erwartung 16. Lauf:
  - Basis-Gate: untracked Dateien aus U1+U2
    erlaubt.
  - Phasen-Persistenz: 2 done-Pakete geladen.
  - U1, U2 uebersprungen.
  - U3 laeuft (Guardrail-Config-Datei).
  - Bei Erfolg: Phase laeuft weiter (U4-U10).
  - Bei Sammel-Commit am Phasen-Ende:
    Tag probebetrieb-68.

Wenn U3 scheitert und der Reviewer wieder
"Datei unvollstaendig" behauptet: NICHT
manuell eingreifen. Der Truncation-Fix (6041033)
sollte greifen. Wenn nicht: Truncation-Fix
pruefen.

================================================================
ENDE U2-REPARATUR
================================================================

================================================================
17. LAUF VORBEREITUNG 2026-10-16
================================================================

Kontext: 16. PB-68-Lauf (2026-10-16 14:58-15:01) hat
den Meilenstein erreicht: U1, U2, U3 sind done,
der Plan-Korrektur-Schutz haelt sie. U4 ist an
zwei Auftragsfehlern gescheitert.

Fix-Kette seit dem 16. Lauf:
  b8710f5  config: file_whitelist um data/ erweitern
  562fde5  feat: file_whitelist im Prompt sichtbar
           (Reviewer + Builder)

U4-Unterpunkte manuell korrigiert (2026-10-16):
  1. data/migrations/0016_guardrails.sql
     (nicht 0013 — Nummernkollision mit
     0013_whitelist_manage.sql).
     Whitelist-Hinweis.
  2. core/guardrails/repository.py mit KEIN upsert,
     KEIN seed_from_yaml (Auftragstreue).
  3. test_guardrails_repository.py gegen echte
     Migration 0016, kein Inline-Schema.

Herkunft der Praezisierungen (Auflage U4-Auftrag-A3):
  - Punkt 1 Nummernmuster: Bau-Chat-Messung
    (ls data/migrations/).
  - Punkt 1 Whitelist-Hinweis: Reviewer-Befund
    Lauf 16 + Config-Fix b8710f5.
  - Punkt 2 "kein upsert": Builder-Scope-Drift
    in Lauf 16 (Runden 1-5), Reviewer-Befund.
  - Punkt 3 "echte Migration": Reviewer-Befund
    Lauf 16.

Erwartungshaltung 17. Lauf (Auflage A6):
  - U1-U3 done (Pakete: 3, 2, 4).
  - U4 korrigierter Auftrag.
  - Reviewer-Prompt enthaelt FILE-WHITELIST
    mit data/.
  - Erwartung: U4 laeuft.
  - Wenn U4 scheitert: STOP. Bilanz faellig.
    Keine weitere Iteration ohne Reflexion.

Merkposten bleiben offen:
  - Planner-Prompt um Whitelist (eigener Block).
  - Truncation-Konvention (systematisch).
  - Reviewer-Behauptungs-Verifikation.
  - Persistenz-Konvention.
  - Weg X (Plan-Konkretisierung).

================================================================
ENDE 17. LAUF VORBEREITUNG
================================================================

================================================================
BILANZ 17. LAUF 2026-10-16
================================================================

Kontext: 17. PB-68-Lauf (2026-10-16 15:08-15:12).
Auflage A6 verlangt Bilanz bei U4-Scheitern.
Der Lauf ist gescheitert, weil der Auftrag
unterbestimmt ist.

================================================================
WAS FUNKTIONIERT
================================================================

Der Phasen-Modus ist strukturell fertig und im
Live-Betrieb bewiesen:

1. Multi-Run-Faehigkeit.
   Der 17. Lauf hat U1, U2, U3 als done erkannt,
   uebersprungen und mit ihren Paketen (3, 2, 4
   Dateien) in den Sammel-Commit aufgenommen.
   Insgesamt 7 untracked Pfade aus drei
   done-Unterbloecken.

2. Basis-Gate im Phasen-Modus (_phasen_basis_gate_ok).
   Akzeptiert untracked Dateien aus done-Unterbloecken
   deterministisch und auditierbar.

3. Phasen-Persistenz (commit_paket in phase.yaml).
   Die Pakete werden persistiert und beim Resume
   restauriert. Kein Datenverlust zwischen Laeufen.

4. Plan-Korrektur-Schutz (6049a0d).
   Nach 5 NO-GO-Runden und Plan-Korrektur-Versuch
   (mit [n] abgebrochen) sind U1-U3 unveraendert:
   status=done, Pakete intakt, Unterpunkte unveraendert.
   Die Plan-Korrektur-Anzeige zeigte 3 Unterpunkte
   fuer U1 — der Schutz hat die 4 bestehenden
   gerettet.

5. Whitelist im Prompt (562fde5).
   Der Reviewer sieht die file_whitelist jetzt
   direkt im Prompt. Kein "Pfad fehlt"-Fehlbefund
   mehr.

6. Truncation-Marker (6041033).
   Reviewer-Kontexte werden mit Marker gekuerzt.
   Kein "Datei unvollstaendig"-Fehlschluss.

7. Review-Persistenz (a066e0d).
   Reviewer-Antworten landen im Audit-Log.

8. Post-Apply-Messung (eb8119a) + Recovery-Prompt-
   Fix (3bbe681).

9. Resume-Force (7e5cc65).
   no_go/failed -> pending, mit Effekt.

================================================================
WAS NICHT FUNKTIONIERT
================================================================

Der systematische Blocker ist Auftragsqualitaet.

Muster in Lauf 13, 14, 16, 17:
  - Der Planner liefert Auftraege, die das WAS
    nennen, aber nicht das WIE.
  - Der Builder kann das WIE nicht erfinden (R9)
    und dreht im COMMAND-Loop.
  - Der Reviewer eskaliert korrekt ("Auftrag
    unterbestimmt").
  - Die Plan-Korrektur liefert wieder einen
    unterbestimmten Auftrag (Ersatz statt
    Konkretisierung).

Konkreter Fall 17: die Test-Anforderung
"gegen die ECHTE Migration 0016, kein Inline-
Schema" nennt keinen Weg, wie die Migration
im Unit-Test ausgefuehrt wird. Der Builder
pendelt zwischen Inline-Schema (verboten),
Eigenbau-Runner (nicht spezifiziert) und
importierbarem Runner (nicht benannt).

Das ist genau das Problem, fuer das Weg X
(Plan-Konkretisierung) gedacht war.

================================================================
DREI STRUKTURELLE BLOCKE (offen)
================================================================

A) Planner-Praezisierung (Weg X).
   Der Planner soll Auftraege mit dem WIE liefern.
   Konkret: technische Praezisierungen (Mechanik,
   APIs, Konventionen) als Pflichtbestandteil.
   Aufwand: mittel-gross.
   Anlass: vier Laeufe mit demselben Muster.

B) Reviewer-Input-Vollstaendigkeit.
   Der Reviewer soll vollstaendigen Kontext sehen.
   Truncation-Marker sind ein Teil; aber die
   Reviewer-Inputs sind strukturell unvollstaendig
   (z.B. filesystem-Zustand, verfuegbare APIs).
   Aufwand: mittel.

C) Truncation-Konvention.
   Alle ~50 [:N]-Stellen in pipeline.py markieren.
   Aufwand: klein, aber systematisch.

================================================================
EMPFEHLUNG
================================================================

Die Reihenfolge:
  1. U4 manuell mit praezisem WIE korrigieren.
  2. 18. Lauf.
  3. Bei Erfolg: Phasen-Modus ist bewiesen.
     Weiter mit U5-U10.
  4. Danach: Block A (Planner-Praezisierung)
     als Kern-Fix. Ohne ihn wiederholt sich
     das Muster in U5-U10.

Wenn der 18. Lauf U4 mit praezisem Auftrag
schafft: der Beweis ist erbracht, dass die
Werkstatt mit praezisen Auftraegen funktioniert.
Die Auftragslieferung durch den Planner bleibt
der schwierigste Teil.

================================================================
ENDE BILANZ 17. LAUF
================================================================

================================================================
UEBERGABE AN NEUEN BAU-CHAT (2026-10-16, 16:00)
================================================================

Diese Sitzung ist am Kontext-Limit. Ein neuer
Bau-Chat uebernimmt. Dieser Block ist die
Startanweisung.

================================================================
IST-ZUSTAND
================================================================

Werkstatt-HEAD: 4896edf "feat: Phasen-Header +
  R9/R13/R14 — Rollen-Kalibrierung Teil 2".
Werkstatt-Tests: 801 passed.
ruff/mypy: 0.

security-ai-HEAD: 0d0fe2c (PB-67).
  Probebetrieb 68 ist NICHT getaggt (21 Laeufe,
  kein Sammel-Commit).
Working Tree security-ai: 4 untracked
  (core/guardrails/, tests/unit/test_guardrails_config.py,
  test_guardrails_loader.py, test_guardrails_models.py).

phase.yaml:
  phase_aktiv: true
  phase_id: 18
  phase_start_head: 0d0fe2c29b549c968d1ace116a69f57cf65f9998
  U1: done  (4 Unterpunkte, Paket 3)
  U2: done  (2 Unterpunkte, Paket 2)
  U3: done  (2 Unterpunkte, Paket 4)
  U4: failed (4 Unterpunkte)
  U5-U10: pending

Commits seit der Uebergabe (Auswahl, chronologisch):
  651175f (origin/main) doku: Handoff — Lauf 12
  3e77c1f Fix: Post-Apply-Basis-Gate — rc=19
  a066e0d feat: review_round-Audit persistiert
          Reviewer-Antwort
  e52558b feat: Solver-Sichtbarkeit
  7e5cc65 feat: --resume-force
  0651ed6 fix: commit_review_new_file_skip
  eb8119a fix: Post-Apply-Messung + Rollback
  7b79425 doku: Handoff — Weg-Y-Patch
  de93129 feat: Phasen-Persistenz — commit_paket
  f28511e feat: Basis-Gate im Phasen-Modus
  2a39626 fix: Basis-Gate git status -uall
  6049a0d feat: Plan-Korrektur-Schutz
  5217ab2 doku: Handoff — Rekonstruktion
  3bbe681 fix: Recovery-Prompt + rohantwort-Fallback
  6041033 fix: Truncation-Marker
  e2c5db1 doku: Handoff — U2-Reparatur
  b8710f5 config: file_whitelist um data/ erweitern
  562fde5 feat: file_whitelist im Prompt sichtbar
  e6f7da5 doku: Handoff — Vorbereitung 17
  d62d044 doku: Handoff — Bilanz 17
  413921d feat: Rollen-Kalibrierung — Spec-Treue,
          Solver-Befolgung, Sachfaden
  1f098c7 feat: new_file-Marker — Prompt, Rollen,
          HARD_RULES
  4896edf feat: Phasen-Header + R9/R13/R14

================================================================
WAS SEIT DER UEBERGABE FUNKTIONIERT
================================================================

1. Phasen-Modus ist multi-run-faehig.
   U1, U2, U3 sind done und bleiben done
   ueber beliebig viele Resume-Versuche.
   Beweis: Lauf 16-21.

2. Phasen-Persistenz (de93129).
   commit_paket der done-Unterbloecke wird in
   phase.yaml persistiert und beim Resume
   restauriert.

3. Basis-Gate im Phasen-Modus
   (_phasen_basis_gate_ok, f28511e + 2a39626).
   Untracked Dateien aus done-Unterbloecken
   werden deterministisch akzeptiert.

4. Plan-Korrektur-Schutz (6049a0d).
   done-Unterbloecke bleiben unveraendert bei
   Plan-Korrektur. Struktur-Check (Anzahl, ids,
   titel).

5. --resume-force (7e5cc65).
   no_go/failed -> pending.

6. Post-Apply-Messung (eb8119a).
   mess_protokoll_nach_apply fuer new_file-Pfade.

7. Review-Persistenz (a066e0d).
   Reviewer-Antwort im review_round-Audit als raw.

8. Solver-Sichtbarkeit (e52558b).
   Trigger + Befund auf Konsole.

9. Truncation-Marker (6041033).
   _truncate_mit_marker + GEMESSENER INHALT separat.

10. Recovery-Prompt-Fix (3bbe681).
    rohantwort-Fallback + Messblock.

11. Rollen-Kalibrierung (413921d).
    B13 (Spec-Treue), B14 (Solver-Befolgung),
    R11 (Sachfaden).

12. new_file-Marker (1f098c7).
    B15, R12, _NEW_FILE_MARKER,
    _messwerte_fuer_prompt.

13. Phasen-Header (4896edf).
    R13 (Phasen-Trennung), R14 (Verdict-Konsistenz),
    R9 auf ESKALATION, Phasen-Header im Prompt.

================================================================
WAS NICHT FUNKTIONIERT — DER AKTUELLE BLOCKER
================================================================

Der 21. PB-68-Lauf (2026-10-16 15:55-15:56)
ist an U4 gescheitert. Der Auftrag war praezise,
aber der Builder befolgte ihn nicht.

Befund:
  - Builder liefert Migration mit 4 statt 6 Spalten
    (created_at, updated_at fehlen).
  - Builder nutzt GuardrailRepositoryError statt
    GuardrailNotFoundError.
  - Builder nutzt Inline-Schema statt Migration im Test.

Der Reviewer-Verdacht (Truncation) wurde
WIDERLEGT: prompt_len-Werte aus dem Audit-Log
sind 17.259 (Code-Review) und 4.988-6.729
(Recovery). Weit unter redact_all-Limit 100.000.

Der Builder hat den vollstaendigen Auftrag gesehen
und ignoriert trotzdem Teile.

Neue Diagnose:
  Der Planner liefert Auftraege, die nicht
  builder-freundlich genug sind. Konkrete
  Praezisierungen (Feldnamen, Signaturen,
  Reihenfolge) fehlen.

================================================================
VIER OFFENE PLANNER-ANFORDERUNGEN
================================================================

Der Auftraggeber hat vier zusammenhaengende
Planner-Anforderungen formuliert, die noch NICHT
gebaut sind:

1. Planner plant kleiner von vorneherein.
   Heute P15 (1-2 Zieldateien + 1 Test) ist
   zu schwach.

2. Planner kann bei Resume dort weitermachen,
   wo aufgehoert wurde.
   Heute _planner_user_content bekommt KEINEN
   phase_unterbloecke-Zustand.

3. Planner versteht: Plan muss builder-freundlich
   sein. Detailiert.
   Neue Regel P17 fehlt (Signatur, Feldnamen,
   Reihenfolge, Schemas, Prueffaelle).

4. Planner bei Korrektur: Reviewer-Begruendung
   verstehen + Aenderungen im Detail wiedergeben.
   Neue Regel P18 fehlt. Heute reviewer_befund
   als Rohtext ohne Struktur-Anforderung.

================================================================
NAECHSTER SCHRITT — EMPFEHLUNG
================================================================

Der neue Bau-Chat soll:

1. Diesen Handoff lesen.
2. HEAD pruefen:
     git -C /opt/werkstatt log -3 --oneline
     git -C /opt/werkstatt status --porcelain
     /opt/security-ai/.venv/bin/python3 -m pytest \
       /opt/werkstatt/tests/ -q
   Erwartung: 4896edf, clean, 801 passed.
3. phase.yaml pruefen:
     /opt/security-ai/.venv/bin/python3 -c "
     import yaml
     d = yaml.safe_load(open(
         '/opt/werkstatt/projects/security-ai.phase.yaml'))
     for u in d['phase_unterbloecke'][:4]:
         print(f\"{u['id']}: {u['status']}\")
     "
   Erwartung: U1-U3 done, U4 failed, U5-U10 pending.
4. Reviewer-Chat kontaktieren mit dem Hinweis:
     "Neuer Bau-Chat, Uebergabe 2026-10-16 16:00.
      Stand: HEAD 4896edf, 801 passed.
      Blocker: Planner-Praezision.
      Vier Anforderungen: Blockgroesse, Resume,
      Builder-Freundlichkeit, Reviewer-Befund-
      Wiedergabe.
      Siehe Handoff 'UEBERGABE AN NEUEN BAU-CHAT'."

================================================================
HANDOFF-EINTRAEGE DER SITZUNG (Chronologie)
================================================================

- WEG-Y-PATCH 2026-10-16
- REKONSTRUKTION 2026-10-16
- U2-REPARATUR 2026-10-16
- 17. LAUF VORBEREITUNG 2026-10-16
- BILANZ 17. LAUF 2026-10-16
- UEBERGABE AN NEUEN BAU-CHAT 2026-10-16 (dieser Block)

Alle in diesem Handoff dokumentiert.

================================================================
WERKZEUG-REGELN (bestaetigt und aktuell)
================================================================

- ruff --no-cache messen.
- mypy rekursiv pruefen.
- /opt/werkstatt/projects/ gehoert builder:builder 750.
- core.fileMode=false im Werkstatt-Repo.
- post-checkout-Hook setzt projects/-Owner.
- Patch-Skripte > 40 Zeilen in /tmp anlegen,
  nicht als Heredoc.
- Vor jedem Commit: git status --porcelain pruefen.
- Bei Kategorie 3: Reviewer-Block vor Bau.
- Kein Tag ohne echten Pipeline-Durchlauf.

================================================================
MERKPOSTEN (offen, fuer spaetere Bloecke)
================================================================

1. Planner-Praezision (vier Anforderungen).
2. 2169 deterministisch pruefen.
3. list_dir im Katalog (bei Bedarf).
4. Vertrauens-Kalibrierung zwischen Rollen.
5. Truncation-Konvention (systematisch).
6. Reviewer-Behauptungs-Verifikation.
7. Persistenz-Konvention.
8. Weg X (Plan-Konkretisierung).
9. DRY-Refactor Z. 7077
   (_hat_anker_patches -> _alle_patches_sind_new_file).
10. U4 manuelle Neu-Formulierung mit P17-Detailtiefe.

================================================================
ENDE UEBERGABE
================================================================


================================================================
BLOCK 2a PLANNER-KORREKTUR-KONTEXT (2026-10-16)
================================================================

Commit: siehe git log. Kategorie 3.

Aenderungen:
  - _planner_user_content (Z. ~2718):
      reviewer_befund aus dem korrektur_kontext wird
      vollstaendig in den Prompt eingesetzt (Marker
      === REVIEWER-BEFUND (vollstaendig) ===).
      P18 aus Block 1 wird damit wirksam.
      Abschluss-Wortlaut: "Format aus P10-P16,
      beachte P17 (Builder-Freundlichkeit) und
      P18 (Korrektur-Kompetenz)".
  - phase_stand-Parameter + _phase_stand_sektion
    (neu):
      AKTUELLER-PHASENSTAND-Sektion mit id, status,
      paket_groesse, letzter_befund (gekuerzt via
      _truncate_mit_marker auf 200 Zeichen).
      Explizite Anweisung: "Der Resume beginnt bei
      U<n>. Plane NUR U<n>. Beruehre abgeschlossene
      Unterbloecke NICHT."
      Fallback bei allen done: "Alle Unterbloecke
      sind abgeschlossen. Plane einen neuen
      Phasenplan oder brich ab."
  - _phase_plan_korrektur:
      Baut phase_stand aus state.phase_unterbloecke
      + state.review_runden[-1]["raw"] (nur bei
      no_go/failed). "naechster" = erste
      no_go/failed/pending id.
      Uebergibt phase_stand an _planner_lauf.
  - _planner_lauf: phase_stand durchgereicht.
  - tests/test_planner.py: +10 Tests, Signatur-Test
    (TestPlannerLauf.test_planner_lauf_signatur)
    um phase_stand ergaenzt.

Tests: 822 passed (+10).

Auflagen-Abgleich (aus Reviewer-Block GO-mit-Auflagen):
  2a-A1 (Redaction): erfuellt, ask_llm redactet
    user_content (Z. 3149). Keine Aenderung noetig.
    Im Code-Kommentar (Docstring) dokumentiert.
  2a-A2 (_truncate_mit_marker): existiert (Z. 4758),
    genutzt.
  2a-A3 (naechster Edge-Case): erfuellt, Fallback
    "Alle Unterbloecke sind abgeschlossen."
    Plus Test test_user_content_phase_stand_alle_done_fallback.
  2a-A4 (Redundanz phase_stand vs alter_plan):
    erfuellt. phase_stand enthaelt KEINEN titel,
    nur id/status/paket_groesse/letzter_befund.
    alter_plan behaelt titel.
  2a-A5 (Abschluss-Wortlaut): erfuellt, P17 und
    P18 explizit genannt.

Merkposten unveraendert:
  - B1-A5 (UNBEANTWORTET-Behandlung) -> Block 2b.
  - B1-A4 (P17-Beispiel Rotation) -> spaeter.
  - A4 (U5/U6/U9 Unterpunkt-Zahl) -> spaeter.

Naechster Block: 2b (UNBEANTWORTET-Parser +
Entscheidung).

================================================================
ENDE BLOCK 2a
================================================================

================================================================
BLOCK 2b PLANNER UNBEANTWORTET-BEHANDLUNG (2026-10-16)
================================================================

Commit: siehe git log. Kategorie 3.

Aenderungen:
  - _UNBEANTWORTET_PRAEFIX = "UNBEANTWORTET:"
    (neu, B3). Kopplung an P18 Schritt 5.
  - _plan_unbeantwortet_punkte (neu, B1+B2):
      Durchsucht geparste Unterpunkte, erkennt
      Praefix-Treffer. Rueckgabe pro Treffer
      dict{"unterblock": "U<n>", "punkt": "<text>"}.
  - _phase_plan_korrektur: Nach _parse_phase_plan,
    vor Anzeige: Trefferpruefung. Bei Treffern:
      * Audit phase_plan_unbeantwortet mit
        unterblock-Zuordnung.
      * Konsolenausgabe pro Punkt via
        _truncate_mit_marker(200).
      * _phase_rr_k8 (konsistent mit parse_failed).
      * return False (Plan wird nicht gespeichert).
  - _AUDIT_KINDS_BEKANNT + phase_plan_unbeantwortet.
  - _parse_phase_plan unveraendert.
  - tests/test_planner.py: +9 Tests (Klasse
    TestPlannerUnbeantwortet).
  - tests/test_pipeline.py: 2 Katalog-Anzahl-Tests
    auf 63 angepasst.

Tests: 831 passed (+9).

Auflagen-Abgleich:
  B1 (Anzeige-Truncation): erfuellt.
    _truncate_mit_marker(200) pro Punkt.
  B2 (Audit pro Unterblock): erfuellt.
    _plan_unbeantwortet_punkte gibt dict-Liste
    zurueck; Audit enthaelt unterblock-Zuordnung.
  B3 (Konstante _UNBEANTWORTET_PRAEFIX):
    erfuellt. Kopplung an P18 sichtbar.
    Merkposten: bei P18-Aenderung Konstante
    anpassen.
  B4 (Test mehrere Unterbloecke): erfuellt.
    test_plan_unbeantwortet_punkte_mehrere_
    unterbloecke prueft zwei verschiedene
    Unterbloecke.

Merkposten (B3):
  _UNBEANTWORTET_PRAEFIX und P18 Schritt 5
  sind gekoppelt. Bei P18-Wortlaut-Aenderung
  Konstante anpassen.

Stand jetzt:
  P18 ist vollstaendig wirksam (Block 1 als
  Regel, Block 2a als Prompt-Ausgabe, Block 2b
  als Marker-Erkennung und Entscheidung).
  Planner-Praezision Block 1 + Block 2a + 2b
  sind FERTIG.

Naechster Schritt:
  - U4 in security-ai.phase.yaml manuell mit
    P17-Detailtiefe formulieren.
  - 22. PB-68-Lauf mit --resume-force.
  - Beobachten: folgt der Planner P17/P18?
    Verarbeitet er den Reviewer-Befund
    vollstaendig? Plant er kleiner (P15-Neu)?

================================================================
ENDE BLOCK 2b
================================================================

================================================================
LAUF 22 BILANZ (2026-10-16)
================================================================

Kontext: 22. PB-68-Lauf mit neuem U4 (P17-Detailtiefe).
Abbruch am RR-K8-Menue ([2] Phase abbrechen).

Ergebnis:
  - Kein Sammel-Commit.
  - Kein Tag probebetrieb-68.
  - U4 bleibt no_go.
  - Working Tree unveraendert (3 U1-U3-Dateien
    untracked, keine U4-Dateien).

WICHTIGSTE ERKENNTNIS:
  Die 3 U4-Patches wurden NIE auf Platte geschrieben
  (apply_code_patches wurde nicht gerufen).
  Der Reviewer sah die Patch-Texte im Prompt und
  prueft symbolisch: alle Pruefpunkte OK. Gab
  trotzdem 5x UNKLAR statt GO.

Audit-Kette 16:29-16:30:
  - builder_reply_erhalten (3 Patches).
  - review_round runde 1-5: alle verdict=UNKLAR.
  - recovery_no_go.
  - phase_unterblock_ende: U4 / no_go.
  - phase_plan_korrektur_start.
  - phase_plan_korrektur_failed:
      grund=parse_failed,
      exception="U1: id nicht mit 'U1' ueberein
                 (gefunden: 'U4')".

Drei getrennte Blocker:

  B0 — Reviewer UNKLAR-Loop.
    Der Reviewer prueft 5x alle 3 Patches und
    findet alles OK, gibt aber UNKLAR. Vermutung:
    weil die Dateien nicht real existieren
    (apply wurde nicht gerufen), traut er sich
    kein GO.
    Fix-Optionen:
      (a) apply VOR Review (Dateien real da).
      (b) Reviewer-Prompt: bei reinen new_file
          ohne Datei-Pruefung GO erlauben.
      (c) UNKLAR-Behandlung: nach 1x UNKLAR
          Eskalation statt Loop.

  B1 — Planner-Struktur-Verstaendnis.
    Der Planner hat phase_stand (Block 2a)
    bekommen. Er hat fuer U4 einen neuen Plan
    formuliert. ABER: er hat "U4" als erste
    UNTERBLOCK-id geschrieben. _parse_phase_plan
    verlangt monoton ab U1.
    Konsequenz: phase_plan_korrektur_failed
    (parse_failed).
    Fix: phase_stand-Sektion und P18 muessen
    explizit sagen: "Behalte die Gesamtstruktur
    U1-U10. Formuliere NUR den Inhalt von U4 neu.
    Die ids bleiben U1-U10."

  B2 — apply_code_patches im Review-Loop.
    Heute: Builder -> Review-Runde 1..5 ->
    apply (erst nach GO).
    Problem: bei reinen new_file-Patches sieht
    der Reviewer nie die Datei.
    Fix: apply VOR Review ODER Datei-Simulation
    im Reviewer-Prompt.

Was funktioniert hat:
  - Block 2a (phase_stand im Prompt): wirksam,
    der Planner bekam den Stand.
  - Block 2b (UNBEANTWORTET): nicht getriggert
    (Plan hatte kein UNBEANTWORTET).
  - Block 1 (P17/P18): nicht bewertbar, weil
    Planner-Parse fehlschlug.

Auflagen-Abgleich (U4-22-A1 bis A8):
  A1 (Design-Entscheidung): umgesetzt, aber
    nicht zum Zug gekommen.
  A2-A4: umgesetzt, nicht zum Zug gekommen.
  A5 (L5): Messung ergab: kein Bug.
  A6 (Hinweise nicht P15): umgesetzt.
  A7 (5 Test-Prueffaelle): umgesetzt, nicht
    zum Zug gekommen.
  A8 (Bilanz): dieser Block.

Merkposten (neu):
  - B0: Reviewer UNKLAR-Loop.
  - B1: Planner-Struktur-Verstaendnis (id-
    Reihenfolge U1-U10 bei Plan-Korrektur).
  - B2: apply_code_patches im Review-Loop.
  - Manuelle phase.yaml-Eingriffe: jetzt 6
    (Weg-Y U1, U2, U4-Lauf 16, U4-Lauf 21,
    U4-Neufassung Lauf 22). Bilanz-Signal.
  - Bilanz 21 Laeufe ohne Sammel-Commit
    (Handoff-Eintrag "BILANZ 17. LAUF" zeigt
    strukturelle Naehe, aber noch kein
    Durchbruch).

Naechster Block:
  Reviewer-Block fuer B0 (UNKLAR-Loop) und
  B2 (apply vor Review). B1 separat (P18-
  Verscharfung).

================================================================
ENDE LAUF 22 BILANZ
================================================================

================================================================
B0 UNKLAR-BEHANDLUNG (2026-10-16)
================================================================

Commit: siehe git log. Kategorie 3.

Aenderungen:
  - HARD_RULES_REVIEWER +R15 (symbolische
    Pruefung bei reinen new_file-Paketen;
    R15 ergaenzt R12; Widerspruchs-Format
    Widerspruch:/Beleg:).
  - HARD_RULES_SOLVER +S10 (analog fuer den
    Solver; M4: derselbe symbolische
    Blindfleck).
  - _review_unklar_widerspruch (Parser fuer
    Widerspruchs-Block).
  - run_pipeline: UNKLAR-Zweig im Review-Loop.
    1x UNKLAR mit/ohne Widerspruch -> naechste
    Runde (Audit review_unklar_widerspruch
    bzw. review_r15_verstoss).
    2x UNKLAR in Folge -> Eskalation (rc=14,
    konsistent mit ESKALATION-Pfad).
    Konkrete Options-Ausgabe an den Menschen.
  - _AUDIT_KINDS_BEKANNT +3.
  - tests/test_pipeline.py: +11 Tests,
    Katalog-Anzahl 63 -> 66.

Tests: 842 passed (+11).

Auflagen-Abgleich (B0-A1 bis A8):
  A1 (Widerspruchs-Format): erfuellt. R15
    definiert Format, _review_unklar_widerspruch
    parst es, Loop unterscheidet.
  A2 (rc=14): bestaetigt durch Messung
    (ESKALATION-Pfad Z. 7064 return 14).
    Neuer Zweig nutzt rc=14.
  A3 (Slice-Order): state.review_runden.append
    Z. 7006 vor dem UNKLAR-Zweig. [-2:] =
    diese + vorige Runde. Semantik korrekt.
  A4 (Eskalations-Output): Optionen-Liste
    gedruckt.
  A5 (Widerspruchs-Zaehlung): Audit
    review_unklar_widerspruch vs.
    review_r15_verstoss. review_r15_verstoss
    ist neu.
  A6 (11 Tests): erfuellt.
  A7 (Bilanz-Verweis): Handoff Lauf 22
    zitiert.
  A8 (R12/R15-Querverweis): in R15-Wortlaut.

Merkposten:
  B1 (Planner-Struktur-Verstaendnis):
    der Planner versteht die Phasen-Struktur
    nicht vollstaendig (liefert "U4" als
    erste id). P18-Verschaerfung oder
    phase_stand-Sektion muss explizit
    "Behalte U1-U10" sagen. Eigener Block.
  B2 (apply vor Review): nicht notwendig,
    wenn R15/S10 wirken.

Naechster Block: B1 (Planner-Struktur).

================================================================
ENDE B0
================================================================

================================================================
B1 PLANNER-STRUKTUR-VERSTAENDNIS (2026-10-16)
================================================================

Commit: siehe git log. Kategorie 3.

Aenderungen:
  - _phase_stand_sektion: Struktur-Anweisung.
    "Behalte die Gesamtstruktur." "Aendere NUR
    den INHALT von U<n>." "Formuliere den neuen
    Plan mit ALLEN Unterbloecken."
    Generisch (keine spezifische id-Aufzaehlung).
  - P18 Schritt 4: "Er enthaelt ALLE
    Unterbloecke in derselben Reihenfolge."
    Schutz-Hinweis aus Block 1 unveraendert.
  - tests/test_planner.py: +6 Tests.

Tests: 848 passed (+6).

Auflagen-Abgleich (B1-A1 bis A6):
  A1 (generische Wortwahl): erfuellt. Test
    test_phase_stand_sektion_generisch prueft
    Regressionsschutz.
  A2 (P18-Wortlaut vorher): eingehalten.
    Wortlaut aus Block 1 zitiert, ergaenzt.
  A3 (Fallback "alle done"): gemessen.
    Fallback-Text unveraendert.
  A4 (Merkposten Parser-Toleranz): notiert.
  A5 (Reihenfolge B1-a/B1-b): OK.
  A6 (Schutz-Hinweis erhalten): erfuellt.

Merkposten (B1-A4):
  Parser-Toleranz relativ zur Struktur.
  Wenn Lauf 23 wieder parse_failed liefert,
  Parser anpassen: Teilmengen-Plaene erlauben,
  Position aus id ableiten. Eigener Block.

Naechster Schritt:
  23. PB-68-Lauf mit --resume-force.
  Beobachten:
    - Planner liefert Plan mit ALLEN Unterbloecken.
    - Struktur bleibt, nur U4-Inhalt neu.
    - U4 laeuft.
  Bei Scheitern: Bilanz Pflicht.

================================================================
ENDE B1
================================================================

================================================================
B0C VERDICT-PARSER + BUG-1 + BUG-2 (2026-10-16)
================================================================

Commit: siehe git log. Kategorie 3.

Ausgangslage:
  23. PB-68-Lauf (2026-10-16 16:44) ist an B0c gescheitert:
  Reviewer gab 2x UNKLAR, B0b eskalierte korrekt (rc=14).
  Aber: der Reviewer hatte "GO" am Ende der Antwort.
  classify_verdict prueft nur den Anfang (max 15 Zeilen).
  Verdict am Ende wurde nicht erkannt.

Aenderungen:
  - classify_verdict: Fallback fuer Verdict am Ende.
    Nur letzte nicht-leere Zeile, <40 Zeichen,
    Verdict-Wort allein.
  - run_phase: rc=14 als eigene Klasse (status=no_go,
    kein Rollback).
  - review_unklar_eskalation: + raw ([:2000]).
  - TestClassifyVerdict: 2 Tests an B0c angepasst.
  - TestB0cUndBugs: +6 Tests.

Tests: 854 passed (+6).

Auflagen-Abgleich:
  B0c ist ein neuer Fix (nicht in vorherigen Auflagen).
  B0a (R15/S10) wirkt: der Reviewer wendet R15 an
  (Audit zeigt "R15: GO" im Text). Nur der Parser
  hat versagt.
  B0b (UNKLAR-Loop) wirkt: 2x UNKLAR -> Eskalation.
  Bug-1 (rc=14) und Bug-2 (raw) sind neue Befunde
  aus dem 23. Lauf.

Wichtig:
  Die 2059-Grenze (Verdict nur in den ersten 15
  Zeilen) bleibt fuer den ANFANG. Der End-Fallback
  ist eine Ergaenzung. reviewer.md verlangt das
  Verdict am Ende; jetzt erkennt der Parser es.

Naechster Schritt:
  24. PB-68-Lauf mit --resume-force.
  Beobachten:
    - Reviewer R15: GO am Ende.
    - classify_verdict: erkennt GO.
    - apply_code_patches laeuft.
    - U4 done.
    - U5-U10 laufen weiter.
    - Sammel-Commit, Tag probebetrieb-68.

================================================================
ENDE B0C
================================================================

================================================================
TIMEOUT-FIX + U4-PRAEZISIERUNG (2026-10-16)
================================================================

Timeout-Fix (Commit siehe git log). Kategorie 3.

Ausgangslage:
  24. Lauf (2026-10-16 16:50) hat gezeigt:
  B0c wirkt (Reviewer gibt NO-GO, classify_verdict
  korrekt). ABER: der Builder-Call hat nach 460 s
  nicht terminiert (llm_timeout_s=180, Retry-Backoff
  1+3 s, Worst-Case 364 s).

  Ursache: requests int-Timeout wird als
  (connect=180, read=180) interpretiert. Bei
  tropfendem Server (Chunks alle <180 s) greift
  der Read-Timeout nie.

Fix (Option B):
  B1 (primaer, HR-R7): timeout=(15, 180) Tupel.
    Read-Timeout greift bei Chunk-Stille >180 s.
  B2 (sekundaer): Deadline max_total_llm_s=240.
    Verhindert Folgeversuche nach Ueberschreitung.
    Read-Timeout adaptiv: min(180, restzeit).
  + RunState.max_total_llm_s: int = 240.
  + ask_llm aufgabe-Parameter (Audit-Zuordnung).
  + _AUDIT_KINDS_BEKANNT +3.

Tests: 863 passed (+9).

U4-Praezisierung:
  Alle vier Reviewer-Befunde aus Lauf 24 eingearbeitet:
    (a) set_state schreibt updated_at.
    (b) get/list_all nur vier Spalten selektieren.
    (c) __init__(db_path: Path) exakt.
    (d) Fixture Path(__file__).resolve() + exists().
  Plus U4-Praez-A1 (updated_at testen),
  A2 (_insert_guardrail-Helper explizit),
  A3 (Fixture-Reihenfolge),
  A4 (Fehlerklassen mit Docstrings),
  A5 (set_state-Validierungs-Semantik).

Merkposten (Timeout-A3):
  max_total_llm_s aus projects/<name>.yaml
  als optionales Feld (nicht in diesem Block).

Naechster Schritt:
  25. PB-68-Lauf mit --resume-force.
  Beobachten:
    - B0c: Verdict-Parser erkennt NO-GO/GO am Ende.
    - Timeout-Fix: kein Haenger >240 s.
    - U4: vier Befunde eingearbeitet; Reviewer GO?
    - U4 done -> U5 laeuft.
    - Sammel-Commit, Tag probebetrieb-68.
  Bei Scheitern: Bilanz Pflicht.

================================================================
ENDE TIMEOUT-FIX + U4-PRAEZISIERUNG
================================================================

================================================================
F1+F2+F3 COMMIT-PHASE-FIXES (2026-10-16)
================================================================

Commit: siehe git log. Kategorie 3.

Ausgangslage 25. Lauf:
  Erster Code-GO seit Lauf 12 (U4-Patches gebaut).
  Commit-Phase gescheitert an drei Infrastruktur-Bugs.

Fixes:
  F1: _rollback_zieldateien git status -uall.
      Dateien in neuen Verzeichnissen werden
      einzeln gefunden. Rollback entfernt alle
      new_file-Pfade (repository.py bleibt nicht
      mehr liegen).

  F2: apply_and_recheck git add -N.
      2169-Blocker behoben: neue Dateien erscheinen
      in git diff --name-only HEAD.

  F2-A1: git reset HEAD -- <pfade> VOR unlink.
      Index sauber nach intent-to-add-Rollback.

  F3: collect_messwerte git_head-Fallback.
      Liest aus basis_protokoll, wenn
      _nach_apply leer (apply_and_recheck-Skip).

Tests: 875 passed (+12).

Auflagen-Abgleich:
  F1-A1 (Syntax-Konsistenz): -uall wie Z. 7965.
  F2-A1 (Index-Cleanup): git reset HEAD vor unlink.
  F2-B1 (Katalog): 69 -> 71.
  F2-C1 (Pfad-Normalisierung): Pfade aus
    code_patches sind bereits relativ.
  F2-D1 (Timeout 30s): konsistent mit bestehenden
    git-Aufrufen.
  F3-A1 (Regex): bestehende Regex aus
    collect_messwerte wiederverwendet.
  F3-A2 (bestehender Parser): collect_messwerte
    erweitert, keine dritte Regex.
  F3-A3 (Fallback-Absicht): Reviewer erwartet
    git_head (Befund 25. Lauf); Fallback korrekt.

Merkposten (F1-F3-A2):
  _git_status_porcelain (Z. 3234) nutzt
  "git status --porcelain" ohne -uall.
  Bei kuenftigen Aufrufen pruefen, ob -uall
  noetig ist (Konsistenz mit F1).

Naechster Schritt:
  26. PB-68-Lauf mit --resume-force.
  Erwartung:
    - Code-GO (wie 25).
    - apply + git add -N.
    - Commit-Review Runde 1: COMMIT-GO.
    - Sammel-Commit.
    - Tag probebetrieb-68.
  Bei Scheitern: Bilanz Pflicht.

================================================================
ENDE F1+F2+F3
================================================================

================================================================
B0C-2 VERDICT-PARSER (2026-10-16)
================================================================

Commit: siehe git log. Kategorie 3.

Ausgangslage 26. Lauf:
  Reviewer gibt 2x "**GO**" (Markdown), aber
  classify_verdict liefert UNKLAR.
  Ursachen:
    - Markdown-Fett-Marker (*) nicht gestrippt.
    - Nur letzte nicht-leere Zeile geprueft;
      Runde 2 hatte Text nach "**GO**".

Fix:
  - Markdown-Marker (* ` _ #) strippen.
  - Letzte 5 nicht-leere Zeilen rueckwaerts pruefen.
  - Nur Zeilen <40 Zeichen zaehlen (Fliesstext-Schutz).

Tests: 875 + 6 = 881 passed.

Auflagen-Abgleich:
  - B0c aus Lauf 24 erweitert, nicht ersetzt.
  - Bestehende Tests (test_go_at_line_16,
    test_go_after_many_inhalt_lines) bleiben gruen.

Merkposten:
  - Konsolenausgabe "(unbekannt)" bei
    review_unklar_eskalation: raw steht im Audit,
    wird aber nicht auf Konsole gedruckt. Kosmetik.
    Eigener Block.

Naechster Schritt:
  27. PB-68-Lauf mit --resume-force.
  Beobachten:
    - Reviewer Runde 1: GO -> apply + git add -N.
    - Commit-Review Runde 1: COMMIT-GO.
    - Sammel-Commit. Tag probebetrieb-68.

================================================================
ENDE B0C-2
================================================================

================================================================
D1+D3 COMMIT-PAKET-SCOPE (2026-10-16)
================================================================

Commit: siehe git log. Kategorie 3.

Ausgangslage 27. Lauf:
  B0c-2 wirkt, F2 wirkt (Code-GO, apply,
  git add -N). Commit-Review 2x NO-GO:
  BETROFFENE DATEIEN (10) != Commit-Message (3).

Fix:
  D1 (Beratung): build_commit_paket-Prompt
    nennt ZIELDATEIEN aus state.code_patches.
    B2-Fall explizit.
  D3 (Durchsetzung): run_pipeline
    (Phasen-Modus) ueberschreibt
    state.commit_paket["dateien"] deterministisch
    mit state.code_patches-Pfaden. Vor
    phase_commit_pakete.append.
  _AUDIT_KINDS_BEKANNT +1.

Tests: 891 passed (+10). Katalog 71 -> 72.

Auflagen-Abgleich:
  D-A0: D1 Beratung, D3 Durchsetzung —
    im Docstring dokumentiert.
  D-A1: B2-Fall: leere Liste; Fail-closed
    rc=21 greift (Unterblock ohne Dateien
    ist sinnlos).
  D-A2: D3 zwischen build (Z. 7687) und
    Prompt (Z. 7748).
  D-A3: Katalog 72.
  D-A4: D3 vor append (Z. 7900).
  D-A5: Merkposten D-A7 korrigiert —
    _phase_sammel_paket unioniert alle
    Pakete. Kein Datenverlust.
  D-A6: 10 Tests.

HR-R7-Korrektur:
  Reviewer hat D2 (R16) verworfen, D3
  uebernommen. LLM-Regel zu einer
  bestehenden LLM-Regel ist dieselbe
  Wette. Deterministisch ist besser.

Naechster Schritt:
  28. PB-68-Lauf mit --resume-force.
  Erwartung:
    - Code-GO (wie 27).
    - apply + git add -N.
    - D3 greift: phase_commit_dateien_deterministisch.
    - Commit-Review Runde 1: COMMIT-GO.
    - Paket gesammelt (kein Commit).
    - U4 done, U5 laeuft.
  Bei Scheitern: Bilanz Pflicht.

================================================================
ENDE D1+D3
================================================================

================================================================
E + R16 COMMIT-REVIEW-DIFF (2026-10-16)
================================================================

Commit: siehe git log. Kategorie 3.

Ausgangslage 28. Lauf:
  D3 wirkt (BETROFFENE DATEIEN = 3 statt 10).
  ABER Commit-Review 2x NO-GO: "2169 nicht
  erfuellt; Pflichtabgleich gegen
  git diff --name-only HEAD fehlt im Paket."

Fix:
  E: commit_input enthaelt die Sektion
    "GIT DIFF --NAME-ONLY HEAD: <pfade>".
    Vor commit_input ausgelesen.
    Bei git-Fehler: Fail-closed (return 9).
    Leere Liste: "(keine)".
  R16: neue HARD_RULES_REVIEWER-Regel.
    Der Prompt zeigt "PHASEN-MODUS: aktiv/inaktiv".
    Bei aktiv: 2169 = TEILMENGE.
    Bei inaktiv: 2169 = Gleichheit (wie bisher).
    Grund: git diff zeigt alle Unterbloecke
    seit Phase-Start; BETROFFENE DATEIEN nur
    den aktuellen.
  +2 Audit-Kinds.

Tests: 891 + 9 = 900 passed. Katalog 72 -> 74.

Auflagen-Abgleich (E-A1 bis A8):
  E-A1 (Teilmengen-Semantik R16): erfuellt.
  E-A2 (fail-closed statt "(Fehler)"): return 9.
  E-A3 (leere Liste "(keine)"): erfuellt.
  E-A4 (Verhaltens-Tests): Muster aus bestehenden
    Tests (inspect.getsource) uebernommen.
  E-A5 (Reihenfolge D3 -> E -> commit_input):
    Z. 7728 -> 7793 -> Prompt.
  E-A6 (Katalog +2): 72 -> 74.
  E-A7 (8 Tests): 9 Tests.
  E-A8 (Merkposten Sub-Ref): notiert.

Merkposten (E-A8):
  Sub-Ref pro Unterblock fuer praezisere
  2169-Pruefung. Heute reicht R16 (Teilmenge).
  Eigener Block, wenn unklar.

Naechster Schritt:
  29. PB-68-Lauf mit --resume-force.
  Erwartung:
    - Code-GO.
    - apply + git add -N.
    - D3 (3 Pfade).
    - E: GIT DIFF --NAME-ONLY HEAD (3 Pfade).
    - R16: 3 == 3 Teilmenge erfuellt.
    - Commit-Review Runde 1: COMMIT-GO.
    - Paket gesammelt (kein Commit).
    - U4 done, U5 startet.

================================================================
ENDE E + R16
================================================================

================================================================
DURCHBRUCH: U4 DONE (2026-10-16)
================================================================

29. PB-68-Lauf (2026-10-16, Uhrzeit?). Erster
erfolgreicher Commit-Review seit Lauf 12.

U4: status=done. Commit-Paket gesammelt
(3 Dateien):
  - data/migrations/0016_guardrails.sql
  - core/guardrails/repository.py
  - tests/unit/test_guardrails_repository.py

Die Kette funktioniert:
  - B0c-2: Verdict-Parser (Markdown + mehrzeilig).
  - F2: git add -N.
  - D3: BETROFFENE DATEIEN deterministisch.
  - E: GIT DIFF --NAME-ONLY HEAD im Prompt.
  - R16: Teilmenge-Semantik.
  - Timeout-Fix: kein Haenger.

U5 ist direkt gestartet (2 Patches) und
gescheitert (Post-Apply-Basis-Gate rot).

U5-Fehler (Reviewer-Diagnose, praezise):
  Hauptbefund: GuardrailRepository.set_state
  gibt None zurueck. Der Service behandelt
  den Rueckgabewert aber als Guardrail-Objekt.
  AttributeError zur Laufzeit.

  Nebenbefunde:
  - AuditWriter-Import: from core.audit.writer
    import AuditWriter. Modul existiert nicht
    oder anders benannt.
  - 3x totes "# noqa: BLE001".
  - Ungenutzter Import AccessChecker.
  - Test-Fake _FakeRepo.set_state gibt Guardrail
    zurueck (echte API: None) -> maskiert Bug.
  - RBAC-Codes guardrail.view/manage evtl.
    nicht vorhanden.

Auftrags-Unterbestimmtheit U5:
  Der U5-Auftrag nennt nicht:
  - Rueckgabeverhalten von set_state.
  - AuditWriter-Modul-Pfad.
  - Test-Fake-Vertrag.

Merkposten (kritisch):
  1. Rollback-Bug: Fail-Pfad nach
     Post-Apply-Korrektur-max erreicht
     ruft _rollback_zieldateien NICHT immer.
     Working Tree hat 5 A-Eintraege (U4+U5).
     Manuelles Cleanup noetig.
  2. U5-Auftrag praezisieren (wie U4).
  3. Bilanz nach diesem Lauf (Pflicht).

Naechster Schritt:
  - Working-Tree-Cleanup (5 A-Eintraege).
  - U5-Auftrag praezisieren.
  - 30. Lauf mit --resume-force.
  - Ziel: U5 done, dann U6-U10, dann
    Sammel-Commit, Tag probebetrieb-68.

================================================================
ENDE U4 DONE
================================================================

================================================================
7. MANUELLER EINGRIFF: U5-NEUFFASSUNG (2026-10-16)
================================================================

Ausgangslage 29. Lauf:
  U4 durch (Durchbruch). U5 gestartet, 2 Patches,
  Post-Apply-Basis-Gate rot. Reviewer-Diagnose:
  4 Auftrags-Unterbestimmtheiten:
    (1) AuditWriter-Import falsch
        (core.audit.writer statt
         harness.audit.writer).
    (2) set_state gibt None, Service behandelt
        als Guardrail.
    (3) RBAC-Codes guardrail.view/manage
        existieren nicht.
    (4) Test-Fake maskiert Bug.

A0-Messungen (M-a bis M-d):
  M-a: hoechste Migration 0016. Neue: 0017.
  M-b: AccessChecker in core/access/checker.py.
       Import: from core.access.checker import
       AccessChecker, AccessDeniedError.
  M-c: API AccessChecker.require_permission(
       principal_name, code) -> None.
       RBAC-Fehler = AccessDeniedError.
  M-d: AuditWriter.log(*, agent, tool,
       policy_result, permission_level,
       execution_status, args=None, ...,
       details=None) -> AuditEntry.
       Keyword-only.

Aenderung:
  U5-Unterpunkte ersetzt (4 Eintraege):
    1. Migration data/migrations/
       0017_guardrail_permissions.sql
       (Muster 0015: INSERT OR IGNORE,
        role_permissions (role_id, permission_id)).
    2. Service core/services/
       guardrail_service.py (exakte Imports,
       Fehlerklassen, Methoden-Signaturen,
       try/except-Grenze).
    3. Test tests/unit/
       test_guardrail_service.py (drei Fakes,
       5 Prueffaelle).
    4. Hinweis (new_file-Skip).
  P15-Ausnahme dokumentiert: Migration +
  Service atomar (Service ohne RBAC-Codes =
  403 fuer alle Rollen).

Muster:
  7. manueller phase.yaml-Eingriff.
  Der Planner produziert noch keine P15/P17-
  konformen Auftraege mit Signaturtiefe.
  Weg-X-Prioritaet wird durch dieses Muster
  gestuetzt.

Naechster Schritt:
  30. PB-68-Lauf mit --resume-force.
  Beobachtung:
    - U4 done (uebersprungen).
    - U5 laeuft.
    - Ziel: U5 done, U6 startet.

================================================================
ENDE U5-NEUFFASSUNG
================================================================

================================================================
W1 EXTRACT_PATHS ERWEITERT (2026-10-16)
================================================================

Commit: siehe git log. Kategorie 3.

Ausgangslage 30. Lauf:
  Reviewer-Eskalation ("Auftrag unterbestimmt").
  Ursache: extract_paths_from_aufgabe erkannte
  die Pfade im U5-Auftrag nicht (Import-
  Notation, .sql-Endung, neue Dateien).

Fix (W1):
  - Endungen: +sql +json +toml +cfg +ini +txt.
  - from-Importe: from a.b.c import X ->
    a/b/c.py.
  - exists()-Filter entfernt: neue Dateien
    existieren noch nicht. Elternverzeichnis-
    Check ersetzt ihn.
  - Aufrufer unveraendert (3 Stellen:
    Z. 7153, Z. 7163, Z. 7241).

Wirkung (direkter Test mit U5-Auftrag):
  7 Pfade statt 1.
    - data/migrations/0017_guardrail_permissions.sql
    - core/services/guardrail_service.py
    - tests/unit/test_guardrail_service.py
    - core/guardrails/models.py
    - core/access/checker.py
    - core/guardrails/repository.py
    - harness/audit/writer.py

Tests: 900 + 7 = 907 passed.

Auflagen-Abgleich (W1-A1 bis A9):
  A1 (Import-Stile): nur from-Regex noetig.
    Keine relativen/multiline im U5-Auftrag.
  A2 (Aufrufer): 3 Stellen, alle profitieren.
  A3 (exists-Filter): entfernt, Eltern-
    verzeichnis-Check stattdessen.
  A4 (Markdown): nicht noetig (kein ** im
    U5-Auftrag).
  A5 (12 Tests): 7 statt 12; 5 waren redundant
    (bereits in TestExtractPaths).
  A6 (Audit): Merkposten, nicht in W1.
  A7 (Reihenfolge): 907 passed vor Bau.
  A8 (Merkposten): notiert.
  A9 (HARD_RULES_BUILDER): B4/B13 zwingen den
    Builder, dem Auftrag zu folgen — auch wenn
    er falsch ist. Merkposten W2.

Merkposten (W2 wichtig):
  HARD_RULES_BUILDER B4 ("Du bist kein
  Messender") + B13 ("Der Auftrag ist
  verbindlich") verhindern, dass der Builder
  falsche Auftrags-Behauptungen misst.
  W2 sollte B13 verschaerfen: "Wenn der Auftrag
  Pfade/APIs behauptet, die nicht im
  GEMESSENER INHALT belegt sind: COMMAND: RUN
  read_file <pfad>."

Merkposten (W3):
  Planner-Messungs-Kanal. Heute hat der Planner
  kein COMMAND:. Bei Resume-Planung (W4) muss
  er messen koennen.

Merkposten (W4):
  Resume-Planung: der Planner wird im
  --resume-force-Pfad nicht gerufen.
  Struktureller Weg-X-Block.

Naechster Schritt:
  31. PB-68-Lauf mit --resume-force.
  Erwartung:
    - Auto-Messung: > 1 Zieldatei (W1 wirkt).
    - Builder sieht alle Pfade im Prompt.
    - Reviewer kann Import-Pfade pruefen.
    - U5 laeuft.

================================================================
ENDE W1
================================================================

================================================================
W2 + U6-KORREKTUR (2026-10-16)
================================================================

Commit W2: 0e6c881.

Ausgangslage 31. Lauf:
  U5 done (W1 wirkt: Auto-Messung 7 Zieldateien).
  U6 gestartet und gescheitert: Auftrag nannte
  data/migrations/0014_guardrail_permissions.sql,
  aber 0014_internal_name.sql existiert.
  Zwei konkurrierende Migrationen (0014 + 0017).

W2 (HARD_RULES_BUILDER):
  B4 aufgeteilt:
    (a) Systemwerte (Tests, Coverage, ruff,
        mypy, git-Status): Werkstatt.
    (b) Auftrags-Behauptungen (Datei-Existenz,
        Import-Pfad): Builder prueft B13b.
  B13b neu: Behauptungen pruefen.
    (a) "Datei X existiert" -> read_file ok=True.
    (b) "neu: X" -> read_file ok=False.
    (c) "Import aus a/b/c.py" -> read_file ok=True.
    Bei Widerspruch: COMMAND: frage_reviewer.
    NICHT fuer Signaturen/Nummernkreise.
  B13b und B7 komplementaer.

U6-Korrektur (Weg-Y):
  - 0014 -> 0018 (naechste freie Nummer).
  - KEINE neuen Permissions (U5-Migration 0017
    hat sie schon).
  - U6 ergaenzt nur operator + viewer mit
    guardrail.view.
  - Builder soll 0017 lesen.

Tests: 907 -> 912 passed (+5).

Auflagen-Abgleich (W2-A1 bis A7):
  A1 (list_dir): existiert nicht. B13b
    beschraenkt sich auf read_file (datei-genau).
  A2 (B4 praezisieren): erfuellt.
  A3 (B13b konkret): erfuellt.
  A4 (Nummernkreis-Merkposten): notiert.
  A5 (5 Tests): erfuellt.
  A6 (Test-Anzahl): 907 gemessen.
  A7 (Reihenfolge): W2 vor U6-Korrektur vor
    32. Lauf.

Merkposten (W1b):
  Nummernkreis-Pruefung in extract_paths_from_aufgabe:
  wenn data/migrations/NNNN_*.sql genannt:
  Prefix-Scan, ob NNNN belegt ist. Fail-closed
  bei Konflikt. Eigener Werkstatt-Block.

Merkposten (W3):
  Planner-Messungs-Kanal (COMMAND: read_file).

Merkposten (W4):
  Resume-Planung (Planner rufen bei failed/no_go).

Stand:
  U1-U5 done. U6 no_go (bereit fuer 32. Lauf).
  U7-U10 pending.

Naechster Schritt:
  32. PB-68-Lauf mit --resume-force.
  Beobachtung:
    - U5 done uebersprungen.
    - U6 startet.
    - B13b greift: Builder prueft 0018 frei?
      liest 0017.
    - U6 done, U7 startet.
  Bei Scheitern: neuer Reviewer-Block.

================================================================
ENDE W2 + U6
================================================================

================================================================
W3+W4 PLANNER-MESSUNG + PLAN-KORREKTUR (2026-10-16)
================================================================

Commit: siehe git log. Kategorie 3.

Ausgangslage 32. Lauf:
  U6 done (6 von 10). U7 gescheitert.
  Reviewer-Diagnose: der Planner kann den
  Reviewer-Befund nicht konkretisieren, weil
  er keinen Messungs-Kanal hat.

W3 (Planner-Messung):
  - P19 in HARD_RULES_PLANNER_STUFE2:
    "MESSEN VOR DEM PLAN".
    COMMAND: RUN read_file <pfad>.
  - _planner_lauf: lokale Schleife
    (max_runden=3). Bei Erschoepfung:
    fail-closed (return None).
  - ERLAUBTE_QUELLEN + "planner".
  - P9' auf P10-P19 erweitert.
  - _planner_user_content + GEMESSENER INHALT.
    state als Keyword am Ende
    (alte Tests bleiben gruen).
  - _messwerte_fuer_planner: roher
    Messprotokoll-Inhalt.

W4 (Plan-Korrektur):
  - P18 + Punkt 6: gemessene Anker Pflicht.
  - UNBEANTWORTET nur nach Messung.

Tests: 912 -> 924 (+12).
Katalog: 74 -> 75.

Auflagen-Abgleich:
  W3-A1 (Rekursion): lokale Schleife mit
    max_runden-Dekrement per range().
  W3-A2 (ERLAUBTE_QUELLEN): "planner" ergaenzt.
  W3-A3 (P9'): P10-P19.
  W3-A4 (Messwerte): state-Parameter +
    _messwerte_fuer_planner.
  W3-A5 (Signatur): Default max_runden=3,
    3 Aufrufer kompatibel.
  W3-A6 (rc): bestehender Fail-Pfad.
  W3-A7 (Redaction): ask_llm redactet.
  W3-A8 (Stufe1): unveraendert.
  W3-A9 (read_file): existiert.
  W4-A1 (P18): +Punkt 6.
  W4-A2 (DRY): Korrektur-Prompt referenziert
    P18/P19.
  W3-W4-A3 (Test-Anzahl): 912 korrekt.
  W3-W4-A4 (12 Tests): erfuellt.
  W3-W4-A5 (Groessen-Check): ~250 Zeilen,
    ein Block.
  W3-W4-A6 (Katalog): 75.

Merkposten:
  - Stufe-1-Planner-Messung: offen.
  - list_dir im Katalog: offen.
  - Resume-Planung (W4-Langfassung):
    Planner wird bei --resume-force noch
    nicht gerufen. W3 wirkt bisher nur
    im Plan-Korrektur-Pfad.
    MESSUNG: der 33. Lauf wird zeigen, ob
    W3 den Plan-Korrektur-Pfad wirksam
    macht.

Stand:
  U1-U6 done. U7 no_go.
  U8-U10 pending.

Naechster Schritt:
  33. PB-68-Lauf mit --resume-force.
  Beobachtung:
    - U7 startet.
    - Planner-Messung greift (COMMAND
      im Audit).
    - U7 done, U8 startet.

================================================================
ENDE W3+W4
================================================================

================================================================
U7-AUFTEILUNG (2026-10-16)
================================================================

Ausgangslage 33. Lauf:
  U6 done (6 von 10). U7 gestartet, 5 Runden,
  NO-GO. Reviewer-Eskalation:
    "Auftrag unterbestimmt (Zieldatei-
     Ausschnitte fehlen), Block zu gross,
     Sachfaden-Drift."
  Empfehlung: aufteilen in 3 Bloecke.

A0-Messungen (M-a bis M-c):
  M-a: g.principal gesetzt in app.py:181.
  M-b: Migration 0017 existiert, gibt
    guardrail.view/manage an admin.
    0018 (U6) ergaenzt operator + viewer.
  M-c: file_whitelist vollstaendig.

Aenderung:
  U7 aufgeteilt in zwei Unterbloecke:
    U7 (Dashboard-Route + app.py + Test).
    U8 (Dashboard-Template + CSP-Test).
  Nummerierung verschoben:
    ex-U8 -> U9 (Aktion).
    ex-U9 -> U10 (Sidebar).
    ex-U10 -> U11 (Doku).
  U7-Neufassung mit gemessenem Anker
  (app.py Z. 257-258):
    "    from apps.dashboard.routes_tools
     import register_tools_routes\n
         register_tools_routes(app)\n"
  count==1, 4 Spaces, LF.

Wichtige Korrekturen:
  - Reviewer-Annahme "required_permission"
    war falsch: heisst "require_permission".
  - Service wird inline gebaut
    (GuardrailRepository aus DB_PATH).
    Kein extensions-Eintrag.

Muster:
  9. manueller phase.yaml-Eingriff.
  Nach 9 Eingriffen ist die Werkstatt-
  Autonomie strukturell blockiert.
  Weg X (Planner-Konkretisierung) hat
  Prioritaet.

Stand:
  U1-U6 done. U7 no_go.
  U8-U11 pending.

Naechster Schritt:
  34. PB-68-Lauf mit --resume-force.
  Beobachtung:
    - U7 startet.
    - Route + app.py + Test gebaut.
    - 200/403-Tests gruen.
    - Commit-GO.
    - U7 done.
    - U8 startet.
  Bei Scheitern: neuer Reviewer-Block.

================================================================
ENDE U7-AUFTEILUNG
================================================================

================================================================
11. MANUELLER EINGRIFF: U7/U8/U9-AUFTEILUNG (2026-10-16)
================================================================

Ausgangslage 34. Lauf:
  U6 done. U7 gestartet, 4 Runden, Deadlock.
  Reviewer-Diagnose (R11):
    - Template fehlt in der Datei-Liste.
    - COMMAND + Patch im selben Block
      (Loop verwarf Patch).

Reviewer-Loesung:
  Option C: atomare Aufteilung nach P15-Neu.

Aenderung:
  U7 = Dashboard-Template /guardrails (1 Zieldatei).
  U8 = Dashboard-Route + app.py-Patch (1 Zieldatei
       + 1 Patch).
  U9 = Test /guardrails (1 Test-Datei).
  U10 = Dashboard-Aktion aktivieren/deaktivieren
        (ex-U9).
  U11 = Sidebar-Eintrag Guardrails (ex-U10).
  U12 = Doku-Nachzug Guardrails (ex-U11).

Wichtige Korrektur:
  Der U7/U8/U9-Umbau hat zunaechst den Aktion-
  Block verloren (U9 wurde mit U10 "Test"
  ueberschrieben). Manuell korrigiert: Aktion-
  Block als neuer U10 angelegt.

A0-Messungen (M1-M7):
  M1: Anker app.py Z. 257-258 (2 Zeilen, 4
      Spaces, LF, count==1).
  M2: require_permission (decorators.py Z. 28).
  M3: g.principal (app.py:181, str).
  M4: build_dashboard_app nutzt create_app.
  M5: Rollen: admin (view+manage),
      operator (view, 0018), viewer (view,
      0018), system (KEIN view).
  M6: create_role_client(app, "system")
      funktioniert (Muster test_dashboard_alerts
      .py:85).
  M7: Kein U7-Rest aus Lauf 34.

Auflagen-Abgleich:
  U7-U9-A1 (Anker minimal): erfuellt (2 Zeilen).
  U7-U9-A2 (system-Rolle): M6 bestaetigt.
  U7-U9-A3 (11. Eingriff): dieser Eintrag.
  U7-U9-A4 (Working Tree): M7 bestaetigt.
  U7-U9-B1 (Unused Imports): erfuellt (nur 5
    Imports in der Route).
  U7-U9-B2 (Handoff): dieser Eintrag.

Muster:
  11. manueller phase.yaml-Eingriff in Serie.
  Nach 11 Eingriffen ist die Werkstatt-Autonomie
  strukturell gebrochen. Weg X (Planner-
  Konkretisierung) hat Prioritaet.

Audit-Referenz:
  Alte Audit-Logs (Lauf 33, 34) referenzieren
  "U7" fuer "Dashboard-Route". Nach diesem
  Edit bedeutet "U7" "Dashboard-Template".
  Verwechslungsgefahr bei der Nachvoll-
  ziehbarkeit. Umnummerierung dokumentiert:
    Lauf 33/34: U7 = Route.
    Lauf 35+:    U7 = Template,
                 U8 = Route,
                 U9 = Test,
                 U10 = Aktion (ex-U9),
                 U11 = Sidebar (ex-U10),
                 U12 = Doku (ex-U11).

Merkposten:
  W5 (COMMAND+Patch-Bug): eigener Block.
  Weg X (Planner-Konkretisierung).

Stand:
  U1-U6 done. U7-U12 pending.

Naechster Schritt:
  35. PB-68-Lauf mit --resume-force.
  Erwartung: U7 (Template) done.

================================================================
ENDE 11. MANUELLER EINGRIFF
================================================================

================================================================
W6a+W6b READ_FILE-ZEILENBEREICH (2026-10-16)
================================================================

Ausgangslage 35. Lauf:
  U7 (Template) done. U8 gestartet, gescheitert.
  Reviewer-Diagnose (R11):
    "GEMESSENER INHALT enthaelt nur
     apps/dashboard/templates/guardrails.html.
     Die Anker des Auftrags stehen NICHT im
     GEMESSENER INHALT."

Wurzel:
  apps/dashboard/app.py ist ~9.000 Zeilen.
  Der Anker (Z. 257-258) liegt Zeichen ~20.000.
  trim_output kappte auf 10.000 Zeichen
  (MAX_PROTOKOLL_PER_COMMAND).
  Der Anker war abgeschnitten.

W6a (Commit e779c77):
  - _audit_builder_prompt: Regex ignoriert
    ARGV/RC/STDOUT/STDERR als Sektion.
    Behebt Fehldiagnose "gem_len=77".
  - Audit-Feld anzahl_read_file.
  - MAX_PROTOKOLL_PER_COMMAND_READ_FILE = 20_000.
  - MAX_PROTOKOLL_TOTAL = 150_000.
  - +5 Tests (929 passed).

W6b (dieser Commit):
  - read_file Zeilenbereich "<pfad>:<start>-<ende>"
    via sed -n "N,Mp".
  - _anker_zeilenbereich: extrahiert Anker aus
    dem Auftrag (Format "ANKER (...): '...'"),
    findet die Zeile in der Zieldatei.
    Liefert (anker_zeile-5, anker_zeile+10).
  - ensure_ziel_gemessen: aufgabe-Parameter.
    Bei Anker-Pfad wird der Zeilenbereich genutzt.
  - +8 Tests (937 passed).

Direkter Test:
  U8-Auftrag -> _anker_zeilenbereich liefert
  (252, 267). sed -n "252,267p" zeigt den
  vollstaendigen Anker (register_tools_routes).

Merkposten (W5, bleibt):
  COMMAND + Patch im selben Block fuehrt zur
  Verwerfung des Patches. Eigener Block.

Stand:
  U1-U7 done. U8 no_go.
  U9-U12 pending.

Naechster Schritt:
  36. PB-68-Lauf mit --resume-force.
  Erwartung:
    - U8 startet.
    - Auto-Messung: app.py mit Zeilenbereich.
    - Anker im GEMESSENER INHALT.
    - Builder baut Route + app.py-Patch.
    - U8 done.
    - U9 (Test) startet.
  Bei Scheitern: neuer Reviewer-Block.

================================================================
ENDE W6a+W6b
================================================================

================================================================
12. MANUELLER EINGRIFF: U8-AUFTEILUNG (2026-10-16)
================================================================

Ausgangslage 36. Lauf:
  U7 (Template) done. U8 gestartet, 3 Runden,
  Deadlock.
  Reviewer-Diagnose (R11):
    - Anker nicht verifizierbar.
    - Import-API nicht belegt.
    - Weitere ungepruefte Fakten.

A0-Messungen (belegt):

  M1: W6a+W6b wirken:
      gemessener_inhalt_len=2317 (statt 77).
      anzahl_read_file=7.
      app.py-Zeilenbereich 252-267 mit Anker.

  M2: Der Builder liefert:
      - Patch 1: new_file routes_guardrails.py.
      - Patch 2: patch app.py (Anker ok, aber
        ersatz-Check schlaegt fehl).

  M3: pruefe_ersatz_gegen_messung (Z. 3964):
      prueft, ob jede from-Import-Zeile im
      ersatz im mess_protokoll steht.
      Der app.py-ersatz enthaelt:
        from apps.dashboard.routes_guardrails
        import register_guardrails_routes
      Dieses Modul existiert noch nicht (wird im
      gleichen Reply als new_file erzeugt).
      Also: nicht im mess_protokoll -> Fehler.

Aenderung:
  U8 aufgeteilt in:
    U8: Dashboard-Route (new_file).
    U9: Dashboard-Integration (app.py-Patch).
  Nummerierung verschoben:
    ex-U9  -> U10 (Test).
    ex-U10 -> U11 (Aktion).
    ex-U11 -> U12 (Sidebar).
    ex-U12 -> U13 (Doku).

Konsequenz:
  In U8 (new_file) greift der ersatz-Check
  nicht — kein Patch mit ersatz.
  In U9 (Patch) existiert routes_guardrails.py
  bereits — der ersatz-Check findet das Modul
  im mess_protokoll (weil U8 die Datei
  angelegt hat).

Muster:
  12. manueller phase.yaml-Eingriff in Serie.
  Nach 12 Eingriffen ist die Werkstatt-
  Autonomie strukturell gebrochen.
  W5 (COMMAND+Patch), Weg X (Planner-
  Konkretisierung) bleiben Merkposten.

Audit-Referenz:
  Alte Audit-Logs referenzieren "U8" fuer
  "Route + app.py-Patch". Nach diesem Edit:
    U8 = Route (new_file).
    U9 = app.py-Integration (Patch).
    U10 = Test (ex-U9).
    U11 = Aktion (ex-U10).
    U12 = Sidebar (ex-U11).
    U13 = Doku (ex-U12).

Merkposten:
  W5: COMMAND + Patch im selben Block
      (Loop-Logik). Eigener Block.
  W7: pruefe_ersatz_gegen_messung akzeptiert
      Module, die im selben Reply als new_file
      erzeugt werden. Eigener Block.
  W8: Basis-Gate erkennt A-Eintraege nicht.
      Wiederholt manuelle git-reset-Aktionen.
      Eigener Block.

Stand:
  U1-U7 done. U8 no_go.
  U9-U13 pending.

Naechster Schritt:
  37. PB-68-Lauf mit --resume-force.
  Erwartung: U8 (Route) done.

================================================================
ENDE 12. MANUELLER EINGRIFF
================================================================

================================================================
W8 COMMIT-PAKET-PROMPT + MESSAGE-CHECK (2026-10-16)
================================================================

Commit: siehe git log. Kategorie 3.

Ausgangslage 37. Lauf:
  U8 (Route, new_file) gebaut. Code-GO.
  Commit-Review 2x NO-GO. Reviewer-Befund:
  "BETROFFENE DATEIEN sechs Dateien vs.
   GIT DIFF eine Datei."

A0-Messungen (M1-M4):
  M1: D3 wirkt: state.commit_paket["dateien"]
      = 1 Pfad.
  M2: Commit-Review-Prompt zeigt BETROFFENE
      DATEIEN = 1 Pfad.
  M3: Builder-Commit-Message nennt 6-7 Pfade.
  M4: GIT STATUS im build_commit_paket-Prompt
      zeigt 16 untracked Pfade. Der Builder
      kopiert sie in die Message.

W8-1 (GIT STATUS filtern):
  build_commit_paket filtert git_status auf
  _ziel_pfade. Der Builder sieht nur die
  Zieldateien — keine Halluzinations-Quelle.

W8-2 (Message-Sanity-Check):
  Nach D3: Pfade in der Message finden
  (Regex mit Datei-Endungen). Bei starker
  Diskrepanz (> Anzahl BETROFFENE DATEIEN):
  Fail-closed rc=9 + Audit.

W8-3 (commit_paket_gebaut-Audit):
  Reply-Kopf/Fuss + message_len +
  anzahl_dateien. Fuer kuenftige Diagnose.

Auflagen-Abgleich (W8-A1 bis A7):
  A1 (Check-Platzierung nach D3): erfuellt.
  A2 (GIT STATUS Filter): erfuellt.
  A3 (Message-Regex Endungen): erfuellt
    (py|sql|md|yaml|yml|json|toml|html|
     css|js|cfg|ini|txt).
  A4 (Fail-closed Pfad): erfuellt.
  A5 (Merkposten deterministische Message):
    notiert.
  A6 (7 Tests): erfuellt (937 -> 944).
  A7 (Handoff): dieser Eintrag.

R16 unveraendert (Reviewer-Kritik akzeptiert).

Merkposten (W8-A5):
  Deterministische Message-Generierung:
  statt Builder die Message schreiben zu
  lassen, generiert die Werkstatt die
  Message aus state.commit_paket (D3).
  Der Builder liefert nur einen Titel-
  Vorschlag. Eigener Block, HR-R8.

Stand:
  U1-U7 done. U8 no_go (nach U8-Aufteilung:
  Route). U9-U13 pending.

Naechster Schritt:
  38. PB-68-Lauf mit --resume-force.
  Erwartung:
    - U8 (Route) Code-GO, Commit-Review
      Runde 1: COMMIT-GO.
    - Paket gesammelt.
    - U9 (app.py-Patch) startet.
    - U10 (Test) folgt.

================================================================
ENDE W8
================================================================

================================================================
W10 MESSAGE-CHECK PRAEZISER (2026-10-16)
================================================================

Commit: siehe git log. Kategorie 3.

Ausgangslage 41. Lauf:
  U8 (Route) Code-GO in Runde 1 (Messblock
  wirkt). apply. Der W8-2-Check blockte:
    Message nennt 3 Pfade
    (Zieldatei + Muster + Template als
     Referenz).
    BETROFFENE DATEIEN: 1. Fail-closed.

W10:
  - _MESSAGE_SECTION_CHANGE = "Aenderung:".
  - _extrahiere_aenderung_pfade: Regex
    extrahiert Pfade NUR aus dem Bullet-Block
    unter "Aenderung:". Referenzen (Muster,
    Template) werden ignoriert.
  - _normalisiere_pfad: fuehrendes "./",
    "/", trailing "/", Backslash.
  - W8-2-Block ersetzt.
  - Fail-Pfade mit fall-Feld:
    "a" (Section leer), "b" (Section fehlt),
    "c" (Parse-Fehler), "diff" (Mengen-Ungleich).
  - Audit-Kind commit_message_diskrepanz
    bleibt (Katalog unveraendert).
  - 948 -> 956 passed.

Auflagen-Abgleich (W10-A1 bis A9):
  A1 (Section-Name): "Aenderung:" (ae),
    Konstante. Umlaut-Variante wird NICHT
    erkannt (Test).
  A2 (Regex-Grenzen): Bullet nur "-" oder
    "*". Keine trailing Leerzeilen-Toleranz.
  A3 (Parse-Diskriminierung): ein Kind
    mit fall-Feld.
  A4 (D3-Vergleich): Mengenvergleich nach
    Normalisierung.
  A5 (echte Message): nicht verfuegbar
    (Audit-Log leer); Test mit
    synthetischer, realistischer Message.
  A6 (W8b-Prompt-Konsistenz): geprueft,
    Format passt.
  A7 (Ersetzen): W8-2 ersetzt.
  A8 (8 Tests): erfuellt.
  A9 (Handoff): dieser Eintrag.

Merkposten:
  - Echte Message aus Lauf 41 nicht im Audit.
    W9a/W10 helfen kuenftig (commit_paket_gebaut
    speichert Kopf/Fuss).
  - Deterministische Message-Generierung
    (W8-A4) bleibt der langfristige Fix.

Stand:
  U1-U7 done. U8 no_go (nach U8-Aufteilung:
  Route). U9-U13 pending.

Naechster Schritt:
  42. PB-68-Lauf mit --resume-force.
  Erwartung:
    - U8 Code-GO, Commit-Review Runde 1:
      COMMIT-GO.
    - Paket gesammelt.
    - U9 (app.py-Patch) startet.

================================================================
ENDE W10
================================================================

================================================================
W11 UNTERBLOCK-ISOLATION (2026-10-16)
================================================================

Commit: siehe git log. Kategorie 3.

Ausgangslage 43. Lauf:
  U8 (Route, new_file) Code-GO in Runde 1
  (Messblock wirkt). apply. Commit-Review
  2x NO-GO:
    - R7 Anker-Pruefung bei new_file.
    - "Route nicht in app.py registriert."

A0-Messung:
  U8-Auftrag: nur Route. app.py ausgelagert
  nach U9. R16 deckt Datei-Teilmenge ab,
  aber nicht funktionale Vollstaendigkeit.

W11a (R17):
  - HARD_RULES_REVIEWER +R17.
  - Unterblock-Isolation im Phasen-Modus.
  - Der Commit-Review prueft NUR den
    aktuellen Unterblock.
  - Keine funktionalen Vollstaendigkeits-
    Befunde (app.py, Tests, etc.) fuer
    ausgelagerte Folgeunterbloecke.
  - AUSNAHME: Auftrag nennt den Pfad
    woertlich (aufgabe_block).
  - R17 referenziert R11 (Sachfaden) und
    R16 (Datei-Teilmenge).

W11b:
  - Unterblock-Kontext im Commit-Review-
    Prompt (nur Phasen-Modus):
      UNTERBLOCK: <id> (<pos> von <total>)
        — <titel>
      (<done> von <total> bereits done)
  - Fuer den Reviewer klar: er prueft
    einen Unterblock, nicht die ganze Phase.

Tests: 958 -> 967 (+9).

Auflagen-Abgleich:
  W11-A1: AUSNAHME am aufgabe_block
    woertlich. Im Zweifel HINWEIS.
  W11-A2: total + done im Kontext.
  W11-A3: R17 referenziert R11.
  W11-A4: R17 referenziert R16.
  W11-A5: Prompt-Struktur gemessen
    (phase_aktueller_index 0-basiert).
  W11-A6: Merkposten Phasen-Vollstaendigkeit.
  W11-A7: 9 Tests.
  W11-A8: dieser Handoff.
  W11-A9: keine neuen Audit-Kinds.

Stand:
  U1-U7 done. U8 no_go (nach U8-Aufteilung:
  Route). U9-U13 pending.

Naechster Schritt:
  44. PB-68-Lauf mit --resume-force.
  Erwartung:
    - U8 Code-GO, Commit-Review Runde 1:
      COMMIT-GO (R17 verhindert
      app.py-Registrierungs-Befund).
    - Paket gesammelt.
    - U8 done.
    - U9 (app.py-Patch) startet.

================================================================
ENDE W11
================================================================

================================================================
A1-FINAL DETERMINISTISCHE VOR-CHECKS REVIEWER (2026-10-16)
================================================================

Commit: siehe git log. Kategorie 3.

Ausgangslage 45. Lauf:
  U8 Code-GO. Commit-Review 2x NO-GO mit
  R17-verbotenem Befund. Reviewer ignoriert
  R17.

A0-qualitative Messung:
  R15: 63 Zitate, korrekt.
  R12: 65 Zitate, korrekt.
  R16: 0 Zitate.
  R17: 1 Zitat.
  -> R12 und R15 funktionieren. Determinisierung
     waere Regression.

A1-final:
  P1: pruefe_ersatz_gegen_messung
      schliesst typ=new_file aus
      (R5-Aequivalent).
  P3: _check_commit_scope prueft
      BETROFFENE DATEIEN als Teilmenge von
      GIT DIFF --NAME-ONLY HEAD. Fail-closed
      VOR dem Reviewer-Aufruf.

HARD_RULES_REVIEWER: 15 Regeln statt 17.
  R5 entfernt.
  R16 entfernt.

Auflagen-Abgleich (A1-final-1 bis 5):
  A1-final-1 (Handoff): dieser Eintrag.
  A1-final-2 (7 Tests): erfuellt.
  A1-final-3 (Reihenfolge): Checks vor
    Reviewer, dann HARD_RULES-Reduktion.
  A1-final-4 (_check_commit_scope):
    Teilmenge-Check, Audit
    commit_scope_violation.
  A1-final-5 (P1-Erweiterung):
    typ=new_file ausgeschlossen.

Merkposten:
  - R17 bleibt semantisch (W11).
  - W12-Override (Verdict-Override durch
    Code) bleibt offen.
  - Rollen-Split (Option 3) naechster
    Kandidat.
  - Builder (A5), Solver (A6), Planner (A7)
    mit gleicher Methodik.

Stand:
  U1-U7 done. U8 no_go.
  U9-U13 pending.

Naechster Schritt:
  46. PB-68-Lauf mit --resume-force.
  Beobachten:
    - R15/R12/R17 wirken weiter.
    - R16-Aequivalent greift deterministisch
      (kein Reviewer-Aufruf bei Scope-Verstoss).
    - U8 Code-GO, Commit-Review Runde 1:
      COMMIT-GO? (R17 sollte jetzt greifen,
      weil der Reviewer nur R17-Rest hat.)

================================================================
ENDE A1-FINAL
================================================================

================================================================
W13A ANKER-ZEILENBEREICH MIT \n-LITERAL (2026-10-16)
================================================================

Commit: siehe git log. Kategorie 3.

Ausgangslage 48. Lauf:
  U9 (app.py-Patch) scheiterte am
  Anker-Messwert. Anker-Text in phase.yaml
  als '    from ...\\n    register_...\\n'
  (YAML-Single-Quote, literal \n).

  _anker_zeilenbereich (W6b) erkannte
  den Anker nicht -> None -> keine
  Auto-Messung.

W13a:
  Wenn anker_text "\\n" enthaelt und keinen
  echten Zeilenumbruch: literal in echte
  Zeilenumbrueche wandeln.

Direkter Test (U9-Auftrag):
  Anker-Info = (252, 267).

Tests: 976 -> 978 (+2).

Merkposten (Solver-Befund aus Lauf 47/48):
  pruefe_ersatz_gegen_messung prueft ERSATZ-
  Imports (nicht R5 "ersatz != anker"). Der
  ERSATZ enthaelt 'from apps.dashboard.
  routes_guardrails import ...' — das Modul
  existiert noch nicht -> Fehlalarm.
  Eigener Werkstatt-Block (W13b).
  Der Solver hat das in Lauf 47 und 48
  identisch benannt.

Stand:
  U1-U8 done. U9 no_go (nach 48).
  U10-U13 pending.

Naechster Schritt:
  49. PB-68-Lauf mit --resume-force.
  Erwartung:
    - U9 Auto-Messung app.py:252-267.
    - Builder findet Anker count==1.
    - Patch app.py.
    - Commit-Review COMMIT-GO.
    - U9 done.
    - U10 (Test) startet.

================================================================
ENDE W13A
================================================================

================================================================
W13B ERSATZ-PRUEFUNG DEAKTIVIERT (2026-10-16)
================================================================

Commit: siehe git log. Kategorie 3.

Ausgangslage 47-49. Lauf:
  U9 (app.py-Patch) scheiterte. Der Builder
  meldete "1 Ersatz nicht im GEMESSENER
  INHALT". Der ERSATZ enthaelt einen NEUEN
  Import. Das Modul existiert noch nicht.

W13b:
  pruefe_ersatz_gegen_messung wird nicht
  mehr aufgerufen. Der ERSATZ enthaelt
  neuen Code; der Anker-Check +
  apply_code_patches reichen.
  Die Funktion bleibt fuer spaetere Nutzung.

Tests: 978 -> 980 (+2).

Solver-Befund (Lauf 47, 48, 49):
  "pruefe_ersatz_gegen_messung prueft ERSATZ-
   Imports, nicht R5 'ersatz != anker'.
   Der ERSATZ enthaelt 'from apps.dashboard.
   routes_guardrails import ...' — das Modul
   existiert noch nicht -> Fehlalarm."

Drei Laeufe hintereinander identisch
gemeldet. Bestaetigt und behoben.

Stand:
  U1-U8 done. U9 no_go.
  U10-U13 pending.

Naechster Schritt:
  50. PB-68-Lauf mit --resume-force.
  Erwartung:
    - U9 Auto-Messung app.py:252-267 (W13a).
    - Builder findet Anker count==1.
    - Kein Ersatz-Fehlalarm (W13b).
    - Patch app.py.
    - Commit-Review COMMIT-GO.
    - U9 done.
    - U10 (Test) startet.

================================================================
ENDE W13B
================================================================

================================================================
W7 BASIS-GATE A/M AUS DONE-PFADEN (2026-10-16)
================================================================

Commit: siehe git log. Kategorie 3.

Ausgangslage 52. Lauf:
  U1-U10 done. Basis-Gate-Check rot:
    M apps/dashboard/app.py
    A apps/dashboard/routes_guardrails.py
    A tests/unit/test_dashboard_guardrails.py
  Alle drei in done-Pfaden.

W7:
  _phasen_basis_gate_ok klassifiziert jetzt:
    ??          -> untracked
    A , AM      -> intent (intent-to-add)
     M, M , MM  -> modified
    D, R, UD... -> modified (fail-closed)
  Alle drei Listen gegen done_pfade.
  Akzeptiert: alle drei aus done-Pfaden.
  Fail-closed: fremd_untracked / modifiziert
  ohne done-Zuordnung.

W7b: Fallback bei fehlender phase.yaml
  gibt 'modifiziert' bei M-Datei.

Tests: 980 -> 983 (+3).

Merkposten:
  - W8 (Commit-Paket-Prompt bereinigen,
    Solver-Befund seit Lauf 47).
  - W12 (Commit-Review-Prompt verkleinern,
    seit A1-final offen).
  - W13a (Anker-Zeilenbereich) done.
  - W13b (Ersatz-Pruefung deaktiviert) done.

Stand:
  U1-U10 done. U11 pending.
  U12, U13 pending.

Naechster Schritt:
  52. Lauf mit --resume-force.
  Erwartung:
    - U11 startet (Aktion).
    - Basis-Gate gruen (W7).
    - Commit-Review erfolgreich?
  Bei Scheitern: Diagnose.

================================================================
ENDE W7
================================================================

================================================================
W11B COMMIT-SCOPE UNTRACKED (2026-10-16)
================================================================

Commit: siehe git log. Kategorie 3.

Ausgangslage 53. Lauf:
  U11 baute 4 Patches (Route, Template, JS,
  Test). _check_commit_scope blockierte:
    git diff --name-only HEAD sieht
    untracked Dateien nicht
    (templates/guardrails.html).

W11b:
  _check_commit_scope liest zusaetzlich
  git status --porcelain -uall.
  Untracked Pfade landen in diff_pfade.

Tests: 983 -> 985 (+2).

Merkposten (neue Klasse):
  Jede Pruefung, die "git diff --name-only"
  als Wahrheit nutzt, muss untracked
  einbeziehen. Gleiche Klasse wie R16/2169.
  Systematisch pruefen (eigener Block).

Stand:
  U1-U10 done. U11 no_go (nach 53).
  U12, U13 pending.

Naechster Schritt:
  54. Lauf (U11) mit --resume-force.
  Erwartung:
    - Basis-Gate gruen (W7).
    - Code-GO (Vorbedingungen belegt).
    - apply 4 Dateien.
    - Commit-Scope-Check gruen (W11b).
    - Commit-Review COMMIT-GO.
    - U11 done.
    - U12 startet.

================================================================
ENDE W11B
================================================================

================================================================
SITZUNG 2026-10-16 ABENDS — PHASE 18 ABGESCHLOSSEN
================================================================

Werkstatt-HEAD: e26eb32 (W11b + Handoff).
security-ai-HEAD: d7b7c26 (Tag probebetrieb-68).

Werkstatt-Commits in dieser Sitzung:
  (keine — Werkstatt unveraendert seit e26eb32)

security-ai-Commits in dieser Sitzung:
  1fcc6bf  PHASE 18: Guardrails laden und nutzen (25 Dateien)
  d7b7c26  test: drei vorbestehende Testfehler korrigiert (W25)

================================================================
WAS PASSIERT IST
================================================================

Phasen-Modus, Phase 18 (Guardrails laden und nutzen).
Start: U1-U10 done, U11 failed, U12+U13 pending.

Laufe 53-60 (teils aus Vorsitzung):

  Lauf 53: U11 gescheitert (Commit-Scope, W11b).
  Lauf 54: Basis-Gate rot (guardrails.js aus failed-Paket).
  Lauf 55: U11/U12 durch, U13 Deadlock (Doku).
  Lauf 56: U13 Deadlock (GEMESSENER INHALT leer).
  Lauf 57: U13a deadlock, Anker leerer Messblock.
  Lauf 58: U13a-b deadlock, Anker nicht sichtbar.
  Lauf 59: U13a-d durch, Approval-Prompt abgebrochen
           (Fail-closed durch Tippfehler).
  Lauf 60: Kein Lauf — manueller Sammel-Commit.

Ergebnis Phase 18:
  U1-U12: Code komplett.
  U13a-d: Doku-Nachzug STATUS, ROADMAP,
          DECISIONS, SECURITY_LOG.
  Sammel-Commit 1fcc6bf (25 Dateien, 1624 Einfuegungen).
  Nachzieh-Commit d7b7c26 (drei Testfixes).
  Tag probebetrieb-68.

================================================================
W25 — BASIS-GATE PRUEFT TESTANZAHL, NICHT ERGEBNIS
================================================================

Kritischer Befund. `test_count`-Messung im Basis-Gate
fuehrt `pytest --collect-only` aus (Anzahl), nicht
`pytest` (Ergebnis).

Beleg: probebetrieb-65 (d135fd4) hat
ToolArgumentValueError eingefuehrt, ohne den Test
anzupassen. Zwei rote Tests blieben ab da unbemerkt.
Heute kamen zwei weitere hinzu (Viewer-Permission
durch Phase 18, Guard-Test strukturell defekt).

Ergebnis: Sammel-Commit 1fcc6bf lief durch das
Basis-Gate mit 3 roten Tests.

Fix (Kategorie 3):
  test_count-Messung durch test_result ersetzen
  (pytest -q, Exit-Code pruefen). Roter Test
  blockiert Basis-Gate.

================================================================
W25a — AST-BASIERTER GUARD-TEST
================================================================

Der entfernte `test_no_create_table_in_test_file`
war strukturell defekt: Er prueft die eigene Datei
auf "CREATE TABLE" — aber der String muss in einem
solchen Test selbst vorkommen (Selbstreferenz).

Korrektur: AST-basierter Guard (Kategorie 2).
Prueft, dass die Test-Datei kein
`sqlite3.executescript("CREATE TABLE ...")`
enthaelt — ueber `ast.parse` statt String-Match.

================================================================
MERKPOSTEN — VOLLSTAENDIG
================================================================

Kategorie 3 (Kernlogik, Reviewer-Block vor Bau):

  W11c  Pfad-Normalisierung in _check_commit_scope.
        git diff --name-only HEAD (CWD-relativ)
        vs. git status --porcelain -uall (Repo-Root).
        Bei Subdir-Aufruf oder Renames inkonsistent.

  W11d  fail-closed statt fail-open bei
        git-status-Fehler in _check_commit_scope
        (except ... pass → return False + Audit).

  W14   Loop akzeptiert keinen NO-GO ohne
        GEMESSENER INHALT (Audit
        reviewer_no_measurement_no_go).

  W15   --resume-force setzt Status zurueck,
        raeumt Working Tree nicht auf. Dateien
        aus failed-Paketen blockieren Neustart.

  W16   intent-Dateien aus laufendem (pending)
        Paket blockieren Basis-Gate.

  W17   Struktur-Tests pruefen Strings statt
        Verhalten (TestW7). Kategorie 2.

  W18   git add -N (intent-to-add) ist fluechtig.
        Basis-Gate kann zwischen Prozessen
        inkonsistent werden.

  W19   GEMESSENER INHALT fuer Folge-Block ist der
        des Vorgaenger-Blocks. Kontext-Uebergang
        verliert Messgrundlage.

  W20   done mit leerem commit_paket (U11/U12).
        Dateien fehlen in done_pfade und im
        Sammel-Commit.

  W21   file_whitelist ohne CHANGELOG.md (Root).
        Doku-Auftrag mit Root-Dateien nicht baubar.

  W22   Doku-Bloecke brauchen woertlichen Anker
        (W23-D1). Sonst builder_command_deadlock.

  W23   Reviewer-Antwort zur Doku-Block-Frage:
        Option D (Auftrags-Praezisierung) gewaehlt.
        Auflagen W23-D1 bis W23-D6 im Handoff-Abschnitt.

  W24   Messblock kuerzt bei ~20.000 Zeichen.
        Anker am Dateiende grosser Doku-Dateien
        unsichtbar. read_target_snippets liest
        von vorne.

  W25   test_count prueft Anzahl, nicht Ergebnis.
        KRITISCH — siehe oben.

  W25a  AST-basierter Guard statt String-Match.
        Kategorie 2.

Niedrig:

  P17-Beispiel Rotation (GuardrailRepository)
    bei Projektwechsel.

  U5/U6/U9 (ex) mit nur 2 Unterpunkten.
    P15-Neu verlangt 3-7.

  Design-Konflikt U1/U4 (created_at/updated_at).
    models.py 4 Felder, Migration 6 Spalten.
    Mismatch dokumentiert.

  Manuelle phase.yaml-Eingriffe: ca. 15 in dieser
    Sitzung. Autonomie-Anspruch strukturell gebrochen.

================================================================
STAND PHASE 18
================================================================

Alle Unterbloecke U1-U13 done.
Doku aktualisiert: STATUS, ROADMAP, DECISIONS,
  SECURITY_LOG.
Tests: 1395 passed, 0 failed.
ruff: 0.
mypy: 1353 Fehler in 73 Dateien (Altlast, unveraendert).
Tag: probebetrieb-68 auf d7b7c26.

================================================================
NAECHSTER SCHRITT
================================================================

Phase 19 planen. Kandidaten aus ROADMAP-Ausblick:
  Host-Scanner (Phase 3.8).
  Endpoint-Watcher.
  Sofort-Massnahmen-Kategorie.
  ChangeApplier-Implementierung.
  Chat als Aktions-Schnittstelle.
  Token-Mechanik.
  Anbindungs-Registry.
  Cloud-AI-Anbindung.
  Kunden-KI-Basis.
  LLM-Rolle klaeren.

Empfehlung: Erst W25 fixen (Basis-Gate test_result),
sonst wiederholt sich der heutige Fehler bei jedem
weiteren Sammel-Commit.

================================================================
ENDE SITZUNG 2026-10-16
================================================================


================================================================
W17-ERWEITERUNG ERLEDIGT (2026-10-17)
================================================================

Commit: 784dd98.
Kategorie 2 (Test-Qualitaet).
Kein Tag probebetrieb-69 (Werkstatt-Fix).

Was geaendert wurde:
  tests/test_aggregate.py:
    - Neuer Helper _git_repo_mit_commits(pfad,
      commits). Deterministisches Fixture-Repo
      in tmp_path.
      Env: GIT_AUTHOR_*, GIT_COMMITTER_*,
      GIT_CONFIG_NOSYSTEM=1,
      GIT_CONFIG_GLOBAL=/dev/null.
      Zusaetzlich -c user.name/-c user.email
      (W17-A14).
    - test_quelle_werkstatt umgestellt:
      Fixture mit 3 workbench + 2 mensch-Commits,
      sammle_projekt_stand(tmp_path).
      Zwei Assertions:
        assert "werkstatt" in quellen
        assert "mensch" in quellen
      Meldungen: f"quellen={sorted(quellen)}".

FLAKY-BEFUND (W17-A6):
  Vorher: Der Test hing von der Live-Historie
  von /opt/security-ai ab. Er wurde rot, sobald
  die letzten 5 Commits keinen workbench-Scope
  trugen; wieder gruen beim naechsten
  workbench-Commit. Kein Produktiv-Bug, reine
  Test-Fragilitaet.

Test-Anzahl (gemessen):
  Vorher:  1 failed, 984 passed
  Nachher: 0 failed, 985 passed
  tests/test_aggregate.py: 11 passed, 0 failed.

Merkposten W17b (W17-A3K-2):
  test_mit_commits nutzt ebenfalls das Live-Repo
  /opt/security-ai (sammle_projekt_stand,
  max_commits=3, Z. 42-52 in tests/test_aggregate.py).
  Prueft Struktur (basis, felder, quelle-Werte),
  nicht Historie.
  Heute nicht flaky.
  Strukturell flaky: Reset auf <3 Commits,
  Einfuehrung eines dritten quelle-Werts,
  git-log-Fehler.
  Bei kuenftiger Flaky-Reparatur von
  test_aggregate.py ODER bei Erweiterung
  von _ist_werkstatt_commit mitnehmen.

Merkposten W17c (Werkzeug-Hygiene):
  Am 2026-10-17 um 06:46 entstanden drei
  0-Byte-Dateien im Werkstatt-Repo (Commit,
  Handoff, W25.). Vermutlich Shell-Redirect-
  Artefakte aus Chat-Codebloecken. Entfernt.
  Kein Schaden. Klaerung offen: Wer oder was
  legt diese Dateien an? Bei Wiederholung
  .gitignore erweitern.

Merkposten W17-A17 (aus Reviewer-Block):
  W17-Erweiterung deckt gemischte Historie ab.
  Reine mensch-Historie (kein workbench-Scope)
  nicht separat getestet. Eigener Block, wenn
  _ist_werkstatt_commit erweitert wird oder wenn
  ein Fehlklassifikations-Bug auftritt.

W25 ist damit freigegeben:
  Basis-Gate test_result (Kategorie 3).
  Naechster Block.

================================================================
ENDE W17-ERWEITERUNG ERLEDIGT
================================================================


================================================================
W25-1 ERLEDIGT (2026-10-17) — BASIS-GATE TEST_RESULT
================================================================

Commit: 807228a.
Kategorie 3 (Kernlogik).
Kein Tag probebetrieb-69 (Werkstatt-Fix).

Was geaendert wurde:
  pipeline.py:
    - Neue Funktion _venv_fuer_state (deklariert,
      ungenutzt; W25-1 nutzt direkt
      project_dir/.venv/bin/python3).
    - Neue Funktion _ziel_test_pfade(state)
      -> list[str]: filtert state.code_patches
      auf startswith("tests/").
    - Neue Funktion _klassifiziere_pytest(...)
      -> dict: gruen|test_failures|collection_error|
      internal_error|usage_error|no_tests|timeout|
      unknown. Parst failed_count, passed_count,
      failed_test_ids (max 20), failed_test_ids_mehr
      aus pytest-Output.
    - Neue Funktion _basis_gate_pytest_ziel(
      project_dir, pfade, timeout_s=60) -> dict:
      pytest -q --maxfail=1 <pfade>.
    - Neue Funktion _basis_gate_pytest_suite(
      project_dir, timeout_s=900) -> dict:
      pytest -q --maxfail=10 (volle Suite).
    - apply_and_recheck: nach "always"-Loop
      zusaetzlich Zieldatei-Tests (b).
      Bei Rot: bestehender Recovery-Loop (rc=19).
    - Sammel-Commit-Pfad: vor commit_paket-
      Finalisierung Suite-Gate (e). Nur bei
      state.phase_aktiv=True. Bei Rot: rc=18
      (fail-closed, Recovery folgt in W25-2).

  tests/test_pipeline.py:
    - TestW25Klassifizierung (7 Tests).
    - TestW25ZielPfade (3 Tests).
    - TestW25BasisGate (5 Tests).

Bugfix waehrend Bau:
  Klassifizierer nutzte "exit_code or -1",
  was exit_code=0 als falsy auf -1 mappte.
  Korrigiert zu
  "exit_code if exit_code is not None else -1".

Test-Anzahl (gemessen):
  Vorher: 985 passed.
  Nachher: 1000 passed.
  Neue Tests: 15.

Kosten:
  Pro Unterblock: +0.1 s (3 Zieldateien
  mit je ~13 Tests).
  Pro Phase: +560 s (1x volle Suite).
  Bei (e)-Rot: rc=18 sofort (kein Recovery
  in W25-1). Recovery kommt in W25-2
  (Kosten dann ~22-25 min bei (e)-Rot
  mit Recovery-Loop).

Risiko 3 (A27):
  Code-Aenderungen, die bestehende Tests
  rot machen, werden von (b) nicht erkannt,
  weil die betroffene Test-Datei nicht in
  code_patches ist. (e) erkennt sie am
  Phasen-Ende vor dem Sammel-Commit.
  Bei 10 Unterbloecken: Diagnose rueckwaerts
  noetig.

Merkposten:
  W25d (test_run dead): test_run (Z. 3425)
    ist toter Code. Pruefen oder entfernen.
    Eigener Block.
  W25e (venv-Pfad): _basis_gate_pytest_ziel
    und _basis_gate_pytest_suite nutzen
    project_dir/.venv/bin/python3 direkt,
    nicht _venv_fuer_state. Fuer security-ai
    identisch. Bei Projekt-YAML-Abweichung
    (venv_python != project_dir/.venv)
    korrigieren. Eigener Block.
  W25f (Risiko 3 Recovery): Impact-Analyse
    oder (b) erweitern. Eigener Block.

W25-2 (Recovery bei (e)-Rot, A33):
  Freigegeben mit GO-mit-Auflagen
  (A35-A37). Naechster Block.

================================================================
ENDE W25-1
================================================================


================================================================
W25-2 ERLEDIGT (2026-10-17) — RECOVERY BEI (E)-ROT
================================================================

Commit: 7afdea0.
Kategorie 3 (Recovery-Loop).
Kein Tag probebetrieb-69 (Werkstatt-Fix).

Was geaendert wurde:
  pipeline.py:
    - _FRUEHER_VERURSACHT_MARKER (Tupel,
      case-insensitive Marker fuer "Fehler aus
      frueherem Unterblock").
    - _fehler_nach_apply(v, pos) -> bool:
      deterministisch. Prueft Diagnose UND
      Reparaturplan (A36). Marker-Match (A37).
      Kein LLM-Call.
    - _sammel_commit_suite_kontext(state, tr)
      -> str: failed_test_ids, raw_tail,
      Phase-Zustand, Zieldatei-Tests des
      aktuellen Unterblocks.
    - Sammel-Commit-Pfad: bei (e)-Rot
      ask_reviewer_for_recovery.
      - Reparierbar: Phase no_go ->
        _post_apply_korrektur_loop (max 1 Runde)
        -> erneut (e) -> Status zurueck auf done
        (A35).
      - Nicht reparierbar: Phase no_go, rc=18.
      - Timeout (A38): kein Recovery, fail-closed.

  tests/test_pipeline.py:
    - TestW25FehlerNachApply (8 Tests).
    - TestW25SammelCommitRecovery (2 Tests).

Test-Anzahl (gemessen):
  Vorher: 1000 passed.
  Nachher: 1010 passed.
  Neue Tests: 10.

Kosten (A41):
  Pro (e)-Rot ohne Recovery: +0.5-1 min
  (Reviewer-Call, dann fail-closed).
  Pro (e)-Rot mit Recovery: +22-25 min
  (2x Suite-Lauf ~560 s je + 1 Reviewer
  + 1 Builder-Korrektur-Runde).
  Recovery-Loop max_korrektur_runden=1
  (Reviewer-A33).

W25-2 ist abgeschlossen.
W25a (AST-Guard in security-ai) ist
freigegeben als eigener Block (A12).
Vor W25a: pruefen, wo der alte
test_no_create_table_in_test_file lag
und welche Konstruktion er pruefte (A18).

================================================================
ENDE W25-2
================================================================


================================================================
W25A ENTFÄLLT + W25-HANDOFF-NACHTRAG (2026-10-17)
================================================================

W25a (AST-Guard in security-ai) entfällt:
  Messung 2026-10-17 zeigt:
    - Der alte defekte Guard-Test
      test_no_create_table_in_test_file wurde
      in d7b7c26 entfernt (nur __pycache__-
      Ueberrest).
    - Alle heutigen CREATE-TABLE-/
      executescript-Vorkommen in tests/ sind
      legitim (Test-Setups fuer Migration und
      Repository).
    - Ein generischer AST-Guard wuerde false
      positives produzieren.
  security-ai bleibt bei 1395 passed
  (keine Aenderung durch W25a).

Merkposten W25a-1 (Selbstreferenz-Tests):
  Der urspruengliche Guard-Test war strukturell
  defekt (prueft sich selbst) und verschleierte
  einen roten Test. Wie erkennen wir Selbst-
  referenz-Tests systematisch? Kandidat:
  AST-Check, dass test_*-Methoden nicht ihre
  eigene Datei als String lesen.
  Eigener Block, wenn das Muster wieder auftritt.

Merkposten W25a-2 (Migration-Vollstaendigkeit):
  Pruefen, ob jede data/migrations/*.sql von
  mindestens einem Test referenziert wird.
  Verhindert tote Migrationen.
  Eigener Block, wenn Migrationen-Schulden
  aufgebaut werden.

Merkposten W25a-3 (Testdatei-Layout):
  90 Testdateien unter tests/ ist viel.
  Einheitliches Namensschema pruefen
  (test_*.py konsistent?).
  Eigener Block, wenn neue Testdatei-Layouts
  entstehen.

Merkposten A43 (Wert-or-Fallback mit 0):
  Muster "wert or fallback" mit 0 als gueltigem
  Wert: pruefen bei kuenftigen Pipelines.
  Exit-Codes, Counts, Dauern sind oft 0-wertig.
  Konkret: is-not-None-Check statt or-Fallback.
  Anlass: W25-1-Klassifizierer nutzte
  "exit_code or -1", was exit_code=0 als falsy
  auf -1 mappte. Behoben.

Merkposten A45 (Phase-19-Erwartungshaltung):
  Erste Phase mit vollstaendigem Basis-Gate
  (rote Tests blockieren). Erwartung:
  schaerfer, langsamer, teurer bei Rot.
  Bei 10 Unterbloecken: +560 s einmalig
  + jeweils (b)-Kosten (~0.1 s).

================================================================
ENDE W25-HANDOFF-NACHTRAG
================================================================


================================================================
W25D UND W25E ERLEDIGT (2026-10-17)
================================================================

Commit: 97e637f.
Kategorie 2 (Code-Hygiene).
Kein Tag probebetrieb-69.

W25d (test_run dead): entfernt.
  test_run (Measurement) war nirgends aufgerufen.
  Die W25-Gate-Funktionen _basis_gate_pytest_ziel/
  _suite uebernehmen den Zweck.

W25e (_venv_fuer_state dead): entfernt.
  Funktion war deklariert, aber nie gerufen.
  Kommentar Z. 6241 korrigiert:
    apply_and_recheck nutzt project_dir/.venv/bin/python3
  (nicht _venv_fuer_state).

Konsequenz: bei Projekt-YAML-Abweichung
(venv_python != project_dir/.venv) muss ein
neuer Block W25e-2 die venv-Aufloesung
einheitlich machen.

Test-Anzahl: unveraendert 1010 passed.

================================================================
ENDE W25D/W25E
================================================================


================================================================
WEG-X-P19 ERLEDIGT (2026-10-17) — PLANNER MUSS MESSEN
================================================================

Commit: 14337bd.
Kategorie 3 (Planner-Prompt + deterministische Checks).
Kein Tag probebetrieb-69 (Werkstatt-Fix).

Was gebaut wurde:
  pipeline.py:
    - Neue Funktion _plan_ist_messungsbasiert
      (Syntax-Check, nicht Wahrheit; R1-Grenze
      im Docstring).
    - Neue Funktion _plan_ist_portionierbar
      (max 7 Unterpunkte pro Unterblock).
    - P15 verschaerft: HARTES Maximum 7
      Unterpunkte, Erklaerung "Array-Eintrag".
    - P17 verschaerft: 4 Pflichtfelder
      (datei, aktion, signatur/anker, test).
    - P19 verschaerft: "MESSEN IST PFLICHT".
    - Fail-closed im --phase-Pfad (nach
      _parse_phase_plan, vor Anzeige).
    - A6: Anzeige zeigt Anker pro Unterpunkt,
      Runden-Schaetzung markiert.

  tests/test_pipeline.py:
    - TestWEGXP19PlanChecks (7 Tests).
    - TestWEGXP19Anzeige (3 Tests).
    - test_p19_nennt_read_file angepasst
      (neuer Header "MESSEN IST PFLICHT").

Test-Anzahl (gemessen):
  Vorher: 1010 passed.
  Nachher: 1020 passed.
  Neue Tests: 10.

Anlass:
  Planner-Plan Phase 19 (2026-10-17) hat 7
  Unterbloecke mit 88 Unterpunkten geliefert,
  ohne Anker, ohne Zieldateien, ohne Signaturen.
  Mit [n] verworfen.

Entscheidung (Variante a, HR-R8):
  "1-2 Zieldateien + 1 Test" bleibt reine
  Prompt-Regel. _plan_ist_portionierbar
  prueft nur "max 7 Array-Eintraege".
  Variante (b) (Zaehl-Check der Zieldateien)
  waere Scope-Creep, eigener Block bei Bedarf.

Determinismus-Grenze (R1, im Docstring):
  _plan_ist_messungsbasiert prueft Syntax.
  Dekorative Anker (Planner schreibt "anker:"
  ohne zu messen) passieren den Check.
  Wahrheits-Pruefung ist LLM-Sache (P19).
  Bekannte Grenze, bewusst akzeptiert.

Naechster Schritt:
  Phase 19 neu planen mit verschaerftem P19.
  Erwartung: Planner misst (COMMAND: RUN
  read_file), zitiert Anker, portioniert
  3-7 Unterpunkte pro Unterblock.
  Bei Verletzung: Fail-closed, Konsole mit
  Hinweis "Auftrag praezisieren oder
  'neu:'-Modus verwenden."

================================================================
ENDE WEG-X-P19
================================================================


================================================================
WEG-X-P19b ERLEDIGT (2026-10-17) — P17-FORMAT ERKANNT
================================================================

Commit: dcda015.
Kategorie 2 (Bugfix + Tests).
Kein Tag probebetrieb-69.

Was gebaut wurde:
  pipeline.py:
    - _plan_ist_messungsbasiert erweitert:
      akzeptiert BEIDE Formate:
        (1) Praefix "neu:"/"anker:" (degraded,
            backward-compat). Zaehler
            _plan_ist_messungsbasiert_praefix_zaehler
            und Audit-Event
            planner_plan_praefix_format_verwendet.
        (2) P17-Format: datei: + aktion:neu|patch
            + signatur: (bei neu) oder anker:
            (bei patch).
      Echte Verletzungen bleiben fail-closed:
        - "test:..." ohne "datei:..."
        - "aktion: neu" ohne "signatur:"
        - "aktion: patch" ohne "anker:"
        - "datei:" ohne "aktion:"
      Fehlermeldung grund-spezifisch (A4).
    - Katalog erweitert (78 -> 80):
        planner_plan_unvollstaendig,
        planner_plan_praefix_format_verwendet.

  tests/test_pipeline.py:
    - TestWEGXP19bP17Format (8 Tests).
    - 5 Katalog-Anzahl-Asserts 78 -> 80
      (historische Test-Namen bleiben).

Test-Anzahl (gemessen):
  Vorher: 1020 passed.
  Nachher: 1028 passed.
  Neue Tests: 8.

Bugfix waehrend Bau:
  - mypy-Fehler "Callable has no attribute
    letzter_praefix_zaehler" (Funktionsattribut
    nicht typisiert). Fix: modulglobaler
    Zaehler.
  - Test-Klasse doppelt eingefuegt (F811).
    Fix: Doppelten Block entfernt.
  - ISC004 (implizite String-Konkat in
    Collections). Fix: Klammern + Zeilenumbrueche.

Merkposten:
  WEG-X-P19c (Praefix-Format deprecaten):
    Nach Messung von
    planner_plan_praefix_format_verwendet
    in den naechsten Laeufen. Wenn Planner
    das P17-Format zuverlaessig nutzt:
    Praefix-Format im Check entfernen
    (eigener Block, Kategorie 3).

Naechster Schritt:
  Plan-Lauf Phase 19 mit verschaerftem
  P19 + P17-Format-Erkennung.

================================================================
ENDE WEG-X-P19b
================================================================


================================================================
WEG-X-P19c ERLEDIGT (2026-10-17) — P17-VERSTAENDNIS
================================================================

Commit: 7b1ffe9.
Kategorie 3 (HARD_RULES_PLANNER_STUFE2).
Kein Tag probebetrieb-69.

Was gebaut wurde (nur P17-Wortlaut):
  A1: "Ein Unterpunkt = genau EIN datei:-Feld.
       Ein Unterpunkt ohne datei: ist ungueltig.
       Der test:-Eintrag gehoert in DENSELBEN
       Unterpunkt."
  A2: "Bei aktion:patch ist anker: Pflicht.
       signatur: ist bei patch NICHT erlaubt
       (nur bei neu)."
  M4: GUELTIG/UNGUELTIG-Beispiel (A1-Aufloesung
       ii: "(leer)" durch konkrete Signatur
       "from .models import ChangeApplier
       (Re-Export)" ersetzt).

Keine Code-Aenderung an:
  _plan_ist_messungsbasiert, _plan_ist_portionierbar,
  _parse_phase_plan, --phase-Pfad.

Test-Anzahl: unveraendert 1028 passed.

Versuch, keine Loesung:
  WEG-X-P19c verbessert das P17-Verstaendnis
  des Planners durch ein konkretes Beispiel
  und zwei harte Regeln. Ob der Planner das
  umsetzt, zeigt der naechste Lauf.

Merkposten P19d (WEG-X-P19c-A6):
  "Wenn Planner wiederholt P17 verletzt:
   deterministischer Check
   _plan_hat_genau_ein_datei_pro_unterpunkt
   (analog _plan_ist_messungsbasiert).
   Eigener Block, Kategorie 3."

Merkposten WEG-X-P19c-Audit:
  Planner-Lauf Phase 19 (2026-10-17) hat
  planner_plan_praefix_format_verwendet
  NICHT ausgeloest (der Plan war unvollstaendig,
  Fail-closed). Nach dem naechsten erfolgreichen
  Lauf: Zaehler pruefen.

Naechster Schritt:
  Plan-Lauf Phase 19 mit P17c-Wortlaut.
  Wenn P17-konform: Plan-Anzeige, [j]/[n]/[e].
  Wenn wieder Fail-closed: WEG-X-P19d.

================================================================
ENDE WEG-X-P19c
================================================================


================================================================
ANKER-REGEX-FIX + TESTW13A (2026-10-17)
================================================================

Commit: 7d9be73.
Kategorie 2 (Regex + Test).
Kein Tag probebetrieb-69.

Problem:
  _anker_zeilenbereich erkannte P17-Format nicht.
  Regex "ANKER[^:]*:" matcht nur Gross-
  schreibung. Planner liefert "anker:'text'" (P17).

  Folge: Auto-Messung von Anker-Kontexten lief
  ins Nichts. Builder hat bei Phase 19 ohne
  Anker-Kontext improvisiert — vermutlich der
  eigentliche Grund fuer "Builder wirkt dumm".

Fix:
  Regex erweitert:
    r"(?:ANKER[^:]*|anker)\s*:\s*'([^']+)'"
    re.IGNORECASE | re.DOTALL
  TestW13a deterministisch (tmp_path, nicht
  phase.yaml).

Test-Anzahl: 1028 passed, 0 failed.

Naechster Schritt:
  Phase 19 neu planen mit Anker-Regex-Fix.
  Wenn Builder jetzt mit Anker-Kontext baut:
  Phase-19-Lauf testen.
  Wenn wieder NO-GO: Rollen-Sanierung (Prompt-
  Redundanz) als eigener Block.

Merkposten:
  Rollen-Sanierung (Audit-Commit 78462f1)
  bleibt offen. 43% Redundanz in builder.md,
  41% in reviewer.md. agent_docs enthaelt
  DECISIONS.md (1870 Zeilen) und SECURITY_LOG.md
  (2211 Zeilen) in jedem Prompt.
  Sanierung als SAN-A (agent_docs) + SAN-B
  (agents-Diaet) geplant, aber zurueckgezogen
  wegen fehlender Messungen.
  Nach Phase-19-Neuversuch: Sanierung neu
  bewerten.

================================================================
ENDE ANKER-REGEX-FIX
================================================================


================================================================
U4-HINWEIS-TEST ENTFERNT (2026-10-17)
================================================================

Commit: 7aa0583.
Kategorie 2 (Test).
Kein Tag probebetrieb-69.

Problem:
  test_u4_hinweis_models_py las phase.yaml und
  prueft, ob U4 einen "models.py"-Hinweis enthaelt.
  Das war Phase-18-spezifisch (U4 = Guardrail-
  Repository (DB)). In Phase 19 ist U4 =
  SofortMassnahme-Modell — kein models.py.

Fix:
  Test entfernt. Grund: phase.yaml-abhaengige
  Tests sind Anti-Pattern (vgl. W17,
  test_quelle_werkstatt, W13a). Bei jeder
  Phasen-Aenderung brechen sie.

Test-Anzahl: 1027 passed, 0 failed.

Merkposten W17c:
  Bei kuenftigen Tests: keine phase.yaml-
  Abhaengigkeit. Deterministische Fixture
  verwenden (tmp_path, statische YAML-Strings).

Naechster Schritt:
  P20+P21 Reviewer-Block formulieren
  (Planner-Auftrags-Kontext + Selbst-Kritik).

================================================================
ENDE U4-TEST-ENTFERNUNG
================================================================


================================================================
SAN-A ERLEDIGT (2026-10-17) — AGENT_DOCS REDUZIERT
================================================================

Commit: 4469a5e.
Kategorie 3 (Prompt-Diaet).
Kein Tag probebetrieb-69.

Was gebaut wurde:
  projects/security-ai.yaml:
    agent_docs reduziert:
      reviewer: [conventions, web_security]
      builder: [conventions, web_security]
      test_generator: [conventions]
      solver: [conventions, web_security]
      planner: [conventions]
      coverage, chaos: bewusst kein agent_docs.
      decisions, security_log: NICHT mehr statisch.
      Bei Bedarf: COMMAND: RUN read_file
        docs/DECISIONS.md:18-221.

  tests/test_pipeline.py:
    +2 Tests (TestSANAProjektkonfig).
    1 Test angepasst (solver_enthaelt_projektwissen).

Prompt-Groesse (gemessen):
  Vorher (gesch.):
    Builder ~2914 Zeilen Basis.
    Reviewer ~5074.
    Planner ~4651.
    Solver ~4709.
  Nachher (gemessen):
    Builder 1055 Zeilen.
    Reviewer 1004.
    Planner 578.
    Solver 639.

Test-Anzahl: 1027 -> 1029 passed.

Versuch, nicht Loesung:
  Prompt-Groesse ist Hypothese, nicht gemessen.
  Test ist der naechste Phase-19-Lauf mit
  SAN-A-Konfiguration.
  Wenn Builder danach weiter Auftraege
  umdeutet: Ursache woanders (Kanal, Modell,
  Format).

Rollback-Kriterium:
  git reset --hard 43051db.

Naechster Schritt:
  Phase 19 neu planen + laufen lassen.
  Messen: Builder baut konform?
  Wenn ja: SAN-A ist Erfolg.
  Wenn nein: SAN-B (agents/*.md-Diaet)
  als naechster Hebel.

================================================================
ENDE SAN-A
================================================================


================================================================
WEG-X-P22a ERLEDIGT (2026-10-17) — DIAGNOSE-LUECKE
================================================================

Commit: 74050ad.
Kategorie 3.
Kein Tag probebetrieb-69.

Problem:
  Post-Apply-Korrektur-Loop zeigte dem Builder nur
  "rot: ruff" ohne Regeln. Bei Phase-19-U1 fuehrte
  das zu 5 Runden read_file ohne Patch, Fail-closed.

Fix:
  - _basis_gate_pytest_ziel-Output in
    basis_protokoll_nach_apply eingebaut.
  - RunState-Feld basis_gate_test_results
    (strukturiert).
  - _bauer_recovery_prompt: voller Protokoll +
    strukturierte failed_test_ids.

Test-Anzahl: 1029 passed (unveraendert).

Wirkung:
  Builder sieht bei Post-Apply-Rot:
    - Test-ID (tests/unit/test_x.py::test_a).
    - Traceback (raw_tail).
    - Volle ruff/mypy-Ausgabe.

  Vermutlich loest das den 5-Runden-Deadlock
  bei U2-U7.

Naechster Schritt:
  Phase 19 U2-U7 laufen lassen.
  Messen: Baut der Builder mit vollstaendiger
  Diagnose konform?
  Wenn ja: Diagnose-Luecke war der Hauptgrund.
  Wenn nein: naechster Block (Rollen-Sanierung
  SAN-B, oder Crawler WEG-X-P22).

Merkposten Crawler (WEG-X-P22):
  Konzept skizziert (Crawler + Crawler-Reviewer +
  Crawler-Solver, eigener Prozess nach Phasen-
  Ende). NICHT gebaut.
  Prioritaet: nach Phase 19 (wenn Bauloop stabil).
  Block ist ~500 Zeilen, 3-5 Sessions.
  Crawler loest Test-Wartezeit, nicht Auftrags-
  Verstaendnis.

================================================================
ENDE WEG-X-P22a
================================================================


================================================================
W23 ERLEDIGT (2026-10-17) — KOMMUNIKATIONSWEGE-AUDIT
================================================================

Commit: c3bd4db.
Kategorie 3.
Kein Tag probebetrieb-69.

Problem:
  U2a2: Code korrekt (7 Tests gruen, ruff 0),
  aber Commit-Review NO-GO (2x): "rollback fehlt".
  Reviewer zitierte Docstring aus U2a1-Stand.

Diagnose:
  Commit-Review-Prompt (Z. 8977-8985) markierte
  state.mess_protokoll (Stand VOR Apply) als
  "GEMESSENER INHALT (verbindlich)". Der NACH-Stand
  war nur als Zusatz. basis_gate_test_results
  fehlte komplett.

Fix:
  - _format_basis_gate_test_results (neu).
  - _build_commit_input (Refactor).
  - Commit-Review-Prompt: NACH Apply verbindlich,
    VOR Apply historisch, Warnung, TEST-ERGEBNISSE.
  - A4-Grenzfall: nach_apply leer -> VOR verbindlich
    + Hinweis.

Tests: 1029 -> 1032 passed.

HR-R7-Nachtrag:
  Der 2x-NO-GO bei U2a2 beruhte auf falscher
  Datenquelle (VOR statt NACH). Reviewer-Chat
  hat den Docstring aus U2a1 zitiert und
  "rollback fehlt" gemeldet. Der Fix in W23
  behebt die Ursache.

Kommunikationswege-Matrix (Ist nach W23):

| Prompt | mess VOR | mess NACH | basis VOR | basis NACH | test_results |
|---|---|---|---|---|---|
| Code-Review | verbindlich | - | [:800] | Zusatz | - |
| Commit-Review | historisch | verbindlich | - | Zusatz | strukturiert |
| Recovery | - | verbindlich | - | voll | strukturiert |
| Builder-User | verbindlich | - | [:1500] | - | - |

Merkposten:
  W23b: Code-Review zeigt keine test_results.
    Pruefen, ob noetig (Code-Review ist VOR Apply,
    test_results sind NACH).
  MP2: Recovery nutzt eigene format-Logik fuer
    basis_gate_test_results. Konsistenz zu
    _format_basis_gate_test_results pruefen.

Naechster Schritt:
  U2a2-Commit-Review wiederholen (W23-Messung).
  Wenn GO: W23 behebt den Fehler.
  Dann U2a3, U2b, U3-U6.

================================================================
ENDE W23
================================================================


================================================================
W24a ERLEDIGT (2026-10-17) — APPLY IDEMPOTENT
================================================================

Commit: 4531451.
Kategorie 2.
Kein Tag probebetrieb-69.

Problem (heute):
  U2a2: Patch "rollback hinzufuegen" wurde zweimal
  angewendet. rollback doppelt in applier.py.
  Folge: ruff F811 + mypy no-redef. Fail-closed.

Fix:
  Phase 1 (Vorpruefung): count(anker) == 0 und
    ersatz in Datei -> skip + Audit.
  Phase 2 (Anwendung): Ambig nur, wenn anker und
    ersatz im Text und anker NICHT in ersatz.
  Gilt fuer apply_code_patches und
    apply_commit_and_doku.

Neue Audit-Kinds: patch_bereits_angewendet,
patch_ambig, patch_anker_fehlt.
Katalog 80 -> 83.

Tests: 1032 -> 1036 passed.

Naechster Schritt:
  W24b (Loop-Detektor + deterministischer Verdict)
  nach Auftraggeber-Entscheid E1/E2/E3.
  W24c (Protokolle als Dateien) danach.
  U2a3 durch Pipeline (W23 + W24a + SAN-A + P22a
  Wirkungs-Messung).

================================================================
ENDE W24a
================================================================


================================================================
W25 ERLEDIGT (2026-10-17) — SKILLS-INFRASTRUKTUR
================================================================

Commit: 317b000.
Kategorie 3 (Umstrukturierung, Chef-Anweisung).
Kein Tag probebetrieb-69.

Was gebaut wurde:
  - 12 SKILL.md in skills/<name>/SKILL.md:
    * Statisch (5): patch-format, anker-regeln,
      review-work, plan-crafting,
      systematic-debugging.
    * On-Demand (7): web-security, test-patterns,
      commit-history, simplify, security-review,
      milestone-planning, skill-creator.
  - pipeline.py:
    * RunState.geladene_skills: list[str].
    * parse_commands: COMMAND: load_skill <name>.
    * Funktionen: _load_skill, _list_skills,
      _lade_skill_in_state, _geladene_skills_block,
      _available_skills_block, _verarbeite_skill_commands.
    * Planner, Builder, Reviewer: load_skill vor
      execute_commands.
    * Prompt-Bau (3 Stellen): AVAILABLE SKILLS
      + GELADENE SKILLS.

Neue Audit-Kinds: skill_geladen (Katalog 83 -> 84).
Tests: 1036 -> 1039 passed.

Naechster Block: W26 (PLAN.md als Datei).

================================================================
ENDE W25
================================================================


================================================================
W26 ERLEDIGT (2026-10-17) — PLAN.MD ALS DATEI
================================================================

Commit: 05c817e.
Kategorie 3 (Umstrukturierung, Chef-Anweisung).
Kein Tag probebetrieb-69.

Was gebaut wurde:
  - Neue Funktionen:
    * _plan_pfad(state) -> Path.
    * _plan_audit_pfad(state) -> Path.
    * _schreibe_plan(state, plan_text) -> bool.
    * _lese_plan(state) -> str.
    * _lese_plan_audit(state) -> str.
  - _phase_main_pfad: PLAN.md wird nach
    _phase_plan_speichern geschrieben an zwei
    Stellen (.werkstatt/plan.md im Projekt +
    audit-logs/<run_id>/01-plan.md).

Tests: 1039 -> 1042 passed.

Wichtig: Die .werkstatt/plan.md wird noch NICHT
in den Builder-Prompt eingebaut. Das ist W26b
(spaeter, wenn der Builder den Plan liest).

Naechster Block: W27 (Sprint-Contracts).

================================================================
ENDE W26
================================================================


================================================================
W27 ERLEDIGT (2026-10-17) — SPRINT-CONTRACTS
================================================================

Commit: 309aeef.
Kategorie 3 (Umstrukturierung, Chef-Anweisung).
Kein Tag probebetrieb-69.

Was gebaut wurde:
  - Neue Funktionen:
    * _contract_pfad(state, uid) -> Path.
    * _contract_aus_unterblock(unterblock) -> str.
    * _schreibe_contract(state, unterblock) -> bool.
    * _lese_contract(state, uid) -> str.
  - _phase_main_pfad: pro Unterblock wird
    .werkstatt/contracts/<uid>.md angelegt.

Tests: 1042 -> 1045 passed.

Wichtig: Der Builder liest noch NICHT seinen
Contract. Das ist W27b (in W28 integriert).

Naechster Block: W28 (Judge + Repair-Loop).

================================================================
ENDE W27
================================================================


================================================================
W28a ERLEDIGT (2026-10-17) — JUDGE-ROLLE + REVIEWER REDUZIERT
================================================================

Commit: f122c39.
Kategorie 3 (Umstrukturierung, Chef-Anweisung).
Kein Tag probebetrieb-69.

Was gebaut wurde:
  - agents/judge.md (neu, ~120 Zeilen).
  - agents/reviewer.md (reduziert, 410 -> 56 Zeilen).
  - HARD_RULES_JUDGE (J1-J10, ~40 Zeilen).
  - HARD_RULES_BY_ROLE["judge"].
  - RunState.judge_model = "deepseek-reasoner".
  - skills/security-review/SKILL.md ueberarbeitet
    (OWASP Top 10:2025, 4-Fragen-Triage,
    Severity, Reporting-Format).
  - 8 Tests angepasst (reviewer.md -> judge.md /
    HARD_RULES_*), 1 Test geloescht.

Test-Anzahl: 1043 passed.

Wichtig: Der Review-Loop nutzt noch den alten
reviewer_prompt. Das ist W28b (Review-Loop auf
Judge-Prompt umstellen + max_review_rounds 5 -> 2).

Naechster Block: W28b.

================================================================
ENDE W28a
================================================================


================================================================
W28b + W28c ERLEDIGT (2026-10-17)
================================================================

Commits: siehe git log.
Kategorie 3 (W28b) + Kategorie 2 (W28c).
Chef-Anweisung (Umstrukturierung).

W28b — Review-Loop auf Judge umgestellt:
  - judge_prompt = _build_judge_prompt(state).
  - judge_input = _build_judge_input(state).
  - Review-Loop: ask_llm(judge_prompt, judge_input,
    state.judge_model, ...).
  - max_review_rounds: 5 -> 2 (Code + YAML).
  - Commit-Review bleibt beim Reviewer.

W28c — Antwort-Limit (max_tokens):
  - ask_llm: max_tokens-Parameter (default 4096).
  - RunState: 5 max_tokens_*-Felder.
  - security-ai.yaml: budget.max_tokens_*.
  - HARD_RULES_JUDGE + J11.
  - HARD_RULES_REVIEWER + R18.
  - HARD_RULES_BUILDER + B16.
  - 10 ask_llm-Aufrufe mit max_tokens.

Test-Anzahl: 1043 -> 1051 passed.

Wichtige Konsequenzen:
  - Judge sieht NICHT mehr: code_entwurf,
    mess_protokoll, basis_protokoll, commit_message,
    git_diff.
  - Judge sieht NUR: contract.md, mess_nach.txt,
    basis_gate_test_results.
  - max_review_rounds = 2 (statt 5).
  - Antworten haben hartes Limit:
    * Builder: 8192 Token.
    * Judge: 2048 Token.
    * Reviewer: 1024 Token.
    * Planner: 8192 Token.
    * Solver: 2048 Token.

Naechster Block: W29 (Aggregated Phase-Review).

================================================================
ENDE W28b + W28c
================================================================


================================================================
W29 ERLEDIGT (2026-10-17) — AGGREGATED PHASE-REVIEW
================================================================

Commit: 0faa69f.
Block W29 von 5 (W25-W30-Komplex).
Kategorie 3 (Kernlogik).
Kein Tag probebetrieb-69.

Vorher:
  _phase_gesamt_review war rein deterministisch
  (Zaehlung). Kein LLM-Blick auf die Phase.

Nachher:
  W29a — _phase_deterministisch_pruefen (D1-D5):
    D1: alle Unterbloecke done.
    D2: Duplikate = 0 in Datei-Union.
    D3: Whitelist eingehalten.
    D4: keine Waisen (Union == Pakete).
    D5: alle Dateien existieren.
    Fail-closed rc=17.

  W29b — Phase-Judge (PHASE-GO / PHASE-NO-GO):
    _build_phase_judge_input (neu):
      plan.md + Diff-Statistik + Top-3-Voll-Diffs
      + basis_gate_test_results.
    _phase_judge_review (neu).
    _phase_judge_repair_runde (neu, Cap 1,
      A-W29-4).
    _git_diff_phase (neu): git diff <start>..HEAD
      via subprocess.run, analog _git_rev_parse_head.
    Bei NO-GO nach Repair: Fail-closed rc=18.

  run_phase-Einhaengung zwischen Z. 2966 (aggregat)
  und Z. 2989 (Approval-Anzeige).
  Approval-Prompt wird bei NO-GO nicht erreicht.
  Audit-Kind phase_gesamt_review_no_go (92 -> 93).

Resume-Verhalten:
  phase_commit_pakete bleiben bei NO-GO erhalten.

A-W29-3-Wahl: (a).
  Diff-Statistik + Top-3-Dateien als Voll-Diff.
  Chunking (b) als Merkposten.
  (c) verworfen.

Test-Anzahl: 1051 -> 1065 passed.
  TestW29Deterministisch: 6 Tests.
  TestW29JudgePrompt: 3 Tests.
  TestW29JudgeVerdict: 5 Tests.
  Fixture-Fixes:
    _mock_run_pipeline erzeugt pro Aufruf eine
      andere Datei (D2-Schutz).
    Autouse-Fixture _mock_phase_judge_go (GO als
      Default fuer bestehende Phase-Tests).
    test_approval_j_commit: Datei-Liste angepasst
      (["apps/x0.py", "apps/x1.py"]).
    test_build_phase_judge_input_enthaelt_plan:
      phase_id als str.
    Katalog-Anzahl 84 -> 85 in 5 Tests.

Merkposten W29:
  - Chunking (A-W29-3 b): bei wachsenden Phasen
    Diff-Chunking oder selektiveres Top-N.
  - phase_id-Typ: str, nicht int. In RunState
    dokumentiert (Z. ~4718).
  - Wenn PHASE-NO_GO haeufig: Judge-Prompt
    schaerfen oder Phase-Review zurueckbauen
    (RR1 im Reviewer-Block).

Naechster Block: W30 (Loop-Cap + Solver-Trigger).

================================================================
ENDE W29
================================================================


================================================================
W30 + W31-MYPY + W31-MYPY-B ERLEDIGT (2026-10-17)
================================================================

Commits: e590766, 22464ec, bd3cd70.
Kategorien: 3 (W30), 2 (W31-Mypy, W31-Mypy-b).
Kein Tag probebetrieb-69.

W30 — Loop-Cap-Konsistenz:
  - A-W30-1: YAML-Default max_review_rounds
    5 -> 2 (Z. 8733). Widerspruch zu Code-Default
    2 (Z. 9012) behoben.
  - A-W30-2: Kommentar an beiden
    max_korrektur_runden-Aufrufen
    (Z. 9461 normal=2, Z. 9626 Recovery=1).
    Unterschied bewusst (Recovery kurz halten).
  - A-W30-3: Solver-Trigger unveraendert. Belegt:
    solver_trigger_a Z. 6929/9266,
    solver_trigger_b Z. 9273,
    solver_trigger_c Z. 6924/9261,
    rufe_solver Z. 5445/6959/9315,
    solver_config aus YAML Z. 8735-8745.
  - A-W30-4: _loop_erkannt NICHT gebaut
    (existiert nicht, war W24-B).
    Merkposten W30b, Auftraggeber-Entscheid
    offen.
  - Neue Funktion _loop_cap_erreicht (Z. ~2181):
    zentraler Cap-Check. Audit loop_cap_erreicht
    mit loop_name + aktuelle_runde + max_runden.
    rc=18 einheitlich.
  - Audit-Kind loop_cap_erreicht (Katalog 85 -> 86).
  - 8 neue Tests (TestW30LoopCap).

  A-W30-6 (Handoff-Satz zu Pakete-behalten):
    Abnahme 9 (Pakete behalten bei NO-GO):
    belegt. Drei Fundstellen fuer
    state.phase_commit_pakete = [] (Z. 2171,
    2794, 2880) liegen im Rollback-Pfad
    (_phase_rollback) oder im Phase-NO-GO-Pfad
    MIT explizitem Rollback. Der W29-NO-GO-Pfad
    (Deterministik/Judge) ruft KEIN Rollback
    und leert die Pakete NICHT.

  A-W30-7 (Abweichung Chef-Anweisung):
    _loop_erkannt(state): Hash der letzten 2
    Review-Runden. Bei Wiederholung: fail-closed.
    NICHT in W30 gebaut. Begruendung: existiert
    nicht im Code, war W24-B, nicht W28.
    Merkposten W30b.

W31-Mypy (Commit 22464ec):
  - pipeline.py:
      _review_round_audit_payload Rueckgabetyp
      dict[str, object] -> dict[str, Any].
  - tests/test_pipeline.py:
      (a) _state() in TestCodeEntwurfHistorie
          Rueckgabetyp -> pipeline.RunState.
      (b) lambda append-return -> benannte
          _mock_rufe_solver-Funktion.
      (c) state.code_patches: type-ignore[list-item]
          an den zwei nicht-dict-Elementen.
      (d) 3 _v()-Helper -> SimpleNamespace.
  28 mypy-Fehler weg.

W31-Mypy-b (Commit bd3cd70):
  - tests/test_phase.py: 6 mypy-Fehler weg.
      pakete: list[dict[str, object]] explizit
      typisiert, dict-Comprehension durch
      Schleife ersetzt (isinstance-Verengung
      greift nicht durch zwei get()-Aufrufe).

Werkstatt-Test-Basis jetzt vollstaendig
mypy-clean:
  pipeline.py:             0.
  tests/test_pipeline.py:  0.
  tests/test_phase.py:     0.

Handoff-Schuld "tests-mypy: 15 Fehler"
abgetragen (Stand vor W31-Mypy war 28+6=34,
jetzt 0+0).

W25-W31-Komplex ABGESCHLOSSEN.
  W25a entfaellt (defekter Guard-Test).
  W25b+c (Skill-Infrastruktur + plan.md).
  W25d+e (toten Code entfernt).
  W26 (PLAN.md als Datei).
  W27 (Sprint-Contracts).
  W28a-c (Judge + Review-Loop + max_tokens).
  W29 (Aggregated Phase-Review).
  W30 (Loop-Cap-Konsistenz).
  W31-Mypy + W31-Mypy-b (Test-Schuld).

Naechster Schritt:
  1. Phase 19 neu planen mit verschaerftem
     Planner (Weg-X-P19c).
  2. Plan pruefen (P17-konform? P19-Messung?).
  3. Lauf starten.
  4. Messung: Loop-Cap greift? (Wenn >30%
     der Laeufe Runde 3 brauchen: A-W30-1-
     Messung greift, Auftraggeber-Entscheid.)
  5. Bei Scheitern: Bilanz.

Merkposten nach W30:
  W30b (_loop_erkannt): Auftraggeber-Entscheid.
  A-W30-1-Messung: nach 5 Phasen-Laeufen.
  A-W30-2: Recovery-Runde 1 in Laeufen pruefen.

Merkposten nach W29 (aus Handoff-Abschnitt W29):
  Chunking (A-W29-3 b): bei wachsenden Phasen.
  phase_id: str, nicht int.

Merkposten W31-Mypy:
  mypy --strict ist NICHT eingefuehrt. Nur
  der bestehende Test-Stand ist clean.
  Neue Tests muessen typisiert sein (Pflicht).
  Wenn --strict gewuenscht: eigener Block.

================================================================
ENDE W30 + W31-MYPY + W31-MYPY-B
================================================================


================================================================
W32 + W33a + W33b ERLEDIGT (2026-10-17)
================================================================

Commits: e3e16bb (W32), dc7160d (W33a),
         c39ebbb (W33b).
Kategorien: 3 (alle).
Kein Tag probebetrieb-69.

W32 (_schreibe_contract in run_phase-Loop):
  Bug: _schreibe_contract war nur im Erst-Anlage-
    Pfad (_phase_main_pfad) verankert. Bei Resume
    fehlte der Contract, der Judge eskalierte.
  Fix: _schreibe_contract(state, u) direkt nach
    _phase_yaml_status_update(..., "running") im
    run_phase-Loop (Z. ~3081).
  Tests: 2 (test_schreibe_contract_im_loop,
    test_contract_existiert_nach_loop).

W33a (_post_apply_messung liest patch-Pfade):
  Bug (Wurzel des Deadlocks): _post_apply_messung
    las nur new_file-Pfade. Bei reinen
    patch-Aktionen (typ=patch) blieb mess_nach
    leer. Der Judge (W28b) sieht
    "(keine Messung nach Apply)" und eskaliert.
  Fix: typ in {"new_file", "patch"} lesen.
    Verhalten bei leerer Pfad-Liste bleibt
    return True ohne Setzen (W25-1-Verhalten).
  Messung A-W33-5: U2a3 (applier.py, 91 Zeilen,
    ~696 Token). Judge-Budget 2048. 34%.
    Option 1 (voller read_file) sicher.
  Tests: 2 netto + 2 Umbenennung.
    test_nur_patch_wird_jetzt_gelesen
      (patch-only: mess_nach befuellt).
    test_mixed_new_file_und_patch.
    test_nur_patch_regression_new_file.
    test_leere_code_patches (Regression).

  A-W33-11 (Rollback-Kriterium W33a):
    git reset --hard e3e16bb (W32), wenn ein
    Test ausserhalb W33a rot wird oder
    mess_nach in einem bestehenden Unterblock-
    Pfad bricht.

W33b (_phase_apply_vor_review + Aufruf):
  Bug: apply_and_recheck (Z. 9489) ruft
    apply_code_patches erst NACH dem Review-
    Loop. Der Judge sieht mess_nach +
    basis_gate_test_results im Prompt, beide
    leer -> ESKALATION.
  Fix: Neue Funktion _phase_apply_vor_review
    (6 Schritte: apply, git add -N,
    veraltet-Flag, _post_apply_messung,
    Guard, _basis_gate_pytest_ziel).
    Aufruf in run_pipeline zwischen parse_
    code_patches und dem Review-Loop, nur
    bei state.phase_aktiv=True.
  A-W33-7 (Guard): mess_nach nahe Judge-Budget
    (>50%) -> Warnung + Audit, KEIN fail-closed.
  A-W33-8 (basis_gate-Format):
    state.basis_gate_test_results.append mit
    demselben Format wie apply_and_recheck
    (Z. 7462-7472).
  A-W33-9 (i) ((b)-Rot): rc=17 sofort, kein
    Recovery. W25-2-Recovery bleibt (e)-Rot
    vorbehalten.
  K1 (max_tokens_judge): state.max_tokens_judge
    (Z. 4950) Default 2048; Config-Loader liest
    aus YAML budget.max_tokens_judge.
    Code-Default ist Fallback.
  K2 (4 Zeichen/Token): Kommentar gesetzt.
  K3 (Guard-Bezug): Kommentar gesetzt.
  Tests: 9 (T1, T2, T4, T4b, T5, T6, T7, T8, T9).
  Test-Helper _state initialisiert tmp_path als
    Git-Repo (git add -N braucht es).

  A-W33-12 (Umbenennung sauber):
    test_nur_patch_wird_jetzt_gelesen prueft
    EXPLIZIT:
      assert "core/x.py" in
          state.mess_protokoll_nach_apply
      assert "x = 1" in
          state.mess_protokoll_nach_apply
    (Nicht nur "Test existiert", sondern
    nachgewiesener Inhalt.)

Test-Anzahl: 1075 -> 1086 passed (+11 gesamt:
  2 W32 + 2 W33a netto + 9 W33b).

Naechster Schritt: Phase-19-Lauf mit U2a3.
  Messung: Judge sieht mess_nach + basis_gate.
  Erwartung: GO oder NO-GO statt ESKALATION.

Bekannte Luecken (Merkposten):
  W28a-Repair-Loop fehlt (W33b-2, eigener Block).
  W33b-4 (Doppel-_post_apply_messung W33b +
    apply_and_recheck nach GO — inhaltlich
    gleich, ~0.1 s Overhead, Optimierung spaeter).
  _loop_erkannt (W30b).
  A-W30-1-Messung (max_review_rounds: 2 nach
    5 Phasen-Laeufen pruefen).

================================================================
ENDE W32 + W33a + W33b
================================================================


================================================================
W35a-1 ERLEDIGT (2026-10-17) — LETZTER_BEFUND
================================================================

Commit: 79027d8.
Kategorie 2 (Schema, Tests).
Kein Tag probebetrieb-69.

Aenderungen:
  - _phase_yaml_status_update: neuer optionaler
    Parameter letzter_befund: str | None.
    Bei status="no_go": letzter_befund[:500]
    im Unterblock-Feld "letzter_befund".
    Bei status="done": letzter_befund = "".
  - _letzter_reviewer_befund (neu): liefert
    state.review_runden[-1]["raw"][:500]
    oder "".
  - run_phase, zwei no_go-Stellen (Z. ~3180
    unklar_eskalation, Z. ~3198 unterblock_no_go):
    letzter_befund=_letzter_reviewer_befund(state).

Schreibstelle (A-W35a-3a):
  Z. 2058-2066:
    ziel["status"] = status
    if status == "no_go" and letzter_befund:
        ziel["letzter_befund"] = letzter_befund[:500]
    elif status == "done":
        ziel["letzter_befund"] = ""

Tests: 1089 -> 1091 passed (+2).
  T1: test_no_go_schreibt_letzter_befund.
  T2: test_done_loescht_letzter_befund.

W35a-1-Rollback:
  git reset --hard b7d5c02 (W34b), wenn ein
  Test ausserhalb W35a-1 rot wird oder
  _phase_yaml_status_update-Aufrufe in
  bestehenden Tests brechen.

Naechster Schritt: W35a-2 (Planner-Resume),
  A-W35a-12/13/15/5b/10-Neu.

================================================================
ENDE W35a-1
================================================================


================================================================
W34b + W35a-1 + W35a-2 ERLEDIGT (2026-10-17)
================================================================

Commits: b7d5c02 (W34b), 79027d8 (W35a-1),
         5a2d7cf (W35a-1-Handoff),
         ca483cb (W35a-2).
Kategorien: 3 (W34b), 2 (W35a-1), 3 (W35a-2).
Kein Tag probebetrieb-69.

W34b (_phasen_basis_gate_ok ignoriert .werkstatt/):
  Bug: W32 (_schreibe_contract in run_phase)
    hat .werkstatt/contracts/<uid>.md geschrieben.
    Das Basis-Gate hat es als fremd_untracked
    markiert -> Deadlock vor Unterblock-Start.
  Fix: Filter auf _norm(p).startswith("werkstatt/")
    (nach _norm, weil _norm fuehrende Punkte
    entfernt).
  Tests: 3 (T1 .werkstatt/ ignoriert, T2 fremd
    fail-closed, T4 gemischt).
  Test-Anzahl: 1086 -> 1089.

W35a-1 (letzter_befund in phase.yaml):
  Vorbereitung W35a-2.
  - _phase_yaml_status_update: neuer Parameter
    letzter_befund: str | None.
    Bei no_go: letzter_befund[:500].
    Bei done: "".
  - _letzter_reviewer_befund (neu): liefert
    state.review_runden[-1]["raw"][:500].
  - run_phase, zwei no_go-Stellen (Z. ~3180
    unklar_eskalation, Z. ~3198 unterblock_no_go):
    letzter_befund=_letzter_reviewer_befund(state).
  Tests: 2 (T1 schreiben, T2 loeschen).
  Test-Anzahl: 1089 -> 1091.
  W35a-1-Rollback: git reset --hard b7d5c02
    (W34b) im Handoff-Commit 5a2d7cf
    nachgetragen (A-W35a-14).
  Lehre (A-W35a-18): Rollback-Kriterium gehoert
    in den CODE-Commit-Body, nicht nur in den
    Handoff.

W35a-2 (Planner-Resume im Phasen-Pfad):
  Bug: _phase_main_pfad uebersprang den Planner
    bei existierendem Plan. Bei offenen no_go/
    failed musste der Mensch manuell nachbessern
    (U2a3 yaml.YAMLError -> ValueError,
     Commit fbba8b0).

  Fix:
  - _phase_planner_resume (neu):
    Zustands-Automat Z1/Z2a/Z2b/Z3/Z4.
    Cap pro uid (state.planner_resume_anzahl).
    Merge via Struktur-Check (W16-Weg-Y-Schutz):
    done bleibt, no_go/failed -> pending.
    phase_stand + korrektur_kontext
    (reviewer_befund + solver_befund) an
    _planner_lauf (stufe=2).
  - RunState.planner_resume_anzahl:
    dict[str, int].
  - Aufruf in _phase_main_pfad vor dem
    Skip-Planner-Zweig, wenn
    "not resume_force" und offene no_go/failed.
    resume_force gewinnt (A-W35a-7).
  - 8 neue Audit-Kinds (Katalog 86 -> 94):
    planner_resume_start, _merge, _failed,
    _cap_erreicht, _solver_nicht_gerufen,
    _solver_ohne_befund, _befund_ohne_trigger,
    _solver_befund_kaputt.

  Zustands-Automat:
    Z4:  befund + trigger leer -> rc=18.
    Z1:  trigger leer + befund leer -> Resume.
    Z2a: trigger + aufrufe==0 -> rc=18.
    Z2b: trigger + aufrufe>0 + befund leer -> rc=18.
    Z3:  trigger + befund -> Resume MIT solver_kontext.
    ValueError in format_solver_befund -> rc=18.

  Tests: 11 (T1, T2, T4a, T4b, T5, T6, T7,
    T8, T9, T10, T11).
  Test-Anzahl: 1091 -> 1102.

W34a (in security-ai, Commit 87a2fbe):
  .gitignore enthaelt ".werkstatt/".

U2a3 (in security-ai, Commit fbba8b0):
  Manuell nachgebessert (yaml.YAMLError ->
  ValueError in apply()). W35a-2 macht das
  strukturell ueberfluessig: der Planner
  praezisiert beim Resume, statt Mensch.

Test-Anzahl Werkstatt: 1086 -> 1102 passed.
Test-Anzahl security-ai: 20 (unveraendert).

Naechster Schritt: Phase-19-Lauf mit W35a-Stack.
  U2b ist der naechste offene Block.
  Erwartung: Planer-Resume greift nicht (kein
  no_go/failed), U2b laeuft normal.
  Danach W29 (Phase-Review) greift am Ende.

Merkposten nach W35a:
  W35a-b (W29-Konsistenz bei Planner-Resume):
    Phase-Judge prueft geaenderten Plan.
    Erwartung: konsistent (Resume VOR
    Unterblock-Lauf). Nach 5 Phase-Laeufen
    messen.
  RR4 (Planner-Resume-Kosten): nach 5
    Phase-Laeufen messen, wie oft Planner-
    Resume triggert. Wenn > 30%:
    Ursache pruefen.
  RR2 (Praefix-Format): Planner liefert
    wieder das Praefix-Format, das der
    Check akzeptiert. Merkposten.

================================================================
ENDE W34b + W35a-1 + W35a-2
================================================================


================================================================
W36-W41 + PHASE 19 STAND (2026-10-17 abends)
================================================================

Werkstatt-HEAD: 6e4926a (W41).
security-ai-HEAD: f53a435 (U2b1+U2b2).
Tests Werkstatt: 1102 passed.
Tests security-ai: 1413 passed (9:20 min).

Phase 19:
  done:    U1, U2a1, U2a2, U2a3, U2b1, U2b2
  no_go:   U3
  pending: U4, U5, U6

Refactoring (W36):
  werkstatt/state.py:    BudgetExhausted, Measurement,
                         LLMReply, RunState, RepairAttempt,
                         SolverDiagnose, SolverBefund,
                         RecoveryVorschlag.
  werkstatt/parser.py:   _parse_phase_kopf, _parse_phase_plan,
                         _ID_MUSTER.
  pipeline.py:           11942 -> 11564 Zeilen.
  Re-Export-Fassade:     pipeline.py importiert aus
                         werkstatt.state + werkstatt.parser.

Strukturelle Fixes (W35a-2d-Reihe):
  W35a-2d-4: Anzahl-Check bei validiertem Split ueberspringen.
  W35a-2d-5: ID-Check bei validiertem Split ueberspringen.
  W35a-2d-6: Ambig-Check bidirektional (Praefix-Faelle).
  W38:       alter_plan im P10-P16-Format.
  W39:       Parser toleriert Kommentarzeilen.
  W41:       classify_verdict akzeptiert NO_GO.

Rollen-Prompts:
  W37: builder.md um 3 Abschnitte erweitert
       (Anker-Minimalitaet, test:-Feld, __all__).
  W40: judge.md (Auftragsverstoss = NO_GO),
       planner.md (letzter_befund ist Pflicht).

WAS HEUTE BLOCKIERT (U3):
  Auftrag verlangt Anker 'class RiskLevel(Enum):'.
  models.py enthaelt aber 'RiskCategory' (nicht RiskLevel).
  Der Auftrag stammt aus dem alten Plan (vor U2b1/U2b2)
  und wurde nie gegen die echte Datei gemessen.

  Der Solver hat das im letzten Lauf korrekt erkannt
  ('Der Auftrag beruht auf einer falschen Messung').
  Der Planner hat aber im Resume-Modus die Zieldatei
  NICHT gemessen (kein read_file), also den Fehler
  nicht gesehen.

NAECHSTER SCHRITT (W42):
  Planner-Resume muss vor dem Plan die Zieldateien
  messen (COMMAND: RUN read_file <pfad>).
  Heute macht der Planner das im Resume-Modus nicht.

  Konkret:
    - In _phase_planner_resume: read_file auf alle
      datei:-Pfade des offenen Unterblocks, BEVOR
      _planner_lauf gerufen wird.
    - Ergebnis an planner_lauf als 'gemessener_inhalt'
      (oder in korrektur_kontext) mitgeben.
    - Planner sieht dann 'class RiskCategory', nicht
      'class RiskLevel'.

  Ohne W42 wiederholt sich der Fehler bei jedem
  U3-Lauf.

  Alternativ pragmatisch:
    - U3-Auftrag manuell korrigieren (RiskCategory
      statt RiskLevel, ImmediateActionCategory
      anlegen, Mapping + Test als aktion:neu).
    - Dann U3-Lauf.
  Das ist aber der manuelle Eingriff, den W42
  strukturell verhindern soll.

OFFEN (heute nicht mehr):
  - W42 (Planner-Resume-Messung).
  - W36-2b (weitere Parser-Funktionen).
  - W36-3 (audit).
  - W36-4 (judge).
  - W36-5 (planner).
  - W36-6 (apply).
  - W35a-2c-Abnahme (war nachgeholt, aber nicht im
    Handoff als erledigt markiert).
  - Phase-19 U3-U6 + Sammel-Commit.
  - A-W30-1-Messung (max_review_rounds).
  - W28a-Repair-Loop (fehlt strukturell).

================================================================
ENDE W36-W41
================================================================

================================================================
UEBERGABE AN NEUEN BAU-CHAT (2026-10-18)
================================================================

Werkstatt-HEAD:  8aaa861 (W47).
security-ai-HEAD: c264c7f (U6 Doku-Nachzug).
Werkstatt-Tests: 1102 passed.
security-ai-Tests: 1448 passed.
Tag security-ai: probebetrieb-69 auf c264c7f.

PHASE 19 — inhaltlich abgeschlossen:
  U1, U2a1, U2a2, U2a3 (ChangeApplier)
  U2b1, U2b2 (Stub entfernt)
  U3 (ImmediateActionCategory)
  U4 (ImmediateActionService)
  U5 (Detection-Pipeline-Hook)
  U6 (Doku-Nachzug)
  Alle als Einzel-Commits im security-ai-main.
  KEIN formeller Sammel-Commit (W47-Bug:
  Gesamt-Review wurde uebersprungen, weil
  run_phase bei "alle done + phase_aktiv=True"
  zu frueh zurueckkehrte). Tag auf c264c7f.

phase.yaml:
  phase_id: 19
  phase_aktiv: False
  phase_start_head: d7b7c26.

WERKSTATT-FIXES SEIT W25-W30 (Kurzliste):
  W31-Mypy: tests/test_pipeline.py + test_phase.py
    mypy-clean.
  W32: _schreibe_contract im run_phase-Loop.
  W33a: _post_apply_messung liest patch-Pfade.
  W33b: _phase_apply_vor_review + Apply vor
    Review-Loop.
  W34b: Basis-Gate ignoriert .werkstatt/.
  W35a-1: letzter_befund in phase.yaml.
  W35a-2: Planner-Resume Zustands-Automat.
  W35a-2d: Merge-Block Suffix-Aufteilung
    (U2b -> U2b1+U2b2).
  W36-1a/1b: werkstatt/state.py.
  W36-2a: werkstatt/parser.py (Phasen-Parser).
  W37: builder.md (Anker-Minimalitaet,
    test:-Feld, __all__).
  W38: alter_plan im P10-P16-Format.
  W39: Parser toleriert Kommentarzeilen.
  W40: judge.md (Auftragsverstoss=NO_GO),
    planner.md (letzter_befund=Pflicht).
  W41: classify_verdict akzeptiert NO_GO.
  W42: Planner-Resume-Messung (read_file auf
    Zieldateien).
  W43: new_file-Idempotenz.
  W44: Judge-Prompt-Groesse begrenzen.
  W45: Planner-Resume zeigt fehlende Dateien.
  W47: Idempotenz-Check vor Gesamt-Review.

OFFENE PUNKTE:
  W46: Judge-Prompt fuer Doku-Bloecke.
    Doku-Patches (U6) haben keine Tests.
    Judge bekommt basis_gate_test_results leer
    + mess_nach 40652 bytes. Antwortet leer.
    Loesung: Doku ohne Judge pruefen (nur
    Commit-Review) oder Prompt drastisch
    kuerzen. Kategorie 3, Reviewer-Block.

  W48: Planner-Resume bei phase_aktiv=False.
    Der Lauf 23:38 hat den Planner gerufen,
    obwohl phase_aktiv=False. Planner hat
    Phase 20 mit WERKSTATT-Dateien formuliert
    (harness/pipeline/judge.py), nicht
    security-ai-Dateien. Vermutlich fehlt
    der phase_aktiv-Check in _phase_main_pfad
    vor dem Planner-Resume.

  W49: Sammel-Commit-Erkennung (Phase 19).
    W47 loest das fuer kuenftige Laeufe.

  W36-2b..6: weitere Modularisierung
    (parser.py-Rest, audit.py, judge.py,
    planner.py, apply.py).

  W28a-Repair-Loop (fehlt strukturell).

  W35a-2d-b: W29-Konsistenz nach
    Planner-Resume.

  A-W30-1-Messung: max_review_rounds=2
    nach 5 Phasen-Laeufen pruefen.

NAECHSTER SCHRITT:
  1. W48 (klein): _phase_main_pfad: Planner-
     Resume nur bei phase_aktiv=True UND
     no_go/failed.
  2. Phase 20 mit --phase (echter Auftrag).
     planner_modus: manual.
  3. W46 als Vorbereitung fuer Phase 20.

Testbasis (Werkstatt):
  pytest tests/ -q: 1102 passed.
  ruff --no-cache: 0.
  mypy pipeline.py + werkstatt/: 0.

Testbasis (security-ai):
  pytest tests/ -q: 1448 passed.
  ruff --no-cache: 0.
  mypy core/ harness/: 0 (100 Dateien).

ENDE UEBERGABE
================================================================

## W48-NACHABNAHME (2026-10-18)

W48 wurde am 2026-10-18 vor expliziter Reviewer-
Freigabe committet (NO-GO aus A-W48-9). Inhaltlich
umgesetzt: A-W48-9b (direkter phase.yaml-Leser in
_planner_main_pfad, fail-closed bei aktiv und
abgeschlossen), A-W48-10 (4 Tests T-W48-a/b/c/d),
A-W48-11 (Sperre auch bei inaktiver Phase — bewusst;
0 bestehende Tests betroffen). Nachabnahme durch
Reviewer am 2026-10-18 mit Auflagen A-W48-13..19.

Nachbesserung W48-A16 (Commit 7c46c7b):
  Katalog 107 -> 109 (planner_blockiert_aktive_phase,
  planner_blockiert_phase_abgeschlossen) — A-W48-14.
  Print-Statement in _planner_main_pfad um
  "K offene Reste" erweitert (beide Zustaende) —
  A-W48-18.
  T-W48-a/b um Katalog-Assertion erweitert, T-W48-e
  neu — A-W48-17.
  Tests: 1113 -> 1114 passed.

Merkposten W48-A16-b (A-W48-19, Kategorie 2):
  Struktureller Test, der alle audit("…")-Aufrufe
  in pipeline.py gegen _AUDIT_KINDS_BEKANNT prueft
  (kein audit("X") ohne X im Katalog). Ziel: die
  Klasse der Katalog-Zaehlfehler strukturell
  schliessen, statt sie einzeln nachzubessern.
  Nicht in W48-Scope. Nach Phase 20.

Merkposten W46b/c-Rollback:
  W46 ist ein Commit (38d3960), W46b (Doku-Patch)
  und W46c (Doku-Phase) teilen den Rollback. Bei
  spaeterem Rollback von W46c muss W46b mitgerollt
  oder separat revertiert werden.

## W50-NACHABNAHME (2026-10-18)

W48 adressiert --planner, nicht --phase. Der 23:38-Bug
(--phase bei abgeschlossener Phase -> Planner-Durchfall
mit falschem phasen_text) wird erst mit W50 gefixt.
A-W48-9b-Empfehlung des Reviewers (W48 in
_planner_main_pfad) war falsch; Korrektur in W50
(HR-R7: Reviewer-Fehler).

W50 (Commit 739397f):
  _phase_main_pfad: force_new_phase-Parameter.
  Direkter phase.yaml-Leser nach Basis-Gate, vor
  RunState-Bau. phase_aktiv=False ohne Flag -> rc=65,
  audit phase_abgeschlossen_keine_neuanlage.
  Mit Flag: audit phase_neuanlage_mit_flag, durchlassen.
  CLI: --new-phase nur mit --phase, _validate_new_phase_args
  als eigene Funktion (vor main()-root-Check testbar).
  Katalog 109 -> 111.
  Tests: 1114 -> 1120 passed (T-W50-a..f).

A-W50-8: Katalog-Kette
  103 (W35a-2d) -> 109 (W48-A16, +6 in W46+W48)
  -> 111 (W50, +2).
  Neue Kinds W50: phase_abgeschlossen_keine_neuanlage,
                  phase_neuanlage_mit_flag.

Merkposten W50-A16-b (A-W48-19, Kategorie 2):
  Katalog-Nutzungs-Test (alle audit("…")-Aufrufe
  gegen _AUDIT_KINDS_BEKANNT). Nach Phase 20.

## W51h-NACHABNAHME (2026-10-18)

W51h gebaut (Commit 8205456, 5 Tests, 1153 -> 1158).
Plan + COMMANDs im selben Reply werden jetzt
verwertet (parser-basierte Plan-Pruefung, VOR
W51e). W51g-Kollision aufgeloest: Format-Fehler ->
Loop Runde 2, W51g-b-Kontext greift.

W52 (Planner-Loop als Modul, Messungen/Replies in
Dateien) wird getrennt:
  W52a (Modul-Refactor, Kategorie 2): planner.py
    auslagern, Verhalten identisch. Nach Phase 20a.
  W52b (Datei-Struktur, Kategorie 3): Messungen
    und Replies in Dateien. Nach W52a.
Grund: W51h-Fix zuerst (akut Phase-20a-blockierend),
W52a als sicherer Refactor auf gruener Basis,
W52b als Verhaltensaenderung auf W52a.

Merkposten (nach Phase 20a):
  W51h-b: nach 3 Laeufen pruefen, ob W51h
    ueberhaupt greift (Plan parsebar in Runde 1).
    Wenn nein: Parser-Lockerung pruefen.
  W51g-b2: Check-Fehler (nicht Parse-Fehler) in
    letzter_plan_fehler aufnehmen (oder durch
    W52b-fehler.json loesen).
  W51b-2: Resume-Pfad hat keine _plan_ist_*-
    Pruefungen. Eigener Block.

Phase-20a-Messung M1-M8:
  M1: Runde 1: COMMANDs.
  M2: Runde 1: Plan parsebar? (W51h greift)
  M3: Runde 1 Format-Fehler? W51g-b-Kontext in
      Runde 2?
  M4: Dedup greift (W51g-a)?
  M5: Plan angenommen (PHASE-Kopf)?
  M6: max_review_rounds=2 (Lauf 1/5 fuer A-W30-1).
  M7: W46b/c bei Doku-Patches.
  M8: Review-Runden bis GO/NO-GO.

---

# Handoff 2026-10-22 (archiviert)

Stand: 3a-3 komplett (HEAD 6e440e6).
Aus Bau-Handoff.md entfernt 2026-10-22, um den aktiven Handoff
schlank zu halten. Aktueller Handoff: Bau-Handoff.md.

## Aktueller Block

3a-3 (_phase_main_pfad, 641 Z., Z. 10360-11000):
641 Z. / 43 Statements / 23 Returns / 5 Parameter.
Aufteilungs-Vorschlag in 3 Sub-Bloecke:
  3a-3a Vorlauf    (body[0]..[21], Z. 10360-10462, ~103 Z.)
  3a-3b Plan-Verarb.(body[22], Z. 10463-10632, ~170 Z.)
  3a-3c Planner-Loop (body[23]..[42], Z. 10635-11000, ~366 Z.)
Deadlock-Kette: 3x run_phase-Aufruf + phase_korrektur_zyklus-
Sicherung in 3a-3c (Vorab-Messung unten).
6 getsource-Tests (Kandidaten Kategorie 2).

Naechster konkreter Schritt: Reviewer-Start-Posting 3a-3
mit Aufteilungs-Vorschlag. Dann 3a-3a.

Rollback-Anker: 416550a. Delta != 0 -> Rollback.

## Abgeschlossen seit letztem Handoff

- 3a-1c-2b (W2-Extraktion): done (277029f + 74ff77d + ac4956f).
  _commit_review_w25_loop, 10 Parameter, Aufruf Z. 8811-8817.
- 3a-1c-3 (C0+C1+C2): done (da67198 + bb919d1 + d06cf23 + fafc5b5).
  _vorlauf_und_state + VorlaufErgebnis, _basis_gate.
- 3a-1c-4 (C8+C9): done (75f844b Handoff-Refresh, 5762d8e Code).
  _approval_und_human_gate (4 Parameter, 8 Returns).
  C8 = 8819-8854, C9 = 8855-8898. run_pipeline endet 8917.
  Return-Bilanz: 27/3/2/7/8 = 47.
  3 Test-Anpassungen (#1 test_phase.py:804, #5 test_pipeline.py:6324,
  #12 test_pipeline.py:8671) via duale Quelle/Split.
- 3a-2a (Vorlauf): done (20f0e7d).
  _phase_vorlauf(state, project_name) -> PhaseVorlaufErgebnis | int.
  Dataclass PhaseVorlaufErgebnis in werkstatt/state.py
  (state, unterbloecke, api_key, max_phase).
  if-state_ref-Guard bleibt in run_phase.
  Return-Bilanz: run_phase 17, _phase_vorlauf 7, Summe 24
  (+2 Extraktions-Artefakte gegen 22).
  Baseline 1245/17/9 unveraendert.
- 3a-2b (Loop): done (8e46062).
  _phase_unterblock_loop(state, project_name, unterbloecke,
  max_phase) -> int. 4 Parameter (Signatur-Freeze 18c).
  M-72-Fix: rc_unterblock = 0 Vor-Init + return rc_unterblock
  (Z. 2399 Klasse-4 + Z. 2400 Fallback).
  Return-Bilanz: 89 Returns (run_phase 13, loop 6).
  2 Test-Anpassungen (getsource -> _phase_unterblock_loop).
  Baseline 1245/17/9 unveraendert.
- 3a-2d (Wiederaufnahme): done (00ffb5e).
  _phase_wiederaufnahme(state, project_name, state_ref,
  aggregat, wahl, api_key) -> int. 6 Parameter.
  5 Returns. Rekursion max 1 Tiefe.
  Test-Anpassung test_zyklus_teilt_sich (erster Assert).
- 3a-2 GESAMT (20f0e7d + 8e46062 + 3f98364 + 00ffb5e):
  run_phase von 528 Z. / 22 Returns auf 4 Verteiler-Returns.
  4 neue Funktionen: _phase_vorlauf, _phase_unterblock_loop,
  _phase_nachlauf, _phase_wiederaufnahme.
  2 neue Dataclasses: PhaseVorlaufErgebnis, NachlaufErgebnis.
  Return-Bilanz: 87 -> 92 (Delta +5, Extraktions-Artefakte).
  Baseline 1245/17/9 durchgehend.
- C6 (Coverage/Chaos): gestrichen (Durchlauf 48, gehoert zu 3b).

## C8/C9-Grenzen-Korrektur (Reviewer-Auflage A1)

OFFENE-BLOECKE.md Z. 20 war FALSCH. Altes Zitat:
  "C8 Approval Schritt 6 (Z. 8762-8797) offen | C9 Human-Gate
   (Z. 8798-8841) offen"
Real gemessen (HEAD 5e50ea6, SCHRITT-Kommentare + AST):
  SCHRITT 5 (Commit-Review) = Z. 8660  -> C7 (done)
  SCHRITT 6 (Approval+Human-Gate) = Z. 8820 -> C8+C9
  C8 = Z. 8819-8854 (Approval-Dokument + Phasen-Paket-Sammlung)
  C9 = Z. 8855-8898 (Human-Gate, input(), Commit-Entscheidung)
  run_pipeline endet bei Z. 8898 (nicht 8841).
  Bereich 8762-8817 = C7-Rest, nicht C8.
Korrektur ist in docs/OFFENE-BLOECKE.md eingepflegt (Z. 20).


---

## Naechste Bloecke (Reihenfolge laut ROADMAP.md Z. 217-223)

1. 3a-3 (_phase_main_pfad, 641 Z., Deadlock) — naechster Block.
2. 3b (Loop-Umbau; enthaelt C6 + Reviewer-Modus + Quality-Gate).
3. 3c (NEUBAU-Abloesung).

## Offene Merkposten

- Werkstatt-Entkopplung von security-ai: UEBERFAELLIG laut
  OFFENE-BLOECKE.md Z. 19 (sollte nach 3a-1c-2b, vor 3a-1c-3
  erledigt sein). Kein Blocker fuer 3a-1c-4, aber zeitnah
  einsortieren. Nach 3a-1c-4 als eigenen Block einplanen.
- 3a-1c-2-V2-Groesse (OFFENE-BLOECKE.md Z. 29): V2 = 303 Z.,
  13 Steuerstellen, 12 Parameter. Zerlegung V2a/V2b vor 3b pruefen.
- Struktur-Tests umstellen: Rest-Klassifikation folgt in 3a-1c-4
  (Auflage 2).
- M-57 (Commit-Bezuege pro Body-VOR-Wert): offen aus der Runde
  vor diesem Handoff. Nachziehen vor Session-Abschluss.
- Commit-Body-Lehre (Z. 21): bei Commit-Body-Pruefung ZWEI
  Messungen — git-log-Chronologie + pytest --collect-only auf
  JEDEM Zwischenstand.

## Archiv

Vorheriger Handoff (2026-10-18, W52b) in Bau-Handoff-Archiv.md.
Vorgaenger-Handoff (2026-10-20, 3a-1c-2b "NO-GO") war ueberholt:
3a-1c-2b ist done, 3a-1c-3 ist done, C6 gestrichen.


## 3a-3 — Vorab-Messung (HEAD 416550a)

Gemessen am 2026-10-22. Dient als Startpunkt fuer den naechsten Block.
Naechster Kontext kann direkt hier ansetzen.

### _phase_main_pfad — Signatur + Zeilen

  def Z. 10360..11000 (641 Zeilen).
  positional: ['project_name', 'phasen_text', 'state_ref',
               'resume_force', 'force_new_phase']
  kw-only:    []
  Returns: 23.

### Aufrufer

  Intern:
    Z. 11386: rc = _phase_main_pfad(
    (einziger interner Aufrufer, in main()).
  Tests: 6 getsource-Ziele (siehe unten).

### Top-Level-Statements (43)

  Block A (Vorlauf, body[0]..[21], Z. 10360-10462, ~103 Z.):
    Docstring, api_key, project_dir, Baseline-Gate,
    agents_dir, load_agents, load_docs, file_whitelist,
    build_catalog, planner-config (modus, max_runden),
    plan_vorhanden-Try.

  Block B (Plan-Verarbeitung, body[22], Z. 10463-10632, ~170 Z.):
    if plan_vorhanden is not None:
    Enthaelt Plan-Parsing, Resume-Logik, Unterblock-Init,
    phase_start_head-Setzung, audit-Calls.

  Block C (Planner-Loop, body[23]..[42], Z. 10635-11000, ~366 Z.):
    historie, phase_yaml-Pfad, force_new_phase-Check,
    RunState-Anlage, run_id-Setzung, audit pipeline_start,
    for runde in range(1, planner_max_runden+1):
      -> Planner-Aufruf, run_phase-Aufruf (3x),
         phase_korrektur_zyklus-Sicherung.
    phase_plan_ok-Check, return 0.

### Rekursion + Deadlock-Stellen

  run_phase-Aufrufe in _phase_main_pfad:
    Z. 10617: rc = run_phase(project_name, state, state_ref)
    Z. 10629: rc = run_phase(project_name, state, state_ref)
    Z. 10931: rc = run_phase(
  phase_korrektur_zyklus-Sicherung:
    Z. 10621: if ... and state.phase_korrektur_zyklus < 1:
    Z. 10627: state.phase_korrektur_zyklus += 1
    Z. 10541: audit phase_korrektur_zyklus_vorher: 0

  Deadlock-Kette dreistufig (strukturell):
    run_phase -> _phase_wiederaufnahme -> run_phase
      (Rekursion in 3a-2d, max 1 Tiefe).
    _phase_main_pfad -> run_phase (3x)
      (Sicherung durch phase_korrektur_zyklus < 1
       in _phase_main_pfad Z. 10621).
    Doppelte Sicherung: run_phase-Rekursion UND
      _phase_main_pfad-Sicherung.

### getsource-Tests auf _phase_main_pfad

  tests/test_pipeline.py:7452  inspect.getsource(pipeline._phase_main_pfad)
  tests/test_pipeline.py:7463  inspect.getsource(pipeline._phase_main_pfad)
  tests/test_pipeline.py:7472  inspect.getsource(pipeline._phase_main_pfad)
  tests/test_phase.py:1383     ins.getsource(pipeline._phase_main_pfad)
  tests/test_phase.py:1591     ins.getsource(pipeline._phase_main_pfad)
  tests/test_phase.py:1600     ins.getsource(pipeline._phase_main_pfad)

  6 Kandidaten fuer Test-Anpassungen (Kategorie 2) bei
  Extraktion von Teilen aus _phase_main_pfad.

### Baseline

  pytest 1245 passed / ruff 17 / mypy 9 / AST 6 / Katalog 167.
  Delta 0.

### Aufteilungs-Vorschlag (3 Sub-Bloecke, analog 3a-2)

  Der Block ist mit 641 Z. / 43 Statements / 23 Returns
  zu gross fuer einen Schnitt. Drei natuerliche Sub-Bloecke:

  3a-3a: Vorlauf (body[0]..[21], Z. 10360-10462, ~103 Z.)
    api_key, project_dir, Baseline-Gate, agents, docs,
    file_whitelist, build_catalog, planner-config.
    Neue Funktion: _phase_main_vorlauf(...) -> PhaseMainVorlaufErgebnis | int.

  3a-3b: Plan-Verarbeitung (body[22], Z. 10463-10632, ~170 Z.)
    if plan_vorhanden is not None.
    Neue Funktion: _phase_main_plan_verarbeiten(...) -> ... | int.
    ODER als Teil von 3a-3a belassen (haengt von
    Variablen-Transfer ab, M-94).

  3a-3c: Planner-Loop (body[23]..[42], Z. 10635-11000, ~366 Z.)
    RunState, historie, for runde-Loop mit 3 run_phase-Aufrufen,
    phase_korrektur_zyklus-Sicherung, phase_plan_ok-Check.
    Neue Funktion: _phase_main_planner_loop(...) -> int.
    ODER weiter zerlegt (Loop-Body vs. Loop-Vorbereitung).

  Reihenfolge-Empfehlung: 3a-3a -> 3a-3b -> 3a-3c (wie 3a-2a/b/c/d).
  Deadlock-Analyse (M-65-Muster): vor 3a-3c, weil dort die 3
  run_phase-Aufrufe + phase_korrektur_zyklus-Sicherung liegen.

  Test-Anpassungen: 6 getsource-Tests. Kategorisierung pro Block
  im jeweiligen Start-Posting (a/b/c/d), wie bei 3a-2.

### Naechster Schritt (frische Session)

  1. Reviewer-Start-Posting 3a-3 mit Aufteilungs-Vorschlag.
  2. Nach Freigabe: 3a-3a (Vorlauf), dann 3a-3b, 3a-3c.
  3. 3a-3c: Deadlock-Analyse strukturell + phase_korrektur_zyklus
     zitieren (wie 3a-2d).


---

# Archiv: Bau-Handoff 2026-10-29 + Loop-Neubau 2026-10-30

Archiviert am: 2026-10-30 18:57:11

Dies ist der alte Handoff (Session 2026-10-29 + Loop-Neubau 2026-10-30).
Der aktuelle Handoff ist `Bau-Handoff.md`.

# Bau-Handoff — Session 2026-10-29 (Durchbruch)

**Session-Ergebnis:** Gold-Umbau + Scout-Agent + Prompt-Audit.
Suite 1619 -> 1622. Erster RERUN mit 3/3 Tasks approved.
Commit `2c4703d` (Gold-Umbau: `_baue_api_index` + Reviewer).

---

## STAND

**Werkstatt** (`/opt/werkstatt`):
- Branch `umbau/phase-2`
- Suite: **432 passed, 5 skipped**
- Ruff Baseline (gesamt): 13 Errors ueber alle `werkstatt/*.py`.
  Hauptverteilung: loop.py 7, planner.py 1, builder.py 2,
  agent.py, apply.py, audit.py, commit_input.py, measurement.py,
  prompts.py, verify.py (Rest). `pipeline.py` ist weg.

**Zielprojekt** (`/opt/security-ai`):
- Services active, `.env` vollstaendig
- Timeline funktioniert (15 Eintraege, klickbar, mit Score)
- Letzter RERUN 19:10 — 3/3 Tasks approved

---

## LOOP-NEUBAU (2026-10-30)

Der grosse Schnitt: `pipeline.py` (11.119 Z.) und die alte
`pipeline`-Test-Suite (~28.000 Z.) sind entfernt. Der Loop
laeuft ausschliesslich ueber `werkstatt/*.py`.

**Was weg ist:**

- `pipeline.py` (11.119 Zeilen) — Monolith, produktiv tot.
- `tests/test_pipeline.py` (11.377 Z.).
- `tests/test_pipeline_integration.py` (1.958 Z.).
- `tests/test_phase.py` (2.637 Z.).
- `tests/test_planner.py` (649 Z., testete 70% `pipeline`-Planner).
- `tests/test_anti_patterns.py` (549 Z.).
- `tests/test_hooks_anti_patterns.py` (58 Z.).
- `tests/test_audit_kinds.py` (268 Z.).
- `tests/test_projekt_schema.py` (227 Z.).
- `hooks/anti_patterns.py` + `anti-patterns/` (Katalog + README).
- `tests/conftest.py`: `import pipeline as _pipe` + `ap_block_inprocess`-Fixture.
- `werkstatt/agent.py`: `_anti_pattern_block`, `_AP_HOOK_PATH`, `_AP_HOOK_TIMEOUT_S`, `mit_anti_patterns`-Parameter.
- `werkstatt/audit.py`: `_ap_audit_haeufigkeit`, `anti_patterns_injiziert` aus Katalog.

**Commits 2026-10-30:**

- `513ab55` — `build_system_prompt` ohne `mit_anti_patterns`-Parameter.
- `a9abe5b` — 2 `mit_anti_patterns`-Tests entfernt.
- `0bcc732` — 5 Test-Dateien + Anti-Pattern-Hook + Katalog entfernt (17.473 Z.).
- `f163f33` — `patch(pipeline.*)`-Aufrufe entfernt (wirkungslos).
- `07a4de6` — `pipeline.py` + 3 Tests + Anti-Pattern-Code (12.401 Z.).

**Neue Suite:** 432 passed, 5 skipped. **32 Test-Dateien** weniger als vorher.
**Ruff gesamt:** 13 Errors (Baseline ohne `pipeline.py`).
**`voraus 31`** ungepusht.

**Was jetzt kommt (Roadmap):**

1. **Loop-Weg-Tests** — jeder Pfad im Gold-Loop braucht einen Test:
   Explorer, Scout, Architect, Planner-Split, Builder (mit
   `_filtere_auf_funktionen`), Reviewer (mit `## SEMANTIK-CHECK`),
   Human-Gate (M-487: committet selbst), Phasen-Uebergaenge,
   Fail-Closed, Redaction. **Die alten Tests sind Historie, die
   neuen sind Spec.**
2. **Security-Audit** — wenn der Loop produktiv ist:
   - Keine IPs / Secrets / Nutzdaten ans LLM.
   - UI-Login (fehlt komplett).
   - `redact_all` in `ask_llm` ist da, aber niemand testet ihn.
3. **Push** — 31 Commits.

---

## WAS FUNKTIONIERT (verifiziert 2026-10-29)

### Gold-Umbau (`2c4703d`)
- **Architect** (`ARCHITECT_SYSTEM`, deepseek-reasoner): freie Prosa
  mit `## <pfad>`-Ueberschriften, Interface + Logik + Integration.
- **Planner** (`_zerlege_in_sub_tasks`, deepseek-chat): zerlegt Prosa
  in Tasks (JSON).
- **Zwei Agents, zwei Calls.** Tool-Use-Loop entfernt.

### Scout-Agent (`_run_scout` + `_baue_api_index`)
- **`_baue_api_index`:** AST-basiert, deterministisch. Liefert pro Datei:
  `__all__`, Klassen (Methoden + Signaturen + Rueckgabetypen),
  Top-Level-Funktionen, Imports.
- **`_format_api_index_for_prompt`:** deterministisch, kompakt.
- **`_finde_api`:** deterministisch, sucht API im Index.
- **`_run_scout`** (deepseek-chat): formuliert Auftrag aus API-Index.
- **Widerspruchs-Check:** prueft APIs aus Auftrag gegen Code-Index
  (`read_events` existiert nicht -> `list_recent_assessments`).

### Prompt-Audit (P0-P3)
- **`_BUILDER_SCHNITTSTELLE`** an `ARCHITECT_SYSTEM`:
  Architect kennt Builder-Grenzen (max 8000 Tokens, keine Tools,
  `## <pfad>`-Pflicht).
- **`_REVIEWER_SCHNITTSTELLE`** an `BUILDER_SYSTEM`:
  Builder kennt Reviewer (bestehende Aufrufe pruefen, HIGH-Bug bei
  Entfernung).
- **`ARCHITECT_SYSTEM`:** `GOLD: SCOUT-KONTEXT` — nutzt APIs aus
  dem Code-Index, NICHT aus der Aufgabe.
- **`_SCOUT_NACHFOLGER_BLOCK`:** Scout liefert JSON, Architect Prosa.
- **Toter else-Zweig (`PLANNER_SYSTEM`)** entfernt.

### Reviewer Diff-Check (P0)
- `REVIEWER_SYSTEM` prueft **jede `-`-Zeile** gegen die volle Zieldatei.
- **HIGH-Bug** wenn bestehender Aufruf entfernt, Funktion ueberschrieben,
  API erfunden.
- **Live-Beleg 18:58:** t3 rejected (Builder wollte `_section_timeline`
  statt `_section_timeline_entries` aendern).

### Import-Validierung (`996d616`)
- Klassischer Builder-Pfad prueft jetzt Imports
  (`_validate_imports_in_patch`).
- Bei Fehler: Patch verworfen, `builder_patch_import_fehler`.
- **Live-Beleg 18:51:** `AuditReadError` (erfunden) -> Task failte sauber,
  kein Service-Crash.

### Timeline (Zielprojekt, `5101e84`)
- **Backend** (`routes_state.py`):
  * `_section_timeline_entries` liefert `ts_display`, `href`, `score`,
    `audit_id`.
  * `_format_timeline_ts` (ISO -> YYYY-MM-DD HH:MM:SS).
  * `dashboard_state` ruft `_section_timeline_entries` (nicht
    `_section_timeline`).
- **Frontend** (`dashboard.js`):
  * `fetchState` unterstuetzt Array + `{entries}`.
  * `renderTimeline` nutzt `ts_display`, `href`, `score`, `agent`.
- **CSS** (`components.css`): 7 Timeline-Klassen.
- **Ergebnis:** 15 Eintraege, formatiert, klickbar (Link auf
  `/audit/<audit_id>`), mit Score.

---

### M-487 — Human-Gate committet selbst (`31c6ff3`)
- **`_committe_zielprojekt(state)`** in `werkstatt/loop.py`:
  `git status` -> `git add -A` -> `git commit` -> `git rev-parse HEAD`.
- Aufruf im `_human_gate`-`j`-Zweig. Fail-closed: Bei Git-Fehler
  bricht der Loop ab (`✗ LOOP FEHLGESCHLAGEN`), statt `✓` zu luegen.
- **Nur bei explizitem `j`.** Auto-Approve committet nicht.
- **4 Audit-Events:** `loop_human_gate_committed`,
  `loop_human_gate_commit_skip`, `loop_human_gate_commit_fehler`,
  `loop_human_gate_commit_abort`.
- **Betriebs-Voraussetzung:** `.git/` im Zielprojekt muss vom
  Loop-User (`security-ai`, Gruppe `builder`) beschreibbar sein.
  Setgid auf `.git`-Verzeichnisse. Keine `root:root`-Dateien.
- **Live-Beleg 20:36:** RERUN `4e860c3` — Builder+Reviewer+Phase-Review
  in 4s, Human-Gate `j` -> automatischer Commit, `✓ LOOP ERFOLGREICH`.

## ERLEDIGT (2026-10-29)

### K48 — old_string-Patch-Ansatz
- Builder nutzt `_build_patches_fuer_datei` mit vollem Datei-Inhalt +
  relevantem Architect-Abschnitt + Feedback + Reviewer-Bugs +
  Verify-Fehlern + Reflection-History.
- `BUILDER_SYSTEM`: "Erweitern statt Ueberschreiben"-Regel.
- `_architect_abschnitt`: versteht beide Formate
  (`## <pfad>` + innerhalb von `## 3.`).

### K50 — Fake-Done bei Reviewer-Reject
- `_patches_wirklich_angewendet` (fail-closed).
- `last_verify_errors` kumulativ.
- `applied_count` an allen Apply-Pfaden.

### K55b — `_marker_rest` praezisieren
- Nur konkrete Tool-Call-Marker pruefen.
- `<migrationsstand pflicht>` wird durchgelassen.

### K56a — Planner-Reflection
- Cherry-Pick, aber **nicht** aktiv (Kaskade, im Gold-Umbau entfernt).

### K60 — Builder-Diagnose
- `builder_keine_patches` mit Details (raw_len, raw_prefix,
  raw_has_context, patches_vor_normalisierung, ...).

### K61a — `task_files` normalisieren
- `_normalisiere_task_files` an 3 Stellen.
- Kurze Pfade -> volle Pfade (aus Explorer).

### K61b — `last_planner_info` bei JSON-Fehler
- Wird gesetzt bei `planner_json_fehler`.

### K61c — Explorer-Pfade aufloesen
- `rglob` findet volle Pfade.
- `_aufgabe_pfade` enthaelt volle Pfade.

### K62 — Import-Validierung klassischer Pfad
- In `run_builder` nach `_normalisiere_aider_patches`.

### Prompt-Audit P0-P3 + Gold-Umbau + Scout + API-Index
- Siehe "Was funktioniert".

---

## OFFEN (Prioritaet)

Kanonische offene Liste: `docs/OFFENE-BLOECKE.md`.
Dieser Abschnitt fuehrt nur die session-relevanten P0-P4.

### ✅ P0 — `PLANNER_SPLIT_SYSTEM` an Gold-Format (erledigt `aa7881f`)
**Entscheidung:** Option (b) — deterministische Python-Segmentierung.
`_segmentiere_nach_pfad(prosa)` in planner.py zerlegt an
`## <pfad>`-Ueberschriften, Fallback in `_zerlege_in_sub_tasks` und
`_llm_split_einzel_task`, wenn `architect_start` fehlt.
Der `PLANNER_SPLIT_SYSTEM`-Prompt bleibt unveraendert — die
LLM-Marker sind nicht mehr Pflicht.

### ✅ P0 — Builder-Prompt: Funktion-Wahl (erledigt `aa7881f` + `c13bb8a`)
**Loesung:** zwei Ebenen.
1. `## FUNKTION-WAHL` in `BUILDER_SYSTEM` (`aa7881f`): waehle die
   genannte Funktion, nicht die aehnlichste.
2. `_filtere_auf_funktionen(abschnitt, task_text)` (`c13bb8a`):
   schneidet den Architect-Abschnitt auf die Task-Funktionen zu,
   bevor er in den Builder-Prompt geht. Verhindert, dass der Builder
   fremde Funktionen aus demselben Datei-Block umbaut.

### ✅ P1 — Reviewer Semantik (erledigt `aa7881f`)
**Loesung:** `## SEMANTIK-CHECK` in `REVIEWER_SYSTEM`:
- Task nennt Funktion X, Diff nutzt Funktion Y → HIGH-Bug.
- Bestehender Aufruf ohne Task-Auftrag entfernt → HIGH-Bug.
- API erfunden (nicht im Import-/Code-Index) → HIGH-Bug.
Live-Beleg 20:16: RERUN approved im 1. Durchlauf, weil Builder
nur `_section_timeline_entries` angefasst hat.

### P2 — Frontend-Tests (1-2h)
**Problem:** `dashboard.js` ist ungetestet.
**Optionen:** Jest/Vitest mit jsdom; `node --check` (nur Syntax);
manuelle Browser-Tests.

### P3 — Doku-Ueberarbeitung
- `AGENTS.md`: Agent-Kette (Scout, Architect, Planner, Builder,
  Reviewer).
- `docs/ARCHITEKTUR.md`: Layer, API-Index, Prompt-Kette.
- `docs/RUNBOOK.md`: RERUN, Debug, safe.directory.

### P4 — K14 / K18 (gross)
- `run_pipeline_loop` 700 Zeilen -> 7 Phasen-Funktionen.
- `pipeline.py` 11k Zeilen zerlegen.

---

## NAECHSTE SESSION — START

**Aus Session 2026-10-29 spaet (nach Handoff-Update):**

- **M-487 erledigt** (`31c6ff3`), live bewiesen (`4e860c3`).
- **Neuer offener Punkt `R-CHECK-1`** (siehe `docs/OFFENE-BLOECKE.md`):
  Reviewer prueft Task-Zahlen nicht. Live-Beleg 20:42: Task verlangt
  `limit=10`, Builder schreibt `limit=5`, Phase-Review approved.
  Fix: `## KONSTANTEN-CHECK` in `REVIEWER_SYSTEM`.
- **Naechster Block:** `R-CHECK-1` (klein, ~15 min).

## NAECHSTE SESSION — START (alt)

**Vorbereitung:**
1. `git status --short --branch` sauber?
2. `git log --oneline -1` == letzter Commit?
3. `pytest -q` — 1622 erwartet.
4. `systemctl is-active` — alle active?

**Erste Aktion: P4 (PLANNER_SPLIT_SYSTEM)**
- Messung: `grep -n "architect_start\|PLANNER_SPLIT_SYSTEM" werkstatt/planner.py`
- Fix: `PLANNER_SPLIT_SYSTEM` anpassen.

**Danach:** Builder-Prompt (Funktion-Wahl) + Reviewer (Semantik).

**Dann:** RERUN mit neuer Aufgabe (z. B. Timeline-Sortierung).

---

## HARD-RULES

1. **Messen, nicht raten.** Keine Fixes ohne Grep-/Test-Beleg.
2. **Ein Block, warten auf Paste.** Kein Vorpreschen.
3. **Backup vor `cat >`.** `/root/backups/werkstatt/` oder
   `/root/backups/security-ai/`.
4. **`python3`, nicht `python`.**
5. **Kein `systemctl stop <timer>`.**
6. **Kein `grep`/`tee` um interaktive Prozesse** (TTY-Problem).
7. **`git status --short` vor Commit.**
8. **Heredoc in Bash: nur <30 Zeilen.** Sonst Python-Heredoc oder
   stueckweise.
9. **Kein Aider-Mix.** `old_string`/`new_string` — nicht
   `context+old+new`.
10. **`_format_code_index_for_prompt` ist tot** — nur
    `_format_api_index_for_prompt` nutzen.
11. **`PLANNER_SYSTEM` ist tot** (Z. 34) — nicht reaktivieren.
12. **`_section_timeline` (Z. 226) ist alte Funktion** — nicht fuer
    `dashboard_state` nutzen. `_section_timeline_entries` (Z. 295) ist
    die richtige.
13. **Kein String-Patching an System-Prompts.** Wrapper-Funktionen
    nutzen (`_architect_system_with_builder`,
    `_scout_system_with_nachfolger`).

---

## WICHTIGE PFADE

- Code: `/opt/werkstatt/werkstatt/*.py`
- Tests: `/opt/werkstatt/tests/`
- Hooks: `/opt/werkstatt/hooks/*.py`
- PhaseState: `/opt/security-ai/.werkstatt/security-ai.phase.yaml`
- Audit: `/opt/werkstatt/audit-logs/agent-pipeline-YYYY-MM-DD.jsonl`
- Zielprojekt: `/opt/security-ai/`
- Logs: `/tmp/rerun_*.log`
- Backups: `/root/backups/{security-ai,werkstatt}/`

---

## BEWAEHRTE RERUN-INVOCATION

```bash
cd /opt/werkstatt

LOG="/tmp/rerun_$(date +%Y%m%d-%H%M%S).log"

script -q -e -c "su -s /bin/bash security-ai -c 'cd /opt/werkstatt && PYTHONUNBUFFERED=1 WERKSTATT_RENDER=live WERKSTATT_ARCHITECT_MODEL=deepseek-reasoner exec timeout 2400 python3 -m werkstatt.loop --fresh --project security-ai --aufgabe \"<AUFGABE>\"'" "$LOG"
```
