# Werkstatt

Werkstatt ist eine projektbezogene Agenten- und Entwicklungsumgebung fuer
mehrere Projekte. Der Chat ist der zentrale Ansprechpartner: Er untersucht
das aktive Repository, erklaert Befunde, nimmt Auftraege an und kann den
Loop nach einer konkreten Freigabe steuern.

Der Loop nutzt spezialisierte Rollen und deterministische Verify-Schritte.
Das verpflichtende Plan-Gate und das Ergebnis-/Review-Gate bleiben
menschlich. Lang laufende Runs und Chat-Diagnosen muessen sich gegenseitig
nicht blockieren.

## Aktueller Arbeitsstand

- Die Web-UI bietet eine Projektuebersicht und die Modi Cockpit, Control,
  Debug sowie Runs.
- Control zeigt den Live-Feed; Cockpit dient der Zusammenfassung und
  zeitlichen Einordnung; Debug ist fuer Diagnose und Fehlerbehebung.
- Der Chat arbeitet im Projektkontext. Schreibende Aktionen brauchen eine
  konkrete Freigabe; diese ersetzt kein Loop-Gate.
- STATUS enthaelt die aktuelle, startbare Arbeitsqueue. ROADMAP beschreibt
  Fokus und spaetere Phasen. PROGRESS dokumentiert abgeschlossene Arbeit.
- Lokale Serverprojekte sind vorhanden. GitHub-Projektquellen und
  projektbezogene Modellwahl sind geplante Arbeit in OP-399/OP-400; ADR-0030
  ist vorgeschlagen und noch keine angenommene Implementierungsentscheidung.

## Installation

Python 3.11 oder neuer wird vorausgesetzt.

    cd /opt/werkstatt
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

Der Loop kann aus dem Repository gestartet werden:

    python3 -m werkstatt.loop --project <projekt> --aufgabe "<konkreter Auftrag>"

Fuer die Weboberflaeche:

    python3 -m werkstatt.web --host 0.0.0.0 --port 8001

API-Schluessel gehoeren in die serverseitige Umgebung oder eine lokale
.env-Datei und duerfen nicht eingecheckt werden. Siehe werkstatt/env_loader.py.

## Architektur und Leitplanken

Die Rollen-Pipeline ist im Loop deterministisch orchestriert. Explorer und
Scout sammeln Kontext; Architect und Planner formen einen begrenzten Plan;
Builder erstellt Aenderungen; Verify und Reviewer pruefen sie; Reflection
behandelt fehlgeschlagene Versuche. Rollenrouting und Modell-Defaults stehen
in werkstatt/model_routing.py und werkstatt/rollen.py.

Der Chat ist ein paralleler, projektgebundener Kontroll- und Diagnosepfad.
Er kann Repository-Fragen beantworten, Hintergrundjobs begleiten und
bestaetigungspflichtige Aktionen vorschlagen. Er darf weder ein Gate
ueberspringen noch einen bereits freigegebenen Plan still aendern.

Architekturentscheidungen stehen in docs/adr/. Nur ADRs mit Status
accepted sind bindend. Vorschlaege bleiben offen, bis sie angenommen
oder verworfen werden.

## Projekt-Dokumentation

| Datei | Zweck |
|---|---|
| AGENTS.md | Arbeitsregeln fuer Agenten und Entwickler |
| docs/ROADMAP.md | aktueller Fokus und spaetere Phasen |
| docs/STATUS.md | offene, startbare OPs |
| PROGRESS.md | append-only Verlauf abgeschlossener/verworfener Arbeit |
| docs/DOC_CONVENTIONS.md | Format- und Pflegevertrag |
| docs/ARCHITECTURE.md | implementierte Systemarchitektur |
| docs/adr/ | Architekturentscheidungen mit Status |

## Entwicklung und Verify

    source .venv/bin/activate
    python -m pytest -q
    python -m ruff check . --output-format concise
    python -m tools.quality_gate --json

Die verbindliche Verify-Konfiguration liegt in .werkstatt/verify.json.
Die Quality Gate-Ausgabe ist massgeblich fuer den jeweiligen getesteten
Commit; README-Zahlen werden daher nicht als bewegliche Test-Baseline gepflegt.

## Abgrenzung

Werkstatt ist keine automatische Freigabemaschine. Der Nutzer bleibt fuer
Plan und Ergebnis an den vorgesehenen Gates beteiligt. Remote-Schreiben,
Push und Merge brauchen jeweils eine eigene Freigabe.
