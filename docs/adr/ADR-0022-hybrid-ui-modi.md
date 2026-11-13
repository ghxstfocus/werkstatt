# ADR-0022: Chat-zentrierte Projektoberflaeche und Arbeitsmodi

- **Datum:** 2026-11-13
- **Status:** accepted
- **Ersetzt:** die urspruengliche ADR-0022 sowie die Layout- und Modusentscheidungen aus ADR-0009 und ADR-0022a
- **Produktspezifikation:** [Freigegebener UI-Plan](../UI-PLAN-2026-11-12.md)
- **Abgrenzung:** ADR-0029 definiert Chat-Aktionen und Freigaben; ADR-0032 definiert Run-, Event-, Inbox- und Checkpoint-Vertraege; ADR-0031 definiert den werkstattweiten Metaorchestrator.

## Kontext

Die Werkstatt ist eine Multi-Projekt-Entwicklungsumgebung. Der Chat ist
Ansprechpartner und primaerer Steuerungsort fuer Fragen, Auftraege, Runs,
Freigaben und Ergebnisse. Die UI muss waehrenddessen die technische Arbeit
erklaerbar machen, ohne Chat, Gate, Run und Timeline zu getrennten
Wahrheiten zu machen.

Der am 2026-11-12 freigegebene UI-Plan beschreibt die konkrete
Produktspezifikation. Diese ADR legt die dauerhaften Architektur- und
Interaktionsregeln fest. Sie behauptet nicht, dass die Zieloberflaeche
bereits vollstaendig umgesetzt ist.

## Entscheidung

### 1. Informationshierarchie

Die Projektoberflaeche hat eine feste, responsive Struktur:

1. **Projektleiste:** Home/Uebersicht, offene Projekttabs und Plus-Menue.
   Das Plus-Menue bietet Projektanlage, GitHub-Verbindung/Registrierung
   und das Oeffnen eines vorhandenen lokalen Projekts.
2. **Modusleiste direkt darunter:** Cockpit, Control, Debug und Runs.
3. **Projektstatus:** kompakte Anzeige von Laufzustand, offenem Gate und
   letztem Run des aktiven Projekts.
4. **Arbeitsflaeche:** Chat bleibt im Projekt dauerhaft sichtbar und
   bedienbar. Eine kontextuelle Arbeitsansicht ergaenzt ihn, ersetzt ihn
   aber nicht als Steuerungsweg.
5. **Detailleiste:** Audit, Loop-Log, Diff, Verify und Dateien bleiben
   erreichbar und auf Projekt sowie gegebenenfalls Run gefiltert.

Ohne geoeffnetes Projekt ist die Projektuebersicht die Default-Ansicht.
Sie zeigt registrierte Projekte, belegte Laufzustaende, Zeitraeume und
Datenaktualitaet, Run-Ergebnisse sowie Aktionen zum Oeffnen oder Anlegen.
Der spaetere Metaorchestrator sitzt auf dieser Uebersicht. Er verwendet
dieselben Projekt- und Run-Belege und hebt weder Projektisolation noch
Human-Gates auf.

Die Moduswahl aendert Schwerpunkt und Detailgrad, nicht aktives Projekt,
Chat-Session, Run oder Gate. Projekt-, Tab- und Sessionwechsel duerfen
Nachrichten, Aktionen, Events und Freigaben nicht vermischen.

### 2. Vier Modi, eine Quelle der Wahrheit

Chat, Modi und Detailleiste lesen dieselbe persistierte Run-/Event-Projektion.
Sie duerfen Informationen unterschiedlich darstellen, aber keinen eigenen
widersprechenden Prozess-, Gate- oder Chat-Zustand fuehren.

| Ansicht | Leitfrage | Inhalt |
|---|---|---|
| **Cockpit** | Wo stehen Ziel und Projekt? | Ziel und Akzeptanzkriterien, belegter Gesamtfortschritt, offene Risiken und Gates, Run-Ergebnisse sowie verdichteter langsamer Verlauf. |
| **Control** | Was tut der Run gerade und was folgt? | Vollstaendige chronologische Live-Timeline mit Akteur/Faehigkeit, Zweck, Task/Pfad, Status, Ergebnis/Beleg und naechstem Schritt. Die Reihenfolge bleibt sichtbar. |
| **Debug** | Was ist fehlgeschlagen und wie wird es behoben? | Failure Record, Stage/Exit-Code, Commit- und Worktree-Fingerprint, Log-/Artefaktverweise, betroffene Kriterien, Reparaturversuche und erneute Verify in Ursache-Wirkungs-Reihenfolge. |
| **Runs** | Was lief in einem oder mehreren Projekten? | Filterbare Run-Historie, Status, Gate-Verlauf und Replay. Werkstattweite Schreibsteuerung bleibt bis zu den Aktivierungskriterien aus ADR-0031 gesperrt. |

