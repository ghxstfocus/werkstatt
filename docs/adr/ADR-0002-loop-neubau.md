# ADR-0002: Loop-Neubau aus pipeline.py-Monolith

- **Datum:** 2026-11-03
- **Status:** accepted
- **Kontext:** `pipeline.py` (11.000+ Zeilen) enthielt die gesamte Loop-Logik
  in einem File: Explorer, Planner, Architect, Builder, Reviewer, Reflection,
  Verify, Gates, Human-Gates, Audit, Committer — alles in einer Datei, alle
  Funktionen mit `pipeline.*`-Präfix. Wartbarkeit und Testbarkeit waren
  entsprechend schlecht: eine Änderung an einem Gate konnte den Reviewer
  brechen, Tests deckten nur Ausschnitte ab, neue Rollen mussten in der
  Monolith-Datei mitwachsen.

## Entscheidung

Strangler-Fig-Extraktion in modulare Rollen-Module unter `werkstatt/`:

- `werkstatt/explorer.py` — Explorer-Phase (Kontext-Sammlung)
- `werkstatt/scout.py` — Scout-Phase (bereits erfüllt? API-Widerspruch?)
- `werkstatt/planner.py` — Planner + Architect + Split
- `werkstatt/builder.py` — Builder (Patch-Generierung)
- `werkstatt/reviewer.py` — Reviewer (Diff-Bewertung)
- `werkstatt/reflection.py` — Reflection-Runden
- `werkstatt/verify.py` — Verify-Stages (py_compile, ruff, mypy, pytest)
- `werkstatt/gates.py` — Plan-Gate, Human-Gate
- `werkstatt/loop.py` — Orchestrierung
- `werkstatt/audit.py` — Audit-Katalog + Event-Log
- `werkstatt/task_runner.py` — Task-Lifecycle
- `werkstatt/pipeline_phases.py` — Phasen-Funktionen (`_phase_tasks_loop`)

`pipeline.py` wurde am 2026-10-31 gelöscht (Phase 22). Die Rollen-Module
bleiben als dauerhafte Struktur.

## Konsequenzen

Positiv:
- Ein Modul pro Rolle — Änderungen bleiben lokal.
- Tests pro Modul isolierbar.
- Neue Rollen sind ein Modul, kein 500-Zeilen-Block in `pipeline.py`.
- `pytest`-Suite wuchs von ~200 auf 1200+ Tests ohne dass eine einzelne
  Test-Datei >500 Zeilen wurde.

Negativ:
- Zirkularität zwischen Modulen (`verify.py` ↔ `loop.py`) via Late-Binding-
  Proxies. Siehe ADR-0003 (Kontroll-Zentralisierung) als nächste Schicht.
- Re-Exports in `loop.py` blähen die Datei auf und machen die tatsächliche
  Impl schwer auffindbar (5× `_verify_patches` — echte Impl in `verify.py`,
  4 Proxies in anderen Modulen).
- Test-Mocks patchen oft den Re-Export-Pfad statt der Impl — Migration ist
  Multi-Session-Arbeit (OP-100).

## Alternativen

- **Monolith patchen:** Kurzfristig billiger, langfristig unwartbar.
  Verworfen.
- **Kompletter Rewrite:** Wochen Arbeit, kein inkrementeller Fortschritt.
  Verworfen.
- **Plugin-System mit dynamischer Registrierung:** Overhead für Solo-Setup.
  Verworfen (aber siehe ADR-0003 für Kontroll-Registry).

## Referenzen

- ROADMAP.md, Phase 1-22 (Strangler-Fig)
- Commit `07a4de6`: `pipeline.py + 3 Tests + Anti-Pattern-Code komplett
  entfernen (Loop-Neubau)`
- ADR-0003: Kontroll-Zentralisierung (nachfolgende Schicht)
