# Werkstatt

Das Agenten-System. Unabhängig von jedem Projekt.
Es baut Projekte, aber es gehört keinem Projekt.

**Ziel:** Das Beste aus Claude Code, Copilot, Aider, Cursor,
Grok und Codex nehmen und ein eigenes Agentensystem bauen.

**Kernprinzip:** On-Demand-Messung + deterministische Gates.
Der Loop prüft, bevor er baut. Kein LLM-Token ohne Plan.

**Stand 2026-10-31 (nach Doku-Migration, Scaffolder, Migrator):**

- **Baseline:** 945 passed, 5 skipped.
- **Branch:** umbau/phase-2 (origin gepusht).
- **Loop:** liest `docs/STATUS.md` reproduzierbar (3 Live-Tests:
  OP-005, OP-001, OP-002). OP-NNN-Disziplin greift.
- **Werkzeuge:** `werkstatt.scaffold` + `werkstatt.migrate` fuer
  neue Projekt-Doku (siehe `docs/index.md`).

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

## Doku-Werkzeuge (2026-10-31)

- `python3 -m werkstatt.scaffold <name> --dir <pfad>` legt alle
  `DOC_CONVENTIONS.md` §2-Pflichtdateien an (idempotent, `--dry-run`,
  `--force`).
- `python3 -m werkstatt.migrate <name> --dir <pfad> [--dry-run|--apply]`
  prueft §2/§3/§5/§6, meldet Verstoesse, legt mit `--apply` fehlende
  Pflichtdateien an (loescht NICHTS).
- Der Loop liest die Living Docs in §6-Reihenfolge (entry > status >
  roadmap > architecture > conventions > adr_index > glossary). Der
  Scout bekommt `## PROJEKT-DOKU` (priorisiert). Bei vagen Aufgaben
  waehlt er GENAU EINEN OP-NNN aus `docs/STATUS.md`.

## Verifikation

- `ruff --fix` vor `_verify_patches` (deterministisch, M-467).
- Circuit Breaker: Reflection stoppt, wenn Ruff-Fehler nicht
  sinken (`loop_reflection_stagnation`).
- Kein `except Exception` ohne `# noqa: BLE001`.
- Fail closed: jeder Fehler → `ApplierError`-Subklasse.

## Doku

- `docs/index.md` — Doku-Einstieg
- `docs/STATUS.md` — offene Punkte (OP-NNN, §5-Format)
- `PROGRESS.md` — Historie (append-only)
- `docs/adr/` — Architecture Decision Records
- `docs/DOC_CONVENTIONS.md` — Golden-Standard (Meta)
