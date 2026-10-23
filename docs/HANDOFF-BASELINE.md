# Werkstatt-Baseline — verbindliche Definition

Stand: 2026-10-22, HEAD 76f4bf1, Branch umbau/phase-2.

## Messbefehle (kanonisch)

| Metrik  | Befehl                          | Soll         |
|---------|---------------------------------|--------------|
| pytest  | `pytest -q`                     | 1282 passed  |
| ruff    | `ruff check .`                  | 14 errors    |
| mypy    | `mypy pipeline.py werkstatt/`   | 8 errors     |
| AST     | AST-Test (siehe tests/)         | 6 passed     |
| Katalog | `_KATALOG_SOLL`                 | 162          |

## Fallstricke

- `python` ist auf dem System NICHT installiert (nur `python3` und
  `/usr/bin/pytest`). `python -m pytest` funktioniert nicht.
  Kanonisch ist `pytest -q`.
- `mypy .` zaehlt `tests/` mit und liefert 40 Fehler. Die Baseline
  von 9 gilt NUR fuer `mypy pipeline.py werkstatt/`. Jede Messung,
  die nicht explizit diesen Befehl nutzt, ist NICHT die Baseline.
- AST- und Katalog-Zahlen (6 / 167) werden ueber den jeweiligen
  Testlauf gemessen; beide sind in der pytest-Suite enthalten.
  Die separate Ausweisung dient der schnellen Sichtpruefung.

## Rollback-Anker

Vor jedem Code-Touch in 3a-1c-4 und Nachfolgern:
- HEAD = 5e50ea6 (oder Nachfolger-Commit)
- Delta Baseline != 0 -> Rollback auf diesen HEAD, NICHT Tests anpassen.

## Historie

- 2026-10-20: Baseline 1245/17/7/6/167 (mypy 7, weil vor W2-Fix).
- 2026-10-21: Baseline 1245/17/9/6/167 (mypy 9, nach 3a-1c-2b-W2).

## Klarstellung AST+Katalog

- "AST+Katalog 14" ist eine Summen-Konvention (6 AST + 8 andere
  Test-Kategorien), KEIN Messwert. Baseline: AST-Test
  `pytest tests/test_audit_kinds.py -q` = 6 passed, Katalog
  `_KATALOG_SOLL` = 167. Reviewer-Bestaetigung #138 (2026-10-21).
