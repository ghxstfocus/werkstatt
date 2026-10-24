# Offene Bloecke — Werkstatt

Stand: 2026-10-24 (nach M-322..M-343c, RERUN-23/24).
Vorherige Liste: `OFFENE-BLOECKE-ARCHIV-2.md`.

Nur noch **offene** Bloecke. Erledigte stehen in
`ERLEDIGT.md`. Merkposten (M-Nummern) in `MERKPOSTEN.md`.

## Loop-Haertung (M-323b, M-341, M-344)

| Block | Aufwand | Kurz |
|---|---|---|
| M-323b | mittel | `phase_end`-Checkpoint pro logischer Phase. Aktuell: Phasen sind Gruppierung, kein Checkpoint. Nach jeder Phase `_verify_patches(state, phase="phase_end")` + Reflection. |
| M-341 | klein | Explorer ueberspringen, wenn `task_files` gesetzt. Aktuell: Explorer liefert 0 files (M-338 zu strikt), was kosmetisch ist. |
| M-344 | klein | `PROGRESS.md` mit Phasen-Header. Aktuell: pro Task, nicht pro Phase. |

## Pipeline-Abbau (M-345, M-346)

| Block | Aufwand | Kurz |
|---|---|---|
| M-345 | mittel | `pipeline.py` (11.639 Z.) loeschen. Erst wenn `werkstatt/agent.py` keine Kopien mehr braucht (M-231 Zwischenzustand). |
| M-346 | klein | `pipeline._approval_und_human_gate` und `pipeline.load_project_config` in `werkstatt/` verschieben. Letzte Abhaengigkeiten. |

## CLI (M-347)

| Block | Aufwand | Kurz |
|---|---|---|
| M-347 | klein | CLI-Einstiegspunkt fuer den Loop. Aktuell nur `python3 -m werkstatt.loop --project ... --aufgabe ...`. |

## Werkstatt-Entkopplung

| Block | Aufwand | Kurz |
|---|---|---|
| Entkopplung | mittel | `werkstatt/verify.py` importiert `harness.*` und `core.changeapplier.*` (nur Introspektion). Ziel: null Fremd-Imports. Empfohlen: AST-basierte Signatur-Extraktion aus `project_dir`. |

## Baseline

| Block | Aufwand | Kurz |
|---|---|---|
| 5-ruff | klein | ruff 13 Fehler. Kein Runtime-Bug. |
| 5-mypy | klein | mypy 8 Fehler in 2 Dateien. |

## Phase 3c — NEUBAU-Abloesung

| Block | Aufwand | Kurz |
|---|---|---|
| 3c | mittel | Alte Tests, die mit dem alten Code fallen, entfernen. Erkenntnisse in Inventar. |

## Merkposten (alte Session)

| Block | Aufwand | Kurz |
|---|---|---|
| M-162 | klein | „Recovery nach Loop" als eigenstaendigen Pfad messen oder als nicht-existent schliessen. |
| Werkstatt-Entkopplung | mittel | siehe oben. |
| Phase 3.0 | mittel | Rollen-Reduktion (10 -> 8 Rollen). Teils erledigt. |

## Verweise

- `ROADMAP.md` — Phasen-Uebersicht.
- `ERLEDIGT.md` — erledigte Bloecke.
- `MERKPOSTEN.md` — M-Nummern.
- `OFFENE-BLOECKE-ARCHIV-2.md` — archivierte Bloecke (vor 2026-10-24).
- `NEUBAU-ZIELBILD.md` — aktueller Loop als Ziel.
- `Bau-Handoff.md` — aktueller Stand.

## Hooks statt Prompts (M-349..M-352)

| Block | Aufwand | Kurz |
|---|---|---|
| **M-348-Fix** | klein | `plan_ok` nach `run_planner` neu berechnen. Sonst wird das Plan-Human-Gate uebersprungen. |
| **M-349** | klein | `hooks/planner_gate.py` neu: Doku-Tasks ablehnen. `_plan_gate` ruft Hook. Planner-Reflection mit `last_planner_info`. |
| **M-350** | mittel | `planner_gate.py` erweitern: action, task_files, phasen-Pflicht, phase_id. `PLANNER_SYSTEM` halbieren. |
| **M-351** | klein | `loop.py:1167`: toter `post_tool_use`-Aufruf entfernen. |

## Offene Merkposten (unveraendert)

- **M-323b:** Phasen-Checkpoints (`phase_end` pro Phase).
- **M-341:** Explorer ueberspringen bei `task_files`.
- **M-344:** PROGRESS.md mit Phasen-Header.
- **M-345:** pipeline.py loeschen (nach agent.py-Aufloesung).
- **M-346:** pipeline._approval_und_human_gate verschieben.
- **M-347:** CLI-Einstiegspunkt.

## M-350..M-353 (Hooks + Rollback)

| Block | Aufwand | Kurz |
|---|---|---|
| **M-350** | erledigt | planner_gate.py erweitert (5 Checks), PLANNER_SYSTEM gekuerzt. |
| **M-351** | erledigt | no_effect-Patches filtern (builder + loop). |
| **M-354** | offen | Checkpoint nach jedem Task (Aider-Muster, statt reset --hard). |


## M-355b..M-363 (Loop-Durchbruch, 2026-10-24)

