# Ist-Zustand des Werkstatt-Loops — GitHub main 2026-11-14

Diese Bestandsaufnahme beschreibt den Repository-Stand und trennt ihn vom
laufenden Server. Ein gruener GitHub-Run beweist die Tests des Commits, aber
nicht, dass der Server diesen Commit bereits ausfuehrt.

Gepruefter Hauptlinienstand: `d7f32e8` (Merge PR #25). GitHub Actions
Quality Gate [43576037105](https://github.com/ghxstfocus/werkstatt/actions/runs/43576037105)
bestand fuer den PR-Tree mit 2.262 Pytests und 5 uebersprungenen Tests,
Ruff, Mypy, AST und Audit-Katalog. Der zuletzt vom Nutzer gemeldete
Serverlauf aktualisierte `main` bis `3cbaf26` und bestand mit denselben
2.262 Tests; er belegt nicht, dass der Server bereits `d7f32e8` ausfuehrt.
Der zusaetzliche Recovery-Beleg aus PR #8 wurde auf Commit `2130019` mit
Quality-Gate-Run
[43488902240](https://github.com/ghxstfocus/werkstatt/actions/runs/43488902240)
erfolgreich verifiziert. Seit der letzten Bestandsaufnahme
wurden unter anderem Akzeptanzkriterien explizit auf Tasks abgebildet und als
Checkpoint-Daten erhalten, Verify-Reparaturen auf betroffene Stages begrenzt
und danach die vollstaendige Phase-End-Pruefung erneut ausgefuehrt. Der
Werkzeugdialog erkennt wiederholte und alternierende Werkzeugzyklen ohne
pauschale Rundengrenze. Diese CI-Belege betreffen den Repository-Stand, nicht
den aktuell laufenden Produktionsserver.

## Chat-Belegsuche: GNU-grep-Alternation

Der gespeicherte Chat-Verlauf zur OP-374-Pruefung zeigte eine widerspruechliche
Recherche: `grep` fand `_letzter_run_id` zunaechst korrekt, meldete bei
spaeteren Suchmustern wie `run_id|project` aber faelschlich keinen Treffer.
Ursache war GNU grep im Basic-Regular-Expression-Modus, in dem `|` keine
Alternation ist. PR #20 aktiviert ERE mit `-E`; der Chat-Prompt verlangt bei
widerspruechlichen Suchbelegen nun erneutes Lesen der Quelle und priorisiert
bestaetigte positive Treffer. Die Regression ist in
`tests/test_chat_tools.py::test_grep_unterstuetzt_ere_alternation` abgesichert.
Der laufende Webprozess wurde nach dem Merge neu gestartet; der Regressionstest
lief danach direkt auf dem Server erfolgreich.

## Scout-/Architect-Beleguebergabe

Im Scout-Pfad ersetzt der kompakte Scout-Bericht die Explorer-Rohdaten.
Der Architect erhaelt deshalb jetzt fuer OP-, Scout- und Explorer-Zieldateien
einen begrenzten Auszug aus dem aktuellen AST-Index. Angeforderte Scout-Symbole
werden gegen aktuelle Signaturen abgeglichen; deterministisch erkannte
API-Widersprueche bleiben im Architect-Kontext erhalten. Scout-Pfade mit
Windows-Backslashes werden vor dem Symbolabgleich normalisiert. Regressionen
pruefen konkrete Projector-/Inspector-Signaturen, ausgeschlossene Dateien,
Pfad-Traversal und die Auszugslimits. Das macht den Scout nicht zum
Pflichtschritt: der Planner darf ihn bei einem expliziten, belegten Einzel-
Dateiziel weiterhin ueberspringen.

### Nachpruefung: API-Wirkungen und Verify-Interpreter

Der vorherige Signaturauszug war nur Prompt-Kontext: er belegte Namen und
Signaturen, setzte aber weder eine verbindliche API-Pruefung vor dem Builder
noch eine Lese-/Schreibwirkung durch. Das zeigte OP-375: `get_run_record()`
und `transition_run_status()` existieren tatsaechlich in
`werkstatt/event_store.py`; der Architect hatte also keine fehlenden Methoden
erfunden. Der Plan setzte aber die schreibende Statusmutation
`transition_run_status()` in einen Lese-Aggregator. Der Reviewer bemerkte den
Seiteneffekt erst nach dem Builder-Aufruf. Der AST-Index kennzeichnet jetzt
erkennbare Effekte; der Architect-Preflight verwirft unbelegte APIs und
Schreib- oder unbekannte Effekte in einem als read-only beschriebenen
Aggregator vor Planner-Split und Builder und gibt einen Korrekturversuch.
Das ist ein deterministischer Guard fuer codeartig referenzierte APIs, kein
allgemeiner Beweis beliebiger Python-Purity.

Der OP-375-Run protokollierte ausserdem Ruff-, Mypy- und Import-Linter-Ausfaelle,
weil `projects/werkstatt.yaml` nur `venv_python: python3` vorgab und die
Verify-Stages dadurch System-Python bzw. System-Tools verwendeten. Verify loest
eine solche generische Angabe jetzt auf die Projekt-`.venv` auf, sofern sie
existiert; explizite Interpreterpfade bleiben vorrangig. Die Regression wird
lokal unter Windows gezielt getestet; der komplette Loop-Testlauf ist dort
nicht als Linux-Nachweis verwendbar, weil Projektkonfiguration und POSIX-
Annahmen einen grossen Teil der Tests fail-closed abbrechen lassen. CI muss
den Linux-Qualitaetslauf fuer den Branch bestaetigen.

## Kurzbefund

Die Werkstatt hat operative Bausteine fuer Projekt-Runs, spezialisierte
Rollen, harte Verify-Stufen, Human Gates, Failure Records, Event Store,
Chatjobs und Prozess-Registry. Rote Phase-End-Verifikation kann im selben Run
diagnostiziert und repariert werden; nach Commits wird der committed Stand
erneut vollstaendig verifiziert.

Der Produktionslauf bleibt jedoch eine feste Folge aus Setup/Explorer,
Plan/Preflight, Task-Loop und Finalizer. Der persistierte RunRecord,
Event-Inbox, Chatjob, Phase-Checkpoint und Prozess-Registry bilden noch
keinen einheitlichen zielorientierten Koordinator mit veraenderbarem
Arbeitsgraphen und Evidence Ledger.

## Implementierte Vertraege

| Bereich | Aktueller Stand |
|---|---|
| Laufsteuerung | `run_pipeline_loop` ruft Setup, Plan, Task-Loop und Finalizer in fester Folge auf. Phasen bleiben Runtime-Steuerung. |
| Failure Records | Rote Abschlusspruefungen liefern redigierte, Run-gebundene Befunde mit Stage, Exit-Code, HEAD und Worktree-Fingerprint. Recovery zielt auf fehlgeschlagene Verify-Stages; nach einer Reparatur wird die vollstaendige Phase-End-Pruefung erneut ausgefuehrt. Wiederholte Befunde ohne wirksame Worktree-Aenderung stoppen fail-closed. |
| Recovery | `test_resume_endpoint_runs_production_cli_to_completed_run` laesst den HTTP-Resume-Endpunkt den echten CLI-Worker starten und prueft denselben Run bis zum erfolgreichen Phase-End-Verify: Run-ID, terminaler Exitcode, Checkpoint-Version, Verify-Marker und weiterhin erledigte Tasks. `test_resume_route_recovers_after_real_worker_exit` prueft zusaetzlich Reattach ueber eine neue Registry-Instanz und den Resume-Aufruf nach Worker-Ende. Ein tatsaechlicher Webserver-Absturz mit anschliessendem Serverneustart und autonomer Wiederaufnahme ist weiterhin nicht E2E belegt. |
| Commit und Verify | Commit-Pruefungen pinnen Parent-HEAD und Index-Tree. Nach einem Commit laeuft die vollstaendige Phase-End-Verify erneut; Snapshot-Abweichungen verhindern Erfolg. |
| Run-Ergebnis | Ein gruener Teilcheck genuegt nicht. Task-Akzeptanzkriterien werden vor dem Gate auf Abdeckung geprueft und Referenzen bleiben im Checkpoint erhalten. Offene/fehlgeschlagene Tasks, nicht abgedeckte Kriterien oder rotes Verify verhindern den Erfolg. |
| Prozessstatus | Die Registry ueberlebt Webserver-Neustarts und kann lebende Worker wiederfinden. Sie und der RunRecord bleiben getrennte Speichervertraege. |
| Run-Inbox | SQLite speichert Nachrichten idempotent mit Lease/Fencing. Run-gebundene Chatjobs fuehren zusaetzlich eine Outbox-Markierung: Inbox-Eintrag wird vor Worker-Dispatch geschrieben und bei Reconnect/Resume idempotent reconciliert. Der Task-Loop konsumiert Annahme- und terminale Ergebnis-Hinweise an Task-Grenzen und schreibt sie crash-sicher in getrennte Checkpoint-Cursor. Beide erscheinen mit stabiler Audit-ID und redigierten Metadaten in der Control-Timeline, bevor der Checkpoint geschrieben und die Inbox bestaetigt wird. Der Ergebnis-Hinweis enthaelt Status und Antwort-Hash, nicht den Antworttext; er bestaetigt die Rueckkehr des Paralleljobs, nimmt aber dessen Inhalt noch nicht als Ziel-/Scope-Aenderung in den Hauptlauf auf. Allgemeine Fragen, Steueraktionen, Gate-Antworten und Schreibauftraege bleiben noch keine vollstaendig integrierten Koordinator-Ereignisse. |
| Control-Timeline | Viele Rollen- und Verify-Schritte sind sichtbar. Lueckenloses Builder-/LLM-Eventing und eine einheitliche Run-Projektion bleiben offen. Chat-Werkzeuge haben keine pauschale Rundengrenze mehr; wiederholte Zyklen loesen Kurskorrektur und bei weiterem Stillstand eine belegte Abschlussantwort aus. |

## Nachgewiesene Start-Race und Korrektur

Vor dieser Aenderung reservierte der Webserver einen Run in der Prozess-
Registry und startete den Worker; der Worker erzeugte den RunRecord erst
spaeter im Loop. Die Chat-Job-API erkennt bereits den Registry-Zustand
`starting`, konnte aber mangels RunRecord keine `job_notice`-Nachricht
einstellen. Der Chatjob wurde trotzdem angenommen. Damit konnte ein waehrend
des Starts eingereichter Job ohne Run-Inbox-Verknuepfung bleiben.

Seit dem Outbox-Fix wird der Chatjob zuerst persistent angelegt, die
Run-Inbox-Nachricht idempotent per `chat-job:<job_id>` geschrieben und erst
danach der Worker dispatcht. Ein lokaler `run_inbox_enqueued`-Marker wird
nach erfolgreichem Inbox-Commit gesetzt. Wenn der Prozess zwischen Inbox-
Commit und Marker ausfaellt, schreibt Resume dieselbe Message-ID erneut;
der Event-Store dedupliziert den Retry. Fehlt der RunRecord temporaer, bleibt
der Outbox-Eintrag offen und wird vor spaeterem Resume erneut versucht.

Der Webstart legt den RunRecord vor `Popen` mit Status `starting` an. Seit
13. November 2026 persistiert er dort zusaetzlich den versionierten
`start_context` (Nutzerziel, OP, Ursprung, freigegebener Vorschlag und
gepinnte Projektquelle). Ein Worker-Retry darf diesen Kontext nicht ersetzen;
ein Konflikt wird vor einer Lifecycle-Aenderung abgelehnt. Alte Datenbanken
erhalten die Spalte additiv und lesen Legacy-Runs mit leerem Kontext und
Version 0. Der Worker-Aufruf wechselt denselben Record idempotent und
zielgebunden nach `running`; ein fehlgeschlagener Spawn markiert den Record
per Compare-and-Swap als `failed`, ohne den Checkpoint zu veraendern. Der
Worker fuellt ausserdem den noch leeren `base_commit` nach, ohne einen bereits
gepinnten Commit zu ueberschreiben. Tests sichern diese Lifecycle-Kanten und
den Spawn-Fehlerpfad.

## Verbleibender Architekturabstand zu ADR-0032

1. **Gemeinsame Run-SSOT fehlt weiterhin:** Der RunRecord enthaelt jetzt den
   unveraenderlichen Startkontext und Checkpoint. Registry, Prozessstatus,
   Freigabedetails und naechste Aktion sind aber noch nicht vollstaendig in
   einen atomar abgeglichenen Run-Vertrag migriert.
2. **Inbox ist nur teilweise integriert:** `job_notice` wird persistiert
   und checkpoint-sicher konsumiert. Bestaetigte Chat-Folgeauftraege werden
   ebenfalls dauerhaft der aktiven Run-Inbox zugeordnet. Explizite OPs
   transportieren dabei ihren gespeicherten Vorschautext; fehlt der Inhalt,
   wird die Annahme fail-closed abgelehnt. Die Aufgaben werden am Checkpoint
   aber noch nicht fachlich disponiert oder in den Arbeitsgraphen uebernommen.
   Der Checkpoint-Consumer weist leere/whitespace-only Inbox-Texte jetzt
   ebenfalls fail-closed ab, bevor sie persistiert oder quittiert werden.
   Fragen, Control und Gate-Antworten veraendern den Arbeitsgraphen ebenfalls
   noch nicht.
3. **Zielorientierter Arbeitsgraph fehlt weiterhin:** Der Planner verwirft
   jetzt strukturell ungueltige Task-DAGs vor dem Plan-Gate und sortiert
   gueltige Abhaengigkeiten stabil. Der Run disponiert Tasks aber weiterhin
   aus dem freigegebenen Plan in einer festen Task-Schleife, statt an
   Checkpoints gegen offene Akzeptanzkriterien neu zu waehlen.
4. **Evidence Ledger fehlt:** Einzelne Verify-/Audit-Belege existieren,
   aber es gibt keine einheitliche Kriterium-zu-Beleg-Zuordnung mit Quelle,
   Befehl, Exit-Code, SHA und Artefakt-Hash.
5. **Recovery ist nicht vollstaendig E2E belegt:** HTTP-Resume startet und
   finalisiert nachweislich denselben Run in einem echten Workerprozess.
   Der integrierte Webserver-Absturz mit anschliessendem Neustart und
   autonomer Wiederaufnahme bleibt offen.
6. **UI-Projektionen sind getrennt:** Chat, Control, Runs und Prozessstatus
   beziehen Teile ihrer Fakten aus verschiedenen Speicher-/API-Pfaden.

## M1-Fortschritt: versionierter Startkontext im RunRecord

Der Webstart schreibt denselben `run_context` in die Prozess-Registry und den
RunRecord, bevor der Worker startet. Der RunRecord bleibt dabei die
persistente Quelle fuer Replay und Recovery; das Registry-Feld bleibt aus
Rueckwaertskompatibilitaetsgruenden bestehen. Bei einem Retry ohne Kontext
bleibt der gespeicherte Wert erhalten. Ein Retry mit abweichendem Kontext
bricht fail-closed ab, bevor der Status von `starting` zu `running` wechselt.
Der Recovery-Pfad vergleicht nun beide gespeicherten Kontexte und lehnt eine
Abweichung ab; Legacy-RunRecords ohne Kontext bleiben wiederaufnehmbar, sofern
die Registry den bisherigen Kontext enthaelt. Migration, Worker-Retry und
Recovery-Konsistenz sind durch Tests abgesichert. Dies ist ein abgegrenzter
M1-Baustein, kein Abschluss von OP-397 oder ADR-0032.

Diese Punkte sind keine fertige Zielarchitektur. Verbindlich sind
[ADR-0032](adr/ADR-0032-adaptiver-zielorientierter-run-kern.md) und
[ROADMAP.md](ROADMAP.md); startbare Arbeit steht in [STATUS.md](STATUS.md).

## OP-403 und Betriebsnachweis

OP-403 ist abgeschlossen und aus der offenen Queue entfernt. Unit-Tests und
GitHub-CI belegen keine vollstaendige Server-Dogfooding-Abnahme. Zehn
UI-Runs mit Frage waehrend Arbeit, Gate, Pause/Resume, Reconnect,
Verify-Fehler-Recovery und Abschluss bleiben Teil von OP-382.

## OP-398: deterministische DAG-Grenze

Der Planner lehnt duplicate/fehlende Task-IDs, malformed, unbekannte,
doppelte oder selbstreferenzierende Abhaengigkeiten sowie Zyklen vor dem
Plan-Gate mit einem konkreten Audit-Befund ab. Gueltige Graphen werden stabil
topologisch sortiert. Akzeptanzkriterien muessen Tasks zugeordnet sein; die
Referenzen werden im Checkpoint wiederhergestellt, waehrend Legacy-Plaene ohne
explizite Referenzen rueckwaertskompatibel bleiben. Das verhindert bekannte
Struktur- und Abdeckungsfehler vor der Ausfuehrung. Der Run disponiert Tasks
aber weiterhin aus dem freigegebenen Plan in einer festen Task-Schleife,
statt an Checkpoints gegen offene Kriterien neu zu waehlen; der zielorientierte
Arbeitsgraph von OP-398 bleibt offen.

### Nachpruefung: Rollenrouting und Spec-First-Runtime

Der Planner waehlt den Scout bereits bedarfsgesteuert: ein enges, explizites
Einzeldateiziel kann den Scout-LLM-Aufruf ueberspringen; der Architect bleibt
im normalen Pfad fuer den unabhaengigen Plan aktiv. Ein deterministisch
belegbarer atomarer Plan kann auch den Architect ueberspringen. Diese Wege
sind in `tests/test_planner_agent.py` und `tests/test_scout_kette.py` abgedeckt.

Der in ADR-0032 vorgesehene Spec-First-Pfad ist dagegen noch nicht in die
Produktionssteuerung verdrahtet. `werkstatt/test_spec.py` und
`werkstatt/test_spec_validator.py` enthalten Datentypen und einen Validator,
aber in `werkstatt/` gibt es keinen Aufruf von `validate_test_spec()`.
`run_planner()` ruft weiterhin Architect und anschliessend den separaten
Planner-Split auf; ein Routingentscheid fuer Spec-First, ein eingefrorener
Spec-/Test-Hash und ein technisch abgeschirmter Blind-Builder sind nicht
belegt. Die vorhandenen Module allein erfuellen ADR-0032 daher nicht.

### Nachpruefung: OP-374 und Projekt-Herkunft

Der aktuelle `_letzter_run_id()` in `werkstatt/web/inspector.py` schliesst
bereits `NULL` und leere Run-IDs aus. In `werkstatt/projection.py` ist
`events.run_id` als `NOT NULL` angelegt; `_insert()` normalisiert eine fehlende
ID zu `''`. Bei alten Schemas wird eine fehlende `project`-Spalte mit
`DEFAULT 'werkstatt'` migriert. `Projector.status()` beschreibt den Vergleich
ausdruecklich als global.

Folgerung fuer die Umsetzung von OP-374: Herkunft darf nicht pauschal gegen
das Literal `'werkstatt'` geprueft werden. Das wuerde gueltige Events anderer
Projekte fehlklassifizieren. Ein Projekt-Backfill braucht einen eigenen,
projektisolierten Replay-Vertrag und darf weder den globalen Tail-Checkpoint
verschieben noch fremde Projektzeilen als wiederverifizierten Erfolg
ausweisen. Akzeptanztests muessen mindestens zwei Projekte und historische
Zeilen mit leerer Run-ID abdecken, bevor der Pfad als erledigt gelten kann.

## Naechster Architektur-Schritt

M1 aus ADR-0032 bleibt offen: die vorhandene Run-Inbox muss in einen
einheitlichen Run-Vertrag ueberfuehrt werden, der Fragen, Steuerung,
Gate-Antworten und Schreibauftraege idempotent dem selben Run zuordnet und
deren Wirkung an sicheren Checkpoints definiert. Die vorhandenen SQLite-
Stores, Prozess-Registry und Phase-Checkpoints sind zu migrieren, nicht
durch einen unverbundenen zweiten Statusspeicher zu verdoppeln.

### Aktuelle Inbox-Grenze

Der Codepfad bestaetigt die dokumentierte OP-401-Luecke: `chat_followup_request`
wird in `werkstatt/phases/tasks.py::_persist_run_checkpoint` validiert,
auditiert und als `received` im RunCheckpoint abgelegt. Die Web-UI bekommt
eine `loop_followup_checkpointed`-Rueckmeldung. Im Repository gibt es danach
keinen Consumer, der diese Nachricht als Frage/Diagnose, Steuerung, innerhalb
des freigegebenen Scopes liegenden Folgeauftrag oder Scope-Aenderung disponiert
und gegebenenfalls den Task-Graph aktualisiert. Deshalb ist der Checkpoint
ein dauerhafter Eingangsnachweis, aber noch keine Bearbeitungs- oder
Abschlussbestaetigung fuer den Folgeauftrag. Diese Grenze muss bei OP-401/
ADR-0032 erhalten bleiben, bis die Disposition und ihr Ergebnis-Gate umgesetzt
und getestet sind.
