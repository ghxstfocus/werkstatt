# Bau-Handoff — Werkstatt

Stand: 2026-10-25. Werkstatt-HEAD: `efe4ffc` (M-472).
Zielprojekt: f436e42 + ChangeApplier-Code (RERUN-80, uncommitted).
Baseline: 1448 / 13 / 11 / 6 / 162.

## Loop-Status: FERTIG

Der Loop läuft Ende-zu-Ende mit ADaPT (On-Demand-Zerlegung).
RERUN-80: ChangeApplier.apply/rollback implementiert
(237 Zeilen), 6/6 Tasks approved, LOOP_RC=0.

## Architektur (5+1 Rollen + ADaPT)

1. **Explorer** (`werkstatt/explorer.py`) — read-only, messt
   deterministisch (ruff, pytest). Liefert `key_files`.
2. **Architect** (deepseek-reasoner) — Prosa mit numerierten
   Schritten. Keine Skills, keine Tools (M-446).
3. **Planner-Split** (deepseek-chat) — zerlegt Prosa in Tasks
   (architect_start/ende, M-461). Rekursiv (M-469).
4. **Builder** (deepseek-chat) — search/replace pro Task.
   Bekommt wörtlichen Architect-Abschnitt (M-461).
5. **Reviewer** (deepseek-chat) — prüft Task-Description,
   nicht Gesamtaufgabe (M-459).
6. **Human-Gate** — Plan-Gate + Ergebnis-Gate.
7. **ADaPT** — On-Demand-Zerlegung bei Fehlern (M-472..M-475).

## Verifikation

- `ruff --fix` vor `_verify_patches` (M-467).
- Circuit Breaker: Reflection stoppt, wenn Ruff-Fehler nicht
  sinken (`loop_reflection_stagnation`).
- Kein `except Exception` ohne `# noqa: BLE001`.
- Fail closed: jeder Fehler → `ApplierError`-Subklasse.

## Nächste Schritte

1. **ChangeApplier committen** (RERUN-80, Zielprojekt).
2. **Vollsuite** (11 Min, manuell): `.venv/bin/python3 -m pytest -q`.
3. **Doku-Diátaxis** (Phase 21, in Arbeit):
   - `docs/README.md`, `AGENTS.md`, `README.md`,
     `docs/ARCHITEKTUR.md`, `docs/ROADMAP.md`,
     `docs/ERLEDIGT.md`, `docs/OFFENE-BLOECKE.md`.
4. **M-345:** `pipeline.py` löschen (11.639 Zeilen).

## Verweise

- `docs/README.md` — Diátaxis-Map
- `docs/ARCHITEKTUR.md` — System-Map
- `docs/ROADMAP.md` — Phasen
- `docs/ERLEDIGT.md` — M-441..M-476
- `docs/OFFENE-BLOECKE.md` — offene Blöcke
- `AGENTS.md` — Agenten-Routing
