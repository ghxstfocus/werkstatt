---
name: review-semantik
description: |
  Semantik-Check: Interface-Signaturen unveraendert? HIGH-Bug wenn gebrochen.
globs:
  - "**/*.py"
rollen:
  - reviewer
---

# review-semantik

## SEMANTIK-CHECK (HIGH-Bug)

- Wenn die Task eine Funktion X nennt, der Diff aber eine andere
  Funktion Y nutzt (z.B. `_section_timeline` statt
  `_section_timeline_entries`): HIGH-Bug, reject.
- Wenn ein bestehender Aufruf einer Funktion entfernt wird, ohne
  dass die Task das verlangt: HIGH-Bug.
- Wenn eine API erfunden wird (nicht im Import-/Code-Index):
  HIGH-Bug.