| Block | Aufwand | Kurz |
|---|---|---|
| **M-355b** | erledigt (403823d) | run_builder=False -> sofort return 1. |
| **M-356** | erledigt (b844ab8) | Rollback auf start-HEAD. |
| **M-357** | erledigt (9b31ec8) | _run_with_progress re-raised Exceptions -> False. |
| **M-358** | erledigt (9b31ec8) | Footer mit echten Task-Zahlen. |
| **M-359** | erledigt (9b31ec8) | fail-closed bei kein Patch (old_string_not_found). |
| **M-360** | erledigt (f4e45ed) | create + Datei fehlt -> anlegen statt fail. |
| **M-361** | offen | Test fuer M-355b (run_builder=False -> return 1). |
| **M-362** | offen | Test fuer M-360 (create + Datei fehlt -> anlegen). |
| **M-363** | offen | Doku-Pflege Baseline/HISTORISCH. |

**Stand RERUN-38:** Loop erstmals seit RERUN-23 vollstaendig
erfolgreich (8/8, RC=0, echte Aenderung im Zielprojekt,
Zielprojekt committed 2a0a284).


## M-361..M-363 (Nachpflege nach RERUN-38)

| Block | Aufwand | Kurz |
|---|---|---|
| **M-361** | offen | Test fuer M-355b (run_builder=False -> sofort return 1). |
| **M-362** | offen | Test fuer M-360 (create + Datei fehlt -> anlegen). |
| **M-363** | offen | Doku-Pflege Baseline/HISTORISCH. |


## M-365..M-370 (Methodische Luecken, 2026-10-24)

Kandidaten aus `ARCHITEKTUR.md` Abschnitt 7. Nicht Teil
des aktuellen Loops, aber strukturell sinnvoll.

| Block | Aufwand | Kurz |
|---|---|---|
| **M-365** | mittel | Read-Before-Write im Builder (Tool-Use-Contract). |
| **M-366** | klein | mtime-Check in apply_code_patches (Stale-Read-Detection). |
| **M-367** | mittel | Builder-Feedback-Loop (Verify-Before-Commit). |
| **M-368** | mittel | Reviewer-als-Reflection (Agent-Handoff/Escalation). |
| **M-369** | gross | Router-Pattern fuer Task-Typen (Dynamic Dispatch). |
| **M-370** | klein | Prompt-Budget im Builder (Context-Window-Management). |

## M-386/M-387 (nach RERUN-48)

| Block | Aufwand | Kurz |
|---|---|---|
| **M-386** | mittel | Rollen-Audit (alle Rollen gegen goldenen Standard + Widerspruchs-Check). |
| **M-387** | mittel | RERUN-49 mit schwierigerer Aufgabe (mehrere Fehler, verschiedene Typen). |

## M-389 — Doku-Pflege im Loop (geplant 2026-10-25)

**Problem:** Der Loop schreibt nur `PROGRESS.md` (Selbst-Tracking).
Echte Projektdokumentation (`docs/*.md`, `README.md`) wird
nicht gepflegt. Bei Code-Aenderungen veraltet die Doku.

**Goldstandard:** Living Documentation (Doctyze, Codebase-Cortex)
— der Agent prueft Doku-Freshness und flaggt veraltete Seiten.

**Architektur:**
- `skills/doku-pflege/SKILL.md` — neuer Skill.
  Trigger: "doku", "readme", "docs", "dokumentation".
  allowed-tools: run_readonly
- `explorer.py` — `_messen()` erkennt Doku-Trigger,
  `grep -r "TODO\|FIXME\|XXX" docs/`.
- `reviewer.py` — Prompt: "Pruefe Doku-Freshness. Wenn stale:
  flagge als Doku-Task."
- `planner.py` — Wenn Reviewer Doku-Task flaggt: separater
  Task mit action=update, task_files=["docs/*.md"].

**Wichtig:** Doku ist KEIN Code-Patch. Der Reviewer flaggt,
der Planner baut einen separaten Task. Der Builder schreibt
die Doku.

**Aufwand:** mittel (~150 Zeilen + neuer Skill + Reviewer-Prompt
+ Planner-Erweiterung).

**Voraussetzung:** M-345 (Pipeline-Abbau) sollte vorher
abgeschlossen sein.

**Nicht in dieser Session** — Loop ist gerade stabil
(RERUN-48/49/50 alle LOOP_RC=0).

## M-388 — UI-Testing via Chrome DevTools (geplant 2026-10-25)

**Problem:** Der Loop kann aktuell nur ruff/pytest messen.
Projekte mit UI (Browser, Frontend) koennen nicht getestet werden.

**Goldstandard:** Chrome DevTools MCP (offizieller MCP-Server von
Google) — verbindet den Agenten mit einer live Chrome-Instanz.
Accessibility-Snapshots statt CSS-Selektoren, Netzwerk-Inspektion,
Console-Messages, Performance-Traces.

**Architektur:**
- `skills/ui-testing/SKILL.md` — neuer Skill.
  Trigger: "ui", "browser", "chrome", "frontend", "oberflaeche".
  allowed-tools: run_chrome_devtools
- `werkstatt/tools.py` — `run_chrome_devtools()` via MCP-Client.
- `explorer.py` — `_messen()` erkennt UI-Trigger.
- Python-MCP-Library (`mcp`), `npx chrome-devtools-mcp@latest`.

**Aufwand:** mittel-gross (~200 Zeilen + MCP-Setup).

**Voraussetzung:** M-345 (Pipeline-Abbau) sollte vorher
abgeschlossen sein.

**Nicht in dieser Session** — Loop ist gerade stabil.
