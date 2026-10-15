# Anti-Pattern-Bibliothek

Zentrale Sammlung bekannter Fehler-Muster der Werkstatt,
ihrer Loesungen und ihrer historischen Anlaesse.

## Zweck

Die Werkstatt soll aus vergangenen Fehlern lernen. Statt
denselben Fehler in jedem neuen Block zu wiederholen,
werden Anti-Patterns einmal dokumentiert und den Rollen
zur richtigen Zeit gezeigt:

- Builder bei Anker-Rueckmeldung (Phase 3b).
- Reviewer bei Bedarf (Phase 3c).
- Solver bei Trigger-Grund (Phase 3c).

Der Katalog ist maschinenlesbar und mit dem Audit-Log
verknuepft, damit die Auswahl nach Relevanz sortiert
werden kann.

## Dateien

- katalog.yaml - die Eintraege (Daten).
- README.md    - dieses Dokument (Format, Pflege).

## Schema pro Eintrag

### Pflichtfelder

- id           str        Eindeutig. Regex ^ap-[a-z0-9-]+$.
- titel        str        Kurzer Name.
- beschreibung str        Was ist das Anti-Pattern?
- loesung      str        Wie vermeidet oder behebt man es?
- begruendung  str        Warum ist es ein Anti-Pattern?
- kategorie    int        1, 2 oder 3. Werkstatt-Kategorien.
- rollen       list[str]  Nicht leer. Aus builder, reviewer,
                          solver, test_generator.

### Optionale Felder

- anlass           list[str]  Historische Anlaesse
                              (Auflage, Datum, Commit).
- audit_kinds      list[str]  Audit-Log-kind-Werte, die auf
                              dieses Anti-Pattern zeigen.
                              Werte muessen in
                              _AUDIT_KINDS_BEKANNT (pipeline.py)
                              stehen.
- trigger_gruende  list[str]  Filter-Werte aus
                              ERLAUBTE_SOLVER_QUELLEN.
                              Leer oder fehlend = Eintrag bei
                              jedem Trigger-Grund sichtbar.

## Top-Level

version: 1
eintraege:
  - id: ap-...
    ...

version ist heute 1. Bei Format-Aenderungen wird sie
erhoeht, der Loader prueft.

## Konsumenten und Filter

Der Loader heisst pipeline.lade_anti_patterns(). Er
liefert die Liste der validierten Eintraege oder bricht
fail-closed ab.

Der Filter heisst pipeline.anti_patterns_fuer(rolle,
trigger_grund=None, limit=3). Er liefert maximal limit
Eintraege, sortiert nach Audit-Haeufigkeit:

1. Nur Eintraege, in denen rolle in rollen.
2. Wenn trigger_grund gesetzt:
   - Eintrag ohne trigger_gruende: immer zeigen.
   - Eintrag mit trigger_gruende: nur, wenn
     trigger_grund enthalten.
3. Sortierung: Summe der Treffer aller audit_kinds
   im Werkstatt-Audit-Log, absteigend.
4. Abschneiden auf limit.

## Audit-Verankerung

Die Werkstatt-Audit-Logs liegen in
/opt/werkstatt/audit-logs/. Das Feld kind ist der
Event-Name. Der Katalog referenziert diese Werte in
audit_kinds.

Die Liste der bekannten Kinds ist in pipeline.py als
_AUDIT_KINDS_BEKANNT definiert. Neuer Kind-Wert im
Audit-Log: die Liste muss erweitert werden, sonst
schlaegt die Katalog-Validierung fehl (fail-closed).

## Pflege

### Neuen Eintrag anlegen

1. id waehlen nach dem Muster ap-<kurzname>.
2. Alle Pflichtfelder setzen.
3. anlass mit mindestens einem konkreten Beleg
   (Auflage, Commit, gemessener Fall).
4. Wenn ein Audit-Kind bekannt ist: in audit_kinds.
5. Wenn nur bei bestimmtem Trigger-Grund relevant:
   trigger_gruende setzen.

### Katalog erweitern

Die Erstbefuellung umfasst 7 Eintraege (Phase 3a-1,
2026-10-15). Weitere Eintraege kommen in Phase 3a-2
(19 Kandidaten aus der Recherche).

Nicht alle Recherche-Kandidaten sind generisch:
Manche sind security-ai-spezifisch. Die Trennung
zwischen Werkstatt-Katalog und projekt-spezifischen
Anti-Patterns ist noch nicht entschieden (siehe
Reviewer-Block 2026-10-15, Frage 6).

### Format aendern

Wenn ein Feld hinzukommt oder entfaellt:

1. version erhoehen.
2. Loader anpassen.
3. Alle bestehenden Eintraege pruefen.
4. Tests anpassen.

## Verwandte Dokumente

- docs/WORKFLOW.md in der Werkstatt - die 2
  Werkstatt-Anti-Patterns (Anker in Dekorator-Kette,
  Patch-Anker ohne Semantik-Pruefung).
- security-ai/docs/WORKFLOW.md - der reichste Bestand
  mit ca. 25 Eintraegen aus der Praxis.
- docs/ROADMAP.md - Ziel 5 (Anti-Pattern-Bibliothek),
  Ziel 6 (Planner-Agent).
