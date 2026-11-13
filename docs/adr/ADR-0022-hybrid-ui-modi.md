# ADR-0022: Chat-zentrierte Projektoberflaeche und Arbeitsmodi

- **Datum:** 2026-11-13
- **Status:** accepted
- **Ersetzt:** Die urspruengliche ADR-0022 sowie die Layout- und Modusentscheidungen aus ADR-0009 und ADR-0022a.
- **Bestaetigt durch:** Freigegebener UI-Plan in `docs/UI-PLAN-2026-11-12.md`
- **Zusammenarbeit:** ADR-0029 definiert Chat-Steuerung und Freigaben; ADR-0031 den werkstattweiten Metaorchestrator; ADR-0032 den Run-Kern.

## Kontext

Die frueheren UI-Entscheidungen entstanden aus einer phasenorientierten
Workbench: Timeline zuerst, Chat als schmales Nebenpanel und mehrere
abweichende Layouts. Das passt nicht mehr zum Produktziel. Der Nutzer soll
mit dem Chat wie mit einem technischen Ansprechpartner arbeiten koennen:
Fragen stellen, den Projektstand pruefen lassen, Auftraege erteilen, Runs
steuern und Freigaben erteilen. Die Arbeit muss dabei nachvollziehbar bleiben,
ohne Chat, Run, Gate und Timeline als getrennte Systeme zu behandeln.

Der am 2026-11-12 freigegebene UI-Plan ist die konkrete Produktspezifikation.
Diese ADR legt dessen dauerhafte Architekturregeln fest. Sie beschreibt das
Ziel und ist kein Nachweis, dass die UI bereits vollstaendig umgesetzt ist.

## Entscheidung

### 1. Eine Projektoberflaeche mit Chat als Steuerung

Die Informationshierarchie ist verbindlich:

1. **Projektleiste:** Home/Uebersicht, geoeffnete Projekt-Tabs und Plus-Menue
   fuer Projekt anlegen, GitHub-Projekt verbinden oder ein lokales Projekt
   oeffnen.
2. **Modusleiste darunter:** Cockpit, Control, Debug und Runs. Ohne aktives
   Projekt ist die Werkstatt-Uebersicht die Default-Ansicht.
3. **Projektstatus:** kompakte, aus Run-Ereignissen abgeleitete Anzeige von
   Laufzustand, offenem Gate und letztem Run.
4. **Arbeitsflaeche:** Der Projektchat bleibt der primaere Handlungsort und in
   jedem Projektmodus sichtbar. Die jeweilige Modusansicht gibt dem Chat
   Kontext; sie ersetzt weder Eingabe noch Steuerung.
5. **Detailleiste:** Audit, Loop-Log, Diff, Verify und Dateien bleiben
   projekt- und run-gefiltert erreichbar.

Der Chat ist projektgebunden, dauerhaft bedienbar und nicht als schwebendes
Overlay umgesetzt. Eine Moduswahl aendert Fokus und Detailgrad, nicht den
aktiven Projekt-/Run-Kontext. Projekt- oder Sessionwechsel vermischen keine
Nachrichten, Aktionen, Ereignisse oder Gates.

### 2. Vier Modi, ein Zustand

Alle Modi lesen dieselbe persistierte Run-/Event-Projektion. Sie duerfen
denselben Sachverhalt unterschiedlich verdichten, aber keine eigenen
widersprechenden Prozess-, Gate- oder Chat-Zustaende halten.

| Modus | Leitfrage | Verantwortung |
|---|---|---|
| **Cockpit** | Wo stehen Ziel und Projekt? | Ziel und Akzeptanzkriterien, belegter Gesamtfortschritt, offene Risiken/Gates, Run-Ergebnisse und langsamere, verdichtete Verlaufssicht. Historische Swimlane-/Wasserfallansichten gehoeren hierher. |
| **Control** | Was passiert gerade und was folgt? | Live-Feed in chronologischer Reihenfolge mit Akteur/Faehigkeit, Zweck, Task oder Pfad, Status, Ergebnis/Beleg und naechstem Schritt. Keine Aggregation, die die Reihenfolge verschleiert. |
| **Debug** | Was ist fehlgeschlagen und wie wird es behoben? | Failure Record, Stage/Exit-Code, Commit- und Worktree-Fingerprint, Log-/Artefaktverweise, betroffene Kriterien, Reparaturversuche und Verify-Ergebnis in Ursache-Wirkungs-Reihenfolge. |
| **Runs** | Was lief in einem oder mehreren Projekten? | Filterbare Run-Historie, Status, Gate-Verlauf und Replay. Werkstattweite Steuerung bleibt bis zu ihren Freigabekriterien deaktiviert. |

