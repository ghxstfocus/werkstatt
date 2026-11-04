# ADR-0009: Timeline primaer, Chat rechts sichtbar (Layout Variante A)

- **Datum:** 2026-11-04
- **Status:** accepted
- **Kontext:** Das aktuelle UI ist ein 2x2-Grid: Terminal links oben,
  Chat rechts oben, Audit rechts unten. Das Terminal zeigt CI-Roh-
  Ausgabe mit `::log::`-Prefixen und doppelten Zeilen. Es fehlt eine
  sichtbare Phasen-Struktur. Der Chat ist zwar vorhanden, aber ohne
  Kontext (kein Hinweis auf Runs, Tools, oder aktuellen Zustand).
  Drei Layout-Varianten wurden diskutiert (A: Chat rechts + Workbench-
  Drawer; B: Tabs; C: Chat-Overlay).

**Fragestellung:** Welches Layout macht die Werkstatt-Streke (Rollen,
Gates, Audit) sichtbar, ohne den Chat zu verstecken?

**Optionen:**

A) Runs links, Timeline Mitte, Chat rechts (immer sichtbar),
   Workbench als Collapsible Drawer.
B) Runs links, Timeline Mitte, Tabs rechts (Chat ODER Workbench).
C) Runs links, Timeline voll, Chat als Overlay.

## Entscheidung

**Option A.**

- **Links (200 px):** Runs-Liste pro Projekt mit Status-Indikatoren.
- **Mitte (flex):** Timeline mit Phasen-Knoten (Explorer, Scout,
  Architect, Planner-Split, Builder tN, Reviewer tN, Reflection,
  Verify, Gate). Aktiver Knoten mit Spinner, Fehler rot, aufklappbar
  mit I/O-Details (was gelesen, welcher Prompt, welche Patches).
- **Rechts (400 px):** Chat immer sichtbar.
- **Unten:** Status-Leiste (Tasks, Verify, Drift, Budget, aktive Phase).
- **Workbench:** Collapsible Drawer (default zu), Tabs [Dateien]
  [Diff] [Verify] [Audit] [Terminal].

**Begruendung:** Die Werkstatt ist ein **Phasen-Loop**, kein Chat-
Agent. Die Timeline ist die Hauptflaeche; der Chat ist Assistent
*neben* dem Loop. Chat und Timeline nie gleichzeitig zu zeigen
(Variante B) versteckt entweder die Arbeit oder den Assistenten.
Overlay (C) macht beides schwer zugaenglich.

**Style:** bleibt wie im Screenshot (dunkel, lila Akzente,
schlicht). Keine Framework-Migration, kein Redesign.

## Konsequenzen

Positiv:
- Rollen-Struktur wird sichtbar (das ist der Unterschied zu
  Claude Code / Cursor).
- Chat ist immer erreichbar, ohne die Timeline zu verdecken.
- Workbench bleibt verfügbar, aber nicht permanent im Weg.

Negativ:
- Chat bei 400 px Breite ist eng fuer lange Tool-Outputs.
- Drawer-Konzept braucht saubere State-Verwaltung (welcher Tab
  offen, welche Datei ausgewaehlt).

Neutral:
- Die `terminal_proxy`-Ansicht bleibt als Workbench-Tab erhalten
  (niemand verliert CI-Debugging).
