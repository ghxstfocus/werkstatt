# Status — Werkstatt

Format gemaess `DOC_CONVENTIONS.md` §5. Diese Queue enthaelt nur offene, konkret loop-faehige Arbeit aus dem aktuellen Produktfokus. Historische, optionale und noch nicht angenommene Architekturideen stehen nicht als startbare OPs hier.

`—` bedeutet: vor dem Start konkretisieren. Der Arbeitsfokus steht in `docs/ROADMAP.md`; abgeschlossene oder verworfene Arbeit steht in `PROGRESS.md`.

Letzte Aktualisierung: 2026-11-13.

## Offene Punkte
### OP-404: Codeguardian als unabhaengige Schutz- und Evidenzschicht
- **Status:** open
- **Typ:** change-guardian
- **Betroffene Dateien:** Verify-/Review-Vertrag, Rollen- und Tool-Policies, Event-Projektion, Control-/Debug-UI und Tests
- **Akzeptanzkriterien:** Der Codeguardian ist kein zweiter schreibender Builder. Deterministische Scope-, Secret-, Dependency-, Test- und Policy-Checks laufen auf dem gepinnten Diff; unabhaengige semantische Review wird risikobasiert zugeschaltet. Jeder Befund verweist auf Datei/Zeile oder Verify-Artefakt und unterscheidet Blocker, Warnung und Information. Er darf keine Gates oder harten Checks umgehen; Reparaturen gehen an denselben Run zurueck und muessen erneut verifiziert werden. Vor Ausfuehrung sind Regelquellen, False-Positive-Pfad, Datenredaktion und Betriebsgrenzen dokumentiert.
- **Tests:** Scope-Verletzung, Secret-/Dependency-Befund, begruendetes Risiko-Routing, sichere Tool-Ausgaben, Finding-Provenance, False-Positive-Ablehnung und erneute Verify nach Patch.
- **Blockiert von:** OP-396

### OP-405: Rollenbezogenen Belegkontext und Kontextbudgets steuern
- **Status:** open
- **Typ:** loop-quality
- **Betroffene Dateien:** Rollen-/Prompt-Builders, Repo-Retrieval, Verify-Konfiguration und Tests
- **Akzeptanzkriterien:** Jede aktive Rolle hat ein deterministisches Kontextbudget und eine Priorisierung, die Nutzerauftrag, relevante ADRs, aktuelle Diff-/Verify-Belege und Sicherheitsregeln vor optionalem Kontext erhaelt. Rollen koennen bei belegtem Bedarf projektgebunden, read-only und begrenzt Dateien/Symbole nachladen; Belege tragen Pfad und Fundstelle. Ueberschreitungen und Retrieval-Ergebnisse werden auditiert und sichtbar markiert, nie still abgeschnitten. Volle Logs bleiben als Artefakte verfuegbar, aber nur relevante markierte Auszuege gelangen in Modellkontexte. Verify prueft Budget und Rollenrouting deterministisch. Rollen-Tokens und Ergebnisqualitaet werden auf einem repräsentativen Eval-Satz gemessen.
- **Tests:** Budgetgrenzen und Priorisierung je Rolle; JIT-Retrieval mit Projektisolation, Treffer, leere/mehrdeutige Suche; untrusted Tool-Ausgabe; sichtbare Ueberschreitung; Regression bei Rolle, Limit und Prompt-Aufbau; Tokens-/Qualitaetsvergleich.
- **Blockiert von:** OP-398

