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
ausgefuehrt. Vor jeder schreibenden Chat-Aktion zeigt das System die
konkrete Aktion und ihren Umfang und wartet auf ausdrueckliche
Freigabe. Diese Freigabe gilt nur fuer genau diese Aktion und ersetzt
weder Loop-Gates noch weitere Freigaben fuer neue Schreibaktionen.
Schreibende Code-Arbeit laeuft durch denselben Patch-, Verify-,
Review- und Human-Gate-Pfad wie ein normaler Loop-Lauf. Das Plan-Gate
ist immer verpflichtend: kein CLI-Schalter und keine Projektoption
duerfen es ueberspringen. Start, Pause, Resume und Stop sind explizite
Kontrollaktionen. Gates und menschliche Entscheidungen werden nie aus
Chat-Prosa abgeleitet oder automatisch bestaetigt.

### 3. Hintergrundarbeit bleibt asynchron und sichtbar

Ein langer Run oder Diagnoseauftrag darf die Chat-Verbindung nicht
blockieren. Chat-Dialog und Loop-Prozess bleiben unabhaengig. Der Chat
kann waehrend eines Runs neue Fragen beantworten; lange Pruefungen
laufen als nachvollziehbare Jobs und melden Fortschritt als Events.

**Parallelitaetsvertrag fuer Read-Jobs derselben Session:** Ein langsamer
LLM-Turn darf eine spaeter eingereichte Lesefrage nicht in eine
Session-FIFO-Warteschlange zwingen. Jeder Read-Job arbeitet mit einem
unveraenderlichen Snapshot der bis zur Annahme abgeschlossenen Turns und
einem eigenen Transcript-Zweig. User-Turn, Tool-Calls, Tool-Ergebnisse und
Antwort bleiben an die stabile Job-ID gebunden; Worker schreiben waehrend
der Generierung nicht in denselben Transcript. Erfolgreiche Turns werden
idempotent als zusammengehoeriges User-/Assistant-Paar in die Eltern-Session
uebernommen. Fehler, Abbruch und unvollstaendige Tool-Traces werden nicht in
den Prompt anderer Jobs gemischt. Antworten duerfen in anderer Reihenfolge
fertig werden und bleiben in der UI ihrer ausloesenden Nachricht zugeordnet.
Ein neuer Job wartet nicht auf vorherige langsame Inferenz, sieht aber nur
die abgeschlossenen Turns seines beim Annehmen festgehaltenen Snapshots.

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
Er kann eng verwandte OPs zu einem gemeinsamen, begrenzten Arbeitsziel
buendeln, wenn Reihenfolge, Abhaengigkeiten, Umfang und Verifikation
klar bleiben. Er waehlt anhand expliziter Prioritaet, des aktuellen
Nutzerziels, nachgewiesener Auswirkung, Risiko und erwarteter
Verifikation und schreibt Begruendung sowie Zielgrenzen ins Run-Audit.

Ein direkt vom Menschen ausgewaehltes OP oder ein konkreter Chat-Auftrag
hat Vorrang vor autonomer Auswahl. Der zusammengefasste Plan samt OP-Liste,
Reihenfolge und Abbruchgrenzen wird vor Schreibarbeit im verpflichtenden
Plan-Gate menschlich freigegeben. Bei Gleichstand, widerspruechlichen
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

## 6. Zielorientierter Run statt OP-Zeilenlauf

Ein Run besitzt ein explizites Ziel und kann aus einer ausgewaehlten
STATUS-OP, einem konkreten Chat-Auftrag oder einer freigegebenen Gruppe
abhaengiger OPs entstehen. Eine angeklickte OP bleibt dabei eine
bewusste Begrenzung: der Selector darf sie nicht still durch eine andere
Arbeit ersetzen.

Der Orchestrator ist primaer deterministisch. Er loest den Auftrag in
Kandidaten und Abhaengigkeiten auf, bildet nur dann einen gemeinsamen
Arbeitsblock, wenn Akzeptanzkriterien und Grenzen zusammenpassen, und
legt Ziel, OP-Liste, Reihenfolge, Verify-Plan, Budget und Stop-Regeln
im Plan-Gate vor. Nach Freigabe arbeitet der Loop diese genehmigte
Einheit selbststaendig ab: Diagnose, begrenzte Reparatur-/Reflection-
Runden, Verify und Review. Fehler werden als Befunde weitergereicht;
der Loop repariert sie innerhalb des genehmigten Umfangs und stoppt bei
Budget-, Risiko- oder Mehrdeutigkeitsgrenzen.

Das Ergebnis ist ein Run-Bericht mit erledigten und offenen Teilzielen,
aufgetretenen Fehlern samt Ursache, vorgenommenen Reparaturen,
Verify-/Review-Belegen und Commit. STATUS wird erst anhand dieser
Belege fortgeschrieben. Ein groesseres autonomes Batch ist ein
ausdruecklich gewaehlter Modus mit klarer Obergrenze, kein unendliches
Weiterarbeiten nach einem OP.

Bei Code-Arbeit enthaelt der freigegebene Plan getrennte Code- und
Test-Specs. Der Test-Builder qualifiziert die Tests am unveraenderten
Stand und friert sie ein; der Code-Builder erhaelt keine Einsicht in
die Testdateien. Danach prueft Verify die Aenderungen gegen diese Tests
und die konfigurierten Qualitaets-Gates. Eine Reflection-Reparatur
invalidiert oder umgeht den Test-Freeze nicht; nach jeder Reparatur
laufen die betroffenen Pruefungen erneut. Diese Test-Loop-/Freeze-
Kette ist Zielzustand aus OP-210/211 und im aktuellen Loop noch nicht
vollstaendig gebaut.

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
- Jede schreibende Chat-Aktion verlangt eine konkrete, vorherige
  Zustimmung; pauschale Zustimmung fuer spaetere Aktionen gibt es nicht.
- Planfreigabe bleibt auch bei automatisierten Skript-Runs verpflichtend;
  headless bedeutet nur, dass die menschliche Antwort ueber den Gate-Store
  statt stdin eingeht. Der isolierte Testmodus ist die einzige Ausnahme fuer
  automatisierte Testlaeufe.
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
- Tests beweisen, dass auch der Scout-No-Op-Pfad das Plan-Gate nicht ueberspringt, Chat keinen Human-Gate-Entscheid automatisiert,
  keine schreibende Chat-Aktion ohne vorherige Zustimmung ausfuehrt,
  das Plan-Gate weder durch CLI noch Projektkonfiguration umgangen wird
  und Code-Aenderungen weiterhin durch Verify/Review laufen.
