# ADR-0015: Tests sind Specs, keine Attrappen

- **Datum:** 2026-11-06
- **Status:** accepted

## Kontext

Die Testsuite war historisch mit zwei Anti-Patterns gebaut:

1. **`SimpleNamespace`-States**: Tests bauten `SimpleNamespace(project_dir=..., aufgabe=...)`. Je nach Test fehlten unterschiedliche Felder.
2. **Hand-rolled Mock-Klassen**: `class _State: def __init__(self): self.X = ...` oder `type("S", (), {...})()`. Pro Test-Datei neu, jedes Mal unvollstaendig.

Konsequenzen (gemessen 2026-11-06):

- **262 von 263** `getattr(state, "X", default)`-Aufrufe in Prod beziehen sich auf **deklarierte** `RunState`-Felder — aber der `getattr` ist noetig, weil Tests nicht garantieren, dass das Feld existiert.
- **28 `# type: ignore[attr-defined]`** in Prod, weil `getattr(state, "X")` als potentiell fehlend typisiert ist.
- **`mypy` blind fuer Feld-Umbenennungen**: `getattr(state, "alter_name")` findet mypy nicht, weil Strings opak sind.
- **Tippfehler in Test-Feldern bleiben unentdeckt**: `SimpleNamespace(apikey="x")` funktioniert, weil der Test nur `st.apikey` liest — der Prod-Code liest aber `state.api_key`.
- **Zombie-Felder in Tests**: Loop-Test zeigte 13 nicht-deklarierte Felder in Test-States (`explorer_ctx`, `plan_gate_errors`, `architect_beschreibung`), die nie gelesen wurden — reine Attrappen.
- **Ein Prod-Rueckbau von `getattr` auf `state.X` war unmoeglich**, ohne dass 100+ Tests mit `AttributeError` brachen (hand-rolled Mock-Klassen ohne das Feld).

Der historische `SimpleNamespace`-Ansatz war ein Kompromiss: simpel zu schreiben, aber Tests testen damit Attrappen statt Spec-Verhalten.

## Entscheidung

**Tests sind Specs.** Jeder Test-State ist ein **vollstaendiger** `RunState` mit Defaults, kein Attrapppen-Objekt. Konkret:

1. **`RunState` hat Defaults fuer alle Felder** (seit 2026-11-06). `RunState()` ohne Argumente baubar. `project_dir=Path(".")`, `api_key=""`, `tasks=[]` etc. als sentinel-sichere Defaults.

2. **`tests/factories.py::mk_state(**overrides)`** ist die **einzige** Test-Konstruktion:
   - Liefert vollstaendigen `RunState`
   - Fail-loud bei unbekanntem Feld (Tippfehler-Schutz: `mk_state(apikey="x")` wirft `AttributeError`)
   - Neue Felder erben automatisch den Default

3. **`SimpleNamespace` bleibt nur fuer Mock-Bundles** (Function-Referenzen wie `SimpleNamespace(run_builder=..., audit=...)` oder LLM-Reply-Bundles). Keine State-Attrappen mehr.

4. **`getattr(state, "X", default)` wird schrittweise durch `state.X` ersetzt**, wo der Default semantisch identisch ist. Der Rest bleibt als Verteidigung gegen hypothetische Mocks — niedrige Prioritaet.

## Konsequenzen

**Positiv:**
- Neue Felder in `RunState` brechen keine Tests (Defaults greifen).
- mypy findet Feld-Umbenennungen in **allen** Tests (keine String-Indirektion mehr).
- Tippfehler in Test-Feldern fail-loud.
- Prod-Code kann `state.X` direkt nutzen — bessere Lesbarkeit, echte Typpruefung.
- Zombie-Felder in Tests werden entdeckt und entfernt.
- Kuenftige Tests sind Specs: `mk_state(patches=[...])` sagt aus, welches Verhalten geprueft wird.

**Negativ / Trade-offs:**
- `RunState`-Defaults sind jetzt Teil des Spec-Vertrags — neue Felder muessen einen Default haben, sonst brechen alle Tests, die sie nicht setzen.
- `mk_state()` fail-loud erfordert, dass neue Felder **vorher** in `RunState` deklariert werden — `setattr(state, "neues_feld", ...)` ausserhalb von `RunState` ist verboten.
- Einmalige Migration von 34 Dateien (2026-11-06 abgeschlossen).

**Neutral:**
- `SimpleNamespace` als Mock-Bundle bleibt erlaubt — Mock-Objekte sind keine Specs, sie simulieren externe APIs.

## Umsetzung (2026-11-06)

- **P1**: `RunState` mit Defaults + `mk_state`-Factory + `test_factories.py`
- **P2**: 2 Pilot-Dateien (`test_reflection.py`, `test_reflection_spec_erschoepfung.py`)
- **P3**: 34 Test-Dateien migriert (Batches A, B1a, B1b, B2, C1-C10) — Commits `9ba86dd..462ea81`
- **P3-Nachtrag**: 5 hand-rolled `_State`/`type("S",...)`-Klassen migriert — Commit `f91cb1a`
- **P4a-c**: 145 `getattr`-Ersetzungen (30 identisch, 126 sicher, 15 Bool) — Commits `472dd8b..a73bf58`
- **P4d-e ausstehend**: `project_dir` (35), `project_name` (20), `aktuelle_task` (10), Rest (35) — Sichtpruefung pro Stelle

## Verweise

- `tests/factories.py` (Factory)
- `tests/test_factories.py` (3 Spec-Tests fuer die Factory selbst)
- `tests/test_loop_state.py::test_ehemalige_pflichtfelder_haben_defaults` (RunState-Defaults)
- OP-174 (Spec-Tests — RunState-Factory statt SimpleNamespace)
- Commits: `9ba86dd..a73bf58` (P3 + P3-Nachtrag + P4a-c)
