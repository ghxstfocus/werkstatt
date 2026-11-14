# Architektur — Werkstatt


> Diese Datei beschreibt die implementierte Architektur und verweist fuer
> geplante Arbeit auf docs/ROADMAP.md. Verbindliche Architekturregeln
> stehen in akzeptierten ADRs; vorgeschlagene ADRs sind nicht bindend.
>
> Statusqueue: docs/STATUS.md · Abschlussverlauf: PROGRESS.md


Stand: 2026-11-14.


## 1. Produktarchitektur


Werkstatt verbindet projektbezogenen Chat, kontrollierte Loop-Runs,
spezialisierte Agentenrollen und deterministische Verify-Stufen. Der Chat
ist die zentrale Oberflaeche fuer Fragen und Auftraege. Er kann lesend im
Repository untersuchen, Hintergrundjobs begleiten und nach konkreter
Freigabe Loop-Steuerungsaktionen ausloesen.


Ein Chat-Vorschlag ist keine Gate-Freigabe. Der Loop verlangt weiterhin
das verpflichtende Plan-Gate und das abschliessende Review-/Ergebnis-Gate.
Eine waehrend eines Runs angeforderte Plan-Aenderung muss als eigener
Vorschlag am sicheren Checkpoint erneut freigegeben werden. Sie veraendert
keinen aktiven Plan still.


Die Agentenrollen werden durch den Loop orchestriert. Lesende Chatfragen
koennen parallel dazu beantwortet werden; schreibende Arbeit benoetigt
einen kontrollierten Projekt-Schreibpfad. Eine getrennte Debugger-Loop-Rolle
gibt es nicht: Debugging ist eine Chat-Faehigkeit (ADR-0011/0029).


### UI-Modi


- **Cockpit:** Zusammenfassung des Laufs und langsamere, nachtraegliche
  Timeline-Einordnung.
- **Control:** Live-Feed und aktuelle Loop-Steuerung; das Chatpanel bleibt
  als zentraler Projektkontakt erreichbar.
- **Debug:** Diagnose, Run-Kontext und Fehlerbehebung.
- **Runs:** Projektlaeufe und deren Status.


Die verbindliche UI-Hierarchie, Modussemantik und Abgrenzung der
Ansichten steht in ADR-0022 und im freigegebenen UI-Plan. ADR-0022a ist
abgeloest und keine gueltige Bauvorgabe.

## 1.5 Ausfuehrung

Der produktive Run-Kern ist weiterhin die bestehende lineare Folge aus
Setup/Explorer, Plan/Preflight, Task-Loop und Finalizer. Der Finalizer hat
einen Failure-Record-Recoverypfad fuer das Phase-End-Verify. Nach einem
erfolgreichen Commit wird die vollstaendige Phase-End-Verify erneut
ausgefuehrt; HEAD und Working Tree werden danach gegen den geprueften Commit
validiert. Ein roter oder veraenderter Stand kann keinen Run-Erfolg ausloesen.
Der persistierte Zielkoordinator, die Inbox fuer Folgeauftraege und ein
gemeinsames Evidence Ledger aus ADR-0032 sind noch nicht implementiert.

Entwicklungs- und Verify-Befehle laufen aus dem Repository-Root und der
projektspezifischen Umgebung. Die verbindlichen Abhaengigkeiten und
Verify-Stages stehen in pyproject.toml, requirements.txt und
.werkstatt/verify.json. Test-Loop und Mutation-Gate sind nicht Teil des
aktiven Produktionspfads, solange die zugehoerigen ADRs nicht angenommen
und in der Roadmap aktiviert sind.

### 1.6 GitHub-Quellen und Run-Worktrees (ADR-0030)

Bei einem GitHub-verbundenen Projekt prueft der Server vor dem Start
den lokalen Git-Status und den konfigurierten origin-Upstream. Er fetcht den
Branch in eine eigene Remote-Tracking-Referenz, pinnt dessen Commit-SHA und
stoppt bei Statusfehlern, lokalen Aenderungen, Fetch-Fehlern sowie
ahead/divergent Branches. Der bestehende Checkout wird nicht aktualisiert
oder verworfen. Der Loop startet in einem eigenen Run-Branch und Worktree
auf der gefetchten SHA. Worktrees liegen ausserhalb des Projekt-Checkouts
im Werkstatt-State (konfigurierbar ueber
`WERKSTATT_RUN_WORKTREE_DIR`, sonst unter
`$XDG_STATE_HOME/werkstatt/run-worktrees` bzw.
`~/.local/state/werkstatt/run-worktrees`). Der API-Response nennt
Repository, Remote-Branch, Basis-SHA, gepinnte SHA und Run-Branch.

