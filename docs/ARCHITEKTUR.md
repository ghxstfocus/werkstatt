# Architektur — Werkstatt

Stand: 2026-10-25 (nach M-472, ADaPT).
Technische Architektur des aktuellen Loops.
Zielbild: `NEUBAU-ZIELBILD.md`. Roadmap: `ROADMAP.md`.
Historische Architektur (6 Rollen, W-Blöcke): siehe
Abschnitt "Archiv" am Ende.

## 1. Ziel-Architektur

Die Werkstatt ist ein Multi-Agent-System mit
**5+1 Rollen** und **ADaPT (On-Demand-Zerlegung)**.
Der Mensch ist das letzte Gate.

```
Explorer -> Architect -> Planner-Split -> Builder -> Verify -> Reviewer -> Human-Gate
   (read)    (Prosa)     (JSON-Tasks)     (search/repl)  (ruff/pytest)  (Bug-Check)
                                                             |
                                                             v (bei Fehler)
                                                         ADaPT (Split in 2-3 Sub-Tasks)
```

## 2. Rollen

### 2.1 Explorer (`werkstatt/explorer.py`)

Read-only Subagent. Messt deterministisch (`ruff check .`,
`pytest -q`) und liefert `key_files` aus der Messung.
M-396: Explorer läuft immer, auch bei expliziten Dateien.
M-373: `_messen()` + `_extract_dateien()`.

### 2.2 Architect (`werkstatt/planner.py`, Prosa-Modus)

deepseek-reasoner. Keine Skills, keine Tools (M-446).
Produziert Prosa mit numerierten Schritten (M-462).
Max 16000 Tokens (M-447).

### 2.3 Planner-Split (`werkstatt/planner.py`, JSON-Modus)

deepseek-chat. Zerlegt die Architect-Prosa in Tasks mit
`architect_start`/`architect_ende` (wörtliche Marker, M-461).
Rekursiv, max 2 Ebenen (M-469/M-470/M-471).

### 2.4 Builder (`werkstatt/builder.py`)

deepseek-chat. search/replace pro Task. Bekommt den wörtlichen
Architect-Abschnitt (M-461). `_architect_abschnitt` gibt leeren
String zurück, wenn die Datei nicht in der Prosa ist (M-450).

### 2.5 PreToolUse-Hook (`hooks/pre_tool_use.py`)

AST-basierte Import-Validierung (M-334a). Blockt erfundene
Imports deterministisch.

### 2.6 Verify (`_verify_patches` in `loop.py`)

verify.json-Stages: `py_compile_changed`, `ruff_changed`,
`pytest_changed`, `py_compile_core`, `pytest_full_checks`
(phase_end, M-476: nach human_gate).

### 2.7 Reviewer (`werkstatt/reviewer.py`)

deepseek-chat. Prüft die Task-Description, nicht die
Gesamtaufgabe (M-459). Bekommt den vollen Diff (M-448).

### 2.8 Human-Gate (`_human_gate` in `loop.py`)

Plan-Gate (nach Planner) + Ergebnis-Gate (nach Reviewer).
fail-closed.

## 3. ADaPT (On-Demand-Zerlegung)

Wenn ein Task scheitert (`builder_failed`,
`post_build_verify_failed`, `reviewer_high_bug_fail_closed`),
wird er in 2–3 Sub-Tasks zerlegt (M-472/M-473/M-474/M-475).
Max 2 Ebenen tief. Abgeschlossene Tasks bleiben.
`get_next_task` liefert nur `pending`. `while`-Loop
(M-473) statt `for`.

## 4. Verifikation

- `ruff --fix` vor `_verify_patches` (M-467).
- Circuit Breaker in `_reflection_loop` (M-467).
- Kein `except Exception` ohne `# noqa: BLE001`.
- Fail closed: jeder Fehler → `ApplierError`-Subklasse.

## 5. Doku-Verweise

- `docs/README.md` — Diátaxis-Map
- `docs/NEUBAU-ZIELBILD.md` — Aktueller Loop als Zielbild
- `docs/ROADMAP.md` — Phasen
- `docs/ERLEDIGT.md` — Erledigte Blöcke
- `docs/OFFENE-BLOECKE.md` — Offene Blöcke
