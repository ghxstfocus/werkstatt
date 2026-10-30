# Bau-Handoff — Stand 2026-10-30

**Loop-Neubau abgeschlossen.** `pipeline.py` (11.119 Z.) und die
alte Test-Suite sind entfernt. Neue Suite: **432 passed, 5 skipped**.
Der Loop laeuft ausschliesslich ueber `werkstatt/*.py`.

Alter Handoff: `Bau-Handoff-Archiv.md` (Stand 2026-10-29 + Loop-Neubau).

---

## STAND

**Werkstatt** (`/opt/werkstatt`):
- Branch `umbau/phase-2`, `voraus 32` ungepusht.
- Suite: **432 passed, 5 skipped** (60 Test-Dateien).
- Ruff Baseline (gesamt): **13 Errors** ueber alle `werkstatt/*.py`.
  Hauptverteilung: loop.py 7, planner.py 1, builder.py 2, Rest
  in agent.py, apply.py, audit.py, commit_input.py, measurement.py,
  prompts.py, verify.py.

**Zielprojekt** (`/opt/security-ai`):
- Services active, `.env` vollstaendig.
- Timeline funktioniert (15 Eintraege, klickbar, mit Score).
- Letzter RERUN 19:10 (2026-10-29): 3/3 Tasks approved.

---

## LOOP-NEUBAU (2026-10-30, abgeschlossen)

### Was entfernt wurde

- `pipeline.py` (11.119 Z.) — Monolith, produktiv tot.
- Test-Suite: `test_pipeline.py` (11.377), `test_pipeline_integration.py`
  (1.958), `test_phase.py` (2.637), `test_planner.py` (649),
  `test_anti_patterns.py` (549), `test_hooks_anti_patterns.py` (58),
  `test_audit_kinds.py` (268), `test_projekt_schema.py` (227).
- Anti-Pattern-System: `hooks/anti_patterns.py`, `anti-patterns/`
  (Katalog + README), `agent.py:_anti_pattern_block`,
  `audit.py:_ap_audit_haeufigkeit`, `audit.anti_patterns_injiziert`,
  `conftest.py:ap_block_inprocess`-Fixture.

### Commits 2026-10-30

- `513ab55` — `build_system_prompt` ohne `mit_anti_patterns`-Parameter.
- `a9abe5b` — 2 `mit_anti_patterns`-Tests entfernt.
- `0bcc732` — 5 Test-Dateien + Anti-Pattern-Hook + Katalog entfernt (17.473 Z.).
- `f163f33` — `patch(pipeline.*)`-Aufrufe entfernt (wirkungslos).
- `07a4de6` — `pipeline.py` + 3 Tests + Anti-Pattern-Code (12.401 Z.).
- `def4f8d` — Loop-Neubau 2026-10-30 dokumentiert.

### Neue Baseline

| Aspekt | Wert |
|---|---|
| Tests | 432 passed, 5 skipped |
| Test-Dateien | 60 |
| `werkstatt/*.py` | 25 Module |
| Ruff gesamt | 13 Errors |

---

## WAS FUNKTIONIERT (verifiziert 2026-10-30)

### Gold-Umbau (`2c4703d`)
- **Architect** (`ARCHITECT_SYSTEM`, deepseek-reasoner): freie Prosa
  mit `## <pfad>`-Ueberschriften, Interface + Logik + Integration.
- **Planner** (`_zerlege_in_sub_tasks`, deepseek-chat): zerlegt Prosa
  in Tasks (JSON).
- **Zwei Agents, zwei Calls.** Tool-Use-Loop entfernt.

### Scout-Agent (`_run_scout` + `_baue_api_index`)
- **`_baue_api_index`:** AST-basiert, deterministisch. Liefert pro
  Datei `__all__`, Klassen (Methoden + Signaturen + Rueckgabetypen),
  Top-Level-Funktionen, Imports.
- **`_format_api_index_for_prompt`:** deterministisch, kompakt.
- **`_finde_api`:** deterministisch, sucht API im Index.
- **`_run_scout`** (deepseek-chat): formuliert Auftrag aus API-Index.
- **Widerspruchs-Check:** prueft APIs aus Auftrag gegen Code-Index
  (`read_events` existiert nicht -> `list_recent_assessments`).

### Prompt-Audit (P0-P3, `aa7881f`)
- **`_BUILDER_SCHNITTSTELLE`** an `ARCHITECT_SYSTEM`.
- **`_REVIEWER_SCHNITTSTELLE`** an `BUILDER_SYSTEM`.
- **`ARCHITECT_SYSTEM`:** `GOLD: SCOUT-KONTEXT`.
- **`_SCOUT_NACHFOLGER_BLOCK`:** Scout liefert JSON, Architect Prosa.
- **Toter `PLANNER_SYSTEM`-else-Zweig** entfernt.