Projekte ohne GitHub-origin laufen weiter im konfigurierten Serverpfad.
Remote-Push und Merge bleiben getrennte, freizugebende Aktionen. Die
Integration von Ergebnis-Gates und Remote-Schreibaktionen ist weiterhin
offene Arbeit in OP-399. ADR-0030 ist angenommen; dessen Annahme bedeutet
nicht, dass alle OP-399-Akzeptanzkriterien bereits umgesetzt sind.

## 2. Rollen

### 2.1 Explorer (werkstatt/explorer.py)

Read-only Agent. Sammelt Projektkontext und key_files; die Pruefungen
selbst bleiben deterministisch. Modell: deepseek-flash, Thinking aus.
Der Planner kann den Scout bei einem einzelnen, expliziten und im
Projekt belegten Dateiziel ueberspringen; der Explorer liefert weiterhin den
Projektkontext.

### 2.2 Architect (werkstatt/planner.py, Prosa-Modus)

deepseek-v4-pro mit Thinking/high. Keine Skills, keine Tools (M-446).
Produziert Prosa mit nummerierten Schritten. Max 16000 Tokens.

### 2.3 Planner-Split (werkstatt/planner.py, JSON-Modus)

deepseek-flash mit Thinking aus. Zerlegt die Architect-Prosa in Tasks mit
architect_start/architect_ende (woertliche Marker, M-461).
Rekursiv, max 2 Ebenen (M-469/M-470/M-471).

### 2.4 Builder (werkstatt/roles/builder/run.py)

deepseek-flash mit Thinking aus. search/replace pro Task. Bekommt den woertlichen
Architect-Abschnitt (M-461). _architect_abschnitt gibt leeren
String zurueck, wenn die Datei nicht in der Prosa ist (M-450).

### 2.5 PreToolUse-Hook (hooks/pre_tool_use.py)

AST-basierte Import-Validierung (M-334a). Blockt erfundene
Imports deterministisch.

### 2.6 Verify (_verify_patches in loop.py)

verify.json-Stages: py_compile_changed, ruff_changed, pytest_changed,
py_compile_core, pytest_full_checks (phase_end, M-476).

### 2.7 Reviewer (werkstatt/reviewer.py)

deepseek-flash mit Thinking aus. Prueft die Task-Description, nicht die Gesamtaufgabe
(M-459). Bekommt den vollen Diff (M-448).

### 2.8 Scout, Reflection, Chat und Debugger


Scout und Reflection unterstuetzen den schreibenden Loop. Der projektbezogene
Chat arbeitet parallel fuer Fragen, Repo-Analyse und bestaetigungspflichtige
Kontrollaktionen. Der Debugger ist ein Chat-Modus mit evidenzgebundener
Diagnose und Patch-Handoff an den normalen Loop. Chat-Freigabe, Plan-Gate,
Verify, Review und Ergebnis-Gate bleiben getrennte Schritte.

### 2.9 Human-Gates (_human_gate in loop.py)

Plan-Gate (nach Planner) + Ergebnis-Gate (nach Reviewer). fail-closed.

## 3. Plan- und Task-Zerlegung

Der Planner waehlt Scout- und Architect-Aufrufe nach Auftrag und aktueller
Dateievidenz. Breite, mehrdeutige oder belegbeduerftige Auftraege laufen
ueber den Scout. Ein einzelnes explizites Dateiziel kann den Scout nur
ueberspringen, wenn Explorer und Pfadpruefung es bestaetigen. Ein
deterministischer Architect-Bypass ist auf belegte, eindeutige
Einzeldatei-Ersetzungen mit vollstaendigen Feldern begrenzt; veraltete,
mehrdeutige oder unvollstaendige Treffer fallen in den Reasoning-Pfad
zurueck. Diese Entscheidungen werden auditiert.