### OP-396: Chat als projektbezogene Hauptoberflaeche
- **Status:** open
- **Typ:** ui-orchestration
- **Betroffene Dateien:** Chat/Web-UI, Chat- und Loop-Control-Tests
- **Akzeptanzkriterien:** Repo-Fragen liefern Datei-/Zeilen- oder Testbelege. Das Status-Werkzeug liest die kanonische Queue, Roadmap und Architektur sowie den neuesten Abschnitt aus der Root-`PROGRESS.md`; eine verbotene `docs/PROGRESS.md`-Kopie darf den aktuellen Stand nicht ueberschreiben. Der Chat erstellt fuer direkte Auftraege und OPs einen begruendeten Plan samt Empfehlung und uebergibt genau diesen ohne Copy/Paste an den Loop. Planstand und Freigabeversion bleiben interne Metadaten; die UI zeigt eine natuerliche Zusammenfassung. Neue Chatfragen koennen parallel beantwortet werden. Bei laengerer Arbeit zeigt eine einzelne temporaere Zeile im Chat knapp den aktuellen Schritt; sie wird ersetzt und nach Abschluss entfernt. Die detaillierten Ereignisse bleiben in Control replaybar. Das Plan-Gate erscheint im Chat; Freigabe ist intern an Projekt und Planstand gebunden. Eine relevante Scope-/Basis-Aenderung invalidiert die alte Freigabe; Mehrdeutigkeit fragt gezielt nach. Die freigegebene Version autorisiert Code, Tests, Doku, Verify und lokalen Commit nur innerhalb ihres Umfangs; externe/destruktive Aktionen erhalten ein separates Gate. Werkzeugarbeit endet nicht an einer willkuerlichen Standard-Rundenzahl, sondern an einer finalen Antwort, Nutzerabbruch oder erkannten Stillstand: Wiederholte identische Aufrufe mit gleichem Ergebnis loesen erst eine Kurskorrektur, bei weiterem Stillstand eine belegte Abschlussantwort mit offenen Punkten aus. Abgeschlossene Dialoghistorie und aktive Werkzeugrunden werden innerhalb definierter Kontextbudgets priorisiert und verdichtet, ohne den persistenten Event-Store zu kuerzen; gekuerzte Ausgaben sind als Auszuege markiert und koennen gezielt erneut gelesen werden. Kontrollaktionen bleiben explizit; ein bestaetigter Start bei bereits laufendem Loop wird als nicht gestartet gemeldet und nicht als Erfolg verbucht; Ergebnis-Gate und Reconnect sind abgesichert.
- **Tests:** Status-Tool liest Root-PROGRESS statt verbotener Duplikatdatei und liefert aktuelle STATUS/ROADMAP/ARCHITECTURE-Quellen; Plan-Version und Loop-Handoff, Empfehlungsbelege, Freigabe/Ablehnung/Revision, mehrdeutige Antworten, Projektisolation, Kontrollaktionen, Reconnect und parallele Fragen waehrend eines Runs; mehr als fuenf Werkzeugrunden ohne Abbruch, Fortsetzung bis Ziel, Nutzerabbruch, echte Run-Budgetgrenze oder belegter Stillstand, Kurskorrektur bei wiederholtem identischem Werkzeugzyklus und Nutzerabbruch. Abgeschlossene alte Turns halten das Prompt-Zeichenbudget ein; alte Roh-Werkzeugausgaben werden nicht erneut injiziert. Auch waehrend eines aktiven Auftrags wird der Werkzeugkontext zwischen abgeschlossenen Runden auf ein Zeichenbudget begrenzt: neueste Runden bleiben bevorzugt vollstaendig, aeltere Belege werden markiert verdichtet; grosse Einzel-Ausgaben werden nur im Prompt gekuerzt und bleiben im Event-Store vollstaendig. Ein gekuerzter Beleg muss bei Bedarf gezielt erneut gelesen werden. Der persistente Transcript bleibt unveraendert.
- **Blockiert von:** —

