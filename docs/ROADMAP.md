# Roadmap — Werkstatt


Stand: 2026-11-12. Diese Roadmap beschreibt nur den aktuellen Produktfokus
und die Abfolge grober Meilensteine. Konkrete startbare Auftraege stehen in
docs/STATUS.md; abgeschlossene Arbeit in PROGRESS.md. Alte Phasenberichte
liegen im Archiv und sind keine aktuelle Betriebs- oder Architekturvorgabe.
ADR-0032 ist angenommen und ersetzt die feste Phasenfolge als Runtime-Steuerung
durch einen zielorientierten, wiederaufnehmbaren Koordinator. Die nachfolgenden
Roadmap-Meilensteine beschreiben nur die Migration; sie sind keine neuen
Zwangsphasen im Lauf. Die konkrete Ist-Aufnahme steht in
`docs/IST-ZUSTAND-LOOP-2026-11-12.md`.


## Ziel


Die Werkstatt soll eine verlässliche Multi-Projekt-Agenten- und
Entwicklungsumgebung sein. Der Chat ist Ansprechpartner und Kontrollpunkt:
er untersucht das aktive Projekt, macht seine Arbeit sichtbar, bleibt bei
laengeren Runs ansprechbar und steuert den Loop nach konkreter Freigabe.
Plan- und Ergebnis-Gates bleiben verpflichtend.


## Aktueller Fokus

### 0. Run-Abschluss und Failure-Recovery
- **OP-403:** finale Verify-Fehler als reparierbare Befunde desselben Runs
  behandeln und Doku-/PROGRESS-Reihenfolge korrigieren. Der erste Schnitt
  speichert den redigierten Failure Record samt HEAD- und Worktree-Fingerprint;
  derselbe Run muss Diagnose/Repair und erneute Verify weiterfuehren.
- Spec-First bleibt als bedarfsgesteuerter Pfad erhalten: Spec-Builder friert
  unabhaengige Tests/Vertraege ein, Code-Builder implementiert ohne Einsicht
  in diese Tests; einfache Aufgaben ueberspringen den Pfad.
- Das harte Doku-Gate prueft nur den aktuellen Worktree; Historien-Drift
  bleibt Teil des separaten Qualitaetsgates. Vor dem Gate wird
  `verify_pending` protokolliert, danach das tatsaechliche Ergebnis.
- Live-Prozessstatus fuer Chat und fehlende Builder-Ereignisse an dieselbe
  Run-Projektion anbinden.
- OP-403 ist der erste vertikale Zuverlaessigkeitsschnitt fuer ADR-0032;
  verpflichtende Plan-, Ergebnis- und Human Gates bleiben unveraendert.


### 1. Chat und UI als Arbeitsoberflaeche
- OP-396: Projektchat, evidenzbasierte Antworten und sichere Loop-Steuerung.
- OP-397: Hintergrundjobs, Reconnect/Replay und Checkpoint-Steuerung.
- OP-401: neue Chat-Arbeit sicher an aktive Sessions koppeln.
- OP-402: unabhaengige Schreibauftraege parallel, aber konfliktbewusst integrieren.
- Chat bleibt bei laufender Arbeit ansprechbar; Schreibauftraege nutzen getrennte, commit-gepinnte Worktrees und werden am Checkpoint konfliktbewusst integriert. Control zeigt die Arbeitsschritte chronologisch mit Status, Belegen, kurzer Entscheidungszusammenfassung und naechstem Schritt.
- OP-394/395: nachvollziehbare Live-Ereignisse im Control-Modus.
- OP-404: Codeguardian als diff-gebundene Schutzschicht; deterministische
  Regeln zuerst, risikobasierte semantische Review danach. Er schreibt keine
  Patches und delegiert Befunde in denselben Run.
- OP-308: nachtraegliche Phasen-Timeline im Cockpit.
- OP-240: belegter Debugger-Handoff in den normalen Loop.

Projektleiste zuerst, Modusleiste darunter. Control zeigt die vollstaendige, chronologische Live-Arbeitsspur. Der Chat zeigt waehrend langer Schritte nur eine menschliche temporaere Aktivitaetszeile, die ersetzt wird und nach Abschluss verschwindet. 
Cockpit fasst abgeschlossene/laengere Verlaeufe zusammen; Debug verbindet
Fehler, Run-Kontext und konkrete Diagnose.


### 2. Loop-Qualitaet und Betriebsnachweis
- OP-398: begruendete Auswahl einzelner startbarer oder zusammenhaengender OPs; jeder gruene Zwischenschritt wird gegen das Hauptziel geprueft, bevor der Loop selbst weiterarbeitet oder abschliesst.
- OP-384–388 und OP-324: Scout-/Architect-Kontext, Reflection, Retrieval
  und begrenzte Plaene verbessern.
- OP-280: Doku-Drift beim Verify zuverlaessig erkennen.
- OP-372/374/375: Projektstatistik und Event-Projektion semantisch korrekt halten.
- OP-382: zehn vollstaendige UI-Runs mit Run-, Gate- und Verify-Belegen.

Keine optionale Selbstverbesserung oder Memory-Injektion vor Abschluss
dieses Betriebsnachweises.


### 3. Projektquellen und Modellwahl
- OP-399: Projekte server-first anlegen, GitHub beim Greenfield-Setup oder
  spaeter verbinden, vor Runs serverseitig fetch/pinnen und sicher in
  Werkstatt-Konventionen ueberfuehren.
