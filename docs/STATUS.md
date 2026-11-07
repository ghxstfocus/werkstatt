# Status — Werkstatt

Format aus `DOC_CONVENTIONS.md` §5. Nur offene, **loop-faehige** OPs.
`—` in Feldern = noch nicht spezifiziert (Loop praezisiert bei Bearbeitung).
Letzte Aktualisierung: 2026-11-04.

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

- **Blockiert von:** —
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
- **Blockiert von:** —
- **Anmerkung:** Discovery 2026-11-03: 163 Patch-Calls (45x _verify_patches,
  93x audit, 10x _plan_gate, 15x sonst). Nicht an einem Tag machbar.

### OP-113: Erfahrungs-Gehirn — deterministisches Fehler-Gedaechtnis (Sammel-OP)

- **Status:** open
- **Typ:** architektur (Sammel-OP, 8 Sub-OPs)
- **Betroffen:** `werkstatt/erfahrung.py` (neu), `werkstatt/skills.py`,
  `werkstatt/diagnose.py`, `werkstatt/antipattern.py`,
  `werkstatt/reflection.py`, `werkstatt/reviewer.py`, `docs/MERKPOSTEN.md`
- **Problem:** Erfahrungen aus geloesten Fehlern verpuffen. `diagnose.py`
  erkennt deterministisch 2 Fehlerklassen, schreibt aber nicht zurueck.
  `antipattern.py::scan_patches` findet 6 Anti-Pattern-Klassen, lernt
  aber nicht. `MERKPOSTEN.md` hat ~30 Prozess-Lehren als Absaetze —
  nicht durchsuchbar ausser per grep. `state.geladene_skills` ist eine
  flache Namen-Liste ohne Bezug zu Problem/Loesung. Folge: Loop
  wiederholt Fehler die in `MERKPOSTEN.md` schon geloest sind.
- **Kernidee:** SQLite `.werkstatt/erfahrung.db` mit strukturierten
  Absaetzen (1-3 Saetze pro Eintrag). Retrieval liefert nur die
  Absaetze zur passenden Problem-Klasse. Prompt-Injektion on-demand,
  nicht ganze DB/Datei.

### OP-113a: erfahrung-Tabelle um scope-Spalte erweitern

- **Status:** open
- **Typ:** feature (Erfahrungs-Gehirn, Sub-OP zu OP-113)
- **Betroffen:** `werkstatt/erfahrung.py` (neu, siehe OP-113)
- **Problem:** ADR-0010 legt zweistufige Memory fest. OP-113 legt
  Basis-Tabelle `erfahrung` an, aber ohne `scope`-Spalte. OP-129
  (Destillation), OP-130 (Semantic Memory) und OP-113i (Log-Backfill)
  brauchen `scope TEXT NOT NULL DEFAULT 'projekt'` als Voraussetzung.
- **Akzeptanzkriterien:**
  - `erfahrung`-Tabelle hat Spalte `scope TEXT NOT NULL DEFAULT 'projekt'`,
    CHECK auf `scope IN ('projekt','global')`.
  - Alle bestehenden Inserts setzen explizit `scope='projekt'`.
  - Migration idempotent (ALTER TABLE nur wenn Spalte fehlt).
  - 2 Tests: Insert mit/ohne scope, Constraint-Verletzung.
- **Tests:** `tests/test_erfahrung.py::test_scope_default`,
  `tests/test_erfahrung.py::test_scope_constraint`
- **Blockiert von:** OP-113
- **Quelle:** `docs/adr/ADR-0010-memory-zweistufig.md`

### OP-123: Gate-Bridge (Loop wartet auf HTTP statt stdin)

- **Status:** open
- **Typ:** architektur
- **Betroffen:** `werkstatt/gate_bridge.py` (neu),
  `werkstatt/gates.py` (`input()` -> `gate_bridge.wait()`),
  `werkstatt/web/app.py` (`POST /api/runs/{id}/gate`)
- **Problem:** Loop laeuft nur im Vordergrund mit `input()`.
  Browser-Betrieb (Buttons statt Terminal) nicht moeglich,
  Headless-Lauf nicht moeglich.
- **Akzeptanzkriterien:** (a) `gate_bridge.wait(run_id, gate_id,
  timeout=300) -> str` blockiert bis POST.
  (b) `_human_gate_plan` ruft `gate_bridge.wait()` wenn `--headless`,
  sonst weiter `input()`. (c) `GET /api/runs/{id}/gates` listet offene
  Gates. (d) Test: Mock liefert "j", Gate liefert 0.
- **Tests:** `tests/test_gate_bridge.py` (neu)
- **Blockiert von:** —

### OP-124: Chat-Agent + read-only Tool-Registry

- **Status:** open
- **Typ:** feature
- **Betroffen:** `werkstatt/chat_agent.py` (neu),
  `werkstatt/chat_tools.py` (neu)
- **Problem:** Der Nutzer will einen Assistenten pro Projekt, der
  Fragen beantwortet, Audit-Logs liest, Diffs prueft — wie
  ChatGPT/Claude Code, aber ohne Messbloecke an den Nutzer zu
  schicken. Heute gibt es keinen Chat-Loop.
- **Akzeptanzkriterien:** (a) `chat_loop(session, message, tools) ->
  str` mit Tool-Use-Iteration. (b) `CHAT_TOOLS`-Dict read-only:
  `read_file`, `grep`, `git_log`, `git_diff`, `audit_query`,
  `pytest_collect`, `diagnose`, `read_status`. (c) **Kein**
  `write_file`/`apply_patch`/`git_commit`. (d) Test: Mock-LLM liefert
  `tool_call("git_diff")`, Tool-Result landet in Session.
- **Tests:** `tests/test_chat_agent.py` (neu),
  `tests/test_chat_tools.py` (neu)
- **Blockiert von:** OP-125

### OP-125: Chat-Session-Store (SQLite, pro Projekt)

- **Status:** open
- **Typ:** feature
- **Betroffen:** `werkstatt/chat_session.py` (neu)
- **Problem:** Chat-Sessions muessen pro Projekt persistieren.
  Heute gibt es nichts.
- **Akzeptanzkriterien:** (a) SQLite-Tabelle `events(seq, session_id,
  ts, kind, payload)`. (b) `ChatSession.append`, `load`,
  `list_sessions(project)`. (c) `derive_messages()` rekonstruiert
  LLM-Historie aus Events. (d) 3 Tests: append+load, Fork, derive.
- **Tests:** `tests/test_chat_session.py` (neu)
- **Blockiert von:** —

### OP-126: Chat-UI (Tool-Call-Karten, Session-Anzeige)

- **Status:** open
- **Typ:** ui-feature
- **Betroffen:** `werkstatt/web/static/chat.js` (neu),
  `werkstatt/web/static/style.css`
- **Problem:** Chat-Panel ist nur ein Eingabefeld. Keine
  Nachrichtenliste, keine Tool-Call-Karten, keine Session-Anzeige.
- **Akzeptanzkriterien:** (a) `ChatPanel`-Komponente mit
  Nachrichtenliste (user/assistant, scrollbar, auto-scroll).
  (b) `ToolCallCard` einklappbar mit Status (pending/running/ok/Fehler)
  und I/O-Details. (c) WebSocket-Client fuer
  `WS /api/projects/{name}/chat`. (d) Datei-Pfade im Chat sind klickbar
  und oeffnen den Workbench-Drawer mit entsprechender Datei.
  (e) Manuell verifiziert.
- **Tests:** keine (UI, visuell)
- **Blockiert von:** OP-124, OP-125

### OP-127: Timeline + Layout-Umbau Variante A

- **Status:** open
- **Typ:** ui-feature
- **Betroffen:** `werkstatt/web/static/layout.js` (neu),
  `werkstatt/web/static/timeline.js` (neu),
  `werkstatt/web/static/style.css`
- **Problem:** Aktuelles Layout ist 2x2-Grid (Terminal links oben,
  Chat rechts oben, Audit rechts unten). Variante A: Runs-Liste links,
  Timeline Mitte, Chat rechts (immer sichtbar), Workbench als
  Collapsible Drawer.
- **Akzeptanzkriterien:**
  (a) 3-Spalten-Layout: Runs-Liste (200px, mit Status-Indikatoren
  pro OP/Run), Timeline (flex), Chat (400px, immer sichtbar).
  (b) Timeline rendert Phasen-Knoten aus Event-Store-Events
  (Explorer, Scout, Architect, Planner-Split, Builder tN, Reviewer tN,
  Reflection, Verify, Gate). Aktiver Knoten mit Spinner.
  Fehlgeschlagene Knoten rot mit Fehlertext. Aufklappbar: was wurde
  gelesen, welcher Prompt, welche Patches, welcher Reviewer-Bug.
  (c) Workbench als Collapsible Drawer (default: geschlossen), Tabs
  [Dateien] [Diff] [Verify] [Audit] [Terminal].
  (d) Status-Leiste unten: Tasks, Verify, Drift, Budget, aktive Phase.
  (e) Style bleibt wie im Screenshot (dunkel, lila Akzente, schlicht) —
  keine Framework-Migration.
  (f) Manuell verifiziert gegen Wireframe.
- **Tests:** keine (UI, visuell)
- **Blockiert von:** OP-126

### OP-128: Chat-Modus Debugger (evidence-first, Ladder)

- **Status:** open
- **Typ:** feature
- **Betroffen:** `werkstatt/chat_agent.py` (`chat_loop`),
  `werkstatt/chat_tools.py`, `werkstatt/web/static/chat.js`
- **Problem:** Bei fehlgeschlagenem Run soll der Chat dem Menschen
  eine **Eskalations-Ladder** anbieten. Der Chat entscheidet NICHTS
  — er stellt die Optionen vor. Der **Mensch** waehlt ueber den
  Chat, welche Stufe greift. Der Debugger ist eine Faehigkeit des
  Chats (nur im Modus `debugger` verfuegbar), keine eigene Rolle.