Wenn der Scout-Pfad aktiv ist, bekommt der Architect einen begrenzten
AST-Signaturauszug fuer die benannten Zieldateien. Angeforderte Scout-Symbole
werden mit dem aktuellen Code-Index verglichen; bei Widerspruch gilt die
verifizierte Code-Signatur und der Befund wird dem Architect gezeigt.
Windows- und POSIX-Pfade werden fuer diesen Abgleich normalisiert. Dieser
Belegpfad verbessert die Scout-zu-Architect-Uebergabe, aendert aber nicht die
adaptive Scout-Auswahl.

Im normalen Reasoning-Pfad strukturiert der Architect den Auftrag; der
Planner-Split ueberfuehrt den Plan in Tasks und Abhaengigkeiten, die
topologisch sortiert ausgefuehrt werden. Tasks durchlaufen Builder, Verify
und Reviewer; fehlgeschlagene Befunde gehen in den begrenzten
Reflection-/Reparaturpfad. Ein Fehlschlag erweitert den freigegebenen
Auftrag nicht still. Der verpflichtende Plan- und Ergebnis-Gate-Pfad bleibt
davon unberuehrt.

Der alte ADaPT-On-Demand-Split wurde am 2026-11-08 entfernt: historische
Runs belegten seltene Nutzung und fehlende Auditierbarkeit. Planfehler
werden daher ueber evidenzbasiertes Replanning behandelt, nicht ueber
unprotokolliertes Zerteilen einer fehlgeschlagenen Task.

## 4. Verifikation

**Tests sind Specs, keine Attrappen** (ADR-0015, 2026-11-06).

Jeder Test baut seinen State ueber `tests/factories.py::mk_state(**overrides)`.
Damit ist garantiert:
- Alle `RunState`-Felder existieren (Defaults greifen fuer nicht-ueberschriebene)
- Tippfehler in Test-Feldern fail-loud (`mk_state(apikey=...)` wirft)
- mypy findet Feld-Umbenennungen in Tests
- Prod-Code kann `state.X` direkt nutzen (kein `getattr`-Fallback noetig)

`SimpleNamespace` bleibt nur fuer **Mock-Bundles** erlaubt (LLM-Reply,
Function-Referenzen wie `SimpleNamespace(run_builder=..., audit=...)`).
State-Attrappen mit `SimpleNamespace(project_dir=..., aufgabe=...)` oder
`class _State: def __init__(self): self.X = ...` sind verboten.

Verifikations-Pipeline:- ruff --fix vor _verify_patches (M-467).
- Circuit Breaker in _reflection_loop (M-467).
- Kein except Exception ohne # noqa: BLE001.
- Fail closed: jeder Fehler -> ApplierError-Subklasse.

## 5. Doku-Werkzeuge (2026-10-31)

- werkstatt/scaffold.py: legt §2-Pflichtdateien idempotent an.
  Templates in werkstatt/templates/.
- werkstatt/migrate.py: prueft §2/§3/§5/§6 (§7-Schritt A).
  --apply legt fehlende Pflichtdateien an, loescht NICHTS.
- werkstatt/orchestrator.py::_sortiere_docs_nach_prioritaet:
  sortiert docs-Dict nach §6-Lese-Reihenfolge. load_docs nutzt das;
  d.h. state.docs ist bereits priorisiert.
- werkstatt/scout.py: bekommt PROJEKT-DOKU-Sektion (max 4000 Z. je
  Doc, §6-Reihenfolge) in user_content, direkt nach der Original-
  Zuweisung (_docs_prepend + user_content).
- werkstatt/scout.py::SCOUT_SYSTEM: OP-NNN-DISZIPLIN-Sektion.
  Bei vagen Aufgaben waehlt der Scout GENAU EINEN OP-NNN aus
  docs/STATUS.md.

## 6. Doku-Vertrag

Der Loop liest die Living Docs in der Reihenfolge aus
DOC_CONVENTIONS.md §6. Pflichtfelder im Manifest
projects/<name>.yaml: {entry, status, roadmap, architecture, progress,
conventions, adr_index, glossary}. PROGRESS wird als historische Evidenz
begrenzt auf die zehn neuesten Bloecke und 12.000 Zeichen in den Run-Kontext
geladen. STATUS bleibt Quelle fuer offene OPs; Progress-Eintraege muessen bei
einem OP-Abschluss mit STATUS und Delete-Zone konsistent aktualisiert sein.
CHANGELOG bleibt optional und wird nicht in den Loop-Kontext geladen.