- OP-400: Provider und Modell je Projekt und Rolle mit geerbten Defaults.

ADR-0030 ist angenommen. OP-399 setzt die Projektquellen server-first und
sichert Credentials, Remote-Schreiben, Revision-Pinning und isolierte Runs
vor ihrer Aktivierung ab. Bis zur Umsetzung bleiben bestehende lokale Quellen
und globale Modell-Defaults der Betriebsweg.


## Spaetere Phase: Metaorchestrator

ADR-0031 ist angenommen; die Umsetzung bleibt an OP-396/397 und die dortigen Nachweise gebunden. Die Annahme aktiviert keinen Automodus.
Der Metaorchestrator soll alle Projekte nach einem expliziten, versionierten
Nutzervertrag priorisieren, Sicherheits-/Semantikprobleme erkennen und
Diagnose oder Debugger-Reparatur in den jeweiligen Projektloop delegieren.
Chat bleibt waehrenddessen ansprechbar und zeigt Belege, Patch, Gate-Status
und Empfehlung. Ein automatisch gestarteter Debugger darf nur im Run-Worktree
arbeiten; erst wenn die echten Verify-Gates gruen sind, wird ein belegter
Vorschlag dem verpflichtenden Human Gate vorgelegt. Fehlende Belege,
Sicherheitsbefunde und Zielkonflikte gehen als konkrete Rueckfrage an den
Chat. Nutzerantworten duerfen Vertragsaenderungen vorschlagen, aber
Berechtigungen nicht still erweitern.

Jede Chatfrage bleibt im gewohnten natuerlichen Ablauf. Plan- und Basisversionen
sind intern; der Chat fragt nur dann nach, wenn sich die Freigabe oder das
Nutzerziel tatsaechlich aendert. Parallele Aenderungen werden an festen
Commits und getrennten Worktrees aufgebaut. Der Loop beobachtet Projekt-
Aenderungsereignisse und pausiert nur betroffene Arbeit am sicheren
Checkpoint; er vergleicht nie Diffs verschiedener Basen.

Voraussetzungen sind OP-396/397 fuer Chat und Hintergrundjobs, OP-399 fuer
Projektquellen, OP-401/402 fuer laufende Aenderungsereignisse und sichere
parallele Integration, OP-382 als Betriebsnachweis sowie nachvollziehbare
Projektisolation und Audit-Replay. UI-Aenderungen muessen zusaetzlich in
einem isolierten Browser mit kontrollierten Testdaten verifiziert werden;
Screenshots, Accessibility-/DOM-Befunde und Browser-Logs werden als
Verify-Artefakte gespeichert. Vor diesen Belegen wird kein Projekt in
einen projektuebergreifenden Automodus geschaltet.

## Spaetere Phase: Lernen und Memory


Fehlercluster, Reflexions-/Memory-Promotion und Memory-Graph bleiben
gesperrt, bis OP-382 erfolgreich abgeschlossen ist. Der spaetere Fehler-
Memory-Store folgt ADR-0032 und uebernimmt ADR-0010s Provenance-, unabhaengige
Bestaetigungs-, Sanitization- und Widerlegungsregeln; Projekt- und Global-
Scope sind zwei Bereiche desselben Speichers. ADR-0026 ist nur eine spaetere
read-only Projektion darauf. ADR-0016 und ADR-0017
(Spec-First Testloop und Mutation-Gate) sind vorgeschlagen; sie werden erst
nach expliziter Architekturentscheidung zu Implementierungsauftraegen.
Debugging bleibt eine Chat-Faehigkeit, keine neue Loop-Rolle.


## Spaeterer UI-Feinschliff

Nach Abschluss der aktuellen Funktions- und Betriebsnachweise die gemeldeten
kleinen UI-Punkte gemeinsam pruefen und beheben:

- Audit-Kalender: fruehere Tage muessen anklickbar sein; der Zeitraum soll
  mindestens bis zum 2026-11-08 zurueckreichen.
- Chat-Eingabe: die doppelte Umrandung entfernen.
- Kopfbereich: Abstaende in allen Projekt-Tabs angleichen; aktuell weicht
  insbesondere das Werkstatt-Projekt ab.

Diese Punkte sind bewusst nachrangig und blockieren den aktuellen
Loop-/Projektquellen-Fokus nicht.

## Verbindliche Quellen


- Akzeptierte Architektur: ADRs mit Status accepted in docs/adr/.
- Offene, startbare Arbeit: docs/STATUS.md.
- Implementierte Architektur: docs/ARCHITECTURE.md.
- Verlauf: PROGRESS.md.



## UI-Zielbild und Codeguardian

Der konkrete, ueberarbeitete UI-Plan liegt in
`docs/UI-PLAN-2026-11-12.md`. Er fuehrt Projektwahl, Modusleiste, Chat,
Control-Timeline, Cockpit und Debug auf eine gemeinsame Run-Projektion
zurueck. Codeguardian-Befunde erscheinen als normale Chat-Karten fuer
Handlungsbedarf, als Timeline-Ereignisse in Control und als Ursache-Wirkungs-
Fall in Debug; es gibt keinen separaten Chat-Agenten, der unabhaengig am
gleichen Diff schreibt.
