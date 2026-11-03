# Status — Werkstatt

Format aus `DOC_CONVENTIONS.md` §5. Nur offene, **loop-faehige** OPs.
`—` in Feldern = noch nicht spezifiziert (Loop praezisiert bei Bearbeitung).
Letzte Aktualisierung: 2026-11-03.

Roadmap-Phasen (M-NNN, nicht loop-faehig) stehen seit 2026-11-03 in
`docs/ROADMAP.md`, Abschnitt "Aus STATUS.md (Loop-Queue)".


## Offene Punkte

### OP-070: Scout-Redundanz messen vor Umbau
- **Status:** open
- **Betroffene Dateien:** `werkstatt/scout.py`, `werkstatt/planner.py` (`_run_scout`, `_baue_api_index`)
- **Akzeptanzkriterien:** Auswertung der letzten 10 Loop-Läufe: (a) Wie oft setzt `_run_scout` `bereits_erfuellt == True`? (b) Wie oft liefert `_pruefe_api_widerspruch` einen Befund, den der Architect ohne Scout-Auszug nicht gefunden hätte? (c) Wie oft weicht `api_auszug` von einem reinen Token-Match ab? Entscheidung: Scout-LLM behalten (Wahrscheinlichkeit hoch nach Rollen-Analyse) oder deterministisch ersetzen. Kein Umbau vor Messung.
- **Tests:** Keine — Mess-Aufgabe.
- **Blockiert von:** —

### Notiz 2026-11-02: `explorer_result` fehlt in aktuellen Logs

- **Beobachtung:** `audit("explorer_result", ...)` existiert in
  `werkstatt/explorer.py`. In Logs vom 23.-25.10. taucht er auf (10-58x),
  in Logs ab 26.10. **nicht mehr**. Stattdessen gibt es heute 15x
  `explorer_messung_findings`.
- **Verdacht:** Der Event wurde bei einer Explorer-Refactor-Welle
  umbenannt oder der Pfad, der ihn schreibt, wird nicht mehr erreicht.
- **Konsequenz:** `explorer_context` (den der Scout fuer Datei-Previews
  braucht) ist moeglicherweise leer -> Scout-Redundanz-Analyse (OP-070)
  hat keine Basis.
- **Naechster Schritt:** Pruefen ob `explorer_result` noch erreicht wird;
  falls nicht, Event wieder aktivieren oder durch `explorer_messung_findings`
  ersetzen (semantisch gleich?). Kein sofortiger Fix.


### OP-073: Werkzeug fuer Roadmap-to-OP Compiler

- **Status:** open
- **Beschreibung:** Baut das Werkzeug `werkstatt/roadmap_compiler.py`, das wie in Phase 31
  beschrieben, die naechste ROADMAP-Phase liest und automatisch in STATUS.md-OPs uebersetzt.
- **Betroffene Dateien:** `werkstatt/roadmap_compiler.py` (neu), `tests/test_roadmap_compiler.py` (neu)
- **Akzeptanzkriterien:** CLI-Tool, das den Architect aufruft, die Ausgabe validiert
  (OP-NNN, Akzeptanzkriterien vorhanden) und die OPs formatiert in STATUS.md einfuegt.
- **Tests:** Unit-Tests fuer die Validierungs-Logik und den Parser der Roadmap.
- **Blockiert von:** —





### OP-086: Doku-Drift als Verify-Gate (deterministisch)