### OP-397: Hintergrundjobs und Checkpoint-Steuerung
- **Status:** open
- **Typ:** async-jobs
- **Betroffene Dateien:** Chatjobs, Event-Store, Loop-Registry, Web-API, `werkstatt/phases/plan.py` und Tests
- **Akzeptanzkriterien:** Beim atomaren Web-Start werden mindestens Zieltext, OP-ID, Herkunft, gepinnte Remote-Revision und Auswahlbegruendung als versionierter Startkontext in der restartfesten Run-Registry gespeichert und ueber den aktiven Loop-Endpunkt wieder abgerufen; bestehende Registry-Daten werden additiv migriert. Lange Lese-/Verify-Aufgaben laufen mit stabiler Job-ID unabhaengig von Chat-Requests und sind nach Reconnect replaybar. Idempotenz, Abbruch und Projektisolation sind abgesichert. Lese- und Diagnosejobs duerfen parallel laufen. Die Checkpoint-Steuerung liefert die Grundlage fuer parallele Schreibauftraege und deren Integration in OP-402. Plan-Aenderungen pausieren am sicheren Checkpoint; eine neue Freigabe ist nur noetig, wenn Scope oder Freigabeinhalt betroffen sind. Ein Auftragwechsel aendert den Run-Zielgraphen nur am sicheren Checkpoint. Bisherige Belege und erledigte Arbeit bleiben als Run-Historie erhalten. Wird nach einem fehlgeschlagenen Phase-End-Verify mit bereits erledigten Tasks fortgesetzt, zaehlt der Phase-State die `done`-Tasks weiter und laesst die Abschlusspruefung erneut laufen; der integrierte Resume-Pfad muss vom Task-Loop bis zur erneuten Phase-End-Verify und deren Ergebnis belegt sein; `no_successful_tasks` darf nicht allein deshalb ausgeloest werden, weil dieser Versuch keine Tasks neu ausgefuehrt hat; eine scopeveraendernde Neuplanung erfordert vor dem Fortsetzen die passende Freigabe. Strukturell ungueltige, einem anderen Projekt oder einem anderen Run zugeordnete Checkpoints werden verworfen, bevor sie in den Task-Loop gelangen; Legacy-Checkpoints ohne Run-ID bleiben ladbar, sind aber nicht fuer automatische Web-Recovery freigegeben. Ein Fresh-Start ueberschreibt keine vorhandene Recovery-Kopie stillschweigend; aeltere Checkpoints bleiben nummeriert archiviert und Fehler beim Sichern stoppen den Start fail-closed. Ein Stop-Signal persistiert den Checkpoint und stellt ausschliesslich den von diesem Run angelegten User-Stash wieder her. Kann Git den Dirty-Zustand eines erkennbaren Repositories nicht bestimmen oder scheitert das Sichern/Wiederherstellen, startet der Loop nicht weiter bzw. behaelt den Stash zur manuellen Recovery; fremde Stashes werden nie geloescht. Cleanup-Ergebnis und Fehler werden auditiert.
- **Tests:** Startkontext ueber Registry-/Webserver-Reconnect, additiver Registry-Schema-Upgrade und atomarer Duplikatschutz; Job-Lifecycle, parallele Lese- und Diagnosejobs, Event-Replay fuer aktive Runs, Checkpoint-Integration einschliesslich integriertem Resume nach fehlgeschlagenem Phase-End-Verify mit ausschliesslich bereits erledigten Tasks (`tests/test_loop_phases.py`), Replan nur bei relevanter Scope-Aenderung und Erhalt bisheriger Run-Belege; Abbruch und Cleanup bei SIGTERM; Worker-Lease-Verlust beendet alte Worker fail-closed vor weiteren Tool-Aufrufen; nach einem Interpreter-/venv-Wechsel wird ein noch lebender, passend identifizierter Worker fail-closed als mehrdeutig behandelt statt die Writer-Reservierung freizugeben; exakte Stash-Zuordnung, fehlender/neuerer Fremd-Stash, Konflikt-Recovery ohne Drop, Git-Statusfehler im Repo, fehlgeschlagenes Stashen mit fail-closed Start; Planrevision mit Reject/Expiry, Auftragwechsel mit belegter Checkpoint-/Graph-Revision und ungueltige/Legacy-/Fremdprojekt-Checkpoints; wiederholte Fresh-Starts archivieren Recovery-Checkpoints ohne Ueberschreiben, ein fehlgeschlagener Checkpoint-Move bricht fail-closed ab.
- **Blockiert von:** —

