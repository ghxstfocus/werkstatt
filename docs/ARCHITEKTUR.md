# Architektur — Werkstatt

Stand: 2026-10-24 (nach M-360, RERUN-38).
Technische Architektur des aktuellen Loops.
Zielbild: `NEUBAU-ZIELBILD.md`. Roadmap: `ROADMAP.md`.
Historische Architektur (6 Rollen, W-Bloecke): siehe
Abschnitt "Archiv" am Ende.

## 1. Ziel-Architektur

Die Werkstatt ist ein Multi-Agent-System mit
**fuenf Rollen** und **zwei deterministischen Hooks**.
Der Mensch ist das letzte Gate.

    +--------------------------------------------------+
    |                     MENSCH                       |
    |              (Plan-Gate, Human-Gate)             |
    +--------------------------------------------------+
                          |  ^
                          v  |
    +--------------------------------------------------+
    |                     WERKSTATT                    |
    |                                                  |
    |   Explorer ----> Planner ----> Builder           |
    |    (read)         (JSON)        (search/replace) |
    |                                     |            |
    |                                     v            |
    |                            Verify (verify.json)  |
    |                                     |            |
    |                                     v            |
    |                              Reviewer            |
    |                              (Bug-Check)         |
    |                                     |            |
    |                                     v            |
    |                              Human-Gate          |
    |                              (fail-closed)       |
    +--------------------------------------------------+
                          |
                          v
                   Ziel-Projekt (security-ai)

**Deterministische Gates:**
- `pre_tool_use`-Hook (AST-Import-Validierung)
- `simplify`-Hook (Komplexitaets-Check)

## 2. Rollen (5)

| Rolle | Modell | Aufgabe | Datei |
|---|---|---|---|
| Explorer | deepseek-chat | Read-only Kontext, `key_files` | `werkstatt/explorer.py` |
| Planner | deepseek-chat | JSON-Plan (tasks, tests, akzeptanzkriterien, phasen) | `werkstatt/planner.py` |
| Builder | deepseek-chat | search/replace-Patches (`old_string` -> `new_string`) | `werkstatt/builder.py` |
| Reviewer | deepseek-reasoner | Bug-Check, pytest ist letztes Wort (M-343c) | `werkstatt/reviewer.py` |
| Human-Gate | no-LLM | fail-closed, Diff-Anzeige, Plan-Gate + Human-Gate | `_human_gate` in `loop.py` |

## 3. Hooks (2)

Deterministische Gates, die unabhaengig vom LLM pruefen:

1. **`pre_tool_use`** (`hooks/pre_tool_use.py`, M-334a)
   AST-basierte Import-Validierung. Prueft `import X` /
   `from X import Y` gegen die tatsaechlichen Projekt-Module.
   Blockiert halluzinierte Imports, bevor der Patch angewendet
   wird. Deterministisch, kein LLM-Call.

2. **`simplify`** (`hooks/simplify.py`)
   Komplexitaets-Check auf dem Diff. Blockiert uebergrosse
   Patches, bevor sie das Zielprojekt erreichen.

## 4. Loop-Ablauf

Pro Task:

1. **Explorer** — `key_files` aus der Aufgabe.
2. **Planner** — JSON-Plan mit Phasen (M-323c: Pflicht bei
   >5 Tasks, >2 Dateien oder Keywords).
3. **Plan-Human-Gate** — Plan anzeigen, j/n/a (M-348).
4. Pro Task:
   - **Builder** — search/replace. Zieldatei deterministisch
     aus `task_files` (M-337, M-360).
   - **PreToolUse-Hook** — Import-Validierung.
   - **Simplify-Hook** — Komplexitaet.
   - **Verify** — `verify.json`-Stages (`py_compile_changed`,
     `pytest_changed`, `py_compile_core`, `pytest_full_checks`).
   - **Reviewer** — Bug-Check. pytest ist das letzte Wort
     (M-343c, M-359).
5. **Phase-End Verify** — Vollsuite.
6. **Human-Gate** — Diff anzeigen, j/n/e. Fail-closed.
7. **Rollback** — bei `LOOP_RC != 0` auf `start-HEAD`
   (M-356).

## 5. Verify (verify.json)

Vier Stages, in `.werkstatt/verify.json` des Zielprojekts:

| Stage | Befehl | Phase |
|---|---|---|
| `py_compile_changed` | `py_compile {changed_py_files}` | post_build |
| `pytest_changed` | `pytest {changed_test_files} -q` | post_build |
| `py_compile_core` | `py_compile core/...` | phase_end |
| `pytest_full_checks` | `pytest tests/unit/test_checks.py -q` | phase_end |

**Wichtig:** `py_compile` nur fuer `.py` (M-340). Platzhalter
werden aus dem Diff gefuellt (M-322).

## 6. Was die Werkstatt gut macht

- **Klare Rollen-Trennung:** Explorer liest, Planner plant,
  Builder schreibt, Reviewer prueft, Mensch entscheidet.
- **Deterministische Hooks:** Import-Validierung und
  Komplexitaets-Check sind LLM-unabhaengig.
- **Fail-closed:** Human-Gate, Rollback (M-356), Reviewer
  entscheidet per pytest (M-343c).
- **Audit-Log:** Jede Entscheidung ist im JSONL (`audit()`).
- **Rollback:** immer auf `start-HEAD` bei Fehler (M-356).
- **Idempotenz:** nur bei `action="create"` und existierender
  Zieldatei (M-352).

