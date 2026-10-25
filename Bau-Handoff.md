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

---

## Zwischenstand 2026-10-24 19:30 — M-348..M-353

**Werkstatt-HEAD:** 99eae5d (M-351). Arbeitsbaum: M-352 + M-353.
**Zielprojekt-HEAD:** f1bd193 (sauber, RERUN-33 zurueckgerollt).
**Baseline:** 1410 / 13 / 8 / 6 / 162.

### Was seit M-348 passiert ist

- **M-348:** Plan-Human-Gate (`_human_gate_plan`). 4 Tests.
  RERUN-32 zeigte: funktioniert (Plan wird angezeigt).
- **M-349:** Planner-Gate-Hook (`hooks/planner_gate.py`).
  Doku-Tasks werden deterministisch abgelehnt.
- **M-350:** Hook erweitert (5 Checks: Doku, action,
  task_files, phasen, phase_id). PLANNER_SYSTEM gekuerzt.
- **M-351:** no_effect-Patches filtern (Builder + Loop).
  RERUN-33 zeigte: Builder liefert old==new, Loop zaehlt
  als updated. M-351 filtert.
- **M-352:** (Arbeitsbaum) Idempotenz NUR bei create +
  Datei existiert. M-318 war zu locker (update wurde
  als "nichts zu tun" gewertet).
- **M-353:** (Arbeitsbaum) Rollback auf sauberen Tree
  bei Loop-Fehler (git reset --hard + git clean).

### RERUN-Ergebnisse (chronologisch)

- **RERUN-27/28:** Vage Aufgabe, Planner plant Doku-Tasks.
  Hook blockt, Loop stoppt. Plan-Human-Gate nicht erreicht.
- **RERUN-29:** Exakte Fakten (kein "Plane neu", sondern
  "ABGELEHNT: regel/fakt/erklaerung/details"). Planner
  ignoriert weiter. Strukturelle LLM-Neigung.
