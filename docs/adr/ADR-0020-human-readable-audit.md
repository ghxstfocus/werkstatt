# ADR-0020: Human-Readable Audit-Trail im Frontend

- **Datum:** 2026-11-08
- **Status:** accepted

## Kontext

Das Audit-Panel zeigte Roh-JSON pro Event. Der User konnte die 143 Events eines Tages nicht lesen — `plan_text="## ..."`, `run_id="test-ui-..."`, `anzahl=1 begriffe=[...]`. Bei unbekannten Kinds fiel der Renderer auf `key=value`-Format zurueck.

Zwei Anforderungen kollidieren:

1. **Payload-Vollstaendigkeit:** Debugging braucht alle Felder. `audit_id`, `run_id`, `timestamp` sind relevant.
2. **Mensch-Lesbarkeit:** Der normale UI-Nutzer will "Plan an Mensch gezeigt (3087 Zeichen)", nicht `plan_text="..." plan_laenge=3087`.

## Entscheidung

**Frontend-Routing pro Kind.**

- Neue JS-Funktion `_humanSummary(ev)` in `static/audit.js` mappt jeden bekannten Kind auf einen Satz.
- Pro Kind eine Regel. Beispiele:
  - `loop_fresh_reset` → "Frischer Start (bak gespeichert)"
  - `loop_explorer_suchbegriffe` → "N Begriffe: a, b, c"
  - `planner_architect_ok` → "Architect: N Zeichen Prosa"
  - `builder_patches_erstellt` → "N Patches erstellt"
  - `loop_verify_stage_skipped` → "Verify-Stage uebersprungen: pytest_changed (no changed files)"
- Fallback fuer unbekannte Kinds: kompaktes `key: value`-Format, keine Anfuehrungszeichen um Strings.
- `run_id`/`audit_id`/`timestamp`/`agent`/`project`/`kind` werden aus dem Fallback gefiltert (System-Felder).
- Das Backend bleibt neutral: liefert vollstaendiges JSON. Anzeige ist Frontend-Verantwortung.

## Konsequenzen

Positiv:
- Audit-Panel ist lesbar.
- Neue Kinds erfordern einen Eintrag in `_humanSummary` — bekannt, dokumentiert.
- Payload-Daten bleiben unveraendert (Debugging per Raw-API weiter moeglich).

Negativ:
- `_humanSummary` ist eine wachsende Funktion. Bei 100+ Kinds wird sie zum Mapping-Table.
- Zweite Quelle fuer Anzeige-Wissen (Backend `kind` + Frontend `_humanSummary`).

Neutral:
- Kein Test erzwingt, dass jeder neue Kind einen `_humanSummary`-Eintrag hat. Manueller Prozess.
