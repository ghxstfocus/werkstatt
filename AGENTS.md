# AGENTS.md — Werkstatt

Einstiegspunkt fuer Agenten und Menschen, die mit der
Werkstatt arbeiten. Kurz, konkret, Befehle statt Prosa.

## Was ist die Werkstatt

Ein Agenten-System fuer autonome Code-Aenderungen:
Explorer -> Planner -> Builder -> Hooks -> Reviewer -> Human-Gate.
`werkstatt/loop.py` orchestriert, `werkstatt/` sind die Module,
`hooks/` sind die deterministischen Gates, `agents/*.md` sind
die Rollen-Prompts, `skills/*/SKILL.md` sind die Skills.

## Pflicht-Befehle

    pytest -q                              # 1401 passed
    ruff check .                           # 14 errors
    mypy pipeline.py werkstatt/            # 8 errors
    pytest tests/test_audit_kinds.py -q    # 6 passed
    grep -n "_KATALOG_SOLL" pipeline.py    # 162

**Nicht** `python -m pytest` (Binary `python` fehlt).
**Nicht** `mypy .` (zaehlt tests/, 40 Fehler).

## Quality-Gate

    python3 -m tools.quality_gate --json

Prueft alle 5 Baseline-Werte. Exit 0 = ok, 1 = regression,
2 = Skript-Fehler.

## Key

Nicht `export DEEPSEEK_API_KEY=...`. Stattdessen:

    sops exec-env --pristine secrets.enc.yaml 'python pipeline.py'

Setup: `docs/KEY-ARCHITEKTUR.md`.

## Struktur

    pipeline.py           Orchestrierung (~13000 Z.)
    werkstatt/            11 Module (state, exec, verify, ...)
    agents/               Rollen-Prompts (builder, planner, ...)
    skills/               12 Skills (anker-regeln, plan-crafting, ...)
    tools/                quality_gate.py, audit.py
    tests/                1401 Tests
    docs/                 30 Doku-Dateien (INDEX.md als Einstieg)

## Doku

- `docs/INDEX.md` — nach Diaetaxis sortiert (tutorial/howto/reference/explanation).
- `docs/glossary/index.md` — M-Nummern + Fachbegriffe.
- `Bau-Handoff.md` — aktueller Stand (HEAD, Baseline, offene Bloecke).
- `docs/adr/` — Architecture Decision Records (ab A7-2).

## Regeln

- **Messen vor Bau.** Kein Code-Touch ohne read-only Messung.
- **Baseline pro Commit gruen.** Delta != 0 -> Rollback.
- **Ein Ziel pro Commit.** Kein Mixed-Commit ohne A9-12.
- **Keine Zeilennummern aus alten Messungen.** Nach jeder
  Aenderung neu messen (M-202).
- **Kandidaten vollstaendig pruefen.** `grep` nach allen
  String-Vorkommen, nicht nur `audit("literal")` (M-202).

## Naechster groesser Umbau

**Pipeline-Tot (M-345):** pipeline.py (11.639 Z.) loeschen,
sobald `werkstatt/agent.py` keine Kopien mehr braucht
(M-231 Zwischenzustand). Danach: Werkstatt-Entkopplung
von security-ai (werkstatt/verify.py importiert noch
harness.*-Module, nur Introspektion).


## Loop-Neubau (Phase 1-17)

Der neue Orchestrator ist `werkstatt/loop.py`.
Ablauf: Explorer -> Planner -> Builder -> Hooks -> Reviewer -> Human.

Agenten:
- `werkstatt/explorer.py` (read-only Kontext)
- `werkstatt/planner.py` (JSON-Plan)
- `werkstatt/builder.py` (str_replace-Patches, create + update)
- `werkstatt/reviewer.py` (Bug-Check, Diff im Zielprojekt)
- `werkstatt/phase_state.py` (Resume, Decisions)

Hooks:
- `hooks/pre_tool_use.py` (Waechter: .env, destruktive Kommandos, Datei-Existenz)
- `hooks/simplify.py` (Aufraeumer: Komplexitaet)

Multi-Projekt:
- Werkstatt-YAML: WO liegt das Projekt (project_dir).
- `.werkstatt/verify.json`: WIE verifizieren (stages).

Human-Gate: fail-closed (EOFError -> reject), respektiert require_human_approval.

Baseline: 1401 passed / 13 ruff / 8 mypy.
