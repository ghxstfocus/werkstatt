# ADR-0031: Metaorchestrator fuer projektuebergreifende Arbeit

- **Datum:** 2026-11-11
- **Status:** accepted
- **Ergaenzt:** ADR-0023 (Multi-Projekt-Kontext), ADR-0024 (Event-Log),
  ADR-0029 (Chat-Control-Plane), ADR-0030 (Projektquellen und Rollenmodelle)
- **Grundlage fuer:** OP-396/397/401/402 und spaetere Metaorchestrator-Umsetzung; kein sofort freigeschalteter Automodus

## Kontext

Die Werkstatt soll mehrere Projekte gleichzeitig beobachten und in
Uebereinstimmung mit den Zielen und Sicherheitsgrenzen des Nutzers steuern.
Der Nutzer soll im Chat ansprechbar bleiben, waehrend Hintergrundarbeit
laeuft. Technische oder semantische Probleme sollen nicht einfach als
menschliche Gate-Entscheidung liegenbleiben: das System soll sie, soweit
sicher moeglich, untersuchen, an einen geeigneten Debugger delegieren und
einen belegten Reparaturvorschlag zur Freigabe vorlegen.

Der Metaorchestrator darf bestehende Projektloops, Gates, Reviews und
Verify nicht umgehen. Insbesondere ist ein fehlgeschlagenes Gate kein
Zustimmungsereignis und ein Modellurteil allein kein Beleg fuer einen
erfolgreichen Fix.

## Entscheidung

1. **Dauerhafte, kontextgebundene Auftraege.** Jede Chat-Nachricht wird
   als Frage, Diagnose, Steuerungsaktion oder Schreibauftrag klassifiziert.
   Auftraege tragen intern Projekt, Chat-Session, Elternauftrag, aktiven Run,
   Prioritaet, bestaetigten Auftragsstand, Basis-Commit und eigenen Worktree.
   Interne Plan-/Kontextversionen sind technische Metadaten und werden dem
   Nutzer nicht als zusaetzliche Bedienaufgabe aufgebuerdet. Der Chat bleibt
   waehrend laufender Runs ansprechbar; unabhaengige Lese-/Diagnoseauftraege
   duerfen sofort parallel laufen.
2. **Versionierter Nutzervertrag.** Prioritaeten, Rueckfrageverhalten,
   erlaubte automatische Reparaturen, Budgets und Freigabegrenzen werden
   als expliziter, versionierter Vertrag gespeichert. Antworten duerfen
   eine Praeferenz als Vorschlag zur Vertragsaenderung vormerken, aber
   bestehende Regeln oder Berechtigungen nicht still erweitern. Der Vertrag
   kann keine globalen Sicherheitsregeln oder verpflichtenden Gates
   abschwaechen.
3. **Probleme zuerst diagnostizieren.** Bei fehlgeschlagenem Test, Review
   oder Gate erzeugt der Koordinator einen Diagnoseauftrag mit Projekt-,
   Run-, Plan-, Diff- und Verify-Belegen. Er kann den Debugger innerhalb
   der erlaubten Vertragsgrenzen selbststaendig starten. Bei Unsicherheit,
   semantischen Zielkonflikten, Sicherheitsbefunden, Bereichsueberschreitung
   oder fehlenden Belegen eskaliert er im Chat mit konkreter Rueckfrage und
   Empfehlung.
4. **Reparatur nur in Grenzen.** Der Debugger darf einen Patch nur im
   isolierten Worktree des betroffenen Runs erstellen. Aenderungen muessen
   Scope-, Sicherheits-, Test-, Doku- und Review-Pruefungen durchlaufen.
   Ein gruenes Ergebnis muss aus tatsaechlich ausgefuehrten, identifizierten
   Gates stammen; die LLM-Einschaetzung kann diese nicht ersetzen. Bei
   Fehlschlag wird nicht weiter eskaliert oder ein Gate als bestanden
   markiert, sondern der Befund samt Logs und naechster Empfehlung im Chat
   gezeigt.
5. **Natuerlicher Chatfluss mit unsichtbarer Konsistenzsicherung.** Der
   Chat zeigt knapp, welche Arbeit parallel laeuft und was als Naechstes
   passiert. Er zwingt den Nutzer nicht, Plan- oder Versionsnummern zu
   verwalten. Planfreigaben bleiben an den intern gespeicherten Auftrag und
   Diff gebunden. Nur wenn ein neuer Auftrag den aktiven Scope, seine
   Annahmen oder betroffene Dateien veraendert, pausiert der Loop am naechsten
   sicheren Checkpoint, erklaert die Auswirkung in normaler Sprache und holt
   nur dann eine neue Freigabe ein. Externe Aktionen wie Push, Merge, Release
   oder destruktive Aenderungen behalten jeweils ein eigenes, exakt gebundenes
   Gate.
6. **Parallele Aenderungen ohne bewegliche Arbeitsbaeume.** Jeder
   schreibende Auftrag arbeitet in einem eigenen Worktree auf einem festen
   Basis-Commit; niemals schreiben zwei Worker in denselben Worktree. Damit
   koennen unabhaengige Aenderungen parallel entstehen. Integration in den
   gemeinsamen Projektstand wird pro Projekt serialisiert und geschieht an
   einem sicheren Checkpoint. Der Koordinator veroeffentlicht jede relevante
   Aenderung als Ereignis mit Commit, betroffenen Pfaden und Auftragsbezug.
   Der aktive Loop vergleicht Diffs nur bei gleicher Basis-SHA. Aendert sich
   eine Basis oder ueberschneiden sich Pfade/Annahmen, wird die betroffene
   Arbeit als veraltet markiert, sauber pausiert und auf dem integrierten
   Stand neu geplant und verifiziert. Diffs werden nie still gegen einen
   beweglichen Checkout verglichen; ein Konflikt wird als bearbeitbarer
   Integrationsauftrag im Chat erklaert, nicht als unerwarteter Testfehler.
   Nachweislich disjunkte Aenderungen koennen ohne Nutzerunterbrechung am
   Checkpoint integriert werden, wenn alle betroffenen Gates erneut auf dem
   exakten kombinierten Commit laufen.
