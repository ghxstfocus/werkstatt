# Werkstatt

Ein Meta-Loop-System. Es baut und repariert andere Projekte
durch einen LLM-getriebenen Agenten-Loop. Die Werkstatt gehört
keinem Projekt — sie arbeitet an jedem.

**Kernprinzip:** Erst messen, dann designen, dann bauen.
Deterministische Gates vor jedem Commit. Kein LLM-Token ohne Plan.

**Python:** 3.11 · **Tests:** 1364 passed, 8 skipped · **Version:** 0.1.0 (in Arbeit)

---

## Was ist Werkstatt?

Werkstatt ist ein Orchestrator für LLM-Agenten, die Software bauen.
Der Loop liest offene Aufgaben aus `docs/STATUS.md` (Format: OP-NNN),
wählt einen Punkt, baut ihn, testet ihn, und committet nur, wenn alle
Verifikationen grün sind.

**Was heute funktioniert (Stand 2026-11-07):**

- 7 spezialisierte Rollen (Explorer, Scout, Architect, Planner,
  Builder, Reviewer, Reflection)
- Loop-Läufe bauen eigenständig Bugfixes und Features (siehe
  `PROGRESS.md` für ~15 dokumentierte Loop-Tests)
- 9 harte Verify-Stages vor jedem Commit
- 4 Human-Gates (Plan, Reflection, Phase-Review, Commit)
- 1364 Tests, `ruff`-Baseline 0, `mypy` sauber
- 20 Skills (on-demand geladen pro Rolle)
- Vollständige Audit-Historie (`audit-logs/agent-pipeline-*.jsonl`)

**Was in Planung ist (SOLL, ADR-0016/0017/0018):**

- **Spec-First Test-Loop:** Tests werden vor dem Code gebaut,
  qualifiziert (müssen auf unverändertem Repo rot sein) und
  eingefroren (SHA256). Der Code-Builder ist test-blind.
- **Mutation-Gate:** `pytest-gremlins` prüft, ob die Tests
  tatsächlich Spec-Verhalten testen oder nur den Ist-Zustand.
- **Debugger als eigene Rolle:** 3-Wege-Check (Spec ↔ Code ↔ Test)
  mit Test-Thaw-Mechanik.

Die Details stehen in den ADRs 0016, 0017, 0018 und in den
OPs 188-195. Diese README dokumentiert **beides** — IST und SOLL.

---

## Installation

### Heute: cwd-Import (empfohlen für Loop-Entwicklung)

