---
name: plan-crafting
description: 'Struktur fuer Phasenplaene. Executable multi-step plans,

  jede Step enthaelt echten Code, keine Platzhalter.

  Nutze diese Skill immer, wenn du als Planner planst.

  Sie ist statisch im Planner-Prompt.

  '
allowed-tools: run_readonly
---

# Plan-Crafting

## Format
PHASE <id>: <Titel>

U1: <Titel>
  Kontext: ...
  Fail-closed: ...
  Grenzen: ...
  Akzeptanz:
    - <test>
    - <verhalten>
  Abhaengigkeiten: ...
  Unterpunkte:
    - datei:<pfad>, aktion:neu|patch, signatur/anker:..., test:<pfad>

## Regeln
1. 3-7 Unterbloecke pro Phase.
2. Max 7 Unterpunkte pro Unterblock.
3. Jeder Unterpunkt: datei, aktion, signatur/anker, test.
4. Vor dem Plan: MESSEN (P19).
5. Builder-freundlich (P17).

## Tools
- `run_readonly("ruff check .")` — Fehler VOR dem Plan messen.
- `run_readonly("pytest -q")` — Test-Stand VOR dem Plan messen.
