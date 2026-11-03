# ADR-0005: verify.json hart-Feld — asymmetrische Semantik

- **Datum:** 2026-11-03
- **Status:** accepted
- **Kontext:** `verify.json` definiert Verify-Stages die nach dem Builder
  laufen (py_compile, ruff, mypy, pytest). Jede Stage muss als **hart**
  (blockiert bei Fail) oder **weich** (Warnung, aber Task läuft weiter)
  klassifiziert sein. Bis 2026-11-03 gab es **kein explizites Feld** —
  die Klassifikation lief über Prefix-Matching in
  `_HARTE_STAGE_PREFIXES` / `_WEICHE_STAGE_PREFIXES`:

  - hart: `py_compile*`, `pytest*`, `test*`, `migrations_check`, `schema`,
    `import_check`
  - weich: `ruff*`, `lint*`, `mypy*`, `style*`, `format*`, `flake8*`,
    `bandit*`, `pip_audit*`
  - unbekannt → hart (fail-closed)

  Das war fragil: eine neue Stage wie `pyright_changed` wäre unbemerkt als
  **hart** klassifiziert worden (blockiert einen Commit der eigentlich
  nur Warnungen hat). Umgekehrt würde ein Typo wie `pytest_xyz` als **hart**
  durchgehen — der `pytest`-Prefix rettet das, aber `pytestx` würde als
  hart klassifiziert weil der Prefix nicht matcht (fail-closed).

**Fragestellung:** Wenn `verify.json` jetzt ein explizites `"hart": true|false`
bekommt, wie ist die Semantik?

**Zwei mögliche Designs:**

A) **Symmetrisch:** `hart=true` → hart, `hart=false` → weich. Explizit
   überschreibt Prefix in beide Richtungen.

B) **Asymmetrisch:** `hart=true` → hart (verschärfen erlaubt),
   `hart=false` → Prefix-Klassifikation gilt weiter (nicht entschärfen).

## Entscheidung

**Design B — asymmetrisch.**

Regel:
- `hart=true` → immer hart (verschärfen).
- `hart=false` → **nicht** entschärfen. Prefix-Klassifikation gilt weiter.
  Ein `pytest_changed` mit `hart=false` bleibt **hart**.
- `hart` fehlt → Prefix-Fallback + `audit("verify_stage_ohne_hart_flag", {...})`.

**Begründung:** Sonst könnte ein Fehler in `verify.json` (versehentlich
`pytest_regression: hart=false` gesetzt) den wichtigsten Gate entschärfen,
und Tests würden nie mehr committen blockieren. Das ist fail-open. Die
Asymmetrie ist fail-closed: im Zweifel hart.

Der Prefix-Match bleibt als Fallback für:
- Stages die vor der Migration (2026-11-03) existierten und noch kein
  `hart`-Feld haben.
- Stages die in einem anderen Repo (Sub-Projekte) über `verify.json`-Loader
  eingebracht werden ohne `hart`-Feld.

## Konsequenzen

Positiv:
- Explizit: `verify.json` zeigt pro Stage welcher Charakter gewollt ist.
- Fail-closed bei versehentlicher Entschärfung: `hart=false` auf einem
  `pytest_*`-Stage entschärft nicht.
- Vergessene Stages sind sichtbar (`audit("verify_stage_ohne_hart_flag")`).
- Neue Stages wie `pyright_changed` müssen bewusst klassifiziert werden.

Negativ:
- Asymmetrie ist nicht sofort intuitiv — "hart=false" klingt wie
  "auf jeden Fall weich". Muss in Doku + Code-Kommentar erklärt werden
  (ist in `_stage_ist_hart`-Docstring).
- `hart=true` kann eine weiche Stage zu hart machen — das ist gewollt
  (verschärfen), aber überraschend wenn ein Stage-Name Prefix-weise weich
  ist (`mypy_changed` + `hart=true` blockiert).
- Ein Programmierer der eine weiche Stage will muss den **Stage-Namen**
  ändern (z.B. `mypy_changed` → `mypy_changed_soft`), nicht nur das Feld.
  Das ist bewusst: Stage-Namen sind die API.

## Alternativen

- **Symmetrisch (Design A):** `hart=false` entschärft. Fail-open-Risiko.
  Verworfen nach Test `test_hart_flag_false_laesst_prefix_gelten`
  (beweist dass jemand bereits `pytest_changed` mit `hart=false`
  versucht hatte zu entschärfen — der Test schützt davor).
- **Kein Prefix-Fallback:** Nur `hart`-Feld gilt, fehlendes Feld → hart
  (fail-closed ohne Warnung). Verworfen: Migration wäre breaking change,
  Sub-Projekte mit eigenem `verify.json`-Loader würden brechen.
- **hart als Enum (`"hart"|"weich"|"auto"`):** Expliziter aber
  überkompliziert. "auto" = Prefix = aktuelle Semantik. Verworfen.

## Referenzen

- Commit `4da252d`: `fix(verify): OP-095 hart-Feld explizit + fail-loud warn`
- Commit `1ac3446`: `fix(verify): hart=false entschaerft nicht (Docstring-Semantik)`
- `tests/test_verify_mypy_hart.py` (6 Tests, 4 davon Semantik-Schutz)
- `werkstatt/verify.py::_stage_ist_hart`
- OP-095 (Phase 33.2a)
