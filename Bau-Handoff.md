# Bau-Handoff — Session 2026-10-29 (Durchbruch)

**Session-Ergebnis:** Gold-Umbau + Scout-Agent + Prompt-Audit.
Suite 1619 -> 1622. Erster RERUN mit 3/3 Tasks approved.
Commit `2c4703d` (Gold-Umbau: `_baue_api_index` + Reviewer).

---

## STAND

**Werkstatt** (`/opt/werkstatt`):
- Branch `umbau/phase-2`
- Suite: **1622 passed, 5 skipped**
- Ruff Baseline: loop.py 7, planner.py 1, builder.py 2,
  reviewer.py 0, explorer.py 0, pipeline.py 2
  (planner.py 3 -> 1 durch Cleanup 2026-10-30)

**Zielprojekt** (`/opt/security-ai`):
- Services active, `.env` vollstaendig
- Timeline funktioniert (15 Eintraege, klickbar, mit Score)
- Letzter RERUN 19:10 — 3/3 Tasks approved

---

## WAS FUNKTIONIERT (verifiziert 2026-10-29)

### Gold-Umbau (`2c4703d`)
- **Architect** (`ARCHITECT_SYSTEM`, deepseek-reasoner): freie Prosa
  mit `## <pfad>`-Ueberschriften, Interface + Logik + Integration.
- **Planner** (`_zerlege_in_sub_tasks`, deepseek-chat): zerlegt Prosa
  in Tasks (JSON).
- **Zwei Agents, zwei Calls.** Tool-Use-Loop entfernt.

### Scout-Agent (`_run_scout` + `_baue_api_index`)
- **`_baue_api_index`:** AST-basiert, deterministisch. Liefert pro Datei:
  `__all__`, Klassen (Methoden + Signaturen + Rueckgabetypen),
  Top-Level-Funktionen, Imports.
- **`_format_api_index_for_prompt`:** deterministisch, kompakt.
- **`_finde_api`:** deterministisch, sucht API im Index.
- **`_run_scout`** (deepseek-chat): formuliert Auftrag aus API-Index.
- **Widerspruchs-Check:** prueft APIs aus Auftrag gegen Code-Index
  (`read_events` existiert nicht -> `list_recent_assessments`).

### Prompt-Audit (P0-P3)
- **`_BUILDER_SCHNITTSTELLE`** an `ARCHITECT_SYSTEM`:
  Architect kennt Builder-Grenzen (max 8000 Tokens, keine Tools,
  `## <pfad>`-Pflicht).
- **`_REVIEWER_SCHNITTSTELLE`** an `BUILDER_SYSTEM`:
  Builder kennt Reviewer (bestehende Aufrufe pruefen, HIGH-Bug bei
  Entfernung).
- **`ARCHITECT_SYSTEM`:** `GOLD: SCOUT-KONTEXT` — nutzt APIs aus
  dem Code-Index, NICHT aus der Aufgabe.
- **`_SCOUT_NACHFOLGER_BLOCK`:** Scout liefert JSON, Architect Prosa.
- **Toter else-Zweig (`PLANNER_SYSTEM`)** entfernt.

### Reviewer Diff-Check (P0)
- `REVIEWER_SYSTEM` prueft **jede `-`-Zeile** gegen die volle Zieldatei.
- **HIGH-Bug** wenn bestehender Aufruf entfernt, Funktion ueberschrieben,
  API erfunden.
- **Live-Beleg 18:58:** t3 rejected (Builder wollte `_section_timeline`
  statt `_section_timeline_entries` aendern).

### Import-Validierung (`996d616`)
- Klassischer Builder-Pfad prueft jetzt Imports
  (`_validate_imports_in_patch`).
- Bei Fehler: Patch verworfen, `builder_patch_import_fehler`.
- **Live-Beleg 18:51:** `AuditReadError` (erfunden) -> Task failte sauber,
  kein Service-Crash.

### Timeline (Zielprojekt, `5101e84`)
- **Backend** (`routes_state.py`):
  * `_section_timeline_entries` liefert `ts_display`, `href`, `score`,
    `audit_id`.
  * `_format_timeline_ts` (ISO -> YYYY-MM-DD HH:MM:SS).
  * `dashboard_state` ruft `_section_timeline_entries` (nicht
    `_section_timeline`).
- **Frontend** (`dashboard.js`):
  * `fetchState` unterstuetzt Array + `{entries}`.
  * `renderTimeline` nutzt `ts_display`, `href`, `score`, `agent`.
- **CSS** (`components.css`): 7 Timeline-Klassen.
- **Ergebnis:** 15 Eintraege, formatiert, klickbar (Link auf
  `/audit/<audit_id>`), mit Score.

---

### M-487 — Human-Gate committet selbst (`31c6ff3`)
- **`_committe_zielprojekt(state)`** in `werkstatt/loop.py`:
  `git status` -> `git add -A` -> `git commit` -> `git rev-parse HEAD`.
