# Architektur — Werkstatt

Stand: 2026-10-31 (nach Doku-Migration, Scaffolder, Migrator, OP-NNN-Disziplin).

## 1. Ziel-Architektur

Die Werkstatt ist ein Multi-Agent-System mit 5+1 Rollen und
ADaPT (On-Demand-Zerlegung). Der Mensch ist das letzte Gate.

    Explorer -> Scout -> Architect -> Planner-Split -> Builder -> Verify -> Reviewer -> Human-Gate

## 2. Rollen

### 2.1 Explorer (werkstatt/explorer.py)

Read-only Subagent. Messt deterministisch (ruff check ., pytest -q)
und liefert key_files aus der Messung. M-396: Explorer laeuft immer,
auch bei expliziten Dateien.

### 2.2 Architect (werkstatt/planner.py, Prosa-Modus)

deepseek-reasoner. Keine Skills, keine Tools (M-446). Produziert
Prosa mit numerierten Schritten (M-462). Max 16000 Tokens (M-447).

### 2.3 Planner-Split (werkstatt/planner.py, JSON-Modus)

deepseek-chat. Zerlegt die Architect-Prosa in Tasks mit
architect_start/architect_ende (woertliche Marker, M-461).
Rekursiv, max 2 Ebenen (M-469/M-470/M-471).

### 2.4 Builder (werkstatt/builder.py)

deepseek-chat. search/replace pro Task. Bekommt den woertlichen
Architect-Abschnitt (M-461). _architect_abschnitt gibt leeren
String zurueck, wenn die Datei nicht in der Prosa ist (M-450).

### 2.5 PreToolUse-Hook (hooks/pre_tool_use.py)

AST-basierte Import-Validierung (M-334a). Blockt erfundene
Imports deterministisch.

### 2.6 Verify (_verify_patches in loop.py)

verify.json-Stages: py_compile_changed, ruff_changed, pytest_changed,
py_compile_core, pytest_full_checks (phase_end, M-476).

### 2.7 Reviewer (werkstatt/reviewer.py)

deepseek-chat. Prueft die Task-Description, nicht die Gesamtaufgabe
(M-459). Bekommt den vollen Diff (M-448).

### 2.8 Human-Gate (_human_gate in loop.py)

Plan-Gate (nach Planner) + Ergebnis-Gate (nach Reviewer). fail-closed.

## 3. ADaPT (On-Demand-Zerlegung)

Wenn ein Task scheitert (builder_failed, post_build_verify_failed,
reviewer_high_bug_fail_closed), wird er in 2-3 Sub-Tasks zerlegt
(M-472/M-473/M-474/M-475). Max 2 Ebenen tief. Abgeschlossene Tasks
bleiben. get_next_task liefert nur pending. while-Loop (M-473).

## 4. Verifikation

**Tests sind Specs, keine Attrappen** (ADR-0015, 2026-11-06).

Jeder Test baut seinen State ueber `tests/factories.py::mk_state(**overrides)`.
Damit ist garantiert:
- Alle `RunState`-Felder existieren (Defaults greifen fuer nicht-ueberschriebene)
- Tippfehler in Test-Feldern fail-loud (`mk_state(apikey=...)` wirft)
- mypy findet Feld-Umbenennungen in Tests
- Prod-Code kann `state.X` direkt nutzen (kein `getattr`-Fallback noetig)

`SimpleNamespace` bleibt nur fuer **Mock-Bundles** erlaubt (LLM-Reply,
Function-Referenzen wie `SimpleNamespace(run_builder=..., audit=...)`).
State-Attrappen mit `SimpleNamespace(project_dir=..., aufgabe=...)` oder
`class _State: def __init__(self): self.X = ...` sind verboten.

Verifikations-Pipeline:- ruff --fix vor _verify_patches (M-467).
- Circuit Breaker in _reflection_loop (M-467).
- Kein except Exception ohne # noqa: BLE001.
- Fail closed: jeder Fehler -> ApplierError-Subklasse.

## 5. Doku-Werkzeuge (2026-10-31)

- werkstatt/scaffold.py: legt §2-Pflichtdateien idempotent an.
  Templates in werkstatt/templates/.
- werkstatt/migrate.py: prueft §2/§3/§5/§6 (§7-Schritt A).
  --apply legt fehlende Pflichtdateien an, loescht NICHTS.
