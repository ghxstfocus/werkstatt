---
name: funktion-wahl
description: |
  Bestehende Funktion pruefen bevor neue erfunden. Best Match waehlen.
globs:
  - "**/*.py"
rollen:
  - builder
---

# funktion-wahl

- Wenn die Task eine Funktion/Klasse X namentlich nennt: waehle X.
  Nicht die "aehnlichste", nicht die kuerzere.
- Bei Namens-Aehnlichkeit (z.B. `_section_timeline` vs.
  `_section_timeline_entries`): pruefe, welche die Task nennt,
  und nutze genau diese.
- Wenn du unsicher bist: Task failen lassen, nicht raten.