### P0/P1 — Builder-Funktion-Wahl + Reviewer-Semantik
- **`_segmentiere_nach_pfad(prosa)`** (`aa7881f`): zerlegt
  Architect-Prosa an `## <pfad>`-Ueberschriften. Fallback in
  `_zerlege_in_sub_tasks` und `_llm_split_einzel_task`, wenn
  `architect_start` fehlt.
- **`## FUNKTION-WAHL`** in `BUILDER_SYSTEM` (`aa7881f`): waehle
  die genannte Funktion, nicht die aehnlichste.
- **`## SEMANTIK-CHECK`** in `REVIEWER_SYSTEM` (`aa7881f`): HIGH-Bug,
  wenn Diff eine andere Funktion nutzt, als die Task nennt.
- **`_filtere_auf_funktionen(abschnitt, task_text)`** (`c13bb8a`):
  schneidet den Architect-Abschnitt auf die Task-Funktionen zu.
- **Live-Beleg 2026-10-29 20:16:** RERUN `1/1 approved` im
  1. Durchlauf, Patch minimal (5 Zeilen).

### Reviewer Diff-Check (P0)
- `REVIEWER_SYSTEM` prueft **jede `-`-Zeile** gegen die Zieldatei.
- **HIGH-Bug** wenn bestehender Aufruf entfernt, Funktion
  ueberschrieben, API erfunden.

### Import-Validierung (`996d616`)
- Klassischer Builder-Pfad prueft Imports
  (`_validate_imports_in_patch`).
- Bei Fehler: Patch verworfen, `builder_patch_import_fehler`.

### M-487 — Human-Gate committet selbst (`31c6ff3`)
- **`_committe_zielprojekt(state)`** in `werkstatt/loop.py`:
  `git status` -> `git add -A` -> `git commit` -> `git rev-parse HEAD`.
- Aufruf im `_human_gate`-`j`-Zweig. Fail-closed: Bei Git-Fehler
  bricht der Loop ab (`✗ LOOP FEHLGESCHLAGEN`).
- **Nur bei explizitem `j`.** Auto-Approve committet nicht.
- **4 Audit-Events:** `loop_human_gate_committed`,
  `loop_human_gate_commit_skip`, `loop_human_gate_commit_fehler`,
  `loop_human_gate_commit_abort`.
- **Betriebs-Voraussetzung:** `.git/` im Zielprojekt muss vom
  Loop-User (`security-ai`, Gruppe `builder`) beschreibbar sein.
- **Live-Beleg 2026-10-29 20:36:** RERUN `4e860c3`, automatischer
  Commit, `✓ LOOP ERFOLGREICH`.

### MESS-1 — Prompt-Laengen + Prompt-Dump (`b3b9511`)
- **`LLMReply`** (state.py) um `system_len: int`, `user_len: int`
  erweitert.
- **`ask_llm`** (agent.py): alle 7 `return`-Pfade fuellen die
  Laengen; `audit("llm_call", {agent, model, system_len, user_len,
  max_tokens})`, wenn `state` gesetzt.
- **Prompt-Dump:** `WERKSTATT_PROMPT_DUMP=1` schreibt die
  wortwoertlichen System- und User-Prompts nach
  `/tmp/werkstatt-prompts/<agent>_<ts>_<suffix>_{system,user,meta}.txt`.

### Timeline (Zielprojekt, `5101e84`)
- **`_section_timeline_entries`** liefert `ts_display`, `href`,
  `score`, `audit_id`.
- **`dashboard_state`** ruft `_section_timeline_entries` (nicht
  `_section_timeline`).
- **`dashboard.js`:** `fetchState` + `renderTimeline` nutzen die
  neuen Felder.
- **Ergebnis:** 15 Eintraege, formatiert, klickbar, mit Score.

---

## ROADMAP (2026-10-31+)

### 1. Loop-Weg-Tests (die neue Test-Suite als Spec)

Jeder Pfad im Gold-Loop braucht einen Test — **nicht** als
Bugfix-Historie, sondern als Spec:

| Test-Datei | Testet |
|---|---|
| `test_loop_explorer.py` | Explorer-Phase, `_extract_dateien`, `_messen` |
| `test_loop_scout.py` | Scout, API-Index, Widerspruchs-Check |
| `test_loop_architect.py` | Architect-Prosa, `## <pfad>`-Ueberschriften |
| `test_loop_planner.py` | Planner-Split, `architect_start`-Fallback |
| `test_loop_builder.py` | Builder, `_filtere_auf_funktionen`, `old_string`/`new_string` |
| `test_loop_reviewer.py` | Reviewer, `## SEMANTIK-CHECK`, HIGH-Bug-Erkennung |
| `test_loop_human_gate.py` | M-487: committet selbst, fail-closed |
| `test_loop_phases.py` | Phasen-Uebergaenge, Reflection, Fail-Closed |
| `test_loop_redaction.py` | **Security:** `redact_all` filtert IPs, Secrets, Keys |

