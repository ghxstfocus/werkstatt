# ADR-0012: Vier Strukturmuster als Ursache fuer Multi-File-Failure

- **Datum:** 2026-11-04
- **Status:** accepted
- **Kontext:** Die Session 2026-11-04 hat drei Multi-File-OPs
  (OP-111, OP-114, OP-122) mit manuellen Eingriffen abgeschlossen.
  OP-122 brauchte 3 manuelle Fixes (F821 Import, Signatur-Mismatch,
  fehlende `set_run_id`-Initialisierung) und 1 manuellen Smoke-Test.
  Eine nachfolgende Analyse (Explorer/AST) hat zwei falsche
  Hypothesen aufgedeckt, bevor die echte Ursache klar wurde.

**Fragestellung:** Warum scheitert der Loop an Multi-File-Tasks,
und welche strukturellen Muster verursachen die wiederkehrenden
Failure-Mode?

**Vier identifizierte Muster:**

**Muster 1 — Re-Export-Kaskaden als Zirkularitaets-Loeser.**
`loop.py` ist CLI-Einstieg UND Re-Export-Hub (`run_explorer`,
`_human_gate_plan`, `run_reviewer`, `_with_spinner`, `audit`,
`time`). `pipeline_phases.py` enthaelt Late-Binding-Proxies
(`def run_explorer(): from .loop import run_explorer`). `scout.py`
proxyt auf `planner.py`. Folge: kein Modul kennt seine echten
Abhaengigkeiten, der `__all__`-Block ist ungepflegt (13 ruff-Fehler
in `loop.py` mit toten `_Path`, `_UTC`, `_load_cfg`-Eintraegen).

**Muster 2 — Gott-Objekte.**
`RunState` (state.py) hat 100+ Felder, keine Doku zu Schreiber/Leser.
`pipeline_phases.py` (1600 Zeilen) mischt Phase-Orchestrierung,
Re-Export-Proxies, `_with_spinner`-Proxy, `run_reviewer`-Proxy.
`loop_renderer.py` (900 Zeilen, 18 oeffentliche Funktionen) mischt
Emit, Progress, Task, Spinner, Tee, Rich, Plan-Rendering.
`_with_spinner` hat 5 Sorgen: Thread, Spinner, Events, Elapsed,
Logging.

**Muster 3 — Implizite Datenvertraege.**
`explorer_context` (33 Dateien + Previews) und `explorer_findings`
(git_dirty, pytest_laufzeit) klingen aehnlich, enthalten aber
voellig Verschiedenes. `architect.py:385` liest `explorer_findings`
statt `explorer_context` — niemand merkt es, weil nichts prueft,
ob der Architect tatsaechlich Dateien sieht. `api_index_cache` wird
in `architect.py` gebaut, aber nie in den Prompt gehaengt (toter
Cache). Handoff §7 nennt 47 weitere tote `RunState`-Felder.

**Muster 4 — Layer-Verletzungen.**
Rollenen (builder, architect, reviewer) greifen direkt auf `_publish`,
`audit`, `paths`, `event_store` zu. Es gibt keine Regel, die sagt:
"Der Builder darf `event_store` nicht kennen." Folge: Aenderungen
an Infrastruktur ziehen Aenderungen an Rollen nach sich, oft
unbemerkt bis zum Test-Lauf.

## Entscheidung

**Alle vier Muster werden adressiert**, aber nicht in einem
Big-Bang-Refactor. Die Reihenfolge folgt dem MERKPOSTEN-Prinzip
"erst messen, dann designen, dann fixen":

- **OP-134 (State-Inventur):** MESS-OP. Datenbasis fuer Muster 3.
- **OP-135 (State-Contract-Design):** Dataclasses + Registry.
- **OP-136 (Contract-Validierung):** Fail-loud in Pipeline.
- **OP-137 (Fix architect.py):** Konkreter Bug aus dem Mess-Ergebnis.
- **OP-138..143 (Submodul-Splits):** Muster 1, 2, 4.
- **OP-144 (import-linter):** Erzwingt Muster-4-Regeln mechanisch.

Details in ADR-0013.

## Konsequenzen

Positiv:
- Strukturelle Ursachen benannt statt Symptome.
- Splits in kleiner Reihenfolge, jeder einzeln testbar.
- Mess-OP zuerst, keine Blind-Refactors.

Negativ:
- Multi-Session-Arbeit (8-12 Sessions).
- Re-Export-Aufraeumen bricht 20+ Tests (Tests patchen
  `werkstatt.loop.audit` etc.) — bewusste Entscheidung mit
  Test-Anpassungen.
- `import-linter` als neue Verify-Stage muss initial viele
  bestehende Verletzungen ignorieren (Whitelist), dann schrittweise
  schaerfer werden.

Neutral:
- Der Loop bleibt waehrend der Splits funktionsfaehig. Kein
  Big-Bang.
