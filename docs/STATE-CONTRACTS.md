# State-Contracts (OP-135a)

Stand: 2026-11-05. Quelle: `werkstatt/state_contracts.py`.
Vollständige Feld-Inventur: `docs/STATE-INVENTUR.md` (OP-134).

## Überblick

- 5 Inter-Role-Übergänge, 5 Dataclasses, 1 Registry (`CONTRACTS`).
- Read-only Property-Views auf `RunState`. Schreiber bleiben auf
  bestehenden Feldern (Migration → OP-135b).
- Kein Pipeline-Fix außer `explorer_diagnostics`-Befüllung im
  deterministischen Explorer-Pfad.

## ASCII-Diagramm: Rolle → Feld → Rolle

    Explorer ──explorer_output──────> Builder
       │                                 ↑
       │                                 │
       └──explorer_diagnostics────> Architect
                                      │
    Scout ──scout_output──────────────┘
                                      │
                                  Planner
                                      │
                              planner_output
                                      │
                                  Builder
                                      │
                              architect_output
                                      │
                                  Planner

Jedes Feld hat einen Schreiber und 1–3 Leser (siehe `CONTRACTS`).

## Tabelle der 5 Verträge

| Feld | Schreiber | Leser | Pflicht |
|---|---|---|---|
| `explorer_output` | pipeline_phases | builder, planner, scout | ja |
| `explorer_diagnostics` | explorer (deterministisch) | architect | ja |
| `scout_output` | planner._run_scout | architect, builder | nein |
| `architect_output` | architect | planner, builder, gates | ja |
| `planner_output` | planner, task_runner | builder, gates, pipeline_phases | ja |

## Datenform pro Rolle (belegt aus STATE-INVENTUR.md)

- **Architect** bekommt: `explorer_findings` (Diagnostics),
  `scout_api_auszug` (Symbol-Liste), `api_index_cache` (AST-Block),
  OP-Felder. **NICHT** `explorer_context` (Datei-Liste).
- **Builder** bekommt: `explorer_context` (Datei-Liste),
  `explorer_findings`, `api_index_cache` (AST), `scout_api_auszug`.
- **Planner** bekommt: `explorer_context` via `getattr`.
- **Scout** bekommt: `explorer_context` via `getattr`.

**Asymmetrie:** Der Architect sieht keinen `explorer_context`
(Datei-Liste). Das ist OP-137.

## Bekannte stille Degradierungen (25 Ghosts, OP-134)

Gruppiert nach Rolle:

- **Explorer-Pfad (3):** `explorer_context`, `explorer_pytest_laufzeit_s`,
  `explorer_ruff_befunde`
- **Reflection-Pfad (8):** `_reflection_bug_sigs_vorher`,
  `_reflection_diff_hash`, `applied_count`, `aktuelle_task`,
  `last_verify_errors`, `reflection_phase`,
  `reviewer_stagnation_false_positive`, `spec_widerspruch_erkannt`
- **Pipeline-Glue (9):** `auto_approve`, `phase_review_uebersprungen`,
  `progress_written_at_commit`, `reflection_erschoepft`,
  `reviewer_deterministic_fail`, `scout_bereits_erfuellt`,
  `split_failure_grund`, `tasks_ok_counter`, `tests`
- **Namens-Drift (1):** `auftrag_bereits_erfuellt` (OP-145)
- **Sonstige (4):** `baseline_gruen`, `last_planner_info`,
  `last_verify_hart_stages`, `messungen_nach_apply`

Vollständige Liste: `docs/STATE-INVENTUR.md` Abschnitt "ghost (25)".

## Offene Punkte (NICHT in OP-135a deklariert)

- **`ScoutOutput.widersprueche`**: existiert heute nur als Audit-Event
  (`planner_scout_api_widerspruch`), nicht als State-Feld. Feld zu
  deklarieren würde denselben Fehler wie `explorer_findings`
  produzieren (deklariert, aber tot). Eigenes Migrations-OP.
- **`ArchitectOutput.zieldateien`**: existiert heute nur implizit in
  `architect_prosa` (Prosa-Parsing durch Planner). Strukturierte
  Extraktion ist eigener OP (Kandidat für OP-137-Nachfolge).

## Verweise

- `werkstatt/state_contracts.py` — Implementation
- `docs/STATE-INVENTUR.md` — Mess-Grundlage (OP-134)
- OP-134 (Inventur), OP-135b (Migration), OP-136 (Validierung),
  OP-137 (Fix architect), OP-145 (Namens-Drift)
