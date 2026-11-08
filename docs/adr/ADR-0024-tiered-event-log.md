# ADR-0024: Tiered Event Log + Projector (CQRS-light)

Datum: 2026-11-08
Status: Accepted
Grundlage fuer: OP-321..323

## Kontext

Zwei Event-Systeme, historisch gewachsen, gemessen divergent (OP-319):

    System                  Events    Kinds   Runs   Ziel
    audit() -> JSONL        32804     320     267    semantisch
    _publish() -> SQLite    374353    10      5290   Live-UI

    Schnittmenge: 0 Kinds, 25 Runs.

Kein gemeinsamer Commit, keine atomare Garantie. Das ist Dual-Write --
von Confluent, Microsofts CQRS-Pattern und AutoMQ als Ursache stiller
Divergenz benannt.

## Entscheidung

Drei Ebenen mit klaren Rollen.

### 1. Write Model -- zwei JSONL-Streams

    Stream     Datei                                  git      Inhalt
    Semantic   audit-logs/semantic-YYYY-MM-DD.jsonl   ja       loop_*, builder_*, reviewer_*, gate_*, pipeline_start, summary, explorer_*
    Stream     audit-logs/stream-YYYY-MM-DD.jsonl     nein     log_line, progress, spinner, heartbeat, task_started, task_done

Zuordnung in werkstatt/audit.py::_STREAM_KINDS. Fail-closed: unbekannter
Kind geht in Semantic.

### 2. Writer -- zwei Funktionen, ein Pfad

    Funktion                  Ziel       Verbietet
    audit(kind, payload)      Semantic   -
    stream(kind, payload)     Stream     -
    EventStore().append()     -          aus Production verbannt

Beide bauen dasselbe JSON-Schema mit
event_id = sha256(run_id + seq + kind + ts)[:16].

### 3. Read Model -- SQLite, rebuildbar

werkstatt/projection.py::Projector:

    rebuild(von_seq=0)   alle JSONL -> SQLite, idempotent
    tail()               ab Checkpoint, inkrementell
    status()             {jsonl_events, sqlite_rows, diff, last_checkpoint}

SQLite-Schema: events(event_id UNIQUE, ...) mit INSERT ... ON CONFLICT
IGNORE. Checkpoint-Tabelle projection_state(key, value).

Kern-Regel: SQLite wird ausschliesslich vom Projektor beschrieben.

## Konsequenzen

Positiv:

- Single-Writer. JSONL ist die Wahrheit, SQLite ist Ableitung.
- Rebuildbar. DELETE events.db + rebuild() rekonstruiert identisch.
- Git-freundlich. 30k statt 374k Events im Repo, log_line bleibt draussen.
- Vollstaendige Timeline. loop_erfolg, pipeline_start, gate_* jetzt sichtbar.
- Temporal queryable. Events haben ts, run_id, seq, event_id.

Negativ:

- rebuild() dauert Sekunden bis Minuten bei 30k+ Events.
- Neue Kinds muessen in _STREAM_KINDS deklariert werden (fail-closed).
- Ein Umstellungstag: alte SQLite bleibt bis rebuild() gruen, dann Wechsel.

Risiko-Mitigation:

- Alte SQLite bleibt unangetastet bis db_hash_identisch() nach Doppel-Rebuild.
- Bei Fehler: alte DB zurueck, kein Datenverlust.
- Divergenz > 0 = sichtbarer Alarm in Status-Bar (OP-323).

## Nicht-Ziele

Keine Aenderung existierender JSONL-Dateien. Kein History-Rewrite. Kein
externer Broker. Keine Schema-Versionierung (eigene OP spaeter).

## Referenzen

- Confluent: Using logs to build a solid data infrastructure (or: why
  dual writes are a bad idea)
- Microsoft Cloud Design Patterns: CQRS
- AutoMQ: durable, ordered, replayable for investigations
- Aevatar Station: event-sourced agent orchestration
- OP-319-Messung (2026-11-08)