- **RERUN-30:** Praezisierter Befehl ("Sieh dir das Projekt
  an und plane die naechsten logischen Schritte"). Planner
  plant 12 Tasks ohne Phasen. Hook blockt. Loop stoppt.
- **RERUN-31:** Praezisierter Befehl ("Plane fuer den
  Builder"). Planner plant Code statt Doku. Aber .sql
  wird geblockt (M-349f erlaubt .sql).
- **RERUN-32:** Plan-Human-Gate erscheint (11 Tasks,
  5 Phasen). 10/11 Tasks task_ok. Aber Diff nur
  PROGRESS.md — no_effect-Patches.
- **RERUN-33:** Praezisierter Befehl. 11 Tasks, 5 Phasen.
  ECHTE Aenderungen: applier.py +163, change_service.py
  +88, errors.py +10, test_change_applier.py +35.
  Task 11 (update) failed (Reviewer rejected nach
  Reflection). Loop-RC=1.
  **create-Tasks (t3, t5, t10): idempotent, aber Datei
  fehlt** -> fail-open (M-318).
  **Rollback auf f1bd193** durchgefuehrt.

### Aktuelle Blocker (M-352 + M-353)

1. **M-352:** Idempotenz NUR bei create + Datei existiert.
   M-318 war zu locker. Tests (3) muessen angepasst werden:
   - test_builder_idempotent_bei_korrekter_datei
   - test_builder_idempotent_bei_create_und_update
   - test_builder_idempotent_bei_update_mit_korrekter_datei

2. **M-353:** Rollback auf sauberen Tree. `git-Helper` in
   loop.py eingefuegt. ruff-Fehler gefixt (6x noqa BLE001).
   Noch nicht committet.

### Naechster Schritt

1. Drei Idempotenz-Tests anpassen (create statt update).
2. Gate gruen (ruff 13, mypy 8, pytest 1410).
3. Commit M-352 + M-353.
4. RERUN-34 (praezisierter Befehl, create fail-closed).
5. Pruefen: create-Tasks schreiben Dateien ODER
   loop_builder_failed (fail-closed).


---

## Zwischenstand 2026-10-24 20:30 — M-355b..M-360, RERUN-36/37/38

**Werkstatt-HEAD:** f4e45ed (M-360).
**Zielprojekt-HEAD:** 2a0a284 (RERUN-38, auf f1bd193).
**Baseline:** 1411 / 13 / 8 / 6 / 162.

### Was seit RERUN-35 passiert ist

- **M-355b** (403823d): run_builder=False -> sofort return 1.
  M-355 hatte den Loop-Idempotenz-Check entfernt, aber im
  Fehlerpfad fehlte continue/return. RERUN-36 zeigte: Task 3
  (create) scheiterte, Loop fiel 45s durch Verify/Reviewer/
  Reflection, wurde erst von M-359 gefangen.
- **M-356** (b844ab8): Rollback immer auf start-HEAD. M-353
  griff nur bei dirty Ausgang und war invertiert.
- **M-357** (9b31ec8): _run_with_progress re-raised Exceptions
  -> Loop starb ohne Audit. RERUN-35 zeigte: Task 9 lief
  sichtbar, dann LOOP_RC=1 ohne Traceback.
- **M-358/M-358b** (9b31ec8): Footer hartcodiert Tasks: 0/0.
  Jetzt echte Zahlen aus state.tasks_ok_counter.
- **M-359** (9b31ec8): Reviewer-Reject + pytest gruen reichte
  fuer task_ok, auch wenn kein Patch angewendet wurde
  (old_string_not_found). Jetzt: zusaetzlich state.patches
  != [] noetig. Sonst fail-closed.
- **M-360** (f4e45ed): Builder warf builder_zieldatei_nicht_
  gefunden auch bei action=create und fehlender Zieldatei.
  Damit wurde M-352 nie erreicht. Jetzt: create + Datei fehlt
  -> Zieldatei aus task_files, LLM legt sie an.

### RERUN-Ergebnisse

- **RERUN-36:** 4/6, LOOP_RC=1. M-355b entdeckt (45s-Durchfall).
  M-357/358/359 wirken (keine Traceback, Tasks: 4/6,
  fail_closed).
- **RERUN-37:** 4/6, LOOP_RC=1. M-355b wirkt
  (loop_task_failed, grund builder_failed, kein 45s-Durchfall).
  M-360 entdeckt (builder_zieldatei_nicht_gefunden bei create).
- **RERUN-38:** 8/8, LOOP_RC=0, ERFOLGREICH. Erster
  vollstaendiger Durchlauf seit RERUN-23. Echte Aenderung:
  harness/audit/writer.py (+23, Owner-Check im AuditWriter).
  Zielprojekt committed 2a0a284.

### Aktuelle Bloecke

- **M-361:** Test fuer M-355b.
- **M-362:** Test fuer M-360.
- **M-363:** Doku-Pflege Baseline/HISTORISCH.

### Naechster Schritt

1. Doku committen (M-355b..M-360 in Bau-Handoff + OFFENE-BLOECKE).
2. RERUN-39 mit create-lastiger Aufgabe (M-360 gezielt testen).
3. Danach M-361/M-362 (Tests fuer ungetestete Fixes).


---

## Zwischenstand 2026-10-24 20:30 — M-355b..M-360, RERUN-36/37/38

**Werkstatt-HEAD:** f4e45ed (M-360).
**Zielprojekt-HEAD:** 2a0a284 (RERUN-38, auf f1bd193).
**Baseline:** 1411 / 13 / 8 / 6 / 162.

### Was seit RERUN-35 passiert ist

- **M-355b** (403823d): run_builder=False -> sofort return 1.
- **M-356** (b844ab8): Rollback immer auf start-HEAD.
- **M-357** (9b31ec8): Exception -> False statt re-raise.
- **M-358/M-358b** (9b31ec8): Footer mit echten Task-Zahlen.
- **M-359** (9b31ec8): fail-closed bei kein Patch.
- **M-360** (f4e45ed): create + Datei fehlt -> anlegen.

### RERUN-Ergebnisse

- **RERUN-36:** 4/6, LOOP_RC=1. M-355b entdeckt.
- **RERUN-37:** 4/6, LOOP_RC=1. M-355b wirkt, M-360 entdeckt.
- **RERUN-38:** 8/8, LOOP_RC=0, ERFOLGREICH. Erster
  vollstaendiger Durchlauf seit RERUN-23. Zielprojekt committed
  2a0a284.

### Naechster Schritt

1. Doku committen.
2. RERUN-39 mit create-lastiger Aufgabe (M-360 gezielt).
3. M-361/M-362 (Tests fuer ungetestete Fixes).

---

## Zwischenstand 2026-10-25 — M-338-Fix..M-385, RERUN-40..48

**Werkstatt-HEAD:** 5127154 (M-384).
**Zielprojekt-HEAD:** c0216d2 (RERUN-48, auf main).
**Baseline:** 1435 / 13 / 8 / 6 / 162.

### Der Durchbruch

RERUN-48 ist der **erste vollstaendig erfolgreiche Loop-Lauf**
seit RERUN-23 mit dem **kompletten Skillsystem**:

- Explorer messt deterministisch (`ruff check .` -> 1 Datei).
- Planner folgt (`<measured_files>` + `<pflicht>`).
- Builder fixt (I001).
- Verify `ruff_changed` gruen.
- Reviewer approved.
- **ruff: 1 -> 0.** LOOP_RC=0.

### Was seit RERUN-39 passiert ist

**Explorer (M-338-Fix, M-373):**
- Prompt umgeschrieben: "Messe. Rate nicht."
- `_messen()` ruft deterministisch `run_readonly('ruff check .')`
  bzw. `pytest -q`.
- `_extract_dateien()` parst ruff-concise-Output.
- key_files kommen jetzt aus der Messung, nicht aus dem LLM.

**Skills (M-374):**
- `werkstatt/skills.py`: SkillLoader mit Progressive Disclosure
  (Level 1: name+description, Level 2: SKILL.md-Body).
- `werkstatt/tools.py`: run_readonly / run_write mit Whitelist
  (ruff, pytest, grep, find, git status/diff/log, py_compile)
  und Deny (rm, git commit/push, pip install, sudo, curl, wget).
- Skills erweitert um `allowed-tools`.

**Planner (M-375, M-376):**
- Liest `state.explorer_context` (M-375).
- Explorer-Dateien als `<measured_files>` + `<pflicht>` +
  `<erinnerung>` VOR und NACH PLANNER_SYSTEM (M-376,
  Lost-in-the-Middle + Recency-Bias).

**Meta-Skill (M-374):**
- `skills/using-werkstatt/SKILL.md`: "Wenn ein Skill passt,
  MUSST du ihn nutzen. Messe statt raten."
- Explorer + Planner laden es IMMER.

**Live-Renderer (M-377):**
- `_run_with_progress` ruft KEIN spinner_start/stop mehr.
- spinner_start ist idempotent.
- spinner_stop setzt `_live = None` garantiert.

**Verify (M-378):**
- Neue `ruff_changed`-Stage in `.werkstatt/verify.json`.
- `_reflection_loop` sieht ruff-Fehler und ruft Builder erneut.

**Reviewer + noqa (M-380..M-384):**
- M-380: Reviewer-Prompt ignoriert Loop-Doku.
- M-381: patch-format-Skill: `# noqa` nur entfernen, wenn
  Code NICHT absichtlich ist.
- M-382: `_get_git_diff` (reviewer.py + loop.py) schliesst
  `PROGRESS.md` per Pathspec aus.
- M-383: Builder-Reflection: bei RUF100 `# noqa` BEHALTEN.
- M-384: Reviewer-Prompt STRIKT: "PROGRESS.md ist NICHT
  Teil deines Reviews."

**Ruff-Konfiguration (M-385):**
- `RUF100` in `per-file-ignores` fuer `tests/*`.
- Grund: Ruff 0.17 hat DTZ aus dem Default-Set entfernt,
  dadurch wurden die absichtlichen `# noqa: DTZ001`-Tags
  in Negativtests zu RUF100.
- Loesung analog dismech-PR: scoped ignore, `# noqa` bleibt.
- ruff: 5 -> 1 Fehler (nur I001 in test_checks.py).

### RERUN-Ergebnisse (chronologisch)

- **RERUN-40:** Explorer 0 files (M-338-Prompt). Planner 15
  halluzinierte Tasks. Loop-RC=1.
- **RERUN-41:** Explorer 4 files (M-373), Planner 15 falsche
  Tasks (M-376 fehlte). Loop-RC=1.
- **RERUN-42:** Explorer 4 files, Planner 4 Tasks (echte
  Dateien, M-376). Loop-RC=1 (LiveError bei Task 2).
- **RERUN-43:** 4/4 tasks ok, aber RUF100-Fehler von Builder
  eingefuehrt (Verify prueft ruff nicht). Loop-RC=0.
- **RERUN-44:** 1/4 tasks ok. Reviewer rejected wegen
  PROGRESS.md + noqa-Entfernung. Loop-RC=1.
- **RERUN-45:** 1/4. Reviewer rejected 2x. Loop-RC=1.
- **RERUN-46:** 1/4. 3 Reflection-Runden, dann rejected.
  Loop-RC=1.
- **RERUN-47:** 1/4. `builder_patch_no_effect` (M-383: noqa
  nicht entfernt, aber nichts anderes gemacht).
- **RERUN-48:** **1/1, LOOP_RC=0, ruff 1->0.** ERFOLG.

### Aktuelle Bloecke

- **M-361/M-362:** Tests fuer M-355b/M-360 (aus frueheren Bloecken).
- **M-386:** Rollen-Audit (alle Rollen gegen goldenen Standard
  + Widerspruchs-Check).
- **M-387:** RERUN-49 mit schwierigerer Aufgabe (mehrere Fehler,
  verschiedene Typen).

### Naechster Schritt

1. Rollen-Audit (M-386).
2. RERUN-49 (Belastbarkeitstest).
3. Doku nachziehen.

---

## Zwischenstand 2026-10-25 — Architect/Editor + M-416

**Werkstatt-HEAD:** f6a94df (M-415) + M-416 uncommitted.
**Zielprojekt-HEAD:** f436e42 (clean, Rollback nach RERUN-51).
**Baseline:** 1435 / 13 / 8 / 6 / 162.

### Was seit M-390 passiert ist

**M-390:** Heartbeat fuer Verify-Stages (`_verify_stage_with_heartbeat`).
**M-391:** `.env`-Loader (`env_loader.py`, `DEEPSEEK_API_KEY`).
**M-392:** Doku-Exploration (`grep Offen docs/`, `cat STATUS.md`).
**M-393:** pytest-Trigger eingeschraenkt.
**M-394:** Doku-Dateien NICHT als key_files.
**M-395:** Planner liest key_files-Inhalt.
**M-396:** Explorer ueberspringt bei expliziten Dateien.
**M-397:** `<doku_verbot>` im Planner.
**M-398:** Planner Tool-Use (read_file, grep).
**M-399a:** `<datei_pruefung>` im Planner.
**M-399b:** High-Bug fail-closed im Reviewer.
**M-400:** Heartbeat fuer Explorer + Planner.
**M-401:** Task-Groesse 2-5 Min.
**M-402:** `_reflection_loop` mit phase-Parameter.
**M-403:** Builder Tool-Use (explore, read_file, write_file, run_command).
**M-405:** `<hinweis>` statt `<pflicht>` bei leeren key_files.
**M-406:** BUILDER_SYSTEM Tools zuerst.
**M-407:** `_planner_system` entschlackt (4998 -> 2488 Zeichen).
**M-408:** Architect/Editor-Pattern (Planner = Prosa, Builder = Editor).
**M-409:** Architect-Beschreibung anzeigen.
**M-410:** Architect-Anzeige entdoppelt + Plan-Tasks.
**M-411:** Architect + Builder ruff-konform, 10 Runden.
**M-412:** Diff-Limit 50000 + Architect-Text im Reviewer.
**M-413:** max_tokens 16000.
**M-414:** Volle Zieldatei im Reviewer.
**M-415:** Architect API-Stabilitaet + frozen dataclass.
**M-416:** Builder radikal gekuerzt — nur search/replace, keine Tools.

### Das Ziel (Architect/Editor)

**Aider-Muster:** Der Architect (deepseek-reasoner) beschreibt die
Loesung in Prosa. Der Editor (deepseek-chat) setzt sie in
search/replace-Patches um. **Zwei Modelle, zwei Rollen, ein Format.**

**Aider-Zahlen (belegt):**
- DeepSeek solo (diff-Format): 48,4 %
- o1-preview + DeepSeek (Architect/Editor): 80,5 %
- Der Unterschied: Architect/Editor-Trennung.

**Dein Loop:** Planner (Architect) = deepseek-chat, Builder (Editor)
= deepseek-chat. Beide Rollen nutzen dasselbe Modell — aber der
Prompt trennt sie jetzt (M-408, M-416).

### Was funktioniert

- Explorer messt (0-6 files).
- Planner (Architect) baut exzellente Prosa-Loesungen (4395 Zeichen).
- Builder (Editor) schreibt search/replace-Patches.
- Verify (`ruff_changed`) gruen.
- Reviewer findet echte Bugs (M-399b fail-closed).
- Rollback (M-356) greift.

### Was nicht funktioniert

- **ChangeApplier.apply/rollback** (600 Zeilen, 12 Tests):
  Der Builder setzt die Architect-Vorgabe **nicht 1:1** um.
  Reviewer findet reproduzierbar 5-10 Bugs (Fail-closed-Semantik,
  Idempotenz, frozen dataclass).
  RERUN-51 scheitert **immer** an Task 1.

**Das ist ein LLM-Limit:** DeepSeek-Chat (Editor) versteht
"fail closed" nicht semantisch. Der Architect gibt Prosa — der
Editor braucht konkrete Code-Beispiele.

### Naechster Schritt (M-417)

**Architect mit Code-Beispielen:** Der Architect gibt konkrete
Python-Snippets (nicht Prosa). Der Editor kopiert sie.
**Das ist Aider's naechster Schritt** — Code-Beispiele statt
Prosa.

**Aber:** ChangeApplier ist **zu gross** fuer einen Run.
**Manuell** implementieren, M-417 fuer **zukuenftige** komplexe
Aufgaben.

### Aufgabe fuer den naechsten Chat

**Ziel:** Pruefe den Loop im **Jetzt-Zustand**. Finde Logik-Luecken,
Fehler, Widersprueche. Bewerte, ob der Loop **sinnvoll** ist.

**Konkret:**
1. **Lies** `Bau-Handoff.md` (dieser Block), `docs/OFFENE-BLOECKE.md`,
   `docs/ERLEDIGT.md`, `docs/ROADMAP.md`, `docs/ARCHITEKTUR.md`.
2. **Messe** den Loop:
   - `python3 -m tools.quality_gate --json`
   - `pytest -q tests/test_loop.py tests/test_planner_agent.py tests/test_builder_agent.py`
3. **Pruefe** die Rollen-Kette:
   - Explorer → Planner → Builder → Reviewer → Human-Gate.
   - Uebergaben (explorer_context, task_files, patches, reviewer_bugs).
   - Widersprueche (Prompt vs. Code).
4. **Finde** Logik-Luecken:
   - Fehlt ein `continue`/`return`?
   - Wird ein Fehler verschluckt?
   - Ist die Fail-closed-Kette vollstaendig?
5. **Bewerte**:
   - Ist der Loop **sinnvoll** fuer 80% der Aufgaben?
   - Wo sind die **echten** Limits (LLM, Prompt, Architektur)?
   - Was ist der **naechste** richtige Fix?

**Wichtig:** Keine **neuen** Features bauen. **Erst** messen und
analysieren. **Dann** entscheiden.

### Offene Merkposten

- **M-345:** `pipeline.py` (408 KB) + `hard_rules.py` + `agents/*.md`
  + alte Tests loeschen.
- **M-388:** UI-Testing via Chrome DevTools.
- **M-389:** Doku-Pflege im Loop.
- **M-417:** Architect mit Code-Beispielen.
- **M-418:** Loop-Audit (Logik-Luecken, Widersprueche).

---

## Nachtrag: Recherche-Auftrag fuer den naechsten Chat

**Zusaetzlich zu "messen und Logik-Luecken finden":**

Der naechste Chat **soll recherchieren**, wie der **Goldstandard**
aussieht und wie man das **Beste aus allen Welten** vereint.

### Was zu recherchieren ist

**1) Aider Architect/Editor (belegt):**
- Architect (Reasoning-Modell) beschreibt Loesung in Prosa.
- Editor (Chat-Modell) setzt sie in search/replace um.
- Aider-Zahlen: DeepSeek solo 48,4 %; R1+Sonnet 64,0 %;
  o1-preview+DeepSeek 85 % [citation:1][citation:13].
- **Frage:** Ist dein Loop-Design (Planner=Architect, Builder=Editor)
  korrekt umgesetzt? Wo weicht es ab?

**2) Loop Engineering (2026):**
- arXiv-Paper: "Stop Hand-Holding Your Coding Agent" .
- Loop-Spezifikation: Trigger, Goal, Verification, Stopping Rule,
  Memory.
