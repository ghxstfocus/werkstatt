# ADR-0006: Event-Store als SSOT fuer Loop-Events

- **Datum:** 2026-11-04
- **Status:** accepted
- **Kontext:** Der Loop schreibt heute zwei Formate parallel: eine
  JSONL-Datei (`audit-logs/*.jsonl`) fuer den Audit-Trail und eine
  Render-Log-Datei (`logs/loop-render-*.log`) fuer den Menschen. Die
  Web-UI pollt die Render-Log-Datei und dedupliziert per Regex. Das
  fuehrt zu bekannten Artefakten: doppelte Zeilen, `::log::`-Prefixe
  im sichtbaren UI, Races zwischen Schreiber und Leser. Eine
  Timeline, ein Inspector oder ein Replay sind auf dieser Basis nicht
  sauber baubar.

**Fragestellung:** Was ist die Primaerquelle fuer Loop-Events, aus der
UI, Timeline, Inspector, Cost-Dashboard und Memory-Injektion lesen?

**Optionen:**

A) JSONL bleibt SSOT, UI aggregiert im Frontend. Kein neues Modul.
B) SQLite-Event-Store als SSOT, JSONL bleibt als Export-Format.

## Entscheidung

**Option B — SQLite-Event-Store.**

- Neue Tabelle `events(seq, run_id, ts, kind, phase, status, payload)`.
- `_publish()` schreibt primaer in den Store, JSONL bleibt Export
  (Kompatibilitaet fuer Tools, die noch Dateien lesen).
- `GET /api/runs/{run_id}/events?since_seq=N` ist der einzige Weg,
  wie die UI an Events kommt. Kein Polling von Log-Dateien.

**Begruendung:** Die Audit-Erfahrung aus 30.288 Events (OP-113i) zeigt,
dass strukturierte Events die Grundlage fuer Clustering, Matching und
Timeline sind. JSONL-Polling kann das nicht leisten. SQLite ist
verfuegbar, dependency-frei, und querybar ohne Zusatz-Service.

## Konsequenzen

Positiv:
- Timeline, Inspector, Cost-Dashboard lesen aus einer Quelle.
- Races entfallen; `since_seq` macht Inkremental-Updates billig.
- Replay/Fork werden moeglich (Run-ID + Sequenz).
- Bestehende JSONL-Tools bleiben funktional (Export).

Negativ:
- Zwei Schreiber-Pfade muessen synchron gehalten werden (Store +
  Export) — Fehlerquelle, wenn Export scheitert.
- SQLite-Datei muss in Backups (`.werkstatt/*.db`).

Neutral:
- `_publish()`-Signatur bleibt gleich; Store ist ein neuer Sink.
