# Werkstatt

Das Agenten-System. Unabhaengig von jedem Projekt.
Es baut Projekte, aber es gehoert keinem Projekt.

**Ziel:** Das Beste aus Claude Code, Copilot, Aider, Cursor,
Grok und Codex nehmen und ein eigenes Agentensystem bauen.

**Kernprinzip:** On-Demand-Messung + deterministische Gates.
Der Loop prueft, bevor er baut. Kein LLM-Token ohne Plan.

**Stand 2026-10-24 (nach M-322..M-343c, RERUN-23/24):**

- **Baseline:** 1401 Tests, ruff 13, mypy 8, AST 6, Katalog 162.
- **HEAD:** a4c487d. Branch: umbau/phase-2 (origin gepusht).
- **Loop:** Ende-zu-Ende gruen (RERUN-23/24, Loop-RC=0).

## Loop-Architektur

Der Orchestrator ist `werkstatt/loop.py` (run_pipeline_loop).
Er ruft pro Task:

1. **Explorer** (`werkstatt/explorer.py`) — read-only Kontext,
   JSON mit key_files. Wird durch M-338 (nur explizit genannte
   Dateien) gehaertet, liefert bei Phasen-Aufgaben oft 0 files
   (kosmetisch, weil M-337-b nur task_files nutzt).
2. **Planner** (`werkstatt/planner.py`) — JSON-Plan
   (tasks, tests, akzeptanzkriterien, phasen). M-323c: Phasen
   sind Pflicht bei >5 Tasks oder >2 Dateien.
3. **Builder** (`werkstatt/builder.py`) — search/replace-Patches
   (create + update). M-337: Zieldatei deterministisch aus
   task_files[0], action wird erzwungen.
4. **PreToolUse-Hook** (`hooks/pre_tool_use.py`) — M-334a:
   AST-basierte Import-Validierung. Blockt erfundene Imports
   deterministisch.
5. **Simplify-Hook** (`hooks/simplify.py`) — Aufraeumer:
   Komplexitaet, Duplikate.
6. **Verify** (`_verify_patches`) — verify.json-Stages:
   py_compile_changed, pytest_changed, py_compile_core,
   pytest_full_checks. M-322: {changed_files},
   {changed_test_files}, {changed_py_files}-Platzhalter.
   M-340: py_compile nur auf .py.
7. **Reviewer** (`werkstatt/reviewer.py`) — Bug-Check im
   Zielprojekt. M-343c: pytest ist das letzte Wort —
   Reviewer-Reject wird ignoriert, wenn last_verify_errors
   leer ist (= Tests gruen).
8. **Human-Gate** (`_human_gate` in loop.py) — fail-closed,
   respektiert require_human_approval.

**PostToolUse-Hook wurde entfernt** (M-334b): Er prueft die
Werkstatt-Baseline statt des Zielprojekts und war redundant
zu _verify_patches.

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
    |     Builder -> PreToolUse -> Patch -> Simplify           |
    |              -> Verify -> Reviewer                       |
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

Beispiel `verify.json` (security-ai):

    {
      "stages": [
        {"id": "py_compile_changed",
         "command": ["python3", "-m", "py_compile", "{changed_py_files}"],
         "phase": "post_build"},
        {"id": "pytest_changed",
         "command": ["python3", "-m", "pytest", "{changed_test_files}", "-q"],
         "phase": "post_build"},
        {"id": "py_compile_core",
         "command": ["python3", "-m", "py_compile", "core/__init__.py"],
         "phase": "post_build"},
        {"id": "pytest_full_checks",
         "command": ["python3", "-m", "pytest", "tests/unit/test_checks.py", "-q"],
         "phase": "phase_end"}
      ]
    }

## Aufruf

Der Loop wird ueber Python aufgerufen (CLI folgt, M-347):

    python3 -m werkstatt.loop \
      --project security-ai \
      --aufgabe "Refaktoriere core/checks/ in logische Phasen..."

Alternativ mit `WERKSTATT_RENDER=pretty` (M-321) fuer
strukturierte Ausgabe ohne ANSI-Codes:

    WERKSTATT_RENDER=pretty python3 -m werkstatt.loop ... | tee log