- Aufruf im `_human_gate`-`j`-Zweig. Fail-closed: Bei Git-Fehler
  bricht der Loop ab (`✗ LOOP FEHLGESCHLAGEN`), statt `✓` zu luegen.
- **Nur bei explizitem `j`.** Auto-Approve committet nicht.
- **4 Audit-Events:** `loop_human_gate_committed`,
  `loop_human_gate_commit_skip`, `loop_human_gate_commit_fehler`,
  `loop_human_gate_commit_abort`.
- **Betriebs-Voraussetzung:** `.git/` im Zielprojekt muss vom
  Loop-User (`security-ai`, Gruppe `builder`) beschreibbar sein.
  Setgid auf `.git`-Verzeichnisse. Keine `root:root`-Dateien.
- **Live-Beleg 20:36:** RERUN `4e860c3` — Builder+Reviewer+Phase-Review
  in 4s, Human-Gate `j` -> automatischer Commit, `✓ LOOP ERFOLGREICH`.

## ERLEDIGT (2026-10-29)

### K48 — old_string-Patch-Ansatz
- Builder nutzt `_build_patches_fuer_datei` mit vollem Datei-Inhalt +
  relevantem Architect-Abschnitt + Feedback + Reviewer-Bugs +
  Verify-Fehlern + Reflection-History.
- `BUILDER_SYSTEM`: "Erweitern statt Ueberschreiben"-Regel.
- `_architect_abschnitt`: versteht beide Formate
  (`## <pfad>` + innerhalb von `## 3.`).

### K50 — Fake-Done bei Reviewer-Reject
- `_patches_wirklich_angewendet` (fail-closed).
- `last_verify_errors` kumulativ.
- `applied_count` an allen Apply-Pfaden.

### K55b — `_marker_rest` praezisieren
- Nur konkrete Tool-Call-Marker pruefen.
- `<migrationsstand pflicht>` wird durchgelassen.

### K56a — Planner-Reflection
- Cherry-Pick, aber **nicht** aktiv (Kaskade, im Gold-Umbau entfernt).

### K60 — Builder-Diagnose
- `builder_keine_patches` mit Details (raw_len, raw_prefix,
  raw_has_context, patches_vor_normalisierung, ...).

### K61a — `task_files` normalisieren
- `_normalisiere_task_files` an 3 Stellen.
- Kurze Pfade -> volle Pfade (aus Explorer).

### K61b — `last_planner_info` bei JSON-Fehler
- Wird gesetzt bei `planner_json_fehler`.

### K61c — Explorer-Pfade aufloesen
- `rglob` findet volle Pfade.
- `_aufgabe_pfade` enthaelt volle Pfade.

### K62 — Import-Validierung klassischer Pfad
- In `run_builder` nach `_normalisiere_aider_patches`.

### Prompt-Audit P0-P3 + Gold-Umbau + Scout + API-Index
- Siehe "Was funktioniert".

---

## OFFEN (Prioritaet)

Kanonische offene Liste: `docs/OFFENE-BLOECKE.md`.
Dieser Abschnitt fuehrt nur die session-relevanten P0-P4.

### ✅ P0 — `PLANNER_SPLIT_SYSTEM` an Gold-Format (erledigt `aa7881f`)
**Entscheidung:** Option (b) — deterministische Python-Segmentierung.
`_segmentiere_nach_pfad(prosa)` in planner.py zerlegt an
`## <pfad>`-Ueberschriften, Fallback in `_zerlege_in_sub_tasks` und
`_llm_split_einzel_task`, wenn `architect_start` fehlt.
Der `PLANNER_SPLIT_SYSTEM`-Prompt bleibt unveraendert — die
LLM-Marker sind nicht mehr Pflicht.

### ✅ P0 — Builder-Prompt: Funktion-Wahl (erledigt `aa7881f` + `c13bb8a`)
**Loesung:** zwei Ebenen.
1. `## FUNKTION-WAHL` in `BUILDER_SYSTEM` (`aa7881f`): waehle die
   genannte Funktion, nicht die aehnlichste.
2. `_filtere_auf_funktionen(abschnitt, task_text)` (`c13bb8a`):
   schneidet den Architect-Abschnitt auf die Task-Funktionen zu,
   bevor er in den Builder-Prompt geht. Verhindert, dass der Builder
   fremde Funktionen aus demselben Datei-Block umbaut.

### ✅ P1 — Reviewer Semantik (erledigt `aa7881f`)
**Loesung:** `## SEMANTIK-CHECK` in `REVIEWER_SYSTEM`:
- Task nennt Funktion X, Diff nutzt Funktion Y → HIGH-Bug.
- Bestehender Aufruf ohne Task-Auftrag entfernt → HIGH-Bug.
- API erfunden (nicht im Import-/Code-Index) → HIGH-Bug.
Live-Beleg 20:16: RERUN approved im 1. Durchlauf, weil Builder
nur `_section_timeline_entries` angefasst hat.

