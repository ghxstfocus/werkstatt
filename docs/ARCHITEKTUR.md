# Architektur — Werkstatt

Stand: 2026-10-18
Ziel: Das Beste aus Claude Code, Copilot, AutoGen,
Swarm und OpenAI Agents SDK nehmen und ein eigenes
Agentensystem bauen.

## 1. Ziel-Architektur

Die Werkstatt ist ein Multi-Agent-System mit
sechs Rollen. Jede Rolle hat einen eigenen
Prompt, ein eigenes Modell, eine eigene Aufgabe.
Der Mensch ist das letzte Gate.

    +--------------------------------------------------+
    |                     MENSCH                        |
    |            (Reviewer-Chat, Human-Gate)            |
    +--------------------------------------------------+
                          |  ^
                          v  |
    +--------------------------------------------------+
    |                     WERKSTATT                     |
    |                                                   |
    |   Planner ---- Auftrag ----> Builder             |
    |      |                          |                 |
    |      |                          v                 |
    |      |                     Code-Patches           |
    |      |                          |                 |
    |      |                          v                 |
    |      |                     Solver (Diagnose)      |
    |      |                          |                 |
    |      |                          v                 |
    |      |                     Judge (Contract)       |
    |      |                          |                 |
    |      |                          v                 |
    |      |                     Reviewer (Commit)      |
    |      |                          |                 |
    |      v                          v                 |
    |   Phasenplan              Commit-Paket            |
    +--------------------------------------------------+
                          |
                          v
                   Ziel-Projekt (security-ai)

## 2. Die Rollen

| Rolle | Modell | Aufgabe | Groesse |
|---|---|---|---|
| planner | deepseek-chat | Auftrag (Stufe 1) oder Phasenplan (Stufe 2) | 297 Z. |
| builder | deepseek-chat | Code-Patches, Commit-Paket | 647 Z. |
| solver | deepseek-chat | Diagnose bei Deadlock | 182 Z. |
| judge | deepseek-reasoner | Contract-Treue, Sicherheit | 90 Z. |
| reviewer | deepseek-reasoner | Commit-Paket | 56 Z. |
| test_generator | deepseek-chat | Test-Vorschlaege | 18 Z. |
| coverage/chaos | no-LLM | Messungen | 10 Z. |

## 3. Was die Werkstatt gut macht

- Multi-Agent mit klaren Rollen: Planner, Builder,
  Judge, Reviewer sind getrennt. Jeder hat einen
  eigenen Prompt, ein eigenes Modell.
- Human-Gate: Der Mensch entscheidet bei NO-GO
  und am Phasenende.
- Audit-Log: Jede Entscheidung ist im JSONL.
- Rollback: apply_code_patches hat In-Memory-
  Rollback. phase_rollback bei Deadlock.
- Basis-Gate: py_compile, ruff, mypy, pytest,
  git_status, git_head vor jedem Bau.

## 4. Was die Werkstatt NICHT hat (Luecken)

### 4.1 Read-vor-Edit (Claude Code)

Claude Code erzwingt: "File hasn't been read —
must read first" (error code 6). Die Werkstatt
hat das NICHT. Der Builder kann patchen, ohne
zu messen. Folge: Phase-20b-Laeufe, Builder
wiederholt Anker 3x, Solver-Deadlock, Reviewer
antwortet leer.

W59 (Deadlock-Mechanismus): Patch nur nach
Messung (RunState.gelesene_dateien, mtime-Check).

### 4.2 mtime-Check (Claude Code)

Claude Code prueft: "File has been modified
since read". Die Werkstatt hat das NICHT.

W59: mtime-Check in apply_code_patches.

### 4.3 Verify-vor-PR (Copilot)

Copilot Coding Agent verifiziert vor PR: Tests,
Linter, Self-Review. Die Werkstatt hat das
teilweise: Basis-Gate prueft Tests, aber der
Builder sieht das Ergebnis NICHT und korrigiert
nicht.

W59: Builder-Loop mit Fail-closed bei
Wiederholung ohne Messung.

### 4.4 Handoff-Mechanik (AutoGen)

AutoGen hat "Handoff": Agent A gibt an Agent B
ab, wenn er nicht weiterkommt. Die Werkstatt hat
das teilweise: Solver-Trigger bei Deadlock. Aber
der Solver antwortet oft mit falscher Diagnose
(Phase-20b: "Auftrag erfuellt", obwohl .log()
fehlt).

W55 (Solver-Fehldiagnose): Solver-Prompt muss
die tatsaechliche Aufgabe pruefen, nicht den
Ist-Zustand.

### 4.5 Dynamic Routing (Swarm)

Swarm routet dynamisch zwischen Agenten. Die
Werkstatt hat statische Rollen. Kein dynamisches
Routing.

W58 (Deadlock-Mechanismus): Wenn zwei Runden
hintereinander derselbe Fehler auftritt,
fail-closed statt Loop.

### 4.6 Prompt-Groessen-Limit (Anthropic)

Die Rollen-Prompts sind zu gross:
- builder.md: 647 Zeilen (Audit-Ziel < 300).
- planner.md: 297 Zeilen (Audit-Ziel < 150).

W61 (Rollen-Sanierung): Redundanz aufloesen
(builder 43%, planner 20%), Roll-Body < 300.

## 5. Was funktioniert (verifiziert)

- W31-W47: Modularisierung (state.py, parser.py).
- W28b: Judge als eigene Rolle.
- W40: Reviewer-Sanierung (410 -> 56).
- W48-A16: Katalog-Bug gefixt (105 -> 109).
- W50: Planner-Durchfall verhindert.
- W51a-h: Planner-Mess-Mechanik (8 Bloecke,
  Symptom-Behandlung).
- W54-a, W54-g, W54-h: Builder-Fixes
  (Symptom-Behandlung).

## 6. Was nicht funktioniert (Deadlock in Phase 20b)

Der Phase-20b-Lauf ist 3x gescheitert:
- Builder sendet 2 Anker, deren Ersatz nicht im
  GEMESSENER INHALT steht.
- 3 Runden Wiederholung.
- Solver diagnostiziert "Auftrag erfuellt".
- Reviewer antwortet leer.

Die Wurzel: Read-vor-Edit fehlt (W59). Und der
Builder-Prompt ist zu gross (647 Zeilen), das LLM
liest die Anker-Regeln nicht mehr (W61).

## 7. Reihenfolge der Fixes

1. W59 (Deadlock-Mechanismus) — mechanisch,
   wirksam, mittel.
2. W61 (Rollen-Sanierung) — strukturell, aus
   dem Audit, gross.
3. W55 (Solver-Fehldiagnose) — Solver-Prompt,
   klein.
4. W58 (Reviewer-Leer-Antwort) — Reviewer-Loop,
   klein.
5. W36-2b..6 (Modularisierung) — pipeline.py,
   gross.
