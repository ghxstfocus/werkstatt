# Roadmap — Werkstatt


Stand: 2026-11-11. Diese Roadmap beschreibt nur den aktuellen Produktfokus
und die Abfolge grober Meilensteine. Konkrete startbare Auftraege stehen in
docs/STATUS.md; abgeschlossene Arbeit in PROGRESS.md. Alte Phasenberichte
liegen im Archiv und sind keine aktuelle Betriebs- oder Architekturvorgabe.


## Ziel


Die Werkstatt soll eine verlässliche Multi-Projekt-Agenten- und
Entwicklungsumgebung sein. Der Chat ist Ansprechpartner und Kontrollpunkt:
er untersucht das aktive Projekt, macht seine Arbeit sichtbar, bleibt bei
laengeren Runs ansprechbar und steuert den Loop nach konkreter Freigabe.
Plan- und Ergebnis-Gates bleiben verpflichtend.


## Aktueller Fokus


### 1. Chat und UI als Arbeitsoberflaeche
- OP-396: Projektchat, evidenzbasierte Antworten und sichere Loop-Steuerung.
- OP-397: Hintergrundjobs, Reconnect/Replay und Checkpoint-Steuerung.
- OP-394/395: nachvollziehbare Live-Ereignisse im Control-Modus.
- OP-308: nachtraegliche Phasen-Timeline im Cockpit.
- OP-240: belegter Debugger-Handoff in den normalen Loop.

Projektleiste zuerst, Modusleiste darunter. Control zeigt Live-Aktivitaet;
Cockpit fasst abgeschlossene/laengere Verlaeufe zusammen; Debug verbindet
Fehler, Run-Kontext und konkrete Diagnose.


### 2. Loop-Qualitaet und Betriebsnachweis
- OP-398: begruendete Auswahl einzelner startbarer oder zusammenhaengender OPs.
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


## Spaetere Phase: Lernen und Memory


Fehlercluster, Reflexions-/Memory-Promotion und Memory-Graph bleiben
gesperrt, bis OP-382 erfolgreich abgeschlossen ist. ADR-0016 und ADR-0017
(Spec-First Testloop und Mutation-Gate) sind vorgeschlagen; sie werden erst
nach expliziter Architekturentscheidung zu Implementierungsauftraegen.
Debugging bleibt eine Chat-Faehigkeit, keine neue Loop-Rolle.


## Verbindliche Quellen


- Akzeptierte Architektur: ADRs mit Status accepted in docs/adr/.
- Offene, startbare Arbeit: docs/STATUS.md.
- Implementierte Architektur: docs/ARCHITECTURE.md.
- Verlauf: PROGRESS.md.
