# Status — Werkstatt

Format gemaess `DOC_CONVENTIONS.md` §5. Diese Queue enthaelt nur offene, konkret loop-faehige Arbeit aus dem aktuellen Produktfokus. Historische, optionale und noch nicht angenommene Architekturideen stehen nicht als startbare OPs hier.

`—` bedeutet: vor dem Start konkretisieren. Der Arbeitsfokus steht in `docs/ROADMAP.md`; abgeschlossene oder verworfene Arbeit steht in `PROGRESS.md`.

Letzte Aktualisierung: 2026-11-11.

## Offene Punkte

### OP-396: Chat als projektbezogene Hauptoberflaeche
- **Status:** open
- **Typ:** ui-orchestration
- **Betroffene Dateien:** Chat/Web-UI, Chat- und Loop-Control-Tests
- **Akzeptanzkriterien:** Repo-Fragen liefern Datei-/Zeilen- oder Testbelege. Der Chat erstellt fuer direkte Auftraege und OPs einen versionierten, begruendeten Plan samt Empfehlung und uebergibt genau diesen ohne Copy/Paste an den Loop. Das Plan-Gate erscheint im Chat; Freigabe ist an Projekt und Planversion gebunden, Ablehnung/Aenderung erzeugt eine neue Version, Mehrdeutigkeit fragt nach. Die freigegebene Version autorisiert Code, Tests, Doku, Verify und lokalen Commit nur innerhalb ihres Umfangs; externe/destruktive Aktionen erhalten ein separates Gate. Kontrollaktionen bleiben explizit; Ergebnis-Gate und Reconnect sind abgesichert.
- **Tests:** Plan-Version und Loop-Handoff, Empfehlungsbelege, Freigabe/Ablehnung/Revision, mehrdeutige Antworten, Projektisolation, Kontrollaktionen, Reconnect und parallele Fragen waehrend eines Runs.
- **Blockiert von:** —

### OP-397: Hintergrundjobs und Checkpoint-Steuerung
- **Status:** open
- **Typ:** async-jobs
- **Betroffene Dateien:** Chatjobs, Event-Store, Loop-Registry, Web-API, `werkstatt/phases/plan.py` und Tests
- **Akzeptanzkriterien:** Lange Lese-/Verify-Aufgaben laufen mit stabiler Job-ID unabhaengig von Chat-Requests und sind nach Reconnect replaybar. Idempotenz, Abbruch, Projektisolation und maximal ein schreibender Run pro Projekt sind abgesichert. Plan-Aenderungen pausieren am sicheren Checkpoint und brauchen eine neue Planfreigabe. Ein Auftragswechsel verwirft den alten PhaseState; erst nach Freigabe wird der neue Checkpoint mit den neuen Tasks geschrieben. Strukturell ungueltige oder einem anderen Projekt zugeordnete Checkpoints werden verworfen, bevor sie in den Task-Loop gelangen. Ein Stop-Signal persistiert den Checkpoint und stellt ausschliesslich den von diesem Run angelegten User-Stash wieder her. Scheitert das Sichern oder Wiederherstellen, startet der Loop nicht weiter bzw. behaelt den Stash zur manuellen Recovery; fremde Stashes werden nie geloescht. Cleanup-Ergebnis und Fehler werden auditiert.
- **Tests:** Job-Lifecycle, Parallelitaet, Replay, Abbruch und Cleanup bei SIGTERM; exakte Stash-Zuordnung, fehlender/neuerer Fremd-Stash, Konflikt-Recovery ohne Drop, fehlgeschlagenes Stashen mit fail-closed Start; Planrevision mit Reject/Expiry, Auftragwechsel mit Checkpoint-Ersetzung und ungueltige/Legacy-/Fremdprojekt-Checkpoints.
- **Blockiert von:** —

### OP-398: Evidenzbasierte Auswahl autonomer Arbeit
- **Status:** open
- **Typ:** loop-autonomy
- **Betroffene Dateien:** STATUS-Parser, OP-Selector, Loop-Start und Tests
- **Akzeptanzkriterien:** Nur eindeutig startbare offene OPs mit aufgeloesten Blockern, Akzeptanzkriterien und Verifikation werden vorgeschlagen. Mehrdeutigkeit oder veralteter Status stoppt den Start und liefert dem Chat Kandidaten samt Gruenden. Begrenzte OP-Buendel werden vor Ausfuehrung im Plan-Gate einzeln verstaendlich freigegeben.
- **Tests:** Statusvarianten, Blocker, Ambiguitaet, Auswahlbegruendung und Fail-closed.
- **Blockiert von:** —

