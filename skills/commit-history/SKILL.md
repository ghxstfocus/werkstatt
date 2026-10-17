---
name: commit-history
description: |
  Letzte Commits des Ziel-Projekts, gefiltert nach
  Zieldateien. Strukturiert nach Warum/Was/Dateien.
  Use when planning or reviewing to understand
  project history.
---

# Commit-History

## Format
Strukturiert (nicht rohe git log):

## <commit-hash>: <message-titel>
- Datum: ...
- Dateien: ...
- Warum: ...
- Was: ...

## Filtern
Nur Commits, die die Zieldateien beruehren.
Nicht alle Commits des Projekts.

## Wann laden
- Planner: vor Plan-Formulierung.
- Judge: vor Review, um Regressionen zu erkennen.
