# Status — Werkstatt

Format aus `DOC_CONVENTIONS.md` §5. Nur offene, **loop-faehige** OPs.
`—` in Feldern = noch nicht spezifiziert (Loop praezisiert bei Bearbeitung).
Letzte Aktualisierung: 2026-11-10.

Roadmap-Phasen (M-NNN, nicht loop-faehig) stehen seit 2026-11-03 in
`docs/ROADMAP.md`, Abschnitt "Aus STATUS.md (Loop-Queue)".


## Roadmap 2026-11 (User-Direktive 2026-11-10)

**Phase 1 — UI ready fuer die eigentliche Arbeit**

1. OP-381c — Gate-Modal-Redesign (Vollbild, Copy, strukturiert)
2. OP-381b — Freitext-Gate (plan_reason im Modal)
3. OP-306  — 3 Modi: Wasserfall + Debug + Cockpit
4. OP-306b — Etappe 2-4: Startseite / Overview
5. Interfaces — Verify/CI-Status, Rollen-Details, Debug-Ansicht

**Phase 2 — Loop stabilisieren, mit UI im Betrieb**

6. OP-382  — Dogfooding: 10x echte OPs durch die UI
7. Debugger-Modus als wichtigstes Werkzeug (Kette fertig machen)
8. Loop zuverlaessig: konstant Erfolge, keine Abbrueche

**Phase 3 — Kernarbeit am Loop**

9. Erst wenn Phase 2 gruen: Selbstverbesserung (OP-376-379),
   Memory-Graph (OP-380), Gehirn (OP-220 ff.)

**Regel:** Phase 3 ist gesperrt bis Phase 2 nachweislich stabil ist.
Die Kette selbst ist in Phase 2 fertig zu bauen — sie ist heute
noch nicht vollstaendig.

---

## Offene Punkte

### OP-396: Chat als projektbezogene Hauptoberflaeche
- **Status:** open
- **Typ:** ui-orchestration
- **Betroffene Dateien:** `werkstatt/chat_agent.py`, `werkstatt/chat_tools.py`, `werkstatt/web/app.py`, `static/chat.js`, `static/layout.css`, Chat- und Web-Tests
- **Problem:** Der Chat ist read-only und getrennt von der Loop-Steuerung. Projektfragen sollen natuerlich formuliert werden koennen; der Chat muss das Repo untersuchen, Belege liefern, Aktionen verstaendlich erklaeren und waehrend eines Runs ansprechbar bleiben. Schreibende Aktionen erfordern eine ausdrueckliche Freigabe im Chat, bevor Aenderungen ausgefuehrt werden.
- **Akzeptanzkriterien:**
  - Chat ist in Cockpit, Control und Debug der primaere, dauerhaft sichtbare Interaktionspunkt.
  - Repo-Antworten verwenden projektgebundene Tools und nennen Datei/Zeile oder konkreten Run-/Test-Beleg.
  - Der Chat kann explizit einen Loop starten, pausieren, fortsetzen oder stoppen; jede Aktion wird vor Ausfuehrung angezeigt und auditiert. UI und Chat zeigen Erfolg, Ablehnung, laufenden Zustand und Fehler direkt sichtbar.
  - Vor jeder schreibenden Chat-Aktion fragt das System nach ausdruecklicher Freigabe; die Freigabe gilt nur fuer die konkret beschriebene Aktion und ihren Umfang.
  - Das Plan-Gate ist immer verpflichtend und darf weder per CLI-Flag noch Projektkonfiguration automatisch bestaetigt oder deaktiviert werden. Auch Chat-Freigabe ersetzt dieses Gate nicht; der Scout-No-Op-Pfad muss den Befund ebenfalls vor dem Ergebnis-Gate freigeben lassen.
  - Code-Aenderungen durchlaufen weiterhin Verify, Review und das bestehende Human-Gate. Chat kann kein Gate implizit bestaetigen.
  - Lange Tool-Aufrufe blockieren weder Loop-Prozess noch weitere Chat-Nachrichten.
- **Tests:** Projekt-Isolation, Belegdarstellung, explizite Loop-Kontrolle, Human-Gate-Invariante und Chat waehrend aktivem Run.
- **Blockiert von:** —

### OP-397: Hintergrundjobs, Projekt-Inbox und Checkpoint-Steuerung
- **Status:** open
- **Typ:** async-jobs
- **Betroffene Dateien:** `werkstatt/web/app.py`, `werkstatt/event_store.py`, `werkstatt/projection.py`, `static/chat.js`, `static/live_feed.js`, WebSocket-/Event-Tests
- **Problem:** Ein synchroner Chat-Request kann lange Repo-Pruefungen an die Verbindung binden. Nutzer muessen Zweck, Fortschritt und Ergebnis jeder Hintergrundaktion sehen und waehrenddessen weiterfragen sowie neue Arbeit einreichen koennen.

- **Steuerungsmodell bei aktivem Run:**
  - Lesende Chatfragen laufen unabhaengig vom Loop und duerfen ihn nicht blockieren oder seinen Plan veraendern.
  - Neue Aufgaben werden als persistente Projektjobs mit Status `queued` aufgenommen. Der Chat kann sie analysieren; schreibende Arbeit wartet auf den exklusiven Projekt-Schreibslot.
  - Eine Aenderung am laufenden Auftrag ist ein eigener `run_change_request`, kein stilles Editieren des freigegebenen Plans. Am naechsten sicheren Task-Checkpoint pausiert der Loop; der Chat zeigt neue Ziele, Umfang, betroffene Dateien und Verify-Folgen. Erst ein erneutes ausdrueckliches Plan-Gate darf eine versionierte Planrevision aktivieren.
  - Abgelehnte oder abgelaufene Planrevisionen veraendern weder freigegebenen Plan noch Working Tree; der Mensch kann den bisherigen Run fortsetzen oder stoppen.

- **Akzeptanzkriterien:**
  - Lange Diagnose- und Verify-Aufgaben erhalten stabile Job-IDs und laufen ausserhalb des Chat-Request-Lifecycles.
  - Job-Events verknuepfen Projekt, Chat-Session und optional run_id; Fortschritt, Erfolg, Fehler, Abbruch und Replay sind persistent und nach Reconnect lesbar.
  - Doppelte Requests mit gleicher Idempotency-Key erzeugen keinen doppelten Job; Session-Turns werden gegen konkurrierende Schreibzugriffe serialisiert.
  - Chat-Nachrichten koennen waehrend aktivem Loop und Hintergrundjob unabhaengig beantwortet werden.
  - Jede Aktion zeigt im Chat und in der UI sofort Status, Ergebnis oder konkreten Fehler; Konsolen-Logs allein genuegen nicht.
  - Pro Projekt gibt es hoechstens einen schreibenden Loop-Run; lesende Diagnosejobs duerfen parallel laufen.
  - Tests decken Job-Lifecycle, Reconnect/Replay, Idempotenz, Parallelitaet, Abbruch, Checkpoint-Pause, Planrevision mit neuem Human-Gate sowie Ablehnung ohne Working-Tree-Aenderung ab.
- **Stand 2026-11-10:** Chatjobs haben persistente Session-Serialisierung, FIFO, Worker-Lease-Recovery, Idempotenzkonflikte, Reconnect fuer Fehler und kooperativen Abbruch. Fuer laufende Streams wird der Abbruch an SSE-Chunk-Grenzen verarbeitet; bei stiller Verbindung begrenzt ein 30-Sekunden-Read-Timeout die Wartezeit. Noch offen sind u.a. Run-/Event-Store-Verknuepfung, Chat parallel zum aktiven Loop, Projekt-Schreibslot und Checkpoint-gesteuerte Planrevision.
- **Blockiert von:** —

### OP-398: Evidenzbasierte Auswahl autonomer Arbeit
- **Status:** open
- **Prioritaet:** P1
- **Typ:** loop-autonomy
- **Betroffene Dateien:** `werkstatt/loop.py`, `werkstatt/planner.py`, `werkstatt/web/app.py`, STATUS-Parser, Selector- und Loop-Tests
- **Problem:** STATUS ist eine menschenlesbare Arbeitsliste, aber Zeilenreihenfolge ist keine ausreichende Auswahlstrategie. Der Web-Start-Endpunkt verspricht eine naechste OP-Auswahl ohne Aufgabentext; der Loop muss diese Auswahl nachweisbar und sicher treffen.
- **Akzeptanzkriterien:**
  - Die erste Selector-Stufe fuer den Web-Start waehlt ausschliesslich einen einzelnen, eindeutig startfaehigen OP mit Status `open`, aufgeloesten Blockern, dokumentierten Akzeptanzkriterien und konkretem Test/Nachweis; wenn mehrere Kandidaten passen oder ein Status widerspruechlich ist, wird kein Run gestartet und der Chat erhaelt strukturierte Kandidaten samt Gruenden.
  - Direkte Nutzeraufgabe hat Vorrang vor einer optional mitgesendeten OP-ID; eine explizit gewaehlte OP bleibt direkt startbar.
  - Auswahlentscheidung, Kandidaten und Ausschlussgruende sind als strukturierte API-Antwort sichtbar und die autonome Auswahl wird auditiert; ein automatischer Start durchlaeuft weiterhin das verpflichtende Plan-Gate.
  - Der Selector bildet ausschliesslich explizite, offene OPs mit erfuellten Abhaengigkeiten als Kandidaten und kann eng verwandte OPs zu einem gemeinsam begrenzten, verifizierbaren Arbeitsblock buendeln.
  - Direkter Nutzerauftrag oder ausgewaehlte OP haben Vorrang vor autonomer Auswahl. Eine OP-Buendelung nennt gemeinsamen Zweck, Reihenfolge, Abhaengigkeiten und Abbruchgrenzen und wird vor Ausfuehrung im Plan-Gate freigegeben.
  - Ranking-Begruendung nennt Prioritaet, Relevanz zum Projektziel, Risiko und verfuegbare Verifikation; Ergebnis wird auditiert.
  - Bei Gleichstand, fehlenden Akzeptanzkriterien, veralteten Blockern oder widerspruechlichem Status wird nicht geraten: Kandidaten werden erklaert und der Chat fragt nach.
  - Erfolg des gesamten Arbeitsblocks wird nur nach Verify/Review mit Referenzen auf Run und Commit als abgeschlossen markiert; Teilerfolge und ungelöste OPs bleiben getrennt sichtbar. Fehlschlaege aktualisieren Versuch/Blocker, nicht den Abschlussstatus.
  - Runs haben begrenzte Versuche, Checkpoints und klare Stop-Bedingungen; parallele Schreib-Runs fuer dasselbe Projekt sind gesperrt.
- **Tests:** Parser/Statusvarianten, Dependency-Aufloesung, Ranking, Ambiguitaet, Fail-closed und Abschlussbelege.
- **Blockiert von:** —


### OP-281: Scout-Redundanz messen vor Umbau
- **Status:** open
- **Blockiert von:** OP-385 (Scout-Kette reparieren — Messung erst sinnvoll wenn Architect nur Scout-Output sieht)
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
  braucht) ist moeglicherweise leer -> Scout-Redundanz-Analyse (OP-281)
  hat keine Basis.
- **Naechster Schritt:** Pruefen ob `explorer_result` noch erreicht wird;
  falls nicht, Event wieder aktivieren oder durch `explorer_messung_findings`
  ersetzen (semantisch gleich?). Kein sofortiger Fix.

### OP-282: Werkzeug fuer Roadmap-to-OP Compiler

- **Status:** open
- **Beschreibung:** Baut das Werkzeug `werkstatt/roadmap_compiler.py`, das wie in Phase 31
  beschrieben, die naechste ROADMAP-Phase liest und automatisch in STATUS.md-OPs uebersetzt.
- **Betroffene Dateien:** `werkstatt/roadmap_compiler.py` (neu), `tests/test_roadmap_compiler.py` (neu)
- **Akzeptanzkriterien:** CLI-Tool, das den Architect aufruft, die Ausgabe validiert
  (OP-NNN, Akzeptanzkriterien vorhanden) und die OPs formatiert in STATUS.md einfuegt.
- **Tests:** Unit-Tests fuer die Validierungs-Logik und den Parser der Roadmap.
- **Blockiert von:** —

### OP-280: Doku-Drift als Verify-Gate (deterministisch)

- **Status:** open
- **Beschreibung:** `tools/doku_check.py` prueft bisher nur
  bereits committete Historie. Eine Verify-Stage vor dem Commit muss
  zusaetzlich staged, unstaged und untracked Aenderungen im aktuellen
  Working Tree pruefen; sonst kann sie den gerade entstehenden Patch
  nicht absichern. Code-Aenderungen ohne Doku-Aenderung blockieren den
  Commit. Die Commit-Historie bleibt eine zusaetzliche Drift-Diagnose.
  Ausnahmen fuer Commit-Subjects (`docs(`, `test(`, `ci(`,
  [skip-doku]) gelten nur fuer die Historienpruefung.
  Ziel: Doku-Pflege ist strukturell erzwungen, nicht Erinnerung des
  Menschen. Begruendung: der Loop liest seine Queue aus docs/STATUS.md.
  Wenn dort stale OPs stehen (Beispiel 2026-11-03: Chat-Agent
  empfahl OP-084/085, obwohl beide bereits durch 82502f0..98a53d3
  erledigt waren), arbeitet der Loop gegen Phantom-Eintraege.
- **Betroffene Dateien:** `.werkstatt/verify.json` (harte
  `phase_end`-Stage `doku_drift`), `tools/doku_check.py`,
  `tests/test_doku_check.py`, `AGENTS.md`.
- **Akzeptanzkriterien:** (a) Verify-Stage ruft
  `python3 tools/doku_check.py --strict --limit 5 --worktree` in
  `phase_end` auf, nach allen Builder-Tasks und vor dem Commit.
  (b) Staged, unstaged und untracked Code-Aenderungen ohne
  Doku-Aenderung blockieren. Geloeschte Doku allein gilt nicht als
  Update. (c) Historienpruefung behaelt die Ausnahmen `docs(`,
  `test(`, `ci(`, `[skip-doku]`). (d) Tests decken Code-only,
  Code-plus-Doku, geloeschte Doku, untracked Code und die vier
  Historienfaelle ab. (e) `python3 tools/doku_check.py --strict
  --limit 5 --worktree` auf dem Werkstatt-Repo ist gruen.
- **Tests:** `pytest tests/test_doku_check.py -v`
- **Blockiert von:** —

### OP-260: Loop-Agenten mit explizitem Kontext-Vertrag (Sammel-OP)

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

### OP-266: Phase 33.2b — verify-Migration nach control/ (gross)

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

### OP-220: Erfahrungs-Gehirn — deterministisches Fehler-Gedaechtnis (Sammel-OP)

- **Status:** open
- **Phase:** Phase-3; erst nach Abschluss von OP-382 beginnen
- **Blockiert von:** OP-382
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

### OP-220a: erfahrung-Tabelle um scope-Spalte erweitern

- **Status:** open
- **Typ:** feature (Erfahrungs-Gehirn, Sub-OP zu OP-220)
- **Betroffen:** `werkstatt/erfahrung.py` (neu, siehe OP-220)
- **Problem:** ADR-0010 legt zweistufige Memory fest. OP-220 legt
  Basis-Tabelle `erfahrung` an, aber ohne `scope`-Spalte. OP-221
  (Destillation), OP-222 (Semantic Memory) und OP-220i (Log-Backfill)
  brauchen `scope TEXT NOT NULL DEFAULT 'projekt'` als Voraussetzung.
- **Akzeptanzkriterien:**
  - `erfahrung`-Tabelle hat Spalte `scope TEXT NOT NULL DEFAULT 'project'`,
    CHECK auf `scope IN ('project','global')` entsprechend ADR-0010.
  - Alle bestehenden Inserts setzen explizit `scope='projekt'`.
  - Migration idempotent (ALTER TABLE nur wenn Spalte fehlt).
  - 2 Tests: Insert mit/ohne scope, Constraint-Verletzung.
- **Tests:** `tests/test_erfahrung.py::test_scope_default`,
  `tests/test_erfahrung.py::test_scope_constraint`
- **Blockiert von:** OP-220
- **Quelle:** `docs/adr/ADR-0010-memory-zweistufig.md`


### OP-240: Chat-Modus Debugger (evidence-first, Ladder)

- **Status:** open
- **Typ:** feature
- **Betroffen:** `werkstatt/chat_agent.py` (`chat_loop`),
  `werkstatt/chat_tools.py`, `werkstatt/web/static/chat.js`
- **Problem:** Bei fehlgeschlagenem Run oder offenem Gate soll der Chat dem Menschen eine **Eskalations-Ladder** und direkte Kontextuebergabe anbieten. Der Chat entscheidet nichts und beantwortet keine Gates. Der Mensch waehlt Diagnose, Patch-Uebergabe oder Loop-Neustart. Der Debugger ist eine Faehigkeit des Chats (Modus `debugger`), keine eigene Loop-Rolle (ADR-0011/0029; ADR-0018 verworfen).

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
    `werkstatt/`. Debugger schreibt Produktionscode nicht direkt.
    Der strukturierte Fix kann nach Anzeige des exakten Diffs und
    einmaliger ausdruecklicher Freigabe ohne Copy/Paste als Auftrag
    an den Coding-Loop uebergeben werden; verpflichtendes Plan-Gate,
    Verify, Review und Human-Gate bleiben erhalten (ADR-0029).
    **Nach erfolgreicher Verifikation (Loop-Re-Run gruen):**
    Lern-Event `debugger_fix_verifiziert` → Memory-Hook (OP-243).
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
  - (g) Aktion „Datei bearbeiten“ an einem offenen Gate uebergibt
    Projekt, run_id, gate_id, Fehler-/Verify-Belege und betroffene
    Datei an den Debug-Chat. Das Gate bleibt offen; Chat-Text oder
    Patch-Freigabe beantwortet es nicht. Nur eine separate explizite
    Gate-Antwort setzt den Lauf fort.
  - (h) Nach ausdruecklicher Freigabe uebergibt der Chat den exakten
    strukturierten Patch samt Projekt- und Run-Kontext maschinenlesbar
    an den Coding-Loop. Kein manueller Copy/Paste-Schritt und kein
    vom Chat frei formulierter Ersatzauftrag. Freigabe ist einmalig
    und an Patch-Hash/Umfang gebunden.

- **Tests:** `tests/test_chat_debugger.py` (neu),
  `tests/test_debugger_memory_hook.py` (neu, OP-243)
- **Blockiert von:** —
- **Lern-Hook:** OP-243 (Debugger → Memory)

### OP-221: Memory-Destillation + Promotion (scope-aware)

- **Status:** open
- **Typ:** feature (Erfahrungs-Gehirn)
- **Betroffen:** `werkstatt/erfahrung.py`, `tools/memory_destill.py`
  (neu), `tools/memory_promote.py` (neu),
  `tools/memory_drift.py` (neu)
- **Problem:** OP-220 speichert Episoden, destilliert aber keine Regeln,
  konsolidiert nicht, promotet nicht. Ergebnis: derselbe Fehler
  wiederholt sich. Zusaetzlich fehlt eine projektuebergreifende Ebene —
  Antipatterns wie `# type: ignore` sind universell, werden aber pro
  Projekt neu gelernt.
