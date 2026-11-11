# ADR-0031: Metaorchestrator fuer projektuebergreifende Arbeit

- **Datum:** 2026-11-11
- **Status:** proposed
- **Ergaenzt:** ADR-0023 (Multi-Projekt-Kontext), ADR-0024 (Event-Log),
  ADR-0029 (Chat-Control-Plane), ADR-0030 (Projektquellen und Rollenmodelle)
- **Grundlage fuer:** spaeteren Metaorchestrator-Plan; noch keine startbare OP

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

1. **Globale Koordination, lokale Ausfuehrung.** Der Metaorchestrator
   beobachtet Projektzustand, Ereignisse, Blocker und aktive Auftraege,
   priorisiert projektuebergreifend und delegiert einzelne Aufgaben an
   isolierte Projektloops oder passende Rollen. Jeder schreibende Auftrag
   bleibt strikt einem Projekt und dessen Run-Worktree zugeordnet.
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
5. **Chat als Eskalations- und Freigabeflaeche.** Der Chat meldet, was
   erkannt wurde, welche Rolle arbeitet, was geaendert und geprueft wurde,
   welche Risiken offen sind und was als Naechstes vorgeschlagen wird.
   Der Nutzer bestaetigt weiterhin Plan und Abschluss gemaess ADR-0029.
   Externe Aktionen wie Push, Merge, Release oder destruktive Aenderungen
   behalten jeweils ein eigenes, inhaltlich genau gebundenes Gate.
6. **Unterbrechungen und Prioritaet.** Neue Nutzerauftraege, insbesondere
   direkte Chat-Eingriffe, werden als dauerhafte Jobs mit eigener Prioritaet
   aufgenommen. Der Koordinator darf am naechsten sicheren Checkpoint
   pausieren, fortsetzen oder einen Auftrag dazwischenschieben; der
   urspruengliche Plan und sein Checkpoint bleiben erhalten. Pro Projekt
   bleibt hoechstens ein schreibender Run aktiv; unabhaengige Lese- und
   Diagnosejobs duerfen parallel laufen.
7. **Browser-Verifikation als Werkzeug.** Fuer UI-Arbeit darf ein
   isolierter Browser-Testworker die Anwendung mit kontrollierten,
   kurzlebigen Testdaten bedienen und Screenshots, DOM-/Accessibility-
   Befunde sowie Browser-Logs als Verify-Artefakte speichern. Er verwendet
   keine produktiven Sessions oder realen externen Konten. Browseraktionen
   ausserhalb der genehmigten Testumgebung brauchen eine eigene Freigabe.
8. **Nachvollziehbare Entscheidungsspur.** Jede Priorisierung, Delegation,
   Rueckfrage, Vertragsversion, Gate-Entscheidung und automatische Reparatur
   wird mit Begruendung, Eingangsbelegen, gewaehlter Rolle, Budget und
   Ergebnis als Projekt-/Meta-Event protokolliert. Eine globale Uebersicht
   darf diese Ereignisse projektuebergreifend aggregieren, aber keine
   Projektisolation aufheben.

## Aktivierungskriterien

Vor einem Automodus muessen mindestens Chat- und Hintergrundjob-
Wiederaufnahme, Projektisolation, sichere Plan-/Ergebnis-Gates,
Debugger-Handoff, reproduzierbare Browser- und Quality-Gates,
Audit-Replay sowie ein dokumentierter Nutzervertrag durch Tests und
Betriebslaeufe belegt sein. Bis diese Kriterien erfuellt und eine
Umsetzungs-ADR angenommen ist, bleibt diese ADR ein Vorschlag und der
Metaorchestrator darf nicht als implementiert oder autonom freigegeben
behandelt werden.
