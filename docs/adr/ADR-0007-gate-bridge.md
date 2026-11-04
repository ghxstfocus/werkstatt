# ADR-0007: Gate-Bridge — Loop headless, Gates ueber HTTP

- **Datum:** 2026-11-04
- **Status:** accepted
- **Kontext:** Der Loop ruft Gates (`_human_gate_plan`,
  `_human_gate_body`) heute direkt mit `input()`. Das zwingt jeden
  Lauf in den Vordergrund eines Terminals. Ein Browser-Betrieb ist
  nicht moeglich: Entweder pollt die UI nach Freitext-Antworten im
  Terminal-Log (fragil), oder der Loop laeuft als Job und braucht
  einen Weg, auf Antworten zu warten, ohne stdin.

**Fragestellung:** Wie fragt ein headless Loop einen Menschen nach
`j`/`n`/`a`, und wie kommt die Antwort zurueck?

**Optionen:**

A) Loop bleibt CLI-only; Browser startet Terminal-Sessions via PTY
   (so heute via `terminal_proxy`).
B) Loop laeuft headless als Job; Gates sind HTTP-Endpoints; ein
   `gate_bridge.wait(run_id, gate_id)` blockiert bis Antwort.

## Entscheidung

**Option B — Gate-Bridge.**

- `werkstatt/gate_bridge.py` mit `wait(run_id, gate_id, timeout=300)`.
- `--headless`-Flag im CLI. Bei gesetztem Flag ruft
  `_human_gate_plan` `gate_bridge.wait()` statt `input()`.
- `POST /api/runs/{id}/gate {gate_id, answer}` beantwortet.
- `GET /api/runs/{id}/gates` listet offene Gates (UI-Buttons).
- Timeout (300 s) → fallback auf fail-closed (Reflection/Abbruch).

**Begruendung:** Reproduzierbarkeit (Run als Job), Multi-Client
(zwei Browser-Tabs sehen dasselbe Gate), und Auditierbarkeit
(jede Antwort ist ein Event). PTY-Ansatz (A) bleibt als Fallback,
wenn `--headless` nicht gesetzt ist — niemand verliert den
Terminal-Workflow.

## Konsequenzen

Positiv:
- Browser-Buttons ersetzen `input()` sauber.
- Runs sind Jobs, nicht Sessions.
- Gate-Antworten landen im Event-Store (audit-fest).

Negativ:
- Loop-Kern wird um HTTP-Wartepunkt erweitert — Fehlerquelle.
- Zwei Pfade (`input()` und `gate_bridge`) muessen konsistent bleiben.

Neutral:
- Timeout-Verhalten muss dokumentiert und getestet werden.
