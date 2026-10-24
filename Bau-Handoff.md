# Bau-Handoff — Werkstatt

Stand: 2026-10-24 (nach M-322..M-343c, RERUN-23/24).
Werkstatt-HEAD: a4c487d. Branch: umbau/phase-2 (origin gepusht).
Zielprojekt-HEAD: f1bd193 (security-ai, RERUN-24).
Baseline: 1401 / 13 / 8 / 6 / 162.

## Loop-Neubau — Status: FERTIG

Der Loop laeuft Ende-zu-Ende. Beweis: RERUN-23 und RERUN-24,
beide Loop-RC=0, 7/7 Tasks, 4 Phasen.

Aufgabe: "Refaktoriere core/checks/ in logische Phasen:
analysiere alle check_port_*-Funktionen, dokumentiere sie
mit Docstrings und Typannotationen, schreibe Grenzfall-Tests."

Ergebnis RERUN-23:
- core/checks/__init__.py +115 (Docstrings + Typannotationen)
- docs/STATUS.md +30
- PROGRESS.md +25
- 53 Tests gruen, Human-Gate approved.

Ergebnis RERUN-24 (Reproduzierbarkeit):
- core/checks/__init__.py +85/-25
- docs/STATUS.md +4
- PROGRESS.md +21
- 53 Tests gruen, Human-Gate approved.

## Architektur (5 Rollen, 2 Hooks)

Der Loop ruft pro Task:

1. **Explorer** (`werkstatt/explorer.py`) — read-only,
   `key_files`.
2. **Planner** (`werkstatt/planner.py`) — JSON-Plan,
   M-323c: Phasen-Pflicht.
3. **Builder** (`werkstatt/builder.py`) — search/replace,
   M-337: Zieldatei + action erzwungen.
4. **PreToolUse-Hook** (`hooks/pre_tool_use.py`, M-334a) —
   Import-Validierung deterministisch.
5. **Simplify-Hook** (`hooks/simplify.py`) — Komplexitaet.
6. **Verify** (`_verify_patches`) — verify.json-Stages,
   M-322/M-340: Platzhalter + py_compile nur .py.
7. **Reviewer** (`werkstatt/reviewer.py`) — Bug-Check,
   M-343c: pytest entscheidet.
8. **Human-Gate** (`_human_gate`) — fail-closed.

**post_tool_use wurde entfernt** (M-334b): prueft
Werkstatt statt Zielprojekt.

## Strukturelle Fixes (M-322 bis M-343c)

22 Fixes in 17 Commits. Kurzfassung:

| # | Commit | Titel |
|---|---|---|
| M-322 | 3f615af | Verify-Contract (Platzhalter, phase_end) |
| M-324 | 8f31fdf | verify.json mit changed-scope |
| M-326 | 3abe09b | Reflection im Zielprojekt |
| M-328 | 3abb3fb | Reflection-Patch prozess-sicher |
| M-329 | f8becb8 | Reflection nutzt Builder (search/replace) |
| M-330 | d504c77 | Hooks in Reflection |
| M-331 | b9aea97 | Gate fail-closed (failed zaehlt) |
| M-331b | a8db21c | Gate-Tests |
| M-333 | 4dc6a86 | keine halluzinierten Imports |
| M-334a | 42671d2 | pre_tool_use prueft Imports deterministisch |
| M-334b | fee2bb6 | post_tool_use entfernt |
| M-335 | 87c7ed8 | task_files aus Planner priorisieren |
| M-336 | 74cc816 | Ordner in task_files aufloesen |
| M-337 | e005513 | Builder strukturell begrenzt |
| M-337-b/c/d | 5f4e500 | Explorer/Planner/Builder Kontext |
| M-340 | badb75d | py_compile nur .py |
| M-343c | 8a71eb0 | pytest ist das letzte Wort |

## Offene Merkposten

- **M-323b:** Phasen-Checkpoints (`phase_end` pro Phase).
- **M-341:** Explorer ueberspringen bei `task_files`.
- **M-344:** PROGRESS.md mit Phasen-Header.
- **M-345:** pipeline.py loeschen (nach agent.py-Aufloesung).
- **M-346:** pipeline._approval_und_human_gate verschieben.
- **M-347:** CLI-Einstiegspunkt.

## Naechster Block

**M-323b** (Phasen-Checkpoints). Dann M-341/M-344 (kosmetisch),
dann M-345..M-347 (Pipeline-Abbau + CLI).

## Rollback-Anker

c55c849 (historisch), a4c487d (aktuell).
Zielprojekt: f1bd193 (RERUN-24).

## Verweise

- `README.md` — Einstieg (Loop-Architektur).
- `AGENTS.md` — Agenten-Einstieg.
- `docs/ROADMAP.md` — Phasen.
- `docs/ERLEDIGT.md` — Erledigte Bloecke.
- `docs/OFFENE-BLOECKE.md` — offene Bloecke.
- `docs/MERKPOSTEN.md` — M-Nummern.
- `docs/NEUBAU-ZIELBILD.md` — aktueller Loop als Ziel.
- `docs/ARCHITEKTUR.md` — technische Architektur.

---

## Zwischenstand 2026-10-24 18:00 — M-348..M-351

**HEAD:** c9eb707 (M-348). Arbeitsbaum: M-350 in Arbeit.

### M-348 (committet, c9eb707): Plan-Human-Gate

`_human_gate_plan` zwischen Planner und Builder. Zeigt Plan,
fragt j/n/a. 4 Tests. **Bug:** `plan_ok` wird nach `run_planner`
nicht neu berechnet → Gate wird uebersprungen. **M-348-Fix**
liegt im Arbeitsbaum.

### M-349 (Arbeitsbaum): Doku-Tasks via Hook ablehnen

- `hooks/planner_gate.py` neu: prueft `state.tasks` nach
  Doku-Mustern (docs/, CHANGELOG.md, ...).
- `_plan_gate` ruft Hook, speichert `state.last_planner_info`.
- `planner.py` haengt `last_planner_info` an den Prompt.
- **Status:** gebaut, nicht committet.

### M-350 (Arbeitsbaum): Hooks erweitern, Prompts reduzieren

- `planner_gate.py`: 5 Checks (Doku, action, task_files,
  phasen-Pflicht, phase_id).
- `PLANNER_SYSTEM`: von ~80 auf ~40 Zeilen gekuerzt.
- Regeln stehen am **Ende** des Prompts (Recency).
- **Status:** gebaut, nicht committet.

### M-351 (Arbeitsbaum): post_tool_use-Aufruf entfernt

- `loop.py:1167`: toter `_call_hook("post_tool_use.py", {})`
  entfernt (Datei seit M-334b geloescht, Aufruf war fail-open).
- **Status:** gebaut, nicht committet.

### Offene Bugs

1. **M-348-Fix:** `plan_ok` nach `run_planner` neu berechnen.
   (Im Arbeitsbaum, Zeile ~925.)
2. **RERUN-25/26:** Rollback auf f1bd193, `backups/`/`deploy/*`
   waren untracked (kein Verlust). Doku-Aenderungen weg.
3. **`anti_patterns.py`:** wird nie gerufen (tot). Nicht
   angefasst (Entscheidung offen).

### Naechster Schritt

1. M-350-Block ausfuehren (Hooks erweitern).
2. Baseline setzen, Commit M-349+M-350+M-351.
3. RERUN-27 (vage Aufgabe).
