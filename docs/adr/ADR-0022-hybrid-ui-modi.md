# ADR-0022: Projektzentrierte Chat- und Arbeitsmodi

- **Datum:** 2026-11-13
- **Status:** accepted
- **Ersetzt:** Die urspruengliche ADR-0022 vom 2026-11-08 mit drei eigenstaendigen Layouts, schwebendem Chat und phasenbezogenem Wasserfall.
- **Bestaetigt durch:** Freigegebener UI-Plan vom 2026-11-12 in `docs/UI-PLAN-2026-11-12.md`
- **Ergaenzt:** ADR-0009, ADR-0022a, ADR-0029, ADR-0031 und ADR-0032

## Kontext

Die bisherige Modusentscheidung beschreibt drei getrennte Layouts und einen
schwebenden Chat. Das passt nicht mehr zum Produktziel: Der Projektchat ist
der Ansprechpartner und Steuerungspunkt, waehrend Cockpit, Control und Debug
unterschiedliche Sichten auf denselben Run und dieselben Belege liefern.
Ein schwebendes Panel, getrennte Statuszustaende oder ein Gate ausserhalb des
Chatverlaufs lassen Aktionen und Entscheidungen auseinanderfallen.

Die UI soll zugleich eine Entwicklungsumgebung bleiben: Projekte muessen
schnell erreichbar sein, laufende Arbeit soll im Control-Modus nachvollziehbar
sein, und Fehler brauchen in Debug einen belastbaren Ursache-Wirkungs-Kontext.

## Entscheidung

### 1. Gemeinsame Informationsarchitektur

Die Anwendung hat diese Reihenfolge:

1. **Projektleiste:** Startseite/Uebersicht, geoeffnete Projekt-Tabs und ein
   Plus-Menue fuer Projekt anlegen, GitHub-Projekt verbinden sowie bestehendes
   lokales Projekt oeffnen.
2. **Modusleiste darunter:** Cockpit, Control, Debug und Runs. Ohne aktives
   Projekt ist die Projektuebersicht die Standardansicht.
3. **Projektstatus:** kompakte Anzeige von belegtem Laufzustand, offenem Gate
   und letztem Run.
4. **Arbeitsflaeche:** projektbezogener Chat als primaerer Handlungsort; die
   jeweilige Modusansicht ergaenzt den Chat um passenden Kontext.
5. **Detailleiste:** Audit, Loop-Log, Diff, Verify und Dateien, jeweils nach
   Projekt und Run gefiltert.

Der Chat bleibt im Projektkontext verankert und wird nicht als unabhaengiges
schwebendes Steuerungsfenster umgesetzt. Der Projektwechsel darf keine
Nachrichten, Ereignisse oder Gates zwischen Projekten vermischen.

### 2. Vier Modi, eine Run-Projektion

| Modus | Beantwortet | Zeigt |
|---|---|---|
| **Cockpit** | Wo stehen Ziel und Projekt? | Ziel und Akzeptanzkriterien, belegten Fortschritt, letzte Runs, offene Gates und Risiken sowie Statistiken mit Zeitraum und Datenqualitaet. |
| **Control** | Was tut der Run gerade und was folgt? | Chronologische Ereignisse mit Akteur/Faehigkeit, kurzer Zweckbeschreibung, Task/Pfad, Status, Beleg oder Artefakt und naechstem Schritt. |
| **Debug** | Was ist fehlgeschlagen und wie wird es behoben? | Failure Record, Stage und Exit-Code, Commit-/Worktree-Fingerprint, Logauszug, betroffene Kriterien, Reparaturversuche und Verify-Ergebnis in Ursache-Wirkungs-Reihenfolge. |
| **Runs** | Was lief im Projekt oder in der Werkstatt? | Filterbare Run-Historie, Laufzustand, Ergebnis, Gate-Verlauf und Replay. Werkstattweite Metaansichten bleiben read-only, bis ihre Aktivierungskriterien belegt sind. |

Diese Modi sind Projektionen auf dieselbe persistierte Run-Quelle und denselben
Event-Verlauf. Sie halten keine konkurrierenden Prozess-, Gate- oder
Chat-Zustaende. Der Projektstatus wird aus dieser Quelle abgeleitet, nicht aus
DOM-Heuristiken oder einer blossen Prozessliste.

### 3. Chat-, Aktivitaets- und Gate-Vertrag

- Nutzerbeitraege stehen rechts in kompakten, rechtsbuendigen Bubbles.
  Assistentenantworten stehen links in einer begrenzten Lesespalte mit
  gut lesbarer Markdown-Formatierung.
- Der Composer bleibt unten erreichbar, mehrzeilig und per Tastatur nutzbar.
  Enter sendet; Shift+Enter fuegt eine neue Zeile ein. Fokuszustand und
  Bedienbarkeit muessen sichtbar bleiben.
- Waehrend langer Arbeit erscheint im Chat hoechstens eine temporaere,
  menschlich formulierte Aktivitaetszeile. Sie wird beim Schrittwechsel
  ersetzt und nach Abschluss entfernt. Die detaillierte Schrittfolge gehoert
  in Control.