- **Akzeptanzkriterien:**
  - Tabelle `regeln(id, titel, trigger, anweisung, trust, scope,
    beobachtungen_json, quelle_episoden, erstellt_am, letzte_nutzung,
    widerlegt)`. Trust in {candidate, confirmed, canonical};
    scope in {project, global}.
  - OP-220a erweitert die `erfahrung`-Tabelle um `scope TEXT NOT NULL
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
- **Blockiert von:** OP-220a

### OP-222: Semantic Memory (Projekt-Fakten + globale Praeferenzen)

- **Status:** open
- **Typ:** feature (Erfahrungs-Gehirn)
- **Betroffen:** `werkstatt/erfahrung.py`,
  `projects/<name>/profile.yaml`, `werkstatt/chat_tools.py`
- **Problem:** Chat muss Basics per grep herausfinden (Test-Runner,
  DB-Typ, Migrationspfad). OP-220 speichert nur Fehler-Episoden.
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
- **Blockiert von:** OP-220a

### OP-250: Loop-Memory-Panel (was das Gehirn gelernt hat)

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
- **Blockiert von:** OP-221, OP-222

### OP-242: "Why did it fail?"-Button (Repair Ladder)

- **Status:** open
- **Typ:** ui-feature
- **Betroffen:** `werkstatt/web/static/timeline.js`,
  `werkstatt/web/static/chat.js`, `werkstatt/web/app.py`
- **Problem:** Bei fehlgeschlagenem Run muss der User manuell
  entscheiden, was zu tun ist. Es fehlt eine eskalierende
  Handlungsleiter — drei Stufen, die in Sekunden beginnen und bis zum
  vollen Loop reichen.
- **Siehe auch:** OP-306 (Mode-Switch), OP-308 (Focus-View)
- **Akzeptanzkriterien:**
  - Nach `run_failed`-Event erscheint in Timeline und/oder Chat ein
    Banner: "Run #N fehlgeschlagen (OP-M, X/Y Tasks)" mit drei Buttons.
  - Button 1 **„Chat analysiert"**: sendet automatisch Nachricht an
    Chat-Agent (OP-231) mit Auftrag: "Analysiere Run #N: Audit-Logs,
    Diff, Fehlerursache. Antwort in Sekunden."
  - Button 2 **„Debugger starten"**: startet Chat im Modus
    `debugger` (OP-240) mit identischem Diagnose-Auftrag und bindet
    Run, Gate, betroffene Datei und Fehlerbelege als Kontext.
  - Bei Auswahl **„Datei bearbeiten"** an einem offenen Gate wird
    derselbe strukturierte Gate-Kontext an den Debug-Chat uebergeben;
    das Gate bleibt offen und wartet auf eine separate Gate-Antwort.
  - Button 3 **„Coding-Loop neu"**: startet neuen Loop-Lauf mit
    identischer `--aufgabe` (Wiederholung nach Fix, falls manuell
    durchgefuehrt).
  - Eine vom Menschen freigegebene Debugger-Aenderung wird als
    strukturierter Patch-Inhalt direkt an den Coding-Loop uebergeben;
    kein Copy/Paste und kein automatisches Beantworten des Gates.
  - Test: Mock-Event `run_failed` → Panel rendert drei Buttons;
    Klick auf Button 1 → `POST /api/projects/{name}/chat` mit
    erwarteter Nachricht.
- **Tests:** keine (UI, visuell)
- **Blockiert von:** OP-240

### OP-283: Cost/Token-Dashboard

- **Status:** open
- **Typ:** ui-feature
- **Betroffen:** `werkstatt/web/static/stats.js` (neu),
  `werkstatt/web/app.py` (`/api/stats/*`),
  `werkstatt/state.py` (bereits `llm_calls`), `werkstatt/agent.py`
- **Problem:** Token-Verbrauch und Kosten sind im Terminal nur als
  Gesamt-Budget sichtbar. DSH und OpenHands zeigen per-Model,
  per-Phase, per-Tool aufgeschluesselt. Wir haben `state.llm_calls`,
  aber keine UI und keine Aggregation.
- **Siehe auch:** OP-301 (Ambient Status Bar — Basis-Token-Anzeige), OP-307 (Tool-Call-Karten — per-Tool Detail)
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

### OP-261: `state/` Submodul-Split (RunState aufteilen)

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

### OP-262: `cli/` + Re-Export-Bereinigung

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

### OP-263: State-Contract fuer auftrag_bereits_erfuellt-Familie

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

### OP-257: Reflection-Verdrahtung (kleine Luecken)

- **Status:** open
- **Typ:** architektur (klein, komplementaer zu OP-220/129/130/131)
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

### OP-264: Planner-Dependencies deterministisch aus Prosa

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

### OP-265: Reviewer AUFTRAG-TREUE-Check bei Rename-Aufgaben

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


### OP-294: Spec-Tests — RunState-Factory statt SimpleNamespace

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

### OP-255: Loop-PROGRESS.md-Format an DOC_CONVENTIONS §5 angleichen

- **Status:** open
- **Typ:** fix (Doku-Konsistenz)
- **Betroffen:** `werkstatt/progress.py` (`append_progress`,
  `PROGRESS_FILE`), `werkstatt/phases/finalize.py` (Z. 147-156
  `M-307b: Phasen-Ende in PROGRESS.md`), `tests/test_progress.py`
  (erweitern).
- **Problem:** Der Loop schreibt am Phasen-Ende
  `## 2026-11-07T13:23:18+00:00 -- Phase abgeschlossen: werkstatt`
  mit `- **Status:** phase_ende`. Menschliche OP-Eintraege sind
  `### YYYY-MM-DD — OP-NNN abgeschlossen: Titel`. Zwei Formate in
  derselben Datei. Siehe PROGRESS.md-Ende nach OP-181-Close.
- **Akzeptanzkriterien:**
  - **Format (a):** Wenn `state.aufgabe` einen OP-Header enthaelt
    (`### OP-NNN: ...`, Regex wie im Loop-Startbefehl), schreibt
    `_phase_end_progress`-Pfad
    `### YYYY-MM-DD — OP-NNN abgeschlossen: <op-titel>` +
    Fliesstext. Sonst Fallback auf das bestehende
    `## ISO-Timestamp -- Phase abgeschlossen`.
  - **Verdrahtung (b):** `phases/finalize.py:147` reicht
    `state.aufgabe` an `progress.append_progress` weiter
    (oder ermittelt OP-NNN selbst per Regex).
  - **Test (c):** `tests/test_progress.py`:
    (i) mit OP-Aufgabe -> `### YYYY-MM-DD — OP-NNN abgeschlossen`;
    (ii) ohne OP-Aufgabe -> `## ISO-Timestamp -- Phase abgeschlossen`;
    (iii) idempotent (kein Duplikat bei zweitem Aufruf).
  - `pytest` gruen.
- **Tests:** `tests/test_progress.py` (erweitern).
- **Blockiert von:** —
- **Blockiert:** —
- **Prioritaet:** mittel — kosmetisch, aber Doku-Drift ist der
  naechste Kandidat fuer OP-280.
- **Quelle:** OP-181-Close (2026-11-07, Commit `5529df6`).

### OP-256: Loop-Push-Option (`--auto-push` / `--no-push`)

- **Status:** open
- **Typ:** feature (Loop-Ergonomie)
- **Betroffen:** `werkstatt/loop.py` (CLI-Args),
  `werkstatt/phases/finalize.py` (Commit-Pfad),
  `werkstatt/git_ops.py` (`push`-Funktion, falls fehlt),
  `tests/test_loop_push.py` (neu).
- **Problem:** `grep 'git push' werkstatt/` liefert 0 Treffer. Der
  Loop committet lokal, der Push ist komplett manuell. Jeder
  erfolgreiche Loop-Lauf erzeugt Reibung: User muss nach dem
  Commit-Gate manuell `git push` tippen. Bei Loop-Tests ist das
  in Ordnung, im Alltag Unterbrechung.
- **Akzeptanzkriterien:**
  - **CLI (a):** `--auto-push` (Default: **aus**, opt-in) und
    `--no-push` (Default-Wert fuer Rueckwaerts-Kompatibilitaet).
    Beide Parameter in `loop.py`-`argparse`.
  - **Push-Pfad (b):** Nach erfolgreichem Commit-Gate
    (Approved `j`) ruft der Loop `git push origin <branch>`
    via `git_ops.push(pd)` auf, aber **nur wenn `auto_push=True`**.
    Bei Fehler (non-zero rc): Audit-Event `loop_push_failed`,
    aber Loop **bricht nicht ab** (Commit bleibt gueltig,
    Push ist nachholbar).
  - **Test (c):** `tests/test_loop_push.py`:
    (i) Default-Verhalten: kein Push-Aufruf;
    (ii) `--auto-push`: Push-Aufruf nach Commit;
    (iii) Push-Fehler: Loop laeuft weiter, Audit-Event geschrieben.
  - **Doku (d):** `docs/ARCHITECTURE.md`-Abschnitt „Loop-CLI"
    ergaenzt die zwei Flags (Architektur-Doku ist Wahrheit).
  - `pytest` gruen, keine neuen ruff/mypy-Fehler.
- **Tests:** `tests/test_loop_push.py` (neu).
- **Blockiert von:** —
- **Blockiert:** —
- **Prioritaet:** mittel — Ergonomie, aber explizite User-Entscheidung
  noetig (Default-Verhalten darf sich nicht still aendern).
- **Quelle:** OP-181-Close (2026-11-07), `grep 'git push' werkstatt/`
  leer.

### OP-210: Test-Loop-Phase mit Qualification und Freeze

- **Status:** open
- **Typ:** architektur (Tests + Spec)
- **Betroffen:** `werkstatt/phases/test_loop.py` (neu),
  `werkstatt/test_agent.py` (neu), `werkstatt/loop.py`
  (Phase einhaengen), `werkstatt/state.py` (`test_spec` +
  `test_manifest`), `tests/test_test_agent.py` (neu),
  `tests/test_phase_test_loop.py` (neu).
- **Problem:** ADR-0016 umsetzen. Tests werden heute im selben
  LLM-Call wie der Code gebaut — Code und Test bestaetigen sich
  gegenseitig, aber Spec-Abweichungen bleiben unsichtbar
  (Loop-Test 9, OP-181, OP-183). Der Benchmark 2026-11-07 zeigt
  3/18 ueberlebende Mutanten auf einem Mini-Modul.
- **Akzeptanzkriterien:**
  - **(a)** `state.test_spec` wird von `run_architect` befuellt
    (Block 6 im `ARCHITECT_SYSTEM`: `[{name, target_file,
    assertion_prose}]`).
  - **(b)** Test-Agent baut Test-Datei aus `test_spec`, keine
    Code-Interna.
  - **(c)** Qualification: Test auf unveraendertem Repo MUSS rot
    sein (sonst testet er den Ist-Zustand).
  - **(d)** Freeze: SHA256 in `state.test_manifest`.
  - **(e)** Max 2 Runden, dann `_phase_review_gate`.
  - **(f)** Tests fuer (a)-(e).
  - **(g)** Test-Thaw-Mechanik integriert (siehe OP-213):
    bei Test-Bug `state.test_thawed=True`,
    `state.test_manifest={}`, Audit `test_thawed`,
    zurueck zu Phase 2b.
  - **`pytest` gruen, ruff/mypy 0.**
- **Tests:** `tests/test_test_agent.py` (neu),
  `tests/test_phase_test_loop.py` (neu).
- **Blockiert von:** OP-260 (Context-Vertrag), OP-201
  (pyproject `test-tools` optional-dependencies).
- **Blockiert:** OP-211.
- **Prioritaet:** hoch.
- **Quelle:** ADR-0016 (2026-11-07), Loop-Test 9/10, Benchmark
  /tmp/mutbench.

### OP-211: Builder test-blind + verify-Stages test_integrity/must_fail

- **Status:** open
- **Typ:** architektur (Tests + Spec)
- **Betroffen:** `werkstatt/roles/builder/run.py` (Filter),
  `.werkstatt/verify.json` (2 neue Stages),
  `tools/test_integrity.py` (neu),
  `tools/test_must_fail.py` (neu),
  `tests/test_builder_test_blind.py` (neu).
- **Problem:** Builder sieht heute Test-Dateien im Prompt, wenn
  `task_files` sie enthaelt. Zusaetzlich fehlen verify-Stages,
  die SHA256 des Test-Manifests pruefen und die Qualification
  erzwingen.
- **Akzeptanzkriterien:**
  - **(a)** Builder filtert `tests/` und `test_*.py` aus
    `task_files`. Wenn nach Filter leer: fail-closed mit Audit
    `builder_test_file_rejected`.
  - **(b)** Stage `test_integrity` failt bei Hash-Mismatch
    (`state.test_manifest` vs. aktuelle Test-Dateien).
  - **(c)** Stage `test_must_fail_initial` failt bei gruenem Test
    auf unveraendertem Repo.
  - **(d)** Tests fuer (a)-(c).
  - **`pytest` gruen.**
- **Tests:** `tests/test_builder_test_blind.py` (neu),
  `tests/test_verify_test_stages.py` (neu).
- **Blockiert von:** OP-210.
- **Blockiert:** OP-214.
- **Prioritaet:** hoch.
- **Quelle:** ADR-0016.


### OP-214: Mutation-Gate als verify-Stage

- **Status:** open
- **Typ:** architektur (Tests + Qualitaet)
- **Betroffen:** `.werkstatt/verify.json` (1 neue Stage),
  `pyproject.toml` (`[tool.pytest-gremlins]`),
  `tests/test_mutation_gate_stage.py` (neu).
- **Problem:** Test-Qualitaet wird heute nicht mechanisch
  gemessen. Ein gruener Test kann unvollstaendig sein.
- **Akzeptanzkriterien:**
  - **(a)** Stage `mutation_gate` in `verify.json` mit
    `hart: false`.
  - **(b)** `pytest-gremlins` laeuft auf geaenderte Files
    (`paths` dynamisch pro Task gesetzt).
  - **(c)** Score < 0.8: Audit `mutation_gate_low_score`,
    kein Hard-Block in Runde 1.
  - **(d)** Nach 4 Wochen: auf `hart: true` pruefen (eigene OP).
  - **(e)** Tests fuer (a)-(c).
  - **`pytest` gruen.**
- **Tests:** `tests/test_mutation_gate_stage.py` (neu).
- **Blockiert von:** OP-211, OP-201.
- **Blockiert:** —
- **Prioritaet:** mittel.
- **Quelle:** ADR-0017, Benchmark 2026-11-07.

### OP-213: Test-Thaw-Mechanik (an OP-210 gekoppelt)

- **Status:** open
- **Typ:** architektur (Tests + Spec)
- **Betroffen:** `werkstatt/phases/test_loop.py` (neu, via OP-210),
  `werkstatt/phases/tasks.py` (Thaw-Trigger),
  `tests/test_test_thaw.py` (neu).
- **Problem:** Wenn ein eingefrorener Test sich als falsch
  herausstellt (Code = Spec, Test != Spec), muss der Test
  auditierbar invalidiert werden. Heute gibt es keinen
  Mechanismus dafuer.
- **Akzeptanzkriterien:**
  - **(a)** Test-Thaw invalidiert `state.test_manifest`.
  - **(b)** Audit-Event `test_thawed` mit Grund und
    betroffener Test-Datei.
  - **(c)** Test-Loop startet neu nach Thaw.
  - **(d)** `state.test_thawed=True` bis zur naechsten
    Qualification.
  - **(e)** Tests fuer (a)-(d).
  - **`pytest` gruen.**
- **Tests:** `tests/test_test_thaw.py` (neu).
- **Blockiert von:** OP-210 (Test-Loop-Phase).
- **Blockiert:** —
- **Prioritaet:** hoch.
- **Quelle:** ADR-0016, Chat-Debugger (OP-240) als Thaw-Trigger.

### OP-215: Hypothesis als optionale Dependency + erste Property-Tests

- **Status:** open
- **Typ:** architektur (Tests + Qualitaet)
- **Betroffen:** `pyproject.toml`
  (`[project.optional-dependencies].test-tools`),
  `tests/conftest.py` (CI-Profil),
  `tests/test_property_planner.py` (neu),
  `tests/test_property_reflection.py` (neu).
- **Problem:** Property-Based-Tests fehlen komplett. Fuer
  deterministische Funktionen (JSON-Repair, Signatur-
  Normalisierung, Task-Klassifikation) sind sie ideal.
- **Akzeptanzkriterien:**
  - **(a)** `pip install -e ".[test-tools]"` installiert
    `hypothesis`.
  - **(b)** 3 Property-Tests: `_parse_json_robust`,
    `_fehler_signatur_normalisiert`, `_ist_verify_task`.
  - **(c)** CI-Profil in `tests/conftest.py` mit
    `derandomize=True, max_examples=10`.
  - **(d)** Tests fuer (a)-(c).
  - **`pytest` gruen.**
- **Tests:** `tests/test_property_planner.py` (neu),
  `tests/test_property_reflection.py` (neu).
- **Blockiert von:** OP-201.
- **Blockiert:** —
- **Prioritaet:** mittel.
- **Quelle:** ADR-0016, Benchmark 2026-11-07.

### OP-216: Architektur-Doku an Test-Loop und Chat-Debugger angleichen

- **Status:** open
- **Typ:** doku
- **Betroffene Dateien:** `docs/ARCHITECTURE.md`, `docs/SOLL.md`,
  `docs/adr/README.md`.
- **Problem:** Die OP-Beschreibung basiert teilweise auf ADR-0018,
  das verworfen wurde. Die akzeptierte Architektur behandelt Debugging
  als Chat-Modus (ADR-0011/0029), nicht als eigene Loop-Rolle. Die
  Architektur-Doku muss IST und Zielbild sauber trennen.
- **Akzeptanzkriterien:**
  - **(a)** `docs/ARCHITECTURE.md` dokumentiert die Test-Loop mit
    Qualification, Freeze und Test-Blindheit als implementierten IST
    nur, soweit OP-210/211 dies belegen; verbleibendes Zielverhalten
    ist als SOLL markiert.
  - **(b)** Debugging ist als Chat-Modus nach ADR-0011/0029 beschrieben:
    Reproduktion, ausschliesslich temporaere Tests, strukturierter
    Patch, einmalige Freigabe und Uebergabe an den normalen Loop mit
    Plan-Gate, Verify, Review und Human-Gate.
  - **(c)** Es wird keine separate `debugger`-Loop-Rolle erfunden;
    der Rollen-Registry-Abschnitt bleibt auf tatsaechlich registrierte
    Rollen beschraenkt.
  - **(d)** `docs/SOLL.md` beschreibt noch nicht implementierte
    Test-Loop-/Debugger-Faehigkeiten als Ziel, nicht als IST.
  - **(e)** ADR-Index stimmt mit den ADR-Statusfeldern ueberein
    (ADR-0016/0017 proposed; ADR-0018 rejected).
- **Tests:** keine — Doku-Konsistenz gegen ADR-0011/0016/0017/0018/0029.
- **Blockiert von:** OP-210, OP-211, OP-240.
- **Prioritaet:** mittel.
- **Quelle:** ADR-0011/0016/0017/0018/0029.

### OP-217: Test-Agent-Spec-Qualitaet (Verhalten statt Config)

- **Status:** open
- **Typ:** architektur (Tests + Spec-Qualitaet)
- **Betroffen:** `werkstatt/test_agent.py` (neu, via OP-210),
  `werkstatt/test_spec_validator.py` (neu, via OP-212),
  `tests/test_test_agent_spec.py` (neu).
- **Problem:** OP-201 (Loop-Lauf 19:46-19:56) zeigte: der
  Test-Agent prueft Config-Details, statt Spec-Verhalten.
  Drei Tests schrieben `pytest.ini`, `requirements.txt` und
  `--collect-only`-Smoke fest, statt AK-Verhalten abzubilden.
  Folge: Phase-Review rejected, Loop-Abbruch, manuelle
  Nachziehung. Das ist ein systematisches Muster, nicht
  OP-spezifisch.
- **Akzeptanzkriterien:**
  - **(a)** `test_spec`-Schema erweitert um
    `expected_behavior: str` und
    `verification: str` (public_api|cli_output|file_content).
  - **(b)** Test-Agent-Prompt-Regel: "Uebersetze AK in
    Verhalten. Config-Details sind Implementierungs-Detail,
    wenn AK sie nicht explizit fordert."
  - **(c)** Post-Test-Validation: Tests, die nur
    `pytest.ini`/`requirements.txt`/`.gitignore` pruefen und
    `verification='file_content'` mit
    `expected_behavior` fehlt → Audit
    `test_spec_smoke_test_verdacht`, Test-Loop-Runde 2.
  - **(d)** Config-Integritaets-Tests gehoeren in eigene
    Datei `test_config_integritaet.py`, Spec-Validierung
    prueft die Trennung.
  - **(e)** Tests fuer (a)-(d).
  - **`pytest` gruen.**
- **Tests:** `tests/test_test_agent_spec.py` (neu),
  `tests/test_test_spec_validator.py` (erweitern).
- **Blockiert von:** OP-210 (Test-Loop), OP-212 (Spec-Validator).
- **Blockiert:** OP-214 (Mutation-Gate) — indirekt, weil
  Mutation-Score sonst falsch (Config-Smoke-Tests sind nicht
  mutierbar).
- **Prioritaet:** hoch (Erkenntnis aus OP-201, echte
  Schwaechung des Test-Agents).
- **Quelle:** OP-201-Loop-Lauf 2026-11-07 19:46-19:56,
  ADR-0016-Nachtrag 2026-11-07.


### OP-212: Test-Spec-Validator (unabhaengige Pruefung der Architect-Spec)

- **Status:** partial (Code+Tests done, Verdrahtung in OP-210 offen)
- **Typ:** architektur (Tests + Spec-Validierung)
- **Betroffen:** `werkstatt/test_spec_validator.py` (neu),
  `werkstatt/phases/test_loop.py` (neu, via OP-210),
  `tests/test_test_spec_validator.py` (neu).
- **Problem:** Architect und Test-Agent sind beide LLMs, koennen
  dieselbe falsche Interpretation der Anforderung uebernehmen.
  Technisch korrekte Tests, die falsches Verhalten bestaetigen.
- **Akzeptanzkriterien:**
  - **(a)** `validate_test_spec(original_requirement, test_spec)
    -> ValidationResult` mit `{deckt_ab: bool, fehlende_ak: list,
    negativ_faelle_ok: bool, mehrdeutigkeiten: list}`.
  - **(b)** Eigenstaendiger LLM-Call mit eigenem Prompt (nicht
    Architect-Prompt), der Spec gegen Original-Anforderung prueft.
  - **(c)** Mehrdeutigkeiten fuehren zu Human-Gate VOR Test-Loop.
  - **(d)** `test_spec`-Struktur erweitert um
    `requirement_id`, `acceptance_criteria` (mit `id`, `condition`,
    `verification`), `negative_cases`.
  - **(e)** Tests fuer (a)-(d).
  - **`pytest` gruen.**
- **Tests:** `tests/test_test_spec_validator.py` (neu).
- **Blockiert von:** OP-210 (test_spec-Feld).
- **Blockiert:** OP-210 (Validator-Integration).
- **Prioritaet:** hoch.
- **Quelle:** ADR-0016 Nachtrag 2026-11-07, externer Review.

### OP-241: Debugger-Sandbox (isolierte Ausfuehrung temporaerer Tests)

- **Status:** open
- **Typ:** architektur (Sicherheit)
- **Betroffen:** `werkstatt/debugger_sandbox.py` (neu),
  `werkstatt/chat_tools.py` (Wiring),
  `tests/test_debugger_sandbox.py` (neu).
- **Problem:** `write_temp_test` schreibt nur nach
  `.werkstatt/temp_tests/`, aber temporaere Tests koennen sensible
  Dateien lesen, Netzwerk aufbauen, `.env` auslesen. Isolation
  fehlt.
- **Akzeptanzkriterien:**
  - **(a)** Temporare Tests laufen in isolierter Umgebung:
    eigener `tmp`-Root, `.env` nicht lesbar, kein Netzwerk
    (Loopback erlaubt).
  - **(b)** Allowlist fuer Umgebungsvariablen
    (`PATH`, `PYTHONPATH`, `WERKSTATT_IN_TEST`).
  - **(c)** Zeitlimit 30s pro Test, Speicherlimit 512 MB.
  - **(d)** Audit `debugger_sandbox_ok` / `debugger_sandbox_escape`
    mit Details.
  - **(e)** Tests fuer (a)-(d).
  - **`pytest` gruen.**
- **Tests:** `tests/test_debugger_sandbox.py` (neu).
- **Blockiert von:** OP-240 (Chat-Debugger).
- **Blockiert:** —
- **Prioritaet:** mittel (Sicherheits-Backstop, nicht Blocker).
- **Quelle:** Punkt 4 aus externem Review 2026-11-07.


### OP-372: Projection-Status-Diff vergleicht JSONL mit SQLite semantisch falsch

- **Status:** open
- **Typ:** bugfix
- **Phase:** Phase-2 (Focus)
- **Betroffene Dateien:** `werkstatt/projection.py` (`status`), `static/statusleiste.js` (Anzeige), `tests/test_projection.py`
- **Problem:** `Projector.status()` vergleicht `jsonl_events` (aktuelle Tagesdateien seit OP-320, ~33k) mit `sqlite_rows` (Gesamtzeilen inkl. Vor-OP-320-Migration, ~410k). Diff ist **immer** stark negativ (-377.834 am 2026-11-08). User sieht im UI bei 'Projection-Status' eine scheinbare Katastrophe, obwohl der Projector korrekt arbeitet. Ursache: Aepfel-mit-Birnen-Vergleich — `_count_jsonl()` zaehlt nur aktuelle Tagesdateien, SQLite enthaelt zusaetzlich die Vor-JSONL-Aera.
- **Akzeptanzkriterien:** (a) `status()` liefert zusaetzlich `jsonl_rows_seit_migration` (nur Zeilen ab dem ersten echten `last_audit_id`-Anker). (b) `diff` relativ zu dieser Basis, nicht zur SQLite-Gesamtsumme. (c) Felder `basis` und `vergleich_seit` fuer Nachvollziehbarkeit. (d) `static/statusleiste.js` zeigt nur den semantisch korrekten `diff`, roher SQLite-Count als Diagnose-Detail (nicht prominent). (e) Bestehende Tests bleiben gruen.
- **Tests:** `tests/test_projection.py` (2 Tests: status mit korrekter Basis, status ohne Migration).
- **Blockiert von:** —


### OP-374: security-ai ehrliche Anzeige + Backfill-Reproduzierbarkeit (Sammel-OP)

- **Status:** open
- **Typ:** bugfix (Sammel-OP, mehrere Teilpunkte)
- **Phase:** Phase-2 (Focus)
- **Betroffene Dateien:** `werkstatt/projection.py`, `werkstatt/web/inspector.py`, `tests/test_projection.py`, `tests/test_ambient_aggregation.py`
- **Problem (aus OP-373-Backfill 2026-11-08):** Nach dem Projekt-Backfill zeigt `aggregate_ambient('security-ai')` ehrliche aber verwirrende Werte. Vier zusammenhaengende Teilprobleme, die einzeln zu klein fuer eigene OPs sind:
  - **(a) `_letzter_run_id` filtert nicht:** `SELECT run_id ... ORDER BY seq DESC LIMIT 1` liefert `run_id=''` (Events ohne run_id dominieren chronologisch). Live: ambient('security-ai') zeigt `last_run.run_id=''` obwohl der letzte echte Run `20261018-223549-256043` ist.
  - **(b) Kein reproduzierbarer Backfill:** OP-373 wurde als einmaliges SQL ausgefuehrt. `Projector.backfill_project_from_jsonl()` als Methode fehlt. Bei kuenftigen Migrationen (z.B. wenn weitere Projekte auftauchen) muss der Backfill wieder manuell geschrieben werden.
  - **(c) 18.165 Events ohne run_id (18.10.-02.11.):** Loop-Bug vor OP-303 (`set_run_id()` wurde nicht aufgerufen). Information ueber Run-Zugehoerigkeit ist verloren — nicht rekonstruierbar. Muss ehrlich dokumentiert sein.
  - **(d) `ops_run_status` fuer pre-OP-303-Runs:** 0 OPs weil `pipeline_start.payload` kein `op_id` hat. Ehrliche Luecke, keine Regression. UI sollte das nicht als '0 Runs' zeigen, sondern 'vor OP-303, keine Zuordnung'.
- **Akzeptanzkriterien:**
  (a1) `_letzter_run_id` filtert `run_id IS NOT NULL AND run_id != ''`. Tests: bestehende Tests bleiben gruen, neuer Test `test_letzter_run_id_ignoriert_leere`. Live: ambient('security-ai').last_run.run_id = `20261018-223549-256043`.
  (b1) `Projector.backfill_project_from_jsonl()` als Methode: liest `agent-pipeline-*.jsonl`, baut `event_id -> project`-Map, `UPDATE events SET project=? WHERE event_id IN (...)`, idempotent. Tests: 3 (setzt-project, idempotent, wirft-bei-fremdem-project). Hinweis: `-migrated-*` wird von `_jsonl_files` bereits excludet (siehe a640b19).
  (c1) Doku-Klarstellung: `events` mit `run_id=''` sind pre-OP-303-Runs und werden in Sparklines/Ambient **nicht** als Runs gezaehlt. Keine automatische Rekonstruktion.
  (d1) `static/ambient_status.js` bei `gates_open=0 AND last_run=null AND pre_op303=True` zeigt Tooltip 'Vor OP-303, keine Run-Zuordnung' statt 'Idle'.
  (e1) `pytest tests/test_ambient_aggregation.py tests/test_projection.py` >1538 passed, ruff/mypy/Drifts gruen.
- **Tests:** `tests/test_ambient_aggregation.py` +1 (leere-run_id), `tests/test_projection.py` +3 (backfill-methode).
- **Blockiert von:** —


### OP-375: Erfolgsquote-Detail-Sektion (Donut + Fehlerklassen)

- **Status:** open
- **Typ:** ui-feature
- **Phase:** Phase-2 (Focus)
- **Blockiert von:** OP-306b (Etappe 2)
- **Betroffene Dateien:** `werkstatt/web/inspector.py` (`aggregate_erfolgsquote`), `static/overview.js` (Donut + Segmentbar + Fehlerklassen-Tabelle), `static/layout.css` (Donut-SVG + Segmentbar), `tests/test_erfolgsquote_backend.py` (neu), `tests/test_overview_shell_spec.py` (Spec-Erweiterung)
- **Problem:** Overview-Shell (OP-306b) zeigt Projekt-Karten, aber keine aggregierte Erfolgs-Sicht. Fehlerklassen (`reviewer_bug`, `loop_verify_failed`, `loop_failed`) liegen in SQLite, werden aber nirgends aufgeschluesselt. Ohne diese Sicht hat der User keine Handlungsgrundlage fuer den Selbstverbesserungs-Loop (ADR-0027).
- **Akzeptanzkriterien:**
  (a) Backend `aggregate_erfolgsquote()` in `inspector.py` liefert: Gesamt-Donut-Daten (Erfolg/Fehlgeschlagen/Abgebrochen), Projekt-Segmentbar (pro Projekt eine Zeile), Fehlerklassen-Top-3 (normalisiert, mit Count).
  (b) Frontend-Sektion unter der Overview: Gesamt-Donut (2-4 Segmente, kein 3D, KPI-Wert gross im Zentrum), Projekt-Segmentbar (horizontale Balken), Fehlerklassen-Tabelle mit sem-Farben.
  (c) Bei leeren 30-Tage-Daten: Hinweis "keine Daten", kein leerer Donut.
  (d) Bei genau 2 Segmenten: Halb-Donut.
  (e) Pre-OP-303-Erkennung: security-ai mit `run_id=''`-Runs wird als "vor OP-303, keine Zuordnung" markiert (Tooltip).
  (f) Klick auf Fehlerklasse: Detail-Panel mit 5 juengsten Events, Verweis auf OP-376.
  (g) Kein externer Chart-Lib-Import (SVG + CSS only).
- **Tests:** `tests/test_erfolgsquote_backend.py` (4 Tests: leere Daten, gemischte Daten, 2-Segmente-Halb-Donut, Pre-OP-303-Marker) + `tests/test_overview_shell_spec.py` (2 Spec-Tests: Donut-Rendering-Aufruf, Klick-Handler). Spec-First nach ADR-0015/0016.
- **ADR:** ADR-0025 (Erfolgsquoten-Visualisierung)

### OP-376: Fehler-Cluster-Aggregation (aggregate_fehler_cluster)

- **Status:** open
- **Typ:** architektur (Datenmodell)
- **Phase:** Phase-3 (Fundament Selbstverbesserung)
- **Blockiert von:** —
- **Betroffene Dateien:** `werkstatt/web/inspector.py` (`aggregate_fehler_cluster`, `aggregate_fehler_trend`), `tests/test_fehler_cluster.py` (neu)
- **Problem:** Fehlerdaten liegen in SQLite (`reviewer_bug`, `loop_verify_failed`, `loop_failed`, `verify_stage_ohne_hart_flag`), aber niemand gruppiert sie. Fuer ADR-0027 Phase 1 (Analyse) brauchen wir normalisierte Cluster: welche Fehler-Klasse tritt wie oft auf, in welcher Datei, mit welcher Signatur. Ohne diese Aggregation ist der Selbstverbesserungs-Loop blind.
- **Akzeptanzkriterien:**
  (a) `aggregate_fehler_cluster(projekt, tage=30)` liefert normalisierte Cluster als `[{signatur, haeufigkeit, datei, bug_typ, kontext_hash, letzte_ts, run_ids}]`. Signatur aus `reviewer_bug`-Payload: Datei + Bug-Typ + normalisierter Kontext (Whitespace, Zahlen).
  (b) `aggregate_fehler_trend(projekt, tage=30)` liefert pro Cluster eine Tages-Serie (Fehlerrate pro Tag).
  (c) Fail-loud bei kaputtem Payload-JSON (kein stilles skip). Leere Payload-Felder fuehren zu Signatur "unbekannt", nicht zu Crash.
  (d) Deterministisch: gleiche Eingabe -> gleiche Cluster-Reihenfolge (sortiert nach Haeufigkeit desc, dann Signatur).
  (e) Live: lauffaehig gegen die 387.487 Werkstatt-Events, Anzahl Cluster messbar.
- **Tests:** `tests/test_fehler_cluster.py` (5 Tests: leere DB, ein Cluster, mehrere Cluster sortiert, kaputte Payload, pre-OP-303-events ohne run_id). Spec-First nach ADR-0015/0016.
- **ADR:** ADR-0027 (Phase 1)

### OP-377: Selbstreflexions-Phase (Analyse -> OP-Entwurf)

- **Status:** open
- **Typ:** architektur (LLM-getrieben, Meta)
- **Phase:** Phase-3 (Fundament Selbstverbesserung)
- **Blockiert von:** OP-376 (Fehler-Cluster), OP-220 (Erfahrungs-Gedaechtnis)
- **Betroffene Dateien:** `werkstatt/selbstverbesserung.py` (neu), `tests/test_selbstverbesserung.py` (neu)
- **Problem:** Der Loop kann heute seine eigenen Fehler-Cluster nicht in OP-Entwuerfe uebersetzen. ADR-0027 Phase 2 fordert: pro Cluster identifiziert das LLM den verantwortlichen Code-Pfad und schlaegt einen OP-Entwurf vor (Titel, AK, Zieldateien). Ohne diese Phase bleibt der Selbstverbesserungs-Loop ein Messwerkzeug, kein Verbesserer.
- **Akzeptanzkriterien:**
  (a) Neue Datei `selbstverbesserung.py` mit `analysiere_cluster(cluster, codebase_pfad) -> OPEntwurf | None`.
  (b) `schreibe_op_entwurf(entwurf, projekt_dir)` haengt den Entwurf als neuen OP-Block in `docs/STATUS.md` (Format nach DOC_CONVENTIONS §5).
  (c) LLM-Prompt enthaelt: Cluster-Signatur, Haeufigkeit, 3 juengste Evidenz-Events, Code-Auszug der betroffenen Datei (max 200 Zeilen).
  (d) `None`-Rueckgabe bei: unklarer Ursache, Code fehlt, Aufwand > 1 Session (LLM schaetzt).
  (e) Kein Auto-Commit. Kein Auto-Start. Der OP landet in STATUS.md als `Status: open`, wartet auf Human-Gate.
  (f) Cluster-ID + Evidenz-IDs werden im OP-Block als Kommentar vermerkt (Nachvollziehbarkeit).
- **Tests:** `tests/test_selbstverbesserung.py` (4 Tests: LLM-Entwurf, None bei klarer Ursache, OP-Schreiben idempotent, Evidenz-IDs im Text). Spec-First nach ADR-0015/0016.
- **ADR:** ADR-0027 (Phase 2)



### OP-378: Preservation-Gate (verify-Stage)

- **Status:** open
- **Typ:** architektur (Verify-Stage)
- **Phase:** Phase-3 (Fundament Selbstverbesserung)
- **Blockiert von:** OP-377 (Selbstreflexions-Phase)
- **Betroffene Dateien:** `verify.json` (neue Stage), `werkstatt/verify.py` (preservation_gate-Handler), `tests/test_preservation_gate.py` (neu)
- **Problem:** ADR-0027 Phase 4 fordert: vor Commit pruefen, ob der Fix alte Fehler nicht wiederbringt ("Beneath the Surface": alle 16 evolvierten Agenten verloren alte Tasks). Der bestehende Verify (9 Stages) prueft nur aktuelle Tests, nicht die Fehler-Cluster-Rate gegen Baseline. Ohne Preservation-Gate kann ein Selbstverbesserungs-Patch alte Fehler wieder einbauen, ohne dass es auffaellt.
- **Akzeptanzkriterien:**
  (a) Neue verify-Stage `preservation_gate` in `verify.json`, hart, laeuft nach `pytest_regression`.
  (b) Baseline-Vergleich: die Top-N Cluster aus OP-376 muessen `AFTER <= BEFORE` sein (nach jeder neuen Event-Batch). Baseline-Ableitung: letzte 30 Tage.
  (c) Wenn `AFTER > BEFORE` in irgendeinem Cluster: Gate rot, Commit blockiert.
  (d) Wenn keine Baseline vorhanden (frisches Projekt): Gate gelb (nicht hart) mit Hinweis "keine Preservation-Baseline".
  (e) Konfigurierbar pro Projekt in `projects/<name>.yaml` (opt-out moeglich mit explizitem Grund in STATUS.md).
  (f) Fail-safe: bei SQLite-Fehler Gate rot (nicht "gruen aus Unsicherheit").
- **Tests:** `tests/test_preservation_gate.py` (4 Tests: Baseline vorhanden + keine Regression -> gruen; Regression -> rot; keine Baseline -> gelb; SQLite-Fehler -> rot). Spec-First nach ADR-0015/0016.
- **ADR:** ADR-0027 (Phase 4)

### OP-379: Trace-Evolution-Messung (Seed-Band)

- **Status:** open
- **Typ:** architektur (Messung)
- **Phase:** Phase-3 (Fundament Selbstverbesserung)
- **Blockiert von:** OP-378 (Preservation-Gate)
- **Betroffene Dateien:** `werkstatt/evolution.py` (neu), `tests/test_evolution.py` (neu)
- **Problem:** ADR-0027 Phase 5 fordert: nach N Runs messen, ob der Fix die Fehlerrate gesenkt hat, mit Seed-Band (Trace Evolution Bench: kein Text-Update-Verfahren bleibt auf jedem Seed ueber seinem Rauschband, ein gepa_llm-Seed faellt um -12,5 Punkte). Ohne Seed-Band messen wir Rauschen als Fortschritt.
- **Akzeptanzkriterien:**
  (a) Neue Datei `evolution.py` mit `messe_cluster_trend(projekt, cluster_signatur, referenz_runs=3) -> TrendErgebnis`.
  (b) Ergebnis-Format: `{cluster, vorher_rate, nachher_rate, band, delta, signifikant}`. Band aus den 3 Referenz-Runs (min/max).
  (c) `signifikant=True` nur wenn `delta > band_breite`. Sonst "keine Aussage".
  (d) Ergebnisse landen in `erfahrung.db` (OP-220-Schema): neue Tabelle `evolution_messung(cluster_signatur, run_id, ts, vorher, nachher, band, signifikant)`.
  (e) CLI-Aufruf `python3 -m werkstatt.evolution --projekt <name> --cluster <sig>` (manuell, kein Auto-Trigger).
  (f) Wenn keine 3 Referenz-Runs: `signifikant=False` mit Grund "zu wenig Referenz-Runs".
- **Tests:** `tests/test_evolution.py` (3 Tests: signifikanter Fix, nicht-signifikanter Fix (Rauschen), zu wenig Runs). Spec-First nach ADR-0015/0016.
- **ADR:** ADR-0027 (Phase 5)

### OP-380: Memory-Graph-UI (2D Ring-Layout, Evidence-Panel)

- **Status:** open
- **Typ:** ui-feature
- **Phase:** Phase-3 (Fundament Selbstverbesserung)
- **Blockiert von:** OP-221 (Memory-Destillation), OP-222 (Semantic Memory)
- **Betroffene Dateien:** `static/memory_graph.js` (neu), `static/layout.css` (Graph-Styling), `werkstatt/web/app.py` (`GET /api/projects/{name}/memory/graph`), `werkstatt/web/inspector.py` (`aggregate_memory_graph`), `tests/test_memory_graph_backend.py` (neu), `tests/test_memory_graph_spec.py` (neu)
- **Problem:** Nach OP-221/222 entstehen Erfahrungs-Eintraege. Ohne Visualisierung bleibt dem User verborgen, welche Loesungen gegriffen haben, welche Fehler zusammenhaengen, wo die Evidenz liegt. ADR-0026 begruendet: 2D-Canvas + Ring-Layout (heym) + Evidence-Panel (Cognee/AgentFlow/Langfuse). Kein 3D als Start.
- **Akzeptanzkriterien:**
  (a) `GET /api/projects/{name}/memory/graph` liefert `{nodes, edges}` mit Node-Typen (`fehler`, `loesung`, `evidenz`, `projekt`, `op`) und Kanten (`loeste`, `trat_auf`, `verwandt`, `blockierte`). Verwandtschaft opt-in via `?verwandt=1`.
  (b) Frontend: 2D-Canvas, Ring-Layout (stabile Position per `hash(node_id) -> (radius, angle)`), SVG bei <200 Nodes, Canvas ab 200.
  (c) Node-Farbe nach sem-Variablen (sem-error, sem-ok, sem-history, sem-active, sem-action).
  (d) Klick auf Node -> Evidence-Panel (rechts, einklappbar): Node-Info, direkte Nachbarn, letzte 10 SQLite-Events als Evidenz, verwandte OPs aus STATUS.md.
  (e) Hover auf Kante: opacity 0.3 -> 1.0.
  (f) Bei >20 Nachbarn pro Node: gruppieren nach Typ (Klapp-Header).
  (g) Kein 3D, keine fliessenden Kanten, keine externe Chart-Library.
- **Tests:** `tests/test_memory_graph_backend.py` (3 Tests: leere DB, ein Fehler + Evidenz, mehrere Typen gemischt) + `tests/test_memory_graph_spec.py` (5 Spec-Tests: Layout-Stabilitaet, Evidence-Panel-Trigger, Hover-Verhalten, Verwandtschaft-opt-in, Node-Farbe-Konstanten). Spec-First nach ADR-0015/0016.
- **ADR:** ADR-0026 (Memory-Graph-Visualisierung)



### OP-381: Loop-UI-Interaktion (Gate-Bridge + Ambient-Live-Status)

- **Status:** open
- **Typ:** bugfix (Sammel-OP)
- **Phase:** Phase-2 (Focus, blockiert Loop-Nutzung aus der UI)
- **Blockiert von:** —
- **Betroffene Dateien:** `werkstatt/web/app.py` (`POST /api/runs/{run_id}/gate` an Live-Loop anbinden), `werkstatt/web/inspector.py` (`_audit_events`-Feld-Mapping, `aggregate_ambient`-Gate-Wait-Erkennung, `aggregate_gate_context`-Gate-Parsing), `werkstatt/gate_bridge.py` (`_finde_antwort` erweitern: schreibt `gate_answered` in SQLite/JSONL), `static/gate_panel.js` (Polling + Submit), `static/ambient_status.js`
- **Problem (aus Live-Test 2026-11-08 23:25):** Loop aus UI gestartet (`POST /start` mit OP-324). Loop lief korrekt an, öffnete Plan-Gate (`plan-4ce22f2a`), wartete 5+ Minuten. UI zeigte **nichts** — kein running, kein Gate, keine Antwort. Vier unabhängige Bugs, alle im UI↔Loop-Datenfluss:
  - **(A) `_audit_events` liest `ts` statt `timestamp`:** JSONL-Events haben `"timestamp"`. Parser im `aggregate_gate_context` liest `ev.get("ts")` → alle `ts` leer. Folgefehler: keine Historie in der UI erkennbar.
  - **(B) `offene_gates: []` trotz `gate_open` in SQLite:** Folgefehler A oder eigenständig — `_audit_events`-basierte Gate-Erkennung scheitert.
  - **(C) Ambient zeigt nicht `running`:** Der Loop schreibt keinen `heartbeat` während `gate_bridge.wait()` blockiert. `aggregate_ambient` prüft nur `heartbeat` in letzten 60s → sieht Loop als idle/failed. Gate-Wait-Events (`gate_open` in letzten 60s) müssten als running zählen.
  - **(D) UI kann Gate nicht beantworten:** `POST /api/runs/{run_id}/gate` existiert, aber `gate_bridge.wait()` pollt nur `gate_answered`-Events. Kein Endpoint schreibt `gate_answered` für einen laufenden Subprozess-Loop. Folge: Loop hängt bis Timeout.
- **Akzeptanzkriterien:**
  (a) `_audit_events` mappt `timestamp → ts` beim Einlesen (oder liest beide Felder). Unit-Test.
  (b) `aggregate_gate_context` liefert bei offenem Gate in JSONL `offene_gates: [{gate_id, prompt, optionen, ts}]`. Test: `gate_open` im JSONL → Gate in offene_gates.
  (c) `aggregate_ambient` erkennt Loop als `running`, wenn in letzten 60s **entweder** `heartbeat` **oder** `gate_open` mit noch nicht beantwortetem `gate_id` vorliegt. Test: Loop im Gate-Wait → ambient.running.
  (d) Neue Route/Logik: UI-Gate-Antwort (`POST /api/runs/{run_id}/gate`) schreibt `gate_answered`-Event in die SQLite/JSONL, so dass `gate_bridge._finde_antwort` es beim nächsten Poll sieht. Live-Test: Loop aus UI, Plan-Gate, Klick auf „j" im Gate-Panel, Loop läuft weiter.
  (e) `gate_panel.js` pollt `GET /api/projects/{name}/gate/context` alle 2s, zeigt offene Gates, Submit → `POST /api/runs/{run_id}/gate`.
  (f) Ende-zu-Ende-Live-Test (in PROGRESS.md dokumentiert): Loop aus UI starten, Gate beantworten, Loop bis Commit durchlaufen lassen.
- **Tests:** `tests/test_gate_bridge_ui.py` (~6 Tests: `_audit_events`-Mapping, `gate_open`-Erkennung, ambient-running-bei-gate-wait, `gate_answered`-Event-Schreiben, Poll-Loop) + Frontend-Spec `tests/test_gate_panel_spec.py` (~3 Tests).
- **Grund:** Loop kann heute aus der UI gestartet werden, aber nicht durchlaufen — er hängt am ersten Gate. Ohne Fix ist Loop-aus-UI praktisch nicht nutzbar. Blocker für OP-306 (Mode-Switch).



### OP-381b: Freitext-Gates im UI (plan_reason / Reflection-Reject-Grund)

- **Status:** open
- **Typ:** bugfix (Sub-OP zu OP-381)
- **Phase:** Phase-2 (Focus)
- **Blockiert von:** OP-381c (Modal-Redesign, Textarea sitzt im Modal)
- **Betroffene Dateien:** `static/gate_panel.js`, `static/layout.css`, `werkstatt/web/inspector.py` (Gate-Typ-Erkennung), `werkstatt/gates.py` + `werkstatt/gate_bridge.py` (typ-Feld im Payload)
- **Problem (Live 2026-11-09 23:56):** Der Loop hat zwei strukturell verschiedene Gate-Typen:
  **(1) Plan-Gate** — `j/n/a` (Plan ausführen?) mit Buttons.
  **(2) Reflection-Reject-Grund-Gate** — `plan_reason`, **Freitext** ("Reject-Grund eingeben"). Kommt nach Plan-Reject (oder Plan-Gate-Timeout) als Teil der Reflection-Phase. Der User gibt optional einen Grund ein; leer = harter Abbruch.
  
  `gate_panel.js` rendert **alle** Gates als j/n/a-Buttons. Klick auf `j` für ein `plan_reason`-Gate sendet `answer="j"` → Loop interpretiert als Reject-Grund "j" (oder leer) → **LOOP FEHLGESCHLAGEN Tasks: 0/7**. Beleg: run `test-clean-1794181131`, seq 788855 (`gate_open plan_reason-0fbc146e`, prompt="Reject-Grund (optional, Enter=leer)") + seq 788856 (`gate_answered answer=j`), Log "Tasks: 0/7".
  
  **Wichtig zur Semantik:** Der Freitext vom **Architect** (Prosa) geht an den **Planner** (macht Splits) — das ist ein anderer Pfad. `plan_reason` ist **Reflection-Input**, nicht Architect-Input.
- **Akzeptanzkriterien:**
  (a) Gate-Payload bekommt neues Feld `typ: "jna" | "freitext"`. Backend setzt es bei `gate_bridge.signal_open()` basierend auf `optionen`-Feld oder explizitem Parameter.
  (b) `gate_panel.js` rendert bei `typ="freitext"` ein `<textarea>` + `Senden`-Button statt j/n/a-Buttons.
  (c) `POST /api/runs/{run_id}/gate` akzeptiert `answer` als beliebigen String (schon so, aber Validierung auf max-len prüfen).
  (d) Fallback bei fehlendem `typ`: `jna` (rückwärtskompatibel, weil alte Gates den typ nicht haben).
  (e) Live-Test: Loop mit OP-324 starten, Plan-Gate ablehnen, `plan_reason`-Gate im UI als Textarea, Freitext eingeben, Loop macht Reflection mit dem Grund.
- **Tests:** `tests/test_gate_panel_typ.py` (~4 Tests: jna default, freitext-Erkennung im Payload, POST mit Freitext-Antwort, Fallback). Frontend-Spec in `tests/test_gate_panel_spec.py` (Textarea-Rendering).
- **ADR:** —



### OP-382: Dogfooding-Phase — UI-Loop 10× stabil im Betrieb

- **Status:** open
- **Typ:** meta (Prozess-OP, keine Code-OP)
- **Phase:** Phase-2 (Focus, **vor jedem neuen Feature**)
- **Blockiert von:** OP-381c (funktionierendes Gate-Modal), OP-381b (Freitext-Gate)
- **Blockiert:** alle OPs mit `Phase: Phase-3` (Selbstverbesserung OP-376..379, Memory-Graph OP-380, Mode-Switch OP-306)
- **Prinzip:** „Eat your own dogfood." Große Software-Firmen testen Produkte intern im echten Betrieb, bevor neue Features gebaut werden. Dabei fallen die Bugs auf, die Unit-Tests nicht finden — weil der Entwickler blind für die eigene Denkweise ist.
- **Problem:** Werkstatt hat heute (2026-11-09) einen kritischen Zustand erreicht: der Loop kann aus der UI gestartet werden, Gates werden im Browser angezeigt, Klicks kommen an. **Aber**: jede Live-Nutzung deckt 1-2 weitere Bugs auf (heute: 4 Bugs bei einem einzigen Loop-Versuch, danach noch der `KeyboardInterrupt` im Test-Lauf). Neue Features (Selbstverbesserung, Memory-Graph) zu bauen, während der Kern noch wackelt, wäre Roulette. Erst muss der **Kern im Betrieb stabil sein**, dann wachsen die Features organisch aus echter Nutzung.
- **Akzeptanzkriterien (Dogfooding-Zyklus):**
  **(Phase A: Stabilisierung)**
  (a) OP-381c (Gate-Modal) gebaut + live getestet.
  (b) OP-381b (Freitext-Gate) gebaut + live getestet.
  (c) `pytest` 100 % grün, `ruff`/`mypy`/5 Drifts grün, Server mit aktueller Code-Version, `DEEPSEEK_API_KEY` gesetzt.
  **(Phase B: Betrieb)**
  (d) 10 echte OPs aus STATUS.md werden **vollständig über die UI** durchgebaut (Start → Gates → Verify → Commit). Kein Terminal-Eingriff außer Beobachten.
  (e) Jede Frustration / jeder Bug / jede Unklarheit wird **sofort** als eigene OP angelegt (`docs/STATUS.md`, `Typ: bugfix` oder `ui-feature`).
  (f) Nach jedem der 10 Runs: Tagebuch-Eintrag in `PROGRESS.md` mit
       - Was lief gut?
       - Was hat genervt?
       - Was fehlte?
  **(Phase C: Auswertung)**
  (g) Nach 10 Runs: Konsolidierung der Notizen. **Welche 3 Dinge** tauchen am häufigsten auf? Diese 3 werden in den nächsten Sprint priorisiert.
  (h) Erst wenn alle 10 Runs stabil durchliefen: Freigabe für Phase-3-OPs (Selbstverbesserung, Memory-Graph, Mode-Switch).
- **Tests:** Keine klassischen Tests (Meta-OP). Stattdessen: 10 PROGRESS-Einträge + 1 Abschluss-Reflexion in MERKPOSTEN.
- **Warum diese Phase:** Unit-Tests finden Bugs im Code. Nur echte Nutzung findet **Usability-Bugs** (zu kleines Gate-Panel, fehlender Copy-Button, Drag sinnlos), **Infrastruktur-Bugs** (Server-Neustart vergessen, Cache-Buster-Mix) und **Denkfehler** (Freitext-Gate vs. j/n/a-Gate verwechselt). Genau diese 3 Kategorien sind die, die ein Produkt „fertig" vs. „nutzbar" unterscheiden.
- **Grund für Blockierung von Phase-3:** Selbstverbesserung und Memory-Graph setzen auf einem **stabilen Loop** auf. Wenn der Loop selbst noch alle 2 Runs abstürzt, ist jeder Gewinn aus Selbstverbesserung nicht messbar (Rauschen > Signal).
- **Nicht blockiert:** OP-306b Etappe 2 (Overview-Shell) — kann parallel gebaut werden, weil sie unabhängig vom Loop-Start ist.
- **ADR:** —


### OP-383: LLM-Token-Verbrauch pro Rolle tracken (Messung)

- **Status:** open
- **Typ:** messung
- **Phase:** Phase-2 (Loop-Stabilisierung, Context-Engineering-Achse)
- **Blockiert von:** —
- **Blockiert:** OP-384, OP-385
- **Betroffene Dateien:** `werkstatt/architect.py`, `werkstatt/planner.py`, `werkstatt/roles/builder/run.py`, `werkstatt/roles/reviewer.py`, `werkstatt/reflection.py`, `tests/test_llm_usage_pro_rolle.py` (neu)
- **Problem:** Aus Live-Messung 2026-11-09 (Run `test-clean-1794181131`): max **35.550 prompt-Tokens** in einem einzigen Call, 95.263 prompt-Tokens total über 5 Calls. Aber: das Feld `agent` im `llm_usage`-Payload ist NULL (`json_extract` gibt NULL) — **wir wissen nicht, welche Rolle die Tokens verbraucht**. Ohne diese Zuordnung ist jede Context-Optimierung blind.
  **Forschung 2025/26:** "Context Rot" (Chroma 2025): Selbstgenerierte Wiederholungen in rekursiven KI-Schleifen verschmutzen den Kontext. Größere Fenster ≠ besser. "Lost-in-the-Middle" (Liu et al.): Modelle ignorieren Informationen in der Mitte langer Kontexte. Wir müssen wissen *wer* wie viel schickt, *bevor* wir kürzen.
- **Akzeptanzkriterien:**
  (a) Jeder `llm_usage`-Event enthaelt ein eigenes Feld `rolle` mit einem der stabilen Namen `architect`, `planner`, `builder`, `reviewer`, `reflection`, `explorer`, `scout`, `debugger`; unbekannte Tasks werden als `unbekannt` ausgewiesen. Das Audit-Umschlagfeld `agent` bleibt `agent_pipeline` und wird nicht fuer Tasknamen ueberschrieben.
  (b) Rollenaggregation liest die JSON-Payload-Felder aus dem Event-Store (keine nicht vorhandenen SQL-Spalten) und liefert Anzahl, Summen sowie maximalen Prompt pro Call.
  (c) Neue Funktion `aggregate_tokens_per_rolle()` in `inspector.py` liefert die Aggregation fuer Projekt und Run.
  (d) `/api/projects/{name}/tokens` liefert `by_role`; die Statusleisten-Tokenanzeige zeigt bei Hover je Rolle Calls, Prompt-Summe und groessten Prompt-Call als eigene Zeile. Live nach einem Loop-Run verifizieren.
- **Tests:** `tests/test_loop_ask_llm.py` (Rollenfeld und unveraendertes Audit-Umschlagfeld); `tests/test_llm_usage_pro_rolle.py` (Rollen-Mapping, Aggregation, API-Response, Spitzenwert und ungueltige Payloads). Frontend-/Live-Verhalten separat verifizieren.
- **ADR:** —
- **Kontext:** Erste OP der Context-Engineering-Achse (Phase 2). Muss vor OP-384/385 laufen, sonst sind deren Zahlen geraten.

### OP-384: Context-Budget pro Rolle (hartes Token-Limit)

- **Status:** open
- **Typ:** architektur
- **Phase:** Phase-2 (Loop-Stabilisierung)
- **Blockiert von:** OP-383 (Messung: welche Rolle zieht wie viel)
- **Blockiert:** OP-387, OP-388
- **Betroffene Dateien:** `werkstatt/context_budget.py` (neu), `werkstatt/architect.py`, `werkstatt/planner.py`, `werkstatt/roles/builder/prompt.py`, `werkstatt/reflection.py`, `tests/test_context_budget.py` (neu)
- **Problem:** Kein Prompt-Builder hat ein **hartes Token-Budget**. `explorer_findings`, `scout_api_auszug` und `api_index_cache` gehen ungekuerzt in den Architect-Prompt. Bei wachsender Codebase waechst der Prompt unbegrenzt. `planner.py:1991` hat als einzige echte Truncation `_findings[:2000]`. Alles andere: unbegrenzt.
  **Forschung:** Anthropic "Effective context engineering" (2025): "Find the smallest possible set of high-signal tokens." Structured Eviction statt simpler LLM-Kompression. Context Rot: mehr Tokens ≠ mehr Leistung.
- **Akzeptanzkriterien:**
  (a) Neue Datei `context_budget.py` mit einer testbaren Budgetfunktion. Das Budget zaehlt System- und User-Prompt sowie Nachrichten-Overheads und reserviert Completion-Tokens. Pro Modell wird ein passender Tokenizer genutzt; wenn keiner verfuegbar ist, greift ein dokumentierter konservativer Schaetzer, der nie als exakte Messung ausgegeben wird.
  (b) **Prioritaeten** (hoch nach niedrig): `OP-Spec` > `Akzeptanzkriterien` > `task_files` > `explorer_findings` > `api_index_cache` > `scout_api_auszug` > `historie` > `patches`. OP-Spec und Akzeptanzkriterien sind Pflichtfelder: wenn sie nicht in das Budget passen, wird der LLM-Call fail-closed abgebrochen und ein Human-Review-Signal erzeugt.
  (c) Nur optionale Felder duerfen gekuerzt oder weggelassen werden. Kuerzungen erfolgen an Feld-/Datensatzgrenzen; das Ergebnis und Schaetzverfahren werden vor dem Call geprueft. Audit-Metadaten enthalten Rollenname, Modell, Schaetzverfahren, Vorher-/Nachher-Zaehler und Feldnamen, aber keine Prompt-Inhalte.
  (d) Pro Rolle und Modell konfigurierbar (Default-Werte, ueberschreibbar):
      - Architect: 12_000 Tokens
      - Planner: 6_000
      - Builder: 8_000
      - Reviewer: 8_000
      - Reflection: 10_000
      - Debugger (spaeter): 15_000
  (e) `audit("context_budget_angewendet", {"rolle": ..., "weggelassen": ..., "final_tokens": ...})` bei jeder Anwendung.
- **Tests:** `tests/test_context_budget.py` (4 Tests: Prioritaet wirkt, Kuerzung, Limit-Erkennung, leeres Feld).
- **ADR:** —
- **Kontext:** Nach OP-383 wissen wir die echten Zahlen. Diese OP setzt die Limits basierend darauf.

### OP-385: Scout-Kette reparieren — Auftrag als Hauptzweck + einziger Architect-Input

- **Status:** open
- **Typ:** architektur (Design + Umbau, Phase 2.5)
- **Phase:** Phase-2.5 (Context-Architektur, vor Phase-3)
- **Blockiert von:** —
- **Blockiert:** OP-281 (Scout-Messung erst nach Kette sinnvoll), OP-387 (JIT-Retrieval erst nach sauberem Input)
- **Verwandt:** OP-342 (Mutter-OP Prompt-Engineering pro Rolle), OP-260 (Kontext-Vertrag fuer Builder/Test/Debugger — Scout nicht drin)
- **Betroffene Dateien:** `werkstatt/scout.py` (Prompt), `werkstatt/architect.py` (Prompt-Bau), `werkstatt/state.py` (neues Feld `scout_auftrag`), `tests/test_scout_kette.py` (neu)
- **Problem (zwei zusammenhaengende Brueche):**
  **Original-Design:** Explorer -> Scout -> Architect. Explorer sucht breit, Scout formt daraus einen praezisen Auftrag mit AST + nur relevanten Infos, Architect bekommt genau diesen Auftrag. Der Sinn: Architect ist der erste echte Inputgeber fuer die ganze Kette. Je praeziser sein Input, desto besser die Kette.
  
  **Brueche in der Praxis:**
  (a) **Scout-Prompt:** Fordert schon "Du formulierst einen Auftrag fuer den Architect" (Zeile 1-2 SCOUT_SYSTEM). ABER: Der Auftrag ist Nebenprodukt. 90 % des Prompts drehen sich um Widerspruch-Checks, IST-ZUSTAND-Checks, atomare Plaene, OP-Disziplin. Ein `auftrag_prosa` entsteht "nebenbei" — nicht als Hauptziel. Live: Scout laeuft 8.6s, `api_auszug` ist da, aber `auftrag_prosa` bleibt vage.
  (b) **Architect-Input:** Architect bekommt **direkt** `explorer_findings` (1.020 Findings) aus dem State (architect.py:447-453). Zusaetzlich `scout_api_auszug` und `api_index_cache`. **Explorer-Rohdaten und Scout-Filter parallel.** Der Schnitt, der die Kette sauber halten soll, ist damit aufgehoben.
  
  **Konsequenz:** Architect-Prompt 35.550 prompt-Tokens (Live 2026-11-09). 1.020 Findings + AST 10 Dateien + Scout-Output parallel. Context Rot.
- **Akzeptanzkriterien:**
  **(a) Scout-Prompt: Auftrag ist Hauptziel**
  - `SCOUT_SYSTEM` umstrukturiert: `auftrag_prosa` als **erstes** Output-Feld, Checks sekundaer
  - Neuer Block im Prompt: `## DEIN HAUPTZIEL\nFormuliere den Auftrag fuer den Architect. Der Architect braucht:\n- Einen praezisen Auftrag (3-10 Saetze)\n- AST der relevanten Dateien (aus api_auszug)\n- Nur was wirklich relevant ist\nKein Ballast, keine Rohdaten. Der Architect ist der wichtigste Punkt in der Kette.`
  
  **(b) Scout-Output als einziges Architect-Input**
  - Neues State-Feld `scout_auftrag: dict` in `werkstatt/state.py`
  - Scout fuellt `scout_auftrag` mit allen Output-Feldern
  - `architect.py`: `explorer_findings` **nicht mehr** direkt in den Prompt (architect.py:447-453 entfernen)
  - `architect.py`: `api_index_cache` kommt aus `scout.auftrag.api_auszug` (nicht mehr parallel)
  - Architect-Prompt: nur noch `scout_auftrag`-Felder + OP-Spec + Migrationsstand
  
  **(c) Begrenzter Fallback fuer gespeicherte Alt-Runs**
  - Nur ein gespeicherter Run aus der Zeit vor `scout_auftrag` darf den alten Explorer-Kontext verwenden.
  - Der Fallback ist hart begrenzt und auditiert.
  - Fehlt der Scout-Auftrag in einem neuen Run, wird fail-closed abgebrochen und ein klares Fehler-/Human-Review-Signal gesetzt.
  
  **(d) `bereits_erfuellt`-Check bleibt harter Filter**
  - Wenn `scout.bereits_erfuellt == true`: Loop bricht ab, Architect uebersprungen
  
  **(e) Live: Architect-Prompt 30-50 % kleiner, Plan-Qualitaet gleich oder besser**
- **Tests:** `tests/test_scout_kette.py` (5 Tests: Scout-Auftrag im Systemprompt, kein doppelter Explorer-User-Kontext, fail-closed bei unvollstaendigem Report, Legacy-Fallback, `bereits_erfuellt`-Check).
- **ADR:** ADR-0028 (Scout-Kette als Kontext-Verengung — wird mit OP-385 angelegt)

### OP-386: Reflection-Kontext bereinigen (Diff statt Patches)

- **Status:** open
- **Typ:** architektur
- **Phase:** Phase-2 (Loop-Stabilisierung)
- **Blockiert von:** —
- **Betroffene Dateien:** `werkstatt/reflection.py`, `werkstatt/roles/builder/run.py`, `werkstatt/verify.py`, `tests/test_reflection_kontext.py` (neu)
- **Problem:** Die Reflection-Phase bekommt drei Felder:
  1. `patches` — vollstaendiger Patch-Text (alle Zeilen, alle Dateien)
  2. `last_verify_errors` — Fehler-Ausgabe (z.T. 500+ Zeilen mit Stacktraces)
  3. `reviewer_bugs` — Bugs vom Reviewer (auch `medium` und `low`)
  Redundanz: `patches` enthaelt oft genau das, was `last_verify_errors` schon beschreibt. `reviewer_bugs` mit `medium`-Severity sind oft Rauschen (Forschung: Reflection ohne externes Signal verschlechtert Leistung — Self-Refine-Papers 2025).
- **Akzeptanzkriterien:**
  (a) `patches` durch den tatsaechlichen `git diff` fuer die betroffenen Task-Dateien ersetzen (nicht den ganzen Datei-Inhalt — nur die geaenderten Zeilen). Diff-Pfade kommen aus dem Task-Scope, nicht aus einem unbeschraenkten Repository-Diff.
  (b) `last_verify_errors` via `_extrahiere_fehlerkern` (existiert schon in `verify.py`) zu einem kurzen Fehlerkern verdichten; falls die Extraktion leer ist, einen begrenzten Fail-closed-Auszug behalten statt den Verify-Fehler zu verwerfen.
  (c) `reviewer_bugs` nur `severity in ("HIGH", "critical")`, `medium`/`low` weg.
  (d) Wenn keine HIGH-/critical-Bugs uebrig bleiben, werden keine medium-/low-Bugs nachgeschoben. Der Prompt enthaelt stattdessen einen expliziten Hinweis, dass der Severity-Filter keine Reviewer-Bugs uebrigliess. Deterministische Verify-Fehler bleiben davon unberuehrt.
  (e) Live: Reflection-Prompt messbar kleiner (Vergleich in PROGRESS.md).
- **Tests:** `tests/test_builder_agent.py` (HIGH/critical-Filter, leerer Filter-Fallback, beide Resume-Feedbackquellen); `tests/test_reflection_kontext.py` (Diff statt Datei, Fehlerkern-Extraktion, Severity-Filter und begrenzter Fallback).
- **ADR:** —

### OP-387: JIT-Retrieval fuer Architect (view_api-Tool)

- **Status:** open
- **Typ:** architektur (gross)
- **Phase:** Phase-2.5 (Context-Architektur)
- **Blockiert von:** OP-384 (Context-Budget), OP-385 (Scout-Kette muss erst sauber sein)
- **Betroffene Dateien:** `werkstatt/architect.py`, `werkstatt/roles/architect_tools.py` (neu), `tests/test_architect_jit.py` (neu)
- **Problem:** Der Architect bekommt heute den `api_index_cache` fuer 10 Dateien **vorab geladen** (AST-Struktur im Prompt). Statt On-Demand: er bekommt die **Liste der 10 Pfade** und ruft selbst ab, was er fuer den Plan braucht. Anthropic "Effective context engineering" (2025): JIT-Retrieval ist der zentrale Hebel gegen Context Rot.
  **Aber:** grosser Umbau — Architect wird zum Agenten mit Tools statt einmaligem Prompt-Builder.
- **Akzeptanzkriterien:**
  (a) Neue Datei `architect_tools.py` mit `view_api(path)` — liefert AST-Struktur einer Datei (wie heute `api_index_cache[path]`).
  (b) Architect-Prompt enthaelt nur: `Verfuegbare Dateien: <10 Pfade>` und die Tool-Definition.
  (c) Architect ruft `view_api(path)` selbst auf, maximal 5x pro Plan-Erstellung.
  (d) Fallback: wenn Architect nach 5 Calls keinen Plan hat, greift der alte Code-Pfad (volle `api_index_cache` im Prompt).
  (e) Live: Architect-Prompt messbar kleiner, Plan-Qualitaet gleich oder besser (Test-Suite).
- **Tests:** `tests/test_architect_jit.py` (6+ Tests: Tool-Definition, Tool-Aufruf, Fallback, End-to-End mit Mock-LLM).
- **ADR:** —
- **Kontext:** Groesster Umbau der Achse. Eigene Session. Erst nach OP-384/385.

### OP-388: Context-Budget als Verify-Stage (Praeventiv)

- **Status:** open
- **Typ:** verify-stage
- **Phase:** Phase-2 (Loop-Stabilisierung)
- **Blockiert von:** OP-384 (Context-Budget)
- **Betroffene Dateien:** `verify.json`, `werkstatt/verify.py`, `tools/context_drift.py` (neu), `tests/test_context_drift.py` (neu)
- **Problem:** Damit kuenftige Aenderungen die Budget-Limits nicht wieder aufheben. Wenn OP-384 ein 12k-Limit setzt, aber ein spaeterer Patch `explorer_findings` wieder unbegrenzt durchlaesst, faellt das niemandem auf — bis die Prompts wieder 35k Tokens haben.
- **Akzeptanzkriterien:**
  (a) Neues Tool `tools/context_drift.py`: prueft jeden `llm_usage`-Event pro Rolle gegen das konfigurierte harte Limit und meldet zusaetzlich den Spitzenwert je Rolle; ein spaeterer kleiner Call darf einen frueheren Ausreisser nicht verdecken.
  (b) Neue **weiche** Stage `context_drift` in `verify.json` (Start: warnen, nicht blocken).
  (c) Nach 14 Tagen ohne Warnung: auf hart umstellen (eigene OP).
  (d) Baseline-Vergleiche gruppieren nach gleicher Rolle und gleichem Modell und vergleichen den hoechsten Einzel-Call. Waehrend der weichen Einfuehrungsphase erzeugt eine Steigerung >20 % eine Warnung. Ein konfiguriertes absolutes Hard-Limit gilt unabhaengig von der Baseline; Baseline-Toleranz darf keinen uebergrossen Einzel-Call freigeben.
- **Tests:** `tests/test_context_drift.py` (2 Tests: Limit-Ueberschreitung wird erkannt, Baseline-Toleranz).
- **ADR:** —



### OP-389b: [P3] DRY-Migration der WS-Auth auf `require_ws_auth`

- **Status:** open
- **Typ:** refactor (klein, tech-debt)
- **Phase:** Phase-2 (Sauberkeit; kein Sicherheitsproblem)
- **Blockiert von:** —
- **Quelle:** Folge-OP aus OP-389 (Commit 8880d04, 2026-11-09). Im OP-389-Close bewusst nicht mitgemacht (Regress-Risiko an 3 funktionierenden Endpoints).
- **Betroffene Dateien:** `werkstatt/web/app.py`, `werkstatt/web/audit_panel.py`, `werkstatt/web/terminal_proxy.py`, `tests/test_ws_endpoint_helpers.py` (neu)
- **Problem:** Nach OP-389 gibt es einen Helper `require_ws_auth(websocket)` in `werkstatt/web/auth.py`. Die drei Bestandsendpoints (`/api/projects/{name}/chat/stream` app.py:616, `/api/projects/{name}/audit/stream` audit_panel.py:292, `/ws/terminal/{project}` terminal_proxy.py:298) nutzen aber noch die 4-Zeilen-Kopie inline: `if not is_auth_disabled() and not is_authed_ws(websocket): await websocket.close(code=1008); return`. Bei einer künftigen Änderung an der Auth-Logik (z.B. Cookie-Name, neuer Header) müssten 4 Stellen gepflegt werden — echte technische Schuld, kein akuter Bug.
- **Akzeptanzkriterien:**
  (a) Die drei Bestandsendpoints rufen `await require_ws_auth(websocket)` statt der Inline-Kopie auf. Semantisch identisch (close 1008 vor accept()).
  (b) `from werkstatt.web.auth import require_ws_auth` als lokaler Import am Funktionskopf (Muster wie bisheriger `from werkstatt.web.auth import is_auth_disabled, is_authed_ws`).
  (c) Kein Verhaltenswechsel — `tests/test_ws_auth.py` (13 Tests aus OP-389) bleibt grün.
  (d) Meta-Test in `tests/test_ws_endpoint_helpers.py`: Source-Scan über `werkstatt/web/{app,audit_panel,terminal_proxy,ws}.py` verbietet das Muster `if not is_auth_disabled() and not is_authed_ws` (Regress-Barriere: taucht es wieder auf, wird's rot).
- **Tests:** `tests/test_ws_endpoint_helpers.py` (1-2 Tests: Source-Scan). `tests/test_ws_auth.py` unverändert — bleibt grün als Verhaltensbeweis.
- **ADR:** —



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


### OP-303: Loop-Start-Button + Run-Status-Badge

- **Status:** open
- **Typ:** ui-feature
- **Phase:** Phase-1 (Cockpit-Fundament)
- **Betroffene Dateien:** `static/runs.js`, `werkstatt/web/app.py` (`/api/projects/{name}/ops` liefert run_status pro OP)
- **Problem:** Der Nutzer kann keinen Loop starten ohne SSH. Die Runs-Liste zeigt OPs, aber nicht welcher davon gerade laeuft.
- **Akzeptanzkriterien:** (a) Jede OP-Zeile in Runs-Liste hat Status-Badge: `○ idle`, `● running`, `✓ done`, `✗ failed` (basiert auf letztem `loop_started`/`loop_ended`/`loop_failed` dieses OPs). (b) Hover ueber OP-Zeile zeigt Ghost-Preview: "OP-213: Test-Thaw. Blockiert von OP-210 (open). [Trotzdem starten]". (c) Klick auf `▶`-Button startet Loop mit dieser OP-Aufgabe. (d) Bei laufendem Loop: OP wird blau markiert, ein "Stop"-Button erscheint. (e) Nach Loop-Ende: Badge aktualisiert innerhalb 5s via Polling.
- **Tests:** Smoke: `POST /start` aus UI-Klick ruft Endpoint. Kein pytest (UI-Verhalten).
- **Blockiert von:** —

### OP-306: Mode-Switch (Cockpit / Control / Debug)

- **Status:** open
- **Typ:** ui-feature
- **Phase:** Phase-1 (Cockpit-Fundament)
- **Betroffene Dateien:** `static/mode.js` (neu), `static/layout.html`, `static/layout.css`, `static/tabs.js`
- **Problem:** Das UI hat genau einen Modus. Der Cockpit-Typ wird erschlagen von drei Spalten, der Kontrollraum-Typ will mehr Dichte. ADR-0022 fordert 3 Modi.
- **Akzeptanzkriterien:** (a) Drei Modi: `cockpit` (default, 3 Spalten wie heute), `control` (Focus-View, breite Timeline, Chat schwebend), `debug` (Timeline + Audit gekoppelt). (b) Wechsel via `Shift+Space` zyklisch, via Command Palette (`mode cockpit`), via URL `?mode=control`, via Dropdown oben links. (c) Persistiert in localStorage und URL. (d) Mode-Name oben sichtbar. (e) Guard: bei Wechsel waehrend laufendem Run → Warnung "Run laeuft, Modus wechseln?". (f) Alle drei Modi nutzen dieselben semantischen Farben (OP-300).
- **Tests:** Keine (UI).
- **Blockiert von:** OP-381c (Gate-Modal, Wasserfall braucht ordentliches Gate)

### OP-307: Chat Tool-Call-Karten

- **Status:** open
- **Typ:** ui-feature
- **Phase:** Phase-1 (Cockpit-Fundament)
- **Betroffene Dateien:** `static/chat.js`, `static/layout.css`, `static/chat.css` (neu wenn noetig)
- **Problem:** Chat zeigt Tool-Calls als rohe Textbloecke. Grep-Output, JSON-Payloads, read_file-Inhalte stehen ungefiltert im Verlauf. Der Nutzer kann den Verlauf nicht schnell ueberfliegen.
- **Akzeptanzkriterien:** (a) Jeder `tool_call` rendert als Karte: Icon (📄 read_file, 🔍 grep, 📝 git_diff, …), Tool-Name, Status-Badge (⏳ running / ✓ ok / ✗ error), Laufzeit. (b) Karte aufklappbar: Input-Parameter + Output (human-readable). (c) Roher JSON nur im "Details"-Toggle innerhalb der Karte. (d) Mehrere Tool-Calls in einer Assistant-Runde: als verschachtelte Container-Karte. (e) Karten scrollen mit der Konversation, keine Modal-Overlays. (f) Farb-Kodiert nach OP-300.
- **Tests:** Keine (UI).
- **Blockiert von:** —

### OP-308: Focus-View (Control-Modus) mit horizontalem Phasen-Wasserfall

- **Status:** open
- **Typ:** ui-feature
- **Phase:** Phase-2 (Focus)
- **Betroffene Dateien:** `static/waterfall.js` (neu), `static/layout.html`, `static/layout.css`
- **Problem:** Die Timeline ist vertikal und listenartig. Bei einem laufenden Run mit 8+ Phasen und 30+ Sub-Events ist nicht erkennbar wo der Run steht und wie die Phasen zueinander stehen.
- **Akzeptanzkriterien:** (a) Im Control-Modus: Timeline als horizontaler Wasserfall (a la Chrome DevTools Performance-Panel). Jede Phase = ein Block, Breite proportional zur Dauer. (b) Aktive Phase blau, fertige gruen, fehlgeschlagene rot. (c) Klick auf Phase: Detail-Bereich darunter mit vertikalen Events (wie heute). (d) Hover auf Phase: Tooltip mit Name + Dauer + Status. (e) Zoom via Scroll-Rad (Zeit-Achse). (f) Im Cockpit-Modus bleibt die vertikale Timeline — Wasserfall nur im Control-Modus.
- **Tests:** Keine (UI).
- **Blockiert von:** OP-306

### OP-309: Chat schwebend im Control-Modus

- **Status:** open
- **Typ:** ui-feature
- **Phase:** Phase-2 (Focus)
- **Betroffene Dateien:** `static/chat.js`, `static/layout.css`
- **Problem:** Im Control-Modus ist der Chat als dritte Spalte zu schmal fuer Laengere Konversation, waehrend der Wasserfall den Platz braucht.
- **Akzeptanzkriterien:** (a) Im Control-Modus: Chat als schwebendes Panel unten rechts (max 400×300px, resizable). (b) Panel-Zustand (offen/geschlossen, Groesse) in localStorage. (c) Doppelklick auf Chat-Header: Maximieren (volle rechte Spalte). (d) Chat weiss im Control-Modus welcher Run aktiv ist → "Frage zu diesem Run" als Placeholder. (e) Im Cockpit- und Debug-Modus bleibt Chat als feste Spalte (wie heute).
- **Tests:** Keine (UI).
- **Blockiert von:** OP-308

### OP-310: Run-Pause/Resume

- **Status:** open
- **Typ:** architektur
- **Phase:** Phase-2 (Focus)
- **Betroffene Dateien:** `werkstatt/loop.py`, `werkstatt/gates.py`, `werkstatt/web/app.py`, `static/runs.js`
- **Problem:** Ein laufender Loop kann nur mit `stop` (kill) beendet werden. Kein sanftes Pausieren, kein Fortsetzen von einem Checkpoint. Der User kann nicht eingreifen ohne den ganzen Run zu verlieren.
- **Akzeptanzkriterien:** (a) `POST /api/projects/{name}/pause` setzt ein Pause-Flag; Loop prueft vor jedem Phase-Start. (b) Pausierter Loop schreibt `loop_paused`-Event, Zustand ist `paused`. (c) `POST /api/projects/{name}/resume` setzt Pause-Flag zurueck, Loop laeuft weiter. (d) UI: `⏸`- und `▶`-Buttons neben laufendem Run. (e) Timeout: Pausierter Run bleibt maximal 1 Stunde pausiert, danach fail-closed (loop_failed mit grund=pause_timeout). (f) Pause/Resume sind idempotent und race-free (Lock).
- **Tests:** `tests/test_loop_pause_resume.py` (neu): (1) Pause-Flag→Loop haelt an, (2) Resume→Loop laeuft weiter, (3) Timeout→fail-closed.
- **Blockiert von:** OP-308

### OP-311: Audit-Filterleiste + Tag-Gruppierung

- **Status:** open
- **Typ:** ui-feature
- **Phase:** Phase-3 (Urgrossvater)
- **Betroffene Dateien:** `static/audit.js`, `static/layout.css`, `werkstatt/web/audit_panel.py`
- **Problem:** Das Audit-Panel zeigt 100+ Events, aber Filter sind rudimentaer (nur `kind` und `run_id`). Kein Volltext-Suche, keine Zeitraum-Filter, keine Tag-Gruppierung. Als Analyse-Werkzeug kaum brauchbar.
- **Akzeptanzkriterien:** (a) Filterleiste: Volltext-Suche, Event-Type-Dropdown (mit Live-Counts), Run-ID-Filter, Zeitraum (24h / 7d / 30d / All). (b) Events gruppiert nach Tag mit Collapsible-Header ("Heute · 143 Events"). (c) Export als CSV und JSON (mit Permission-Gate). (d) Filter persistieren in URL (`?kind=loop_*&days=7`). (e) Kombinierbar mit OP-302 Command Palette (`audit kind:loop_* heute`).
- **Tests:** `tests/test_audit_filter.py` (neu): Query-Parameter→korrekt gefiltert.
- **Blockiert von:** —

### OP-312: Semantic Zoom (Tag ↔ Run ↔ Phase)

- **Status:** open
- **Typ:** ui-feature
- **Phase:** Phase-3 (Urgrossvater)
- **Betroffene Dateien:** `static/zoom.js` (neu), `static/timeline.js`, `static/layout.css`
- **Problem:** Kalender, Runs-Liste, Timeline sind drei getrennte Views mit drei Navigationswegen. Der Nutzer muss wissen welcher View welchen Zeitraum zeigt.
- **Akzeptanzkriterien:** (a) Drei Zoom-Stufen: Monat (Kalender), Run (Phasen-Uebersicht), Phase (Events). (b) Uebergang per Scroll-Rad (vertikal) oder `Cmd+0/1/2`. (c) Sanfte Animation (300ms ease). (d) Aktuelle Zoom-Stufe sichtbar (Breadcrumb oben: "November 2026 › Run 0425 › Phase 3 Builder"). (e) In jeder Stufe: Klick auf Element zoomt naechste Stufe tiefer. (f) Breadcrumb-Klick zoomt zurueck.
- **Tests:** Keine (UI).
- **Blockiert von:** OP-308

### OP-313: Ghost Intents (plan_intent + Vorschau + Blockieren)

- **Status:** open
- **Typ:** architektur
- **Phase:** Phase-3 (Urgrossvater)
- **Betroffene Dateien:** `werkstatt/builder.py`, `werkstatt/reviewer.py`, `werkstatt/loop.py`, `static/timeline.js`
- **Problem:** Der Loop schreibt Events erst nach der Aktion. Der Nutzer sieht nichts von geplanten Aktionen. Kein Eingreifen bevor Code geschrieben ist.
- **Akzeptanzkriterien:** (a) Builder/Reviewer schreiben `plan_intent`-Event BEVOR sie eine Datei aendern: `{intent: "patch"|"write"|"delete", file: ..., estimated_lines: N, reason: ...}`. (b) UI zeigt Intent-Karten als "Ghost"-Vorschau (gestrichelter Rand, gedaempfte Farbe). (c) Nutzer kann Intent blockieren: `POST /api/runs/{id}/intents/{intent_id}/block` → Loop bricht diese Aktion ab, schreibt `intent_blocked`-Event. (d) Timeout: Unbeantwortete Intents nach 30s automatisch approven (default) ODER fail-closed (config). (e) Config-Setting: `intent_mode: "ghost"|"blind"` pro Projekt.
- **Tests:** `tests/test_plan_intent.py` (neu): Intent→block→Loop-Abbruch; Intent→timeout→approve.
- **Blockiert von:** OP-310

### OP-314: Explaining Presence (Right-Click → Chat erklaert)

- **Status:** open
- **Typ:** ui-feature
- **Phase:** Phase-3 (Urgrossvater)
- **Betroffene Dateien:** `static/timeline.js`, `static/chat.js`, `static/contextmenu.js` (neu)
- **Problem:** Wenn der Nutzer ein Event im Audit sieht, muss er selbst interpretieren was es bedeutet. Er kann nicht "Was ist hier passiert?" fragen.
- **Akzeptanzkriterien:** (a) Rechtsklick auf Timeline-Knoten / Audit-Event / Chat-Message: Kontextmenue mit "Was passierte hier?". (b) Klick sendet Nachricht an Chat mit Event-ID + Kontext: "Erklaere dieses Event: <kind> <payload>. Nutze read_status und grep um Kontext zu sammeln." (c) Chat-Antwort ist im Chat sichtbar UND als Tooltip/Popup direkt am Element. (d) Erreichbar auch via Command Palette: "explain last error" / "explain this event".
- **Tests:** Keine (UI).
- **Blockiert von:** OP-307

### OP-315: Causal Chain (Initiator-Referenzen in Timeline)

- **Status:** open
- **Typ:** ui-feature
- **Phase:** Phase-3 (Urgrossvater)
- **Betroffene Dateien:** `static/timeline.js`, `werkstatt/audit.py`
- **Problem:** Ein Timeline-Knoten zeigt "explorer_result" — aber nicht warum. Der Nutzer muss Events manuell in Beziehung setzen.
- **Akzeptanzkriterien:** (a) Audit-Events bekommen optional ein `caused_by`-Feld (seq oder audit_id des Vorgaengers). (b) Timeline zeigt pro Knoten eine "Initiator"-Zeile: `← loop_explorer_suchbegriffe ← explorer_messung → planner_scout_ok`. (c) Klick auf Initiator springt zu diesem Event. (d) Events ohne `caused_by`: Heuristik (chronologisch letzter Event derselben Rolle).
- **Tests:** `tests/test_causal_chain.py` (neu): Heuristik findet korrekte Vorgaenger.
- **Blockiert von:** —

### OP-316: Living Typography

- **Status:** open
- **Typ:** ui-politur
- **Phase:** Phase-4 (Politur)
- **Betroffene Dateien:** `static/layout.css`
- **Problem:** Schriftgroessen sind heute fix (11/12/13px). Bei "active" Runs ist die UI genauso ruhig wie im Idle — kein visuelles Signal dass etwas wichtig ist.
- **Akzeptanzkriterien:** (a) Font-Size-Scale skaliert mit Modus und Status: Idle = 11px body, Active Run = 13px, Failure = 14px. (b) Line-Height skaliert mit (1.4/1.5/1.6). (c) Semantische Font-Familien: User-Messages Serif (Absicht), Agent-Antworten Sans (Reaktion), Tool-Calls Mono (Aktion), System-Hinweise Small-caps (Kontext). (d) Schriftgroessen-Wechsel animiert 200ms.
- **Tests:** Keine (visuell).
- **Blockiert von:** OP-306

### OP-317: Hover-Previews mit Konsequenz-Vorschau

- **Status:** open
- **Typ:** ui-politur
- **Phase:** Phase-4 (Politur)
- **Betroffene Dateien:** `static/hover_preview.js` (neu), `static/layout.css`
- **Problem:** Hover zeigt heute nur Tooltip mit Titel. Der Nutzer muss klicken um zu sehen was passieren wuerde.
- **Akzeptanzkriterien:** (a) Hover ueber OP-Zeile: Ghost-Preview mit Blockiert-von-Status, geschaetzter Dauer, Token-Schaetzung. (b) Hover ueber "Start Loop"-Button: Preview mit Aufgabe, Phasen-Schaetzung, Zeit-Schaetzung. (c) Hover ueber Gate-Button: Preview mit Konsequenz ("j = bauen, n = Loop-Abbruch"). (d) Preview erscheint nach 400ms Hover, verschwindet nach 100ms ohne Hover. (e) Preview ist klickbar (Link zur Detail-Ansicht).
- **Tests:** Keine (UI).
- **Blockiert von:** OP-305


### OP-318: Legacy-OPs 1XX auditieren

- **Status:** open
- **Typ:** doku-cleanup
- **Phase:** Phase-0 (Vorbereitung)
- **Betroffene Dateien:** `docs/STATUS.md`, `PROGRESS.md`, `docs/adr/`
- **Problem:** 15 OPs im 1XX-Bereich (OP-101, 105-107, 109-110, 112-113i, 115-118, 120-121) stammen aus der Pre-Loop-Neubau-Zeit. Manche sind nach dem Neubau obsolet (Legacy-Refactorings, alte Pfade), andere nicht. Ohne Pruefung ist die Liste mit Zombie-OPs ueberladen — der Loop kann sie nicht sinnvoll priorisieren.
- **Akzeptanzkriterien:** (a) Jede 1XX-OP einzeln gegen aktuellen Code pruefen: betroffene Datei existiert noch? Fordert das was der Code heute nicht hat? (b) Kategorisierung: `kill` (obsolet, in Delete-Zone), `keep` (weiterhin relevant), `transform` (AK an aktuellen Code anpassen). (c) Ergebnis als Tabelle in `PROGRESS.md` dokumentiert. (d) Kill-Kandidaten in Delete-Zone verschieben (mit Begruendung + Commit-Referenz).
- **Tests:** Keine (Doku-Audit).
- **Blockiert von:** —


### OP-330: Skill script-bank (Manifest + Struktur)

- **Status:** open
- **Typ:** skill-fundament
- **Phase:** Phase-2 (Intelligenz)
- **Betroffene Dateien:** `skills/script-bank/SKILL.md` (neu), `skills/script-bank/MANIFEST.yaml` (neu), `skills/script-bank/tools/` (neu), `werkstatt/script_bank.py` (neu)
- **Problem:** Chat-Debugger und Loop schreiben Analyse-Scripts jedes Mal neu. Kein Manifest, keine Versionierung, keine Variable-Bindung an Projekt-Kontext.
- **Akzeptanzkriterien:** (a) `MANIFEST.yaml` mit Schema: `name`, `beschreibung`, `parameter`, `kategorie` (analyze|debug|test|verify), `sicherheitsstufe` (read|write-dry|write-sandbox). (b) `script_bank.py` mit `list_scripts(kategorie=None)`, `call(name, params, project_root)`. (c) Scaffolder-Vertrag dokumentiert (Pflicht-Variablen: `project_root`, `python_bin`, `test_command`). (d) 0 Scripts (nur Geruest).
- **Tests:** `tests/test_script_bank.py` (3 Tests).
- **Blockiert von:** —

### OP-331: Script-Bank — erste 6 Kern-Scripts

- **Status:** open
- **Typ:** skill-inhalt
- **Phase:** Phase-2 (Intelligenz)
- **Betroffene Dateien:** `skills/script-bank/tools/pytest_analyze.py`, `ruff_analyze.py`, `mypy_analyze.py`, `git_diff_analyze.py`, `test_integrity.py`, `dependency_graph.py`, `MANIFEST.yaml`
- **Problem:** Erste sechs Analyse-Scripts fehlen. Decken 90% der Alltags-Fehler ab.
- **Akzeptanzkriterien:** (a) Jedes Script: `analyze()` liefert `{kategorie, ursache, betroffene_dateien[], beispiel_ohne_code, confidence}`. (b) Parameter aus ENV/Config. (c) Alle <5s. (d) Read-only.
- **Tests:** `tests/test_script_bank_tools.py` (6 Tests).
- **Blockiert von:** OP-330

### OP-332: Scaffolder-Vertrag Script-Bank

- **Status:** open
- **Typ:** skill-fundament
- **Phase:** Phase-2 (Intelligenz)
- **Betroffene Dateien:** `werkstatt/scaffold.py`, `skills/script-bank/SKILL.md`, `werkstatt/templates/werkstatt/script-bank.yaml` (neu)
- **Problem:** Scripts brauchen Projekt-Kontext. Ohne Scaffolder-Vertrag fehleranfaellig.
- **Akzeptanzkriterien:** (a) Scaffolder schreibt `.werkstatt/script-bank.yaml`. (b) `script_bank.call()` liest fehlende Parameter daraus. (c) Template vorhanden. (d) Fehlende Variablen: fail-loud.
- **Tests:** `tests/test_scaffold_scriptbank.py` (3 Tests).
- **Blockiert von:** OP-330

### OP-333: Chat-Debugger-Integration Script-Bank

- **Status:** open
- **Typ:** skill-wiring
- **Phase:** Phase-2 (Intelligenz)
- **Betroffene Dateien:** `werkstatt/chat_tools.py`, `werkstatt/chat_agent.py`, `tests/test_chat_script_bank.py` (neu)
- **Problem:** Chat-Agent hat 8 Tools, aber keinen Script-Aufruf. Debugger schreibt Analyse-Scripts jedes Mal neu.
- **Akzeptanzkriterien:** (a) Chat-Tool `run_script {name, params}`. (b) Sicherheitspruefung: `write-sandbox` nur mit `mode=write`. (c) Rueckgabe JSON. (d) In `openai_schemas()`.
- **Tests:** `tests/test_chat_script_bank.py` (3 Tests).
- **Blockiert von:** OP-330, OP-331

### OP-334: Loop-Reflection-Integration Script-Bank

- **Status:** open
- **Typ:** skill-wiring
- **Phase:** Phase-2 (Intelligenz)
- **Betroffene Dateien:** `werkstatt/reflection.py`, `werkstatt/verify.py`, `tests/test_reflection_script_bank.py` (neu)
- **Problem:** Reflection bekommt `last_verify_errors` als Rohtext. Typisierter Fehler waere besser.
- **Akzeptanzkriterien:** (a) `verify.py` liefert `fehler_kategorie`. (b) Reflection ruft passenden Analyzer. (c) Fallback Rohtext. (d) Kein Aufruf bei Erfolg.
- **Tests:** `tests/test_reflection_script_bank.py` (4 Tests).
- **Blockiert von:** OP-331

### OP-340: Reviewer-Bug-Schema loesungsorientiert

- **Status:** open
- **Typ:** prompt-fundament
- **Phase:** Phase-2 (Intelligenz)
- **Betroffene Dateien:** `werkstatt/reviewer.py`, `tests/test_reviewer_schema.py` (neu)
- **Problem:** Heute: `{file, line, description, severity}`. Kein `warum`, kein `wie_loesen`, kein `beispiel`. Reflection bekommt nur "X ist falsch".
- **Akzeptanzkriterien:** (a) Neues Schema: `{file, line, severity, warum, wie_loesen, beispiel_ohne_code}`. (b) `description` als Alias auf `warum` (rueckwaertskompatibel). (c) `REVIEWER_SYSTEM` fordert Prosa, keine Codebloecke. (d) `beispiel_ohne_code` max 3 Saetze.
- **Tests:** `tests/test_reviewer_schema.py` (3 Tests).
- **Blockiert von:** —

### OP-341: Reflection + Hook + Gedaechtnis auf loesungsorientiert

- **Status:** open
- **Typ:** prompt-fundament
- **Phase:** Phase-2 (Intelligenz)
- **Betroffene Dateien:** `werkstatt/reflection.py`, `werkstatt/phases/*`, `werkstatt/erfahrung.py`, `tests/test_reflection_loesungsorientiert.py` (neu)
- **Problem:** Reflection-Feedback uneinheitlich. Kein Loesungs-Schema.
- **Akzeptanzkriterien:** (a) Einheitliches Schema: `{warum, wie_loesen, beispiel_ohne_code, confidence}`. (b) Reflection-Prompt: "Analysiere + Repariere". (c) Hook: gleicher Vertrag. (d) Gedaechtnis: `record_erfahrung(warum, wie, beispiel, ...)`. (e) **Bug mit Zeilen-Kontext:** Jeder Bug traegt `{file, line_start, line_end, code_ausschnitt}` (max 20 Zeilen). Ohne Zeilenangabe ist der Bug ungueltig — fail-loud. (f) **Vollstaendiger Verlauf im Prompt:** Der Reviewer sieht alle vorherigen Bug-Meldungen ALLER Runden (nicht nur n-1), jede mit Zeilen und Code-Ausschnitt. Kontext bleibt eng: pro Runde max 5 Bugs (aeltere werden zusammengefasst, nie stumm verworfen). (g) **Delta-Klassifikation:** Pro Bug einer von `bestehend | behoben | neu | verschoben`. Identitaet = Hash aus `(file, kategorie, code_ausschnitt_normalisiert)`. (h) **Kausale Kette bei `bestehend`:** Pflichtfelder `alter_vorschlag`, `warum_alter_vorschlag_scheiterte`, `kausale_kette` ("Patch Runde N hat Zeile X-Y geaendert, dadurch brach Zeile Z"), `neuer_vorschlag`. Reines Neuvorschlagen ohne Kette = Fail. Bei `neu` reicht frischer Vorschlag. Grund: ohne kausale Rekonstruktion raet der Agent blind und der Loop dreht im Kreis (Zirkel-Falle).
- **Tests:** `tests/test_reflection_loesungsorientiert.py` (8 Tests).
- **Blockiert von:** OP-340

### OP-342: Prompt-Engineering pro Rolle (Lichtkegel-Prinzip)

- **Status:** open
- **Typ:** prompt-fundament
- **Phase:** Phase-2 (Intelligenz)
- **Betroffene Dateien:** `werkstatt/planner.py`, `werkstatt/builder.py`, `werkstatt/reviewer.py`, `werkstatt/reflection.py`, `werkstatt/architect.py`, `werkstatt/scout.py`, `werkstatt/explorer.py`
- **Problem:** System-Prompts gewachsen, nicht entworfen. Rollen sehen zu viel oder zu wenig.
- **Akzeptanzkriterien:** (a) Pro Rolle dokumentiert: Sichtfeld, Ziel, Loesungsvertrag. (b) Prompt-Abschnitte entfernt falls redundant. (c) `_build_selbst_check_block` nur auf Nicht-Reasoning. (d) Token-Verbrauch pro Rolle dokumentiert.
- **Tests:** `tests/test_prompt_kontrakte.py` (7 Tests).
- **Blockiert von:** OP-340, OP-341

### OP-350: Scaffolder Greenfield-Modus

- **Status:** open
- **Typ:** feature-fundament
- **Phase:** Phase-1 (Cockpit-Fundament)
- **Betroffene Dateien:** `werkstatt/scaffold.py`, `werkstatt/templates/greenfield/` (neu), `tests/test_scaffold_greenfield.py` (neu)
- **Problem:** `scaffold.py` legt PFLICHTDATEIEN an, aber ohne Greenfield-Struktur (leere Verzeichnisse, minimale Config, Verify-Kette, OP-Stub, Script-Bank-Variablen).
- **Akzeptanzkriterien:** (a) `scaffold(name, dir, greenfield=True)` erzeugt: `src/`, `tests/`, `.werkstatt/`, `docs/adr/`, `docs/STATUS.md` mit 3 Starter-OPs. (b) `.gitkeep`. (c) `.werkstatt/script-bank.yaml` mit `excluded_from_explorer`-Liste (`.env`, `.env.*`, `*.secret`, `*.pem`, `*.key`, `credentials*`, `*token*`). (d) `.env`-Template mit Platzhaltern statt echten Werten (`DB_HOST=<set-me>`). (e) Explorer (`werkstatt/explorer.py`) respektiert `excluded_from_explorer` aus `script-bank.yaml` — fail-closed wenn Datei fehlt: `.env`-Dateien werden NIE gelesen, auch ohne Config. (f) Idempotent, `--dry-run`.
- **Tests:** `tests/test_scaffold_greenfield.py` (6 Tests: Struktur, idempotent, dry-run, fehlendes Arg, `.env`-Template, Explorer-Filter).
- **Blockiert von:** OP-332

### OP-351: UI-Maske Projekt-Anlage

- **Status:** open
- **Typ:** ui-feature
- **Phase:** Phase-1 (Cockpit-Fundament)
- **Betroffene Dateien:** `static/layout.html`, `static/tabs.js`, `static/layout.css`, `werkstatt/web/app.py` (`POST /api/projects/create`), `tests/test_project_create_api.py` (neu)
- **Problem:** Projekte heute nur per CLI. Kein UI-Weg.
- **Akzeptanzkriterien:** (a) `+`-Button oeffnet Modal: Name, Pfad, greenfield. (b) `POST /api/projects/create` ruft `scaffold`. (c) Nach Erfolg Tab. (d) Fehler-Feedback. (e) Pfad nur unter `/opt/`.
- **Tests:** `tests/test_project_create_api.py` (4 Tests).
- **Blockiert von:** OP-350

### OP-352: Scaffolder-Drift-Check + Tests

- **Status:** open
- **Typ:** verify-fundament
- **Phase:** Phase-1 (Cockpit-Fundament)
- **Betroffene Dateien:** `tools/scaffold_drift.py` (neu), `tools/verify.json`, `tests/test_scaffold_drift.py` (neu)
- **Problem:** Konventions-Aenderung → niemand merkt ausser manueller `migrate.py`.
- **Akzeptanzkriterien:** (a) `--check` prueft alle `/opt/*` gegen `PFLICHTDATEIEN`. (b) Rueckgabe fehlender Dateien. (c) verify-Stage `scaffold_drift` (weich). (d) `migrate.py` nutzt gleiche Logik.
- **Tests:** `tests/test_scaffold_drift.py` (3 Tests).
- **Blockiert von:** OP-350, OP-351

### OP-360: Skill senior-architekt

- **Status:** open
- **Typ:** skill-fundament
- **Phase:** Phase-1 (Cockpit-Fundament)
- **Betroffene Dateien:** `skills/senior-architekt/SKILL.md` (neu), `skills/senior-architekt/WERKZEUGE.md` (neu)
- **Problem:** Leeres Geruest, Idee im Kopf, kein Weg zu Architektur + OPs.
- **Akzeptanzkriterien:** (a) SKILL.md mit Rolle, Dialog-Fokus, Konventionen, Ergebnisformat. (b) Werkzeuge: File-Explorer, Konventions-Lookup, OP-Writer, Roadmap-Compiler (OP-282). (c) Beispiel-Dialog. (d) Fail-closed ohne User-Input.
- **Tests:** `tests/test_skill_senior_architekt.py` (2 Tests).
- **Blockiert von:** OP-282, OP-350

### OP-361: Senior-Architekt Dialog-Flow

- **Status:** open
- **Typ:** skill-wiring
- **Phase:** Phase-1 (Cockpit-Fundament)
- **Betroffene Dateien:** `werkstatt/chat_agent.py` (oder `arch_agent.py`), `static/chat.js`, `tests/test_arch_dialog.py` (neu)
- **Problem:** Skill alleine reicht nicht — Dialog mit User noetig.
- **Akzeptanzkriterien:** (a) Chat-Modus `architekt`. (b) Schrittweise: Idee → Anforderungen → Ordnerstruktur → Komponenten → erste OPs. (c) Jede Antwort: Rueckfrage oder naechster Schritt. (d) "Fertig" schreibt nach `docs/`.
- **Tests:** `tests/test_arch_dialog.py` (3 Tests).
- **Blockiert von:** OP-360

### OP-362: Senior-Architekt schreibt Plan-Artefakte

- **Status:** open
- **Typ:** skill-wiring
- **Phase:** Phase-1 (Cockpit-Fundament)
- **Betroffene Dateien:** `werkstatt/arch_agent.py`, Templates, `tests/test_arch_output.py` (neu)
- **Problem:** Am Ende muss Architekt konkrete Artefakte schreiben.
- **Akzeptanzkriterien:** (a) `schreibe_plan(idee, struktur, komponenten)` → 3 Dateien. (b) OPs OP-001..OP-005 mit Blocker-Ketten. (c) `docs/ARCHITECTURE.md` nennt Ordner, Komponenten, Abhaengigkeiten. (d) User-Bestaetigung.
- **Tests:** `tests/test_arch_output.py` (3 Tests).
- **Blockiert von:** OP-360, OP-361

### OP-370: detect() — Secret-Detection ohne Redaction

- **Status:** open
- **Typ:** security
- **Phase:** Phase-3 (Politur, aber früh)
- **Betroffene Dateien:** `werkstatt/redaction.py` (neu), `werkstatt/audit.py`, `static/statusleiste.js`, `static/layout.css`, `tests/test_redaction.py` (neu)
- **Problem:** Werkstatt arbeitet an Code, aber Explorer/Builder/Reviewer lesen Dateien die API-Keys, .env-Werte, IPs oder Credentials-URLs enthalten können. Die landen dann im LLM-Prompt (DeepSeek) im Klartext. Kein Schutz, kein Warnsystem.
- **Akzeptanzkriterien:** (a) `detect(text) -> list[Finding]` mit Finding=`{typ, start, ende}`. Katalog: `ip4`, `ip6`, `api_key` (sk-, ghp_, xoxb-, AKIA, ...), `email`, `credential_url` (scheme://user:pass@...), `private_path` (/home/<user>/, /Users/<user>/). (b) `audit()` prueft Payload bei jedem Aufruf — bei Finding: Event `secret_detected {typ, quelle_kind}` (NICHT der Original-Wert). (c) Statusbar zeigt Warnung `\u26a0 N Secrets` (`--sem-warn`) bei `secret_detected` in letzten 24h. (d) Kein Restore, keine Redaction, keine LLM-Aenderung. (e) Doku-Klarstellung im SKILL: Detect ist Hinweis, keine Garantie — bei echten Secrets lokales Modell waehlen.
- **Tests:** `tests/test_redaction.py` (10 Tests: pro Typ Positiv, Negativ-Kontexte, Performance <5ms/10k Zeichen).
- **Blockiert von:** —

### OP-306b: Workspace-Overview-Shell (Projekt-Karten + Sparklines + Home-Navigation)

- **Status:** open
- **Typ:** ui-feature
- **Phase:** Phase-1 (UI bereitstellen)
- **Betroffene Dateien:** `werkstatt/web/app.py` (`GET /api/overview`), `werkstatt/web/aggregate.py` (Sparkline/KPI-Aggregation, falls nicht vorhanden: neu), `static/overview.js` (neu), `static/tabs.js` (Home-Button + Pause-Logik), `static/layout.html` (Overview-Screen + Home-Button + CSS-Variablen), `tests/test_overview.py` (neu), `tests/test_overview_shell_spec.py` (neu)
- **Problem:** (1) Angelegte Projekte in `/opt/*` sind unsichtbar wenn sie keinen Tab haben. (2) Der Startzustand ist ein einzelner `werkstatt`-Tab statt einer Uebersicht — Profi-Standard (JetBrains New UI, VS Code Welcome, Linear, Notion) ist ein Overview-Screen mit Projekt-Karten und dauerhaft erreichbarer Home-Navigation. (3) Kein visuelles Feedback zur Bau-Aktivitaet pro Projekt, obwohl die Daten (Event-Architektur OP-319..323) vorhanden sind.
- **Akzeptanzkriterien:**
  (a) Overview-Screen als Default bei leerem Storage (statt `werkstatt`-Tab) — ersetzt OP-306a-Fallback.
  (b) Overview zeigt Projekt-Karten fuer alle `/opt/*`-Projekte mit `docs/STATUS.md`.
  (c) Jede Karte zeigt: Status-Dot (Loop laeuft / fertig / Fehler / idle), 30-Tage-Sparkline der Loop-Runs (SVG `<polyline>`), KPI-Zeile (Runs total, Erfolgsquote, offene OPs), relativer letzter Run.
  (d) Top-Bereich "Diese Woche am meisten gebaut": Top-3 Projekte nach Run-Anzahl (7-Tage-Fenster).
  (e) Home-Button in der Tab-Leiste (immer sichtbar): klick → Overview kommt nach vorne, Tabs bleiben im Hintergrund erhalten.
  (f) Klick auf Projekt-Karte → Tab wird erstellt (falls nicht vorhanden) + aktiv.
  (g) Klick auf Tab (der im Hintergrund war) → zurueck in Projekt, Overview wird pausiert.
  (h) Fallback: keine Projekte → Overview mit Hinweis "Keine Projekte — Neues anlegen" (nutzt `project_create.js`-Modal).
- **Tests:** `tests/test_overview.py` (~12 Tests: Backend-Aggregation, Sparkline-Daten, Top-3, Erfolgsquote, Fallback bei 0 Projekten) + `tests/test_overview_shell_spec.py` (~8 Tests: Spec-First via `OverviewSpiegel`-Klasse: Home-Klick, Projekt-Klick, Tab-Pause, Default-Overview, Fallback). Spec-First nach ADR-0015/0016.
- **Blockiert von:** —

### OP-324: Planner-Qualitaet haerten (Architect-Block 5 strukturell)

- **Status:** open
- **Typ:** architektur (Prompt + Dependency-Qualitaet)
- **Phase:** Phase-1 (Cockpit-Fundament)
- **Betroffene Dateien:** `werkstatt/planner.py`, `tests/test_planner_deps_hybrid.py`, `tests/test_planner_struktur.py` (neu)
- **Problem:** ADaPT war Nothelfer fuer schlechte Plaene und wurde 2026-11-08 entfernt (Commit c94ed52). Ohne ADaPT muss der Plan von Anfang an logisch korrekt sein (Interface -> Backend -> Tests). `_leite_deps_deterministisch` (OP-187) existiert, aber Architect-Block 5 ("Dependencies") wird als Freitext geliefert, nicht strukturell. Ohne strukturierten Block 5 greift die Heuristik (test/baseline/doku warten auf alle code-Tasks), was zu groben Deps fuehrt.
- **Akzeptanzkriterien:** (a) ARCHITECT-Prompt fordert `## BLOCK 5: DATEI-ABHAENGIGKEITEN` mit Format `<datei>: <deps>` — fail-loud bei fehlendem Block. (b) Test: Architect-Output ohne Block 5 fuehrt zu `audit("architect_block5_fehlt")` (neuer Kind). (c) Neuer Test `test_planner_struktur.py`: 5 Szenarien (einfach, multi-file, kreisfoermig, fehlend, explizit-"keine") gegen `_leite_deps_deterministisch`. (d) `_parse_architect_deps_block` haerten: parst Whitespace-Varianten (`<datei> -> <deps>`, `<datei>: <deps>`), lehnt Freitext explizit ab. (e) Mindestens 3 echte Loop-Tests mit vollstaendigem Architect-Block 5, in PROGRESS.md dokumentiert.
- **Tests:** `tests/test_planner_struktur.py` (5 Szenarien) + Erweiterung `tests/test_planner_deps_hybrid.py` (+3 Block-5-Format-Tests). Gesamt 8 neue Tests.
- **Blockiert von:** —

### OP-393: Phase-Review-Gate nutzt input() statt gate_bridge

- **Status:** open
- **Typ:** bugfix
- **Phase:** Phase-2 (Focus, blockiert Loop-aus-UI)
- **Blockiert von:** —
- **Quelle:** Live-Test 2026-11-10 10:23 (Run werkstatt-20261110-101720-3fa14f18). Nach reviewer_phase_rejected kommt loop_human_gate_eof -> Loop sofort failed. Der Loop-Plan-Gate funktioniert (nutzt `_frage_gate` -> `gate_bridge`), aber der Phase-Review-Human-Gate (`_human_gate_body`) und weitere interaktive Stellen nutzen direkt `input()`. Im `--headless`-Modus (stdin=/dev/null) wirft `input()` sofort `EOFError` -> `loop_human_gate_eof` -> `loop_gate_failed`.
- **Betroffene Dateien:** `werkstatt/phases/review.py` (`_phase_review_gate` — der TTY-Check bei Z. 30-38 schlaegt im headless-Modus fehl, ruft sofort `loop_human_gate_eof`). Der Commit-Gate in `gates.py::_human_gate` nutzt dagegen bereits `_frage_gate` und ist OK. `tests/test_phase_review_gate.py` (bestehend, bleibt gruen), plus neuer Test `test_phase_review_headless`.
- **Problem:** Live-Beleg 2026-11-10: `789819 reviewer_phase_rejected`, `789820 loop_human_gate_eof` (gleiche Sekunde = kein User-Wait, sofortiger EOFError), `789821 loop_gate_failed`, `789825 loop_failed`. Der Loop kam durch Explorer, Plan-Gate (Klick j), Builder t1-t3, Reviewer bis zur Phase-Review. Erst der Phase-Review-Human-Gate crasht, weil er nicht `gate_bridge` nutzt.
- **Akzeptanzkriterien:**
  (a) Alle interaktiven `input()`-Aufrufe in `gates.py` (Ausnahme `_frage_gate`-intern) sind durch `_frage_gate` ersetzt.
  (b) Im `--headless`-Modus erscheint ein `gate_open` mit `kind=phase_review` im UI; Nutzer klickt `j` -> `gate_answered` -> Loop faehrt fort.
  (c) Test `tests/test_human_gate_body.py`: mit `_HEADLESS=True` und gefaktem `gate_bridge.wait` liefert der Gate `j` -> kein `loop_human_gate_eof`.
- **Tests:** `tests/test_human_gate_body.py` (2-3 Tests).
- **Grund:** Loop-aus-UI laeuft heute bis Phase-Review und crasht dann.

### OP-394: Live-Feed UI-Redesign — semantische Labels + Sortierung

- **Status:** open
- **Typ:** ui-feature
- **Phase:** Phase-2 (UI-Ehrlichkeit)
- **Blockiert von:** —
- **Quelle:** Live-Test 2026-11-10 10:17-10:23. UI-Kritik: (a) Reviewer blitzt auf, dann weg (Aktiv-Block zeigt nur letztes Event), (b) Sortierung verwirrend (neuestes unten, aktueller Run oben), (c) keine semantischen Verben ("denke nach", "plane", "splitte", "baue" fehlen).
- **Betroffene Dateien:** `werkstatt/web/inspector.py` (`_tl_detail`, `_tl_label`, `aggregate_live_feed` — Sortierung explizit), `static/live_feed.js` (Sortierung, Aktiv-Block).
- **Problem:** Aktiv-Block zeigt nur letztes Event; Sortierung implizit (Backend/Frontend nicht abgestimmt); `aktion` im Live-Feed ist `kind` (technisch), kein semantisches Verb.
- **Akzeptanzkriterien:**
  (a) Live-Feed-Steps explizit chronologisch aufsteigend sortiert (dokumentiert).
  (b) Aktiv-Block zeigt auch gerade-fertig-gewordene Rollen (5s-Fenster).
  (c) Semantische Aktion pro Zeile: `loop_phase architect` → "Architect denkt", `loop_phase planner` → "Planner splittet Plan", `builder_file_context` → "Builder liest N Dateien", `builder_patches_erstellt` → "Builder liefert N Patches", `loop_verify_ok` → "Verify OK", `gate_answered` → "Antwort: j". Fallback: `_tl_detail`.
  (d) Test `tests/test_live_feed_semantik.py`: 5-6 Kinds mit je erwartetem Aktions-String.
- **Tests:** `tests/test_live_feed_semantik.py` (neu), `tests/test_live_feed_backend.py` erweitert.
- **Grund:** UI zeigt technische Kinds. Ohne semantische Labels ist Loop im Live-Test schwer nachvollziehbar.

### OP-395: Builder-Event-Emission waehrend LLM-Call

- **Status:** open
- **Typ:** ui-feature
- **Phase:** Phase-3 (Loop-Telemetrie)
- **Blockiert von:** —
- **Quelle:** Live-Test 2026-11-10. Builder-Phase hat 30-60s Luecke ohne Events (`builder_file_context` 10:20:59 -> `builder_patches_erstellt` 10:21:49). UI wirkt "Builder tot".
- **Betroffene Dateien:** `werkstatt/roles/builder/run.py` (LLM-Call-Stelle), optional `static/live_feed.js`.
- **Problem:** Zwischen `builder_import_context` und `builder_patches_erstellt` liegen 40-60s (LLM-Call). Kein Zwischen-Event. Explorer/Scout/Reviewer haben alle `llm_call_start`/`llm_call_end` — nur Builder nicht.
- **Akzeptanzkriterien:**
  (a) Builder emittiert `llm_call_start`/`llm_call_end` um den LLM-Aufruf.
  (b) Alternative: Heartbeat-Event alle 5s.
  (c) Live-Feed zeigt "Builder denkt (35s)".
- **Tests:** `tests/test_live_feed_backend.py` erweitert, `tests/test_builder.py` (Event-Reihenfolge).
- **Grund:** UI-Ehrlichkeit. "Builder tot" ist falsche Interpretation eines arbeitenden Loops.

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

- 2026-11-09 | OP-110 | done | `_pruefe_zieldatei_existenz` erkennt create-bei-existierender-Datei (Commit 72a8d4f). **Live-Bug 22:15:** Planner-LLM gab `action=create` fuer `inspector.py` (existiert), Builder korrigierte auf `update` (Datei-Realitaet), Builder-Check erwartete `create` -> `builder_patch_invalid` -> 5x Reflection -> `loop_failed`. Fix: neue Bedingung `if aktion==create and ziel_pfad.exists(): aktion = update` analog zur bestehenden `update->create`-Regel. **Spec-Test:** `tests/test_planner.py::test_pruefe_zieldatei_existenz_create_bei_existierender_datei_wird_update`. **Revert-Beweis:** Regel raus -> Test rot. Baseline: 1604 -> 1605 passed.

- 2026-11-09 | OP-381c | done | Gate-Modal ersetzt 460px-Draggable-Panel (Commits de77082 + 05bc3fc). **Backend (`de77082`, Etappe 1):** `signal_open(typ="jna")`, `_frage_gate` leitet `typ` aus `kind` ab (`plan_reason` -> `freitext`), `aggregate_gate_context` reicht `typ` durch. **Frontend (`05bc3fc`):** neues Modal (max 900px, max 90vh, scale 0.96->1 180ms), Backdrop mit `backdrop-filter: blur(8px)`, Banner oben mit Pulse + Dismiss, Copy-Button (`navigator.clipboard`), Plan-Bereich 400px scrollbar mit `.gm-h2`/`.gm-li`-CSS-Markdown, Sections (Diff/Scout/Historie) als `<details>` mit 300px, Actions sticky. `typ=jna` -> Buttons, `typ=freitext` -> Textarea (Enter sendet, Shift+Enter Zeilenumbruch). `Escape`/Backdrop schliessen. `_machDraggable` entfernt. **Spec-Tests:** `tests/test_gate_bridge.py` 3 neu, `tests/test_ui_gate_modal.py` 15 Source-Scan. **Revert-Beweise:** 2 Tests (Bridge), Source-Scan. Baseline: 1591 -> 1682 passed (kumulativ mit 381d-k).

- 2026-11-09 | OP-381-Serie (d/e/f/g/h/i/j/k) + Ad-hoc-Fixes | done | Ad-hoc-Serie ohne eigene STATUS-Header (im Chat abgenickt, in Commits dokumentiert). **381d (a1caf53):** `aggregate_ambient.gates_open` konsistent mit `aggregate_gate_context` (vorher 2 vs 0-Widerspruch). **381e (5b05f43):** Read-Through `_frische_projektion()` (Projector.tail vor UI-Aggregatoren) gegen SQLite-Lag bei <100 Events. **381f (c868fc1):** `aggregate_timeline` ignoriert `-migrated-*-Dateien` (vorher las es den statischen OP-323-Dump, zeigte 4 alte Events statt 143). **381g (b35502d):** `loop_phase:build`-Marker in `_phase_tasks_loop` (Timeline gruppiert Builder/Verify/Reflection jetzt unter Build statt Plan). **381h (e5a4101 + b44da43):** Rollen pro Kind (`_tl_rolle` mit `agent`-Vorrang + `loop_*`-Prefixe fuer Loop-Events), `aggregate_timeline_aktiv` (Live-Rollen-Status 300s-Fenster), `_TL_AGENT_ROLLEN` + `_TL_KIND_ROLLEN`-Map. **381i (ca6f0e7 + 1200484 + e3a6299 + 697fe46 + 3671fe9):** Swimlane-Wasserfall Backend (`aggregate_swimlane`: start/end-Paar-Gruppierung, 5s-Einzel-Events, Lanes nach Rollen-Reihenfolge) + Frontend (`waterfall.js`: SVG-Renderer, Zeit-Achse, Rollen-Farben aus sem-Variablen, 8px-Balken, `_fmtTick` kompakt) + Runs-Sidebar togglebar (`body[data-runs-open]`, Taste `r`) + Umzug ins Cockpit als Nachanalyse (ADR-0022a). **381j (262ed8b + e37b705 + ba78af5):** Live-Feed Backend (`aggregate_live_feed`: chronologische Steps, `aktiv` aus `_tl_aggregate_aktiv`, `naechster`-Heuristik explorer->scout->architect->planner->builder->verify->reviewer->loop) + Frontend (`live_feed.js`: vertikale Chronologie, Aktiv-Block prominent, Codex-Polish: Braille-Spinner 80ms, animierte Dots, Shimmer-Gradient, `_just_finished`-Transition, STEPS_LIMIT=8, prefers-reduced-motion) im Control-Modus. **381k (8af1d99):** Resume-Aufgabe-Check in `phases/plan.py` (`_resume_erlaubt`-Flag, `phase_state.data['aufgabe'] != aufgabe` -> verwerfen). **Ad-hoc:** `_OPS_RE` erkennt OP-Suffixe a/b/c (f90e427, Loop-Crash bei OP-389b behoben), Explorer-Fallback-Grep bei leeren key_files (15ec8b9, verhindert `loop_explorer_leer` bei Backtick-Suchbegriffen), Fixture-Isolation fuer `test_ambient_gate_konsistenz.py` (4 Bindings). **Mode-Switch-Fundament:** OP-306a (85a29db, Cockpit/Control/Debug via Shift+Space + 1/2/3 + URL + localStorage + Dropdown + CSS-Grid-Varianten), OP-306 bleibt offen fuer Etappe 2-4. **Architect-Kontext-Verengung:** OP-385a (1ad363f, `scout_auftrag` als einzige Quelle, `explorer_findings`-Block in Fallback, Baseline-Prompt 100k user_len -> erwartet <60k), OP-385b (Scout-Prompt-Umbau: Auftrag als Hauptzweck) bleibt offen. Baseline: 1550 -> 1686 passed (+136), alle Commits mit Revert-Beweis oder Source-Scan-Test.

- 2026-11-09 | OP-392 | done | `loop.py` _full_cfg UnboundLocalError + Stash-Verlust bei Exception (Commit 9c29910). **Bug A:** `_full_cfg: dict = {}` vor try initialisiert (Zeile 493-508), sonst bei kaputter YAML (ValueError aus `_load_cfg`) UnboundLocalError. **Bug B:** `run_pipeline_loop` in `try/except BaseException/finally` eingewickelt; `_ps.save()` und `_git_stash_pop` laufen auch bei Exception (Datenrettung). `except BaseException` faengt `KeyboardInterrupt` mit (AK d), Propagation bleibt durch `raise`, `main()` emittiert `loop_failed` via existierendem `_emit_lifecycle_end` (bereits exception-safe). **Design:** `rc=1` safe-default, `_hat_exception` unterscheidet Fehlerpfad-Audits (`loop_rollback`/`loop_rollback_skipped`/`loop_stash_pop`) von Exception (kein Reset, aber pop). Reihenfolge reset→pop bleibt (alle 12 bestehenden Tests in `test_loop_main.py` gruen). **Spec-Tests:** 2 neu in `tests/test_loop_main.py`: (1) kaputte Config -> kein UnboundLocalError, `main()` laeuft durch; (2) `RuntimeError` in `run_pipeline_loop` -> `pop_calls == 1` (Datenrettung), Exception propagiert. **Regress-Barriere verifiziert (zwei Reverts):** Fix-A-Weg -> Test 1 rot mit exakt `UnboundLocalError` Zeile 508; Fix-B-Weg (pop im finally weg) -> Test 2 rot mit `AssertionError` (pop_calls leer). Baseline: 1589 -> 1591 passed, 5 skipped. ruff/mypy clean, alle 5 Drifts gruen. **Bewusst NICHT gemacht:** Reihenfolge reset→pop nicht umgestellt (Referenz-Tests binden sie explizit); kein `finally` um `_emit_lifecycle_end` (das ist bereits in `main()` aussen).

- 2026-11-09 | OP-391 | done | Files-/Diff-Endpoint respektieren den Projektnamen (Commit 0cb8ae0). `/diff`: `basis = _PROJECTS_BASE / _pruefe_projektname(name)` statt `Path("/opt/werkstatt")`; Rueckgabe von `_pruefe_projektname` wird jetzt abgefangen und verwendet (vorher verworfen). `/files`: analog, `_pruefe_projektname(name)` wird jetzt ueberhaupt aufgerufen (vorher gar nicht — Multi-Projekt war halb fertig seit OP-306c). **Spec-Tests:** `tests/test_files_projekt.py`, 4 Tests: (1) files fuer test-a zeigt nur test-a-Dateien (nicht test-b), (2) `?pfad=../test-b/x` bleibt 400 (Root-Check unveraendert), (3) unbekanntes Projekt -> 404, (4) diff ruft `subprocess.run` mit `cwd=<PROJECTS_BASE>/test-a`. Isolation: `_PROJECTS_BASE` via monkeypatch auf `tmp_path`, `subprocess.run` fuer /diff gemockt — Test haengt nicht vom Working Tree ab. **Regress-Barriere verifiziert:** bei Revert beider basis-Zeilen werden 3 von 4 Tests rot (files-beruecksichtigt, files-404, diff-cwd); `pfad_traversal_blockiert` bleibt gruen (Root-Check unveraendert). Baseline: 1585 -> 1589 passed, 5 skipped. ruff/mypy clean, alle 5 Drifts gruen. **Bewusst NICHT gemacht (nicht im Scope):** andere Endpoints mit hardcoded Pfaden pruefen — sie nutzen bereits `_PROJECTS_BASE` (Zeilen 335, 363, 525), sauber.

- 2026-11-09 | OP-390 | done | Git-Diff-Argument-Injection (ref ungeprueft) geschlossen (Commit f4952ff). Neues zentrales Modul `werkstatt/validierung.py` mit REF_MUSTER (Branch/Tag/SHA/HEAD~N/HEAD^/origin/main/refs/heads/x; verbietet fuehrendes '-', Leerzeichen, Shell-Metazeichen, >128 Zeichen) und pruefe_ref(). `app.py:/diff` ruft `_pruefe_ref(ref)` vor git-diff, HTTP-Adapter wandelt ValueError in HTTPException(400). `chat_tools._git_diff` ruft `pruefe_ref(ref)` vor subprocess, ValueError -> `return 'git_diff: ungueltiger ref ...'`. **Spec-Tests:** `tests/test_diff_ref_validation.py`, 22 Tests (8x gueltig-param, 7x ungueltig-param, 3x HTTP-Endpoint inkl. 400-Vor-Validierung, 2x chat-tools, 1x Meta, 1x Endpoint-200). **Regress-Barriere verifiziert:** bei Revert der chat_tools-Pruefung werden BEIDE chat-tools-Tests rot (output-option + leerer-ref) — staerker als OP-389 (dort nur 1 rot). **AK-Abweichungen (dokumentiert im Commit):** (a) REF_MUSTER zentral in `werkstatt/validierung.py` statt app.py, weil chat_tools.py (Kern) werkstatt/web/ nicht importieren darf (import_drift-Contract). (e) `--` steht NACH ref (`git diff {ref} --`), nicht davor — `git diff -- {ref}` interpretiert ref als Pathspec und haette den Endpoint funktional gebrochen (git diff -- HEAD = leer). **Bewusst NICHT gemacht (nicht im Scope):** andere subprocess.run-Aufrufe in app.py/chat_tools.py (Zeilen 63, 77, 125) auf unvalidierte Argumente pruefen — eigene OP-Kandidaten, nicht Teil von OP-390. Baseline: 1563 -> 1585 passed, 5 skipped. ruff/mypy clean, alle 5 Drifts gruen.

- 2026-11-09 | OP-389 | done | WebSocket-Auth-Bypass in /ws/{tab_id} geschlossen (Commit 8880d04). Neuer async-Helper `require_ws_auth(websocket)` in auth.py: prueft is_auth_disabled() oder is_authed_ws() vor accept(), schliesst mit Close 1008 wenn nicht autorisiert. ws.py:websocket_kanaele nutzt ihn. Damit 4 WS-Endpoints gegen Unauth geschuetzt (chat/stream, audit/stream, terminal_ws waren schon geschuetzt; /ws/{tab_id} war die Luecke). **Spec-Tests:** tests/test_ws_auth.py, 13 Tests: 4x unauth->1008-vor-accept (parametrisiert pro WS-Pfad), 4x mit-Cookie->akzeptiert, 4x _AUTH_DISABLED=True->akzeptiert, 1x Meta-Test (jede @websocket-Route muss in WS_ROUTEN_SOURCE eingetragen sein — faengt neue Endpoints ohne Auth-Test). **Regress-Barriere verifiziert:** bei Revert von ws.py wird genau test_unauth_ws_wird_abgelehnt_vor_accept[/ws/abc] rot; die 3 anderen Pfade bleiben gruen (Bestandsschutz vorhanden, Test deckt exakt die Luecke). Baseline: 1550 -> 1563 passed, 5 skipped. ruff/mypy clean, alle 5 Drifts gruen. **Folge-OP:** OP-389b — app.py, audit_panel.py, terminal_proxy.py auf denselben Helper migrieren (DRY, kein Verhaltenswechsel; bewusst in eigener Session wegen Regress-Risiko an funktionierenden Endpoints).

- 2026-11-08 | OP-373 | done | Backfill project-Spalte: 23.289 Werkstatt-Events von project='werkstatt' auf 'security-ai' korrigiert. Ausgefuehrt als manueller SQL-UPDATE mit event_id-IN-Liste (event_ids eindeutig aus JSONL-Zeilen mit project=security-ai abgeleitet, keine Kollisionsgefahr). project-Verteilung: werkstatt=387487, security-ai=23289, default=9. Idempotent (2. Lauf = 0 Aenderungen). **Ehrlich offen (in OP-374):** (a) Kein reproduzierbarer Code (nur manuelles SQL); (b) `_letzter_run_id` filtert nicht auf `run_id != ''` — security-ai zeigt leere run_id als 'letzter Run'; (c) 18.165 security-ai Events (18.10.-02.11.) ohne run_id durch Loop-Bug vor OP-303; (d) `ops_run_status` findet 0 security-ai-OPs weil pre-OP-303 `op_id` fehlt (ehrliche Luecke). pytest 1538 passed.

- 2026-11-08 | OP-371 | done | Ambient-Loop-Status: neuestes Terminal-Event entscheidet (loop_erfolg|loop_failed|loop_ended). Vorher 3-stufige Kaskade mit loop_erfolg zuerst -> ein spaeteres loop_failed wurde ignoriert. Live 2026-11-08 22:10: ambient('werkstatt') zeigte 'done' (loop_erfolg 01:26), obwohl um 19:41 loop_failed das letzte Terminal-Event war. Fix: 1 Query mit IN-Klausel + ORDER BY seq DESC LIMIT 1, kind des Neuesten entscheidet. 2 neue Tests (Konflikt-Reihenfolge in beide Richtungen). pytest 1538 passed.

- 2026-11-08 | OP-306c-Fix | done | Projector-Deadlock behoben (Commit a640b19). Sentinel-Checkpoint MIGRATED-SEM-352017 (aus OP-323-Migration) stand in der alphabetisch letzten agent-pipeline-migrated-2026-11-08.jsonl Zeile 33/33 — _read_events() fand ihn nie in den echten Tagesdateien, uebersprang stumm alle Events, Checkpoint blieb Sentinel. Folge: SQLite stand seit 15:14 still, JSONL hatte 31 echte Events nach 15:14 (u.a. loop_started 17:57 OP-280, loop_failed 19:41). Fix: _jsonl_files() excludet *-migrated-*.jsonl (statische DB-Dumps); _read_events() wirft ValueError bei unbekanntem Checkpoint statt stumm 0. 3 neue Tests. Daten-Reset: Checkpoint auf PIPE-20261108-151341-a8a36a -> tail() las 31 Events ein (2 wegen event_id-Kollision uebersprungen, harmlos). tail#2 idempotent. Checkpoint landet auf PIPE-20261108-194159-bd35bf. COUNT 410754 -> 410785, MAX(seq) 788707 -> 788736. pytest 1536 passed.

- 2026-11-08 | OP-306c | done | Multi-Projekt-Datenquellen (SQLite project-Spalte). Commits 71cc471 (Etappe 1 Schema), 60a0f92 (Etappe 2 Writer), 0ce6852 (Etappe 3a Reader SQL), 62a6cdd (Etappe 3b Reader ambient+timeline). Migration: ALTER TABLE events ADD COLUMN project TEXT NOT NULL DEFAULT 'werkstatt', 410754 historische Zeilen bekommen 'werkstatt' (ehrlich: alle bisherigen Events stammen aus Werkstatt). Index idx_events_project_seq. Projector._insert reicht project aus JSONL in Spalte (single source of truth, aus payload entfernt). _letzter_run_id(es, projekt='werkstatt') zentral + 4 aggregate_*-Funktionen (status, tokens, ops_run_status, ambient) + aggregate_timeline-JSONL-Filter filtern AND project=?. **AK-Anpassungen:** (c) audit()/stream() schrieben project schon vor OP-306c ins JSONL — war bereits erfuellt. (f) Frontend-URLs waren schon /api/projects/{name}/... — war bereits erfuellt. Tests: 10 statt 8 (6 in Etappe 3a, 4 in Etappe 3b), Test-Datei tests/test_multi_projekt_daten.py. Live: test16=idle/0, werkstatt=done/0. pytest 1533 passed.

- 2026-11-08 | OP-306a | done | Tab-Persistenz via localStorage. Commit f5d333a. 10 Verhaltens-Tests + 4 Drift-Guards (Spec-First nach ADR-0015/0016), Klammer-Balance als node--check-Ersatz. Key `werkstatt-tabs:v1` statt AK-`werkstatt_tabs` — Schema-Versionierung, User-bestaetigt 2026-11-08. Test-Datei `tests/test_ui_tab_persistenz.py` statt AK-`tests/test_tabs_persist.py`, 14 statt 4 Tests. AK-Punkt (f) als Lesart A interpretiert (leerer Storage -> Default-Tab `werkstatt`); Overview-Screen als Startansicht ist OP-306b (Workspace-Overview-Shell). pytest 1521 passed.

- 2026-11-08 | OP-323 | done | Wiring. SQLite-Write aus _publish entfernt (JSONL einzige Quelle). Flush-Hook in audit.py (nach 100 Events Projector.tail). Endpoint /api/projects/{name}/projection/status. Statusleiste zeigt Proj-OK / Proj-Warnung bei Divergenz. .gitignore um stream-*.jsonl. **Bugfix:** audit_id mit UUID-Suffix (Kollision bei schnellen Calls behoben), event_id-Fallback mit file+line. 4 neue Tests. pytest 1452 passed.
- 2026-11-08 | OP-322 | done | Projector (rebuild/tail/status). JSONL -> SQLite idempotent (event_id UNIQUE, INSERT OR IGNORE), Checkpoint in projection_state, rebuild() deterministisch (Doppel-Rebuild ergibt identischen Hash). 6 neue Tests. pytest 1448 passed.
- 2026-11-08 | OP-321 | done | JSONL-Trennung stream/semantic. _STREAM_KINDS (log_line/progress/spinner/heartbeat/task_started/task_done), stream() schreibt nach stream-YYYY-MM-DD.jsonl, audit() nach agent-pipeline, fail-closed fuer unbekannte Kinds. event_id = sha256(run_id|audit_id)[:16] in beiden. _publish schreibt jetzt zusaetzlich JSONL (SQLite bleibt bis OP-323). 5 neue Tests. pytest 1442 passed.
- 2026-11-08 | OP-320 | done | ADR-0024 Tiered Event Log + Projector. Deklariert Semantic-Stream (git) + Stream-Stream (gitignore), SQLite rebuildbar, audit()/stream() als einzige Writer, EventStore.append() verbannt. Grundlage fuer OP-321..323.
- 2026-11-08 | OP-319 | done | Event-Architektur-Messung. 32804 JSONL-Events (320 Kinds, 267 Runs) vs. 374353 SQLite-Events (10 Kinds, 5290 Runs). Schnittmenge: 0 Kinds, 25 Runs. Beweis fuer Dual-Write-Anti-Pattern (Confluent/Microsoft-CQRS/AutoMQ). Grundlage fuer OP-320..323.
- 2026-11-08 | OP-304 | done | Shortcut-Help-Overlay (?-Taste). shortcut_help.js, 3 Kategorien (Navigation/Chat/Palette), kbd-Boxen. 6 Tests. pytest 1497 passed.
- 2026-11-08 | OP-305 | done | Utility-Bar + Klickwege + Projekt-Anlage. utility_bar.js (⌘K/?-Buttons), Alt+N-Shortcut (Chrome-Konflikt behoben), project_create.js mit Modal + POST /api/projects/create + multi-projekt-Sicherheit (_PROJECTS_BASE-Konstante, /start validiert docs/STATUS.md, /ops + Palette projekt-spezifisch). Ambient-Projektname prominent. **Lehren:** (a) Python-Docstring """...""" in JS = SyntaxError, Node-fehlt-Guard zu streng. (b) if(false)-Block mit Kommentar schluckte function-Definition, Bracket-Matcher half. (c) Clone-von-tab-neu brach insertBefore-Referenz, dynamischer Lookup noetig. (d) Test-Fixture-Falle: Path("/opt") in Produktion muss via _PROJECTS_BASE-Konstante testbar sein. (e) Auth-Disable ist _AUTH_DISABLED, nicht _AUTH_DISABLED_OVERRIDE. 19 Tests (4 Help + 5 Utility + 11 Project-Create + Multi-Projekt). pytest 1515 passed.
- 2026-11-08 | OP-302 | done | Command Palette (Ctrl+K). Backend aggregate_palette() + /palette-Endpoint, Server-Filter. Frontend palette.js mit Overlay (blur), 4 Kategorien (AKTION/NAVIGATION/OP/SESSION/RUN), Icons ▸ → ⚙ ◆ ↻, Keyboard-Nav (↑↓ Enter Esc), Klick-Ausfuehrung, Race-Schutz via _letzterQuery. **Bekannter Datenfehler:** OP-221 zeigt „blockiert von: OP-221" (Selbstverweis) — vermutlich Tippfehler in STATUS.md, sollte OP-220a sein. Eigene OP fuer Doku-Aufraeumen. 10 Tests (4 Backend + 6 Frontend-Smoke). pytest 1497 passed.
- 2026-11-08 | OP-301 | done | Ambient Status Bar. Drei Elemente zwischen Tab-Leiste und Grid: Loop-Status (○ Idle / ◉ Läuft / ● Fertig / ✗ Fehler — ● statt ✓ verhindert Kollision mit Run-✓), letzter Run (relativ mit ✓/✗), Gates (hidden bei 0, pulsierend bei >0). Polling 3s. Klick Timeline / Gate-Panel. **Option A Redundanz-Fix:** Tokens und Phase raus (Diagnose, Statusbar). Ambient = Handlungsampel, Statusbar = Diagnose mit Icons ↻ Loop / ◆ Chat. **Backend:** aggregate_ambient() + /ambient, loop_erfolg-Semantik-Fix (Event-Name impliziert Erfolg, payload hat kein erfolg/success). Fallback: loop_erfolg > loop_ended > loop_failed > idle. **Naming:** Chat bleibt Chat (kein Assistent-Synonym; Cursor/Claude-Code-Vorbild: zwei Begriffe für zwei Dinge). 13 Tests (6 Backend + 7 Frontend-Smoke inkl. Icon-Kollisions-Test). pytest 1467 passed.
- 2026-11-08 | OP-300 | done | Semantic Colors System (Commit `320b029`). 6 semantische CSS-Variablen (`--sem-action`, `--sem-active`, `--sem-ok`, `--sem-warn`, `--sem-error`, `--sem-history`) + 7 Shades + 4 Struct-Variablen im `:root`. 57 Hex-Vorkommen ausserhalb `:root` ersetzt. Explorer-Cyan `#06b6d4` -> `var(--sem-active)` (bewusster Farbwechsel, Frage 1a). `.diff-hunk` -> `var(--sem-active)` (Frage 3: Diff im laufenden Build ist Ist-Zustand, nicht Vergangenheit). chat.css hatte schon 0 Hex, unveraendert. Guard: Hex ausserhalb `:root` == 0. pytest 1437 passed, ruff/mypy 0, alle 5 Drifts 0. **Lehre:** Erster Patch-Versuch zerstoerte `:root`-Block durch fehlerhaftes Reassembly (`s = body` statt `s = head + neuer_root + tail`); In-Python-Guard SEM==0 hat Commit verhindert, Rollback manuell. Zweiter Versuch mit Guards vor `write_text` erfolgreich. **Strukturelle Altlast:** zwischen `## Erledigt (Auto-Log)` und `## Delete-Zone` stehen 16 offene OPs (OP-263, OP-257, ..., OP-241) faelschlich unter Auto-Log.

- 2026-11-07 | OP-181 | done | Reviewer-Dead-Code-Erkennung (Commits `9b700e3` t1, `fdb01df` t3+t4). Loop-Lauf 13:23 baute t1 (REVIEWER_SYSTEM-`DEAD-CODE-CHECK`-Abschnitt mit 3 Regeln), brach dann bei t2 ab (Planner-Fehler: Verifikations-Task als update formuliert, Builder setzte `auftrag_bereits_erfuellt`, Reviewer meldete HIGH-Bug). OP-182-Fix begrenzte den Loop auf 2 Reflection-Runden, aber t3+t4 blieben offen. Manueller Nachzug: t3 = `run_reviewer` ruft `_pruefe_neue_module_genutzt(pd, diff)` nach den LLM-Filtern und vor `reviewer_result`-Audit; HIGH-Bug setzt `approved=False`. t4 = `tests/test_reviewer_dead_code.py` mit 3 AK-(c)-Tests + AST-Wiring-Test (`test_run_reviewer_ruft_pre_check_auf`, analog `test_rollen_registry_migration.py`) — kodiert die Lehre aus Loop-Test 9, dass die Funktion sonst toter Code werden kann. pytest 1342 passed, ruff/mypy 0, alle Drift-Checks gruen. **Lehre (Loop-Test 10, eingeplant als OP):** Planner-Task-Typ „pruefe/verifiziere X" braucht eigenes `action: verify`, sonst falscher Builder-Pfad. Siehe Stufe-2-Planung.
- 2026-11-07 | OP-183 | done | Planner-Task-Typ `action: verify` (Commits `c3e308f` t1-t3 + 3 Tests, `f9243a8` Test (iv)). Loop-Lauf 15:24 hat t1 (Planner `_ist_verify_task` + `PLANNER_SPLIT_SYSTEM` vierter Action-Wert + `_korrigiere_aktion`-Vorspann), t2 (`phases/tasks.py` verify-Dispatch ohne Builder), t3 (`reviewer.py` `_filter_auftrag_treue_false_positives` `action`-Parameter + System-Prompt VERIFY-TASK-Block) gebaut. t4 (Tests) hatte 3/4 gruen, Test (iv) `test_verify_setzt_kein_auftrag_bereits_erfuellt` fehlte — manuell nachgezogen als deterministischer Text-Scan-Test. pytest 1364 passed. **Lehre:** Loop-Reflection kann bei Test-Tasks mit >3 Tests die letzte Assertion verlieren, wenn der Builder die gesamte Test-Datei zu gross plant. **Nachtrag 2026-11-07:** Delete-Zone-Eintrag fehlte, pytest-Fail `test_status_md_konsistenz` entdeckt und hier nachgetragen.
- 2026-11-07 | OP-182 | done | verify_alternierend als Stagnations-Grund (Commit `4de3a65`). Loop-Test 9 (5 Runden statt 2): alternierende Verify-Fehler (PIE810 / mypy Duplicate / beide) haben `_verify_fehler_zwischen_runden_gleich` (Stage-Set exakt, OP-175 Bug B) nie gematcht, Counter sprang 1->0->1. Fix: neuer Grund `verify_alternierend` in `_reflection_loop` via `_verify_fehler_alternierend` (Signatur-Set-Intersection ueber `_fehler_signatur_normalisiert`, nicht-leer und nicht-identisch). Option Y: `_is_spec` wird bei diesem Grund uebersprungen -> normaler Task-Fail statt `spec_widerspruch_erschoepft`. 5 Unit-Tests + 1 Integration-Test (`test_reflection_alternierende_fehler_stagniert`). Konsequenz: 3 Builder-Aufrufe statt 5 in Loop-Test-9-Szenario.
- 2026-11-07 | OP-173 | superseded | Duplikat zu OP-174. Beide OPs haben identischen Titel "Spec-Tests — RunState-Factory statt SimpleNamespace". OP-174 bleibt als einzige Version offen. Kein Code geaendert, kein Test.
- 2026-11-07 | OP-201 | done | pyproject.toml Paket-Registrierung + test-tools (Commit `a1eee3b`). Loop-Lauf 19:46-19:56 baute 6/6 Tasks, Phase-Review rejected wegen 3 roter Tests, Human-Gate `n` + manuelle Nachziehung. `[project]` mit name=werkstatt, version=0.1.0, `[project.optional-dependencies].test-tools = [hypothesis>=6.100, pytest-gremlins>=1.13.2]`, `[tool.setuptools.packages.find]`, `[tool.pytest-gremlins]`. `[tool.importlinter]` + `[tool.ruff.lint]` byte-identisch. 2 neue Test-Dateien (`test_package_registrierung.py`, `test_config_integritaet.py`). Manuelle Nachträge: `pytest.ini` um testpaths/python_files, requirements.txt Kommentarzeilen mit Markern, `tools/quality_gate.py`-Guard vom Import in `main()` verschoben (behebt `--collect-only`-INTERNALERROR). `pip install -e ".[test-tools]"` grün, `pip show werkstatt` zeigt Version 0.1.0, pytest 1384 passed. Entblockt OP-214 (Mutation-Gate) und OP-215 (Hypothesis).
- 2026-11-07 | OP-174 | re-numbered | -> OP-294 (Backlog). Grund: Umnummerierung nach Phasen-Reihenfolge. Der PROGRESS.md-Header "OP-174: Spec-Tests" stammt aus der Zeit vor der Umnummerierung und bleibt als Historie. OP-294 ist der aktive OP.
- 2026-11-07 | OP-187 | done | Planner-Dependency-Hybrid (Commit `e960a40`, Doku `91102a7`). Architect-Aussagen in Block 5 sind ab jetzt verbindlich: `_leite_deps_deterministisch` wertet Architect-Dependencies aus (Multi-File), Heuristik nur als Ergaenzung fuer Tasks ohne Architect-Aussage. Explizites `- (keine)` im Architect-Block stoppt Heuristik. Fallback-Pfad ruft Deps + Topo-Sort ebenfalls. 10 Unit-Tests in `test_planner_deps_hybrid.py`. **Nachtrag 2026-11-07:** DZ-Eintrag fehlte beim Close-Commit `91102a7`, hier nachgetragen.
- 2026-11-07 | OP-176 | done | contract_check-Haertung gegen `setattr(state, "<unbekannt>", ...)` (Commit `7eab26d`, Loop-Test 8, 11:50-11:58). AST-Walk findet setattr-Aufrufe auf RunState-Felder, die nicht in `RunState.__dataclass_fields__` sind. Wiring ueber `state_inventory.py --changed` (verify.json contract_check-Stage). 3 Unit-Tests (test_contract_check_setattr.py) + 2 Integration-Tests (test_verify_contract_stage.py erweitert). Fail-closed mit rc=1 bei unbekanntem Feld, rc=0 bei deklariertem. Bug-D aus OP-175 (Loop-Test 6, Agent-Patch mit `setattr(state, "phase_review_gate_auto", True)`) ist jetzt deterministisch gefangen — vorher fing nur ruff B010 den Umgehungs-Versuch. Die zwei Integration-Tests verifizieren das Ende-zu-Ende-Wiring (Subprocess `python3 tools/state_inventory.py --changed <file>`).
- 2026-11-07 | OP-180 | wontfix | Reviewer-Praezision (Konfidenz-Feld + Pre-Check): falsche Problem-Annahme. Loop-Test 7 hatte keinen Reviewer-Bug, sondern OP-179 (mypy Duplicate-Module) — die 3 HIGH reviewer_phase_rejected-Bugs waren ALLE berechtigt (t3/t4/t5 wurden wegen OP-179 nicht gebaut). Konfidenz-Feld und Pre-Check basieren auf "Reviewer meldet falsche Bugs" — das war nie wahr. Kein Code angelegt, kein Test, wird nicht gebraucht.
- 2026-11-07 | OP-179 | wontfix | mypy-Setup "Duplicate-Module": **falsche Problem-Annahme**. Ich habe den truncated mypy-Output aus Loop-Test 7 (`(also at "werkstatt/phases/review.py")`) als "Source file found twice" interpretiert — das war eine Fehldeutung des OP-172-Truncation-Artefakts. Reproduktion (Block 33, 2026-11-07): alle vier mypy-Varianten rc=0 auf aktuellem Code-State, kein Duplicate-Module-Fehler, kein Top-Level-`phases/`-Konflikt, `__init__.py` ueberall da. Wahre Loop-Test-7-Ursache fuer t3/t4-Fails: der Loop baute zuerst t2 (`review.py`, setzt `state.phase_review_gate_auto`), aber t1 (`state.py`, deklariert das Feld) war noch nicht gebaut — Planner erkannte Cross-Task-Feldabhaengigkeit nicht. **Bereits behoben** durch OP-168b (c713033): Feld ist jetzt in RunState deklariert, Loop-Test 8 findet es. Kein Code angelegt, kein Test.
- 2026-11-07 | OP-177 | wontfix | Reviewer-Kontext-Vertrag: falsche Problem-Annahme. _phase_files (alle Task-Dateien der Phase) liefert vollstaendigen Diff — bestaetigt durch Messblock 31. Die 3 HIGH-Bugs aus Loop-Test 7 waren berechtigt, weil t3/t4/t5 tatsaechlich nicht gebaut wurden (OP-179). Der Reviewer-Selbst-Hinweis "nur der Anfang von _phase_end_reflection ist sichtbar" war praezise Diagnose ("Patch fehlt im sichtbaren Kontext"), nicht Truncation-Beschwerde. Kein Code angelegt, kein Test. Ursache fuer "3 von 4 Tasks nicht gebaut" ist OP-179 (mypy Setup) + OP-172 (Verify-Truncation, heute gefixt).
- 2026-11-07 | OP-172 | done | Fehlerkern-Extraktion in verify.py (`_extrahiere_fehlerkern`) statt `_out[-500:]` (8effad1). mypy-Fehler-Output wird auf `error:`-Zeilen + Kontext reduziert, `note:`/`help:`/Statistik verworfen. Live-Beleg Loop-Test 7 (18:29:11): der alte Truncation-Pfad schnitt den error-Kopf ab, sodass der Builder nur "(also at ...)" + Notes sah. Jetzt sieht er "error: Source file found twice under different module names: \"werkstatt.phases.review\" and \"phases.review\"" — das Setup-Problem ist damit **diagnostizierbar**, aber nicht behebbar (eigene OP-179). 9 neue Tests (test_verify_fehlerkern.py).
- 2026-11-07 | OP-178 | done | Rollen-Registry-Migration: planner/builder/reviewer/reflection via ROLLEN[name].lade_skills() (0388d1b), Alias-Cleanup (8954f83), Explorer-Migration + systematic-debugging-Rausnahme (5a5c941). 5 von 5 Aufrufern migriert, scout bleibt fail-closed-leer. Neuer Migration-Test test_rollen_registry_migration.py (AST-Scan: jede Rolle mit skills/filter_rolle muss ROLLEN[name] nutzen). Verhaltensaenderung Explorer: systematic-debugging wird nicht mehr geladen (auch nicht bei Trigger); SKILL.md-Frontmatter `rollen: [builder]`. systematic-debugging-Zuordnung zum geplanten Debugger (OP-128/OP-160) dort offen, keine eigene OP.
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

### OP-160: Verifizierte Debugger-Fixes ins Erfahrungs-Gedaechtnis ueberfuehren

- **Status:** open
- **Typ:** architektur (Debugger und projektuebergreifendes Memory)
- **Phase:** Phase-3; Umsetzung erst nach Abschluss von OP-382
- **Betroffene Dateien:** `werkstatt/chat_agent.py`, `werkstatt/chat_tools.py`, `werkstatt/erfahrung.py`, `werkstatt/reflection.py`, Event-Schema und zugehoerige Tests
- **Problem:** Der fruehere Entwurf koppelt die Arbeit an OP-128 und OP-113/129. OP-128 wurde durch die akzeptierte Chat-Debugger-Architektur in OP-240 ersetzt; OP-113a und OP-129 sind nicht mehr offene STATUS-OPs. Der Lernpfad muss an das aktuelle projektlokale und globale Memory aus OP-220/220a/221 anschliessen.

- **Vertrauensgrenze:** Ein Diagnosevorschlag oder angezeigter Diff ist keine Erfahrung. Ein Fix darf erst nach einmaliger Freigabe des konkreten Patch-Hashes an den Coding-Loop und nach erfolgreichem Plan-Gate, Verify und Review als verifizierte Episode gespeichert werden. Bei fehlgeschlagener Verifikation entsteht kein erfolgreicher Memory-Eintrag. Die bestehenden Human-Gates bleiben verbindlich.

- **Datenstrom:**
  1. Fehlgeschlagener Run wird im Chat mit Projekt- und Run-Kontext diagnostiziert.
  2. Der Mensch waehlt den Debugger-Modus; der Chat erstellt einen strukturierten Fix mit betroffenen Dateien und Diff.
  3. Der Mensch gibt genau diesen Patch-Hash frei; der Coding-Loop uebernimmt den Patch ohne Copy/Paste und durchlaeuft seine verpflichtenden Gates.
  4. Erst nach erfolgreichem Verify und Review wird ein provenance-behaftetes `debugger_fix_verifiziert`-Event fuer die Projekt-Memory-Episode erzeugt.
  5. Fehlgeschlagene oder abgelehnte Aenderungen werden nicht als erfolgreiche Fix-Erfahrung gespeichert.

- **Memory-Regeln:** Schema, `scope`, Provenance und Trust-Stufen folgen ADR-0010 sowie OP-220/220a/221. Keine automatische Promotion ins globale Memory. Retrieval und Prompt-Injektion bleiben bis zum erfolgreichen Abschluss der Dogfooding-Phase ausgeschaltet; danach nur passend zum Fehlerkontext, mit Herkunftsnachweis und ohne Injektion in Scout, Architect oder Reviewer.

- **Akzeptanzkriterien:**
  - (a) Das Event ist an Projekt, Run, Patch-Hash, betroffene Dateien, Verify-/Review-Beleg und Herkunft gebunden.
  - (b) Gruener Verify- und Review-Abschluss erzeugt genau eine idempotente Episode; roter Verify, Reject oder abgelaufene Freigabe erzeugt keine erfolgreiche Episode.
  - (c) Projekt- und globale Memory-Grenzen sowie Provenance aus ADR-0010 werden eingehalten; Promotion benoetigt einen getrennten expliziten Vorgang.
  - (d) Es gibt keinen Memory-Retrieval-Pfad vor Abschluss von OP-382. Danach decken Tests erlaubte kontextbezogene Retrievals und ausgeschlossene Rollen ab.
  - (e) Tests decken Patch-Hash-Bindung, Wiederholung/Idempotenz, erfolgreiche und fehlgeschlagene Verifikation sowie Projektisolation ab.

- **Tests:** `tests/test_debugger_memory_hook.py`, `tests/test_reflection_memory_inject.py`
- **Blockiert von:** OP-240, OP-220, OP-220a, OP-221, OP-382
- **Quelle:** ADR-0010, ADR-0011, ADR-0029


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

### OP-113i: Audit-Log-Backfill — geeignete Problem-Events ins Erfahrungs-Memory

- **Status:** open
- **Typ:** erfahrung-backfill
- **Phase:** Phase-3; Umsetzung erst nach Abschluss von OP-382
- **Betroffene Dateien:** `tools/backfill_erfahrung.py` (neu), projektlokale Memory-Datenbank aus OP-220
- **Erkenntnis (2026-11-03 23:55):** Die damalige Inventur fand 1.253 Problem-Events in `audit-logs/*.jsonl`; nur ungefaehr 650 sind anhand ihrer Payloads belastbar clusterfaehig. Backfill darf nur Events mit ausreichender strukturierter Provenance und reproduzierbarer Signatur uebernehmen. Reviewer-, Gate- und Plan-Rejects ohne beschreibende Fehlerfelder sind keine geeignete Trainings-/Memory-Grundlage.

- **Akzeptanzkriterien:**
  - Das Werkzeug liest die dokumentierten Event-Dateien read-only und clustert nur die belegten Klassen `loop_verify_failed`, `builder_patch_invalid`, `loop_task_failed` und `loop_reflection_stagnation_abort`.
  - Loesungskontext wird nur bei einem korrelierten erfolgreichen Folge-Event innerhalb des dokumentierten Zeitfensters eingetragen; andernfalls bleibt die Episode als unverifiziert markiert.
  - Herkunft, Projekt, Run-ID, Signatur und Erfolg/Verifikation werden gemass ADR-0010 gespeichert; andere Projekte und globale Memory werden nicht veraendert.
  - Wiederholte Ausfuehrung ist idempotent; Dry-Run zeigt Anzahl und Beispiele vor jedem Schreibvorgang.
  - Tests decken jede Signaturklasse, fehlenden Loesungskontext, Projektisolation und Idempotenz ab.

- **Tests:** `tests/test_backfill_erfahrung.py` (neu)
- **Blockiert von:** OP-220a, OP-382
- **Quelle:** ADR-0010


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