### OP-398: Evidenzbasierte Auswahl autonomer Arbeit
- **Status:** open
- **Typ:** loop-autonomy
- **Betroffene Dateien:** STATUS-Parser, OP-Selector, Loop-Start und Tests
- **Akzeptanzkriterien:** Nur eindeutig startbare offene OPs mit aufgeloesten Blockern, Akzeptanzkriterien und Verifikation werden vorgeschlagen. Mehrdeutigkeit oder veralteter Status stoppt den Start und liefert dem Chat Kandidaten samt Gruenden. Ein deterministischer Plan-Compiler prueft Abdeckung der Akzeptanzkriterien, Abhaengigkeiten und Zyklen vor dem Plan-Gate. Der Koordinator waehlt Scout, Architect und bedarfsgesteuerten Spec-First-Pfad nach Auftragsbreite, Unsicherheit und Risiko; einfache Auftraege ueberspringen unnoetige Rollen. Begrenzte OP-Buendel werden vor Ausfuehrung im Plan-Gate einzeln verstaendlich freigegeben. Nach jedem gruenen Schritt prueft der Koordinator die gespeicherten Belege gegen das uebergeordnete Ziel und dessen Akzeptanzkriterien. Gruen allein beendet den Auftrag nicht: erst wenn alle freigegebenen Graph-Aufgaben erledigt, das Ziel belegt erreicht und die abschliessende Verify erfolgreich ist, wird abgeschlossen. Auch ein Scout-No-Op durchlaeuft nach dem Ergebnis-Gate die Phase-End-Verify; die Full-Suite darf in Repo- und Scaffold-Verify-Konfiguration bei leerem Diff nicht durch einen Changed-Files-Guard entfallen. Fehlgeschlagene, blockierte oder offene Tasks koennen nach freigegebener Teilpruefung dokumentiert und gegebenenfalls committed werden, duerfen den Run aber nie als loop_erfolg markieren. Sonst waehlt der Loop selbst den naechsten begruendeten Schritt innerhalb der freigegebenen Grenze. Neue, unabhaengige Funde werden als Folgeauftrag vorgemerkt; unklare oder scopeveraendernde Schritte gehen als gezielte Chat-Rueckfrage zur Freigabe.
- **Tests:** Statusvarianten, Blocker, Ambiguitaet, Auswahlbegruendung und Fail-closed; Task-Plan-Compiler weist duplizierte/fehlende IDs, malformed, unbekannte, doppelte und selbstreferenzierende Abhaengigkeiten sowie Zyklen vor dem Plan-Gate ab; Run-Abschluss mit failed/blocked/pending/running Tasks bleibt trotz gruenem Verify ohne loop_erfolg; Scout-No-Op fuehrt nach dem Human-Gate Phase-End-Verify und Full-Suite aus und bleibt bei rotem Verify ohne loop_erfolg; nach einem gruenen Zwischenschritt wird weitergearbeitet, wenn Zielkriterien offen sind; fehlende explizite Kriterienzuordnung wird am Checkpoint als ungetrackt markiert und nie als Zielerreichung dargestellt; bei belegter Zielerreichung wird sauber abgeschlossen; kein endloses Reflexions-/Folgeauftragswachstum; neuer Fund bleibt vom freigegebenen Scope getrennt; jede Fortsetzungsentscheidung erscheint in Control als kurze Begruendung mit Beleg und naechstem Schritt.
- **Blockiert von:** —

