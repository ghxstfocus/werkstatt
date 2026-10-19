# Umbau-Fahrplan — Ergaenzung: Subagenten und Skills

Stand: 2026-10-19
Herkunft: Ergaenzung von der abendlichen Reflexion
(Claude, 2026-10-19) zum Umbau-Fahrplan.
Bezug: docs/UMBAU-FAHRPLAN.md, Phase 3 + Phase 5.
Bau-Chat-Nachtrag 2026-10-19: Datei-Struktur korrigiert
nach Code-Inspektion (Befund K, M).

## Warum diese Ergaenzung

Der Umbau-Fahrplan (Phase 3) beschreibt den Kern-Loop
(Planner -> Generator -> Evaluator), aber er nennt die
Subagenten nicht. Das ist eine Luecke: Die Profis bauen
den Kern-Loop mit Werkzeug-Subagenten drumherum, nicht
nur mit drei Rollen.

## Der Unterschied: Rollen vs. Subagenten vs. Skills

- **Rollen** sind Stationen im Loop. Eigener Contract,
  eigener State. Es gibt genau drei: Planner, Generator,
  Evaluator. Geladen via load_agents aus agents/*.md.
- **Subagenten** sind Werkzeuge. Der Rollen-Agent ruft
  sie bei Bedarf. Isolierter Kontext, enger Auftrag,
  knapper Report, dann verfaellt der Kontext.
- **Skills** sind Wissensbausteine. Geladen via
  load_skills aus skills/*/SKILL.md. Sie sind keine
  Agenten, sondern Regeln/Anleitungen, die in Prompts
  eingebettet werden koennen.

## Befund K (Bau-Chat) — Ist-Stand der Subagenten

Die Ergaenzung nannte "agents/explore.md (gebaut)".
Das ist falsch. Real:

- Drei Subagenten-Prompts sind INLINE in pipeline.py:
  - EXPLORE_SUBAGENT_PROMPT, gerufen von
    rufe_explore_subagent (Z. 5302-5313), aktiv.
  - BASH_SUBAGENT_PROMPT, gerufen von
    rufe_bash_subagent (Z. 5316-5326), inaktiv.
  - BROWSER_SUBAGENT_PROMPT, gerufen von
    rufe_browser_subagent (Z. 5329-5339), inaktiv.
- Kein agents/subagents/, keine explore.md.

## Befund M (Bau-Chat) — Skills als vierte Kategorie

skills/*/SKILL.md existiert (10 Dateien, u.a.
patch-format, anker-regeln, systematic-debugging,
security-review). Geladen via load_skills (Z. 6520).
Im Fahrplan und in der urspruenglichen Ergaenzung
nicht erwaehnt.

## Die korrigierte Datei-Struktur (Soll, Phase 3)

Kategorien trennen:

  agents/             Rollen (3)
    planner.md
    generator.md      (heute: builder.md)
    evaluator.md      (heute: judge.md)
    evaluator_commit.md

  subagents/          Werkzeuge (Phase 3 extrahieren)
    explore.md        (heute: EXPLORE_SUBAGENT_PROMPT
                       inline in pipeline.py)
    bash.md           (heute: BASH_SUBAGENT_PROMPT inline,
                       inaktiv)
    browser.md        (heute: BROWSER_SUBAGENT_PROMPT
                       inline, inaktiv)
    debugger.md       (neu)
    test_runner.md    (neu, ueberschneidung mit
                       test_generator.md pruefen)
    security_auditor.md (optional, Phase 5)

  skills/             Wissensbausteine (10, bleiben)
    simplify/SKILL.md
    web-security/SKILL.md
    ... (8 weitere)

## Was die Profis real haben (Beleg)

Cursor: Debugger, Test-Runner, Orchestrator-Pattern
(Planner -> Implementer -> Verifier).
Claude Code: Explore (built-in), Custom Subagents.
Security-Auditor-Muster: Read-only (Read + Grep).
12-Factor-Agents Factor 10: Small focused agents, 3-10 Steps.

## Konsequenz fuer Phase 3

Phase 3 (Loop neu) wird ergaenzt:

1. Kern-Loop bauen (Planner, Generator, Evaluator).
2. Subagenten aus pipeline.py extrahieren:
   - EXPLORE_SUBAGENT_PROMPT -> subagents/explore.md
   - BASH_SUBAGENT_PROMPT -> subagents/bash.md
   - BROWSER_SUBAGENT_PROMPT -> subagents/browser.md
3. Neue Subagenten:
   - debugger.md (Phase 3, bei rotem Test)
   - test_runner.md (Phase 3, nach Patch)
   - security_auditor.md (Phase 5, optional)
4. Skills bleiben in skills/*/SKILL.md, aber:
   Welche Skills werden in welche Prompts injiziert?
   Das ist Phase-6-Arbeit (Prompt-Kuerzung).

## Was das fuer den Bau-Chat bedeutet

- Rollen-Loeschung (Charge 2a) betrifft nur agents/*.md.
  Pflicht-Rollen (reviewer, builder, test_generator)
  sind durch load_agents (pipeline.py:3888) hart
  kodiert. Loeschen ohne Aenderung an load_agents
  fuehrt zu sys.exit(1). Befund J.
- Subagenten-Extraktion ist Phase 3, nicht Phase 1.
- Skills sind Phase 6 (Prompt-Kuerzung).

## Bezug

- docs/UMBAU-FAHRPLAN.md (Hauptplan, 7 Phasen).
- docs/UEBERGABE-BAU-CHAT-2026-10-19.md (Stand).
- Befund J (load_agents-Pflicht), K (Subagenten inline),
  M (skills/ als vierte Kategorie) im Bau-Chat 2026-10-19.
