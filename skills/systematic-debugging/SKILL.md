---
name: systematic-debugging
description: |
  Reproduce-first bug fixing. Erst reproduzieren, dann
  fixen. Nutze diese Skill, wenn ein Test rot ist und
  die Ursache unklar. Sie ist statisch im Solver-Prompt.
---

# Systematic-Debugging

## Ablauf
1. Reproduce: Test rot? Welcher? Welche Zeile?
2. Isolate: Welche Funktion? Welcher Input?
3. Hypothesis: Was koennte die Ursache sein?
4. Test: Hypothese pruefen (read_file, grep).
5. Fix: Minimaler Fix, der die Hypothese adressiert.
6. Verify: Test erneut laufen lassen.

## Regeln
- Nie raten. Immer messen.
- Nie mehrere Fixes gleichzeitig.
- Bei Unklarheit: mehr messen, nicht mehr raten.