### OP-399: Projekt-Hub fuer GitHub- und lokale Quellen
- **Status:** open
- **Typ:** project-platform
- **Betroffene Dateien:** Projekt-Registry, werkstatt/project_sources.py, werkstatt/loop.py, Web-API, Scaffolder, Projektleiste und Tests
- **Akzeptanzkriterien:** Plus und der werkstattweite Metaorchestrator koennen serverlokale Projekte ueber denselben typisierten, bestaetigungspflichtigen Anlagepfad anlegen. Ein erfolgreicher Greenfield-Aufruf scaffoldet die Dokus, prueft den strukturellen Doku-Vertrag und registriert eine startbare projects/<name>.yaml-Konfiguration; Kollisionen oder ungueltige Pfade ueberschreiben nichts. Ein GitHub-Remote beim Greenfield-Setup oder spaeter verbinden, bestehende GitHub-Repositories registrieren und Projekte oeffnen. Quellen/Refs werden validiert. Der Server ist der primaere Arbeitsort: neue Projekte werden dort angelegt und koennen beim Greenfield-Setup oder spaeter mit GitHub verbunden werden. Vor jedem Run eines verbundenen Projekts ruft der Server den konfigurierten Ref selbst und pinnt dessen Commit-SHA; ein manueller Clone/Pull ist nicht erforderlich. Einen cleanen, nur hinterherhaengenden Branch darf er per Fast-Forward aktualisieren. Lokale Commits, uncommittete Aenderungen und divergierende Branches werden nie ueberschrieben; unsichere Sync-Zustaende werden im Chat erklaert und erfordern eine gezielte Entscheidung. Runs arbeiten in verwalteten isolierten Worktrees auf einem eigenen Run-Branch; die Start-API zeigt Remote-Branch und gepinnte Revision. Initiales Veroeffentlichen sowie spaetere Pushes/Merges brauchen jeweils eine eigene Freigabe. Projekte ohne Remote bleiben lokal.
- **Tests:** URL-/Ref-Validierung, Server-first-Greenfield, initiales Pushen nur nach Freigabe, serverseitiger Fetch und SHA-Pinning, Upstream-/Fast-Forward-Pruefung, Run-Branch, Fetch/Auth/Ref-Fehler, Dirty-/Divergenzschutz, Projekt-/Worktree-Isolation mit externem Run-State, wiederholte Runs ohne projektseitige Ignore-Regel, lokales Projekt ohne Remote sowie Migrationsvorschau und Ablehnung ohne Aenderung.
- **Architektur-Voraussetzung:** ADR-0030
- **Blockiert von:** —

### OP-401: Laufende Sessions ueber neue Chat-Arbeit informieren
- **Status:** open
- **Typ:** task-coordination
- **Betroffene Dateien:** Chatjobs, Event-Store, Loop-Registry, Projekt-Chat und Tests
- **Akzeptanzkriterien:** Jede neue Chat-Anfrage bleibt dem aktiven Projekt und der Session zugeordnet. Reine Fragen laufen parallel gegen einen stabilen Run-/Projekt-Snapshot und unterbrechen den Builder nicht. Das persistierte Hauptziel bleibt bei Zwischenfragen und eingeschobenen Anliegen erhalten; neue Nachrichten werden als Frage/Diagnose, Steuerung, Gate-Antwort, Folgeauftrag im freigegebenen Scope oder separate/scopeveraendernde Schreibarbeit eingeordnet. Unklare Zuordnung wird gezielt erfragt statt still als Ersatzauftrag behandelt. Ein neuer Schreibauftrag wird dauerhaft mit Elternauftrag, aktivem Run/Checkpoint und Basis-Commit aufgenommen; der Chat zeigt knapp, dass er ihn bearbeitet oder einreiht. Der Koordinator bewertet, ob Auftrag, Annahmen oder Dateien den aktiven Run betreffen und sendet ein replaybares Aenderungsereignis. Nicht betroffene Runs arbeiten weiter. Betroffene Runs gleichen Ziel, Freigabe, Akzeptanzkriterien, Inbox, Code-/Doku-Stand und Verify-Belege am naechsten sicheren Checkpoint erneut ab; sie markieren betroffene Arbeit als veraltet und planen dort neu. Ein gruener Teilcheck schliesst den Auftrag nicht ab. Bei unklarer Auswirkung fragt der Chat gezielt nach. Planversionen bleiben intern.
- **Tests:** Frage waehrend aktivem Run, Schreibauftrag waehrend Run, Projekt-/Session-Zuordnung, Hauptziel bleibt nach Zwischenfrage erhalten, Replay nach Reconnect/Neustart, verlorene/duplizierte Ereignisse, disjunkte Aenderung und unklare Scope-Auswirkung, Gruen-Teilcheck bei offenem Gesamtkriterium, erneuter Abgleich von Freigabe/Diff/Doku/Tests nach Patch oder Replan; Chat-Job-Annahme und terminales Ergebnis werden jeweils vor Inbox-Ack stabil auditiert und nach Checkpoint-Retry nicht doppelt projiziert. Der Ergebnisbeleg enthaelt Status und Hash, keinen duplizierten Antworttext.
- **Blockiert von:** OP-396, OP-397