### P2 — Frontend-Tests (1-2h)
**Problem:** `dashboard.js` ist ungetestet.
**Optionen:** Jest/Vitest mit jsdom; `node --check` (nur Syntax);
manuelle Browser-Tests.

### P3 — Doku-Ueberarbeitung
- `AGENTS.md`: Agent-Kette (Scout, Architect, Planner, Builder,
  Reviewer).
- `docs/ARCHITEKTUR.md`: Layer, API-Index, Prompt-Kette.
- `docs/RUNBOOK.md`: RERUN, Debug, safe.directory.

### P4 — K14 / K18 (gross)
- `run_pipeline_loop` 700 Zeilen -> 7 Phasen-Funktionen.
- `pipeline.py` 11k Zeilen zerlegen.

---

## NAECHSTE SESSION — START

**Aus Session 2026-10-29 spaet (nach Handoff-Update):**

- **M-487 erledigt** (`31c6ff3`), live bewiesen (`4e860c3`).
- **Neuer offener Punkt `R-CHECK-1`** (siehe `docs/OFFENE-BLOECKE.md`):
  Reviewer prueft Task-Zahlen nicht. Live-Beleg 20:42: Task verlangt
  `limit=10`, Builder schreibt `limit=5`, Phase-Review approved.
  Fix: `## KONSTANTEN-CHECK` in `REVIEWER_SYSTEM`.
- **Naechster Block:** `R-CHECK-1` (klein, ~15 min).

## NAECHSTE SESSION — START (alt)

**Vorbereitung:**
1. `git status --short --branch` sauber?
2. `git log --oneline -1` == letzter Commit?
3. `pytest -q` — 1622 erwartet.
4. `systemctl is-active` — alle active?

**Erste Aktion: P4 (PLANNER_SPLIT_SYSTEM)**
- Messung: `grep -n "architect_start\|PLANNER_SPLIT_SYSTEM" werkstatt/planner.py`
- Fix: `PLANNER_SPLIT_SYSTEM` anpassen.

**Danach:** Builder-Prompt (Funktion-Wahl) + Reviewer (Semantik).

**Dann:** RERUN mit neuer Aufgabe (z. B. Timeline-Sortierung).

---

## HARD-RULES

1. **Messen, nicht raten.** Keine Fixes ohne Grep-/Test-Beleg.
2. **Ein Block, warten auf Paste.** Kein Vorpreschen.
3. **Backup vor `cat >`.** `/root/backups/werkstatt/` oder
   `/root/backups/security-ai/`.
4. **`python3`, nicht `python`.**
5. **Kein `systemctl stop <timer>`.**
6. **Kein `grep`/`tee` um interaktive Prozesse** (TTY-Problem).
7. **`git status --short` vor Commit.**
8. **Heredoc in Bash: nur <30 Zeilen.** Sonst Python-Heredoc oder
   stueckweise.
9. **Kein Aider-Mix.** `old_string`/`new_string` — nicht
   `context+old+new`.
10. **`_format_code_index_for_prompt` ist tot** — nur
    `_format_api_index_for_prompt` nutzen.
11. **`PLANNER_SYSTEM` ist tot** (Z. 34) — nicht reaktivieren.
12. **`_section_timeline` (Z. 226) ist alte Funktion** — nicht fuer
    `dashboard_state` nutzen. `_section_timeline_entries` (Z. 295) ist
    die richtige.
13. **Kein String-Patching an System-Prompts.** Wrapper-Funktionen
    nutzen (`_architect_system_with_builder`,
    `_scout_system_with_nachfolger`).

---

## WICHTIGE PFADE

- Code: `/opt/werkstatt/werkstatt/*.py`
- Tests: `/opt/werkstatt/tests/`
- Hooks: `/opt/werkstatt/hooks/*.py`
- PhaseState: `/opt/security-ai/.werkstatt/security-ai.phase.yaml`
- Audit: `/opt/werkstatt/audit-logs/agent-pipeline-YYYY-MM-DD.jsonl`
- Zielprojekt: `/opt/security-ai/`
- Logs: `/tmp/rerun_*.log`
- Backups: `/root/backups/{security-ai,werkstatt}/`

---

## BEWAEHRTE RERUN-INVOCATION

```bash
cd /opt/werkstatt

LOG="/tmp/rerun_$(date +%Y%m%d-%H%M%S).log"

script -q -e -c "su -s /bin/bash security-ai -c 'cd /opt/werkstatt && PYTHONUNBUFFERED=1 WERKSTATT_RENDER=live WERKSTATT_ARCHITECT_MODEL=deepseek-reasoner exec timeout 2400 python3 -m werkstatt.loop --fresh --project security-ai --aufgabe \"<AUFGABE>\"'" "$LOG"
```
