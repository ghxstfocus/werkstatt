# Werkstatt

Das Agenten-System. Unabhaengig von jedem Projekt.
Es baut Projekte, aber es gehoert keinem Projekt.

**Ziel:** Das Beste aus Claude Code, Copilot, Aider, Cursor,
Grok und Codex nehmen und ein eigenes Agentensystem bauen.

**Kernprinzip:** On-Demand-Messung + deterministische Gates.
Der Loop prueft, bevor er baut. Kein LLM-Token ohne Plan.

**Stand 2026-10-24:**

- Werkstatt: 1290 Tests, ruff 13, mypy 8, AST 6, Katalog 162.
- HEAD: f930e0c. Branch: umbau/phase-2 (origin gepusht).
- Loop-Neubau Phase 1-18 abgeschlossen.

## Loop-Architektur (Phase 1-18)

Der neue Orchestrator ist `werkstatt/loop.py` (447 Z.).
Er ruft:

1. **Explorer** (`werkstatt/explorer.py`, 89 Z.)
   read-only Kontext. JSON mit key_files.
2. **Planner** (`werkstatt/planner.py`, 81 Z.)
   JSON-Plan (tasks, tests, akzeptanzkriterien).
3. **Builder** (`werkstatt/builder.py`, 89 Z.)
   str_replace-Patches (create + update).
4. **PreToolUse-Hook** (`hooks/pre_tool_use.py`, 89 Z.)
   Waechter: .env, destruktive Kommandos, Datei-Existenz.
5. **PostToolUse-Hook** (`hooks/post_tool_use.py`, 42 Z.)
   Verifier: Baseline.
6. **Simplify-Hook** (`hooks/simplify.py`, 64 Z.)
   Aufraeumer: Komplexitaet.
7. **Reviewer** (`werkstatt/reviewer.py`, 103 Z.)
   Bug-Check im Zielprojekt.
8. **Human-Gate** (`_human_gate` in loop.py)
   fail-closed, respektiert `require_human_approval`.

Visualisiert:

    +----------------------------------------------------------+
    |                        MENSCH                             |
    |                  (Human-Gate, fail-closed)                |
    +----------------------------------------------------------+
                              |  ^
                              v  |
    +----------------------------------------------------------+
    |                  WERKSTATT LOOP                           |
    |                                                           |
    |   Explorer -> Planner -> Pre-Build Verify                |
    |        |                                                  |
    |        v                                                  |
    |   Pro Task:                                               |
    |     Builder -> PreToolUse -> Patch -> PostToolUse        |
    |              -> Simplify -> Verify -> Reviewer           |
    |        |                                                  |
    |        v                                                  |
    |   Human-Gate                                             |
    +----------------------------------------------------------+
                              |
                              v
                     Ziel-Projekt (z. B. security-ai)

## Multi-Projekt

Die Werkstatt betreut mehrere Projekte. Zwei Quellen:

- **Werkstatt-YAML** (`/opt/werkstatt/projects/<name>.yaml`):
  WO liegt das Projekt (`project_dir`).
- **Zielprojekt-Contract** (`/opt/<name>/.werkstatt/verify.json`):
  WIE verifizieren (stages: pytest, ruff, mypy).

Beispiel `verify.json`:

    {
      "stages": [
        {"id": "pytest", "command": ["python3", "-m", "pytest", "-q"]},
        {"id": "ruff", "command": ["ruff", "check", "."]}
      ]
    }

