# Werkstatt

Das Agenten-System. Unabhängig von jedem Projekt.
Es baut Projekte, aber es gehört keinem Projekt.

**Ziel:** Das Beste aus Claude Code, Copilot, Aider, Cursor,
Grok und Codex nehmen und ein eigenes Agentensystem bauen.

**Kernprinzip:** On-Demand-Messung + deterministische Gates.
Der Loop prüft, bevor er baut. Kein LLM-Token ohne Plan.

**Stand 2026-10-25 (nach M-472, ADaPT):**

- **Baseline:** 1448 Tests, ruff 13, mypy 11, AST 6, Katalog 162.
- **HEAD:** efe4ffc. Branch: umbau/phase-2 (origin gepusht).
- **Loop:** Ende-zu-Ende gruen (RERUN-80, Loop-RC=0).

## Loop-Architektur (5+1 Rollen + ADaPT)

Der Orchestrator ist `werkstatt/loop.py` (run_pipeline_loop).
Er ruft pro Task:

1. **Explorer** (`werkstatt/explorer.py`) — read-only, messt
   deterministisch (`ruff check .`, `pytest -q`). Liefert
   `key_files` aus der Messung, nicht aus dem LLM.
2. **Architect** (deepseek-reasoner) — Prosa mit numerierten
   Schritten. Keine Skills, keine Tools (M-446).
3. **Planner-Split** (deepseek-chat) — zerlegt die Prosa in
   Tasks mit `architect_start`/`architect_ende` (wörtliche
   Marker). Rekursiv, max 2 Ebenen (M-469/M-470/M-471).
4. **Builder** (deepseek-chat) — search/replace pro Task.
   Bekommt den wörtlichen Architect-Abschnitt (M-461).
5. **PreToolUse-Hook** (`hooks/pre_tool_use.py`) — AST-basierte
   Import-Validierung (M-334a).
6. **Verify** (`_verify_patches`) — verify.json-Stages:
   py_compile_changed, ruff_changed, pytest_changed,
   py_compile_core, pytest_full_checks (phase_end).
7. **Reviewer** (`werkstatt/reviewer.py`) — prüft die
   Task-Description, nicht die Gesamtaufgabe (M-459).
8. **Human-Gate** (`_human_gate`) — Plan-Gate + Ergebnis-Gate,
   fail-closed.

## ADaPT (On-Demand-Zerlegung)

Wenn ein Task scheitert (`builder_failed`,
`post_build_verify_failed`, `reviewer_high_bug_fail_closed`),
wird er in 2–3 Sub-Tasks zerlegt (M-472/M-473/M-474/M-475).
Max 2 Ebenen tief. Abgeschlossene Tasks bleiben. `get_next_task`
liefert nur `pending`.

## Verifikation

- `ruff --fix` vor `_verify_patches` (deterministisch, M-467).
- Circuit Breaker: Reflection stoppt, wenn Ruff-Fehler nicht
  sinken (`loop_reflection_stagnation`).
- Kein `except Exception` ohne `# noqa: BLE001`.
- Fail closed: jeder Fehler → `ApplierError`-Subklasse.

## Doku

- `docs/README.md` — Diátaxis-Map
- `docs/ARCHITEKTUR.md` — System-Map
- `docs/NEUBAU-ZIELBILD.md` — Aktueller Loop
- `docs/ERLEDIGT.md` — Erledigte Blöcke
- `docs/OFFENE-BLOECKE.md` — Offene Blöcke
- `AGENTS.md` — Agenten-Routing