## 7. Doku-Verweise

- docs/index.md — Doku-Einstieg
- docs/STATUS.md — offene Punkte (OP-NNN, §5)
- docs/ROADMAP.md — Phasen
- PROGRESS.md — Historie (append-only)
- docs/adr/ — Architecture Decision Records


## Daten-Fluesse im Loop (Stand 2026-11-02)

### Explorer-Findings (Welle E)

Der Explorer schreibt `state.explorer_findings` mit:
- `git_dirty` (bool)
- `pytest_laufzeit_s` (int)
- `ruff_befunde` (list)

Diese fliessen in Architect- und Builder-Prompt (`## EXPLORER-FINDINGS`).
Zweck: Architect/Builder entscheiden mit Ground-Truth statt mit Vermutung.
Live-Beleg OP-039: Architect schlug "Doku-Eintrag" vor, obwohl pytest
11 Min laeuft — er wusste es nicht.

### Repair-Hints (Welle F)

`reflection._klassifiziere_fehler` erkennt die dominante Fehlerklasse in
`state.last_verify_errors` und liefert einen konkreten Hint:
- mypy object/int -> typing.cast
- ruff import -> Import reparieren
- patch_not_applied -> neuen Anker suchen
- pytest assertion -> Code/Test-Diagnose

Builder-Prompt erhaelt den Hint als `## REPAIR-HINT`-Block.
Zweck: Reflection mit konkretem Pattern statt "repariere irgendwas".
Live-Beleg: 3 von 3 Reflection-Stagnationen am 2026-11-02 hatten eine
Klasse, fuer die es einen klaren Hint gibt.

### Scout-API-Auszug (Welle D3, bereits vorher live)

`state.scout_api_auszug` wird vom Scout gefuellt und in Builder-Prompt
injiziert (`## API-SIGNATUREN`). Reduziert den AST-Index (13 Dateien) auf
die relevanten Symbole fuer den Builder.

### Rollen-Kette (unveraendert, bewusst)

Explorer -> Scout -> Architect -> Planner-Split -> Builder -> Verify ->
Reviewer -> (Reflection bei Fail) -> Phase-Review -> Human-Gate.

Jede Stufe reduziert die Kontextmenge fuer die naechste. Der Builder
bekommt am Ende: 1 Task-Beschreibung, 1 Datei, relevante API-Signaturen,
Explorer-Findings, Repair-Hints. Nicht: den ganzen Repo-Index.

Welle G (`single_call`-Modus, Architect liefert Tasks direkt) wurde am
2026-11-02 versucht und revertiert (`c1e8377`). Grund: Planner-Split
parst Prosa in logische Task-Granularitaet, nicht in Datei-Granularitaet.
Ein datei-basierter Extraktor produziert falsche Task-Grenzen.

### Determinismus-Inseln

- `verify.json` als Projekt-Vertrag
- `_baue_api_index` (AST)
- `_pruefe_api_widerspruch`
- `_deterministic_entfernen_precheck`
- `_stage_anzahl`, `_stage_ids` (Verify-Helpers)
- `_collapse_excess_blank_lines` (Post-Patch)
- `_klassifiziere_fehler` (Repair-Hint-Klassifikation)
- OP-064b Antipattern-Scanner
- OP-064a Sticky-Veto
- `_delete_zone_op_append` (Doku-Nachzug)

## 8. Event-Architektur (2026-11-08, ADR-0024)

Zwei Ebenen, single-writer, rebuildbar.

### 8.1 Write Model — zwei JSONL-Streams

`audit()` schreibt semantische Events, `stream()` hochfrequente
Laufzeit-Events. Beide bauen ein JSON-Schema mit
`event_id = sha256(run_id|audit_id)[:16]`.

    Stream     Datei                                  git      Inhalt
    Semantic   audit-logs/semantic-YYYY-MM-DD.jsonl   ja       loop_*, builder_*, reviewer_*, gate_*, pipeline_start, summary, explorer_*
    Stream     audit-logs/stream-YYYY-MM-DD.jsonl     nein     log_line, progress, spinner, heartbeat, task_started, task_done