### OP-399: Projekt-Hub fuer GitHub- und lokale Quellen
- **Status:** open
- **Typ:** project-platform
- **Betroffene Dateien:** Projekt-Registry, Quellenadapter, Scaffolder, Projektleiste und Tests
- **Akzeptanzkriterien:** Plus kann serverlokale Projekte anlegen, ein GitHub-Remote beim Greenfield-Setup oder spaeter verbinden, bestehende GitHub-Repositories registrieren und Projekte oeffnen. Quellen/Refs werden validiert. Der Server ist der primaere Arbeitsort: neue Projekte werden dort angelegt und koennen beim Greenfield-Setup oder spaeter mit GitHub verbunden werden. Vor jedem Run eines verbundenen Projekts ruft der Server den konfigurierten Ref selbst und pinnt dessen Commit-SHA; ein manueller Clone/Pull ist nicht erforderlich. Einen cleanen, nur hinterherhaengenden Branch darf er per Fast-Forward aktualisieren. Lokale Commits, uncommittete Aenderungen und divergierende Branches werden nie ueberschrieben; unsichere Sync-Zustaende werden im Chat erklaert und erfordern eine gezielte Entscheidung. Runs arbeiten in verwalteten isolierten Worktrees. Initiales Veroeffentlichen sowie spaetere Pushes/Merges brauchen jeweils eine eigene Freigabe. Projekte ohne Remote bleiben lokal.
- **Tests:** URL-/Ref-Validierung, Server-first-Greenfield, initiales Pushen nur nach Freigabe, serverseitiger Fetch und SHA-Pinning, Fast-Forward-Update, Fetch/Auth/Ref-Fehler, Dirty-/Divergenzschutz, Projekt-/Worktree-Isolation, lokales Projekt ohne Remote sowie Migrationsvorschau und Ablehnung ohne Aenderung.
- **Architektur-Voraussetzung:** ADR-0030
- **Blockiert von:** —

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

### OP-385: Scout-Auftrag als Hauptzweck und Architect-Kontext
- **Status:** open
- **Typ:** loop-quality
- **Betroffene Dateien:** werkstatt/scout.py, werkstatt/planner.py und Tests
- **Akzeptanzkriterien:** Repo-Fakten werden zuerst gezielt gelesen; der Scout-LLM-Aufruf laeuft nur bei breiten, mehrdeutigen oder evidenzbeduerftigen Auftraegen. Architect liefert einen strukturierten Plan, den deterministische Validierung in Tasks ueberfuehrt; ein zweiter LLM-Task-Split ist nur ein begrenzter Fallback. Kontext enthaelt Belege statt redundanter Explorer-Ausgaben. Fehlende/widerspruechliche Belege fuehren zur Rueckfrage. LLM-Aufrufe und Tokens werden je Rolle gemessen; Representative Regressionsevaluation schuetzt die Qualitaet.
- **Tests:** Kleine/einfache und breite/mehrdeutige Auftraege, strukturierter Plan/Compiler, Scout-Bedingung, Fallback und Token-/Qualitaetsvergleich.
- **Blockiert von:** —

### OP-386: Reflection auf Fehlerbelege begrenzen
- **Status:** open
- **Typ:** loop-quality
- **Betroffene Dateien:** werkstatt/reflection.py und Tests
- **Akzeptanzkriterien:** Reflection erhaelt den relevanten Diff und aktuelle Verify-/Reviewer-Befunde statt redundanter Patchkopien. Jeder Folgeversuch benennt, welcher Befund adressiert wird. Tests sichern Kontextgrenzen und Regressionen ab.
- **Tests:** Prompt-Kontext fuer Verify- und Reviewer-Fehler.
- **Blockiert von:** —

### OP-384: Rollenbezogene Kontextbudgets
- **Status:** open
- **Typ:** loop-quality
- **Betroffene Dateien:** werkstatt/model_routing.py, Prompt-Builders und Tests
- **Akzeptanzkriterien:** Jede Rolle hat ein dokumentiertes Kontextbudget mit deterministischer Begrenzung. Wichtige Auftrags-, ADR- und Fehlerbelege werden vor optionalem Kontext erhalten. Ueberschreitungen werden sichtbar protokolliert und nicht still abgeschnitten.
- **Tests:** Budgetgrenzen und Priorisierung je Rolle.
- **Blockiert von:** OP-385

### OP-387: JIT-Retrieval fuer Architect
- **Status:** open
- **Typ:** loop-quality
- **Betroffene Dateien:** werkstatt/planner.py, Repo-Tools und Tests
- **Akzeptanzkriterien:** Architect kann bei belegtem Bedarf gezielt Symbole/Dateien nachladen, statt unbeschraenkte Repo-Kontexte zu erhalten. Retrieval ist projektgebunden, read-only und begrenzt; Ergebnisse werden mit Pfad und Fundstelle in den Plan-Kontext aufgenommen.
- **Tests:** Tool-Berechtigung, Projektgrenze, Treffer und leere/mehrdeutige Suche.
- **Blockiert von:** OP-384, OP-385

### OP-388: Kontextbudget im Verify absichern
- **Status:** open
- **Typ:** verify-fundament
- **Betroffene Dateien:** Verify-Konfiguration und Prompt-/Routing-Tests
- **Akzeptanzkriterien:** Verify prueft die konfigurierten Rollenkontextbudgets deterministisch. Eine Regression, die unbegrenzten oder falschen Rollenkontext wieder einfuehrt, blockiert den Commit. Fehlermeldungen nennen Rolle, Limit und gemessenen Wert.
- **Tests:** Regressionen bei Budget, Rolle und Prompt-Aufbau.
- **Blockiert von:** OP-384

