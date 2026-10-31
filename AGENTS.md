# AGENTS.md — Werkstatt

Routing für Agenten. Keine Enzyklopädie.

## First Read (Loop-Lese-Reihenfolge, DOC_CONVENTIONS.md §6)

1. `docs/STATUS.md` — offene Punkte (einziger Ort fuer "was ist zu tun")
2. `docs/ROADMAP.md` — Phasen, Milestones
3. `docs/ARCHITECTURE.md` — Modul-Map
4. `docs/CONVENTIONS.md` — Coding-Regeln
5. `docs/adr/` — Entscheidungen
6. `docs/glossary.md` — Begriffe
7. `docs/index.md` — Doku-Einstieg
8. `docs/DOC_CONVENTIONS.md` — Golden-Standard (Meta)

## Loop-Start

    python3 -m werkstatt.loop --project NAME --aufgabe "TEXT"

## Rollen (5+1)

1. Explorer (werkstatt/explorer.py) — read-only, messt deterministisch.
2. Architect (deepseek-reasoner) — Prosa, numerierte Schritte.
3. Planner-Split (deepseek-chat) — zerlegt Prosa in Tasks.
4. Builder (deepseek-chat) — search/replace pro Task.
5. Reviewer (deepseek-chat) — prueft Task-Description.
6. Human-Gate — Plan-Gate + Ergebnis-Gate.

## Werkzeuge (CLI)

- python3 -m werkstatt.loop --project NAME --aufgabe "TEXT"
  vollstaendiger Loop-Lauf (Plan-Gate + Human-Gate).
- python3 -m werkstatt.scaffold NAME --dir PFAD [--dry-run] [--force]
  legt alle §2-Pflichtdateien an (idempotent).
- python3 -m werkstatt.migrate NAME --dir PFAD [--dry-run|--apply]
  prueft §2/§3/§5/§6, meldet Verstoesse, legt mit --apply fehlende
  Pflichtdateien an (loescht NICHTS).

## Doku-Vertrag (Loop)

Loop liest Living Docs in §6-Reihenfolge (entry > status > roadmap >
architecture > conventions > adr_index > glossary). Scout bekommt eine
PROJEKT-DOKU-Sektion (priorisiert, max 4000 Z. je Doc). Bei vagen
Aufgaben waehlt Scout GENAU EINEN OP-NNN aus docs/STATUS.md
(OP-NNN-Disziplin, SCOUT_SYSTEM).

## ADaPT (On-Demand-Zerlegung)

Wenn ein Task scheitert (builder_failed, post_build_verify_failed,
reviewer_high_bug_fail_closed), wird er in 2-3 Sub-Tasks zerlegt.
Max 2 Ebenen tief. Abgeschlossene Tasks bleiben. get_next_task
liefert nur pending.

## Hard Rules

- Fail closed: jeder Fehler -> ApplierError-Subklasse.
- Kein except Exception ohne # noqa: BLE001.
- ruff --fix vor _verify_patches (deterministisch).
- Circuit Breaker: Reflection stoppt, wenn Ruff-Fehler nicht sinken.
- Frozen dataclasses: kein setattr.

## Pflicht-Befehle

    pytest -q                              # 945 passed, 5 skipped (2026-10-31)
    ruff check .                           # 248 errors, 198 fixable
    mypy werkstatt/                        # 16 errors in 7 files
    python3 -m tools.quality_gate --json   # exit 1, regression true (2026-10-31)

Nicht python -m pytest (Binary python fehlt).
Nicht mypy . (zaehlt tests/, mehr Fehler).

## Baseline-Hinweis (2026-10-31)

docs/HANDOFF-BASELINE.md und tools/quality_gate.py fuehren eine Baseline
aus VOR dem Loop-Neubau (pytest 1435, ruff 13, mypy 11, AST 6, Katalog 162).
Diese Baseline ist VERALTET:

- pytest 1435 -> 945 (Loop-Neubau: pipeline.py + test_pipeline.py entfernt)
- ruff 13 -> 248 (tests/ wurde nie durchgerufft; keine ruff-Config)
- mypy 11 -> 16 (werkstatt/, nicht auf .)
- AST 6 -> 0, Katalog 162 -> fehlt (_KATALOG_SOLL entfernt)

Konsequenz: quality_gate ist rot (exit 1). Re-Baseline als eigener OP
(siehe docs/STATUS.md). Bis dahin: Zahlen oben sind die Wahrheit.

## Doku

- docs/index.md — Doku-Einstieg
- docs/STATUS.md — offene Punkte (OP-NNN, §5-Format)
- PROGRESS.md — Historie (append-only)
- docs/adr/ — Architecture Decision Records
- docs/DOC_CONVENTIONS.md — Golden-Standard (Meta)