## Sicherheit

- **Kein shell=True.** Argumentlisten.
- **PreToolUse-Hook:** blockt .env-Dateien, destruktive
  Kommandos (git reset --hard, rm -rf /), leere Patches,
  erfundene Imports (M-334a).
- **Datei-Existenz-Check:** create ueberschreibt keine
  bestehende Datei (loop_patch_file_exists).
- **Whitelist:** read_file nur aus file_whitelist.
- **Redaction** vor jedem LLM-Call.
- **Human-Gate fail-closed:** bei EOFError -> reject.
- **pytest als letztes Wort** (M-343c): Reviewer-Reject wird
  ignoriert, wenn Tests gruen sind.
- **Audit-JSONL** pro Tag mit project und run_id.

## Baseline

| Metrik | Wert |
|---|---|
| pytest | 1401 passed |
| ruff | 13 errors |
| mypy | 8 errors |
| AST | 6 passed |
| Katalog | 162 |

Quelle: `docs/HANDOFF-BASELINE.md`. Skript: `tools/quality_gate.py`.

## Struktur

    /opt/werkstatt/
    ├── pipeline.py              Alter Monolith (11.639 Z., Fallback, M-345)
    ├── werkstatt/               Neue Module
    │   ├── loop.py              Orchestrator
    │   ├── loop_renderer.py     CI-Optik (M-321: WERKSTATT_RENDER=pretty)
    │   ├── agent.py             ask_llm, execute_commands
    │   ├── explorer.py          Read-only Kontext
    │   ├── planner.py           JSON-Plan (M-323c: Phasen-Pflicht)
    │   ├── builder.py           search/replace (M-337: deterministisch)
    │   ├── reviewer.py          Bug-Check (M-343c: pytest entscheidet)
    │   ├── phase_state.py       Resume, Decisions (M-323a/d: action durchgereicht)
    │   ├── state.py             RunState, Measurement
    │   ├── config.py            Config-Wrapper
    │   └── ...                  (weitere Module)
    ├── hooks/                   Deterministische Hooks
    │   ├── pre_tool_use.py      Waechter + Import-Validierung (M-334a)
    │   ├── simplify.py          Aufraeumer
    │   └── anti_patterns.py     Anti-Patterns
    ├── agents/                  Rollen-Prompts (Markdown)
    ├── skills/                  Skills (SKILL.md)
    ├── projects/                Projekt-Konfigurationen
    ├── tests/                   1401 Tests
    ├── docs/                    Doku (INDEX.md als Einstieg)
    ├── AGENTS.md                Agenten-Einstieg
    ├── Bau-Handoff.md           Aktueller Stand
    └── README.md                Dieses Dokument

## Was noch offen ist

- **M-323b:** Phasen-Checkpoints (`phase_end` pro Phase).
- **M-341:** Explorer ueberspringen bei task_files.
- **M-344:** PROGRESS.md mit Phasen-Header.
- **M-345:** pipeline.py loeschen (erst wenn agent.py-Kopien
  aufgeloest).
- **M-346:** pipeline._approval_und_human_gate verschieben.
- **M-347:** CLI-Einstiegspunkt.

## Doku

- `AGENTS.md` — Agenten-Einstieg (Befehle, Struktur, Regeln).
- `Bau-Handoff.md` — aktueller Stand, naechster Schritt.
- `docs/INDEX.md` — Diaetaxis (tutorial/howto/reference/explanation).
- `docs/ROADMAP.md` — Phasen-Uebersicht.
- `docs/ERLEDIGT.md` — abgeschlossene Bloecke.
- `docs/OFFENE-BLOECKE.md` — offene Bloecke.
- `docs/OFFENE-BLOECKE-ARCHIV-2.md` — archivierte Bloecke (vor 2026-10-24).
- `docs/MERKPOSTEN.md` — M-Nummern.
- `docs/NEUBAU-ZIELBILD.md` — Ziel-Architektur.
- `docs/ARCHITEKTUR.md` — technische Architektur.
