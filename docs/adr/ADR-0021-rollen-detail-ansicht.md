# ADR-0021: Rollen-spezifische Detail-Ansicht im Chat-Drawer

- **Datum:** 2026-11-08
- **Status:** accepted
- **Ergaenzt:** ADR-0008 (Chat als eigener Agent)

## Kontext

Der Detail-Drawer hatte fuenf statische Tabs: Plan, Evidence, Handoffs, Plan-Diff. Klick auf eine Timeline-Zeile (Builder, Reviewer, Verify) zeigte immer dasselbe: die Explorer-Evidence. Der User konnte nicht sehen, was der Reviewer tatsaechlich geschrieben hat, welche Patches der Builder erzeugt hat, welche Stages im Verify liefen.

Der Rollen-Kontext ging verloren. Die Timeline wusste ihn (Gruppe = Rolle), der Drawer ignorierte ihn.

## Entscheidung

**Dynamischer Rollen-Tab.**

- Neuer Endpoint `GET /api/projects/{name}/role/{rolle}` liefert alle Events einer Rolle im aktuellen Run (Payload vollstaendig).
- `inspector.aggregate_role_events(projekt, rolle, run_id)` filtert die Audit-Events nach Rollen-Praefix (`builder_`, `reviewer_`, `verify_`, `explorer_`, etc.).
- Frontend `WerkstattDetail.oeffneRolle(rolle)` baut einen dynamischen Tab `__rolle__` in der Tab-Liste.
- Klick auf Timeline-Kind ruft `oeffneRolle(rolle)` mit der Rolle aus der Gruppen-Zuordnung.
- Klick auf Gruppen-Summary klappt nur die Gruppe auf, oeffnet **keinen** Drawer.
- Der Rollen-Tab bleibt sichtbar, auch wenn der User auf Evidence/Plan wechselt. Klick auf den Rollen-Tab kehrt zum letzten Rollen-Kontext zurueck.

## Konsequenzen

Positiv:
- Builder-Klick zeigt Builder-Payloads (Patches, Datei-Kontexte, Zieldatei).
- Reviewer-Klick zeigt Reviewer-Verdict und Review-Text.
- Verify-Klick zeigt Stages, Skip-Gruende, Fehler.
- Rollen-Kontext ist persistent (Memory im Tab).

Negativ:
- Ein Tab mehr in der Drawer-Leiste (dynamisch, aber sichtbar).
- `__letzteRolle` ist global im `window` — State-Management nicht ideal, aber funktional.

Neutral:
- Der Endpoint ist pro Rolle. Neue Rollen (`architect`, `scout`) sind im Backend schon vorbereitet.
