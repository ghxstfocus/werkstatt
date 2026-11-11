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

Der projektbezogene Chat ist der normale Start- und Kontrollpunkt in der UI.
Er untersucht das Repo, formuliert den konkreten Auftrag und verlangt vor
Aktionen eine eigene Freigabe. Plan- und Ergebnis-Gates bleiben Pflicht.
Der CLI-Einstieg bleibt fuer automatisierte und serverseitige Runs verfuegbar:

    python3 -m werkstatt.loop --project NAME --aufgabe "TEXT"

## Agentenrollen und Kontrollschritte

1. Explorer (werkstatt/explorer.py) — read-only Kontext und Befunde
   (deepseek-flash, Thinking aus).
2. Scout (werkstatt/scout.py) — Auftrags- und API-Kontext
   (deepseek-flash, Thinking aus).
3. Architect (werkstatt/planner.py) — strukturierter Plan
   (deepseek-v4-pro, Thinking high).
4. Planner-Split (werkstatt/planner.py) — Architect-Prosa in Tasks
   (deepseek-flash, Thinking aus).
5. Builder (werkstatt/roles/builder/run.py) — Patch pro Task
   (deepseek-flash, Thinking aus).
6. Verify (verify.json-Stages) — deterministische Pruefungen.
7. Reviewer (werkstatt/reviewer.py) — Task-Review
   (deepseek-flash, Thinking aus).
8. Reflection (werkstatt/reflection.py) — Feedback bei Reject
   (deepseek-flash, Thinking aus).
9. Chat (werkstatt/chat_agent.py) — projektbezogene Repo-Analyse,
   Hintergrundfragen und freigabepflichtige Loop-Steuerung. Debugging ist
   eine Chat-Faehigkeit gemaess ADR-0011/ADR-0029, keine eigene Loop-Rolle.
10. Human-Gates — Plan- und Ergebnisfreigabe, fail-closed.

## Werkzeuge (CLI)

- python3 -m werkstatt.loop --project NAME --aufgabe "TEXT"
  vollstaendiger Loop-Lauf (Plan-Gate + Human-Gate).
- python3 -m werkstatt.scaffold NAME --dir PFAD [--dry-run] [--force]
  legt alle §2-Pflichtdateien an (idempotent).
- python3 -m werkstatt.migrate NAME --dir PFAD [--dry-run|--apply]
  prueft §2/§3/§5/§6, meldet Verstoesse, legt mit --apply fehlende
  Pflichtdateien an (loescht NICHTS).

## Skills (Progressive Disclosure)

Skills in `skills/<name>/SKILL.md`. Jeder Skill hat:

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

## Roadmap und Aufgabenwahl

`ROADMAP.md` setzt Fokus und Reihenfolge; sie ist keine startbare Queue.
`STATUS.md` enthaelt nur konkrete, aktuelle und startfaehige OPs. Direkte
Nutzerauftraege haben Vorrang. Ohne konkreten Auftrag waehlt der Selector
begruendet aus startfaehigen OPs; Mehrdeutigkeit wird dem Chat mit Gruenden
und Optionen zurueckgegeben. Verwandte OPs duerfen nur als begrenzter,
verifizierbarer Arbeitsblock vorgeschlagen und muessen am Plan-Gate
freigegeben werden. Es gibt keinen Roadmap-Compiler oder Meta-OP fuer
ungeprueftes automatisches Zerlegen.

## Doku-Vertrag (Loop)

Loop liest Living Docs in §6-Reihenfolge (entry > status > roadmap >
architecture > conventions > adr_index > glossary). Scout bekommt eine
PROJEKT-DOKU-Sektion (priorisiert, max 4000 Z. je Doc). Bei vagen Aufgaben werden offene, startfaehige OPs durch den Selector
geprueft. Kandidat, Blocker und Begruendung muessen sichtbar sein; bei
Mehrdeutigkeit wird gefragt statt geraten.

## Task-Zerlegung (Plan-first)

