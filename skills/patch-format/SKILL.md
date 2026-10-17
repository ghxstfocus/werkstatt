---
name: patch-format
description: |
  Format fuer Code-Patches. PATCH-BEGINN/PATCH-ENDE,
  typ:patch (bestehende Datei), typ:new_file (neue Datei).
  Nutze diese Skill immer, wenn du Code-Patches lieferst.
  Sie ist statisch im Builder-Prompt.
---

# Patch-Format

## Zwei Typen

typ:patch (Default, fuer bestehende Datei):
  PATCH-BEGINN
  pfad: <pfad relativ zum Projekt>
  anker: |
    <der ALTE Text, count(anker) == 1>
  ersatz: |
    <der NEUE Text, ersatz != anker>
  PATCH-ENDE

typ:new_file (fuer neue Datei):
  PATCH-BEGINN
  typ: new_file
  pfad: <pfad relativ zum Projekt>
  inhalt: |
    <voller Datei-Inhalt>
  PATCH-ENDE

## Regeln
- Ein Reply enthaelt AUSSCHLIESSLICH Patch-Bloecke.
- Kein Fliesstext, kein Markdown, kein CODE-ENTWURF-Block.
- Bei Unsicherheit: COMMAND: RUN read_file <pfad>.