## Struktur

    /opt/werkstatt/
    ├── pipeline.py              Alter Monolith (11.118 Z., Fallback)
    ├── werkstatt/               Neue Module (5.027 Z.)
    │   ├── loop.py              Orchestrator (447 Z.)
    │   ├── loop_renderer.py     CI-Optik (94 Z.)
    │   ├── agent.py             ask_llm, execute_commands (609 Z.)
    │   ├── explorer.py          Read-only Kontext (89 Z.)
    │   ├── planner.py           JSON-Plan (81 Z.)
    │   ├── builder.py           str_replace-Patches (89 Z.)
    │   ├── reviewer.py          Bug-Check (103 Z.)
    │   ├── phase_state.py       Resume, Decisions (137 Z.)
    │   ├── state.py             RunState, Measurement (369 Z.)
    │   ├── config.py            Config-Wrapper (117 Z.)
    │   └── ...                  (weitere Module)
    ├── hooks/                   Deterministische Hooks (281 Z.)
    │   ├── pre_tool_use.py      Waechter (89 Z.)
    │   ├── post_tool_use.py     Verifier (42 Z.)
    │   ├── simplify.py          Aufraeumer (64 Z.)
    │   └── anti_patterns.py     Anti-Patterns (86 Z.)
    ├── agents/                  Rollen-Prompts (Markdown)
    ├── skills/                  Skills (SKILL.md)
    ├── projects/                Projekt-Konfigurationen
    ├── tests/                   1290 Tests
    ├── docs/                    Doku (INDEX.md als Einstieg)
    ├── AGENTS.md                Agenten-Einstieg
    ├── Bau-Handoff.md           Aktueller Stand
    └── README.md                Dieses Dokument

## Aufruf

Der Loop wird ueber Python aufgerufen (CLI folgt):

    python3 -c "
    from pathlib import Path
    from werkstatt.state import RunState
    from werkstatt.loop import run_pipeline_loop

    st = RunState(
        block_id='b1', aufgabe='Baue Feature X',
        api_key=os.environ['DEEPSEEK_API_KEY'],
        project_dir=Path('/opt/security-ai'),
        project_name='security-ai',
        ...
    )
    rc = run_pipeline_loop('security-ai', st.aufgabe, [st])
    "

## Sicherheit

- **Kein shell=True.** Argumentlisten.
- **PreToolUse-Hook:** blockiert `.env`-Dateien, destruktive
  Kommandos (`git reset --hard`, `rm -rf /`), leere Patches.
- **Datei-Existenz-Check:** `create` ueberschreibt keine
  bestehende Datei (blockiert mit `loop_patch_file_exists`).
- **Whitelist:** read_file nur aus `file_whitelist`.
- **Redaction** vor jedem LLM-Call.
- **Human-Gate fail-closed:** bei `EOFError` → reject.
- **Audit-JSONL** pro Tag mit project und run_id.

## Baseline

| Metrik | Wert |
|---|---|
| pytest | 1290 passed |
| ruff | 13 errors |
| mypy | 8 errors |
| AST | 6 passed |
| Katalog | 162 |

Quelle: `docs/HANDOFF-BASELINE.md`. Skript: `tools/quality_gate.py`.

## Was noch offen ist

- **PhaseState** (`werkstatt/phase_state.py`): implementiert,
  aber noch nicht in den Loop integriert (Resume-Logik).
- **Alte Abhaengigkeiten:** `pipeline._approval_und_human_gate`,
  `pipeline.load_project_config` noch in `loop.py`.
- **Scaffolder:** Agent, der Projekt-Ordnerstruktur anlegt.
- **Echter Test mit `security-ai`** (Original, nicht Kopie).
- **CLI-Einstiegspunkt** fuer den Loop.

## Doku

- `AGENTS.md` — Agenten-Einstieg (Befehle, Struktur, Regeln).
- `Bau-Handoff.md` — aktueller Stand, naechster Schritt.
- `docs/INDEX.md` — Diaetaxis (tutorial/howto/reference/explanation).
- `docs/ARCHITEKTUR.md` — Ziel-Architektur.
- `docs/AUFRAEUM-UND-LOOP-PLAN.md` — Block A-E.
- `docs/glossary/index.md` — M-Nummern + Fachbegriffe.
- `docs/ROADMAP.md` — Phasen-Uebersicht.
- `docs/ERLEDIGT.md` — abgeschlossene Bloecke.
- `docs/OFFENE-BLOECKE.md` — offene Bloecke.
