# ADR-0023: Multi-Projekt-Kontext

Datum: 2026-11-08
Status: Accepted
Grundlage fuer: OP-305, OP-306a/b/c

## Kontext

Werkstatt wurde ursprueglich als Single-Project-System gebaut: der Loop
baut Werkstatt, alle UI-Panels (Ambient, Runs, Timeline, Audit, Tokens)
lasen aus `/opt/werkstatt` und der globalen `.werkstatt/events.db`.

Mit OP-305 (Projekt-Anlage-Modal + `+`-Button) wurde Multi-Projekt
erstmals real: User legt via UI ein neues Projekt unter `/opt/<name>`
an. Das legte drei Bugs offen, die alle dieselbe Ursache hatten:

1. `/ops` rief `parse_ops()` ohne Argument — las immer
   `/opt/werkstatt/docs/STATUS.md`, zeigte also Werkstatt-OPs in
   fremden Projekt-Tabs.
2. `/start` startete den Loop ohne Projekt-Existenz zu pruefen — ein
   versehentlicher `POST /start` mit `op_id="OP-260"` haette den Loop
   mit falscher Aufgabe im falschen Verzeichnis gestartet.
3. `parse_ops()`-Backend hatte `Path("/opt")` hardcoded — untestbar
   ohne das echte Verzeichnis.

## Entscheidung

Drei Regeln.

### 1. Projekt-Pfad-Basis ist eine testbare Konstante

`werkstatt/web/app.py` und `werkstatt/web/inspector.py` deklarieren:

    _PROJECTS_BASE = Path("/opt")

Alle Stellen, die einen Projekt-Pfad bauen, nutzen:
`_PROJECTS_BASE / projektname`.

Tests monkeypatchen `_PROJECTS_BASE` auf `tmp_path`. Kein hartes
`Path("/opt")` im Produktivcode mehr.

### 2. `/start` validiert Projekt-Existenz

`POST /api/projects/{name}/start` prueft vor dem `subprocess.Popen`:

    _pd = _PROJECTS_BASE / projektname
    if not (_pd / "docs" / "STATUS.md").is_file():
        raise HTTPException(status_code=404, ...)

Ohne `docs/STATUS.md` gibt es keine sinnvolle Aufgabe — der Loop
wuerde ins Leere laufen. 404 statt Silent-Fehler.

### 3. Projekt-spezifische Datenquellen sind pro Endpoint

- `/ops` liest `parse_ops(_PROJECTS_BASE / projektname)`.
- `aggregate_palette(projekt)` liest `parse_ops(_PROJECTS_BASE / projekt)`.
- `/ambient`, `/status`, `/timeline`, `/tokens`: **noch nicht**
  projekt-gefiltert (SQLite hat keine `project`-Spalte). Eigene OP.

## Konsequenzen

Positiv:

- Kein falscher Loop-Start mehr (404 statt Silent).
- Runs-Liste zeigt echte OPs des aktiven Tabs.
- Palette ist projekt-aware.
- Backend testbar ohne echte Verzeichnisse.

Negativ / offen:

- SQLite-Events sind noch global. `/ambient`, `/status`, `/timeline`,
  `/tokens` zeigen Werkstatt-Daten in fremden Tabs. Loesung: OP-306c
  (SQLite-`project`-Spalte + Migration + Filterung in allen
  Aggregatoren).
- Tabs sind nicht persistent (Reload → weg). Loesung: OP-306a
  (localStorage).
- Projekt-Selector fuer existierende Projekte fehlt. Loesung:
  OP-306b (`GET /api/projects/list`).

## Nicht-Ziele

Keine Tab-Persistenz hier (OP-306a). Keine SQLite-Migration hier
(OP-306c). Kein `projects/<name>.yaml`-Auto-Write (Loop faellt auf
`/opt/<name>` zurueck, funktioniert).

## Referenzen

- OP-305 (Projekt-Anlage-Modal + `_PROJECTS_BASE`)
- OP-306a (Tab-Persistenz)
- OP-306b (Projekt-Selector)
- OP-306c (Multi-Projekt-Datenquellen / SQLite-Migration)