Die Projektuebersicht zeigt registrierte Projekte, belegte Laufzustaende,
Run-Statistiken mit Zeitraum und Datenqualitaet, Aktualitaet sowie Aktionen
zum Oeffnen und Anlegen. Der spaetere Metaorchestrator sitzt auf dieser
Uebersicht und koordiniert Projekte ueber deren isolierte Projektloops. Er
nutzt dieselben Projekt-/Run-Belege, fuehrt keinen zweiten Statusspeicher und
hebt weder Projektisolation noch Human-Gates auf.

### 3. Chat- und Eingabevertrag

- Nutzernachrichten erscheinen rechtsbuendig in einer kompakten Bubble.
  Assistentenantworten stehen links in einer begrenzten Lesespalte mit
  ruhiger, gut lesbarer Markdown-Formatierung.
- Die mehrzeilige Eingabe bleibt am unteren Rand erreichbar. Enter sendet,
  Shift+Enter fuegt eine Zeile ein; Fokus, Tastaturbedienung und
  Screenreader-Namen sind sichtbar und korrekt.
- Bei laengerer Arbeit zeigt der Chat maximal eine temporaere, menschlich
  formulierte Aktivitaetszeile. Sie wird beim Schrittwechsel ersetzt und
  nach Abschluss entfernt. Detaillierte Ereignisse gehoeren in Control,
  nicht als Spinner oder Folge von Statusblasen in den Chat.
- Chatfragen waehrend eines Runs koennen parallel beantwortet werden und
  blockieren die schreibende Arbeit nicht. Neue Schreibauftraege werden dem
  Projekt und der Session zugeordnet und am sicheren Checkpoint disponiert.
- Antworten auf Repo-, Status- und Run-Fragen nennen verfuegbare Belege
  (Datei/Fundstelle, Event, Kommando, Ergebnis und Zeitpunkt). Ohne Beleg
  wird die Unsicherheit genannt; Aktivitaet wird nicht erfunden.
- Prozessstart gilt nicht als Aufgabenannahme oder erfolgreicher Run. Die UI
  zeigt Annahme, Ausfuehrung, Ablehnung, Abschluss und Fehler getrennt.

### 4. Timeline- und Evidenzvertrag

Control ist die technische, replaybare Arbeitsspur. Jeder Schritt soll
soweit zutreffend Zeit, Projekt/Run, Akteur oder Faehigkeit, Zweck,
Task/Pfad, Status, Ergebnis, Artefakt-/Belegreferenz und naechsten Schritt
tragen. Aktive Arbeit muss anhand realer Events sichtbar sein; ein Spinner
oder eine Prozessliste allein ist kein Fortschrittsbeleg.

Cockpit verdichtet denselben Verlauf fuer Orientierung und Nachanalyse.
Debug verbindet Fehler und Reparatur kausal. Keine Ansicht gibt rohe interne
Gedankengaenge aus: sichtbare Begruendungen sind kurze Zusammenfassungen mit
Belegen. Reconnect rekonstruiert dieselben Fakten idempotent aus gespeichertem
Zustand; DOM-Heuristiken und getrennte UI-Schattenzustaende sind keine
Statusquelle.

### 5. Gates gehoeren in den Projektchat

Plan-, Rueckfrage- und Ergebnisfreigaben erscheinen als Nachrichten/Karten
im passenden Projekt- und Sessionverlauf. Eine Gate-ID bindet Antwort,
Status und Audit idempotent an genau eine Freigabe. Eine Karte zeigt
Handlung, Umfang, betroffene Dateien oder Kriterien, Empfehlung, Risiko und
klare Optionen. Ein Modal darf dieselbe Karte als Detailansicht darstellen,
ist aber weder eigener Gate-Zustand noch separater Antwortkanal.

Reconnect stellt offene und abgeschlossene Gate-Karten ohne Duplikate wieder
her. Veraltete, abgelaufene, mehrdeutige oder bereits beantwortete Gates
koennen keine Aktion ausloesen. Scope-aendernde Aenderungen entwerten die
betroffene Freigabe und benoetigen eine neue Entscheidung gemaess ADR-0029.