- **Status:** open
- **Beschreibung:** `tools/doku_check.py` ist gebaut, aber noch nicht
  im Loop-Gate. Commits mit Subject `feat/fix/chore/...` und Code-
  Aenderung ohne Doku-Aenderung sollen als eigene verify-Stage laufen.
  Wenn Verdacht: Gate rot, Commit blockiert. Ausnahmen (docs(, test(,
  ci(, [skip-doku]) bereits implementiert.

  Ziel: Doku-Pflege ist strukturell erzwungen, nicht Erinnerung des
  Menschen. Begruendung: der Loop liest seine Queue aus docs/STATUS.md.
  Wenn dort stale OPs stehen (Beispiel 2026-11-03: Chat-Agent
  empfahl OP-084/085, obwohl beide bereits durch 82502f0..98a53d3
  erledigt waren), arbeitet der Loop gegen Phantom-Eintraege.
- **Betroffene Dateien:** `.werkstatt/verify.json` (neue Stage
  `doku_drift`), `tools/doku_check.py` (nutzen), `tests/test_doku_check.py`
  (neu), `AGENTS.md` (Pflicht-Befehl dokumentieren)
- **Akzeptanzkriterien:** (a) `verify.json` enthaelt Stage
  `doku_drift` mit Command `python3 tools/doku_check.py --strict
  --limit 5`. (b) Stage ist `hart=True`, blockiert Commit. (c) Tests
  `tests/test_doku_check.py` mit 4 Szenarien: Verdacht erkannt,
  Doku-Aenderung da, `[skip-doku]` greift, `docs(`-Scope greift.
  (d) `python3 tools/doku_check.py --strict` im Repo aktuell
  exit 0 (kein Verdacht in letzten 5 Commits) — sonst Commit
  sowieso blockiert.
- **Tests:** `pytest tests/test_doku_check.py -v`
- **Blockiert von:** —




### OP-092: Loop-Agenten mit explizitem Kontext-Vertrag (Sammel-OP)

- **Status:** open
- **Typ:** architektur (Sammel-OP, 5 Sub-OPs)
- **Betroffen:** `werkstatt/context_builder.py` (neu), `werkstatt/test_agent.py` (neu),
  `werkstatt/debugger.py` (neu), `werkstatt/pipeline_phases.py`, `werkstatt/loop.py`,
  `docs/ARCHITECTURE.md`
- **Problem:** Builder/Test-Agent/Debugger raten heute. OP-047: Builder schrieb
  Test mit falschem Trigger (`nur docs/A.md` = single-target statt multi-file).
  OP-089: Builder rief `_deterministische_diagnose` auf, die es nicht gibt.
  Beide Fehler wären durch deterministischen Kontext verhindert worden.
- **Kernidee:** Jeder Agent bekommt VOR seinem LLM-Aufruf einen
  deterministisch gefüllten Kontext-Vertrag mit vier Feldern:
  1. **Ziel** — Akzeptanzkriterien aus OP-Text (nicht aus Code)
  2. **Ist-Zustand** — was existiert (Files, Tests, letzter Diff, vorherige Patches)
  3. **Design-Entscheidung** — ARCHITECTURE-Auszug, MERKPOSTEN, Commit-History
  4. **Deterministische Fakten** — `inspect.signature()` der echten API,
     `dir()` der Module, verfügbare pytest-Marker, Import-Pfade

- **Sub-OPs:**
  - **092a** `werkstatt/context_builder.py` (neu): Funktion
    `build_agent_context(role, task, state) -> dict` mit den 4 Feldern.
    Deterministisch (kein LLM), alle Werte aus `inspect`, `git`, `pytest`,
    `grep`. Max 500ms pro Aufruf.
  - **092b** Builder-Scope: `role=builder` schreibt KEINE Tests mehr
    (`*_test.py` aus Scope). Context-Builder liefert
    `design.architecture_auszug` + `deterministische_fakten.signaturen`.
  - **092c** Test-Agent (`test_agent.py`): liest Ziel aus OP + Code-Ist,
    schreibt `tests/test_*.py`. Darf nur Code lesen, nicht selbst pytest
    ausführen (pytest ist deterministisch danach).
  - **092d** Debugger (`debugger.py`, siehe eigener Abschnitt unten)
  - **092e** Reflection-Loop aus `pipeline_phases.py` raus, in `loop.py`
    als Orchestrator. Max 2 Runden, Human-Gate bei Runde 2.

- **092d Debugger — Rollenbeschreibung:**
  - **Rolle:** Professioneller Root-Cause-Analyst, kein Test-Satisfier.
  - **Kernprinzip:** Erst Code prüfen, dann Test. Nie Test an faulen Code anpassen.
  - **Ablauf:**
    1. **Code-Health (deterministisch):** ruff, mypy, py_compile, Signatur-Check.
       Fehler → Code fixen, Runde+1. Kein LLM nötig.
    2. **3-Wege-Check (LLM mit Kontext-Vertrag):** Spec (aus OP-Text) ←→ Code ←→ Test.
       - Code ≠ Spec, Test = Spec → **Fix Code** (Test hatte recht)
       - Code = Spec, Test ≠ Spec → **Human-Gate** (Test falsch, nicht still patchen)
       - Code ≠ Spec, Test ≠ Spec → **Human-Gate** (fundamentale Misalignment)
       - Alle = Spec, Test rot → **Human-Gate** (Infra/flaky/env)
    3. **Verifikation:** Original-Test + Regression-Suite + ruff/mypy.
    4. **Max 3 Runden.** Runde 3 ohne Grün → Human-Gate mit kompletter Historie.
  - **System-Verständnis (Profi-Level):** Import-Graph, Call-Graph,
    Design-History (ARCHITECTURE, MERKPOSTEN zu ähnlichen Bugs),
    Git-History (letzte 5 Commits an betroffenen Files),
    Signatures aller aufgerufenen Funktionen, Konventionen (pytest.ini).
  - **Test-File-Guard:** `_ist_testdatei(pfad)` prüft `*_test.py` / `test_*.py`.
    Debugger-Patch auf Test-Datei nur erlaubt wenn (a) nur syntaktisch
    kaputt (SyntaxError), nicht semantisch; (b) Human-Gate-Freigabe.
    Sonst `debugger_test_patch_blocked`-Audit + Eskalation.
  - **API:** `debug(state, failing_test, spec) -> DebugResult`
    mit `patches: list[dict]`, `escalation: str | None`, `runden: int`,
    `diagnose: {code_ok, test_ok, spec_klar, ursache: "code|test|spec|infra"}`

- **Akzeptanzkriterien:**
  - **092a:** `tests/test_context_builder.py` mit 3 Szenarien
    (leerer State, existierende Files, fehlende API)
  - **092b:** Builder darf `task_files` mit `*_test.py` nicht mehr
    akzeptieren → `builder_scope_violation`-Audit-Event
  - **092c:** Test-Agent-Tests: (a) leerer Code → leerer Test,
    (b) Code mit Funktion → Test mit `inspect.signature()`-konformem Aufruf,
    (c) Akzeptanz-Kriterium fehlt → Fail-closed
  - **092d:** `tests/test_debugger.py` mit 6 Szenarien:
    (a) Code-Bug → Code-Patch, Test unverändert, grün
    (b) Test-Bug → Eskalation, kein Test-Patch
    (c) Spec unklar → Eskalation
    (d) Code + Test = Spec, Test rot → Log + Eskalation
    (e) Debugger versucht Test semantisch zu patchen → Assertion-Error
    (f) Debugger versucht Test-Syntax zu patchen → erlaubt, Audit-Event
  - **092e:** Reflection-Runden max 2, Human-Gate bei Runde 2 auch ohne
    `Approve?`-Prompt

- **Tests:** `tests/test_context_builder.py` (neu), `tests/test_test_agent.py`
  (neu), `tests/test_debugger.py` (neu), `tests/test_pipeline_phases.py` (erweitern)

- **Blockiert von:** OP-089 (Reflection-Bug), OP-090 (Human-Gate-Skip)
- **Hinweis:** Struktureller Fix für die Klasse OP-047 / OP-089. Nach 092a-e
  hat der Agent deterministischen Kontext und rät nicht mehr.


### OP-100: Phase 33.2b — verify-Migration nach control/ (gross)

- **Status:** open
- **Typ:** architektur-refactor (Multi-Session)
- **Betroffen:** `werkstatt/verify.py` (620 Zeilen), `werkstatt/loop.py`
  (Re-Export), 5 `_verify_patches`-Proxies, **163 Test-Patch-Calls**
- **Problem:** `_verify_patches` existiert 5x als Proxy, echte Impl in
  verify.py:341. Aber: `verify.py` importiert `loop.py` (via audit-Proxy),
  `loop.py` re-exportiert `verify`, alle Tests patchen
  `werkstatt.loop._verify_patches` (21x) und `werkstatt.verify._verify_patches`
  (22x) und 4 weitere Formen. Ein mechanischer Move bricht 163 Test-Pfade.
- **Scope (Stufenplan):**
  - 100a: Late-Binding `audit`-Proxy in verify.py aufloesen (Kern der
    Zirkularitaet, ~93 Test-Pfade auf `audit`). Vermutlich via
    `state.audit`-Callable oder direkter `from werkstatt.audit import audit`.
  - 100b: `verify.py` nach `control/verify.py`, `werkstatt/verify.py`
    als Deprecation-Proxy.
  - 100c: `loop.py`-Re-Export entfernen, Aufrufer direkt auf
    `control.verify` umstellen.
  - 100d: 5 Proxies in gates/reflection/pipeline_phases/task_runner
    entfernen.
  - 100e: 163 Test-Patch-Calls migrieren (separater Sub-OP, pro Datei).
- **Akzeptanzkriterien:** Nach 100a-e: `_verify_patches` existiert genau
  1x (in `control/verify.py`). `control_drift --check` gruen. `pytest`
  gruen. Keine Deprecation-Warnungen mehr.
- **Tests:** `pytest -q --ignore=tests/test_shell.py` + 163 Patch-Migrationen.
- **Blockiert von:** OP-095 (hart-Feld zuerst), OP-100a-e in Reihenfolge.
- **Anmerkung:** Discovery 2026-11-03: 163 Patch-Calls (45x _verify_patches,
  93x audit, 10x _plan_gate, 15x sonst). Nicht an einem Tag machbar.

## Erledigt (Auto-Log)

- 2026-11-02 | OP-076 | done | Chat-Fenster (f0e6d50)
- 2026-11-02 | OP-077 | done | Audit-Panel (92b3b69)
- 2026-11-02 | OP-078 | done | UI-Layout (0f916f9..e75bc7d)
- 2026-10-30 | OP-071 | `c1e8377`: revertiert
- 2026-11-02 | OP-003 | wontfix (security-ai-Drift)
- 2026-11-02 | OP-030 | wontfix (Duplikat zu OP-074)
- 2026-11-02 | OP-031 | wontfix (Duplikat zu OP-075)
- 2026-11-02 | OP-032 | wontfix (Duplikat zu OP-076)
- 2026-11-02 | OP-033 | wontfix (Duplikat zu OP-078)
- 2026-11-02 | OP-039 | wontfix (security-ai)
- 2026-11-02 | OP-041 | wontfix (security-ai)
- 2026-11-02 | OP-066 | done | Reviewer prueft Zwischenstand (bereits implementiert)
- 2026-11-02 | OP-065 | wontfix | Phase-2-Kette (Modell-Latenz, nicht Code)
- 2026-11-02 | OP-026 | wontfix | R-CHECK-1 Prompt-Block ist Skill
- 2026-11-02 | OP-067 | done | pytest_changed feuert in Reflection (69889b7)
- 2026-11-02 | OP-072 | done | UI-Phase 30 in OPs zerlegt (88ab237)
- 2026-11-02 | OP-074 | done | FastAPI-Backend (624fb5e + c82f537)
- 2026-11-02 | OP-075 | done | Terminal-Proxy (b8dce51)
- 2026-11-02 | OP-079 | done | review-work-Skill: Markdown-Hunk-Header (d023535)
- 2026-11-02 | OP-080 | done | review-work-Skill: Python-PATCHES (3d7fd1f)

## Delete-Zone

Nach Delete-Zone-Muster: erledigte OPs werden hier protokolliert.

- 2026-11-03 | OP-104 | done | control/reflection.py wortgleiche Kopie (manuell, Scout-Plan-Bug)
- 2026-11-03 | OP-099 | done | Phase 33.6: control_drift als Post-Build-Stage hart (67cd6b0)
- 2026-11-03 | OP-088 | done | explorer_result in beiden Zweigen (Mess+LLM), audit.py-Katalog (4b6058f)
- 2026-11-03 | OP-091 | done | audit_panel: _home_kontext Modulebene (Diagnose korrigiert: Writer OK, Reader crasht) (4a10645)
- 2026-11-03 | OP-095 | done | Phase 33.2a: verify.json hart-Feld explizit + fail-loud (1ac3446)
- 2026-11-03 | OP-089 | done | Reflection-Circuit-Breaker + Katalog-Drift (c00ef17)
- 2026-11-03 | OP-093 | done | Plan-Gate Fail-closed bei ungültiger Antwort (d0f871a)
- 2026-11-03 | OP-090 | done | Human-Gate bei Reflection-Erschöpfung (47b6e07)
- 2026-11-03 | OP-047 | done | `_doku_post_check` gruppiert pro Datei (bb719b1)
- 2026-11-02 | OP-035 | Doku-Task-Datum wird halluziniert — deterministisch geloest (BUILDER_SYSTEM + {date}-Ersetzung + _korrigiere_doku_datum Sicherheitsnetz)
- 2026-11-02 | OP-068 | Heartbeat-Stage-Name (Builder/Reviewer) — Commit 2c099da
- 2026-11-02 | OP-069 | Delete-Zone-Sektion anlegen — Commit 6fa1d74 + Fix ebe8049
- 2026-11-03 | OP-045 | docs/WORKFLOW.md geloescht (nicht mehr gepflegt, nicht in DOC_CONVENTIONS §2 Pflicht)- 2026-11-03 | OP-008 | obsolete (pipeline.py geloescht) — Commit 07a4de6
- 2026-11-03 | OP-009 | obsolete (python3 -m werkstatt.loop funktioniert (CLI seit Monaten aktiv)) — Commit n/a


### OP-096: Phase 33.3 — gates.py nach control/ migrieren

- **Status:** open
- **Typ:** architektur
- **Betroffen:** `werkstatt/gates.py` nach `werkstatt/control/gates.py`
- **Problem:** 16 Funktionen in gates.py, davon 6 echte Gates.
  13 Aufrufe in pipeline_phases.py.
- **Akzeptanzkriterien:** `control/gates.py` mit plan_gate,
  human_gate_plan, human_gate, human_gate_body. Deprecation-Proxy.
  Aufrufer migriert. `tests/test_gates.py` gruen.
- **Blockiert von:** OP-095

### OP-097: Phase 33.4 — reflection.py nach control/ migrieren

- **Status:** open
- **Typ:** architektur
- **Betroffen:** `werkstatt/reflection.py` nach `werkstatt/control/reflection.py`
- **Problem:** 7 Aufrufer von `_reflection_loop`, 1 von
  `_plan_reject_reflection`. 12 Funktionen.
- **Akzeptanzkriterien:** `control/reflection.py` mit 3 Einstiegspunkten.
  Deprecation-Proxy. Aufrufer migriert. `tests/test_reflection*.py` gruen.
- **Blockiert von:** OP-095, OP-096

### OP-098: Phase 33.5 — pipeline_phases.py reduzieren

- **Status:** open
- **Typ:** architektur (groesster Schritt)
- **Betroffen:** `werkstatt/pipeline_phases.py` (1600+ Zeilen)
- **Problem:** 13 Phase-End-Hooks, 3 Pre-Build, 5 Post-Build direkt
  im Monolithen. Nach 33.2-33.4 sollte diese Datei nur noch
  `run_phase(Phase.X, state)` aufrufen.
- **Akzeptanzkriterien:** pipeline_phases.py unter 400 Zeilen. Jede
  Phase ruft `run_phase`. Keine direkten `_verify_patches`-Aufrufe.
  Voller Loop-Durchlauf funktioniert.
- **Blockiert von:** OP-095, OP-096, OP-097


### OP-101: Loop-Status-Inkonsistenz bei human_review-Tasks

- **Status:** open
- **Typ:** ux-bugfix
- **Betroffen:** `werkstatt/pipeline_phases.py` (`_phase_tasks_loop`),
  `werkstatt/task_runner.py` (`_task_ende`)
- **Problem:** Wenn ein Task `human_review` ist (z.B. `spec_widerspruch_vermutet`)
  und der User am Human-Gate `j` drückt (approve + commit), werden die
  Änderungen committet — aber der Loop zählt den Task weiterhin als
  `failed`. Beim OP-088-Lauf 2026-11-03 19:23: Commit `4b6058f` enthält
  alle 3 Dateien (`explorer.py`, `audit.py`, `test_loop_explorer.py`),
  aber der Loop meldet `1/3 Tasks · 2 failed` und `✗ LOOP FEHLGESCHLAGEN`.
- **Akzeptanzkriterien:** (a) Wenn User am Human-Gate `j` drückt, alle
  offenen `human_review`-Tasks auf `ok` setzen (nicht `failed`).
  (b) `LOOP ERFOLGREICH` wenn Commit durch, auch wenn Tasks als
  `human_review` markiert waren. (c) Test: `_phase_tasks_loop` mit
  2 human_review-Tasks, Gate liefert `j` → `tasks_ok == total`.
- **Tests:** `tests/test_pipeline_phases.py` (neu).
- **Blockiert von:** -


### OP-105: reflection.py → Deprecation-Proxy

- **Status:** open
- **Typ:** architektur (sub-OP, 1 Datei)
- **Betroffen:** nur `werkstatt/reflection.py`
- **Auftrag:** Ersetze `reflection.py` durch Proxy via `__getattr__`.
  Setzt OP-104 voraus (`control/reflection.py` vollständig).
- **Akzeptanz:** `from werkstatt.reflection import _reflection_loop`
  funktioniert. `python3 -c "from werkstatt.control.reflection import _reflection_loop"` funktioniert.
- **Blockiert von:** OP-104

### OP-106: Aufrufer auf control.reflection umstellen

- **Status:** open
- **Typ:** architektur (sub-OP, 3 Dateien)
- **Betroffen:** `werkstatt/loop.py`, `werkstatt/pipeline_phases.py`,
  `werkstatt/task_runner.py` (nur Import-Zeilen)
- **Auftrag:** Alle `from werkstatt.reflection import X` auf
  `from werkstatt.control.reflection import X` umstellen. Keine Logik-Änderung.
- **Akzeptanz:** grep findet keine `from werkstatt.reflection import` mehr
  (außer in `control/reflection.py`-Docstring + Tests).
- **Blockiert von:** OP-104, OP-105

### OP-107: Test-Patch-Pfade migrieren

- **Status:** open
- **Typ:** architektur (sub-OP, mehrere Tests)
- **Betroffen:** `tests/test_reflection*.py`, `tests/test_loop*.py`
- **Auftrag:** `mock.patch("werkstatt.reflection.X")` → `mock.patch("werkstatt.control.reflection.X")`.
- **Blockiert von:** OP-106