```bash
cd /opt/werkstatt
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt



Der Loop läuft aus dem Arbeitsverzeichnis: `python3 -m werkstatt.loop
--project <name> --aufgabe "..."`. Kein `pip install` nötig.

### Zukünftig: Package-Install (nach OP-195)

    pip install -e ".[test-tools]"

Registriert `werkstatt` als Package und installiert `hypothesis` +
`pytest-gremlins`. Der Loop läuft dann von überall, cwd-Import
bleibt Fallback.

**Status:** `pyproject.toml` existiert, hat aber noch keine
`[project]`-Sektion. OP-195 ergänzt sie.

### API-Key

Der Loop braucht `DEEPSEEK_API_KEY` in `.env` oder als
Umgebungsvariable. Siehe `werkstatt/env_loader.py`.

---

## Quickstart

### Loop starten

    cd /opt/werkstatt
    source .venv/bin/activate
    python3 -m werkstatt.loop --project werkstatt --fresh

Der Loop wählt einen offenen OP, plant ihn in Tasks, baut sie,
testet sie und fragt an drei Gates nach Bestätigung (`j/n/a`).

### Tests laufen lassen

    pytest tests/ -q

### Status anschauen

    less docs/STATUS.md
    tail -50 PROGRESS.md
    tail -50 docs/MERKPOSTEN.md

### Audit-Log

    tail -20 audit-logs/agent-pipeline-$(date -u +%Y-%m-%d).jsonl

---

## Architektur — IST (Stand 2026-11-07)

### Pipeline (5 Phasen)

    Explorer → Plan-Gate → Planner → Builder → Reviewer → Verify → Human-Gate

Jede Phase lebt in `werkstatt/phases/`:

| Phase | Modul | Aufgabe |
|---|---|---|
| 1 | `phases/explorer.py` | Deterministische Messung (ruff, pytest) + key_files |
| 2 | `phases/plan.py` | Plan-Gate + Planner + Plan-Human-Gate |
| 3 | `phases/tasks.py` | Autonomer Task-Loop (Builder + Reviewer + Reflection) |
| 4+5 | `phases/finalize.py` | Phase-Review + Human-Gate + Commit |

### Die 7 Rollen

| Rolle | Skills | Filter | Aufgabe |
|---|---|---|---|
| Explorer | `using-werkstatt` | — | Deterministische Messung, key_files |
| Scout | — | — | Auftrag formulieren, IST-Zustand prüfen |
| Architect | — | — | Prosa-Plan (deepseek-reasoner, max 32000 Tokens) |
| Planner | `using-werkstatt`, `milestone-planning`, `plan-crafting` | — | Task-Zerlegung aus Prosa |
| Builder | — | `builder` | Code-Patches (Aider-Style search/replace) |
| Reviewer | `review-work` | `reviewer` | Diff-Prüfung gegen Task-Description |
| Reflection | `systematic-debugging` | — | Fehlerbehandlung nach Verify-Fail |

**SOLL (ADR-0018):** `systematic-debugging` wandert zu einer eigenen
`debugger`-Rolle. Reflection behält die Loop-Logik ohne Debugging-Skill.

### Task-Typen (`action`)

| Action | Bedeutung |
|---|---|
| `create` | Neue Datei anlegen |
| `update` | Bestehende Datei ändern |
| `read` | Nur lesen (kein Builder, kein Diff) |
| `verify` | Zustand prüfen (kein Builder, Reviewer prüft ohne Diff-Erwartung) — **neu seit OP-183** |

**SOLL (ADR-0016):** neuer Task-Typ `test` — vom Test-Agent gebaut,
nicht vom Builder.

### Human-Gates (4 Stellen)

| Gate | Wann | `n` = ? |
|---|---|---|
| Plan-Gate | Nach Planner, vor Builder | Reflection mit Grund (1 Runde), dann neuer Plan |
| Reflection-Gate | Nach Reflection-Erschöpfung | Task fail, Loop läuft weiter |
| Phase-Review-Gate | Nach 2 Runden Phase-End-Reflection | Loop bricht ab |
| Commit-Gate | Am Phase-Ende | Loop bricht ab |

**Wichtig:** `n` bedeutet an jedem Gate etwas anderes. Der Gate-Text
sagt es jeweils explizit.

### Verify-Kette (9 Stages, alle hart)

| Stage | Command | Timeout |
|---|---|---|
| `py_compile_changed` | `py_compile {changed_py_files}` | 60 |
| `ruff_changed` | `ruff check {changed_py_files}` | 120 |
| `state_drift` | `state_drift.py --check` | 30 |
| `control_drift` | `control_drift.py --check` | 30 |
| `import_drift` | `import_drift.py` | 60 |
| `mypy_changed` | `mypy {changed_py_files}` | 90 |
| `pytest_changed` | `pytest {changed_test_files}` | 300 |
| `contract_check` | `state_inventory.py --changed` | 30 |
| `pytest_regression` | `pytest -q` (phase_end) | 300 |

Hart heißt: bei rc!=0 blockt der Commit.

### Die 3 Statusdateien

| Datei | Zweck | Format |
|---|---|---|
| `docs/STATUS.md` | Offene OPs | `### OP-NNN:` + Felder |
| `PROGRESS.md` | Erledigt, append-only | `### YYYY-MM-DD — OP-NNN` |
| `docs/MERKPOSTEN.md` | Prozess-Lehren | chronologisch, neueste oben |

---

## Architektur — SOLL (Ziel, ADR-0016/0017/0018)

### Spec-First Test-Loop (ADR-0016)