Cockpit und Control sind keine konkurrierenden Timelines: Cockpit verdichtet
den Verlauf zur Orientierung und Nachanalyse; Control bewahrt dessen
chronologische Detailspur. Debug verbindet Fehler und Reparatur mit den
konkreten Belegen.

### 3. Chat und Nachrichtenlayout

- Nutzernachrichten stehen rechtsbuendig in kompakten Bubbles mit begrenzter
  Maximalbreite. Sie wachsen mit dem Text, nehmen aber nicht die gesamte
  Chatbreite ein.
- Assistentenantworten stehen linksbuendig in einer ruhig lesbaren,
  begrenzten Textspalte. Lange Zeilen werden umgebrochen; Code und Tabellen
  duerfen das Layout nicht horizontal aufziehen.
- Der Composer bleibt am unteren Rand erreichbar, ist mehrzeilig und
  tastaturbedienbar. Enter sendet, Shift+Enter erzeugt einen Zeilenumbruch.
  Fokuszustand und Screenreader-Beschriftung sind eindeutig.
- Die Chat-Historie bleibt bei Moduswechsel erhalten. Neue Antworten werden
  der ausloesenden Nachricht und Session zugeordnet; parallele Read-Jobs
  duerfen in anderer Reihenfolge fertig werden.
- Antworten auf Repo-, Status- und Run-Fragen nennen verfuegbare Belege wie
  Datei/Fundstelle, Event, Kommando, Ergebnis und Zeitpunkt. Ohne Beleg wird
  die Unsicherheit benannt; Aktivitaet wird nicht erfunden.

Bei laengerer Arbeit zeigt der Chat hoechstens eine temporaere,
menschlich formulierte Aktivitaetszeile fuer den aktuellen Chat-Auftrag.
Sie wird beim Schrittwechsel ersetzt und nach Abschluss entfernt.
Detaillierte Agenten-/Loop-Schritte stehen in Control. Der Chat zeigt keine
Spinnerfolge und keine internen Rohgedanken, sondern kurze erklaerende
Zusammenfassungen.

Prozessstart, Aufgabenannahme, Ausfuehrung, Ablehnung, Abschluss und Fehler
sind getrennte Zustaende und werden entsprechend dargestellt. Ein gestarteter
Prozess ist kein Beleg fuer angenommene oder abgeschlossene Arbeit.

### 4. Timeline und Evidenz

Control ist die vollstaendige, gespeicherte und replaybare Arbeitsspur.
Ein Ereignis enthaelt, soweit zutreffend:

- Zeit, Projekt- und Run-Bezug;
- Akteur oder Faehigkeit sowie den konkreten Arbeitsschritt;
- kurzen Zweck und betroffenen Task, Pfad oder Akzeptanzpunkt;
- Status und Ergebnis;
- Beleg-, Log- oder Artefaktverweis;
- naechsten Schritt oder den Grund fuer eine Pause.

Cockpit verdichtet dieselben Ereignisse. Debug ordnet Fehler, Diagnose,
Reparatur und Verify kausal. Reconnect rekonstruiert denselben Zustand
idempotent aus persistierten Run-/Event-Daten. DOM-Heuristiken und
unpersistierte UI-Schattenzustaende sind keine Statusquelle.

Sichtbare Erklaerungen sind kurze, evidenzgebundene Zusammenfassungen und
keine Wiedergabe interner Gedankengaenge.

### 5. Gates im Chat

Plan-, Rueckfrage- und Ergebnisfreigaben erscheinen als Karten im passenden
Projekt- und Sessionverlauf. Eine Karte zeigt die konkrete Handlung, den
Umfang, betroffene Dateien oder Kriterien, Empfehlung, Risiko und eindeutige
Optionen. Eine stabile Gate-ID bindet Antwort, Status und Audit idempotent
an genau diese Freigabe.

