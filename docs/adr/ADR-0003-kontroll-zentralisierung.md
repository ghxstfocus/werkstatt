# ADR-0003: Kontroll-Zentralisierung in werkstatt/control/

- **Datum:** 2026-11-03
- **Status:** accepted (schrittweise Migration, Phase 33)
- **Kontext:** Nach dem Loop-Neubau (ADR-0002) waren 32 Kontrollfunktionen
  über 14 Dateien verstreut, 21 Phase-Hooks über 10 Dateien:
  `verify.py`, `gates.py`, `reflection.py`, `planner.py`, `scout.py`,
  `task_runner.py`, `pipeline_phases.py`. Debugging eines Loop-Fehlers
  erforderte Grep über den halben Code. `_verify_patches` existierte 5×
  (1 echte Impl + 4 Late-Binding-Proxies), die echte Implementierung war
  ohne Trace nicht auffindbar. Kein File zeigte, welche Kontrolle in welcher
  Phase was tut.

## Entscheidung

Neues Paket `werkstatt/control/` als Single Source of Truth:

- `control/control.py` — `Control`-Dataclass (name, phase, fn, source, hart,
  prioritaet, legacy_imports, deprecated_by).
- `control/phases.py` — `Phase`-Enum (12 Werte, chronologisch):
  `PRE_BUILD, SCOUT, PLAN_GATE, PLAN_REJECT, TASK_START, TASK_END,
  POST_BUILD, REFLECTION, PHASE_START, PHASE_END, HUMAN_GATE, ADR_MINI`.
- `control/registry.py` — `CONTROL_REGISTRY`, Einträge für alle 13
  Loop-Kontrollen (Phase 33.1: 13; nach 33.5: ~30).
- `control/runner.py` — `run_control(name, ctx)` + `run_phase(phase, ctx)`.
  Dispatcht über Registry.
- `control/drift.py` — `check_drift()` (Registry vs. Code).
- `tools/control_drift.py` — CLI (`--check`, `--list`, `--dead`, `--json`).

**Migration gestaffelt (Phase 33.2–33.6):**

| Sub-Phase | Inhalt | OP |
|---|---|---|
| 33.1 | Skelett + Registry + Drift-Check | ✅ erledigt 2026-11-03 |
| 33.2a | verify.json hart-Feld explizit | ✅ erledigt (OP-095) |
| 33.2b | verify.py → control/verify.py (163 Patch-Calls) | OP-100 |
| 33.3 | gates.py → control/gates.py | OP-096 |
| 33.4 | reflection.py → control/reflection.py | OP-097 |
| 33.5 | pipeline_phases.py 1600 → <400 Zeilen | OP-098 |
| 33.6 | control_drift als Pre-Commit-Gate | OP-099 |

**Kernprinzip:** Bestehende Kontrollen werden NICHT verschoben bis die
Registry steht. Registry dokumentiert zuerst was existiert, Migration
erfolgt schrittweise mit `control_drift --check` als Guardrail pro Phase.

## Konsequenzen

Positiv:
- Ein File (`registry.py`) zeigt alle Kontrollen mit Name, Phase,
  Priority, Impl-Pfad.
- `run_control(name, ctx)` ersetzt verstreute direkte Aufrufe — ein
  Breakpoint, ein Test-Mock-Pfad, eine Impl.
- `control_drift --check` failt bei:
  - Registry-Eintrag dessen `source`-Modul nicht importierbar ist.
  - Registry-Eintrag dessen `source`-Funktion nach Refactor fehlt.
  - Kandidat-Funktionen im Code die noch nicht registriert sind.
- Phase-Enum macht Phasen-Reihenfolge explizit statt implizit in Strings.
- Toter Code wird sichtbar (Registry-Einträge ohne Aufrufer, Kandidaten
  ohne Registry-Eintrag).

Negativ:
- Migration ist Multi-Session-Arbeit (OP-100: 163 Patch-Calls; OP-098:
  1600 → <400 Zeilen).
- Während der Migration existieren zwei Wege (direkt + Registry) —
  Gefahr der Inkonsistenz. Guardrail: `control_drift --check` pro Commit.
- Neue Abhängigkeit: `werkstatt.control` importiert alle Rollen-Module
  für die Registry — potenzieller Import-Zyklus. Aktuell nicht kritisch
  weil `control` von keinem Rollen-Modul importiert wird; wird relevant
  bei 33.3-33.4.

## Alternativen

- **Verstreut lassen:** Kein Fortschritt, Debugging bleibt mühsam.
  Verworfen (war der Status quo).
- **Alles in eine Datei (`control.py`) werfen:** Monolith 2.0.
  Verworfen.
- **Plugin-System mit dynamischer Registrierung (Entry-Points):** Overhead
  für Solo-Setup, kein Mehrwert bei einem Repo. Verworfen.
- **Big-Bang-Migration in einer Session:** Risiko Test-Brüche (163
  Patch-Calls), kein Rollback-Punkt. Verworfen.

## Referenzen

- ROADMAP.md, Phase 33 (Kontroll-Zentralisierung)
- AGENTS.md, Sektion "Loop-Kontrollen"
- OP-095, OP-096, OP-097, OP-098, OP-099, OP-100
- ADR-0002 (Loop-Neubau, Voraussetzung)
- ADR-0004 (Drift-Check-Pattern, ergänzendes Muster)