### OP-402: Parallele Schreibauftraege sicher integrieren
- **Status:** open
- **Typ:** worktree-coordination
- **Betroffene Dateien:** Werkstatt-Worktree-Verwaltung, Loop/Verify, Event-Store, Chat-Control und Tests
- **Akzeptanzkriterien:** Jeder freigegebene Schreibauftrag arbeitet in einem eigenen Worktree auf einem festgehaltenen Basis-Commit; zwei Worker schreiben nie in denselben Worktree. Unabhaengige Auftraege duerfen parallel bauen und pruefen. Integration in den gemeinsamen Projektstand ist pro Projekt serialisiert und erfolgt nur an einem sicheren Checkpoint. Diffs werden nur verglichen, wenn sie dieselbe Basis-SHA haben. Bei neuer Basis, ueberschneidenden Pfaden/Abhaengigkeiten oder geaenderten Planannahmen wird die betroffene Arbeit nicht als generischer Verify-Fehler beendet: sie pausiert nachvollziehbar, erstellt einen Integrations-/Replan-Auftrag und fuehrt alle betroffenen Gates auf dem exakten kombinierten Stand erneut aus. Nachweislich disjunkte Aenderungen koennen ohne Rueckfrage integriert werden, wenn die freigegebene Scope-Grenze gleich bleibt. Eine Scope-Erweiterung braucht eine neue, im Chat erklaerte Freigabe.
- **Tests:** Zwei parallele Worktrees gleicher Basis, disjunkte Aenderungen, ueberschneidende Aenderungen, bewegte Basis-SHA, Integrationsserialisierung, Neustart/Reconcile, Gate-Lauf auf kombiniertem Commit und Ablehnung veralteter Freigaben.
- **Blockiert von:** OP-399, OP-401

### OP-400: Provider- und Modellrouting je Projekt und Rolle
- **Status:** open
- **Typ:** model-configuration
- **Betroffene Dateien:** Rollen-/Modellregistry, Projektkonfiguration, Einstellungen und Tests
- **Akzeptanzkriterien:** Projekte koennen je Rolle einen Provider und ein Modell ueberschreiben oder den globalen Default nutzen. Servervalidierung prueft Provider, Verfuegbarkeit und Rollenfaehigkeiten; unpassende Kombinationen werden fail-closed abgewiesen. Secrets bleiben serverseitig und werden nie in UI, Projektdateien oder Logs ausgegeben.
- **Tests:** Defaults, Overrides, Capabilities, Projektisolation und Secret-Redaktion.
- **Architektur-Voraussetzung:** ADR-0030
- **Blockiert von:** —

### OP-280: Doku-Drift als Verify-Gate
- **Status:** open
- **Typ:** verify-fundament
- **Betroffene Dateien:** tools/doku_check.py, Verify-Konfiguration und Tests
- **Akzeptanzkriterien:** Der Check erkennt relevante staged, unstaged und untracked Aenderungen im Working Tree. Code ohne erforderliche Doku wird vor Commit sichtbar blockiert; reine Dokumentations- und Testaenderungen bleiben moeglich. Commit-Historie bleibt Diagnose, kein Ersatz fuer den Working-Tree-Check.
- **Tests:** Staged/unstaged/untracked Faelle und dokumentierte Ausnahmen.
- **Blockiert von:** —