Der Loop baut heute Code und Tests im selben Builder-Call. Code und
Test bestätigen sich gegenseitig, aber Spec-Abweichungen bleiben
unsichtbar. Der Benchmark (2026-11-07) zeigt: 3 von 18 Mutanten
überleben auf einem Mini-Modul, weil Grenzfälle nicht getestet sind.

**Ziel-Ablauf:**

    Architect
      → AK + test_spec (Test-Namen + Assertion-Prosa, KEIN Code)
    Test-Loop (Phase 2b)
      → Test-Agent baut Tests aus test_spec
      → Qualification: Tests MÜSSEN auf unverändertem Repo rot sein
      → Freeze: SHA256 in state.test_manifest
    Code-Loop (Phase 3, test-blind)
      → Builder sieht tests/ NICHT
      → verify-Stage test_integrity prüft SHA256
      → verify-Stage pytest_changed läuft auf eingefrorenen Tests
    Mutation-Gate
      → pytest-gremlins auf geänderte Files
      → Score < 0.8: Audit (kein Hard-Block in Runde 1)
    Debugger (bei Wiederholungs-Fail)
      → 3-Wege-Check: Spec ↔ Code ↔ Test
      → Test-Thaw nur über Human-Gate (auditierbar)

### Mutation-Gate (ADR-0017)

`pytest-gremlins` 1.13.2. Native pytest-Integration. Mutation
Switching statt fork-basiertem Neuladen — schnell genug für
"pro Task". Score-Schwelle 0.8, im ersten Rollout `hart: false`.

Cosmic-ray als Alternative dokumentiert, aber nicht gewählt
(ConfigError im Benchmark, CLI-lastiger).

### Debugger als eigene Rolle (ADR-0018)

`systematic-debugging` wandert von `builder`/`reflection` zu einer
eigenen Rolle `debugger`. Der Debugger implementiert den 3-Wege-Check:

| Code | Test | Aktion |
|---|---|---|
| ≠ Spec | = Spec | Fix Code (Test hatte recht) |
| = Spec | ≠ Spec | Test-Thaw (Human-Gate) |
| ≠ Spec | ≠ Spec | Human-Gate (fundamentale Misalignment) |
| = Spec | = Spec, rot | Human-Gate (Infra/flaky/env) |

**Test-File-Guard:** Debugger-Patch auf Test-Datei nur bei
Syntax-Fehler oder Human-Gate-Freigabe.

### OP-Serie (Reihenfolge)

| OP | Titel | Blockiert von |
|---|---|---|
| OP-195 | `pyproject.toml` Package-Registrierung + test-tools | — |
| OP-188 | Test-Loop-Phase mit Qualification und Freeze | OP-092, OP-195 |
| OP-189 | Builder test-blind + verify-Stages | OP-188 |
| OP-190 | Mutation-Gate als verify-Stage | OP-189, OP-195 |
| OP-191 | Debugger-Rolle mit 3-Wege-Check | OP-188 |
| OP-192 | Test-Thaw-Mechanik | OP-191 |
| OP-193 | Hypothesis als optionale Dependency | OP-195 |
| OP-194 | Architektur-Doku aktualisieren | OP-188, OP-191 |

**Reihenfolge:** 195 → 188 → 189 → 190 (parallel 193); 188 → 191 → 192;
194 am Ende.

---

## Verzeichnisse

    werkstatt/
    ├── werkstatt/              # Python-Package
    │   ├── loop.py             # CLI + Hauptschleife
    │   ├── phases/             # 5 Phasen
    │   ├── roles/              # Rollen-Registry + builder/-Submodule
    │   ├── render/             # 7 Render-Module
    │   ├── architect.py        # Architect-Prompt + run_architect
    │   ├── planner.py          # Planner + Task-Split
    │   ├── reviewer.py         # Reviewer + Filter
    │   ├── reflection.py       # Reflection-Loops + Stagnation
    │   ├── state.py            # RunState (~90 Felder)
    │   └── audit.py            # Audit + _AUDIT_KINDS_BEKANNT (~235)
    ├── tests/                  # 197 Test-Dateien, 1364 Tests
    ├── tools/                  # Drift-Checks + Inventory
    ├── skills/                 # 20 Skills (SKILL.md pro Verzeichnis)
    ├── docs/
    │   ├── STATUS.md           # offene OPs
    │   ├── ARCHITECTURE.md     # Architektur (Wahrheits-Quelle)
    │   ├── MERKPOSTEN.md       # Prozess-Lehren
    │   └── adr/                # 18 ADRs
    ├── audit-logs/             # agent-pipeline-YYYY-MM-DD.jsonl
    ├── hooks/                  # pre_tool_use.py, planner_gate.py
    ├── logs/                   # loop-render-*.log
    └── .werkstatt/             # RunState + verify.json