Ein Modal darf dieselbe Karte als Detailansicht oeffnen, ist aber weder ein
separater Gate-Zustand noch ein eigener Antwortkanal. Offene und
abgeschlossene Karten werden nach Reconnect ohne Duplikate rekonstruiert.
Abgelaufene, veraltete, mehrdeutige oder bereits beantwortete Gates loesen
keine Aktion aus. Aendert sich der freigegebene Umfang, gilt die
Freigabesemantik aus ADR-0029.

### 6. Codeguardian

Der Codeguardian ist eine Schutz- und Evidenzfaehigkeit, kein schreibender
Builder. Befunde erscheinen im Chat, wenn eine Entscheidung oder Handlung
noetig ist; Control zeigt Regel, Grund, Status und Beleg; Debug verknuepft
Schweregrad, Pfad/Zeile, Regelversion, Diff-Fingerprint und Verify-Ergebnis.
Der Guardian erstellt keinen eigenen Patch, umgeht keine Gates und
ueberschreibt keine harten Pruefungen. Sicherheits- und Scope-Verletzungen
bleiben bis zur belegten Aufloesung blockierend.

### 7. Responsive Bedienbarkeit und Browserpruefung

Alle Ansichten muessen auf schmalen Viewports nutzbar bleiben. Tastatur,
Fokusindikatoren, Screenreader-Namen, ausreichender Kontrast und reduzierte
Bewegung gehoeren zur Abnahme. Browserpruefungen laufen mit isolierten
Testdaten; Screenshots, DOM-/Accessibility-Befunde und Browser-Logs werden
als Verify-Artefakte gespeichert.

## Abnahme

Die UI ist erst nachgewiesen, wenn:

1. Chat, Cockpit, Control, Debug und Runs denselben Run nach Replay
   widerspruchsfrei darstellen.
2. Projekt-, Tab- und Sessionwechsel Nachrichten, Gates und Events strikt
   isolieren.
3. Gate-Entscheidungen genau einmal in Chat und Audit erscheinen und nach
   Reconnect korrekt rekonstruiert werden.
4. Fragen waehrend eines Runs beantwortbar bleiben und Aktivitaet nur aus
   realen Events stammt.
5. Ein Verify-Fehler an den exakten Commit-/Worktree-Stand gebunden ist und
   Failure Record, Reparatur und erneute Pruefung zusammenhaengen.
6. Responsive Bedienbarkeit und Browserpruefung Abschnitt 7 erfuellen.
7. Zehn vollstaendige UI-Runs Start, Frage waehrend Arbeit, Gate,
   Pause/Resume, Reconnect, Verify-Fehler-Recovery und Abschluss mit
   Projekt, OP, Run-ID und Belegen nachweisen.

Das sind Zielbedingungen, kein Umsetzungsnachweis. Offene Umsetzung bleibt
in `docs/STATUS.md`, bis Tests und Betriebsbelege die Kriterien erfuellen.

## Abloesung und Folgen

Diese ADR ersetzt die fruehere Timeline-primaer-Anordnung und die
eigenstaendige Modus-/Wasserfallentscheidung aus ADR-0009 und ADR-0022a.
Eine primaere Timeline mit Chat als Nebenpanel, ein eigener Gate-
Antwortkanal und unterschiedliche Statusquellen pro Modus sind keine
gueltigen Bauvorgaben mehr.

Die fachliche Trennung aus ADR-0022a bleibt gueltig: Control zeigt eine
sequenzielle Live-Chronologie, Cockpit den verdichteten Verlauf.
ADR-0029 bleibt fuer Chat-Aktionen und Freigaben massgeblich; ADR-0031 fuer
den Metaorchestrator; ADR-0032 fuer Run-, Event-, Inbox- und
Checkpoint-Vertraege.

Konsequenzen:

- Der Chat ist in jedem Projektmodus sichtbar und der primaere
  Handlungsort.
- Moduswechsel veraendern die Perspektive, nicht den Run oder dessen
  Quelle der Wahrheit.
- Relevante UI- und Gate-Aktionen muessen als gespeicherte, replaybare
  Ereignisse erscheinen.
- UI-Arbeit wird auf den Run-/Event-Vertraegen aus ADR-0032 aufgebaut.
  Visueller Feinschliff darf Chat-, Control- und Gate-Vertraege nicht
  abschwaechen.
