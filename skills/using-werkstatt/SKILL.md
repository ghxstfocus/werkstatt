---
name: using-werkstatt
description: |
  META-SKILL. Immer geladen. Wenn ein Skill zu deiner
  Aufgabe passt, MUSST du ihn nutzen. Wenn die Aufgabe
  eine Messung verlangt (ruff, pytest, Bug), MUSST du
  messen. Rate NICHT.
allowed-tools: run_readonly
---

# Using-Werkstatt (Meta-Skill)

## Die eiserne Regel
Wenn ein Skill zu deiner Aufgabe passt, hast du KEINE Wahl.
Du MUSST ihn laden und befolgen.

## Messen statt Raten
- **ruff-Fehler?** -> `run_readonly("ruff check . --output-format=concise")`
- **Test-Fehler?** -> `run_readonly("pytest -q")`
- **Unklare Ursache?** -> erst messen, dann handeln.

## Rollen
- **Explorer:** MESSEN. Liefert die echten Dateien aus der Messung.
- **Planner:** MESSEN. Liest `explorer_context`. Erfindet KEINE Dateien.
- **Builder:** Bauen + Messen (`py_compile`, `ruff check <datei>`).
- **Reviewer:** Diff lesen + `pytest -q`.

## Verbot
- Keine Datei erfinden, die nicht gemessen wurde.
- Kein Fix ohne Reproduce.