- **Frage:** Hat dein Loop eine klare Stopping-Rule? Eine Memory?
  Einen Verifier-Ladder?

**3) Devin Subagents:**
- `subagent_explore` (read-only) vs. `subagent_general` (full tools) [citation:10].
- **Frage:** Entspricht dein Explorer/Builder dieser Trennung?

**4) Multi-Agent-Patterns:**
- Planner → Builder → Validator → Critic → Lead [citation:12].
- **Frage:** Fehlt deinem Loop ein "Validator" (deterministisch)
  oder ein "Critic" (Reviewer)?

### Ziel der Recherche

**Nicht:** Kopieren. **Sondern:** Pruefen, ob dein Loop die
**Prinzipien** umsetzt, die bei den Profis funktionieren.
**Dann:** Bewerten, was fehlt, was ueberfluessig ist, was
widerspruechlich ist.

### Konkrete Fragen an den naechsten Chat

1. **Architect/Editor:** Ist die Trennung sauber? (Prompt, Modell,
   Edit-Format)
2. **Verifier-Ladder:** Prueft dein Loop deterministisch (ruff,
   pytest) **vor** dem Reviewer? Oder nur der Reviewer?
3. **Stopping-Rule:** Wann bricht der Loop ab? (Max Runden?
   Max Reflection? Fail-closed?)
4. **Memory:** Was weiss der Loop ueber vergangene Runs?
   (`PROGRESS.md`, `phase_state`, `audit-logs`)
5. **Human-Gate:** Ist der Mensch **richtig** platziert?
   (Nach Planner? Nach Reviewer? Nach beidem?)
6. **Kontext-Explosion:** Bekommt der Builder **zu viel** Kontext?
   (Architect-Text + `_file_context` + `user_content`)
7. **Edit-Format:** search/replace vs. whole-file — was ist
   **wirklich** besser fuer deine Dateien?

### Wichtig

**Erst messen, dann recherchieren, dann bewerten.**
**Keine neuen Features bauen.** Der naechste Chat **soll nicht
fixen** — er **soll verstehen**.