- Control protokolliert Status, Belege, Ergebnis und naechsten Schritt.
  Sichtbare Begruendungen sind kurze, belegte Zusammenfassungen; rohe interne
  Gedankengaenge werden nicht ausgegeben.
- Freigaben sind Chat-Nachrichten/Karten im selben Projekt- und
  Sessionverlauf. Eine Gate-ID bindet Antwort, Status und Audit idempotent an
  genau eine Freigabe. Ein Modal darf dieselbe Gate-Karte zusaetzlich
  darstellen, ist aber kein eigener Gate-Zustand und kein separater
  Antwortkanal.
- Bei Reconnect werden Nachrichten, Aktivitaet, Gate-Karten und Antworten aus
  dem gespeicherten Zustand wiederhergestellt, ohne Duplikate oder verlorene
  Antworten. Eine Chat-Aktion meldet Annahme, Ausfuehrungsstatus oder
  Ablehnung eindeutig; Prozessstart gilt nicht als erfolgreiche Annahme.

### 4. Startseite und Metaorchestrator

Die Startseite ist der Default, wenn kein Projekt geoeffnet ist. Sie zeigt
registrierte Projekte, belegte Laufzustaende, Erfolgs-/Fehlerstatistik,
Aktualitaet der Daten und Aktionen zum Oeffnen oder Anlegen.

Der spaetere Metaorchestrator sitzt auf dieser Startseite und koordiniert
registrierte Projekte. Er aggregiert dieselben belegten Projekt-/Run-Events;
er erhaelt weder einen zweiten Statusspeicher noch direkten Schreibzugriff
auf Projekt-Checkouts. Projektisolation und Human-Gates bleiben wirksam.

### 5. Codeguardian

Codeguardian-Befunde verwenden dieselbe Run-Identitaet und Evidenz:

- Im Chat erscheinen sie bei Entscheidung oder erforderlicher Handlung.
- Control zeigt Regel, Grund, Status und Beleg.
- Debug verknuepft Schweregrad, Pfad/Zeile, Regelversion, Diff-Fingerprint
  und Verify-Ergebnis.

Codeguardian schreibt keinen eigenen Patch und umgeht keine Freigabe.
Sicherheits- oder Scope-Verletzungen bleiben blockierend, bis sie belegbar
aufgeloest sind.

## Qualitaets- und Abnahmekriterien

Die Umsetzung gilt fuer diese ADR erst dann als verifiziert, wenn:

1. Ein Run-Replay in Chat, Cockpit, Control und Debug dieselben Status- und
   Ereignisfakten liefert; jede Ansicht darf sie anders ordnen, nicht
   widersprechen.
2. Projektwechsel, mehrere Tabs und Sessionwechsel sauber isoliert sind.
3. Ein Gate genau einmal in der Projektkonversation und Audit-Spur erscheint;
   offene und abgeschlossene Gates werden nach Reconnect korrekt angezeigt
   und koennen nicht durch eine veraltete Antwort bestaetigt werden.
4. Chatfragen waehrend eines Runs dessen Schreibarbeit nicht blockieren;
   Aktivitaet wird ersetzt und endet sichtbar mit dem Schritt.
5. Verify-Fehler auf den exakten Commit-/Worktree-Stand bezogen sind und
   Failure Record, Reparatur und erneute Pruefung zusammenhaengen.
6. Tastaturbedienung, Fokus, Screenreader-Namen, Kontrast, reduzierte
   Bewegung und schmale Viewports geprueft sind.
7. Browserpruefungen mit isolierten Testdaten DOM-/Accessibility-Befunde,
   Screenshots und Browser-Logs als Verify-Artefakte festhalten.
8. Zehn vollstaendige UI-Runs Start, Fragen waehrend der Arbeit, Gates,
   Pause/Resume, Reconnect, Verify-Fehler-Recovery und sauberen Abschluss
   mit Projekt, OP, Run-ID und Belegen nachweisen.

Diese Entscheidung beschreibt das Zielbild. Sie erklaert keine offenen
Umsetzungs- oder Betriebs-OPs fuer erledigt; diese bleiben in
`docs/STATUS.md` offen, bis ihre Kriterien und Belege erfuellt sind.

## Konsequenzen

- Die UI hat eine dauerhafte Projekt- und Chat-Orientierung; Modi aendern
  Schwerpunkt und Detailgrad, nicht die Quelle der Wahrheit.
- Jede Laufzeit- oder Gate-Aktion muss als gespeichertes, replaybares Ereignis
  sichtbar sein.
- Der Chat kann waehrend langer Arbeit ansprechbar bleiben, waehrend Control
  die vollstaendige technische Arbeitsspur bewahrt.
- Umsetzung und Browser-Dogfooding haengen von den Run-, Event-, Inbox- und
  Checkpoint-Vertraegen aus ADR-0032 ab.
- UI-Feinschliff ohne Einfluss auf diese Daten- und Bedienvertraege bleibt
  nachgelagert und blockiert die Loop-Stabilisierung nicht.
