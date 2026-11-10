# ADR-0029: Chat-zentrierter Projekt-Control-Plane und autonome Arbeit

- **Datum:** 2026-11-10
- **Status:** accepted
- **Ersetzt teilweise:** ADR-0008 (read-only Chat), ADR-0009 (Timeline primaer)
- **Ergaenzt:** ADR-0006 (Event-Store), ADR-0007 (Gate-Bridge),
  ADR-0022 (UI-Modi), ADR-0024 (Event-Log)
- **Grundlage fuer:** OP-396, OP-397, OP-398

## Kontext

Der Chat ist heute ein separates Diagnose-Panel mit read-only Tools.
Der Mensch muss Loop-Arbeit anderweitig starten und kann waehrend eines
langen Chat-Tools nicht fluessig weiterfragen. Gleichzeitig sind
Timeline, Live-Feed und Cockpit-Summary getrennte Ansichten. Der Mensch
muss selbst aus Logs und Statusdateien ableiten, was das System macht,
was als naechstes ansteht und ob eine Antwort belegt ist.

Das Ziel ist eine intuitive Entwicklungsumgebung, die sich wie ein
kompetenter technischer Partner verhaelt: Sie untersucht das aktuelle
Projekt bei Fragen, startet passende Hintergrundarbeit, erklaert jeden
Schritt und bleibt waehrend eines laufenden Runs ansprechbar.

## Entscheidung

### 1. Chat ist die zentrale Projekt-Oberflaeche

Der Chat ist in allen Modi der primaere Ort, um Aufgaben zu formulieren,
Fragen zu stellen, Runs zu steuern und Ergebnisse zu verstehen. Er
arbeitet immer im aktiven Projektkontext. Antworten auf Code-,
Test-, Status- und Laufzeitfragen muessen passende Repo-/Run-Belege
verwenden: Datei und Zeile, ausgefuehrter Befehl, Ergebnis und
Zeitpunkt. Fehlt ein Beleg, sagt das System, was es noch prueft oder
welche Information fehlt.

Die UI-Modi geben dem Chat verschiedene, miteinander verknuepfte
Arbeitsflaechen:

| Modus | Primaere Zusatzansicht |
|---|---|
| Cockpit | Zusammenfassung des Runs und langsamere, verdichtete Timeline |
| Control | Live-Feed mit aktuellem Schritt, Ereignissen und naechstem Schritt |
| Debug | spaeter: Fehler, Artefakte, Event-Replay und Ursache-Wirkung |

Der Chat bleibt in allen Modi sichtbar und bedienbar. Der Debug-Modus
wird erst dann als fertig behandelt, wenn er konkrete Run-Belege
erklaert und zu den verantwortlichen Aktionen navigieren kann.

### 2. Chat koordiniert; spezialisierte Rollen fuehren aus

Die Trennung von Chat-Agent und Coding-Loop als getrennte
Verantwortlichkeiten bleibt bestehen. Der Chat darf projektbezogene
Lesewerkzeuge selbst einsetzen und gezielte Jobs an den Loop oder
Diagnose-Worker delegieren. Er ersetzt weder Builder, Verify, Reviewer
noch die vorhandene Kontrollschicht.

Werkzeuge sind projektgebunden, capability-basiert, validiert und
auditiert. Kein frei formulierter Shell-Befehl wird aus Chat-Text
ausgefuehrt. Schreibende Code-Arbeit laeuft durch denselben Patch-,
Verify-, Review- und Human-Gate-Pfad wie ein normaler Loop-Lauf.
Start, Pause, Resume und Stop sind explizite Kontrollaktionen. Gates
und menschliche Entscheidungen werden nie aus Chat-Prosa abgeleitet
oder automatisch bestaetigt.

### 3. Hintergrundarbeit bleibt asynchron und sichtbar

Ein langer Run oder Diagnoseauftrag darf die Chat-Verbindung nicht
blockieren. Chat-Dialog und Loop-Prozess bleiben unabhaengig. Der Chat
kann waehrend eines Runs neue Fragen beantworten; lange Pruefungen
laufen als nachvollziehbare Jobs und melden Fortschritt als Events.