### 6. Codeguardian in denselben Ablauf einordnen

Codeguardian ist eine Schutz- und Evidenzfaehigkeit, kein zweiter Builder.
Seine Befunde erscheinen nur dann im Chat, wenn eine Entscheidung oder
Handlung noetig ist; Control zeigt Regel, Grund, Status und Beleg; Debug
verknuepft Schweregrad, Pfad/Zeile, Regelversion, Diff-Fingerprint und
Verify-Ergebnis. Der Guardian schreibt keinen eigenen Patch und kann weder
Gates umgehen noch harte Pruefungen ueberschreiben. Sicherheits- und
Scope-Verletzungen bleiben bis zur belegten Aufloesung blockierend.

### 7. Bedienbarkeit und Browserpruefung

Alle Modi muessen auf schmalen Viewports nutzbar bleiben. Tastaturbedienung,
Fokusindikatoren, Screenreader-Namen, Kontrast und reduzierte Bewegung sind
Teil der Abnahme. Browserpruefungen verwenden isolierte Testdaten und
speichern DOM-/Accessibility-Befunde, Screenshots und Browser-Logs als
Verify-Artefakte.

## Abnahmekriterien

Die UI gilt erst als nachgewiesen, wenn:

1. Chat, Cockpit, Control, Debug und Runs widerspruchsfrei dieselben
   Run-Fakten aus Replay darstellen.
2. Projekt-, Tab- und Sessionwechsel Daten strikt isolieren.
3. Jede Gate-Entscheidung genau einmal in Chat und Audit erscheint und nach
   Reconnect korrekt weitergefuehrt wird.
4. Chatfragen waehrend eines Runs beantwortbar bleiben und Aktivitaet nur
   aus Run-Events stammt.
5. Ein Verify-Fehler an den exakten Commit-/Worktree-Stand gebunden ist und
   Failure Record, Reparatur und erneute Pruefung verbunden bleiben.
6. Bedienbarkeit und Browserpruefung die Anforderungen aus Abschnitt 7
   erfuellen.
7. Zehn vollstaendige UI-Runs Start, Frage waehrend Arbeit, Gate,
   Pause/Resume, Reconnect, Verify-Fehler-Recovery und Abschluss mit
   Projekt, OP, Run-ID und Belegen nachweisen.

Diese Abnahmekriterien sind Zielbedingungen. Offene Umsetzungs- und
Betriebsarbeit bleibt in `docs/STATUS.md` offen, bis Kriterien und Belege
erfuellt sind.

## Abloesung frueherer UI-Entscheidungen

Diese ADR ersetzt die frueheren Layout- und Modusfestlegungen aus ADR-0009
und ADR-0022a. Insbesondere gelten nicht mehr: Timeline als primaere
Arbeitsflaeche mit Chat als Nebenpanel, getrennte Modi mit abweichenden
Layouts, ein phasenbezogener Wasserfall in Control oder ein eigener Gate-
Antwortkanal ausserhalb des Chats.

Die fachliche Erkenntnis aus ADR-0022a bleibt gueltig: Control braucht eine
sequenzielle Live-Chronologie; Cockpit eignet sich fuer verdichtete
Nachanalyse. ADR-0029 bleibt fuer Chat-Aktionen und Freigabesemantik
massgeblich, ADR-0031 fuer den spaeteren Metaorchestrator und ADR-0032 fuer
Run-, Event-, Inbox- und Checkpoint-Vertraege.

## Konsequenzen

- Die UI ist dauerhaft projekt- und chat-zentriert; Modi aendern
  Schwerpunkt und Detailgrad, nicht die Quelle der Wahrheit.
- Jede Laufzeit- oder Gate-Aktion muss als gespeichertes, replaybares Ereignis
  sichtbar sein.
- Der Chat kann waehrend laengerer Arbeit ansprechbar bleiben, waehrend
  Control die technische Arbeitsspur bewahrt.
- Die Umsetzung baut auf den stabilen Run-, Event-, Inbox- und
  Checkpoint-Vertraegen aus ADR-0032 auf.
- Visueller Feinschliff ohne Einfluss auf diese Vertraege folgt nach der
  Loop-Stabilisierung; er darf den Control- und Gate-Vertrag nicht
  verwischen.
