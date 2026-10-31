# AGENTS.md — Werkstatt

Routing für Agenten. Keine Enzyklopädie.

## First Read

1. `docs/index.md` — Doku-Map (Diátaxis)
2. `docs/ARCHITECTURE.md` — System-Map
3. `docs/NEUBAU-ZIELBILD.md` — Aktueller Loop

## Loop-Start

```bash
python3 -m werkstatt.loop --project <name> --aufgabe "<text>"
```

## Rollen (5+1)

1. **Explorer** (`werkstatt/explorer.py`) — read-only, messt deterministisch.
2. **Architect** (deepseek-reasoner) — Prosa, numerierte Schritte.
3. **Planner-Split** (deepseek-chat) — zerlegt Prosa in Tasks.
4. **Builder** (deepseek-chat) — search/replace pro Task.
5. **Reviewer** (deepseek-chat) — prueft Task-Description.
6. **Human-Gate** — Plan-Gate + Ergebnis-Gate.

## ADaPT (On-Demand-Zerlegung)

Wenn ein Task scheitert (builder_failed, post_build_verify_failed,
reviewer_high_bug_fail_closed), wird er in 2–3 Sub-Tasks zerlegt.
Max 2 Ebenen tief. Abgeschlossene Tasks bleiben. get_next_task
liefert nur pending.

## Hard Rules

- Fail closed: jeder Fehler -> ApplierError-Subklasse.
- Kein except Exception ohne # noqa: BLE001.
- ruff --fix vor _verify_patches (deterministisch).
- Circuit Breaker: Reflection stoppt, wenn Ruff-Fehler nicht sinken.
- Frozen dataclasses: kein setattr.

## Pflicht-Befehle

```bash
pytest -q                              # (Zahl siehe pytest-Ausgabe)
ruff check .                           # 13 errors
mypy pipeline.py werkstatt/            # 11 errors
pytest tests/test_audit_kinds.py -q    # 6 passed
python3 -m tools.quality_gate --json   # Exit 0 = ok
```

**Nicht** python -m pytest (Binary python fehlt).
**Nicht** mypy . (zaehlt tests/, 40 Fehler).

## Doku

- docs/index.md — Diátaxis-Map
- docs/playbooks/ — How-to
- docs/references/ — Reference
- PROGRESS.md — Erledigte Bloecke
- docs/STATUS.md — Offene Bloecke