Jedes Event ist mit Projekt, Run, Job und ausloesender Chat-Session
verknuepft, soweit zutreffend. Fortschritt, Ergebnis, Fehler und
Abbruch werden dauerhaft gespeichert und nach Reconnect rekonstruiert.
Doppelte Start-Kommandos muessen idempotent sein; pro Projekt gilt eine
explizite Schreib-/Run-Konkurrenzregel, damit zwei Builder nicht
denselben Working Tree veraendern.

### 4. STATUS ist Backlog und Absicht, kein blinder Zeilen-Runner

`docs/STATUS.md` bleibt die menschenlesbare Quelle genehmigter
Arbeitspakete. Zeilenreihenfolge allein ist keine Auswahlstrategie.
Der Selector ermittelt zunaechst Kandidaten, die offen, nicht erledigt,
nicht blockiert und mit Abhaengigkeiten/Projektgrenzen vereinbar sind.
Er waehlt anhand expliziter Prioritaet, des aktuellen Nutzerziels,
nachgewiesener Auswirkung, Risiko und erwarteter Verifikation und
schreibt eine kurze Auswahlbegruendung ins Run-Audit.

Ein direkt vom Menschen ausgewaehltes OP oder ein konkreter Chat-Auftrag
hat Vorrang vor autonomer Auswahl. Bei Gleichstand, widerspruechlichen
Statusangaben, hohem Risiko oder fehlender Akzeptanzinformation fragt
das System nach. Es darf keine OP aus ROADMAP-Text erfinden oder
deren Abschluss allein aus LLM-Einschaetzung ableiten.

### 5. Autonomie endet an Evidenz- und Risikogrenzen

Der Loop darf selbststaendig Kontext sammeln, kleine Aufgaben zerlegen,
Tests und statische Checks ausfuehren, begrenzte Korrekturschleifen
durchlaufen und nach erfolgreicher Verifikation den naechsten
freigegebenen Arbeitsschritt waehlen. Er muss pro Schritt Zweck,
Fortschritt, Belege und Ergebnis offenlegen.

Jeder Lauf hat ein Ziel, Akzeptanzkriterien, Zeit-/Versuchsbudget,
Checkpoints und eine Abbruchbedingung. Der Loop stoppt und erklaert
Blocker, wenn Evidenz fehlt, Pruefungen widersprechen, der Fortschritt
stagniert oder eine Entscheidung menschliche Praeferenz erfordert.
Status wird erst mit Verifikation und dokumentiertem Ergebnis
fortgeschrieben.

## Konsequenzen

- Der Chat wird zur Bedien- und Erklaerungsschicht, nicht zu einem
  zweiten, unkontrollierten Coding-Agenten.
- Cockpit und Control zeigen denselben Lauf mit unterschiedlicher
  zeitlicher Aufloesung; Debug liefert spaeter kausale Evidenz.
- STATUS bleibt lesbar und editierbar; Auswahl und Fortschritt werden
  als maschinenpruefbare Fakten ergaenzt statt durch eine zweite
  widerspruechliche Queue ersetzt.
- Bestehende read-only Tools bleiben als sichere Grundmenge. Neue
  Kontrollwerkzeuge erhalten enge Schemas, Idempotenz, Audit und Tests.
- Die heutige Aussage im Web-Start-Endpunkt, ohne Aufgabe werde die
  naechste STATUS-OP gelesen, muss gegen tatsaechlichen Code verifiziert
  und entweder implementiert oder korrigiert werden.

## Verifikation

- Chat kann waehrend eines aktiven Loop-Runs eine weitere Frage
  beantworten und Repo-Belege liefern.
- Lange Diagnosejobs bleiben nach UI-Reconnect sichtbar und blockieren
  weder Chat noch Loop.
- Selector ueberspringt blockierte/erledigte OPs, begruendet seine Wahl
  und fragt bei Mehrdeutigkeit.
- Wiederholte Start-Requests erzeugen keinen zweiten Schreib-Run.
- Tests beweisen, dass Chat keinen Human-Gate-Entscheid automatisiert
  und Code-Aenderungen weiterhin durch Verify/Review laufen.
