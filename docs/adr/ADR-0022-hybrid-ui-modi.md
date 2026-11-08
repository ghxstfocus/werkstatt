# ADR-0022: Hybrid-UI-Modi (Cockpit / Control / Debug)

- **Datum:** 2026-11-08
- **Status:** accepted
- **Ergaenzt:** ADR-0009 (Timeline primaer, Layout A)
- **Verworfen:** Monolithisches Single-Mode-Layout

## Kontext

Das Web-UI hat heute drei feste Spalten (Runs / Timeline / Chat) plus
Workbench-Drawer. Diese Struktur ist funktional, aber sie skaliert
weder nach unten (User will nur Status sehen, wird von drei Spalten
erschlagen) noch nach oben (User will einen laufenden Run im Detail
verfolgen, kann aber die Spalten nicht umschichten).

Zwei User-Typen kollidieren:

- **Cockpit-Typ**: will ruhige, minimale Anzeige. „Das System macht
  das schon, ich greife nur ein wenn noetig." Ambient presence statt
  Aufmerksamkeit.
- **Kontrollraum-Typ**: will dichte Information, alle Panels
  gleichzeitig, Farb-kodiert, Filter, Detail. „Ich habe die Kontrolle."

Ein Single-Mode-Layout bedient immer nur einen Typ. Der andere muss
sich anpassen oder wird nicht bedient.

Vorbilder aus der Branche:
- Claude Code: reines Terminal, immer gleich
- Cline/Cursor: immer Chat + Code nebeneinander
- VS Code: Sidebar-Toggle (nur Groesse)
- Devin: Kanban (nur Run-Liste)
- Linear: 2 Layouts (Liste + Board)

Kein System wechselt die **semantische Rolle** der UI-Elemente.

## Entscheidung

**Drei explizite UI-Modi, manuell waehlbar, persistent.**

| Modus | Wann | Was sichtbar | Was versteckt |
|---|---|---|---|
| **Cockpit** (default) | Kein aktiver Run / Idle | 3 Spalten wie heute, Ambient Bar oben, Kalender eingeklappt | Detail-Panels, Multi-Run-History |
| **Control** | Run laeuft / aktives Verfolgen | Horizontaler Phasen-Wasserfall, Chat schwebend, Runs-Liste schmal | Kalender, alte Runs, Session-History |
| **Debug** | Fehlersuche | Timeline + Audit gekoppelt (Klick → Scroll), keine Runs-Liste | Kalender, History |

**Wechsel:**
- `Shift+Space` zyklisch durch die 3 Modi
- Command Palette (`⌘K`) → „mode cockpit" / „mode control" / „mode debug"
- URL-Parameter `?mode=cockpit` (Deep-Link)
- localStorage persistiert

**Semantik je Modus:**
- Cockpit: alles was Ruhe braucht, ohne Ablenkung
- Control: alles was Aufmerksamkeit braucht, grosse Schrift, wenig Chrome
- Debug: alles was Analyse braucht, zwei Ansichten synchronisiert

**Discoverability-Pflicht:**
- Mode-Name oben links sichtbar
- `?`-Overlay zeigt alle Shortcuts
- Jeder Mode-Wechsel ist auch per Maus klickbar (Dropdown oben)

## Konsequenzen

Positiv:
- Cockpit-Typ und Kontrollraum-Typ sind beide bedient — jeder bekommt
  „sein" UI.
- Default Cockpit ist ruhig. Wer mehr will, schaltet selbst um.
- Focus (Control) ist der Beweis dass die UI „wach" sein kann — im
  Gegensatz zu ruhigem Cockpit.
- Drei spezifische Layouts sind einfacher zu bauen und zu testen als
  ein komplexes responsives Grid.

Negativ:
- Drei Layouts warten statt eins. Neue Features muessen in jedem Modus
  einen Platz finden (oder bewusst versteckt sein).
- State-Management: Mode-Persistenz, Guard bei Mode-Wechsel waehrend
  eines laufenden Runs.
- Nutzer die Control nie entdecken verpassen die Dichte.

Neutral:
- Farb-Semantik (6 Farben) ist Vorbedingung: alle 3 Modi nutzen
  dieselbe Farbsprache.
- Ambient Bar (Status oben) ist in allen Modi sichtbar — identitaets-
  stiftendes Element.

## Verwandte OPs

- OP-300 (Semantic Colors) — Vorbedingung
- OP-301 (Ambient Status Bar) — Vorbedingung
- OP-306 (Mode-Switch) — Implementierung
- OP-308 (Focus-View Wasserfall) — Control-Modus
- OP-309 (Chat schwebend) — Control-Modus
- OP-311 (Audit-Filterleiste) — Debug-Modus