Der Planner zerlegt die Architect-Prosa von Anfang an logisch
(Interface -> Backend -> Tests), `_leite_deps_deterministisch`
(OP-187) uebersetzt Architect-Aussagen in Dependencies, Topo-Sort
bestimmt die Reihenfolge. Kein On-Demand-Split bei Fehlschlag
(ADaPT entfernt 2026-11-08).


## Verify-Stages (post_build, hart/weich)

Nach jedem Builder-Patch laufen (`.werkstatt/verify.json`):
- `py_compile_changed` (hart)
- `ruff_changed` (weich fuer Style, hart fuer F-Klasse)
- `mypy_changed` (weich, mit `--follow-imports=silent`)
- `control_drift` (hart) — faehrt `python3 tools/control_drift.py --check`
- `pytest_changed` (hart)

### Registry-Drift

Die Stage prueft fuer jede Kontrolle in `CONTROL_REGISTRY` (a) dass ihre
`source` importierbar ist und (b) dass sie auf die registrierte Funktion
zeigt. Bei Verstoss ist die Stage hart und blockiert den Commit; die
Meldung lautet `BROKEN <name>: <source> nicht importierbar` bzw.
`DEAD <name>: source zeigt auf andere fn`. Manueller Gegencheck:
`python3 tools/control_drift.py --list` (zeigt alle registrierten
Kontrollen mit Phase, Haerte, Prioritaet) und `--dead` (zeigt
unregistrierte Kandidaten) — damit der Mensch bei rotem Gate weiss,
welches Kommando die Diagnose liefert, ohne den Code zu lesen.
- `pytest_regression` (hart, phase_end)
- `doku_drift` (hart, phase_end) — prueft letzte 5 Commits und
  staged, unstaged sowie untracked Working-Tree-Aenderungen mit
  `python3 tools/doku_check.py --strict --limit 5 --worktree`.
  Code-Aenderungen ohne geaenderte Projektdoku blockieren den Commit.

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

Im Repository-Root und mit der Projekt-Virtualenv:

    python3 -m pytest -q
    python3 -m ruff check . --output-format concise
    python3 tools/doku_check.py --strict --limit 10 --worktree
    python3 -m tools.quality_gate --json

Keine alten Ergebniszahlen als Sollwerte verwenden. Der aktuelle Nachweis
kommt aus dem CI-Lauf zum geprueften Commit. `quality_gate` prueft die
konfigurierte Suite einschliesslich AST- und Audit-Katalog-Check.

## Historischer Baseline-Hinweis

Die in `docs/HANDOFF-BASELINE.md` dokumentierten Zaehler aus 2026-11-02
sind ein historischer Snapshot und keine aktuelle Betriebsanweisung. Die
2026-11-02 genannten fehlenden AST-/Katalogdateien wurden spaeter wieder
durch aktive Checks ersetzt. Massgeblich sind die aktuelle Konfiguration
von `tools/quality_gate.py` und der CI-Nachweis des jeweiligen Commits.

## Doku

- docs/index.md — Doku-Einstieg
- docs/STATUS.md — offene Punkte (OP-NNN, §5-Format)
- PROGRESS.md — Historie (append-only)
- docs/adr/ — Architecture Decision Records
- docs/DOC_CONVENTIONS.md — Golden-Standard (Meta)

## Loop-Kontrollen (werkstatt/control/)

Alle Loop-Kontrollen (Gates, Verify-Stages, Reflections, Guards) sind
in `werkstatt/control/` als Registry inventarisiert:

- `control/registry.py` — `CONTROL_REGISTRY`, Single Source of Truth.
- `control/phases.py` — `Phase`-Enum (12 Werte).
- `control/runner.py` — `run_control(name, ctx)` / `run_phase(phase, ctx)`.
- `control/drift.py` — `check_drift()` (Registry vs. Code).

**Pflicht-Befehl vor jedem Commit:**

    python3 tools/control_drift.py --check

Exit 0 erwartet. Exit 1 bei Registry-Eintrag dessen `source`-Modul
nicht importierbar ist oder dessen Funktion fehlt.

Neue Kontrolle: Eintrag in `registry.py`, dann `--check`. Migrationen werden nur aus aktuellen OPs oder akzeptierten ADRs abgeleitet; historische OP-Nummern sind keine aktive Anweisung.
