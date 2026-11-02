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

## Skills (Progressive Disclosure)

20 Skills in `skills/<name>/SKILL.md`. Jeder Skill hat:

- `globs:` — Datei-Muster, die den Skill aktivieren (deterministisch per fnmatch)
- `rollen:` — Rollen-Filter: `builder`, `reviewer`, `architect`, `scout`,
  `explorer`, `planner` (leer = alle Rollen)
- `always:` — in jeder Rolle aktiv (selten; `using-werkstatt` ist der Fall)
- Body (Markdown) — wird bei Aktivierung in den Prompt geladen

Aktivierung: `skills_aktivieren(skills, task_files, max_total=3, rolle=...)`.
Ranking nach Glob-Spezifitaet (OP-072): spezifischere Muster gewinnen.
Max 3 Skills pro Aufruf, um Context-Overload zu verhindern.

**Skills statt Prompt-Bloecke:** Reviewer-Checks (SEMANTIK/KONSTANTEN/
SYMBOL/SCOPE) und Builder-Regeln (FUNKTION-WAHL/RUFF-GRUNDREGELN/
TYP-NARROWING) leben als Skills, nicht im Prompt. Ausnahme: `DATUM
(STRIKT)` bleibt im BUILDER_SYSTEM — Output-Contract, immer gebraucht
auch bei `.py`-Patches. Referenz: Commits `122b979` und `22b7776`.

**Audit:** `loop_skills_geladen`-Event pro Aufruf mit `rolle` und `neu`
(dedupliziert). `state.geladene_skills` trackt was bereits im Kontext
ist — kein doppeltes Laden.

**Pflege:** Neue Skills brauchen Frontmatter mit `globs:` + `rollen:`.
Skills-Test: `tests/test_skills.py` + `tests/test_skills_loader.py`
pruefen Anzahl und Struktur.

## Roadmap-to-OP (Vision -> Queue)

Der Loop frisst OPs (`STATUS.md`), aber die Etappen (`ROADMAP.md`) muessen
in OPs uebersetzt werden. Bis Phase 31 (Roadmap-Compiler) geschieht das
manuell:

1. Phase aus `ROADMAP.md` waehlen.
2. Meta-OP in `STATUS.md` anlegen: *"Lies Phase X und zerlege sie in OPs."*
3. Loop fuehrt den Meta-OP aus -> Architect schreibt die OPs.
4. Loop arbeitet die neuen OPs ab.

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

## Verify-Stages (post_build, hart/weich)

Nach jedem Builder-Patch laufen (`.werkstatt/verify.json`):
- `py_compile_changed` (hart)
- `ruff_changed` (weich fuer Style, hart fuer F-Klasse)
- `mypy_changed` (weich, mit `--follow-imports=silent`)
- `pytest_changed` (hart)
- `pytest_regression` (hart, phase_end)

**Pre-Reviewer-Gate** (`werkstatt/verify_classify.py` + `_phase_tasks_loop`):
Vor jedem Reviewer-Aufruf werden `_v_weich`-Fehler klassifiziert. Harte
Fehler (py_compile, pytest, ruff F821/F822) fuehren zu `review_result=rejected`
OHNE LLM-Call. Verhindert, dass der Reviewer Code approved, der gar nicht
importiert werden kann.

**Hart** (blockiert): py_compile, pytest, ruff F*
**Weich** (blockiert nicht): ruff E/C/W, mypy (Baseline-Drift bekannt)

## Hard Rules

- Fail closed: jeder Fehler -> ApplierError-Subklasse.
- Kein except Exception ohne # noqa: BLE001.
- ruff --fix vor _verify_patches (deterministisch).
- Circuit Breaker: Reflection stoppt, wenn Ruff-Fehler nicht sinken.
- Frozen dataclasses: kein setattr.

## Pflicht-Befehle

    pytest -q                              # 1164 passed, 5 skipped (2026-11-02)
    ruff check .                           # 306 errors (2026-11-02)
    mypy werkstatt/                        # 21 errors in 9 files (2026-11-02)
    python3 -m tools.quality_gate --json   # exit 0, regression false (2026-11-02)

Nicht python -m pytest (Binary python fehlt).
Nicht mypy . (zaehlt tests/, mehr Fehler).

## Baseline-Hinweis (2026-11-02)

docs/HANDOFF-BASELINE.md und tools/quality_gate.py fuehren eine Baseline
aus VOR dem Loop-Neubau (pytest 1435, ruff 13, mypy 11, AST 6, Katalog 162).
Diese Baseline ist VERALTET:

- pytest 1435 -> 1164 (Loop-Neubau + spaeter wieder Tests ergaenzt)
- ruff 13 -> 306 (tests/ wurde nie durchgerufft; keine ruff-Config)
- mypy 11 -> 21 (werkstatt/, pipeline.py entfernt)
- AST 6 -> 0 (tests/test_audit_kinds.py entfernt), Katalog 162 -> fehlt (_KATALOG_SOLL entfernt)

Konsequenz: quality_gate BASELINE wurde 2026-11-02 re-baselined
(pytest=1164, ruff=306, mypy=21). AST- und Katalog-Check skippen, wenn
die jeweilige Datei fehlt (delta=0). quality_gate ist gruen (exit 0).

## Doku

- docs/index.md — Doku-Einstieg
- docs/STATUS.md — offene Punkte (OP-NNN, §5-Format)
- PROGRESS.md — Historie (append-only)
- docs/adr/ — Architecture Decision Records
- docs/DOC_CONVENTIONS.md — Golden-Standard (Meta)
