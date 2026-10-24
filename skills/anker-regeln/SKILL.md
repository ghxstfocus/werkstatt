---
name: anker-regeln
description: 'Regeln fuer Anker und Ersatz in typ:patch.

  count(anker) == 1, ersatz != anker, Einrueckung

  beachten. Nutze diese Skill immer, wenn du

  typ:patch lieferst. Sie ist statisch im

  Builder-Prompt.

  '
allowed-tools: run_write
---

# Anker-Regeln

## Grundregeln
1. count(anker) == 1: Anker muss genau einmal im Zieldatei-Ausschnitt vorkommen.
2. ersatz != anker: Wenn identisch, ist der Patch wirkungslos.
3. Einrueckung: Anker muss die exakte Einrueckung aus dem GEMESSENER INHALT haben.
4. Anker nicht gefunden? -> COMMAND: RUN read_file <pfad>.

## Einrueckungs-Korrektur
Wenn der Anker um 2 Spaces verschoben ist, korrigiert die Werkstatt automatisch.

## Wirkungsloser Patch
Wenn ersatz == anker: Kein Patch. Liefere keinen.

## Tools (nach Patch — der LOOP macht das)
- Der Loop prueft `py_compile` nach dem Patch (Builder muss nichts tun).
- Der Loop prueft `ruff check` nach dem Patch (via verify.json ruff_changed).