7. **Browser-Verifikation als Werkzeug.** Fuer UI-Arbeit darf ein
   isolierter Browser-Testworker die Anwendung mit kontrollierten,
   kurzlebigen Testdaten bedienen und Screenshots, DOM-/Accessibility-
   Befunde sowie Browser-Logs als Verify-Artefakte speichern. Er verwendet
   keine produktiven Sessions oder realen externen Konten. Browseraktionen
   ausserhalb der genehmigten Testumgebung brauchen eine eigene Freigabe.
8. **Nachvollziehbare Entscheidungsspur.** Jede Priorisierung, Delegation,
   Rueckfrage, Vertragsversion, Gate-Entscheidung, Basis-/Planrevision,
   Aenderungsereignis, Integration und automatische Reparatur wird mit
   Begruendung, Eingangsbelegen, betroffenen Pfaden, gewaehlter Rolle, Budget
   und Ergebnis als Projekt-/Meta-Event protokolliert. Ein Run konsumiert
   Ereignisse seines Projekts und erkennt, wenn sein Arbeitsstand oder Plan
   nicht mehr aktuell ist. Eine globale Uebersicht darf diese Ereignisse
   projektuebergreifend aggregieren, aber keine Projektisolation aufheben.
9. **Fortsetzung anhand des Ziels.** An jedem sicheren Checkpoint vergleicht
   der Koordinator den aktuellen Belegstand mit dem uebergeordneten Auftrag,
   dem Nutzervertrag und den freigegebenen Akzeptanzkriterien. Ein gruener
   Einzeltest oder Task ist nur ein Zwischenbeleg. Sind Kriterien offen,
   waehlt der Loop den naechsten begruendeten Schritt innerhalb des bereits
   freigegebenen Umfangs und arbeitet weiter. Erst belegte Zielerreichung
   plus abschliessende Verify auf dem integrierten Stand erlauben den
   Abschluss. Reflexion passiert an Aufgaben-/Checkpoint-Grenzen, nicht als
   zusaetzlicher LLM-Aufruf nach jedem Tool. Ihre kurze, belegbasierte
   Entscheidung mit Grund fuer Fortsetzung/Abschluss und naechstem Schritt
   erscheint in der detaillierten Control-Timeline. Der Chat zeigt nur eine
   temporaere knappe Aktivitaetszeile, die bei jedem Schritt ersetzt wird
   und nach Abschluss verschwindet. Rohe interne Gedankengaenge werden nicht
   protokolliert. Reflexion darf weder neue Ziele erfinden noch den
   freigegebenen Umfang erweitern; neue unabhaengige Funde werden getrennt
   vorgemerkt, Unsicherheit wird knapp im Chat geklaert.

## Aktivierungskriterien

Vor einem Automodus muessen mindestens Chat- und Hintergrundjob-
Wiederaufnahme, Projektisolation, sichere Plan-/Ergebnis-Gates,
Debugger-Handoff, reproduzierbare Browser- und Quality-Gates,
Audit-Replay, evidenzbasierte Fortsetzung nach gruener Zwischenarbeit
sowie ein dokumentierter Nutzervertrag durch Tests und Betriebslaeufe
belegt sein. Diese ADR ist angenommen; ihre Annahme schaltet keinen
Automodus frei. Bis die Kriterien belegt sind, bleibt die Umsetzung
schrittweise an OP-396/397 und den jeweils verpflichtenden Human Gates
gebunden. Kein Projekt wird als autonom freigegeben behandelt.


## Klarstellung: Werkstattweite Startseite und Projektassistenten

Der Metaorchestrator ist eine werkstattweite Steuerungsebene fuer **alle
registrierten Projekte** und sitzt auf der Startseite/Projektuebersicht. Sein
Chat ist der globale Ansprechpartner: Er kann projektuebergreifend Status,
ADRs, Roadmaps, offene Ops und belegte Risiken sichten, Arbeit priorisieren
und konkrete Auftraege an die betroffenen Projektloops delegieren.

Der Chat innerhalb eines Projekts bleibt zugleich dessen projektbezogener
Koordinator und Assistent. Er nimmt freie Auftraege entgegen, prueft den
Projektkontext und die passende OP-Queue und verfolgt das Ziel bis zur
belegten Abschlusspruefung. Beide Chats verwenden denselben natuerlichen
Arbeitsfluss; der globale Metaorchestrator schreibt nicht direkt in
Projekt-Checkouts und mischt keine Projektbelege. Er delegiert an den
isolierten Projektloop und aggregiert nur die fuer die werkstattweite
Priorisierung noetigen, provenance-tragenden Status- und Ereignisdaten.

Globale Nutzerpraeferenzen gelten als versionierter Vertrag. Projekte duerfen
zusaetzliche, engere Regeln besitzen. Korrekturen des Nutzers koennen
Vertragsaenderungen vorschlagen; sie erweitern weder Berechtigungen noch
Auto-Gate-Grenzen stillschweigend. Bis die Aktivierungskriterien dieses ADRs
belegt sind, bleiben Human Gates verbindlich.