### OP-324: Planner-Qualitaet strukturell pruefen
- **Status:** open
- **Typ:** loop-quality
- **Betroffene Dateien:** werkstatt/planner.py und Planner-Tests
- **Akzeptanzkriterien:** Plan-Tasks decken Auftrag und Akzeptanzkriterien nachvollziehbar ab. Datei-/Task-Abhaengigkeiten sind explizit und zyklusfrei. Unvollstaendige Plaene werden vor dem Plan-Gate mit konkreten Luecken gezeigt.
- **Tests:** AK-Abdeckung, Abhaengigkeitsgraph und unvollstaendige Plaene.
- **Blockiert von:** —

### OP-240: Debugger-Handoff an den normalen Loop
- **Status:** open
- **Typ:** debugger
- **Betroffene Dateien:** werkstatt/debugger_handoff.py, Chat-API und Tests
- **Akzeptanzkriterien:** Debug-Diagnosen referenzieren einen belegten Run-/Gate-Fehler desselben Projekts. Eine Freigabe bindet sich an Basis-HEAD und Diff-Hash und uebergibt genau diesen Patch als Auftrag an den normalen Loop. Diagnose oder Vorschlag schreibt selbst keinen Code und umgeht kein Gate.
- **Tests:** Patch-Hash, Projekt-/Run-Isolation, Einmaligkeit und Ablehnung.
- **Blockiert von:** OP-396

### OP-372: Projection-Status semantisch vergleichen
- **Status:** open
- **Typ:** data-integrity
- **Betroffene Dateien:** werkstatt/projection.py, UI-Status und Tests
- **Akzeptanzkriterien:** JSONL- und SQLite-Zaehler werden nur fuer denselben Zeitraum und dieselbe Basis verglichen. API und UI zeigen Vergleichsbasis und Zeitraum, damit historische Migrationen keine falsche Driftmeldung erzeugen. Rebuild und wiederholte Projektion bleiben idempotent.
- **Tests:** Migrationsanker, Event-Deduplizierung und UI-Anzeige.
- **Blockiert von:** —

### OP-374: Backfill reproduzierbar und letzte Runs korrekt anzeigen
- **Status:** open
- **Typ:** data-integrity
- **Betroffene Dateien:** werkstatt/projection.py, werkstatt/web/inspector.py und Tests
- **Akzeptanzkriterien:** Letzte Runs ignorieren Events ohne Run-ID. Backfills sind als wiederholbarer, idempotenter Projektvorgang verfuegbar. Historische Events ohne belastbare Herkunft werden getrennt ausgewiesen und nicht als verifizierter Erfolg gezaehlt.
- **Tests:** Leere Run-IDs, Backfill-Wiederholung und Projektisolation.
- **Blockiert von:** —

### OP-375: Erfolgsquote und Fehlerklassen in der Uebersicht
- **Status:** open
- **Typ:** ui-analytics
- **Betroffene Dateien:** werkstatt/web/inspector.py, static/overview.js und Tests
- **Akzeptanzkriterien:** Projekt- und Gesamtwerte zeigen erfolgreiche, fehlgeschlagene und abgebrochene Runs getrennt. Fehlerklassen sind normalisiert und auf belegte Events zurueckfuehrbar. Leere Daten oder partielle Historie werden ehrlich als unvollstaendig dargestellt.
- **Tests:** Aggregation, Fehlerklassen, Nullwerte und UI-Rendering.
- **Blockiert von:** OP-372, OP-374

### OP-394: Live-Feed semantisch und stabil sortieren
- **Status:** open
- **Typ:** observability
- **Betroffene Dateien:** werkstatt/web/inspector.py, static/live_feed.js und Tests
- **Akzeptanzkriterien:** Der Live-Feed zeigt lesbare Eventnamen, Zeit und Run-Kontext. JSONL- und SQLite-Kopien derselben Event-ID erscheinen nur einmal. Projektfilter und chronologische Reihenfolge bleiben korrekt.
- **Tests:** Deduplizierung, Projektisolation und Sortierung.
- **Blockiert von:** —

### OP-395: Builder-Fortschritt waehrend Modellaufrufen zeigen
- **Status:** open
- **Typ:** observability
- **Betroffene Dateien:** Builder, Chat-/Live-Feed-UI und Tests
- **Akzeptanzkriterien:** Waehrend langer Builder-Aufrufe erscheinen Fortschritt und Stillstands-Heartbeat mit Task-/Dateikontext. Fortschrittsereignisse blockieren keine Chatfragen und werden nach Reconnect nicht als doppelte Runs dargestellt.
- **Tests:** Eventfolge, Heartbeat-Fallback und Replay.
- **Blockiert von:** OP-397

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
