# ADR-0019: Gate-Lifecycle-Vertrag statt PID/Heartbeat/Timeout

- **Datum:** 2026-11-08
- **Status:** accepted
- **Ergaenzt:** ADR-0007 (Gate-Bridge)
- **Verworfen:** expire_stale() mit PID-Check, gate_waiting-Heartbeat, 300s-Timeout als Primaermechanismus

## Kontext

ADR-0007 hat Gates per HTTP eingefuehrt: Loop schreibt `gate_open`, wartet auf `gate_answered`. In der Praxis blieben Gates nach Loop-Abbruch ewig offen. Die UI zeigte sie weiter als "offen", obwohl kein Prozess mehr wartete.

Erste Reparatur-Versuche:

1. **PID-Check:** `loop_started`-Event mit PID, `expire_stale()` prueft per `os.kill(pid, 0)`. Bricht bei PID-Recycling, Permission-Races, Containern.
2. **Heartbeat:** `gate_waiting`-Event alle 5s. Reines Busy-Signal, kein State.
3. **Timeout:** 300s. Greift zu spaet, kein klares Kriterium.

Alle drei sind Symptom-Fixerei. Der Loop weiss, wann er endet — er muss es nur sagen.

## Entscheidung

**Lifecycle-Vertrag.**

- `loop.main()` ist in `try/finally` gewrappt. `_main_inner()` enthaelt die Logik.
- `_emit_lifecycle_end(erfolg)` wird im `finally` immer gerufen — bei `return`, Exception, KeyboardInterrupt.
- Es schreibt ein Terminal-Event `loop_ended` (Erfolg) oder `loop_failed` (Exception) und ruft `gate_bridge.expire_for_run(run_id, grund=kind)`.
- `expire_for_run()` schliesst alle offenen Gates des Runs atomar: `gate_expired`-Event pro `gate_id` mit `grund=loop_ended`/`loop_failed`.
- `inspector.aggregate_gate_context` prueft pro Run: wenn ein Terminal-Event existiert (`loop_ended`/`loop_failed`/`loop_crashed`), sind alle Gates des Runs abgebrochen — unabhaengig von EventStore-Inhalt.

SIGKILL bleibt als einzige Luecke. Dort greift das 300s-Netz in `gate_bridge.wait()` als Defense-in-Depth — nicht als Design-Pfad.

## Konsequenzen

Positiv:
- Gate schliesst in Millisekunden (naechster UI-Poll, 2s).
- Kein PID-Check, kein Heartbeat, keine False-Positives durch Prozess-Recycling.
- Loop-Abbruch jeder Art (Ctrl+C, Exception, normaler Exit) wird sauber behandelt.

Negativ:
- SIGKILL ist nicht abgefangen. Akzeptiert — selten, und 300s-Netz existiert.
- Loop-Code muss `try/finally`-Disziplin halten. Neue Endpunkte muessen `_emit_lifecycle_end` bewusst nicht umgehen.

Neutral:
- `gate_bridge.py` reduziert auf `wait`, `signal_open`, `expire_for_run`, `make_gate_id`. Keine 200-Zeilen-Workaround-Kaskade mehr.
