# ADR-0004: Deterministische Drift-Checks als Qualitätsschicht

- **Datum:** 2026-11-03
- **Status:** accepted
- **Kontext:** Zwei Klassen von "stiller Drift" traten wiederholt auf:

  1. **Audit-Katalog-Drift:** `_AUDIT_KINDS_BEKANNT` in `werkstatt/audit.py`
     enthielt Event-Namen die nie aufgerufen wurden, während Code
     `audit("event")`-Aufrufe enthielt die nicht im Katalog standen. Erst
     nach einem Commit sichtbar (Test `test_katalog_enthaelt_alle_code_kinds`
     failt erst im CI). Live-Beleg 2026-11-03: OP-090 und OP-093 führten
     je 1-2 fehlende Events ein, die niemandem auffielen bis der Test failte.

  2. **Kontroll-Registry-Drift (prognostiziert):** Nach Einführung von
     `werkstatt/control/` (ADR-0003) würde jede nicht-registrierte
     Kontrollfunktion unbemerkt an der Registry vorbeilaufen, und jede
     Registry-Kontrolle deren Impl umbenannt wird würde stumm brechen.

**Beide Klassen sind deterministisch prüfbar** — kein LLM nötig, nur AST +
Set-Diff. Warum also nicht automatisch prüfen statt auf Tests zu warten?

## Entscheidung

Zwei deterministische Drift-Check-Tools, gleiches Muster:

### `tools/audit_drift.py`

- **AST-Scan** aller `audit("name", ...)`-Aufrufe in `werkstatt/*.py`
  (nicht Regex — fängt auch `f"..."`-Calls wenn Literal-erkennbar).
- **Katalog-Lesen** aus `_AUDIT_KINDS_BEKANNT`.
- **Set-Diff:** tot (Katalog − Code) + fehlend (Code − Katalog).
- **Klassifikation:** `difflib.get_close_matches` (Ratio ≥ 0.8) unterscheidet
  Tippfehler (→ Vorschlag Katalog→Code) von echtem Drift.
- **Auto-Fix** (`--fix`) nur bei Ratio ≥ 0.9, sonst manuell.
- **CI-Modus** (`--check`): Exit 1 bei Drift.

### `tools/control_drift.py`

- **Registry-Lesen** aus `CONTROL_REGISTRY`.
- **Import-Check:** jede `Control.source` muss auflösbar sein
  (`importlib` + `getattr`).
- **AST-Scan:** alle Kandidaten-Funktionen (Präfix `_check_`, `_verify_`,
  `_gate_`, `_pruefe_`, `_reflection_loop`, `scan_patches`) sammeln, mit
  Registry-Namen vergleichen.
- **CI-Modus** (`--check`): Exit 1 bei gebrochenen Sources oder Dead-Registry.

**Regel:** Beide Tools sind **Pflicht-Befehl vor jedem Commit** (dokumentiert
in `AGENTS.md`) und werden schrittweise in `verify.json` als Stages
eingetragen (OP-094, OP-099).

## Konsequenzen

Positiv:
- Drift wird **vor** dem Commit erkannt, nicht im Test nach dem Commit.
- `--fix` löst Tippfehler in Sekunden statt einem 20-Minuten-Test-Zyklus.
- Entwickler sieht sofort **was** falsch ist (`'loop_human_gate_...' →
  'loop_human_gate_...'`), nicht nur "ein Test failt".
- AST-basiert: erkennt auch dynamische Konstrukte wo Regex blind ist.
- Muster ist erweiterbar: jede zukünftige Registry (Skills, Validators,
  Prompt-Blöcke) kann dasselbe Tool-Muster nutzen.

Negativ:
- Zwei neue Tools zu warten (aber je ~150 Zeilen, stdlib-only).
- `difflib`-Cutoff 0.8 kann bei sehr kreativen Tippfehlern danebenliegen
  (dann kein Auto-Fix, aber Vorschlag fehlt).
- AST-Scan ist anfällig für dynamische `audit(name_var, ...)`-Aufrufe
  (nicht erkennbar). Lösung: Codebase hat aktuell nur String-Literale.
  Wenn dynamische Aufrufe nötig werden, entweder Registry-Feld
  `dynamisch=True` oder AST-Pattern erweitern.

## Alternativen

- **Nur Tests:** Test-Methoden wie `test_katalog_enthaelt_alle_code_kinds`
  sind gut als Sicherheitsnetz, aber laufen erst nach `pytest`. Ein
  Drift-Check im Pre-Commit ist Sekunden statt Minuten. Verworfen
  (beide behalten: Test = Netz, Drift-Check = Frühwarnung).
- **Regex statt AST:** Bricht bei mehrzeiligen Aufrufen, String-Concatenation,
  Kommentaren. Verworfen.
- **Nur `difflib` (kein AST):** Findet Tippfehler, aber nicht "Event fehlt
  komplett". Verworfen.
- **Dynamische Registrierung (Entry-Points):** Overhead. Verworfen.

## Referenzen

- `tools/audit_drift.py` (Commit `c00ef17`)
- `tools/control_drift.py` (Commit `c4bf6b1`)
- AGENTS.md, Sektion "Loop-Kontrollen" + "Pflicht-Befehl"
- OP-094, OP-099
- ADR-0003 (control/-Zentralisierung, Voraussetzung für control_drift)