### OP-382: Zehn vollstaendige UI-Runs dogfooding-verifizieren
- **Status:** open
- **Typ:** betrieb
- **Betroffene Dateien:** Chat, Loop-Control, Gate-Bridge, Event-Store und UI
- **Akzeptanzkriterien:** Zehn aufeinanderfolgende OP-Runs werden aus der UI gestartet und mit Chat, Plan-Gate, Status, Ergebnis-Gate, Reconnect und Verify-Beleg dokumentiert. Jeder Nachweis nennt Projekt, OP, Run-ID und Ergebnis. Fehler werden behoben oder als konkreter Blocker festgehalten; keine stillen Abbrueche.
- **Tests:** Betriebsprotokoll mit Run-IDs und Quality-Gate-Belegen.
- **Blockiert von:** OP-396, OP-397

### OP-240: Debugger-Handoff an den normalen Loop
- **Status:** open
- **Typ:** debugger
- **Betroffene Dateien:** werkstatt/debugger_handoff.py, Chat-API und Tests
- **Akzeptanzkriterien:** Debug-Diagnosen referenzieren einen belegten Run-/Gate-Fehler desselben Projekts. Eine Freigabe bindet sich an Basis-HEAD und Diff-Hash und uebergibt genau diesen Patch als Auftrag an den normalen Loop. Diagnose oder Vorschlag schreibt selbst keinen Code und umgeht kein Gate.
- **Tests:** Patch-Hash, Projekt-/Run-Isolation, Einmaligkeit und Ablehnung.
- **Blockiert von:** OP-396

### OP-374: Backfill reproduzierbar und letzte Runs korrekt anzeigen
- **Status:** open
- **Typ:** data-integrity
  - **Betroffene Dateien:** werkstatt/projection.py, werkstatt/web/inspector.py, static/overview.js, static/layout.css und Tests
- **Akzeptanzkriterien:** Letzte Runs ignorieren Events ohne Run-ID. Backfills sind als wiederholbarer, idempotenter Projektvorgang verfuegbar. Historische Events ohne belastbare Herkunft werden getrennt ausgewiesen und nicht als verifizierter Erfolg gezaehlt.
- **Tests:** Leere Run-IDs, Backfill-Wiederholung und Projektisolation.
- **Blockiert von:** —

### OP-375: Erfolgsquote und Fehlerklassen in der Uebersicht
- **Status:** open
- **Typ:** ui-analytics
- **Betroffene Dateien:** werkstatt/web/inspector.py, static/overview.js und Tests
- **Akzeptanzkriterien:** Projekt- und Gesamtwerte zeigen erfolgreiche, fehlgeschlagene und abgebrochene Runs getrennt. Fehlerklassen sind normalisiert und auf belegte Events zurueckfuehrbar. Leere Daten oder partielle Historie werden ehrlich als unvollstaendig dargestellt.
- **Tests:** Aggregation, Fehlerklassen, Nullwerte und UI-Rendering.
- **Blockiert von:** OP-374

### OP-394: Live-Feed semantisch und stabil sortieren
- **Status:** open
- **Typ:** observability
- **Betroffene Dateien:** werkstatt/web/inspector.py, static/live_feed.js und Tests
- **Akzeptanzkriterien:** Die Control-Timeline zeigt fuer jeden Arbeitsschritt lesbaren Namen, Zeit, Projekt/Run, Phase oder Task, Status sowie Ergebnis und Beleg. Entscheidungsschritte enthalten eine kurze, belegbasierte Begruendung und den naechsten Schritt. Der Feed verraet keine rohen internen Gedankengaenge. JSONL- und SQLite-Kopien derselben Event-ID erscheinen nur einmal. Projektfilter, Replay und chronologische Reihenfolge bleiben korrekt.
- **Tests:** Deduplizierung, projektisolierte JSONL-Timeline/Swimlane/Aktivitaet auch bei expliziter Run-ID und Run-ID-Kollisionen, Sortierung, Entscheidungsschritt mit Beleg/naechstem Schritt, Replay und sichere Zusammenfassung ohne Rohgedanken; Task-Erfolg nur nach realem `done`-Uebergang mit stabiler Task-ID und Phase-State-Beleg.
- **Blockiert von:** OP-395, OP-397

