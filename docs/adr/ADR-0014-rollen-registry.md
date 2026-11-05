# ADR-0014: Rollen-Registry als Single Source of Truth

- **Datum:** 2026-11-05
- **Status:** accepted
- **Kontext:** Der Loop hat 7 Rollen (Architect, Planner, Builder,
  Reviewer, Explorer, Scout, Reflection). Bis 2026-11-05 hat jede
  Rolle ihre Skills in ihrem eigenen Modul hartkodiert geladen:
  - `architect.py`: `("using-werkstatt", "plan-crafting",
    "commit-history")`
  - `planner.py`: `("using-werkstatt", "milestone-planning",
    "plan-crafting")`
  - `explorer.py`: `using-werkstatt` + `systematic-debugging`
  - `builder.py`: `skills_aktivieren(..., rolle="builder")`
  - `reviewer.py`: `review-work` + `skills_aktivieren(..., rolle="reviewer")`
  - `reflection.py`: `systematic-debugging`

  Kein gemeinsames Objekt, keine Konsistenz. Der `rollen:`-Marker
  in den Skills (`skills/*.md`) wurde von `architect.py` und
  `planner.py` ignoriert — sie luden hartkodierte Listen.

  Der Regress-Bug 2026-11-03 (M-446): `architect.py` lud
  `plan-crafting`, der `## Tools` mit `run_readonly(...)` enthaelt.
  `deepseek-reasoner` interpretierte das als echte Tool-Calls
  und lieferte DSML-Syntax statt Prosa. `docs/ARCHITECTURE.md:20-22`
  sagt woertlich "Keine Skills, keine Tools" — der Code widersprach
  der Doku.

**Fragestellung:** Wie verhindern wir, dass einzelne Module die
Architektur-Entscheidungen (Rolle X bekommt Y Skills, Z Tools)
eigenmaechtig umgehen?

**Entscheidung:** Zentrale Rollen-Registry `werkstatt/rollen.py`.
Pro Rolle:
- `skills: tuple[str, ...]` — explizite Skill-Namen
- `skill_filter_rolle: str | None` — Marker-Filter fuer dynamische Skills
- `tools: tuple[str, ...]` — erlaubte Tools (leer = keine)
- `prompt_module` + `prompt_const` — LAZY-Referenz zum System-Prompt

Aufrufer nutzen `ROLLEN[name].lade_skills(...)` statt eigener
Ladelogik. `lade_system_prompt()` ist lazy (Zirkel-Import vermeiden).

**Zentrale Regel (fail-closed):** Eine Rolle ohne explizite Skills
und ohne `skill_filter_rolle` bekommt **keine Skills**. Leere Tupel
= explizite Entscheidung, nicht Versehen.

**Konsequenzen:**
- **Positiv:** Rollen-Definitionen sind an einem Ort sichtbar. Neue
  Rollen (Debugger, Judge) lassen sich ergaenzen, ohne 5 Module
  anzufassen. `plan-crafting` (mit Tools) landet nur in der
  Planner-Rolle, nicht mehr versehentlich im Architect.
- **Positiv:** Tests koennen die Registry pruefen (7 Rollen, Architect
  fail-closed, plan-crafting nur bei planner, siehe
  `tests/test_rollen_registry.py`).
- **Negativ:** Ein Registry-Fehler wirkt auf alle Rollen gleichzeitig.
  Mitigation: fail-loud-Pruefung in `architect.py` (RuntimeError wenn
  `ROLLEN['architect'].lade_skills(...)` nicht leer ist).
- **Offen:** Migration der restlichen 5 Aufrufer (`planner`, `builder`,
  `reviewer`, `explorer`, `scout`) laeuft in einer Folge-OP. Aktuell
  nutzt nur `architect.py` die Registry.

**Verweise:**
- `werkstatt/rollen.py` (Implementierung)
- `tests/test_rollen_registry.py` (5 Strukturtests)
- `docs/ARCHITECTURE.md:20-22` ("Keine Skills, keine Tools")
- Commit `c8c28d0` (Registry + Architect-Pilot)
- Regress-Kontext: Commit `dd897b5` (2026-10-25, M-446-Fix)
