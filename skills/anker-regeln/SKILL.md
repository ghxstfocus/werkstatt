---
name: anker-regeln
description: |
  Regeln fuer Anker und Ersatz in typ:patch.
  count(anker) == 1, ersatz != anker, Einrueckung
  beachten. Nutze diese Skill immer, wenn du
  typ:patch lieferst. Sie ist statisch im
  Builder-Prompt.
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
