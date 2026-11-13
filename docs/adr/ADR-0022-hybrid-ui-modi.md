# ADR-0022: Chat-zentrierte Projektoberflaeche

- **Datum:** 2026-11-13
- **Status:** accepted
- **Ersetzt:** die fruehere ADR-0022 sowie die Layout- und Modusentscheidungen aus ADR-0009 und ADR-0022a
- **Produktspezifikation:** [Freigegebener UI-Plan](../UI-PLAN-2026-11-12.md)
- **Ergaenzt:** ADR-0029 (Chat-Aktionen und Freigaben), ADR-0031 (Metaorchestrator), ADR-0032 (Run-, Event- und Checkpoint-Vertraege)

## Kontext

Die Werkstatt ist eine Multi-Projekt-Entwicklungsumgebung. Der Projektchat
ist Ansprechpartner und primaerer Ort fuer Fragen, Arbeitsauftraege,
Run-Steuerung, Freigaben und Ergebnisse. Die UI muss technische Arbeit
erklaerbar und pruefbar machen, ohne fuer Chat, Gate, Run und Timeline
getrennte Wahrheiten zu erzeugen.

Der freigegebene UI-Plan definiert Produktdetails und Lieferumfang. Diese
ADR legt nur die stabilen Architektur- und Interaktionsentscheidungen fest.
Sie ist kein Implementierungsnachweis.

## Entscheidung

### 1. Projekt-Shell und Hierarchie

Die Projektansicht ordnet die Bereiche verbindlich so:

1. **Projektleiste:** Uebersicht, geoeffnete Projekte und ein Plus-Menue zum
   Anlegen, Verbinden oder Oeffnen eines Projekts.
2. **Modusleiste:** direkt darunter Cockpit, Control, Debug und Runs.
3. **Projektstatus:** kompakter, belegter Laufzustand, offene Freigaben und
   letzter Run des aktiven Projekts.
4. **Arbeitsflaeche:** Chat und eine zum Modus passende Zusatzansicht.
5. **Detailleiste:** Audit, Loop-Log, Diff, Verify und Dateien, gefiltert nach
   Projekt und bei Bedarf Run.

Ohne aktives Projekt ist die Projektuebersicht die Default-Ansicht. Sie
aggregiert registrierte Projekte und deren belegte Kennzahlen. Der spaetere
Metaorchestrator sitzt auf dieser Uebersicht; seine Befugnisse und
Aktivierungsvoraussetzungen stehen in ADR-0031.

Projektwechsel isolieren Sessions, Aktionen, Gates, Runs und Events.
Ein Moduswechsel aendert nur die Perspektive, nicht Projekt, Session oder
Laufzustand.

### 2. Eine Quelle der Wahrheit, mehrere Sichten

Chat, Cockpit, Control, Debug und Runs projizieren denselben persistenten
Projekt-/Run-/Event-Zustand gemaess ADR-0024 und ADR-0032. Sie duerfen
unterschiedliche Detailgrade zeigen, aber keine voneinander abweichenden
Status-, Gate- oder Laufzustaende verwalten. Nicht persistierte DOM- oder
Frontend-Schattenzustaende sind keine Statusquelle. Reconnect muss denselben
Zustand idempotent rekonstruieren.

| Ansicht | Zweck | Verbindlicher Schwerpunkt |
|---|---|---|
| **Cockpit** | Orientierung und Verlauf | Ziel, Kriterien, belegter Fortschritt, Risiken, Gates, Run-Ergebnisse und verdichtete Timeline |
| **Control** | Laufende Arbeit verstehen | Chronologische Live-Ereignisse mit Akteur, Schritt, Zweck, Status, Beleg und naechstem Schritt |
| **Debug** | Fehler nachvollziehen | Fehler, Diagnose, betroffene Kriterien, Reparaturversuche und erneute Verify kausal verknuepfen |
| **Runs** | Laeufe vergleichen und wiedergeben | Projekt-/Run-Historie, Ergebnis, Gates und Replay |

Cockpit verdichtet Ereignisse; Control bewahrt ihre zeitliche Detailfolge;
Debug ordnet sie nach Ursache und Wirkung. Keine dieser Ansichten ersetzt
den Chat als Handlungsort.

### 3. Chat als Interaktionsflaeche

Der Chat bleibt in jedem Projektmodus sichtbar und bedienbar. Er zeigt
Nutzernachrichten rechts als kompakte, in der Breite begrenzte Bubbles und
Assistentenantworten links in einer gut lesbaren Textspalte. Der Composer
bleibt erreichbar, mehrzeilig und tastaturbedienbar.

Fragen zu Code, Status und Runs werden mit verfuegbaren Datei-, Zeilen-,
Event-, Kommando- oder Verify-Belegen beantwortet. Fehlende Evidenz wird
benannt. Prozessstart, Aufgabenannahme und erfolgreicher Abschluss sind
getrennte Zustaende.

