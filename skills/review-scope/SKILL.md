---
name: review-scope
description: |
  Scope-Check: Over-Delivery als HIGH-Bug erkennen (Aenderungen ausserhalb Task-Scope).
globs:
  - "**/*.py"
rollen:
  - reviewer
---

# review-scope

## SCOPE-CHECK (Over-Delivery)

Zusaetzlich zur fachlichen Pruefung: pruefe, ob der Diff im Scope der
Task-Beschreibung bleibt. Over-Delivery ist ein HIGH-Bug.

Beispiele:
- Task: "Einen Docstring-Absatz hinzufuegen". Diff: 20 Zeilen Code +
  1 neuer Test + __all__-Aenderung. -> HIGH-Bug.
- Task: "Eine Zeile in __all__ ergaenzen". Diff: 10 Zeilen __all__
  umgeschrieben mit anderen Anfuehrungszeichen + 2 unbezogene Eintraege
  hinzugefuegt. -> HIGH-Bug.
- Task: "Neue Funktion X". Diff: X + 3 unbezogene Refactors in
  anderen Funktionen. -> HIGH-Bug.

Regel:
- Jede Zeile im Diff muss durch die Task-Beschreibung gedeckt sein.
- Refactors, Formatierungs-Aenderungen, Whitespace-Korrekturen ausserhalb
  des Ziel-Bereichs sind nicht im Scope, auch wenn sie "besser" aussehen.
- Kosmetische Aenderungen (Anfuehrungszeichen, removesuffix, etc.) ohne
  Auftrag: HIGH-Bug.
- Loeschen von Inhalt ausserhalb des Scopes: HIGH-Bug.

Wenn du eine Over-Delivery findest, benenne sie explizit mit der
betroffenen Zeile und dem Grund. Kein "sieht ok aus" bei unklarem Scope.