---

## Doku

- **`docs/STATUS.md`** — offene Punkte (OP-NNN-Format §5)
- **`PROGRESS.md`** — erledigte Punkte (append-only)
- **`docs/MERKPOSTEN.md`** — Prozess-Lehren aus jeder Session
- **`docs/ARCHITECTURE.md`** — Architektur (Wahrheit bei Konflikten)
- **`docs/DOC_CONVENTIONS.md`** — Golden-Standard für Doku
- **`docs/adr/`** — 18 ADRs (0016/0017/0018 sind neu)
- **`AGENTS.md`** — Hinweise für Agenten-Entwicklung

---

## Entwicklung

### Konventionen

Vollständig in `docs/MERKPOSTEN.md`. Die wichtigsten:

1. **Erst messen, dann designen, dann fixen.** Kein Fix ohne
   reproduzierten Bug.
2. **Pre-Commit-Pflicht:** py_compile, ruff, mypy, pytest, alle
   Drift-Checks. Alle grün → commit.
3. **Handoff ist Messbericht, kein Freitext.**
4. **Test-Contract bei Verhaltens-Änderung:** Vor jedem Patch, der
   eine Verhaltens-Änderung durchführt, prüfen, ob ein Test das
   alte Verhalten testet.
5. **`git push` nur wenn alle Gates grün sind.**

### Loop-Tests

Loop-Tests 1-10 sind in `PROGRESS.md` dokumentiert. Loop-Test 10
ergab: OP-182, OP-183, OP-186, OP-187 — alle 2026-11-07 gefixt.

### Neue OPs anlegen

Vor `## Delete-Zone` in `docs/STATUS.md` einfügen:
`### OP-NNN: Titel` + Felder nach `DOC_CONVENTIONS.md §5`.

### Neue ADRs anlegen

`docs/adr/ADR-NNNN-titel.md` + Eintrag in `docs/adr/README.md`.

---

## Roadmap

**Kurzfristig (Stufe 3):** OP-195 pyproject.toml, OP-092 Body
aktualisieren, OP-188 Test-Loop-Phase.

**Mittelfristig (Stufe 4):** OP-189 Builder test-blind, OP-190
Mutation-Gate, OP-191 Debugger-Rolle, OP-192 Test-Thaw-Mechanik.

**Langfristig (Stufe 5):** OP-193 Hypothesis, OP-194 Architektur-
Doku, Loop-Test 11 (Verifikation).

**Weitere Baustellen:** siehe `docs/STATUS.md` (54 offene OPs).

---

## Was Werkstatt NICHT ist

- **Kein Chat-Agent.** Die Chat-Erweiterung (OP-124-132) ist
  geplant, aber eigenes System.
- **Kein CI/CD-Ersatz.** Werkstatt committet lokal. CI ist ein
  separater Schritt.
- **Kein Bugfixer für fremde Codebasen.** Werkstatt arbeitet an
  ihrem eigenen Repo (oder explizit konfigurierten Zielprojekten).
- **Keine stabile API.** `RunState`-Felder und Modul-Struktur
  sind in Bewegung (siehe OP-141, OP-143).

---

## Danksagung

Baut auf den Ideen auf von:
- Aider (search/replace-Patches, Reflection-Loop)
- Claude Code (Task-Loop, Human-Gates)
- SWE-agent (Task-Zerlegung)
- Meta TestGen-LLM (Mutation als Test-Quality-Gate)

Lizenz: noch nicht festgelegt.