Bei laengerer Arbeit zeigt der Chat hoechstens eine temporaere, menschlich
formulierte Statuszeile zum aktuellen Chat-Auftrag. Sie wird beim
Schrittwechsel ersetzt und nach Abschluss entfernt. Detaillierte
Loop-Schritte gehoeren in Control. Die UI zeigt kurze, belegte
Erklaerungen, keine internen Gedankengaenge.

Aktionen, Planfreigaben und Human-Gates folgen ausschliesslich ADR-0029.
Diese ADR legt keine zweite Aktions- oder Gate-Logik fest.

### 4. Ereignis- und Gate-Darstellung

Jedes Control-Ereignis wird aus gespeicherten Run-Daten aufgebaut und
enthaelt, soweit zutreffend: Projekt und Run, Zeitpunkt, Akteur/Faehigkeit,
Arbeitsschritt, Zweck, Task/Pfad/Kriterium, Status, Ergebnis/Beleg und
naechsten Schritt oder Pausengrund. Cockpit und Debug verwenden dieselben
Ereignisse fuer Verdichtung beziehungsweise Fehlerzusammenhang.

Gate-Karten erscheinen im ausloesenden Projektchat und in der passenden
Session. Eine stabile Gate-ID bindet Karte, Antwort, Status und Audit an
dieselbe Freigabe. Modal oder Banner duerfen die Karte zusaetzlich
darstellen, sind aber kein eigener Gate-Zustand und kein separater
Antwortkanal. Abgelaufene, mehrdeutige, veraltete oder bereits beantwortete
Gates loesen keine Aktion aus. Exakte Freigaberegeln bleiben ADR-0029
vorbehalten.

Codeguardian-Befunde verwenden denselben Run-/Event-Bezug: Chat zeigt
Handlungsbedarf, Control den Befund mit Regel und Evidenz, Debug den
Ursache-Wirkungs-Verlauf. Der Codeguardian schreibt keine eigenen Patches
und umgeht keine Verify- oder Human-Gates.

### 5. Bedienbarkeit und Verifikation

Alle Ansichten muessen responsiv und per Tastatur bedienbar sein,
eindeutige Fokus- und Screenreader-Zustaende besitzen, ausreichenden
Kontrast bieten und reduzierte Bewegung respektieren. UI-Aenderungen werden
mit isolierten Testdaten im Browser geprueft. Screenshots, DOM-/
Accessibility-Befunde und Browser-Logs sind Verify-Artefakte, keine
informellen Sichtpruefungen.

## Umsetzung und Abnahme

Die UI baut auf den Run-, Event-, Replay-, Job- und Gate-Vertraegen aus
ADR-0032 und ADR-0029 auf. Danach folgen Projekt-Shell und Chat, Gate- und
Kontrollaktionen, die vier konsistenten Sichten und die Browserabnahme.
Der freigegebene UI-Plan beschreibt die Lieferdetails; STATUS.md fuehrt die
startbaren Arbeitspakete. Diese Reihenfolge erzeugt keine zusaetzliche
Runtime-Phasenlogik.

Die Architektur gilt erst als umgesetzt, wenn:

1. alle vier Sichten nach Replay denselben Run-Zustand widerspruchsfrei
   darstellen;
2. Projekt-, Tab- und Sessionwechsel keine Nachrichten, Aktionen, Gates
   oder Events vermischen;
3. Gate-Entscheidungen genau einmal im Chat und Audit erscheinen und nach
   Reconnect korrekt rekonstruiert werden;
4. Fragen waehrend eines Runs beantwortbar bleiben und angezeigte Aktivitaet
   aus realen Events stammt;
5. Fehler, Reparatur und erneute Verify an denselben Commit-/Worktree-Stand
   gebunden sind;
6. responsive, Tastatur- und Accessibility-Pruefungen sowie die
   Browserabnahme bestanden sind.

Diese Kriterien beschreiben Zielbedingungen. Sie bescheinigen keinen
Implementierungsstand. Der Betriebsnachweis mit zehn vollstaendigen
UI-Runs wird in STATUS.md/OP-382 gefuehrt.

## Abloesung und Folgen

Die fruehere Timeline-primaer-Anordnung aus ADR-0009 und die eigenstaendige
Wasserfall-/Modusentscheidung aus ADR-0022a sind keine Bauvorgaben mehr.
Ihre fachliche Trennung bleibt erhalten: Control ist chronologisch,
Cockpit verdichtet den Verlauf. ADR-0029 bleibt massgeblich fuer
Chat-Aktionen und Freigaben; ADR-0031 fuer den Metaorchestrator; ADR-0032
fuer Run-, Event-, Inbox- und Checkpoint-Vertraege.

Daraus folgen:

- Der Chat ist der primaere Handlungsort; Zusatzansichten liefern Kontext
  und Belege.
- Moduswechsel aendern Darstellung, niemals Berechtigungen oder Laufzustand.
- Status und Gate-Zustaende muessen aus persistenten, replaybaren Daten
  stammen.
- Der UI-Plan und STATUS.md bleiben die Quellen fuer Produktspezifikation
  beziehungsweise offene Umsetzung.
