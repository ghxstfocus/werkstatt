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

## 4.7 On-Demand-Messung (fehlt)

Claude Code, Copilot, Cursor und AutoGen arbeiten alle mit
On-Demand-Messung: der Agent entscheidet selbst, welche
Datei er liest, basierend auf der aktuellen Aufgabe. Kein
Pre-Loading des ganzen Repos.

Was die grossen machen:

- **Claude Code:** Glob/Grep zuerst, dann Read nur der
  relevanten Dateien, dann Edit. Read vor Edit ist
  Pflicht (error code 6: "File hasn't been read — must
  read first"). Nach Edit wird die mtime im Read-Cache
  aktualisiert, damit der naechste Edit auf derselben
  Datei durchgeht.
- **Copilot:** Tool Search (Tools nur laden, wenn
  gebraucht), Prompt Caching fuer stabile Prefixe.
  Plan Mode: erst Kontext sammeln, dann Plan, dann
  Mensch-Gate, dann Implementierung.
- **Cursor:** Semantische Suche + Grep, Agent entscheidet
  welche Dateien er liest. Nach jeder Aktion: Ergebnis
  pruefen, dann naechster Schritt.
- **AutoGen:** RetrieveUserProxyAgent, Retrieval-
  Augmented Generation nur bei Bedarf.

Werkstatt heute:

- `mess_protokoll` als String, waechst bei jedem
  `read_file`.
- `_planner_user_content` baut GEMESSENER INHALT-Block
  (100K Prompt-String bei 10 Dateien).
- `_builder_lauf` bekommt den ganzen Mess-Kontext, nicht
  "hier ist der Index, lies was du brauchst".
- `apply_code_patches` hat **keinen Read-Cache**. Builder
  kann patchen, ohne zu messen. Folge: Deadlock in
  Phase 20b.
- `_builder_lauf` hat **keinen Loop-Schutz**. Builder
  wiederholt dieselben Anker 3 Runden.

Soll (W52b + W59):

- `mess_protokoll` als Verzeichnis
  (`.werkstatt/<phase>/messungen/<sha1>.txt`).
- `index.json` mit Pfad, SHA, mtime, Groesse, Quelle.
- Prompt: "Messungen liegen unter X. Index: Y." Statt
  des vollen Inhalts.
- Agent liest bei Bedarf per `read_file`, statt alles
  im Prompt zu haben.
- `apply_code_patches` prueft `gelesene_dateien` +
  mtime (`RunState.gelesene_dateien: dict[str, float]`).
- Loop-Schutz: 2 Runden ohne neuen Read -> Fail-closed,
  Audit `builder_wiederholt_ohne_messung`.

Blöcke:

- **W52b** (Kategorie 3): Messungen/Replies als Dateien.
  On-Demand-Messung strukturell.
- **W59** (Kategorie 3): Read-Cache + mtime-Check +
  Loop-Schutz. Mechanisch.

Beide sind P1 (akut) bzw. P3 (Refactor). W59 zuerst,
weil es Phase 20b direkt blockiert.

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