Zuordnung in `werkstatt/audit.py::_STREAM_KINDS`. Fail-closed:
unbekannter Kind geht in Semantic.

### 8.2 Read Model — SQLite als Projektion

`werkstatt/projection.py::Projector` liest JSONL und schreibt SQLite
idempotent:

- `rebuild(von_seq=0)` — alle JSONL → SQLite, DELETE + replay
- `tail()` — ab Checkpoint inkrementell
- `status()` — `{jsonl_events, sqlite_rows, diff, last_checkpoint}`

Schema: `events(event_id UNIQUE, ...)` mit `INSERT ... ON CONFLICT
IGNORE`. Checkpoint in `projection_state(key, value)`.

**Kern-Regel:** SQLite wird ausschliesslich vom Projektor beschrieben.
Web-Control-Events werden ueber `audit()` in Semantic-JSONL geschrieben;
Chat-Job-Lifecycle-Events werden aus der persistenten Job-Event-Tabelle mit
stabiler `event_id` in JSONL ausgespielt; Benutzertexte und Tool-Inhalte
bleiben aus dem git-sichtbaren Audit-Stream heraus. Danach aktualisiert `Projector.tail()`
das Read Model. Ein Rebuild rekonstruiert damit auch Control- und Chat-Events.
Direkte `EventStore().append()`-Aufrufe in der Produktion sind verboten.

### 8.3 Health

`GET /api/projects/{name}/projection/status` liefert den globalen
JSONL/SQLite-Vergleich gemaess ADR-0023. `jsonl_events` und `sqlite_rows`
zaehlen dieselbe Basis eindeutiger Event-IDs aus aktiven, nicht migrierten
JSONL-Dateien. Historische SQLite-Zeilen ausserhalb der Basis stehen separat
in `sqlite_rows_outside_basis`. `comparison_basis`, `comparison_anchor` und
`comparison_period` machen die Herleitung sichtbar; fehlerhafte JSONL-Zeilen
oder fehlende/ungueltige Zeitstempel setzen `comparable=false`. Die
Statusleiste warnt bei `diff > 0` oder einem unvollstaendigen Vergleich.

### 8.4 Regel

Alte SQLite bleibt unangetastet bis `rebuild()` gruen und
`db_hash_identisch()` nach Doppel-Rebuild. Bei Fehler: alte DB
zurueck, kein Datenverlust.

## 9. UI und Projektkontext


Die Weboberflaeche ist projektzentriert: Projektleiste, darunter
Modusleiste, danach die Flaeche fuer den gewaehlten Modus. Bei leerer
Projektauswahl dient die Projektuebersicht als Startseite. Sie zeigt
Projektkarten, Laufstatus, Erfolgskennzahlen und den Zugang zum Oeffnen
oder Anlegen eines Projekts. Der spaetere werkstattweite Metaorchestrator
sitzt auf dieser Startseite und koordiniert alle registrierten Projekte.
Sein Chat ist der globale Ansprechpartner fuer Status, offene Ops,
Priorisierung und Delegation. In jedem Projekt bleibt der dortige Chat der
projektbezogene Koordinator und Assistent; schreibende Arbeit laeuft nur im
isolierten Projektloop. Globale Praeferenzen sind versioniert, waehrend
projektbezogene Regeln und Belege strikt im jeweiligen Projektkontext bleiben.


Im Control-Modus stehen Live-Feed und Chat nebeneinander. Aktionen wie
Start, Pause, Fortsetzen und Stop muessen im Chat bzw. in der sichtbaren
Steuerung eine nachvollziehbare Statusrueckmeldung liefern. Der Chat wird
nicht als schwebendes, vom Projektkontext getrenntes Panel geplant.


Die UI zeigt nur Daten, die durch Backend/Event-Store belegt sind. Live-
Ereignisse und nachtraegliche Zusammenfassungen haben getrennte
Darstellungsaufgaben. ADR-0030 fuer Projektquellen und Rollenmodelle ist
angenommen; OP-399/OP-400 beschreiben die noch offene Umsetzung.
