---
name: ruff-regeln
description: |
  Ruff-Grundregeln (Sortierung, noqa-Verbot, Exception-Handling).
globs:
  - "**/*.py"
rollen:
  - builder
---

# ruff-regeln

Der Verify-Schritt faehrt `ruff check` auf den geaenderten Dateien.
Wenn du eine dieser Regeln verletzt, wird der Patch verworfen.

- **PLR0124 (self-comparison):** Kein `value != value` oder `x == x`.
  NaN-Check via `math.isnan(value)` (Import `math` ergaenzen) oder
  `value != value  # noqa: PLR0124` direkt an der Zeile.
  Kein `# noqa: PLR0124` an einer anderen Zeile als der Verletzung.
- **F821 (undefined name):** `Mapping` erfordert
  `from collections.abc import Mapping`. Pruefe VOR dem Patch, ob
  das Symbol importiert ist; wenn nicht, Import im selben Patch
  ergaenzen.
- **F401 (unused import):** Keinen Import hinzufuegen, der nicht
  benutzt wird. Wenn du einen Import entfernst, pruefe mit Grep,
  ob er noch gebraucht wird.
- **E501 (line too long):** Zeilen <= 100 Zeichen. Lange Ausdruecke
  auf mehrere Zeilen umbrechen.
- **S110 (try/except/pass):** Kein `except: pass` ohne Logging.
  Wenn noetig: `except Exception as _e:  # noqa: BLE001` + `audit(...)`
  oder `logger.warning(...)`.
- **Allgemein:** Wenn ein Ruff-Fix (`ruff check --fix`) etwas
  entfernt, was inhaltlich gebraucht wird (z.B. `noqa` an einer
  berechtigten Stelle), pruefe danach erneut mit `ruff check`.
  Kein Fix ohne Nachkontrolle.
