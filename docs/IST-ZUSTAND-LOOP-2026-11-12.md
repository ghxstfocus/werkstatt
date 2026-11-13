# Ist-Zustand des Werkstatt-Loops — GitHub main 2026-11-13

Diese Bestandsaufnahme beschreibt den Repository-Stand und trennt ihn vom
laufenden Server. Ein gruener GitHub-Run beweist die Tests des Commits, aber
nicht, dass der Server diesen Commit bereits ausfuehrt.

Gepruefter Code-Stand: `93831e5` (Quality-Gate-Run
[43362294835](https://github.com/ghxstfocus/werkstatt/actions/runs/43362294835));
der zugehoerige Dokumentationsstand wurde anschliessend bis `6042fe7`
fortgeschrieben. Seit dem UI-Plan-Abgleich (`9ecc994`) sind
RunRecord-Startzustand, Run-Inbox-Outbox und Outbox-Recovery integriert.
Der Plan-Compiler verwirft inzwischen ungueltige Task-DAGs vor dem Plan-Gate.
Der Quality-Gate-Run belegt 2.158 bestandene Tests, 5 uebersprungene Tests
und fehlerfreie Ruff-, Mypy-, AST- und Audit-Katalog-Pruefungen. Das belegt
Repository-Tests, nicht den aktuell laufenden Produktionsserver.

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
| Failure Records | Rote Abschlusspruefungen koennen redigierte, Run-gebundene Befunde mit Stage, Exit-Code, HEAD und Worktree-Fingerprint liefern. |
| Recovery | Der Resume-Akzeptanztest prueft HTTP-Route, dieselbe Run-ID und `--resume`, dann die Ausfuehrung bis zur erfolgreichen Phase-End-Verify. Der CLI-Aufruf laeuft im Test-Hauptthread; ein separater Probe prueft den Launcher. Ein echter vom HTTP-Endpunkt gestarteter Worker, der nach einem Webserver-Absturz autonom denselben Run wiederaufnimmt, ist nicht durchgehend belegt. |
| Commit und Verify | Commit-Pruefungen pinnen Parent-HEAD und Index-Tree. Nach einem Commit laeuft die vollstaendige Phase-End-Verify erneut; Snapshot-Abweichungen verhindern Erfolg. |
| Run-Ergebnis | Ein gruener Teilcheck genuegt nicht. Offene/fehlgeschlagene Tasks oder rotes Verify verhindern den Erfolg. |
| Prozessstatus | Die Registry ueberlebt Webserver-Neustarts und kann lebende Worker wiederfinden. Sie und der RunRecord bleiben getrennte Speichervertraege. |
| Run-Inbox | SQLite speichert Nachrichten idempotent mit Lease/Fencing. Run-gebundene Chatjobs fuehren zusaetzlich eine Outbox-Markierung: Inbox-Eintrag wird vor Worker-Dispatch geschrieben und bei Reconnect/Resume idempotent reconciliert. Der Task-Loop konsumiert Hinweise an Task-Grenzen und schreibt sie crash-sicher in den Checkpoint. Fragen, Steueraktionen, Gate-Antworten und Schreibauftraege sind noch keine vollstaendig integrierten Koordinator-Ereignisse. |
| Control-Timeline | Viele Rollen- und Verify-Schritte sind sichtbar. Lueckenloses Builder-/LLM-Eventing und eine einheitliche Run-Projektion bleiben offen. |

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

Der Webstart legt den RunRecord jetzt vor `Popen` mit Status
`starting` an. Der Worker-Aufruf wechselt denselben Record idempotent und
zielgebunden nach `running`; ein fehlgeschlagener Spawn markiert den Record
per Compare-and-Swap als `failed`, ohne den Checkpoint zu veraendern. Der
Worker fuellt ausserdem den noch leeren `base_commit` nach, ohne einen bereits
gepinnten Commit zu ueberschreiben. Tests sichern diese Lifecycle-Kanten und
den Spawn-Fehlerpfad.

## Verbleibender Architekturabstand zu ADR-0032

1. **Gemeinsame Run-SSOT fehlt:** Ziel, Freigabe, Basis, Checkpoint,
   naechste Aktion und Prozessstatus liegen weiterhin in getrennten
   Komponenten.
2. **Inbox ist nur teilweise integriert:** `job_notice` wird persistiert
   und checkpoint-sicher konsumiert. Fragen, Control, Gate-Antworten und
   Schreibauftraege veraendern den Arbeitsgraphen noch nicht.
3. **Zielorientierter Arbeitsgraph fehlt weiterhin:** Der Planner verwirft
   jetzt strukturell ungueltige Task-DAGs vor dem Plan-Gate und sortiert
   gueltige Abhaengigkeiten stabil. Der Run disponiert Tasks aber weiterhin
   aus dem freigegebenen Plan in einer festen Task-Schleife, statt an
   Checkpoints gegen offene Akzeptanzkriterien neu zu waehlen.
4. **Evidence Ledger fehlt:** Einzelne Verify-/Audit-Belege existieren,
   aber es gibt keine einheitliche Kriterium-zu-Beleg-Zuordnung mit Quelle,
   Befehl, Exit-Code, SHA und Artefakt-Hash.
5. **Recovery ist nicht vollstaendig E2E belegt:** Der integrierte
   Webserver-Absturz mit autonomer Wiederaufnahme eines gestarteten Workers
   bleibt offen.
6. **UI-Projektionen sind getrennt:** Chat, Control, Runs und Prozessstatus
   beziehen Teile ihrer Fakten aus verschiedenen Speicher-/API-Pfaden.

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
topologisch sortiert. Das verhindert, dass bekannte Strukturfehler erst im
Task-Loop als still blockierte Arbeit sichtbar werden. Es ersetzt weder die
Abdeckung von Akzeptanzkriterien noch den zielorientierten Arbeitsgraphen;
diese Teile von OP-398 bleiben offen.

## Naechster Architektur-Schritt

M1 aus ADR-0032 bleibt offen: die vorhandene Run-Inbox muss in einen
einheitlichen Run-Vertrag ueberfuehrt werden, der Fragen, Steuerung,
Gate-Antworten und Schreibauftraege idempotent dem selben Run zuordnet und
deren Wirkung an sicheren Checkpoints definiert. Die vorhandenen SQLite-
Stores, Prozess-Registry und Phase-Checkpoints sind zu migrieren, nicht
durch einen unverbundenen zweiten Statusspeicher zu verdoppeln.