**Prinzip:** Die alten Tests sind Historie, die neuen sind Spec.

### 2. Security-Audit (wenn der Loop produktiv ist)

- **Keine IPs / Secrets / Nutzdaten ans LLM.**
  `redact_all` ist in `ask_llm`, aber niemand testet ihn.
- **UI-Login** — fehlt komplett. Design + Implementierung + Tests.
- **Loop-Wege vollstaendig getestet** — Voraussetzung fuer Security-Audit.

### 3. Push

- `voraus 32` Commits (Werkstatt), `voraus 18` (Zielprojekt).

### 4. Kleinere offene Punkte

- **`R-CHECK-1`** (in `docs/OFFENE-BLOECKE.md`): Reviewer prueft
  Task-Zahlen nicht. Live-Beleg 2026-10-29 20:42: Task verlangt
  `limit=10`, Builder schreibt `limit=5`, Phase-Review approved.
  Fix: `## KONSTANTEN-CHECK` in `REVIEWER_SYSTEM`.
- **Ruff-Baseline abbauen** (13 Errors).
- **`docs/RUNBOOK.md`** fehlt (im alten P3 genannt).

---

## HARD-RULES

1. **Messen, nicht raten.** Keine Fixes ohne Grep-/Test-Beleg.
2. **Ein Block, warten auf Paste.** Kein Vorpreschen.
3. **Backup vor `cat >`.** `/root/backups/werkstatt/`.
4. **`python3`, nicht `python`.**
5. **Kein `systemctl stop <timer>`.**
6. **Kein `grep`/`tee` um interaktive Prozesse** (TTY-Problem).
7. **`git status --short` vor Commit.**
8. **Heredoc in Bash: nur <30 Zeilen.** Sonst Python-Heredoc.
9. **Kein Aider-Mix.** `old_string`/`new_string`.
10. **`_format_code_index_for_prompt` ist tot** — nur
    `_format_api_index_for_prompt` nutzen.
11. **`PLANNER_SYSTEM` ist tot** — nicht reaktivieren. Nur noch
    von 2 Tests geprueft (Deprecation-Kommentar in planner.py).
12. **`_section_timeline` ist alte Funktion** — nicht fuer
    `dashboard_state` nutzen. `_section_timeline_entries` ist richtig.
13. **Kein String-Patching an System-Prompts.** Wrapper-Funktionen
    nutzen (`_architect_system_with_builder`,
    `_scout_system_with_nachfolger`).
14. **`pipeline.py` ist weg.** Jede Referenz auf `pipeline.*` ist
    ein Bug — ausser in `docs/`-Historie und diesem Handoff.
15. **Neue Tests sind Spec, nicht Historie.** Loop-Wege testen,
    nicht Bugfixes dokumentieren.

---

## WICHTIGE PFADE

- Code: `/opt/werkstatt/werkstatt/*.py` (25 Module)
- Tests: `/opt/werkstatt/tests/` (60 Dateien, 432 Tests)
- Hooks: `/opt/werkstatt/hooks/*.py`
- PhaseState: `/opt/security-ai/.werkstatt/security-ai.phase.yaml`
- Audit: `/opt/werkstatt/audit-logs/agent-pipeline-YYYY-MM-DD.jsonl`
- Zielprojekt: `/opt/security-ai/`
- Logs: `/tmp/rerun_*.log`
- Prompt-Dumps: `/tmp/werkstatt-prompts/` (nur bei `WERKSTATT_PROMPT_DUMP=1`)
- Backups: `/root/backups/{security-ai,werkstatt}/`
- Alter Handoff: `/opt/werkstatt/Bau-Handoff-Archiv.md`

---

## BEWAEHRTE RERUN-INVOCATION

```bash
cd /opt/werkstatt

LOG="/tmp/rerun_$(date +%Y%m%d-%H%M%S).log"

script -q -e -c "su -s /bin/bash security-ai -c 'cd /opt/werkstatt && PYTHONUNBUFFERED=1 WERKSTATT_RENDER=live WERKSTATT_ARCHITECT_MODEL=deepseek-reasoner exec timeout 2400 python3 -m werkstatt.loop --fresh --project security-ai --aufgabe \"<AUFGABE>\"'" "$LOG"
```
