# Architektur — Werkstatt


> **IST-Zustand.** Diese Datei beschreibt, was heute läuft.
>
> **SOLL-Zustand:** `docs/SOLL.md` — die Ziel-Architektur
> (Chat-UI, Chat-Debugger, Erfahrungs-Gehirn, Test-Loop).
>
> **Bei Widersprüchen:** ADR > `docs/SOLL.md` > diese Datei.
>
Stand: 2026-11-08 (Event-Architektur via ADR-0024 + UI-Layer + Multi-Projekt via ADR-0023).

## 1. Ziel-Architektur

Die Werkstatt ist ein Multi-Agent-System mit 9 spezialisierten
Rollen (Detail §2) und ADaPT (On-Demand-Zerlegung). Der Mensch ist
das letzte Gate.

    Explorer -> Scout -> Architect -> Planner-Split -> Builder -> Verify -> Reviewer -> Reflection -> Human-Gate

## 1.5 Installation

Zwei gleichwertige Wege — beide funktionieren:

**cwd-Import (Default, keine Installation nötig):**
Aus dem Repo-Root heraus. `pytest tests/` importiert `werkstatt` über
`sys.path[0]`. Funktioniert ohne venv-Setup, ohne `pip install`.
Bevorzugt für Loop-Läufe, lokale Entwicklung und CI ohne Wheel-Cache.

**Editable-Install (`pip install -e ".[test-tools]"`):**
`pip show werkstatt` zeigt dann `Version: 0.1.0` und `Name: werkstatt`.
Die Extras-Gruppe `test-tools` zieht `hypothesis` und
`pytest-gremlins` nach. Funktioniert auch aus anderen Verzeichnissen
heraus (z.B. wenn `pytest` nicht aus dem Repo-Root gestartet wird).
Voraussetzung für Mutation-Gate (OP-190) und Hypothesis-Tests (OP-193).

Beide Wege bleiben dauerhaft unterstützt. Kein Migrationszwang, keine
`[tool.pytest.ini_options]` — `pytest.ini` bleibt aktive Config.

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

## 8. Event-Architektur (2026-11-08, ADR-0024)

Zwei Ebenen, single-writer, rebuildbar.

### 8.1 Write Model — zwei JSONL-Streams

`audit()` schreibt semantische Events, `stream()` hochfrequente
Laufzeit-Events. Beide bauen ein JSON-Schema mit
`event_id = sha256(run_id|audit_id)[:16]`.

    Stream     Datei                                  git      Inhalt
    Semantic   audit-logs/semantic-YYYY-MM-DD.jsonl   ja       loop_*, builder_*, reviewer_*, gate_*, pipeline_start, summary, explorer_*
    Stream     audit-logs/stream-YYYY-MM-DD.jsonl     nein     log_line, progress, spinner, heartbeat, task_started, task_done

Zuordnung in `werkstatt/audit.py::_STREAM_KINDS`. Fail-closed:
unbekannter Kind geht in Semantic.

### 8.2 Read Model — SQLite als Projektion

`werkstatt/projection.py::Projector` liest JSONL und schreibt SQLite
idempotent:

- `rebuild(von_seq=0)` — alle JSONL → SQLite, DELETE + replay
- `tail()` — ab Checkpoint inkrementell
- `status()` — `{jsonl_events, sqlite_rows, diff, last_checkpoint}`

Schema: `events(event_id UNIQUE, ...)` mit `INSERT ... ON CONFLICT
IGNORE`. Checkpoint in `projection_state(key, value)`.

**Kern-Regel:** SQLite wird ausschliesslich vom Projektor beschrieben.
`EventStore().append()` ist aus der Produktion verbannt (gestern in
`gate_bridge.py` und `web/app.py` migriert).

### 8.3 Health

`GET /api/projects/{name}/projection/status` liefert Divergenz JSONL
vs. SQLite. Statusbar zeigt Warnung bei `diff > 0`.

### 8.4 Regel

Alte SQLite bleibt unangetastet bis `rebuild()` gruen und
`db_hash_identisch()` nach Doppel-Rebuild. Bei Fehler: alte DB
zurueck, kein Datenverlust.

## 9. UI-Layer (2026-11-08)

Die Web-UI ist dreischichtig: Ambient (Handlungsampel), Panels
(Diagnose), Palette (Navigation).

### 9.1 Ambient Status Bar (OP-301)

Zeile zwischen Tab-Leiste und Grid. Drei Elemente:

- Loop-Status: `○ Idle` / `◉ Laeuft` / `● Fertig` / `✗ Fehler`
- Letzter Run (relativ mit ✓/✗)
- Gates (hidden bei 0, pulsierend bei > 0)

Polling 3 s gegen `/ambient`. Klick Ziele: Timeline / Gate-Panel.

**Design-Entscheidung:** Tokens und Phase sind **nicht** in der
Ambient-Bar — sie sind Diagnose, nicht Handlung. Sie leben in der
Statusbar unten.

### 9.2 Command Palette (OP-302)

`Ctrl+K` / `Cmd+K` oeffnet Overlay. Server-Filter ueber `/palette?q=`
mit 4 Kategorien: Aktionen, OPs, Sessions, Runs. Icons ▸ → ⚙
◆ ↻. Keyboard-Nav: ↑↓ Enter Esc.

### 9.3 Runs-Liste mit Run-Status + Start/Stop (OP-303)

Pro OP-Zeile: Run-Status-Badge (○ idle / ● laeuft / ✓ fertig /
✗ fehler), Start-Button ▶, Stop-Button ■. Polling 5 s.
Hover-Tooltip mit Blockiert-von-Info.

Backend: `aggregate_ops_run_status()` liest `loop_started`-Marker
(primär) und `pipeline_start` (Legacy-Fallback).

### 9.4 Audit-Panel (ruhiges Layout)

Ein-Zeilen-Layout pro Event, Icon inline vor Text, Kind-Name klein
rechts. Run-Gruppierung mit duennen Trennern. Klick expandiert
Payload. Kategorie-Icons (↻ Loop, ⚙ Builder, ⌕ Explorer,
✓/✗ Verify/Reviewer, ⚑ Gate).

Sem-Farben aus OP-300: `--sem-action` (lila), `--sem-active` (blau),
`--sem-ok` (gruen), `--sem-warn` (gelb), `--sem-error` (rot),
`--sem-history` (grau).

### 9.5 Shortcut-Help + Utility-Bar (OP-304/305)

`?`-Taste oeffnet Overlay mit Kategorien (Navigation, Chat, Palette).
Utility-Bar oben rechts: `⌘K`-Button, `?`-Button. Klickwege
parallel zu Shortcuts.

### 9.6 Projekt-Anlage (OP-305)

`+`-Button oder `Alt+N` oeffnet Modal. Name + Pfad (Auto-Fill
`/opt/<name>`). Backend `POST /api/projects/create` ruft
`scaffold()` + schreibt Projekt-Pflichtdateien. Ambient zeigt aktives
Projekt prominent.

### 9.7 Multi-Projekt-Kontext (ADR-0023)

`_PROJECTS_BASE`-Konstante in app.py + inspector.py, testbar via
monkeypatch. `/start` validiert `docs/STATUS.md` (404 sonst). `/ops`
+ Palette lesen projekt-spezifisch.

Offen (OP-306a/b/c): Tab-Persistenz, Projekt-Selector, SQLite-
`project`-Spalte fuer `/ambient` `/status` `/timeline` `/tokens`.
