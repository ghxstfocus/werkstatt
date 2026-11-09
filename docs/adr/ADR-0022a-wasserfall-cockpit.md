# ADR-0022a: Wasserfall wandert ins Cockpit, Control bekommt Live-Feed

- **Datum:** 2026-11-09
- **Status:** accepted
- **Ergaenzt:** ADR-0022 (Hybrid-UI-Modi)
- **Aendert:** Wasserfall-Zuordnung Control -> Cockpit

## Kontext

ADR-0022 ordnete den horizontalen Wasserfall dem Control-Modus zu
("Control: alles was Aufmerksamkeit braucht, grosse Schrift, wenig
Chrome").

Live-Erfahrung 2026-11-09 (Swimlane-Wasserfall, Commit 1200484):

- Wasserfall aggregiert nach Rolle. Explorer-Lane zeigt 11 Balken,
  aber keine Reihenfolge. "War das Builder->Verify->Builder oder
  alle Builder zusammen?" ist aus dem aggregierten Bild nicht
  ablesbar.
- Wasserfall passt fuer Nachanalyse (wo war der Bottleneck? welche
  Phase dauerte wie lang?), nicht fuer Live-Verfolgung.
- Live-Verfolgung braucht sequenzielle Chronologie: "was laeuft
  jetzt, was kommt als naechstes?"

## Entscheidung

Wasserfall (Swimlane) wird **Nachanalyse-Tool** und lebt im Cockpit
als unterer Bereich unter der Timeline-Liste (max 240px hoch).

Control-Modus bekommt **Live-Feed** (OP-381j, folgt): vertikale
Chronologie, Schritt fuer Schritt, mit pulsierendem aktiven Step.
Kein Gruppieren. "Was macht der Loop **jetzt**?"

Debug-Modus behaelt die gekoppelte Timeline + Audit-Ansicht
(unveraendert).

## Konsequenzen

Positiv:
- Cockpit (ruhig, Nachanalyse) bekommt Wasserfall als Zusatz ohne
  den Blick auf den Verlauf zu verlieren (Timeline-Liste oben,
  Wasserfall unten).
- Control (Live) bekommt was es braucht: Reihenfolge, nicht
  Aggregation.
- Semantik-Trennung ist sauber: Nachanalyse vs. Live-Verfolgung.

Negativ:
- ADR-0022 (accepted) wird durch diesen Nachtrag teilweise
  ausser Kraft gesetzt. Dokumentation muss beide lesen.
- Control hat bis OP-381j (Live-Feed) keine Live-Ansicht mehr —
  nur die alte Timeline-Liste. Uebergangszeit.

## Verwandte OPs

- OP-306 (Mode-Switch) — Basis
- OP-308 (Focus-View Wasserfall) — bleibt fuer Cockpit-Nachanalyse
- OP-381i (Swimlane-Daten) — Backend steht, Frontend umgezogen
- OP-381j (Live-Feed, geplant) — Control-Modus-Hauptansicht