### OP-395: Builder-Fortschritt waehrend Modellaufrufen zeigen
- **Status:** open
- **Typ:** observability
- **Betroffene Dateien:** Builder, Chat-/Live-Feed-UI und Tests
- **Akzeptanzkriterien:** Waehrend langer Builder-Aufrufe erscheinen Fortschritt und Stillstands-Heartbeat mit Task-/Dateikontext. Im Chat steht nur eine temporaere, menschlich formulierte Aktivitaetszeile, die knapp beschreibt, woran der Assistent gerade arbeitet; sie wird beim Schrittwechsel ersetzt und verschwindet nach Abschluss. Die vollstaendige Schrittfolge mit Status, Belegen, Ergebnissen, kurzer Entscheidungszusammenfassung und naechstem Schritt bleibt ausschliesslich als detaillierte Control-Timeline erhalten. Der Chat bleibt waehrenddessen fuer Fragen und neue Auftraege ansprechbar. Ereignisse blockieren keine Chat-Requests und werden nach Reconnect ohne doppelte Runs replayt. Sichtbare Begruendungen sind kurze Zusammenfassungen mit Belegen, keine rohen internen Gedankengaenge.
- **Tests:** Eventfolge, Heartbeat-Fallback, Ergebnis-/Belegreferenz, Fortsetzungsentscheidung, Replay, Chatfrage waehrend Build, einzelne temporaere Chat-Aktivitaetszeile statt Spinner/Statusblasen, Ersatz beim Schrittwechsel, Entfernung bei Abschluss, detaillierte Control-Timeline und keine Ausgabe interner Rohgedanken.

### OP-308: Cockpit-Timeline fuer abgeschlossene Runs
- **Status:** open
- **Typ:** ui-feature
- **Betroffene Dateien:** Cockpit-Timeline, Event-Projektion und UI-Tests
- **Akzeptanzkriterien:** Cockpit zeigt fuer einen ausgewaehlten Run Phasenreihenfolge, Status und Dauer aus belegten Events. Die Auswahl einer Phase zeigt ihre Detailereignisse. Control behaelt den chronologischen Live-Feed; der Chat bleibt fest im Projektkontext.
- **Tests:** Reihenfolge, Dauer, fehlende Zeitstempel und Trennung Cockpit/Control.
- **Blockiert von:** —

## Sub-OPs

Keine separat startbaren Sub-OPs. Zerlegung erfolgt projektbezogen im Plan-Gate.

## Erledigt (Auto-Log)

Abgeschlossene OPs werden append-only in PROGRESS.md dokumentiert.

## Delete-Zone

| Pfad | Warum entfernt | Ersetzt durch | Wiedereinfuehrung |
|---|---|---|---|
| `pipeline.py` | Alte Einstiegsschicht entfernt | `werkstatt/loop.py` | Nur bei angenommener Architekturentscheidung |
| `docs/WORKFLOW.md` | Inhalt wurde nicht eigenstaendig gepflegt | `AGENTS.md` und `docs/DOC_CONVENTIONS.md` | Nicht vorgesehen |
| `werkstatt/control/reflection.py` | Unnoetige doppelte Implementierung entfernt | `werkstatt/reflection.py` | Nicht vorgesehen |
| `docs/SOLL.md` | Spekulatives Zielbild widersprach akzeptierter Chat-/Gate-Architektur | Akzeptierte ADRs, `docs/ROADMAP.md` und `docs/ARCHITECTURE.md`; historische Fassung in `docs/archiv/soll-zielbild-2026-11-08.md` | Nur nach Annahme der betroffenen ADRs |

