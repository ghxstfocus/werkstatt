---
name: review-symbol
description: |
  Symbol-Check: im Diff referenzierte Symbole muessen im Projekt existieren.
globs:
  - "**/*.py"
rollen:
  - reviewer
---

# review-symbol

## SYMBOL-CHECK (HIGH-Bug, verhindert Fehltreffer)

- Bevor du einen Bug meldest ("Symbol X nicht definiert"): pruefe
  im Block `AKTUELLER DATEI-INHALT`, ob X dort definiert ist.
- Wenn X im Datei-Inhalt steht (als Zuweisung, def, class, import):
  KEIN Bug.
- Wenn X nirgends definiert ist: HIGH-Bug.
- Belege im `description`-Feld, ob du X im Datei-Inhalt gesucht
  hast: "X nicht im Datei-Inhalt (Zeilen 1-N)".
- Beispiel: `_SCORE_SENTINEL` ist im Datei-Inhalt bei Zeile 65
  als `_SCORE_SENTINEL = float("-inf")` definiert -> kein Bug.