- werkstatt/orchestrator.py::_sortiere_docs_nach_prioritaet:
  sortiert docs-Dict nach §6-Lese-Reihenfolge. load_docs nutzt das;
  d.h. state.docs ist bereits priorisiert.
- werkstatt/scout.py: bekommt PROJEKT-DOKU-Sektion (max 4000 Z. je
  Doc, §6-Reihenfolge) in user_content, direkt nach der Original-
  Zuweisung (_docs_prepend + user_content).
- werkstatt/scout.py::SCOUT_SYSTEM: OP-NNN-DISZIPLIN-Sektion.
  Bei vagen Aufgaben waehlt der Scout GENAU EINEN OP-NNN aus
  docs/STATUS.md.

## 6. Doku-Vertrag

Der Loop liest die Living Docs in der Reihenfolge aus
DOC_CONVENTIONS.md §6. Manifest-Feld docs: {entry, status, roadmap,
architecture, conventions, adr_index, glossary} in
projects/<name>.yaml. progress + changelog optional, werden nicht im
Loop-Kontext verwendet.

## 7. Doku-Verweise

- docs/index.md — Doku-Einstieg
- docs/STATUS.md — offene Punkte (OP-NNN, §5)
- docs/ROADMAP.md — Phasen
- PROGRESS.md — Historie (append-only)
- docs/adr/ — Architecture Decision Records


## Daten-Fluesse im Loop (Stand 2026-11-02)

### Explorer-Findings (Welle E)

Der Explorer schreibt `state.explorer_findings` mit:
- `git_dirty` (bool)
- `pytest_laufzeit_s` (int)
- `ruff_befunde` (list)

Diese fliessen in Architect- und Builder-Prompt (`## EXPLORER-FINDINGS`).
Zweck: Architect/Builder entscheiden mit Ground-Truth statt mit Vermutung.
Live-Beleg OP-039: Architect schlug "Doku-Eintrag" vor, obwohl pytest
11 Min laeuft — er wusste es nicht.

### Repair-Hints (Welle F)

`reflection._klassifiziere_fehler` erkennt die dominante Fehlerklasse in
`state.last_verify_errors` und liefert einen konkreten Hint:
- mypy object/int -> typing.cast
- ruff import -> Import reparieren
- patch_not_applied -> neuen Anker suchen
- pytest assertion -> Code/Test-Diagnose

Builder-Prompt erhaelt den Hint als `## REPAIR-HINT`-Block.
Zweck: Reflection mit konkretem Pattern statt "repariere irgendwas".
Live-Beleg: 3 von 3 Reflection-Stagnationen am 2026-11-02 hatten eine
Klasse, fuer die es einen klaren Hint gibt.

### Scout-API-Auszug (Welle D3, bereits vorher live)

`state.scout_api_auszug` wird vom Scout gefuellt und in Builder-Prompt
injiziert (`## API-SIGNATUREN`). Reduziert den AST-Index (13 Dateien) auf
die relevanten Symbole fuer den Builder.

### Rollen-Kette (unveraendert, bewusst)

Explorer -> Scout -> Architect -> Planner-Split -> Builder -> Verify ->
Reviewer -> (Reflection bei Fail) -> Phase-Review -> Human-Gate.

Jede Stufe reduziert die Kontextmenge fuer die naechste. Der Builder
bekommt am Ende: 1 Task-Beschreibung, 1 Datei, relevante API-Signaturen,
Explorer-Findings, Repair-Hints. Nicht: den ganzen Repo-Index.

Welle G (`single_call`-Modus, Architect liefert Tasks direkt) wurde am
2026-11-02 versucht und revertiert (`c1e8377`). Grund: Planner-Split
parst Prosa in logische Task-Granularitaet, nicht in Datei-Granularitaet.
Ein datei-basierter Extraktor produziert falsche Task-Grenzen.

### Determinismus-Inseln

- `verify.json` als Projekt-Vertrag
- `_baue_api_index` (AST)
- `_pruefe_api_widerspruch`
- `_deterministic_entfernen_precheck`
- `_stage_anzahl`, `_stage_ids` (Verify-Helpers)
- `_collapse_excess_blank_lines` (Post-Patch)
- `_klassifiziere_fehler` (Repair-Hint-Klassifikation)
- OP-064b Antipattern-Scanner
- OP-064a Sticky-Veto
- `_delete_zone_op_append` (Doku-Nachzug)
