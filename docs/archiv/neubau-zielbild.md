# Zielbild — Aktueller Loop (Stand 2026-10-24)

Branch: umbau/phase-2, HEAD a4c487d.

Das Zielbild ist der **aktuelle Loop** nach M-322..M-343c,
verifiziert durch RERUN-23/24 (Loop-RC=0, 7/7 Tasks, 4 Phasen).

## Rollen (5)

Der Loop hat fuenf Rollen. Jede Rolle hat einen eigenen
Prompt (in `werkstatt/*.py` oder `agents/*.md`) und klare
Verantwortung.

1. **Explorer** (`werkstatt/explorer.py`)
   Read-only Kontext. Liefert `key_files` (explizit genannte
   Dateien). Wird durch M-338 gehaertet: markiert nur Dateien,
   die in der Aufgabe direkt vorkommen. Bei Phasen-Aufgaben
   liefert er oft 0 files (kosmetisch, weil M-337-b nur
   `task_files` nutzt).

2. **Planner** (`werkstatt/planner.py`)
   JSON-Plan: tasks, tests, akzeptanzkriterien, phasen.
   M-323c: Phasen sind Pflicht bei >5 Tasks, >2 Dateien
   oder Keywords (refaktoriere, analysiere, phase, ...).
   Jeder Task hat `action` (read/create/update) und
   `task_files` (explizite Datei-Pfade, M-339: mit Suffix).

3. **Builder** (`werkstatt/builder.py`)
   search/replace-Patches (`old_string` -> `new_string`).
   M-337: Zieldatei deterministisch aus `task_files[0]`,
   `action` wird erzwungen. Der Builder hat KEINE freie Wahl,
   welche Datei er aendert. M-335/336: `task_files` hat
   Vorrang, Ordner werden zu `__init__.py` aufgeloest.

4. **Reviewer** (`werkstatt/reviewer.py`)
   Bug-Check im Zielprojekt. Liest `git diff HEAD` plus
   untracked-Dateien (M-314). M-343c: pytest ist das letzte
   Wort — Reviewer-Reject wird ignoriert, wenn
   `last_verify_errors` leer ist (= Tests gruen).

5. **Human-Gate** (`_human_gate` in `loop.py`)
   fail-closed. Bei EOFError -> reject. Zeigt Diff,
   respektiert `require_human_approval`.

## Hooks (2)

Deterministische Gates, die unabhaengig vom LLM pruefen:

1. **pre_tool_use** (`hooks/pre_tool_use.py`, M-334a)
   AST-basierte Import-Validierung. Prueft `import X` /
   `from X import Y` gegen existierende Module im Zielprojekt.
   Blockt erfundene Imports deterministisch. Standard-Library
   und bekannte Third-Party werden durchgelassen.

2. **simplify** (`hooks/simplify.py`)
   Prueft den Diff auf Komplexitaet (max. 200 Zeilen,
   Duplikate, Over-Engineering).

**post_tool_use wurde entfernt** (M-334b): Er prueft die
Werkstatt-Baseline statt des Zielprojekts und war redundant
zu `_verify_patches`.

## Verify (verify.json)

Der Projekt-Contract definiert, WIE verifiziert wird.
Beispiel security-ai:

- `py_compile_changed` (M-340: nur `.py`, `{changed_py_files}`)
- `pytest_changed` (`{changed_test_files}`)
- `py_compile_core` (feste Dateien)
- `pytest_full_checks` (phase_end, Vollsuite)

M-322: Platzhalter `{changed_files}`, `{changed_test_files}`,
`{changed_py_files}`, `phase_end`.

## Loop-Ablauf

1. Explorer -> key_files (Wegweiser).
2. Planner -> tasks + phasen.
3. `_plan_gate` validiert (M-323c: Phasen-Struktur).
4. Pro Task:
   - Builder -> Patches (M-337: deterministisch).
   - PreToolUse -> Import-Validierung.
   - Apply -> search/replace.
   - Simplify -> Komplexitaet.
   - Verify -> py_compile + pytest.
   - Bei Rot: Reflection (M-329: Builder erneut, nicht git apply).
   - Reviewer -> Bug-Check.
   - Bei Reject + pytest gruen: M-343c ignoriert.
5. Human-Gate -> approve/reject.
6. Loop-RC: 0 = erfolgreich, 1 = fail-closed.

## Was das Zielbild NICHT hat

- **Kein Judge** (alte Rolle, ersetzt durch Reviewer).
- **Kein Debugger, Test-Runner, Verifier** als eigene
  Subagenten (alte Phase-1-Idee, nicht implementiert).
- **Kein separater Scaffolder** (M-312, M-313 sind Merkposten,
  nicht Teil des aktuellen Loops).
- **Kein Pipeline-Trichotomie** (M-298 ist erledigt,
  pipeline.py ist Altlast, M-345).

## Was noch fehlt

- M-323b: `phase_end`-Checkpoint pro Phase.
- M-341: Explorer ueberspringen bei `task_files`.
- M-344: PROGRESS.md mit Phasen-Header.
- M-345: pipeline.py loeschen.
- M-346: pipeline._approval_und_human_gate verschieben.
- M-347: CLI-Einstiegspunkt.

## Beweis

RERUN-23 (Loop-RC=0, 7/7 Tasks, 4 Phasen):
  core/checks/__init__.py +115 (Docstrings + Typannotationen)
  docs/STATUS.md +30
  53 Tests gruen.

RERUN-24 (Loop-RC=0, 7/7 Tasks, 4 Phasen):
  core/checks/__init__.py +85/-25
  docs/STATUS.md +4
  53 Tests gruen.