- **Ladder-Modi** (Auswahl durch den Menschen; `chat_loop(...,
  modus=...)` setzt die Wahl um):
  - `manuell` — Chat diagnostiziert read-only. Der Mensch
    entscheidet selbst, was er mit der Diagnose tut. Keine
    Debugger-Tools. Keine automatische Memory-Schreibung.
  - `debugger` — Der Mensch hat den Chat in den Debugger-Modus
    geschaltet. Chat ruft `pytest_run(path, test)`,
    `read_file(path, start, end)`, `write_temp_test(content)`.
    `write_temp_test` schreibt ausschliesslich nach
    `.werkstatt/temp_tests/` — nie nach `tests/`, nie nach
    `werkstatt/`. Fix bleibt Diff-Vorschlag, kein Auto-Apply.
    **Nach erfolgreicher Verifikation (Loop-Re-Run gruen):**
    Lern-Event `debugger_fix_verifiziert` → Memory-Hook (OP-160).
  - `reject` — Der Mensch lehnt ab, gibt Begruendung ueber den
    Chat zurueck an Loop. Kein Fix → kein Memory-Eintrag, aber
    Grund fliesst in Reflection-Kontext.

- **Wichtige Trennung:**
  - Der Chat ist **Interface**, kein Entscheider.
  - Der Mensch ist der Entscheider. Er sieht die drei Modi als
    Auswahl und waehlt einen.
  - Die Memory-Schreibung ist die **Folge der menschlichen
    Entscheidung** fuer den Debugger-Modus + einer erfolgreichen
    deterministischen Verifikation — nicht eine Chat-Automatik.

- **Akzeptanzkriterien:**
  - (a) `chat_loop(..., modus="manuell"|"debugger"|"reject")`.
    Der Modus wird vom Menschen gesetzt (UI/CLI-Argument), nicht
    vom Chat gewaehlt. Modus wird pro Turn in Session-Events
    markiert.
  - (b) Debugger-Modus: `pytest_run` (nicht nur
    `--collect-only`), `read_file`, `write_temp_test` verfuegbar.
    In den Modi `manuell` und `reject` sind diese Tools NICHT
    verfuegbar (fail-closed).
  - (c) `write_temp_test` ausschliesslich nach
    `.werkstatt/temp_tests/`.
  - (d) Strukturierter Fix-Output (Dataclass `DebuggerFix`):
    `{signatur, ursache_tag, diff, betroffene_dateien, confidence}`.
  - (e) Nach erfolgreichem Re-Run: Event
    `debugger_fix_verifiziert` mit `{signatur, fix_hash, run_id}`.
  - (f) Test: Mock-`pytest_run`, Tool-Result landet in Session,
    Fix-Event bei gruenem Re-Run.

- **Tests:** `tests/test_chat_debugger.py` (neu),
  `tests/test_debugger_memory_hook.py` (neu, OP-160)
- **Blockiert von:** OP-124
- **Lern-Hook:** OP-160 (Debugger → Memory)

### OP-129: Memory-Destillation + Promotion (scope-aware)

- **Status:** open
- **Typ:** feature (Erfahrungs-Gehirn)
- **Betroffen:** `werkstatt/erfahrung.py`, `tools/memory_destill.py`
  (neu), `tools/memory_promote.py` (neu),
  `tools/memory_drift.py` (neu)
- **Problem:** OP-113 speichert Episoden, destilliert aber keine Regeln,
  konsolidiert nicht, promotet nicht. Ergebnis: derselbe Fehler
  wiederholt sich. Zusaetzlich fehlt eine projektuebergreifende Ebene —
  Antipatterns wie `# type: ignore` sind universell, werden aber pro
  Projekt neu gelernt.
- **Akzeptanzkriterien:**
  - Tabelle `regeln(id, titel, trigger, anweisung, trust, scope,
    beobachtungen_json, quelle_episoden, erstellt_am, letzte_nutzung,
    widerlegt)`. Trust in {candidate, confirmed, canonical};
    scope in {project, global}.
  - OP-113a erweitert die `erfahrung`-Tabelle um `scope TEXT NOT NULL
    DEFAULT 'project'` — Voraussetzung fuer Promotion.
  - `destilliere_regeln(min_episoden=3, scope='project')`: gruppiert
    gleiche `(problem_klasse, kontext_hash)`, ruft LLM, legt
    `candidate`-Regel mit Verweis auf die Episoden an.
  - `promote(regel_id)`: nach 2-3 erfolgreicher Anwendung → confirmed;
    nach 5+ ohne Widerlegung → canonical + AGENTS.md-Vorschlag.
  - `promote_to_global(regel_id)`: prueft, ob dieselbe problem_klasse
    in ≥2 anderen Projekt-DBs `confirmed` ist → legt globalen
    `candidate` an.
  - **Sanitization bei Promotion:** Pfade generalisieren
    (`/opt/projekt/...` → `<project>/...`), IPs maskieren,
    Projekt-Namen durch `<project>` ersetzen.
  - `tools/memory_promote.py --scan`: scannt alle Projekt-DBs, listet
    Promotionskandidaten und Widersprueche, fuehrt NICHT automatisch
    aus.
  - Append-only `memory_ledger(id, ts, aktion, regel_id, payload,
    commit_sha)` — jede Mutation nachvollziehbar.
  - `tools/memory_drift.py --check`: (a) jede Canonical hat 5+
    Beobachtungen, (b) keine Regel widerspricht einer neueren
    Confirmed-Regel, (c) jede Ledger-Zeile hat `commit_sha` oder
    `quelle=backfill`.
  - **Persistenz-Pfad `gehirn-global.db`:** Entscheidung noetig —
    `~/.werkstatt/gehirn-global.db` (User-Home, mehrere Projekte)
    oder `docs/gehirn-global.db` (git-getrackt). Empfehlung:
    `~/.werkstatt/` mit taeglichem Backup nach `.backups/`.
  - Tests: destilliere_regeln aus 3 synthetischen Episoden ergibt 1
    candidate; promote zweimal → confirmed; promote_to_global mit
    3 Projekt-DBs ergibt 1 globalen candidate; memory_drift 0.
- **Tests:** `tests/test_memory_destill.py` (neu),
  `tests/test_memory_promote.py` (neu),
  `tests/test_memory_drift.py` (neu)
- **Blockiert von:** OP-113a

### OP-130: Semantic Memory (Projekt-Fakten + globale Praeferenzen)

- **Status:** open
- **Typ:** feature (Erfahrungs-Gehirn)
- **Betroffen:** `werkstatt/erfahrung.py`,
  `projects/<name>/profile.yaml`, `werkstatt/chat_tools.py`