## 7. Methodische Luecken (bewusst dokumentiert)

Die folgenden Methode sind in der Werkstatt **teilweise** oder
**nicht** umgesetzt. Sie sind Kandidaten fuer kuenftige Bloecke,
nicht fuer den aktuellen.

### 7.1 Read-Before-Write-Protokoll (Tool-Use-Contract)

Ein Read-Before-Write-Protokoll erzwingt, dass ein Agent eine
Datei liest, bevor er sie aendert. Die Werkstatt hat das nicht.
Der Builder kann patchen, ohne den aktuellen Inhalt zu messen.
**Folge:** In fruehen Phasen wiederholte Anker-Fehler,
Deadlock mit dem Solver, leere Reviewer-Antworten.

**Kandidat:** M-365 (Read-Before-Write im Builder).

### 7.2 Optimistic-Concurrency (Stale-Read-Detection)

Optimistic-Concurrency prueft per `mtime`, ob eine Datei seit
dem letzten Lesen veraendert wurde. Die Werkstatt hat das nicht.

**Kandidat:** M-366 (mtime-Check in `apply_code_patches`).

### 7.3 Verify-Before-Commit (Pre-Merge-Gate)

Verify-Before-Commit verifiziert Aenderungen (Tests, Linter,
Self-Review) **vor** dem Commit. Die Werkstatt hat das
teilweise: `_verify_patches` prueft Tests, aber der Builder
sieht das Ergebnis nicht und korrigiert nicht.

**Kandidat:** M-367 (Builder-Feedback-Loop).

### 7.4 Agent-Handoff (Escalation-Pattern)

Agent-Handoff gibt bei Deadlock an eine hoehere Rolle ab.
Die Werkstatt hat das teilweise: Reflection-Loop bei
`old_string_not_found` und Reviewer-Reject. Aber die
Reflection nutzt denselben Builder-Prompt — sie kann
strukturelle Fehler nicht beheben.

**Kandidat:** M-368 (Reviewer-als-Reflection).

### 7.5 Dynamic Dispatch (Router-Pattern)

Dynamic Dispatch routet Aufgaben dynamisch zwischen Agenten.
Die Werkstatt hat statische Rollen. Kein dynamisches Routing.

**Kandidat:** M-369 (Router-Pattern fuer Task-Typen).

### 7.6 Context-Window-Management (Prompt-Budgeting)

Context-Window-Management budgetiert den Prompt anhand der
Modell-Grenzen. Die Werkstatt hat das nicht — der Builder-Prompt
kann zu gross werden.

**Kandidat:** M-370 (Prompt-Budget im Builder).

## 8. Was funktioniert (verifiziert RERUN-38)

- **Loop laeuft Ende-zu-Ende:** 8/8 Tasks, `LOOP_RC=0`.
- **Echte Aenderung im Zielprojekt:** `harness/audit/writer.py`
  (+23, Owner-Check im AuditWriter), committed `2a0a284`.
- **Rollen + Hooks greifen:** Explorer (0 files, kosmetisch),
  Planner (8 Tasks, 5 Phasen), Builder (search/replace),
  Verify (53 Tests gruen), Reviewer (pytest entscheidet),
  Human-Gate (approved).
- **Rollback funktioniert:** RERUN-36/37 — `rc=1` -> Tree clean.

## 9. Was noch fehlt (operativ)

- **M-361:** Test fuer M-355b.
- **M-362:** Test fuer M-360.
- **M-363:** Doku-Pflege Baseline/HISTORISCH.
- **M-323b:** Phasen-Checkpoints (`phase_end` pro Phase).
- **M-341:** Explorer ueberspringen bei `task_files`.
- **M-344:** `PROGRESS.md` mit Phasen-Header.
- **M-345..M-347:** Pipeline-Abbau + CLI.

## 10. Archiv (historisch, nicht mehr aktuell)

**Vor dem Loop-Neubau** (bis Commit `a4c487d`, 2026-10-24)
hatte die Werkstatt **sechs Rollen** mit einem anderen
Ablauf:

| Rolle | Modell | Aufgabe |
|---|---|---|
| planner | deepseek-chat | Auftrag oder Phasenplan |
| builder | deepseek-chat | Code-Patches |
| solver | deepseek-chat | Diagnose bei Deadlock |
| judge | deepseek-reasoner | Contract-Treue, Sicherheit |
| reviewer | deepseek-reasoner | Commit-Paket |
| test_generator | deepseek-chat | Test-Vorschlaege |

Der **Solver** und der **Judge** existieren im Loop-Neubau
**nicht mehr**. Ihre Aufgaben sind teilweise in den Reviewer
und die Reflection verschoben.

Die **W-Block-Serien** (W1..W62) beschreiben die
Vor-Umbau-Phasen und sind in `ERLEDIGT.md` archiviert.
Sie sind **nicht** Teil der aktuellen Roadmap.

### Warum der Umbau?

Die alte Architektur hatte strukturelle Deadlocks (Phase 20b):
Solver-Fehldiagnose, leere Reviewer-Antworten, Builder ohne
Read-vor-Edit. Der Umbau (Strangler-Fig, M-322..M-360) hat
die Rollen auf 5 reduziert, Hooks deterministisch gemacht,
und die Idempotenz/Rollback-Semantik gehaertet.
