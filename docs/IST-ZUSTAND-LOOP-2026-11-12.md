# Ist-Zustand des Werkstatt-Loops — GitHub main 2026-11-13

Diese Bestandsaufnahme beschreibt den Repository-Stand und trennt ihn vom
laufenden Server. Ein gruener GitHub-Run beweist die Tests des Commits, aber
nicht, dass der Server diesen Commit bereits ausfuehrt.

Gepruefter Stand: `b65cb83dcb501e4db146062f4f76014326fc9612`
(`fix(loop): keep old-interpreter workers fail closed`).
GitHub Actions Quality Gate:
[Run 43354116256](https://github.com/ghxstfocus/werkstatt/actions/runs/43352637612).

## Kurzbefund

Die Werkstatt hat solide operative Bausteine: Projekt-Runs, spezialisierte
Rollen, harte Verify-Stufen, Human Gates, Failure Records, Event Store,
Chatjobs und eine Prozess-Registry. Der Abschlussfehlerpfad ist deutlich
staerker als im frueheren Befund: Ein rotes Phase-End-Verify kann im selben
Run gezielt diagnostiziert und repariert werden. Nach einem Commit prueft
der Loop den committed Stand noch einmal vollstaendig.

Der groesste Architekturabstand zu ADR-0032 bleibt der Run-Kern: Der
Produktionslauf ist weiterhin eine feste Funktionsfolge aus Setup/Explorer,
Plan/Preflight, Task-Loop und Finalizer. Ein einheitlicher persistierter
Zielkoordinator mit Inbox, veränderbarem Arbeitsgraphen und Evidence Ledger
fehlt. Chat-Session, Chatjobs, Phase-Checkpoint und Loop-Registry speichern
jeweils Teile des Zustands, bilden aber noch keinen gemeinsamen Run-Vertrag.

## Implementierte Zuverlaessigkeitsvertraege

| Bereich | Aktueller Stand |
|---|---|
| Laufsteuerung | `run_pipeline_loop` ruft die bestehende Setup-, Plan-, Task- und Finalizer-Kette auf. Phasen bleiben im Runtime-Pfad also noch Steuerungsstruktur. |
| Failure Records | Rote Abschlusspruefungen erzeugen redigierte, Run-gebundene Belege mit Stage, Exit-Code, HEAD und Worktree-Fingerprint. |
| Recovery | Der Resume-Akzeptanztest durchlaeuft den HTTP-Endpunkt, prueft genau einen CLI-Aufruf mit derselben Run-ID und `--resume` und fuehrt exakt diese Argumente bis zum erfolgreichen Phase-End-Verify aus. Ein separater Probe prueft den echten Launcher/Subprozessstart. GitHub Quality Gate verifiziert 2.149 Tests. Der Test ersetzt den per HTTP gestarteten Worker durch einen CLI-Aufruf im Test-Hauptthread; ein kompletter Webserver-Absturz mit autonomer Worker-Wiederaufnahme ist damit noch nicht nachgewiesen. Stagnation stoppt fail-closed und zeigt ein adressiertes Recovery-Gate. |
| Commit-Vertrag | Committer pinnt Eltern-HEAD und Index-Tree und kontrolliert Commit-SHA, Parent, Tree, Whitespace und Working-Tree-Zustand. |
| Verify nach Commit | Nach jedem erzeugten Commit laeuft die vollstaendige Phase-End-Verify erneut. Rot startet Recovery desselben Runs; nach Repair wird neu committet und wieder geprueft. Snapshot-Abweichungen verhindern Erfolg. |
| Run-Ergebnis | Ein Run wird nicht allein wegen eines gruenen Teilchecks erfolgreich; offene/fehlgeschlagene Tasks oder rotes Verify bleiben unvollstaendig. |
| Chat und Prozess | Chatjobs, Session-Historie und Loop-Registry sind persistiert, aber Status und Steuerung sind noch nicht aus einem gemeinsamen RunRecord abgeleitet. Der Server kann einen lebenden Prozess wiederfinden; einen beendeten Prozess nicht allgemein aus einem Run-Checkpoint fortsetzen. |
| Control-Timeline | Ereignisse zeigen viele Rollen- und Verify-Schritte. Lueckenloses Builder-Fortschritts-/LLM-Eventing und die einheitliche semantische Run-Projektion bleiben offene Arbeit. |

## Architekturabstand zu ADR-0032

1. **Persistierter Run-Vertrag fehlt:** Es gibt noch keine gemeinsame SSOT fuer Ziel, Freigabe, Basis-Commit, Checkpoint-Version, naechste Aktion und Inbox-Offset.
2. **Nachrichten-Inbox fehlt:** Chatfragen, Steuerung, Folgeauftraege und Gate-Antworten sind noch nicht allesamt idempotente Ereignisse an denselben Koordinator.
3. **Arbeitsgraph fehlt:** Tasks werden weiterhin aus einem Plan in der festen Task-Schleife abgearbeitet, statt am Checkpoint gegen offene Akzeptanzkriterien neu disponiert zu werden.
4. **Evidence Ledger fehlt:** Verify- und Audit-Ereignisse existieren, aber es gibt noch keine einheitliche Zuordnung von Kriterium zu Quelle, Befehl, SHA und Artefakt-Hash.
5. **UI bleibt auf Teilprojektionen:** Chat, Control, Runs und Prozessstatus nutzen verbundene, aber getrennte Speicher- und API-Pfade.

Diese Punkte sind nicht als fertige Architektur zu interpretieren. Der
verbindliche Zielvertrag und die Migrations-Meilensteine stehen in
[ADR-0032](adr/ADR-0032-adaptiver-zielorientierter-run-kern.md) und
[ROADMAP.md](ROADMAP.md). Die konkreten offenen Aufgaben stehen nur in
[STATUS.md](STATUS.md).

## OP-403 Abschlussnachweis

OP-403 ist abgeschlossen und aus der offenen Queue entfernt. Der aktuelle
Nachweis ist der verifizierte Commit oben sowie dessen CI-Lauf. Die
vollstaendige Server-Dogfooding-Abnahme und zehn UI-Runs sind weiterhin
Teil von OP-382; sie werden durch Unit-Tests oder GitHub-CI nicht behauptet.

## Naechster Architektur-Schritt

ADR-0032 nennt M1 als naechsten Architektur-Meilenstein: RunRecord und
idempotente Ereignis-Inbox fuer Fragen, Steuerung, Gate-Antworten und neue
Schreibauftraege. Vor Umsetzung sind die bestehenden SQLite-Stores,
Loop-Registry und Phase-Checkpoints als Migrationsquellen zu behandeln; ein
zweiter paralleler Statusspeicher ohne Replay-/Recovery-Vertrag waere kein
Fortschritt.