- **Problem:** Chat muss Basics per grep herausfinden (Test-Runner,
  DB-Typ, Migrationspfad). OP-113 speichert nur Fehler-Episoden.
  Zusaetzlich fehlt eine globale Ebene fuer User-Praeferenzen
  (z.B. „User bevorzugt Diff-Vorschlaege statt direkter Aenderung").
- **Akzeptanzkriterien:**
  - Tabelle `semantic_memory(schluessel, wert, quelle, ts, confirmed,
    scope, kontext)`. scope in {project, global}.
  - `record_semantic(schluessel, wert, quelle, scope='project')` —
    Default projektlokal. Globale Semantik nur explizit mit
    scope='global'.
  - `load_semantic(kontext=None, scope='project')` — liest eine Ebene;
    `load_all_semantic(kontext)` liest beide (Projekt gewinnt bei
    Konflikt).
  - `profile.yaml` (pro Projekt) mit `semantic:`-Block; beim
    Projekt-Load werden fehlende Eintraege nachgezogen, bestehende
    confirmed-Eintraege nicht ueberschrieben.
  - `chat_loop` injiziert top-3 Semantik projektspezifisch + top-2
    global in den System-Prompt.
  - Test: record_semantic/load_semantic Roundtrip;
    chat_loop mit Mock-LLM prueft, dass Semantik im Prompt ist.
- **Tests:** `tests/test_semantic_memory.py` (neu)
- **Blockiert von:** OP-113a

### OP-131: Loop-Memory-Panel (was das Gehirn gelernt hat)

- **Status:** open
- **Typ:** ui-feature
- **Betroffen:** `werkstatt/web/static/memory.js` (neu),
  `werkstatt/web/app.py` (`/api/memory/*`),
  `werkstatt/erfahrung.py` (Read-API)
- **Problem:** Was das Gehirn gelernt hat, ist unsichtbar. Der User
  kann falsche Regeln nicht erkennen, nicht bestaetigen, nicht
  verwerfen.
- **Akzeptanzkriterien:**
  - `GET /api/memory/summary` → Zaehler (episoden, regeln, proposals,
    canonical, confirmed, candidates), getrennt nach Scope.
  - `GET /api/memory/regeln?ebene=canonical|confirmed|candidate&scope=project|global|all`
    → Liste mit titel, trigger, anweisung, beobachtungen, erstellt_am,
    letzte_nutzung, widerlegt.
  - `GET /api/memory/injiziert?run_id=N` → Regeln + Episoden, die
    dieser Run tatsaechlich in den Prompt bekommen hat (aus
    Audit-Events rekonstruiert).
  - Panel-UI mit 5 Sektionen:
    1. Canonical (global)
    2. Confirmed (global)
    3. Projekt-Regeln
    4. Candidates (unbestaetigt)
    5. „Diese Runde injiziert" (read-only)
  - Filter: „nur global", „nur Projekt", „alle". Klick auf Regel
    oeffnet Inspector mit Beobachtungs-Historie.
  - Button „Regel fuer global vorschlagen" auf jeder Projekt-confirmed
    → triggert `promote_to_global`-Vorschlag (manuell bestaetigt).
  - Manuell verifiziert: Panel zeigt leeren Zustand statt Crash,
    wenn DB leer.
- **Tests:** keine (UI, visuell)
- **Blockiert von:** OP-129, OP-130

### OP-132: "Why did it fail?"-Button (Repair Ladder)

- **Status:** open
- **Typ:** ui-feature
- **Betroffen:** `werkstatt/web/static/timeline.js`,
  `werkstatt/web/static/chat.js`, `werkstatt/web/app.py`
- **Problem:** Bei fehlgeschlagenem Run muss der User manuell
  entscheiden, was zu tun ist. Es fehlt eine eskalierende
  Handlungsleiter — drei Stufen, die in Sekunden beginnen und bis zum
  vollen Loop reichen.
- **Akzeptanzkriterien:**
  - Nach `run_failed`-Event erscheint in Timeline und/oder Chat ein
    Banner: "Run #N fehlgeschlagen (OP-M, X/Y Tasks)" mit drei Buttons.
  - Button 1 **„Chat analysiert"**: sendet automatisch Nachricht an
    Chat-Agent (OP-124) mit Auftrag: "Analysiere Run #N: Audit-Logs,
    Diff, Fehlerursache. Antwort in Sekunden."
  - Button 2 **„Debugger starten"**: startet Chat im Modus
    `debugger` (OP-128) mit identischem Diagnose-Auftrag.
  - Button 3 **„Coding-Loop neu"**: startet neuen Loop-Lauf mit
    identischer `--aufgabe` (Wiederholung nach Fix, falls manuell
    durchgefuehrt).
  - Test: Mock-Event `run_failed` → Panel rendert drei Buttons;
    Klick auf Button 1 → `POST /api/projects/{name}/chat` mit
    erwarteter Nachricht.
- **Tests:** keine (UI, visuell)
- **Blockiert von:** OP-124, OP-127, OP-128

### OP-133: Cost/Token-Dashboard

- **Status:** open
- **Typ:** ui-feature
- **Betroffen:** `werkstatt/web/static/stats.js` (neu),
  `werkstatt/web/app.py` (`/api/stats/*`),
  `werkstatt/state.py` (bereits `llm_calls`), `werkstatt/agent.py`
- **Problem:** Token-Verbrauch und Kosten sind im Terminal nur als
  Gesamt-Budget sichtbar. DSH und OpenHands zeigen per-Model,
  per-Phase, per-Tool aufgeschluesselt. Wir haben `state.llm_calls`,
  aber keine UI und keine Aggregation.
- **Akzeptanzkriterien:**
  - `GET /api/stats/run/{run_id}` → `{tokens_in, tokens_out,
    tokens_cached, cost_usd, per_model, per_phase}`.
  - `GET /api/stats/project/{name}/aggregat?days=7` → gleiche
    Struktur, aggregiert.
  - Dashboard-Panel (read-only): Gesamt-Budget-Bar, per-Phase-
    Aufschluesselung, per-Model-Tabelle, Warnung bei 80 % Verbrauch.
  - Test: Mock-Audit-Events → korrekte Aggregation.
- **Tests:** `tests/test_stats_api.py` (neu)
- **Blockiert von:** —

### OP-141: `state/` Submodul-Split (RunState aufteilen)

- **Status:** open
- **Typ:** architektur (Split, invasiv)
- **Betroffen:** `werkstatt/state/` (neu), `werkstatt/state.py`
- **Problem:** `RunState` hat 100+ Felder, keine Doku zu
  Schreiber/Leser. Handoff §7 nennt 47 tote Felder. Siehe ADR-0012
  Muster 2+3.
- **Akzeptanzkriterien:**
  - Neue Struktur `werkstatt/state/`: `__init__.py` (`RunState`
    als Komposition), `context.py` (`project_dir`, `aufgabe`,
    `api_key`, `budget`, `run_id` — reiner Run-Kontext),
    `explorer.py` (`ExplorerOutput`, `ExplorerDiagnostics`),
    `scout.py` (`ScoutOutput`), `plan.py` (`ArchitectOutput`,
    `PlannerOutput`), `tasks.py` (`TaskState`, `AppliedPatches`),
    `reviewer.py` (`ReviewerOutput`), `reflection.py`
    (`ReflectionState`).
  - Alle Dataclasses mit Docstring (Schreiber/Leser/Pflichtfelder)
    und Contract-Eintrag in `state_contracts.py` (OP-135).
  - Tote Felder (Liste aus OP-134) entfernt. Kein `getattr`-Hack
    mehr fuer fehlende Felder.
  - `RunState` ist Rueckwaerts-kompatibel: `state.explorer_context`
    delegiert an `state.explorer.output`-Property.
- **Tests:** `tests/test_state_split.py` (neu),
  bestehende Suite bleibt gruen (mit Anpassungen an geaenderte
  Feld-Pfade).
- **Blockiert von:** —

### OP-143: `cli/` + Re-Export-Bereinigung

- **Status:** open
- **Typ:** architektur (Split + Aufraeumen)
- **Betroffen:** `werkstatt/cli/` (neu), `werkstatt/loop.py`,
  `werkstatt/pipeline.py` (neu)
- **Problem:** `loop.py` (500 Zeilen) ist CLI-Einstieg UND
  Re-Export-Hub. 13 ruff-Fehler (F822 `__all__` undefined,
  F841 tote Variablen). Tests patchen `werkstatt.loop.audit` etc.
  Siehe ADR-0012 Muster 1.
- **Akzeptanzkriterien:**
  - Neue Struktur: `werkstatt/cli/__init__.py` (leer),
    `cli/main.py` (`main`, argparse), `pipeline.py`
    (`run_pipeline_loop`, Phase-Aufrufe).
  - `loop.py` wird zur Deprecation-Proxy-Datei mit vollstaendigem
    `__all__`. 13 ruff-Fehler behoben.
  - Tests patchen den echten Modul-Pfad
    (`werkstatt.audit.audit` statt `werkstatt.loop.audit`).
    Betroffen: alle `test_loop*.py`, `test_gates.py`,
    `test_audit.py`.
  - Re-Export-Proxies in `pipeline_phases.py` entfallen
- **Tests:** `tests/test_cli.py` (neu).
- **Blockiert von:** —

## Sub-OPs (Erfolgs-Ebene, deterministisch)

- **113a** `werkstatt/erfahrung.py` (neu): Schema `erfahrung(id,
  problem_klasse, problem_sig, kontext_hash, absatz, quelle, erfolg,
  commit_sha, skill_name, erstellt_am, genutzt, letzte_nutzung)`.
  API: `record_erfahrung(...)` + `match_erfahrung(problem_klasse,
  max_n=3)`. SQLite via stdlib. Schema-Init idempotent. Tests.

- **113b** `docs/MERKPOSTEN.md`-Import: einmaliges Script
  `tools/import_merkposten.py`. Parsed `### M-XX — Titel` + Absatz,
  schreibt als `quelle='manual'`, `problem_klasse='prozess-lehre'`,
  `erfolg=1`. Idempotent per problem_sig.

- **113c** `diagnose.py`-Write-Hook: nach erfolgreichem Fix (in
  `reflection._reflection_loop` bei `return True`) →
  `record_erfahrung(klasse, sig, fix_absatz, quelle='diagnose')`.

- **113d** `antipattern.py`-Write-Hook: bei Treffer der zu
  `reviewer_rejected` fuehrt → `record_erfahrung('antipattern:<kind>',
  sig, erklaerung, quelle='antipattern', erfolg=0)`. Bei `approved`
  → `erfolg=1`.

- **113e** Skills-Matching: `skills/*/SKILL.md`-Frontmatter erweitern
  um `problem_klassen: [...]`. Neuer Helper
  `skills.match_for_problem(klasse) -> list[Skill]` (max 3).
  `_merke_geladene_skills` schreibt zusaetzlich
  `record_erfahrung(klasse, sig, skill_body_absatz, quelle='skill',
  skill_name=name)`.

- **113f** Reflection-Injektion: `reflection._reflection_loop` ruft
  vor Builder-Prompt `match_erfahrung(_problem_klasse, max_n=3)`,
  injiziert `## ERFAHRUNGEN`-Block (max 800 Zeichen).

## Sub-OPs (Proposal-Ebene, LLM-verallgemeinert)

- **113g** Proposal-Miner: `erfahrung.get_failure_cluster(problem_klasse,
  kontext_hash, min_count=3) -> dict` mit `{ids, absaetze,
  letzter_versuch}`. Neue Tabelle `proposal_queue(id, cluster_sig,
  failure_ids, proposed_absatz, status, erstellt_am, letzte_nutzung,
  genutzt)` mit `status in {pending, accepted, rejected, expired}`.
  Nach erschoepfter Reflection (`return False` + Runde=max): wenn
  Cluster >= 3 Failures UND kein pending/accepted Proposal fuer
  `cluster_sig` → **ein** LLM-Call mit den 3+ Tracebacks →
  `proposed_absatz` (1-3 Satz Lehre). Insert mit `status='pending'`.
  Kein LLM wenn Cluster bekannt.

- **113h** Proposal-Resolution: `match_erfahrung` liefert zusaetzlich
  pending-Proposals zum Cluster. Reflection-Injektion (113f) bekommt
  `## UNBESTAETIGTE VORSCHLAEGE (aus N Fehlversuchen)`-Block. Nach
  `_reflection_loop`:
  - `return True` + Proposal war im Prompt → `status='accepted'` +
    `record_erfahrung(..., erfolg=1, quelle='proposal')`.
  - `return False` + Proposal war im Prompt → `status='rejected'`,
    nie wieder fuer diesen Cluster.

## Akzeptanz

(a) `erfahrung.db` existiert nach erstem Loop-Lauf.
(b) `MERKPOSTEN.md` einmalig importiert.
(c) Nach jedem erfolgreichen Reflection-Fix waechst die DB.
(d) Naechster aehnlicher Fix findet den Absatz in < 100ms.
(e) Prompt-Groesse unveraendert +-800 Zeichen.
(f) 3 identische Failures → genau **1** Proposal (nicht 3).
(g) Fix klappt nach Proposal → `accepted` + neuer erfahrung-Eintrag.
(h) Fix klappt nicht → `rejected`, Prompt ohne diesen Absatz.
(i) Kein LLM-Call wenn Cluster schon bekannt (Idempotenz).

## Reihenfolge

113a → 113b → 113e → 113c → 113f → 113d → 113g → 113h

## Beispiel (OP-091-Fall)

3x `NameError: _home_kontext` in `audit_panel.py` → Miner ruft LLM
mit 3 Tracebacks → Proposal "NameError auf modul-level-Feld: pruefe
ob das Feld im Modul deklariert ist". 4. Lauf: gleicher Fehler +
Proposal im Prompt → Fix klappt → accepted. 5. Lauf: neuer
NameError in anderem Modul → Match findet den Absatz sofort.

- **Blockiert von:** -


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

### OP-145b: State-Contract fuer auftrag_bereits_erfuellt-Familie

- **Status:** open
- **Typ:** architektur (State-Contract)
- **Betroffen:** `werkstatt/state_contracts.py`,
  `tests/test_state_contracts_auftrag.py` (neu),
  `docs/STATE-INVENTUR.md`
- **Problem:** Drei Felder teilen ein Konzept, haben aber
  unterschiedliche Semantik:
  - `auftrag_bereits_erfuellt: bool` (`state.py:256`) — "ein Pfad
    hat es erkannt" (auch LLM-Vermutung).
  - `auftrag_bereits_erfuellt_bestaetigt: bool` (`state.py:147`) —
    "deterministisch bewiesen".
  - `auftrag_bereits_erfuellt_quelle: str` (`state.py:148`) —
    welcher Pfad.
  Writer-Set (5 Pfade, gemessen 2026-11-06):
  `planner:deterministic_precheck` (T/T),
  `planner:scout_llm_urteil` (T/F),
  `builder:llm_keine_patches` (T/F),
  `builder:old_nicht_da_aber_new_da` (T/T),
  `builder:alle_patches_no_effect` (T/F).
  Reader unterscheiden: `phases/tasks.py:218` verlangt beide True;
  `phases/plan.py:99,109`, `phases/explorer.py:176`, `gates.py:435`,
  `builder/run.py:857` lesen nur `_erfuellt`.
  `state_flow` zeigt fuer alle drei: Risiko HOCH (multi-writer,
  keine Contracts).
  Die Verwirrung: ein Rename `_erfuellt` -> `_bestaetigt`
  (urspruengliche OP-145-AK) wuerde `planner.py:1830`
  (scout_llm_urteil) regressen — scout setzt bewusst
  `_erfuellt=True, _bestaetigt=False`, damit `plan.py:109`
  (skip plan gate) triggert, aber `tasks.py:218` (Task-Done)
  NICHT.
- **Akzeptanzkriterien:**
  - `state_contracts.py` deklariert
    `AUFTRAG_BEREITS_ERFUELLT_FELDER` mit Doku-String pro Feld
    (Semantik + zulaessige Werte-Kombinationen).
  - Neuer Helper
    `setze_auftrag_bereits_erfuellt(state, quelle, bestaetigt)`
    als einziger Writer (statt 5 verstreuter Stellen), der die
    drei Felder konsistent setzt.
  - Alle 5 Writer-Pfade rufen den Helper.
  - `docs/STATE-INVENTUR.md`: Sektion
    "auftrag_bereits_erfuellt-Familie" mit Semantik-Tabelle
    (Writer -> Werte-Kombination, Reader -> welche Felder).
  - Tests: 3 Writer-Pfade (Scout, Builder-LLM, Builder-deterministisch)
    setzen die richtigen Werte-Kombinationen; `plan.py` triggert
    bei `_erfuellt=True` unabhaengig von `_bestaetigt`;
    `tasks.py` triggert nur bei beiden True.
- **Tests:** `tests/test_state_contracts_auftrag.py` (neu)
- **Blockiert von:** —
- **Hinweis:** Ersetzt OP-145 (verworfen). OP-145 hat einen Rename
  vorgeschlagen, der Scout-Pfad-Regress verursacht haette.
  Quelle: Loop-Test-4-Analyse 2026-11-06, Messung der 5 Writer.

### OP-147: Reflection-Verdrahtung (kleine Luecken)

- **Status:** open
- **Typ:** architektur (klein, komplementaer zu OP-113/129/130/131)
- **Betroffen:** `werkstatt/reflection.py`,
  `werkstatt/control/reflection.py`, `werkstatt/prompts.py`,
  `werkstatt/state.py` (nur Doku)
- **Ziel (bestaetigt 2026-11-05):** Reflection hat den Zweck, dem
  Builder bei Reviewer-Reject konkret zurueckzugeben, was schief
  lief, mit Begruendung + Empfehlung. Das tut `_reflection_loop`
  heute schon (liest `last_verify_errors`, `reviewer_bugs`, baut
  Feedback-Prompt, ruft Builder erneut). Diese OP schliesst die
  drei kleinen Verdrahtungsluecken, die dabei offen sind.

- **Problem (Messung 2026-11-05):**
  1. **`state.letzter_test_fehler`** (eines der 47 toten Felder)
     ist konzeptionell ein Reflection-Input, wird aber in
     `reflection.py` und `control/reflection.py` nirgends gelesen.
     Der Feld-Kommentar sagt: "Wird in den naechsten Builder-Prompt
     gerendert" — das passiert nicht.
  2. **`state.geladene_skills`** (deklariert, getattr_only in
     `skills.py:merke_geladene_skills`) wird von Reflection mit
     `_merke_geladene_skills(state, [...])` geschrieben, aber nur
     fuer Audit-Sichtbarkeit. Keine Verdrahtung zur Auswahl-Strategie.
  3. **3 Reflection-Varianten** (`_reflection_loop` Z. 240,
     `_phase_end_reflection` Z. 658, `_plan_reject_reflection` Z.
     810) nutzen unterschiedliche Kontext-Inputs — kein gemeinsames
     "Was weiss Reflection?"-Modell.

- **Akzeptanzkriterien:**
  - **`letzter_test_fehler`:** Wenn `state.letzter_test_fehler`
    gesetzt ist und `_reflection_loop` laeuft, wird es zusaetzlich
    zu `last_verify_errors` in den Feedback-Prompt gehaengt
    (dedupliziert, wenn identisch). Wenn nicht gesetzt: kein
    Verhalten-Delta.
  - **`geladene_skills`:** In `state.reflection_skill_body`-Auswahl
    (heute nur `systematic-debugging`) wird `state.geladene_skills`
    gelesen, um bereits geladene Skills nicht erneut zu laden.
    Kein doppelter Skill-Body im Prompt.
  - **3 Varianten dokumentieren:** In `reflection.py`-Docstring
    (Kopf) eine 10-zeilige Tabelle: welche Variante liest welche
    Felder. Vereinheitlichen erst in einer spaeteren OP — heute nur
    dokumentieren.
  - **Nicht in dieser OP:** ContractViolation-Retry.
    `validate_transition` (OP-136) bleibt fail-loud.
- **Tests:** `tests/test_reflection_verdrahtung.py` (neu) — 3 Tests
  (letzter_test_fehler landet im Prompt, geladene_skills wird
  respektiert, Doku-Vollstaendigkeit der 3 Varianten via AST-Read).
- **Blockiert von:** —

### OP-163b: Planner-Dependencies deterministisch aus Prosa

- **Status:** open
- **Typ:** architektur (Planner)
- **Betroffen:** `werkstatt/planner.py` (`_zerlege_in_sub_tasks`,
  `_extrahiere_prosa_abschnitt`), `tests/test_planner_deps.py` (neu)
- **Problem:** OP-163 hat `PLANNER_SPLIT_SYSTEM` um die Pflicht-Regel
  "Konsequenz-Tasks MUESSEN dependencies setzen" erweitert (Z. 293-296
  in planner.py). Loop-Test-4 hat gezeigt: Prompt-Regel wird vom
  Split-LLM ignoriert. Audit-Event `planner_split` 2026-11-05 14:17:47:
  alle 8 Tasks `deps=[]`. PhaseState bestaetigt: `deps=[]` bei t1-t8.
  Der `get_next_task`-Filter aus OP-163 greift ins Leere.
- **Akzeptanzkriterien:**
  - Neue deterministische Funktion `_leite_deps_aus_prosa(tasks, prosa)`
    in `planner.py`: scannt Architect-Prosa nach Marker-Saetzen
    ("haengt von", "erst nach", "Abhaengigkeiten"), mappt die genannten
    Task-Namen auf Task-IDs, setzt `dependencies` direkt (LLM-frei).
  - Fallback: wenn die Prosa keine Marker enthaelt, bleibt
    `dependencies=[]` (kein Regress fuer unabhaengige Tasks).
  - `planner_split`-Event loggt `deps` (durch OP-171 bereits da) —
    Tests pruefen den Live-Beleg.
  - Tests: 3 Smoke-Tests — (a) Prosa "t3 haengt von t1" -> t3 bekommt
    `deps=["t1"]`; (b) Prosa "erst nach t2" -> gleiche Wirkung;
    (c) Prosa ohne Marker -> deps bleibt leer.
- **Tests:** `tests/test_planner_deps.py` (neu)
- **Blockiert von:** —

### OP-164b: Reviewer AUFTRAG-TREUE-Check bei Rename-Aufgaben

- **Status:** open
- **Typ:** architektur (Reviewer)
- **Betroffen:** `werkstatt/reviewer.py` (`REVIEWER_SYSTEM`,
  `run_reviewer`), `tests/test_reviewer_auftrag_treue.py` (neu)
- **Problem:** OP-164 patcht den GOLD-Diff-Block (`-`-Zeile +
  bestehende Zuweisung entfernt), aber der Live-Beleg aus Loop-Test-4
  liegt im `AUFTRAG-TREUE-CHECK`-Block (Z. 165-179). Zwei
  Bug-Klassen wurden live beobachtet:
  - (a) **Wert statt Feldname ersetzt**: `state.auftrag_bereits_erfuellt
    = True` -> `state.auftrag_bereits_erfuellt_bestaetigt = False`
    (Semantik-Kipp True->False). Loop-Test-4 10:13, builder.py:945/1043/1596.
  - (b) **Neue type-ignore auf fremden Feldern**: Diff fuegt
    `# type: ignore[attr-defined]` auf `reflection_erschoepft`,
    `scout_bereits_erfuellt`, `phase_review_uebersprungen` hinzu —
    Over-Delivery gegen Task-Anweisung "restliche Logik unveraendert".
    Loop-Test-4 14:20, gates.py:419.
- **Akzeptanzkriterien:**
  - Neue deterministische Funktion `_filter_auftrag_treue_false_positives(
    bugs, diff, task_desc)` in `reviewer.py`: bei Rename-Kontext
    (`umbenennen`/`rename`/`ersetzen durch`):
    (a) Bug "Wert X->Y geaendert" auf medium herab, wenn derselbe
        Hunk eine `+`-Zeile mit `bestaetigt`/`_neu`-Feld und
        Wert-Gleichheit mit alt (True/True, False/False) zeigt.
    (b) Bug "type-ignore auf Feld Z hinzugefuegt" auf medium herab,
        wenn Z nicht in `task_files`-Description erwaehnt ist.
  - Test-Beleg: Loop-Test-4-Audit-Text als Fixture, Filter setzt
    severity auf medium.
  - Tests: 3 Smoke-Tests — (a) Wert-Kipp Rename-OK -> medium,
    (b) Wert-Kipp ohne Rename-Kontext -> HIGH, (c) type-ignore
    Over-Delivery -> medium.
- **Tests:** `tests/test_reviewer_auftrag_treue.py` (neu)
- **Blockiert von:** —



### OP-172: Verify→Builder-Kette — Builder sieht nur 5 Fehler

- **Status:** open
- **Typ:** architektur (Verify + Builder-Prompt)
- **Betroffen:** `werkstatt/verify.py` (Z. 479 `_out[-500:]`),
  `werkstatt/roles/builder/run.py` (Z. 147-156 `_err_lines`),
  `tests/test_verify_builder_kette.py` (neu)
- **Problem:** Die Kette Verify→State→Builder-Prompt schneidet
  Fehler-Information an **drei** Stellen ab:
  1. **`verify.py:479`** speichert `_out[-500:]` — die **letzten**
     500 Zeichen. Bei mypy/ruff/pytest steht dort die Statistik
     ("Found N errors", "N failed"), nicht die Fehler selbst.
     Der Builder bekommt "3 Fehler" ohne zu wissen **welche**.
  2. **`run.py:149`** nimmt `[:5]` — nur die ersten 5 Fehler.
     Bei 20 mypy-Fehlern sieht der Builder 15 nicht.
  3. **`run.py:149`** schneidet pro Error auf `[:500]`. Langer
     mypy-Fehler mit Pfad+Zeile+Type wird abgeschnitten.
  Der Gate blockt zwar (ruff_changed hart seit 8c52cf3,
  mypy_changed hart seit b950b97), aber der Builder bekommt
  nicht genug Info zum Reparieren. Er ratet.
- **Live-Beleg (Loop-Test 5, 2026-11-06):** Builder hat in t4
  den Import `format_letzter_test_fehler_block` vergessen.
  Die Reflection sah `F821` im State, aber die konkreten
  Zeilen (444:22) im Prompt waren ungemessen. Nach 8c52cf3
  haette der Gate den Fehler geblockt, aber der Builder
  braucht den **Detail-Text** fuer den Fix.
- **Akzeptanzkriterien:**
  - `verify.py:479`: `_out[-500:]` → `_out[:2000]`, mit
    Fallback auf `_out[-500:]` wenn die ersten 2000 leer
    sind (Edge-Case: nur whitespace im Anfang).
  - `run.py:149`: `[:5]` → `[:15]`, `[:500]` → `[:1000]`
    pro Error.
  - Neue Formatierung: pro Error nur `<stage>: <file:line: msg>`
    extrahieren (Regex), den restlichen Traceback verwerfen.
    Reduziert Prompt-Groesse ohne Info-Verlust.
  - `_format_repair_hint` bekommt die vollen (nicht mehr
    gekuerzten) Errors — Klassifikation (F821, ruff TRY004,
    py_compile) funktioniert damit auf allen Fehlern, nicht
    nur den ersten 5.
  - Neuer Test `tests/test_verify_builder_kette.py`:
    (a) 20 synthetische mypy-Fehler → alle 20 im Builder-Prompt;
    (b) 1500-Zeichen-Output pro Fehler → auf 1000 gekuerzt,
        nicht 500;
    (c) `_out[:2000]` enthaelt die Fehler-Zeilen, nicht nur
        die Statistik-Zeile.
- **Tests:** `tests/test_verify_builder_kette.py` (neu)
- **Blockiert von:** —
- **Priorität:** hoch — Voraussetzung für sinnvolle
  Reflection-Runden. Der Gate blockt, aber der Builder
  kann ohne Detail-Info nur raten.
- **Quelle:** Messung 2026-11-06 nach Gate-Härtung
  (ruff=0, mypy=0, alle Stages hart). Naechster logischer
  Schritt nach Altlastabbau.

### OP-173: Spec-Tests — RunState-Factory statt SimpleNamespace

- **Status:** open
- **Typ:** architektur (Test-Infrastruktur + Spec-Qualitaet)
- **Betroffen:** `werkstatt/state.py` (RunState Defaults),
  `tests/factories.py` (neu), 167 Test-Dateien (schrittweise),
  `werkstatt/*` (getattr-Rueckbau nach Migration)
- **Ziel (bestaetigt 2026-11-06):** Tests sind Specs, nicht
  White-Box-Implementierungspruefungen. Jeder Test sagt mit
  Docstring aus, welches Verhalten er erzwingt. Kein Test
  haengt von zufaelligen `SimpleNamespace`-Feldern ab.
  Prod-Code nutzt `state.x` statt `getattr(state, "x", default)`.
- **Problem (Messung 2026-11-06):**
  1. **262 von 263 `getattr(state, ...)`-Stellen** in Prod-Code
     beziehen sich auf DEKLARIERTE RunState-Felder. Kein
     Ghost-getattr. Aber der Aufruf ist noetig, weil **167
     Test-Dateien `SimpleNamespace`** statt `RunState` uebergeben.
     `state.x` wuerde dort mit `AttributeError` crashen.
  2. **28 `# type: ignore[attr-defined]`** in Prod bleiben
     bestehen, weil mypy die `getattr`-Aufrufe als potentiell
     fehlend markiert.
  3. **Test-Qualitaet**: viele Tests sind technisch gruen, aber
     testen Implementation statt Verhalten. Beispiel: `assert
     state.letzter_test_fehler == "..."` mit
     `SimpleNamespace`-State sagt nichts ueber den Spec-Vertrag
     von `_reflection_loop` aus.
  4. **`getattr`-Wald bremst Refactoring**: Feldname umbenennen
     → grep findet 262 Stellen, aber mypy findet 0 (weil
     `getattr` strings sind). Bei `state.x` wuerde mypy alles
     zeigen.
  5. **`SimpleNamespace`-Fallback-Werte** sind zufaellig. Ein
     Test mit `SimpleNamespace()` und einem Feld `api_key`
     fehlt → `getattr(state, "api_key", "")` gibt `""`,
     Test "funktioniert". Spec sagt aber "api_key MUSS
     vorhanden sein".
- **Akzeptanzkriterien:**
  - **P1 (Basis):** `RunState` hat Defaults fuer alle 13
    Pflichtfelder. `RunState()` ohne Argumente baubar.
    `tests/factories.py::mk_state(**overrides) -> RunState`
    als einzige Test-Konstruktion.
  - **P2 (Pilot):** 2 Test-Dateien auf `mk_state` umgestellt.
    `SimpleNamespace`-Import entfernt. Alle Tests gruen.
  - **P3 (Migration):** alle 167 Test-Dateien umgestellt.
    `SimpleNamespace` nur noch, wo explizit
    "Feld fehlt"-Verhalten getestet wird (max 5 Dateien).
  - **P4 (Prod-Rueckbau):** 262 `getattr(state, "x", default)`
    → `state.x`. Kein `# type: ignore[attr-defined]` mehr in
    Prod (nur noch bei externen Typ-Stubs).
  - **P5 (Spec-Review):** die 20 wichtigsten Tests
    (reflection, builder, verify, gates, planner) haben
    Docstring mit Spec-Vertrag. `arrange-act-assert`-Struktur.
    Keine `mock.assert_called_with(...)`-White-Box-Assertions.
  - **P6 (Metriken):** `state_flow --check` zeigt 0
    getattr-only Felder in Prod. `grep -c 'type: ignore'
    werkstatt/` = 0 ausser `import-untyped`.
- **Tests:** `tests/test_factories.py` (neu, 3 Tests fuer
  `mk_state`), Pilot in `tests/test_reflection.py` +
  `tests/test_reflection_spec_erschoepfung.py`.
- **Reihenfolge:** P1 → P2 → P3 → P4 → P5 → P6.
- **Blockiert von:** —
- **Prioritaet:** hoch — Voraussetzung fuer vertrauenswuerdige
  Loop-Tests. Ohne Spec-Tests testet der Loop gegen Attrappen.
- **Quelle:** Messung 2026-11-06 (262/263 getattr deklariert,
  0 Ghost). Nach ruff=0/mypy=0/Verify-Kette hart ist das der
  naechste strukturelle Schritt.

### OP-174: Spec-Tests — RunState-Factory statt SimpleNamespace

- **Status:** open
- **Typ:** architektur (Test-Infrastruktur + Spec-Qualitaet)
- **Betroffen:** `werkstatt/state.py` (RunState Defaults),
  `tests/factories.py` (neu), 167 Test-Dateien (schrittweise),
  `werkstatt/*` (getattr-Rueckbau nach Migration)
- **Ziel:** Tests sind Specs. Jeder Test sagt per Docstring aus,
  welches Verhalten er erzwingt. Kein Test haengt von zufaelligen
  `SimpleNamespace`-Feldern ab. Prod-Code nutzt `state.x` statt
  `getattr(state, "x", default)`.
- **Problem (Messung 2026-11-06):**
  1. **262/263 `getattr(state, ...)`** in Prod beziehen sich auf
     deklarierte RunState-Felder (0 Ghosts). Aber noetig, weil
     **167 Test-Dateien `SimpleNamespace`** uebergeben.
  2. **28 `# type: ignore[attr-defined]`** in Prod bleiben noetig.
  3. Tests testen Implementation, nicht Spec-Vertrag.
  4. `getattr`-Wald bremst Refactoring: mypy findet umbenannte
     Felder nicht.
  5. `SimpleNamespace`-Fallback-Werte sind zufaellig: fehlendes
     Feld → `getattr`-Default statt Spec-Bruch.
- **Akzeptanzkriterien:**
  - **P1 (Basis):** `RunState` Defaults fuer alle 12 Pflichtfelder.
    `RunState()` ohne Argumente baubar.
    `tests/factories.py::mk_state(**overrides) -> RunState`
    als einzige Test-Konstruktion.
  - **P2 (Pilot):** 2 Test-Dateien migriert
    (`test_reflection.py`, `test_reflection_spec_erschoepfung.py`).
  - **P3 (Migration):** alle 167 Dateien umgestellt.
    `SimpleNamespace` nur, wo explizit "Feld fehlt"-Verhalten
    getestet wird (max 5 Dateien).
  - **P4 (Prod-Rueckbau):** 262 `getattr` → `state.x`.
    Kein `# type: ignore[attr-defined]` mehr.
  - **P5 (Spec-Review):** 20 wichtigste Tests mit Spec-Vertrag,
    `arrange-act-assert`, keine White-Box-Mock-Assertions.
  - **P6 (Metriken):** `state_flow --check` zeigt 0 getattr-only
    in Prod. `grep -c 'type: ignore' werkstatt/` = 0 ausser
    `import-untyped`.
- **Tests:** `tests/test_factories.py` (neu, 3 Spec-Tests),
  Pilot in `test_reflection.py` + `test_reflection_spec_erschoepfung.py`.
- **Reihenfolge:** P1 → P2 → P3 → P4 → P5 → P6.
- **Blockiert von:** —
- **Prioritaet:** hoch — Voraussetzung fuer vertrauenswuerdige
  Loop-Tests.

### OP-176: contract_check-Haertung — setattr(state, "<unbekannt>") deterministisch fangen

- **Status:** open
- **Typ:** architektur (Verteidigungskette)
- **Betroffen:** `tools/contract_check.py` (oder neues Modul in
  `werkstatt/`), `werkstatt/state_contracts.py`,
  `tests/test_contract_check_setattr.py` (neu)
- **Problem:** Loop-Test 6 (2026-11-06, Bug D aus OP-175): Der
  Builder versuchte zweimal, ein fehlendes RunState-Feld zu
  setzen — erst `state.phase_review_gate_auto = True` (mypy
  fing `attr-defined`), dann `setattr(state, "phase_review_gate_auto",
  True)` (ruff B010 fing es in der Folge-Runde). Die
  Verteidigungskette hat funktioniert, aber `setattr` mit
  String ist heute nur durch ruff-Regel B010 und Zufall
  gedeckt. Deterministische AST-Regel im `contract_check`
  schliesst die Luecke.

- **Akzeptanzkriterien:**
  - AST-Walk ueber `werkstatt/` findet jeden
    `setattr(<state-var>, "<const>", ...)`-Aufruf.
  - Prueft: Attribut existiert in `RunState.__dataclass_fields__`.
  - Fail-closed mit klarer Fehlermeldung (Datei, Zeile,
    Feldname).
  - `tests/test_contract_check_setattr.py`: (a) unbekanntes
    Feld -> fail; (b) bekanntes Feld -> ok; (c) `setattr(x,
    var, ...)` mit dynamischem Namen -> skip (statisch nicht
    aufloesbar).

- **Tests:** siehe AK.
- **Blockiert von:** —
- **Blockiert:** nichts (Loop-Test 7 laeuft ohne).
- **Prioritaet:** mittel — Verteidigungskette funktioniert
  heute, aber nur durch zufaellig aktive ruff-Regel B010.
- **Quelle:** OP-175 Bug D, Loop-Test 6, 2026-11-06.

### OP-177: Reviewer-Praezision — False Positives messen und reduzieren

- **Status:** open
- **Typ:** architektur (Reviewer + Gates)
- **Betroffen:** `werkstatt/reviewer.py` (Prompt, Bug-Klassifikation),
  `tests/test_reviewer_false_positive_aufrufer.py`,
  `tests/test_reviewer_false_positive.py` (erweitern),
  `docs/STATUS.md` (Loop-Log-Auswertung)
- **Problem:** Loop-Test 7 (2026-11-06, OP-168b) hatte
  5 Reviewer-Bugs (3 HIGH, 2 medium). Messung gegen AK-Text
  und Code (Messblock 14) zeigte: nur 1 Bug berechtigt
  (Test-Luecke), 3 HIGH waren false positives:

  - Bug 1 HIGH: "Gate in `_reflection_loop` fehlt" —
    AK-Text sagt explizit `_phase_end_reflection` als Ziel.
    Reviewer interpretierte den Auftrag semantisch statt
    woertlich.
  - Bug 2 HIGH: "`phase_review_auto = False` vor Gate-
    Aufruf macht `a`-Zweig unwirksam" — Code liest
    `phase_review_auto` NACH dem Gate-Aufruf. Reviewer
    las falsche Code-Stelle.
  - Bug 5 medium: "Gate im falschen Reject-Pfad" — Code
    hat dort gar kein Gate. Reviewer hatte veraltete Diff-
    Version (Patch war bereits durch eine spaetere Runde
    ueberschrieben).

  Muster: Reviewer-LLM faellt bei zwei Klassen von Bugs
  systematisch daneben — (a) AK-Interpretation, (b) Diff-
  Snapshot-Aktualitaet. Beide sind per deterministischem
  Pre-Check adressierbar.

- **Akzeptanzkriterien:**
  - **Messung (a):** Auswertung der letzten 10 Loop-Laeufe
    (audit-logs/agent-pipeline-*.jsonl): Reviewer-Praezision =
    berechtigte Bugs / alle gemeldeten Bugs, pro Loop-Lauf.
    Baseline erheben, in PROGRESS.md festhalten.
  - **Pre-Check (b):** Deterministische Vorpruefung fuer
    Bugs, die per AST/String-Vergleich pruefbar sind:
    - Wenn Bug sagt "Funktion X fehlt", pruefe AST, ob X im
      Code existiert. Wenn ja: Bug als "unwahrscheinlich"
      markieren (nicht verwerfen, aber Flag).
    - Wenn Bug sagt "Datei Y hat Zeile Z nicht", pruefe den
      aktuellen Diff-Hash gegen den im Bug referenzierten
      Snapshot.
  - **Bug-Klassifikation (c):** Reviewer-Bugs bekommen ein
    zusaetzliches Feld `konfidenz: hoch | mittel | niedrig`.
    `hoch` = deterministischer Pre-Check stimmt zu.
    `mittel` = weder bestaetigt noch widerlegt.
    `niedrig` = Pre-Check widerspricht.
  - **Task-Fail-Trigger (d):** Nur `konfidenz: hoch` fuehrt
    zu automatischem Task-Fail. `mittel`/`niedrig` erfordern
    User-Bestaetigung am Gate (Prompt-Text erweitern:
    "Reviewer meldet [niedrig] — pruefen?").
  - **Smoke-Tests:** 2 neue Tests:
    (a) Reviewer-Bug mit `konfidenz: niedrig` fuehrt NICHT
    zu Task-Fail; (b) `konfidenz: hoch` fuehrt zu Task-Fail.

- **Tests:** `tests/test_reviewer_false_positive_aufrufer.py`,
  `tests/test_reviewer_false_positive.py` (erweitern)
- **Blockiert von:** —
- **Blockiert:** nichts (Loop-Test 8 laeuft ohne; OP-172 ist
  unabhaengiger Blocker)
- **Prioritaet:** mittel — Loop-Test 7 hat gezeigt, dass
  Reviewer-FPs den User-Zeit-Aufwand erhoehen (3 Iterationen
  im `e`-Pfad), aber die Sicherheits-Kette funktioniert
  (kein Auto-Approve).
- **Quelle:** Loop-Test 7 (18:27-19:55, OP-168b),
  Commit `749172c`, Merkposten "Reviewer-LLM produziert
  false positives bei AK-Text".
- **Hinweis:** Loest NICHT das Problem, dass der Reviewer
  Bugs uebersieht (Recall). Nur Praezision. Recall-Messung
  ist eigene OP, wenn Praezision steht.

## Delete-Zone

Nach Delete-Zone-Muster: erledigte OPs werden hier protokolliert.

- 2026-11-06 | OP-168b | done | Gate in `_phase_end_reflection` nach jeder Reject-Runde (c713033), `phase_review_auto: bool` in RunState (state_flow_baseline nachgezogen), 2 Smoke-Tests in test_phase_review_gate.py. Live-Beleg Loop-Test 7 (18:xx): Gate nach Runde 1 in Phase-End-Reflection. Reviewer-Bugs aus Loop-Test 7 geprueft: nur Test-Luecke berechtigt (jetzt gefuellt); Bug 1/2/5 waren false positives (Reviewer interpretierte AK-Text falsch, Code liest phase_review_auto nach Gate-Aufruf). Test-Spec-Abweichung: 2 Tests test_reflection_reject_ruft_gate + test_gate_n_bricht_reflection_ab. Task-Reflection-Gate (`_reflection_loop`) explizit NICHT im Scope — OP-Text nennt `_phase_end_reflection`.
- 2026-11-06 | OP-175 | done | Bugs A, B, C gefixt (6aa8694 Topo-Sort, f204965 verify_gleich, 2538174 Gate-Message). Bug D nicht reproduzierbar: Builder versuchte aktiv mypy-Umgehung (state.X = -> setattr), Verteidigungskette (mypy+ruff B010+spec_widerspruch) hat es gefangen; Haertung als OP-176. Bug E zurueckgezogen: Fehlmessung (Audit-Events existieren, 0s korrekt). Test-Namen AK-abweichend: test_planner_deps_sortierung.py statt test_planner_deps_richtung.py (Bug war Sortierung, nicht Richtung), test_reflection_stagnation_verify.py statt test_reflection_stagnation_5_runden.py, test_phase_review_gate_kontext.py nicht angelegt (Bug C war Message-Bug, kein Code-Gate). Hinweis: OP-168b (Gate zwischen Task-Reflection-Runden) bleibt offen.
- 2026-11-06 | OP-168 | done | `_phase_review_gate` in phases/review.py:11 + 6 Tests + Verdrahtung in phases/finalize.py:117; AK (b) erfuellt; AK (a) (Gate zwischen jeder Reflection-Runde) als OP-168b angelegt
- 2026-11-06 | OP-145 | wontfix | Semantik geklaert: `_erfuellt`/`_bestaetigt`/`_quelle` haben verschiedene Rollen (5 Writer-Pfade, 2 Reader-Muster); Rename haette Scout-Pfad (`planner.py:1830`) regressen. Ersetzt durch OP-145b (State-Contract, in Planung)
- 2026-11-06 | OP-166 | done | per-Task-State-Reset `last_verify_errors` + `reviewer_bugs` via `_reset_task_state`; 4 Tests; AK (b) bewusst nicht implementiert (K50-Bug-C in reflection.py:394-403); entblockt OP-164b (a720fe0)
- 2026-11-05 | OP-144 | done | import-linter als Post-Build-Stage (hart), 3 Layer-Regeln aus ADR-0013 (render, roles.builder, phases); allow_indirect_imports=true; werkstatt/roles/__init__.py nachgezogen (30eef6e)
- 2026-11-05 | OP-142 | superseded | verworfen: shell.py und terminal_proxy.py machen fundamental verschiedene Dinge (PTY-Ausfuehrung vs. Log-Tailing); 17 identische Code-Zeilen sind Boilerplate (Imports, websocket.accept, except-Klauseln). 5 routes/-Wrapper haetten existierende Module gewrappt statt Duplikate aufzuloesen. Details in PROGRESS.md.
- 2026-11-05 | OP-140 | done | roles/builder/-Split in 5 Submodule (ast, prompt, validate, patch, run) + _common; builder.py als sys.modules-Alias (6334d80)
- 2026-11-05 | OP-139 | done | phases/-Split: _common + 5 Phasen-Submodule; pipeline_phases.py als sys.modules-Alias (d41233f)
- 2026-11-05 | OP-138 | done | render/-Split in 7 Module (tee, rich, emit, spinner, progress, tasks, plan); loop_renderer.py als sys.modules-Alias (b6f75db)
- 2026-11-05 | OP-136b | done | state_drift.py + 3 Registry-Checks + 2 validate_transition-Aufrufe + verify-Stage hart (bfd38e9)
- 2026-11-05 | OP-167 | done | tasks_ok_counter in 2 Erfolgs-Pfaden + AST-Guard-Test (a3a538b)
- 2026-11-05 | OP-165 | done | Contract-Verify pro Task (contract_check-Stage) (f73dde5)
- 2026-11-05 | OP-163 | done | Planner-Dependencies als Pflichtfeld durchgesetzt (9797b31); **live-wirkungslos (Loop-Test-4, siehe OP-163b)**
- 2026-11-05 | OP-164 | done | Reviewer versteht Rename-Aufgaben (2dde8cd); **live-wirkungslos (Loop-Test-4, siehe OP-164b)**
- 2026-11-05 | OP-135a | done | State-Contract-Design: Dataclasses + Registry + Property-Views (35c2aa3)
- 2026-11-04 | OP-134 | done | State-Inventur — Tool + Doku (7177f16)
- 2026-11-04 | OP-146 | done | Stale Blocker-Referenzen bereinigt (11 OPs, 18 Refs); OP-113a angelegt (Work-Commit 44b4350)
- 2026-11-05 | OP-137 | done | AST-Block liest file-Feld + sortiert nach confidence (dbaa40b)
- 2026-11-05 | OP-135b | done | explorer_context + tests deklariert, Property-Views direkt, 15 getattr-Callsites auf direkte Felder (171b10d + 4824c45)
- 2026-11-05 | OP-136a | done | Contract-Validierung explorer->scout + planner->builder (fail-loud) (Work-Commit b77ee26)
- 2026-11-04 | OP-149 | done | pytest_regression requires -> changed_py_files + security-ai Cross-Repo (ebc7c46; Work-Commit 11f02b1)
- 2026-11-04 | OP-148 | done | test_shell.py 3 PTY-Tests auf skip (W36-RP-Guard; Work-Commit 547eab0)
- 2026-11-04 | OP-150 | done | control/reflection.py geloescht (byte-identisch zu reflection.py, 0 Imports; Work-Commit 1752d76)
- 2026-11-04 | OP-122 | done | SQLite-Event-Store fuer Loop-Events (append/query, kind-Filter, WAL, .werkstatt/events.db)

- 2026-11-04 | OP-119 | done | _TeeWriter defensiv gegen geschlossene Streams (bd0db4b)
- 2026-11-04 | OP-114 | done | Audit-Events reicher: bugs/grund/gate/fehler (c4b525a)
- 2026-11-04 | OP-111 | done | Progress-Events in ask_llm + _with_spinner (4c0c59d, 2c1b30d)
- 2026-11-03 | OP-108 | done | Scout create/update + Kopier-Auftrag (3884036)
- 2026-11-03 | OP-097 | superseded | aufgeteilt in OP-104 (Kopie) + OP-105 (Proxy) + OP-106 (Aufrufer) + OP-107 (Tests)
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

### OP-160: Debugger-Lern-Loop — Debugger-Fixes ins Erfahrungs-Gehirn

- **Status:** open
- **Typ:** architektur (Verzahnung OP-128 + OP-113/129)
- **Betroffen:** `werkstatt/chat_agent.py`, `werkstatt/erfahrung.py`
  (neu, via OP-113), `werkstatt/reflection.py`,
  `werkstatt/chat_tools.py`
- **Problem:** Der Debugger (OP-128) ist der einzige Punkt im System,
  an dem ein Fix deterministisch verifiziert wird (Loop-Re-Run nach
  Fix). Diesen verifizierten Fix-Strom soll das Erfahrungs-Gehirn
  (OP-113/129) als Quelle nutzen — nicht als Freitext-Sammlung,
  sondern als strukturierte, vertrauenswuerdige Eintraege.

- **Voraussetzung (menschliche Entscheidung):** Ein Fix gelangt nur
  ins Gedaechtnis, wenn (a) der Mensch den Debugger-Modus im Chat
  gewaehlt hat, (b) der Debugger einen Fix vorgeschlagen hat,
  (c) der Mensch den Fix angewendet hat, (d) der Loop-Re-Run
  deterministisch gruen ist. Ohne (a)-(d) KEINE Schreibung.

- **Datenstrom:**
  1. Loop scheitert → Chat bietet Ladder an
  2. Mensch waehlt Modus `debugger` ueber den Chat
  3. Chat reproduziert + schlaegt Fix vor (Diff, kein Auto-Apply)
  4. Mensch wendet Fix an → Loop-Re-Run
  5. **Verify gruen** → `debugger_fix_verifiziert`-Event mit
     `{signatur, ursache_tag, fix_hash, betroffene_dateien, run_id}`
  6. **Verify rot** → kein Memory-Eintrag (Fix war falsch)

- **Injektions-Architektur (WICHTIG — nicht standard):**
  - **Builder Standard-Pfad:** KEINE Memory-Injektion.
  - **Builder innerhalb `_reflection_loop`:** Memory-Injektion fuer
    die aktuelle Fehler-Signatur, wenn `confidence >= high`.
  - **Debugger-Prompt (OP-128):** Memory-Injektion fuer die aktuelle
    Signatur, wenn `confidence >= medium`.
  - **Planner / Architect / Scout / Reviewer:** KEINE
    Memory-Injektion (sie sollen das aktuelle Problem loesen,
    nicht raten).

- **Reife-Modell (Vorschlag, zu klaeren vor Bau):**
  - 1. Vorkommen der Signatur: Audit-Event, kein Gedaechtnis
  - 2. Vorkommen: Eintrag `confidence=low`
  - 3. Vorkommen + erfolgreicher Fix: `confidence=medium`
  - 5. Vorkommen + erfolgreicher Fix: `confidence=high`

- **Signatur (zu klaeren vor Bau):** Welche Felder identifizieren
  einen Fehler eindeutig? Vorschlag: `stage` + `error_class` +
  `test_id`/`file` + `root_cause_tag`. Ohne diese Struktur wird
  Aehnlichkeitssuche zur Textsuche und damit wertlos.

- **Fix-Format (zu klaeren vor Bau):** Ein Fix ist nicht immer
  ein Code-Diff. Moegliche Typen: `patch`, `prompt_aenderung`,
  `config_aenderung`, `test_aenderung`. Jeder Typ braucht ein
  eigenes Speicherformat.

- **Akzeptanzkriterien:**
  - (a) `debugger_fix_verifiziert`-Event wird bei gruenem Re-Run
    geschrieben (Hook in OP-128).
  - (b) `erfahrung.py` (via OP-113) hat Tabelle `fix_episode` mit
    Signatur-Feldern und `fix_hash`.
  - (c) Reflection injiziert Memory nur bei `confidence >= high`.
  - (d) Debugger injiziert Memory nur bei `confidence >= medium`.
  - (e) Builder Standard-Pfad hat KEINE Memory-Injektion
    (grep auf `memory_inject` in `builder.py` = 0 ausserhalb
    Reflection).
  - (f) Test: Fix mit gruenem Re-Run → Eintrag; Fix mit rotem
    Re-Run → kein Eintrag.

- **Tests:** `tests/test_debugger_memory_hook.py` (neu),
  `tests/test_reflection_memory_inject.py` (neu)
- **Blockiert von:** OP-128 (Ladder + strukturierter Fix-Output),
  OP-113a (scope-Spalte), OP-129 (Destillation)

### OP-096: Phase 33.3 — gates.py nach control/ migrieren

- **Status:** open
- **Typ:** architektur
- **Betroffen:** `werkstatt/gates.py` nach `werkstatt/control/gates.py`
- **Problem:** 16 Funktionen in gates.py, davon 6 echte Gates.
  13 Aufrufe in pipeline_phases.py.
- **Akzeptanzkriterien:** `control/gates.py` mit plan_gate,
  human_gate_plan, human_gate, human_gate_body. Deprecation-Proxy.
  Aufrufer migriert. `tests/test_gates.py` gruen.
- **Blockiert von:** —

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
- **Blockiert von:** OP-096

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
- **Blockiert von:** —

### OP-106: Aufrufer auf control.reflection umstellen

- **Status:** open
- **Typ:** architektur (sub-OP, 3 Dateien)
- **Betroffen:** `werkstatt/loop.py`, `werkstatt/pipeline_phases.py`,
  `werkstatt/task_runner.py` (nur Import-Zeilen)
- **Auftrag:** Alle `from werkstatt.reflection import X` auf
  `from werkstatt.control.reflection import X` umstellen. Keine Logik-Änderung.
- **Akzeptanz:** grep findet keine `from werkstatt.reflection import` mehr
  (außer in `control/reflection.py`-Docstring + Tests).
- **Blockiert von:** OP-105

### OP-107: Test-Patch-Pfade migrieren

- **Status:** open
- **Typ:** architektur (sub-OP, mehrere Tests)
- **Betroffen:** `tests/test_reflection*.py`, `tests/test_loop*.py`
- **Auftrag:** `mock.patch("werkstatt.reflection.X")` → `mock.patch("werkstatt.control.reflection.X")`.
- **Blockiert von:** OP-106

### OP-109: Tests für scout._erkenne_kopier_auftrag

- **Status:** open
- **Typ:** test
- **Betroffen:** `tests/test_scout.py` (neu oder erweitern)
- **Problem:** OP-108 hat `_erkenne_kopier_auftrag` eingebaut, aber
  die 4 Tests decken nur `_pruefe_zieldatei_existenz` ab.
- **Akzeptanzkriterien:** 3 Tests: (a) "kopiere a.py nach b.py" ->
  {quelle, ziel}, (b) ohne "kopiere" -> None, (c) "Kopiere nur" -> None.
- **Blockiert von:** -

### OP-110: _pruefe_zieldatei_existenz ignoriert existierende Zieldatei

- **Status:** open
- **Typ:** bugfix
- **Betroffen:** `werkstatt/planner.py::_pruefe_zieldatei_existenz`
- **Problem:** Bei Kopier-Auftrag mit existierender Zieldatei wird
  trotzdem `aktion: create` gesetzt statt `update`.
- **Akzeptanzkriterien:** Zieldatei existiert -> `update`; fehlt ->
  `create`. 2 Tests in `tests/test_planner.py`.
- **Blockiert von:** -

### OP-115: Progress-Events Builder-Spezifika

- **Status:** open
- **Typ:** ux-feature
- **Betroffen:** `werkstatt/builder.py`
- **Problem:** OP-111 Etappe 1+2 decken `start`, `prompt_sent`,
  `response_received`, `done` ab. Innerhalb von `_build_patches_fuer_datei`
  (nach `response_received`, vor `done`) fehlen granulare Schritte.
  Bei 30s+ Patch-Parsing sieht der User nur Heartbeats.
- **Akzeptanzkriterien:**
  - `_emit_progress("Builder tN", "patches_parsed", f"{n} patches")`
    nach `_normalisiere_aider_patches`.
  - `_emit_progress("Builder tN", "patches_validated", ...)` nach
    `_validate_imports_in_patch`-Loop.
  - `_emit_progress("Builder tN", "patches_applied", ...)` nach
    Apply-Block.
- **Tests:** `tests/test_builder.py` — Smoke-Test, dass die drei
  Events mit dem aktuellen Task-Label emittiert werden (mocken
  `_emit_progress`, assert call_count).
- **Blockiert von:** -

### OP-116: Progress-Events Reviewer-Spezifika

- **Status:** open
- **Typ:** ux-feature
- **Betroffen:** `werkstatt/reviewer.py`
- **Problem:** Reviewer-Call (OP-111 Etappe 1+2) zeigt `start`/`done`,
  aber nicht `diff_received`, `analysis_start`, `verdict`.
- **Akzeptanzkriterien:**
  - `_emit_progress("Reviewer tN", "diff_received", f"{n} files")`
    nach `_get_git_diff`.
  - `_emit_progress("Reviewer tN", "analysis_start", "")` vor
    `ask_llm`.
  - `_emit_progress("Reviewer tN", "verdict", "approved"|"rejected")`
    nach JSON-Parse.
- **Tests:** `tests/test_reviewer.py` — Smoke-Test analog OP-115.
- **Blockiert von:** -

### OP-112: Antipattern + Skill-Matching in Reflection-Runden

- **Status:** open
- **Typ:** reflection-feature
- **Betroffen:** `werkstatt/reflection.py`, `werkstatt/antipattern.py`,
  `werkstatt/skills.py`, `werkstatt/hard_rules.py`
- **Problem:** Reflection-Runden reagieren nur auf Verify-Fehler +
  Reviewer-Bugs. Zwei Luecken: (a) `antipattern.scan_patches` laeuft
  nur am Task-Ende (OP-064b-Veto), nicht pro Reflection-Runde. (b) Die
  Skills werden beim Loop-Start einmal geladen (`systematic-debugging`
  fuer Reflection), aber nicht problem-spezifisch gematcht — d.h. bei
  "Tests rot wegen Import" wird kein Import-Skill zurueckgegeben, bei
  "Test schwaechen" kein Test-Quality-Skill.
- **Akzeptanzkriterien:**
  - `reflection._reflection_loop`: vor dem Builder-Prompt
    `scan_patches(state.patches)` aufrufen. Treffer werden in den
    Reflection-Prompt als "## ANTIPATTERN-WARNUNG" eingebaut.
  - Neuer Helper `skills.match_skills_for_problem(fehler, bugs) -> list`.
    Matching-Matrix: `ImportError` -> `python-imports`; `type.*ignore`
    -> `strict-typing`; `pytest assert` geschwaecht -> `test-quality`;
    `ruff.*F401` -> `unused-imports`. Config in `skills/_matching.yaml`
    oder hardcoded in `skills.py`.
  - Reflection-Prompt bekommt "## EMPFOHLENE SKILLS" mit den gematchten
    Bodies (max 3, je 800 Zeichen).
  - Bestehender `systematic-debugging`-Skill bleibt als Fallback.
- **Tests:** `tests/test_reflection.py` — 2 Tests (Antipattern-Warnung
  im Prompt, Skill-Matching bei ImportError).
- **Blockiert von:** —

### OP-113i: Log-Backfill — DB aus 30k Audit-Events vorfuellen

- **Status:** open
- **Typ:** erfahrung-backfill
- **Betroffen:** `tools/backfill_erfahrung.py` (neu), `.werkstatt/erfahrung.db`
- **Erkenntnis (2026-11-03 23:55):** Von 1.253 Problem-Events in
  `audit-logs/*.jsonl` (12.10.-03.11.) sind nur **~650 cluster-fähig**:
  - `loop_verify_failed` (490): `errors`, `stages`, `phase` → Sig
    über `(stage_id, erste-3-error-zeilen-hash)`.
  - `builder_patch_invalid` (84): `grund`, `file`, `action` → Sig
    über `(grund, action)`.
  - `loop_task_failed` (34): `grund` → Sig über `grund`.
  - `loop_reflection_stagnation_abort` (41): `grund`, `stagnation` → Sig.
  - **NICHT** backfillbar: `loop_reviewer_rejected` (240),
    `loop_plan_gate_rejected` (90), `loop_gate_failed` (153) —
    keine beschreibenden Felder. Siehe OP-114.
- **Akzeptanz:** `tools/backfill_erfahrung.py` liest alle
  `agent-pipeline-*.jsonl`, clustert nach den obigen Sigs, filtert
  Cluster mit `>= 3` Vorkommen und ruft `record_erfahrung(...)`.
  Lösungs-Absatz aus folgendem Kontext-Fenster: naechster
  `loop_task_ok` / `reviewer_phase_approved` / `loop_phase=phase_ok`
  innerhalb 5 min. `quelle='log-backfill'`, `erfolg=1` wenn Lösung
  gefunden, `erfolg=0` sonst. Idempotent per `problem_sig`.
- **Blockiert von:** OP-113a

### OP-117: Scout-Prosa optimieren

- **Status:** open
- **Typ:** ux-fix
- **Betroffen:** `werkstatt/scout.py` (SCOUT_SYSTEM-Prompt),
  `werkstatt/loop_renderer.py` (SCOUT-AUFRAG-Panel)
- **Problem:** Rendering zeigt abgeschnittene Prosa
  (`… beschreibende Pay`). Aus Handoff §4: "Prosa 150→800 Zeichen
  + wrap(88)" greift nicht für den Scout-Auftrag, oder die
  Scout-Prosa selbst ist zu knapp formuliert.
- **Akzeptanzkriterien:**
  - Scout-Prompt erzeugt Prosa mit konkreten Payload-Feldern statt
    generisch (`loop_reviewer_rejected → payload={"bugs": [...]}`).
  - Panel rendert bis 800 Zeichen ohne Wort-Abschneidung
    (Wrap, kein Truncate).
  - Test: 200-Zeichen-Prosa → Panel vollständig sichtbar.
- **Blockiert von:** -

### OP-118: Heartbeat-Redundanz bei aktivem _emit_progress

- **Status:** open
- **Typ:** ux-cleanup
- **Betroffen:** `werkstatt/loop_renderer.py` (`_with_spinner`)
- **Problem:** OP-111 sagt: "Heartbeat nur Fallback wenn Sub-Component
  keine Events sendet." Aktuell feuert der Heartbeat trotzdem, auch
  wenn `start`/`prompt_sent`/`response_received` bereits laufen.
  Doppelte Info im Terminal.
- **Akzeptanzkriterien:**
  - `_with_spinner._heartbeat_loop` unterdrueckt Heartbeat, wenn
    innerhalb der letzten 15s `_emit_progress` mit gleichem `label`
    gefeuert wurde.
  - Test: 2× `_emit_progress` in 3s → 0 Heartbeats.
- **Blockiert von:** -

### OP-120: Revidierter Plan wird nicht gerendert

- **Status:** open
- **Typ:** ux-bug
- **Betroffen:** `werkstatt/gates.py` (`_human_gate_plan`),
  `werkstatt/loop_renderer.py` (`plan`)
- **Problem:** Nach Reject am Plan-Gate laeuft die Reflection und
  erzeugt einen revidierten Plan. Der Prompt `Revidierter Plan OK?`
  wird gezeigt, aber **der Plan selbst nicht**. Der User muss blind
  j/n druecken. Testlauf 2026-11-04 hat das reproduziert.
- **Akzeptanzkriterien:**
  - `_human_gate_plan` mit `kontext="revidierter_plan"` ruft
    `_r.plan(...)` mit `state.tasks`/`tests`/`akzeptanzkriterien`
    auf, **bevor** `input()`.
  - Test: Mock-`input`, revidierter Plan da -> `plan()`-Call
    nachweisbar vor dem Prompt.
- **Blockiert von:** -

### OP-121: step() und _emit_progress ohne Timestamp im CI-Log

- **Status:** open
- **Typ:** observability
- **Betroffen:** `werkstatt/loop_renderer.py` (`step`, `_emit_progress`)
- **Problem:** In `RENDER_MODE=ci` schreibt `_emit_raw` Timestamps
  `[HH:MM:SS]`, aber `step()` (Rich-Panel) und `_emit_progress`
  gehen ueber andere Pfade. Folge: Messungen wie Explorer->Scout-Gap
  sind aus dem Log nur grob rekonstruierbar (Testlauf 2026-11-04:
  Gap ~27 s, aber keine exakten Zeitpunkte im Log).
- **Akzeptanzkriterien:**
  - `step()`-Aufrufe in CI haben `[HH:MM:SS]`-Prefix im Log.
  - `_emit_progress`-Aufrufe in CI haben `[HH:MM:SS]`-Prefix im Log.
  - Bestehende Tests in `test_loop_renderer.py` bleiben gruen.
- **Blockiert von:** -
